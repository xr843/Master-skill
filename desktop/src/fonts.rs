use std::path::{Path, PathBuf};
use std::sync::Arc;

use eframe::egui;

const CJK_FONT_CANDIDATES: &[&str] = &[
    "/mnt/c/Windows/Fonts/NotoSansSC-VF.ttf",
    "/mnt/c/Windows/Fonts/msyh.ttc",
    "/mnt/c/Windows/Fonts/Deng.ttf",
    "/mnt/c/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
];

pub fn install_cjk_fonts(ctx: &egui::Context) {
    let Some(path) = first_existing_path(CJK_FONT_CANDIDATES.iter().map(Path::new)) else {
        return;
    };
    let Ok(bytes) = std::fs::read(path) else {
        return;
    };

    let mut fonts = egui::FontDefinitions::default();
    fonts.font_data.insert(
        "master_skill_cjk".to_string(),
        Arc::new(egui::FontData::from_owned(bytes)),
    );

    for family in [egui::FontFamily::Proportional, egui::FontFamily::Monospace] {
        fonts
            .families
            .entry(family)
            .or_default()
            .insert(0, "master_skill_cjk".to_string());
    }

    ctx.set_fonts(fonts);
}

fn first_existing_path<'a>(paths: impl IntoIterator<Item = &'a Path>) -> Option<PathBuf> {
    paths
        .into_iter()
        .find(|path| path.is_file())
        .map(Path::to_path_buf)
}

#[cfg(test)]
mod tests {
    use super::first_existing_path;
    use std::fs;

    #[test]
    fn picks_first_existing_font_candidate() {
        let root =
            std::env::temp_dir().join(format!("master-skill-font-test-{}", std::process::id()));
        let missing = root.join("missing.ttf");
        let existing = root.join("existing.ttf");
        fs::create_dir_all(&root).unwrap();
        fs::write(&existing, b"font").unwrap();

        let picked = first_existing_path([missing.as_path(), existing.as_path()]);

        assert_eq!(picked.as_deref(), Some(existing.as_path()));
        fs::remove_dir_all(root).unwrap();
    }
}
