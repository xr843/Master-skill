# Desktop Runtime Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make desktop trace persistence and background command execution safe under crashes, concurrent launches, worker disconnects, invalid CLI arguments, and stalled child processes.

**Architecture:** Keep the existing single-crate, thread-and-channel architecture, but establish explicit ownership boundaries. A process-lifetime `TraceStoreLease` becomes the only application path that saves a versioned trace snapshot atomically; a synchronous `CommandRunner` bounds every child command; and one `PendingTask` state machine represents all worker terminal states. CLI argument parsing remains separate from eframe initialization so headless modes cannot accidentally launch a window.

**Tech Stack:** Rust 2021, `serde`/`serde_json`, `fs4` 1.1 sync-only locking, `tempfile` 3 atomic replacement, `wait-timeout` 0.2 bounded process waits, standard threads and MPSC channels, eframe/egui.

## Global Constraints

- Stack this branch on the reviewed head of `fix/desktop-evaluation-contract`; open PR 2 against that branch.
- Use `fs4` version `1.1` with `default-features = false, features = ["sync"]`.
- Use `tempfile` version `3`.
- Use `wait-timeout` version `0.2`.
- Retain one Rust crate and the existing `std::thread` plus channel execution model.
- Use a five-minute production deadline for each direct child command.
- Kill and reap the direct child on timeout; process-tree termination is explicitly out of scope.
- Accept the current unversioned trace object as legacy input, save only schema version 1, and reject unknown versions.
- Do not persist runtime `capacity`.
- A contended GUI is visibly read-only; a contended `--baseline` exits non-zero.
- `--help` and `-h` exit zero without initializing eframe; invalid or extra arguments exit `2`.
- Do not run paid model evaluation.

---

### Task 1: Versioned, Atomic Trace Persistence

**Files:**
- Modify: `desktop/Cargo.toml`
- Modify: `desktop/Cargo.lock`
- Modify: `desktop/src/trace.rs:1-20`
- Modify: `desktop/src/trace.rs:1822-1870`
- Test: `desktop/src/trace.rs:4930-end`

**Interfaces:**
- Consumes: existing `TraceRecord`, `TraceStatus`, and `TraceStore` record-management behavior.
- Produces: `TraceStore::load_from_path(path: &Path, capacity: usize) -> anyhow::Result<TraceStore>`, `TraceStore::save_to_path(path: &Path) -> anyhow::Result<()>`, and `TraceStoreLease::{try_acquire, load, save, path}`.

- [ ] **Step 1: Add failing schema and lease tests**

Add these tests to `trace.rs`:

```rust
#[test]
fn loads_legacy_trace_file_and_rewrites_schema_v1() {
    let directory = temp_dir("trace-legacy");
    let path = directory.join("desktop-traces.json");
    fs::create_dir_all(&directory).unwrap();
    fs::write(
        &path,
        r#"{"capacity":99,"next_id":7,"records":[]}"#,
    )
    .unwrap();

    let store = TraceStore::load_from_path(&path, 10).unwrap();
    store.save_to_path(&path).unwrap();
    let value: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();

    assert_eq!(value["schema_version"], 1);
    assert_eq!(value["next_id"], 7);
    assert!(value.get("capacity").is_none());
    assert!(value["records"].is_array());
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn rejects_unknown_trace_schema_version() {
    let directory = temp_dir("trace-version");
    let path = directory.join("desktop-traces.json");
    fs::create_dir_all(&directory).unwrap();
    fs::write(
        &path,
        r#"{"schema_version":2,"next_id":1,"records":[]}"#,
    )
    .unwrap();

    let error = TraceStore::load_from_path(&path, 10).unwrap_err();

    assert!(format!("{error:#}").contains("unsupported trace schema version 2"));
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn versioned_trace_file_round_trips_without_capacity() {
    let directory = temp_dir("trace-v1");
    let path = directory.join("desktop-traces.json");
    let mut store = TraceStore::new(10);
    store.begin("one");

    store.save_to_path(&path).unwrap();
    let restored = TraceStore::load_from_path(&path, 3).unwrap();
    let value: serde_json::Value =
        serde_json::from_str(&fs::read_to_string(&path).unwrap()).unwrap();

    assert_eq!(restored.summary().total, 1);
    assert_eq!(value["schema_version"], 1);
    assert!(value.get("capacity").is_none());
    fs::remove_dir_all(directory).unwrap();
}

#[test]
fn only_one_trace_store_lease_can_hold_a_path() {
    let directory = temp_dir("trace-lease");
    let path = directory.join("desktop-traces.json");
    let first = TraceStoreLease::try_acquire(&path).unwrap().unwrap();

    assert!(TraceStoreLease::try_acquire(&path).unwrap().is_none());
    drop(first);
    assert!(TraceStoreLease::try_acquire(&path).unwrap().is_some());
    fs::remove_dir_all(directory).unwrap();
}
```

Add a `temp_dir` helper beside the existing `temp_path` helper:

```rust
fn temp_dir(label: &str) -> PathBuf {
    let suffix = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir().join(format!("master-skill-desktop-{label}-{suffix}"))
}
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml loads_legacy_trace_file_and_rewrites_schema_v1 -- --nocapture
cargo test --locked --manifest-path desktop/Cargo.toml only_one_trace_store_lease_can_hold_a_path -- --nocapture
```

Expected: compilation fails because `TraceStoreLease` and the v1 persistence contract do not exist; after filtering tests individually, the current serializer also persists `capacity`.

- [ ] **Step 3: Add the persistence dependencies**

Add:

```toml
fs4 = { version = "1.1", default-features = false, features = ["sync"] }
tempfile = "3"
```

Run `cargo check --manifest-path desktop/Cargo.toml` once to update `desktop/Cargo.lock`.

- [ ] **Step 4: Implement schema-aware loading and atomic saving**

Replace direct `TraceStore` serialization with explicit persisted payloads:

```rust
const TRACE_STORE_SCHEMA_VERSION: u64 = 1;

#[derive(Debug, Deserialize)]
struct TraceStoreFileV1 {
    schema_version: u64,
    next_id: u64,
    records: VecDeque<TraceRecord>,
}

#[derive(Debug, Deserialize)]
struct LegacyTraceStoreFile {
    capacity: usize,
    next_id: u64,
    records: VecDeque<TraceRecord>,
}

#[derive(Serialize)]
struct TraceStoreFileV1Ref<'a> {
    schema_version: u64,
    next_id: u64,
    records: &'a VecDeque<TraceRecord>,
}
```

Remove `Serialize` and `Deserialize` from `TraceStore` itself. In `load_from_path`, parse to `serde_json::Value`, inspect `schema_version` before deserializing, reject any non-v1 version, and otherwise parse the legacy object. Build the runtime `TraceStore` with the caller-provided capacity, recompute a safe lower bound for `next_id`, mark running records interrupted, and enforce capacity.

Implement saving as:

```rust
pub fn save_to_path(&self, path: &Path) -> Result<()> {
    let content = serde_json::to_vec_pretty(&TraceStoreFileV1Ref {
        schema_version: TRACE_STORE_SCHEMA_VERSION,
        next_id: self.next_id,
        records: &self.records,
    })?;
    let parent = path
        .parent()
        .filter(|parent| !parent.as_os_str().is_empty())
        .unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent)?;

    let mut temporary = tempfile::NamedTempFile::new_in(parent)?;
    temporary.write_all(&content)?;
    temporary.flush()?;
    temporary.as_file().sync_all()?;
    temporary.persist(path).map_err(|error| error.error)?;
    Ok(())
}
```

Import `std::io::Write`. Serialization must occur before directory creation or destination replacement.

- [ ] **Step 5: Implement the process-lifetime writer lease**

Add:

```rust
#[derive(Debug)]
pub struct TraceStoreLease {
    trace_path: PathBuf,
    _lock_file: fs::File,
}

impl TraceStoreLease {
    pub fn try_acquire(trace_path: &Path) -> Result<Option<Self>> {
        let parent = trace_path
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
            .unwrap_or_else(|| Path::new("."));
        fs::create_dir_all(parent)?;
        let mut lock_name = trace_path.as_os_str().to_os_string();
        lock_name.push(".lock");
        let lock_path = PathBuf::from(lock_name);
        let lock_file = fs::OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .open(&lock_path)?;

        match fs4::FileExt::try_lock(&lock_file) {
            Ok(()) => Ok(Some(Self {
                trace_path: trace_path.to_path_buf(),
                _lock_file: lock_file,
            })),
            Err(fs4::TryLockError::WouldBlock) => Ok(None),
            Err(fs4::TryLockError::Error(error)) => Err(error.into()),
        }
    }

    pub fn path(&self) -> &Path {
        &self.trace_path
    }

    pub fn load(&self, capacity: usize) -> Result<TraceStore> {
        TraceStore::load_from_path(&self.trace_path, capacity)
    }

    pub fn save(&self, store: &TraceStore) -> Result<()> {
        store.save_to_path(&self.trace_path)
    }
}
```

The open file handle holds the advisory lock until `TraceStoreLease` is dropped.

- [ ] **Step 6: Run focused and complete trace tests**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml trace::tests -- --nocapture
```

Expected: all trace tests pass, including legacy migration, v1 round-trip, unknown-version rejection, contention, and reacquisition after drop.

- [ ] **Step 7: Commit**

```bash
git add desktop/Cargo.toml desktop/Cargo.lock desktop/src/trace.rs
git commit -m "fix(desktop): make trace persistence atomic"
```

---

### Task 2: Exclusive Baseline Writer

**Files:**
- Modify: `desktop/src/baseline.rs:20-115`
- Modify: `desktop/tests/baseline_cli.rs`

**Interfaces:**
- Consumes: `TraceStoreLease::try_acquire`, `TraceStoreLease::load`, and `TraceStoreLease::save` from Task 1.
- Produces: `run_headless_baseline() -> anyhow::Result<i32>` that refuses to run while another process owns the store.

- [ ] **Step 1: Write the lock-contention integration test**

Add:

```rust
#[test]
fn baseline_lock_contention_fails_clearly() {
    let xdg_data_home = temp_xdg_data_home();
    let store_path = xdg_data_home
        .join("master-skill")
        .join("desktop-traces.json");
    let _lease = TraceStoreLease::try_acquire(&store_path)
        .unwrap()
        .expect("test must acquire the first lease");
    let mut command = Command::new(env!("CARGO_BIN_EXE_master-skill-desktop"));
    command
        .arg("--baseline")
        .current_dir(repo_root())
        .env("XDG_DATA_HOME", &xdg_data_home);

    let output = run_with_timeout(command, Duration::from_secs(10));
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert_eq!(output.status.code(), Some(1));
    assert!(stderr.contains("trace store"));
    assert!(stderr.contains("another"));
    fs::remove_dir_all(xdg_data_home).ok();
}
```

Import `TraceStoreLease` with `TraceStore`.

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml --test baseline_cli baseline_lock_contention_fails_clearly -- --nocapture
```

Expected: FAIL because the child baseline currently loads, runs, and saves despite the held lease.

- [ ] **Step 3: Acquire and retain the lease in the baseline**

Before loading the store:

```rust
let store_path = desktop_trace_store_path();
let lease = TraceStoreLease::try_acquire(&store_path)?.ok_or_else(|| {
    anyhow!(
        "trace store {:?} is locked by another desktop or baseline process",
        store_path
    )
})?;
let mut traces = lease.load(TRACE_STORE_CAPACITY)?;
```

Replace the final `traces.save_to_path(&store_path)?` with `lease.save(&traces)?`. Keep `lease` in scope for the complete run.

- [ ] **Step 4: Run all baseline integration tests**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml --test baseline_cli -- --nocapture
```

Expected: all baseline tests pass; the normal baseline still writes v1 and the contended run exits quickly with status `1`.

- [ ] **Step 5: Commit**

```bash
git add desktop/src/baseline.rs desktop/tests/baseline_cli.rs
git commit -m "fix(desktop): serialize baseline trace writers"
```

---

### Task 3: Bounded Command Runner

**Files:**
- Modify: `desktop/Cargo.toml`
- Modify: `desktop/Cargo.lock`
- Create: `desktop/src/command.rs`
- Modify: `desktop/src/lib.rs`
- Modify: `desktop/src/cli.rs:1-130`
- Test: `desktop/src/command.rs`

**Interfaces:**
- Consumes: `std::process::Command`.
- Produces: `CommandRunner::new(timeout: Duration)`, `CommandRunner::run(command: &mut Command) -> anyhow::Result<CommandOutput>`, and a clonable five-minute default runner used by `CliClient`.

- [ ] **Step 1: Add the dependency and failing runner tests**

Add `wait-timeout = "0.2"` to `desktop/Cargo.toml`, declare `pub mod command;` in `desktop/src/lib.rs`, and create `desktop/src/command.rs` with tests first:

```rust
#[cfg(test)]
mod tests {
    use super::CommandRunner;
    use std::io::{self, Write};
    use std::process::Command;
    use std::time::{Duration, Instant};

    const HELPER_MODE: &str = "MASTER_SKILL_COMMAND_RUNNER_HELPER";

    #[test]
    fn command_runner_helper() {
        let Ok(mode) = std::env::var(HELPER_MODE) else {
            return;
        };
        if mode == "output" {
            let stdout = vec![b'o'; 128 * 1024];
            let stderr = vec![b'e'; 128 * 1024];
            io::stdout().write_all(&stdout).unwrap();
            io::stderr().write_all(&stderr).unwrap();
        } else if mode == "sleep" {
            std::thread::sleep(Duration::from_secs(5));
        }
    }

    fn helper_command(mode: &str) -> Command {
        let mut command = Command::new(std::env::current_exe().unwrap());
        command
            .args([
                "--exact",
                "command::tests::command_runner_helper",
                "--nocapture",
            ])
            .env(HELPER_MODE, mode);
        command
    }

    #[test]
    fn drains_and_retains_stdout_and_stderr() {
        let output = CommandRunner::new(Duration::from_secs(5))
            .run(&mut helper_command("output"))
            .unwrap();

        assert!(output.status.success());
        assert!(!output.timed_out);
        assert!(output.stdout.matches('o').count() >= 128 * 1024);
        assert!(output.stderr.matches('e').count() >= 128 * 1024);
    }

    #[test]
    fn kills_and_reaps_a_child_after_the_deadline() {
        let started = Instant::now();
        let output = CommandRunner::new(Duration::from_millis(100))
            .run(&mut helper_command("sleep"))
            .unwrap();

        assert!(output.timed_out);
        assert!(!output.status.success());
        assert!(started.elapsed() < Duration::from_secs(2));
    }
}
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml command::tests -- --nocapture
```

Expected: compilation fails because `CommandRunner` does not exist.

- [ ] **Step 3: Implement concurrent pipe draining and bounded waiting**

Implement:

```rust
use std::io::{self, Read};
use std::process::{Command, ExitStatus, Stdio};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use anyhow::{anyhow, Context, Result};
use wait_timeout::ChildExt;

pub const DEFAULT_COMMAND_TIMEOUT: Duration = Duration::from_secs(5 * 60);

#[derive(Clone, Debug)]
pub struct CommandRunner {
    timeout: Duration,
}

#[derive(Debug)]
pub struct CommandOutput {
    pub status: ExitStatus,
    pub stdout: String,
    pub stderr: String,
    pub elapsed: Duration,
    pub timed_out: bool,
}

impl CommandRunner {
    pub fn new(timeout: Duration) -> Self {
        Self { timeout }
    }

    pub fn run(&self, command: &mut Command) -> Result<CommandOutput> {
        command.stdout(Stdio::piped()).stderr(Stdio::piped());
        let started = Instant::now();
        let mut child = command.spawn().context("failed to spawn child command")?;
        let stdout = child.stdout.take().context("child stdout was not piped")?;
        let stderr = child.stderr.take().context("child stderr was not piped")?;
        let stdout_reader = spawn_reader(stdout);
        let stderr_reader = spawn_reader(stderr);

        let wait_result = child.wait_timeout(self.timeout);
        let (status, timed_out) = match wait_result {
            Ok(Some(status)) => (status, false),
            Ok(None) => {
                let _ = child.kill();
                (
                    child.wait().context("failed to reap timed-out child")?,
                    true,
                )
            }
            Err(error) => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = join_reader(stdout_reader, "stdout");
                let _ = join_reader(stderr_reader, "stderr");
                return Err(error).context("failed while waiting for child command");
            }
        };
        let stdout = join_reader(stdout_reader, "stdout")?;
        let stderr = join_reader(stderr_reader, "stderr")?;

        Ok(CommandOutput {
            status,
            stdout: String::from_utf8_lossy(&stdout).into_owned(),
            stderr: String::from_utf8_lossy(&stderr).into_owned(),
            elapsed: started.elapsed(),
            timed_out,
        })
    }
}

impl Default for CommandRunner {
    fn default() -> Self {
        Self::new(DEFAULT_COMMAND_TIMEOUT)
    }
}

fn spawn_reader<R>(mut reader: R) -> JoinHandle<io::Result<Vec<u8>>>
where
    R: Read + Send + 'static,
{
    thread::spawn(move || {
        let mut bytes = Vec::new();
        reader.read_to_end(&mut bytes)?;
        Ok(bytes)
    })
}

fn join_reader(
    reader: JoinHandle<io::Result<Vec<u8>>>,
    stream: &str,
) -> Result<Vec<u8>> {
    reader
        .join()
        .map_err(|_| anyhow!("{stream} reader thread panicked"))?
        .with_context(|| format!("failed to read child {stream}"))
}
```

- [ ] **Step 4: Route every `CliClient` child through the runner**

Add `runner: CommandRunner` to `CliClient`, initialize it with `CommandRunner::default()`, and add:

```rust
pub fn with_command_timeout(mut self, timeout: Duration) -> Self {
    self.runner = CommandRunner::new(timeout);
    self
}
```

Replace `Command::output()` in `run_command`:

```rust
let output = self
    .runner
    .run(command)
    .with_context(|| context.to_string())?;
if !output.timed_out && output.status.success() {
    return Ok(output.stdout);
}

let reason = if output.timed_out {
    format!("command timed out after {} ms", output.elapsed.as_millis())
} else {
    format!(
        "command failed after {} ms with status {}",
        output.elapsed.as_millis(),
        output.status
    )
};
Err(anyhow!(
    "{context}: {reason}\nstdout:\n{}\nstderr:\n{}",
    output.stdout,
    output.stderr
))
```

This formatted error is what the existing task layer stores in trace detail.

- [ ] **Step 5: Run command and CLI tests**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml command::tests -- --nocapture
cargo test --manifest-path desktop/Cargo.toml cli:: -- --nocapture
cargo test --manifest-path desktop/Cargo.toml --test cli_client -- --nocapture
```

Expected: the large-output helper cannot deadlock, the sleeping helper returns in under two seconds with `timed_out = true`, and all real CLI integration tests pass.

- [ ] **Step 6: Commit**

```bash
git add desktop/Cargo.toml desktop/Cargo.lock desktop/src/lib.rs desktop/src/command.rs desktop/src/cli.rs
git commit -m "fix(desktop): bound child command execution"
```

---

### Task 4: Explicit Pending State and Read-Only GUI

**Files:**
- Modify: `desktop/src/app.rs:1-780`
- Modify: `desktop/src/app.rs:930-2290`
- Test: `desktop/src/app.rs:2480-end`

**Interfaces:**
- Consumes: `TraceStoreLease` from Task 1 and bounded `CliClient` from Task 3.
- Produces: one `PendingTask` slot that distinguishes `Empty`, completion, and disconnection; a retained optional writer lease; and centralized read-only action enforcement.

- [ ] **Step 1: Write failing pending-state and action-policy tests**

Add:

```rust
#[test]
fn disconnected_pending_task_is_removed_and_marks_trace_failed() {
    let mut traces = TraceStore::new(10);
    let trace_id = traces.begin_with_action(
        "Running full validation",
        TraceAction::FullValidation,
        Some("npm test"),
        "Queued.",
    );
    let (sender, receiver) = channel::<TaskResult>();
    drop(sender);
    let mut pending = Some(PendingTask {
        trace_id: Some(trace_id),
        label: "Running full validation".to_string(),
        started: Instant::now(),
        receiver,
    });

    let event = poll_pending_task(&mut pending);
    let PendingTaskEvent::Disconnected {
        trace_id,
        elapsed,
    } = event
    else {
        panic!("expected disconnected event");
    };
    let message = finish_disconnected_trace(&mut traces, trace_id, elapsed);

    assert!(pending.is_none());
    assert_eq!(traces.recent()[0].status, TraceStatus::Failed);
    assert_eq!(
        message,
        "Task worker disconnected before reporting a result"
    );
}

#[test]
fn read_only_policy_allows_browsing_but_rejects_trace_writes() {
    assert!(!trace_action_requires_writer(&TraceAction::Refresh));
    assert!(!trace_action_requires_writer(&TraceAction::InspectSkill {
        slug: "huineng".to_string(),
    }));
    assert!(trace_action_requires_writer(&TraceAction::InstallAll));
    assert!(trace_action_requires_writer(&TraceAction::FullValidation));
    assert!(trace_action_requires_writer(
        &TraceAction::FidelityDryRunAll
    ));
}
```

Import `channel` and `Instant` in the test module.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml disconnected_pending_task_is_removed_and_marks_trace_failed -- --nocapture
cargo test --manifest-path desktop/Cargo.toml read_only_policy_allows_browsing_but_rejects_trace_writes -- --nocapture
```

Expected: compilation fails because the pending-task state machine and read-only policy do not exist.

- [ ] **Step 3: Replace the split receiver/label fields with `PendingTask`**

Define:

```rust
struct PendingTask {
    trace_id: Option<u64>,
    label: String,
    started: Instant,
    receiver: Receiver<TaskResult>,
}

enum PendingTaskEvent {
    Pending,
    Completed {
        trace_id: Option<u64>,
        elapsed: Duration,
        result: TaskResult,
    },
    Disconnected {
        trace_id: Option<u64>,
        elapsed: Duration,
    },
}
```

Replace `task_rx` and `busy_label` with `pending_task: Option<PendingTask>`. Implement `poll_pending_task` with an exact `TryRecvError` match: `Empty` retains the slot, while both completion and `Disconnected` take the slot. Make workers send only `TaskResult`; compute elapsed from `PendingTask::started`.

Implement:

```rust
const WORKER_DISCONNECTED_MESSAGE: &str =
    "Task worker disconnected before reporting a result";

fn finish_disconnected_trace(
    traces: &mut TraceStore,
    trace_id: Option<u64>,
    elapsed: Duration,
) -> String {
    if let Some(trace_id) = trace_id {
        traces.finish_error_with_detail(
            trace_id,
            WORKER_DISCONNECTED_MESSAGE,
            WORKER_DISCONNECTED_MESSAGE,
            elapsed,
        );
    }
    WORKER_DISCONNECTED_MESSAGE.to_string()
}
```

Update `MasterSkillApp::poll_task` to apply success/error outcomes as before, persist traced terminal results, and use this helper for disconnection.

- [ ] **Step 4: Acquire the GUI lease and represent read-only mode**

Replace `trace_path` with:

```rust
trace_lease: Option<TraceStoreLease>,
read_only_reason: Option<String>,
```

In `MasterSkillApp::new`, call `TraceStoreLease::try_acquire(&trace_path)` before loading. Retain `Some(lease)` for the application lifetime. For `Ok(None)`, load the store for browsing and set:

```rust
Some(format!(
    "Trace store is in use by another process; this window is read-only: {}",
    trace_path.display()
))
```

For lock I/O errors, also open read-only and include the error in the reason. Change `persist_traces` to save only through `self.trace_lease.as_ref().map(|lease| lease.save(&self.traces))`.

- [ ] **Step 5: Enforce read-only behavior centrally**

Add:

```rust
fn trace_action_requires_writer(action: &TraceAction) -> bool {
    !matches!(action, TraceAction::Refresh | TraceAction::InspectSkill { .. })
}

fn is_read_only(&self) -> bool {
    self.trace_lease.is_none()
}

fn can_mutate(&self) -> bool {
    !self.is_busy() && !self.is_read_only()
}
```

At the start of `start_task_with_action`, if the app is read-only and its action requires a writer, log the read-only reason and return before creating a trace or spawning a worker. For `Refresh` and `InspectSkill` in read-only mode, create `PendingTask { trace_id: None, ... }`; do not mutate or persist the trace store.

- [ ] **Step 6: Make read-only mode visible and disable writer controls**

Show the read-only reason in the toolbar. Keep Refresh and Open/Inspect enabled while idle. Gate Install, Uninstall, Install all, Update all, fidelity runs, full validation, rerun actions, and Clear traces on `can_mutate()` or an action-specific helper:

```rust
fn can_start_trace_action(&self, action: &TraceAction) -> bool {
    !self.is_busy()
        && (!self.is_read_only() || !trace_action_requires_writer(action))
}
```

Retain centralized enforcement even where UI controls are disabled.

- [ ] **Step 7: Run app and full Rust tests**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml app::tests -- --nocapture
cargo test --manifest-path desktop/Cargo.toml
```

Expected: the disconnected receiver is removed in one poll and its traced operation ends `Failed`; browsing policy tests pass; all existing UI and evaluation tests remain green.

- [ ] **Step 8: Commit**

```bash
git add desktop/src/app.rs
git commit -m "fix(desktop): make task termination explicit"
```

---

### Task 5: Explicit Desktop CLI Argument Contract

**Files:**
- Create: `desktop/src/desktop_args.rs`
- Modify: `desktop/src/lib.rs`
- Modify: `desktop/src/main.rs`
- Create: `desktop/tests/desktop_args_cli.rs`

**Interfaces:**
- Consumes: `run_headless_baseline()` and the existing eframe startup closure.
- Produces: `parse_launch_mode(args: impl IntoIterator<Item = OsString>) -> Result<LaunchMode, LaunchArgsError>`, `DESKTOP_USAGE`, and binary exit behavior `0` for help, `2` for invalid arguments.

- [ ] **Step 1: Write failing binary integration tests**

Create:

```rust
use std::process::Command;

fn desktop() -> Command {
    Command::new(env!("CARGO_BIN_EXE_master-skill-desktop"))
}

#[test]
fn help_exits_zero_without_launching_a_window() {
    for flag in ["--help", "-h"] {
        let output = desktop().arg(flag).output().unwrap();
        assert!(output.status.success(), "{flag} failed: {output:?}");
        assert!(String::from_utf8_lossy(&output.stdout).contains("Usage:"));
    }
}

#[test]
fn unknown_argument_exits_two_and_prints_usage_to_stderr() {
    let output = desktop().arg("--unknown").output().unwrap();
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert_eq!(output.status.code(), Some(2));
    assert!(stderr.contains("invalid arguments"));
    assert!(stderr.contains("Usage:"));
}

#[test]
fn extra_or_incompatible_arguments_exit_two() {
    for args in [
        vec!["--baseline", "extra"],
        vec!["--baseline", "--help"],
        vec!["--help", "extra"],
    ] {
        let output = desktop().args(&args).output().unwrap();
        assert_eq!(output.status.code(), Some(2), "args {args:?}: {output:?}");
    }
}
```

- [ ] **Step 2: Run the integration tests and verify RED**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml --test desktop_args_cli -- --nocapture
```

Expected: `--help` and unknown arguments fall into GUI initialization or are incorrectly accepted.

- [ ] **Step 3: Implement the pure parser**

Create `desktop_args.rs`:

```rust
use std::ffi::OsString;
use std::fmt;

pub const DESKTOP_USAGE: &str =
    "Usage: master-skill-desktop [--baseline | --help]\n\n\
     Options:\n  --baseline  Run the headless fidelity dry-run baseline\n  \
     -h, --help  Print this help";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LaunchMode {
    Gui,
    Baseline,
    Help,
}

#[derive(Debug)]
pub struct LaunchArgsError {
    args: Vec<OsString>,
}

impl fmt::Display for LaunchArgsError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid arguments: {:?}", self.args)
    }
}

impl std::error::Error for LaunchArgsError {}

pub fn parse_launch_mode(
    args: impl IntoIterator<Item = OsString>,
) -> Result<LaunchMode, LaunchArgsError> {
    let args: Vec<OsString> = args.into_iter().collect();
    match args.as_slice() {
        [] => Ok(LaunchMode::Gui),
        [argument] if argument == "--baseline" => Ok(LaunchMode::Baseline),
        [argument] if argument == "--help" || argument == "-h" => Ok(LaunchMode::Help),
        _ => Err(LaunchArgsError { args }),
    }
}
```

Declare `pub mod desktop_args;` in `lib.rs`.

- [ ] **Step 4: Parse before any eframe initialization**

In `main`, match `parse_launch_mode(std::env::args_os().skip(1))`:

```rust
match parse_launch_mode(std::env::args_os().skip(1)) {
    Ok(LaunchMode::Gui) => run_gui(),
    Ok(LaunchMode::Baseline) => {
        let exit_code = match run_headless_baseline() {
            Ok(code) => code,
            Err(error) => {
                eprintln!("baseline failed: {error:#}");
                1
            }
        };
        std::process::exit(exit_code);
    }
    Ok(LaunchMode::Help) => {
        println!("{DESKTOP_USAGE}");
        Ok(())
    }
    Err(error) => {
        eprintln!("{error}\n\n{DESKTOP_USAGE}");
        std::process::exit(2);
    }
}
```

Move the current eframe setup into `fn run_gui() -> eframe::Result`.

- [ ] **Step 5: Run CLI and baseline tests**

Run:

```bash
cargo test --manifest-path desktop/Cargo.toml --test desktop_args_cli -- --nocapture
cargo test --manifest-path desktop/Cargo.toml --test baseline_cli -- --nocapture
```

Expected: help exits `0`, every invalid combination exits `2`, normal baseline behavior and lock contention remain correct.

- [ ] **Step 6: Commit**

```bash
git add desktop/src/desktop_args.rs desktop/src/lib.rs desktop/src/main.rs desktop/tests/desktop_args_cli.rs
git commit -m "fix(desktop): reject invalid launch arguments"
```

---

### Task 6: Self-Review and Cross-Platform Verification

**Files:**
- Modify only files implicated by review findings.

**Interfaces:**
- Consumes: all Tasks 1-5.
- Produces: a clean, reviewed stacked PR with recorded verification evidence.

- [ ] **Step 1: Review the complete stacked diff**

Run:

```bash
git diff --check fix/desktop-evaluation-contract...HEAD
git diff --stat fix/desktop-evaluation-contract...HEAD
git diff fix/desktop-evaluation-contract...HEAD -- desktop/Cargo.toml desktop/src desktop/tests
```

Inspect specifically for:

- any application save that bypasses `TraceStoreLease`;
- any write action still enabled or executable in read-only mode;
- any `try_recv().ok()` that collapses `Disconnected` into `Empty`;
- any direct `Command::output`, `Command::status`, or unbounded `wait`;
- any CLI argument path that can reach eframe for non-empty invalid input;
- any timeout path that fails to kill, reap, or join both output readers;
- any persisted `capacity` field or version fallback that accepts an unknown version.

- [ ] **Step 2: Run format and strict lint**

Run:

```bash
cargo fmt --manifest-path desktop/Cargo.toml -- --check
cargo clippy --locked --manifest-path desktop/Cargo.toml --all-targets -- -D warnings
```

Expected: both exit zero with no warnings.

- [ ] **Step 3: Run all repository test suites**

Run:

```bash
cargo test --locked --manifest-path desktop/Cargo.toml
cargo build --locked --manifest-path desktop/Cargo.toml
npm test
python3 -m pytest tests/ scripts/tests/ -q
```

Expected: every Rust, Node, validator, and Python test passes.

- [ ] **Step 4: Check the Windows target**

Run:

```bash
rustup target add x86_64-pc-windows-msvc
cargo check --locked --manifest-path desktop/Cargo.toml --all-targets --target x86_64-pc-windows-msvc
```

Expected: cross-target checking exits zero, proving the fs4 lock, tempfile replacement, command wait, argument parser, and tests compile for Windows.

- [ ] **Step 5: Commit any review corrections**

If review produced changes, stage only the implicated files and commit:

```bash
git add desktop/Cargo.toml desktop/Cargo.lock desktop/src desktop/tests
git commit -m "fix(desktop): harden runtime reliability edges"
```

If the tree is already clean, do not create an empty commit.

- [ ] **Step 6: Push and open the stacked draft PR**

Push `fix/desktop-runtime-reliability` and open a draft PR against `fix/desktop-evaluation-contract`. The body must summarize the lease/atomic-persistence contract, bounded command execution, disconnected-worker terminal state, read-only GUI behavior, CLI parsing, exact test results, and the Windows target check.
