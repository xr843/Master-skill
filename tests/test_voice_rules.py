"""Tests for voice.md identity-neutral rules (首轮身份中立原则).

Verifies:
1. Every voice.md contains the 首轮身份中立原则 rule in Layer 0
2. Every voice.md's 开场方式 and 称呼方式 sections are tiered into 首轮中立 / 身份已知后
3. The 首轮中立 section does NOT contain identity-assuming address terms

A fourth case asserted SKILL.md inlined voice.md as "PART B". The v0.3
rebuild (937b642, 88debde) moved masters to progressive disclosure —
SKILL.md now points at references/voice.md instead of inlining it, and
the PART B marker exists in no file — so that case, and the
tools/sync_skill_from_voice.py it pointed at, were dropped.
"""

from pathlib import Path
import pytest

PREBUILT_DIR = Path(__file__).parent.parent / "prebuilt"

# Identity-assuming terms forbidden in first-turn sections
IDENTITY_TERMS = [
    "居士", "善信", "行者", "学人",
    "善男子", "善女人", "出家人", "师父",
    "大众", "道友",
]

# Get all master slugs that have a voice.md. It lives under references/;
# globbing prebuilt/<slug>/voice.md matched nothing, so every case below
# was parametrized over an empty set and skipped — this file asserted
# nothing at all while reporting green.
MASTER_SLUGS = sorted([
    d.name for d in PREBUILT_DIR.iterdir()
    if d.is_dir() and (d / "references" / "voice.md").exists()
])

# An empty parameter set skips instead of failing, which is how the wrong
# path above stayed invisible. Refuse to run rather than report a silent pass.
assert MASTER_SLUGS, (
    f"no prebuilt master has references/voice.md under {PREBUILT_DIR} — "
    "voice rules would be silently unchecked"
)


@pytest.fixture(params=MASTER_SLUGS)
def slug(request):
    return request.param


@pytest.fixture
def voice_content(slug):
    return (PREBUILT_DIR / slug / "references" / "voice.md").read_text(encoding="utf-8")


def test_layer0_contains_neutrality_rule(slug, voice_content):
    """Every voice.md Layer 0 must contain 首轮身份中立原则."""
    assert "首轮身份中立原则" in voice_content, (
        f"{slug}/voice.md missing 首轮身份中立原则 rule in Layer 0"
    )


def test_opening_section_is_tiered(slug, voice_content):
    """开场方式 must have both 首轮中立开场 and 后续开场 sub-headers."""
    assert "首轮中立开场" in voice_content, (
        f"{slug}/voice.md 开场方式 missing 首轮中立开场 subsection"
    )
    assert "后续开场" in voice_content, (
        f"{slug}/voice.md 开场方式 missing 后续开场 subsection"
    )


def test_address_section_is_tiered(slug, voice_content):
    """称呼方式 must have both 首轮中立称呼 and 身份已知后 sub-headers."""
    assert "首轮中立称呼" in voice_content, (
        f"{slug}/voice.md 称呼方式 missing 首轮中立称呼 subsection"
    )
    assert "身份已知后" in voice_content, (
        f"{slug}/voice.md 称呼方式 missing 身份已知后 subsection"
    )


def _extract_section(content: str, start_marker: str, end_marker: str) -> str:
    """Extract text between two markers."""
    start = content.find(start_marker)
    if start == -1:
        return ""
    end = content.find(end_marker, start + len(start_marker))
    if end == -1:
        return content[start:]
    return content[start:end]


def test_neutral_opening_has_no_identity_terms(slug, voice_content):
    """首轮中立开场 section must not contain identity-assuming terms."""
    section = _extract_section(
        voice_content,
        "**首轮中立开场**",
        "**后续开场**",
    )
    assert section, f"{slug}: could not extract 首轮中立开场 section"

    violations = [term for term in IDENTITY_TERMS if term in section]
    assert not violations, (
        f"{slug}/voice.md 首轮中立开场 contains forbidden identity terms: {violations}\n"
        f"Section content:\n{section}"
    )


def test_neutral_address_has_no_identity_terms(slug, voice_content):
    """首轮中立称呼 section must not contain identity-assuming terms."""
    section = _extract_section(
        voice_content,
        "**首轮中立称呼**",
        "**身份已知后**",
    )
    assert section, f"{slug}: could not extract 首轮中立称呼 section"

    violations = [term for term in IDENTITY_TERMS if term in section]
    assert not violations, (
        f"{slug}/voice.md 首轮中立称呼 contains forbidden identity terms: {violations}\n"
        f"Section content:\n{section}"
    )


