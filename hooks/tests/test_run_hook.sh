#!/usr/bin/env bash
# Tests for hooks/run-hook.cmd — the polyglot cmd.exe/Unix wrapper that
# hooks.json invokes for every SessionStart.
#
# The wrapper has no shebang: on Unix, execve returns ENOEXEC and the
# CALLING shell interprets it. That shell is /bin/sh (dash on Debian and
# Ubuntu), not necessarily bash — so every case below is driven through
# both `bash -c` and `sh -c`, mirroring how a real hook invocation lands.
#
# Regressions these cases pin down:
#
#   1. `exec bash "$0" "$@"` re-execs the wrapper itself, spinning forever.
#      hooks.json runs this with "async": false, so every startup/clear/
#      compact blocked until the harness hook timeout, with 2>/dev/null
#      swallowing any sign of it.
#   2. `${@:2}` is a bashism. Under dash it is a "Bad substitution" error,
#      trading the hang for a silent failure on half the installed base.
#   3. The wrapper must actually dispatch $1; an unknown hook name has to
#      fail loudly rather than hang or report success.
#
# Exit non-zero on any failed assertion.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/../run-hook.cmd"
TIMEOUT_SECS=10

if [ ! -f "$WRAPPER" ]; then
    echo "FAIL: cannot find $WRAPPER" >&2
    exit 1
fi

PASS=0
FAIL=0

# Run the wrapper under $1 (bash|sh) and report "<exit>|<stdout>".
# A timeout surfaces as exit 124, which is what the self-exec loop produces.
run_wrapper() {
    local shell="$1"
    shift
    local out
    local rc
    out=$(timeout "$TIMEOUT_SECS" "$shell" -c "'$WRAPPER' $*" 2>/dev/null)
    rc=$?
    printf '%s|%s' "$rc" "$out"
}

# --- Cases 1-2: the hook runs to completion and emits valid JSON ---------
# Driven under both shells: bash alone would not catch the ${@:2} bashism,
# and sh alone would not catch a bash-only regression.
for shell in bash sh; do
    if ! command -v "$shell" >/dev/null 2>&1; then
        printf "  SKIP  %s not available\n" "$shell"
        continue
    fi

    result=$(run_wrapper "$shell" session-start)
    rc="${result%%|*}"
    out="${result#*|}"

    if [ "$rc" -eq 124 ]; then
        printf "  FAIL  %s: wrapper hung (timed out after %ss — self-exec loop?)\n" \
            "$shell" "$TIMEOUT_SECS"
        FAIL=$((FAIL + 1))
        continue
    fi

    if [ "$rc" -ne 0 ]; then
        printf "  FAIL  %s: wrapper exited %s (expected 0)\n" "$shell" "$rc"
        FAIL=$((FAIL + 1))
        continue
    fi

    if printf '%s' "$out" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; then
        printf "  PASS  %s: session-start dispatched, emitted valid JSON\n" "$shell"
        PASS=$((PASS + 1))
    else
        printf "  FAIL  %s: output is not valid JSON: %.60s\n" "$shell" "$out"
        FAIL=$((FAIL + 1))
    fi
done

# --- Case 3: the dispatched hook is really session-start, not something else
result=$(run_wrapper bash session-start)
out="${result#*|}"
case "$out" in
    *"Master-skill plugin loaded"*)
        echo "  PASS  dispatches the named hook (context payload present)"
        PASS=$((PASS + 1))
        ;;
    *)
        printf "  FAIL  dispatched hook did not produce session-start output: %.60s\n" "$out"
        FAIL=$((FAIL + 1))
        ;;
esac

# --- Case 4: an unknown hook name fails loudly, never hangs --------------
result=$(run_wrapper bash no-such-hook)
rc="${result%%|*}"
if [ "$rc" -eq 124 ]; then
    echo "  FAIL  unknown hook name hung instead of failing"
    FAIL=$((FAIL + 1))
elif [ "$rc" -eq 0 ]; then
    echo "  FAIL  unknown hook name reported success"
    FAIL=$((FAIL + 1))
else
    printf "  PASS  unknown hook name fails loudly (exit %s)\n" "$rc"
    PASS=$((PASS + 1))
fi

echo
# The wrapper ships with CRLF because cmd.exe mis-parses an LF-only batch file
# (measured 2026-09-18 on Windows 11: it echoed a comment as a command and
# emitted no JSON). bash has to run it either way, so the bash half is one line
# ending in a comment — the CR lands inside that comment.
for ending in lf crlf; do
    tmp_eol=$(mktemp -d)
    mkdir -p "$tmp_eol/hooks" "$tmp_eol/prebuilt/master-probe"
    printf -- '---\nname: master-probe\nlineage: 禅宗\n---\n' > "$tmp_eol/prebuilt/master-probe/SKILL.md"
    cp "$SCRIPT_DIR/../session-start" "$SCRIPT_DIR/../session_start.py" "$tmp_eol/hooks/"
    if [ "$ending" = crlf ]; then
        sed 's/\r*$/\r/' "$WRAPPER" > "$tmp_eol/hooks/run-hook.cmd"
    else
        tr -d '\r' < "$WRAPPER" > "$tmp_eol/hooks/run-hook.cmd"
    fi
    out=$(cd "$tmp_eol" && CLAUDE_PLUGIN_ROOT="$tmp_eol" bash hooks/run-hook.cmd session-start 2>/dev/null)
    if printf '%s' "$out" | grep -q "master-probe"; then
        printf "  PASS  bash runs the %s wrapper\n" "$ending"
        PASS=$((PASS + 1))
    else
        printf "  FAIL  bash could not run the %s wrapper: %s\n" "$ending" "$out"
        FAIL=$((FAIL + 1))
    fi
    rm -rf "$tmp_eol"
done

# .gitattributes is what guarantees the CRLF the Windows half needs, on every
# checkout rather than only where core.autocrlf is true.
if [ "$(cd "$SCRIPT_DIR/../.." && git check-attr eol -- hooks/run-hook.cmd 2>/dev/null | sed 's/.*: //')" = "crlf" ]; then
    echo "  PASS  .gitattributes pins the wrapper to CRLF"
    PASS=$((PASS + 1))
else
    echo "  FAIL  .gitattributes no longer pins hooks/run-hook.cmd to CRLF"
    FAIL=$((FAIL + 1))
fi

printf "Summary: %d passed, %d failed\n" "$PASS" "$FAIL"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
