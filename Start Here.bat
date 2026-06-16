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

REM --- Find the Python bundle installed by "CSM Setup.bat" ---
set "VELOCITY_PY=%LOCALAPPDATA%\Velocity\python\python.exe"
if not exist "%VELOCITY_PY%" (
    color 0C
    echo   This computer has not been set up yet.
    echo.
    echo   Please double-click "CSM Setup.bat" once and wait for "Done",
    echo   then run "Start Here.bat" again.
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

REM --- Start the server in the background using the bundled Python ---
start "" /b "%VELOCITY_PY%" app.py

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
