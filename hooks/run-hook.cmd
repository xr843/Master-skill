: ; # Polyglot wrapper — runs as cmd.exe on Windows, bash on Unix. Dispatches $1
: ; # by name. This line once read `exec bash "$0" "$@"`, which re-exec'd this
: ; # same file forever; hooks.json runs the wrapper with "async": false, so every
: ; # session start spun until the harness hook timeout while 2>/dev/null hid the
: ; # cause. Keep this half POSIX — the file has no shebang, so /bin/sh interprets
: ; # it, and that is dash on Debian/Ubuntu where ${@:2} is a "Bad substitution".
: ; # It is ONE line, ending in a comment, because the file ships with CRLF: cmd.exe
: ; # mis-parses the LF original (measured — it echoed a comment as a command and
: ; # emitted no JSON), and under bash a CR would otherwise end up inside a command
: ; # word. Everything after the `#` — including that CR — is a comment.
: ; HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"; HOOK="${1:-}"; [ "$#" -gt 0 ] && shift; exec bash "$HOOK_DIR/$HOOK" "$@" #
: ; exit 1 #
@echo off
setlocal

:: No `enabledelayedexpansion`. With it on, cmd.exe strips every `!` from a
:: %VAR% value as it expands, so a plugin under a path like C:\Users\bang!x
:: dispatched to ...\bangx\hooks\session-start and failed with "No such file or
:: directory" (measured on Windows 11). Delayed expansion was only there for
:: !ERRORLEVEL! inside the old for/if blocks, where %ERRORLEVEL% freezes at
:: parse time. So nothing below runs bash inside a parenthesized block: the
:: interpreter is picked first, then run on its own line, where %ERRORLEVEL% on
:: the next line is read after it exits. Quoted %VAR% expansion is single-pass,
:: so `&`, `^`, `%`, spaces and parentheses in the path stay literal too.

set "HOOK=%~1"
set "HOOK_DIR=%~dp0"
set "BASH_EXE="

:: Common Git for Windows bash locations, first match wins, then bash on PATH.
if exist "C:\Program Files\Git\bin\bash.exe" set "BASH_EXE=C:\Program Files\Git\bin\bash.exe"
if not defined BASH_EXE if exist "C:\Program Files (x86)\Git\bin\bash.exe" set "BASH_EXE=C:\Program Files (x86)\Git\bin\bash.exe"
if not defined BASH_EXE if exist "%LOCALAPPDATA%\Programs\Git\bin\bash.exe" set "BASH_EXE=%LOCALAPPDATA%\Programs\Git\bin\bash.exe"
if not defined BASH_EXE where bash >nul 2>&1 && set "BASH_EXE=bash"

:: No bash found — exit silently
if not defined BASH_EXE exit /b 0

"%BASH_EXE%" "%HOOK_DIR%%HOOK%" %2 %3 %4 %5
exit /b %ERRORLEVEL%
