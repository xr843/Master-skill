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
        let id = self.next_id;
        self.next_id += 1;
        self.records.push_back(TraceRecord {
            id,
            label: label.into(),
            status: TraceStatus::Running,
            summary: "Started.".to_string(),
            duration_ms: None,
        });
        self.enforce_capacity();
        id
    }

    pub fn finish_success(&mut self, id: u64, summary: impl Into<String>, duration: Duration) {
        self.finish(id, TraceStatus::Succeeded, summary, duration);
    }

    pub fn finish_error(&mut self, id: u64, summary: impl Into<String>, duration: Duration) {
        self.finish(id, TraceStatus::Failed, summary, duration);
    }

    pub fn recent(&self) -> Vec<TraceRecord> {
        self.records.iter().rev().cloned().collect()
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
        duration: Duration,
    ) {
        if let Some(record) = self.records.iter_mut().find(|record| record.id == id) {
            record.status = status;
            record.summary = summary.into();
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
}
