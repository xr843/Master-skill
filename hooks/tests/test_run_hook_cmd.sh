#!/usr/bin/env bash
# Tests the cmd.exe half of hooks/run-hook.cmd — that a failing hook's
# exit code reaches the caller instead of being reported as success.
#
# Runs wherever cmd.exe is reachable: Git bash on windows-latest (which is
# what CI uses) and WSL. Skips elsewhere, so the Linux jobs stay quiet.
#
# The wrapper is staged with CRLF endings, which is what a Windows checkout
# actually holds: the repo has no .gitattributes and git defaults to
# autocrlf=true there. cmd.exe mis-parses the LF original badly enough that
# testing it as-committed would measure the staging, not the wrapper.
#
# Exit non-zero on any failed assertion.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/../run-hook.cmd"

PASS=0
FAIL=0

# Resolve cmd.exe plus a temp directory it can actually cd into. A WSL path
# is UNC to cmd.exe, which refuses it and silently runs from C:\Windows.
if command -v cygpath >/dev/null 2>&1; then
    CMD_EXE="$(command -v cmd.exe || echo /c/Windows/System32/cmd.exe)"
    TMP_DIR="$(mktemp -d)"
    WIN_TMP="$(cygpath -w "$TMP_DIR")"
elif [ -x /mnt/c/Windows/System32/cmd.exe ] && command -v wslpath >/dev/null 2>&1; then
    CMD_EXE=/mnt/c/Windows/System32/cmd.exe
    WIN_BASE="$("$CMD_EXE" /c "echo %TEMP%" 2>/dev/null | tr -d '\r\n')"
    WIN_TMP="${WIN_BASE}\\run-hook-test.$$"
    TMP_DIR="$(wslpath -u "$WIN_BASE")/run-hook-test.$$"
    mkdir -p "$TMP_DIR"
else
    echo "  SKIP  cmd.exe unavailable — Windows dispatch not exercised here"
    exit 0
fi

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

mkdir -p "$TMP_DIR/hooks"
# Strip any CR before adding one: a Windows checkout already holds CRLF, and
# appending blindly yields CR CR LF. cmd.exe then reads the argument to
# `setlocal enabledelayedexpansion` with a trailing CR, rejects it, leaves
# delayed expansion off, and !ERRORLEVEL! stays literal — which looks exactly
# like the bug this file tests.
sed 's/\r*$/\r/' "$WRAPPER" > "$TMP_DIR/hooks/run-hook.cmd"

# Stage two hooks: one that fails with a distinctive code, one that succeeds.
printf '#!/usr/bin/env bash\necho "failing hook ran"\nexit 42\n' \
    > "$TMP_DIR/hooks/failing-hook"
printf '#!/usr/bin/env bash\necho "ok hook ran"\nexit 0\n' \
    > "$TMP_DIR/hooks/ok-hook"
chmod +x "$TMP_DIR/hooks/failing-hook" "$TMP_DIR/hooks/ok-hook"

run_via_cmd() {
    "$CMD_EXE" /c "cd /d $WIN_TMP && hooks\\run-hook.cmd $1" >/dev/null 2>&1
}

# --- Case 1: a failing hook must not be reported as success -------------
run_via_cmd failing-hook
rc=$?
if [ "$rc" -eq 42 ]; then
    echo "  PASS  failing hook: exit code 42 propagated"
    PASS=$((PASS + 1))
elif [ "$rc" -eq 0 ]; then
    echo "  FAIL  failing hook reported success (exit 0) — hook exit code lost"
    FAIL=$((FAIL + 1))
else
    printf "  FAIL  failing hook: expected exit 42, got %s\n" "$rc"
    FAIL=$((FAIL + 1))
fi

# --- Case 2: a succeeding hook still reports success --------------------
run_via_cmd ok-hook
rc=$?
if [ "$rc" -eq 0 ]; then
    echo "  PASS  succeeding hook: exit 0 preserved"
    PASS=$((PASS + 1))
else
    printf "  FAIL  succeeding hook: expected exit 0, got %s\n" "$rc"
    FAIL=$((FAIL + 1))
fi

echo
printf "Summary: %d passed, %d failed\n" "$PASS" "$FAIL"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
