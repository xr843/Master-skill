use std::collections::BTreeMap;
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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SkillKind {
    Persona,
    MetaSkill,
}

impl SkillKind {
    pub fn label(self) -> &'static str {
        match self {
            Self::Persona => "persona",
            Self::MetaSkill => "meta-skill",
        }
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct SkillDiagnostics {
    pub fidelity_case_count: usize,
    pub source_index_present: bool,
    pub kind: SkillKind,
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
            kind: detect_skill_kind(&skill_dir),
        }
    }
}

impl Default for SkillKind {
    fn default() -> Self {
        Self::Persona
    }
}

fn detect_skill_kind(skill_dir: &Path) -> SkillKind {
    let skill_md = fs::read_to_string(skill_dir.join("SKILL.md")).unwrap_or_default();
    let meta_json = fs::read_to_string(skill_dir.join("meta.json")).unwrap_or_default();
    let meta_kind = serde_json::from_str::<serde_json::Value>(&meta_json)
        .ok()
        .and_then(|value| {
            value
                .get("kind")
                .and_then(serde_json::Value::as_str)
                .map(str::to_string)
        });

    if skill_md.contains("kind: meta-skill") || meta_kind.as_deref() == Some("meta-skill") {
        SkillKind::MetaSkill
    } else {
        SkillKind::Persona
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DiagnosticAction {
    pub title: String,
    pub detail: String,
    pub command: Option<String>,
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
    pub kind: SkillKind,
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
            kind: SkillKind::Persona,
        }
    }

    pub fn title(&self) -> &str {
        self.display_name.as_deref().unwrap_or(&self.name)
    }

    pub fn apply_diagnostics(&mut self, diagnostics: SkillDiagnostics) {
        self.fidelity_case_count = diagnostics.fidelity_case_count;
        self.source_index_present = diagnostics.source_index_present;
        self.kind = diagnostics.kind;
    }

    pub fn quality_level(&self) -> QualityLevel {
        if !self.installed {
            return QualityLevel::Missing;
        }

        if self.kind == SkillKind::MetaSkill {
            return if self.fidelity_case_count > 0 {
                QualityLevel::Ready
            } else {
                QualityLevel::Attention
            };
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

    pub fn diagnostic_gaps(&self) -> Vec<&'static str> {
        let mut gaps = Vec::new();

        if !self.installed {
            gaps.push("not installed");
            return gaps;
        }

        if self.kind == SkillKind::Persona {
            if self.source_count == 0 {
                gaps.push("missing sources");
            }
            if !self.source_index_present {
                gaps.push("missing source index");
            }
            if !self.has_citation_format {
                gaps.push("missing citation format");
            }
            if !self.live_grounding {
                gaps.push("live grounding off");
            }
        }

        if self.fidelity_case_count == 0 {
            gaps.push("missing fidelity suite");
        }

        gaps
    }

    pub fn diagnostic_summary(&self) -> String {
        let gaps = self.diagnostic_gaps();
        if gaps.is_empty() {
            "complete".to_string()
        } else {
            gaps.join(", ")
        }
    }

    pub fn diagnostic_actions(&self) -> Vec<DiagnosticAction> {
        if !self.installed {
            return vec![DiagnosticAction {
                title: "Install skill".to_string(),
                detail: "Install this skill into the local Codex/Claude skills directory."
                    .to_string(),
                command: Some(format!("master-skill install {}", self.slug)),
            }];
        }

        let mut actions = Vec::new();
        if self.kind == SkillKind::Persona {
            if self.source_count == 0 {
                actions.push(DiagnosticAction {
                    title: "Add source declarations".to_string(),
                    detail: "Declare primary textual sources in the skill metadata.".to_string(),
                    command: None,
                });
            }
            if !self.source_index_present {
                actions.push(DiagnosticAction {
                    title: "Create source index".to_string(),
                    detail: "Add sources/INDEX.md so source grounding is auditable.".to_string(),
                    command: None,
                });
            }
            if !self.has_citation_format {
                actions.push(DiagnosticAction {
                    title: "Declare citation format".to_string(),
                    detail: "Add the expected citation format to the skill metadata.".to_string(),
                    command: None,
                });
            }
            if !self.live_grounding {
                actions.push(DiagnosticAction {
                    title: "Enable live grounding".to_string(),
                    detail: "Set the runtime grounding protocol for this persona.".to_string(),
                    command: None,
                });
            }
        }

        if self.fidelity_case_count == 0 {
            actions.push(DiagnosticAction {
                title: "Add fidelity suite".to_string(),
                detail: "Create tests/fidelity.jsonl, then dry-run the suite for this skill."
                    .to_string(),
                command: Some(format!(
                    "python3 scripts/test-fidelity.py --master master-{} --dry-run",
                    self.slug
                )),
            });
        }

        actions
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
    pub persona_count: usize,
    pub meta_skill_count: usize,
}

pub fn console_summary(
    rows: &[SkillRow],
    available_count: usize,
    runtime_status: &str,
    problem_count: usize,
) -> ConsoleSummary {
    let installed_count = rows.iter().filter(|row| row.installed).count();
    let missing_count = rows.len().saturating_sub(installed_count);
    let persona_count = rows
        .iter()
        .filter(|row| row.kind == SkillKind::Persona)
        .count();
    let meta_skill_count = rows
        .iter()
        .filter(|row| row.kind == SkillKind::MetaSkill)
        .count();
    let source_ready_count = rows
        .iter()
        .filter(|row| {
            row.kind == SkillKind::Persona && row.source_count > 0 && row.source_index_present
        })
        .count();
    let evaluation_ready_count = rows
        .iter()
        .filter(|row| row.fidelity_case_count > 0)
        .count();
    let protocol_ready_count = rows
        .iter()
        .filter(|row| {
            row.kind == SkillKind::Persona && row.live_grounding && row.has_citation_format
        })
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
        persona_count,
        meta_skill_count,
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationGroup {
    pub tradition: String,
    pub skill_count: usize,
    pub case_count: usize,
    pub missing_suite_count: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvaluationSummary {
    pub skill_count: usize,
    pub case_count: usize,
    pub ready_count: usize,
    pub attention_count: usize,
    pub missing_count: usize,
    pub missing_suite_count: usize,
    pub groups: Vec<EvaluationGroup>,
}

pub fn evaluation_summary(rows: &[SkillRow]) -> EvaluationSummary {
    let mut ready_count = 0;
    let mut attention_count = 0;
    let mut missing_count = 0;
    let mut groups: BTreeMap<String, EvaluationGroup> = BTreeMap::new();

    for row in rows {
        match row.quality_level() {
            QualityLevel::Ready => ready_count += 1,
            QualityLevel::Attention => attention_count += 1,
            QualityLevel::Missing => missing_count += 1,
        }

        let tradition = row
            .tradition
            .clone()
            .filter(|value| !value.trim().is_empty())
            .unwrap_or_else(|| "unspecified".to_string());
        let group = groups.entry(tradition.clone()).or_insert(EvaluationGroup {
            tradition,
            skill_count: 0,
            case_count: 0,
            missing_suite_count: 0,
        });
        group.skill_count += 1;
        group.case_count += row.fidelity_case_count;
        if row.fidelity_case_count == 0 {
            group.missing_suite_count += 1;
        }
    }

    EvaluationSummary {
        skill_count: rows.len(),
        case_count: rows.iter().map(|row| row.fidelity_case_count).sum(),
        ready_count,
        attention_count,
        missing_count,
        missing_suite_count: rows
            .iter()
            .filter(|row| row.fidelity_case_count == 0)
            .count(),
        groups: groups.into_values().collect(),
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
        console_summary, evaluation_summary, filter_rows, tradition_options, EvaluationGroup,
        InstallFilter, QualityLevel, SkillDiagnostics, SkillKind, SkillRow,
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
            kind: SkillKind::Persona,
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
        assert_eq!(summary.persona_count, 3);
        assert_eq!(summary.meta_skill_count, 0);
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

    #[test]
    fn treats_meta_skills_as_ready_when_their_fidelity_suite_exists() {
        let mut meta = row("curriculum", "学修路径", "", true);
        meta.kind = SkillKind::MetaSkill;
        meta.live_grounding = false;
        meta.source_count = 0;
        meta.source_index_present = false;
        meta.has_citation_format = false;
        meta.fidelity_case_count = 8;

        assert_eq!(meta.quality_level(), QualityLevel::Ready);

        let summary = console_summary(&[meta], 1, "ok", 0);

        assert_eq!(summary.persona_count, 0);
        assert_eq!(summary.meta_skill_count, 1);
        assert_eq!(summary.source_ready_count, 0);
        assert_eq!(summary.protocol_ready_count, 0);
        assert_eq!(summary.evaluation_ready_count, 1);
        assert_eq!(summary.attention_count, 0);
    }

    #[test]
    fn reports_persona_diagnostic_gaps() {
        let mut broken = row("huineng", "慧能大师", "汉传", true);
        broken.live_grounding = false;
        broken.source_count = 0;
        broken.source_index_present = false;
        broken.has_citation_format = false;
        broken.fidelity_case_count = 0;

        assert_eq!(
            broken.diagnostic_gaps(),
            vec![
                "missing sources",
                "missing source index",
                "missing citation format",
                "live grounding off",
                "missing fidelity suite",
            ]
        );
        assert_eq!(
            broken.diagnostic_summary(),
            "missing sources, missing source index, missing citation format, live grounding off, missing fidelity suite"
        );
    }

    #[test]
    fn reports_meta_skill_diagnostic_gaps_without_persona_only_requirements() {
        let mut meta = row("curriculum", "学修路径", "", true);
        meta.kind = SkillKind::MetaSkill;
        meta.live_grounding = false;
        meta.source_count = 0;
        meta.source_index_present = false;
        meta.has_citation_format = false;
        meta.fidelity_case_count = 0;

        assert_eq!(meta.diagnostic_gaps(), vec!["missing fidelity suite"]);
        assert_eq!(meta.diagnostic_summary(), "missing fidelity suite");
    }

    #[test]
    fn recommends_install_action_for_missing_skill() {
        let missing = row("atisha", "阿底峡尊者", "藏传", false);

        let actions = missing.diagnostic_actions();

        assert_eq!(actions.len(), 1);
        assert_eq!(actions[0].title, "Install skill");
        assert_eq!(
            actions[0].command.as_deref(),
            Some("master-skill install atisha")
        );
    }

    #[test]
    fn recommends_contract_actions_for_incomplete_persona() {
        let mut broken = row("huineng", "慧能大师", "汉传", true);
        broken.live_grounding = false;
        broken.source_count = 0;
        broken.source_index_present = false;
        broken.has_citation_format = false;
        broken.fidelity_case_count = 0;

        let actions = broken.diagnostic_actions();
        let titles: Vec<&str> = actions.iter().map(|action| action.title.as_str()).collect();
        let commands: Vec<Option<&str>> = actions
            .iter()
            .map(|action| action.command.as_deref())
            .collect();

        assert_eq!(
            titles,
            vec![
                "Add source declarations",
                "Create source index",
                "Declare citation format",
                "Enable live grounding",
                "Add fidelity suite",
            ]
        );
        assert_eq!(
            commands,
            vec![
                None,
                None,
                None,
                None,
                Some("python3 scripts/test-fidelity.py --master master-huineng --dry-run"),
            ]
        );
    }

    #[test]
    fn reads_meta_skill_kind_from_skill_frontmatter_and_meta_json() {
        let root = temp_dir();
        let curriculum_dir = root.join("master-curriculum");
        fs::create_dir_all(curriculum_dir.join("tests")).unwrap();
        fs::write(
            curriculum_dir.join("SKILL.md"),
            "---\nname: master-curriculum\nkind: meta-skill\n---\n",
        )
        .unwrap();
        fs::write(curriculum_dir.join("tests").join("fidelity.jsonl"), "{}\n").unwrap();

        let debate_dir = root.join("master-debate");
        fs::create_dir_all(debate_dir.join("tests")).unwrap();
        fs::write(
            debate_dir.join("SKILL.md"),
            "---\nname: master-debate\n---\n",
        )
        .unwrap();
        fs::write(
            debate_dir.join("meta.json"),
            "{\n  \"kind\": \"meta-skill\"\n}\n",
        )
        .unwrap();
        fs::write(debate_dir.join("tests").join("fidelity.jsonl"), "{}\n").unwrap();

        let curriculum = SkillDiagnostics::from_prebuilt_dir(Path::new(&root), "curriculum");
        let debate = SkillDiagnostics::from_prebuilt_dir(Path::new(&root), "debate");

        assert_eq!(curriculum.kind, SkillKind::MetaSkill);
        assert_eq!(debate.kind, SkillKind::MetaSkill);

        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn summarizes_evaluation_center_by_quality_and_tradition() {
        let mut rows = vec![
            row("huineng", "慧能大师", "汉传", true),
            row("zhiyi", "智者大师", "汉传", true),
            row("atisha", "阿底峡尊者", "藏传", true),
            row("ajahn-chah", "阿姜查", "南传", false),
        ];
        rows[0].fidelity_case_count = 12;
        rows[1].fidelity_case_count = 10;
        rows[2].fidelity_case_count = 0;
        rows[3].fidelity_case_count = 13;

        let summary = evaluation_summary(&rows);

        assert_eq!(summary.skill_count, 4);
        assert_eq!(summary.case_count, 35);
        assert_eq!(summary.ready_count, 2);
        assert_eq!(summary.attention_count, 1);
        assert_eq!(summary.missing_count, 1);
        assert_eq!(summary.missing_suite_count, 1);
        assert_eq!(
            summary.groups,
            vec![
                EvaluationGroup {
                    tradition: "南传".to_string(),
                    skill_count: 1,
                    case_count: 13,
                    missing_suite_count: 0,
                },
                EvaluationGroup {
                    tradition: "汉传".to_string(),
                    skill_count: 2,
                    case_count: 22,
                    missing_suite_count: 0,
                },
                EvaluationGroup {
                    tradition: "藏传".to_string(),
                    skill_count: 1,
                    case_count: 0,
                    missing_suite_count: 1,
                },
            ]
        );
    }
}
