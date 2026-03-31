@echo off
title CSI Velocity
color 0A

cd /d M:\ARS

echo.
echo ======================================================================
echo   CSI VELOCITY
echo   Starting...
echo ======================================================================
echo.

if not exist "05_UI\app.py" (
    echo   ERROR: 05_UI\app.py not found in M:\ARS
    echo.
    pause
    exit /b 1
)

start http://localhost:8000
python 05_UI\app.py

pause
