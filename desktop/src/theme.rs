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
    visuals.selection.stroke = egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(76, 164, 196));
    visuals.widgets.inactive.bg_fill = egui::Color32::from_rgb(38, 42, 42);
    visuals.widgets.hovered.bg_fill = egui::Color32::from_rgb(48, 56, 56);
    visuals.widgets.active.bg_fill = egui::Color32::from_rgb(30, 84, 96);
    visuals.widgets.noninteractive.fg_stroke =
        egui::Stroke::new(1.0_f32, egui::Color32::from_rgb(186, 194, 190));
    ctx.set_visuals(visuals);

    // egui 0.36 把 style 变成按主题存放:`Context::style()` / `set_style()` 没了,
    // 取而代之的是 `style_of(theme)` / `set_style_of(theme, style)`。这里要的是
    // 旧行为 —— 不分主题一律生效 —— 所以用 `all_styles_mut`,而不是挑一个
    // `Theme::Dark` 写进去:那样浅色主题下这三行间距就会无声地失效。
    ctx.all_styles_mut(|style| {
        style.spacing.item_spacing = egui::vec2(8.0, 5.0);
        style.spacing.button_padding = egui::vec2(8.0, 3.0);
        style.spacing.interact_size.y = 22.0;
    });
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
    use super::{apply_console_theme, sidebar_default_width, sidebar_row_height, status_badge_width};

    /// egui 0.36 删掉了 `Context::style()` / `set_style()`。这三行间距原本靠
    /// 它们设置,换成 `all_styles_mut` 之后必须仍然生效 —— 编译通过不代表
    /// 值写进去了:`set_style_of(Theme::Dark, …)` 也编译得过,却会让浅色主题
    /// 下这一段无声失效。
    #[test]
    fn console_theme_sets_spacing_on_a_real_context() {
        let ctx = eframe::egui::Context::default();
        ctx.set_fonts(eframe::egui::FontDefinitions::empty());
        apply_console_theme(&ctx);

        for theme in [
            eframe::egui::Theme::Dark,
            eframe::egui::Theme::Light,
        ] {
            let style = ctx.style_of(theme);
            assert_eq!(
                style.spacing.item_spacing,
                eframe::egui::vec2(8.0, 5.0),
                "{theme:?} 的 item_spacing 没被设置"
            );
            assert_eq!(style.spacing.button_padding, eframe::egui::vec2(8.0, 3.0));
            assert_eq!(style.spacing.interact_size.y, 22.0);
        }
    }

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
