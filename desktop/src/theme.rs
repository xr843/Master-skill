use eframe::egui;

pub const SIDEBAR_DEFAULT_WIDTH: f32 = 280.0;
pub const SIDEBAR_ROW_HEIGHT: f32 = 24.0;
pub const STATUS_BADGE_WIDTH: f32 = 54.0;

pub fn apply_console_theme(ctx: &egui::Context) {
    let mut visuals = egui::Visuals::dark();
    visuals.panel_fill = egui::Color32::from_rgb(18, 20, 20);
    visuals.window_fill = egui::Color32::from_rgb(20, 23, 23);
    visuals.faint_bg_color = egui::Color32::from_rgb(26, 30, 30);
    visuals.extreme_bg_color = egui::Color32::from_rgb(8, 10, 10);
    visuals.selection.bg_fill = egui::Color32::from_rgb(18, 94, 126);
    visuals.selection.stroke = egui::Stroke::new(1.0, egui::Color32::from_rgb(76, 164, 196));
    visuals.widgets.inactive.bg_fill = egui::Color32::from_rgb(38, 42, 42);
    visuals.widgets.hovered.bg_fill = egui::Color32::from_rgb(48, 56, 56);
    visuals.widgets.active.bg_fill = egui::Color32::from_rgb(30, 84, 96);
    visuals.widgets.noninteractive.fg_stroke =
        egui::Stroke::new(1.0, egui::Color32::from_rgb(186, 194, 190));
    ctx.set_visuals(visuals);

    let mut style = (*ctx.style()).clone();
    style.spacing.item_spacing = egui::vec2(8.0, 5.0);
    style.spacing.button_padding = egui::vec2(8.0, 3.0);
    style.spacing.interact_size.y = 22.0;
    ctx.set_style(style);
}

pub fn status_badge_width() -> f32 {
    STATUS_BADGE_WIDTH
}

pub fn sidebar_row_height() -> f32 {
    SIDEBAR_ROW_HEIGHT
}

pub fn sidebar_default_width() -> f32 {
    SIDEBAR_DEFAULT_WIDTH
}

#[cfg(test)]
mod tests {
    use super::{sidebar_default_width, sidebar_row_height, status_badge_width};

    #[test]
    fn keeps_sidebar_rows_dense_but_clickable() {
        assert!(sidebar_row_height() >= 22.0);
        assert!(sidebar_row_height() <= 28.0);
    }

    #[test]
    fn keeps_status_badges_wide_enough_for_attention_labels() {
        assert!(status_badge_width() >= 52.0);
    }

    #[test]
    fn gives_sidebar_enough_width_for_names_and_badges() {
        assert!(sidebar_default_width() >= 280.0);
    }
}
