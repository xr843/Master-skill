#!/usr/bin/env python3
"""Validate tests/persona/*.promptfooconfig.yaml against repo conventions.

This validator complements `promptfoo validate` (which checks the upstream
schema). It enforces Master-skill specific contracts that promptfoo cannot
know about:

  - Filename convention: tests/persona/<slug>.promptfooconfig.yaml — <slug>
    must match a real master under prebuilt/master-<slug>/.
  - Test coverage: at least 4 tests, each with a `description` prefixed by
    one of "RAW:", "SPE:", or "CUS:" — and all three dimensions must appear
    at least once.
  - Each test must carry at least one `llm-rubric` assertion (otherwise it
    isn't actually grading persona fidelity).
  - Any `contains-any` assertion value must be drawn from a known
    fidelity-anchor set for that master — currently the master's own
    `signature_phrases` plus a short curated whitelist per master
    (Pāli term variants, common gloss spellings, etc.). This blocks the
    drift mode where a tester slips in arbitrary keywords and the rubric
    silently passes on noise.
  - The inlined prompt string in each promptfooconfig must match the
    corresponding template key inside tests/persona/shared.yaml (after
    whitespace normalisation). shared.yaml is the source of truth; the
    inlining is a promptfoo limitation (no `file://shared.yaml#key`
    indirection at the time of writing).

Run:
    python3 scripts/validate-promptfoo-configs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PREBUILT_DIR = REPO_ROOT / "prebuilt"
PERSONA_DIR = REPO_ROOT / "tests" / "persona"

# Per-master whitelist additions on top of signature_phrases.
# Keep this list short and curated — every entry is justified by
# language/script variation, not arbitrary keywords.
EXTRA_ALLOWED_CONTAINS: dict[str, set[str]] = {
    "huineng": {
        "顿",            # short form of 顿悟
        "本来面目",      # Tan Jing canonical line, not in signature_phrases
        "无念",          # short form of 无念为宗
        "自性",          # short form of 何期自性 — core southern-school term
        "见性",          # short form of 明心见性
    },
    "ajahn-chah": {
        # Pāli term + diacritic / spelling variants
        "sila",
        "sīla",
        "virtue",
        "precepts",
        "moral conduct",
        # Plain-English signature reformulations
        "letting go",
        "let go",
        "mindfulness",
        "the heart",
        "the middle way",
        "as they are",
    },
    "tsongkhapa": {
        "应成",          # short form of 应成中观
        "空性",          # core Gelug-Madhyamaka term (in 三主要道 list)
    },
}


# -----------------------------------------------------------------------------
# Minimal YAML loader (no PyYAML dependency to keep CI surface small)
# -----------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load a YAML file. Prefers PyYAML if available; otherwise calls a
    bundled JSON-via-Python fallback. Persona configs are simple enough
    that PyYAML is reliable when present, and CI installs it already
    (see .github/workflows/validate-and-test.yml -> `pip install ... pyyaml`).
    """
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PyYAML is required to validate promptfoo configs. "
            "Install with: pip install pyyaml"
        ) from exc
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: top-level YAML must be a mapping")
    return data


# -----------------------------------------------------------------------------
# Master metadata helpers
# -----------------------------------------------------------------------------

def _load_master_meta(slug: str) -> dict | None:
    path = PREBUILT_DIR / f"master-{slug}" / "meta.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _allowed_contains_values(slug: str, meta: dict) -> set[str]:
    """Build the whitelist of allowed `contains-any` values for this master."""
    allowed: set[str] = set()
    phrases = meta.get("signature_phrases", [])
    if isinstance(phrases, list):
        allowed.update(p for p in phrases if isinstance(p, str) and p.strip())
    allowed.update(EXTRA_ALLOWED_CONTAINS.get(slug, set()))
    return allowed


# -----------------------------------------------------------------------------
# shared.yaml prompt key resolution
# -----------------------------------------------------------------------------

SHARED_KEY_MAP = {
    "huineng": "huineng_persona_prompt",
    "ajahn-chah": "ajahn_chah_persona_prompt",
    "tsongkhapa": "tsongkhapa_persona_prompt",
}


def _normalise(text: str) -> str:
    """Collapse trailing whitespace per line + trim outer blanks for diffing."""
    lines = [line.rstrip() for line in text.splitlines()]
    # drop leading/trailing all-blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _check_prompt_sync(slug: str, cfg: dict, shared: dict) -> list[str]:
    errors: list[str] = []
    key = SHARED_KEY_MAP.get(slug)
    if key is None:
        # Unknown master — we still require it appears in shared.yaml under
        # a deterministic name. Skip sync check but warn.
        errors.append(
            f"{slug}: no entry in SHARED_KEY_MAP — add the master's prompt to "
            f"shared.yaml and update validate-promptfoo-configs.py."
        )
        return errors
    if key not in shared:
        errors.append(f"{slug}: shared.yaml missing key '{key}'")
        return errors
    shared_text = shared[key]
    prompts = cfg.get("prompts", [])
    if not prompts or not isinstance(prompts, list):
        errors.append(f"{slug}: promptfooconfig has no `prompts:` list")
        return errors
    inlined = prompts[0]
    if not isinstance(inlined, str):
        errors.append(f"{slug}: first prompt is not an inlined string")
        return errors
    if _normalise(inlined) != _normalise(shared_text):
        errors.append(
            f"{slug}: inlined prompt does not match shared.yaml#{key} "
            f"(update either side to re-sync)"
        )
    # The prompt template MUST reference {{question}} — without it, every
    # test case gets the same input and the eval is meaningless. Easy footgun
    # when a contributor copies a prompt and forgets to wire vars through.
    if "{{question}}" not in inlined:
        errors.append(
            f"{slug}: inlined prompt does not reference '{{{{question}}}}' — "
            f"vars.question would never be injected, rendering tests no-ops"
        )
    return errors


# -----------------------------------------------------------------------------
# Per-config checks
# -----------------------------------------------------------------------------

DIM_PREFIXES = ("RAW:", "SPE:", "CUS:")


def _check_filename_and_slug(path: Path) -> tuple[str | None, list[str]]:
    name = path.name
    suffix = ".promptfooconfig.yaml"
    if not name.endswith(suffix):
        return None, [f"{name}: filename must end with '{suffix}'"]
    slug = name[: -len(suffix)]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", slug):
        return None, [
            f"{name}: slug '{slug}' must be lowercase letters / digits / "
            f"hyphen, starting with a letter"
        ]
    if not (PREBUILT_DIR / f"master-{slug}").is_dir():
        return slug, [
            f"{name}: no matching master at prebuilt/master-{slug}/"
        ]
    return slug, []


def _check_tests(slug: str, cfg: dict, allowed_contains: set[str]) -> list[str]:
    errors: list[str] = []
    tests = cfg.get("tests")
    if not isinstance(tests, list) or not tests:
        return [f"{slug}: `tests:` must be a non-empty list"]
    if len(tests) < 4:
        errors.append(
            f"{slug}: at least 4 tests required, got {len(tests)}"
        )
    seen_dims: set[str] = set()
    for i, t in enumerate(tests):
        prefix = f"{slug}.tests[{i}]"
        if not isinstance(t, dict):
            errors.append(f"{prefix}: entry must be a mapping")
            continue
        desc = t.get("description", "")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"{prefix}: description must be a non-blank string")
        else:
            matched_dim = None
            for dp in DIM_PREFIXES:
                if desc.startswith(dp):
                    matched_dim = dp.rstrip(":")
                    break
            if matched_dim is None:
                errors.append(
                    f"{prefix}: description must start with one of "
                    f"{', '.join(DIM_PREFIXES)} — got {desc!r}"
                )
            else:
                seen_dims.add(matched_dim)
        # vars present?
        if "vars" not in t or not isinstance(t["vars"], dict):
            errors.append(f"{prefix}: missing `vars:` mapping")
        elif not t["vars"].get("question"):
            errors.append(f"{prefix}: vars.question must be set (non-empty)")
        # assertions
        asserts = t.get("assert", [])
        if not isinstance(asserts, list) or not asserts:
            errors.append(f"{prefix}: `assert:` must be a non-empty list")
            continue
        has_rubric = False
        for j, a in enumerate(asserts):
            apath = f"{prefix}.assert[{j}]"
            if not isinstance(a, dict):
                errors.append(f"{apath}: entry must be a mapping")
                continue
            atype = a.get("type")
            if atype == "llm-rubric":
                has_rubric = True
                value = a.get("value")
                if not isinstance(value, str) or len(value.strip()) < 10:
                    errors.append(
                        f"{apath}: llm-rubric.value must be a non-trivial "
                        f"string (>= 10 chars)"
                    )
            elif atype in ("contains-any", "icontains-any"):
                vals = a.get("value")
                if not isinstance(vals, list) or not vals:
                    errors.append(
                        f"{apath}: {atype}.value must be a non-empty list"
                    )
                else:
                    for v in vals:
                        if not isinstance(v, str):
                            errors.append(
                                f"{apath}: {atype}.value entries must be "
                                f"strings (got {type(v).__name__})"
                            )
                            continue
                        if v not in allowed_contains:
                            errors.append(
                                f"{apath}: {atype}.value entry "
                                f"{v!r} is not in {slug}'s fidelity anchors "
                                f"(signature_phrases + curated extras). "
                                f"Add it to meta.json or to "
                                f"EXTRA_ALLOWED_CONTAINS if intentional."
                            )
            elif atype in (None, ""):
                errors.append(f"{apath}: missing `type:`")
            # Other deterministic assertion types are allowed but not required.
        if not has_rubric:
            errors.append(
                f"{prefix}: must have at least one llm-rubric assertion"
            )
    # All three dimensions must appear at least once
    for dim in ("RAW", "SPE", "CUS"):
        if dim not in seen_dims:
            errors.append(
                f"{slug}: missing dimension '{dim}' — every persona config "
                f"must cover RAW + SPE + CUS"
            )
    return errors


def _check_providers(slug: str, cfg: dict) -> list[str]:
    errors: list[str] = []
    providers = cfg.get("providers")
    if not isinstance(providers, list) or not providers:
        return [f"{slug}: `providers:` must be a non-empty list"]
    first = providers[0]
    if not isinstance(first, dict) or not first.get("id"):
        errors.append(f"{slug}: providers[0] must be a mapping with an `id`")
    # default judge provider
    default_test = cfg.get("defaultTest", {})
    judge = (
        default_test.get("options", {}).get("provider")
        if isinstance(default_test, dict) else None
    )
    if not judge:
        errors.append(
            f"{slug}: defaultTest.options.provider must be set "
            f"(the llm-rubric judge model)"
        )
    return errors


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def validate(persona_dir: Path = PERSONA_DIR) -> list[str]:
    """Return a flat list of error strings; empty list means OK."""
    errors: list[str] = []
    if not persona_dir.exists():
        return [f"tests/persona/ directory does not exist at {persona_dir}"]
    shared_path = persona_dir / "shared.yaml"
    if not shared_path.exists():
        errors.append("tests/persona/shared.yaml is missing")
        shared: dict = {}
    else:
        try:
            shared = _load_yaml(shared_path)
        except Exception as exc:
            errors.append(f"shared.yaml: failed to parse — {exc}")
            shared = {}
    configs = sorted(persona_dir.glob("*.promptfooconfig.yaml"))
    if not configs:
        errors.append(
            "tests/persona/: no *.promptfooconfig.yaml files found"
        )
        return errors
    for cfg_path in configs:
        slug, fname_errs = _check_filename_and_slug(cfg_path)
        errors.extend(fname_errs)
        if slug is None or fname_errs:
            continue
        meta = _load_master_meta(slug)
        if meta is None:
            errors.append(
                f"{slug}: meta.json not found at prebuilt/master-{slug}/"
            )
            continue
        try:
            cfg = _load_yaml(cfg_path)
        except Exception as exc:
            errors.append(f"{slug}: failed to parse YAML — {exc}")
            continue
        allowed = _allowed_contains_values(slug, meta)
        errors.extend(_check_providers(slug, cfg))
        errors.extend(_check_tests(slug, cfg, allowed))
        if shared:
            errors.extend(_check_prompt_sync(slug, cfg, shared))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"{len(errors)} promptfoo-config error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
        return 1
    print("promptfoo configs OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
