# Preserve installation filesystem nodes

Base: main merge 5620ee1. Work on fix/install-node-preservation, then submit a
reviewable PR; do not publish packages or run paid models.

## Evidence and intended behavior

The installer computes baseline hashes after rejecting only symbolic links.
Replacing a tracked SKILL.md with a FIFO therefore blocks update --all before the
existing local-edit protection can run. A three-second child-process regression
reproduced the hang. Only ordinary files should reach the hash reader; other node
types are local modifications and should block the batch unless forced.

existsSync follows links, hiding dangling installed roots from preflight and
backup. A regression reproduced the missing local-edit warning and inability to
explicitly replace the link. Inspect entries with lstat, protect links without
force, and move the link itself into backup when replacement is authorized.
A simulated staging-rename failure then reproduced the same existence-check bug
in rollback: the old dangling link was left in backup rather than restored.
The rollback checks now use lstat too, without overwriting an existing destination.

Generator updates ignored a dangling masters root, replacing the user's link with
the package seed directory. Its regression failed on readlink after a successful
update. Preserve the link literally after removing the staged seed directory.
A direct Node reproduction showed cpSync still stats dangling root links with
dereference:false, so use readlink/symlink for the root; directory copies keep the
existing recursive non-dereferencing behavior. Cover available roots with external
contents too. External targets must remain unchanged.

## Verification

Run focused integration cases, full npm test, independent read-only review and
the new PR's CI, including Windows. Tests operate exclusively in temporary homes
and skip unavailable symlink creation / POSIX-only pipes on unsupported systems.
Keep links, user files and recovery backups intact when an operation fails.

Independent review identified Windows junction privilege compatibility: absolute
Windows directory targets now use junction creation; relative symlinks preserve
their spelling. Root-link tests create actual junctions on Windows so this path
is covered without requiring directory-symlink privileges.

The review's scoped-out installation-record node was reconsidered because the
same FIFO hang occurs before baseline hashing. A dedicated regression timed out,
then passed after requiring a regular record before reading. A self-check also
reproduced ENOTDIR when forcing a generator install over a regular file: inspect
masters only when the old install resolves to a directory. Concurrent filesystem
changes and existing cleanup-I/O error reporting remain outside this correction.

Final local verification: eight focused cases pass, including seven added
regressions and the existing internal-link case. Full npm test passes all gates,
109 CLI tests and 1408 Python tests (two CI-only integrations skipped locally).
Windows junction behavior will be verified by the PR's Windows CLI job. The
absolute-target requirement is documented in Node's official filesystem API:
https://nodejs.org/api/fs.html#fssymlinktarget-path-type-callback

PR #297's first Windows run passed. Its CodeQL alert identified a check/read
race in the record path check, so file and record reads now share a descriptor:
nonblocking/no-follow open flags where supported, fstat regular-file validation,
readFileSync of the same descriptor, and close in finally. A new regression
replaces the record pathname with a FIFO immediately after open and confirms the
old regular descriptor is still read. Restoring unsafe pathname reads first
reproduced a three-second timeout; descriptor reads pass. Re-run all gates and
CodeQL after this correction before declaring the PR green.

Descriptor follow-up verification: full npm test passes all gates, 110 CLI tests
and 1408 Python tests (two CI-only integrations skipped). Independent read-only
review found no material issue in descriptor closure, FIFO flags or race-test
behavior. Parent-directory replacement and concurrent content edits remain beyond
the targeted pathname-read correction. Eight new CLI regressions are now included.

The second CodeQL run no longer reported the production record read; it caught
the test's final pathname type-check/read assertion. That assertion now opens,
checks and reads its own descriptor too, without suppressing the scan. The second
Windows run passed the descriptor implementation.
