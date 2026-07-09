#!/usr/bin/env node

import fs from "fs";
import path from "path";
import os from "os";
import { fileURLToPath } from "url";

// fileURLToPath (not new URL().pathname) — on Windows the URL pathname is
// "/C:/…", which fs cannot resolve, so every command saw an empty prebuilt/.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PREBUILT = path.join(__dirname, "..", "prebuilt");
const SKILLS_DIR = path.join(os.homedir(), ".claude", "skills");

// --- helpers ---

function pkgVersion() {
  try {
    const pkg = JSON.parse(
      fs.readFileSync(path.join(__dirname, "..", "package.json"), "utf8")
    );
    return pkg.version || "unknown";
  } catch {
    return "unknown";
  }
}

// Names feed into path.join + rmSync; reject separators / ".." so a typo
// like "../foo" can never escape PREBUILT or SKILLS_DIR.
function isSafeName(name) {
  return /^[A-Za-z0-9_-]+$/.test(name);
}

function cpR(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) cpR(s, d);
    else fs.copyFileSync(s, d);
  }
}

function parseFrontmatter(filepath) {
  // \r?\n: a CRLF checkout (git autocrlf on Windows) must not blank out
  // every description.
  const text = fs.readFileSync(filepath, "utf8");
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return {};
  const fm = {};
  for (const line of m[1].split(/\r?\n/)) {
    const idx = line.indexOf(":");
    if (idx > 0 && !line.startsWith(" ") && !line.startsWith("-")) {
      fm[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }
  }
  return fm;
}

function availableMasters() {
  if (!fs.existsSync(PREBUILT)) return [];
  return fs
    .readdirSync(PREBUILT, { withFileTypes: true })
    .filter((d) => d.isDirectory() && d.name !== "compare")
    .map((d) => {
      const skillMd = path.join(PREBUILT, d.name, "SKILL.md");
      const fm = fs.existsSync(skillMd) ? parseFrontmatter(skillMd) : {};
      return { name: d.name, description: fm.description || "" };
    });
}

function readJson(filepath) {
  return JSON.parse(fs.readFileSync(filepath, "utf8"));
}

function installedSkillDirs() {
  if (!fs.existsSync(SKILLS_DIR)) return [];
  return fs
    .readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();
}

function hasLiveGrounding(masterDir) {
  const skillMd = path.join(masterDir, "SKILL.md");
  if (!fs.existsSync(skillMd)) return false;
  const text = fs.readFileSync(skillMd, "utf8");
  return text.includes("FoJin 实时检索") || text.includes("FoJin live");
}

function sourceIds(meta) {
  if (!Array.isArray(meta.sources)) return [];
  return meta.sources.map((s) => [s.id, s.title].filter(Boolean).join(" — "));
}

// --- commands ---

function cmdList() {
  const masters = availableMasters();
  if (!masters.length) {
    console.log("No prebuilt masters found.");
    return;
  }
  console.log(`\nAvailable masters (${masters.length}):\n`);
  const nameW = Math.max(...masters.map((m) => m.name.length), 4);
  for (const m of masters) {
    const desc = m.description.length > 80 ? m.description.slice(0, 77) + "..." : m.description;
    console.log(`  ${m.name.padEnd(nameW)}  ${desc}`);
  }
  console.log();
}

// Resolve a master directory accepting both short ("zhiyi") and full
// ("master-zhiyi") forms. Returns the absolute prebuilt/<dir> path or null.
function resolveMasterDir(input) {
  const candidates = [
    path.join(PREBUILT, input),                  // exact: master-zhiyi
    path.join(PREBUILT, `master-${input}`),      // short: zhiyi → master-zhiyi
  ];
  return candidates.find((p) => fs.existsSync(p)) || null;
}

// Returns the number of failures so main can set a non-zero exit code —
// scripted callers must be able to tell a typo from a clean install.
function cmdInstall(names) {
  fs.mkdirSync(SKILLS_DIR, { recursive: true });
  let failed = 0;
  for (const name of names) {
    if (!isSafeName(name)) {
      console.log(`  ✗ ${name} — invalid name (letters, digits, "-", "_" only)`);
      failed++;
      continue;
    }
    const src = resolveMasterDir(name);
    if (!src) {
      console.log(`  ✗ ${name} — not found in prebuilt/ (tried "${name}" and "master-${name}")`);
      failed++;
      continue;
    }
    const dirName = path.basename(src);          // master-zhiyi
    const dest = path.join(SKILLS_DIR, dirName);
    // Clear any previous install first: files renamed or removed upstream
    // must not linger as stale skill content under ~/.claude/skills/.
    fs.rmSync(dest, { recursive: true, force: true });
    cpR(src, dest);
    console.log(`  ✓ ${name} → ${dest}`);
  }
  return failed;
}

function cmdInstallAll(label = "Installing") {
  const all = availableMasters().map((m) => m.name);
  if (!all.length) {
    console.log("No masters available.");
    return 1;
  }
  console.log(`${label} all ${all.length} masters...\n`);
  return cmdInstall(all);
}

function cmdUninstall(names) {
  let failed = 0;
  for (const name of names) {
    if (!isSafeName(name)) {
      console.log(`  ✗ ${name} — invalid name (letters, digits, "-", "_" only)`);
      failed++;
      continue;
    }
    // Try both prefixed and bare directory names for backward compatibility
    // with any pre-v0.6 installs that may still sit at ~/.claude/skills/<slug>/.
    const candidates = [
      path.join(SKILLS_DIR, name),               // exact: master-zhiyi
      path.join(SKILLS_DIR, `master-${name}`),   // short: zhiyi → master-zhiyi
    ];
    const dest = candidates.find((p) => fs.existsSync(p));
    if (!dest) {
      console.log(`  ✗ ${name} — not installed`);
      failed++;
      continue;
    }
    fs.rmSync(dest, { recursive: true, force: true });
    console.log(`  ✓ ${name} removed (${dest})`);
  }
  return failed;
}

function cmdDoctor() {
  const masters = availableMasters();
  const installed = installedSkillDirs();
  const expectedInstalled = masters.filter((m) => installed.includes(m.name));
  const missingSkillMd = masters.filter((m) => {
    const masterDir = path.join(PREBUILT, m.name);
    return !fs.existsSync(path.join(masterDir, "SKILL.md"));
  });

  console.log(`master-skill doctor\n`);
  console.log(`Package version: ${pkgVersion()}`);
  console.log(`Node version: ${process.version}`);
  console.log(`Prebuilt path: ${PREBUILT}`);
  console.log(`Claude skills path: ${SKILLS_DIR}`);
  console.log(`Available skills: ${masters.length}`);
  console.log(`Installed known skills: ${expectedInstalled.length}`);
  console.log(`Other installed skill dirs: ${installed.length - expectedInstalled.length}`);

  if (missingSkillMd.length) {
    console.log(`\nProblems:`);
    for (const m of missingSkillMd) {
      console.log(`  ✗ ${m.name} is missing SKILL.md`);
    }
    return 1;
  }

  console.log(`\nStatus: ok`);
  return 0;
}

function cmdInspect(name) {
  if (!name) {
    console.log("Usage: master-skill inspect <name>");
    return 1;
  }
  if (!isSafeName(name)) {
    console.log(`  ✗ ${name} — invalid name (letters, digits, "-", "_" only)`);
    return 1;
  }

  const masterDir = resolveMasterDir(name);
  if (!masterDir) {
    console.log(`  ✗ ${name} — not found in prebuilt/ (tried "${name}" and "master-${name}")`);
    return 1;
  }

  const dirName = path.basename(masterDir);
  const skillMd = path.join(masterDir, "SKILL.md");
  const metaPath = path.join(masterDir, "meta.json");
  const fm = fs.existsSync(skillMd) ? parseFrontmatter(skillMd) : {};
  const meta = fs.existsSync(metaPath) ? readJson(metaPath) : {};
  const installed = fs.existsSync(path.join(SKILLS_DIR, dirName));
  const sources = sourceIds(meta);

  console.log(`${dirName}\n`);
  console.log(`Display name: ${meta.name || "(none)"}`);
  console.log(`Slug: ${meta.slug || dirName.replace(/^master-/, "")}`);
  console.log(`Version: ${fm.version || meta.version || "(unknown)"}`);
  console.log(`Tradition: ${meta.tradition || "(unspecified)"}`);
  console.log(`School: ${meta.school || "(unspecified)"}`);
  console.log(`Era: ${meta.era || "(unspecified)"}`);
  console.log(`Installed: ${installed ? "yes" : "no"}`);
  console.log(`Live grounding: ${hasLiveGrounding(masterDir) ? "yes" : "no"}`);
  console.log(`Citation format: ${fm.citation_format || "(not declared in SKILL frontmatter)"}`);

  if (sources.length) {
    console.log(`\nSources (${sources.length}):`);
    for (const source of sources) console.log(`  - ${source}`);
  } else {
    console.log(`\nSources: none declared in meta.json`);
  }

  if (meta.search_scope?.keywords?.length) {
    const keywords = meta.search_scope.keywords.slice(0, 12).join(", ");
    const suffix = meta.search_scope.keywords.length > 12 ? ", ..." : "";
    console.log(`\nSearch keywords: ${keywords}${suffix}`);
  }

  return 0;
}

function showHelp() {
  console.log(`
master-skill v${pkgVersion()} — Buddhist Master AI Skills installer

Usage:
  master-skill install <name...>   Install masters to ~/.claude/skills/
  master-skill install --all       Install all available masters
  master-skill update --all        Reinstall all masters, clearing stale files
  master-skill list                List available masters
  master-skill inspect <name>      Show source/runtime metadata for one master
  master-skill doctor              Check local install and runtime paths
  master-skill uninstall <name...> Remove installed masters
  master-skill --version           Print version
  master-skill --help              Show this help

Names accept both short (zhiyi) and full (master-zhiyi) forms.
Slash commands are always /master-<slug> (e.g. /master-zhiyi).

Examples:
  npx master-skill install zhiyi fazang
  npx master-skill install master-milarepa master-tsongkhapa
  npx master-skill install --all
  npx master-skill update --all
  npx master-skill list
  npx master-skill inspect huineng
  npx master-skill doctor
  npx master-skill uninstall zhiyi
`);
}

// --- main ---

const args = process.argv.slice(2);
const cmd = args[0];

if (!cmd || cmd === "--help" || cmd === "-h") {
  showHelp();
} else if (cmd === "--version" || cmd === "-v") {
  console.log(pkgVersion());
} else if (cmd === "list") {
  cmdList();
} else if (cmd === "doctor") {
  if (cmdDoctor() > 0) process.exitCode = 1;
} else if (cmd === "inspect") {
  if (cmdInspect(args[1]) > 0) process.exitCode = 1;
} else if (cmd === "install") {
  const rest = args.slice(1);
  if (rest.includes("--all")) {
    if (cmdInstallAll("Installing") > 0) process.exitCode = 1;
  } else if (rest.length === 0) {
    console.log("Usage: master-skill install <name...> | --all");
    process.exitCode = 1;
  } else {
    if (cmdInstall(rest) > 0) process.exitCode = 1;
  }
} else if (cmd === "update") {
  const rest = args.slice(1);
  if (rest.length === 1 && rest[0] === "--all") {
    if (cmdInstallAll("Updating") > 0) process.exitCode = 1;
  } else {
    console.log("Usage: master-skill update --all");
    process.exitCode = 1;
  }
} else if (cmd === "uninstall") {
  const rest = args.slice(1);
  if (rest.length === 0) {
    console.log("Usage: master-skill uninstall <name...>");
    process.exitCode = 1;
  } else {
    if (cmdUninstall(rest) > 0) process.exitCode = 1;
  }
} else {
  console.log(`Unknown command: ${cmd}\nRun master-skill --help for usage.`);
  process.exitCode = 1;
}
