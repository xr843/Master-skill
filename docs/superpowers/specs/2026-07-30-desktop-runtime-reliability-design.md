# Desktop Runtime Reliability Design

**Date:** 2026-07-30

**Target branch:** `fix/desktop-runtime-reliability`

**Base:** reviewed head of `fix/desktop-evaluation-contract`

**Goal:** Make desktop trace persistence and background command execution safe
under crashes, concurrent launches, worker disconnects, invalid CLI arguments,
and stalled child processes.

## Scope and selected approach

This stacked PR addresses the runtime findings after the evaluation contract is
correct:

- trace saves truncate the destination directly;
- GUI and `--baseline` can overwrite each other's in-memory snapshots;
- persisted files have no schema version;
- a disconnected worker leaves the UI permanently busy;
- child processes have no deadline;
- `--help` and unknown arguments launch the GUI.

Three approaches were considered:

1. **Temporary file plus rename only.** This prevents partial JSON but does not
   prevent a stale process from replacing newer records.
2. **Versioned JSON, a process-lifetime single-writer lease, and a bounded
   synchronous command runner.** This is the selected approach because it
   fixes corruption, lost updates, and hangs without changing the local
   product architecture.
3. **SQLite and Tokio.** This would support concurrent writers and asynchronous
   process management, but it is unjustified for a 200-record store and one
   active background task.

The implementation remains in one Rust crate and retains `std::thread` plus
channels.

## Root-cause evidence

### Atomic replacement alone does not solve lost updates

The GUI and `--baseline` load the same trace file into separate in-memory
stores. Even if each save uses a temporary file and atomic rename, a later save
can replace newer records with a stale snapshot.

The root cause is multiple independent read-modify-write owners. This design
uses a process-lifetime single-writer lease rather than inventing merge
semantics.

### Worker disconnects and child processes are unbounded

The GUI converts every `try_recv` error to `None`. If the worker panics and the
sender disconnects, the receiver remains installed forever and the UI remains
busy. Child commands use `Command::output()` without a deadline, so a stalled
Node, Python, or npm process can produce the same visible symptom.

The root cause is representing `Empty` and `Disconnected` as the same state and
having no bounded command-execution abstraction.

## Versioned trace file

New saves use this envelope:

```json
{
  "schema_version": 1,
  "next_id": 42,
  "records": []
}
```

`capacity` is runtime configuration and is no longer persisted. Loading accepts
the current unversioned object containing `capacity`, `next_id`, and `records`,
then writes v1 on the next successful save. Unknown schema versions fail
loudly. Existing `TraceAction` and record fields remain backward compatible.

## Single-writer lease and atomic save

A `TraceStoreLease` owns:

- the trace path;
- an open sibling lock file;
- an exclusive cross-platform `fs4` lock.

The GUI attempts to acquire the lease before loading writable trace state and
retains it for the application lifetime. If another GUI or `--baseline` owns
the lease, a second GUI opens in visibly read-only mode and disables install,
uninstall, update, validation, and fidelity actions. Browsing remains
available; refresh and inspect may update in-memory display data but do not
create or persist trace records while read-only.

`--baseline` fails immediately with a clear non-zero error when it cannot
acquire the lease.

Every save:

1. serializes the complete v1 payload before touching the destination;
2. creates a temporary file in the destination directory;
3. writes, flushes, and `sync_all`s the temporary file;
4. atomically persists it over the destination;
5. leaves the previous valid file intact if serialization or temporary writing
   fails.

The implementation uses `fs4` version `1.1` with synchronous-only features and
`tempfile` version `3`. It does not implement record merging. If concurrent
writers become a product requirement, that requirement triggers a separate
SQLite or append-journal design.

## Explicit pending-task state

The application replaces `task_rx` and `busy_label` with one `PendingTask`
containing the trace id, label, start time, and receiver.

Polling distinguishes:

- `Empty`: keep waiting;
- `Ok`: apply the existing success or error outcome;
- `Disconnected`: clear busy state, mark the trace failed, persist it, and show
  `Task worker disconnected before reporting a result`.

No disconnected receiver remains installed for a later frame.

Read-only mode rejects trace-producing actions before creating a trace or
spawning a worker. Refresh and inspect use a non-traced read path.

## Bounded command runner

`CliClient` owns a synchronous `CommandRunner`. The production deadline is five
minutes per direct child command; tests inject a shorter duration.

The runner:

- spawns the child with piped stdout and stderr;
- drains both streams concurrently so a full pipe cannot deadlock the child;
- waits with `wait-timeout` version `0.2`;
- kills and reaps the direct child on deadline;
- joins both reader threads;
- preserves exit status, stdout, stderr, duration, and timeout state in the
  error presented to the trace.

Process-tree termination is a non-goal for this PR. The direct-child timeout
still guarantees that the desktop worker returns instead of remaining busy
forever.

## Desktop CLI argument contract

Argument parsing accepts:

- no arguments: launch the GUI;
- `--baseline`: run the headless baseline;
- `--help` or `-h`: print usage and exit zero.

Unknown arguments, extra arguments, or incompatible combinations print usage to
stderr and exit `2`. Help never initializes eframe.

## Tests and acceptance

Tests cover:

- legacy trace files load and save as schema v1;
- unknown schema versions fail;
- saved files round-trip and contain no persisted `capacity`;
- two leases cannot own the same store simultaneously;
- dropping the first lease permits a later acquisition;
- a disconnected task receiver produces a terminal failure state;
- command stdout and stderr are drained and retained;
- a helper child that exceeds an injected deadline is killed and reported as a
  timeout;
- `--help` exits zero without launching a window;
- unknown and extra arguments exit `2`;
- `--baseline` lock contention fails clearly.

The PR must pass Rust formatting, strict Clippy, all Rust tests, `npm test`, the
complete Python test suite, and
`cargo check --locked --all-targets --target x86_64-pc-windows-msvc`.

## Stacking and rollout

PR 1 is opened against `main`. This PR starts from the reviewed PR 1 head and is
opened against the PR 1 branch. After PR 1 merges, this PR is rebased or
retargeted to `main` without mixing unrelated changes.

No paid model evaluation is run by this work.

## Non-goals

- No SQLite, append-only journal, or concurrent record merging.
- No Tokio or other async runtime.
- No process-tree termination.
- No multi-crate workspace or broad mechanical module split.
- No Node/Python runtime bundling or platform executable resolver.
- No CJK font work.
- No eframe, egui, Rust edition, or MSRV migration.
- No new desktop screens beyond minimal read-only and error messaging.
