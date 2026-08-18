use std::io::{self, Read};
use std::process::{Command, ExitStatus, Stdio};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use anyhow::{anyhow, Context, Result};
use wait_timeout::ChildExt;

pub const DEFAULT_COMMAND_TIMEOUT: Duration = Duration::from_secs(5 * 60);

#[derive(Clone, Debug)]
pub struct CommandRunner {
    timeout: Duration,
}

#[derive(Debug)]
pub struct CommandOutput {
    pub status: ExitStatus,
    pub stdout: String,
    pub stderr: String,
    pub elapsed: Duration,
    pub timed_out: bool,
}

impl CommandRunner {
    pub fn new(timeout: Duration) -> Self {
        Self { timeout }
    }

    pub fn run(&self, command: &mut Command) -> Result<CommandOutput> {
        command
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        let started = Instant::now();
        let mut child = command.spawn().context("failed to spawn child command")?;
        let stdout = child.stdout.take().context("child stdout was not piped")?;
        let stderr = child.stderr.take().context("child stderr was not piped")?;
        let stdout_reader = spawn_reader(stdout);
        let stderr_reader = spawn_reader(stderr);

        let (status, timed_out) = match child.wait_timeout(self.timeout) {
            Ok(Some(status)) => (status, false),
            Ok(None) => {
                let _ = child.kill();
                (
                    child.wait().context("failed to reap timed-out child")?,
                    true,
                )
            }
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = join_reader(stdout_reader, "stdout");
                let _ = join_reader(stderr_reader, "stderr");
                return Err(error).context("failed while waiting for child command");
            }
        };
        let stdout = join_reader(stdout_reader, "stdout")?;
        let stderr = join_reader(stderr_reader, "stderr")?;

        Ok(CommandOutput {
            status,
            stdout: String::from_utf8_lossy(&stdout).into_owned(),
            stderr: String::from_utf8_lossy(&stderr).into_owned(),
            elapsed: started.elapsed(),
            timed_out,
        })
    }
}

impl Default for CommandRunner {
    fn default() -> Self {
        Self::new(DEFAULT_COMMAND_TIMEOUT)
    }
}

fn spawn_reader<R>(mut reader: R) -> JoinHandle<io::Result<Vec<u8>>>
where
    R: Read + Send + 'static,
{
    thread::spawn(move || {
        let mut bytes = Vec::new();
        reader.read_to_end(&mut bytes)?;
        Ok(bytes)
    })
}

fn join_reader(reader: JoinHandle<io::Result<Vec<u8>>>, stream: &str) -> Result<Vec<u8>> {
    reader
        .join()
        .map_err(|_| anyhow!("{stream} reader thread panicked"))?
        .with_context(|| format!("failed to read child {stream}"))
}

#[cfg(test)]
mod tests {
    use super::CommandRunner;
    use std::io::{self, Write};
    use std::process::Command;
    use std::time::{Duration, Instant};

    const HELPER_MODE: &str = "MASTER_SKILL_COMMAND_RUNNER_HELPER";

    #[test]
    fn command_runner_helper() {
        let Ok(mode) = std::env::var(HELPER_MODE) else {
            return;
        };
        if mode == "output" {
            let stdout = vec![b'o'; 128 * 1024];
            let stderr = vec![b'e'; 128 * 1024];
            io::stdout().write_all(&stdout).unwrap();
            io::stderr().write_all(&stderr).unwrap();
        } else if mode == "failure" {
            io::stdout().write_all(b"failure stdout marker").unwrap();
            io::stderr().write_all(b"failure stderr marker").unwrap();
            std::process::exit(7);
        } else if mode == "sleep" {
            std::thread::sleep(Duration::from_secs(5));
        }
    }

    fn helper_command(mode: &str) -> Command {
        let mut command = Command::new(std::env::current_exe().unwrap());
        command
            .args([
                "--exact",
                "command::tests::command_runner_helper",
                "--nocapture",
            ])
            .env(HELPER_MODE, mode);
        command
    }

    #[test]
    fn drains_and_retains_stdout_and_stderr() {
        let output = CommandRunner::new(Duration::from_secs(5))
            .run(&mut helper_command("output"))
            .unwrap();

        assert!(output.status.success());
        assert!(!output.timed_out);
        assert!(output.stdout.matches('o').count() >= 128 * 1024);
        assert!(output.stderr.matches('e').count() >= 128 * 1024);
    }

    #[test]
    fn kills_and_reaps_a_child_after_the_deadline() {
        let started = Instant::now();
        let output = CommandRunner::new(Duration::from_millis(100))
            .run(&mut helper_command("sleep"))
            .unwrap();

        assert!(output.timed_out);
        assert!(!output.status.success());
        assert!(started.elapsed() < Duration::from_secs(2));
    }
}
