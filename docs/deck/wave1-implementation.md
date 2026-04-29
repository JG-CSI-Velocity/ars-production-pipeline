# TXN Deck Restructure — Wave 1 Implementation Notes

**Branch:** `feature/txn-deck-restructure` (off `main`)
**Date:** 2026-04-28
**Spec source:** `docs/deck/txn-deck-review.md` (Proof doc `8aj75wzq`) + `docs/deck/txn-followups.md`

---

## What Wave 1 ships

This is a **plumbing-only pilot.** It establishes infrastructure that later waves populate. The 339-slide TXN deck output should be **unchanged** from before, except:
- Slides whose underlying data is empty are silently dropped (G6).
- Run report logs how many slides were dropped.
- A second `*_aux_deck.pptx` is produced **only if** `ctx.auxiliary_slide_ids` is populated (Wave 1 ships it empty, so no aux deck appears yet).

### G6 — Drop-if-empty
- File: `01_Analysis/00-Scripts/pipeline/steps/generate.py`
- New helper `_drop_empty_slides(ctx)` runs at the top of `step_generate`.
- Criterion: `success=True` AND no chart file AND no Excel data → drop.
- Logs: `G6 drop-if-empty: skipped N slide(s) with empty data: <ids>`.
- Effect on this run: **Section 8 (ICS Acquisition, 0 charts) silently skipped.** No deck output regression.

### G7 — Auxiliary deck plumbing
- New context field: `PipelineContext.auxiliary_slide_ids: set[str]` (in `01_Analysis/00-Scripts/pipeline/context.py`).
- New helper: `_build_aux_deck(ctx)` in `generate.py`.
- New filename branch in `deck_builder.build_deck`: when `ctx._aux_build == True`, output is `<client>_<month>_<product>_aux_deck.pptx`.
- Wave 1 ships `auxiliary_slide_ids` empty: **no aux deck is produced today.** To test the wiring, set the field manually in code or add a manifest reader (Wave 3).

### File rename
- `01_Analysis/00-Scripts/analytics/competition/17_total_spend.py` → `17_engagement_depth.py` (filename was misleading; script header literally says "COMPETITOR ENGAGEMENT DEPTH").
- Numeric prefix `17_` preserved → no impact on the wrapper's sorted script discovery.

---

## What is **NOT** done in Wave 1

Everything below has been specced in the review doc but is **not implemented** yet.

### Engine / global rules (Wave 2 candidates)
- **G1 — TXN-only preamble title text.** Still says "Account Revenue Solution". Decision pending (e.g., "Transaction Insights Report").
- **G2 — Divider font standardization.** Mailer Summaries (P10) font size should win across all dividers. Layout-master fix in `.pptx` template.
- **G3 — Mode-aware preamble.** `_build_preamble_slides()` does not branch on TXN-only vs ARS+TXN. TXN-only run still gets all 13 ARS preamble slides.
- **G4 — Slide budget target.** No enforcement; budget is informational.
- **G5 — Combo CONDENSE policy** for response slides. Likely subsumed by G9; not implemented.
- **G8 — Layout title/subtitle overlap.** Layout-master fix in `.pptx` template.

### Section dashboard combos (Wave 3)
- **G9 — Section dashboard.** No combo builder yet. Sections 1–5, 10–14, 17 all spec'd to fold `02_kpi + 03_bar + 04_donut` into one slide; today they still emit three slides each.
- **G10 — Concentration / trend → aux** routing. No automatic routing; today these slides still appear in main deck.
- **G11 — Cross-tab keep.** Default behavior matches today; no aux routing exists yet.

### Section 6 (Competition) specials (Wave 4)
None of the following are implemented:
- A1 combo: `02_competitor_detection_01` + `07_kpi_dashboard_01`
- A2 combo: `02_competitor_detection_02` + `02_competitor_detection_03`
- A3 combo: `08_top_competitors_bar` + `09_category_donut` + `10_biz_vs_personal`
- A5 combo: `13_threat_quadrant` + `16_opportunity` (winback)
- A9 combo: `18_competition_aggregate_01` + `_02` side-by-side
- `12_bubble_chart` axis scaling fix
- `13_threat_quadrant` axis scaling fix
- `24_segment_heatmap` 4-cell collapse to one slide
- `25_at_risk_accounts` y-axis label fix (currently positional `Account #N`) + redesign
- `26_spend_scatter` axis scaling fix
- `27_recency_analysis` x-axis label overlap fix
- `28_spend_vs_frequency` axis scaling fix
- `29_wallet_share` conditional filter (top competitor per segment, only if in top 10)

### Per-section chart fixes (Wave 5)
- Section 1: `25_time_to_first_txn` (3-way splits), `24_account_age_bar` (overlay), `26/27/30` (improvement triage).
- Section 2: `09_merchant_lifecycle` (label fix). `08_merchant_volatility` script-failure triage.
- Section 3: `12_mcc_seasonal` (calc), `14_mcc_spend_profile` (data + scaling).
- Sections 4 & 5: `09_*_lifecycle` × 2 (label QA).
- Section 7: `01_config` / `02_identify` — investigate, likely strip from manifest.
- Section 17: `06_payroll_processors`, `10_action_summary` script-failure triage.

### Spec gaps (still TBD in review doc)
- **G1** TXN-only title text.
- **G4** TXN-only slide budget target.
- **`25_at_risk_accounts` label fix:** option (a) real account ID visible, or (b) synthetic + companion CSV export.
- **`24_segment_heatmap` implementation:** small-multiples vs unified grid.
- **Section 9 (Campaign Analysis, 76 slides)** — entire block-level review pending.
- **Section 7** — `01_config` / `02_identify` keep / strip decision.
- **Section 22** — likely under-built; expansion pass deferred.

---

## How to verify Wave 1 on the work PC

1. Pull this branch (or a ZIP of this branch) onto `M:\ARS\`.
2. Run a normal TXN pipeline:
   ```bat
   cd M:\ARS\01_Analysis
   python run.py --month 2026.04 --csm "1776" --client 1776 --product txn
   ```
3. Expected diff vs prior run:
   - Same `*_txn_deck.pptx` output (same slide count, ~339).
   - **No** `*_txn_aux_deck.pptx` file (aux routing is empty in Wave 1).
   - Log line `G6 drop-if-empty: skipped N slide(s)` — likely 0 or a small number depending on data.
   - Section 8 (ICS Acquisition) gone from the deck if it produced no charts.
4. Optional aux-deck smoke test: temporarily edit `00-Scripts/pipeline/steps/generate.py` to populate `ctx.auxiliary_slide_ids` with one or two known slide IDs, re-run, confirm a `*_aux_deck.pptx` appears containing only those slides.

If the run works, we proceed to Wave 2.
