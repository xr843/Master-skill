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
}

impl MasterSkillApp {
    pub fn new() -> Self {
        let mut app = Self {
            client: CliClient::default(),
            inventory: None,
            doctor: None,
            selected: None,
            selected_slug: None,
            log: "Starting desktop manager...".to_string(),
        };
        app.refresh_all();
        app
    }

    fn refresh_all(&mut self) {
        match self.client.list() {
            Ok(inventory) => {
                let first_slug = inventory.masters.first().map(|m| m.slug.clone());
                self.inventory = Some(inventory);
                if self.selected_slug.is_none() {
                    self.selected_slug = first_slug;
                }
            }
            Err(err) => {
                self.log = format!("Failed to load inventory: {err:#}");
                return;
            }
        }

        match self.client.doctor() {
            Ok(report) => self.doctor = Some(report),
            Err(err) => self.log = format!("Doctor failed: {err:#}"),
        }

        if let Some(slug) = self.selected_slug.clone() {
            self.inspect(&slug);
        }

        self.log = "Runtime data refreshed.".to_string();
    }

    fn inspect(&mut self, slug: &str) {
        match self.client.inspect(slug) {
            Ok(inspect) => {
                self.selected = Some(inspect);
                self.selected_slug = Some(slug.to_string());
                self.log = format!("Loaded master-{slug}.");
            }
            Err(err) => self.log = format!("Inspect failed for {slug}: {err:#}"),
        }
    }

    fn install_all(&mut self) {
        match self.client.install_all() {
            Ok(output) => {
                self.log = output.trim().to_string();
                self.refresh_all();
            }
            Err(err) => self.log = format!("Install failed: {err:#}"),
        }
    }

    fn update_all(&mut self) {
        match self.client.update_all() {
            Ok(output) => {
                self.log = output.trim().to_string();
                self.refresh_all();
            }
            Err(err) => self.log = format!("Update failed: {err:#}"),
        }
    }

    fn show_toolbar(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading("Master-skill Desktop Manager");
            ui.separator();
            if ui.button("Refresh").clicked() {
                self.refresh_all();
            }
            if ui.button("Install all").clicked() {
                self.install_all();
            }
            if ui.button("Update all").clicked() {
                self.update_all();
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
                    self.inspect(&master.slug);
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

    fn show_selected(&self, ui: &mut egui::Ui) {
        ui.heading("Selected Skill");
        if let Some(master) = &self.selected {
            ui.label(master.display_name.as_deref().unwrap_or(&master.name));
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
