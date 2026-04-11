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

cd /d "%~dp005_UI"

:: Start the server in the background
start /b python app.py

:: Wait for the server to be ready
echo   Waiting for server...
:wait_loop
timeout /t 1 /nobreak >nul
curl -s -o nul http://localhost:8000 2>nul
if errorlevel 1 goto wait_loop

echo   Server ready! Opening browser...
echo.
echo ======================================================================
echo   Velocity is running at http://localhost:8000
echo   Close this window to stop the server.
echo ======================================================================

start http://localhost:8000

:: Keep the window open (server runs in background)
pause >nul
