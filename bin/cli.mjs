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

function showHelp() {
  console.log(`
master-skill v${pkgVersion()} — Buddhist Master AI Skills installer

Usage:
  master-skill install <name...>   Install masters to ~/.claude/skills/
  master-skill install --all       Install all available masters
  master-skill list                List available masters
  master-skill uninstall <name...> Remove installed masters
  master-skill --version           Print version
  master-skill --help              Show this help

Names accept both short (zhiyi) and full (master-zhiyi) forms.
Slash commands are always /master-<slug> (e.g. /master-zhiyi).

Examples:
  npx master-skill install zhiyi fazang
  npx master-skill install master-milarepa master-tsongkhapa
  npx master-skill install --all
  npx master-skill list
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
} else if (cmd === "install") {
  const rest = args.slice(1);
  if (rest.includes("--all")) {
    const all = availableMasters().map((m) => m.name);
    if (!all.length) {
      console.log("No masters available.");
      process.exitCode = 1;
    } else {
      console.log(`Installing all ${all.length} masters...\n`);
      if (cmdInstall(all) > 0) process.exitCode = 1;
    }
  } else if (rest.length === 0) {
    console.log("Usage: master-skill install <name...> | --all");
    process.exitCode = 1;
  } else {
    if (cmdInstall(rest) > 0) process.exitCode = 1;
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
