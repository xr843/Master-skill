"""Every gate in `npm test` must be shown to FAIL on something it exists to catch.

This repo's recurring defect is a check that reports success having examined
nothing — `pytest.ini` missing a suite, an empty glob parametrizing zero cases,
a required job exiting 0 without a key, a validator whose guard short-circuits.
Each was found by a person, after shipping.

The suites already here assert that the gates pass on a healthy tree. That is
the half that cannot distinguish a working gate from an inert one. These assert
the other half: break the repository in a way the gate names as its job, and
the gate must go non-zero.

Each case copies the tree, applies one targeted mutation, and runs the real
script as a subprocess — the same way CI runs it, rather than importing a
function and hoping the CLI wires it up.

Writing these caught a mistake of my own, worth recording: the first version
emptied `fidelity.jsonl` and concluded `validate-persona-fidelity.py` was inert.
It validates `meta.json` fields and has nothing to do with that file. A
mis-aimed mutation makes a working gate look broken exactly as convincingly as
a real hole — so every case below names the contract it is aiming at.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
IGNORE = shutil.ignore_patterns(
    ".git", "desktop", "node_modules", "__pycache__", ".worktrees",
    ".pytest_cache", "*.tgz",
)


@pytest.fixture(scope="module")
def pristine(tmp_path_factory) -> Path:
    """One copy of the tree, reused as the source for each mutation."""
    target = tmp_path_factory.mktemp("pristine") / "repo"
    shutil.copytree(ROOT, target, ignore=IGNORE)
    return target


def _copy(pristine: Path, tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(pristine, repo, ignore=IGNORE)
    return repo


def _run(repo: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, f"scripts/{script}", *args],
        cwd=repo, capture_output=True, text=True, timeout=180,
    )


def _edit_json(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# (script, args, contract it is aiming at, mutation)
CASES = [
    (
        "validate.py", ("--strict",),
        "SKILL.md frontmatter must carry the declared keys",
        lambda r: (r / "prebuilt/master-huineng/SKILL.md").write_text(
            (r / "prebuilt/master-huineng/SKILL.md")
            .read_text(encoding="utf-8").replace("lineage:", "xlineage:", 1),
            encoding="utf-8",
        ),
    ),
    (
        "validate-routing.py", (),
        "routing.json must describe the real master/mode table",
        lambda r: (r / "routing.json").write_text('{"modes": {}}', encoding="utf-8"),
    ),
    (
        "check-manifest-versions.py", (),
        "the version must agree across every platform manifest",
        lambda r: _edit_json(r / "package.json", lambda d: d.__setitem__("version", "9.9.9")),
    ),
    (
        "validate-citation-references.py", (),
        "a persona must not instruct a citation its contract forbids",
        lambda r: (r / "prebuilt/master-huineng/SKILL.md").write_text(
            (r / "prebuilt/master-huineng/SKILL.md").read_text(encoding="utf-8")
            + "\n【《伪经》，Z99n9999】\n",
            encoding="utf-8",
        ),
    ),
    (
        "validate-fidelity.py", (),
        "every persona must ship gradeable fixtures",
        lambda r: (r / "prebuilt/master-huineng/tests/fidelity.jsonl").write_text("", encoding="utf-8"),
    ),
    (
        "validate-persona-fidelity.py", (),
        "signature_phrases must hold 3-7 entries",
        lambda r: _edit_json(
            r / "prebuilt/master-huineng/meta.json",
            lambda d: d.__setitem__("signature_phrases", ["一"]),
        ),
    ),
    (
        "validate-persona-fidelity.py", (),
        "style must carry exactly its three keys",
        lambda r: _edit_json(
            r / "prebuilt/master-huineng/meta.json",
            lambda d: d.get("style", {}).pop("qa", None),
        ),
    ),
    (
        "check-gate-liveness.py", (),
        "every skill must carry at least one fixture",
        lambda r: shutil.rmtree(r / "prebuilt/master-huineng/tests"),
    ),
    (
        "validate-fixture-terms.py", (),
        "a requirement may only be called undecidable with an adjudication behind it",
        # The laundering move this gate exists to stop: take an inconvenient
        # `must_mention` and reclassify it as `must_convey`, which the matcher
        # cannot decide. The build goes green and looks more rigorous.
        lambda r: _move_a_requirement_to_must_convey(
            r / "prebuilt/master-huineng/tests/fidelity.jsonl"
        ),
    ),
    (
        "verify-adjudication.py", (),
        "every verdict must quote text that is actually in the stored answer",
        lambda r: _forge_review_evidence(
            r / "eval/reports/adjudication-06b8142-deepseek.json"
        ),
    ),
    (
        "verify-adjudication.py", (),
        "the summary's case count must match the cases actually present",
        # Dropping the awkward rulings used to leave the file self-inconsistent
        # and the gate still printing OK — with a smaller number, in the same
        # sentence that says everything is backed.
        lambda r: _drop_a_case(r / "eval/reports/adjudication-06b8142-deepseek.json"),
    ),
    (
        "verify-adjudication.py", (),
        "deleting every adjudication is not the same as verifying clean",
        lambda r: [
            path.unlink()
            for path in (r / "eval/reports").glob("adjudication-*.json")
        ],
    ),
]


def _drop_a_case(adjudication: Path) -> None:
    data = json.loads(adjudication.read_text(encoding="utf-8"))
    data["cases"].pop(0)
    adjudication.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _move_a_requirement_to_must_convey(fixtures: Path) -> None:
    records = [
        json.loads(line)
        for line in fixtures.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for record in records:
        if record.get("must_mention"):
            record.setdefault("must_convey", []).append(record["must_mention"].pop(0))
            break
    else:  # pragma: no cover - the fixture set would have to change shape
        raise AssertionError("no must_mention requirement to move")
    fixtures.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )


def _forge_review_evidence(adjudication: Path) -> None:
    data = json.loads(adjudication.read_text(encoding="utf-8"))
    for case in data["cases"]:
        if case.get("review_evidence"):
            case["review_evidence"] = "这段文字在任何答案里都不存在 xyzzy"
            break
    else:  # pragma: no cover
        raise AssertionError("no case carries review_evidence")
    adjudication.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("script", "args", "contract", "mutate"), CASES,
    ids=[f"{c[0]}::{c[2][:40]}" for c in CASES],
)
def test_the_gate_fails_when_its_contract_is_broken(
    pristine, tmp_path, script, args, contract, mutate
):
    repo = _copy(pristine, tmp_path)

    healthy = _run(repo, script, *args)
    assert healthy.returncode == 0, (
        f"{script} is already failing on an unmodified tree, so this case "
        f"proves nothing:\n{healthy.stdout}\n{healthy.stderr}"
    )

    mutate(repo)
    broken = _run(repo, script, *args)
    assert broken.returncode != 0, (
        f"{script} still exits 0 after breaking: {contract}\n"
        f"{broken.stdout}\n{broken.stderr}"
    )


def test_every_gate_in_npm_test_has_a_case_here():
    """A gate added to the chain without one of these is the gap, not an oversight."""
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    chain = package["scripts"]["test"]
    invoked = {
        part.split("/")[-1]
        for part in chain.split()
        if part.startswith("scripts/") and part.endswith(".py")
    }
    covered = {c[0] for c in CASES}
    # test-fidelity.py is the paid grader; it is exercised by its own suite and
    # cannot be driven here without an API key.
    exempt = {"test-fidelity.py"}
    missing = sorted(invoked - covered - exempt)
    assert missing == [], (
        f"these gates run in `npm test` with nothing proving they can fail: {missing}"
    )


def test_an_empty_adjudication_set_can_be_declared(pristine, tmp_path):
    """The empty-set guard must stay escapable, or a fresh tree cannot pass.

    A repository that genuinely has not adjudicated anything is a real state;
    what must not be silent is arriving there by deleting the file that was
    inconvenient. The declaration is the difference.
    """
    repo = _copy(pristine, tmp_path)
    for path in (repo / "eval" / "reports").glob("*.json"):
        path.unlink()

    result = subprocess.run(
        [sys.executable, "scripts/verify-adjudication.py"],
        cwd=repo, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
