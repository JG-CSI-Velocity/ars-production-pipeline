@echo off
title CSM Setup - Velocity Pipeline
color 0B

echo.
echo ======================================================================
echo   VELOCITY PIPELINE - One-time setup
echo ======================================================================
echo.
echo   This installs everything the tool needs on THIS computer.
echo   It runs ONCE. You will not need to do this again.
echo.
echo   You can leave it running - it will say "Done" when it finishes.
echo   This can take a few minutes the first time.
echo.

set "TARGET=%LOCALAPPDATA%\Velocity"
set "ZIP=%TEMP%\Velocity-Python.zip"
set "URL=https://github.com/JG-CSI-Velocity/ars-production-pipeline/releases/download/python-bundle/Velocity-Python.zip"

REM --- Already set up? Skip straight to Done. ---
if exist "%TARGET%\python\python.exe" (
    color 0A
    echo   This computer is already set up. Nothing to do.
    echo.
    echo   Done. You can close this window and double-click "Start Here.bat".
    pause >nul
    exit /b 0
)

echo   [1 of 3] Downloading ^(one time, a few hundred MB^)...
powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%URL%' -OutFile '%ZIP%' -UseBasicParsing } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 goto fail_download

echo   [2 of 3] Installing ^(unpacking files^)...
if not exist "%TARGET%" mkdir "%TARGET%"
powershell -NoProfile -Command "try { Expand-Archive -Path '%ZIP%' -DestinationPath '%TARGET%' -Force } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 goto fail_unzip

echo   [3 of 3] Checking the install...
"%TARGET%\python\python.exe" -c "import fastapi, pandas, numpy, matplotlib, pptx; print('ok')" >nul 2>nul
if errorlevel 1 goto fail_verify

del "%ZIP%" >nul 2>nul

color 0A
echo.
echo ======================================================================
echo   Done. This computer is ready.
echo   Close this window and double-click "Start Here.bat".
echo ======================================================================
pause >nul
exit /b 0

:fail_download
color 0C
echo.
echo   COULD NOT DOWNLOAD the setup file.
echo     - Check that you have internet access and try again.
echo     - If it keeps failing, screenshot this window and send it to James.
echo.
pause >nul
exit /b 1

:fail_unzip
color 0C
echo.
echo   COULD NOT UNPACK the setup file.
echo     - Try running "CSM Setup.bat" again.
echo     - If it keeps failing, screenshot this window and send it to James.
echo.
pause >nul
exit /b 1

:fail_verify
color 0C
echo.
echo   Setup finished but a final check failed.
echo     - Screenshot this window and send it to James.
echo.
pause >nul
exit /b 1
