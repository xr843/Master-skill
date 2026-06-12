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
    return { stdout: (err.stdout || "") + (err.stderr || ""), code: err.status };
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

test("unknown command exits non-zero", () => {
  const { code } = run(["frobnicate"]);
  assert.equal(code, 1);
});
