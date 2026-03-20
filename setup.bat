@echo off
title ARS Pipeline Setup
color 0A

echo.
echo ======================================================================
echo   ARS PIPELINE SETUP
echo   Installs all required Python packages
echo ======================================================================
echo.

pip install -r "%~dp0requirements.txt"

echo.
echo ======================================================================
echo   Setup complete. You can now run:
echo.
echo   Step 1 (Format):
echo     cd M:\ARS\00_Formatting
echo     python run.py --month 2026.03 --csm JamesG --client 1200
echo.
echo   Step 2 (Analyze):
echo     cd M:\ARS\01_Analysis
echo     python run.py --month 2026.03 --csm JamesG --client 1200
echo ======================================================================
echo.
pause
