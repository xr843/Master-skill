use master_skill_desktop::model::{DoctorReport, MasterInspect, SkillInventory};

#[test]
fn parses_skill_inventory_json_contract() {
    let payload = r#"
    {
      "count": 1,
      "masters": [
        {
          "name": "master-huineng",
          "slug": "huineng",
          "description": "Chan master"
        }
      ]
    }
    "#;

    let inventory: SkillInventory = serde_json::from_str(payload).unwrap();

    assert_eq!(inventory.count, 1);
    assert_eq!(inventory.masters[0].name, "master-huineng");
    assert_eq!(inventory.masters[0].slug, "huineng");
}

#[test]
fn parses_doctor_json_contract() {
    let payload = r#"
    {
      "packageVersion": "0.9.1",
      "nodeVersion": "v22.22.0",
      "prebuiltPath": "/repo/prebuilt",
      "skillsPath": "/home/user/.claude/skills",
      "availableSkills": 17,
      "installedKnownSkills": 15,
      "otherInstalledSkillDirs": 2,
      "status": "ok",
      "problems": []
    }
    "#;

    let report: DoctorReport = serde_json::from_str(payload).unwrap();

    assert_eq!(report.package_version, "0.9.1");
    assert_eq!(report.available_skills, 17);
    assert_eq!(report.installed_known_skills, 15);
    assert!(report.problems.is_empty());
}

#[test]
fn parses_inspect_json_contract() {
    let payload = r#"
    {
      "name": "master-huineng",
      "displayName": "慧能大师",
      "slug": "huineng",
      "version": "0.5.0",
      "tradition": "汉传",
      "school": "禅宗",
      "era": "638-713",
      "installed": true,
      "liveGrounding": true,
      "citationFormat": "【《{title}》{section}，{cbeta_id}】",
      "sources": ["T48n2008 — 六祖大师法宝坛经"],
      "searchKeywords": ["自性", "顿悟"]
    }
    "#;

    let inspect: MasterInspect = serde_json::from_str(payload).unwrap();

    assert_eq!(inspect.name, "master-huineng");
    assert_eq!(inspect.display_name.as_deref(), Some("慧能大师"));
    assert_eq!(inspect.tradition.as_deref(), Some("汉传"));
    assert!(inspect.installed);
    assert!(inspect.live_grounding);
    assert_eq!(inspect.sources.len(), 1);
}
