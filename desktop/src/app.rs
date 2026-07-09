use std::collections::BTreeMap;
use std::path::PathBuf;
use std::sync::mpsc::{channel, Receiver};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::Result;
use eframe::egui;

use crate::catalog::{
    console_summary, evaluation_summary, filter_rows, tradition_options, DiagnosticAction,
    DiagnosticOperation, FidelityCase, InstallFilter, QualityLevel, SkillDiagnostics, SkillRow,
};
use crate::cli::CliClient;
use crate::layout::{
    dashboard_columns_for_width, dense_table_mode_for_width, metric_card_width,
    metric_cards_per_row, operation_log_height, TwoPaneMode,
};
use crate::model::{DoctorReport, MasterInspect, SkillInventory};
use crate::theme::{
    apply_console_theme, sidebar_default_width, sidebar_row_height, status_badge_width,
};
use crate::trace::{
    EvaluationDecisionAction, EvaluationDecisionBrief, EvaluationDecisionPosture,
    EvaluationFailureInsights, EvaluationFailureItem, EvaluationFailurePriority,
    EvaluationRegressionItem, EvaluationRunHistoryFilter, EvaluationRunHistoryItem,
    EvaluationRunResult, EvaluationRunTrend, EvaluationTrendSummary, TraceAction, TraceFailureItem,
    TraceListFilter, TraceStatus, TraceStore,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ConsoleSection {
    Overview,
    Evaluation,
    Runs,
    SkillDetail,
}

impl ConsoleSection {
    fn label(self) -> &'static str {
        match self {
            ConsoleSection::Overview => "Overview",
            ConsoleSection::Evaluation => "Evaluation",
            ConsoleSection::Runs => "Runs",
            ConsoleSection::SkillDetail => "Skill Detail",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum SuiteFilter {
    All,
    Ready,
    Attention,
    Missing,
    NotRun,
    FailedRun,
}

impl SuiteFilter {
    fn label(self) -> &'static str {
        match self {
            Self::All => "All",
            Self::Ready => "Ready",
            Self::Attention => "Attention",
            Self::Missing => "Missing",
            Self::NotRun => "Not Run",
            Self::FailedRun => "Failed Run",
        }
    }
}

fn suite_matches_filter(
    row: &SkillRow,
    latest_result: Option<&EvaluationRunResult>,
    filter: SuiteFilter,
) -> bool {
    match filter {
        SuiteFilter::All => true,
        SuiteFilter::Ready => row.quality_level() == QualityLevel::Ready,
        SuiteFilter::Attention => row.quality_level() == QualityLevel::Attention,
        SuiteFilter::Missing => row.quality_level() == QualityLevel::Missing,
        SuiteFilter::NotRun => latest_result.is_none(),
        SuiteFilter::FailedRun => latest_result.is_some_and(|result| {
            !result.dry_run && result.total_count > 0 && result.passed_count < result.total_count
        }),
    }
}

fn suite_matches_query(row: &SkillRow, query: &str) -> bool {
    let query = query.trim().to_ascii_lowercase();
    if query.is_empty() {
        return true;
    }

    row.title().to_ascii_lowercase().contains(&query)
        || row.name.to_ascii_lowercase().contains(&query)
        || row.slug.to_ascii_lowercase().contains(&query)
        || row.description.to_ascii_lowercase().contains(&query)
        || row
            .tradition
            .as_ref()
            .is_some_and(|value| value.to_ascii_lowercase().contains(&query))
        || row
            .school
            .as_ref()
            .is_some_and(|value| value.to_ascii_lowercase().contains(&query))
        || row
            .diagnostic_summary()
            .to_ascii_lowercase()
            .contains(&query)
}

pub struct MasterSkillApp {
    client: CliClient,
    inventory: Option<SkillInventory>,
    rows: Vec<SkillRow>,
    doctor: Option<DoctorReport>,
    selected: Option<MasterInspect>,
    selected_slug: Option<String>,
    search_query: String,
    install_filter: InstallFilter,
    tradition_filter: Option<String>,
    log: String,
    log_lines: Vec<String>,
    task_rx: Option<Receiver<TaskEnvelope>>,
    busy_label: Option<String>,
    console_section: ConsoleSection,
    log_expanded: bool,
    trace_filter: TraceListFilter,
    trace_query: String,
    suite_filter: SuiteFilter,
    suite_query: String,
    run_history_filter: EvaluationRunHistoryFilter,
    traces: TraceStore,
    trace_path: PathBuf,
}

struct Snapshot {
    inventory: SkillInventory,
    rows: Vec<SkillRow>,
    doctor: DoctorReport,
    selected_slug: Option<String>,
    selected: Option<MasterInspect>,
}

struct TaskOutcome {
    message: String,
    detail: String,
    snapshot: Option<Snapshot>,
}

type TaskResult = std::result::Result<TaskOutcome, String>;

struct TaskEnvelope {
    trace_id: u64,
    elapsed: Duration,
    result: TaskResult,
}

struct MetricCard {
    title: &'static str,
    value: String,
    detail: String,
    healthy: bool,
}

impl MasterSkillApp {
    pub fn new() -> Self {
        let trace_path = desktop_trace_store_path();
        let (traces, trace_load_message) = match TraceStore::load_from_path(&trace_path, 200) {
            Ok(traces) => (traces, None),
            Err(err) => (
                TraceStore::new(200),
                Some(format!("Trace history load failed: {err:#}")),
            ),
        };
        let mut app = Self {
            client: CliClient::default(),
            inventory: None,
            rows: Vec::new(),
            doctor: None,
            selected: None,
            selected_slug: None,
            search_query: String::new(),
            install_filter: InstallFilter::All,
            tradition_filter: None,
            log: "Starting desktop manager...".to_string(),
            log_lines: vec!["Starting desktop manager...".to_string()],
            task_rx: None,
            busy_label: None,
            console_section: ConsoleSection::Overview,
            log_expanded: false,
            trace_filter: TraceListFilter::All,
            trace_query: String::new(),
            suite_filter: SuiteFilter::All,
            suite_query: String::new(),
            run_history_filter: EvaluationRunHistoryFilter::All,
            traces,
            trace_path,
        };
        if let Some(message) = trace_load_message {
            app.set_log(message);
        }
        app.refresh_all();
        app
    }

    fn load_snapshot(client: &CliClient, selected_slug: Option<String>) -> Result<Snapshot> {
        let inventory = client.list()?;
        let doctor = client.doctor()?;
        let prebuilt_dir = std::path::Path::new(&doctor.prebuilt_path);
        let resolved_slug =
            selected_slug.or_else(|| inventory.masters.first().map(|m| m.slug.clone()));
        let mut rows = Vec::with_capacity(inventory.masters.len());
        let mut selected = None;

        for summary in &inventory.masters {
            let inspect = client.inspect(&summary.slug)?;
            if resolved_slug.as_deref() == Some(summary.slug.as_str()) {
                selected = Some(inspect.clone());
            }
            let mut row = SkillRow::from_summary_and_inspect(summary, Some(&inspect));
            row.apply_diagnostics(SkillDiagnostics::from_prebuilt_dir(
                prebuilt_dir,
                &summary.slug,
            ));
            rows.push(row);
        }

        Ok(Snapshot {
            inventory,
            rows,
            doctor,
            selected_slug: resolved_slug,
            selected,
        })
    }

    fn apply_snapshot(&mut self, snapshot: Snapshot) {
        self.inventory = Some(snapshot.inventory);
        self.rows = snapshot.rows;
        self.doctor = Some(snapshot.doctor);
        self.selected_slug = snapshot.selected_slug;
        self.selected = snapshot.selected;
    }

    fn set_log(&mut self, message: impl Into<String>) {
        let message = message.into();
        self.log = message.clone();
        self.log_lines.push(message);
        if self.log_lines.len() > 200 {
            self.log_lines.remove(0);
        }
    }

    fn persist_traces(&mut self) {
        if let Err(err) = self.traces.save_to_path(&self.trace_path) {
            self.set_log(format!("Trace history save failed: {err:#}"));
        }
    }

    fn refresh_all(&mut self) {
        match Self::load_snapshot(&self.client, self.selected_slug.clone()) {
            Ok(snapshot) => {
                self.apply_snapshot(snapshot);
                self.set_log("Runtime data refreshed.");
            }
            Err(err) => self.set_log(format!("Refresh failed: {err:#}")),
        }
    }

    fn is_busy(&self) -> bool {
        self.task_rx.is_some()
    }

    fn start_task_with_action<F>(
        &mut self,
        label: impl Into<String>,
        action: Option<TraceAction>,
        command: Option<impl Into<String>>,
        task: F,
    ) where
        F: FnOnce(CliClient) -> Result<TaskOutcome> + Send + 'static,
    {
        if self.is_busy() {
            self.set_log("A task is already running.");
            return;
        }

        let client = self.client.clone();
        let label = label.into();
        let trace_id = if let Some(action) = action {
            self.traces
                .begin_with_action(label.clone(), action, command, "Queued.")
        } else {
            self.traces
                .begin_with_detail(label.clone(), command, "Queued.")
        };
        self.persist_traces();
        let (tx, rx) = channel();
        self.task_rx = Some(rx);
        self.busy_label = Some(label.clone());
        self.set_log(format!("{label}..."));

        thread::spawn(move || {
            let started = Instant::now();
            let result = task(client).map_err(|err| format!("{err:#}"));
            let _ = tx.send(TaskEnvelope {
                trace_id,
                elapsed: started.elapsed(),
                result,
            });
        });
    }

    fn poll_task(&mut self) {
        let envelope = self.task_rx.as_ref().and_then(|rx| rx.try_recv().ok());
        if let Some(envelope) = envelope {
            self.task_rx = None;
            self.busy_label = None;
            match envelope.result {
                Ok(outcome) => {
                    if let Some(snapshot) = outcome.snapshot {
                        self.apply_snapshot(snapshot);
                    }
                    self.traces.finish_success_with_detail(
                        envelope.trace_id,
                        outcome.message.clone(),
                        outcome.detail.clone(),
                        envelope.elapsed,
                    );
                    self.persist_traces();
                    self.set_log(outcome.message);
                }
                Err(message) => {
                    self.traces.finish_error_with_detail(
                        envelope.trace_id,
                        first_line(&message),
                        message.clone(),
                        envelope.elapsed,
                    );
                    self.persist_traces();
                    self.set_log(message);
                }
            }
        }
    }

    fn start_refresh(&mut self) {
        let selected_slug = self.selected_slug.clone();
        self.start_task_with_action(
            "Refreshing runtime data",
            Some(TraceAction::Refresh),
            None::<String>,
            move |client| {
                let snapshot = Self::load_snapshot(&client, selected_slug)?;
                Ok(TaskOutcome {
                    message: "Runtime data refreshed.".to_string(),
                    detail: "Reloaded inventory, runtime doctor report, selected skill metadata, and local diagnostics.".to_string(),
                    snapshot: Some(snapshot),
                })
            },
        );
    }

    fn start_inspect(&mut self, slug: String) {
        self.start_task_with_action(
            format!("Loading master-{slug}"),
            Some(TraceAction::InspectSkill { slug: slug.clone() }),
            None::<String>,
            move |client| {
                let snapshot = Self::load_snapshot(&client, Some(slug.clone()))?;
                Ok(TaskOutcome {
                    message: format!("Loaded master-{slug}."),
                    detail: format!(
                        "Loaded source, evaluation, install, and runtime metadata for master-{slug}."
                    ),
                    snapshot: Some(snapshot),
                })
            },
        );
    }

    fn start_install(&mut self, slug: String) {
        self.start_task_with_action(
            format!("Installing master-{slug}"),
            Some(TraceAction::InstallSkill { slug: slug.clone() }),
            Some(format!("master-skill install {slug}")),
            move |client| {
                let output = client.install(&slug)?;
                let snapshot = Self::load_snapshot(&client, Some(slug))?;
                Ok(TaskOutcome {
                    message: output.trim().to_string(),
                    detail: output.trim().to_string(),
                    snapshot: Some(snapshot),
                })
            },
        );
    }

    fn start_uninstall(&mut self, slug: String) {
        self.start_task_with_action(
            format!("Uninstalling master-{slug}"),
            Some(TraceAction::UninstallSkill { slug: slug.clone() }),
            Some(format!("master-skill uninstall {slug}")),
            move |client| {
                let output = client.uninstall(&slug)?;
                let snapshot = Self::load_snapshot(&client, Some(slug))?;
                Ok(TaskOutcome {
                    message: output.trim().to_string(),
                    detail: output.trim().to_string(),
                    snapshot: Some(snapshot),
                })
            },
        );
    }

    fn start_install_all(&mut self) {
        let selected_slug = self.selected_slug.clone();
        self.start_task_with_action(
            "Installing all skills",
            Some(TraceAction::InstallAll),
            Some("master-skill install --all"),
            move |client| {
                let output = client.install_all()?;
                let snapshot = Self::load_snapshot(&client, selected_slug)?;
                Ok(TaskOutcome {
                    message: output.trim().to_string(),
                    detail: output.trim().to_string(),
                    snapshot: Some(snapshot),
                })
            },
        );
    }

    fn start_update_all(&mut self) {
        let selected_slug = self.selected_slug.clone();
        self.start_task_with_action(
            "Updating all skills",
            Some(TraceAction::UpdateAll),
            Some("master-skill update --all"),
            move |client| {
                let output = client.update_all()?;
                let snapshot = Self::load_snapshot(&client, selected_slug)?;
                Ok(TaskOutcome {
                    message: output.trim().to_string(),
                    detail: output.trim().to_string(),
                    snapshot: Some(snapshot),
                })
            },
        );
    }

    fn start_fidelity_dry_run(&mut self) {
        self.start_task_with_action(
            "Running fidelity dry-run",
            Some(TraceAction::FidelityDryRunAll),
            Some("python3 scripts/test-fidelity.py --all --dry-run --json"),
            move |client| {
                let output = client.run_fidelity_dry_run()?;
                Ok(TaskOutcome {
                    message: summarize_command_output("Fidelity dry-run finished", &output),
                    detail: output.trim().to_string(),
                    snapshot: None,
                })
            },
        );
    }

    fn start_skill_fidelity_dry_run(&mut self, slug: String) {
        self.start_task_with_action(
            format!("Running master-{slug} fidelity dry-run"),
            Some(TraceAction::FidelityDryRunSkill { slug: slug.clone() }),
            Some(format!(
                "python3 scripts/test-fidelity.py --master master-{slug} --dry-run --json"
            )),
            move |client| {
                let output = client.run_fidelity_dry_run_for(&slug)?;
                Ok(TaskOutcome {
                    message: summarize_command_output(
                        &format!("master-{slug} fidelity dry-run finished"),
                        &output,
                    ),
                    detail: output.trim().to_string(),
                    snapshot: None,
                })
            },
        );
    }

    fn start_full_validation(&mut self) {
        self.start_task_with_action(
            "Running full validation",
            Some(TraceAction::FullValidation),
            Some("npm test"),
            move |client| {
                let output = client.run_full_validation()?;
                Ok(TaskOutcome {
                    message: summarize_command_output("Full validation finished", &output),
                    detail: output.trim().to_string(),
                    snapshot: None,
                })
            },
        );
    }

    fn show_toolbar(&mut self, ui: &mut egui::Ui) {
        let busy = self.is_busy();
        ui.horizontal(|ui| {
            ui.heading("Master-skill Desktop Manager");
            ui.separator();
            if ui
                .add_enabled(!busy, egui::Button::new("Refresh"))
                .clicked()
            {
                self.start_refresh();
            }
            if ui
                .add_enabled(!busy, egui::Button::new("Install all"))
                .clicked()
            {
                self.start_install_all();
            }
            if ui
                .add_enabled(!busy, egui::Button::new("Update all"))
                .clicked()
            {
                self.start_update_all();
            }
            if let Some(label) = &self.busy_label {
                ui.separator();
                ui.spinner();
                ui.label(label);
            }
        });
        ui.horizontal(|ui| {
            for section in [
                ConsoleSection::Overview,
                ConsoleSection::Evaluation,
                ConsoleSection::Runs,
                ConsoleSection::SkillDetail,
            ] {
                ui.selectable_value(&mut self.console_section, section, section.label());
            }
            ui.separator();
            if let Some(report) = &self.doctor {
                ui.label(format!(
                    "Runtime: {} | Installed: {}/{}",
                    report.status, report.installed_known_skills, report.available_skills
                ));
            }
        });
        ui.small(format!("Repo: {}", self.client.repo_root().display()));
    }

    fn quality_color(level: QualityLevel) -> egui::Color32 {
        match level {
            QualityLevel::Ready => egui::Color32::from_rgb(100, 190, 130),
            QualityLevel::Attention => egui::Color32::from_rgb(220, 170, 80),
            QualityLevel::Missing => egui::Color32::from_rgb(210, 100, 100),
        }
    }

    fn trace_color(status: TraceStatus) -> egui::Color32 {
        match status {
            TraceStatus::Running => egui::Color32::from_rgb(120, 170, 230),
            TraceStatus::Succeeded => egui::Color32::from_rgb(100, 190, 130),
            TraceStatus::Failed => egui::Color32::from_rgb(210, 100, 100),
        }
    }

    fn failure_priority_color(priority: EvaluationFailurePriority) -> egui::Color32 {
        match priority {
            EvaluationFailurePriority::Critical => egui::Color32::from_rgb(220, 90, 85),
            EvaluationFailurePriority::High => egui::Color32::from_rgb(210, 145, 70),
            EvaluationFailurePriority::Medium => egui::Color32::from_rgb(145, 160, 180),
        }
    }

    fn decision_posture_color(posture: EvaluationDecisionPosture) -> egui::Color32 {
        match posture {
            EvaluationDecisionPosture::Blocked => egui::Color32::from_rgb(220, 90, 85),
            EvaluationDecisionPosture::Attention => egui::Color32::from_rgb(220, 170, 80),
            EvaluationDecisionPosture::Unproven => egui::Color32::from_rgb(120, 170, 230),
            EvaluationDecisionPosture::Ready => egui::Color32::from_rgb(100, 190, 130),
        }
    }

    fn evaluation_trend_color(trend: EvaluationRunTrend) -> egui::Color32 {
        match trend {
            EvaluationRunTrend::Improved => egui::Color32::from_rgb(100, 190, 130),
            EvaluationRunTrend::Regressed => egui::Color32::from_rgb(220, 90, 85),
            EvaluationRunTrend::Stable => egui::Color32::from_rgb(145, 160, 180),
            EvaluationRunTrend::New => egui::Color32::from_rgb(120, 170, 230),
        }
    }

    fn quality_badge_fill(level: QualityLevel) -> egui::Color32 {
        match level {
            QualityLevel::Ready => egui::Color32::from_rgb(21, 64, 44),
            QualityLevel::Attention => egui::Color32::from_rgb(76, 57, 28),
            QualityLevel::Missing => egui::Color32::from_rgb(74, 36, 36),
        }
    }

    fn show_quality_badge(ui: &mut egui::Ui, level: QualityLevel) {
        let fill = Self::quality_badge_fill(level);
        let stroke = egui::Stroke::new(1.0, Self::quality_color(level));
        ui.allocate_ui_with_layout(
            egui::vec2(status_badge_width(), sidebar_row_height() - 4.0),
            egui::Layout::top_down(egui::Align::Center),
            |ui| {
                egui::Frame::new()
                    .fill(fill)
                    .stroke(stroke)
                    .inner_margin(egui::Margin::symmetric(6, 2))
                    .show(ui, |ui| {
                        ui.set_width((status_badge_width() - 16.0).max(28.0));
                        ui.centered_and_justified(|ui| {
                            ui.small(level.label());
                        });
                    });
            },
        );
    }

    fn start_diagnostic_operation(&mut self, operation: DiagnosticOperation) {
        match operation {
            DiagnosticOperation::Manual => {
                self.set_log("Manual action selected; edit the skill files and refresh.");
            }
            DiagnosticOperation::InstallSkill { slug } => self.start_install(slug),
            DiagnosticOperation::FidelityDryRun { slug } => self.start_skill_fidelity_dry_run(slug),
        }
    }

    fn start_trace_action(&mut self, action: TraceAction) {
        match action {
            TraceAction::Refresh => self.start_refresh(),
            TraceAction::InspectSkill { slug } => self.start_inspect(slug),
            TraceAction::InstallSkill { slug } => self.start_install(slug),
            TraceAction::UninstallSkill { slug } => self.start_uninstall(slug),
            TraceAction::InstallAll => self.start_install_all(),
            TraceAction::UpdateAll => self.start_update_all(),
            TraceAction::FidelityDryRunAll => self.start_fidelity_dry_run(),
            TraceAction::FidelityDryRunSkill { slug } => self.start_skill_fidelity_dry_run(slug),
            TraceAction::FullValidation => self.start_full_validation(),
        }
    }

    fn start_evaluation_decision_action(&mut self, action: EvaluationDecisionAction) {
        match action {
            EvaluationDecisionAction::RerunAll | EvaluationDecisionAction::RunFidelityBaseline => {
                self.start_fidelity_dry_run()
            }
            EvaluationDecisionAction::RerunSkill { slug } => {
                self.start_skill_fidelity_dry_run(slug)
            }
            EvaluationDecisionAction::OpenSkill { slug } => {
                self.console_section = ConsoleSection::SkillDetail;
                self.start_inspect(slug);
            }
            EvaluationDecisionAction::RunFullValidation => self.start_full_validation(),
        }
    }

    fn show_workspace_header(
        ui: &mut egui::Ui,
        title: &str,
        detail: &str,
        actions: impl FnOnce(&mut egui::Ui),
    ) {
        ui.horizontal(|ui| {
            ui.vertical(|ui| {
                ui.heading(title);
                ui.small(detail);
            });
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), actions);
        });
        ui.separator();
    }

    fn show_metric_card(
        ui: &mut egui::Ui,
        width: f32,
        title: &str,
        value: impl Into<String>,
        detail: &str,
        healthy: bool,
    ) {
        let fill = if healthy {
            egui::Color32::from_rgb(24, 42, 34)
        } else {
            egui::Color32::from_rgb(50, 37, 26)
        };
        let stroke = if healthy {
            egui::Stroke::new(1.0, egui::Color32::from_rgb(67, 120, 88))
        } else {
            egui::Stroke::new(1.0, egui::Color32::from_rgb(140, 103, 55))
        };

        ui.allocate_ui_with_layout(
            egui::vec2(width, 58.0),
            egui::Layout::top_down(egui::Align::Min),
            |ui| {
                egui::Frame::new()
                    .fill(fill)
                    .stroke(stroke)
                    .inner_margin(egui::Margin::same(8))
                    .show(ui, |ui| {
                        let inner_width = (width - 18.0).max(80.0);
                        ui.set_min_width(inner_width);
                        ui.set_max_width(inner_width);
                        ui.small(title);
                        ui.heading(value.into());
                        ui.small(detail);
                    });
            },
        );
    }

    fn show_metric_cards(ui: &mut egui::Ui, cards: &[MetricCard]) {
        let card_width = metric_card_width(ui.available_width());
        let columns = metric_cards_per_row(
            ui.available_width(),
            card_width,
            ui.spacing().item_spacing.x,
        );

        for row in cards.chunks(columns) {
            ui.horizontal(|ui| {
                for card in row {
                    Self::show_metric_card(
                        ui,
                        card_width,
                        card.title,
                        card.value.clone(),
                        &card.detail,
                        card.healthy,
                    );
                }
            });
        }
    }

    fn show_dashboard(&self, ui: &mut egui::Ui) {
        Self::show_workspace_header(
            ui,
            "Overview",
            "Runtime health, installation coverage, and selected skill context.",
            |_| {},
        );
        ui.heading("Console Health");
        if let Some(report) = &self.doctor {
            let summary = console_summary(
                &self.rows,
                report.available_skills,
                &report.status,
                report.problems.len(),
            );
            let total = self.rows.len().max(1);
            let runtime_value = if summary.runtime_ok { "OK" } else { "Review" };
            let cards = vec![
                MetricCard {
                    title: "Runtime",
                    value: runtime_value.to_string(),
                    detail: format!("{} problem(s)", report.problems.len()),
                    healthy: summary.runtime_ok,
                },
                MetricCard {
                    title: "Installation",
                    value: format!("{}/{}", summary.installed_count, summary.available_count),
                    detail: format!("{} missing", summary.missing_count),
                    healthy: summary.missing_count == 0,
                },
                MetricCard {
                    title: "Sources",
                    value: format!("{}/{}", summary.source_ready_count, summary.persona_count),
                    detail: "persona sources".to_string(),
                    healthy: summary.source_ready_count == summary.persona_count,
                },
                MetricCard {
                    title: "Evaluations",
                    value: format!("{}/{}", summary.evaluation_ready_count, total),
                    detail: "fidelity suites".to_string(),
                    healthy: summary.evaluation_ready_count == total,
                },
                MetricCard {
                    title: "Protocols",
                    value: format!("{}/{}", summary.protocol_ready_count, summary.persona_count),
                    detail: "protocols".to_string(),
                    healthy: summary.protocol_ready_count == summary.persona_count,
                },
                MetricCard {
                    title: "Meta-skills",
                    value: summary.meta_skill_count.to_string(),
                    detail: "workflows".to_string(),
                    healthy: true,
                },
                MetricCard {
                    title: "Attention",
                    value: summary.attention_count.to_string(),
                    detail: "needs review".to_string(),
                    healthy: summary.attention_count == 0,
                },
            ];
            Self::show_metric_cards(ui, &cards);
        } else {
            ui.label("No runtime report loaded.");
        }
    }

    fn show_evaluation_center(&mut self, ui: &mut egui::Ui) {
        let busy = self.is_busy();
        let summary = evaluation_summary(&self.rows);
        let run_coverage = self.traces.evaluation_run_coverage(summary.skill_count);
        let failure_insights = self.traces.evaluation_failure_insights();
        let failure_queue = self.traces.evaluation_failure_queue();
        let trend_summary = self.traces.evaluation_trend_summary(8);
        let decision_brief =
            EvaluationDecisionBrief::from_signals(&run_coverage, &trend_summary, &failure_insights);
        let run_history = self
            .traces
            .evaluation_run_history_filtered(8, self.run_history_filter);
        let regressions = self.traces.evaluation_regressions(8);
        Self::show_workspace_header(
            ui,
            "Evaluation Center",
            "Fidelity coverage, tradition distribution, and validation actions.",
            |ui| {
                if ui
                    .add_enabled(!busy, egui::Button::new("Run full validation"))
                    .clicked()
                {
                    self.start_full_validation();
                }
                if ui
                    .add_enabled(!busy, egui::Button::new("Run fidelity dry-run"))
                    .clicked()
                {
                    self.start_fidelity_dry_run();
                }
            },
        );

        let cards = vec![
            MetricCard {
                title: "Fidelity Cases",
                value: summary.case_count.to_string(),
                detail: format!("{} skills", summary.skill_count),
                healthy: summary.missing_suite_count == 0,
            },
            MetricCard {
                title: "Run Coverage",
                value: run_coverage.label(),
                detail: format!(
                    "{} dry-run / {} graded",
                    run_coverage.dry_run_count, run_coverage.graded_count
                ),
                healthy: summary.skill_count > 0
                    && run_coverage.run_skill_count == summary.skill_count,
            },
            MetricCard {
                title: "Ready",
                value: summary.ready_count.to_string(),
                detail: "complete".to_string(),
                healthy: summary.ready_count == summary.skill_count,
            },
            MetricCard {
                title: "Attention",
                value: summary.attention_count.to_string(),
                detail: "needs review".to_string(),
                healthy: summary.attention_count == 0,
            },
            MetricCard {
                title: "Missing",
                value: summary.missing_count.to_string(),
                detail: "not installed".to_string(),
                healthy: summary.missing_count == 0,
            },
            MetricCard {
                title: "Missing Suites",
                value: summary.missing_suite_count.to_string(),
                detail: "complete".to_string(),
                healthy: summary.missing_suite_count == 0,
            },
        ];
        Self::show_metric_cards(ui, &cards);

        ui.separator();
        self.show_evaluation_decision_brief(ui, &decision_brief);

        ui.separator();
        Self::show_evaluation_trend_summary(ui, &trend_summary);

        ui.separator();
        self.show_evaluation_regressions(ui, &regressions);

        ui.separator();
        self.show_evaluation_failure_insights(ui, &failure_insights, &failure_queue);

        ui.separator();
        self.show_evaluation_run_history(ui, &run_history);

        ui.separator();
        let mode = dense_table_mode_for_width(ui.available_width());
        if mode == TwoPaneMode::TwoColumns {
            ui.columns(2, |columns| {
                Self::show_tradition_coverage(&mut columns[0], &summary.groups);
                self.show_skill_suites(&mut columns[1]);
            });
        } else {
            Self::show_tradition_coverage(ui, &summary.groups);
            ui.separator();
            self.show_skill_suites(ui);
        }
    }

    fn show_evaluation_decision_brief(
        &mut self,
        ui: &mut egui::Ui,
        brief: &EvaluationDecisionBrief,
    ) {
        ui.heading("Decision Brief");
        let busy = self.is_busy();
        let mut decision_action = None;
        ui.horizontal_wrapped(|ui| {
            ui.colored_label(
                Self::decision_posture_color(brief.posture),
                egui::RichText::new(brief.status_label()).strong(),
            );
            ui.separator();
            ui.strong(&brief.headline);
            ui.separator();
            if ui
                .add_enabled(!busy, egui::Button::new(brief.action.label()))
                .clicked()
            {
                decision_action = Some(brief.action.clone());
            }
        });
        egui::Grid::new("evaluation-decision-brief-grid")
            .num_columns(2)
            .striped(true)
            .min_col_width(128.0)
            .show(ui, |ui| {
                ui.strong("Primary Risk");
                ui.label(&brief.primary_risk);
                ui.end_row();
                ui.strong("Evidence");
                ui.label(&brief.evidence);
                ui.end_row();
                ui.strong("Next Action");
                ui.label(&brief.recommendation);
                ui.end_row();
            });

        if let Some(action) = decision_action {
            self.start_evaluation_decision_action(action);
        }
    }

    fn show_evaluation_trend_summary(ui: &mut egui::Ui, summary: &EvaluationTrendSummary) {
        ui.heading("Trend Summary");
        let latest_regression = summary
            .latest_regression_scope
            .clone()
            .unwrap_or_else(|| "none".to_string());
        let cards = vec![
            MetricCard {
                title: "Trend Health",
                value: summary.health_label().to_string(),
                detail: format!("{} recent runs", summary.total_runs),
                healthy: summary.regressed_count == 0,
            },
            MetricCard {
                title: "Regressed",
                value: summary.regressed_count.to_string(),
                detail: latest_regression,
                healthy: summary.regressed_count == 0,
            },
            MetricCard {
                title: "Improved",
                value: summary.improved_count.to_string(),
                detail: "scopes".to_string(),
                healthy: true,
            },
            MetricCard {
                title: "Stable / New",
                value: format!("{}/{}", summary.stable_count, summary.new_count),
                detail: "scopes".to_string(),
                healthy: summary.regressed_count == 0,
            },
        ];
        Self::show_metric_cards(ui, &cards);
    }

    fn show_evaluation_regressions(
        &mut self,
        ui: &mut egui::Ui,
        regressions: &[EvaluationRegressionItem],
    ) {
        ui.heading("Regression Queue");
        if regressions.is_empty() {
            ui.small("No regressions detected in recent evaluation runs.");
            return;
        }

        let busy = self.is_busy();
        let mut action_to_rerun = None;
        let mut skill_to_open = None;
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::Grid::new("evaluation-regression-grid")
                    .num_columns(6)
                    .striped(true)
                    .min_col_width(104.0)
                    .show(ui, |ui| {
                        ui.strong("Scope");
                        ui.strong("Current");
                        ui.strong("Previous");
                        ui.strong("Failed Delta");
                        ui.strong("Pass Rate Delta");
                        ui.strong("Actions");
                        ui.end_row();

                        for item in regressions {
                            ui.label(&item.scope);
                            ui.label(format!(
                                "#{} / {} failed / {}%",
                                item.current_trace_id,
                                item.current_failed_count,
                                item.current_pass_rate
                            ));
                            ui.label(format!(
                                "#{} / {} failed / {}%",
                                item.previous_trace_id,
                                item.previous_failed_count,
                                item.previous_pass_rate
                            ));
                            ui.colored_label(
                                Self::evaluation_trend_color(EvaluationRunTrend::Regressed),
                                format!("+{}", item.failed_delta),
                            );
                            ui.colored_label(
                                Self::evaluation_trend_color(EvaluationRunTrend::Regressed),
                                format!("{} pts", item.pass_rate_delta_points),
                            );
                            ui.horizontal(|ui| {
                                if ui
                                    .add_enabled(
                                        !busy && item.action.is_some(),
                                        egui::Button::new("Rerun"),
                                    )
                                    .clicked()
                                {
                                    action_to_rerun = item.action.clone();
                                }
                                if let Some(slug) =
                                    item.scope.strip_prefix("master-").map(str::to_string)
                                {
                                    if ui.button("Open").clicked() {
                                        skill_to_open = Some(slug);
                                    }
                                }
                            });
                            ui.end_row();
                        }
                    });
            });

        if let Some(action) = action_to_rerun {
            self.start_trace_action(action);
        }
        if let Some(slug) = skill_to_open {
            self.console_section = ConsoleSection::SkillDetail;
            self.start_inspect(slug);
        }
    }

    fn show_evaluation_failure_insights(
        &mut self,
        ui: &mut egui::Ui,
        insights: &EvaluationFailureInsights,
        failure_queue: &[EvaluationFailureItem],
    ) {
        ui.heading("Failure Insights");
        let top_failure_value = insights
            .top_failure_skill_slug
            .as_ref()
            .map(|slug| slug.as_str())
            .unwrap_or("none")
            .to_string();
        let cards = vec![
            MetricCard {
                title: "Failed Cases",
                value: insights.failed_cases.to_string(),
                detail: format!("{} latest cases", insights.total_cases),
                healthy: insights.failed_cases == 0,
            },
            MetricCard {
                title: "Pass Rate",
                value: insights.pass_rate_label(),
                detail: format!(
                    "{} graded / {} dry-run",
                    insights.graded_cases(),
                    insights.dry_run_cases
                ),
                healthy: insights.failed_cases == 0,
            },
            MetricCard {
                title: "Failing Skills",
                value: insights.failing_skill_count.to_string(),
                detail: "latest results".to_string(),
                healthy: insights.failing_skill_count == 0,
            },
            MetricCard {
                title: "Top Failure",
                value: top_failure_value,
                detail: format!("{} failed case(s)", insights.top_failure_skill_count),
                healthy: insights.top_failure_skill_count == 0,
            },
        ];
        Self::show_metric_cards(ui, &cards);

        if insights.total_cases == 0 {
            ui.small("Run a fidelity dry-run with JSON output to populate case-level insights.");
            return;
        }

        egui::Grid::new("evaluation-failure-insight-grid")
            .num_columns(5)
            .striped(true)
            .min_col_width(112.0)
            .show(ui, |ui| {
                ui.strong("Missing cites");
                ui.strong("Missing mentions");
                ui.strong("Forbidden");
                ui.strong("Boundary");
                ui.strong("Fabricated cites");
                ui.end_row();
                ui.label(insights.missing_cites_count.to_string());
                ui.label(insights.missing_mentions_count.to_string());
                ui.label(insights.forbidden_found_count.to_string());
                ui.label(insights.boundary_violations_count.to_string());
                ui.label(insights.fabricated_cites_count.to_string());
                ui.end_row();
            });

        ui.separator();
        self.show_evaluation_failure_queue(ui, failure_queue);
    }

    fn show_evaluation_failure_queue(
        &mut self,
        ui: &mut egui::Ui,
        failure_queue: &[EvaluationFailureItem],
    ) {
        ui.heading("Failure Queue");
        if failure_queue.is_empty() {
            ui.small("No failing cases in the latest case-level evaluation results.");
            return;
        }

        let busy = self.is_busy();
        let mut skill_to_open = None;
        let mut skill_to_run = None;
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .max_height(220.0)
                    .show(ui, |ui| {
                        egui::Grid::new("evaluation-failure-queue-grid")
                            .num_columns(7)
                            .striped(true)
                            .min_col_width(92.0)
                            .show(ui, |ui| {
                                ui.strong("Skill");
                                ui.strong("Priority");
                                ui.strong("Case");
                                ui.strong("Status");
                                ui.strong("Question");
                                ui.strong("Evidence");
                                ui.strong("Actions");
                                ui.end_row();

                                for item in failure_queue {
                                    ui.label(format!("master-{}", item.slug));
                                    ui.colored_label(
                                        Self::failure_priority_color(item.priority),
                                        item.priority.label(),
                                    );
                                    ui.label(format!("#{}", item.case_index));
                                    ui.label(&item.status);
                                    ui.label(&item.question);
                                    ui.label(&item.failure_summary);
                                    ui.horizontal(|ui| {
                                        if ui.button("Open").clicked() {
                                            skill_to_open = Some(item.slug.clone());
                                        }
                                        if ui.add_enabled(!busy, egui::Button::new("Run")).clicked()
                                        {
                                            skill_to_run = Some(item.slug.clone());
                                        }
                                    });
                                    ui.end_row();
                                }
                            });
                    });
            });

        if let Some(slug) = skill_to_open {
            self.console_section = ConsoleSection::SkillDetail;
            self.start_inspect(slug);
        }
        if let Some(slug) = skill_to_run {
            self.start_skill_fidelity_dry_run(slug);
        }
    }

    fn show_evaluation_run_history(
        &mut self,
        ui: &mut egui::Ui,
        run_history: &[EvaluationRunHistoryItem],
    ) {
        ui.heading("Run History");
        ui.horizontal_wrapped(|ui| {
            ui.label("Filter");
            for filter in [
                EvaluationRunHistoryFilter::All,
                EvaluationRunHistoryFilter::Regressed,
                EvaluationRunHistoryFilter::Improved,
                EvaluationRunHistoryFilter::Stable,
                EvaluationRunHistoryFilter::New,
                EvaluationRunHistoryFilter::Failed,
            ] {
                ui.selectable_value(&mut self.run_history_filter, filter, filter.label());
            }
        });
        if run_history.is_empty() {
            ui.small("No evaluation runs match the current filter.");
            return;
        }

        let busy = self.is_busy();
        let mut action_to_rerun = None;
        let mut skill_to_open = None;
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .max_height(180.0)
                    .show(ui, |ui| {
                        egui::Grid::new("evaluation-run-history-grid")
                            .num_columns(9)
                            .striped(true)
                            .min_col_width(92.0)
                            .show(ui, |ui| {
                                ui.strong("Trace");
                                ui.strong("Scope");
                                ui.strong("Status");
                                ui.strong("Result");
                                ui.strong("Failed");
                                ui.strong("Trend");
                                ui.strong("Mode");
                                ui.strong("Duration");
                                ui.strong("Actions");
                                ui.end_row();

                                for item in run_history {
                                    ui.label(format!("#{}", item.trace_id));
                                    ui.label(&item.scope);
                                    ui.colored_label(
                                        Self::trace_color(item.status),
                                        item.status.label(),
                                    );
                                    ui.label(item.result_label());
                                    ui.label(item.failed_count.to_string());
                                    ui.colored_label(
                                        Self::evaluation_trend_color(item.trend),
                                        item.trend.label(),
                                    );
                                    ui.label(if item.dry_run { "dry-run" } else { "graded" });
                                    ui.label(
                                        item.duration_ms
                                            .map(|duration| format!("{duration} ms"))
                                            .unwrap_or_else(|| "running".to_string()),
                                    );
                                    ui.horizontal(|ui| {
                                        if ui
                                            .add_enabled(
                                                !busy && item.action.is_some(),
                                                egui::Button::new("Rerun"),
                                            )
                                            .clicked()
                                        {
                                            action_to_rerun = item.action.clone();
                                        }
                                        if let Some(slug) =
                                            item.scope.strip_prefix("master-").map(str::to_string)
                                        {
                                            if ui.button("Open").clicked() {
                                                skill_to_open = Some(slug);
                                            }
                                        }
                                    });
                                    ui.end_row();
                                }
                            });
                    });
            });

        if let Some(action) = action_to_rerun {
            self.start_trace_action(action);
        }
        if let Some(slug) = skill_to_open {
            self.console_section = ConsoleSection::SkillDetail;
            self.start_inspect(slug);
        }
    }

    fn show_tradition_coverage(ui: &mut egui::Ui, groups: &[crate::catalog::EvaluationGroup]) {
        ui.heading("Tradition Coverage");
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::Grid::new("evaluation-tradition-grid")
                    .num_columns(4)
                    .striped(true)
                    .min_col_width(96.0)
                    .show(ui, |ui| {
                        ui.strong("Tradition");
                        ui.strong("Skills");
                        ui.strong("Cases");
                        ui.strong("Missing");
                        ui.end_row();
                        for group in groups {
                            ui.label(&group.tradition);
                            ui.label(group.skill_count.to_string());
                            ui.label(group.case_count.to_string());
                            ui.label(group.missing_suite_count.to_string());
                            ui.end_row();
                        }
                    });
            });
    }

    fn show_skill_suites(&mut self, ui: &mut egui::Ui) {
        ui.heading("Skill Suites");
        let latest_results: BTreeMap<_, _> = self
            .traces
            .latest_evaluation_results_by_slug()
            .into_iter()
            .map(|result| (result.slug.clone(), result))
            .collect();
        ui.horizontal_wrapped(|ui| {
            ui.label("Filter");
            for filter in [
                SuiteFilter::All,
                SuiteFilter::Ready,
                SuiteFilter::Attention,
                SuiteFilter::Missing,
                SuiteFilter::NotRun,
                SuiteFilter::FailedRun,
            ] {
                ui.selectable_value(&mut self.suite_filter, filter, filter.label());
            }
        });
        ui.add(
            egui::TextEdit::singleline(&mut self.suite_query)
                .hint_text("Search suites by skill, tradition, school, description, or gap"),
        );
        let rows: Vec<_> = self
            .rows
            .clone()
            .into_iter()
            .filter(|row| {
                suite_matches_filter(row, latest_results.get(&row.slug), self.suite_filter)
                    && suite_matches_query(row, &self.suite_query)
            })
            .collect();
        if rows.is_empty() {
            ui.small("No skill suites match the current filter.");
            return;
        }
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .max_height(260.0)
                    .show(ui, |ui| {
                        egui::Grid::new("evaluation-skill-grid")
                            .num_columns(7)
                            .striped(true)
                            .min_col_width(104.0)
                            .show(ui, |ui| {
                                ui.strong("Skill");
                                ui.strong("Tradition");
                                ui.strong("Kind");
                                ui.strong("Cases");
                                ui.strong("Last Run");
                                ui.strong("Status");
                                ui.strong("Gaps");
                                ui.end_row();
                                for row in rows {
                                    let level = row.quality_level();
                                    if ui.selectable_label(false, &row.name).clicked() {
                                        self.console_section = ConsoleSection::SkillDetail;
                                        self.start_inspect(row.slug.clone());
                                    }
                                    ui.label(row.tradition.as_deref().unwrap_or("unspecified"));
                                    ui.label(row.kind.label());
                                    ui.label(row.fidelity_case_count.to_string());
                                    ui.label(
                                        latest_results
                                            .get(&row.slug)
                                            .map(|result| result.label())
                                            .unwrap_or_else(|| "not run".to_string()),
                                    );
                                    ui.colored_label(Self::quality_color(level), level.label());
                                    ui.label(row.diagnostic_summary());
                                    ui.end_row();
                                }
                            });
                    });
            });
    }

    fn show_trace_center(&mut self, ui: &mut egui::Ui) {
        let summary = self.traces.summary();
        let failure_queue = self.traces.trace_failure_queue(6);
        let can_clear = summary.total > 0 && summary.running == 0;
        Self::show_workspace_header(
            ui,
            "Run Trace Center",
            "Recent desktop operations, durations, and failure summaries.",
            |ui| {
                if ui
                    .add_enabled(can_clear, egui::Button::new("Clear traces"))
                    .clicked()
                {
                    self.traces.clear();
                    self.persist_traces();
                    self.set_log("Run trace history cleared.");
                }
            },
        );
        let cards = vec![
            MetricCard {
                title: "Traces",
                value: summary.total.to_string(),
                detail: "recent ops".to_string(),
                healthy: summary.failed == 0,
            },
            MetricCard {
                title: "Running",
                value: summary.running.to_string(),
                detail: "active task".to_string(),
                healthy: summary.running <= 1,
            },
            MetricCard {
                title: "Succeeded",
                value: summary.succeeded.to_string(),
                detail: "completed".to_string(),
                healthy: true,
            },
            MetricCard {
                title: "Failed",
                value: summary.failed.to_string(),
                detail: "needs review".to_string(),
                healthy: summary.failed == 0,
            },
            MetricCard {
                title: "Last",
                value: summary
                    .last_status
                    .map(TraceStatus::label)
                    .unwrap_or("none")
                    .to_string(),
                detail: "latest".to_string(),
                healthy: summary.last_status != Some(TraceStatus::Failed),
            },
        ];
        Self::show_metric_cards(ui, &cards);

        ui.separator();
        self.show_trace_failure_queue(ui, &failure_queue);

        ui.separator();
        ui.horizontal_wrapped(|ui| {
            ui.label("Filter");
            for filter in [
                TraceListFilter::All,
                TraceListFilter::Running,
                TraceListFilter::Succeeded,
                TraceListFilter::Failed,
                TraceListFilter::Evaluation,
                TraceListFilter::Install,
            ] {
                ui.selectable_value(&mut self.trace_filter, filter, filter.label());
            }
        });
        ui.add(
            egui::TextEdit::singleline(&mut self.trace_query)
                .hint_text("Search traces by operation, command, summary, detail, or skill"),
        );

        let recent = self
            .traces
            .recent_matching(self.trace_filter, &self.trace_query);
        if recent.is_empty() {
            ui.label("No traces match the current filter.");
            return;
        }

        let busy = self.is_busy();
        let mut action_to_rerun = None;
        let mut skill_to_open = None;

        egui::ScrollArea::vertical()
            .max_height(320.0)
            .show(ui, |ui| {
                for record in recent {
                    let duration = record
                        .duration_ms
                        .map(|duration| format!("{duration} ms"))
                        .unwrap_or_else(|| "running".to_string());
                    let header = format!(
                        "#{}  {}  {}  {}",
                        record.id,
                        record.status.label(),
                        duration,
                        record.label
                    );
                    egui::CollapsingHeader::new(header)
                        .default_open(record.status == TraceStatus::Failed)
                        .show(ui, |ui| {
                            egui::Grid::new(format!("trace-detail-grid-{}", record.id))
                                .num_columns(2)
                                .striped(true)
                                .show(ui, |ui| {
                                    ui.label("Status");
                                    ui.colored_label(
                                        Self::trace_color(record.status),
                                        record.status.label(),
                                    );
                                    ui.end_row();
                                    ui.label("Duration");
                                    ui.label(&duration);
                                    ui.end_row();
                                    ui.label("Operation");
                                    ui.label(&record.label);
                                    ui.end_row();
                                    ui.label("Summary");
                                    ui.label(first_line(&record.summary));
                                    ui.end_row();
                                    ui.label("Issue");
                                    if let Some(kind) = record.failure_kind() {
                                        ui.colored_label(
                                            Self::trace_color(TraceStatus::Failed),
                                            kind.label(),
                                        );
                                    } else {
                                        ui.label("none");
                                    }
                                    ui.end_row();
                                    ui.label("Command");
                                    if let Some(command) = &record.command {
                                        ui.monospace(command);
                                    } else {
                                        ui.label("internal");
                                    }
                                    ui.end_row();
                                });
                            ui.horizontal(|ui| {
                                if ui
                                    .add_enabled(
                                        !busy && record.can_rerun(),
                                        egui::Button::new("Rerun"),
                                    )
                                    .clicked()
                                {
                                    action_to_rerun = record.action.clone();
                                }
                                if let Some(slug) = record.related_skill_slug() {
                                    if ui.button("Open Skill").clicked() {
                                        skill_to_open = Some(slug.to_string());
                                    }
                                }
                            });
                            ui.separator();
                            ui.label("Detail");
                            let detail = if record.detail.trim().is_empty() {
                                &record.summary
                            } else {
                                &record.detail
                            };
                            egui::ScrollArea::vertical()
                                .max_height(160.0)
                                .show(ui, |ui| {
                                    ui.monospace(detail);
                                });
                        });
                    ui.separator();
                }
            });
        if let Some(action) = action_to_rerun {
            self.start_trace_action(action);
        }
        if let Some(slug) = skill_to_open {
            self.console_section = ConsoleSection::SkillDetail;
            self.start_inspect(slug);
        }
    }

    fn show_trace_failure_queue(&mut self, ui: &mut egui::Ui, failure_queue: &[TraceFailureItem]) {
        ui.heading("Failure Queue");
        if failure_queue.is_empty() {
            ui.small("No failed traces require recovery.");
            return;
        }

        let busy = self.is_busy();
        let mut action_to_rerun = None;
        let mut skill_to_open = None;
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .max_height(180.0)
                    .show(ui, |ui| {
                        egui::Grid::new("trace-failure-queue-grid")
                            .num_columns(6)
                            .striped(true)
                            .min_col_width(96.0)
                            .show(ui, |ui| {
                                ui.strong("Trace");
                                ui.strong("Issue");
                                ui.strong("Operation");
                                ui.strong("Summary");
                                ui.strong("Duration");
                                ui.strong("Actions");
                                ui.end_row();

                                for item in failure_queue {
                                    ui.label(format!("#{}", item.trace_id));
                                    ui.colored_label(
                                        Self::trace_color(TraceStatus::Failed),
                                        item.kind.label(),
                                    );
                                    ui.label(&item.label);
                                    ui.label(first_line(&item.summary));
                                    ui.label(
                                        item.duration_ms
                                            .map(|duration| format!("{duration} ms"))
                                            .unwrap_or_else(|| "running".to_string()),
                                    );
                                    ui.horizontal(|ui| {
                                        if ui
                                            .add_enabled(
                                                !busy && item.action.is_some(),
                                                egui::Button::new("Rerun"),
                                            )
                                            .clicked()
                                        {
                                            action_to_rerun = item.action.clone();
                                        }
                                        if let Some(slug) = &item.related_skill_slug {
                                            if ui.button("Open Skill").clicked() {
                                                skill_to_open = Some(slug.clone());
                                            }
                                        }
                                    });
                                    ui.end_row();
                                }
                            });
                    });
            });

        if let Some(action) = action_to_rerun {
            self.start_trace_action(action);
        }
        if let Some(slug) = skill_to_open {
            self.console_section = ConsoleSection::SkillDetail;
            self.start_inspect(slug);
        }
    }

    fn show_sidebar(&mut self, ui: &mut egui::Ui) {
        let ready_count = self
            .rows
            .iter()
            .filter(|row| row.quality_level() == QualityLevel::Ready)
            .count();
        ui.horizontal(|ui| {
            ui.heading("Skills");
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.small(format!("{ready_count}/{} ready", self.rows.len()));
            });
        });
        ui.add(
            egui::TextEdit::singleline(&mut self.search_query)
                .hint_text("Search name, slug, tradition, school"),
        );

        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.install_filter, InstallFilter::All, "All");
            ui.selectable_value(
                &mut self.install_filter,
                InstallFilter::Installed,
                "Installed",
            );
            ui.selectable_value(&mut self.install_filter, InstallFilter::Missing, "Missing");
        });

        egui::ComboBox::from_label("Tradition")
            .selected_text(self.tradition_filter.as_deref().unwrap_or("All traditions"))
            .show_ui(ui, |ui| {
                ui.selectable_value(&mut self.tradition_filter, None, "All traditions");
                for tradition in tradition_options(&self.rows) {
                    ui.selectable_value(
                        &mut self.tradition_filter,
                        Some(tradition.clone()),
                        tradition,
                    );
                }
            });

        ui.separator();
        let visible_rows: Vec<SkillRow> = filter_rows(
            &self.rows,
            &self.search_query,
            self.install_filter,
            self.tradition_filter.as_deref(),
        )
        .into_iter()
        .cloned()
        .collect();

        egui::ScrollArea::vertical().show(ui, |ui| {
            for row in visible_rows {
                let selected = self.selected_slug.as_deref() == Some(row.slug.as_str());
                let quality = row.quality_level();
                let title = row.title().to_string();
                ui.allocate_ui_with_layout(
                    egui::vec2(ui.available_width(), sidebar_row_height()),
                    egui::Layout::left_to_right(egui::Align::Center),
                    |ui| {
                        let name_width =
                            (ui.available_width() - status_badge_width() - 10.0).max(80.0);
                        let name = egui::RichText::new(row.name.clone()).size(13.0);
                        if ui
                            .add_sized(
                                egui::vec2(name_width, sidebar_row_height()),
                                egui::SelectableLabel::new(selected, name),
                            )
                            .clicked()
                        {
                            self.console_section = ConsoleSection::SkillDetail;
                            self.start_inspect(row.slug.clone());
                        }
                        Self::show_quality_badge(ui, quality);
                    },
                );
                if selected && title != row.name {
                    ui.small(title);
                }
            }
        });
    }

    fn show_doctor(&self, ui: &mut egui::Ui) {
        ui.heading("Environment");
        if let Some(report) = &self.doctor {
            egui::Grid::new("doctor-grid")
                .num_columns(2)
                .show(ui, |ui| {
                    ui.label("Status");
                    ui.label(&report.status);
                    ui.end_row();
                    ui.label("Package");
                    ui.label(&report.package_version);
                    ui.end_row();
                    ui.label("Node");
                    ui.label(&report.node_version);
                    ui.end_row();
                    ui.label("Available");
                    ui.label(report.available_skills.to_string());
                    ui.end_row();
                    ui.label("Installed");
                    ui.label(report.installed_known_skills.to_string());
                    ui.end_row();
                    ui.label("Skills path");
                    ui.label(&report.skills_path);
                    ui.end_row();
                    ui.label("Other skill dirs");
                    ui.label(report.other_installed_skill_dirs.to_string());
                    ui.end_row();
                    ui.label("Prebuilt path");
                    ui.label(&report.prebuilt_path);
                    ui.end_row();
                });

            if !report.problems.is_empty() {
                ui.separator();
                ui.heading("Problems");
                for problem in &report.problems {
                    ui.label(&problem.message);
                }
            }
        } else {
            ui.label("No runtime report loaded.");
        }
    }

    fn show_identity_panel(ui: &mut egui::Ui, master: &MasterInspect, kind: &str) {
        ui.heading("Identity");
        egui::Grid::new(format!("identity-grid-{}", master.slug))
            .num_columns(2)
            .show(ui, |ui| {
                ui.label("Slug");
                ui.label(&master.slug);
                ui.end_row();
                ui.label("Type");
                ui.label(kind);
                ui.end_row();
                ui.label("Version");
                ui.label(master.version.as_deref().unwrap_or("unknown"));
                ui.end_row();
                ui.label("Tradition");
                ui.label(master.tradition.as_deref().unwrap_or("unspecified"));
                ui.end_row();
                ui.label("School");
                ui.label(master.school.as_deref().unwrap_or("unspecified"));
                ui.end_row();
                ui.label("Era");
                ui.label(master.era.as_deref().unwrap_or("unspecified"));
                ui.end_row();
            });
        ui.separator();
    }

    fn show_source_contract_panel(ui: &mut egui::Ui, master: &MasterInspect, source_index: bool) {
        ui.heading("Source Contract");
        egui::Grid::new(format!("source-contract-grid-{}", master.slug))
            .num_columns(2)
            .show(ui, |ui| {
                ui.label("Declared sources");
                ui.label(master.sources.len().to_string());
                ui.end_row();
                ui.label("Source index");
                ui.label(if source_index { "present" } else { "missing" });
                ui.end_row();
                ui.label("Citation format");
                ui.label(master.citation_format.as_deref().unwrap_or("not declared"));
                ui.end_row();
            });
        if !master.sources.is_empty() {
            ui.separator();
            for source in &master.sources {
                ui.small(source);
            }
        }
        ui.separator();
    }

    fn show_evaluation_contract_panel(
        ui: &mut egui::Ui,
        fidelity_count: usize,
        quality: QualityLevel,
        diagnostic_summary: &str,
    ) {
        ui.heading("Evaluation Contract");
        egui::Grid::new("evaluation-contract-grid")
            .num_columns(2)
            .show(ui, |ui| {
                ui.label("Fidelity cases");
                ui.label(fidelity_count.to_string());
                ui.end_row();
                ui.label("Quality status");
                ui.colored_label(Self::quality_color(quality), quality.label());
                ui.end_row();
                ui.label("Gaps");
                ui.label(diagnostic_summary);
                ui.end_row();
            });
        ui.separator();
    }

    fn show_fidelity_cases_panel(&mut self, ui: &mut egui::Ui, slug: &str, cases: &[FidelityCase]) {
        ui.heading("Fidelity Cases");
        let latest_result = self.traces.latest_evaluation_result_for(slug);
        let case_results: BTreeMap<usize, _> = self
            .traces
            .latest_evaluation_case_results_for(slug)
            .into_iter()
            .map(|result| (result.case_index, result))
            .collect();
        ui.horizontal(|ui| {
            ui.label(format!("{} cases", cases.len()));
            ui.separator();
            if let Some(result) = &latest_result {
                ui.label(format!("Latest: {}", result.label()));
                ui.separator();
            } else {
                ui.label("Latest: not run");
                ui.separator();
            }
            if ui
                .add_enabled(
                    !self.is_busy() && !cases.is_empty(),
                    egui::Button::new("Run skill dry-run"),
                )
                .clicked()
            {
                self.start_skill_fidelity_dry_run(slug.to_string());
            }
        });

        if cases.is_empty() {
            ui.label("No fidelity cases detected.");
            ui.separator();
            return;
        }

        egui::ScrollArea::vertical()
            .max_height(220.0)
            .show(ui, |ui| {
                egui::Grid::new(format!("fidelity-case-grid-{slug}"))
                    .num_columns(7)
                    .striped(true)
                    .min_col_width(72.0)
                    .show(ui, |ui| {
                        ui.strong("#");
                        ui.strong("Difficulty");
                        ui.strong("Cites");
                        ui.strong("Keywords");
                        ui.strong("Last Result");
                        ui.strong("Evidence");
                        ui.strong("Prompt");
                        ui.end_row();
                        for case in cases {
                            ui.label(case.index.to_string());
                            ui.label(case.difficulty.as_deref().unwrap_or("unspecified"));
                            ui.label(case.citation_assertion_count.to_string());
                            ui.label(case.keyword_assertion_count.to_string());
                            if let Some(result) = case_results.get(&case.index) {
                                ui.label(result.status.as_str());
                                ui.label(result.failure_summary());
                            } else {
                                ui.label(
                                    latest_result
                                        .as_ref()
                                        .map(|result| {
                                            if result.dry_run {
                                                "N/A dry-run".to_string()
                                            } else {
                                                result.label()
                                            }
                                        })
                                        .unwrap_or_else(|| "not run".to_string()),
                                );
                                ui.label("not run");
                            }
                            ui.label(first_line(&case.question));
                            ui.end_row();
                        }
                    });
            });
        ui.separator();
    }

    fn show_recommended_actions_panel(&mut self, ui: &mut egui::Ui, actions: &[DiagnosticAction]) {
        ui.heading("Recommended Actions");
        if actions.is_empty() {
            ui.label("No action needed.");
            ui.separator();
            return;
        }

        let busy = self.is_busy();
        let mut operation_to_start = None;
        egui::Grid::new("recommended-actions-grid")
            .num_columns(4)
            .striped(true)
            .min_col_width(104.0)
            .show(ui, |ui| {
                ui.strong("Action");
                ui.strong("Reason");
                ui.strong("Command");
                ui.strong("Run");
                ui.end_row();
                for action in actions {
                    ui.label(&action.title);
                    ui.label(&action.detail);
                    if let Some(command) = &action.command {
                        ui.monospace(command);
                    } else {
                        ui.label("manual");
                    }
                    match &action.operation {
                        DiagnosticOperation::Manual => {
                            ui.label("manual");
                        }
                        operation => {
                            if ui.add_enabled(!busy, egui::Button::new("Run")).clicked() {
                                operation_to_start = Some(operation.clone());
                            }
                        }
                    }
                    ui.end_row();
                }
            });
        if let Some(operation) = operation_to_start {
            self.start_diagnostic_operation(operation);
        }
        ui.separator();
    }

    fn show_runtime_protocol_panel(ui: &mut egui::Ui, master: &MasterInspect) {
        ui.heading("Runtime Protocol");
        egui::Grid::new(format!("runtime-protocol-grid-{}", master.slug))
            .num_columns(2)
            .show(ui, |ui| {
                ui.label("Installed");
                ui.label(if master.installed { "yes" } else { "no" });
                ui.end_row();
                ui.label("Live grounding");
                ui.label(if master.live_grounding { "yes" } else { "no" });
                ui.end_row();
                ui.label("Keywords");
                ui.label(master.search_keywords.len().to_string());
                ui.end_row();
            });
        if !master.search_keywords.is_empty() {
            ui.separator();
            ui.label(master.search_keywords.join(", "));
        }
        ui.separator();
    }

    fn show_selected(&mut self, ui: &mut egui::Ui, show_workspace_header: bool) {
        if show_workspace_header {
            Self::show_workspace_header(
                ui,
                "Skill Detail",
                "Source metadata, evaluation status, installation state, and runtime protocol.",
                |_| {},
            );
        }
        ui.heading("Selected Skill");
        if let Some(master) = self.selected.clone() {
            let selected_row = self
                .rows
                .iter()
                .find(|row| row.slug == master.slug)
                .cloned();
            let quality = selected_row
                .as_ref()
                .map(SkillRow::quality_level)
                .unwrap_or(QualityLevel::Missing);
            let source_index = selected_row
                .as_ref()
                .map(|row| row.source_index_present)
                .unwrap_or(false);
            let fidelity_count = selected_row
                .as_ref()
                .map(|row| row.fidelity_case_count)
                .unwrap_or_default();
            let fidelity_cases = selected_row
                .as_ref()
                .map(|row| row.fidelity_cases.clone())
                .unwrap_or_default();
            let kind = selected_row
                .as_ref()
                .map(|row| row.kind.label())
                .unwrap_or("unknown");
            let diagnostic_summary = selected_row
                .as_ref()
                .map(SkillRow::diagnostic_summary)
                .unwrap_or_else(|| "not loaded".to_string());
            let diagnostic_actions = selected_row
                .as_ref()
                .map(SkillRow::diagnostic_actions)
                .unwrap_or_default();

            ui.label(master.display_name.as_deref().unwrap_or(&master.name));
            ui.horizontal(|ui| {
                Self::show_quality_badge(ui, quality);
                ui.separator();
                if master.installed {
                    if ui
                        .add_enabled(!self.is_busy(), egui::Button::new("Uninstall"))
                        .clicked()
                    {
                        self.start_uninstall(master.slug.clone());
                    }
                } else if ui
                    .add_enabled(!self.is_busy(), egui::Button::new("Install"))
                    .clicked()
                {
                    self.start_install(master.slug.clone());
                }
            });

            ui.separator();

            let two_columns =
                dashboard_columns_for_width(ui.available_width()) == TwoPaneMode::TwoColumns;
            if two_columns {
                ui.columns(2, |columns| {
                    Self::show_identity_panel(&mut columns[0], &master, kind);
                    Self::show_source_contract_panel(&mut columns[0], &master, source_index);
                    Self::show_evaluation_contract_panel(
                        &mut columns[1],
                        fidelity_count,
                        quality,
                        &diagnostic_summary,
                    );
                    self.show_fidelity_cases_panel(&mut columns[1], &master.slug, &fidelity_cases);
                    self.show_recommended_actions_panel(&mut columns[1], &diagnostic_actions);
                    Self::show_runtime_protocol_panel(&mut columns[1], &master);
                });
            } else {
                Self::show_identity_panel(ui, &master, kind);
                Self::show_source_contract_panel(ui, &master, source_index);
                Self::show_evaluation_contract_panel(
                    ui,
                    fidelity_count,
                    quality,
                    &diagnostic_summary,
                );
                self.show_fidelity_cases_panel(ui, &master.slug, &fidelity_cases);
                self.show_recommended_actions_panel(ui, &diagnostic_actions);
                Self::show_runtime_protocol_panel(ui, &master);
            }
        } else {
            ui.label("No skill selected.");
        }
    }

    fn show_operation_log(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading("Operation Log");
            let toggle_label = if self.log_expanded {
                "Collapse"
            } else {
                "Expand"
            };
            if ui.button(toggle_label).clicked() {
                self.log_expanded = !self.log_expanded;
            }
            if ui.button("Clear").clicked() {
                self.log_lines.clear();
            }
            ui.separator();
            ui.label(first_line(&self.log));
        });

        if self.log_expanded {
            egui::ScrollArea::vertical()
                .stick_to_bottom(true)
                .show(ui, |ui| {
                    for line in &self.log_lines {
                        ui.label(line);
                    }
                });
        }
    }

    fn show_overview_workspace(&mut self, ui: &mut egui::Ui) {
        self.show_dashboard(ui);
        ui.separator();
        if dashboard_columns_for_width(ui.available_width()) == TwoPaneMode::TwoColumns {
            ui.columns(2, |columns| {
                self.show_doctor(&mut columns[0]);
                self.show_selected(&mut columns[1], false);
            });
        } else {
            self.show_doctor(ui);
            ui.separator();
            self.show_selected(ui, false);
        }
    }

    fn show_active_workspace(&mut self, ui: &mut egui::Ui) {
        match self.console_section {
            ConsoleSection::Overview => self.show_overview_workspace(ui),
            ConsoleSection::Evaluation => self.show_evaluation_center(ui),
            ConsoleSection::Runs => self.show_trace_center(ui),
            ConsoleSection::SkillDetail => self.show_selected(ui, true),
        }
    }
}

impl Default for MasterSkillApp {
    fn default() -> Self {
        Self::new()
    }
}

impl eframe::App for MasterSkillApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        apply_console_theme(ctx);
        self.poll_task();
        if self.is_busy() {
            ctx.request_repaint();
        }

        egui::TopBottomPanel::top("top").show(ctx, |ui| self.show_toolbar(ui));

        egui::SidePanel::left("skills")
            .resizable(true)
            .default_width(sidebar_default_width())
            .show(ctx, |ui| self.show_sidebar(ui));

        egui::TopBottomPanel::bottom("log")
            .resizable(true)
            .default_height(operation_log_height(self.log_expanded))
            .show(ctx, |ui| self.show_operation_log(ui));

        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                self.show_active_workspace(ui);
            });
        });
    }
}

fn summarize_command_output(prefix: &str, output: &str) -> String {
    let lines: Vec<&str> = output
        .lines()
        .filter(|line| !line.trim().is_empty())
        .collect();
    if lines.is_empty() {
        return prefix.to_string();
    }

    let start = lines.len().saturating_sub(12);
    format!("{prefix}:\n{}", lines[start..].join("\n"))
}

fn first_line(value: &str) -> String {
    value
        .lines()
        .find(|line| !line.trim().is_empty())
        .map(str::trim)
        .unwrap_or("")
        .to_string()
}

fn desktop_trace_store_path() -> PathBuf {
    desktop_trace_store_path_from_env(
        std::env::var("XDG_DATA_HOME").ok().as_deref(),
        std::env::var("HOME").ok().as_deref(),
        std::env::var("APPDATA").ok().as_deref(),
    )
    .unwrap_or_else(|| {
        std::env::temp_dir()
            .join("master-skill")
            .join("desktop-traces.json")
    })
}

fn desktop_trace_store_path_from_env(
    xdg_data_home: Option<&str>,
    home: Option<&str>,
    appdata: Option<&str>,
) -> Option<PathBuf> {
    if let Some(path) = xdg_data_home.filter(|value| !value.trim().is_empty()) {
        return Some(
            PathBuf::from(path)
                .join("master-skill")
                .join("desktop-traces.json"),
        );
    }

    if let Some(path) = appdata.filter(|value| !value.trim().is_empty()) {
        return Some(
            PathBuf::from(path)
                .join("Master-skill")
                .join("desktop-traces.json"),
        );
    }

    home.filter(|value| !value.trim().is_empty()).map(|path| {
        PathBuf::from(path)
            .join(".local")
            .join("share")
            .join("master-skill")
            .join("desktop-traces.json")
    })
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use crate::catalog::{SkillKind, SkillRow};
    use crate::trace::EvaluationRunResult;

    #[test]
    fn trace_store_path_prefers_xdg_data_home() {
        let path = super::desktop_trace_store_path_from_env(
            Some("/tmp/xdg-data"),
            Some("/home/user"),
            None,
        )
        .unwrap();

        assert_eq!(
            path,
            PathBuf::from("/tmp/xdg-data")
                .join("master-skill")
                .join("desktop-traces.json")
        );
    }

    #[test]
    fn filters_skill_suites_by_quality_and_latest_run_state() {
        let ready = suite_row("huineng", true, true, 12);
        let attention = suite_row("zhiyi", true, false, 10);
        let missing = suite_row("xuyun", false, true, 10);
        let passing_run = EvaluationRunResult {
            slug: "huineng".to_string(),
            passed_count: 12,
            total_count: 12,
            dry_run: false,
            trace_id: 1,
        };
        let failed_run = EvaluationRunResult {
            slug: "zhiyi".to_string(),
            passed_count: 8,
            total_count: 10,
            dry_run: false,
            trace_id: 2,
        };

        assert!(super::suite_matches_filter(
            &ready,
            Some(&passing_run),
            super::SuiteFilter::Ready
        ));
        assert!(super::suite_matches_filter(
            &attention,
            Some(&failed_run),
            super::SuiteFilter::Attention
        ));
        assert!(super::suite_matches_filter(
            &missing,
            None,
            super::SuiteFilter::Missing
        ));
        assert!(super::suite_matches_filter(
            &missing,
            None,
            super::SuiteFilter::NotRun
        ));
        assert!(super::suite_matches_filter(
            &attention,
            Some(&failed_run),
            super::SuiteFilter::FailedRun
        ));
        assert!(!super::suite_matches_filter(
            &ready,
            Some(&passing_run),
            super::SuiteFilter::FailedRun
        ));
    }

    #[test]
    fn searches_skill_suites_across_metadata_and_gaps() {
        let ready = suite_row("huineng", true, true, 12);
        let attention = suite_row("zhiyi", true, false, 10);

        assert!(super::suite_matches_query(&ready, "HUINENG"));
        assert!(super::suite_matches_query(&ready, "chan"));
        assert!(super::suite_matches_query(&ready, "test row"));
        assert!(super::suite_matches_query(&attention, "source index"));
        assert!(super::suite_matches_query(&attention, "citation format"));
        assert!(super::suite_matches_query(&attention, "   "));
        assert!(!super::suite_matches_query(&ready, "missing source index"));
    }

    fn suite_row(
        slug: &str,
        installed: bool,
        complete_contract: bool,
        case_count: usize,
    ) -> SkillRow {
        SkillRow {
            name: format!("master-{slug}"),
            slug: slug.to_string(),
            description: "test row".to_string(),
            display_name: None,
            tradition: Some("Chan".to_string()),
            school: None,
            installed,
            live_grounding: complete_contract,
            source_count: usize::from(complete_contract),
            keyword_count: 1,
            has_citation_format: complete_contract,
            fidelity_case_count: case_count,
            fidelity_cases: Vec::new(),
            source_index_present: complete_contract,
            kind: SkillKind::Persona,
        }
    }
}
