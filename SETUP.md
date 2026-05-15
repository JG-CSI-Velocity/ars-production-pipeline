# Velocity Pipeline Setup

## Your slide manifest is NOT tracked by git

`SLIDE_MANIFEST.xlsx` is your personal working copy -- edit it freely, mark `Keep? Y/N/A`, add notes. Pulls will never overwrite it.

The repo ships `SLIDE_MANIFEST.template.xlsx` as a fresh starting point. On a new machine, seed your working copy once:

```
copy SLIDE_MANIFEST.template.xlsx SLIDE_MANIFEST.xlsx
```

From then on it's yours -- nothing in git can clobber it.

## M: Drive Structure

```
M:\ARS\
  00_Formatting\
    run.py
    00-Scripts\
    01-Data-Ready for Formatting\   <- extracted CSVs land here
    02-Data-Ready for Analysis\     <- formatted Excel output
  01_Analysis\
    run.py
    00-Scripts\
    01_Completed_Analysis\          <- Excel + charts output
  02_Presentations\                 <- PPTX output
  03_Config\
    clients_config.json
  04_Logs\                          <- per-run log files
  05_UI\
    app.py
    index.html
```

## First-Time Setup

### 1. Install Python packages

```
pip install loguru rich pydantic pydantic-settings openpyxl xlsxwriter python-pptx matplotlib numpy pandas fastapi uvicorn
```

### 2. Clone the repo

```
M:
cd \ARS
git clone https://github.com/JG-CSI-Velocity/ars-production-pipeline.git .
```

### 3. Verify clients_config.json

Check that `M:\ARS\03_Config\clients_config.json` has the correct:
- `EligibleStatusCodes` -- stat codes for eligible accounts (e.g. `["20", "30"]`)
- `EligibleProductCodes` -- product codes for eligible accounts (e.g. `["20", "7"]`)
- `RegEOptInCode` -- value(s) in the Reg E column that mean "opted in" (e.g. `["Y"]`)
- `ICRate` -- interchange rate for revenue calculations
- `BranchMapping` -- branch ID to branch name mapping

## Running

### Step 1: Format ODD files

Reads raw ZIPs from the CSM's data dump folder, extracts, formats via 7-step
pipeline, writes formatted Excel to `02-Data-Ready for Analysis`.

```
cd M:\ARS\00_Formatting
python run.py --month 2026.03 --csm James --client 1780
python run.py --month 2026.03 --csm James --client 1780 --force   # overwrite existing
python run.py --month 2026.03 --csm James                         # all clients for this CSM
```

CSM name is fuzzy-matched: `James` matches `JamesG` folder.

**Output folders created:**
```
M:\ARS\00_Formatting\01-Data-Ready for Formatting\JamesG\2026.03\1780\   <- extracted CSV
M:\ARS\00_Formatting\02-Data-Ready for Analysis\JamesG\2026.03\1780\    <- formatted Excel
```

### Step 2: Run analysis + generate PPTX

Reads the formatted Excel, runs 22 ARS analysis modules, generates Excel
workbook + PowerPoint deck.

```
cd M:\ARS\01_Analysis
python run.py --month 2026.03 --csm James --client 1780
```

**Output folders created:**
```
M:\ARS\01_Analysis\01_Completed_Analysis\JamesG\2026.03\1780\           <- Excel + data
M:\ARS\01_Analysis\01_Completed_Analysis\JamesG\2026.03\1780\charts\    <- chart PNGs
M:\ARS\02_Presentations\JamesG\2026.03\1780\                            <- PowerPoint deck
M:\ARS\04_Logs\JamesG\2026.03\1780_YYYYMMDD_HHMMSS.log                 <- run log
```

### Launch the UI

```
cd M:\ARS\05_UI
python app.py
```

Then open http://localhost:8000

If port 8000 is already in use from a previous run:
```
netstat -ano | findstr :8000
taskkill /PID <pid> /F
python app.py
```

### Run all clients (batch)

```
cd M:\ARS\00_Formatting
python run.py --month 2026.03 --csm James

cd M:\ARS\01_Analysis
python run.py --month 2026.03 --csm James --client 1200
python run.py --month 2026.03 --csm James --client 1780
```

## Updating

```
cd M:\ARS
git pull
```

## Troubleshooting

### OLE warning when opening formatted Excel
If Excel shows "waiting for another application to complete an OLE action",
the file was written with openpyxl. Re-run Step 1 with `--force` after
pulling the latest code (now uses xlsxwriter).

### Port 8000 already in use
Kill the old process:
```
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### Stale "James" folders (should be "JamesG")
Earlier runs created folders under `James/` instead of `JamesG/`. Delete them:
```
rmdir /s /q "M:\ARS\04_Logs\James"
rmdir /s /q "M:\ARS\01_Analysis\01_Completed_Analysis\James"
rmdir /s /q "M:\ARS\02_Presentations\James"
```

### Reg E showing no data
Check `clients_config.json` for the correct `RegEOptInCode` value. Also verify
that `EligibleProductCodes` and `EligibleStatusCodes` are correct -- if those
filters eliminate all accounts, Reg E has nothing to analyze.

### mplstyle chart failures
If slides fail with "not a valid package style", pull the latest code. The
fix loads the style as a dict instead of a file path.
