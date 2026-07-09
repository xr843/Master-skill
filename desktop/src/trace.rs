use std::collections::VecDeque;
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
pub struct TraceRecord {
    pub id: u64,
    pub label: String,
    pub status: TraceStatus,
    pub summary: String,
    pub detail: String,
    pub command: Option<String>,
    pub duration_ms: Option<u128>,
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
        let id = self.next_id;
        self.next_id += 1;
        self.records.push_back(TraceRecord {
            id,
            label: label.into(),
            status: TraceStatus::Running,
            summary: "Started.".to_string(),
            detail: detail.into(),
            command: command.map(Into::into),
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

    use super::{TraceStatus, TraceStore};

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
