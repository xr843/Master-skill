use std::sync::mpsc::{channel, Receiver};
use std::thread;
use std::time::{Duration, Instant};

use anyhow::Result;
use eframe::egui;

use crate::catalog::{
    console_summary, evaluation_summary, filter_rows, tradition_options, InstallFilter,
    QualityLevel, SkillDiagnostics, SkillRow,
};
use crate::cli::CliClient;
use crate::layout::{dashboard_columns_for_width, TwoPaneMode};
use crate::model::{DoctorReport, MasterInspect, SkillInventory};
use crate::trace::{TraceStatus, TraceStore};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum DetailView {
    Overview,
    Sources,
    Evaluation,
    Runtime,
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
    detail_view: DetailView,
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
    snapshot: Option<Snapshot>,
}

type TaskResult = std::result::Result<TaskOutcome, String>;

struct TaskEnvelope {
    trace_id: u64,
    elapsed: Duration,
    result: TaskResult,
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
            detail_view: DetailView::Overview,
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
        if self.is_busy() {
            self.set_log("A task is already running.");
            return;
        }

        let client = self.client.clone();
        let label = label.into();
        let trace_id = self.traces.begin(label.clone());
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
                    self.traces.finish_success(
                        envelope.trace_id,
                        outcome.message.clone(),
                        envelope.elapsed,
                    );
                    self.set_log(outcome.message);
                }
                Err(message) => {
                    self.traces
                        .finish_error(envelope.trace_id, message.clone(), envelope.elapsed);
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
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_inspect(&mut self, slug: String) {
        self.start_task(format!("Loading master-{slug}"), move |client| {
            let snapshot = Self::load_snapshot(&client, Some(slug.clone()))?;
            Ok(TaskOutcome {
                message: format!("Loaded master-{slug}."),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_install(&mut self, slug: String) {
        self.start_task(format!("Installing master-{slug}"), move |client| {
            let output = client.install(&slug)?;
            let snapshot = Self::load_snapshot(&client, Some(slug))?;
            Ok(TaskOutcome {
                message: output.trim().to_string(),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_uninstall(&mut self, slug: String) {
        self.start_task(format!("Uninstalling master-{slug}"), move |client| {
            let output = client.uninstall(&slug)?;
            let snapshot = Self::load_snapshot(&client, Some(slug))?;
            Ok(TaskOutcome {
                message: output.trim().to_string(),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_install_all(&mut self) {
        let selected_slug = self.selected_slug.clone();
        self.start_task("Installing all skills", move |client| {
            let output = client.install_all()?;
            let snapshot = Self::load_snapshot(&client, selected_slug)?;
            Ok(TaskOutcome {
                message: output.trim().to_string(),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_update_all(&mut self) {
        let selected_slug = self.selected_slug.clone();
        self.start_task("Updating all skills", move |client| {
            let output = client.update_all()?;
            let snapshot = Self::load_snapshot(&client, selected_slug)?;
            Ok(TaskOutcome {
                message: output.trim().to_string(),
                snapshot: Some(snapshot),
            })
        });
    }

    fn start_fidelity_dry_run(&mut self) {
        self.start_task("Running fidelity dry-run", move |client| {
            let output = client.run_fidelity_dry_run()?;
            Ok(TaskOutcome {
                message: summarize_command_output("Fidelity dry-run finished", &output),
                snapshot: None,
            })
        });
    }

    fn start_full_validation(&mut self) {
        self.start_task("Running full validation", move |client| {
            let output = client.run_full_validation()?;
            Ok(TaskOutcome {
                message: summarize_command_output("Full validation finished", &output),
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
        ui.label(format!("Repo: {}", self.client.repo_root().display()));
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

    fn show_metric_card(
        ui: &mut egui::Ui,
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

        egui::Frame::new()
            .fill(fill)
            .stroke(stroke)
            .inner_margin(egui::Margin::same(10))
            .show(ui, |ui| {
                ui.set_min_width(135.0);
                ui.small(title);
                ui.heading(value.into());
                ui.small(detail);
            });
    }

    fn show_dashboard(&self, ui: &mut egui::Ui) {
        ui.heading("Console Health");
        if let Some(report) = &self.doctor {
            let summary = console_summary(
                &self.rows,
                report.available_skills,
                &report.status,
                report.problems.len(),
            );
            let total = self.rows.len().max(1);
            ui.horizontal_wrapped(|ui| {
                Self::show_metric_card(
                    ui,
                    "Runtime",
                    if summary.runtime_ok { "OK" } else { "Review" },
                    &format!("{} problem(s)", report.problems.len()),
                    summary.runtime_ok,
                );
                Self::show_metric_card(
                    ui,
                    "Installation",
                    format!("{}/{}", summary.installed_count, summary.available_count),
                    &format!("{} missing", summary.missing_count),
                    summary.missing_count == 0,
                );
                Self::show_metric_card(
                    ui,
                    "Sources",
                    format!("{}/{}", summary.source_ready_count, summary.persona_count),
                    "persona source sets",
                    summary.source_ready_count == summary.persona_count,
                );
                Self::show_metric_card(
                    ui,
                    "Evaluations",
                    format!("{}/{}", summary.evaluation_ready_count, total),
                    "fidelity suites",
                    summary.evaluation_ready_count == total,
                );
                Self::show_metric_card(
                    ui,
                    "Protocols",
                    format!("{}/{}", summary.protocol_ready_count, summary.persona_count),
                    "persona grounding + citation",
                    summary.protocol_ready_count == summary.persona_count,
                );
                Self::show_metric_card(
                    ui,
                    "Meta-skills",
                    summary.meta_skill_count.to_string(),
                    "workflow skills",
                    true,
                );
                Self::show_metric_card(
                    ui,
                    "Attention",
                    summary.attention_count.to_string(),
                    "skills needing review",
                    summary.attention_count == 0,
                );
            });
        } else {
            ui.label("No runtime report loaded.");
        }
    }

    fn show_evaluation_center(&mut self, ui: &mut egui::Ui) {
        ui.heading("Evaluation Center");
        let busy = self.is_busy();
        let summary = evaluation_summary(&self.rows);

        ui.horizontal_wrapped(|ui| {
            Self::show_metric_card(
                ui,
                "Fidelity Cases",
                summary.case_count.to_string(),
                &format!("{} skills", summary.skill_count),
                summary.missing_suite_count == 0,
            );
            Self::show_metric_card(
                ui,
                "Ready",
                summary.ready_count.to_string(),
                "source + protocol + eval",
                summary.ready_count == summary.skill_count,
            );
            Self::show_metric_card(
                ui,
                "Attention",
                summary.attention_count.to_string(),
                "installed but incomplete",
                summary.attention_count == 0,
            );
            Self::show_metric_card(
                ui,
                "Missing",
                summary.missing_count.to_string(),
                "not installed",
                summary.missing_count == 0,
            );
            Self::show_metric_card(
                ui,
                "Missing Suites",
                summary.missing_suite_count.to_string(),
                "no fidelity jsonl",
                summary.missing_suite_count == 0,
            );
        });

        ui.horizontal(|ui| {
            if ui
                .add_enabled(!busy, egui::Button::new("Run fidelity dry-run"))
                .clicked()
            {
                self.start_fidelity_dry_run();
            }
            if ui
                .add_enabled(!busy, egui::Button::new("Run full validation"))
                .clicked()
            {
                self.start_full_validation();
            }
        });

        ui.separator();
        let mode = dashboard_columns_for_width(ui.available_width());
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
        egui::ScrollArea::horizontal().show(ui, |ui| {
            egui::Grid::new("evaluation-tradition-grid")
                .num_columns(4)
                .striped(true)
                .min_col_width(70.0)
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

    fn show_skill_suites(&self, ui: &mut egui::Ui) {
        ui.heading("Skill Suites");
        egui::ScrollArea::horizontal().show(ui, |ui| {
            egui::ScrollArea::vertical()
                .max_height(210.0)
                .show(ui, |ui| {
                    egui::Grid::new("evaluation-skill-grid")
                        .num_columns(5)
                        .striped(true)
                        .min_col_width(82.0)
                        .show(ui, |ui| {
                            ui.strong("Skill");
                            ui.strong("Tradition");
                            ui.strong("Kind");
                            ui.strong("Cases");
                            ui.strong("Status");
                            ui.end_row();
                            for row in &self.rows {
                                let level = row.quality_level();
                                ui.label(&row.name);
                                ui.label(row.tradition.as_deref().unwrap_or("unspecified"));
                                ui.label(row.kind.label());
                                ui.label(row.fidelity_case_count.to_string());
                                ui.colored_label(Self::quality_color(level), level.label());
                                ui.end_row();
                            }
                        });
                });
        });
    }

    fn show_trace_center(&self, ui: &mut egui::Ui) {
        ui.heading("Run Trace Center");
        let summary = self.traces.summary();
        ui.horizontal_wrapped(|ui| {
            Self::show_metric_card(
                ui,
                "Traces",
                summary.total.to_string(),
                "recent operations",
                summary.failed == 0,
            );
            Self::show_metric_card(
                ui,
                "Running",
                summary.running.to_string(),
                "active task",
                summary.running <= 1,
            );
            Self::show_metric_card(
                ui,
                "Succeeded",
                summary.succeeded.to_string(),
                "completed tasks",
                true,
            );
            Self::show_metric_card(
                ui,
                "Failed",
                summary.failed.to_string(),
                "needs review",
                summary.failed == 0,
            );
            Self::show_metric_card(
                ui,
                "Last",
                summary
                    .last_status
                    .map(TraceStatus::label)
                    .unwrap_or("none"),
                "latest operation",
                summary.last_status != Some(TraceStatus::Failed),
            );
        });

        ui.separator();
        let recent = self.traces.recent();
        if recent.is_empty() {
            ui.label("No traces recorded yet.");
            return;
        }

        egui::ScrollArea::horizontal().show(ui, |ui| {
            egui::ScrollArea::vertical()
                .max_height(190.0)
                .show(ui, |ui| {
                    egui::Grid::new("run-trace-grid")
                        .num_columns(5)
                        .striped(true)
                        .min_col_width(88.0)
                        .show(ui, |ui| {
                            ui.strong("ID");
                            ui.strong("Status");
                            ui.strong("Duration");
                            ui.strong("Operation");
                            ui.strong("Summary");
                            ui.end_row();
                            for record in recent {
                                ui.label(format!("#{}", record.id));
                                ui.colored_label(
                                    Self::trace_color(record.status),
                                    record.status.label(),
                                );
                                ui.label(
                                    record
                                        .duration_ms
                                        .map(|duration| format!("{duration} ms"))
                                        .unwrap_or_else(|| "running".to_string()),
                                );
                                ui.label(record.label);
                                ui.label(first_line(&record.summary));
                                ui.end_row();
                            }
                        });
                });
        });
    }

    fn show_sidebar(&mut self, ui: &mut egui::Ui) {
        ui.heading("Skills");
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
                ui.horizontal(|ui| {
                    if ui.selectable_label(selected, row.name.clone()).clicked() {
                        self.start_inspect(row.slug.clone());
                    }
                    ui.colored_label(Self::quality_color(quality), quality.label());
                });
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

    fn show_selected(&mut self, ui: &mut egui::Ui) {
        ui.heading("Selected Skill");
        if let Some(master) = self.selected.clone() {
            let row_metrics = self
                .rows
                .iter()
                .find(|row| row.slug == master.slug)
                .map(|row| {
                    (
                        row.quality_level(),
                        row.source_index_present,
                        row.fidelity_case_count,
                        row.kind,
                    )
                });
            let quality = row_metrics
                .map(|metrics| metrics.0)
                .unwrap_or(QualityLevel::Missing);
            ui.label(master.display_name.as_deref().unwrap_or(&master.name));
            ui.horizontal(|ui| {
                ui.colored_label(Self::quality_color(quality), quality.label());
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
            ui.horizontal(|ui| {
                ui.selectable_value(&mut self.detail_view, DetailView::Overview, "Overview");
                ui.selectable_value(&mut self.detail_view, DetailView::Sources, "Sources");
                ui.selectable_value(&mut self.detail_view, DetailView::Evaluation, "Evaluation");
                ui.selectable_value(&mut self.detail_view, DetailView::Runtime, "Runtime");
            });

            ui.separator();
            match self.detail_view {
                DetailView::Overview => {
                    egui::Grid::new("inspect-overview-grid")
                        .num_columns(2)
                        .show(ui, |ui| {
                            ui.label("Slug");
                            ui.label(&master.slug);
                            ui.end_row();
                            ui.label("Type");
                            ui.label(
                                row_metrics
                                    .map(|metrics| metrics.3.label())
                                    .unwrap_or("unknown"),
                            );
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
                }
                DetailView::Sources => {
                    let source_index = row_metrics.map(|metrics| metrics.1).unwrap_or(false);
                    ui.label(format!(
                        "Declared sources: {} | Source index: {}",
                        master.sources.len(),
                        if source_index { "present" } else { "missing" }
                    ));
                    ui.separator();
                    if master.sources.is_empty() {
                        ui.label("No sources declared.");
                    } else {
                        for source in &master.sources {
                            ui.label(source);
                        }
                    }
                }
                DetailView::Evaluation => {
                    let fidelity_count = row_metrics.map(|metrics| metrics.2).unwrap_or_default();
                    egui::Grid::new("evaluation-grid")
                        .num_columns(2)
                        .show(ui, |ui| {
                            ui.label("Fidelity cases");
                            ui.label(fidelity_count.to_string());
                            ui.end_row();
                            ui.label("Quality status");
                            ui.colored_label(Self::quality_color(quality), quality.label());
                            ui.end_row();
                        });
                    if fidelity_count == 0 {
                        ui.label("No fidelity suite detected for this skill.");
                    }
                }
                DetailView::Runtime => {
                    egui::Grid::new("runtime-grid")
                        .num_columns(2)
                        .show(ui, |ui| {
                            ui.label("Installed");
                            ui.label(if master.installed { "yes" } else { "no" });
                            ui.end_row();
                            ui.label("Live grounding");
                            ui.label(if master.live_grounding { "yes" } else { "no" });
                            ui.end_row();
                            ui.label("Citation format");
                            ui.label(master.citation_format.as_deref().unwrap_or("not declared"));
                            ui.end_row();
                            ui.label("Keywords");
                            ui.label(master.search_keywords.len().to_string());
                            ui.end_row();
                        });
                    if !master.search_keywords.is_empty() {
                        ui.separator();
                        ui.heading("Search Keywords");
                        ui.label(master.search_keywords.join(", "));
                    }
                }
            }
        } else {
            ui.label("No skill selected.");
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
        self.poll_task();
        if self.is_busy() {
            ctx.request_repaint();
        }

        egui::TopBottomPanel::top("top").show(ctx, |ui| self.show_toolbar(ui));

        egui::SidePanel::left("skills")
            .resizable(true)
            .default_width(260.0)
            .show(ctx, |ui| self.show_sidebar(ui));

        egui::TopBottomPanel::bottom("log")
            .resizable(true)
            .default_height(130.0)
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.heading("Operation Log");
                    if ui.button("Clear").clicked() {
                        self.log_lines.clear();
                    }
                });
                egui::ScrollArea::vertical()
                    .stick_to_bottom(true)
                    .show(ui, |ui| {
                        for line in &self.log_lines {
                            ui.label(line);
                        }
                    });
            });

        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                self.show_dashboard(ui);
                ui.separator();
                self.show_evaluation_center(ui);
                ui.separator();
                self.show_trace_center(ui);
                ui.separator();
                if dashboard_columns_for_width(ui.available_width()) == TwoPaneMode::TwoColumns {
                    ui.columns(2, |columns| {
                        self.show_doctor(&mut columns[0]);
                        self.show_selected(&mut columns[1]);
                    });
                } else {
                    self.show_doctor(ui);
                    ui.separator();
                    self.show_selected(ui);
                }
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
