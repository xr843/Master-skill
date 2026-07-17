: ; # Polyglot wrapper — runs as cmd.exe on Windows, bash on Unix.
: ; # Dispatch $1 by name. This line once read `exec bash "$0" "$@"`,
: ; # which re-exec'd this same file forever; hooks.json runs the wrapper
: ; # with "async": false, so every session start spun until the harness
: ; # hook timeout while 2>/dev/null hid the cause. Keep this half POSIX —
: ; # the file has no shebang, so /bin/sh interprets it, and that is dash
: ; # on Debian/Ubuntu where ${@:2} is a "Bad substitution" error.
: ; HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
: ; HOOK="${1:-}"
: ; [ "$#" -gt 0 ] && shift
: ; exec bash "$HOOK_DIR/$HOOK" "$@"
: ; exit 1
@echo off
setlocal enabledelayedexpansion

set "HOOK=%~1"
set "HOOK_DIR=%~dp0"

:: Try common Git for Windows bash locations
for %%B in (
    "C:\Program Files\Git\bin\bash.exe"
    "C:\Program Files (x86)\Git\bin\bash.exe"
    "%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
) do (
    if exist %%B (
        %%B "%HOOK_DIR%%HOOK%" %2 %3 %4 %5
        rem !...!, not %...%: cmd.exe expands %ERRORLEVEL% while parsing the
        rem whole parenthesized block, so it would freeze to the value from
        rem before the loop and report every hook failure as success. This is
        rem what `setlocal enabledelayedexpansion` above is for.
        exit /b !ERRORLEVEL!
    )
)

:: Fallback: try bash from PATH
where bash >nul 2>&1 && (
    bash "%HOOK_DIR%%HOOK%" %2 %3 %4 %5
    exit /b !ERRORLEVEL!
)

:: No bash found — exit silently
exit /b 0
