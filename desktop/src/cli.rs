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
            // Through the same helper as the other two: `NODE=` set but blank
            // used to resolve to "", which spawns nothing at all. It predates
            // the python/npm resolvers and did not get their guard.
            node_bin: resolve_interpreter(std::env::var_os("NODE"), "node", "node"),
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
        // `doctor --json` exits 1 when it finds problems and still prints the
        // whole report: the report is the answer, not a failure. Treated as a
        // failed command, the first real problem doctor found made
        // load_snapshot fail, so the console could never show the report
        // written to explain it. Only that shape is accepted — exit 1, no
        // timeout, stdout a report whose status is "problems"; a crash, a
        // timeout or unparseable output is still an error.
        let args = ["doctor", "--json"];
        let context = format!("failed to run master-skill CLI with args {args:?}");
        let output = self
            .runner
            .run(&mut self.cli_command(&args))
            .with_context(|| context.clone())?;
        if !output.timed_out && output.status.code() == Some(1) {
            if let Ok(report) = serde_json::from_str::<DoctorReport>(&output.stdout) {
                if report.status == "problems" {
                    return Ok(report);
                }
            }
        }
        let stdout = self.check_output(output, &context)?;
        serde_json::from_str(&stdout).with_context(|| format!("failed to parse JSON from {args:?}"))
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

    fn cli_command(&self, args: &[&str]) -> Command {
        let mut command = Command::new(&self.node_bin);
        command
            .arg(self.repo_root.join("bin").join("cli.mjs"))
            .args(args)
            .current_dir(&self.repo_root);
        if let Some(home) = &self.home {
            command.env("HOME", home).env("USERPROFILE", home);
        }
        command
    }

    fn run(&self, args: &[&str]) -> Result<String> {
        self.run_command(
            &mut self.cli_command(args),
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
        self.check_output(output, context)
    }

    fn check_output(&self, output: crate::command::CommandOutput, context: &str) -> Result<String> {
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
    resolve_interpreter(std::env::var_os("MASTER_SKILL_PYTHON"), "python", "python3")
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
    resolve_interpreter(std::env::var_os("MASTER_SKILL_NPM"), "npm.cmd", "npm")
}

/// The decision, with the environment passed in.
///
/// Split out for the same reason `resolve_repo_root_with` was, 100 lines down,
/// and for the same reason its comment gives: driving these through
/// `std::env::set_var` races the parallel test runner. The first version of
/// this module did exactly that and claimed in a comment that restoring the
/// variable made the race impossible — it does not, and the test failed 2 runs
/// in 60. A flaky test in the code that decides which interpreter to execute
/// is worse than no test.
fn resolve_interpreter(
    explicit: Option<std::ffi::OsString>,
    windows_default: &str,
    unix_default: &str,
) -> String {
    if let Some(value) = explicit {
        // `to_str`, not `to_string_lossy`. Lossy conversion turns a non-UTF-8
        // variable into a name full of U+FFFD, which spawns nothing — the same
        // failure the blank guard exists to remove. `NODE`'s previous
        // `std::env::var` fell back to the default on NotUnicode; keep that.
        if let Some(text) = value.to_str() {
            if !text.is_empty() {
                return text.to_string();
            }
        }
    }
    if cfg!(windows) {
        windows_default.to_string()
    } else {
        unix_default.to_string()
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
///   2. A discovered root is refused unless the root, `scripts/`, `bin/` and
///      the files run out of them are all owned by you and not group- or
///      world-writable (Unix only — see `check_root_trust`). The fallback
///      then applies, and the startup line names the refused path and why
///      rather than silently running foreign code.
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
        .filter(|root| check_root_trust(root).is_ok())
        .unwrap_or_else(compile_time_repo_root)
}

/// Why a discovered root was refused: the exact path that failed, and what
/// was wrong with it. Carried into the startup disclosure so the user is told
/// which directory to fix, not just that something was rejected.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Refusal {
    pub path: PathBuf,
    pub reason: String,
}

impl std::fmt::Display for Refusal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} {}", self.path.display(), self.reason)
    }
}

/// Everything under a root that this app executes, or that decides what gets
/// executed, relative to the root. The root itself comes first.
///
/// `scripts/test-fidelity.py` runs under python, `bin/cli.mjs` under node, and
/// `npm test` reads `package.json` to decide what to run. A missing entry is
/// skipped, not refused: `find_repo_root_from` only requires `prebuilt/` and
/// the fidelity script, and nobody but the owner can create the others once
/// the directory above them has passed.
#[cfg(unix)]
const EXECUTED_PATHS: &[&str] = &[
    "",
    "scripts",
    "scripts/test-fidelity.py",
    "bin",
    "bin/cli.mjs",
    "package.json",
];

/// Whether a discovered directory is safe to execute code out of.
///
/// Unix: every path in `EXECUTED_PATHS` must be owned by the effective uid and
/// not group- or other-writable. Those are the paths a second party could use
/// to plant code — a shared `/tmp`, a group-writable share, a misconfigured
/// home. `std::fs::metadata` follows symlinks, so a `scripts/` that links
/// elsewhere is judged by its target, not by the link.
///
/// Until 2026-10-21 this looked at the root's mode bits and nothing else. A
/// reviewer showed the hole: root 0755, `scripts/` 0777, and a planted
/// `scripts/test-fidelity.py` was run by `--baseline` and announced as
/// "discovered from the working directory". Ownership was not checked either,
/// so a 0755 root that belongs to another user passed.
///
/// What it deliberately does NOT cover:
///   - A directory you own and wrote yourself — an extracted archive in
///     `~/Downloads`, a cloned fork. Running the binary inside a repo you chose
///     is the documented workflow, and no permission bit can distinguish a repo
///     you trust from one you regret. That case is addressed by *announcing*
///     the resolved root instead of silently executing from it; see
///     `describe_repo_root`.
///   - The directories *above* the root (or above a symlink's target), and the
///     modules the executed files import (`scripts/*.py`, `lib/`,
///     `node_modules/`). Checking the entry points and their directories closes
///     the planted-file case without walking the whole tree on every start.
fn check_root_trust(root: &Path) -> std::result::Result<(), Refusal> {
    #[cfg(unix)]
    {
        // SAFETY: geteuid has no preconditions and cannot fail.
        let euid = unsafe { libc::geteuid() };
        check_root_trust_as(root, euid)
    }
    // Windows: no check. Mode bits do not exist there, and the real answer —
    // reading each path's ACL and owner SID — is a different mechanism this
    // file does not attempt. A discovered root on Windows is trusted as
    // before; `describe_repo_root` still names it, and `MASTER_SKILL_REPO_ROOT`
    // is the way to pin it. A known gap, written down rather than faked.
    #[cfg(not(unix))]
    {
        let _ = root;
        Ok(())
    }
}

/// `check_root_trust` with the uid passed in, so tests can play "a directory
/// owned by somebody else" without needing root to `chown` one.
#[cfg(unix)]
fn check_root_trust_as(root: &Path, euid: u32) -> std::result::Result<(), Refusal> {
    use std::os::unix::fs::MetadataExt;
    for relative in EXECUTED_PATHS {
        let path = if relative.is_empty() {
            root.to_path_buf()
        } else {
            root.join(relative)
        };
        let meta = match std::fs::metadata(&path) {
            Ok(meta) => meta,
            Err(err) if !relative.is_empty() && err.kind() == std::io::ErrorKind::NotFound => {
                continue
            }
            // Unreadable, or a dangling link: refuse rather than guess.
            Err(err) => {
                return Err(Refusal {
                    path,
                    reason: format!("could not be inspected ({err})"),
                })
            }
        };
        if let Err(reason) = judge_mode_and_owner(meta.mode(), meta.uid(), euid) {
            // Name the target too when a symlink was followed: the thing to
            // fix is the target, and the link alone would not say where it is.
            let reason = match std::fs::canonicalize(&path) {
                Ok(target) if path.is_symlink() => {
                    format!("(a symlink to {}) {reason}", target.display())
                }
                _ => reason,
            };
            return Err(Refusal { path, reason });
        }
    }
    Ok(())
}

/// The rule itself, on raw numbers: owned by `euid`, and no group or other
/// write bit. Returns the human-readable reason on refusal.
#[cfg(unix)]
fn judge_mode_and_owner(mode: u32, owner: u32, euid: u32) -> std::result::Result<(), String> {
    if owner != euid {
        return Err(format!("is owned by uid {owner}, not by you (uid {euid})"));
    }
    if mode & 0o022 != 0 {
        return Err(format!(
            "is group- or world-writable (mode {:04o})",
            mode & 0o7777
        ));
    }
    Ok(())
}

/// One line naming the directory whose `scripts/` and `bin/` are about to be
/// executed, and how it was chosen.
///
/// The binary runs `python3 <root>/scripts/test-fidelity.py` and
/// `node <root>/bin/cli.mjs`. Which root that is used to be decided silently
/// from the working directory. Printing it does not stop a bad root, but it
/// is the difference between a user being able to notice one and not.
pub fn describe_repo_root(root: &Path) -> String {
    describe_repo_root_with(root, &RootProvenance::of(root))
}

/// How the resolved root was actually arrived at.
///
/// The first version of this printed "(discovered from the working directory)"
/// whenever `MASTER_SKILL_REPO_ROOT` was unset — including the one case the
/// guard exists for. A refused directory falls through to
/// `compile_time_repo_root()`, a path from whichever machine built the binary,
/// and the line then named a directory the user has never visited and called it
/// discovered from their cwd, with no hint that anything had been rejected. A
/// disclosure that misdescribes the case it was added for is worse than none.
#[derive(Debug, PartialEq, Eq)]
pub enum RootProvenance {
    Explicit,
    Discovered,
    /// Discovery found a candidate and refused it; this is the build-time
    /// fallback, which almost certainly does not exist here.
    RefusedFellBack {
        rejected: PathBuf,
        /// Which path under it failed, and how — e.g. `…/scripts is group- or
        /// world-writable (mode 0777)`.
        reason: String,
    },
    /// Nothing qualified anywhere up the tree.
    NoneFoundFellBack,
}

impl RootProvenance {
    fn of(resolved: &Path) -> Self {
        if explicit_repo_root().is_some() {
            return Self::Explicit;
        }
        match std::env::current_dir()
            .ok()
            .and_then(|cwd| find_repo_root_from(&cwd))
        {
            Some(found) if found == resolved => Self::Discovered,
            Some(rejected) => {
                let reason = match check_root_trust(&rejected) {
                    Err(refusal) => refusal.to_string(),
                    // Passed now but not when resolved: it changed in between.
                    Ok(()) => "failed the ownership/permission check".to_string(),
                };
                Self::RefusedFellBack { rejected, reason }
            }
            None => Self::NoneFoundFellBack,
        }
    }
}

fn describe_repo_root_with(root: &Path, provenance: &RootProvenance) -> String {
    let how = match provenance {
        RootProvenance::Explicit => "MASTER_SKILL_REPO_ROOT".to_string(),
        RootProvenance::Discovered => "discovered from the working directory".to_string(),
        RootProvenance::RefusedFellBack { rejected, reason } => format!(
            "REFUSED {}: {reason}; it must be owned by you and not group- or \
             world-writable (or set MASTER_SKILL_REPO_ROOT). Fell back to the \
             build-time path",
            rejected.display()
        ),
        RootProvenance::NoneFoundFellBack => {
            "no repo found above the working directory; build-time path".to_string()
        }
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
    use super::{default_npm_bin, default_python_bin, resolve_interpreter};
    use std::ffi::OsString;

    /// The released Windows binary spawned `python3` and `npm`, neither of
    /// which resolves there: Python ships as `python.exe`, npm as `npm.cmd`,
    /// and Rust's `Command` appends only `.exe` to a bare name. Nothing
    /// caught it — `desktop-rust` runs on ubuntu-latest, and at the time
    /// release-desktop.yml smoke-tested only the Linux artifact. Since
    /// 2026-09-14 every release leg runs `--help` and `--baseline`.
    ///
    /// Asserted against literals rather than `cfg!(windows)`, so this cannot
    /// become the tautology `cfg!(windows) == cfg!(windows)` that passes even
    /// with the table inverted.
    #[test]
    fn each_platform_gets_the_name_that_exists_on_it() {
        assert_eq!(resolve_interpreter(None, "python", "python3"), {
            #[cfg(windows)]
            {
                "python"
            }
            #[cfg(not(windows))]
            {
                "python3"
            }
        });
        assert_eq!(resolve_interpreter(None, "npm.cmd", "npm"), {
            #[cfg(windows)]
            {
                "npm.cmd"
            }
            #[cfg(not(windows))]
            {
                "npm"
            }
        });
    }

    /// Matches the existing `NODE` override, and gives anyone on a venv,
    /// pyenv, or a `python3`-less box a way out without editing the source.
    #[test]
    fn an_explicit_override_wins() {
        let chosen = OsString::from("/opt/py/bin/python3.13");
        assert_eq!(
            resolve_interpreter(Some(chosen), "python", "python3"),
            "/opt/py/bin/python3.13"
        );
    }

    /// `MASTER_SKILL_NPM=` set but blank must not resolve to "".
    #[test]
    fn a_blank_override_falls_back_to_the_platform_default() {
        let resolved = resolve_interpreter(Some(OsString::new()), "npm.cmd", "npm");
        assert!(resolved == "npm" || resolved == "npm.cmd");
    }

    /// The wiring: the public helpers must read the variables they document.
    #[test]
    fn the_public_helpers_return_a_usable_name() {
        assert!(!default_python_bin().is_empty());
        assert!(!default_npm_bin().is_empty());
    }
}

#[cfg(test)]
mod repo_root_trust_tests {
    // Every test that calls it is Unix-only; the Windows check is a no-op.
    #[cfg(unix)]
    use super::check_root_trust;
    use super::{describe_repo_root_with, resolve_repo_root_with, RootProvenance};
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

    /// The reviewer's repro (2026-10-21): root 0755, `scripts/` 0777, and a
    /// planted `scripts/test-fidelity.py` was executed by `--baseline` as
    /// "discovered from the working directory". Only the root was checked.
    #[cfg(unix)]
    #[test]
    fn a_world_writable_scripts_dir_under_a_safe_root_is_not_used() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::set_permissions(root.join("scripts"), std::fs::Permissions::from_mode(0o777))
            .unwrap();

        assert_ne!(resolve_repo_root_with(None, Some(root.clone())), root);
    }

    /// Same hole one directory over: `node <root>/bin/cli.mjs` runs too.
    #[cfg(unix)]
    #[test]
    fn a_world_writable_bin_dir_under_a_safe_root_is_not_used() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);
        std::fs::create_dir_all(root.join("bin")).unwrap();
        std::fs::write(root.join("bin").join("cli.mjs"), "").unwrap();
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::set_permissions(root.join("bin"), std::fs::Permissions::from_mode(0o777)).unwrap();

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
            assert_eq!(check_root_trust(&root).is_ok(), expected, "mode {mode:o}");
        }
    }

    // Unix only: on Windows the check is a documented no-op (see
    // `check_root_trust`), so this assertion never held there.
    #[cfg(unix)]
    #[test]
    fn an_unreadable_root_is_refused_rather_than_guessed() {
        assert!(check_root_trust(Path::new("/definitely/not/a/real/path/xyzzy")).is_err());
    }

    /// A full checkout shape — root, scripts/, bin/, package.json, all 0755 /
    /// 0644 and yours — must still pass, or the fix broke the normal case.
    #[cfg(unix)]
    #[test]
    fn a_normal_checkout_with_bin_and_package_json_passes() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);
        std::fs::create_dir_all(root.join("bin")).unwrap();
        std::fs::write(root.join("bin").join("cli.mjs"), "").unwrap();
        std::fs::write(root.join("package.json"), "{}").unwrap();
        for dir in [root.clone(), root.join("scripts"), root.join("bin")] {
            std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o755)).unwrap();
        }
        for file in [
            root.join("scripts/test-fidelity.py"),
            root.join("bin/cli.mjs"),
            root.join("package.json"),
        ] {
            std::fs::set_permissions(&file, std::fs::Permissions::from_mode(0o644)).unwrap();
        }

        assert_eq!(check_root_trust(&root), Ok(()));
        assert_eq!(resolve_repo_root_with(None, Some(root.clone())), root);
    }

    /// The refusal must say which path failed and why — "something was
    /// refused" gives the user nothing to fix.
    #[cfg(unix)]
    #[test]
    fn the_refusal_names_the_failing_subdirectory_and_its_mode() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::set_permissions(root.join("scripts"), std::fs::Permissions::from_mode(0o777))
            .unwrap();

        let refusal = check_root_trust(&root).unwrap_err();
        assert_eq!(refusal.path, root.join("scripts"));
        let text = refusal.to_string();
        assert!(text.contains("group- or world-writable"), "{text}");
        assert!(text.contains("0777"), "{text}");
    }

    /// The executed file itself, not only its directory: a 0666
    /// `test-fidelity.py` in a 0755 `scripts/` can be overwritten in place.
    #[cfg(unix)]
    #[test]
    fn a_world_writable_executed_file_is_refused() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();
        std::fs::set_permissions(root.join("scripts"), std::fs::Permissions::from_mode(0o755))
            .unwrap();
        let script = root.join("scripts").join("test-fidelity.py");
        std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o666)).unwrap();

        assert_eq!(check_root_trust(&root).unwrap_err().path, script);
    }

    /// A `scripts/` symlink is judged by what it points at: the link itself
    /// can only be replaced by whoever can write the root, but its target can
    /// be written by whoever can write the target.
    #[cfg(unix)]
    #[test]
    fn a_symlinked_scripts_dir_is_judged_by_its_target() {
        use std::os::unix::fs::PermissionsExt;
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        std::fs::create_dir_all(root.join("prebuilt")).unwrap();
        let elsewhere = temp.path().join("shared-scripts");
        std::fs::create_dir_all(&elsewhere).unwrap();
        std::fs::write(elsewhere.join("test-fidelity.py"), "").unwrap();
        std::os::unix::fs::symlink(&elsewhere, root.join("scripts")).unwrap();
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();

        // Target safe: the link is fine.
        std::fs::set_permissions(&elsewhere, std::fs::Permissions::from_mode(0o755)).unwrap();
        assert_eq!(check_root_trust(&root), Ok(()));

        // Target world-writable: refused, and the message names the target.
        std::fs::set_permissions(&elsewhere, std::fs::Permissions::from_mode(0o777)).unwrap();
        let refusal = check_root_trust(&root).unwrap_err();
        assert_eq!(refusal.path, root.join("scripts"));
        assert!(
            refusal.reason.contains("shared-scripts"),
            "name the symlink target: {refusal}"
        );
        assert_ne!(resolve_repo_root_with(None, Some(root.clone())), root);
    }

    /// Ownership. `chown`ing a directory to another user needs root, so this
    /// injects the uid instead: the same tree, judged as if we were somebody
    /// else, must be refused at the root with both uids named.
    #[cfg(unix)]
    #[test]
    fn a_root_owned_by_another_uid_is_refused() {
        use std::os::unix::fs::{MetadataExt, PermissionsExt};
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("repo");
        make_repo(&root);
        std::fs::set_permissions(&root, std::fs::Permissions::from_mode(0o755)).unwrap();
        let owner = std::fs::metadata(&root).unwrap().uid();

        assert_eq!(super::check_root_trust_as(&root, owner), Ok(()));
        let refusal = super::check_root_trust_as(&root, owner.wrapping_add(1)).unwrap_err();
        assert_eq!(refusal.path, root);
        assert!(
            refusal.reason.contains(&format!("owned by uid {owner}")),
            "{refusal}"
        );
    }

    /// The rule on raw numbers, so every branch is covered without touching
    /// the filesystem.
    #[cfg(unix)]
    #[test]
    fn the_rule_requires_both_ownership_and_no_group_or_other_write() {
        use super::judge_mode_and_owner;
        let me = 1000;
        for (mode, owner, ok) in [
            (0o040755, me, true),
            (0o040700, me, true),
            (0o100644, me, true),
            (0o040775, me, false),
            (0o040757, me, false),
            (0o041777, me, false), // sticky does not help: we execute what is in it
            (0o040755, 0, false),
            (0o040755, me + 1, false),
        ] {
            assert_eq!(
                judge_mode_and_owner(mode, owner, me).is_ok(),
                ok,
                "mode {mode:o} owner {owner}"
            );
        }
    }

    #[test]
    fn no_cwd_and_no_override_still_yields_a_path() {
        assert_ne!(resolve_repo_root_with(None, None), PathBuf::from(""));
    }

    #[test]
    fn the_disclosure_names_the_path_and_says_it_will_execute() {
        let text =
            describe_repo_root_with(Path::new("/tmp/some-repo"), &RootProvenance::Discovered);
        assert!(text.contains("/tmp/some-repo"));
        assert!(text.contains("will be executed"));
        assert!(text.contains("discovered from the working directory"));

        let explicit =
            describe_repo_root_with(Path::new("/tmp/some-repo"), &RootProvenance::Explicit);
        assert!(explicit.contains("MASTER_SKILL_REPO_ROOT"));
    }

    /// The case the guard exists for must not be described as the normal one.
    #[test]
    fn a_refused_directory_is_named_as_refused() {
        let text = describe_repo_root_with(
            Path::new("/build/machine/path"),
            &RootProvenance::RefusedFellBack {
                rejected: PathBuf::from("/tmp/world-writable"),
                reason: "/tmp/world-writable/scripts is group- or world-writable (mode 0777)"
                    .to_string(),
            },
        );
        assert!(text.contains("REFUSED"));
        assert!(
            text.contains("/tmp/world-writable/scripts is group- or world-writable"),
            "say which path failed and why: {text}"
        );
        assert!(
            text.contains("/tmp/world-writable"),
            "name what was rejected"
        );
        assert!(!text.contains("discovered from the working directory"));
    }

    #[test]
    fn finding_nothing_is_not_described_as_a_discovery() {
        let text = describe_repo_root_with(
            Path::new("/build/machine/path"),
            &RootProvenance::NoneFoundFellBack,
        );
        assert!(text.contains("no repo found"));
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
