use serde::Deserialize;

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct SkillInventory {
    pub count: usize,
    #[serde(default)]
    pub masters: Vec<SkillSummary>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct SkillSummary {
    pub name: String,
    pub slug: String,
    pub description: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct DoctorReport {
    #[serde(rename = "packageVersion")]
    pub package_version: String,
    #[serde(rename = "nodeVersion")]
    pub node_version: String,
    #[serde(rename = "prebuiltPath")]
    pub prebuilt_path: String,
    #[serde(rename = "skillsPath")]
    pub skills_path: String,
    #[serde(rename = "availableSkills")]
    pub available_skills: usize,
    #[serde(rename = "installedKnownSkills")]
    pub installed_known_skills: usize,
    #[serde(rename = "otherInstalledSkillDirs")]
    pub other_installed_skill_dirs: isize,
    pub status: String,
    #[serde(default)]
    pub problems: Vec<DoctorProblem>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct DoctorProblem {
    pub code: String,
    pub name: String,
    pub message: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
pub struct MasterInspect {
    pub name: String,
    #[serde(rename = "displayName")]
    pub display_name: Option<String>,
    pub slug: String,
    pub version: Option<String>,
    pub tradition: Option<String>,
    pub school: Option<String>,
    pub era: Option<String>,
    pub installed: bool,
    #[serde(rename = "liveGrounding")]
    pub live_grounding: bool,
    #[serde(rename = "citationFormat")]
    pub citation_format: Option<String>,
    #[serde(default)]
    pub sources: Vec<String>,
    #[serde(rename = "searchKeywords", default)]
    pub search_keywords: Vec<String>,
}
