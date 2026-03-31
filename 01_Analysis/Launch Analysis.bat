@echo off
title CSI Velocity - ARS Analysis
color 0A

:: Stay in the folder where this .bat file lives (01_Analysis)
cd /d "%~dp0"

echo.
echo ======================================================================
echo   CSI VELOCITY - ARS Analysis Pipeline
echo ======================================================================
echo.
set /p month="   Month (e.g. 2026.03): "
set /p csm="   CSM name (e.g. JamesG): "
set /p client="   Client ID (e.g. 1200): "
echo.
echo   Running analysis for client %client%, month %month%...
echo.

python run.py --month %month% --csm %csm% --client %client%

echo.
if %errorlevel% neq 0 (
    echo   Something went wrong. Check the error above.
) else (
    echo   Done.
)
echo.
pause
