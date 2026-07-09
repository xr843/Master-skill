use std::collections::{BTreeMap, VecDeque};
use std::time::Duration;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
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

#[derive(Clone, Debug, PartialEq, Eq)]
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

#[derive(Clone, Debug, PartialEq, Eq)]
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

#[derive(Clone, Debug)]
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
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use super::{FailureKind, TraceAction, TraceStatus, TraceStore};

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
