# Velocity UI — Component & Screen Reference

A developer-facing map of every screen, what each component does, where it lives in the code, and which APIs it talks to. Use this to brief a designer or developer when proposing changes to the operator UI.

**Stack:** FastAPI (`05_UI/app.py`) serves a single-page static `index.html` with vanilla JS. No build step. State is fetched from `/api/*` endpoints and polled where long-running.

**Design tokens** (defined as CSS vars at top of `index.html`):
| Token | Value | Use |
|---|---|---|
| `--bg` | `#EFEFEF` | Page background |
| `--card` | `#ffffff` | Card surfaces |
| `--border` | `#d6d6d6` | Card borders, dividers |
| `--text` | `#222` | Body text |
| `--muted` | `#9F9EA2` | Labels, secondary text |
| `--dark` | `#00274C` | Header bar, dark CTAs (canonical CSI navy, per `shared/brand.py`) |
| `--accent` | `#F15D22` | Primary action / brand orange |
| `--accent-light` | `#fef0e8` | Soft accent fills |
| `--accent-dark` | `#d14e1a` | Hover state on accent |
| `--green` | (inline `#2A8B3E`) | Success states |

**Type:** Montserrat (UI body / titles), Space Mono (numerics, IDs, log).

---

## Header (`<header>`)
Persistent across all pages.

| Element | ID / class | Function |
|---|---|---|
| Brand | `.h-brand` | "Velocity" label, top-left |
| Tab nav | `.h-nav li` | Six top-level pages (Dashboard / Format / Generate / Results / History / Schedules). Active tab gets `.on`. Click invokes `showPage(name)`. |
| User | `.h-user` | Logged-in operator (currently hardcoded to `james.gilmore`) |

---

## 1. Dashboard (`#page-dashboard`)
Landing page. Pipeline overview.

| Component | ID | Function | Data source |
|---|---|---|---|
| KPI tiles | `.grid-4` of `.kpi-card` | At-a-glance counts: clients, runs this month, slides generated, recent failure count | `/api/stats` |
| Recent runs table | `.recent-table` | Last N runs across all CSMs with status badges | `/api/recent` |
| Reports by CSM | `#csmChart` card | Distribution of runs per CSM (chart) | derived from `/api/recent` |

---

## 2. Format (`#page-format`)
Step 1 of the pipeline — extracts and formats raw ODD ZIPs from a CSM's data dump folder into the `02-Data-Ready for Analysis/` layout.

| Component | ID | Function | API |
|---|---|---|---|
| CSM selector | `#fCsmSel` | Picks which CSM's source folder to scan | `/api/csms` |
| Period selector | `#fMonthSel` | Picks the YYYY.MM month to format | `/api/months?source=raw` |
| Client filter | `#fClientSel` (if present) | Optional: format a single client only | (frontend) |
| Run button | `.btn` | Starts the format pipeline | `POST /api/format` |
| Progress card | (legacy linear bar + log) | Streams progress | `GET /api/run/{run_id}` (polled 1s) |

**Note:** Format tab still uses the **old** linear progress bar + raw log. The new checklist+completion-card pattern is currently only on the Generate tab. Replicating it here is a tracked follow-up.

---

## 3. Generate (`#page-generate`)
**Primary operator surface.** Pick client + product, run end-to-end analysis, get a PowerPoint.

### Step 1 — Client picker
| Component | ID | Function | API |
|---|---|---|---|
| CSM selector | `#gCsmSel` | Filters client list to that CSM. `onchange` → `refreshGenClients()` | `/api/csms` |
| Period selector | `#gMonthSel` | Filters by month. `onchange` → `refreshGenClients()` | `/api/months?source=all` |
| Client selector | `#gClientSel` | Lists clients found in any pipeline stage (raw / formatted / completed) for the chosen CSM+month. `onchange` → `updateGenClientFromAPI()` | `/api/clients?csm=X&month=Y` |

**Client filtering logic** (`refreshGenClients`):
- Posts CSM + month to `/api/clients`
- Backend unions client IDs from: raw dumps, formatted folder, completed-analysis folder
- Clients in folders but missing from `clients_config.json` surface as `"Client <id> (not in config)"`
- Empty result → `"No clients for this CSM / period"`

### Client banner + config panel
After client selection, a banner shows the client's name + ID and an 8-cell config grid:

| Cell | ID | Field |
|---|---|---|
| IC Rate | `#cdIcRate` | Interchange rate, % |
| NSF/OD Fee | `#cdNsfFee` | NSF/overdraft fee dollar amount |
| Eligible Stat Codes | `#cdStatCodes` | Account status codes counted as active |
| Eligible Product Codes | `#cdProdCodes` | Product codes counted as eligible |
| Reg E Opt-In Code | `#cdRegeOptIn` | Value(s) meaning "opted in" |
| Eligible Mail Code | `#cdMailCode` | Mail-eligibility code |
| Branch Mapping | `#cdBranch` | Count of mapped branches |
| Client ID | `#cdClientId` | Echo of selected client |

Populated by `_applyConfig(cfg)` from `/api/clients` payload.

### Step 2 — Product picker + Run
| Component | ID | Function |
|---|---|---|
| Run bar | `.run-bar` with `#gRunWhat` / `#gRunMeta` | Inline "what will run" summary updated by `updRunBar()` |
| Run button | `#genRunBtn` | Starts the run. Click → `smartRunGen()` → `runGenReal()` |
| Product cards | `.p-card` × 4 | ARS Full Suite / Transaction / Combined / Deposits. Click → `selectProd(name)` |
| Modules panel | `.modules-panel` | Expandable list of modules included in the selected product |

### Step 3 — Running view (the rebuilt section)

The progress card (`#gProg`) has two states:

#### Running state (`#gRunView`)
| Element | ID | Function |
|---|---|---|
| Headline | `#gRunTitle` | Plain-English status ("Analyzing mailer effectiveness…") |
| Subtitle | `#gRunSub` | Context line ("Working through 25 analytics reports") |
| Elapsed clock | `#gElapsed` | Live `M:SS` timer, updates every 500ms |
| Stage checklist | `#gStages` (5× `li.stage`) | See below |
| Technical log | `<details>` → `#gProgLog` | Collapsed by default. Full raw log, color-coded |

**The 5 stages** (`li.stage[data-stage="..."]`):
1. `read` — Read your data (Step 1 formatting output picked up)
2. `prep` — Prepare analyses (pipeline setup + retrieve_data)
3. `analyze` — Run analytics (the long one; has a nested sub-progress bar `#gAnalyzeBar` + meta `#gAnalyzeMeta`)
4. `deck` — Build PowerPoint deck (generate_output starts → deck built)
5. `finalize` — Save and deliver files (Step 2 complete)

**Stage states** (`data-state` attribute):
- `(none)` — pending (○ outline icon, grey label)
- `active` — running (orange filled icon, pulse animation, sub-progress visible if analyze)
- `done` — completed (green ✓ icon, elapsed time shown on right)
- `error` — failed (red ! icon)

**State derivation** (frontend-only, in `runGenReal()`):
- `_classifyStage(line)` — maps backend log lines to stage transitions
- `_parseModuleProgress(line)` — extracts `Module N/M: module_id`
- `MODULE_THEME` map — `module_id.prefix` → friendly theme name shown to operator
  - `overview` → Account overview
  - `dctr` → Debit performance
  - `rege` → Reg E compliance
  - `value` → Value to members
  - `attrition` → At-risk accounts
  - `mailer` → Mailer effectiveness
  - `insights` → Strategic insights

#### Completion state (`#gDoneView`)
Replaces the running view when the run finishes.

| Element | ID | Function |
|---|---|---|
| Status check | `.done-check` | Big circle, green ✓ on success, orange ! on partial, red ✕ on error |
| Title | `#gDoneTitle` | "Report ready — <client>" / "Report ready (with warnings)" / "Run did not complete" |
| Subtitle | `#gDoneSub` | "Generated in N:NN" |
| Status tiles | `#gDoneStats` | Color-coded counts: |
| · Slides succeeded | `.done-stat.success` | Green left border, green value with ✓ |
| · No chart data | `.done-stat.warn` | Orange left border, orange value with ⚠ |
| · Slides failed | `.done-stat.error` | Red left border, red value with ✕ |
| · Excel sheets | `.done-stat` (neutral) | Sheet count |
| · Total time | `.done-stat` (neutral) | Elapsed |
| Warnings panel | `#gDoneWarnings` | Per-failure breakdown (slide ID + translated reason) + file-lock notice |
| Actions | `#gDoneActions` | `Open downloads` (primary) + `Run another report` (secondary) |

**Status determination:** `success` if all OK, `partial` if any soft-failures or no-chart slides, `error` if pipeline itself failed.

**Error translation** (`_translateError(raw)`) — maps known errors to plain English:
- `out-of-bounds` → "Data range issue"
- `Need 2+ months` → "Not enough months of data"
- `No Product Code column` → "Missing Product Code column"
- etc.

### Step 4 — Downloads
After run completes, `#gDl` populates with download cards (PowerPoint, Excel, run report). Driven by `loadDownloads(csm, month, clientId)` → `GET /api/outputs/{csm}/{month}/{client_id}`.

---

## 4. Results (`#page-results`)
Slide gallery for browsing completed analysis output without opening PowerPoint.

| Component | ID | Function | API |
|---|---|---|---|
| Client selector | `#rClientSel` | Lists clients with completed analysis | `/api/results/clients` |
| Section nav | `#resultsSidebar` / `#resultsSections` | Left rail listing slide sections | derived |
| Slide viewer | `#rSlideContainer` | Main viewport with prev/next, double-click for lightbox | `/api/results/charts/{csm}/{month}/{client}` |

---

## 5. History (`#page-history`)
All runs across all CSMs in a sortable table.

| Component | ID | Function | API |
|---|---|---|---|
| Filters | (top of page) | CSM / month / product / status filters | (frontend) |
| Runs table | `.recent-table` (history variant) | One row per run | `/api/recent?limit=N` |

---

## 6. Schedules (`#page-schedules`)
Set up recurring monthly auto-runs.

| Component | ID | Function | API |
|---|---|---|---|
| CSM selector | `#schedCsm` | Picks CSM for scheduled run | `/api/csms` |
| Client selector | `#schedClient` | Picks client to schedule | `/api/clients` |
| Day-of-month | `#schedDay` | Day each month to auto-run | (frontend) |
| Extras | inline checkboxes | Optional add-ons (e.g. include TXN) | (frontend) |
| Schedule table | `.recent-table` (schedules variant) | Active recurring schedules | `/api/schedules` |

---

## Backend API surface (`05_UI/app.py`)

All endpoints are FastAPI, JSON over HTTP. The frontend polls long-running endpoints every ~1 second.

### Data / config
- `GET /api/csms` — CSM names from `ars_config.json`
- `GET /api/months?source=raw|formatted|all` — Available months
- `GET /api/clients?csm=&month=` — Client list (union of raw / formatted / completed when filtered)
- `GET /api/products` — Product definitions
- `GET /api/files/{csm}/{month}/{client_id}` — Per-client file availability

### Runs
- `POST /api/format` — Kick off formatting; returns `{run_id}`
- `POST /api/run?csm=&month=&client_id=&product=` — Kick off analysis; returns `{run_id}`
- `GET /api/run/{run_id}` — Poll: returns `{status, progress, current_step, log: [...]}`. Status: `running` / `complete` / `error`

### Outputs
- `GET /api/outputs/{csm}/{month}/{client_id}` — List of produced files (PPTX, XLSX, etc.)
- `GET /api/results/clients` — Clients that have completed analysis (for Results tab)
- `GET /api/results/charts/{csm}/{month}/{client_id}` — Chart PNGs for the Results gallery
- `GET /api/recent` — Recent runs across all CSMs
- `GET /api/stats` — Dashboard KPIs

### Path constants
- `READY_FOR_ANALYSIS` → `M:\ARS\00_Formatting\02-Data-Ready for Analysis`
- `COMPLETED_ANALYSIS` → `M:\ARS\01_Analysis\01_Completed_Analysis`
- `PRESENTATIONS_BASE` → `M:\ARS\02_Presentations`
- Raw CSM source paths come from `03_Config/ars_config.json → csm_sources.sources.<CSM>`

---

## Conventions & gotchas

- **CSM-to-client membership is folder-based** — there's no master mapping. Client appears in dropdown if their folder exists in any of: raw dumps / formatted output / completed analysis. See issue #123 for the design rationale.
- **No build step.** Edit `index.html` and reload (Ctrl+Shift+R) — Python server serves it as static.
- **Server restart needed** for `app.py` changes (uvicorn dev-reload is not enabled).
- **Style scope:** all CSS is in a single `<style>` block at the top of `index.html`. No CSS Modules / Tailwind / framework. Class naming is BEM-ish but loose (`done-stat`, `done-stat-value`, `stage-icon`).
- **The technical log is preserved** behind the `<details>` disclosure. It is the source of truth for debugging — never remove it.
- **All state derivation for the Run view happens client-side** by parsing the log strings the backend already produces. If a backend log line format changes, update the regex parsers in `runGenReal()`.

---

## Files

- `05_UI/app.py` — FastAPI backend
- `05_UI/index.html` — Single-page UI (HTML + CSS + JS, ~2100 lines)
- `05_UI/UI-OVERVIEW.md` — This file
- `Start Here.bat` — Operator launcher (Windows; starts `app.py`, waits for port, opens browser)
