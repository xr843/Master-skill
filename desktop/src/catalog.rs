use std::fs;
use std::path::Path;

use crate::model::{MasterInspect, SkillSummary};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InstallFilter {
    All,
    Installed,
    Missing,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum QualityLevel {
    Ready,
    Attention,
    Missing,
}

impl QualityLevel {
    pub fn label(self) -> &'static str {
        match self {
            Self::Ready => "ready",
            Self::Attention => "attention",
            Self::Missing => "missing",
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SkillDiagnostics {
    pub fidelity_case_count: usize,
    pub source_index_present: bool,
}

impl SkillDiagnostics {
    pub fn from_prebuilt_dir(prebuilt_dir: &Path, slug: &str) -> Self {
        let skill_dir = prebuilt_dir.join(format!("master-{slug}"));
        let fidelity_path = skill_dir.join("tests").join("fidelity.jsonl");
        let fidelity_case_count = fs::read_to_string(fidelity_path)
            .map(|content| {
                content
                    .lines()
                    .filter(|line| !line.trim().is_empty())
                    .count()
            })
            .unwrap_or(0);

        Self {
            fidelity_case_count,
            source_index_present: skill_dir.join("sources").join("INDEX.md").is_file(),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SkillRow {
    pub name: String,
    pub slug: String,
    pub description: String,
    pub display_name: Option<String>,
    pub tradition: Option<String>,
    pub school: Option<String>,
    pub installed: bool,
    pub live_grounding: bool,
    pub source_count: usize,
    pub keyword_count: usize,
    pub has_citation_format: bool,
    pub fidelity_case_count: usize,
    pub source_index_present: bool,
}

impl SkillRow {
    pub fn from_summary_and_inspect(
        summary: &SkillSummary,
        inspect: Option<&MasterInspect>,
    ) -> Self {
        Self {
            name: summary.name.clone(),
            slug: summary.slug.clone(),
            description: summary.description.clone(),
            display_name: inspect.and_then(|i| i.display_name.clone()),
            tradition: inspect.and_then(|i| i.tradition.clone()),
            school: inspect.and_then(|i| i.school.clone()),
            installed: inspect.map(|i| i.installed).unwrap_or(false),
            live_grounding: inspect.map(|i| i.live_grounding).unwrap_or(false),
            source_count: inspect.map(|i| i.sources.len()).unwrap_or(0),
            keyword_count: inspect.map(|i| i.search_keywords.len()).unwrap_or(0),
            has_citation_format: inspect
                .and_then(|i| i.citation_format.as_ref())
                .map(|value| !value.trim().is_empty())
                .unwrap_or(false),
            fidelity_case_count: 0,
            source_index_present: false,
        }
    }

    pub fn title(&self) -> &str {
        self.display_name.as_deref().unwrap_or(&self.name)
    }

    pub fn apply_diagnostics(&mut self, diagnostics: SkillDiagnostics) {
        self.fidelity_case_count = diagnostics.fidelity_case_count;
        self.source_index_present = diagnostics.source_index_present;
    }

    pub fn quality_level(&self) -> QualityLevel {
        if !self.installed {
            return QualityLevel::Missing;
        }

        if self.live_grounding
            && self.source_count > 0
            && self.source_index_present
            && self.has_citation_format
            && self.fidelity_case_count > 0
        {
            QualityLevel::Ready
        } else {
            QualityLevel::Attention
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ConsoleSummary {
    pub available_count: usize,
    pub installed_count: usize,
    pub missing_count: usize,
    pub source_ready_count: usize,
    pub evaluation_ready_count: usize,
    pub protocol_ready_count: usize,
    pub attention_count: usize,
    pub runtime_ok: bool,
}

pub fn console_summary(
    rows: &[SkillRow],
    available_count: usize,
    runtime_status: &str,
    problem_count: usize,
) -> ConsoleSummary {
    let installed_count = rows.iter().filter(|row| row.installed).count();
    let missing_count = rows.len().saturating_sub(installed_count);
    let source_ready_count = rows
        .iter()
        .filter(|row| row.source_count > 0 && row.source_index_present)
        .count();
    let evaluation_ready_count = rows
        .iter()
        .filter(|row| row.fidelity_case_count > 0)
        .count();
    let protocol_ready_count = rows
        .iter()
        .filter(|row| row.live_grounding && row.has_citation_format)
        .count();
    let attention_count = rows
        .iter()
        .filter(|row| row.quality_level() != QualityLevel::Ready)
        .count();

    ConsoleSummary {
        available_count,
        installed_count,
        missing_count,
        source_ready_count,
        evaluation_ready_count,
        protocol_ready_count,
        attention_count,
        runtime_ok: runtime_status == "ok" && problem_count == 0,
    }
}

pub fn filter_rows<'a>(
    rows: &'a [SkillRow],
    query: &str,
    install_filter: InstallFilter,
    tradition_filter: Option<&str>,
) -> Vec<&'a SkillRow> {
    let query = query.trim().to_lowercase();
    rows.iter()
        .filter(|row| match install_filter {
            InstallFilter::All => true,
            InstallFilter::Installed => row.installed,
            InstallFilter::Missing => !row.installed,
        })
        .filter(|row| {
            tradition_filter
                .map(|tradition| row.tradition.as_deref() == Some(tradition))
                .unwrap_or(true)
        })
        .filter(|row| {
            if query.is_empty() {
                return true;
            }
            let haystack = [
                row.name.as_str(),
                row.slug.as_str(),
                row.display_name.as_deref().unwrap_or(""),
                row.tradition.as_deref().unwrap_or(""),
                row.school.as_deref().unwrap_or(""),
                row.description.as_str(),
            ]
            .join(" ")
            .to_lowercase();
            haystack.contains(&query)
        })
        .collect()
}

pub fn tradition_options(rows: &[SkillRow]) -> Vec<String> {
    let mut options: Vec<String> = rows
        .iter()
        .filter_map(|row| row.tradition.clone())
        .filter(|value| !value.trim().is_empty())
        .collect();
    options.sort();
    options.dedup();
    options
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::{
        console_summary, filter_rows, tradition_options, InstallFilter, QualityLevel,
        SkillDiagnostics, SkillRow,
    };

    fn temp_dir() -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("master-skill-desktop-catalog-test-{suffix}"))
    }

    fn row(slug: &str, display_name: &str, tradition: &str, installed: bool) -> SkillRow {
        SkillRow {
            name: format!("master-{slug}"),
            slug: slug.to_string(),
            description: format!("{display_name} description"),
            display_name: Some(display_name.to_string()),
            tradition: Some(tradition.to_string()),
            school: None,
            installed,
            live_grounding: true,
            source_count: 3,
            keyword_count: 8,
            has_citation_format: true,
            fidelity_case_count: 4,
            source_index_present: true,
        }
    }

    #[test]
    fn filters_by_query_install_state_and_tradition() {
        let rows = vec![
            row("huineng", "慧能大师", "汉传", true),
            row("atisha", "阿底峡尊者", "藏传", false),
            row("ajahn-chah", "阿姜查", "南传", true),
        ];

        let filtered = filter_rows(&rows, "阿", InstallFilter::Installed, Some("南传"));

        assert_eq!(filtered.len(), 1);
        assert_eq!(filtered[0].slug, "ajahn-chah");
    }

    #[test]
    fn returns_sorted_unique_tradition_options() {
        let rows = vec![
            row("huineng", "慧能大师", "汉传", true),
            row("zhiyi", "智者大师", "汉传", true),
            row("atisha", "阿底峡尊者", "藏传", false),
        ];

        assert_eq!(tradition_options(&rows), vec!["汉传", "藏传"]);
    }

    #[test]
    fn classifies_skill_quality_from_sources_evaluations_and_protocol() {
        let ready = row("huineng", "慧能大师", "汉传", true);

        let mut attention = row("atisha", "阿底峡尊者", "藏传", true);
        attention.fidelity_case_count = 0;

        let missing = row("ajahn-chah", "阿姜查", "南传", false);

        assert_eq!(ready.quality_level(), QualityLevel::Ready);
        assert_eq!(attention.quality_level(), QualityLevel::Attention);
        assert_eq!(missing.quality_level(), QualityLevel::Missing);
    }

    #[test]
    fn summarizes_console_health_for_dashboard_cards() {
        let rows = vec![
            row("huineng", "慧能大师", "汉传", true),
            row("zhiyi", "智者大师", "汉传", true),
            row("atisha", "阿底峡尊者", "藏传", false),
        ];

        let summary = console_summary(&rows, 17, "ok", 0);

        assert_eq!(summary.available_count, 17);
        assert_eq!(summary.installed_count, 2);
        assert_eq!(summary.missing_count, 1);
        assert_eq!(summary.source_ready_count, 3);
        assert_eq!(summary.evaluation_ready_count, 3);
        assert_eq!(summary.protocol_ready_count, 3);
        assert_eq!(summary.attention_count, 1);
        assert!(summary.runtime_ok);
    }

    #[test]
    fn reads_skill_diagnostics_from_prebuilt_files() {
        let root = temp_dir();
        let skill_dir = root.join("master-huineng");
        fs::create_dir_all(skill_dir.join("sources")).unwrap();
        fs::create_dir_all(skill_dir.join("tests")).unwrap();
        fs::write(skill_dir.join("sources").join("INDEX.md"), "# Sources\n").unwrap();
        fs::write(
            skill_dir.join("tests").join("fidelity.jsonl"),
            "{\"prompt\":\"one\"}\n\n{\"prompt\":\"two\"}\n",
        )
        .unwrap();

        let diagnostics = SkillDiagnostics::from_prebuilt_dir(Path::new(&root), "huineng");

        assert!(diagnostics.source_index_present);
        assert_eq!(diagnostics.fidelity_case_count, 2);

        fs::remove_dir_all(root).unwrap();
    }
}
