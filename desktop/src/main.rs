use eframe::egui;
use master_skill_desktop::app::MasterSkillApp;

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([1120.0, 720.0]),
        ..Default::default()
    };

    eframe::run_native(
        "Master-skill Desktop Manager",
        options,
        Box::new(|_cc| Ok(Box::new(MasterSkillApp::new()))),
    )
}
