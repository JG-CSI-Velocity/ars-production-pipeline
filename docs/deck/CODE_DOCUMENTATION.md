# Code Documentation — ARS Slide Design System

**Audience:** developers extending the slide design system from PRD #145.
**Parent issue:** #160 (T5.5).

This is the developer reference. For operator workflow see `IMPLEMENTATION_GUIDE.md`. For design rules see `SLIDE_DESIGN.md`.

## Module map

```
01_Analysis/00-Scripts/
├── shared/
│   └── charts.py                  # COLORS, SECTION_COLORS, CATEGORY_PALETTE, MAX_CATEGORICAL_COLORS, section_color()
├── charts/
│   ├── style.py                   # PRIMARY/TEAL/HISTORICAL/TTM aliases + chart helpers
│   └── ars.mplstyle               # matplotlib rcParams
├── pipeline/
│   ├── context.py                 # PipelineContext (ctx.results, ctx.all_slides, ctx.dropped_slides, etc.)
│   └── steps/
│       └── generate.py            # G6 drop-if-empty, DropReason, detect_section_drops, step_generate, _run_tier3_outputs
└── output/
    ├── deck_builder.py            # SlideContent dataclass, DeckBuilder, build_deck() — main PPTX render path
    ├── headlines.py               # Legacy per-slide title generators (T2.2 superseded for mapped IDs)
    ├── notes.py                   # Section-keyed speaker notes
    ├── callout_builder.py         # T1.4 — CalloutBox dataclass + CalloutBoxBuilder
    ├── action_title_populator.py  # T2.2 — template-driven action title rendering
    ├── section_consolidator.py    # T2.3 — 3-into-1 combo slides
    ├── excel_exporter.py          # T3.1 — 4-sheet review summary
    ├── quality_gate.py            # T3.2 — 10-check QualityReport
    └── metadata_writer.py         # T3.3 — run audit JSON
```

## Data flow

```
       runner / analytics modules
              │
              ▼
      ctx.results, ctx.all_slides
              │
              ▼
   step_generate(ctx) in pipeline/steps/generate.py
              │
              ├── detect_section_drops(ctx)             # T2.6 section-level drops
              ├── _drop_empty_slides(ctx)               # G6 + T2.6 slide-level drops
              ├── _write_excel(ctx)                     # legacy Excel
              ├── _build_deck(ctx)                      # main PPTX
              │       │
              │       ▼
              │   build_deck(ctx) in output/deck_builder.py
              │       │
              │       ├── _infer_product_mode(ctx)      # T2.4
              │       ├── _build_preamble_slides(..., product_mode)
              │       ├── SectionConsolidator.consolidate(section, slides)  # T2.3
              │       ├── per-slide:
              │       │   _result_to_slide(result, ctx_results)
              │       │      ├── ActionTitlePopulator.populate(template_id, ...)  # T2.2
              │       │      ├── headlines.generate_headline(...)  (fallback)
              │       │      ├── notes.generate_notes(...)
              │       │      └── attaches section_key, callout_box
              │       └── DeckBuilder.build()
              │             │
              │             └── _add_slide() per SlideContent:
              │                 ├── _build_<slide_type>_slide()
              │                 ├── CalloutBoxBuilder.render()  # T1.4
              │                 └── _add_footer_band()
              ├── _build_aux_deck(ctx)                  # aux PPTX (G7)
              └── _run_tier3_outputs(ctx)               # T3.4
                      │
                      ├── ExcelExporter.export()        # T3.1 — review_summary.xlsx
                      ├── QualityGate.run()             # T3.2 — quality_report.{txt,json}
                      └── MetadataWriter.write()        # T3.3 — meta.json
```

## Key dataclasses

### `SlideContent` (output/deck_builder.py)

Carries everything `DeckBuilder` needs to render a slide. Fields added during the rollout:

| Field | Tier | Purpose |
|---|---|---|
| `slide_type` | existing | dispatch into the right `_build_*` method |
| `title` | existing | action title (post-populator or fallback) |
| `images`, `kpis`, `bullets`, `layout_index`, `notes_text` | existing | per-slide content |
| `callout_box` | T1.4 | structured `CalloutBox`; supersedes the legacy `kpis`-derived callout |
| `section_key` | T1.3 / T2.5 | drives chart-chrome accent + callout tinting |
| `slide_id` | T2.3 | propagated so the consolidator can find slides by id |

### `CalloutBox` (output/callout_builder.py)

`CalloutBoxBuilder.from_kpis(kpis, slide_type=..., section_key=...)` produces one from the legacy `kpis` dict so existing callers don't need updating; `CalloutBoxBuilder.render(slide, callout)` paints it.

### `DropReason` (pipeline/steps/generate.py)

Six string constants: `data_missing`, `client_no_product`, `threshold_not_met`, `module_failed`, `manifest_dropped`, `section_inactive`. Consumed by `QualityGate._check_drops_logged()`, `ExcelExporter._sheet_quality_flags()`, and `MetadataWriter._build()`.

### `CheckResult` / `QualityReport` (output/quality_gate.py)

Ten checks per run; each returns a `CheckResult(name, passed, detail, severity)`. The aggregate `QualityReport` exposes `.summary()` (dict) for metadata, `.to_text()` (human-readable), and `.to_json()` (machine-readable).

## Extension points

### Add a new action-title template
1. Append a block to `docs/action_title_templates.md` following the established markdown shape.
2. Add an entry to `deck_builder._SLIDE_TEMPLATE_MAP` mapping the slide_id to your new template id.
3. Confirm the placeholder `ctx.results` paths exist in the analytics module that produces this slide.
4. Test by running a client and inspecting the slide title.

### Add a new section combo
1. Append a `ComboPattern` to `output/section_consolidator.py::COMBO_PATTERNS[section_key]`.
2. Verify the three source slide IDs actually exist in your typical run.
3. Test by running a client and confirming the combo replaces the originals in the main flow while the detail slides route to the appendix.

### Add a new quality check
1. Add a `_check_<name>(...)` function in `output/quality_gate.py` returning a `CheckResult`.
2. Append it to the list in `QualityGate.run()`.
3. Update `IMPLEMENTATION_GUIDE.md` to describe the new check.

### Add a new section
1. Add the section to `SECTION_COLORS` in `shared/charts.py`.
2. Add it to `_SECTION_LABELS`, `_SECTION_NUMBERS`, `_SECTION_LEAD_INS` in `output/deck_builder.py`.
3. Add it to `SECTION_ORDER` in `output/deck_builder.py` (insertion point determines narrative arc position).
4. Add a `_section_main` mapping for the slides that belong to it in `build_deck`.
5. If section dashboards apply, add patterns to `COMBO_PATTERNS`.
6. Author `docs/slide_specs/<new_section>.md`.

### Add a new preamble variant
1. Add a `_preamble_<mode>(...)` function in `output/deck_builder.py`.
2. Update `_build_preamble_slides()` dispatch.
3. Update `_infer_product_mode()` if a new product mode is involved.
4. Update `QualityGate._check_preamble_correct` to know the expected count for the new mode.

## Failure modes + safety nets

| Component | Failure path | Behavior |
|---|---|---|
| Action title populator | Catalog file missing | All slides fall back to `headlines.py` generators; logged at WARNING |
| Action title populator | Missing `ctx.results` for a placeholder | Falls back to template's `fallback` sentence; logged at INFO |
| Section consolidator | Any of the 3 source slides absent | Combo skipped; originals pass through untouched |
| CalloutBoxBuilder | All placement options collide with charts | Callout skipped (better than overlapping); logged at INFO |
| ExcelExporter | openpyxl error | None returned; pipeline continues; quality gate notes absence |
| QualityGate | Individual check raises | Doesn't crash the run; the deck still ships |
| MetadataWriter | JSON write error | None returned; pipeline continues |

Invariant: **the run always produces a PPTX as long as analytics succeeded.** Tier 3 deliverables are advisory; their absence isn't fatal.

## Testing

Until the project is on real CI:

- `python3 -c "import ast; ast.parse(open('<file>').read())"` for syntax on every change
- `python3 -m pytest 01_Analysis/00-Scripts/...` if/when test fixtures land per checklist T4
- Smoke-test the populator: `python3 -c "from output.action_title_populator import load_catalog; print(len(load_catalog()))"` should return 28
- Smoke-test the palette: `python3 -c "from shared.charts import COLORS, SECTION_COLORS; assert COLORS['primary'] == '#1E3D59' and 'dctr' in SECTION_COLORS"`
- E2E: run a real client through the UI and confirm the five Tier 3 + Tier 1/2 outputs land
