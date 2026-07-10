use eframe::egui;
use master_skill_desktop::app::MasterSkillApp;
use master_skill_desktop::baseline::run_headless_baseline;
use master_skill_desktop::fonts::install_cjk_fonts;

fn main() -> eframe::Result {
    if std::env::args().any(|arg| arg == "--baseline") {
        let exit_code = match run_headless_baseline() {
            Ok(code) => code,
            Err(err) => {
                eprintln!("baseline failed: {err:#}");
                1
            }
        };
        std::process::exit(exit_code);
    }

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([1120.0, 720.0]),
        ..Default::default()
    };

    eframe::run_native(
        "Master-skill Desktop Manager",
        options,
        Box::new(|cc| {
            install_cjk_fonts(&cc.egui_ctx);
            Ok(Box::new(MasterSkillApp::new()))
        }),
    )
}
