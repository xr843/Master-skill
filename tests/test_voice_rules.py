"""Tests for voice.md identity-neutral rules (首轮身份中立原则).

Verifies:
1. Every voice.md contains the 首轮身份中立原则 rule in Layer 0
2. Every voice.md's 开场方式 and 称呼方式 sections are tiered into 首轮中立 / 身份已知后
3. The 首轮中立 sections exclude persona-specific terms declared in Layer 0
4. Every SKILL.md routes to voice.md and summarizes the first-turn rule
"""

import re
from pathlib import Path
import pytest

PREBUILT_DIR = Path(__file__).parent.parent / "prebuilt"

# Get all master slugs that have a voice.md
MASTER_SLUGS = sorted([
    d.name for d in PREBUILT_DIR.iterdir()
    if d.is_dir() and (d / "references" / "voice.md").exists()
])


def _extract_heading_section(content: str, level: int, title: str) -> str:
    """Extract one Markdown heading region up to the next peer/parent heading."""
    heading = re.compile(
        rf"^{'#' * level}\s+{re.escape(title)}(?=$|[\s：:（(]).*$",
        re.MULTILINE,
    )
    match = heading.search(content)
    if match is None:
        return ""
    boundary = re.compile(rf"^#{{1,{level}}}\s+", re.MULTILINE)
    next_heading = boundary.search(content, match.end())
    end = next_heading.start() if next_heading else len(content)
    return content[match.end():end]


def _extract_section(content: str, start_marker: str, end_marker: str) -> str:
    """Extract text between two markers within an already scoped region."""
    start = content.find(start_marker)
    if start == -1:
        return ""
    end = content.find(end_marker, start + len(start_marker))
    if end == -1:
        return content[start:]
    return content[start:end]


def _forbidden_identity_terms(content: str) -> list[str]:
    """Derive this persona's first-turn prohibitions from its Layer 0 rule."""
    layer0 = _extract_heading_section(content, 2, "Layer 0")
    neutrality_lines = [
        line for line in layer0.splitlines() if "首轮身份中立原则" in line
    ]
    if len(neutrality_lines) != 1:
        return []
    match = re.search(
        r"(?:禁用于首轮的称谓|禁用首轮称谓|第一轮禁用)[：:]([^。]+)",
        neutrality_lines[0],
    )
    if match is None:
        return []

    terms = []
    for raw_term in re.split(r"[、，,]", match.group(1)):
        term = re.sub(r"[（(][^）)]*[）)]", "", raw_term).strip(" `*_\"'：:")
        if term:
            terms.append(term)
    return terms


def _neutral_opening_section(content: str) -> str:
    opening = _extract_heading_section(content, 3, "开场方式")
    return _extract_section(opening, "**首轮中立开场**", "**后续开场**")


def _neutral_address_section(content: str) -> str:
    address = _extract_heading_section(content, 3, "称呼方式")
    start_marker = (
        "**首轮中立称呼**"
        if "**首轮中立称呼**" in address
        else "**首轮中立**"
    )
    return _extract_section(address, start_marker, "**身份已知后**")


def _identity_violations(section: str, content: str) -> list[str]:
    return [term for term in _forbidden_identity_terms(content) if term in section]


def _neutral_opening_violations(content: str) -> list[str]:
    return _identity_violations(_neutral_opening_section(content), content)


def _neutral_address_violations(content: str) -> list[str]:
    return _identity_violations(_neutral_address_section(content), content)


@pytest.fixture(params=MASTER_SLUGS)
def slug(request):
    return request.param


@pytest.fixture
def voice_content(slug):
    return (PREBUILT_DIR / slug / "references" / "voice.md").read_text(
        encoding="utf-8"
    )


@pytest.fixture
def skill_content(slug):
    return (PREBUILT_DIR / slug / "SKILL.md").read_text(encoding="utf-8")


def test_voice_persona_discovery_is_complete():
    assert len(MASTER_SLUGS) == 15, MASTER_SLUGS


def test_layer0_contains_neutrality_rule(slug, voice_content):
    """Every voice.md Layer 0 must contain 首轮身份中立原则."""
    layer0 = _extract_heading_section(voice_content, 2, "Layer 0")
    assert layer0, f"{slug}/voice.md missing Layer 0 heading"
    assert "首轮身份中立原则" in layer0, (
        f"{slug}/voice.md missing 首轮身份中立原则 rule in Layer 0"
    )
    assert _forbidden_identity_terms(voice_content), (
        f"{slug}/voice.md Layer 0 does not declare parseable first-turn prohibitions"
    )


def test_opening_section_is_tiered(slug, voice_content):
    """开场方式 must have both 首轮中立开场 and 后续开场 sub-headers."""
    opening = _extract_heading_section(voice_content, 3, "开场方式")
    assert opening, f"{slug}/voice.md missing 开场方式 heading"
    assert "首轮中立开场" in opening, (
        f"{slug}/voice.md 开场方式 missing 首轮中立开场 subsection"
    )
    assert "后续开场" in opening, (
        f"{slug}/voice.md 开场方式 missing 后续开场 subsection"
    )


def test_address_section_is_tiered(slug, voice_content):
    """称呼方式 must have both 首轮中立称呼 and 身份已知后 sub-headers."""
    address = _extract_heading_section(voice_content, 3, "称呼方式")
    assert address, f"{slug}/voice.md missing 称呼方式 heading"
    assert (
        "**首轮中立称呼**" in address
        or "**首轮中立**" in address
    ), (
        f"{slug}/voice.md 称呼方式 missing 首轮中立称呼 subsection"
    )
    assert "身份已知后" in address, (
        f"{slug}/voice.md 称呼方式 missing 身份已知后 subsection"
    )


def test_neutral_opening_has_no_identity_terms(slug, voice_content):
    """首轮中立开场 section must not contain identity-assuming terms."""
    section = _neutral_opening_section(voice_content)
    assert section, f"{slug}: could not extract 首轮中立开场 section"

    violations = _neutral_opening_violations(voice_content)
    assert not violations, (
        f"{slug}/voice.md 首轮中立开场 contains forbidden identity terms: {violations}\n"
        f"Section content:\n{section}"
    )


def test_neutral_address_has_no_identity_terms(slug, voice_content):
    """首轮中立称呼 section must not contain identity-assuming terms."""
    section = _neutral_address_section(voice_content)
    assert section, f"{slug}: could not extract 首轮中立称呼 section"

    violations = _neutral_address_violations(voice_content)
    assert not violations, (
        f"{slug}/voice.md 首轮中立称呼 contains forbidden identity terms: {violations}\n"
        f"Section content:\n{section}"
    )


def test_skill_md_routes_to_voice_reference(slug, skill_content):
    assert "references/voice.md" in skill_content
    assert "首轮身份中立" in skill_content


def test_neutrality_rule_must_be_inside_layer0_heading():
    content = """\
## Layer 0：硬规则（最高优先级）

- 其他规则

## Layer 1：身份

- **首轮身份中立原则**：第一轮禁用：弟子。首轮用：您。
"""

    layer0 = _extract_heading_section(content, 2, "Layer 0")

    assert "首轮身份中立原则" not in layer0


def test_opening_marker_must_be_inside_opening_heading():
    content = """\
### 开场方式

没有首轮 marker。

### 称呼方式

**首轮中立开场**：放错位置
"""

    opening = _extract_heading_section(content, 3, "开场方式")

    assert "首轮中立开场" not in opening


def test_address_marker_must_be_inside_address_heading():
    content = """\
### 开场方式

**首轮中立称呼**：放错位置

### 称呼方式

没有首轮 marker。
"""

    address = _extract_heading_section(content, 3, "称呼方式")

    assert "首轮中立称呼" not in address


@pytest.mark.parametrize(
    ("slug", "term"),
    [
        ("master-milarepa", "金刚兄弟"),
        ("master-atisha", "弟子"),
        ("master-mahasi-sayadaw", "禅修者"),
        ("master-ajahn-chah", "优婆塞"),
    ],
)
def test_forbidden_terms_are_derived_from_each_personas_layer0(slug, term):
    content = (PREBUILT_DIR / slug / "references" / "voice.md").read_text(
        encoding="utf-8"
    )

    assert term in _forbidden_identity_terms(content)


def test_tibetan_opening_mutation_detects_persona_specific_term():
    content = (
        PREBUILT_DIR / "master-milarepa" / "references" / "voice.md"
    ).read_text(encoding="utf-8")
    mutated = content.replace(
        "**首轮中立开场**：",
        "**首轮中立开场**：\n- \"金刚兄弟，且听一歌……\"",
        1,
    )

    assert "金刚兄弟" in _neutral_opening_violations(mutated)


def test_theravada_address_mutation_detects_persona_specific_term():
    content = (
        PREBUILT_DIR / "master-mahasi-sayadaw" / "references" / "voice.md"
    ).read_text(encoding="utf-8")
    mutated = content.replace(
        "**首轮中立**：",
        "**首轮中立**：禅修者 / ",
        1,
    )

    assert "禅修者" in _neutral_address_violations(mutated)
