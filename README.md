# Velocity Pipeline

**ARS + Transaction analysis pipeline for credit union clients.**

Formats raw ODD data, runs 25 analysis modules, generates PowerPoint decks -- all from a web UI so CSMs never touch the command line.

## Folder Structure

```
M:\ARS\
├── 00_Formatting/          # Step 1: Format raw ODD files
│   ├── run.py              # Formatting entry point
│   ├── 01-Data-Ready for Formatting/   # Staging (extracted ZIPs)
│   └── 02-Data-Ready for Analysis/     # Output (formatted Excel per client)
│
├── 01_Analysis/            # Step 2: Run analysis + generate deck
│   ├── run.py              # Analysis entry point
│   ├── run_sampler.py      # Slide sampler (review tool)
│   ├── 00-Scripts/
│   │   ├── analytics/      # 25 ARS modules + 23 TXN script folders
│   │   ├── charts/         # Chart styling and guards
│   │   ├── output/         # Deck builder, Excel formatter, sample builder
│   │   ├── pipeline/       # Pipeline runner, steps, context
│   │   └── shared/         # Shared utilities, format_odd, helpers
│   └── 01_Completed_Analysis/  # Output (Excel, charts, JSON per client)
│
├── 02_Presentations/       # Step 3: Generated PPTX output
│   └── {CSM}/{YYYY.MM}/{client_id}/    # Per-client decks
│
├── 03_Config/              # All configuration
│   ├── ars_config.json     # Pipeline paths, CSM sources, extra file paths
│   ├── clients_config.json # Per-client settings (22 credit unions)
│   └── settings.py         # Pydantic settings loader
│
├── 04_Logs/                # Run logs and history
│
├── 05_UI/                  # Web interface
│   ├── app.py              # FastAPI server
│   └── index.html          # Single-page UI
│
├── Start Here.bat          # Double-click to launch UI
├── setup.bat               # Install Python dependencies
├── requirements.txt        # Python package requirements
├── SLIDE_MAPPING.md        # Master slide spec (layouts, headlines, charts)
└── SETUP.md                # Setup and troubleshooting guide
```

## Quick Start

### First Time Setup

```
cd M:\ARS
python -m pip install -r requirements.txt
```

Or double-click `setup.bat`.

### Launch the UI

Double-click `Start Here.bat` at `M:\ARS\`.

Opens http://localhost:8000 in your browser. Keep the black window open while using the UI.

### Command Line Usage

**Format ODD files:**
```
cd M:\ARS\00_Formatting
python run.py --month 2026.04 --csm JamesG --client 1615
python run.py --month 2026.04 --csm JamesG --with-all
```

Flags:
- `--with-trans` -- also copy transaction files from data dump
- `--with-deferred` -- also copy deferred revenue files
- `--with-workbook` -- also copy workbook files from R: drive
- `--with-all` -- all three above
- `--force` -- re-process even if output already exists

**Run analysis + generate deck:**
```
cd M:\ARS\01_Analysis
python run.py --month 2026.04 --csm JamesG --client 1615
```

**Run slide sampler (review all slide variants):**
```
cd M:\ARS\01_Analysis
python run_sampler.py --month 2026.04 --csm JamesG --client 1615
python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
python run_sampler.py --list-sections
```

## Pipeline Flow

```
CSM Data Dump (M:\JamesG\OD Data Dumps\2026.04\)
  │
  ├─ ODD ZIPs ──────► 00_Formatting/run.py
  │                      │
  │                      ├─ Extract ZIP to staging
  │                      ├─ 7-step formatting
  │                      └─ Output: 02-Data-Ready for Analysis/{CSM}/{month}/{client}/
  │
  ├─ Trans files ───► (--with-trans copies to client folder)
  ├─ Deferred ──────► (--with-deferred copies from billing folder)
  └─ Workbooks ─────► (--with-workbook copies from R: drive)
                           │
                           ▼
                    01_Analysis/run.py
                      │
                      ├─ Load formatted ODD
                      ├─ Run 25 analysis modules
                      ├─ Generate charts (PNG)
                      ├─ Build PowerPoint deck
                      └─ Output:
                           ├─ 01_Completed_Analysis/{CSM}/{month}/{client}/
                           └─ 02_Presentations/{CSM}/{month}/{client}/
```

## Configuration

### ars_config.json

Controls pipeline paths and CSM source folders:

```json
{
    "paths": {
        "ars_base": "M:\\ARS",
        "retrieve_dir": "00_Formatting\\01-Data-Ready for Formatting",
        "watch_root": "00_Formatting\\02-Data-Ready for Analysis"
    },
    "csm_sources": {
        "sources": {
            "JamesG": "M:\\JamesG\\OD Data Dumps",
            "Jordan": "M:\\Jordan\\OD Data Dumps"
        }
    },
    "extra_files": {
        "deferred_base": "M:\\My Rewards Logistics\\...",
        "workbook_base": "R:"
    }
}
```

### clients_config.json

Per-client settings: IC rates, NSF fees, status codes, product codes, branch mappings. 22 credit unions configured.

## Analysis Modules

### ARS (25 modules -- ODD data)

| Section | Modules | What it analyzes |
|---------|---------|------------------|
| Overview | 3 | Eligibility, stat codes, product codes |
| Debit Card (DCTR) | 5 | Penetration, trends, branches, funnel |
| Reg E / Overdraft | 3 | Opt-in rates, branch comparison |
| Attrition | 3 | Closure rates, demographics, revenue impact |
| Mailer Campaign | 5 | Response rates, cohort lift, reach |
| Value | 1 | Revenue attribution |
| Insights | 5 | Synthesis, recommendations, branch scorecard |

### TXN (23 folders, 335 scripts -- transaction data)

| Section | Scripts | What it analyzes |
|---------|---------|------------------|
| General | 29 | Portfolio KPIs, demographics, engagement |
| Merchant | 14 | Top merchants, concentration, trends |
| MCC Code | 15 | Category analysis |
| Business Accts | 14 | Business merchant patterns |
| Personal Accts | 14 | Personal merchant patterns |
| Competition | 33 | Competitor detection, wallet share |
| Financial Services | 19 | FI transaction leakage |
| ICS Acquisition | 10 | Channel analysis |
| Campaign | 43 | Campaign + cohort lift |
| Branch TXN | 10 | Branch-level spend |
| Transaction Type | 16 | PIN/SIG/ACH channels |
| Product | 10 | Product-level spend |
| Attrition TXN | 12 | Velocity-based risk |
| Balance | 10 | Balance band analysis |
| Interchange | 10 | PIN/SIG revenue |
| Reg E Overdraft | 10 | Opt-in trends |
| Payroll | 10 | Direct deposit detection |
| Relationship | 10 | Cross-product holdings |
| Segment Evolution | 8 | Engagement tier migration |
| Retention | 7 | Churn/dormancy |
| Engagement | 6 | Monthly tier classification |
| Executive | 5 | KPI scorecard |
| TXN Setup | 10 | Shared utilities, file config |

**Note:** TXN scripts are merged but not yet wired into the pipeline runner (v2.0 work).

## Slide Sampler

The slide sampler generates a review PPTX showing every slide variant the analysis produces, each stamped with metadata:

```
[MAILER 3/33] id:A12.Jan26.Swipes | layout:8 (CUSTOM) | type:screenshot
```

Use it to review and pick which slides to keep per section, then lock those into the production deck builder.

```
python run_sampler.py --month 2026.04 --csm JamesG --client 1615
python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
```

## Development

- **Develop on Mac**, pipeline runs on **Windows work PC at M:\ARS\**
- **GitHub** is the bridge -- push from Mac, download ZIP on work PC
- Git does not work on the M: drive (network share ownership issue). Use ZIP downloads.
- CSI brand: orange `#F15D22`, navy `#00274C`, gold `#FBAE40`, Montserrat font

## Tech Stack

- Python 3.x
- FastAPI + Uvicorn (web server)
- Pandas (data manipulation)
- Matplotlib (chart generation)
- python-pptx (PowerPoint generation)
- openpyxl / xlsxwriter (Excel I/O)
- loguru (logging)
