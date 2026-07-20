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
const CATALOG_PATH = path.join(REPO, "skill-catalog.json");
const PYTHON = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");

function npmExecutionOptions(platform = process.platform) {
  return { shell: platform === "win32" };
}

test("npm pack enables a shell only on Windows", () => {
  assert.deepEqual(npmExecutionOptions("win32"), { shell: true });
  assert.deepEqual(npmExecutionOptions("linux"), { shell: false });
});

function run(args, env = {}, cli = CLI) {
  try {
    const stdout = execFileSync(process.execPath, [cli, ...args], {
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

function catalogFixture(t, catalog, setup = () => {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "master-skill-catalog-test-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, "bin"), { recursive: true });
  fs.copyFileSync(CLI, path.join(root, "bin", "cli.mjs"));
  fs.writeFileSync(path.join(root, "package.json"), '{"version":"0.0.0-test"}');
  fs.writeFileSync(path.join(root, "skill-catalog.json"), JSON.stringify(catalog));
  setup(root);
  return { root, cli: path.join(root, "bin", "cli.mjs") };
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

test("skill catalog declares 20 unique installable skills", () => {
  const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf8"));
  assert.equal(catalog.version, 1);
  assert.equal(catalog.skills.length, 20);
  const counts = catalog.skills.reduce((groups, skill) => {
    (groups[skill.kind] ||= []).push(skill);
    return groups;
  }, {});
  assert.equal(counts.persona.length, 15);
  assert.equal(counts["teaching-mode"].length, 4);
  assert.equal(counts.generator.length, 1);
  for (const field of ["name", "source", "install_dir"]) {
    assert.equal(new Set(catalog.skills.map((skill) => skill[field])).size, 20);
  }
  const aliases = catalog.skills.flatMap((skill) => skill.aliases);
  assert.equal(new Set(aliases).size, aliases.length);
  const generator = catalog.skills.find((skill) => skill.name === "create-master");
  assert.deepEqual(generator.bundle_paths, [
    "SKILL.md", "tools", "prompts", "references", "requirements.txt",
    "ETHICS.md", "masters",
  ]);
});

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

test("list groups every public skill by kind", () => {
  const { stdout, code } = run(["list"]);
  assert.equal(code, 0);
  assert.match(stdout, /Personas \(15\)/);
  assert.match(stdout, /Teaching modes \(4\)/);
  assert.match(stdout, /Generator \(1\)/);
  assert.match(stdout, /compare-masters/);
  assert.match(stdout, /create-master/);
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

test("list --json exposes all skills while retaining masters compatibility", () => {
  const result = run(["list", "--json"]);
  assert.equal(result.code, 0);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.count, prebuiltMasters.length);
  assert.equal(payload.skillCount, 20);
  assert.equal(payload.skills.length, 20);
  assert.equal(payload.categoryCounts.persona, 15);
  assert.equal(payload.categoryCounts["teaching-mode"], 4);
  assert.equal(payload.categoryCounts.generator, 1);
  assert.ok(Array.isArray(payload.masters));
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
  assert.match(stdout, /Remove installed skills/);
  assert.doesNotMatch(stdout, /Remove installed masters/);
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

test("public compare-masters name installs to its public directory", (t) => {
  const { home, env } = tmpHome(t);
  assert.equal(run(["install", "compare-masters"], env).code, 0);
  assert.ok(fs.existsSync(path.join(skillsDir(home), "compare-masters", "SKILL.md")));
});

test("install create-master copies a self-contained generator bundle", (t) => {
  const { home, env } = tmpHome(t);
  assert.equal(run(["install", "create-master"], env).code, 0);
  const root = path.join(skillsDir(home), "create-master");
  for (const required of [
    "SKILL.md", "tools/sutra_collector.py", "prompts/intake.md",
    "references/workflow-details.md", "requirements.txt", "ETHICS.md", "masters",
  ]) assert.ok(fs.existsSync(path.join(root, required)), `missing ${required}`);
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

test("updating create-master preserves user-generated personas", (t) => {
  const { home, env } = tmpHome(t);
  assert.equal(run(["install", "create-master"], env).code, 0);

  const generatorRoot = path.join(skillsDir(home), "create-master");
  const customMaster = path.join(generatorRoot, "masters", "my-custom-master");
  fs.mkdirSync(customMaster, { recursive: true });
  fs.writeFileSync(
    path.join(customMaster, "meta.json"),
    JSON.stringify({ name: "My Custom Master", version: "1.0.0" })
  );
  fs.writeFileSync(path.join(customMaster, "SKILL.md"), "user-generated\n");
  const staleRuntime = path.join(generatorRoot, "stale-runtime.txt");
  fs.writeFileSync(staleRuntime, "old package content\n");

  const result = run(["update", "--all"], env);
  assert.equal(result.code, 0, result.stdout);
  assert.equal(
    fs.readFileSync(path.join(customMaster, "SKILL.md"), "utf8"),
    "user-generated\n"
  );
  assert.ok(fs.existsSync(path.join(customMaster, "meta.json")));
  assert.ok(!fs.existsSync(staleRuntime), "stale generator runtime survived update");
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

test("uninstall resolves a public teaching-mode name", (t) => {
  const { home, env } = tmpHome(t);
  assert.equal(run(["install", "compare-masters"], env).code, 0);
  assert.equal(run(["uninstall", "compare-masters"], env).code, 0);
  assert.ok(!fs.existsSync(path.join(skillsDir(home), "compare-masters")));
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

test("install --all installs all 20 public skill directories", (t) => {
  const { home, env } = tmpHome(t);
  assert.equal(run(["install", "--all"], env).code, 0);
  const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf8"));
  for (const skill of catalog.skills) {
    assert.ok(
      fs.existsSync(path.join(skillsDir(home), skill.install_dir, "SKILL.md")),
      skill.name
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
  assert.match(stdout, /Updating all 20 skills/);
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

test("catalog name fields reject non-strings before filesystem mutation", (t) => {
  const cases = [];
  for (const invalid of [123, true, null]) {
    cases.push({
      label: `name ${String(invalid)}`,
      mutate(skill) { skill.name = invalid; },
      expected: /Invalid skill catalog: skills\[0\]\.name/,
    });
    cases.push({
      label: `install_dir ${String(invalid)}`,
      mutate(skill) { skill.install_dir = invalid; },
      expected: /Invalid skill catalog: skills\[0\]\.install_dir/,
    });
    cases.push({
      label: `alias ${String(invalid)}`,
      mutate(skill) { skill.aliases = [invalid]; },
      expected: /Invalid skill catalog: skills\[0\]\.aliases/,
    });
  }

  for (const fixtureCase of cases) {
    const skill = {
      name: "demo",
      kind: "persona",
      source: "prebuilt/demo",
      install_dir: "demo",
      aliases: ["demo-alias"],
    };
    fixtureCase.mutate(skill);
    const fixture = catalogFixture(
      t,
      { version: 1, skills: [skill] },
      (root) => {
        const source = path.join(root, "prebuilt", "demo");
        fs.mkdirSync(source, { recursive: true });
        fs.writeFileSync(path.join(source, "SKILL.md"), "---\nname: demo\n---\n");
      }
    );
    const { home, env } = tmpHome(t);
    const result = run(["install", "demo"], env, fixture.cli);
    assert.equal(result.code, 1, fixtureCase.label);
    assert.match(result.stdout, fixtureCase.expected, fixtureCase.label);
    assert.ok(!fs.existsSync(skillsDir(home)), `${fixtureCase.label} mutated the filesystem`);
  }
});

test("catalog rejects alias and canonical-name collisions in either record order", (t) => {
  const aliasOwner = {
    name: "demo-one",
    kind: "persona",
    source: "prebuilt/demo-one",
    install_dir: "demo-one",
    aliases: ["demo-two"],
  };
  const canonicalOwner = {
    name: "demo-two",
    kind: "persona",
    source: "prebuilt/demo-two",
    install_dir: "demo-two",
    aliases: ["two"],
  };
  const orders = [
    [aliasOwner, canonicalOwner],
    [canonicalOwner, aliasOwner],
  ];

  for (const [index, skills] of orders.entries()) {
    const fixture = catalogFixture(
      t,
      { version: 1, skills },
      (root) => {
        for (const name of ["demo-one", "demo-two"]) {
          const source = path.join(root, "prebuilt", name);
          fs.mkdirSync(source, { recursive: true });
          fs.writeFileSync(path.join(source, "SKILL.md"), "---\nname: demo\n---\n");
        }
      }
    );
    const { home, env } = tmpHome(t);
    const result = run(["install", "demo-two"], env, fixture.cli);
    assert.equal(result.code, 1, `record order ${index + 1}`);
    assert.match(
      result.stdout,
      /Invalid skill catalog: alias "demo-two" conflicts with skill/,
      `record order ${index + 1}`
    );
    assert.ok(!fs.existsSync(skillsDir(home)), `record order ${index + 1} mutated filesystem`);
  }
});

test("invalid catalogs fail before filesystem mutation", (t) => {
  const cases = [
    {
      name: "unsupported version",
      catalog: { version: 2, skills: [] },
      expected: /Invalid skill catalog: version must be 1/,
    },
    {
      name: "unsafe source path",
      catalog: {
        version: 1,
        skills: [{
          name: "demo", kind: "persona", source: "../escape",
          install_dir: "demo", aliases: ["demo-alias"],
        }],
      },
      expected: /Invalid skill catalog:.*source/,
    },
    {
      name: "duplicate alias",
      catalog: {
        version: 1,
        skills: [
          {
            name: "demo-one", kind: "persona", source: "prebuilt/demo-one",
            install_dir: "demo-one", aliases: ["duplicate"],
          },
          {
            name: "demo-two", kind: "persona", source: "prebuilt/demo-two",
            install_dir: "demo-two", aliases: ["duplicate"],
          },
        ],
      },
      setup(root) {
        for (const name of ["demo-one", "demo-two"]) {
          const source = path.join(root, "prebuilt", name);
          fs.mkdirSync(source, { recursive: true });
          fs.writeFileSync(path.join(source, "SKILL.md"), "---\nname: demo\n---\n");
        }
      },
      expected: /Invalid skill catalog: duplicate alias/,
    },
    {
      name: "missing source",
      catalog: {
        version: 1,
        skills: [{
          name: "demo", kind: "persona", source: "prebuilt/demo",
          install_dir: "demo", aliases: ["demo-alias"],
        }],
      },
      expected: /Invalid skill catalog: source does not exist/,
    },
    {
      name: "missing generator bundle entry",
      catalog: {
        version: 1,
        skills: [{
          name: "create-master", kind: "generator", source: ".",
          install_dir: "create-master", aliases: ["create-master"],
          bundle_paths: ["missing-runtime"],
        }],
      },
      expected: /Invalid skill catalog: bundle path does not exist/,
    },
  ];

  for (const fixtureCase of cases) {
    const fixture = catalogFixture(t, fixtureCase.catalog, fixtureCase.setup);
    const { home, env } = tmpHome(t);
    const result = run(["install", "demo"], env, fixture.cli);
    assert.equal(result.code, 1, fixtureCase.name);
    assert.match(result.stdout, fixtureCase.expected, fixtureCase.name);
    assert.ok(!fs.existsSync(skillsDir(home)), `${fixtureCase.name} mutated the filesystem`);
  }
});

test("packed npm artifact installs all skills with the complete generator runtime", (t) => {
  const packOutput = execFileSync("npm", ["pack", "--silent"], {
    cwd: REPO,
    encoding: "utf8",
    ...npmExecutionOptions(),
  });
  const tarballName = packOutput.trim().split(/\r?\n/).at(-1);
  const tarballPath = path.join(REPO, tarballName);
  t.after(() => fs.rmSync(tarballPath, { force: true }));

  const extractRoot = fs.mkdtempSync(path.join(os.tmpdir(), "master-skill-pack-test-"));
  t.after(() => fs.rmSync(extractRoot, { recursive: true, force: true }));
  execFileSync("tar", ["-xzf", tarballPath, "-C", extractRoot]);

  const packageRoot = path.join(extractRoot, "package");
  const packagedCli = path.join(packageRoot, "bin", "cli.mjs");
  const { home, env } = tmpHome(t);
  const result = run(["install", "--all"], env, packagedCli);
  assert.equal(result.code, 0, result.stdout);

  const catalog = JSON.parse(
    fs.readFileSync(path.join(packageRoot, "skill-catalog.json"), "utf8")
  );
  for (const skill of catalog.skills) {
    assert.ok(
      fs.existsSync(path.join(skillsDir(home), skill.install_dir, "SKILL.md")),
      `missing packed install ${skill.name}`
    );
  }

  const generatorRoot = path.join(skillsDir(home), "create-master");
  for (const required of [
    "SKILL.md", "tools/sutra_collector.py", "prompts/intake.md",
    "references/workflow-details.md", "requirements.txt", "ETHICS.md", "masters",
  ]) {
    assert.ok(
      fs.existsSync(path.join(generatorRoot, required)),
      `missing packed generator runtime ${required}`
    );
  }

  // Prove the installed generator is operational without reaching back into
  // the transient npm extraction. This is the real publication boundary: the
  // package source disappears before any generator entry point is invoked.
  fs.rmSync(packageRoot, { recursive: true, force: true });
  assert.ok(!fs.existsSync(packageRoot), "packed source extraction still exists");

  const collectedPath = path.join(home, "offline-collected.json");
  const generatedRoot = path.join(home, "offline-generated-masters");
  const collectorOutput = execFileSync(
    PYTHON,
    [
      path.join(generatorRoot, "tools", "sutra_collector.py"),
      "--offline-smoke",
      "--name", "Offline Demo",
      "--tradition", "南传",
      "--output", collectedPath,
    ],
    { encoding: "utf8", cwd: generatorRoot }
  );
  assert.equal(collectorOutput.trim(), `collected data written: ${collectedPath}`);

  const initialCheck = execFileSync(
    PYTHON,
    [
      path.join(generatorRoot, "tools", "verify_sources.py"),
      "--check-links", collectedPath,
    ],
    { encoding: "utf8", cwd: generatorRoot }
  );
  assert.equal(initialCheck.trim(), "declared sources OK (1 sources)");

  const builderOutput = execFileSync(
    PYTHON,
    [
      path.join(generatorRoot, "tools", "master_builder.py"),
      "--offline-smoke",
      "--output", generatedRoot,
    ],
    { encoding: "utf8", cwd: generatorRoot }
  );
  const generated = JSON.parse(builderOutput);
  assert.ok(fs.existsSync(generated.meta_path), "offline builder did not write meta.json");
  assert.ok(
    fs.existsSync(generated.review_input_path),
    "offline builder did not persist the doctrine review input"
  );

  const finalCheck = execFileSync(
    PYTHON,
    [
      path.join(generatorRoot, "tools", "verify_sources.py"),
      "--final-check", generated.teacher_dir,
    ],
    { encoding: "utf8", cwd: generatorRoot }
  );
  assert.equal(finalCheck.trim(), "final source check OK (1 sources)");
});

test("both READMEs document the complete npm installation contract", () => {
  const chinese = fs.readFileSync(path.join(REPO, "README.md"), "utf8");
  const english = fs.readFileSync(path.join(REPO, "README_EN.md"), "utf8");

  assert.match(chinese, /全部 20 个 Skill：15 位祖师、4 个教学模式（含 `\/master-help` 路由），以及 `create-master` 生成器/);
  assert.match(english, /all 20 skills: 15 personas, 4 teaching modes \(including the `\/master-help` router\), and the `create-master` generator/);
  for (const readme of [chinese, english]) {
    assert.match(readme, /npx master-skill install compare-masters/);
    assert.match(readme, /npx master-skill install create-master/);
  }
});

test("both README clone examples install compare under its public name", () => {
  for (const filename of ["README.md", "README_EN.md"]) {
    const readme = fs.readFileSync(path.join(REPO, filename), "utf8");
    assert.match(readme, /for d in prebuilt\/master-\*\/;/, filename);
    assert.match(
      readme,
      /ln -sf "\$\(pwd\)\/prebuilt\/compare" ~\/\.claude\/skills\/compare-masters/,
      filename
    );
    assert.doesNotMatch(readme, /for d in prebuilt\/\*\/;/, filename);
  }
});

test("fidelity runner --json emits parseable JSON without text banners", () => {
  const stdout = execFileSync(
    PYTHON,
    [
      path.join(REPO, "scripts", "test-fidelity.py"),
      "--master",
      "master-huineng",
      "--dry-run",
      "--json",
      "--max-tests",
      "1",
    ],
    { encoding: "utf8" }
  );

  const payload = JSON.parse(stdout);
  assert.equal(payload.length, 1);
  assert.equal(payload[0].master, "master-huineng");
  assert.equal(payload[0].total, 1);
  assert.equal(payload[0].results.length, 1);
  assert.equal(payload[0].results[0].status, "dry_run");
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
  fs.writeFileSync(path.join(tree, "skill-catalog.json"), JSON.stringify({
    version: 1,
    skills: [{
      name: "master-crlf",
      kind: "persona",
      source: "prebuilt/master-crlf",
      install_dir: "master-crlf",
      aliases: ["crlf", "master-crlf"],
    }],
  }));
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

// --- recommend ---
//
// The mode-routing cases below are lifted verbatim from the "示例输入分类"
// table in references/teaching-modes.md, which already ships ten user
// utterances labelled with their expected mode. Reusing them keeps the
// executable router and the prose decision tree from drifting apart: if
// someone edits that table, these tests are where the disagreement surfaces.

function recommendJson(query) {
  const { stdout, code } = run(["recommend", query, "--json"]);
  assert.equal(code, 0, `recommend exited ${code} for ${query}`);
  return JSON.parse(stdout);
}

const MODE_FIXTURES = [
  ["禅宗和净土宗怎么比较", "compare-masters"],
  ["禅净之争究竟谁更对", "master-debate"],
  ["我想学禅宗从哪开始", "master-curriculum"],
  ["天台和华严的圆教有什么不同", "compare-masters"],
  ["性相之辩玄奘和鸠摩罗什会怎么辩", "master-debate"],
  ["刚开始学藏传，应该读什么", "master-curriculum"],
  ["应成中观和顿悟禅的分判", "master-debate"],
  ["印光大师和虚云老和尚的修法异同", "compare-masters"],
  ["中观、唯识、华严的判教高下", "master-debate"],
  ["想综合学习汉传佛教，应该按什么顺序", "master-curriculum"],
];

for (const [query, expected] of MODE_FIXTURES) {
  test(`recommend routes "${query}" to ${expected}`, () => {
    const data = recommendJson(query);
    assert.equal(data.kind, "teaching-mode");
    assert.equal(data.mode, expected);
    assert.equal(data.resolvedBy, "mode_rules");
    assert.ok(data.matched.length > 0, "a mode match must name its keywords");
  });
}

test("recommend scores personas off meta.json keywords", () => {
  const data = recommendJson("阿赖耶识是什么");
  assert.equal(data.resolvedBy, "persona_keywords");
  assert.equal(data.masters[0].name, "master-xuanzang");
  assert.ok(data.masters[0].matched.includes("阿赖耶识"));
});

test("recommend prefers distinct traditions when scores tie", () => {
  const data = recommendJson("菩提心怎么发");
  const traditions = data.masters.map((m) => m.tradition);
  assert.equal(new Set(traditions).size, traditions.length);
});

test("recommend caps at three masters", () => {
  for (const q of ["菩提心怎么发", "正念怎么修", "戒定慧"]) {
    assert.ok(recommendJson(q).masters.length <= 3, `${q} returned too many`);
  }
});

// Seven single-character doctrinal atoms (空 戒 定 慧 苦 禅 业) sit in
// meta.json keyword lists. Matching by containment made them fire on
// ordinary Chinese, so routing.json.min_keyword_length excludes them.
test("recommend ignores single-character keywords", () => {
  for (const q of ["有空吗", "我戒烟了", "苦不苦", "今天天气不错"]) {
    const data = recommendJson(q);
    assert.equal(data.resolvedBy, "default_pairing", `${q} false-matched`);
  }
});

test("recommend falls back to the default pairing with a reason", () => {
  const data = recommendJson("今天天气不错");
  assert.deepEqual(
    data.masters.map((m) => m.name),
    ["master-kumarajiva", "master-yinguang"]
  );
  assert.ok(data.note, "the fallback must say why it fired");
});

test("recommend is deterministic", () => {
  for (const q of ["菩提心怎么发", "念佛怎么念才算老实", "什么是空性"]) {
    assert.deepEqual(recommendJson(q), recommendJson(q), `${q} varied between runs`);
  }
});

test("recommend joins an unquoted multi-word query", () => {
  const { stdout, code } = run(["recommend", "阿赖耶识", "是什么", "--json"]);
  assert.equal(code, 0);
  assert.equal(JSON.parse(stdout).masters[0].name, "master-xuanzang");
});

test("recommend without a query prints usage and exits 1", () => {
  const { stdout, code } = run(["recommend"]);
  assert.equal(code, 1);
  assert.match(stdout, /Usage: master-skill recommend/);
});

test("recommend appears in help", () => {
  const { stdout } = run(["--help"]);
  assert.match(stdout, /master-skill recommend/);
});

test("routing.json passes its validator", () => {
  const { stdout, code } = (() => {
    try {
      return {
        stdout: execFileSync(PYTHON, [path.join(REPO, "scripts", "validate-routing.py")], {
          encoding: "utf8",
        }),
        code: 0,
      };
    } catch (err) {
      return { stdout: (err.stdout || "") + (err.stderr || ""), code: err.status ?? -1 };
    }
  })();
  assert.equal(code, 0, `validate-routing.py failed:\n${stdout}`);
});

// --- situations (vernacular routing) ---
//
// These rows come from the 「你的状况」 table in README.md, which is keyed on
// what a beginner actually feels ("坐不住") rather than on doctrine ("四念处").
// Four of them used to fall through to the default pairing because no
// search_scope.keywords entry carries that wording. Binding the table to tests
// keeps README, routing.json and the CLI from drifting apart — the same
// contract the teaching-modes fixtures above enforce for mode routing.

const SITUATION_FIXTURES = [
  ["妄念纷飞坐不住", ["master-xuyun", "master-zhiyi", "master-ajahn-chah"], "situations"],
  ["读经文看不懂逻辑", ["master-xuanzang"], "situations"],
  ["学佛很久但无力感", ["master-yinguang"], "situations"],
  ["想学最朴素的禅修", ["master-ajahn-chah"], "situations"],
  ["想系统学华严", ["master-fazang"], "persona_keywords"],
  ["对苦行闭关好奇", ["master-milarepa"], "persona_keywords"],
  ["想了解上座部论藏体系", ["master-buddhaghosa"], "persona_keywords"],
  ["想做密集内观禅修", ["master-mahasi-sayadaw"], "persona_keywords"],
  ["想学完整的道次第", ["master-atisha", "master-tsongkhapa"], "topic_pairings"],
];

for (const [query, expected, layer] of SITUATION_FIXTURES) {
  test(`README situation "${query}" routes via ${layer}`, () => {
    const data = recommendJson(query);
    assert.equal(data.resolvedBy, layer);
    assert.deepEqual(data.masters.map((m) => m.name), expected);
  });
}

// 空性 is the ordinary modern rendering of śūnyatā, but neither Madhyamaka
// master declared it — both listed only 性空 — so the query used to surface
// Milarepa alone.
test("空性 reaches the Madhyamaka masters", () => {
  const data = recommendJson("想了解空性");
  assert.equal(data.resolvedBy, "persona_keywords");
  const names = data.masters.map((m) => m.name);
  assert.ok(names.includes("master-nagarjuna"), `got ${names}`);
  assert.ok(names.includes("master-kumarajiva"), `got ${names}`);
});

// An explicit doctrinal term is stronger evidence than a felt-state phrase,
// so the keyword layer must win when both could match.
test("persona keywords outrank situations", () => {
  const data = recommendJson("念佛的时候妄念很多");
  assert.equal(data.resolvedBy, "persona_keywords");
  assert.ok(data.masters.some((m) => m.name === "master-yinguang"));
});

test("mode routing outranks situations", () => {
  const data = recommendJson("我妄念很多，禅修应该从哪开始学");
  assert.equal(data.resolvedBy, "mode_rules");
  assert.equal(data.mode, "master-curriculum");
});
