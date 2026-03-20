@echo off
title ARS ODD File Formatter
color 0A

echo.
echo ======================================================================
echo   ARS ODD FILE FORMATTER
echo ======================================================================
echo.

echo   Who are you?
echo.
echo     1. James
echo     2. Jordan
echo     3. Aaron
echo     4. Gregg
echo     5. Dan
echo     6. Max
echo.
set /p CSM_CHOICE="   Enter number (1-6): "

if "%CSM_CHOICE%"=="1" set CSM_NAME=JamesG
if "%CSM_CHOICE%"=="2" set CSM_NAME=Jordan
if "%CSM_CHOICE%"=="3" set CSM_NAME=Aaron
if "%CSM_CHOICE%"=="4" set CSM_NAME=Gregg
if "%CSM_CHOICE%"=="5" set CSM_NAME=Dan
if "%CSM_CHOICE%"=="6" set CSM_NAME=Max

if not defined CSM_NAME (
    echo   Invalid selection.
    pause
    exit /b
)

echo.
echo   Selected: %CSM_NAME%
echo.

:: Read current path from config for this CSM
for /f "tokens=2 delims=:," %%a in ('findstr /i "%CSM_NAME%" "%~dp0configs\ars_config.json"') do (
    set CURRENT_PATH=%%~a
)
set CURRENT_PATH=%CURRENT_PATH:"=%
set CURRENT_PATH=%CURRENT_PATH: =%

echo   Your current source folder:
echo     %CURRENT_PATH%
echo.
echo   Press ENTER to keep this path, or type a new path:
echo.
set /p NEW_PATH="   Path (or ENTER to keep): "

if not "%NEW_PATH%"=="" (
    echo   Updated path to: %NEW_PATH%
    echo   NOTE: To save permanently, update configs\ars_config.json
)

echo.
echo   Enter a 4-digit client ID, or type ALL to process every client.
echo.
set /p CLIENT_ID="   Client ID (or ALL): "

echo.
echo ======================================================================

if /i "%CLIENT_ID%"=="ALL" (
    echo   Running for %CSM_NAME% -- ALL clients...
    echo ======================================================================
    echo.
    python "%~dp0run.py" --csm %CSM_NAME%
) else (
    echo   Running for %CSM_NAME% -- Client %CLIENT_ID%...
    echo ======================================================================
    echo.
    python "%~dp0run.py" --csm %CSM_NAME% --client %CLIENT_ID%
)

echo.
echo ======================================================================
echo   DONE. Press any key to close.
echo ======================================================================
pause >nul
