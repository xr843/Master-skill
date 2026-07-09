// CLI integration tests — run with: node --test tests/cli.test.mjs
//
// Each test spawns bin/cli.mjs as a child process with HOME/USERPROFILE
// pointed at a temp dir, so installs never touch the real ~/.claude/skills.
// os.homedir() reads HOME on POSIX and USERPROFILE on Windows; setting both
// keeps the suite green on every CI runner.

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.join(__dirname, "..");
const CLI = path.join(REPO, "bin", "cli.mjs");

function run(args, env = {}) {
  try {
    const stdout = execFileSync(process.execPath, [CLI, ...args], {
      encoding: "utf8",
      env: { ...process.env, ...env },
    });
    return { stdout, code: 0 };
  } catch (err) {
    // err.status is null when the child died to a signal — surface -1 so an
    // assertion failure reads as "crashed", not a confusing null-vs-1 diff.
    return { stdout: (err.stdout || "") + (err.stderr || ""), code: err.status ?? -1 };
  }
}

function tmpHome(t) {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "master-skill-cli-test-"));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  return { home, env: { HOME: home, USERPROFILE: home } };
}

function skillsDir(home) {
  return path.join(home, ".claude", "skills");
}

const prebuiltMasters = fs
  .readdirSync(path.join(REPO, "prebuilt"), { withFileTypes: true })
  .filter((d) => d.isDirectory() && d.name !== "compare")
  .map((d) => d.name);

test("list names every prebuilt master with its description", () => {
  const { stdout, code } = run(["list"]);
  assert.equal(code, 0);
  assert.match(stdout, new RegExp(`Available masters \\(${prebuiltMasters.length}\\)`));
  for (const name of prebuiltMasters) {
    assert.ok(stdout.includes(name), `missing ${name} in list output`);
  }
  // Frontmatter must parse (incl. CRLF checkouts): every listed master has a
  // non-empty description, so at least one known description string appears.
  assert.match(stdout, /master-huineng\s+\S/);
});

test("list --json returns machine-readable master inventory", () => {
  const { stdout, code } = run(["list", "--json"]);
  assert.equal(code, 0);
  const payload = JSON.parse(stdout);
  assert.equal(payload.count, prebuiltMasters.length);
  assert.equal(payload.masters.length, prebuiltMasters.length);
  assert.ok(
    payload.masters.some((master) => master.name === "master-huineng" && master.description),
    "missing master-huineng inventory item"
  );
});

test("--version prints the package.json version", () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(REPO, "package.json"), "utf8"));
  const { stdout, code } = run(["--version"]);
  assert.equal(code, 0);
  assert.equal(stdout.trim(), pkg.version);
});

test("help shows the current version, not a hardcoded one", () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(REPO, "package.json"), "utf8"));
  const { stdout, code } = run(["--help"]);
  assert.equal(code, 0);
  assert.ok(stdout.includes(`v${pkg.version}`));
  assert.match(stdout, /master-skill doctor/);
  assert.match(stdout, /master-skill inspect <name>/);
  assert.match(stdout, /master-skill update --all/);
});

test("doctor reports local runtime paths and available skills", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["doctor"], env);
  assert.equal(code, 0);
  assert.match(stdout, /master-skill doctor/);
  assert.match(stdout, /Package version:/);
  assert.match(stdout, /Node version:/);
  assert.match(stdout, new RegExp(`Available skills: ${prebuiltMasters.length}`));
  assert.match(stdout, /Installed known skills: 0/);
  assert.match(stdout, /Status: ok/);
});

test("doctor --json returns machine-readable runtime diagnostics", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["doctor", "--json"], env);
  assert.equal(code, 0);
  const payload = JSON.parse(stdout);
  assert.equal(payload.packageVersion, JSON.parse(fs.readFileSync(path.join(REPO, "package.json"), "utf8")).version);
  assert.equal(payload.nodeVersion, process.version);
  assert.equal(payload.availableSkills, prebuiltMasters.length);
  assert.equal(payload.installedKnownSkills, 0);
  assert.equal(payload.status, "ok");
  assert.deepEqual(payload.problems, []);
});

test("doctor counts installed known skills", (t) => {
  const { env } = tmpHome(t);
  run(["install", "zhiyi"], env);
  const { stdout, code } = run(["doctor"], env);
  assert.equal(code, 0);
  assert.match(stdout, /Installed known skills: 1/);
});

test("inspect shows master metadata, sources, and live grounding", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["inspect", "huineng"], env);
  assert.equal(code, 0);
  assert.match(stdout, /^master-huineng/m);
  assert.match(stdout, /Display name: 慧能大师/);
  assert.match(stdout, /Slug: huineng/);
  assert.match(stdout, /Tradition: 汉传/);
  assert.match(stdout, /Installed: no/);
  assert.match(stdout, /Live grounding: yes/);
  assert.match(stdout, /T48n2008/);
});

test("inspect --json returns machine-readable master metadata", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["inspect", "huineng", "--json"], env);
  assert.equal(code, 0);
  const payload = JSON.parse(stdout);
  assert.equal(payload.name, "master-huineng");
  assert.equal(payload.displayName, "慧能大师");
  assert.equal(payload.slug, "huineng");
  assert.equal(payload.tradition, "汉传");
  assert.equal(payload.installed, false);
  assert.equal(payload.liveGrounding, true);
  assert.ok(payload.sources.some((source) => source.includes("T48n2008")));
});

test("inspect reflects installed state", (t) => {
  const { env } = tmpHome(t);
  run(["install", "huineng"], env);
  const { stdout, code } = run(["inspect", "master-huineng"], env);
  assert.equal(code, 0);
  assert.match(stdout, /Installed: yes/);
});

test("inspect rejects missing and unsafe names", (t) => {
  const { env } = tmpHome(t);
  const missing = run(["inspect", "no-such-master"], env);
  assert.equal(missing.code, 1);
  assert.match(missing.stdout, /not found/);

  const unsafe = run(["inspect", "../escape"], env);
  assert.equal(unsafe.code, 1);
  assert.match(unsafe.stdout, /invalid name/);
});

test("install accepts short and full names", (t) => {
  const { home, env } = tmpHome(t);
  const { code } = run(["install", "zhiyi", "master-fazang"], env);
  assert.equal(code, 0);
  assert.ok(fs.existsSync(path.join(skillsDir(home), "master-zhiyi", "SKILL.md")));
  assert.ok(fs.existsSync(path.join(skillsDir(home), "master-fazang", "SKILL.md")));
});

test("reinstall clears stale files from a previous version", (t) => {
  const { home, env } = tmpHome(t);
  run(["install", "zhiyi"], env);
  const stale = path.join(skillsDir(home), "master-zhiyi", "sources", "removed-in-new-version.md");
  fs.writeFileSync(stale, "stale content");
  const { code } = run(["install", "zhiyi"], env);
  assert.equal(code, 0);
  assert.ok(!fs.existsSync(stale), "stale file survived reinstall");
  assert.ok(fs.existsSync(path.join(skillsDir(home), "master-zhiyi", "SKILL.md")));
});

test("install of an unknown master exits non-zero", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["install", "no-such-master"], env);
  assert.equal(code, 1);
  assert.match(stdout, /not found/);
});

test("install rejects path-traversal names", (t) => {
  const { home, env } = tmpHome(t);
  const { stdout, code } = run(["install", "../escape"], env);
  assert.equal(code, 1);
  assert.match(stdout, /invalid name/);
  assert.ok(!fs.existsSync(path.join(home, ".claude", "escape")));
});

test("uninstall rejects path-traversal names without touching the filesystem", (t) => {
  const { home, env } = tmpHome(t);
  // The victim sits where "../victim" would resolve from ~/.claude/skills/.
  const victim = path.join(home, ".claude", "victim");
  fs.mkdirSync(victim, { recursive: true });
  const { stdout, code } = run(["uninstall", "../victim"], env);
  assert.equal(code, 1);
  assert.match(stdout, /invalid name/);
  assert.ok(fs.existsSync(victim), "victim dir was deleted by traversal");
});

test("partial failure still installs the valid names but exits non-zero", (t) => {
  const { home, env } = tmpHome(t);
  const { code } = run(["install", "zhiyi", "no-such-master"], env);
  assert.equal(code, 1);
  assert.ok(fs.existsSync(path.join(skillsDir(home), "master-zhiyi", "SKILL.md")));
});

test("uninstall removes an installed master", (t) => {
  const { home, env } = tmpHome(t);
  run(["install", "zhiyi"], env);
  const { code } = run(["uninstall", "zhiyi"], env);
  assert.equal(code, 0);
  assert.ok(!fs.existsSync(path.join(skillsDir(home), "master-zhiyi")));
});

test("uninstall of a not-installed master exits non-zero", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["uninstall", "zhiyi"], env);
  assert.equal(code, 1);
  assert.match(stdout, /not installed/);
});

test("install --all installs every prebuilt master", (t) => {
  const { home, env } = tmpHome(t);
  const { code } = run(["install", "--all"], env);
  assert.equal(code, 0);
  for (const name of prebuiltMasters) {
    assert.ok(
      fs.existsSync(path.join(skillsDir(home), name, "SKILL.md")),
      `missing ${name} after install --all`
    );
  }
});

test("update --all reinstalls every master and clears stale files", (t) => {
  const { home, env } = tmpHome(t);
  run(["install", "zhiyi"], env);
  const stale = path.join(skillsDir(home), "master-zhiyi", "stale.md");
  fs.writeFileSync(stale, "stale");

  const { stdout, code } = run(["update", "--all"], env);
  assert.equal(code, 0);
  assert.match(stdout, new RegExp(`Updating all ${prebuiltMasters.length} masters`));
  assert.ok(!fs.existsSync(stale), "stale file survived update --all");
  for (const name of prebuiltMasters) {
    assert.ok(
      fs.existsSync(path.join(skillsDir(home), name, "SKILL.md")),
      `missing ${name} after update --all`
    );
  }
});

test("update requires --all", (t) => {
  const { env } = tmpHome(t);
  const { stdout, code } = run(["update"], env);
  assert.equal(code, 1);
  assert.match(stdout, /Usage: master-skill update --all/);
});

test("unknown command exits non-zero", () => {
  const { code } = run(["frobnicate"]);
  assert.equal(code, 1);
});

// Deterministic CRLF coverage: the windows-latest job only exercises CRLF
// because the repo lacks .gitattributes and the runner defaults autocrlf=true.
// This test pins the code path on every OS by building a synthetic install
// tree whose SKILL.md is written with \r\n line endings.
test("list parses frontmatter from CRLF files", (t) => {
  const tree = fs.mkdtempSync(path.join(os.tmpdir(), "master-skill-crlf-test-"));
  t.after(() => fs.rmSync(tree, { recursive: true, force: true }));

  fs.mkdirSync(path.join(tree, "bin"));
  fs.copyFileSync(CLI, path.join(tree, "bin", "cli.mjs"));
  fs.writeFileSync(path.join(tree, "package.json"), '{"version": "0.0.0-test"}');
  const masterDir = path.join(tree, "prebuilt", "master-crlf");
  fs.mkdirSync(masterDir, { recursive: true });
  fs.writeFileSync(
    path.join(masterDir, "SKILL.md"),
    "---\r\nname: master-crlf\r\ndescription: CRLF survives parsing\r\n---\r\n\r\n# body\r\n"
  );

  const stdout = execFileSync(process.execPath, [path.join(tree, "bin", "cli.mjs"), "list"], {
    encoding: "utf8",
  });
  assert.match(stdout, /master-crlf\s+CRLF survives parsing/);
});
