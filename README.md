# Velocity Pipeline

**ARS + Transaction analysis pipeline for credit union and bank clients.**

CSMs format raw ODD data, run 25+ analytics modules, and ship presentation-ready PowerPoint decks &mdash; entirely from a web UI. No notebooks, no terminals, no Python knowledge required.

The repo is `JG-CSI-Velocity/ars-production-pipeline`. The operator-facing surface lives at `05_UI/` &mdash; everything else is plumbing.

---

## Quick start (work machine)

The pipeline runs on Windows from `M:\ARS\`. To launch:

1. Double-click **`Start Here.bat`** at the repo root
2. Wait a few seconds for the server; your browser opens to `http://localhost:8000` automatically
3. Keep the black terminal window open while you work; closing it stops the server

If port 8000 is busy, the launcher walks 8001..8010 and prints the actual URL it served on. Override the starting port with `ARS_UI_PORT=<n>`.

**First-time setup, updating the code, and troubleshooting** &mdash; see [SETUP.md](SETUP.md).

---

## The UI (six tabs)

| Tab | What it does |
|---|---|
| **Dashboard** | KPIs across all CSMs, recent runs, success rate |
| **Format** | Step 1: read raw ODD ZIPs from a CSM's data dump folder, format into ready-for-analysis Excel. Also: **manual data-drop** panel for CSMs whose dump folder you don't have access to |
| **Generate** | Step 2: pick CSM + period + client + product (ARS / TXN / Combined / Deposits), click **Format + Analyze + Build PPTX**, get a deck |
| **Results** | Browse charts and slides from completed runs; download Excel/PPTX |
| **History** | Every run across every CSM with duration, slide count, status |
| **Schedules** | Recurring monthly auto-runs per client |

The Generate tab is the primary loop. A typical month: pick a client, click Generate, watch a 5-stage checklist (Read your data &rarr; Prepare analyses &rarr; Run analytics &rarr; Build PowerPoint deck &rarr; Save and deliver files) with real-time sub-progress through 25 analytics modules. When it finishes, a completion card shows what worked, what was skipped, and where the files landed &mdash; with a one-click **Open downloads** link.

For a developer-facing map of every screen and the HTML IDs / CSS classes / API endpoints behind each component, see [`05_UI/UI-OVERVIEW.md`](05_UI/UI-OVERVIEW.md).

---

## Pipeline at a glance

```
CSM data dump (raw ZIPs)              -->  Format (Step 1)  --> Ready-for-Analysis Excel
                                                                            |
                                                                            v
Ready-for-Analysis Excel              -->  Analyze (Step 2) --> Completed analysis
   (25 ARS modules, optionally               + chart PNGs + run_manifest.json
    22 TXN sections)                         + run_scorecard.md
                                                                            |
                                                                            v
                                            Build deck       --> PowerPoint (.pptx)
                                                                  + Excel workbook
                                                                  + (optional) local copy
                                                                  + competition_diagnostic.txt
                                                                  + Actionable Lists for Clients/
```

### CSM &harr; client membership

There is **no master CSM-client mapping anywhere**. `03_Config/clients_config.json` is a flat list of every client across every CSM. A client is associated with a CSM when their data appears in the CSM's folder at any pipeline stage:

| Stage | Path |
|---|---|
| Raw | `M:\<CSM>\OD Data Dumps\<period>\<client>_ODDD.zip` |
| Formatted | `00_Formatting\02-Data-Ready for Analysis\<CSM>\<period>\<client>\` |
| Completed | `01_Analysis\01_Completed_Analysis\<CSM>\<period>\<client>\` |

The Generate-tab client dropdown unions all three so a client shows up the moment a raw ZIP lands, and stays visible after formatting/analysis even if the ZIP moves.

### Products

Pick a product on the Generate tab; under the hood it sets the `--product` flag:

| Product | What runs | Deck filename |
|---|---|---|
| **ARS Full Suite** _(default)_ | 25 ARS modules from ODD data | `<id>_<period>_ars_deck.pptx` |
| **Transaction** | 22 TXN sections from transaction data | `<id>_<period>_txn_deck.pptx` |
| **Combined** | ARS + TXN in one deck | `<id>_<period>_combined_deck.pptx` |
| **Deposits** | Deposit-focused subset | (separate output) |

The three product decks have distinct filenames, so running TXN never overwrites an existing ARS deck for the same client + period.

---

## The slide manifest (operator-driven deck shaping)

`SLIDE_MANIFEST.xlsx` at the repo root is **your personal working manifest** &mdash; git pulls will never overwrite it. Each per-section sheet lists every slide and a `Keep? (Y/N)` column you fill in:

| Value | Meaning |
|---|---|
| `Y` | Keep on the main deck |
| `A` | Route to a separate `*_aux_deck.pptx` (appendix) |
| `N` | Drop entirely from every deck |
| _(blank)_ | Not yet decided &mdash; treated as keep |

The deck builder reads these decisions on every run. The Generate tab's completion card surfaces the breakdown: **main / appendix / dropped / undecided**, with color-coded counts.

The repo ships `SLIDE_MANIFEST.template.xlsx` as a fresh starting point. On a new machine, seed your working copy once:

```
copy SLIDE_MANIFEST.template.xlsx SLIDE_MANIFEST.xlsx
```

From then on it's yours &mdash; nothing in git can clobber it.

---

## Other features worth knowing

| Feature | Where | What it does |
|---|---|---|
| **Save deck to local folder** | Checkbox under the Run button on Generate | Optional: also writes the PPTX to a local path you specify (avoids slow download from the shared M: drive) |
| **Manual data-drop** | Collapsible panel on the Format tab | For Dan / Aaron / any CSM whose raw dump folder you can't see &mdash; paste a path to pre-formatted ODD files and stage them into the canonical layout in one click |
| **Run manifest** | Every analysis run writes `run_manifest.json` to `01_Completed_Analysis/<CSM>/<period>/<client>/` | Structured JSON with per-script status, error details, suggested fixes, copy-paste GitHub issue bodies |
| **Run scorecard** | `run_scorecard.md` in the same folder | One-page markdown summary: overall verdict, section table, every failure with context |
| **Competition diagnostic** | Auto-runs at the end of the competition section, writes `competition_diagnostic.txt` | Per-category counts, top merchants, unmatched financial keywords, BNPL audit. Surfaced in the completion card. |
| **File-lock fallback** | Automatic | If your previous deck is open in PowerPoint when a new run finishes, the new deck saves as `..._v2.pptx` instead of failing. 20-minute analyses never have to be redone. |
| **Versioned outputs** | Automatic | Three product flags, three distinct deck filenames. Run TXN without losing your ARS deck. |
| **Actionable Lists for Clients** | `Actionable Lists for Clients/<client>_<name>/cross_sell_lists/` | Cross-sell candidate lists from the competition module, in a clearly-named folder (formerly `output/`) |

---

## Repository layout

```
M:\ARS\
|-- 00_Formatting/                    Step 1: format raw ODDs
|   |-- run.py
|   |-- 01-Data-Ready for Formatting/   Staging (extracted ZIPs)
|   `-- 02-Data-Ready for Analysis/     Formatted Excel (per CSM/period/client)
|
|-- 01_Analysis/                      Step 2: run analysis + generate deck
|   |-- run.py
|   |-- 00-Scripts/
|   |   |-- analytics/                    25 ARS modules + 23 TXN script folders
|   |   |-- charts/                       Chart styling and guards
|   |   |-- output/                       Deck builder, manifest loader, headlines
|   |   |-- pipeline/                     Runner, steps, context, run_manifest
|   |   |-- shared/                       Utilities, format_odd, helpers
|   |   `-- tests/                        pytest test suite
|   `-- 01_Completed_Analysis/        Excel + charts + JSON per client per run
|
|-- 02_Presentations/                 Step 3: PowerPoint decks
|   `-- {CSM}/{YYYY.MM}/{client}/         Per-client decks
|
|-- 03_Config/
|   |-- ars_config.json                   Pipeline paths, CSM source folders
|   `-- clients_config.json               Per-client settings (multi-tenant) -- includes BranchMapping
|
|-- 04_Logs/                          Per-run log files
|-- 05_UI/                            FastAPI backend + single-page UI
|   |-- app.py                            API + run orchestration
|   |-- index.html                        Operator console
|   `-- UI-OVERVIEW.md                    Developer-facing component map
|
|-- Actionable Lists for Clients/    Cross-sell candidate lists (was: output/)
|
|-- Start Here.bat                    Double-click to launch the UI
|-- setup.bat                         Install Python dependencies
|-- requirements.txt
|-- SETUP.md                          First-time setup, common operations, troubleshooting
|-- SLIDE_MANIFEST.template.xlsx      Read-only manifest template (gitignored copy is yours)
|-- SLIDE_MANIFEST.xlsx               Your personal Keep?-marked manifest (NOT tracked)
|-- SLIDE_MAPPING.md                  Master slide spec
`-- SLIDE_DESIGN.md                   Design system reference
```

---

## CLI usage (developer / batch)

The UI calls the same `run.py` entrypoints internally. For batch work or debugging from a terminal:

**Format a single client:**
```
cd M:\ARS\00_Formatting
python run.py --month 2026.04 --csm James --client 1615
```

**Run analysis + generate deck:**
```
cd M:\ARS\01_Analysis
python run.py --month 2026.04 --csm James --client 1615
python run.py --month 2026.04 --csm James --client 1615 --product txn
python run.py --month 2026.04 --csm James --client 1615 --product combined
```

**Save a local copy of the deck:**
```
python run.py --month 2026.04 --csm James --client 1615 --local-copy "C:\Users\you\Documents\Velocity Decks"
```

**Diagnose a malformed TXN CSV (read-only):**
```
python 01_Analysis\00-Scripts\diagnose_txn_files.py --csm James --client 1441
```

CSM names are fuzzy-matched: `James` resolves to the `JamesG` folder if that's what's on disk.

### Environment variables

| Var | Default | Effect |
|---|---|---|
| `SLIDE_MODE` | `standard` | TXN deck size. `standard` (~225 slides), `deep` (~335), `minimal` (~100). |
| `SLIDE_BUDGET` | `150` | If TXN summary exceeds this, prints a notice and suggests `SLIDE_MODE=minimal`. |
| `CLIENT_TYPE` | auto-detect | `cu` or `bank`. Forces member/customer language. Auto-detected from `CLIENT_NAME`. |
| `ARS_UI_PORT` | `8000` | Starting port for the UI server; walks 8001..8010 if busy. |
| `SLIDE_MANIFEST_PATH` | (search) | Override the manifest path. Useful for tests and ad-hoc runs. |

---

## Configuration

### `03_Config/ars_config.json`
Pipeline paths and CSM source folders.

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
      "Dan":    "M:\\Dan\\OD Data Dumps"
    }
  }
}
```

### `03_Config/clients_config.json`
Per-client settings: IC rates, NSF fees, status codes, product codes, branch mappings. Multi-tenant; flat list across all CSMs.

### Branch mapping
Lives inside `clients_config.json` as the `BranchMapping` field on each client entry &mdash; a dict of `"branch_id": "Branch Name"`. The Branch Performance section reads it directly:

```json
"1776": {
  "ClientName": "CoastHills",
  "BranchMapping": {
    "10": "Base",
    "20": "Lompoc",
    "30": "Santa Maria"
  }
}
```

No separate per-client branch file is needed. The pipeline prints a clear warning if a client's `BranchMapping` is missing.

### `01_Analysis/00-Scripts/analytics/competition/01_competitor_config.py`
Per-client competitor patterns (`credit_unions`, `local_banks`, `custom`, `rollups`). New clients onboard by adding an entry to `CLIENT_CONFIGS`. The pipeline prints a loud warning if your `CLIENT_ID` is missing.

---

## Analysis modules

### ARS (25 modules &mdash; from ODD data)

| Section | Modules | What it analyzes |
|---|---:|---|
| Overview | 3 | Eligibility, stat codes, product codes |
| Debit Card Take Rate | 5 | Penetration, trends, branches, funnel |
| Reg E / Overdraft | 3 | Opt-in rates, branch comparison, dimensions |
| Attrition | 3 | Closure rates, demographics, revenue impact |
| Mailer Campaign | 5 | Response rates, cohort lift, reach |
| Value | 1 | Revenue attribution |
| Insights | 5 | Synthesis, recommendations, branch scorecard, dormant opportunity |

### TXN (22 sections &mdash; from transaction data)

| Section | Scripts | Highlights |
|---|---:|---|
| txn_setup (shared) | 10 | File loading, merchant consolidation, Parquet cache |
| general | 30 | Portfolio KPIs, demographics, ARS swipe segmentation |
| merchant | 14 | Top merchants, concentration, trends |
| mcc_code | 15 | Category analysis |
| business_accts / personal_accts | 14 each | Business vs personal patterns |
| competition | 35 | Competitor detection, wallet share, CU/bank audit, detection diagnostic |
| financial_services | 20 | FI leakage, brand-root audit |
| ics_acquisition | 10 | Channel analysis |
| campaign | 43 | Mailer + cohort lift |
| branch_txn | 10 | Branch-level spend |
| transaction_type | 16 | PIN / SIG / ACH channels |
| product | 10 | Product-level spend |
| attrition_txn | 12 | Velocity-based risk |
| balance | 10 | Balance-band analysis |
| interchange | 10 | PIN/SIG revenue |
| rege_overdraft | 10 | Opt-in trends |
| payroll | 10 | Direct deposit detection, PFI scoring |
| relationship | 10 | Cross-product holdings |
| segment_evolution | 8 | Engagement-tier migration |
| retention | 7 | Churn / dormancy |
| engagement | 6 | Monthly tier classification |
| executive | 5 | KPI scorecard, action roadmap |

---

## Development

Everything runs on the Windows work PC at `M:\ARS\`. GitHub is the source of truth &mdash; pull to update, push to share.

### Pull updates and restart the UI
```
M:
cd \ARS
git pull
```
Then close the Velocity Pipeline terminal window, double-click `Start Here.bat` to relaunch, and **Ctrl+Shift+R** in the browser to clear cached HTML/JS.

### Push your own changes
```
M:
cd \ARS
git checkout -b feature/<short-name>
git add <files>
git commit -m "<conventional message>"
git push
gh pr create
```

### Edits made via Claude Code
Changes pushed to GitHub from a Claude session land on a branch in the same repo. Pull on the work PC the same way:
```
git fetch
git checkout <branch-name>
git pull
```

Restart `Start Here.bat`. Ctrl+Shift+R in the browser.

### Files that are operator-local (gitignored)
- `SLIDE_MANIFEST.xlsx` &mdash; your Keep? decisions
- `CLAUDE.md` &mdash; AI-assistant working notes
- `02_Presentations/` and `04_Logs/` &mdash; per-run output

### Tests
```
cd 01_Analysis/00-Scripts
python -m pytest tests/ -q
```

Covers the run manifest (`pipeline/manifest.py`), error-capture utilities (`pipeline/error_capture.py`), scorecard generator (`pipeline/scorecard.py`), slide-manifest loader (`output/manifest.py`), and pipeline integration.

---

## Reference docs

| File | Purpose |
|---|---|
| [`SETUP.md`](SETUP.md) | First-time install, M: drive layout, common operations, troubleshooting |
| [`SLIDE_MAPPING.md`](SLIDE_MAPPING.md) | Master slide spec (slide IDs &rarr; layouts &rarr; headlines) |
| [`SLIDE_DESIGN.md`](SLIDE_DESIGN.md) | Design system &mdash; colors, typography, chart conventions |
| [`05_UI/UI-OVERVIEW.md`](05_UI/UI-OVERVIEW.md) | Developer-facing map of every UI screen and component |
| [`docs/manifest-schema.md`](docs/manifest-schema.md) | Schema reference for `run_manifest.json` |

---

## Tech stack

- Python 3.12
- FastAPI + Uvicorn (web server, single-page UI)
- Pandas + NumPy (data)
- Matplotlib (charts)
- python-pptx (PowerPoint generation)
- openpyxl / xlsxwriter (Excel I/O)
- pyarrow (Parquet cache for TXN)
- loguru (logging)
- pytest (test suite)
- CSI brand: orange `#F15D22`, navy `#1A1A1A`, Montserrat font, Space Mono for numerics
