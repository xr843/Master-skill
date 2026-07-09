use crate::model::{MasterInspect, SkillSummary};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum InstallFilter {
    All,
    Installed,
    Missing,
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
        }
    }

    pub fn title(&self) -> &str {
        self.display_name.as_deref().unwrap_or(&self.name)
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
    use super::{filter_rows, tradition_options, InstallFilter, SkillRow};

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
}
