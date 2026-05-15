# Velocity Pipeline

**ARS + Transaction analysis pipeline for credit union and bank clients.**

Formats raw ODD data, runs 25+ analysis modules, generates PowerPoint decks -- all from a web UI so CSMs never touch the command line.

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
│   │   ├── shared/         # Shared utilities, format_odd, helpers
│   │   └── diagnose_txn_files.py   # Standalone utility to find malformed CSVs
│   └── 01_Completed_Analysis/  # Output (Excel, charts, JSON per client)
│
├── 02_Presentations/       # Step 3: Generated PPTX output
│   └── {CSM}/{YYYY.MM}/{client_id}/    # Per-client decks
│
├── 03_Config/              # All configuration
│   ├── ars_config.json     # Pipeline paths, CSM sources, extra file paths
│   ├── clients_config.json # Per-client settings (multi-tenant)
│   ├── branch_configs/     # Per-client branch number -> name maps
│   │   └── {CLIENT_ID}.json
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

Opens http://localhost:8000 in your browser. If port 8000 is taken (e.g., another instance is running), the server auto-walks 8001..8010 and prints the actual URL it's serving on. Set `ARS_UI_PORT=<n>` to override the starting port. Keep the black window open while using the UI.

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
- `--parallel N` -- format N clients in parallel

**Run analysis + generate deck:**
```
cd M:\ARS\01_Analysis
python run.py --month 2026.04 --csm JamesG --client 1615
python run.py --month 2026.04 --csm JamesG --client 1615 --product txn
python run.py --month 2026.04 --csm JamesG --client 1615 --product combined
```

Products (`--product`):
- `ars` -- ARS analysis only (DEFAULT, recommended for standard client reviews)
- `txn` -- Transaction analysis only (the big TXN deep-dive)
- `combined` -- Both ARS and TXN in one deck (largest output)

**ARS is the main product.** TXN is additive -- explicitly opt-in via `--product txn` or `--product combined`. See issue #94 for the philosophy.

**Run slide sampler (review all slide variants):**
```
cd M:\ARS\01_Analysis
python run_sampler.py --month 2026.04 --csm JamesG --client 1615
python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
python run_sampler.py --list-sections
```

**Diagnose a malformed TXN CSV (read-only, no data changes):**
```
python 01_Analysis/00-Scripts/diagnose_txn_files.py --csm JamesG --client 1441
```
Walks every line of every TXN CSV for the client, finds rows that don't match the expected column count, and prints raw bytes around bad lines so you can see the malformation directly. Use when the loader crashes on a specific line number and you need to fix the source data.

## Environment Variables

| Var | Default | Effect |
|---|---|---|
| `SLIDE_MODE` | `standard` | Controls TXN deck size. `standard` (~225 slides), `deep` (~335, full analyst audit), `minimal` (~100, lean exec one-pager). Honored by competition + campaign sections. |
| `SLIDE_BUDGET` | `150` | If TXN summary exceeds this, prints a notice with the heaviest sections and suggests `SLIDE_MODE=minimal`. |
| `CLIENT_TYPE` | auto-detect | `cu` or `bank`. Forces member/customer language across the deck. Auto-detected from `CLIENT_NAME` (CU markers: ``CREDIT UNION'', ``FCU'', ``FEDERAL CREDIT''). |
| `ARS_UI_PORT` | `8000` | Starting port for the UI. Server walks `port..port+10` if the preferred port is in use. |
| `CSM`, `MONTH`, `CLIENT_ID` | (from CLI) | TXN file path components. Set automatically by `run.py`. |

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
                      ├─ Run 25 ARS modules (always)
                      ├─ Run 22 TXN sections   (if --product txn|combined)
                      │     ├─ txn_setup runs ONCE (Parquet cache: 26 min ─► seconds on 2nd run)
                      │     ├─ Each section's numbered scripts execute in shared namespace
                      │     ├─ Per-script failures surfaced in summary table
                      │     └─ Memory hygiene + telemetry between scripts
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

Per-client settings: IC rates, NSF fees, status codes, product codes, branch mappings. Multi-tenant.

### branch_configs/{CLIENT_ID}.json

Per-client branch number-to-name mapping. Without this file, section 10 (Branch Performance) shows numeric IDs instead of branch names. Sample template at `01_Analysis/00-Scripts/analytics/branch_txn/branch_config.sample.json`. Format:

```json
{
  "1": "Main Office",
  "2": "Downtown Branch",
  "3": "West Branch"
}
```

### CLIENT_CONFIGS (in competition/01_competitor_config.py)

Per-client competitor patterns: `credit_unions`, `local_banks`, `custom`, plus the Fed District top-25 to load. Each new client onboards by adding an entry. The pipeline prints a loud warning if `CLIENT_ID` has no entry.

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

### TXN (22 sections, 340+ scripts -- transaction data)

| Section | Scripts | What it analyzes |
|---------|--------:|------------------|
| txn_setup (shared) | 10 | File loading, merchant consolidation, ODDD account-type tagging, Parquet cache |
| general | 30 | Portfolio KPIs, demographics, engagement, **ARS swipe segmentation (3m vs 12m)** |
| merchant | 14 | Top merchants, concentration, trends, volatility |
| mcc_code | 15 | Category analysis |
| business_accts | 14 | Business merchant patterns |
| personal_accts | 14 | Personal merchant patterns |
| competition | 35 | Competitor detection, wallet share, **multi-competitor count distribution**, CU/bank audit (cell 69), detection diagnostic (cell 68) |
| financial_services | 20 | FI transaction leakage, detection diagnostic (cell 20) |
| ics_acquisition | 10 | Channel analysis |
| campaign | 43 | Mailer + cohort lift |
| branch_txn | 10 | Branch-level spend |
| transaction_type | 16 | PIN/SIG/ACH channels |
| product | 10 | Product-level spend |
| attrition_txn | 12 | Velocity-based risk |
| balance | 10 | Balance band analysis |
| interchange | 10 | PIN/SIG revenue |
| rege_overdraft | 10 | Opt-in trends |
| payroll | 10 | Direct deposit detection, PFI scoring |
| relationship | 10 | Cross-product holdings |
| segment_evolution | 8 | Engagement tier migration |
| retention | 7 | Churn/dormancy |
| engagement | 6 | Monthly tier classification |
| executive | 5 | KPI scorecard |

TXN scripts are wired into the pipeline via `txn_wrapper.py`. Run with `--product txn` or `--product combined`.

### Diagnostic Cells (always run, not pruned by SLIDE_MODE)

| Cell | What it shows |
|---|---|
| `competition/68_detection_diagnostic.py` | Per-category txn counts, top merchants per category, top unmatched financial keyword merchants |
| `competition/69_cu_bank_audit.py` | Per-pattern audit of every configured CU + local bank, plus top untagged FI-like merchants |
| `financial_services/20_detection_diagnostic.py` | Per-category counts, brand-root audit (Coinbase / Robinhood / Fidelity / Schwab / Vanguard) |

## Pipeline Hardening (PR #93 highlights)

- **Per-script failure surfacing.** Cell crashes inside a section used to be logged-only and the summary still said `OK`. The TXN summary now lists every failed script with error type + truncated message under its parent section.
- **Content-aware delimiter detection.** TXN CSVs that are TAB-delimited but named `.csv` (and vice-versa) load correctly; loader sniffs the first 8 KB.
- **Surviving-header-row removal.** Files with a metadata banner before the actual header (header survives `skiprows=1` and pollutes data) are now detected and skipped.
- **Smart Unknown Merchant fallback.** ATMs / fees / ACH transfers / checks no longer all collapse to one ``UNKNOWN MERCHANT'' bucket; they get re-labeled by `transaction_type`.
- **Carrier-prefix stripping.** Merchant strings like `ACH CREDIT SESLOC CREDIT UNION 805-555` are normalized to `SESLOC CREDIT UNION` so prefix-matching in `tag_competitors` works for CUs / local banks (not just for hand-coded brands like VENMO / PAYPAL).
- **Memory hygiene between scripts.** `plt.close('all')` + `gc.collect()` between scripts prevents the campaign section memory cluster.
- **Parquet cache status block.** Always-on HIT / MISS / NO CACHE block at the start of every TXN run -- explains why the run is slow (or fast).
- **Atomic Parquet save.** Sibling-file write + `Path.replace()` instead of cross-filesystem `shutil.move` -- 30-60s save becomes <1s.
- **Universal title/subtitle layout.** `GEN_TITLE_Y` / `GEN_SUBTITLE_Y` / `GEN_TOP_PAD` constants in general theme. Subtitles no longer overlap titles.
- **Dynamic member/customer language.** `member_word()`, `MEMBER_NOUN_PLURAL`, etc. auto-pick CU vs bank terminology based on `CLIENT_NAME` or `CLIENT_TYPE` env var.
- **ARS-standard swipe segmentation.** 7 buckets (`<1`, `1-5`, `6-10`, `11-15`, `16-20`, `21-25`, `25+`) with 3-month rolling AND 12-month averages, plus Stable/Active/Declining KPIs.
- **UI auto-port.** Port-conflict no longer presents as an indefinite hang.

## Web UI

Launch with `Start Here.bat`. Six tabs:

| Tab | What it does |
|-----|-------------|
| **Dashboard** | KPIs (clients, reports, avg time, success rate), reports by CSM chart, recent runs |
| **Format** | Select CSM + month + client, format ODD files. Months populated from raw data dumps. |
| **Generate** | Select product (ARS, TXN, Combined, Deposits), pick client, run analysis + PPTX |
| **Results** | Browse chart images from completed analysis, download Excel/PPTX |
| **History** | All runs with duration, slide count, status parsed from log files |
| **Schedules** | Create recurring monthly schedules per client. Run Now or auto-run on day of month. |

All dropdowns populated dynamically from `ars_config.json` and `clients_config.json`. No hardcoded values.

## Slide Sampler

Generates one PPTX per section from existing analysis results. Each chart shown in 4 layout options (CUSTOM, CONTENT, TWO_CONTENT, WIDE_TITLE) so you can compare and pick.

```
cd M:\ARS\01_Analysis
python run_sampler.py --month 2026.04 --csm JamesG --client 1615
python run_sampler.py --month 2026.04 --csm JamesG --client 1615 --section mailer
python run_sampler.py --list-sections
```

Output: one PPTX per section (`1615_2026.04_SAMPLER_MAILER.pptx`, etc.). Does NOT re-run analysis -- reads from existing chart PNGs in `01_Completed_Analysis/`.

## Slide Manifest

`SLIDE_MANIFEST.xlsx` -- complete inventory of every slide across all modules. 28 tabs (7 ARS + 18 TXN + Preamble + Layout Reference). Fill in Keep? (Y/N) and Layout Choice columns to define the production deck.

## Development

- **Develop on Mac**, pipeline runs on **Windows work PC at M:\\ARS\\**
- **GitHub** is the bridge -- push from Mac, `git pull` (or ZIP download) on work PC
- Git can be flaky on the M: drive (network share ownership). Falling back to ZIP downloads is fine.
- CSI brand: orange `#F15D22`, navy `#00274C`, gold `#FBAE40`, Montserrat font

## Tech Stack

- Python 3.x
- FastAPI + Uvicorn (web server)
- Pandas + NumPy (data manipulation)
- Matplotlib + Seaborn (chart generation)
- python-pptx (PowerPoint generation)
- openpyxl / xlsxwriter (Excel I/O)
- pyarrow (Parquet cache)
- loguru (logging)
- psutil (memory telemetry, optional)
