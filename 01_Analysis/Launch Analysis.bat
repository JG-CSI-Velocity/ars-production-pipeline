@echo off
title CSI Velocity - ARS Pipeline
color 0A

:: Go to M:\ARS (the pipeline root on the work PC)
cd /d M:\ARS

echo.
echo ======================================================================
echo   CSI VELOCITY - ARS Pipeline
echo   Starting server at http://localhost:8000
echo ======================================================================
echo.

:: Verify 05_UI exists
if not exist "05_UI\app.py" (
    echo   ERROR: M:\ARS\05_UI\app.py not found.
    echo.
    pause
    exit /b 1
)

:: Open browser (will load once server is ready)
start http://localhost:8000

:: Start the FastAPI server
python 05_UI\app.py

echo.
pause
