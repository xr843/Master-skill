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

fn temp_xdg_data_home() -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!("master-skill-desktop-baseline-test-{suffix}"))
}

/// Number of `master-*` skill directories under `prebuilt/` that ship a
/// `tests/fidelity.jsonl` fixture. Mirrors the discovery rule the headless
/// `--baseline` run and `scripts/test-fidelity.py --all` both use.
fn master_skill_count_with_fidelity(repo_root: &Path) -> usize {
    let prebuilt = repo_root.join("prebuilt");
    let Ok(entries) = fs::read_dir(&prebuilt) else {
        return 0;
    };

    entries
        .flatten()
        .filter(|entry| {
            let path = entry.path();
            let name = entry.file_name();
            let name = name.to_string_lossy();
            path.is_dir()
                && name.starts_with("master-")
                && path.join("tests").join("fidelity.jsonl").is_file()
        })
        .count()
}

/// Runs `command`, killing it and failing the test if it does not exit within
/// `timeout`. Without `--baseline` implemented, the binary falls through to
/// `eframe::run_native` and hangs forever in this display-less sandbox, so a
/// hard deadline is required to keep this test (and its RED phase) from
/// hanging CI.
fn run_with_timeout(mut command: Command, timeout: Duration) -> std::process::Output {
    command
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .stdin(Stdio::null());
    let mut child = command
        .spawn()
        .expect("failed to spawn master-skill-desktop");

    let deadline = Instant::now() + timeout;
    loop {
        if let Some(_status) = child.try_wait().expect("failed to poll child status") {
            return child
                .wait_with_output()
                .expect("failed to collect child output after exit");
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            panic!(
                "master-skill-desktop did not exit within {:?} (still hangs on GUI startup?)",
                timeout
            );
        }
        std::thread::sleep(Duration::from_millis(50));
    }
}

#[test]
fn baseline_flag_runs_headless_and_records_traces_for_all_master_skills() {
    let xdg_data_home = temp_xdg_data_home();
    fs::create_dir_all(&xdg_data_home).unwrap();

    let mut command = Command::new(env!("CARGO_BIN_EXE_master-skill-desktop"));
    command
        .arg("--baseline")
        .current_dir(repo_root())
        .env("XDG_DATA_HOME", &xdg_data_home);

    let output = run_with_timeout(command, Duration::from_secs(120));
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    assert!(
        output.status.success(),
        "expected exit code 0, got {:?}\nstdout:\n{stdout}\nstderr:\n{stderr}",
        output.status.code()
    );
    assert!(
        stdout.contains("baseline:"),
        "expected stdout to contain a `baseline:` summary line, got:\n{stdout}"
    );

    let store_path = xdg_data_home
        .join("master-skill")
        .join("desktop-traces.json");
    assert!(
        store_path.is_file(),
        "expected trace store to exist at {store_path:?}"
    );

    let content = fs::read_to_string(&store_path).expect("failed to read trace store");
    let value: serde_json::Value =
        serde_json::from_str(&content).expect("trace store is not valid JSON");
    let records = value
        .get("records")
        .and_then(serde_json::Value::as_array)
        .expect("trace store JSON has no `records` array");

    let expected_min = master_skill_count_with_fidelity(&repo_root());
    assert!(
        expected_min > 0,
        "sanity check failed: found no master-* skills with tests/fidelity.jsonl"
    );
    assert!(
        records.len() >= expected_min,
        "expected at least {expected_min} trace record(s) (one per master skill with fidelity.jsonl), found {}",
        records.len()
    );

    fs::remove_dir_all(&xdg_data_home).ok();
}
