@echo off
title CSI Velocity - ARS Analysis
color 0A

:: Go to repo root (one level up from 01_Analysis)
cd /d "%~dp0.."

echo.
echo ======================================================================
echo   CSI VELOCITY - ARS Analysis Pipeline
echo   Starting UI at http://localhost:8000
echo ======================================================================
echo.

:: Launch browser first, then start server
start http://localhost:8000

:: Start the FastAPI server (blocks until closed)
python ui\app.py

echo.
pause
