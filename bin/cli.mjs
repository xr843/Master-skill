#!/usr/bin/env node

import fs from "fs";
import path from "path";
import os from "os";
import { fileURLToPath } from "url";

// fileURLToPath (not new URL().pathname) — on Windows the URL pathname is
// "/C:/…", which fs cannot resolve, so every command saw an empty prebuilt/.
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PACKAGE_ROOT = path.join(__dirname, "..");
const PREBUILT = path.join(PACKAGE_ROOT, "prebuilt");
const CATALOG_PATH = path.join(PACKAGE_ROOT, "skill-catalog.json");
const SKILLS_DIR = path.join(os.homedir(), ".claude", "skills");
const SKILL_KINDS = new Set(["persona", "teaching-mode", "generator"]);

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

function isSafeRelativePath(value, { allowDot = false } = {}) {
  if (typeof value !== "string" || value.length === 0) return false;
  if (allowDot && value === ".") return true;
  if (value === "." || value.includes("\\") || path.posix.isAbsolute(value)) return false;
  if (/^[A-Za-z]:/.test(value)) return false;
  const normalized = path.posix.normalize(value);
  return normalized === value && normalized !== ".." && !normalized.startsWith("../");
}

function invalidCatalog(message) {
  throw new Error(`Invalid skill catalog: ${message}`);
}

function loadCatalog() {
  let catalog;
  try {
    catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf8"));
  } catch (err) {
    invalidCatalog(`cannot read ${path.basename(CATALOG_PATH)} (${err.message})`);
  }

  if (catalog?.version !== 1) invalidCatalog("version must be 1");
  if (!Array.isArray(catalog.skills) || catalog.skills.length === 0) {
    invalidCatalog("skills must be a non-empty array");
  }

  const uniqueFields = {
    name: new Set(),
    source: new Set(),
    install_dir: new Set(),
  };
  const aliases = new Set();
  const tokenOwners = new Map();

  for (const [index, skill] of catalog.skills.entries()) {
    if (!skill || typeof skill !== "object" || Array.isArray(skill)) {
      invalidCatalog(`skills[${index}] must be an object`);
    }
    if (!isSafeName(skill.name)) {
      invalidCatalog(`skills[${index}].name must be a safe non-empty string`);
    }
    if (!SKILL_KINDS.has(skill.kind)) {
      invalidCatalog(`skills[${index}].kind must be persona, teaching-mode, or generator`);
    }
    if (!isSafeRelativePath(skill.source, { allowDot: true })) {
      invalidCatalog(`skills[${index}].source must be a safe relative path`);
    }
    if (!isSafeName(skill.install_dir)) {
      invalidCatalog(`skills[${index}].install_dir must be a safe non-empty string`);
    }
    if (!Array.isArray(skill.aliases)) {
      invalidCatalog(`skills[${index}].aliases must be an array`);
    }

    for (const field of Object.keys(uniqueFields)) {
      if (uniqueFields[field].has(skill[field])) {
        invalidCatalog(`duplicate ${field} "${skill[field]}"`);
      }
      uniqueFields[field].add(skill[field]);
    }

    tokenOwners.set(skill.name, skill.name);
    for (const alias of skill.aliases) {
      if (!isSafeName(alias)) {
        invalidCatalog(`skills[${index}].aliases contains an unsafe value`);
      }
      if (aliases.has(alias)) invalidCatalog(`duplicate alias "${alias}"`);
      aliases.add(alias);
      const existingOwner = tokenOwners.get(alias);
      if (existingOwner && existingOwner !== skill.name) {
        invalidCatalog(`alias "${alias}" conflicts with skill "${existingOwner}"`);
      }
      tokenOwners.set(alias, skill.name);
    }

    const sourcePath = path.resolve(PACKAGE_ROOT, skill.source);
    if (!fs.existsSync(sourcePath)) invalidCatalog(`source does not exist: ${skill.source}`);
    if (!fs.statSync(sourcePath).isDirectory()) {
      invalidCatalog(`source is not a directory: ${skill.source}`);
    }

    if (skill.kind === "generator") {
      if (!Array.isArray(skill.bundle_paths) || skill.bundle_paths.length === 0) {
        invalidCatalog(`generator "${skill.name}" must declare bundle_paths`);
      }
      const bundlePaths = new Set();
      for (const bundlePath of skill.bundle_paths) {
        if (!isSafeRelativePath(bundlePath)) {
          invalidCatalog(`generator "${skill.name}" has an unsafe bundle path`);
        }
        if (bundlePaths.has(bundlePath)) {
          invalidCatalog(`generator "${skill.name}" has duplicate bundle path "${bundlePath}"`);
        }
        bundlePaths.add(bundlePath);
        if (!fs.existsSync(path.resolve(sourcePath, bundlePath))) {
          invalidCatalog(`bundle path does not exist: ${bundlePath}`);
        }
      }
    } else if (skill.bundle_paths !== undefined) {
      invalidCatalog(`only generator skills may declare bundle_paths`);
    }
  }

  return catalog;
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

function printJson(payload) {
  console.log(JSON.stringify(payload, null, 2));
}

let CATALOG;
try {
  CATALOG = loadCatalog();
} catch (err) {
  console.error(err.message);
  process.exitCode = 1;
}

function catalogSkills() {
  return CATALOG.skills.map((skill) => {
    const skillMd = path.join(PACKAGE_ROOT, skill.source, "SKILL.md");
    const fm = fs.existsSync(skillMd) ? parseFrontmatter(skillMd) : {};
    return { ...skill, description: fm.description || "" };
  });
}

function resolveSkill(input) {
  return catalogSkills().find(
    (skill) => skill.name === input || skill.aliases.includes(input)
  ) || null;
}

// --- commands ---

function listData() {
  const masters = availableMasters();
  const skills = catalogSkills();
  const categoryCounts = skills.reduce((counts, skill) => {
    counts[skill.kind] += 1;
    return counts;
  }, { persona: 0, "teaching-mode": 0, generator: 0 });
  return {
    count: masters.length,
    skillCount: skills.length,
    categoryCounts,
    skills: skills.map(({ name, kind, install_dir, description }) => ({
      name,
      kind,
      installDir: install_dir,
      description,
    })),
    masters: masters.map((m) => ({
      name: m.name,
      slug: m.name.replace(/^master-/, ""),
      description: m.description,
    })),
  };
}

function cmdList({ json = false } = {}) {
  const data = listData();
  if (json) {
    printJson(data);
    return;
  }

  const skills = data.skills;
  if (!skills.length) {
    console.log("No installable skills found.");
    return;
  }
  console.log(`\nAvailable masters (${data.count}); installable skills (${data.skillCount}):`);
  const groups = [
    ["persona", "Personas"],
    ["teaching-mode", "Teaching modes"],
    ["generator", "Generator"],
  ];
  const nameW = Math.max(...skills.map((skill) => skill.name.length), 4);
  for (const [kind, label] of groups) {
    const group = skills.filter((skill) => skill.kind === kind);
    console.log(`\n${label} (${group.length}):`);
    for (const skill of group) {
      const desc = skill.description.length > 80
        ? skill.description.slice(0, 77) + "..."
        : skill.description;
      console.log(`  ${skill.name.padEnd(nameW)}  ${desc}`);
    }
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
    const skill = resolveSkill(name);
    if (!skill) {
      console.log(`  ✗ ${name} — not found in skill catalog`);
      failed++;
      continue;
    }
    const src = path.join(PACKAGE_ROOT, skill.source);
    const dest = path.join(SKILLS_DIR, skill.install_dir);
    // Clear any previous install first: files renamed or removed upstream
    // must not linger as stale skill content under ~/.claude/skills/.
    fs.rmSync(dest, { recursive: true, force: true });
    if (skill.kind === "generator") {
      fs.mkdirSync(dest, { recursive: true });
      for (const bundlePath of skill.bundle_paths) {
        const bundleSource = path.join(src, bundlePath);
        const bundleDest = path.join(dest, bundlePath);
        if (fs.statSync(bundleSource).isDirectory()) {
          cpR(bundleSource, bundleDest);
        } else {
          fs.mkdirSync(path.dirname(bundleDest), { recursive: true });
          fs.copyFileSync(bundleSource, bundleDest);
        }
      }
    } else {
      cpR(src, dest);
    }
    console.log(`  ✓ ${name} → ${dest}`);
  }
  return failed;
}

function cmdInstallAll(label = "Installing") {
  const all = catalogSkills().map((skill) => skill.name);
  if (!all.length) {
    console.log("No skills available.");
    return 1;
  }
  console.log(`${label} all ${all.length} skills...\n`);
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
    const skill = resolveSkill(name);
    if (!skill) {
      console.log(`  ✗ ${name} — not found in skill catalog`);
      failed++;
      continue;
    }
    // Keep removing legacy bare persona directories when they exist, while
    // resolving every public name through the catalog's canonical target.
    const candidates = [path.join(SKILLS_DIR, skill.install_dir)];
    if (name !== skill.install_dir) candidates.push(path.join(SKILLS_DIR, name));
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

function doctorData() {
  const masters = availableMasters();
  const installed = installedSkillDirs();
  const expectedInstalled = masters.filter((m) => installed.includes(m.name));
  const missingSkillMd = masters.filter((m) => {
    const masterDir = path.join(PREBUILT, m.name);
    return !fs.existsSync(path.join(masterDir, "SKILL.md"));
  });
  const problems = missingSkillMd.map((m) => ({
    code: "missing-skill-md",
    name: m.name,
    message: `${m.name} is missing SKILL.md`,
  }));

  return {
    packageVersion: pkgVersion(),
    nodeVersion: process.version,
    prebuiltPath: PREBUILT,
    skillsPath: SKILLS_DIR,
    availableSkills: masters.length,
    installedKnownSkills: expectedInstalled.length,
    otherInstalledSkillDirs: installed.length - expectedInstalled.length,
    status: problems.length ? "problems" : "ok",
    problems,
  };
}

function cmdDoctor({ json = false } = {}) {
  const data = doctorData();
  if (json) {
    printJson(data);
    return data.problems.length ? 1 : 0;
  }

  console.log(`master-skill doctor\n`);
  console.log(`Package version: ${data.packageVersion}`);
  console.log(`Node version: ${data.nodeVersion}`);
  console.log(`Prebuilt path: ${data.prebuiltPath}`);
  console.log(`Claude skills path: ${data.skillsPath}`);
  console.log(`Available skills: ${data.availableSkills}`);
  console.log(`Installed known skills: ${data.installedKnownSkills}`);
  console.log(`Other installed skill dirs: ${data.otherInstalledSkillDirs}`);

  if (data.problems.length) {
    console.log(`\nProblems:`);
    for (const problem of data.problems) {
      console.log(`  ✗ ${problem.message}`);
    }
    return 1;
  }

  console.log(`\nStatus: ok`);
  return 0;
}

function inspectData(name) {
  const masterDir = resolveMasterDir(name);
  if (!masterDir) return null;

  const dirName = path.basename(masterDir);
  const skillMd = path.join(masterDir, "SKILL.md");
  const metaPath = path.join(masterDir, "meta.json");
  const fm = fs.existsSync(skillMd) ? parseFrontmatter(skillMd) : {};
  const meta = fs.existsSync(metaPath) ? readJson(metaPath) : {};
  const sources = sourceIds(meta);

  return {
    name: dirName,
    displayName: meta.name || null,
    slug: meta.slug || dirName.replace(/^master-/, ""),
    version: fm.version || meta.version || null,
    tradition: meta.tradition || null,
    school: meta.school || null,
    era: meta.era || null,
    installed: fs.existsSync(path.join(SKILLS_DIR, dirName)),
    liveGrounding: hasLiveGrounding(masterDir),
    citationFormat: fm.citation_format || null,
    sources,
    searchKeywords: meta.search_scope?.keywords || [],
  };
}

function cmdInspect(name, { json = false } = {}) {
  if (!name) {
    console.log("Usage: master-skill inspect <name>");
    return 1;
  }
  if (!isSafeName(name)) {
    console.log(`  ✗ ${name} — invalid name (letters, digits, "-", "_" only)`);
    return 1;
  }

  const data = inspectData(name);
  if (!data) {
    console.log(`  ✗ ${name} — not found in prebuilt/ (tried "${name}" and "master-${name}")`);
    return 1;
  }

  if (json) {
    printJson(data);
    return 0;
  }

  console.log(`${data.name}\n`);
  console.log(`Display name: ${data.displayName || "(none)"}`);
  console.log(`Slug: ${data.slug}`);
  console.log(`Version: ${data.version || "(unknown)"}`);
  console.log(`Tradition: ${data.tradition || "(unspecified)"}`);
  console.log(`School: ${data.school || "(unspecified)"}`);
  console.log(`Era: ${data.era || "(unspecified)"}`);
  console.log(`Installed: ${data.installed ? "yes" : "no"}`);
  console.log(`Live grounding: ${data.liveGrounding ? "yes" : "no"}`);
  console.log(`Citation format: ${data.citationFormat || "(not declared in SKILL frontmatter)"}`);

  if (data.sources.length) {
    console.log(`\nSources (${data.sources.length}):`);
    for (const source of data.sources) console.log(`  - ${source}`);
  } else {
    console.log(`\nSources: none declared in meta.json`);
  }

  if (data.searchKeywords.length) {
    const keywords = data.searchKeywords.slice(0, 12).join(", ");
    const suffix = data.searchKeywords.length > 12 ? ", ..." : "";
    console.log(`\nSearch keywords: ${keywords}${suffix}`);
  }

  return 0;
}

function showHelp() {
  console.log(`
master-skill v${pkgVersion()} — Buddhist Master AI Skills installer

Usage:
  master-skill install <name...>   Install skills to ~/.claude/skills/
  master-skill install --all       Install all 19 available skills
  master-skill update --all        Reinstall all skills, clearing stale files
  master-skill list                List available skills
  master-skill list --json         Print available skills as JSON
  master-skill inspect <name>      Show source/runtime metadata for one master
  master-skill inspect <name> --json
  master-skill doctor              Check local install and runtime paths
  master-skill doctor --json       Print diagnostics as JSON
  master-skill uninstall <name...> Remove installed masters
  master-skill --version           Print version
  master-skill --help              Show this help

Persona names accept both short (zhiyi) and full (master-zhiyi) forms.
Teaching modes and create-master use their public catalog names.

Examples:
  npx master-skill install zhiyi fazang
  npx master-skill install master-milarepa master-tsongkhapa
  npx master-skill install compare-masters
  npx master-skill install create-master
  npx master-skill install --all
  npx master-skill update --all
  npx master-skill list
  npx master-skill inspect huineng
  npx master-skill doctor
  npx master-skill uninstall zhiyi
`);
}

// --- main ---

if (CATALOG) {
  const args = process.argv.slice(2);
  const json = args.includes("--json");
  const positionalArgs = args.filter((arg) => arg !== "--json");
  const cmd = positionalArgs[0];

  if (!cmd || cmd === "--help" || cmd === "-h") {
    showHelp();
  } else if (cmd === "--version" || cmd === "-v") {
    console.log(pkgVersion());
  } else if (cmd === "list") {
    cmdList({ json });
  } else if (cmd === "doctor") {
    if (cmdDoctor({ json }) > 0) process.exitCode = 1;
  } else if (cmd === "inspect") {
    if (cmdInspect(positionalArgs[1], { json }) > 0) process.exitCode = 1;
  } else if (cmd === "install") {
    const rest = positionalArgs.slice(1);
    if (rest.includes("--all")) {
      if (cmdInstallAll("Installing") > 0) process.exitCode = 1;
    } else if (rest.length === 0) {
      console.log("Usage: master-skill install <name...> | --all");
      process.exitCode = 1;
    } else {
      if (cmdInstall(rest) > 0) process.exitCode = 1;
    }
  } else if (cmd === "update") {
    const rest = positionalArgs.slice(1);
    if (rest.length === 1 && rest[0] === "--all") {
      if (cmdInstallAll("Updating") > 0) process.exitCode = 1;
    } else {
      console.log("Usage: master-skill update --all");
      process.exitCode = 1;
    }
  } else if (cmd === "uninstall") {
    const rest = positionalArgs.slice(1);
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
}
