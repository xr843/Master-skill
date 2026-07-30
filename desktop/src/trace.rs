use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Duration;

use anyhow::{anyhow, Context, Result};
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

    fn is_evaluation(&self) -> bool {
        matches!(
            self,
            Self::FidelityDryRunAll | Self::FidelityDryRunSkill { .. } | Self::FullValidation
        )
    }

    fn is_install_operation(&self) -> bool {
        matches!(
            self,
            Self::InstallSkill { .. }
                | Self::UninstallSkill { .. }
                | Self::InstallAll
                | Self::UpdateAll
        )
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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TraceListFilter {
    All,
    Running,
    Succeeded,
    Failed,
    Evaluation,
    Install,
}

impl TraceListFilter {
    pub fn label(self) -> &'static str {
        match self {
            Self::All => "All",
            Self::Running => "Running",
            Self::Succeeded => "Succeeded",
            Self::Failed => "Failed",
            Self::Evaluation => "Evaluation",
            Self::Install => "Install",
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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvaluationMode {
    DryRun,
    Graded,
}

impl EvaluationMode {
    pub fn is_dry_run(self) -> bool {
        self == Self::DryRun
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::DryRun => "dry-run",
            Self::Graded => "graded",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EvaluationSuiteOutcome {
    Completed,
    Error(String),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvaluationEvidenceErrorKind {
    Execution,
    MalformedPayload,
    UnsupportedVersion,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationEvidenceError {
    pub trace_id: u64,
    pub slug: Option<String>,
    pub kind: EvaluationEvidenceErrorKind,
    pub message: String,
}

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
enum EvaluationEvidenceScope {
    All,
    Skill(String),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationRunResult {
    pub slug: String,
    pub passed_count: usize,
    pub total_count: usize,
    pub mode: EvaluationMode,
    pub trace_id: u64,
}

impl EvaluationRunResult {
    pub fn label(&self) -> String {
        let mode = if self.mode.is_dry_run() {
            "N/A"
        } else {
            "graded"
        };
        format!("{}/{} {mode}", self.passed_count, self.total_count)
    }

    pub fn is_dry_run(&self) -> bool {
        self.mode.is_dry_run()
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationRunHistoryItem {
    pub trace_id: u64,
    pub scope: String,
    pub status: TraceStatus,
    pub passed_count: usize,
    pub total_count: usize,
    pub failed_count: usize,
    pub mode: EvaluationMode,
    pub duration_ms: Option<u128>,
    pub action: Option<TraceAction>,
    pub trend: EvaluationRunTrend,
}

impl EvaluationRunHistoryItem {
    pub fn result_label(&self) -> String {
        let mode = if self.mode.is_dry_run() {
            "N/A"
        } else {
            "graded"
        };
        format!("{}/{} {mode}", self.passed_count, self.total_count)
    }

    pub fn is_dry_run(&self) -> bool {
        self.mode.is_dry_run()
    }

    pub fn pass_rate_percent(&self) -> usize {
        self.pass_rate_basis() / 100
    }

    fn pass_rate_basis(&self) -> usize {
        if self.total_count == 0 {
            return 0;
        }
        let basis = (self.passed_count as u128 * 10_000) / self.total_count as u128;
        basis.min(usize::MAX as u128) as usize
    }

    pub fn matches_filter(&self, filter: EvaluationRunHistoryFilter) -> bool {
        match filter {
            EvaluationRunHistoryFilter::All => true,
            EvaluationRunHistoryFilter::Regressed => self.trend == EvaluationRunTrend::Regressed,
            EvaluationRunHistoryFilter::Improved => self.trend == EvaluationRunTrend::Improved,
            EvaluationRunHistoryFilter::Stable => self.trend == EvaluationRunTrend::Stable,
            EvaluationRunHistoryFilter::New => self.trend == EvaluationRunTrend::New,
            EvaluationRunHistoryFilter::Failed => {
                self.status == TraceStatus::Failed || self.failed_count > 0
            }
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvaluationRunTrend {
    New,
    Improved,
    Stable,
    Regressed,
}

impl EvaluationRunTrend {
    pub fn label(self) -> &'static str {
        match self {
            Self::New => "new",
            Self::Improved => "improved",
            Self::Stable => "stable",
            Self::Regressed => "regressed",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvaluationRunHistoryFilter {
    All,
    Regressed,
    Improved,
    Stable,
    New,
    Failed,
}

impl EvaluationRunHistoryFilter {
    pub fn label(self) -> &'static str {
        match self {
            Self::All => "All",
            Self::Regressed => "Regressed",
            Self::Improved => "Improved",
            Self::Stable => "Stable",
            Self::New => "New",
            Self::Failed => "Failed",
        }
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct EvaluationTrendSummary {
    pub total_runs: usize,
    pub improved_count: usize,
    pub regressed_count: usize,
    pub stable_count: usize,
    pub new_count: usize,
    pub latest_regression_scope: Option<String>,
}

impl EvaluationTrendSummary {
    pub fn health_label(&self) -> &'static str {
        if self.regressed_count > 0 {
            "review"
        } else if self.total_runs == 0 {
            "none"
        } else {
            "clear"
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationRegressionItem {
    pub scope: String,
    pub current_trace_id: u64,
    pub previous_trace_id: u64,
    pub current_failed_count: usize,
    pub previous_failed_count: usize,
    pub failed_delta: isize,
    pub current_pass_rate: usize,
    pub previous_pass_rate: usize,
    pub pass_rate_delta_points: isize,
    pub action: Option<TraceAction>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EvaluationCaseStatus {
    Pass,
    Fail,
    DryRun,
    ApiError,
    Unknown(String),
}

impl EvaluationCaseStatus {
    fn from_wire(value: &str) -> Self {
        match value {
            value if value.eq_ignore_ascii_case("PASS") => Self::Pass,
            value if value.eq_ignore_ascii_case("FAIL") => Self::Fail,
            value if value.eq_ignore_ascii_case("dry_run") => Self::DryRun,
            value if value.eq_ignore_ascii_case("api_error") => Self::ApiError,
            value => Self::Unknown(value.to_string()),
        }
    }

    pub fn label(&self) -> &str {
        match self {
            Self::Pass => "PASS",
            Self::Fail => "FAIL",
            Self::DryRun => "dry_run",
            Self::ApiError => "api_error",
            Self::Unknown(value) => value,
        }
    }

    fn is_failure(&self) -> bool {
        matches!(self, Self::Fail | Self::ApiError)
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationCaseResult {
    pub slug: String,
    pub case_index: usize,
    pub question: String,
    pub difficulty: Option<String>,
    pub status: EvaluationCaseStatus,
    pub missing_cites: Vec<String>,
    pub missing_mentions: Vec<String>,
    pub forbidden_found: Vec<String>,
    pub boundary_violations: Vec<String>,
    pub fabricated_cites: Vec<String>,
    pub trace_id: u64,
}

impl EvaluationCaseResult {
    pub fn failure_summary(&self) -> String {
        let mut parts = Vec::new();
        push_detail_part(&mut parts, "missing cites", &self.missing_cites);
        push_detail_part(&mut parts, "missing mentions", &self.missing_mentions);
        push_detail_part(&mut parts, "forbidden", &self.forbidden_found);
        push_detail_part(&mut parts, "boundary", &self.boundary_violations);
        push_detail_part(&mut parts, "fabricated cites", &self.fabricated_cites);

        if parts.is_empty() {
            match &self.status {
                EvaluationCaseStatus::Pass => "pass".to_string(),
                EvaluationCaseStatus::DryRun => "dry-run only".to_string(),
                value => value.label().to_string(),
            }
        } else {
            parts.join("; ")
        }
    }

    fn has_failure_evidence(&self) -> bool {
        !self.missing_cites.is_empty()
            || !self.missing_mentions.is_empty()
            || !self.forbidden_found.is_empty()
            || !self.boundary_violations.is_empty()
            || !self.fabricated_cites.is_empty()
    }

    fn failure_priority(&self) -> EvaluationFailurePriority {
        if !self.fabricated_cites.is_empty()
            || !self.boundary_violations.is_empty()
            || !self.forbidden_found.is_empty()
        {
            EvaluationFailurePriority::Critical
        } else if !self.missing_cites.is_empty() || !self.missing_mentions.is_empty() {
            EvaluationFailurePriority::High
        } else {
            EvaluationFailurePriority::Medium
        }
    }
}

fn push_detail_part(parts: &mut Vec<String>, label: &str, values: &[String]) {
    if !values.is_empty() {
        parts.push(format!("{label}: {}", values.join(", ")));
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

    pub fn matches_filter(&self, filter: TraceListFilter) -> bool {
        match filter {
            TraceListFilter::All => true,
            TraceListFilter::Running => self.status == TraceStatus::Running,
            TraceListFilter::Succeeded => self.status == TraceStatus::Succeeded,
            TraceListFilter::Failed => self.status == TraceStatus::Failed,
            TraceListFilter::Evaluation => {
                self.action.as_ref().is_some_and(TraceAction::is_evaluation)
            }
            TraceListFilter::Install => self
                .action
                .as_ref()
                .is_some_and(TraceAction::is_install_operation),
        }
    }

    pub fn matches_query(&self, query: &str) -> bool {
        let query = query.trim().to_ascii_lowercase();
        if query.is_empty() {
            return true;
        }

        self.label.to_ascii_lowercase().contains(&query)
            || self.summary.to_ascii_lowercase().contains(&query)
            || self.detail.to_ascii_lowercase().contains(&query)
            || self
                .command
                .as_ref()
                .is_some_and(|command| command.to_ascii_lowercase().contains(&query))
            || self
                .related_skill_slug()
                .is_some_and(|slug| slug.to_ascii_lowercase().contains(&query))
    }

    pub fn evaluation_results(&self) -> Vec<EvaluationRunResult> {
        self.parsed_evaluation_evidence().runs
    }

    pub fn evaluation_case_results(&self) -> Vec<EvaluationCaseResult> {
        self.parsed_evaluation_evidence().cases
    }

    pub fn evaluation_errors(&self) -> Vec<EvaluationEvidenceError> {
        self.parsed_evaluation_evidence().errors
    }

    fn parsed_evaluation_evidence(&self) -> ParsedEvaluationEvidence {
        if !matches!(
            self.action,
            Some(TraceAction::FidelityDryRunAll | TraceAction::FidelityDryRunSkill { .. })
        ) || self.status == TraceStatus::Running
        {
            return ParsedEvaluationEvidence::default();
        }

        parse_evaluation_evidence(self)
    }

    fn evaluation_run_history_item(&self) -> Option<EvaluationRunHistoryItem> {
        if !matches!(
            self.action,
            Some(TraceAction::FidelityDryRunAll | TraceAction::FidelityDryRunSkill { .. })
        ) {
            return None;
        }

        let cases = self.evaluation_case_results();
        if !cases.is_empty() {
            let passed_count = cases
                .iter()
                .filter(|case| case.status == EvaluationCaseStatus::Pass)
                .count();
            let failed_count = cases
                .iter()
                .filter(|case| case.status.is_failure() || case.has_failure_evidence())
                .count();
            let mode = if cases
                .iter()
                .all(|case| case.status == EvaluationCaseStatus::DryRun)
            {
                EvaluationMode::DryRun
            } else {
                EvaluationMode::Graded
            };
            return Some(EvaluationRunHistoryItem {
                trace_id: self.id,
                scope: self.evaluation_scope_label(),
                status: self.status,
                passed_count,
                total_count: cases.len(),
                failed_count,
                mode,
                duration_ms: self.duration_ms,
                action: self.action.clone(),
                trend: EvaluationRunTrend::New,
            });
        }

        let results = self.evaluation_results();
        if results.is_empty() {
            return None;
        }

        let passed_count: usize = results.iter().map(|result| result.passed_count).sum();
        let total_count: usize = results.iter().map(|result| result.total_count).sum();
        let mode = if results.iter().all(EvaluationRunResult::is_dry_run) {
            EvaluationMode::DryRun
        } else {
            EvaluationMode::Graded
        };
        let failed_count = if mode.is_dry_run() {
            0
        } else {
            total_count.saturating_sub(passed_count)
        };

        Some(EvaluationRunHistoryItem {
            trace_id: self.id,
            scope: self.evaluation_scope_label(),
            status: self.status,
            passed_count,
            total_count,
            failed_count,
            mode,
            duration_ms: self.duration_ms,
            action: self.action.clone(),
            trend: EvaluationRunTrend::New,
        })
    }

    fn evaluation_scope_label(&self) -> String {
        match &self.action {
            Some(TraceAction::FidelityDryRunSkill { slug }) => format!("master-{slug}"),
            Some(TraceAction::FidelityDryRunAll) => "all".to_string(),
            _ => "evaluation".to_string(),
        }
    }
}

#[derive(Clone, Debug, Deserialize)]
struct EvaluationCaseWire {
    index: usize,
    #[serde(default)]
    question: Option<String>,
    #[serde(default)]
    difficulty: Option<String>,
    status: String,
    #[serde(default)]
    missing_cites: Vec<String>,
    #[serde(default)]
    missing_mentions: Vec<String>,
    #[serde(default)]
    forbidden_found: Vec<String>,
    #[serde(default)]
    boundary_violations: Vec<String>,
    #[serde(default)]
    fabricated_cites: Vec<String>,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum EvaluationModeWire {
    DryRun,
    Graded,
}

impl From<EvaluationModeWire> for EvaluationMode {
    fn from(value: EvaluationModeWire) -> Self {
        match value {
            EvaluationModeWire::DryRun => Self::DryRun,
            EvaluationModeWire::Graded => Self::Graded,
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
enum EvaluationOutcomeWire {
    Completed,
    Error,
}

#[derive(Debug, Deserialize)]
struct EvaluationSuiteV1 {
    schema_version: u64,
    master: String,
    mode: EvaluationModeWire,
    outcome: EvaluationOutcomeWire,
    total: usize,
    results: Vec<EvaluationCaseWire>,
    #[serde(default)]
    passed: Option<usize>,
    #[serde(default)]
    failed: Option<usize>,
    #[serde(default)]
    error: Option<String>,
}

#[derive(Debug, Deserialize)]
struct LegacyEvaluationSuite {
    master: String,
    #[serde(default)]
    total: Option<usize>,
    #[serde(default)]
    results: Vec<EvaluationCaseWire>,
    #[serde(default)]
    passed: Option<usize>,
    #[serde(default)]
    error: Option<String>,
}

#[derive(Debug)]
struct CompletedEvaluationSuite {
    run: EvaluationRunResult,
    cases: Vec<EvaluationCaseResult>,
}

#[derive(Default)]
struct ParsedEvaluationEvidence {
    runs: Vec<EvaluationRunResult>,
    cases: Vec<EvaluationCaseResult>,
    errors: Vec<EvaluationEvidenceError>,
}

impl ParsedEvaluationEvidence {
    fn push_completed(&mut self, suite: CompletedEvaluationSuite) {
        self.runs.push(suite.run);
        self.cases.extend(suite.cases);
    }
}

fn parse_evaluation_evidence(record: &TraceRecord) -> ParsedEvaluationEvidence {
    let fallback_slug = record.related_skill_slug();
    match serde_json::from_str::<serde_json::Value>(&record.detail) {
        Ok(value) => parse_evaluation_json_value(record.id, value, fallback_slug),
        Err(json_error) => {
            let runs = parse_evaluation_results_text(record.id, &record.detail);
            if !runs.is_empty() {
                return ParsedEvaluationEvidence {
                    runs,
                    ..ParsedEvaluationEvidence::default()
                };
            }

            let looks_like_json =
                matches!(record.detail.trim_start().chars().next(), Some('[' | '{'));
            let kind = if record.status == TraceStatus::Failed && !looks_like_json {
                EvaluationEvidenceErrorKind::Execution
            } else {
                EvaluationEvidenceErrorKind::MalformedPayload
            };
            let message = if kind == EvaluationEvidenceErrorKind::Execution {
                nonempty_evaluation_error_message(&record.detail, &record.summary)
            } else {
                format!("invalid fidelity JSON: {json_error}")
            };
            ParsedEvaluationEvidence {
                errors: vec![evaluation_evidence_error(
                    record.id,
                    fallback_slug,
                    kind,
                    message,
                )],
                ..ParsedEvaluationEvidence::default()
            }
        }
    }
}

fn parse_evaluation_json_value(
    trace_id: u64,
    value: serde_json::Value,
    fallback_slug: Option<&str>,
) -> ParsedEvaluationEvidence {
    let Some(suites) = value.as_array() else {
        return ParsedEvaluationEvidence {
            errors: vec![evaluation_evidence_error(
                trace_id,
                fallback_slug,
                EvaluationEvidenceErrorKind::MalformedPayload,
                "invalid fidelity suite: expected a top-level JSON array",
            )],
            ..ParsedEvaluationEvidence::default()
        };
    };

    if suites.is_empty() {
        return ParsedEvaluationEvidence {
            errors: vec![evaluation_evidence_error(
                trace_id,
                fallback_slug,
                EvaluationEvidenceErrorKind::MalformedPayload,
                "invalid fidelity suite: the suite array is empty",
            )],
            ..ParsedEvaluationEvidence::default()
        };
    }

    let mut parsed = ParsedEvaluationEvidence::default();
    for (suite_index, suite) in suites.iter().enumerate() {
        let result = if suite.get("schema_version").is_some() {
            parse_evaluation_suite_v1(trace_id, suite.clone(), fallback_slug)
        } else {
            parse_legacy_evaluation_suite(trace_id, suite.clone(), fallback_slug)
        };
        match result {
            Ok(completed) => parsed.push_completed(completed),
            Err(mut error) => {
                error.message = format!("suite {}: {}", suite_index + 1, error.message);
                parsed.errors.push(error);
            }
        }
    }
    parsed
}

fn parse_evaluation_suite_v1(
    trace_id: u64,
    value: serde_json::Value,
    fallback_slug: Option<&str>,
) -> Result<CompletedEvaluationSuite, EvaluationEvidenceError> {
    let slug = evaluation_slug_from_value(&value, fallback_slug);
    let version = value
        .get("schema_version")
        .and_then(serde_json::Value::as_u64)
        .ok_or_else(|| {
            evaluation_evidence_error(
                trace_id,
                slug.as_deref(),
                EvaluationEvidenceErrorKind::MalformedPayload,
                "invalid fidelity v1 suite: schema_version must be an integer",
            )
        })?;
    if version != 1 {
        return Err(evaluation_evidence_error(
            trace_id,
            slug.as_deref(),
            EvaluationEvidenceErrorKind::UnsupportedVersion,
            format!("unsupported fidelity schema version {version}"),
        ));
    }

    let suite: EvaluationSuiteV1 = serde_json::from_value(value).map_err(|error| {
        evaluation_evidence_error(
            trace_id,
            slug.as_deref(),
            EvaluationEvidenceErrorKind::MalformedPayload,
            format!("invalid fidelity v1 suite: {error}"),
        )
    })?;
    if suite.schema_version != version {
        return Err(evaluation_evidence_error(
            trace_id,
            slug.as_deref(),
            EvaluationEvidenceErrorKind::MalformedPayload,
            "invalid fidelity v1 suite: schema_version changed during parsing",
        ));
    }
    let slug = normalized_master_slug(&suite.master).ok_or_else(|| {
        evaluation_evidence_error(
            trace_id,
            fallback_slug,
            EvaluationEvidenceErrorKind::MalformedPayload,
            "invalid fidelity v1 suite: master must start with master-",
        )
    })?;
    validate_evaluation_scope(trace_id, &slug, fallback_slug)?;
    let outcome = match suite.outcome {
        EvaluationOutcomeWire::Completed => EvaluationSuiteOutcome::Completed,
        EvaluationOutcomeWire::Error => {
            EvaluationSuiteOutcome::Error(suite.error.clone().unwrap_or_default())
        }
    };
    if let EvaluationSuiteOutcome::Error(message) = outcome {
        if suite.total != 0 || !suite.results.is_empty() || message.trim().is_empty() {
            return Err(evaluation_evidence_error(
                trace_id,
                Some(&slug),
                EvaluationEvidenceErrorKind::MalformedPayload,
                "invalid fidelity error suite: expected total 0, empty results, and a non-empty error",
            ));
        }
        return Err(evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::Execution,
            message.trim(),
        ));
    }

    if suite.error.is_some() {
        return Err(evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::MalformedPayload,
            "invalid completed fidelity suite: error must be omitted",
        ));
    }
    let mode = EvaluationMode::from(suite.mode);
    let statuses = evaluation_case_statuses(&suite.results).map_err(|message| {
        evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::MalformedPayload,
            message,
        )
    })?;
    if suite.total != suite.results.len() {
        return Err(evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::MalformedPayload,
            format!(
                "invalid fidelity suite: total {} does not match {} result(s)",
                suite.total,
                suite.results.len()
            ),
        ));
    }

    let passed_count = match mode {
        EvaluationMode::DryRun => {
            if suite.passed.is_some()
                || suite.failed.is_some()
                || statuses
                    .iter()
                    .any(|status| !matches!(status, EvaluationCaseStatus::DryRun))
            {
                return Err(evaluation_evidence_error(
                    trace_id,
                    Some(&slug),
                    EvaluationEvidenceErrorKind::MalformedPayload,
                    "invalid dry-run suite: graded counts must be omitted and every status must be dry_run",
                ));
            }
            0
        }
        EvaluationMode::Graded => {
            let passed = suite.passed.ok_or_else(|| {
                evaluation_evidence_error(
                    trace_id,
                    Some(&slug),
                    EvaluationEvidenceErrorKind::MalformedPayload,
                    "invalid graded suite: passed is required",
                )
            })?;
            let failed = suite.failed.ok_or_else(|| {
                evaluation_evidence_error(
                    trace_id,
                    Some(&slug),
                    EvaluationEvidenceErrorKind::MalformedPayload,
                    "invalid graded suite: failed is required",
                )
            })?;
            if passed.saturating_add(failed) != suite.total
                || statuses
                    .iter()
                    .any(|status| matches!(status, EvaluationCaseStatus::DryRun))
            {
                return Err(evaluation_evidence_error(
                    trace_id,
                    Some(&slug),
                    EvaluationEvidenceErrorKind::MalformedPayload,
                    "invalid graded suite: counts or case modes are inconsistent",
                ));
            }
            let parsed_passed = statuses
                .iter()
                .filter(|status| matches!(status, EvaluationCaseStatus::Pass))
                .count();
            let parsed_failed = statuses
                .iter()
                .filter(|status| {
                    matches!(
                        status,
                        EvaluationCaseStatus::Fail | EvaluationCaseStatus::ApiError
                    )
                })
                .count();
            if parsed_passed != passed || parsed_failed != failed {
                return Err(evaluation_evidence_error(
                    trace_id,
                    Some(&slug),
                    EvaluationEvidenceErrorKind::MalformedPayload,
                    "invalid graded suite: passed/failed counts do not match case statuses",
                ));
            }
            passed
        }
    };

    Ok(completed_evaluation_suite(
        trace_id,
        slug,
        mode,
        passed_count,
        suite.total,
        suite.results,
        statuses,
    ))
}

fn parse_legacy_evaluation_suite(
    trace_id: u64,
    value: serde_json::Value,
    fallback_slug: Option<&str>,
) -> Result<CompletedEvaluationSuite, EvaluationEvidenceError> {
    let value_slug = evaluation_slug_from_value(&value, fallback_slug);
    if let Some(error) = value.get("error") {
        let message = error.as_str().map(str::trim).unwrap_or_default();
        if message.is_empty() {
            return Err(evaluation_evidence_error(
                trace_id,
                value_slug.as_deref(),
                EvaluationEvidenceErrorKind::MalformedPayload,
                "invalid legacy fidelity error suite: error must be a non-empty string",
            ));
        }
        return Err(evaluation_evidence_error(
            trace_id,
            value_slug.as_deref(),
            EvaluationEvidenceErrorKind::Execution,
            message,
        ));
    }

    let suite: LegacyEvaluationSuite = serde_json::from_value(value).map_err(|error| {
        evaluation_evidence_error(
            trace_id,
            value_slug.as_deref(),
            EvaluationEvidenceErrorKind::MalformedPayload,
            format!("invalid legacy fidelity suite: {error}"),
        )
    })?;
    if suite.error.is_some() {
        return Err(evaluation_evidence_error(
            trace_id,
            value_slug.as_deref(),
            EvaluationEvidenceErrorKind::MalformedPayload,
            "invalid legacy fidelity suite: error cannot accompany results",
        ));
    }
    let slug = normalized_master_slug(&suite.master).ok_or_else(|| {
        evaluation_evidence_error(
            trace_id,
            fallback_slug,
            EvaluationEvidenceErrorKind::MalformedPayload,
            "invalid legacy fidelity suite: master must start with master-",
        )
    })?;
    validate_evaluation_scope(trace_id, &slug, fallback_slug)?;
    let statuses = evaluation_case_statuses(&suite.results).map_err(|message| {
        evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::MalformedPayload,
            message,
        )
    })?;
    let mode = if suite.passed.is_some() {
        if statuses
            .iter()
            .any(|status| matches!(status, EvaluationCaseStatus::DryRun))
        {
            return Err(evaluation_evidence_error(
                trace_id,
                Some(&slug),
                EvaluationEvidenceErrorKind::MalformedPayload,
                "invalid legacy graded suite: dry_run status conflicts with passed",
            ));
        }
        EvaluationMode::Graded
    } else if !statuses.is_empty()
        && statuses
            .iter()
            .all(|status| matches!(status, EvaluationCaseStatus::DryRun))
    {
        EvaluationMode::DryRun
    } else {
        return Err(evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::MalformedPayload,
            "ambiguous legacy fidelity suite: expected passed or all dry_run statuses",
        ));
    };
    let total_count = suite.total.unwrap_or(suite.results.len());
    let passed_count = suite.passed.unwrap_or(0);
    if passed_count > total_count {
        return Err(evaluation_evidence_error(
            trace_id,
            Some(&slug),
            EvaluationEvidenceErrorKind::MalformedPayload,
            "invalid legacy fidelity suite: passed exceeds total",
        ));
    }

    Ok(completed_evaluation_suite(
        trace_id,
        slug,
        mode,
        passed_count,
        total_count,
        suite.results,
        statuses,
    ))
}

fn evaluation_case_statuses(
    cases: &[EvaluationCaseWire],
) -> Result<Vec<EvaluationCaseStatus>, String> {
    cases
        .iter()
        .map(|case| {
            if case.index.checked_add(1).is_none() {
                return Err(format!(
                    "invalid fidelity suite: case index {} cannot be displayed one-based",
                    case.index
                ));
            }
            match EvaluationCaseStatus::from_wire(&case.status) {
                EvaluationCaseStatus::Unknown(status) => Err(format!(
                    "invalid fidelity suite: unknown case status {status:?}"
                )),
                status => Ok(status),
            }
        })
        .collect()
}

fn completed_evaluation_suite(
    trace_id: u64,
    slug: String,
    mode: EvaluationMode,
    passed_count: usize,
    total_count: usize,
    cases: Vec<EvaluationCaseWire>,
    statuses: Vec<EvaluationCaseStatus>,
) -> CompletedEvaluationSuite {
    let cases = cases
        .into_iter()
        .zip(statuses)
        .map(|(case, status)| EvaluationCaseResult {
            slug: slug.clone(),
            case_index: case.index + 1,
            question: case.question.unwrap_or_else(|| "untitled case".to_string()),
            difficulty: case.difficulty,
            status,
            missing_cites: case.missing_cites,
            missing_mentions: case.missing_mentions,
            forbidden_found: case.forbidden_found,
            boundary_violations: case.boundary_violations,
            fabricated_cites: case.fabricated_cites,
            trace_id,
        })
        .collect();

    CompletedEvaluationSuite {
        run: EvaluationRunResult {
            slug,
            passed_count,
            total_count,
            mode,
            trace_id,
        },
        cases,
    }
}

fn normalized_master_slug(master: &str) -> Option<String> {
    let slug = master.strip_prefix("master-")?;
    (!slug.is_empty()).then(|| slug.to_string())
}

fn validate_evaluation_scope(
    trace_id: u64,
    actual_slug: &str,
    expected_slug: Option<&str>,
) -> Result<(), EvaluationEvidenceError> {
    if let Some(expected_slug) = expected_slug {
        if actual_slug != expected_slug {
            return Err(evaluation_evidence_error(
                trace_id,
                Some(expected_slug),
                EvaluationEvidenceErrorKind::MalformedPayload,
                format!(
                    "invalid fidelity suite scope: expected master-{expected_slug}, got master-{actual_slug}"
                ),
            ));
        }
    }
    Ok(())
}

fn evaluation_slug_from_value(
    value: &serde_json::Value,
    fallback_slug: Option<&str>,
) -> Option<String> {
    value
        .get("master")
        .and_then(serde_json::Value::as_str)
        .and_then(normalized_master_slug)
        .or_else(|| fallback_slug.map(str::to_string))
}

fn evaluation_evidence_error(
    trace_id: u64,
    slug: Option<&str>,
    kind: EvaluationEvidenceErrorKind,
    message: impl Into<String>,
) -> EvaluationEvidenceError {
    EvaluationEvidenceError {
        trace_id,
        slug: slug.map(str::to_string),
        kind,
        message: message.into(),
    }
}

fn nonempty_evaluation_error_message(detail: &str, summary: &str) -> String {
    let detail = detail.trim();
    if detail.is_empty() {
        summary.trim().to_string()
    } else {
        detail.to_string()
    }
}

fn parse_evaluation_results_text(trace_id: u64, detail: &str) -> Vec<EvaluationRunResult> {
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
                        mode: if rest.contains("(N/A)") {
                            EvaluationMode::DryRun
                        } else {
                            EvaluationMode::Graded
                        },
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

fn annotate_evaluation_run_trends(history: &mut [EvaluationRunHistoryItem]) {
    for index in 0..history.len() {
        if history[index].mode != EvaluationMode::Graded {
            history[index].trend = EvaluationRunTrend::New;
            continue;
        }
        let Some(previous) = history[index + 1..].iter().find(|candidate| {
            candidate.scope == history[index].scope && candidate.mode == EvaluationMode::Graded
        }) else {
            history[index].trend = EvaluationRunTrend::New;
            continue;
        };

        history[index].trend = compare_evaluation_runs(&history[index], previous);
    }
}

fn compare_evaluation_runs(
    current: &EvaluationRunHistoryItem,
    previous: &EvaluationRunHistoryItem,
) -> EvaluationRunTrend {
    if current.failed_count < previous.failed_count {
        EvaluationRunTrend::Improved
    } else if current.failed_count > previous.failed_count {
        EvaluationRunTrend::Regressed
    } else {
        match current.pass_rate_basis().cmp(&previous.pass_rate_basis()) {
            std::cmp::Ordering::Greater => EvaluationRunTrend::Improved,
            std::cmp::Ordering::Less => EvaluationRunTrend::Regressed,
            std::cmp::Ordering::Equal => EvaluationRunTrend::Stable,
        }
    }
}

fn signed_usize_delta(current: usize, previous: usize) -> isize {
    if current >= previous {
        current.saturating_sub(previous).min(isize::MAX as usize) as isize
    } else {
        -(previous.saturating_sub(current).min(isize::MAX as usize) as isize)
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

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TraceFailureItem {
    pub trace_id: u64,
    pub kind: FailureKind,
    pub label: String,
    pub summary: String,
    pub duration_ms: Option<u128>,
    pub action: Option<TraceAction>,
    pub related_skill_slug: Option<String>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct EvaluationRunCoverage {
    pub total_skill_count: usize,
    pub structural_run_skill_count: usize,
    pub graded_run_skill_count: usize,
    pub dry_run_skill_count: usize,
    pub current_error_count: usize,
}

impl EvaluationRunCoverage {
    pub fn structural_label(&self) -> String {
        format!(
            "{}/{}",
            self.structural_run_skill_count, self.total_skill_count
        )
    }

    pub fn graded_label(&self) -> String {
        format!("{}/{}", self.graded_run_skill_count, self.total_skill_count)
    }

    pub fn is_structurally_complete(&self) -> bool {
        self.total_skill_count > 0 && self.structural_run_skill_count >= self.total_skill_count
    }

    pub fn is_graded_complete(&self) -> bool {
        self.total_skill_count > 0 && self.graded_run_skill_count >= self.total_skill_count
    }
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct EvaluationFailureInsights {
    pub total_cases: usize,
    pub pass_cases: usize,
    pub dry_run_cases: usize,
    pub failed_cases: usize,
    pub failing_skill_count: usize,
    pub top_failure_skill_slug: Option<String>,
    pub top_failure_skill_count: usize,
    pub missing_cites_count: usize,
    pub missing_mentions_count: usize,
    pub forbidden_found_count: usize,
    pub boundary_violations_count: usize,
    pub fabricated_cites_count: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationFailureItem {
    pub slug: String,
    pub case_index: usize,
    pub question: String,
    pub status: String,
    pub priority: EvaluationFailurePriority,
    pub failure_summary: String,
    pub trace_id: u64,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum EvaluationFailurePriority {
    Medium,
    High,
    Critical,
}

impl EvaluationFailurePriority {
    pub fn label(self) -> &'static str {
        match self {
            Self::Medium => "medium",
            Self::High => "high",
            Self::Critical => "critical",
        }
    }
}

impl EvaluationFailureInsights {
    pub fn graded_cases(&self) -> usize {
        self.pass_cases + self.failed_cases
    }

    pub fn pass_rate_label(&self) -> String {
        let graded_cases = self.graded_cases();
        if graded_cases == 0 {
            return "N/A".to_string();
        }

        format!("{}%", self.pass_cases * 100 / graded_cases)
    }

    pub fn top_failure_label(&self) -> String {
        self.top_failure_skill_slug
            .as_ref()
            .map(|slug| format!("master-{slug} ({})", self.top_failure_skill_count))
            .unwrap_or_else(|| "none".to_string())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EvaluationDecisionPosture {
    Blocked,
    Attention,
    Unproven,
    Ready,
}

impl EvaluationDecisionPosture {
    pub fn label(self) -> &'static str {
        match self {
            Self::Blocked => "blocked",
            Self::Attention => "attention",
            Self::Unproven => "unproven",
            Self::Ready => "ready",
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationDecisionBrief {
    pub posture: EvaluationDecisionPosture,
    pub headline: String,
    pub primary_risk: String,
    pub evidence: String,
    pub recommendation: String,
    pub action: EvaluationDecisionAction,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EvaluationDecisionAction {
    RerunAll,
    RerunSkill { slug: String },
    OpenSkill { slug: String },
    RunFidelityBaseline,
    RunFullValidation,
}

impl EvaluationDecisionAction {
    pub fn label(&self) -> &'static str {
        match self {
            Self::RerunAll => "Rerun all",
            Self::RerunSkill { .. } => "Rerun skill",
            Self::OpenSkill { .. } => "Open skill",
            Self::RunFidelityBaseline => "Run baseline",
            Self::RunFullValidation => "Run validation",
        }
    }
}

impl EvaluationDecisionBrief {
    pub fn from_signals(
        coverage: &EvaluationRunCoverage,
        trend: &EvaluationTrendSummary,
        insights: &EvaluationFailureInsights,
    ) -> Self {
        if trend.regressed_count > 0 {
            let scope = trend
                .latest_regression_scope
                .clone()
                .unwrap_or_else(|| "recent scope".to_string());
            let action = decision_action_for_regressed_scope(&scope);
            return Self {
                posture: EvaluationDecisionPosture::Blocked,
                headline: "Regression detected".to_string(),
                primary_risk: format!("{scope} regressed"),
                evidence: format!(
                    "{} regression(s) across {} recent run(s)",
                    trend.regressed_count, trend.total_runs
                ),
                recommendation:
                    "Rerun the regressed scope and inspect failed cases before release.".to_string(),
                action,
            };
        }

        if coverage.current_error_count > 0 {
            return Self {
                posture: EvaluationDecisionPosture::Blocked,
                headline: "Evaluation evidence error".to_string(),
                primary_risk: format!(
                    "{} current evaluation error(s)",
                    coverage.current_error_count
                ),
                evidence:
                    "The newest attempt for at least one evaluation scope did not produce valid evidence."
                        .to_string(),
                recommendation:
                    "Rerun the affected evaluation scopes and inspect execution or payload errors before release."
                        .to_string(),
                action: EvaluationDecisionAction::RerunAll,
            };
        }

        if insights.failed_cases > 0 {
            let action = insights
                .top_failure_skill_slug
                .as_ref()
                .map(|slug| EvaluationDecisionAction::OpenSkill { slug: slug.clone() })
                .unwrap_or(EvaluationDecisionAction::RunFidelityBaseline);
            return Self {
                posture: EvaluationDecisionPosture::Attention,
                headline: "Failing fidelity cases".to_string(),
                primary_risk: insights.top_failure_label(),
                evidence: format!(
                    "{} failing case(s) across {} skill(s)",
                    insights.failed_cases, insights.failing_skill_count
                ),
                recommendation:
                    "Open the top failing skill, resolve evidence gaps, then rerun fidelity."
                        .to_string(),
                action,
            };
        }

        if !coverage.is_structurally_complete() {
            let missing_runs = coverage
                .total_skill_count
                .saturating_sub(coverage.structural_run_skill_count);
            return Self {
                posture: EvaluationDecisionPosture::Unproven,
                headline: "Evaluation coverage incomplete".to_string(),
                primary_risk: format!(
                    "{} skills have structural runs",
                    coverage.structural_label()
                ),
                evidence: format!("{missing_runs} skill(s) without a current run"),
                recommendation: "Run fidelity dry-run to establish structural baseline coverage."
                    .to_string(),
                action: EvaluationDecisionAction::RunFidelityBaseline,
            };
        }

        if !coverage.is_graded_complete() {
            let missing_runs = coverage
                .total_skill_count
                .saturating_sub(coverage.graded_run_skill_count);
            return Self {
                posture: EvaluationDecisionPosture::Unproven,
                headline: "Graded evidence incomplete".to_string(),
                primary_risk: format!("{} skills have graded results", coverage.graded_label()),
                evidence: format!(
                    "Structural baseline complete; {missing_runs} skill(s) lack graded evidence"
                ),
                recommendation: "Attach complete graded fidelity evidence before release approval."
                    .to_string(),
                action: EvaluationDecisionAction::RunFullValidation,
            };
        }

        Self {
            posture: EvaluationDecisionPosture::Ready,
            headline: "Graded evaluation clear".to_string(),
            primary_risk: "No current regressions or failing cases".to_string(),
            evidence: format!(
                "{} skills graded, {} recent run(s)",
                coverage.graded_run_skill_count, trend.total_runs
            ),
            recommendation: "Proceed with release review and keep monitoring new runs.".to_string(),
            action: EvaluationDecisionAction::RunFullValidation,
        }
    }

    pub fn status_label(&self) -> &'static str {
        self.posture.label()
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationEvidenceReport {
    pub markdown: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationRemediationPlan {
    pub markdown: String,
    pub item_count: usize,
    pub items: Vec<String>,
}

impl EvaluationEvidenceReport {
    pub fn from_signals(
        brief: &EvaluationDecisionBrief,
        coverage: &EvaluationRunCoverage,
        trend: &EvaluationTrendSummary,
        insights: &EvaluationFailureInsights,
        regressions: &[EvaluationRegressionItem],
        failure_queue: &[EvaluationFailureItem],
        run_history: &[EvaluationRunHistoryItem],
    ) -> Self {
        let mut markdown = String::new();
        markdown.push_str("# Master-skill Evaluation Evidence Report\n\n");
        markdown.push_str("## Quality Gate\n");
        markdown.push_str(&format!("- Status: {}\n", brief.status_label()));
        markdown.push_str(&format!("- Headline: {}\n", brief.headline));
        markdown.push_str(&format!("- Primary risk: {}\n", brief.primary_risk));
        markdown.push_str(&format!("- Evidence: {}\n", brief.evidence));
        markdown.push_str(&format!("- Next action: {}\n\n", brief.recommendation));

        markdown.push_str("## Coverage And Trend\n");
        markdown.push_str(&format!(
            "- Structural coverage: {} skills\n",
            coverage.structural_label()
        ));
        markdown.push_str(&format!(
            "- Graded coverage: {} skills\n",
            coverage.graded_label()
        ));
        markdown.push_str(&format!(
            "- Latest structural mode: {} dry-run skill(s)\n",
            coverage.dry_run_skill_count
        ));
        markdown.push_str(&format!(
            "- Current evaluation errors: {}\n",
            coverage.current_error_count
        ));
        markdown.push_str(&format!(
            "- Trend: {} regressed / {} improved / {} stable / {} new\n\n",
            trend.regressed_count, trend.improved_count, trend.stable_count, trend.new_count
        ));

        markdown.push_str("## Failure Evidence\n");
        markdown.push_str(&format!(
            "- Failure evidence: {} failed case(s), {} failing skill(s), pass rate {}\n",
            insights.failed_cases,
            insights.failing_skill_count,
            insights.pass_rate_label()
        ));
        markdown.push_str(&format!(
            "- Evidence gaps: {} missing cite(s), {} missing mention(s), {} forbidden match(es), {} boundary violation(s), {} fabricated cite(s)\n\n",
            insights.missing_cites_count,
            insights.missing_mentions_count,
            insights.forbidden_found_count,
            insights.boundary_violations_count,
            insights.fabricated_cites_count
        ));

        markdown.push_str("## Regression Queue\n");
        if regressions.is_empty() {
            markdown.push_str("- none\n\n");
        } else {
            for item in regressions {
                markdown.push_str(&format!(
                    "- {}: trace #{} vs #{}, failed {:+}, pass rate {:+} pts\n",
                    item.scope,
                    item.current_trace_id,
                    item.previous_trace_id,
                    item.failed_delta,
                    item.pass_rate_delta_points
                ));
            }
            markdown.push('\n');
        }

        markdown.push_str("## Failure Queue\n");
        if failure_queue.is_empty() {
            markdown.push_str("- none\n\n");
        } else {
            for item in failure_queue {
                markdown.push_str(&format!(
                    "- {} master-{} case #{}: {}\n",
                    item.priority.label(),
                    item.slug,
                    item.case_index,
                    item.failure_summary
                ));
            }
            markdown.push('\n');
        }

        markdown.push_str("## Recent Evaluation Runs\n");
        if run_history.is_empty() {
            markdown.push_str("- none\n");
        } else {
            for item in run_history {
                markdown.push_str(&format!(
                    "- #{} {}: {}, {}, {} failed, {}\n",
                    item.trace_id,
                    item.scope,
                    item.status.label(),
                    item.result_label(),
                    item.failed_count,
                    item.trend.label()
                ));
            }
        }

        Self { markdown }
    }
}

impl EvaluationRemediationPlan {
    pub fn from_signals(
        brief: &EvaluationDecisionBrief,
        regressions: &[EvaluationRegressionItem],
        failure_queue: &[EvaluationFailureItem],
        run_history: &[EvaluationRunHistoryItem],
    ) -> Self {
        let mut markdown = String::new();
        let mut item_count = 0;
        let mut items = Vec::new();

        markdown.push_str("# Master-skill Evaluation Remediation Plan\n\n");
        markdown.push_str("## Gate Decision\n");
        markdown.push_str(&format!("- Status: {}\n", brief.status_label()));
        markdown.push_str(&format!("- Headline: {}\n", brief.headline));
        markdown.push_str(&format!("- Primary risk: {}\n", brief.primary_risk));
        markdown.push_str(&format!("- Evidence: {}\n", brief.evidence));
        markdown.push_str(&format!(
            "- Recommended next action: {}\n",
            brief.recommendation
        ));
        if let Some(latest) = run_history.first() {
            markdown.push_str(&format!(
                "- Latest run: {} from latest trace #{}\n",
                latest.scope, latest.trace_id
            ));
        }
        markdown.push('\n');

        markdown.push_str("## Action Items\n");
        if regressions.is_empty() && failure_queue.is_empty() {
            append_remediation_item(
                &mut markdown,
                &mut item_count,
                &mut items,
                &default_remediation_action(brief),
            );
        } else {
            for item in regressions {
                append_remediation_item(
                    &mut markdown,
                    &mut item_count,
                    &mut items,
                    &format!(
                        "Rerun {} and compare trace #{} against #{} (failed {:+}, pass rate {:+} pts)",
                        item.scope,
                        item.current_trace_id,
                        item.previous_trace_id,
                        item.failed_delta,
                        item.pass_rate_delta_points
                    ),
                );
            }
            for item in failure_queue.iter().take(10) {
                append_remediation_item(
                    &mut markdown,
                    &mut item_count,
                    &mut items,
                    &format!(
                        "Fix master-{} case #{} ({}): {}",
                        item.slug,
                        item.case_index,
                        item.priority.label(),
                        item.failure_summary
                    ),
                );
            }
        }

        markdown.push_str("\n## Verification\n");
        append_remediation_item(
            &mut markdown,
            &mut item_count,
            &mut items,
            "Rerun affected fidelity scopes",
        );
        append_remediation_item(&mut markdown, &mut item_count, &mut items, "Run `npm test`");
        markdown.push_str("- Attach the copied evidence report to the PR or release note.\n");

        Self {
            markdown,
            item_count,
            items,
        }
    }
}

fn append_remediation_item(
    markdown: &mut String,
    item_count: &mut usize,
    items: &mut Vec<String>,
    text: &str,
) {
    *item_count += 1;
    items.push(text.to_string());
    markdown.push_str(&format!("- [ ] {text}\n"));
}

fn default_remediation_action(brief: &EvaluationDecisionBrief) -> String {
    match brief.posture {
        EvaluationDecisionPosture::Ready => {
            "Run full validation before release approval".to_string()
        }
        EvaluationDecisionPosture::Unproven
        | EvaluationDecisionPosture::Attention
        | EvaluationDecisionPosture::Blocked => brief.recommendation.clone(),
    }
}

fn decision_action_for_regressed_scope(scope: &str) -> EvaluationDecisionAction {
    if scope == "all" {
        EvaluationDecisionAction::RerunAll
    } else if let Some(slug) = scope.strip_prefix("master-") {
        EvaluationDecisionAction::RerunSkill {
            slug: slug.to_string(),
        }
    } else {
        EvaluationDecisionAction::RunFidelityBaseline
    }
}

const TRACE_STORE_SCHEMA_VERSION: u64 = 1;

#[derive(Debug, Deserialize)]
struct TraceStoreFileV1 {
    schema_version: u64,
    next_id: u64,
    records: VecDeque<TraceRecord>,
}

#[derive(Debug, Deserialize)]
struct LegacyTraceStoreFile {
    capacity: usize,
    next_id: u64,
    records: VecDeque<TraceRecord>,
}

#[derive(Serialize)]
struct TraceStoreFileV1Ref<'a> {
    schema_version: u64,
    next_id: u64,
    records: &'a VecDeque<TraceRecord>,
}

#[derive(Debug)]
pub struct TraceStoreLease {
    trace_path: PathBuf,
    _lock_file: fs::File,
}

impl TraceStoreLease {
    pub fn try_acquire(trace_path: &Path) -> Result<Option<Self>> {
        let parent = trace_store_parent(trace_path);
        fs::create_dir_all(parent).with_context(|| {
            format!(
                "failed to create trace store directory {}",
                parent.display()
            )
        })?;

        let mut lock_name = trace_path.as_os_str().to_os_string();
        lock_name.push(".lock");
        let lock_path = PathBuf::from(lock_name);
        let lock_file = fs::OpenOptions::new()
            .create(true)
            .truncate(false)
            .read(true)
            .write(true)
            .open(&lock_path)
            .with_context(|| format!("failed to open trace lock {}", lock_path.display()))?;

        match fs4::FileExt::try_lock(&lock_file) {
            Ok(()) => Ok(Some(Self {
                trace_path: trace_path.to_path_buf(),
                _lock_file: lock_file,
            })),
            Err(fs4::TryLockError::WouldBlock) => Ok(None),
            Err(fs4::TryLockError::Error(error)) => Err(error)
                .with_context(|| format!("failed to lock trace store {}", trace_path.display())),
        }
    }

    pub fn path(&self) -> &Path {
        &self.trace_path
    }

    pub fn load(&self, capacity: usize) -> Result<TraceStore> {
        TraceStore::load_from_path(&self.trace_path, capacity)
    }

    pub fn save(&self, store: &TraceStore) -> Result<()> {
        store.save_to_path(&self.trace_path)
    }
}

fn trace_store_parent(path: &Path) -> &Path {
    path.parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."))
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

    pub fn load_from_path(path: &Path, capacity: usize) -> Result<Self> {
        Self::load_from_path_with_interruption_policy(path, capacity, true)
    }

    pub fn load_read_only_from_path(path: &Path, capacity: usize) -> Result<Self> {
        Self::load_from_path_with_interruption_policy(path, capacity, false)
    }

    fn load_from_path_with_interruption_policy(
        path: &Path,
        capacity: usize,
        mark_running_interrupted: bool,
    ) -> Result<Self> {
        if !path.is_file() {
            return Ok(Self::new(capacity));
        }

        let content = fs::read_to_string(path)
            .with_context(|| format!("failed to read trace store {}", path.display()))?;
        let value: serde_json::Value = serde_json::from_str(&content)
            .with_context(|| format!("failed to parse trace store {}", path.display()))?;
        let (next_id, records) = if let Some(raw_version) = value.get("schema_version") {
            let version = raw_version.as_u64().ok_or_else(|| {
                anyhow!(
                    "invalid trace schema_version in {}: expected a positive integer",
                    path.display()
                )
            })?;
            if version != TRACE_STORE_SCHEMA_VERSION {
                return Err(anyhow!("unsupported trace schema version {version}"));
            }
            let payload: TraceStoreFileV1 = serde_json::from_value(value).with_context(|| {
                format!(
                    "invalid trace schema version 1 payload in {}",
                    path.display()
                )
            })?;
            if payload.schema_version != TRACE_STORE_SCHEMA_VERSION {
                return Err(anyhow!(
                    "unsupported trace schema version {}",
                    payload.schema_version
                ));
            }
            (payload.next_id, payload.records)
        } else {
            let payload: LegacyTraceStoreFile =
                serde_json::from_value(value).with_context(|| {
                    format!("invalid legacy trace store payload in {}", path.display())
                })?;
            let _legacy_capacity = payload.capacity;
            (payload.next_id, payload.records)
        };
        let mut store = Self {
            capacity,
            next_id,
            records,
        };
        store.next_id = store
            .records
            .iter()
            .map(|record| record.id)
            .max()
            .unwrap_or(0)
            .saturating_add(1)
            .max(store.next_id);
        if store.next_id == u64::MAX {
            return Err(anyhow!("trace record ID space is exhausted"));
        }
        if mark_running_interrupted {
            store.mark_running_records_interrupted();
        }
        store.enforce_capacity();
        Ok(store)
    }

    pub fn save_to_path(&self, path: &Path) -> Result<()> {
        let content = serde_json::to_vec_pretty(&TraceStoreFileV1Ref {
            schema_version: TRACE_STORE_SCHEMA_VERSION,
            next_id: self.next_id,
            records: &self.records,
        })
        .context("failed to serialize trace store")?;
        let parent = trace_store_parent(path);
        fs::create_dir_all(parent).with_context(|| {
            format!(
                "failed to create trace store directory {}",
                parent.display()
            )
        })?;

        let mut temporary = tempfile::NamedTempFile::new_in(parent).with_context(|| {
            format!(
                "failed to create temporary trace file in {}",
                parent.display()
            )
        })?;
        temporary
            .write_all(&content)
            .context("failed to write temporary trace file")?;
        temporary
            .flush()
            .context("failed to flush temporary trace file")?;
        temporary
            .as_file()
            .sync_all()
            .context("failed to sync temporary trace file")?;
        temporary
            .persist(path)
            .map_err(|error| error.error)
            .with_context(|| format!("failed to replace trace store {}", path.display()))?;
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

    pub fn recent_filtered(&self, filter: TraceListFilter) -> Vec<TraceRecord> {
        self.records
            .iter()
            .rev()
            .filter(|record| record.matches_filter(filter))
            .cloned()
            .collect()
    }

    pub fn recent_matching(&self, filter: TraceListFilter, query: &str) -> Vec<TraceRecord> {
        self.records
            .iter()
            .rev()
            .filter(|record| record.matches_filter(filter) && record.matches_query(query))
            .cloned()
            .collect()
    }

    pub fn trace_failure_queue(&self, limit: usize) -> Vec<TraceFailureItem> {
        self.records
            .iter()
            .rev()
            .filter_map(|record| {
                let kind = record.failure_kind()?;
                Some(TraceFailureItem {
                    trace_id: record.id,
                    kind,
                    label: record.label.clone(),
                    summary: record.summary.clone(),
                    duration_ms: record.duration_ms,
                    action: record.action.clone(),
                    related_skill_slug: record.related_skill_slug().map(str::to_string),
                })
            })
            .take(limit)
            .collect()
    }

    pub fn latest_evaluation_result_for(&self, slug: &str) -> Option<EvaluationRunResult> {
        self.records
            .iter()
            .rev()
            .flat_map(TraceRecord::evaluation_results)
            .find(|result| result.slug == slug)
    }

    pub fn latest_graded_evaluation_result_for(&self, slug: &str) -> Option<EvaluationRunResult> {
        self.records
            .iter()
            .rev()
            .flat_map(TraceRecord::evaluation_results)
            .find(|result| result.slug == slug && result.mode == EvaluationMode::Graded)
    }

    pub fn latest_graded_evaluation_results_by_slug(&self) -> Vec<EvaluationRunResult> {
        let mut results = BTreeMap::new();
        for result in self
            .records
            .iter()
            .rev()
            .flat_map(TraceRecord::evaluation_results)
            .filter(|result| result.mode == EvaluationMode::Graded)
        {
            results.entry(result.slug.clone()).or_insert(result);
        }

        results.into_values().collect()
    }

    pub fn latest_evaluation_errors(&self) -> Vec<EvaluationEvidenceError> {
        let mut handled_scopes = BTreeSet::new();
        let mut current_errors = Vec::new();

        for record in self.records.iter().rev() {
            let Some(action) = record.action.as_ref() else {
                continue;
            };
            match action {
                TraceAction::FidelityDryRunSkill { slug } => {
                    let scope = EvaluationEvidenceScope::Skill(slug.clone());
                    if !handled_scopes.insert(scope) {
                        continue;
                    }

                    if let Some(mut error) = record
                        .parsed_evaluation_evidence()
                        .errors
                        .into_iter()
                        .next()
                    {
                        if error.slug.is_none() {
                            error.slug = Some(slug.clone());
                        }
                        current_errors.push(error);
                    }
                }
                TraceAction::FidelityDryRunAll => {
                    let evidence = record.parsed_evaluation_evidence();
                    let has_errors = !evidence.errors.is_empty();
                    for error in evidence.errors {
                        let scope = error
                            .slug
                            .as_ref()
                            .map(|slug| EvaluationEvidenceScope::Skill(slug.clone()))
                            .unwrap_or(EvaluationEvidenceScope::All);
                        if handled_scopes.insert(scope) {
                            current_errors.push(error);
                        }
                    }
                    for run in evidence.runs {
                        handled_scopes.insert(EvaluationEvidenceScope::Skill(run.slug));
                    }
                    if !has_errors {
                        handled_scopes.insert(EvaluationEvidenceScope::All);
                    }
                }
                _ => {}
            }
        }

        current_errors
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

    pub fn evaluation_run_history(&self, limit: usize) -> Vec<EvaluationRunHistoryItem> {
        let mut history: Vec<_> = self
            .records
            .iter()
            .rev()
            .filter_map(TraceRecord::evaluation_run_history_item)
            .take(limit)
            .collect();
        annotate_evaluation_run_trends(&mut history);
        history
    }

    pub fn evaluation_run_history_filtered(
        &self,
        limit: usize,
        filter: EvaluationRunHistoryFilter,
    ) -> Vec<EvaluationRunHistoryItem> {
        self.evaluation_run_history(limit)
            .into_iter()
            .filter(|item| item.matches_filter(filter))
            .collect()
    }

    pub fn evaluation_trend_summary(&self, limit: usize) -> EvaluationTrendSummary {
        let history = self.evaluation_run_history(limit);
        let mut summary = EvaluationTrendSummary {
            total_runs: history.len(),
            ..EvaluationTrendSummary::default()
        };

        for item in history {
            match item.trend {
                EvaluationRunTrend::Improved => summary.improved_count += 1,
                EvaluationRunTrend::Regressed => {
                    summary.regressed_count += 1;
                    if summary.latest_regression_scope.is_none() {
                        summary.latest_regression_scope = Some(item.scope);
                    }
                }
                EvaluationRunTrend::Stable => summary.stable_count += 1,
                EvaluationRunTrend::New => summary.new_count += 1,
            }
        }

        summary
    }

    pub fn evaluation_regressions(&self, limit: usize) -> Vec<EvaluationRegressionItem> {
        let history = self.evaluation_run_history(limit);
        let mut regressions = Vec::new();

        for index in 0..history.len() {
            let current = &history[index];
            if current.trend != EvaluationRunTrend::Regressed {
                continue;
            }

            let Some(previous) = history[index + 1..].iter().find(|candidate| {
                candidate.scope == current.scope && candidate.mode == EvaluationMode::Graded
            }) else {
                continue;
            };

            let current_failed_count = current.failed_count;
            let previous_failed_count = previous.failed_count;
            let current_pass_rate = current.pass_rate_percent();
            let previous_pass_rate = previous.pass_rate_percent();

            regressions.push(EvaluationRegressionItem {
                scope: current.scope.clone(),
                current_trace_id: current.trace_id,
                previous_trace_id: previous.trace_id,
                current_failed_count,
                previous_failed_count,
                failed_delta: signed_usize_delta(current_failed_count, previous_failed_count),
                current_pass_rate,
                previous_pass_rate,
                pass_rate_delta_points: signed_usize_delta(current_pass_rate, previous_pass_rate),
                action: current.action.clone(),
            });
        }

        regressions
    }

    pub fn latest_evaluation_case_results_for(&self, slug: &str) -> Vec<EvaluationCaseResult> {
        self.latest_evaluation_case_results_by_slug()
            .remove(slug)
            .unwrap_or_default()
    }

    pub fn evaluation_run_coverage(&self, total_skill_count: usize) -> EvaluationRunCoverage {
        let structural_results = self.latest_evaluation_results_by_slug();
        let graded_results = self.latest_graded_evaluation_results_by_slug();
        EvaluationRunCoverage {
            total_skill_count,
            structural_run_skill_count: structural_results.len().min(total_skill_count),
            graded_run_skill_count: graded_results.len().min(total_skill_count),
            dry_run_skill_count: structural_results
                .iter()
                .filter(|result| result.is_dry_run())
                .count()
                .min(total_skill_count),
            current_error_count: self.latest_evaluation_errors().len(),
        }
    }

    pub fn evaluation_failure_insights(&self) -> EvaluationFailureInsights {
        let latest_cases = self.latest_graded_evaluation_case_results_by_slug();
        let mut insights = EvaluationFailureInsights::default();
        let mut failure_counts_by_slug: BTreeMap<String, usize> = BTreeMap::new();

        for result in latest_cases.into_values().flatten() {
            insights.total_cases += 1;

            match &result.status {
                EvaluationCaseStatus::Pass => insights.pass_cases += 1,
                EvaluationCaseStatus::DryRun => insights.dry_run_cases += 1,
                _ => {}
            }

            if result.status.is_failure() || result.has_failure_evidence() {
                insights.failed_cases += 1;
                *failure_counts_by_slug
                    .entry(result.slug.clone())
                    .or_default() += 1;
            }

            insights.missing_cites_count += result.missing_cites.len();
            insights.missing_mentions_count += result.missing_mentions.len();
            insights.forbidden_found_count += result.forbidden_found.len();
            insights.boundary_violations_count += result.boundary_violations.len();
            insights.fabricated_cites_count += result.fabricated_cites.len();
        }

        insights.failing_skill_count = failure_counts_by_slug.len();
        for (slug, count) in failure_counts_by_slug {
            if count > insights.top_failure_skill_count {
                insights.top_failure_skill_slug = Some(slug);
                insights.top_failure_skill_count = count;
            }
        }

        insights
    }

    pub fn evaluation_failure_queue(&self) -> Vec<EvaluationFailureItem> {
        let mut queue: Vec<_> = self
            .latest_graded_evaluation_case_results_by_slug()
            .into_values()
            .flatten()
            .filter(|result| result.status.is_failure() || result.has_failure_evidence())
            .map(|result| {
                let priority = result.failure_priority();
                let failure_summary = result.failure_summary();
                EvaluationFailureItem {
                    slug: result.slug,
                    case_index: result.case_index,
                    question: result.question,
                    status: result.status.label().to_string(),
                    priority,
                    failure_summary,
                    trace_id: result.trace_id,
                }
            })
            .collect();
        queue.sort_by(|left, right| {
            right
                .priority
                .cmp(&left.priority)
                .then_with(|| left.slug.cmp(&right.slug))
                .then_with(|| left.case_index.cmp(&right.case_index))
        });
        queue
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

    fn latest_evaluation_case_results_by_slug(
        &self,
    ) -> BTreeMap<String, Vec<EvaluationCaseResult>> {
        let mut latest_by_slug = BTreeMap::new();
        for record in self.records.iter().rev() {
            let run_slugs: Vec<_> = record
                .evaluation_results()
                .into_iter()
                .map(|result| result.slug)
                .collect();
            let mut record_results: BTreeMap<String, Vec<EvaluationCaseResult>> = run_slugs
                .iter()
                .cloned()
                .map(|slug| (slug, Vec::new()))
                .collect();
            for result in record.evaluation_case_results() {
                record_results
                    .entry(result.slug.clone())
                    .or_default()
                    .push(result);
            }

            for (slug, results) in record_results {
                latest_by_slug.entry(slug).or_insert(results);
            }
        }

        latest_by_slug
    }

    fn latest_graded_evaluation_case_results_by_slug(
        &self,
    ) -> BTreeMap<String, Vec<EvaluationCaseResult>> {
        let mut latest_by_slug = BTreeMap::new();
        for record in self.records.iter().rev() {
            let graded_slugs: Vec<_> = record
                .evaluation_results()
                .into_iter()
                .filter(|result| result.mode == EvaluationMode::Graded)
                .map(|result| result.slug)
                .collect();
            if graded_slugs.is_empty() {
                continue;
            }

            let mut record_results: BTreeMap<String, Vec<EvaluationCaseResult>> = graded_slugs
                .iter()
                .cloned()
                .map(|slug| (slug, Vec::new()))
                .collect();
            for result in record.evaluation_case_results() {
                if graded_slugs.contains(&result.slug) {
                    record_results
                        .entry(result.slug.clone())
                        .or_default()
                        .push(result);
                }
            }

            for (slug, results) in record_results {
                latest_by_slug.entry(slug).or_insert(results);
            }
        }

        latest_by_slug
    }
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::PathBuf;
    use std::time::Duration;
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::{
        EvaluationCaseStatus, EvaluationDecisionAction, EvaluationDecisionBrief,
        EvaluationDecisionPosture, EvaluationEvidenceErrorKind, EvaluationEvidenceReport,
        EvaluationFailureInsights, EvaluationFailureItem, EvaluationFailurePriority,
        EvaluationMode, EvaluationRegressionItem, EvaluationRemediationPlan, EvaluationRunCoverage,
        EvaluationRunHistoryFilter, EvaluationRunHistoryItem, EvaluationRunTrend,
        EvaluationTrendSummary, FailureKind, TraceAction, TraceListFilter, TraceStatus, TraceStore,
        TraceStoreLease,
    };

    fn temp_path(name: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("master-skill-desktop-{name}-{suffix}.json"))
    }

    fn temp_dir(name: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("master-skill-desktop-{name}-{suffix}"))
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
    fn lists_latest_failed_traces_for_recovery_queue() {
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
            "validate.py failed",
            Duration::from_millis(100),
        );

        let refresh = store.begin_with_action(
            "Refreshing runtime data",
            TraceAction::Refresh,
            None::<String>,
            "Queued.",
        );
        store.finish_success(
            refresh,
            "Runtime data refreshed.",
            Duration::from_millis(20),
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
            Duration::from_millis(30),
        );

        let queue = store.trace_failure_queue(5);

        assert_eq!(queue.len(), 2);
        assert_eq!(queue[0].trace_id, install);
        assert_eq!(queue[0].kind, FailureKind::Install);
        assert_eq!(queue[0].label, "Installing master-huineng");
        assert_eq!(queue[0].summary, "install failed");
        assert_eq!(queue[0].duration_ms, Some(30));
        assert_eq!(queue[0].related_skill_slug.as_deref(), Some("huineng"));
        assert_eq!(
            queue[0].action,
            Some(TraceAction::InstallSkill {
                slug: "huineng".to_string()
            })
        );

        assert_eq!(queue[1].trace_id, validation);
        assert_eq!(queue[1].kind, FailureKind::Validation);
        assert_eq!(queue[1].related_skill_slug, None);
    }

    #[test]
    fn filters_recent_traces_by_status_and_operation_class() {
        let mut store = TraceStore::new(10);

        let refresh = store.begin_with_action(
            "Refreshing runtime data",
            TraceAction::Refresh,
            None::<String>,
            "Queued.",
        );
        store.finish_success(refresh, "Runtime data refreshed.", Duration::from_millis(8));

        let install = store.begin_with_action(
            "Installing master-huineng",
            TraceAction::InstallSkill {
                slug: "huineng".to_string(),
            },
            Some("master-skill install huineng"),
            "Queued.",
        );
        store.finish_error(install, "install failed", Duration::from_millis(12));

        let fidelity = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Queued.",
        );
        store.finish_success(fidelity, "fidelity finished", Duration::from_millis(20));

        let validation = store.begin_with_action(
            "Running full validation",
            TraceAction::FullValidation,
            Some("npm test"),
            "Queued.",
        );

        let failed = store.recent_filtered(TraceListFilter::Failed);
        assert_eq!(failed.len(), 1);
        assert_eq!(failed[0].id, install);

        let running = store.recent_filtered(TraceListFilter::Running);
        assert_eq!(running.len(), 1);
        assert_eq!(running[0].id, validation);

        let evaluation = store.recent_filtered(TraceListFilter::Evaluation);
        assert_eq!(evaluation.len(), 2);
        assert_eq!(evaluation[0].id, validation);
        assert_eq!(evaluation[1].id, fidelity);

        let install_ops = store.recent_filtered(TraceListFilter::Install);
        assert_eq!(install_ops.len(), 1);
        assert_eq!(install_ops[0].id, install);
    }

    #[test]
    fn searches_recent_traces_across_metadata_and_detail() {
        let mut store = TraceStore::new(10);

        let refresh = store.begin_with_action(
            "Refreshing runtime data",
            TraceAction::Refresh,
            None::<String>,
            "Queued.",
        );
        store.finish_success(refresh, "Runtime data refreshed.", Duration::from_millis(8));

        let validation = store.begin_with_action(
            "Running full validation",
            TraceAction::FullValidation,
            Some("npm test"),
            "Queued.",
        );
        store.finish_error_with_detail(
            validation,
            "npm test failed",
            "validate.py failed while checking manifests",
            Duration::from_millis(12),
        );

        let fidelity = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            "Queued.",
        );
        store.finish_success_with_detail(
            fidelity,
            "master-huineng fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/12 passed (N/A)",
            Duration::from_millis(20),
        );

        let huineng = store.recent_matching(TraceListFilter::All, "HUINENG");
        assert_eq!(huineng.len(), 1);
        assert_eq!(huineng[0].id, fidelity);

        let manifest = store.recent_matching(TraceListFilter::Failed, "manifest");
        assert_eq!(manifest.len(), 1);
        assert_eq!(manifest[0].id, validation);

        let evaluation = store.recent_matching(TraceListFilter::Evaluation, "npm");
        assert_eq!(evaluation.len(), 1);
        assert_eq!(evaluation[0].id, validation);

        let all = store.recent_matching(TraceListFilter::All, "   ");
        assert_eq!(all.len(), 3);
        assert_eq!(all[0].id, fidelity);
        assert_eq!(all[1].id, validation);
        assert_eq!(all[2].id, refresh);
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
        assert!(result.is_dry_run());
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
        assert_eq!(results[0].status, EvaluationCaseStatus::DryRun);
        assert_eq!(results[0].difficulty.as_deref(), Some("basic"));
        assert_eq!(results[0].trace_id, run);
        assert_eq!(results[1].case_index, 2);
        assert_eq!(results[1].question, "顿悟怎么修？");
    }

    #[test]
    fn latest_case_results_do_not_merge_history() {
        let mut store = TraceStore::new(10);
        let old_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 0,
              "failed": 1,
              "results": [
                {"index": 0, "question": "旧结果", "status": "FAIL"}
              ]
            }]"#,
            Duration::from_millis(50),
        );
        let new_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 1,
              "failed": 0,
              "results": [
                {"index": 0, "question": "新结果", "status": "PASS"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        let cases = store.latest_evaluation_case_results_for("huineng");
        assert_eq!(cases.len(), 1);
        assert_eq!(cases[0].status, EvaluationCaseStatus::Pass);
        assert_eq!(cases[0].trace_id, new_run);
        assert_eq!(cases[0].question, "新结果");
    }

    #[test]
    fn later_dry_run_preserves_graded_evidence() {
        let mut store = TraceStore::new(10);
        let graded_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            graded_run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 1,
              "failed": 0,
              "results": [
                {"index": 0, "question": "已评分", "status": "PASS"}
              ]
            }]"#,
            Duration::from_millis(50),
        );
        let dry_run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            dry_run,
            "master-huineng fidelity dry-run finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "dry_run",
              "outcome": "completed",
              "total": 1,
              "results": [
                {"index": 0, "question": "仅结构检查", "status": "dry_run"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        let latest = store.latest_evaluation_result_for("huineng").unwrap();
        assert_eq!(latest.trace_id, dry_run);
        assert!(latest.is_dry_run());

        let latest_graded = store
            .latest_graded_evaluation_result_for("huineng")
            .unwrap();
        assert_eq!(latest_graded.trace_id, graded_run);
        assert_eq!(latest_graded.mode, EvaluationMode::Graded);
        let graded_results = store.latest_graded_evaluation_results_by_slug();
        assert_eq!(graded_results, vec![latest_graded]);

        let insights = store.evaluation_failure_insights();
        assert_eq!(insights.total_cases, 1);
        assert_eq!(insights.pass_cases, 1);
        assert_eq!(insights.dry_run_cases, 0);

        let history = store.evaluation_run_history(2);
        assert_eq!(history[0].trace_id, dry_run);
        assert_eq!(history[0].trend, EvaluationRunTrend::New);
    }

    #[test]
    fn parses_v1_evaluation_modes_and_case_statuses() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running fidelity suites",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "fidelity suites finished",
            r#"[
              {
                "schema_version": 1,
                "master": "master-huineng",
                "mode": "dry_run",
                "outcome": "completed",
                "total": 1,
                "results": [
                  {"index": 0, "question": "结构检查", "status": "dry_run"}
                ]
              },
              {
                "schema_version": 1,
                "master": "master-zhiyi",
                "mode": "graded",
                "outcome": "completed",
                "total": 2,
                "passed": 1,
                "failed": 1,
                "results": [
                  {"index": 0, "question": "通过", "status": "PASS"},
                  {"index": 1, "question": "失败", "status": "FAIL"}
                ]
              }
            ]"#,
            Duration::from_millis(50),
        );

        let results = store.latest_evaluation_results_by_slug();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].slug, "huineng");
        assert_eq!(results[0].mode, EvaluationMode::DryRun);
        assert_eq!(results[0].passed_count, 0);
        assert_eq!(results[1].slug, "zhiyi");
        assert_eq!(results[1].mode, EvaluationMode::Graded);
        assert_eq!(results[1].passed_count, 1);

        let huineng_cases = store.latest_evaluation_case_results_for("huineng");
        assert_eq!(huineng_cases[0].status, EvaluationCaseStatus::DryRun);
        let zhiyi_cases = store.latest_evaluation_case_results_for("zhiyi");
        assert_eq!(zhiyi_cases[0].status, EvaluationCaseStatus::Pass);
        assert_eq!(zhiyi_cases[1].status, EvaluationCaseStatus::Fail);
    }

    #[test]
    fn rejects_ambiguous_legacy_evaluation_json() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            r#"[{
              "master": "master-huineng",
              "total": 1,
              "results": [
                {"index": 0, "question": "模式不明确", "status": "PASS"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        assert!(store.latest_evaluation_result_for("huineng").is_none());
        assert!(store
            .latest_evaluation_case_results_for("huineng")
            .is_empty());
        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(
            errors[0].kind,
            EvaluationEvidenceErrorKind::MalformedPayload
        );
    }

    #[test]
    fn exposes_v1_evaluation_error_outcome_as_execution_evidence() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_error_with_detail(
            run,
            "master-huineng fidelity failed",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "error",
              "total": 0,
              "results": [],
              "error": "ANTHROPIC_API_KEY environment variable not set"
            }]"#,
            Duration::from_millis(50),
        );

        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].trace_id, run);
        assert_eq!(errors[0].slug.as_deref(), Some("huineng"));
        assert_eq!(errors[0].kind, EvaluationEvidenceErrorKind::Execution);
        assert!(errors[0].message.contains("ANTHROPIC_API_KEY"));
    }

    #[test]
    fn reports_malformed_json_as_evaluation_evidence_error() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            "[",
            Duration::from_millis(50),
        );

        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].slug.as_deref(), Some("huineng"));
        assert_eq!(
            errors[0].kind,
            EvaluationEvidenceErrorKind::MalformedPayload
        );
    }

    #[test]
    fn reports_unsupported_evaluation_schema_version() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 2,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 0,
              "passed": 0,
              "failed": 0,
              "results": []
            }]"#,
            Duration::from_millis(50),
        );

        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(
            errors[0].kind,
            EvaluationEvidenceErrorKind::UnsupportedVersion
        );
        assert!(errors[0].message.contains('2'));
    }

    #[test]
    fn reports_unknown_case_status_as_malformed_evidence() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 0,
              "failed": 1,
              "results": [
                {"index": 0, "question": "未知状态", "status": "SKIPPED"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        assert!(store.latest_evaluation_result_for("huineng").is_none());
        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(
            errors[0].kind,
            EvaluationEvidenceErrorKind::MalformedPayload
        );
        assert!(errors[0].message.contains("SKIPPED"));
    }

    #[test]
    fn rejects_case_index_that_cannot_be_displayed_one_based() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            format!(
                r#"[{{
                  "schema_version": 1,
                  "master": "master-huineng",
                  "mode": "graded",
                  "outcome": "completed",
                  "total": 1,
                  "passed": 1,
                  "failed": 0,
                  "results": [
                    {{"index": {}, "question": "overflow", "status": "PASS"}}
                  ]
                }}]"#,
                usize::MAX
            ),
            Duration::from_millis(50),
        );

        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(
            errors[0].kind,
            EvaluationEvidenceErrorKind::MalformedPayload
        );
        assert!(errors[0].message.contains("index"));
    }

    #[test]
    fn rejects_evaluation_payload_for_wrong_skill_scope() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-zhiyi",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 1,
              "failed": 0,
              "results": [
                {"index": 0, "question": "错误 scope", "status": "PASS"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        assert!(store.latest_evaluation_result_for("zhiyi").is_none());
        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(
            errors[0].kind,
            EvaluationEvidenceErrorKind::MalformedPayload
        );
        assert_eq!(errors[0].slug.as_deref(), Some("huineng"));
        assert!(errors[0].message.contains("scope"));
    }

    #[test]
    fn reports_failed_evaluation_trace_as_execution_evidence() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_error_with_detail(
            run,
            "fidelity command failed",
            "python exited before producing JSON",
            Duration::from_millis(50),
        );

        let errors = store.records.back().unwrap().evaluation_errors();
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].kind, EvaluationEvidenceErrorKind::Execution);
        assert_eq!(errors[0].slug.as_deref(), Some("huineng"));
        assert!(errors[0].message.contains("python exited"));
    }

    #[test]
    fn selects_only_current_evaluation_errors_per_skill_scope() {
        let mut store = TraceStore::new(10);

        let huineng_error = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_error_with_detail(
            huineng_error,
            "master-huineng fidelity failed",
            "old huineng failure",
            Duration::from_millis(50),
        );

        let zhiyi_error = store.begin_with_action(
            "Running master-zhiyi fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "zhiyi".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-zhiyi --json"),
            "Queued.",
        );
        store.finish_error_with_detail(
            zhiyi_error,
            "master-zhiyi fidelity failed",
            "current zhiyi failure",
            Duration::from_millis(50),
        );

        let huineng_success = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            huineng_success,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "dry_run",
              "outcome": "completed",
              "total": 1,
              "results": [
                {"index": 0, "question": "结构检查", "status": "dry_run"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        let xuanzang_error = store.begin_with_action(
            "Running master-xuanzang fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "xuanzang".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-xuanzang --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            xuanzang_error,
            "master-xuanzang fidelity finished",
            "[",
            Duration::from_millis(50),
        );

        let errors = store.latest_evaluation_errors();
        assert_eq!(errors.len(), 2);
        assert_eq!(errors[0].slug.as_deref(), Some("xuanzang"));
        assert_eq!(errors[1].slug.as_deref(), Some("zhiyi"));
        assert!(!errors
            .iter()
            .any(|error| error.slug.as_deref() == Some("huineng")));
    }

    #[test]
    fn successful_all_scope_run_replaces_older_all_scope_error() {
        let mut store = TraceStore::new(10);
        let failed_all = store.begin_with_action(
            "Running all fidelity suites",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_error_with_detail(
            failed_all,
            "all fidelity suites failed",
            "runner exited before producing JSON",
            Duration::from_millis(50),
        );
        assert_eq!(store.latest_evaluation_errors().len(), 1);

        let successful_all = store.begin_with_action(
            "Running all fidelity suites",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --dry-run --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            successful_all,
            "all fidelity suites finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "dry_run",
              "outcome": "completed",
              "total": 1,
              "results": [
                {"index": 0, "question": "结构检查", "status": "dry_run"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        assert!(store.latest_evaluation_errors().is_empty());
    }

    #[test]
    fn summarizes_evaluation_case_failure_details_from_json_trace() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 0,
                "total": 1,
                "results": [
                  {
                    "index": 0,
                    "question": "什么是见性成佛？",
                    "difficulty": "basic",
                    "status": "FAIL",
                    "missing_cites": ["T48n2008"],
                    "missing_mentions": ["自性", "佛性"],
                    "forbidden_found": ["过程旁白"],
                    "boundary_violations": ["风格已立"],
                    "fabricated_cites": ["T99n9999"]
                  }
                ]
              }
            ]"#,
            Duration::from_millis(50),
        );

        let results = store.latest_evaluation_case_results_for("huineng");

        assert_eq!(results.len(), 1);
        assert_eq!(
            results[0].failure_summary(),
            "missing cites: T48n2008; missing mentions: 自性, 佛性; forbidden: 过程旁白; boundary: 风格已立; fabricated cites: T99n9999"
        );
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
        assert_eq!(coverage.structural_run_skill_count, 2);
        assert_eq!(coverage.dry_run_skill_count, 2);
        assert_eq!(coverage.graded_run_skill_count, 0);
        assert_eq!(coverage.current_error_count, 0);
        assert_eq!(coverage.structural_label(), "2/18");
    }

    /// Real (trimmed) `python3 scripts/test-fidelity.py --master master-zhiyi
    /// --dry-run --json` output captured 2026-07-10 as Task 1b evidence,
    /// trimmed from 10 to 3 cases. Field names and nesting are unmodified.
    fn real_json_dry_run_detail_zhiyi() -> &'static str {
        r#"[
  {
    "master": "master-zhiyi",
    "total": 3,
    "results": [
      {
        "index": 0,
        "question": "什么是一念三千？",
        "must_cite": ["T1911", "摩訶止觀"],
        "must_mention": ["十法界", "三千", "一念心"],
        "difficulty": "basic",
        "status": "dry_run"
      },
      {
        "index": 1,
        "question": "三谛圆融是什么意思？",
        "must_cite": ["T1716", "法華玄義"],
        "must_mention": ["空", "假", "中", "圆融"],
        "difficulty": "basic",
        "status": "dry_run"
      },
      {
        "index": 2,
        "question": "五时八教怎么分？",
        "must_cite": ["T1716"],
        "must_mention": ["华严", "阿含", "方等", "般若", "法华"],
        "difficulty": "basic",
        "status": "dry_run"
      }
    ]
  }
]"#
    }

    /// Real (trimmed) `--master master-huineng --dry-run --json` output, 2
    /// of N cases.
    fn real_json_dry_run_detail_huineng() -> &'static str {
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
]"#
    }

    /// Real (trimmed) `--master master-nagarjuna --dry-run --json` output, 2
    /// of 10 cases.
    fn real_json_dry_run_detail_nagarjuna() -> &'static str {
        r#"[
  {
    "master": "master-nagarjuna",
    "total": 2,
    "results": [
      {
        "index": 0,
        "question": "什么是八不中道？",
        "must_cite": ["T30n1564", "中论"],
        "must_mention": ["不生不灭", "不常不断", "中道", "缘起", "戏论"],
        "difficulty": "basic",
        "status": "dry_run"
      },
      {
        "index": 1,
        "question": "'众因缘生法，我说即是空'是什么意思？",
        "must_cite": ["T30n1564"],
        "must_mention": ["缘起", "性空", "空", "假名", "中道"],
        "difficulty": "basic",
        "status": "dry_run"
      }
    ]
  }
]"#
    }

    #[test]
    fn parses_evaluation_results_from_real_json_dry_run_detail() {
        // GUI and headless dry-runs both invoke `--json` (cli.rs, baseline.rs)
        // and store the *full* raw stdout as `detail` (app.rs / baseline.rs
        // use `output.trim().to_string()`, not the truncated
        // `summarize_command_output` summary). `evaluation_results()` must
        // therefore understand this real JSON shape, not just the legacy
        // `Testing: / Result:` plain-text format.
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running master-zhiyi fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "zhiyi".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-zhiyi --dry-run --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-zhiyi fidelity dry-run finished",
            real_json_dry_run_detail_zhiyi(),
            Duration::from_millis(64),
        );

        let result = store
            .latest_evaluation_result_for("zhiyi")
            .expect("expected a parsed evaluation result for the JSON dry-run detail");
        assert_eq!(result.slug, "zhiyi");
        assert_eq!(result.passed_count, 0);
        assert_eq!(result.total_count, 3);
        assert!(result.is_dry_run());
        assert_eq!(result.trace_id, run);
    }

    #[test]
    fn summarizes_evaluation_run_coverage_from_json_dry_run_results() {
        let mut store = TraceStore::new(10);

        for (slug, detail) in [
            ("zhiyi", real_json_dry_run_detail_zhiyi()),
            ("huineng", real_json_dry_run_detail_huineng()),
            ("nagarjuna", real_json_dry_run_detail_nagarjuna()),
        ] {
            let run = store.begin_with_action(
                format!("Running master-{slug} fidelity dry-run"),
                TraceAction::FidelityDryRunSkill {
                    slug: slug.to_string(),
                },
                Some(format!(
                    "python3 scripts/test-fidelity.py --master master-{slug} --dry-run --json"
                )),
                "Queued.",
            );
            store.finish_success_with_detail(
                run,
                format!("master-{slug} fidelity dry-run finished"),
                detail,
                Duration::from_millis(50),
            );
        }

        let coverage = store.evaluation_run_coverage(3);

        assert_eq!(coverage.total_skill_count, 3);
        assert_eq!(coverage.structural_run_skill_count, 3);
        assert_eq!(coverage.dry_run_skill_count, 3);
        assert_eq!(coverage.graded_run_skill_count, 0);
        assert_eq!(coverage.current_error_count, 0);
        assert_eq!(coverage.structural_label(), "3/3");
        assert!(coverage.is_structurally_complete());
    }

    #[test]
    fn complete_dry_run_coverage_is_unproven() {
        // Mirrors `master-skill-desktop --baseline` recording one real
        // `--json` dry-run trace per skill via the shared trace-store code
        // path (baseline.rs / app.rs), then computes the exact signals
        // `evaluation_gate_snapshot` (app.rs) feeds into
        // `EvaluationDecisionBrief::from_signals`.
        let mut store = TraceStore::new(10);

        for (slug, detail) in [
            ("zhiyi", real_json_dry_run_detail_zhiyi()),
            ("huineng", real_json_dry_run_detail_huineng()),
            ("nagarjuna", real_json_dry_run_detail_nagarjuna()),
        ] {
            let run = store.begin_with_action(
                format!("Running master-{slug} fidelity dry-run"),
                TraceAction::FidelityDryRunSkill {
                    slug: slug.to_string(),
                },
                Some(format!(
                    "python3 scripts/test-fidelity.py --master master-{slug} --dry-run --json"
                )),
                "Queued.",
            );
            store.finish_success_with_detail(
                run,
                format!("master-{slug} fidelity dry-run finished"),
                detail,
                Duration::from_millis(50),
            );
        }

        let coverage = store.evaluation_run_coverage(3);
        let insights = store.evaluation_failure_insights();
        let trend = store.evaluation_trend_summary(20);
        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);

        assert!(coverage.is_structurally_complete());
        assert!(!coverage.is_graded_complete());
        assert_eq!(brief.posture, EvaluationDecisionPosture::Unproven);
        assert_eq!(brief.headline, "Graded evidence incomplete");
    }

    #[test]
    fn complete_passing_graded_coverage_is_ready() {
        let mut store = TraceStore::new(10);
        let run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 1,
              "failed": 0,
              "results": [
                {"index": 0, "question": "已评分", "status": "PASS"}
              ]
            }]"#,
            Duration::from_millis(50),
        );

        let coverage = store.evaluation_run_coverage(1);
        let insights = store.evaluation_failure_insights();
        let trend = store.evaluation_trend_summary(8);
        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);

        assert!(coverage.is_structurally_complete());
        assert!(coverage.is_graded_complete());
        assert_eq!(coverage.current_error_count, 0);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Ready);
        assert_eq!(brief.headline, "Graded evaluation clear");
    }

    #[test]
    fn current_evaluation_error_blocks_older_passing_evidence() {
        let mut store = TraceStore::new(10);
        let graded_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            graded_run,
            "master-huineng fidelity finished",
            r#"[{
              "schema_version": 1,
              "master": "master-huineng",
              "mode": "graded",
              "outcome": "completed",
              "total": 1,
              "passed": 1,
              "failed": 0,
              "results": [
                {"index": 0, "question": "旧通过", "status": "PASS"}
              ]
            }]"#,
            Duration::from_millis(50),
        );
        let failed_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_error_with_detail(
            failed_run,
            "master-huineng fidelity failed",
            "runner failed before producing evidence",
            Duration::from_millis(50),
        );

        let coverage = store.evaluation_run_coverage(1);
        let insights = store.evaluation_failure_insights();
        let trend = store.evaluation_trend_summary(8);
        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);

        assert!(coverage.is_graded_complete());
        assert_eq!(coverage.current_error_count, 1);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Blocked);
        assert_eq!(brief.headline, "Evaluation evidence error");
    }

    #[test]
    fn summarizes_evaluation_failure_insights_from_latest_case_results() {
        let mut store = TraceStore::new(10);

        let old_run = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_run,
            "master-huineng fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "旧问题不应重复计算",
                    "status": "FAIL",
                    "missing_cites": ["OLD"]
                  }
                ]
              }
            ]"#,
            Duration::from_millis(40),
        );

        let latest_run = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            latest_run,
            "fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 1,
                "results": [
                  {
                    "index": 0,
                    "question": "什么是见性成佛？",
                    "status": "PASS"
                  },
                  {
                    "index": 1,
                    "question": "顿悟是否等于随意发挥？",
                    "status": "FAIL",
                    "missing_cites": ["T48n2008"],
                    "forbidden_found": ["过程旁白"]
                  }
                ]
              },
              {
                "master": "master-zhiyi",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "一念三千如何表达？",
                    "status": "FAIL",
                    "missing_mentions": ["三谛"],
                    "boundary_violations": ["越出天台语境"]
                  }
                ]
              }
            ]"#,
            Duration::from_millis(55),
        );

        let insights = store.evaluation_failure_insights();

        assert_eq!(insights.total_cases, 3);
        assert_eq!(insights.failed_cases, 2);
        assert_eq!(insights.pass_cases, 1);
        assert_eq!(insights.failing_skill_count, 2);
        assert_eq!(insights.top_failure_skill_slug.as_deref(), Some("huineng"));
        assert_eq!(insights.top_failure_skill_count, 1);
        assert_eq!(insights.missing_cites_count, 1);
        assert_eq!(insights.missing_mentions_count, 1);
        assert_eq!(insights.forbidden_found_count, 1);
        assert_eq!(insights.boundary_violations_count, 1);
        assert_eq!(insights.fabricated_cites_count, 0);
    }

    #[test]
    fn keeps_graded_insights_empty_for_dry_run_only_cases() {
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
                "results": [
                  {
                    "index": 0,
                    "question": "什么是见性成佛？",
                    "status": "dry_run"
                  },
                  {
                    "index": 1,
                    "question": "顿悟怎么修？",
                    "status": "dry_run"
                  }
                ]
              }
            ]"#,
            Duration::from_millis(55),
        );

        let insights = store.evaluation_failure_insights();

        assert_eq!(insights.total_cases, 0);
        assert_eq!(insights.dry_run_cases, 0);
        assert_eq!(insights.graded_cases(), 0);
        assert_eq!(insights.pass_rate_label(), "N/A");
    }

    #[test]
    fn lists_latest_failed_evaluation_cases_for_action_queue() {
        let mut store = TraceStore::new(10);

        let old_run = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_run,
            "master-huineng fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "旧失败不应进入队列",
                    "status": "FAIL",
                    "missing_cites": ["OLD"]
                  }
                ]
              }
            ]"#,
            Duration::from_millis(40),
        );

        let latest_run = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            latest_run,
            "fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 1,
                "results": [
                  {
                    "index": 0,
                    "question": "这个 case 已经通过",
                    "status": "PASS"
                  },
                  {
                    "index": 1,
                    "question": "顿悟是否等于随意发挥？",
                    "status": "FAIL",
                    "missing_cites": ["T48n2008"],
                    "forbidden_found": ["过程旁白"]
                  }
                ]
              },
              {
                "master": "master-zhiyi",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "一念三千如何表达？",
                    "status": "FAIL",
                    "missing_mentions": ["三谛"]
                  }
                ]
              }
            ]"#,
            Duration::from_millis(55),
        );

        let queue = store.evaluation_failure_queue();

        assert_eq!(queue.len(), 2);
        assert_eq!(queue[0].slug, "huineng");
        assert_eq!(queue[0].case_index, 2);
        assert_eq!(queue[0].question, "顿悟是否等于随意发挥？");
        assert_eq!(
            queue[0].failure_summary,
            "missing cites: T48n2008; forbidden: 过程旁白"
        );
        assert_eq!(queue[0].trace_id, latest_run);
        assert_eq!(queue[1].slug, "zhiyi");
        assert_eq!(queue[1].case_index, 1);
        assert_eq!(queue[1].failure_summary, "missing mentions: 三谛");
    }

    #[test]
    fn prioritizes_failure_queue_by_risk() {
        let mut store = TraceStore::new(10);

        let run = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            run,
            "fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "只有 status 失败",
                    "status": "FAIL"
                  }
                ]
              },
              {
                "master": "master-zhiyi",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "缺少引用",
                    "status": "FAIL",
                    "missing_cites": ["T46n1911"]
                  }
                ]
              },
              {
                "master": "master-xuanzang",
                "passed": 0,
                "results": [
                  {
                    "index": 0,
                    "question": "伪造引用",
                    "status": "FAIL",
                    "fabricated_cites": ["T99n9999"]
                  }
                ]
              }
            ]"#,
            Duration::from_millis(55),
        );

        let queue = store.evaluation_failure_queue();

        assert_eq!(queue[0].slug, "xuanzang");
        assert_eq!(queue[0].priority.label(), "critical");
        assert_eq!(queue[1].slug, "zhiyi");
        assert_eq!(queue[1].priority.label(), "high");
        assert_eq!(queue[2].slug, "huineng");
        assert_eq!(queue[2].priority.label(), "medium");
    }

    #[test]
    fn lists_recent_evaluation_run_history_with_counts_and_rerun_actions() {
        let mut store = TraceStore::new(10);

        let skill_run = store.begin_with_action(
            "Running master-huineng fidelity dry-run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            skill_run,
            "master-huineng fidelity dry-run finished",
            "Testing: master-huineng\nResult: 0/12 passed (N/A)",
            Duration::from_millis(40),
        );

        let all_run = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            all_run,
            "fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 1,
                "results": [
                  {"index": 0, "question": "通过", "status": "PASS"},
                  {"index": 1, "question": "失败", "status": "FAIL"}
                ]
              },
              {
                "master": "master-zhiyi",
                "passed": 1,
                "results": [
                  {"index": 0, "question": "通过", "status": "PASS"}
                ]
              }
            ]"#,
            Duration::from_millis(55),
        );

        let history = store.evaluation_run_history(5);

        assert_eq!(history.len(), 2);
        assert_eq!(history[0].trace_id, all_run);
        assert_eq!(history[0].scope, "all");
        assert_eq!(history[0].passed_count, 2);
        assert_eq!(history[0].total_count, 3);
        assert_eq!(history[0].failed_count, 1);
        assert!(!history[0].is_dry_run());
        assert_eq!(history[0].duration_ms, Some(55));
        assert_eq!(history[0].action, Some(TraceAction::FidelityDryRunAll));

        assert_eq!(history[1].trace_id, skill_run);
        assert_eq!(history[1].scope, "master-huineng");
        assert_eq!(history[1].passed_count, 0);
        assert_eq!(history[1].total_count, 12);
        assert_eq!(history[1].failed_count, 0);
        assert!(history[1].is_dry_run());
        assert_eq!(
            history[1].action,
            Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string()
            })
        );
    }

    #[test]
    fn pass_rate_calculation_handles_large_legacy_counts() {
        let item = EvaluationRunHistoryItem {
            trace_id: 1,
            scope: "master-huineng".to_string(),
            status: TraceStatus::Succeeded,
            passed_count: usize::MAX,
            total_count: usize::MAX,
            failed_count: 0,
            mode: EvaluationMode::Graded,
            duration_ms: None,
            action: None,
            trend: EvaluationRunTrend::New,
        };

        assert_eq!(item.pass_rate_percent(), 100);
    }

    #[test]
    fn annotates_evaluation_run_history_with_scope_trends() {
        let mut store = TraceStore::new(10);

        let old_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_huineng,
            "master-huineng fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 0,
                "results": [
                  {"index": 0, "question": "失败一", "status": "FAIL"},
                  {"index": 1, "question": "失败二", "status": "FAIL"}
                ]
              }
            ]"#,
            Duration::from_millis(40),
        );

        let old_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_all,
            "fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 1,
                "results": [
                  {"index": 0, "question": "通过", "status": "PASS"}
                ]
              }
            ]"#,
            Duration::from_millis(45),
        );

        let new_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_huineng,
            "master-huineng fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 1,
                "results": [
                  {"index": 0, "question": "通过", "status": "PASS"},
                  {"index": 1, "question": "仍失败", "status": "FAIL"}
                ]
              }
            ]"#,
            Duration::from_millis(35),
        );

        let new_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_all,
            "fidelity run finished",
            r#"[
              {
                "master": "master-huineng",
                "passed": 0,
                "results": [
                  {"index": 0, "question": "失败", "status": "FAIL"}
                ]
              }
            ]"#,
            Duration::from_millis(50),
        );

        let history = store.evaluation_run_history(4);

        assert_eq!(history[0].trace_id, new_all);
        assert_eq!(history[0].trend.label(), "regressed");
        assert_eq!(history[1].trace_id, new_huineng);
        assert_eq!(history[1].trend.label(), "improved");
        assert_eq!(history[2].trace_id, old_all);
        assert_eq!(history[2].trend.label(), "new");
        assert_eq!(history[3].trace_id, old_huineng);
        assert_eq!(history[3].trend.label(), "new");
    }

    #[test]
    fn filters_evaluation_run_history_by_trend_and_failed_results() {
        let mut store = TraceStore::new(10);

        let old_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_huineng,
            "master-huineng fidelity run finished",
            r#"[{"master": "master-huineng", "passed": 0, "results": [
              {"index": 0, "question": "失败一", "status": "FAIL"},
              {"index": 1, "question": "失败二", "status": "FAIL"}
            ]}]"#,
            Duration::from_millis(40),
        );

        let old_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_all,
            "fidelity run finished",
            r#"[{"master": "master-huineng", "passed": 1, "results": [
              {"index": 0, "question": "通过", "status": "PASS"}
            ]}]"#,
            Duration::from_millis(45),
        );

        let new_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_huineng,
            "master-huineng fidelity run finished",
            r#"[{"master": "master-huineng", "passed": 1, "results": [
              {"index": 0, "question": "通过", "status": "PASS"},
              {"index": 1, "question": "仍失败", "status": "FAIL"}
            ]}]"#,
            Duration::from_millis(35),
        );

        let new_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_all,
            "fidelity run finished",
            r#"[{"master": "master-huineng", "passed": 0, "results": [
              {"index": 0, "question": "失败", "status": "FAIL"}
            ]}]"#,
            Duration::from_millis(50),
        );

        let regressed =
            store.evaluation_run_history_filtered(4, EvaluationRunHistoryFilter::Regressed);
        assert_eq!(regressed.len(), 1);
        assert_eq!(regressed[0].trace_id, new_all);

        let improved =
            store.evaluation_run_history_filtered(4, EvaluationRunHistoryFilter::Improved);
        assert_eq!(improved.len(), 1);
        assert_eq!(improved[0].trace_id, new_huineng);

        let failed = store.evaluation_run_history_filtered(4, EvaluationRunHistoryFilter::Failed);
        assert_eq!(failed.len(), 3);
        assert_eq!(failed[0].trace_id, new_all);
        assert_eq!(failed[1].trace_id, new_huineng);
        assert_eq!(failed[2].trace_id, old_huineng);
    }

    #[test]
    fn summarizes_evaluation_trends_from_recent_run_history() {
        let mut store = TraceStore::new(10);

        let old_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_huineng,
            "master-huineng fidelity run finished",
            r#"[
              {"master": "master-huineng", "passed": 0, "results": [
                {"index": 0, "question": "失败一", "status": "FAIL"},
                {"index": 1, "question": "失败二", "status": "FAIL"}
              ]}
            ]"#,
            Duration::from_millis(40),
        );

        let old_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_all,
            "fidelity run finished",
            r#"[
              {"master": "master-huineng", "passed": 1, "results": [
                {"index": 0, "question": "通过", "status": "PASS"}
              ]}
            ]"#,
            Duration::from_millis(45),
        );

        let new_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_huineng,
            "master-huineng fidelity run finished",
            r#"[
              {"master": "master-huineng", "passed": 1, "results": [
                {"index": 0, "question": "通过", "status": "PASS"},
                {"index": 1, "question": "仍失败", "status": "FAIL"}
              ]}
            ]"#,
            Duration::from_millis(35),
        );

        let new_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_all,
            "fidelity run finished",
            r#"[
              {"master": "master-huineng", "passed": 0, "results": [
                {"index": 0, "question": "失败", "status": "FAIL"}
              ]}
            ]"#,
            Duration::from_millis(50),
        );

        let summary = store.evaluation_trend_summary(4);

        assert_eq!(summary.total_runs, 4);
        assert_eq!(summary.improved_count, 1);
        assert_eq!(summary.regressed_count, 1);
        assert_eq!(summary.stable_count, 0);
        assert_eq!(summary.new_count, 2);
        assert_eq!(summary.latest_regression_scope.as_deref(), Some("all"));
        assert_eq!(summary.health_label(), "review");
    }

    #[test]
    fn builds_evaluation_decision_brief_from_quality_signals() {
        let coverage = EvaluationRunCoverage {
            total_skill_count: 3,
            structural_run_skill_count: 3,
            graded_run_skill_count: 3,
            dry_run_skill_count: 0,
            current_error_count: 0,
        };
        let mut trend = EvaluationTrendSummary {
            total_runs: 3,
            regressed_count: 1,
            latest_regression_scope: Some("master-huineng".to_string()),
            ..EvaluationTrendSummary::default()
        };
        let mut insights = EvaluationFailureInsights {
            total_cases: 3,
            pass_cases: 2,
            failed_cases: 1,
            failing_skill_count: 1,
            top_failure_skill_slug: Some("huineng".to_string()),
            top_failure_skill_count: 1,
            ..EvaluationFailureInsights::default()
        };

        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Blocked);
        assert_eq!(brief.status_label(), "blocked");
        assert_eq!(brief.headline, "Regression detected");
        assert_eq!(brief.primary_risk, "master-huineng regressed");
        assert_eq!(
            brief.action,
            EvaluationDecisionAction::RerunSkill {
                slug: "huineng".to_string()
            }
        );

        trend.regressed_count = 0;
        trend.latest_regression_scope = None;

        let errored = EvaluationRunCoverage {
            current_error_count: 1,
            ..coverage.clone()
        };
        let brief = EvaluationDecisionBrief::from_signals(&errored, &trend, &insights);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Blocked);
        assert_eq!(brief.headline, "Evaluation evidence error");

        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Attention);
        assert_eq!(brief.headline, "Failing fidelity cases");
        assert_eq!(brief.primary_risk, "master-huineng (1)");
        assert_eq!(
            brief.action,
            EvaluationDecisionAction::OpenSkill {
                slug: "huineng".to_string()
            }
        );

        insights.failed_cases = 0;
        insights.failing_skill_count = 0;
        insights.top_failure_skill_slug = None;
        insights.top_failure_skill_count = 0;
        let uncovered = EvaluationRunCoverage {
            structural_run_skill_count: 2,
            ..coverage.clone()
        };
        let brief = EvaluationDecisionBrief::from_signals(&uncovered, &trend, &insights);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Unproven);
        assert_eq!(brief.headline, "Evaluation coverage incomplete");
        assert_eq!(brief.primary_risk, "2/3 skills have structural runs");
        assert_eq!(brief.action, EvaluationDecisionAction::RunFidelityBaseline);

        let graded_gap = EvaluationRunCoverage {
            graded_run_skill_count: 2,
            ..coverage.clone()
        };
        let brief = EvaluationDecisionBrief::from_signals(&graded_gap, &trend, &insights);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Unproven);
        assert_eq!(brief.headline, "Graded evidence incomplete");

        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);
        assert_eq!(brief.posture, EvaluationDecisionPosture::Ready);
        assert_eq!(brief.status_label(), "ready");
        assert_eq!(brief.headline, "Graded evaluation clear");
        assert_eq!(brief.action, EvaluationDecisionAction::RunFullValidation);
    }

    #[test]
    fn renders_evaluation_evidence_report_for_release_review() {
        let coverage = EvaluationRunCoverage {
            total_skill_count: 3,
            structural_run_skill_count: 2,
            graded_run_skill_count: 0,
            dry_run_skill_count: 2,
            current_error_count: 0,
        };
        let trend = EvaluationTrendSummary {
            total_runs: 2,
            regressed_count: 1,
            improved_count: 0,
            stable_count: 1,
            new_count: 0,
            latest_regression_scope: Some("master-huineng".to_string()),
        };
        let insights = EvaluationFailureInsights {
            total_cases: 12,
            pass_cases: 10,
            failed_cases: 2,
            failing_skill_count: 1,
            top_failure_skill_slug: Some("huineng".to_string()),
            top_failure_skill_count: 2,
            fabricated_cites_count: 1,
            boundary_violations_count: 1,
            ..EvaluationFailureInsights::default()
        };
        let brief = EvaluationDecisionBrief::from_signals(&coverage, &trend, &insights);
        let regressions = vec![EvaluationRegressionItem {
            scope: "master-huineng".to_string(),
            current_trace_id: 9,
            previous_trace_id: 5,
            current_failed_count: 2,
            previous_failed_count: 0,
            failed_delta: 2,
            current_pass_rate: 80,
            previous_pass_rate: 100,
            pass_rate_delta_points: -20,
            action: Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            }),
        }];
        let failure_queue = vec![EvaluationFailureItem {
            slug: "huineng".to_string(),
            case_index: 1,
            question: "What is no-thought?".to_string(),
            status: "FAIL".to_string(),
            priority: EvaluationFailurePriority::Critical,
            failure_summary: "fabricated cite: Platform Sutra X".to_string(),
            trace_id: 9,
        }];
        let run_history = vec![EvaluationRunHistoryItem {
            trace_id: 9,
            scope: "master-huineng".to_string(),
            status: TraceStatus::Succeeded,
            passed_count: 10,
            total_count: 12,
            failed_count: 2,
            mode: EvaluationMode::DryRun,
            duration_ms: Some(150),
            action: Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            }),
            trend: EvaluationRunTrend::Regressed,
        }];

        let report = EvaluationEvidenceReport::from_signals(
            &brief,
            &coverage,
            &trend,
            &insights,
            &regressions,
            &failure_queue,
            &run_history,
        );

        assert!(report
            .markdown
            .contains("# Master-skill Evaluation Evidence Report"));
        assert!(report.markdown.contains("- Status: blocked"));
        assert!(report
            .markdown
            .contains("- Structural coverage: 2/3 skills"));
        assert!(report.markdown.contains("- Graded coverage: 0/3 skills"));
        assert!(report
            .markdown
            .contains("- Trend: 1 regressed / 0 improved / 1 stable / 0 new"));
        assert!(report
            .markdown
            .contains("- Failure evidence: 2 failed case(s), 1 failing skill(s), pass rate 83%"));
        assert!(report
            .markdown
            .contains("- master-huineng: trace #9 vs #5, failed +2, pass rate -20 pts"));
        assert!(report
            .markdown
            .contains("- critical master-huineng case #1: fabricated cite: Platform Sutra X"));
        assert!(report
            .markdown
            .contains("- #9 master-huineng: success, 10/12 N/A, 2 failed, regressed"));
    }

    #[test]
    fn builds_copyable_evaluation_remediation_plan() {
        let brief = EvaluationDecisionBrief {
            posture: EvaluationDecisionPosture::Blocked,
            headline: "Regression detected".to_string(),
            primary_risk: "master-huineng regressed".to_string(),
            evidence: "1 regression across 8 recent runs".to_string(),
            recommendation: "Rerun the regressed scope and inspect failed cases before release."
                .to_string(),
            action: EvaluationDecisionAction::RerunSkill {
                slug: "huineng".to_string(),
            },
        };
        let regressions = vec![EvaluationRegressionItem {
            scope: "master-huineng".to_string(),
            current_trace_id: 42,
            previous_trace_id: 40,
            current_failed_count: 2,
            previous_failed_count: 0,
            failed_delta: 2,
            current_pass_rate: 80,
            previous_pass_rate: 100,
            pass_rate_delta_points: -20,
            action: Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            }),
        }];
        let failure_queue = vec![EvaluationFailureItem {
            slug: "huineng".to_string(),
            case_index: 3,
            question: "如何见性?".to_string(),
            status: "FAIL".to_string(),
            priority: EvaluationFailurePriority::Critical,
            failure_summary: "fabricated cites: X9".to_string(),
            trace_id: 42,
        }];
        let run_history = vec![EvaluationRunHistoryItem {
            trace_id: 42,
            scope: "master-huineng".to_string(),
            status: TraceStatus::Succeeded,
            passed_count: 8,
            total_count: 10,
            failed_count: 2,
            mode: EvaluationMode::Graded,
            duration_ms: Some(120),
            action: Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            }),
            trend: EvaluationRunTrend::Regressed,
        }];

        let plan = EvaluationRemediationPlan::from_signals(
            &brief,
            &regressions,
            &failure_queue,
            &run_history,
        );

        assert_eq!(plan.item_count, 4);
        assert_eq!(
            plan.items,
            vec![
                "Rerun master-huineng and compare trace #42 against #40 (failed +2, pass rate -20 pts)",
                "Fix master-huineng case #3 (critical): fabricated cites: X9",
                "Rerun affected fidelity scopes",
                "Run `npm test`",
            ]
        );
        assert!(plan
            .markdown
            .contains("# Master-skill Evaluation Remediation Plan"));
        assert!(plan.markdown.contains("- [ ] Rerun master-huineng"));
        assert!(plan.markdown.contains("- [ ] Fix master-huineng case #3"));
        assert!(plan.markdown.contains("- [ ] Run `npm test`"));
        assert!(plan.markdown.contains("latest trace #42"));
    }

    #[test]
    fn graded_gap_remediation_does_not_recommend_another_dry_run() {
        let coverage = EvaluationRunCoverage {
            total_skill_count: 1,
            structural_run_skill_count: 1,
            graded_run_skill_count: 0,
            dry_run_skill_count: 1,
            current_error_count: 0,
        };
        let brief = EvaluationDecisionBrief::from_signals(
            &coverage,
            &EvaluationTrendSummary::default(),
            &EvaluationFailureInsights::default(),
        );

        let plan = EvaluationRemediationPlan::from_signals(&brief, &[], &[], &[]);

        assert_eq!(brief.headline, "Graded evidence incomplete");
        assert!(plan.items[0].contains("graded fidelity evidence"));
        assert!(!plan.items[0].contains("baseline"));
    }

    #[test]
    fn lists_evaluation_regressions_with_previous_run_context() {
        let mut store = TraceStore::new(10);

        let old_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_huineng,
            "master-huineng fidelity run finished",
            r#"[
              {"master": "master-huineng", "passed": 2, "results": [
                {"index": 0, "question": "通过一", "status": "PASS"},
                {"index": 1, "question": "通过二", "status": "PASS"}
              ]}
            ]"#,
            Duration::from_millis(40),
        );

        let old_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_all,
            "fidelity run finished",
            r#"[
              {"master": "master-zhiyi", "passed": 0, "results": [
                {"index": 0, "question": "失败", "status": "FAIL"}
              ]}
            ]"#,
            Duration::from_millis(45),
        );

        let new_huineng = store.begin_with_action(
            "Running master-huineng fidelity run",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("python3 scripts/test-fidelity.py --master master-huineng --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_huineng,
            "master-huineng fidelity run finished",
            r#"[
              {"master": "master-huineng", "passed": 1, "results": [
                {"index": 0, "question": "通过", "status": "PASS"},
                {"index": 1, "question": "回归失败", "status": "FAIL"}
              ]}
            ]"#,
            Duration::from_millis(35),
        );

        let new_all = store.begin_with_action(
            "Running fidelity run",
            TraceAction::FidelityDryRunAll,
            Some("python3 scripts/test-fidelity.py --all --json"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_all,
            "fidelity run finished",
            r#"[
              {"master": "master-zhiyi", "passed": 1, "results": [
                {"index": 0, "question": "通过", "status": "PASS"}
              ]}
            ]"#,
            Duration::from_millis(50),
        );

        let regressions = store.evaluation_regressions(8);

        assert_eq!(regressions.len(), 1);
        assert_eq!(regressions[0].scope, "master-huineng");
        assert_eq!(regressions[0].current_trace_id, new_huineng);
        assert_eq!(regressions[0].previous_trace_id, old_huineng);
        assert_eq!(regressions[0].current_failed_count, 1);
        assert_eq!(regressions[0].previous_failed_count, 0);
        assert_eq!(regressions[0].failed_delta, 1);
        assert_eq!(regressions[0].current_pass_rate, 50);
        assert_eq!(regressions[0].previous_pass_rate, 100);
        assert_eq!(regressions[0].pass_rate_delta_points, -50);
        assert_eq!(
            regressions[0].action,
            Some(TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string()
            })
        );
    }

    #[test]
    fn saturates_large_legacy_regression_deltas() {
        let mut store = TraceStore::new(10);
        let old_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("legacy fidelity"),
            "Queued.",
        );
        store.finish_success_with_detail(
            old_run,
            "legacy fidelity finished",
            "Testing: master-huineng\nResult: 0/1 passed (0%)",
            Duration::from_millis(50),
        );
        let new_run = store.begin_with_action(
            "Running master-huineng fidelity",
            TraceAction::FidelityDryRunSkill {
                slug: "huineng".to_string(),
            },
            Some("legacy fidelity"),
            "Queued.",
        );
        store.finish_success_with_detail(
            new_run,
            "legacy fidelity finished",
            format!(
                "Testing: master-huineng\nResult: 0/{} passed (0%)",
                usize::MAX
            ),
            Duration::from_millis(50),
        );

        let regressions = store.evaluation_regressions(8);

        assert_eq!(regressions.len(), 1);
        assert_eq!(regressions[0].failed_delta, isize::MAX);
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
    fn loads_legacy_trace_file_and_rewrites_schema_v1() {
        let directory = temp_dir("trace-legacy");
        let path = directory.join("desktop-traces.json");
        fs::create_dir_all(&directory).unwrap();
        fs::write(&path, r#"{"capacity":99,"next_id":7,"records":[]}"#).unwrap();

        let store = TraceStore::load_from_path(&path, 10).unwrap();
        store.save_to_path(&path).unwrap();
        let value: serde_json::Value =
            serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();

        assert_eq!(value["schema_version"], 1);
        assert_eq!(value["next_id"], 7);
        assert!(value.get("capacity").is_none());
        assert!(value["records"].is_array());
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn rejects_unknown_trace_schema_version() {
        let directory = temp_dir("trace-version");
        let path = directory.join("desktop-traces.json");
        fs::create_dir_all(&directory).unwrap();
        fs::write(&path, r#"{"schema_version":2,"next_id":1,"records":[]}"#).unwrap();

        let error = TraceStore::load_from_path(&path, 10).unwrap_err();

        assert!(format!("{error:#}").contains("unsupported trace schema version 2"));
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn rejects_trace_store_with_exhausted_record_ids() {
        let directory = temp_dir("trace-id-exhausted");
        let path = directory.join("desktop-traces.json");
        fs::create_dir_all(&directory).unwrap();
        fs::write(
            &path,
            format!(
                r#"{{"schema_version":1,"next_id":{},"records":[]}}"#,
                u64::MAX
            ),
        )
        .unwrap();

        let error = TraceStore::load_from_path(&path, 10).unwrap_err();

        assert!(format!("{error:#}").contains("record ID space is exhausted"));
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn versioned_trace_file_round_trips_without_capacity() {
        let directory = temp_dir("trace-v1");
        let path = directory.join("desktop-traces.json");
        let mut store = TraceStore::new(10);
        store.begin("one");

        store.save_to_path(&path).unwrap();
        let restored = TraceStore::load_from_path(&path, 3).unwrap();
        let value: serde_json::Value =
            serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();

        assert_eq!(restored.summary().total, 1);
        assert_eq!(value["schema_version"], 1);
        assert!(value.get("capacity").is_none());
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn only_one_trace_store_lease_can_hold_a_path() {
        let directory = temp_dir("trace-lease");
        let path = directory.join("desktop-traces.json");
        let first = TraceStoreLease::try_acquire(&path).unwrap().unwrap();

        assert!(TraceStoreLease::try_acquire(&path).unwrap().is_none());
        drop(first);
        assert!(TraceStoreLease::try_acquire(&path).unwrap().is_some());
        fs::remove_dir_all(directory).unwrap();
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
    fn read_only_load_preserves_running_records_owned_by_writer() {
        let path = temp_path("trace-read-only");
        let mut store = TraceStore::new(10);
        store.begin_with_action(
            "Running full validation",
            TraceAction::FullValidation,
            Some("npm test"),
            "Queued.",
        );
        store.save_to_path(&path).unwrap();

        let restored = TraceStore::load_read_only_from_path(&path, 10).unwrap();

        assert_eq!(restored.recent()[0].status, TraceStatus::Running);
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
