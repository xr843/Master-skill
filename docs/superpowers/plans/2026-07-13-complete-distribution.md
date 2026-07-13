# Complete Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the published npm tarball and CLI install all 19 advertised skills, including a self-contained `create-master` generator.

**Architecture:** A root `skill-catalog.json` is the single installation inventory. The CLI resolves aliases through the catalog, copies prebuilt skills to catalog-defined destinations, and copies the generator through an explicit runtime bundle allowlist. Existing `masters` JSON remains compatible while a new complete `skills` collection is added.

**Tech Stack:** Node.js 18+ ESM, `node:test`, npm packing.

## Global Constraints

- The catalog contains exactly 15 `persona`, 3 `teaching-mode`, and 1 `generator` records.
- `install --all` installs 19 `SKILL.md` files.
- `compare-masters` installs from `prebuilt/compare` into `~/.claude/skills/compare-masters`.
- `create-master` bundles exactly `SKILL.md`, `tools/`, `prompts/`, `references/`, `requirements.txt`, `ETHICS.md`, and `masters/`.
- Existing persona aliases and the existing `masters` field in `list --json` remain compatible through v0.10.x.
- Do not edit citation files, CI workflows, Python validators, or Rust files.

---

### Task 1: Add and validate the installation catalog

**Files:**
- Create: `skill-catalog.json`
- Modify: `tests/cli.test.mjs`

**Interfaces:**
- Produces: a JSON object `{ "version": 1, "skills": SkillRecord[] }`.
- `SkillRecord` fields: `name`, `kind`, `source`, `install_dir`, `aliases`, optional `bundle_paths`.

- [ ] **Step 1: Write the failing catalog test**

Add this test setup and assertion to `tests/cli.test.mjs`:

```js
const CATALOG_PATH = path.join(REPO, "skill-catalog.json");

test("skill catalog declares 19 unique installable skills", () => {
  const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf8"));
  assert.equal(catalog.version, 1);
  assert.equal(catalog.skills.length, 19);
  const counts = catalog.skills.reduce((groups, skill) => {
    (groups[skill.kind] ||= []).push(skill);
    return groups;
  }, {});
  assert.equal(counts.persona.length, 15);
  assert.equal(counts["teaching-mode"].length, 3);
  assert.equal(counts.generator.length, 1);
  for (const field of ["name", "source", "install_dir"]) {
    assert.equal(new Set(catalog.skills.map((skill) => skill[field])).size, 19);
  }
  const aliases = catalog.skills.flatMap((skill) => skill.aliases);
  assert.equal(new Set(aliases).size, aliases.length);
  const generator = catalog.skills.find((skill) => skill.name === "create-master");
  assert.deepEqual(generator.bundle_paths, [
    "SKILL.md", "tools", "prompts", "references", "requirements.txt",
    "ETHICS.md", "masters",
  ]);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test --test-name-pattern="skill catalog" tests/cli.test.mjs`  
Expected: FAIL because `skill-catalog.json` does not exist.

- [ ] **Step 3: Create the catalog**

Create records for these exact names:

```text
personas: master-nagarjuna, master-xuanzang, master-kumarajiva,
master-huineng, master-zhiyi, master-fazang, master-yinguang,
master-ouyi, master-xuyun, master-atisha, master-tsongkhapa,
master-milarepa, master-buddhaghosa, master-mahasi-sayadaw,
master-ajahn-chah
teaching modes: compare-masters, master-debate, master-curriculum
generator: create-master
```

Persona sources and install directories equal their names. Persona aliases contain the unprefixed slug plus the full name. Teaching mode sources are `prebuilt/compare`, `prebuilt/master-debate`, and `prebuilt/master-curriculum`; their install directories equal their public names. The generator source is `.` and uses the exact bundle paths in the test.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run: `node --test --test-name-pattern="skill catalog" tests/cli.test.mjs`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skill-catalog.json tests/cli.test.mjs
git commit -m "feat(cli): add complete skill catalog"
```

### Task 2: Drive list and installation through the catalog

**Files:**
- Modify: `bin/cli.mjs`
- Modify: `tests/cli.test.mjs`

**Interfaces:**
- Consumes: `skill-catalog.json` from Task 1.
- Produces: `catalogSkills()`, `resolveSkill(input)`, and catalog-driven `cmdInstallAll()` behavior.

- [ ] **Step 1: Write failing CLI behavior tests**

Add focused tests with the existing `run`, `tmpHome`, and `skillsDir` helpers:

```js
test("list --json exposes all skills while retaining masters compatibility", () => {
  const result = run(["list", "--json"]);
  assert.equal(result.code, 0);
  const payload = JSON.parse(result.stdout);
  assert.equal(payload.count, prebuiltMasters.length);
  assert.equal(payload.skillCount, 19);
  assert.equal(payload.skills.length, 19);
  assert.equal(payload.categoryCounts.persona, 15);
  assert.equal(payload.categoryCounts["teaching-mode"], 3);
  assert.equal(payload.categoryCounts.generator, 1);
  assert.ok(Array.isArray(payload.masters));
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

test("install --all installs all 19 public skill directories", (t) => {
  const { home, env } = tmpHome(t);
  assert.equal(run(["install", "--all"], env).code, 0);
  const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf8"));
  for (const skill of catalog.skills) {
    assert.ok(fs.existsSync(path.join(skillsDir(home), skill.install_dir, "SKILL.md")), skill.name);
  }
});
```

- [ ] **Step 2: Run the four tests and verify RED**

Run: `node --test --test-name-pattern="list --json exposes|compare-masters name|create-master copies|all 19" tests/cli.test.mjs`  
Expected: all four new behaviors fail against directory-derived installation.

- [ ] **Step 3: Implement catalog loading and validation**

In `bin/cli.mjs`, load `skill-catalog.json` relative to the package root. Validate version 1, required strings, safe paths, unique aliases, existing sources, and generator bundle entries. Every validation error must begin with the literal prefix `Invalid skill catalog:` and occur before any filesystem mutation.

Implement `resolveSkill(input)` by matching `name` or `aliases`. For normal records copy `source` to `install_dir`. For `create-master`, create the destination and copy each `bundle_paths` entry while preserving directory structure. Clear the destination before every reinstall.

Make `cmdInstallAll()` pass all 19 catalog names to `cmdInstall()`. `cmdUninstall()` resolves public names and aliases to catalog install directories.

Make `listData()` return:

```js
{
  count: legacyMasters.length,
  skillCount: skills.length,
  categoryCounts: { persona: 15, "teaching-mode": 3, generator: 1 },
  skills: skills.map(({ name, kind, install_dir, description }) => ({
    name, kind, installDir: install_dir, description,
  })),
  masters: legacyMasters,
}
```

Derive descriptions from each source `SKILL.md`. Preserve the current legacy `masters` items and fields so the Rust desktop parser does not break.

- [ ] **Step 4: Run CLI tests and verify GREEN**

Run: `node --test tests/cli.test.mjs`  
Expected: all CLI tests pass.

- [ ] **Step 5: Commit**

```bash
git add bin/cli.mjs tests/cli.test.mjs
git commit -m "fix(cli): install every advertised skill"
```

### Task 3: Verify the packed artifact and document the contract

**Files:**
- Modify: `package.json`
- Modify: `tests/cli.test.mjs`
- Modify: `README.md`
- Modify: `README_EN.md`

**Interfaces:**
- Produces: a tarball that carries the catalog and complete generator runtime.

- [ ] **Step 1: Write the failing packed-tarball integration test**

Use `execFileSync("npm", ["pack", "--silent"], { cwd: REPO })`, extract the returned tarball with `tar -xzf`, run `package/bin/cli.mjs install --all` under an isolated home, and assert the same 19 directories and generator runtime paths as Task 2. Register cleanup with `t.after()` for both the temporary extraction directory and generated tarball.

- [ ] **Step 2: Run the packed test and verify RED**

Run: `node --test --test-name-pattern="packed npm artifact" tests/cli.test.mjs`  
Expected: FAIL because the current `files` allowlist omits the catalog, tools, prompts, references, requirements, and masters directory.

- [ ] **Step 3: Complete the npm files allowlist**

Add these entries to `package.json#files`:

```json
"skill-catalog.json",
"tools/",
"prompts/",
"references/",
"requirements.txt",
"masters/"
```

Keep existing exclusions for caches and bytecode.

- [ ] **Step 4: Update installation documentation**

State in both READMEs that `install --all` installs 15 personas, 3 teaching modes, and `create-master`. Document `install --personas` only if it is actually implemented; otherwise do not advertise it. Add direct examples for `install compare-masters` and `install create-master`.

- [ ] **Step 5: Run artifact and regression tests**

Run:

```bash
node --test tests/cli.test.mjs
npm pack --dry-run
npm test
```

Expected: all commands exit 0; the dry-run manifest contains all generator runtime directories.

- [ ] **Step 6: Commit**

```bash
git add package.json tests/cli.test.mjs README.md README_EN.md
git commit -m "fix(package): ship the complete skill runtime"
```
