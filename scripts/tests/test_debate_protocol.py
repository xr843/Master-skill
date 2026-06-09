"""Tests for master-debate meta.json debate_protocol schema.

Verifies:
  1. master-debate/meta.json exists, has a `debate_protocol` object
  2. Required scalar fields with valid types + sane ranges
  3. min_rounds <= default_rounds <= max_rounds
  4. per_pair_overrides keys are <slug_a>-vs-<slug_b> with both slugs being
     real masters under prebuilt/
  5. Each pair listed in per_pair_overrides is also covered bidirectionally
     by cross_critique (i.e. the per-pair list does not invent debate pairs
     that v0.7.1 didn't actually arm with ammo)
  6. per_pair_overrides values have valid default_rounds in
     [debate_protocol.min_rounds, debate_protocol.max_rounds]
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PREBUILT = REPO_ROOT / "prebuilt"
DEBATE_META = PREBUILT / "master-debate" / "meta.json"


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def debate_meta():
    assert DEBATE_META.exists(), f"missing {DEBATE_META}"
    return _load_json(DEBATE_META)


@pytest.fixture(scope="module")
def protocol(debate_meta):
    proto = debate_meta.get("debate_protocol")
    assert isinstance(proto, dict), "debate_protocol must be an object"
    return proto


@pytest.fixture(scope="module")
def known_slugs():
    return {p.parent.name.removeprefix("master-")
            for p in PREBUILT.glob("master-*/meta.json")}


def test_protocol_required_scalars(protocol):
    for key, typ in [
        ("default_rounds", int),
        ("max_rounds", int),
        ("min_rounds", int),
        ("selector", str),
        ("stop_on_consensus", bool),
        ("subagent_isolation", bool),
        ("moderator_summary", bool),
    ]:
        assert key in protocol, f"missing debate_protocol.{key}"
        assert isinstance(protocol[key], typ), (
            f"debate_protocol.{key} must be {typ.__name__}, "
            f"got {type(protocol[key]).__name__}"
        )


def test_protocol_round_ranges(protocol):
    min_r = protocol["min_rounds"]
    def_r = protocol["default_rounds"]
    max_r = protocol["max_rounds"]
    assert min_r >= 1, "min_rounds must be >= 1"
    assert min_r <= def_r <= max_r, (
        f"require min_rounds <= default_rounds <= max_rounds, "
        f"got {min_r} <= {def_r} <= {max_r}"
    )
    assert max_r <= 10, "max_rounds sanity cap"


def test_protocol_selector_alternating(protocol):
    assert protocol["selector"] == "alternating", (
        "v0.8 only ships alternating selector"
    )


def test_protocol_subagent_isolation_on(protocol):
    assert protocol["subagent_isolation"] is True, (
        "v0.8 requires subagent_isolation=true (the whole point of the refactor)"
    )


def test_per_pair_overrides_is_object(protocol):
    overrides = protocol.get("per_pair_overrides")
    assert isinstance(overrides, dict), (
        "debate_protocol.per_pair_overrides must be an object"
    )


def test_per_pair_keys_well_formed_and_real_slugs(protocol, known_slugs):
    overrides = protocol["per_pair_overrides"]
    for key in overrides:
        assert "-vs-" in key, f"per-pair key '{key}' must contain '-vs-'"
        parts = key.split("-vs-")
        assert len(parts) == 2, f"per-pair key '{key}' must split into exactly 2 slugs"
        a, b = parts
        assert a != b, f"per-pair key '{key}' self-pair"
        assert a in known_slugs, f"per-pair key '{key}': slug '{a}' not a known master"
        assert b in known_slugs, f"per-pair key '{key}': slug '{b}' not a known master"


def test_per_pair_keys_are_alphabetically_sorted(protocol):
    """SKILL.md tells the orchestrator to compute the lookup key by sorting
    the two slugs alphabetically. If a key here isn't sorted, the orchestrator
    silently misses the override. Lock the convention in."""
    for key in protocol["per_pair_overrides"]:
        a, b = key.split("-vs-", 1)
        assert a < b, (
            f"per-pair key '{key}' must be alphabetically sorted "
            f"('{a}' < '{b}'); orchestrators compute the key by sorting slugs."
        )


def test_per_pair_default_rounds_in_protocol_range(protocol):
    min_r = protocol["min_rounds"]
    max_r = protocol["max_rounds"]
    for key, val in protocol["per_pair_overrides"].items():
        assert isinstance(val, dict), f"override for '{key}' must be object"
        dr = val.get("default_rounds")
        assert isinstance(dr, int), f"override '{key}'.default_rounds must be int"
        assert min_r <= dr <= max_r, (
            f"override '{key}'.default_rounds={dr} out of "
            f"[{min_r}, {max_r}]"
        )


def test_per_pair_overrides_cross_critique_covered(protocol):
    """Each per-pair override must correspond to a pair both directions of
    which appear in cross_critique entries — otherwise the override would
    fire a debate the v0.7.1 ammo system didn't arm."""
    overrides = protocol["per_pair_overrides"]

    # Build {(src, tgt)} set from all cross_critique entries.
    pairs = set()
    for meta_path in PREBUILT.glob("master-*/meta.json"):
        src = meta_path.parent.name.removeprefix("master-")
        data = _load_json(meta_path)
        for e in data.get("cross_critique", []) or []:
            tgt = e.get("target_master")
            if isinstance(tgt, str):
                pairs.add((src, tgt))

    for key in overrides:
        a, b = key.split("-vs-", 1)
        assert (a, b) in pairs, (
            f"override '{key}': cross_critique missing direction {a}→{b}"
        )
        assert (b, a) in pairs, (
            f"override '{key}': cross_critique missing direction {b}→{a}"
        )
