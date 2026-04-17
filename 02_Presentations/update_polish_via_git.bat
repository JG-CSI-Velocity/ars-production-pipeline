@echo off
setlocal

REM ============================================================
REM update_polish_via_git.bat -- pulls the polish feature branch
REM from GitHub using git, then copies 02_Presentations\ to M:\ARS\.
REM
REM Requires git on PATH. Works through corporate proxies that
REM sometimes block GitHub's release-asset download URLs.
REM
REM Safe: only files inside 02_Presentations\ are touched.
REM Your client decks in decks_to_polish\ and outputs in polished\
REM are NOT deleted.
REM ============================================================

set BRANCH=feature/deck-polish
set REPO=https://github.com/JG-CSI-Velocity/ars-production-pipeline.git
set LOCAL=%TEMP%\ars-polish-source
set TARGET=M:\ARS\02_Presentations

echo.
echo Deck Polish -- updater (via git)
echo ---------------------------------
echo Branch: %BRANCH%
echo Target: %TARGET%
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: git not found on PATH.
    echo Install from https://git-scm.com/ or use the download-based update_polish.bat.
    pause
    exit /b 1
)

if not exist "M:\ARS\" (
    echo ERROR: M:\ARS\ does not exist. Is the M: drive mapped?
    pause
    exit /b 1
)

echo [1/3] Fetching %BRANCH% from GitHub...
if exist "%LOCAL%\.git" (
    pushd "%LOCAL%"
    git fetch --depth 1 origin %BRANCH%
    if errorlevel 1 goto git_error
    git checkout %BRANCH%
    if errorlevel 1 goto git_error
    git reset --hard origin/%BRANCH%
    if errorlevel 1 goto git_error
    popd
) else (
    if exist "%LOCAL%" rmdir /s /q "%LOCAL%"
    git clone -b %BRANCH% --depth 1 %REPO% "%LOCAL%"
    if errorlevel 1 goto git_error
)

echo [2/3] Copying 02_Presentations\ into %TARGET%...
REM /E = copy subdirs including empty; no /PURGE so local decks/outputs are preserved
robocopy "%LOCAL%\02_Presentations" "%TARGET%" /E /NFL /NDL /NJH /NJS
REM robocopy returns 0-7 for success, 8+ for real errors
if %errorlevel% GEQ 8 (
    echo ERROR: copy failed (robocopy exit %errorlevel%).
    pause
    exit /b 1
)

echo [3/3] Done.
echo Updated: %TARGET%
echo.
echo Next: drop decks into %TARGET%\decks_to_polish\
echo       then double-click %TARGET%\polish_windows.bat
echo.
pause
exit /b 0

:git_error
echo.
echo ERROR: git operation failed. See messages above.
pause
exit /b 1
