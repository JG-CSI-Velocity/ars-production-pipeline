# Autonomous Deck Generation — Design Spec

**Date:** 2026-05-29
**Branch:** `feat/autonomous-decks` (off `pipeline-improvement`)
**Predecessor work:** Tier 1–3 rollout from PRD #145, all 15 sub-issues closed on `pipeline-improvement`.

## Problem

The Tier 1–3 rollout produces a working deck but pushes design and authorship onto the operator:

- 28-template action title catalog written by hand.
- PowerPoint template requires manual master-slide edits.
- 15-minute per-deck CSM review before sending.
- 6 operator walkthroughs totalling ~5 hours of work per cycle.

Operator goal: click Run → finished deck ready to send to the client, without authoring or per-slide review.

## Constraint

No LLM API access from the runtime machine. No Claude Desktop dependency at the CSM (not every CSM has it). Runtime is pure Python on a Windows work PC backed by an `M:\` network share. Claude (this session and future Claude Code sessions) is the **design-time** authoring tool — content gets baked into the deterministic pipeline before it ever runs.

## Design

A rule-based pipeline with three lever-pulls, each pre-authored with Claude's help and shipped as static content + Python rules.

### A. Branching template catalog

Replace the flat 28-template catalog with branching families. Each family declares variants per data-driven branch:

```
dctr.activation_baseline:
  branch_if: ctx.results['dctr_1.rate']
  >= 0.55  (strong):       3 variants
  0.40-0.54 (healthy):     3 variants
  0.30-0.39 (opportunity): 3 variants
  <  0.30  (urgent):       3 variants
  null/missing:            1 fallback
```

Variant selection uses a stable hash — `variant_idx = int(hashlib.md5(f"{client_id}|{slide_id}".encode()).hexdigest(), 16) % len(variants)`. Stable hash (not Python's built-in `hash()`, which is salted per process) so reruns of the same client always pick the same variant.

Target: ~150 templates spread across the 7 sections. Catalog physically lives as 7 markdown files under `docs/action_title_templates/<section>.md`, loaded once per pipeline run into a process-level cache.

### B. Themed chart engine

Replace per-module matplotlib code with a single `themed_chart()` function over a Plotly custom template:

```python
themed_chart(
    kind: str,                # "rate_volume_combo" | "horizontal_bar_rank" |
                              # "branch_heatmap" | "waterfall" | "pareto" |
                              # "trend_line" | "kpi_tiles" | ...
    data: pd.DataFrame,
    section_key: str,         # picks accent from SECTION_COLORS
    *,
    hero_series: str | None,
    peer_median: float | None,
    your_value: float | None,
    source: str,
    out_path: Path,
) -> Path
```

The template enforces SLIDE_DESIGN.md §5–6 by default — Arial 11pt, hero series in section accent, peer median auto-annotated, source line baked in, no axis title says "Values," origin at zero, gray columns behind rate lines.

Charts export as 1500-px PNG written to `ctx.paths.charts_dir` (unchanged write target from today). Plotly Python package is already in `requirements.txt`; verify version floor before merging.

### C. Auto-built structural slides

Eliminate `blank` placeholder slides by building data-driven content for the structural positions:

| Slide | Source of content |
|---|---|
| Cover | Lead-finding subline picked from `ctx.results['value_summary']` |
| Executive dashboard (slide 2) | Existing 3 KPI tiles + 3 auto-selected lead findings by magnitude |
| Agenda | Per-section bullets naming the headline finding for that section |
| Section opening (after each divider) | 3 bullets pulled from the section's top three slides |
| Summary & key takeaways | Top three findings ordered by dollar magnitude with action verbs |

All content comes from rule-based ranking + template families authored alongside the catalog. New module `output/structural_slides.py` owns this. New copy lives in `docs/structural_templates.md`.

## Architecture diagram

```
   ctx.results (analytics, unchanged)
            │
            ▼
   ┌─────────────────────────────────┐
   │ A. Branching template selector   │
   │    output/template_catalog.py    │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌─────────────────────────────────┐
   │ B. Themed chart renderer         │
   │    shared/charts/themes.py       │
   └────────────┬─────────────────────┘
                │
                ▼
   ┌─────────────────────────────────┐
   │ C. Auto-built structural slides  │
   │    output/structural_slides.py   │
   └────────────┬─────────────────────┘
                │
                ▼
        finished PPTX (no operator review needed)
```

Existing `pipeline/steps/generate.py::step_generate` and `_run_tier3_outputs` orchestration unchanged. The five output files (deck + aux + Excel + quality + meta) keep landing as they do today.

## Files

### New modules

- `01_Analysis/00-Scripts/output/template_catalog.py` — loader + branching selector.
- `01_Analysis/00-Scripts/shared/charts/themes.py` — Plotly template + `themed_chart()`.
- `01_Analysis/00-Scripts/output/structural_slides.py` — cover, dashboard, agenda, section openings, takeaways builders.

### New content

- `docs/action_title_templates/<section>.md` × 7 (`overview`, `dctr`, `rege`, `attrition`, `value`, `mailer`, `insights`).
- `docs/structural_templates.md`.

### Modified files

- `output/deck_builder.py` — `_result_to_slide` calls into `template_catalog`. `_build_preamble_slides` calls `structural_slides.build_*`. `_SLIDE_TEMPLATE_MAP` shrinks to a stub.
- `output/action_title_populator.py` — keeps public `populate()` API but reads from `template_catalog.py`.
- ~25 analytics modules — each replaces matplotlib chart code with `themed_chart(...)` calls.

### Deprecated, not deleted

- `output/headlines.py` — kept as fallback when no template-family match exists.
- `docs/action_title_templates.md` — kept until the per-section catalog reaches parity.
- Per-module matplotlib code paths — kept until `themed_chart` covers every shape used.

## Server-aware behavior

The work PC runs against the `M:\` network share. The design accommodates this:

- Catalog loads **once per pipeline run** into a process-level cache. No per-slide re-reads.
- Catalog physical layout is 7 section files, not 150 individual ones — minimizes M:\ round-trips.
- Catalog-load failure raises an explicit "M: drive disconnected during catalog load — retry the run" message (matches the existing PPTX-move retry pattern in `run.py`).
- Chart PNG writes use the existing `ctx.paths.charts_dir` target. If Plotly's PNG export speed on M:\ proves problematic, render to local temp + `shutil.move` (the pattern `run.py` already uses for PPTX delivery).
- No additional intermediate files written.

## Failure modes + safety nets

| Failure | Detected when | Response |
|---|---|---|
| Catalog file missing on M:\ | Pipeline start | WARNING + fall back to `docs/action_title_templates.md`. Quality gate records `templates_loaded: fallback`. |
| M:\ disconnects mid-catalog-load | Read raises `OSError` | Retry once (1s sleep). If still fails, abort with explicit "retry the run" message. |
| Branching selector finds no match | `select_variant()` returns None | Use family's `fallback` sentence (one per family, authored alongside variants). |
| Plotly chart render fails | `themed_chart()` raises | Fall through to per-module matplotlib path (kept as fallback). Meta JSON records `chart_engine: matplotlib_fallback`. |
| `structural_slides.build_*` can't populate | Builder returns None | Fall back to today's blank-placeholder behavior. Quality gate's `no_blanks` check fires WARNING (not FAIL). |
| Placeholder path typo in a template | Selector returns a value but `populate()` can't fill it | Family's `fallback` sentence. `--strict-templates` flag surfaces these at CI, not runtime. |
| Plotly version mismatch on operator PC | Import-time check | `themed_chart()` falls back to matplotlib + WARNING. |

Two new quality-gate checks layered on top of the 10 from T3.2:

- `templates_loaded` — confirms catalog loaded cleanly (or fallback) and reports the path used.
- `structural_slides_built` — confirms §4 slides populated; degraded ones surface as WARNING.

**Invariant:** the pipeline always produces a deck. New paths add ceiling; existing paths remain as the floor.

## Migration plan

1. Build `output/template_catalog.py` + author one section's family (DCTR — ~20 templates) as a smoke test.
2. Build `shared/charts/themes.py` + migrate one chart kind (rate_volume_combo) end-to-end on one analytics module as a smoke test.
3. Build `output/structural_slides.py` + cover slide first.
4. Wire `_SLIDE_TEMPLATE_MAP` stub + populator delegation.
5. Run smoke tests against a sample client (1615) — verify the 1-section / 1-chart / 1-structural-slide path works end-to-end.
6. Author the remaining 6 section catalogs.
7. Migrate the remaining ~24 analytics modules to `themed_chart()`.
8. Build the remaining 4 structural slides (dashboard, agenda, section openings, takeaways).
9. Add `templates_loaded` + `structural_slides_built` quality-gate checks.
10. Full E2E on the 10-client matrix from `03-e2e-test-plan.md`.

Steps 1–5 are the proof-of-concept slice (1–2 sessions). Steps 6–10 are the long tail (3–5 sessions).

## Out of scope

- Runtime LLM calls of any kind.
- Operator-side authoring of templates (Claude Code authors them; operator commits).
- Auto-delivery of decks to clients (operator still emails).
- Replacing the PPTX output format with HTML.

## Open questions for the user (none blocking)

These don't block the spec but are worth deciding before authoring the bulk of the catalog:

1. **Tone / voice for variants.** Should the 3 variants per branch differ by tone (urgent / measured / curious) or by structure (data-first / context-first / action-first)?
2. **Maintenance cadence.** Quarterly catalog refresh, or only when a client pushes back?
3. **Strict-templates CI flag.** Worth wiring in this milestone, or defer until catalog stabilizes?

Defaults if unanswered: tone = "measured consulting, varied by structure not register"; cadence = "as-needed"; CI flag = "defer."

## Success criteria

- Operator's per-deck active time drops from ~15 minutes to under 1 minute (click Run → glance → send).
- 70-client cycle elapsed time stays within ~6 hours of compute (unchanged from today).
- Quality gate PASS rate ≥ 90% across the E2E matrix in `03-e2e-test-plan.md`.
- No `blank` slide types appear in a default-config run.
- Zero new operator walkthroughs added by this work.
