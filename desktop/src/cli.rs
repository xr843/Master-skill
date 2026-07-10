use std::path::{Path, PathBuf};
use std::process::Command;

use anyhow::{anyhow, Context, Result};

use crate::model::{DoctorReport, MasterInspect, SkillInventory};

#[derive(Clone, Debug)]
pub struct CliClient {
    repo_root: PathBuf,
    node_bin: String,
    home: Option<PathBuf>,
}

impl CliClient {
    pub fn new(repo_root: impl Into<PathBuf>) -> Self {
        Self {
            repo_root: repo_root.into(),
            node_bin: std::env::var("NODE").unwrap_or_else(|_| "node".to_string()),
            home: None,
        }
    }

    pub fn with_home(mut self, home: impl Into<PathBuf>) -> Self {
        self.home = Some(home.into());
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
            Command::new("python3")
                .arg(self.repo_root.join("scripts").join("test-fidelity.py"))
                .arg("--all")
                .arg("--dry-run")
                .arg("--json"),
            "failed to run fidelity dry-run",
        )
    }

    pub fn run_fidelity_dry_run_for(&self, slug: &str) -> Result<String> {
        self.run_command(
            Command::new("python3")
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
            Command::new("npm").arg("test"),
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

        let output = command.output().with_context(|| context.to_string())?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        if output.status.success() {
            return Ok(stdout);
        }

        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(anyhow!(
            "command failed with status {}: {}{}",
            output.status,
            stdout,
            stderr
        ))
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
fn resolve_repo_root() -> PathBuf {
    std::env::current_dir()
        .ok()
        .and_then(|cwd| find_repo_root_from(&cwd))
        .unwrap_or_else(compile_time_repo_root)
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
