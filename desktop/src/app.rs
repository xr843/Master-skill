use std::sync::mpsc::{channel, Receiver};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::Result;
use eframe::egui;

use crate::catalog::{
    console_summary, evaluation_summary, filter_rows, tradition_options, DiagnosticAction,
    DiagnosticOperation, InstallFilter, QualityLevel, SkillDiagnostics, SkillRow,
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
use crate::trace::{TraceStatus, TraceStore};

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
    traces: TraceStore,
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
            traces: TraceStore::new(200),
        };
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

    fn start_task<F>(&mut self, label: impl Into<String>, task: F)
    where
        F: FnOnce(CliClient) -> Result<TaskOutcome> + Send + 'static,
    {
        self.start_task_with_command(label, None::<String>, task);
    }

    fn start_task_with_command<F>(
        &mut self,
        label: impl Into<String>,
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
        let trace_id = self
            .traces
            .begin_with_detail(label.clone(), command, "Queued.");
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
                    self.set_log(outcome.message);
                }
                Err(message) => {
                    self.traces.finish_error_with_detail(
                        envelope.trace_id,
                        first_line(&message),
                        message.clone(),
                        envelope.elapsed,
                    );
                    self.set_log(message);
                }
            }
        }
    }

    fn start_refresh(&mut self) {
        let selected_slug = self.selected_slug.clone();
        self.start_task("Refreshing runtime data", move |client| {
            let snapshot = Self::load_snapshot(&client, selected_slug)?;
            Ok(TaskOutcome {
                message: "Runtime data refreshed.".to_string(),
                detail: "Reloaded inventory, runtime doctor report, selected skill metadata, and local diagnostics.".to_string(),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_inspect(&mut self, slug: String) {
        self.start_task(format!("Loading master-{slug}"), move |client| {
            let snapshot = Self::load_snapshot(&client, Some(slug.clone()))?;
            Ok(TaskOutcome {
                message: format!("Loaded master-{slug}."),
                detail: format!(
                    "Loaded source, evaluation, install, and runtime metadata for master-{slug}."
                ),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_install(&mut self, slug: String) {
        self.start_task_with_command(
            format!("Installing master-{slug}"),
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
        self.start_task_with_command(
            format!("Uninstalling master-{slug}"),
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
        self.start_task_with_command(
            "Installing all skills",
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
        self.start_task_with_command(
            "Updating all skills",
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
        self.start_task_with_command(
            "Running fidelity dry-run",
            Some("python3 scripts/test-fidelity.py --all --dry-run"),
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
        self.start_task_with_command(
            format!("Running master-{slug} fidelity dry-run"),
            Some(format!(
                "python3 scripts/test-fidelity.py --master master-{slug} --dry-run"
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
        self.start_task_with_command("Running full validation", Some("npm test"), move |client| {
            let output = client.run_full_validation()?;
            Ok(TaskOutcome {
                message: summarize_command_output("Full validation finished", &output),
                detail: output.trim().to_string(),
                snapshot: None,
            })
        });
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
        let rows = self.rows.clone();
        egui::ScrollArea::horizontal()
            .max_width(ui.available_width())
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .max_height(260.0)
                    .show(ui, |ui| {
                        egui::Grid::new("evaluation-skill-grid")
                            .num_columns(6)
                            .striped(true)
                            .min_col_width(104.0)
                            .show(ui, |ui| {
                                ui.strong("Skill");
                                ui.strong("Tradition");
                                ui.strong("Kind");
                                ui.strong("Cases");
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
        let recent = self.traces.recent();
        if recent.is_empty() {
            ui.label("No traces recorded yet.");
            return;
        }

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
                                    ui.label("Command");
                                    if let Some(command) = &record.command {
                                        ui.monospace(command);
                                    } else {
                                        ui.label("internal");
                                    }
                                    ui.end_row();
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
