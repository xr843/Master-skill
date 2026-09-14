// Release builds on Windows are GUI programs. Without this the linker makes a
// console program, and Windows opens a console window behind the app when the
// .exe is double-clicked — v0.12.1 shipped that way. Debug builds keep the
// console so `cargo run` output stays visible. This is the setting eframe's own
// template uses.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use eframe::egui;
use master_skill_desktop::app::MasterSkillApp;
use master_skill_desktop::baseline::run_headless_baseline;
use master_skill_desktop::desktop_args::{parse_launch_mode, LaunchMode, DESKTOP_USAGE};
use master_skill_desktop::fonts::install_cjk_fonts;

fn main() -> eframe::Result {
    match parse_launch_mode(std::env::args_os().skip(1)) {
        Ok(LaunchMode::Gui) => run_gui(),
        Ok(LaunchMode::Baseline) => {
            attach_parent_console();
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
            attach_parent_console();
            println!("{DESKTOP_USAGE}");
            Ok(())
        }
        Err(error) => {
            attach_parent_console();
            eprintln!("{error}\n\n{DESKTOP_USAGE}");
            std::process::exit(2);
        }
    }
}

/// A GUI-subsystem program starts without a console, so `--help` or
/// `--baseline` typed in a terminal would print nowhere. Attach to the console
/// of the process that launched this one, but only when stdout has no handle:
/// output already redirected to a file or pipe is left where it is.
#[cfg(windows)]
fn attach_parent_console() {
    use windows_sys::Win32::Foundation::INVALID_HANDLE_VALUE;
    use windows_sys::Win32::System::Console::{
        AttachConsole, GetStdHandle, ATTACH_PARENT_PROCESS, STD_OUTPUT_HANDLE,
    };

    // SAFETY: neither call takes a pointer argument. If either fails, output
    // simply stays wherever it already was.
    unsafe {
        let stdout = GetStdHandle(STD_OUTPUT_HANDLE);
        if stdout.is_null() || stdout == INVALID_HANDLE_VALUE {
            AttachConsole(ATTACH_PARENT_PROCESS);
        }
    }
}

#[cfg(not(windows))]
fn attach_parent_console() {}

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
