@echo off
title CSI Velocity - ARS Analysis
color 0A

echo.
echo ======================================================================
echo   CSI VELOCITY - ARS Analysis Pipeline
echo   Starting UI...
echo ======================================================================
echo.

:: Navigate to repo root (where ui_mockup.py lives)
cd /d "%~dp0.."

:: Check if streamlit is available
where streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo   Streamlit not found. Running setup first...
    echo.
    pip install -r "%~dp0..\requirements.txt"
    echo.
)

:: Launch the Streamlit UI
echo   Opening browser...
echo   (Close this window or press Ctrl+C to stop the server)
echo.
streamlit run ui_mockup.py --server.headless true --browser.gatherUsageStats false
