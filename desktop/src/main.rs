use eframe::egui;
use master_skill_desktop::app::MasterSkillApp;
use master_skill_desktop::baseline::run_headless_baseline;
use master_skill_desktop::desktop_args::{parse_launch_mode, LaunchMode, DESKTOP_USAGE};
use master_skill_desktop::fonts::install_cjk_fonts;

fn main() -> eframe::Result {
    match parse_launch_mode(std::env::args_os().skip(1)) {
        Ok(LaunchMode::Gui) => run_gui(),
        Ok(LaunchMode::Baseline) => {
            let exit_code = match run_headless_baseline() {
                Ok(code) => code,
                Err(err) => {
                    eprintln!("baseline failed: {err:#}");
                    1
                }
            };
            std::process::exit(exit_code);
        }
        Ok(LaunchMode::Help) => {
            println!("{DESKTOP_USAGE}");
            Ok(())
        }
        Err(error) => {
            eprintln!("{error}\n\n{DESKTOP_USAGE}");
            std::process::exit(2);
        }
    }
}

fn run_gui() -> eframe::Result {
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
