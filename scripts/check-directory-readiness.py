#!/usr/bin/env python3
"""Check plugin/ against Anthropic's plugin-directory pre-submission checklist.

Source: https://claude.com/docs/plugins/pre-submission-checklist (read
2026-10-19). The portal's Validate step is the authority; this re-implements
the checks that can be decided from the files alone, so a commit that would be
blocked or held for a reviewer fails here first. Each line is PASS, WARN or
FAIL; the exit code is 1 if any line is FAIL.

Rows that need the portal (name already taken, brand look-alikes, the security
scan) are not checked here.

Usage:
    python3 scripts/check-directory-readiness.py            # checks plugin/
    python3 scripts/check-directory-readiness.py <folder>

Stdlib only (PyYAML used when installed), Python 3.9 compatible, ASCII output.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

KIB = 1024
MAX_TEXT_BYTES = 256 * KIB          # non-image/font files: "under 256 KiB"
MAX_ANY_BYTES = 5 * KIB * KIB       # every file: "under 5 MiB"
MAX_FILES = 512
MIN_README_WORDS = 40

IMAGE_FONT_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
                       ".ttf", ".otf", ".woff", ".woff2"}
SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini", "__macosx"}
WINDOWS_DEVICES = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} \
    | {f"lpt{i}" for i in range(1, 10)}
RESERVED_WHOLE_NAMES = {"claude", "anthropic", "official", "plugin", "mcp", "test"}
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
FOLDER_RE = re.compile(r"^[A-Za-z0-9._-]+$")
PKG_CONFIGS = {".npmrc", ".yarnrc", ".yarnrc.yml", "bunfig.toml", "uv.toml",
               "pip.conf", ".pypirc", "pnpm-workspace.yaml"}
LOCKFILES = {"package-lock.json", "npm-shrinkwrap.json", "bun.lock", "bun.lockb"}
HOOK_EVENTS = {
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest",
    "UserPromptSubmit", "Notification", "Stop", "SubagentStart", "SubagentStop",
    "PreCompact", "PostCompact", "SessionStart", "SessionEnd", "Setup",
    "TeammateIdle", "TaskCompleted", "ConfigChange", "WorktreeCreate",
    "WorktreeRemove", "InstructionsLoaded", "Elicitation", "ElicitationResult",
}
HOOK_TYPES = {"command", "http", "prompt", "agent", "mcp_tool"}
LAUNCHER_RE = re.compile(r"\b(npx|bunx|uvx|pnpm\s+dlx|yarn\s+dlx|pipx\s+run|uv\s+run)\s+(\S+)")
PINNED_RE = re.compile(r"^(@?[A-Za-z0-9._/-]+)(@\d+\.\d+\.\d+[A-Za-z0-9.+-]*|==\d+(\.\d+)*)$")
SECRET_RES = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
]

Result = Tuple[str, str, str]   # (status, check, detail)


def _files(base: Path) -> List[Path]:
    return sorted(p for p in base.rglob("*") if p.is_file() or p.is_symlink())


def _rel(p: Path, base: Path) -> str:
    return p.relative_to(base).as_posix()


def _text(p: Path) -> Optional[str]:
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _manifest(base: Path) -> Tuple[Optional[dict], str]:
    path = base / ".claude-plugin" / "plugin.json"
    if not path.is_file():
        return None, "missing .claude-plugin/plugin.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except ValueError as exc:
        return None, f"plugin.json is not valid JSON: {exc}"


def check_manifest(base: Path) -> List[Result]:
    data, err = _manifest(base)
    if data is None:
        return [("FAIL", "manifest", err)]
    out: List[Result] = [("PASS", "manifest", ".claude-plugin/plugin.json parses")]
    name = data.get("name", "")
    if not isinstance(name, str) or not name.isascii():
        out.append(("FAIL", "name", f"non-ASCII or missing name: {name!r}"))
    elif not NAME_RE.match(name):
        out.append(("WARN", "name", f"{name!r} is not lowercase-hyphen, <=64 chars"))
    else:
        out.append(("PASS", "name", f"{name!r} is lowercase letters/digits/hyphens"))
    words = set(str(name).split("-"))
    if name in RESERVED_WHOLE_NAMES or words & {"claude", "anthropic", "official"}:
        out.append(("FAIL", "name-reserved", f"{name!r} uses a reserved word"))
    else:
        out.append(("PASS", "name-reserved", "no claude/anthropic/official, not a bare reserved word"))
    missing = [k for k in ("description", "author", "version") if not data.get(k)]
    out.append(("WARN" if missing else "PASS", "metadata",
                f"missing {missing}" if missing else "description, author, version set"))
    for field in ("skills", "commands", "agents", "hooks", "mcpServers", "outputStyles"):
        value = data.get(field)
        paths = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for p in paths:
            if isinstance(p, str):
                resolved = (base / p).resolve()
                if base.resolve() not in resolved.parents and resolved != base.resolve():
                    out.append(("FAIL", "component-paths", f"{field} path {p!r} leaves the plugin folder"))
    if "experimental" in data and isinstance(data["experimental"], dict):
        out.append(("FAIL", "component-keys", "component keys inside `experimental`"))
    if data.get("hooks") in ("./hooks/hooks.json", "hooks/hooks.json"):
        out.append(("WARN", "hooks-field", "hooks/hooks.json is loaded automatically; drop the field"))
    return out


def check_readme_license(base: Path) -> List[Result]:
    out: List[Result] = []
    readme = next((base / n for n in ("README.md", "README", "readme.md") if (base / n).is_file()), None)
    if readme is None:
        out.append(("FAIL", "readme", "no README in the plugin folder"))
    else:
        text = re.sub(r"```.*?```", " ", readme.read_text(encoding="utf-8"), flags=re.S)
        words = len(text.split())
        out.append(("PASS" if words >= MIN_README_WORDS else "FAIL", "readme",
                    f"{readme.name}: {words} words outside code blocks (need >= {MIN_README_WORDS})"))
    data, _ = _manifest(base)
    has_file = (base / "LICENSE").is_file() or (base / "LICENSE.md").is_file()
    has_field = bool(data and data.get("license"))
    out.append(("PASS" if (has_file or has_field) else "FAIL", "license",
                f"LICENSE file: {has_file}, plugin.json license: {has_field}"))
    return out


def check_files(base: Path) -> List[Result]:
    files = _files(base)
    out: List[Result] = []
    out.append(("PASS" if len(files) <= MAX_FILES else "FAIL", "file-count",
                f"{len(files)} files (limit {MAX_FILES})"))
    big = []
    huge = []
    links = []
    lfs = []
    binaries = []
    system = []
    for p in files:
        rel = _rel(p, base)
        if p.is_symlink():
            links.append(rel)
            continue
        size = p.stat().st_size
        suffix = p.suffix.lower()
        if size >= MAX_ANY_BYTES:
            huge.append(f"{rel} ({size} B)")
        if suffix not in IMAGE_FONT_SUFFIXES and size >= MAX_TEXT_BYTES:
            big.append(f"{rel} ({size} B)")
        if any(part.lower() in SYSTEM_FILES for part in rel.split("/")):
            system.append(rel)
        head = p.read_bytes()[:200]
        if head.startswith(b"version https://git-lfs.github.com/spec/"):
            lfs.append(rel)
        if suffix not in IMAGE_FONT_SUFFIXES and _text(p) is None:
            binaries.append(rel)
    for d in base.rglob("*"):
        if d.is_dir() and d.is_symlink():
            links.append(_rel(d, base))
    out.append(("FAIL" if big else "PASS", "file-size",
                f"{len(big)} non-image/font file(s) >= 256 KiB: {big[:5]}" if big
                else "every non-image/font file < 256 KiB"))
    out.append(("FAIL" if huge else "PASS", "file-size-5mib",
                f"files >= 5 MiB: {huge[:5]}" if huge else "every file < 5 MiB"))
    out.append(("FAIL" if links else "PASS", "symlinks",
                f"symbolic links: {links[:5]}" if links else "no symbolic links"))
    out.append(("FAIL" if lfs else "PASS", "lfs-pointers",
                f"Git LFS pointer files: {lfs[:5]}" if lfs else "no Git LFS pointer files"))
    out.append(("FAIL" if binaries else "PASS", "binary-files",
                f"non-text, non-image/font files: {binaries[:5]}" if binaries
                else "only UTF-8 text plus image/font files"))
    out.append(("FAIL" if system else "PASS", "system-files",
                f"OS litter: {system[:5]}" if system else "no .DS_Store/Thumbs.db/desktop.ini/__MACOSX"))
    return out


def check_names(base: Path) -> List[Result]:
    bad = []
    seen = {}
    for p in base.rglob("*"):
        rel = _rel(p, base)
        name = p.name
        stem = name.split(".")[0].lower()
        if ":" in name or name.endswith((".", " ")) or stem in WINDOWS_DEVICES:
            bad.append(rel)
        key = rel.lower()
        if key in seen and seen[key] != rel:
            bad.append(f"{rel} vs {seen[key]} (case collision)")
        seen[key] = rel
    path_parts = base.resolve().relative_to(ROOT.resolve()).parts if ROOT.resolve() in base.resolve().parents else ()
    bad += [f"plugin path folder {part!r}" for part in path_parts if not FOLDER_RE.match(part)]
    return [("FAIL" if bad else "PASS", "file-names",
             f"not portable to Windows/macOS: {bad[:5]}" if bad
             else "names portable (no colon, trailing dot/space, device names, case collisions)")]


def check_git(base: Path) -> List[Result]:
    """Submodules and .gitattributes rules — only meaningful inside a git checkout."""
    out: List[Result] = []
    try:
        top = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=base,
                                  capture_output=True, text=True, check=True).stdout.strip())
        listing = subprocess.run(["git", "ls-files", "-s", "--", "."], cwd=base,
                                 capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return [("WARN", "git", "not a git checkout; submodule/.gitattributes checks skipped")]
    gitlinks = [line.split("\t", 1)[1] for line in listing.splitlines() if line.startswith("160000 ")]
    out.append(("FAIL" if gitlinks else "PASS", "submodules",
                f"git submodules: {gitlinks[:5]}" if gitlinks else "no git submodules"))
    problems = []
    for attrs in [top / ".gitattributes"] + sorted(base.rglob(".gitattributes")):
        if not attrs.is_file():
            continue
        for n, line in enumerate(attrs.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if re.search(r"\bexport-(ignore|subst)\b|\bfilter=|\bfilter\b", line):
                problems.append(f"{attrs.relative_to(top).as_posix()}:{n}")
    out.append(("FAIL" if problems else "PASS", "gitattributes",
                f"export-ignore/export-subst/filter at {problems[:5]}" if problems
                else "no export-ignore, export-subst or filter attributes"))
    return out


def _hook_commands(base: Path) -> Tuple[List[str], List[Result]]:
    path = base / "hooks" / "hooks.json"
    if not path.exists():
        return [], [("PASS", "hooks-json", "no hooks/hooks.json")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [], [("FAIL", "hooks-json", f"hooks.json is invalid: {exc}")]
    problems = []
    commands = []
    hooks = data.get("hooks")
    if not isinstance(hooks, dict) and "modules" not in data:
        problems.append("no top-level `hooks` object")
    for event, matchers in (hooks or {}).items():
        if event not in HOOK_EVENTS:
            problems.append(f"unknown hook event {event!r}")
        for matcher in matchers or []:
            for hook in matcher.get("hooks", []):
                if hook.get("type") not in HOOK_TYPES:
                    problems.append(f"unknown hook type {hook.get('type')!r}")
                if hook.get("type") == "http" and not str(hook.get("url", "")).startswith("https://"):
                    problems.append("http hook without an https:// url")
                if hook.get("type") == "command":
                    commands.append(str(hook.get("command", "")))
    if problems:
        return commands, [("FAIL", "hooks-json", "; ".join(problems))]
    return commands, [("PASS", "hooks-json", f"valid; {len(commands)} command hook(s)")]


def check_hooks_and_launchers(base: Path) -> List[Result]:
    commands, out = _hook_commands(base)
    mcp = base / ".mcp.json"
    if mcp.exists():
        try:
            data = json.loads(mcp.read_text(encoding="utf-8"))
            for server in (data.get("mcpServers") or {}).values():
                commands.append(" ".join([str(server.get("command", ""))] + [str(a) for a in server.get("args", [])]))
            out.append(("PASS", "mcp-json", ".mcp.json parses"))
        except ValueError as exc:
            out.append(("FAIL", "mcp-json", f".mcp.json can't be parsed: {exc}"))
    bad = []
    for cmd in commands:
        stripped = cmd.replace("${CLAUDE_PLUGIN_ROOT}", "")
        if re.search(r"\$\{?[A-Za-z_]", stripped) or "$(" in cmd or "`" in cmd:
            bad.append(f"variable or substitution in {cmd[:60]!r}")
        if re.search(r"\b(python3?|node|bash|sh|ruby|perl)\s+-(c|e)\b", cmd):
            bad.append(f"inline program in {cmd[:60]!r}")
        if re.search(r"[*?]", stripped.split("'")[0]):
            bad.append(f"wildcard in {cmd[:60]!r}")
    out.append(("FAIL" if bad else "PASS", "hook-commands",
                "; ".join(bad[:3]) if bad else
                "hook/MCP commands use no variable but ${CLAUDE_PLUGIN_ROOT}, no substitution or inline program"))
    unpinned = []
    for cmd in commands:
        for m in LAUNCHER_RE.finditer(cmd):
            launcher, pkg = m.group(1), m.group(2)
            if launcher == "uv run":
                if "--locked" not in cmd and "--frozen" not in cmd:
                    unpinned.append(cmd[:60])
            elif not PINNED_RE.match(pkg):
                unpinned.append(f"{launcher} {pkg}")
    out.append(("FAIL" if unpinned else "PASS", "launchers-pinned",
                f"unpinned launchers in hooks/MCP: {unpinned[:5]}" if unpinned
                else "no unpinned npx/uvx/bunx/dlx/pipx/uv-run in hooks or MCP commands"))
    # Prose mentions: instructions to the user, not something the plugin runs.
    prose = []
    for p in _files(base):
        text = _text(p)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in LAUNCHER_RE.finditer(line):
                if m.group(1) != "uv run" and not PINNED_RE.match(m.group(2).strip("`'\")")):
                    prose.append(f"{_rel(p, base)}:{n}")
    if prose:
        out.append(("WARN", "launchers-in-text",
                    f"{len(prose)} unpinned launcher mention(s) in file text (not run by the plugin): {prose[:4]}"))
    else:
        out.append(("PASS", "launchers-in-text", "no unpinned launcher mentions anywhere"))
    return out


def check_packages_and_secrets(base: Path) -> List[Result]:
    out: List[Result] = []
    configs = [_rel(p, base) for p in _files(base) if p.name in PKG_CONFIGS]
    out.append(("FAIL" if configs else "PASS", "package-config",
                f"package-manager config files: {configs}" if configs
                else "no .npmrc/bunfig.toml/uv.toml or other registry config"))
    lock = [n for n in LOCKFILES if (base / n).exists()]
    if (base / "package.json").exists() and lock:
        out.append(("WARN", "lockfile-install", f"package.json + {lock}: held for a reviewer"))
    else:
        out.append(("PASS", "lockfile-install", "no package.json + lockfile at the plugin root"))
    hits = []
    for p in _files(base):
        text = _text(p)
        if text is None:
            continue
        for rx in SECRET_RES:
            if rx.search(text):
                hits.append(f"{_rel(p, base)} ({rx.pattern[:16]})")
    out.append(("FAIL" if hits else "PASS", "credentials",
                f"credential-shaped strings: {hits[:5]}" if hits else "no credential-shaped strings"))
    return out


def _frontmatter(text: str) -> Tuple[Optional[dict], str]:
    if not text.startswith("---"):
        return None, "no front matter"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "unterminated front matter"
    try:
        import yaml  # type: ignore
    except ImportError:
        m = re.search(r"^description:\s*(.+)$", parts[1], re.M)
        return ({"description": m.group(1)} if m else {}), ""
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        return None, f"front matter does not parse: {str(exc).splitlines()[0]}"
    return (data if isinstance(data, dict) else {}), ""


def check_skills(base: Path) -> List[Result]:
    skills = sorted((base / "skills").glob("*/SKILL.md")) if (base / "skills").is_dir() else []
    fail, warn = [], []
    for s in skills:
        data, err = _frontmatter(s.read_text(encoding="utf-8"))
        rel = _rel(s, base)
        if data is None:
            (fail if "parse" in err or "unterminated" in err else warn).append(f"{rel}: {err}")
        elif "description" not in data:
            warn.append(f"{rel}: no description")
        elif not isinstance(data["description"], str):
            fail.append(f"{rel}: description is not text")
    out: List[Result] = []
    if fail:
        out.append(("FAIL", "skill-frontmatter", "; ".join(fail[:3])))
    elif warn:
        out.append(("WARN", "skill-frontmatter", "; ".join(warn[:3])))
    else:
        out.append(("PASS", "skill-frontmatter", f"{len(skills)} skills/<name>/SKILL.md with text descriptions"))
    return out


CHECKS: Tuple[Callable[[Path], List[Result]], ...] = (
    check_manifest, check_readme_license, check_files, check_names, check_git,
    check_hooks_and_launchers, check_packages_and_secrets, check_skills,
)


def run(base: Path) -> List[Result]:
    results: List[Result] = []
    for check in CHECKS:
        results.extend(check(base))
    return results


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    base = Path(argv[0]).resolve() if argv else ROOT / "plugin"
    if not base.is_dir():
        print(f"FAIL {base} is not a directory")
        return 1
    results = run(base)
    for status, name, detail in results:
        print(f"{status:<4} {name:<20} {detail}".encode("ascii", "replace").decode("ascii"))
    fails = sum(1 for r in results if r[0] == "FAIL")
    warns = sum(1 for r in results if r[0] == "WARN")
    print(f"{'FAIL' if fails else 'PASS'}: {len(results)} checks, {fails} failed, {warns} warning(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
