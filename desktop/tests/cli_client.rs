use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use master_skill_desktop::cli::CliClient;

fn repo_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn temp_home() -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!("master-skill-desktop-test-{suffix}"))
}

#[test]
fn installs_and_uninstalls_one_master_in_isolated_home() {
    let home = temp_home();
    fs::create_dir_all(&home).unwrap();

    let client = CliClient::new(repo_root()).with_home(&home);

    let install_output = client.install("huineng").unwrap();
    assert!(install_output.contains("master-huineng"));
    assert!(client.inspect("huineng").unwrap().installed);

    let uninstall_output = client.uninstall("huineng").unwrap();
    assert!(uninstall_output.contains("removed"));
    assert!(!client.inspect("huineng").unwrap().installed);

    fs::remove_dir_all(home).unwrap();
}

#[test]
fn runs_fidelity_dry_run_from_repo_root() {
    let client = CliClient::new(repo_root());

    let output = client.run_fidelity_dry_run().unwrap();
    let payload: serde_json::Value = serde_json::from_str(&output).unwrap();

    assert!(payload.as_array().unwrap().len() > 1);
    assert!(payload
        .as_array()
        .unwrap()
        .iter()
        .any(|suite| suite["master"] == "master-huineng"));
}

#[test]
fn runs_single_skill_fidelity_dry_run_from_repo_root() {
    let client = CliClient::new(repo_root());

    let output = client.run_fidelity_dry_run_for("huineng").unwrap();
    let payload: serde_json::Value = serde_json::from_str(&output).unwrap();
    let suites = payload.as_array().unwrap();

    assert_eq!(suites.len(), 1);
    assert_eq!(suites[0]["master"], "master-huineng");
    assert!(suites[0]["results"].as_array().unwrap().len() > 1);
}
