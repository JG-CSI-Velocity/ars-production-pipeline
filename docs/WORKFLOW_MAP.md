# RPE-Workflow — Pipeline Visual Map

End-to-end map of the Velocity Pipeline: from raw ODD ZIPs in a CSM's data dump folder to a finished PowerPoint deck. All three steps are driven by the UI at `05_UI/`; the `run.py` entrypoints are the same code paths, exposed for batch/debug.

---

## Visual map

```
                     ┌──────────────────────────────────────────┐
                     │   OPERATOR (CSM)  —  Browser at :8000    │
                     │   05_UI/index.html  ←→  05_UI/app.py     │
                     └──────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┼────────────────────────────┐
        ▼                              ▼                            ▼
   ┌─────────┐                    ┌─────────┐                  ┌─────────┐
   │ STEP 1  │                    │ STEP 2  │                  │ STEP 3  │
   │ FORMAT  │  ───────────────►  │ ANALYZE │  ──────────────► │  DECK   │
   └─────────┘                    └─────────┘                  └─────────┘

 INPUT                          INPUT                          INPUT
 ─────                          ─────                          ─────
 Raw ODD ZIPs in                Formatted ODD .xlsx            Completed analysis
 M:\<CSM>\OD Data Dumps\        + (optional) TXN CSVs          (Excel + chart PNGs
 <period>\<client>_ODDD.zip     + deferred / workbook            + run_manifest.json)
                                                                + SLIDE_MANIFEST.xlsx

 SCRIPT                         SCRIPT                         SCRIPT
 ──────                         ──────                         ──────
 00_Formatting/run.py           01_Analysis/run.py             02_Presentations/
   └ pipeline/retrieve.py         └ pipeline/runner.py           html_review/builder.py
   └ pipeline/format.py           └ pipeline/steps/              (called by
   └ shared/format_odd.py             load → scan → analyze       01_Analysis/.../output/
                                      → generate → format         deck builder)

 WHAT IT DOES                   WHAT IT DOES                   WHAT IT DOES
 ────────────                   ────────────                   ────────────
 1. Unzip raw ODD               Runs 25 ARS modules and/or     Reads SLIDE_MANIFEST
 2. Convert .csv → .xlsx        22 TXN sections registered     (Keep? Y / A / N),
 3. 7-step ODD format           in analytics/registry.py.      stitches charts +
 4. Stage TXN files             Each module:                   action titles into
 5. Pull deferred-rev rows        - reads formatted ODD         python-pptx slides.
 6. Pull R: workbook              - builds a DataFrame
                                  - writes chart PNG(s)        Routes:
                                  - writes Excel sheet          Y → main deck
                                  - records status in           A → _aux_deck
                                    run_manifest.json           N → dropped

 OUTPUT                         OUTPUT                         OUTPUT
 ──────                         ──────                         ──────
 00_Formatting/                 01_Analysis/                   02_Presentations/
 02-Data-Ready for Analysis/    01_Completed_Analysis/         <CSM>/<period>/<client>/
   <CSM>/<period>/<client>/       <CSM>/<period>/<client>/       <id>_<month>_
     <id>_ODD_formatted.xlsx        charts/*.png                   ars_deck.pptx
     trans/*.csv  (if TXN)          analysis_workbook.xlsx         ars_aux_deck.pptx
     deferred_revenue.xlsx          run_manifest.json              review_summary.xlsx
     workbook.xlsx                  run_scorecard.md               quality_report.txt
                                    competition_diagnostic.txt     meta.json
```

---

## Step 1 — FORMAT

*Format tab in the UI.*

- **Script:** `00_Formatting/run.py` → `pipeline/retrieve.py` (find + unzip) → `pipeline/format.py` → `shared/format_odd.py` (7-step transform)
- **API:** `POST /api/format` in `05_UI/app.py`
- **Analysis:** Mechanical — no metrics. Normalizes columns, coerces types, splits personal/business, applies stat-code and product-code lookups from `03_Config/clients_config.json`, optionally gathers TXN / deferred / workbook side files.
- **Output:** `00_Formatting/02-Data-Ready for Analysis/<CSM>/<period>/<client>/<id>_ODD_formatted.xlsx` (+ `trans/`, `deferred_revenue.xlsx`, `workbook.xlsx` if requested). This file is the contract for Step 2.

---

## Step 2 — ANALYZE

*Generate tab — "Run analytics" stage.*

- **Script:** `01_Analysis/run.py` → `00-Scripts/pipeline/runner.py` orchestrates `pipeline/steps/{load, scan, subsets, analyze, generate, format}.py`
- **Module registry:** `00-Scripts/analytics/registry.py` enumerates 25 ARS modules + (per `--product`) 22 TXN sections wrapped by `analytics/txn_wrapper.py`
- **API:** `POST /api/generate` in `app.py` streams the 5-stage checklist
- **Analysis (ARS, 25 modules):** `overview` (3) · `dctr` debit-card take-rate (5) · `rege` Reg-E opt-in (3) · `attrition` (3) · `mailer` campaign (5) · `value` revenue (1) · `insights` synthesis (5). Each rate anchors to one of the 4 denominator layers (`Eligible / Eligible Personal / Eligible Personal w/Debit / Eligible Business / Open`).
- **Analysis (TXN sections, when `--product=txn` or `combined`):** `txn_setup` shared loaders + ~22 sections (`general, merchant, mcc_code, competition, financial_services, ics_acquisition, campaign, branch_txn, transaction_type, product, attrition_txn, balance, interchange, rege_overdraft, payroll, relationship, segment_evolution, retention, engagement, executive`, etc.).
- **Output:** `01_Analysis/01_Completed_Analysis/<CSM>/<period>/<client>/`
  - `charts/*.png` — every chart for the deck
  - `analysis_workbook.xlsx` — every table behind every chart
  - `run_manifest.json` — per-module status + suggested fixes (schema in `docs/manifest-schema.md`)
  - `run_scorecard.md` — one-page pass/fail summary
  - `competition_diagnostic.txt` — category counts, BNPL audit, unmatched financial keywords

---

## Step 3 — BUILD DECK

*Generate tab — "Build PowerPoint" stage.*

- **Script:** Deck builder in `01_Analysis/00-Scripts/output/` (action-title populator + python-pptx layouts); HTML preview by `02_Presentations/html_review/builder.py`
- **Inputs it reads:**
  - Charts + workbook from Step 2
  - `SLIDE_MANIFEST.xlsx` (operator's `Keep? Y/A/N` column)
  - `docs/action_title_templates.md` (28 reusable headlines)
  - `SLIDE_DESIGN.md` (palette, typography, callouts)
- **Analysis:** No new math. Maps each chart → slide layout → action-title template, fills `ctx.results` placeholders, splits `Y` vs `A` into two decks, drops `N`.
- **Output:** `02_Presentations/<CSM>/<period>/<client>/`
  - `<id>_<month>_ars_deck.pptx` (or `_txn_deck.pptx` / `_combined_deck.pptx`)
  - `<id>_<month>_ars_aux_deck.pptx` (appendix, if any `A`s)
  - `<id>_<month>_review_summary.xlsx` (4-sheet CSM review)
  - `<id>_<month>_quality_report.txt` (10 automated checks)
  - `<id>_<month>_meta.json` (audit trail)
  - Cross-sell candidate CSVs in `Actionable Lists for Clients/<client>_<name>/cross_sell_lists/`

---

## Cross-cutting

- **Driver:** `05_UI/app.py` is the single orchestrator. Every step above also runs from `run.py` on the CLI for batch/debug, but operators only ever click buttons.
- **Per-CSM membership:** no master mapping; a client "belongs" to a CSM by the folder their files sit in at any of the three stages (raw / formatted / completed). `app.py` unions all three for the dropdown.
- **Products** (`--product` flag): `ARS Full Suite` (default, ODD only) · `Transaction` · `Combined` · `Deposits`. Each emits a distinctly-named deck so runs don't clobber each other.
