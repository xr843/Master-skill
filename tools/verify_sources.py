#!/usr/bin/env python3
"""
Validate declared persona source manifests, or audit legacy FoJin links.

Discovers CBETA IDs from meta.json sources and fojin.app URLs in markdown
files, then verifies each against FoJin's API and maps to internal text_ids.

Key insight: meta.json and URLs use the full CBETA catalog format (e.g.
T08n0235) while FoJin internally uses a shorter cbeta_id (e.g. T0235).
This script handles the conversion.

Offline modes validate family identifiers, declared membership, and citation
contracts. They do not parse free-text citations or check HTTP reachability.
The legacy no-argument / --fix modes only audit repository CBETA/FoJin URLs.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Allow importing fojin_bridge from tools/
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fojin_bridge import create_bridge
from skill_writer import derive_citation_contract


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PREBUILT_DIR = os.path.join(PROJECT_ROOT, "prebuilt")

# Matches fojin.app/texts/<ID> in URLs — ID can be CBETA-style or numeric
FOJIN_URL_RE = re.compile(r"(https?://fojin\.app/texts/)([A-Za-z0-9n]+)")

# Full CBETA catalog ID pattern: T08n0235, X62n1182, J36n0348
FULL_CBETA_RE = re.compile(r"^([A-Z])(\d+)n(\d+[a-z]?)$")

SOURCE_ID_PATTERNS = {
    "cbeta": FULL_CBETA_RE,
    "tibetan_canon": re.compile(r"^(?:Toh[: ]\d+[A-Za-z-]*|BDRC:[A-Za-z0-9][A-Za-z0-9-]*)$"),
    "kadam_corpus": re.compile(r"^BDRC:[A-Za-z0-9][A-Za-z0-9-]*$"),
    "tibetan_treatise": re.compile(r"^[A-Za-z][A-Za-z0-9'-]*(?:-[A-Za-z0-9'-]+)*$"),
    "pali_canon": re.compile(r"^(?:SuttaCentral|SC[: ][A-Za-z0-9. -]+|(?:DN|MN|SN|AN|KN) ?\d+(?:\.\d+)?)$"),
    "pali_commentary": re.compile(r"^PTS:[A-Za-z0-9][A-Za-z0-9-]*$"),
    "pali_treatise": re.compile(r"^PTS:[A-Za-z0-9][A-Za-z0-9-]*$"),
    "compiled_teaching": re.compile(r"^[^:\s]+:[^:\s].+$"),
}


def validate_source_document(document: dict) -> list[str]:
    """Validate declared source families, identifiers, contract, and citations."""
    errors: list[str] = []
    sources = document.get("sources") if isinstance(document, dict) else None
    if not isinstance(sources, list) or not sources:
        return ["sources must be a non-empty list"]

    declared: set[tuple[str, str]] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        source_type = source.get("type")
        source_id = source.get("id")
        if source_type not in SOURCE_ID_PATTERNS:
            errors.append(f"sources[{index}].type is unsupported: {source_type!r}")
            continue
        if not isinstance(source_id, str) or not SOURCE_ID_PATTERNS[source_type].fullmatch(source_id):
            errors.append(
                f"sources[{index}] {source_type} identifier is invalid: {source_id!r}"
            )
            continue
        member = (source_type, source_id)
        if member in declared:
            errors.append(
                f"sources[{index}] duplicates declared source {source_type}:{source_id}"
            )
        declared.add(member)

    try:
        expected_contract = derive_citation_contract(sources)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if document.get("citation_contract") != expected_contract:
            errors.append(
                "citation_contract must equal the contract derived from sources[].type"
            )

    citations = document.get("citations", [])
    if not isinstance(citations, list):
        errors.append("citations must be a list when present")
    else:
        for index, citation in enumerate(citations):
            if not isinstance(citation, dict):
                errors.append(f"citations[{index}] must be an object")
                continue
            member = (citation.get("type"), citation.get("id"))
            if member not in declared:
                errors.append(
                    f"citations[{index}] {member[0]}:{member[1]} is not declared in sources[]"
                )

    return errors


def _load_declared_source_target(target: str, *, final: bool) -> tuple[dict | None, list[str]]:
    path = Path(target)
    errors: list[str] = []
    if final:
        if not path.is_dir():
            return None, [f"final-check target is not a persona directory: {path}"]
        missing = [
            name
            for name in ("SKILL.md", "teaching.md", "voice.md", "meta.json")
            if not (path / name).is_file()
        ]
        if missing:
            return None, [f"final-check target is missing required files: {missing}"]
        if not re.fullmatch(r"master-[a-z0-9][a-z0-9-]*", path.name):
            errors.append(
                "final-check persona directory must use master-<slug>: "
                f"{path.name}"
            )
        try:
            skill_text = (path / "SKILL.md").read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"cannot read final SKILL.md: {exc}")
        else:
            name_match = re.search(r"(?m)^name:\s*([^\s]+)\s*$", skill_text)
            skill_name = name_match.group(1) if name_match else None
            if skill_name != path.name:
                errors.append(
                    f"SKILL.md name {skill_name!r} must equal directory "
                    f"{path.name!r}"
                )
        path = path / "meta.json"
    elif not path.is_file():
        return None, [f"check-links input file not found: {path}"]

    try:
        return json.loads(path.read_text(encoding="utf-8")), errors
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read source manifest {path}: {exc}")
        return None, errors


def _run_declared_source_check(target: str, *, final: bool) -> int:
    document, errors = _load_declared_source_target(target, final=final)
    if document is not None:
        errors.extend(validate_source_document(document))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    label = "final source check" if final else "declared sources"
    print(f"{label} OK ({len(document['sources'])} sources)")
    return 0


def full_to_short_cbeta(full_id: str) -> str | None:
    """Convert full CBETA ID (T08n0235) to FoJin short format (T0235).

    FoJin stores cbeta_id as the collection prefix + text number,
    dropping the volume number. E.g.:
        T08n0235  -> T0235
        X62n1182  -> X1182
        J36n0348  -> J0348
        T34n1718  -> T1718
    """
    m = FULL_CBETA_RE.match(full_id)
    if not m:
        return None
    prefix = m.group(1)    # T, X, J, etc.
    text_num = m.group(3)  # 0235, 1182, etc.
    return f"{prefix}{text_num}"


def collect_cbeta_ids() -> dict[str, list[str]]:
    """Scan all meta.json and return {full_cbeta_id: [teacher_slugs]}."""
    cbeta_map: dict[str, list[str]] = {}
    for teacher in sorted(os.listdir(PREBUILT_DIR)):
        meta_path = os.path.join(PREBUILT_DIR, teacher, "meta.json")
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        for src in meta.get("sources", []):
            if src.get("type") == "cbeta" and src.get("id"):
                cbeta_id = src["id"]
                cbeta_map.setdefault(cbeta_id, []).append(teacher)
    return cbeta_map


def collect_all_fojin_urls() -> dict[str, list[tuple[str, int]]]:
    """Scan all md/py files and return {id_in_url: [(filepath, line_num)]}."""
    url_map: dict[str, list[tuple[str, int]]] = {}

    scan_dirs = [PREBUILT_DIR, os.path.join(PROJECT_ROOT, "prompts")]
    extensions = {".md", ".py"}

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, _dirs, files in os.walk(scan_dir):
            for fname in files:
                if os.path.splitext(fname)[1] not in extensions:
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        for m in FOJIN_URL_RE.finditer(line):
                            text_id_in_url = m.group(2)
                            url_map.setdefault(text_id_in_url, []).append(
                                (fpath, line_num)
                            )
    return url_map


def verify_via_search(bridge, title: str, short_cbeta_id: str) -> dict | None:
    """Search FoJin for a text by title, return the matching result with cbeta_id match."""
    try:
        resp = bridge.search_texts(title, sources="cbeta", page=1, size=5)
        for r in resp.get("results", []):
            if r.get("cbeta_id") == short_cbeta_id:
                return r
        # Also try without source filter
        resp = bridge.search_texts(title, page=1, size=5)
        for r in resp.get("results", []):
            if r.get("cbeta_id") == short_cbeta_id:
                return r
    except Exception:
        pass
    return None


def verify_via_lookup(bridge, short_ids: list[str]) -> dict:
    """Try the batch lookup-cbeta endpoint. Returns {short_cbeta_id: internal_id}."""
    result = {}
    try:
        ids_str = ",".join(short_ids)
        resp = bridge.lookup_cbeta_ids(ids_str)
        if isinstance(resp, dict):
            mapping = resp.get("results") or resp.get("data") or resp
            for sid in short_ids:
                entry = mapping.get(sid)
                if entry and isinstance(entry, dict):
                    result[sid] = entry.get("text_id") or entry.get("id")
                elif entry and isinstance(entry, int):
                    result[sid] = entry
    except Exception:
        pass  # Endpoint may not be implemented; fall back to search
    return result


def verify_ids(bridge, cbeta_map: dict[str, list[str]], titles: dict[str, str]) -> dict[str, dict]:
    """Verify all CBETA IDs and return {full_cbeta_id: {text_id, short_id, title, ...}}.

    Args:
        cbeta_map: {full_cbeta_id: [teacher_slugs]}
        titles: {full_cbeta_id: title_from_meta} for search fallback
    """
    results: dict[str, dict] = {}

    # Build full -> short mapping
    full_to_short = {}
    short_to_full = {}
    for full_id in cbeta_map:
        short = full_to_short_cbeta(full_id)
        if short:
            full_to_short[full_id] = short
            short_to_full[short] = full_id

    # Try batch lookup first
    short_ids = list(full_to_short.values())
    lookup_result = verify_via_lookup(bridge, short_ids)

    for full_id, short_id in sorted(full_to_short.items()):
        if short_id in lookup_result:
            results[full_id] = {
                "text_id": lookup_result[short_id],
                "short_cbeta_id": short_id,
                "method": "lookup",
            }
            continue

        # Fallback: search by title
        title = titles.get(full_id, "")
        if title:
            time.sleep(0.2)  # Rate limit
            match = verify_via_search(bridge, title, short_id)
            if match:
                results[full_id] = {
                    "text_id": match["id"],
                    "short_cbeta_id": short_id,
                    "title_zh": match.get("title_zh", ""),
                    "method": "search",
                }
                continue

        # Try direct get with the internal ID if it's numeric-ish
        # Last resort: not found
        results[full_id] = {
            "text_id": None,
            "short_cbeta_id": short_id,
            "method": "not_found",
        }

    return results


def collect_titles_from_meta() -> dict[str, str]:
    """Collect {full_cbeta_id: title} from meta.json sources."""
    titles = {}
    for teacher in os.listdir(PREBUILT_DIR):
        meta_path = os.path.join(PREBUILT_DIR, teacher, "meta.json")
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        for src in meta.get("sources", []):
            if src.get("type") == "cbeta" and src.get("id") and src.get("title"):
                titles[src["id"]] = src["title"]
    return titles


def fix_urls_in_file(
    filepath: str, id_map: dict[str, str], dry_run: bool
) -> list[str]:
    """Replace CBETA IDs with internal text_ids in URLs. Returns list of changes."""
    changes = []
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    def replacer(m):
        prefix = m.group(1)
        old_id = m.group(2)
        if old_id in id_map:
            new_id = id_map[old_id]
            rel = os.path.relpath(filepath, PROJECT_ROOT)
            changes.append(f"    {rel}: {old_id} -> {new_id}")
            return prefix + new_id
        return m.group(0)

    new_content = FOJIN_URL_RE.sub(replacer, content)

    if not dry_run and new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

    return changes


def _run_legacy_link_verification(*, fix: bool) -> int:
    """Preserve the historical FoJin CBETA URL audit and optional fixer."""
    dry_run = not fix

    print("=" * 60)
    print("FoJin Source Verification Report")
    print("=" * 60)
    if dry_run:
        print("Mode: DRY RUN (use --fix to apply changes)\n")
    else:
        print("Mode: FIX (writing changes to files)\n")

    # Step 1: Collect CBETA IDs from meta.json
    cbeta_map = collect_cbeta_ids()
    all_cbeta_ids = sorted(cbeta_map.keys())
    teacher_count = len(set(t for ts in cbeta_map.values() for t in ts))
    print(f"[1/4] Found {len(all_cbeta_ids)} unique CBETA IDs across {teacher_count} teachers")
    for cid in all_cbeta_ids:
        short = full_to_short_cbeta(cid) or "?"
        print(f"  {cid} (-> {short}) <- {', '.join(cbeta_map[cid])}")

    # Step 2: Collect all fojin.app URLs from files
    url_map = collect_all_fojin_urls()
    all_url_ids = sorted(url_map.keys())
    total_urls = sum(len(v) for v in url_map.values())
    print(f"\n[2/4] Found {total_urls} fojin.app URLs using {len(all_url_ids)} unique IDs")

    # IDs in URLs but not in meta.json sources
    extra_url_ids = set(all_url_ids) - set(all_cbeta_ids)
    if extra_url_ids:
        print(f"  Extra IDs in URLs (not in meta.json sources):")
        for eid in sorted(extra_url_ids):
            locs = url_map[eid]
            files = set(os.path.relpath(f, PROJECT_ROOT) for f, _ in locs)
            print(f"    {eid} in {', '.join(sorted(files))}")

    # Combine: all unique CBETA-style IDs from both meta.json and URLs
    all_ids = set(all_cbeta_ids)
    for uid in all_url_ids:
        if FULL_CBETA_RE.match(uid):
            all_ids.add(uid)

    # Non-CBETA IDs in URLs (e.g. suttacentral IDs, placeholder "123")
    non_cbeta_url_ids = [uid for uid in all_url_ids if not FULL_CBETA_RE.match(uid)]
    if non_cbeta_url_ids:
        print(f"  Non-CBETA IDs in URLs (skipped): {', '.join(non_cbeta_url_ids)}")

    # Step 3: Verify with FoJin API
    print(f"\n[3/4] Verifying {len(all_ids)} CBETA IDs against FoJin API...")
    bridge = create_bridge()

    if not bridge.test_connection():
        print("  [ERROR] Cannot connect to FoJin API.")
        print("  Set FOJIN_URL environment variable if using a custom instance.")
        sys.exit(1)
    print("  API connection OK")

    # Build combined cbeta_map (include URL-only IDs)
    combined_map = dict(cbeta_map)
    for uid in all_url_ids:
        if FULL_CBETA_RE.match(uid) and uid not in combined_map:
            combined_map[uid] = ["(URL only)"]

    titles = collect_titles_from_meta()
    verified = verify_ids(bridge, combined_map, titles)

    found = {k: v for k, v in verified.items() if v["text_id"] is not None}
    not_found = {k: v for k, v in verified.items() if v["text_id"] is None}

    print(f"\n  Verified: {len(found)}/{len(verified)}")
    for cid in sorted(found):
        info = found[cid]
        title = info.get("title_zh", titles.get(cid, ""))
        print(f"    [OK]   {cid} -> text_id={info['text_id']}  {title}  ({info['method']})")

    if not_found:
        print(f"\n  Not found in FoJin ({len(not_found)}):")
        for cid in sorted(not_found):
            teachers = combined_map.get(cid, ["?"])
            print(f"    [MISS] {cid} (-> {not_found[cid]['short_cbeta_id']}) used by: {', '.join(teachers)}")

    # Step 4: Update URLs
    # Build replacement map: full_cbeta_id -> str(internal_text_id)
    id_replacement_map: dict[str, str] = {}
    for full_id, info in found.items():
        id_replacement_map[full_id] = str(info["text_id"])

    action = "Would update" if dry_run else "Updating"
    print(f"\n[4/4] {action} URLs...")
    all_changes = []

    files_to_fix = set()
    for locations in url_map.values():
        for fpath, _ in locations:
            files_to_fix.add(fpath)

    for fpath in sorted(files_to_fix):
        changes = fix_urls_in_file(fpath, id_replacement_map, dry_run)
        all_changes.extend(changes)

    if all_changes:
        for c in all_changes:
            print(c)
        verb = "would be made" if dry_run else "applied"
        print(f"\n  Total: {len(all_changes)} URL replacements {verb}")
    else:
        print("  No URL replacements needed")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  CBETA IDs in meta.json:    {len(all_cbeta_ids)}")
    print(f"  CBETA IDs in URLs:         {len([u for u in all_url_ids if FULL_CBETA_RE.match(u)])}")
    print(f"  Total unique CBETA IDs:    {len(all_ids)}")
    print(f"  Verified in FoJin:         {len(found)}")
    print(f"  Not found in FoJin:        {len(not_found)}")
    print(f"  URL replacements:          {len(all_changes)}")
    if dry_run and all_changes:
        print("\n  Run with --fix to apply changes.")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate declared source manifests or audit legacy FoJin links"
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--check-links",
        metavar="JSON",
        help="offline-check a collected JSON source manifest",
    )
    modes.add_argument(
        "--final-check",
        metavar="PERSONA_DIR",
        help="offline-check a generated persona and its final meta.json",
    )
    modes.add_argument(
        "--fix",
        action="store_true",
        help="run the legacy online CBETA URL audit and apply replacements",
    )
    args = parser.parse_args(argv)

    if args.check_links:
        return _run_declared_source_check(args.check_links, final=False)
    if args.final_check:
        return _run_declared_source_check(args.final_check, final=True)
    return _run_legacy_link_verification(fix=args.fix)


if __name__ == "__main__":
    sys.exit(main())
