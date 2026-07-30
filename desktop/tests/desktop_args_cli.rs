use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn run_desktop(args: &[&str]) -> std::process::Output {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let xdg_data_home =
        std::env::temp_dir().join(format!("master-skill-desktop-args-test-{suffix}"));
    fs::create_dir_all(&xdg_data_home).unwrap();

    let mut command = Command::new(env!("CARGO_BIN_EXE_master-skill-desktop"));
    command
        .args(args)
        .current_dir(repo_root())
        .env("XDG_DATA_HOME", &xdg_data_home)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command
        .spawn()
        .expect("failed to spawn master-skill-desktop");
    let deadline = Instant::now() + Duration::from_secs(10);
    let output = loop {
        if child
            .try_wait()
            .expect("failed to poll desktop child")
            .is_some()
        {
            break child
                .wait_with_output()
                .expect("failed to collect desktop child output");
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            panic!("desktop did not exit for arguments {args:?}");
        }
        std::thread::sleep(Duration::from_millis(20));
    };

    fs::remove_dir_all(xdg_data_home).ok();
    output
}

#[test]
fn help_exits_zero_without_launching_a_window() {
    for flag in ["--help", "-h"] {
        let output = run_desktop(&[flag]);
        assert!(output.status.success(), "{flag} failed: {output:?}");
        assert!(String::from_utf8_lossy(&output.stdout).contains("Usage:"));
    }
}

#[test]
fn unknown_argument_exits_two_and_prints_usage_to_stderr() {
    let output = run_desktop(&["--unknown"]);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert_eq!(output.status.code(), Some(2));
    assert!(stderr.contains("invalid arguments"));
    assert!(stderr.contains("Usage:"));
}

#[test]
fn extra_or_incompatible_arguments_exit_two() {
    for args in [
        vec!["--baseline", "extra"],
        vec!["--baseline", "--help"],
        vec!["--help", "extra"],
    ] {
        let output = run_desktop(&args);
        assert_eq!(output.status.code(), Some(2), "args {args:?}: {output:?}");
    }
}
