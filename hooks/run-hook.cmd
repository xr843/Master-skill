: ; # Polyglot wrapper — runs as cmd.exe on Windows, bash on Unix
: ; exec bash "$0" "$@" 2>/dev/null
: ; exit
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
        exit /b %ERRORLEVEL%
    )
)

:: Fallback: try bash from PATH
where bash >nul 2>&1 && (
    bash "%HOOK_DIR%%HOOK%" %2 %3 %4 %5
    exit /b %ERRORLEVEL%
)

:: No bash found — exit silently
exit /b 0
