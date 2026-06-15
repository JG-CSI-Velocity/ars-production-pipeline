---
name: ars-deck
description: >-
  Build, review, and QA the monthly ARS analysis PowerPoint produced by the
  RPE-Workflow / ars-production-pipeline (deck_builder, deck_qa, slide_specs,
  section consolidation). Use this whenever the user works with an ARS deck —
  the 1759/1615/etc. results PowerPoint, the monthly CSM deck, mailer / attrition
  / DCTR / Reg E slides, slide consolidation or the two-slide mailer blocks,
  deck_qa findings, slide_specs / callout templates — or asks to review, fix,
  build, audit, or explain an ARS presentation (wrong slide counts, leaked
  {tokens}, overflowing text, charts overlapping titles) — OR wants to build an
  ARS deck directly from the analysis Excel workbook
  ({client}_{month}_analysis.xlsx) without running the full pipeline. Reach for
  this BEFORE hand-editing a .pptx or trusting a committed deck artifact: ARS
  decks are generated from data, and the cardinal rule is to verify against the
  current code/data, not a stale file.
---

# ARS Deck — Build & Review

The ARS deck is the monthly analysis PowerPoint a CSM hands to a CSI/Velocity
client. It is **generated from code**, never authored by hand. Your job is
either to (a) build/modify how it's generated, or (b) review a produced deck and
find what's wrong. This skill covers both, plus the one mistake that wastes the
most time.

`csi-powerpoint` is the sibling skill for brand/template compliance (colors,
fonts, the approved CSI template). This skill owns the **pipeline mechanics**:
how slides are produced, consolidated, and QA'd. Use both together when brand
polish and pipeline correctness both matter.

## Where everything lives

| Concern | Path |
|---|---|
| Deck assembly | `01_Analysis/00-Scripts/output/deck_builder.py` (`build_deck`, `DeckBuilder`, `_consolidate*`) |
| QA gate | `01_Analysis/00-Scripts/output/deck_qa.py` (`audit_deck`) |
| Per-slide callout templates | `01_Analysis/00-Scripts/output/slide_spec.py` + `docs/slide_specs/<section>.yml` |
| Analysis modules (produce slides) | `01_Analysis/00-Scripts/analytics/<section>/` |
| Pipeline steps | `01_Analysis/00-Scripts/pipeline/steps/{analyze,generate}.py` |
| **Analysis Excel (the data)** | `{client}_{month}[_txn]_analysis.xlsx` — one tab per analysis |
| Deck shape (operator-editable) | `SLIDE_MANIFEST.xlsx` + `{client}_{month}_run_report.json` |
| Run entry | `01_Analysis/run.py` (sets up the `ars_analysis` import alias) |
| Operator UI (the product) | `05_UI/app.py` + `05_UI/index.html` |

Helper scripts bundled with this skill (run them with the repo's venv):
- `scripts/run_deck_qa.py <deck.pptx>` — run the QA gate on any pptx
- `scripts/extract_slides.py <deck.pptx> [--slides 33-43]` — pull per-slide text + chart images so you can actually *see* the deck
- `scripts/check_consolidation.py` — show what **current code** does to slides (the stale-deck test)

## The cardinal rule: verify against code, not the artifact

A committed `*.pptx` is a snapshot from whenever it was last built — it can be
many fixes out of date. The single most expensive mistake on this project is
diagnosing a deck file and "fixing" bugs that the current code already fixes.

Symptoms you are looking at a **stale deck**, not a code bug:
- The deck has problems (leaked `{tokens}`, 167 slides, un-merged 2×1s) but the
  fixes for exactly those problems are already in the git log.
- The deck's mtime / its commit predates the relevant fix commits.

**Before changing any code in response to a bad deck, prove the bug still exists
in current code.** The consolidation and spec functions are pure — exercise them
directly:

```bash
python .claude/skills/ars-deck/scripts/check_consolidation.py
```

This runs `_consolidate_mailer`, the attrition merges, and `get_spec` against
realistic synthetic slide_ids and prints what *current code* produces. If it
shows a tight, correct deck, the file is stale — the fix is **rebuild**, not edit.
(See `references/lessons.md` for the full post-mortem of the time this bit us.)

## Data source: the analysis Excel

The numbers on every slide come from the **analysis Excel workbook**, not from
the ODD directly and not from anything hand-typed. The `generate` step produces,
in this order: `drop-empty → run_report.json → {client}_{month}_analysis.xlsx →
deck (main + aux)`. Every slide's data is a tab in that workbook (written from
each `AnalysisResult.excel_data`).

Consequences for this skill:
- **The workbook is the source of truth for slide figures.** When a number on a
  slide looks wrong, open the matching tab in `{client}_{month}_analysis.xlsx`
  and compare — a slide/Excel mismatch is a rendering bug; a wrong number in
  *both* is an analysis bug (fix the analytics module, not the deck).
- **The deck can be rebuilt deck-only, from the Excel/report.** After the
  operator edits `SLIDE_MANIFEST.xlsx` (the in-UI "Deck Shape editor"),
  `POST /api/rebuild_deck` → `rebuild_deck_from_report` reconstructs the PPTX
  from `run_report.json` + cached chart PNGs **without re-running analysis**.
  This is the fast path for shape/ordering changes — minutes, not the full run.
- So "fix the deck" splits two ways: **data/number** problems live in the
  analytics module (and show up in the Excel); **shape/layout/consolidation**
  problems live in `deck_builder` + the manifest. Diagnose which before editing.

## Reviewing a produced deck

Run these in order. Stop and report if step 1 or 3 already explains the problem.

### 1. Run the QA gate
```bash
python .claude/skills/ars-deck/scripts/run_deck_qa.py <deck.pptx>
```
`deck_qa` is deliberately conservative — it's tuned so the known-good reference
decks pass clean, so anything it flags is real. It catches:
- `leaked_token` (CRITICAL) — an unrendered `{overall_rate:.1f}` etc. on a slide
- `slide_count` (MAJOR) — >60 slides means consolidation/windowing didn't fire
- `text_overflow` (MAJOR) — too many chars for the box (the mailer commentary bug)
- `file_size`, empty/title-only slides

Findings are **advisory data, not law** — some blanks are intentional (the
operator hand-fills P04/P05/P06 and the Agenda). `deck_qa` whitelists those.

### 2. Actually look at the slides
deck_qa can't see a chart with the wrong bars or a legend on the data. LibreOffice
is usually not installed, so extract the embedded chart images and read them:
```bash
python .claude/skills/ars-deck/scripts/extract_slides.py <deck.pptx> --slides 33-43
```
This writes one PNG per chart plus a text inventory (titles, picture counts) to
`/tmp/ars_slides/`. Read the PNGs to judge the actual visuals. Lead with the
section the user named (attrition, mailer, Reg E…).

If a *number* looks wrong (not the layout), open the matching tab in
`{client}_{month}_analysis.xlsx` and compare. Slide ≠ Excel → rendering bug in
the deck. Slide == Excel but both wrong → analysis bug; fix the analytics module
(the deck is faithfully showing bad data).

### 3. Decide: stale deck or real bug?
Run `check_consolidation.py` (above) and compare the deck's commit time to the
fix commits (`git log --oneline -- 01_Analysis/00-Scripts/output 01_Analysis/00-Scripts/analytics`).
- **Stale** → recommend a rebuild; do **not** edit consolidation code.
- **Real** → reproduce it as a failing unit test on the pure function first
  (synthetic results with real slide_id patterns), then fix until green. Real
  data has more mailer waves than the synthetic fixtures, so multi-wave behavior
  is where regressions hide — test with ~22 waves, not 2.

### 4. Check the owner conventions
Read `references/conventions.md` and confirm the deck honors the locked owner
decisions (two-slide mailer blocks, Reg E funnel style, L12M denominators, the
intentionally-blank exec slides). These are taste calls the owner already made —
don't relitigate them, just verify them.

## Building or modifying a deck

The deck is assembled in `build_deck(ctx)` from each section's `AnalysisResult`s,
in `SECTION_ORDER` (an SCR narrative arc):

```
overview → dctr → rege → attrition → mailer → transaction → ics → value → insights
```

Each section's results flow through consolidation before becoming slides:
- **Merges** — pairs like attrition `A9.1 + A9.12 → "Account Closures: Annual &
  Monthly Trend"` become one 2×1 slide (`ATTRITION_MERGES`, `OVERVIEW_MERGES`).
- **Appendix routing** — low-priority slide_ids (`*_APPENDIX_IDS`) move to the
  appendix instead of the main body.
- **Mailer special case** — `_consolidate_mailer` keeps each wave as exactly two
  slides (A13 summary + A16.7 combo), drops the separate A12 swipes/spend, keeps
  only the most-recent `MAIN_MAILER_MONTHS` (6) waves in the main deck, and sends
  older waves to a separate `*_Mailer_Performance.pptx` ancillary deck.

To change a slide:
1. Edit the analytics module in `analytics/<section>/` that emits the
   `AnalysisResult` (its `slide_id`, `slide_type`, chart, bullets, KPIs).
2. If it's a merge/drop/appendix decision, edit the matching constant in
   `deck_builder.py` (`*_MERGES`, `*_APPENDIX_IDS`, `MAIN_MAILER_MONTHS`).
3. If it has a KPI callout headline, edit `docs/slide_specs/<section>.yml`. The
   `slide_id` must match exactly; template keys like `A13.{month}` only match
   real month tokens (`Apr26`), never `A13.5`/`A13.Agg` — keep that capture
   tight or non-month slides drag in unrendered `{tokens}`.
4. **If you drop a slide from the deck, also gate its render.** Slides are
   rendered during the *analysis* step; the deck step only chooses what to keep.
   Dropping a slide from `deck_builder` without gating its chart render means you
   still pay the (often minutes-per-wave) render cost for a slide nobody sees.

Two laws that override convenience:
- **UI-first** (`CLAUDE.md`): every diagnostic/fix/run must be operable from
  `05_UI`. Never tell the operator to run a notebook, edit a `.py`, or tail a
  log. Surface new behavior as a button + endpoint + display.
- **Denominator framework** (4-layer law): every rate anchors to Eligible /
  Eligible Personal / Eligible Business / Open — no bespoke filters. Mailer
  response anchors to the Eligible Mailable subset within Eligible.

## Experimental: build the deck directly from the analysis Excel

The analysis Excel already holds every slide's data — one tab per
`{slide_id}_{sheet}` (e.g. `A13.Apr26_Response`, `A9.1_Closures`), plus a
Summary tab. The numbers are already computed. So you don't always need the full
Python pipeline to produce a deck: **you know the ARS structure, so read the
workbook and assemble the deck directly.** This is faster to iterate and is a
legitimate alternative for drafts, restructuring experiments, and table/KPI-heavy
slides. Treat it as a complement to the pipeline, not a replacement — the
pipeline remains the source of truth for full-fidelity, branded matplotlib charts.

When the user hands you `{client}_{month}_analysis.xlsx` (or asks for a deck "from
the Excel"), do this:

1. **Read the workbook.** `pandas.read_excel(path, sheet_name=None)` → a dict of
   `{tab: DataFrame}`. Start at the Summary tab to orient. The `slide_id` prefix
   tells you the section (A1–A3 overview, A4–A8 DCTR, A8.x Reg E, A9.x attrition,
   A11 value, A12–A17 mailer, insights). The `xlsx` skill helps for messy sheets.
2. **Decide the shape** from `SECTION_ORDER` + `references/conventions.md`: apply
   the same consolidation by hand — mailer = 2 slides/wave for the recent 6
   (older → a separate Mailer Performance deck), attrition 2×1 merges, appendix
   routing, the intentionally-blank exec slides.
3. **Build slides** with the `pptx` skill on the CSI template (use the
   `csi-powerpoint` skill for brand colors, fonts, the approved template). Per
   slide: an action-title headline, the data table and/or a chart you plot from
   the tab, KPI callouts, and a source footer carrying the correct **denominator
   label** (Eligible / Eligible Personal / Eligible Business / Open).
4. **Plot charts from the tab data** (matplotlib) where a slide needs one — the
   numbers are right there in the sheet.
5. **QA the result** with `scripts/run_deck_qa.py` and spot-check a few slides'
   numbers back against their source tabs.

Guardrails for this mode:
- Honor the locked conventions and the denominator law — they don't change just
  because Claude is the one laying out the slides.
- Write to a **distinct filename** so you never clobber the pipeline's deck.
- If the user needs exact parity with the production deck's charts/branding, fall
  back to the pipeline — this path optimizes for speed and flexibility, not pixel
  parity. Say so plainly rather than implying the two are identical.

## Running it (the pipeline way)

- **Dev (Mac):** `python 01_Analysis/run.py --month 2026.06 --csm JamesG --client 1759`
  (needs the formatted ODD under `READY_FOR_ANALYSIS/{csm}/{month}/{client}/`).
  Always go through `run.py` — it installs the `ars_analysis` alias the modules
  import. The bundled scripts do this for you.
- **Operator (Windows, `M:\ARS\`):** `git pull` is unavailable (network share);
  they ZIP-download the branch. To apply changes: re-download the branch ZIP,
  close the Velocity Pipeline window, double-click `Start Here.bat`, hard-refresh
  the browser. Never tell them to `cd 05_UI` / `python app.py` / use a Unix path.

## Performance

A run is `load_data → analyses → generate_output`. The `Analysis timing: <total>s
| slowest: ...` log line names the bottleneck — read it before optimizing.
Historically the mailer modules dominate (per-wave chart renders, per-wave
member-table work). Escape hatches: `ARS_COMBO_MONTHS` (mailer wave window),
`ARS_SKIP_COMBO=1` / `SKIP_COMBO.flag` (skip combos), `ARS_CHART_CACHE=0`
(disable the cross-run chart cache), `ARS_RENDER_DROPPED_MAILER=1` (render the
dropped slides anyway). The deck-build step is now nearly as costly as analysis —
if total runtime matters, profile both halves.

## Pitfalls (learned the hard way)

- **Stale deck > real bug.** Re-read the cardinal rule. Check commit times.
- **Synthetic ≠ real.** The synthetic build is ~39 clean slides; real client data
  has ~22 mailer waves and exposes consolidation gaps the fixtures don't. QA on
  real output, not just the synthetic build.
- **Prior "done" claims are unreliable.** Verify against code + extracted pixels,
  not a handoff note or a memory entry.
- **deck_qa was only ever clean on synthetic.** Run it on the real deck too.

## References

- `references/conventions.md` — locked owner deck conventions (verify, don't change)
- `references/lessons.md` — the stale-deck post-mortem and the multi-wave test gap
- Memory: `project_deck_quality_fixes.md`, `project_denominator_framework.md`,
  `project_data_trust_issue.md` (in the user's auto-memory)
