//! Headless fidelity-dry-run baseline, extracted from the GUI's per-skill
//! "Run skill dry-run" action (`MasterSkillApp::start_skill_fidelity_dry_run`
//! in `app.rs`) so it can run without starting the egui window.
//!
//! This intentionally reuses the exact trace-record shape the GUI produces
//! (same label, command string, `TraceAction::FidelityDryRunSkill`, summary
//! computation, and trace store path/capacity) so trace records written by
//! `--baseline` are indistinguishable from ones written by clicking "Run
//! skill dry-run" for every skill in the GUI. The label, command, and
//! success-message formatting are factored into
//! [`skill_dry_run_label_and_command`] and [`skill_dry_run_success_message`]
//! below, which both `app.rs` and this module call, so the two paths can't
//! drift apart.

use std::fs;
use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{anyhow, Result};

use crate::app::{
    desktop_trace_store_path, first_line, summarize_command_output, TRACE_STORE_CAPACITY,
};
use crate::cli::CliClient;
use crate::trace::{TraceAction, TraceStore};

/// Returns the `(label, command)` pair for running a single master skill's
/// fidelity dry-run: `master-{slug}`'s progress label and the
/// `python3 scripts/test-fidelity.py --master master-{slug} --dry-run --json`
/// invocation. Shared by the GUI's `MasterSkillApp::start_skill_fidelity_dry_run`
/// (`app.rs`) and [`run_headless_baseline`]'s loop below so the two paths
/// can't drift apart.
pub(crate) fn skill_dry_run_label_and_command(slug: &str) -> (String, String) {
    (
        format!("Running master-{slug} fidelity dry-run"),
        format!("python3 scripts/test-fidelity.py --master master-{slug} --dry-run --json"),
    )
}

/// Formats the success message for a single master skill's fidelity
/// dry-run, matching [`summarize_command_output`]'s conventions. Shared by
/// the same two callers as [`skill_dry_run_label_and_command`].
pub(crate) fn skill_dry_run_success_message(slug: &str, output: &str) -> String {
    summarize_command_output(&format!("master-{slug} fidelity dry-run finished"), output)
}

/// Runs `python3 scripts/test-fidelity.py --master <slug> --dry-run --json`
/// for every master skill that ships a `tests/fidelity.jsonl` fixture,
/// recording one trace per skill into the standard trace store (honoring
/// `XDG_DATA_HOME` via [`desktop_trace_store_path`]).
///
/// Prints `ok <slug>` / `fail <slug>` per skill and a final
/// `baseline: <n>/<total> ok` summary line. Returns `Ok(0)` if every skill's
/// dry-run succeeded, `Ok(1)` if at least one failed.
pub fn run_headless_baseline() -> Result<i32> {
    let client = CliClient::default();
    let slugs = discover_master_skill_slugs(client.repo_root());

    if slugs.is_empty() {
        return Err(anyhow!(
            "no master-* skills with tests/fidelity.jsonl were found under {:?} \
             (resolved repo root: {:?}). --baseline must be run from inside a \
             cloned Master-skill repo (needs prebuilt/ and scripts/test-fidelity.py); \
             refusing to report a false 0/0 success.",
            client.repo_root().join("prebuilt"),
            client.repo_root()
        ));
    }

    let store_path = desktop_trace_store_path();
    let mut traces = TraceStore::load_from_path(&store_path, TRACE_STORE_CAPACITY)?;

    let total = slugs.len();
    let mut ok_count = 0usize;

    for slug in &slugs {
        let (label, command) = skill_dry_run_label_and_command(slug);
        let trace_id = traces.begin_with_action(
            label,
            TraceAction::FidelityDryRunSkill { slug: slug.clone() },
            Some(command),
            "Queued.",
        );

        let started = Instant::now();
        match client.run_fidelity_dry_run_for(slug) {
            Ok(output) => {
                let message = skill_dry_run_success_message(slug, &output);
                traces.finish_success_with_detail(
                    trace_id,
                    message,
                    output.trim().to_string(),
                    started.elapsed(),
                );
                println!("ok {slug}");
                ok_count += 1;
            }
            Err(err) => {
                let message = format!("{err:#}");
                traces.finish_error_with_detail(
                    trace_id,
                    first_line(&message),
                    message,
                    started.elapsed(),
                );
                println!("fail {slug}");
            }
        }
    }

    traces.save_to_path(&store_path)?;
    println!("baseline: {ok_count}/{total} ok");

    Ok(if ok_count == total { 0 } else { 1 })
}

/// Finds every `master-*` directory under `<repo_root>/prebuilt` that has a
/// `tests/fidelity.jsonl` fixture, returning slugs with the `master-` prefix
/// stripped (e.g. `huineng`), sorted for deterministic run order.
///
/// Mirrors the discovery rule `scripts/test-fidelity.py --all` uses
/// internally, minus non-master fixture directories (e.g. `compare`) that
/// don't match the `master-*` naming scheme the GUI's per-skill trace scope
/// (`master-{slug}`) assumes.
fn discover_master_skill_slugs(repo_root: &Path) -> Vec<String> {
    let prebuilt_dir = repo_root.join("prebuilt");
    let Ok(entries) = fs::read_dir(&prebuilt_dir) else {
        return Vec::new();
    };

    let mut slugs: Vec<String> = entries
        .flatten()
        .filter_map(|entry| {
            let path: PathBuf = entry.path();
            if !path.is_dir() {
                return None;
            }
            let name = entry.file_name().to_string_lossy().to_string();
            let slug = name.strip_prefix("master-")?.to_string();
            if path.join("tests").join("fidelity.jsonl").is_file() {
                Some(slug)
            } else {
                None
            }
        })
        .collect();

    slugs.sort();
    slugs
}
