@echo off
setlocal enabledelayedexpansion

REM Opens the most recently modified index.html under reports/
REM on the default browser. Run from M:\ARS\02_Presentations\html_review\.

set REPORTS_ROOT=..\reports

if not exist "%REPORTS_ROOT%" (
    echo No reports found at %REPORTS_ROOT%.
    pause
    exit /b 1
)

set LATEST=
set LATEST_TIME=0

for /r "%REPORTS_ROOT%" %%F in (index.html) do (
    set FULL=%%F
    set TS=%%~tF
    if "!TS!" gtr "!LATEST_TIME!" (
        set LATEST=%%F
        set LATEST_TIME=!TS!
    )
)

if "%LATEST%"=="" (
    echo No index.html files found in %REPORTS_ROOT%.
    pause
    exit /b 1
)

echo Opening %LATEST%
start "" "%LATEST%"
