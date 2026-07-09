use std::sync::mpsc::{channel, Receiver};
use std::thread;

use anyhow::Result;
use eframe::egui;

use crate::cli::CliClient;
use crate::model::{DoctorReport, MasterInspect, SkillInventory, SkillSummary};

pub struct MasterSkillApp {
    client: CliClient,
    inventory: Option<SkillInventory>,
    doctor: Option<DoctorReport>,
    selected: Option<MasterInspect>,
    selected_slug: Option<String>,
    log: String,
    task_rx: Option<Receiver<TaskResult>>,
    busy_label: Option<String>,
}

struct Snapshot {
    inventory: SkillInventory,
    doctor: DoctorReport,
    selected_slug: Option<String>,
    selected: Option<MasterInspect>,
}

struct TaskOutcome {
    message: String,
    snapshot: Option<Snapshot>,
}

type TaskResult = std::result::Result<TaskOutcome, String>;

impl MasterSkillApp {
    pub fn new() -> Self {
        let mut app = Self {
            client: CliClient::default(),
            inventory: None,
            doctor: None,
            selected: None,
            selected_slug: None,
            log: "Starting desktop manager...".to_string(),
            task_rx: None,
            busy_label: None,
        };
        app.refresh_all();
        app
    }

    fn load_snapshot(client: &CliClient, selected_slug: Option<String>) -> Result<Snapshot> {
        let inventory = client.list()?;
        let doctor = client.doctor()?;
        let resolved_slug =
            selected_slug.or_else(|| inventory.masters.first().map(|m| m.slug.clone()));
        let selected = match resolved_slug.as_deref() {
            Some(slug) => Some(client.inspect(slug)?),
            None => None,
        };

        Ok(Snapshot {
            inventory,
            doctor,
            selected_slug: resolved_slug,
            selected,
        })
    }

    fn apply_snapshot(&mut self, snapshot: Snapshot) {
        self.inventory = Some(snapshot.inventory);
        self.doctor = Some(snapshot.doctor);
        self.selected_slug = snapshot.selected_slug;
        self.selected = snapshot.selected;
    }

    fn refresh_all(&mut self) {
        match Self::load_snapshot(&self.client, self.selected_slug.clone()) {
            Ok(snapshot) => {
                self.apply_snapshot(snapshot);
                self.log = "Runtime data refreshed.".to_string();
            }
            Err(err) => self.log = format!("Refresh failed: {err:#}"),
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
            self.log = "A task is already running.".to_string();
            return;
        }

        let client = self.client.clone();
        let label = label.into();
        let (tx, rx) = channel();
        self.task_rx = Some(rx);
        self.busy_label = Some(label.clone());
        self.log = format!("{label}...");

        thread::spawn(move || {
            let result = task(client).map_err(|err| format!("{err:#}"));
            let _ = tx.send(result);
        });
    }

    fn poll_task(&mut self) {
        let result = self.task_rx.as_ref().and_then(|rx| rx.try_recv().ok());
        if let Some(result) = result {
            self.task_rx = None;
            self.busy_label = None;
            match result {
                Ok(outcome) => {
                    if let Some(snapshot) = outcome.snapshot {
                        self.apply_snapshot(snapshot);
                    }
                    self.log = outcome.message;
                }
                Err(message) => self.log = message,
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
            let selected = client.inspect(&slug)?;
            Ok(TaskOutcome {
                message: format!("Loaded master-{slug}."),
                snapshot: Some(Snapshot {
                    inventory: client.list()?,
                    doctor: client.doctor()?,
                    selected_slug: Some(slug),
                    selected: Some(selected),
                }),
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

    fn show_sidebar(&mut self, ui: &mut egui::Ui) {
        ui.heading("Skills");
        let masters: Vec<SkillSummary> = self
            .inventory
            .as_ref()
            .map(|inventory| inventory.masters.clone())
            .unwrap_or_default();

        egui::ScrollArea::vertical().show(ui, |ui| {
            for master in masters {
                let selected = self.selected_slug.as_deref() == Some(master.slug.as_str());
                let label = if master.name.starts_with("master-") {
                    master.name.clone()
                } else {
                    format!("master-{}", master.slug)
                };
                if ui.selectable_label(selected, label).clicked() {
                    self.start_inspect(master.slug);
                }
            }
        });
    }

    fn show_doctor(&self, ui: &mut egui::Ui) {
        ui.heading("Runtime");
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
            ui.label(master.display_name.as_deref().unwrap_or(&master.name));
            ui.horizontal(|ui| {
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

            egui::Grid::new("inspect-grid")
                .num_columns(2)
                .show(ui, |ui| {
                    ui.label("Slug");
                    ui.label(&master.slug);
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
                    ui.label("Installed");
                    ui.label(if master.installed { "yes" } else { "no" });
                    ui.end_row();
                    ui.label("Live grounding");
                    ui.label(if master.live_grounding { "yes" } else { "no" });
                    ui.end_row();
                });

            ui.separator();
            ui.heading("Sources");
            if master.sources.is_empty() {
                ui.label("No sources declared.");
            } else {
                for source in &master.sources {
                    ui.label(source);
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

        egui::TopBottomPanel::bottom("log").show(ctx, |ui| {
            ui.label(&self.log);
        });

        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                ui.columns(2, |columns| {
                    self.show_doctor(&mut columns[0]);
                    self.show_selected(&mut columns[1]);
                });
            });
        });
    }
}
