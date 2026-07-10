use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use master_skill_desktop::trace::{EvaluationDecisionBrief, EvaluationDecisionPosture, TraceStore};

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

    // Task 1b: real `--json` dry-run output must actually count toward
    // evaluation coverage, not just exist as opaque trace records. Load the
    // store through the same `TraceStore` the GUI and `--baseline` both use
    // and assert the Quality Gate reaches full coverage and leaves Unproven,
    // exactly as `evaluation_gate_snapshot` (app.rs) computes it.
    let store = TraceStore::load_from_path(&store_path, records.len().max(1))
        .expect("failed to load trace store written by --baseline");
    let coverage = store.evaluation_run_coverage(expected_min);
    assert!(
        coverage.is_complete(),
        "expected full evaluation coverage after --baseline, got {}: {coverage:?}",
        coverage.label()
    );
    assert_eq!(coverage.label(), format!("{expected_min}/{expected_min}"));

    let insights = store.evaluation_failure_insights();
    let trend = store.evaluation_trend_summary(expected_min * 2);
    let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);
    assert_ne!(
        brief.posture,
        EvaluationDecisionPosture::Unproven,
        "Quality Gate should leave Unproven after a full --baseline run: {brief:?}"
    );

    fs::remove_dir_all(&xdg_data_home).ok();
}

/// Builds a directory that *looks* like a Master-skill repo root to the
/// runtime resolver (has `prebuilt/` and `scripts/test-fidelity.py`) but
/// has no `master-*` skills under `prebuilt/`. This is how a released
/// binary run outside a real clone behaves once repo-root resolution is
/// runtime-based: `find_repo_root_from` can match an ancestor that merely
/// has the two marker paths (e.g. a stray/incomplete checkout) while
/// discovering zero skills underneath it.
///
/// A literal, fully empty `cwd` is deliberately *not* used here: this
/// integration test runs the locally built `cargo test` binary, whose
/// compile-time `CARGO_MANIFEST_DIR` fallback always points at this very
/// dev checkout (which does have real `prebuilt/` skills). Walking up from
/// a marker-less empty directory would find nothing and fall through to
/// that fallback by design (see `resolve_repo_root`'s doc comment in
/// `src/cli.rs`) — masking the bug this test exists to catch. Planting the
/// markers directly in `cwd` makes discovery genuinely, deterministically
/// empty regardless of which machine built the test binary.
fn empty_master_skill_repo_dir(label: &str) -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let root =
        std::env::temp_dir().join(format!("master-skill-desktop-empty-repo-{label}-{suffix}"));
    fs::create_dir_all(root.join("prebuilt")).unwrap();
    fs::create_dir_all(root.join("scripts")).unwrap();
    fs::write(root.join("scripts").join("test-fidelity.py"), "# stub\n").unwrap();
    root
}

#[test]
fn baseline_flag_with_no_discovered_skills_fails_loudly_instead_of_reporting_zero_of_zero() {
    let empty_repo = empty_master_skill_repo_dir("baseline");
    let xdg_data_home = temp_xdg_data_home();
    fs::create_dir_all(&xdg_data_home).unwrap();

    let mut command = Command::new(env!("CARGO_BIN_EXE_master-skill-desktop"));
    command
        .arg("--baseline")
        .current_dir(&empty_repo)
        .env("XDG_DATA_HOME", &xdg_data_home);

    let output = run_with_timeout(command, Duration::from_secs(30));
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    assert!(
        !output.status.success(),
        "expected a nonzero exit when no master skills are discovered under the \
         resolved repo root, got {:?}\nstdout:\n{stdout}\nstderr:\n{stderr}",
        output.status.code()
    );
    assert!(
        !stdout.contains("baseline: 0/0 ok"),
        "must never silently report a false 0/0 success, got stdout:\n{stdout}"
    );
    assert!(
        stderr.contains("cloned Master-skill repo"),
        "expected a clear error naming the cloned-repo requirement, got stderr:\n{stderr}"
    );
    assert!(
        stderr.contains(&empty_repo.to_string_lossy().to_string()),
        "expected the error to name the resolved repo-root path {empty_repo:?}, got stderr:\n{stderr}"
    );

    fs::remove_dir_all(&empty_repo).ok();
    fs::remove_dir_all(&xdg_data_home).ok();
}
