@echo off
setlocal

REM ============================================================
REM update_polish.bat -- fetches the latest deck-polish package
REM from GitHub and extracts it into M:\ARS\
REM
REM Double-click any time. Always grabs the latest published
REM drop-in zip; overwrites the existing 02_Presentations\
REM folder with the new version. Nothing else in M:\ARS\ is
REM touched.
REM ============================================================

REM Pinned tag URL (latest/download/ only works for releases on the default branch;
REM this release is on feature/deck-polish, so we hit the tag URL directly).
set ZIP_URL=https://github.com/JG-CSI-Velocity/ars-production-pipeline/releases/download/deck-polish-v0.1.0-pre/deck-polish-drop-in.zip
set TEMP_ZIP=%TEMP%\deck-polish-drop-in.zip
set TARGET=M:\ARS\

echo.
echo Deck Polish -- updater
echo ----------------------
echo Source: %ZIP_URL%
echo Target: %TARGET%
echo.

echo [1/3] Downloading latest drop-in zip...
powershell -NoProfile -Command "try { Invoke-WebRequest '%ZIP_URL%' -OutFile '%TEMP_ZIP%' -UseBasicParsing } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 (
    echo.
    echo ERROR: Download failed. Check your internet connection.
    pause
    exit /b 1
)

if not exist "%TARGET%" (
    echo.
    echo ERROR: %TARGET% does not exist. Is the M: drive mapped?
    pause
    exit /b 1
)

echo [2/3] Extracting into %TARGET%...
powershell -NoProfile -Command "try { Expand-Archive '%TEMP_ZIP%' -DestinationPath '%TARGET%' -Force } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 (
    echo.
    echo ERROR: Extract failed.
    pause
    exit /b 1
)

echo [3/3] Cleaning up...
del "%TEMP_ZIP%" >nul 2>&1

echo.
echo Done. Updated: %TARGET%02_Presentations\
echo.
echo Next: drop decks into %TARGET%02_Presentations\decks_to_polish\
echo       then double-click %TARGET%02_Presentations\polish_windows.bat
echo.
pause
