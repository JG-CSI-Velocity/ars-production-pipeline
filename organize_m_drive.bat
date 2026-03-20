@echo off
title ARS Folder Organizer
color 0E

echo.
echo ======================================================================
echo   ARS FOLDER ORGANIZER
echo   This will organize M:\ARS\ into the new structure.
echo   Nothing is deleted -- old folders are moved to _archive.
echo ======================================================================
echo.
echo   Structure:
echo.
echo     M:\ARS\
echo       _archive\
echo       00_Formatting\
echo         run.py
echo         00-Scripts\
echo         01-Data-Ready for Formatting\CSM\month\clientID
echo         02-Data-Ready for Analysis\CSM\month\clientID
echo       01_Analysis\
echo         run.py
echo         00-Scripts\
echo         01_Completed_Analysis\CSM\month\clientID
echo       02_Presentations\CSM\month\clientID
echo       Config\
echo       Logs\
echo.
echo   Press any key to proceed, or close this window to cancel.
pause >nul

echo.
echo   Working...

:: Create _archive if it doesn't exist
if not exist "M:\ARS\_archive" mkdir "M:\ARS\_archive"

:: Move old folders into _archive (skip the ones we're keeping)
if exist "M:\ARS\Analysis Outputs" (
    echo   Moving "Analysis Outputs" to _archive...
    move "M:\ARS\Analysis Outputs" "M:\ARS\_archive\Analysis Outputs" >nul 2>&1
)
if exist "M:\ARS\Output" (
    echo   Moving "Output" to _archive...
    move "M:\ARS\Output" "M:\ARS\_archive\Output" >nul 2>&1
)
if exist "M:\ARS\Presentations" (
    echo   Moving "Presentations" to _archive...
    move "M:\ARS\Presentations" "M:\ARS\_archive\Presentations" >nul 2>&1
)

:: Ensure the new structure exists
if not exist "M:\ARS\00_Formatting\00-Scripts" mkdir "M:\ARS\00_Formatting\00-Scripts"
if not exist "M:\ARS\00_Formatting\01-Data-Ready for Formatting" mkdir "M:\ARS\00_Formatting\01-Data-Ready for Formatting"
if not exist "M:\ARS\00_Formatting\02-Data-Ready for Analysis" mkdir "M:\ARS\00_Formatting\02-Data-Ready for Analysis"
if not exist "M:\ARS\01_Analysis\00-Scripts" mkdir "M:\ARS\01_Analysis\00-Scripts"
if not exist "M:\ARS\01_Analysis\01_Completed_Analysis" mkdir "M:\ARS\01_Analysis\01_Completed_Analysis"
if not exist "M:\ARS\02_Presentations" mkdir "M:\ARS\02_Presentations"
if not exist "M:\ARS\Config" mkdir "M:\ARS\Config"
if not exist "M:\ARS\Logs" mkdir "M:\ARS\Logs"

:: Create CSM subfolders in each data directory
for %%C in (JamesG Jordan Aaron Gregg Dan Max) do (
    if not exist "M:\ARS\00_Formatting\01-Data-Ready for Formatting\%%C" mkdir "M:\ARS\00_Formatting\01-Data-Ready for Formatting\%%C"
    if not exist "M:\ARS\00_Formatting\02-Data-Ready for Analysis\%%C" mkdir "M:\ARS\00_Formatting\02-Data-Ready for Analysis\%%C"
    if not exist "M:\ARS\01_Analysis\01_Completed_Analysis\%%C" mkdir "M:\ARS\01_Analysis\01_Completed_Analysis\%%C"
    if not exist "M:\ARS\02_Presentations\%%C" mkdir "M:\ARS\02_Presentations\%%C"
    echo   Created folders for %%C
)

echo.
echo ======================================================================
echo   DONE. Structure:
echo ======================================================================
echo.
dir /b /ad "M:\ARS\"
echo.
echo   Clone the repo:
echo     cd M:\ARS\00_Formatting\00-Scripts
echo     git clone https://github.com/JG-CSI-Velocity/ars-production-pipeline.git .
echo.
echo   Step 1 (format):
echo     cd M:\ARS\00_Formatting
echo     python run.py --month 2026.03 --csm JamesG --client 1200
echo.
echo   Step 2 (analyze):
echo     cd M:\ARS\01_Analysis
echo     python run.py "M:\ARS\00_Formatting\02-Data-Ready for Analysis\JamesG\2026.03\1200\1200-ODD.xlsx"
echo.
echo ======================================================================
pause
