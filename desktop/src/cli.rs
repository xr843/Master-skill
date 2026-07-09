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

        let output = command
            .output()
            .with_context(|| format!("failed to run master-skill CLI with args {args:?}"))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        if output.status.success() {
            return Ok(stdout);
        }

        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(anyhow!(
            "master-skill CLI failed with status {}: {}{}",
            output.status,
            stdout,
            stderr
        ))
    }
}

impl Default for CliClient {
    fn default() -> Self {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let repo_root = manifest_dir
            .parent()
            .map(Path::to_path_buf)
            .unwrap_or(manifest_dir);
        Self::new(repo_root)
    }
}
