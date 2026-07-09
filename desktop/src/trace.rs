use std::collections::{BTreeMap, VecDeque};
use std::fs;
use std::path::Path;
use std::time::Duration;

use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub enum TraceStatus {
    Running,
    Succeeded,
    Failed,
}

impl TraceStatus {
    pub fn label(self) -> &'static str {
        match self {
            Self::Running => "running",
            Self::Succeeded => "success",
            Self::Failed => "failed",
        }
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub enum TraceAction {
    Refresh,
    InspectSkill { slug: String },
    InstallSkill { slug: String },
    UninstallSkill { slug: String },
    InstallAll,
    UpdateAll,
    FidelityDryRunAll,
    FidelityDryRunSkill { slug: String },
    FullValidation,
}

impl TraceAction {
    pub fn related_skill_slug(&self) -> Option<&str> {
        match self {
            Self::InspectSkill { slug }
            | Self::InstallSkill { slug }
            | Self::UninstallSkill { slug }
            | Self::FidelityDryRunSkill { slug } => Some(slug),
            Self::Refresh
            | Self::InstallAll
            | Self::UpdateAll
            | Self::FidelityDryRunAll
            | Self::FullValidation => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FailureKind {
    Validation,
    Fidelity,
    Install,
    Runtime,
}

impl FailureKind {
    pub fn label(self) -> &'static str {
        match self {
            Self::Validation => "validation",
            Self::Fidelity => "fidelity",
            Self::Install => "install",
            Self::Runtime => "runtime",
        }
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
pub struct TraceRecord {
    pub id: u64,
    pub label: String,
    pub status: TraceStatus,
    pub summary: String,
    pub detail: String,
    pub command: Option<String>,
    pub action: Option<TraceAction>,
    pub duration_ms: Option<u128>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationRunResult {
    pub slug: String,
    pub passed_count: usize,
    pub total_count: usize,
    pub dry_run: bool,
    pub trace_id: u64,
}

impl EvaluationRunResult {
    pub fn label(&self) -> String {
        let mode = if self.dry_run { "N/A" } else { "graded" };
        format!("{}/{} {mode}", self.passed_count, self.total_count)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationCaseResult {
    pub slug: String,
    pub case_index: usize,
    pub question: String,
    pub difficulty: Option<String>,
    pub status: String,
    pub trace_id: u64,
}

impl TraceRecord {
    pub fn can_rerun(&self) -> bool {
        self.action.is_some() && self.status != TraceStatus::Running
    }

    pub fn related_skill_slug(&self) -> Option<&str> {
        self.action
            .as_ref()
            .and_then(TraceAction::related_skill_slug)
    }

    pub fn failure_kind(&self) -> Option<FailureKind> {
        if self.status != TraceStatus::Failed {
            return None;
        }

        match &self.action {
            Some(TraceAction::FullValidation) => Some(FailureKind::Validation),
            Some(TraceAction::FidelityDryRunAll | TraceAction::FidelityDryRunSkill { .. }) => {
                Some(FailureKind::Fidelity)
            }
            Some(
                TraceAction::InstallSkill { .. }
                | TraceAction::UninstallSkill { .. }
                | TraceAction::InstallAll
                | TraceAction::UpdateAll,
            ) => Some(FailureKind::Install),
            Some(TraceAction::Refresh | TraceAction::InspectSkill { .. }) => {
                Some(FailureKind::Runtime)
            }
            None => classify_failure_text(&format!(
                "{}\n{}\n{}",
                self.label, self.summary, self.detail
            )),
        }
    }

    pub fn evaluation_results(&self) -> Vec<EvaluationRunResult> {
        if !matches!(
            self.action,
            Some(TraceAction::FidelityDryRunAll | TraceAction::FidelityDryRunSkill { .. })
        ) {
            return Vec::new();
        }

        parse_evaluation_results(self.id, &self.detail)
    }

    pub fn evaluation_case_results(&self) -> Vec<EvaluationCaseResult> {
        if !matches!(
            self.action,
            Some(TraceAction::FidelityDryRunAll | TraceAction::FidelityDryRunSkill { .. })
        ) {
            return Vec::new();
        }

        parse_evaluation_case_results(self.id, &self.detail)
    }
}

fn parse_evaluation_case_results(trace_id: u64, detail: &str) -> Vec<EvaluationCaseResult> {
    let Ok(value) = serde_json::from_str::<serde_json::Value>(detail) else {
        return Vec::new();
    };
    let Some(suites) = value.as_array() else {
        return Vec::new();
    };

    let mut case_results = Vec::new();
    for suite in suites {
        let Some(master_name) = suite.get("master").and_then(serde_json::Value::as_str) else {
            continue;
        };
        let Some(slug) = master_name.strip_prefix("master-") else {
            continue;
        };
        let Some(results) = suite.get("results").and_then(serde_json::Value::as_array) else {
            continue;
        };

        for result in results {
            let Some(index) = result.get("index").and_then(serde_json::Value::as_u64) else {
                continue;
            };
            let Some(status) = result.get("status").and_then(serde_json::Value::as_str) else {
                continue;
            };
            case_results.push(EvaluationCaseResult {
                slug: slug.to_string(),
                case_index: index as usize + 1,
                question: result
                    .get("question")
                    .and_then(serde_json::Value::as_str)
                    .unwrap_or("untitled case")
                    .to_string(),
                difficulty: result
                    .get("difficulty")
                    .and_then(serde_json::Value::as_str)
                    .map(str::to_string),
                status: status.to_string(),
                trace_id,
            });
        }
    }

    case_results
}

fn parse_evaluation_results(trace_id: u64, detail: &str) -> Vec<EvaluationRunResult> {
    let mut results = Vec::new();
    let mut current_slug: Option<String> = None;

    for line in detail.lines().map(str::trim) {
        if let Some(rest) = line.strip_prefix("Testing: master-") {
            current_slug = Some(rest.to_string());
            continue;
        }

        if let Some(rest) = line.strip_prefix("Result: ") {
            if let Some(slug) = current_slug.take() {
                if let Some((passed_count, total_count)) = parse_result_counts(rest) {
                    results.push(EvaluationRunResult {
                        slug,
                        passed_count,
                        total_count,
                        dry_run: rest.contains("(N/A)"),
                        trace_id,
                    });
                }
            }
        }
    }

    results
}

fn parse_result_counts(value: &str) -> Option<(usize, usize)> {
    let counts = value.split_whitespace().next()?;
    let (passed, total) = counts.split_once('/')?;
    Some((passed.parse().ok()?, total.parse().ok()?))
}

fn classify_failure_text(text: &str) -> Option<FailureKind> {
    let value = text.to_ascii_lowercase();
    if value.contains("fidelity") || value.contains("fidelity.jsonl") {
        Some(FailureKind::Fidelity)
    } else if value.contains("validation")
        || value.contains("npm test")
        || value.contains("validate")
    {
        Some(FailureKind::Validation)
    } else if value.contains("install")
        || value.contains("uninstall")
        || value.contains("update")
        || value.contains("master-skill cli")
    {
        Some(FailureKind::Install)
    } else if value.trim().is_empty() {
        None
    } else {
        Some(FailureKind::Runtime)
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct TraceSummary {
    pub total: usize,
    pub running: usize,
    pub succeeded: usize,
    pub failed: usize,
    pub last_status: Option<TraceStatus>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct EvaluationRunCoverage {
    pub total_skill_count: usize,
    pub run_skill_count: usize,
    pub dry_run_count: usize,
    pub graded_count: usize,
}

impl EvaluationRunCoverage {
    pub fn label(&self) -> String {
        format!("{}/{}", self.run_skill_count, self.total_skill_count)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct TraceStore {
    capacity: usize,
    next_id: u64,
    records: VecDeque<TraceRecord>,
}

impl TraceStore {
    pub fn new(capacity: usize) -> Self {
        Self {
            capacity,
            next_id: 1,
            records: VecDeque::new(),
        }
    }

    pub fn load_from_path(path: &Path, capacity: usize) -> Result<Self> {
        if !path.is_file() {
            return Ok(Self::new(capacity));
        }

        let content = fs::read_to_string(path)?;
        let mut store: Self = serde_json::from_str(&content)?;
        store.capacity = capacity;
        store.next_id = store
            .records
            .iter()
            .map(|record| record.id)
            .max()
            .unwrap_or(0)
            .saturating_add(1)
            .max(store.next_id);
        store.mark_running_records_interrupted();
        store.enforce_capacity();
        Ok(store)
    }

    pub fn save_to_path(&self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let content = serde_json::to_string_pretty(self)?;
        fs::write(path, content)?;
        Ok(())
    }

    pub fn begin(&mut self, label: impl Into<String>) -> u64 {
        self.begin_with_detail(label, None::<String>, "Started.")
    }

    pub fn begin_with_detail(
        &mut self,
        label: impl Into<String>,
        command: Option<impl Into<String>>,
        detail: impl Into<String>,
    ) -> u64 {
        self.begin_record(label, None, command.map(Into::into), detail)
    }

    pub fn begin_with_action(
        &mut self,
        label: impl Into<String>,
        action: TraceAction,
        command: Option<impl Into<String>>,
        detail: impl Into<String>,
    ) -> u64 {
        self.begin_record(label, Some(action), command.map(Into::into), detail)
    }

    fn begin_record(
        &mut self,
        label: impl Into<String>,
        action: Option<TraceAction>,
        command: Option<String>,
        detail: impl Into<String>,
    ) -> u64 {
        let id = self.next_id;
        self.next_id += 1;
        self.records.push_back(TraceRecord {
            id,
            label: label.into(),
            status: TraceStatus::Running,
            summary: "Started.".to_string(),
            detail: detail.into(),
            command,
            action,
            duration_ms: None,
        });
        self.enforce_capacity();
        id
    }

    pub fn finish_success(&mut self, id: u64, summary: impl Into<String>, duration: Duration) {
        self.finish(
            id,
            TraceStatus::Succeeded,
            summary,
            None::<String>,
            duration,
        );
    }

    pub fn finish_success_with_detail(
        &mut self,
        id: u64,
        summary: impl Into<String>,
        detail: impl Into<String>,
        duration: Duration,
    ) {
        self.finish(
            id,
            TraceStatus::Succeeded,
            summary,
            Some(detail.into()),
            duration,
        );
    }

    pub fn finish_error(&mut self, id: u64, summary: impl Into<String>, duration: Duration) {
        self.finish(id, TraceStatus::Failed, summary, None::<String>, duration);
    }

    pub fn finish_error_with_detail(
        &mut self,
        id: u64,
        summary: impl Into<String>,
        detail: impl Into<String>,
        duration: Duration,
    ) {
        self.finish(
            id,
            TraceStatus::Failed,
            summary,
            Some(detail.into()),
            duration,
        );
    }

    pub fn recent(&self) -> Vec<TraceRecord> {
        self.records.iter().rev().cloned().collect()
    }

    pub fn latest_evaluation_result_for(&self, slug: &str) -> Option<EvaluationRunResult> {
        self.records
            .iter()
            .rev()
            .flat_map(TraceRecord::evaluation_results)
            .find(|result| result.slug == slug)
    }

    pub fn latest_evaluation_results_by_slug(&self) -> Vec<EvaluationRunResult> {
        let mut results = BTreeMap::new();
        for result in self
            .records
            .iter()
            .rev()
            .flat_map(TraceRecord::evaluation_results)
        {
            results.entry(result.slug.clone()).or_insert(result);
        }

        results.into_values().collect()
    }

    pub fn latest_evaluation_case_results_for(&self, slug: &str) -> Vec<EvaluationCaseResult> {
        self.records
            .iter()
            .rev()
            .flat_map(TraceRecord::evaluation_case_results)
            .filter(|result| result.slug == slug)
            .collect()
    }

    pub fn evaluation_run_coverage(&self, total_skill_count: usize) -> EvaluationRunCoverage {
        let results = self.latest_evaluation_results_by_slug();
        EvaluationRunCoverage {
            total_skill_count,
            run_skill_count: results.len(),
            dry_run_count: results.iter().filter(|result| result.dry_run).count(),
            graded_count: results.iter().filter(|result| !result.dry_run).count(),
        }
    }

    pub fn clear(&mut self) {
        self.records.clear();
    }

    pub fn summary(&self) -> TraceSummary {
        TraceSummary {
            total: self.records.len(),
            running: self
                .records
                .iter()
                .filter(|record| record.status == TraceStatus::Running)
                .count(),
            succeeded: self
                .records
                .iter()
                .filter(|record| record.status == TraceStatus::Succeeded)
                .count(),
            failed: self
                .records
                .iter()
                .filter(|record| record.status == TraceStatus::Failed)
                .count(),
            last_status: self.records.back().map(|record| record.status),
        }
    }

    fn finish(
        &mut self,
        id: u64,
        status: TraceStatus,
        summary: impl Into<String>,
        detail: Option<String>,
        duration: Duration,
    ) {
        if let Some(record) = self.records.iter_mut().find(|record| record.id == id) {
            record.status = status;
            record.summary = summary.into();
            if let Some(detail) = detail {
                record.detail = detail;
            }
            record.duration_ms = Some(duration.as_millis());
        }
    }

    fn enforce_capacity(&mut self) {
        while self.records.len() > self.capacity {
            self.records.pop_front();
        }
    }

    fn mark_running_records_interrupted(&mut self) {
        for record in &mut self.records {
            if record.status == TraceStatus::Running {
                record.status = TraceStatus::Failed;
                record.summary = "Interrupted before completion.".to_string();
                record.detail =
                    "Desktop manager closed before this operation reported a result.".to_string();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::PathBuf;
    use std::time::Duration;
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::{FailureKind, TraceAction, TraceStatus, TraceStore};

    fn temp_path(name: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("master-skill-desktop-{name}-{suffix}.json"))
    }

    #[test]
    fn records_success_and_error_traces_with_summary() {
        let mut store = TraceStore::new(10);

        let refresh = store.begin("Refreshing runtime data");
        let validation = store.begin("Running full validation");
        store.finish_success(
            refresh,
            "Runtime data refreshed.",
            Duration::from_millis(42),
        );
        store.finish_error(validation, "npm test failed", Duration::from_millis(125));

        let summary = store.summary();
        assert_eq!(summary.total, 2);
        assert_eq!(summary.running, 0);
        assert_eq!(summary.succeeded, 1);
        assert_eq!(summary.failed, 1);
        assert_eq!(summary.last_status, Some(TraceStatus::Failed));

        let recent = store.recent();
        assert_eq!(recent[0].label, "Running full validation");
        assert_eq!(recent[0].status, TraceStatus::Failed);
        assert_eq!(recent[0].duration_ms, Some(125));
        assert_eq!(recent[1].label, "Refreshing runtime data");
        assert_eq!(recent[1].status, TraceStatus::Succeeded);
    }

    #[test]
    fn records_trace_command_and_detail_for_drilldown() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_detail(
            "Running master-huineng fidelity dry-run",
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Dry-run queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/12 passed (N/A)",
            Duration::from_millis(88),
        );

        let recent = store.recent();
        assert_eq!(
            recent[0].command.as_deref(),
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run")
        );
        assert_eq!(
            recent[0].summary,
            "master-huineng fidelity dry-run finished"
        );
        assert!(recent[0].detail.contains("Testing: master-huineng"));
        assert_eq!(recent[0].duration_ms, Some(88));
    }

    #[test]
    fn records_rerunnable_trace_action_and_related_skill() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Dry-run queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity dry-run finished",
            "Testing: master-huineng",
            Duration::from_millis(91),
        );

        let record = &store.recent()[0];
        assert_eq!(
            record.action,
            Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string()
            })
        );
        assert!(record.can_rerun());
        assert_eq!(record.related_skill_slug(), Some("huineng"));
    }

    #[test]
    fn classifies_failed_trace_kind_from_action_and_detail() {
        let mut store = TraceStore::new(10);

        let validation = store.begin_with_action(
            "Running full validation",
            TraceAction::FullValidation,
            Some("npm test"),
            "Queued.",
        );
        store.finish_error_with_detail(
            validation,
            "npm test failed",
            "validate-fidelity.py failed",
            Duration::from_millis(10),
        );

        let fidelity = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Queued.",
        );
        store.finish_error_with_detail(
            fidelity,
            "fidelity failed",
            "No fidelity.jsonl found",
            Duration::from_millis(11),
        );

        let install = store.begin_with_action(
            "Installing master-huineng",
            TraceAction::InstallSkill {
                slug: "huineng".to_string(),
            },
            Some("master-skill install huineng"),
            "Queued.",
        );
        store.finish_error_with_detail(
            install,
            "install failed",
            "failed to run master-skill CLI",
            Duration::from_millis(12),
        );

        let recent = store.recent();
        assert_eq!(recent[0].failure_kind(), Some(FailureKind::Install));
        assert_eq!(recent[1].failure_kind(), Some(FailureKind::Fidelity));
        assert_eq!(recent[2].failure_kind(), Some(FailureKind::Validation));
    }

    #[test]
    fn indexes_latest_evaluation_result_from_dry_run_trace() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity dry-run finished",
            "\n==================================================\nTesting: master-huineng\n==================================================\n\nResult: 0/12 passed (N/A)\n",
            Duration::from_millis(50),
        );

        let result = store.latest_evaluation_result_for("huineng").unwrap();
        assert_eq!(result.slug, "huineng");
        assert_eq!(result.passed_count, 0);
        assert_eq!(result.total_count, 12);
        assert!(result.dry_run);
        assert_eq!(result.label(), "0/12 N/A");
    }

    #[test]
    fn indexes_latest_evaluation_results_by_skill_from_full_dry_run_trace() {
        let mut store = TraceStore::new(10);

        let old_run = store.begin_with_action(
            "Running fidelity dry-run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --dry-run"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_run,
            "fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/8 passed (N/A)\nTesting: master-zhiyi\nResult: 0/10 passed (N/A)",
            Duration::from_millis(40),
        );

        let new_run = store.begin_with_action(
            "Running fidelity dry-run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --dry-run"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_run,
            "fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/12 passed (N/A)",
            Duration::from_millis(45),
        );

        let results = store.latest_evaluation_results_by_slug();

        assert_eq!(results.len(), 2);
        assert_eq!(results[0].slug, "huineng");
        assert_eq!(results[0].total_count, 12);
        assert_eq!(results[0].trace_id, new_run);
        assert_eq!(results[1].slug, "zhiyi");
        assert_eq!(results[1].total_count, 10);
        assert_eq!(results[1].trace_id, old_run);
    }

    #[test]
    fn indexes_latest_evaluation_case_results_from_json_trace() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity dry-run finished",
            r#"[
              {
                "master": "master-huineng",
                "total": 2,
                "results": [
                  {
                    "index": 0,
                    "question": "什么是见性成佛？",
                    "difficulty": "basic",
                    "status": "dry_run"
                  },
                  {
                    "index": 1,
                    "question": "顿悟怎么修？",
                    "difficulty": "intermediate",
                    "status": "dry_run"
                  }
                ]
              }
            ]"#,
            Duration::from_millis(50),
        );

        let results = store.latest_evaluation_case_results_for("huineng");

        assert_eq!(results.len(), 2);
        assert_eq!(results[0].case_index, 1);
        assert_eq!(results[0].status, "dry_run");
        assert_eq!(results[0].difficulty.as_deref(), Some("basic"));
        assert_eq!(results[0].trace_id, run);
        assert_eq!(results[1].case_index, 2);
        assert_eq!(results[1].question, "顿悟怎么修？");
    }

    #[test]
    fn summarizes_evaluation_run_coverage_from_latest_results() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running fidelity dry-run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --dry-run"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/12 passed (N/A)\nTesting: master-zhiyi\nResult: 0/10 passed (N/A)",
            Duration::from_millis(40),
        );

        let coverage = store.evaluation_run_coverage(18);

        assert_eq!(coverage.total_skill_count, 18);
        assert_eq!(coverage.run_skill_count, 2);
        assert_eq!(coverage.dry_run_count, 2);
        assert_eq!(coverage.graded_count, 0);
        assert_eq!(coverage.label(), "2/18");
    }

    #[test]
    fn persists_trace_history_and_next_record_id() {
        let path = temp_path("trace-history");
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/12 passed (N/A)",
            Duration::from_millis(40),
        );

        store.save_to_path(&path).unwrap();
        let mut restored = TraceStore::load_from_path(&path, 10).unwrap();
        let next = restored.begin("Refreshing runtime data");

        assert_eq!(restored.summary().total, 2);
        assert_eq!(next, 2);
        assert_eq!(
            restored
                .latest_evaluation_result_for("huineng")
                .unwrap()
                .label(),
            "0/12 N/A"
        );

        fs::remove_file(path).unwrap();
    }

    #[test]
    fn marks_persisted_running_traces_as_interrupted_on_load() {
        let path = temp_path("trace-interrupted");
        let mut store = TraceStore::new(10);

        store.begin_with_action(
            "Running full validation",
            TraceAction::FullValidation,
            Some("npm test"),
            "Queued.",
        );

        store.save_to_path(&path).unwrap();
        let restored = TraceStore::load_from_path(&path, 10).unwrap();
        let record = &restored.recent()[0];

        assert_eq!(record.status, TraceStatus::Failed);
        assert_eq!(record.summary, "Interrupted before completion.");
        assert!(record.detail.contains("Desktop manager closed"));

        fs::remove_file(path).unwrap();
    }

    #[test]
    fn enforces_capacity_by_dropping_oldest_trace() {
        let mut store = TraceStore::new(2);

        store.begin("one");
        store.begin("two");
        store.begin("three");

        let recent = store.recent();
        assert_eq!(recent.len(), 2);
        assert_eq!(recent[0].label, "three");
        assert_eq!(recent[1].label, "two");
    }

    #[test]
    fn clears_trace_history_without_resetting_record_ids() {
        let mut store = TraceStore::new(10);

        store.begin("one");
        store.clear();
        let next = store.begin("two");

        assert_eq!(store.summary().total, 1);
        assert_eq!(next, 2);
        assert_eq!(store.recent()[0].label, "two");
    }
}
