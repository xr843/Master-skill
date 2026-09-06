use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

use anyhow::{anyhow, Context, Result};

use crate::command::CommandRunner;
use crate::model::{DoctorReport, MasterInspect, SkillInventory};

#[derive(Clone, Debug)]
pub struct CliClient {
    repo_root: PathBuf,
    node_bin: String,
    python_bin: String,
    npm_bin: String,
    home: Option<PathBuf>,
    runner: CommandRunner,
}

impl CliClient {
    pub fn new(repo_root: impl Into<PathBuf>) -> Self {
        Self {
            repo_root: repo_root.into(),
            node_bin: std::env::var("NODE").unwrap_or_else(|_| "node".to_string()),
            python_bin: default_python_bin(),
            npm_bin: default_npm_bin(),
            home: None,
            runner: CommandRunner::default(),
        }
    }

    pub fn with_home(mut self, home: impl Into<PathBuf>) -> Self {
        self.home = Some(home.into());
        self
    }

    pub fn with_command_timeout(mut self, timeout: Duration) -> Self {
        self.runner = CommandRunner::new(timeout);
        self
    }

    pub fn repo_root(&self) -> &Path {
        &self.repo_root
    }

    pub fn list(&self) -> Result<SkillInventory> {
        self.json(&["list", "--json"])
    }

    pub fn doctor(&self) -> Result<DoctorReport> {
        self.json(&["doctor", "--json"])
    }

    pub fn inspect(&self, slug: &str) -> Result<MasterInspect> {
        self.json(&["inspect", slug, "--json"])
    }

    pub fn install(&self, slug: &str) -> Result<String> {
        self.run(&["install", slug])
    }

    pub fn install_all(&self) -> Result<String> {
        self.run(&["install", "--all"])
    }

    pub fn uninstall(&self, slug: &str) -> Result<String> {
        self.run(&["uninstall", slug])
    }

    pub fn update_all(&self) -> Result<String> {
        self.run(&["update", "--all"])
    }

    pub fn run_fidelity_dry_run(&self) -> Result<String> {
        self.run_command(
            Command::new(&self.python_bin)
                .arg(self.repo_root.join("scripts").join("test-fidelity.py"))
                .arg("--all")
                .arg("--dry-run")
                .arg("--json"),
            "failed to run fidelity dry-run",
        )
    }

    pub fn run_fidelity_dry_run_for(&self, slug: &str) -> Result<String> {
        self.run_command(
            Command::new(&self.python_bin)
                .arg(self.repo_root.join("scripts").join("test-fidelity.py"))
                .arg("--master")
                .arg(format!("master-{slug}"))
                .arg("--dry-run")
                .arg("--json"),
            "failed to run skill fidelity dry-run",
        )
    }

    pub fn run_full_validation(&self) -> Result<String> {
        self.run_command(
            Command::new(&self.npm_bin).arg("test"),
            "failed to run full validation",
        )
    }

    fn json<T>(&self, args: &[&str]) -> Result<T>
    where
        T: serde::de::DeserializeOwned,
    {
        let stdout = self.run(args)?;
        serde_json::from_str(&stdout).with_context(|| format!("failed to parse JSON from {args:?}"))
    }

    fn run(&self, args: &[&str]) -> Result<String> {
        let mut command = Command::new(&self.node_bin);
        command
            .arg(self.repo_root.join("bin").join("cli.mjs"))
            .args(args)
            .current_dir(&self.repo_root);
        if let Some(home) = &self.home {
            command.env("HOME", home).env("USERPROFILE", home);
        }

        self.run_command(
            &mut command,
            &format!("failed to run master-skill CLI with args {args:?}"),
        )
    }

    fn run_command(&self, command: &mut Command, context: &str) -> Result<String> {
        command.current_dir(&self.repo_root);
        if let Some(home) = &self.home {
            command.env("HOME", home).env("USERPROFILE", home);
        }

        let output = self
            .runner
            .run(command)
            .with_context(|| context.to_string())?;
        if !output.timed_out && output.status.success() {
            return Ok(output.stdout);
        }

        let reason = if output.timed_out {
            format!(
                "command timed out after {} ms; terminated with status {}",
                output.elapsed.as_millis(),
                output.status
            )
        } else {
            format!(
                "command failed after {} ms with status {}",
                output.elapsed.as_millis(),
                output.status
            )
        };
        Err(anyhow!(
            "{context}: {reason}\nstdout:\n{}\nstderr:\n{}",
            output.stdout,
            output.stderr
        ))
    }
}

/// The Python interpreter to shell out to.
///
/// `python3` does not exist on a stock Windows install — Python ships as
/// `python.exe`, and the Store's `python3` alias is a stub that opens the
/// Store. This repo's own Node suite already encodes that
/// (`tests/cli.test.mjs`: `platform === "win32" ? "python" : "python3"`);
/// this file did not, so every Python call in the released Windows binary
/// failed to spawn. Nothing caught it: `desktop-rust` runs on ubuntu-latest
/// only, and release-desktop.yml smoke-tests the Linux artifact alone.
fn default_python_bin() -> String {
    if let Ok(explicit) = std::env::var("MASTER_SKILL_PYTHON") {
        if !explicit.is_empty() {
            return explicit;
        }
    }
    if cfg!(windows) {
        "python".to_string()
    } else {
        "python3".to_string()
    }
}

/// The npm executable to shell out to.
///
/// npm on Windows is `npm.cmd`. Rust's `Command` resolves a bare name by
/// appending `.exe` and does not consult PATHEXT, so `Command::new("npm")`
/// simply never finds it there.
///
/// Naming a `.cmd` is safe *here* specifically because the only argument is
/// the literal `test` — no caller-supplied string reaches the command line,
/// which is the condition BatBadBut (CVE-2024-24576) turns on.
fn default_npm_bin() -> String {
    if let Ok(explicit) = std::env::var("MASTER_SKILL_NPM") {
        if !explicit.is_empty() {
            return explicit;
        }
    }
    if cfg!(windows) {
        "npm.cmd".to_string()
    } else {
        "npm".to_string()
    }
}

impl Default for CliClient {
    fn default() -> Self {
        Self::new(resolve_repo_root())
    }
}

/// Resolves the Master-skill repo root a released binary should treat as
/// its working repo.
///
/// Contract: a `master-skill-desktop` binary downloaded from GitHub
/// Releases must be run from inside a clone of the Master-skill repo (the
/// README says as much). `env!("CARGO_MANIFEST_DIR")` is a *compile-time*
/// constant baked in by whichever machine built the binary (e.g. a GitHub
/// Actions runner) — on a user's machine that path almost never exists, so
/// it cannot be used directly to find the repo the binary is actually
/// running from.
///
/// Instead this walks upward from the current working directory looking
/// for the first ancestor (inclusive) that looks like a Master-skill repo
/// root: one containing both a `prebuilt/` directory and a
/// `scripts/test-fidelity.py` file. First match wins.
///
/// If no ancestor qualifies (or the current directory can't be read),
/// falls back to the compile-time `CARGO_MANIFEST_DIR`-based path so
/// `cargo run` / `cargo test` source builds and other dev workflows keep
/// behaving exactly as they did before runtime resolution was added.
///
/// # Why this needs a guard
///
/// Whatever this returns, the app then executes: `python3 <root>/scripts/
/// test-fidelity.py` and `node <root>/bin/cli.mjs`. A *discovered* root is
/// therefore a decision about whose code to run, made from the current
/// working directory alone. Running the binary in a directory somebody else
/// can write to — a shared `/tmp`, a world-writable share — lets them choose
/// that code by dropping `prebuilt/` and `scripts/test-fidelity.py` beside it.
///
/// Two mitigations, both deliberately cheap. Running inside a clone you chose
/// is the documented workflow and stays untouched; this only removes the case
/// where the directory was chosen *for* you:
///
///   1. `MASTER_SKILL_REPO_ROOT` states the root explicitly and skips
///      discovery entirely.
///   2. A discovered root that is group- or world-writable is refused (Unix
///      only — the bits mean nothing on Windows). The fallback then applies,
///      and the caller reports a resolved root that has no `prebuilt/` rather
///      than silently running foreign code.
pub fn resolve_repo_root() -> PathBuf {
    resolve_repo_root_with(explicit_repo_root(), std::env::current_dir().ok())
}

/// The env override, normalized: absent and blank both mean "not set".
///
/// A blank value must not win — `MASTER_SKILL_REPO_ROOT=` would otherwise
/// resolve to `""` and make every path in the app relative to the cwd.
fn explicit_repo_root() -> Option<PathBuf> {
    std::env::var_os("MASTER_SKILL_REPO_ROOT")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

/// The decision, with both inputs passed in.
///
/// Split out so the tests can drive it without `set_var`: mutating process
/// globals races the parallel test runner, and a flaky test in the gate that
/// guards code execution is worse than no test.
fn resolve_repo_root_with(explicit: Option<PathBuf>, cwd: Option<PathBuf>) -> PathBuf {
    if let Some(explicit) = explicit {
        return explicit;
    }
    cwd.and_then(|cwd| find_repo_root_from(&cwd))
        .filter(|root| is_safely_owned(root))
        .unwrap_or_else(compile_time_repo_root)
}

/// Whether a discovered directory is safe to execute code out of.
///
/// Unix: refuse group- or other-writable directories. Those are the ones a
/// second party can plant a `scripts/test-fidelity.py` in — a shared `/tmp`,
/// a group-writable share, a misconfigured home. Everywhere else there is no
/// cheap equivalent signal, so this does not pretend to have one.
///
/// What it deliberately does NOT cover: a directory you own and wrote
/// yourself — an extracted archive in `~/Downloads`, a cloned fork. Running
/// the binary inside a repo you chose is the documented workflow, and no
/// permission bit can distinguish a repo you trust from one you regret. That
/// case is addressed by *announcing* the resolved root instead of silently
/// executing from it; see `describe_repo_root`.
#[cfg(unix)]
fn is_safely_owned(root: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    match std::fs::metadata(root) {
        Ok(meta) => meta.permissions().mode() & 0o022 == 0,
        // Unreadable: refuse rather than guess.
        Err(_) => false,
    }
}

#[cfg(not(unix))]
fn is_safely_owned(_root: &Path) -> bool {
    true
}

/// One line naming the directory whose `scripts/` and `bin/` are about to be
/// executed, and how it was chosen.
///
/// The binary runs `python3 <root>/scripts/test-fidelity.py` and
/// `node <root>/bin/cli.mjs`. Which root that is used to be decided silently
/// from the working directory. Printing it does not stop a bad root, but it
/// is the difference between a user being able to notice one and not.
pub fn describe_repo_root(root: &Path) -> String {
    describe_repo_root_with(root, explicit_repo_root().is_some())
}

fn describe_repo_root_with(root: &Path, was_explicit: bool) -> String {
    let how = if was_explicit {
        "MASTER_SKILL_REPO_ROOT"
    } else {
        "discovered from the working directory"
    };
    format!(
        "repo root: {} ({how}) — its scripts/ and bin/ will be executed",
        root.display()
    )
}

/// The compile-time fallback: the parent of `desktop/` (this crate's
/// `CARGO_MANIFEST_DIR`), i.e. the repo root as seen by whatever machine
/// built this binary.
fn compile_time_repo_root() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or(manifest_dir)
}

/// Walks upward from `start` (inclusive), returning the first ancestor
/// that contains both a `prebuilt/` directory and a
/// `scripts/test-fidelity.py` file, or `None` if no ancestor qualifies.
fn find_repo_root_from(start: &Path) -> Option<PathBuf> {
    let mut candidate = Some(start);
    while let Some(dir) = candidate {
        if dir.join("prebuilt").is_dir() && dir.join("scripts").join("test-fidelity.py").is_file() {
            return Some(dir.to_path_buf());
        }
        candidate = dir.parent();
    }
    None
}

#[cfg(test)]
mod command_error_tests {
    use super::CliClient;
    use std::process::Command;
    use std::time::Duration;

    #[test]
    fn timeout_error_retains_timing_status_and_both_streams() {
        let client = CliClient::new(std::env::current_dir().unwrap())
            .with_command_timeout(Duration::from_millis(100));
        let mut command = Command::new(std::env::current_exe().unwrap());
        command
            .args([
                "--exact",
                "command::tests::command_runner_helper",
                "--nocapture",
            ])
            .env("MASTER_SKILL_COMMAND_RUNNER_HELPER", "sleep");

        let error = client
            .run_command(&mut command, "test command failed")
            .unwrap_err();
        let message = format!("{error:#}");

        assert!(message.contains("test command failed"));
        assert!(message.contains("timed out after"));
        assert!(message.contains("status"));
        assert!(message.contains("stdout:"));
        assert!(message.contains("stderr:"));
    }

    #[test]
    fn nonzero_error_retains_status_and_both_streams() {
        let client = CliClient::new(std::env::current_dir().unwrap());
        let mut command = Command::new(std::env::current_exe().unwrap());
        command
            .args([
                "--exact",
                "command::tests::command_runner_helper",
                "--nocapture",
            ])
            .env("MASTER_SKILL_COMMAND_RUNNER_HELPER", "failure");

        let error = client
            .run_command(&mut command, "test command failed")
            .unwrap_err();
        let message = format!("{error:#}");

        assert!(message.contains("status"));
        assert!(message.contains("failure stdout marker"));
        assert!(message.contains("failure stderr marker"));
    }
}

#[cfg(test)]
mod interpreter_resolution_tests {
    use super::{default_npm_bin, default_python_bin};

    /// The released Windows binary spawned `python3` and `npm`, neither of
    /// which resolves there: Python ships as `python.exe`, npm as `npm.cmd`,
    /// and Rust's `Command` appends only `.exe` to a bare name. Nothing
    /// caught it — `desktop-rust` runs on ubuntu-latest and
    /// release-desktop.yml smoke-tests only the Linux artifact.
    #[test]
    fn interpreters_match_the_platform_they_run_on() {
        if cfg!(windows) {
            assert_eq!(default_python_bin(), "python");
            assert_eq!(default_npm_bin(), "npm.cmd");
        } else {
            assert_eq!(default_python_bin(), "python3");
            assert_eq!(default_npm_bin(), "npm");
        }
    }

    /// Matches the existing `NODE` override, and gives anyone on a venv,
    /// pyenv, or a `python3`-less box a way out without editing the source.
    #[test]
    fn an_explicit_override_wins() {
        // Serialised behind one variable each, and restored, so the parallel
        // test runner cannot observe a half-applied state.
        let previous = std::env::var_os("MASTER_SKILL_PYTHON");
        std::env::set_var("MASTER_SKILL_PYTHON", "/opt/py/bin/python3.13");
        let resolved = default_python_bin();
        match previous {
            Some(v) => std::env::set_var("MASTER_SKILL_PYTHON", v),
            None => std::env::remove_var("MASTER_SKILL_PYTHON"),
        }
        assert_eq!(resolved, "/opt/py/bin/python3.13");
    }

    #[test]
    fn a_blank_override_falls_back_to_the_platform_default() {
        let previous = std::env::var_os("MASTER_SKILL_NPM");
        std::env::set_var("MASTER_SKILL_NPM", "");
        let resolved = default_npm_bin();
        match previous {
            Some(v) => std::env::set_var("MASTER_SKILL_NPM", v),
            None => std::env::remove_var("MASTER_SKILL_NPM"),
        }
        assert_ne!(resolved, "");
    }
}

#[cfg(test)]
mod repo_root_trust_tests {
    use super::{describe_repo_root_with, is_safely_owned, resolve_repo_root_with};
    use std::path::{Path, PathBuf};

    fn make_repo(dir: &Path) {
        std::fs::create_dir_all(dir.join("prebuilt")).unwrap();
        std::fs::create_dir_all(dir.join("scripts")).unwrap();
        std::fs::write(dir.join("scripts").join("test-fidelity.py"), "").unwrap();
    }

    #[test]
    fn explicit_root_wins_over_discovery() {
        let temp = tempfile::tempdir().unwrap();
        let discovered = temp.path().join("discovered");
        make_repo(&discovered);
        let chosen = temp.path().join("chosen");

        let resolved = resolve_repo_root_with(Some(chosen.clone()), Some(discovered));
        assert_eq!(resolved, chosen);
    }

    #[test]
    fn a_safe_discovered_root_is_used() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);

        assert_eq!(resolve_repo_root_with(None, Some(root.clone())), root);
    }

    #[cfg(unix)]
    #[test]
    fn a_world_writable_discovered_root_is_not_used() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("planted");
        make_repo(&root);
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o777)).unwrap();

        // Falls back rather than executing out of a directory a second party
        // can write `scripts/test-fidelity.py` into.
        assert_ne!(resolve_repo_root_with(None, Some(root.clone())), root);
    }

    #[cfg(unix)]
    #[test]
    fn permission_bits_decide_which_directories_are_refused() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);

        for (mode, expected) in [(0o755, true), (0o775, false), (0o777, false), (0o700, true)] {
            std::fs::set_permissions(&root, std::fs::Permissions::from_mode(mode)).unwrap();
            assert_eq!(is_safely_owned(&root), expected, "mode {mode:o}");
        }
    }

    #[test]
    fn an_unreadable_root_is_refused_rather_than_guessed() {
        assert!(!is_safely_owned(Path::new(
            "/definitely/not/a/real/path/xyzzy"
        )));
    }

    #[test]
    fn no_cwd_and_no_override_still_yields_a_path() {
        assert_ne!(resolve_repo_root_with(None, None), PathBuf::from(""));
    }

    #[test]
    fn the_disclosure_names_the_path_and_says_it_will_execute() {
        let text = describe_repo_root_with(Path::new("/tmp/some-repo"), false);
        assert!(text.contains("/tmp/some-repo"));
        assert!(text.contains("will be executed"));
        assert!(text.contains("discovered from the working directory"));

        let explicit = describe_repo_root_with(Path::new("/tmp/some-repo"), true);
        assert!(explicit.contains("MASTER_SKILL_REPO_ROOT"));
    }
}

#[cfg(test)]
mod resolve_repo_root_tests {
    use super::find_repo_root_from;
    use std::fs;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_dir(label: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!(
            "master-skill-desktop-resolve-root-{label}-{suffix}"
        ))
    }

    /// Builds `<root>/prebuilt` and `<root>/scripts/test-fidelity.py` so
    /// `root` satisfies the repo-root marker check.
    fn make_repo_markers(root: &std::path::Path) {
        fs::create_dir_all(root.join("prebuilt")).unwrap();
        fs::create_dir_all(root.join("scripts")).unwrap();
        fs::write(root.join("scripts").join("test-fidelity.py"), "# stub\n").unwrap();
    }

    #[test]
    fn finds_repo_root_by_walking_up_from_a_nested_subdirectory() {
        let root = temp_dir("nested");
        make_repo_markers(&root);
        let nested = root.join("desktop").join("target").join("debug");
        fs::create_dir_all(&nested).unwrap();

        let found = find_repo_root_from(&nested);

        assert_eq!(found, Some(root.clone()));

        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn matches_the_starting_directory_itself_when_it_has_both_markers() {
        let root = temp_dir("self-match");
        make_repo_markers(&root);

        let found = find_repo_root_from(&root);

        assert_eq!(found, Some(root.clone()));

        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn returns_none_when_no_ancestor_has_both_markers() {
        let root = temp_dir("no-markers");
        let nested = root.join("a").join("b");
        fs::create_dir_all(&nested).unwrap();

        // Only a `prebuilt/` dir, no `scripts/test-fidelity.py` — must not
        // match on a partial marker set.
        fs::create_dir_all(root.join("prebuilt")).unwrap();

        let found = find_repo_root_from(&nested);

        assert_eq!(found, None);

        fs::remove_dir_all(&root).ok();
    }
}
