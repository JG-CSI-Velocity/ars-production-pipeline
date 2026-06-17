@echo off
title Velocity Pipeline
color 0A

echo.
echo ======================================================================
echo   VELOCITY PIPELINE - Starting server...
echo ======================================================================
echo.
echo   (Keep this window open while using the UI)
echo.

REM --- Choose a Python: prefer the bundle if it's installed, otherwise fall
REM     back to a system Python already on this machine. Machines that have
REM     run this for months have their own Python and no bundle -- that's fine. ---
set "PYEXE="
set "VELOCITY_PY=%LOCALAPPDATA%\Velocity\python\python.exe"
if exist "%VELOCITY_PY%" (
    set "PYEXE=%VELOCITY_PY%"
) else (
    where python >nul 2>nul && set "PYEXE=python"
)

if not defined PYEXE (
    color 0C
    echo   No Python found on this computer.
    echo.
    echo   Either install Python, or double-click "CSM Setup.bat" once
    echo   ^(wait for "Done"^), then run "Start Here.bat" again.
    echo.
    pause >nul
    exit /b 1
)

REM --- Move into the UI folder.
REM     pushd maps a temporary drive letter for \\network\share paths,
REM     which plain "cd /d" cannot do - that was the old failure. ---
pushd "%~dp005_UI"
if errorlevel 1 (
    color 0C
    echo   Could not open the 05_UI folder.
    echo   Is the network drive / share connected?
    echo.
    pause >nul
    exit /b 1
)

REM --- Start the server in the background using the chosen Python ---
start "" /b "%PYEXE%" app.py

echo   Waiting for server...
:wait_loop
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:8000' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop > $null; exit 0 } catch { exit 1 }" >nul 2>nul
if errorlevel 1 goto wait_loop

echo   Server ready! Opening browser...
echo.
echo ======================================================================
echo   Velocity is running at http://localhost:8000
echo   Close this window to stop the server.
echo ======================================================================

start http://localhost:8000

REM Keep the window (and the temp drive mapping the server runs from) open.
pause >nul
