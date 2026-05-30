# ARS SLIDE DESIGN SYSTEM — IMPLEMENTATION CHECKLIST

**Version:** 1.0
**Date:** May 29, 2026
**Duration:** 12 weeks
**Status:** Ready to Execute
**Source:** Filed as attachment on issue #145; committed here so the
checklist is version-controlled with the code that implements it.

> **Mapping note:** The companion PRD (`ARS_SLIDE_DESIGN_PRD.md`,
> attached separately on #145) is the authoritative requirements
> document. This checklist is the executable breakdown. Each T*.*
> task ID maps to a single GitHub issue (#146-#157) so progress can
> be tracked per-commit.

---

## HOW TO USE THIS CHECKLIST

1. **Print or open in Excel:** Each section lists tasks, owners, timelines, dependencies
2. **Track progress:** Mark ✓ when complete, update % complete
3. **Dependencies:** If a task is blocked, check its prerequisites
4. **Weekly sync:** Review "Week N" section each Monday; update status

---

## TIER 1: VISUAL CONSISTENCY (Weeks 1-2)

### T1.1: Design Standards Document

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T1.1.1 | Audit current SLIDE_DESIGN.md for gaps | Designer | 1 | ☐ | | List missing sections: typography, color, spacing, callout format |
| T1.1.2 | Define typography rules (fonts, sizes, weights, colors) | Designer | 1 | ☐ | | Action title 28pt bold navy, subtitle 20pt gray, footnote 8pt, etc. |
| T1.1.3 | Define color palette (section accent colors + usage rules) | Designer | 1 | ☐ | | DCTR=teal, Rege=purple, Attrition=red, Value=green, Mailer=blue, Insights=gray |
| T1.1.4 | Define spacing & layout rules (margins, gaps, placement) | Designer | 1 | ☐ | | Margins 0.5" all sides, title to chart 0.3", chart to callout 0.2" |
| T1.1.5 | Define callout box format & styling | Designer | 1 | ☐ | | Template: [ICON] METRIC: $VALUE \| DENOMINATOR COMPARISON |
| T1.1.6 | Define chart styling rules (colors, axes, legends, annotations) | Designer | 1 | ☐ | | Section color for primary series, gray scale for secondary, no overlap |
| T1.1.7 | Define per-section divider rules (font, background, subtitle) | Designer | 1 | ☐ | | 32pt bold navy, section color background 10% opacity |
| T1.1.8 | Define slide anatomy diagram (4 regions: title, chart, callout, footnote) | Designer | 2 | ☐ | | Create visual diagram showing placement |
| T1.1.9 | Document section-specific rules (what varies per section, what doesn't) | Designer | 2 | ☐ | | e.g., all callouts follow same format, but color varies per section |
| T1.1.10 | Write SLIDE_DESIGN.md final (10-15 pages, illustrated) | Designer | 2 | ☐ | | Include 5-8 example slides showing rules in action |
| T1.1.11 | Review & approve SLIDE_DESIGN.md with CSM | CSM | 2 | ☐ | | Get sign-off before moving to template updates |

**Dependencies:** None (parallel track)
**Acceptance Criteria:** SLIDE_DESIGN.md complete, documented, approved by CSM
**GitHub issue:** #146

---

### T1.2: Template Layout Updates

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T1.2.1 | Open 2025-CSI-PPT-Template.pptx | Frontend | 1 | ☐ | | Backup original before editing |
| T1.2.2 | Inventory all 20 layouts (list names, placeholder types) | Frontend | 1 | ☐ | | Identify which layouts have title, content, picture areas |
| T1.2.3 | For each layout: update title placeholder to 28pt bold navy | Frontend | 1-2 | ☐ | | All 20 layouts |
| T1.2.4 | For each layout: add/update footnote placeholder (8pt gray, locked) | Frontend | 1-2 | ☐ | | Standardized placement on all layouts |
| T1.2.5 | For each layout: lock margins to 0.5" all sides | Frontend | 2 | ☐ | | Prevents accidental shift |
| T1.2.6 | For section divider layout specifically: set font 32pt bold navy | Frontend | 2 | ☐ | | Matches SLIDE_DESIGN.md divider spec |
| T1.2.7 | For KPI/callout layouts: pre-define box areas (lower-right corner) | Frontend | 2 | ☐ | | Guides callout placement |
| T1.2.8 | For picture layouts: verify consistent margins & alignment | Frontend | 2 | ☐ | | Picture layouts 13, 14, 15 |
| T1.2.9 | Test template on 5 sample slides from past decks | Frontend | 2 | ☐ | | Verify no placeholder shifts, fonts render correctly |
| T1.2.10 | Save updated template, verify file size unchanged | Frontend | 2 | ☐ | | <2MB, backup original |
| T1.2.11 | Commit template changes to repo | Frontend | 2 | ☐ | | Git: "T1.2 template layout updates" |

**Dependencies:** T1.1 (SLIDE_DESIGN.md approved)
**Acceptance Criteria:** All 20 layouts updated, tested on 5 decks, template file <2MB
**GitHub issue:** #147

---

### T1.3: Chart Styling Standards

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T1.3.1 | Review current charts/style.py for gaps | Backend | 1 | ☐ | | List what's already there vs. what's missing |
| T1.3.2 | Define section color mapping (DCTR→teal, Rege→purple, etc.) | Backend | 1 | ☐ | | Create SECTION_COLORS dict in code |
| T1.3.3 | Add function to apply section color to charts | Backend | 1 | ☐ | | Primary series = section accent, secondary = gray |
| T1.3.4 | Add axis label rotation/abbreviation logic | Backend | 1-2 | ☐ | | Auto-rotate if >6 chars + >5 labels; auto-abbreviate if insufficient |
| T1.3.5 | Add legend placement rules (right-aligned, 10pt, no background) | Backend | 2 | ☐ | | Standardize across all charts |
| T1.3.6 | Add annotation styling rules (callout boxes, arrows, numbers) | Backend | 2 | ☐ | | Section color border, white text, 8pt font |
| T1.3.7 | Add grid styling rules (light gray, 0.5pt) | Backend | 2 | ☐ | | Standardize across all charts |
| T1.3.8 | Document all rules in code comments & SLIDE_DESIGN.md | Backend | 2 | ☐ | | Make it easy to modify |
| T1.3.9 | Test on 10 sample charts from past decks (check overlap, colors) | Backend | 2 | ☐ | | Verify no axis label overlap, colors match |
| T1.3.10 | Commit changes to repo | Backend | 2 | ☐ | | Git: "T1.3 chart styling standards" |

**Dependencies:** T1.1 (SLIDE_DESIGN.md approved)
**Acceptance Criteria:** style.py updated, tested on 10 charts, no axis label overlap
**GitHub issue:** #148
**Already partially done:** palette aligned in 51f6ef3 (issue #142 item 3.6).

---

### T1.4: Callout Box Standardization

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T1.4.1 | Create callout_builder.py in output/ | Frontend | 1 | ☐ | | New module |
| T1.4.2 | Define CalloutBox dataclass (metric, value, denominator, comparison, section_color, icon) | Frontend | 1 | ☐ | | Match SLIDE_DESIGN.md spec |
| T1.4.3 | Implement CalloutBoxBuilder.build() method with formatting rules | Frontend | 1-2 | ☐ | | Template: [ICON] METRIC: $VALUE \| DENOMINATOR COMPARISON |
| T1.4.4 | Add section-to-icon mapping (DCTR→💰, Rege→🛡️, etc.) | Frontend | 1 | ☐ | | Or use ASCII icons if emoji unsupported |
| T1.4.5 | Implement color conversion (section_color → hex + 20% opacity for background) | Frontend | 2 | ☐ | | rgba(color, 0.2) for background |
| T1.4.6 | Add placement logic (lower-right, margin 0.2" from edge, no overlap) | Frontend | 2 | ☐ | | Verify doesn't cover critical chart elements |
| T1.4.7 | Integrate into deck_builder.py (_result_to_slide method) | Frontend | 2 | ☐ | | Create CalloutBox object for slides that have callout data |
| T1.4.8 | Test on 10 sample slides (verify format, colors, placement) | Frontend | 2 | ☐ | | Check across different sections |
| T1.4.9 | Document usage in code comments | Frontend | 2 | ☐ | | How to create callout, what fields required |
| T1.4.10 | Commit to repo | Frontend | 2 | ☐ | | Git: "T1.4 callout box standardization" |

**Dependencies:** T1.1 (SLIDE_DESIGN.md), T1.3 (chart styling)
**Acceptance Criteria:** Callout builder module, integrated into deck_builder, tested on 10 slides
**GitHub issue:** #149
**Already partially done:** `_add_callout_box` shipped in b0ff9d6 (Phase 18.1), collision avoidance added in 51f6ef3 (issue #142 item 3.7). Remaining work: dataclass refactor, denominator+comparison fields, section-icon map, broader slide_type coverage.

---

## TIER 2: INTELLIGENT POPULATION & CONSOLIDATION (Weeks 3-6)

### T2.1: Action Title Template Library

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T2.1.1 | Review past 20 decks to identify action title patterns | Analyst | 3 | ☐ | | Document recurring templates per section |
| T2.1.2 | Create DCTR section templates (3-4 templates) | Analyst | 3 | ☐ | | Basic activation, peer comparison, growth driver, momentum |
| T2.1.3 | Create Rege section templates (3-4 templates) | Analyst | 3 | ☐ | | Penetration, revenue impact, growth trajectory, at-risk |
| T2.1.4 | Create Value section templates (3-4 templates) | Analyst | 3 | ☐ | | Total opportunity, gap, benchmark, per-account impact |
| T2.1.5 | Create Attrition section templates (3-4 templates) | Analyst | 3 | ☐ | | Account closure rate, driver analysis, prevention opportunity, peer comparison |
| T2.1.6 | Create Mailer section templates (3-4 templates) | Analyst | 3 | ☐ | | Campaign performance, response rate, revenue impact, segment performance |
| T2.1.7 | Create Insights section templates (3-4 templates) | Analyst | 3-4 | ☐ | | Top insight, growth driver, risk indicator, recommendation headline |
| T2.1.8 | Create Overview section templates (3-4 templates) | Analyst | 4 | ☐ | | Portfolio snapshot, performance summary, segment highlight, trend |
| T2.1.9 | For each template: define placeholders (X%, N count, $Y, verb, reason, etc.) | Analyst | 4 | ☐ | | List all variables needed |
| T2.1.10 | For each template: map placeholders to ctx.results keys (dot notation) | Analyst | 4 | ☐ | | e.g., {"X": "dctr_rate", "N": "eligible_count"} |
| T2.1.11 | Write docs/action_title_templates.md (28 templates total) | Analyst | 4 | ☐ | | Include examples for each template |
| T2.1.12 | Review & approve templates with CSM + Designer | CSM | 4 | ☐ | | Ensure templates are realistic & match client language |
| T2.1.13 | Commit to repo | Analyst | 4 | ☐ | | Git: "T2.1 action title templates" |

**Dependencies:** T1.1 (SLIDE_DESIGN.md)
**Acceptance Criteria:** 28 templates documented, placeholders defined, examples provided
**GitHub issue:** #150

---

### T2.2: Action Title Populator

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T2.2.1 | Create output/action_title_populator.py | Backend | 4 | ☐ | | New module |
| T2.2.2 | Implement ActionTitlePopulator class | Backend | 4 | ☐ | | Load templates, populate from ctx.results |
| T2.2.3 | Implement _load_templates() (parse markdown template file) | Backend | 4 | ☐ | | Convert docs/action_title_templates.md to internal dict |
| T2.2.4 | Implement populate() method (main entry point) | Backend | 4 | ☐ | | Given slide_id + ctx_results, return final title |
| T2.2.5 | Implement _extract_value() (navigate nested dict with dot notation) | Backend | 4 | ☐ | | e.g., "dctr.rate" → ctx_results['dctr']['rate'] |
| T2.2.6 | Implement _format_value() (apply formatting: %, $, count) | Backend | 4-5 | ☐ | | X% → "42%", Y$M → "$2.4M", N count → "1,200" |
| T2.2.7 | Integrate into deck_builder.py (_result_to_slide method) | Frontend | 5 | ☐ | | Create populator instance, call populate() for each slide |
| T2.2.8 | Add error handling (if data missing, log warning, fallback to generic title) | Backend | 5 | ☐ | | Never crash; always produce a title |
| T2.2.9 | Test on 20 sample slides (verify numbers injected correctly) | Backend | 5 | ☐ | | Check formatting: %, $, counts |
| T2.2.10 | Add logging (what values extracted, what was missing) | Backend | 5 | ☐ | | Debug output for CSM if something looks wrong |
| T2.2.11 | Document usage in code | Backend | 5 | ☐ | | How to add new template, how to modify placeholder mapping |
| T2.2.12 | Commit to repo | Backend | 5 | ☐ | | Git: "T2.2 action title populator" |

**Dependencies:** T2.1 (template library), T1.1 (design standards)
**Acceptance Criteria:** Populator works, tested on 20 slides, numbers injected correctly, error handling
**GitHub issue:** #151
**Already partially done:** 31 previously-`_noop` generators implemented in `headlines.py` (fd7119b). T2.2 replaces the per-slide generators with a template-driven model fed from T2.1.

---

### T2.3: Section Dashboard Combos

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T2.3.1 | Create output/section_consolidator.py | Frontend | 5 | ☐ | | New module |
| T2.3.2 | Identify eligible 3-slide combos per section (KPI + bar + donut patterns) | Designer | 5 | ☐ | | DCTR: 2-3 combos, Rege: 2 combos, Value: 2 combos, etc. |
| T2.3.3 | Define COMBO_PATTERNS dict (section → list of {slides: [...], merged_id: "..."}) | Frontend | 5 | ☐ | | Hardcode patterns for each section |
| T2.3.4 | Implement SectionConsolidator.consolidate() method | Frontend | 5 | ☐ | | Returns (main_slides, aux_slides) |
| T2.3.5 | Implement _merge_slides() (combine 3 into 2-up layout) | Frontend | 5-6 | ☐ | | KPI top-left, bar bottom-left, donut right |
| T2.3.6 | Implement slide_type='combo_2up' handling in deck_builder | Frontend | 6 | ☐ | | New layout type for 2-up combos |
| T2.3.7 | Integrate into build_deck() (call consolidator per section) | Frontend | 6 | ☐ | | Consolidate main, send detail to aux |
| T2.3.8 | Update SLIDE_MANIFEST.xlsx to route combo slides | Designer | 6 | ☐ | | Mark combos as "Y" (keep), detail slides as "A" (aux) |
| T2.3.9 | Test on 5 decks (verify combos merge correctly, save ~20 slides) | Frontend | 6 | ☐ | | Check main deck <25 slides (excluding appendix) |
| T2.3.10 | Verify layout renders correctly (no overlap, legible) | Frontend | 6 | ☐ | | KPI callout visible, bar chart readable, donut clear |
| T2.3.11 | Document combo rules in SLIDE_DESIGN.md | Designer | 6 | ☐ | | Which sections have combos, which slides merge |
| T2.3.12 | Commit to repo | Frontend | 6 | ☐ | | Git: "T2.3 section dashboard combos" |

**Dependencies:** T1.2 (template layouts), T1.4 (callout builder), SLIDE_MANIFEST.xlsx
**Acceptance Criteria:** Combos merge correctly, main deck <25 slides, layout renders well, tested on 5 decks
**GitHub issue:** #152

---

### T2.4: Preamble Variants

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T2.4.1 | Implement _infer_product_mode() in deck_builder.py | Frontend | 5 | ☐ | | Detect "ars", "txn", or "hybrid" from module_ids |
| T2.4.2 | Refactor _build_preamble_slides() to accept product_mode parameter | Frontend | 5 | ☐ | | Add conditional logic: if product_mode == "ars" → 13 slides |
| T2.4.3 | Create ARS variant (13 slides, existing behavior) | Frontend | 5 | ☐ | | Title, agenda, context, 4 section dividers, performance section, summary |
| T2.4.4 | Create TXN variant (5 slides: title → agenda → context → section divider) | Frontend | 5 | ☐ | | Simplified for TXN-only reports |
| T2.4.5 | Create Hybrid variant (8 slides: title → unified agenda → ARS divider → TXN divider) | Frontend | 5-6 | ☐ | | For combined ARS+TXN reports |
| T2.4.6 | Define TXN-specific title slide layout (LAYOUT_TITLE_TXN or reuse existing) | Designer | 5 | ☐ | | Maybe distinct branding? Or same as LAYOUT_TITLE_RPE? |
| T2.4.7 | Define Hybrid title slide layout | Designer | 5 | ☐ | | Unified branding spanning both ARS + TXN |
| T2.4.8 | Update template (2025-CSI-PPT-Template.pptx) if new layouts needed | Frontend | 6 | ☐ | | Add TXN and Hybrid title slide layouts if not existing |
| T2.4.9 | Test on 3 sample decks (ARS-only, TXN-only, hybrid) | Frontend | 6 | ☐ | | Verify preamble length matches product mode |
| T2.4.10 | Document product mode detection logic in SLIDE_DESIGN.md | Designer | 6 | ☐ | | How system infers mode from module_ids |
| T2.4.11 | Commit to repo | Frontend | 6 | ☐ | | Git: "T2.4 preamble variants" |

**Dependencies:** T1.2 (template layouts)
**Acceptance Criteria:** ARS variant 13 slides, TXN variant 5 slides, hybrid 8 slides, tested on 3 decks
**GitHub issue:** #153

---

### T2.5: Per-Section Specification Documents

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T2.5.1 | Create docs/slide_specs/ directory | Analyst | 4 | ☐ | | Repo folder for all section specs |
| T2.5.2 | Refine & finalize docs/slide_specs/dctr.md (existing example) | Analyst | 4 | ☐ | | Use as template for others |
| T2.5.3 | Create docs/slide_specs/overview.md (5-8 slides) | Analyst | 4-5 | ☐ | | Portfolio snapshot, product overview, segment highlight, trend |
| T2.5.4 | Create docs/slide_specs/rege.md (5-8 slides) | Analyst | 5 | ☐ | | Penetration, revenue impact, growth trajectory, at-risk, benchmarking |
| T2.5.5 | Create docs/slide_specs/attrition.md (5-8 slides) | Analyst | 5 | ☐ | | Closure rate, drivers, prevention, peer comparison, segment analysis |
| T2.5.6 | Create docs/slide_specs/value.md (5-8 slides) | Analyst | 5 | ☐ | | Total value, gap analysis, benchmark, per-account impact, waterfall |
| T2.5.7 | Create docs/slide_specs/mailer.md (5-8 slides) | Analyst | 5 | ☐ | | Campaign performance, response rate, segment performance, revenue impact |
| T2.5.8 | Create docs/slide_specs/insights.md (5-8 slides) | Analyst | 5-6 | ☐ | | Top insight, growth driver, risk, recommendation, action priority |
| T2.5.9 | For each spec: list slide IDs + title templates | Analyst | 5-6 | ☐ | | Match to docs/action_title_templates.md |
| T2.5.10 | For each spec: list callout format + required data | Analyst | 6 | ☐ | | What ctx.results keys needed for each slide |
| T2.5.11 | For each spec: document styling rules (colors, chart type, annotations) | Analyst | 6 | ☐ | | Match SLIDE_DESIGN.md section rules |
| T2.5.12 | Verify specs match actual slide output (test on 5 decks) | Analyst | 6 | ☐ | | Do slides match their spec? Any discrepancies? |
| T2.5.13 | Commit to repo | Analyst | 6 | ☐ | | Git: "T2.5 per-section specs" |

**Dependencies:** T2.1 (action title templates), T1.1 (design standards)
**Acceptance Criteria:** 7 spec files, each with 5-8 slides, templates + data requirements documented
**GitHub issue:** #154

---

### T2.6: Drop-if-Empty Formalization

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T2.6.1 | Review existing drop logic in pipeline/steps/generate.py | Backend | 4 | ☐ | | Understand current G6 implementation |
| T2.6.2 | Document drop rules in SLIDE_DESIGN.md §12 | Designer | 4 | ☐ | | Criteria: success=False AND no chart AND no data → drop |
| T2.6.3 | List section-specific drop scenarios (ICS, TXN, Mailer) | Analyst | 4 | ☐ | | When does entire section drop? |
| T2.6.4 | Enhance logging in pipeline/steps/generate.py (capture drop reasons) | Backend | 5 | ☐ | | Create dropped_slides dict with reasons |
| T2.6.5 | Implement drop reason enum (data_missing, client_no_product, threshold_not_met, etc.) | Backend | 5 | ☐ | | Standardize reason strings |
| T2.6.6 | Add logging output: "[SLIDE MANIFEST] dropped: 3 (ics_data_missing x2, ...)" | Backend | 5 | ☐ | | Print to console & log file |
| T2.6.7 | Test on 10 decks (verify drops logged correctly, no crashes) | Backend | 5-6 | ☐ | | Check logs for accuracy |
| T2.6.8 | Commit to repo | Backend | 6 | ☐ | | Git: "T2.6 drop-if-empty formalization" |

**Dependencies:** T1.1 (design standards)
**Acceptance Criteria:** Drop rules documented, logging comprehensive, tested on 10 decks
**GitHub issue:** #155
**Already partially done:** `SOFT FAILURES:` summary line + per-slide `SOFT FAILURE` lines shipped in b0ff9d6 (issue #142 item 2.8). T2.6 adds the reason enum and the section-level drop scenarios.

---

## TIER 3: AUTOMATION & QUALITY GATES (Weeks 7-12)

### T3.1: CSM Excel Summary Export

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T3.1.1 | Create output/excel_exporter.py | Backend | 7 | ☐ | | New module using openpyxl |
| T3.1.2 | Define ExcelExporter class + export() method | Backend | 7 | ☐ | | Main entry point |
| T3.1.3 | Implement Sheet 1: Slide Inventory (ID, title, section, status, chart type, data points) | Backend | 7 | ☐ | | Loop through ctx.all_slides, extract metadata |
| T3.1.4 | Implement Sheet 2: KPI Summary (metric, value, period, comparison, vs peer) | Backend | 7-8 | ☐ | | Extract from ctx.results (DCTR %, Reg E %, Value $M, Attrition count, etc.) |
| T3.1.5 | Implement Sheet 3: Callout Text (slide ID, section, metric, value, denominator, comparison, insight) | Backend | 8 | ☐ | | For CSM to spot-check numbers |
| T3.1.6 | Implement Sheet 4: Data Quality Flags (metric, flag, severity, details, action) | Backend | 8 | ☐ | | Null counts, outliers, missing benchmarks |
| T3.1.7 | Add formatting to Excel (headers bold, colors, column widths) | Backend | 8 | ☐ | | Make it easy to read |
| T3.1.8 | Test on 5 decks (verify all sheets populate, no missing data) | Backend | 8 | ☐ | | Check accuracy of KPI values |
| T3.1.9 | Document usage in code | Backend | 8 | ☐ | | How CSM uses each sheet |
| T3.1.10 | Commit to repo | Backend | 8 | ☐ | | Git: "T3.1 CSM excel summary" |

**Dependencies:** T2.1 (action title templates), T2.6 (drop logging)
**Acceptance Criteria:** 4 sheets, all fields populated, tested on 5 decks, <10 min review time
**GitHub issue:** #156

---

### T3.2: Quality Report Generation

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T3.2.1 | Create output/quality_gate.py | Backend | 8 | ☐ | | New module |
| T3.2.2 | Define QualityGate class + run() method | Backend | 8 | ☐ | | Execute all checks, return QualityReport |
| T3.2.3 | Implement check: action_titles_populated (all titles have numbers) | Backend | 8 | ☐ | | Regex: at least one digit |
| T3.2.4 | Implement check: callouts_complete (all have metric + value + denominator + comparison) | Backend | 8 | ☐ | | Verify CalloutBox fields |
| T3.2.5 | Implement check: fonts_correct (action title 28pt, footnote 8pt) | Backend | 9 | ☐ | | May require pptx inspection |
| T3.2.6 | Implement check: colors_correct (section colors applied) | Backend | 9 | ☐ | | Spot-check a few slides |
| T3.2.7 | Implement check: no_blanks (all slides have content) | Backend | 9 | ☐ | | Image OR text required |
| T3.2.8 | Implement check: drops_logged (dropped slides have reasons) | Backend | 9 | ☐ | | Verify ctx.dropped_slides dict |
| T3.2.9 | Implement check: footnotes_complete (content slides have footnote band) | Backend | 9 | ☐ | | Source, methodology, count |
| T3.2.10 | Implement check: preamble_correct (length matches product mode) | Backend | 9 | ☐ | | ARS=13, TXN=5, Hybrid=8 |
| T3.2.11 | Implement check: slide_count_optimal (main deck ≤25) | Backend | 9 | ☐ | | Exclude appendix |
| T3.2.12 | Implement check: section_dividers_consistent (all 32pt bold navy) | Backend | 9 | ☐ | | Spot-check visual |
| T3.2.13 | Define QualityReport dataclass (timestamp, client, month, checks dict, overall_pass) | Backend | 8-9 | ☐ | | Structure output |
| T3.2.14 | Implement report output formats (txt + JSON summary) | Backend | 9 | ☐ | | [PASS/FAIL] Criterion \| Details (txt) + JSON for automation |
| T3.2.15 | Test on 10 decks (verify all 10 checks pass or fail appropriately) | Backend | 9 | ☐ | | Introduce intentional errors to test detection |
| T3.2.16 | Document each check in code | Backend | 9 | ☐ | | What it checks, why it matters |
| T3.2.17 | Commit to repo | Backend | 9 | ☐ | | Git: "T3.2 quality report" |

**Dependencies:** T1.1-T2.6 (all Tier 1-2 features)
**Acceptance Criteria:** 10 checks implemented, tested on 10 decks, reports accurate, <30sec generation
**GitHub issue:** #157

---

### T3.3: Metadata Output

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T3.3.1 | Create output/metadata_writer.py | Backend | 9 | ☐ | | New module |
| T3.3.2 | Define MetadataWriter class + write() method | Backend | 9 | ☐ | | Export JSON metadata |
| T3.3.3 | Capture metadata: timestamp, client_id, client_name, csm | Backend | 9 | ☐ | | ISO format timestamp |
| T3.3.4 | Capture metadata: month, product_mode, modules_included | Backend | 9 | ☐ | | What analysis ran |
| T3.3.5 | Capture metadata: slide counts (main, aux, dropped), sections, combos | Backend | 9 | ☐ | | Aggregate stats |
| T3.3.6 | Capture metadata: quality gate results (overall_pass, checks_passed/total) | Backend | 9 | ☐ | | From quality_report |
| T3.3.7 | Capture metadata: files_generated (list of 5 outputs) | Backend | 9 | ☐ | | PPTX, aux, Excel, report, metadata |
| T3.3.8 | Test JSON output (verify valid JSON, all fields present) | Backend | 10 | ☐ | | json.loads() should work |
| T3.3.9 | Document metadata structure (what each field means) | Backend | 10 | ☐ | | For CSM or downstream automation |
| T3.3.10 | Commit to repo | Backend | 10 | ☐ | | Git: "T3.3 metadata writer" |

**Dependencies:** T3.2 (quality report)
**Acceptance Criteria:** JSON exports with all fields, valid JSON, tested, documented
**GitHub issue:** #158

---

### T3.4: Pipeline Integration

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T3.4.1 | Review pipeline/steps/generate.py current structure | Backend | 10 | ☐ | | Understand flow before changes |
| T3.4.2 | Add step_generate imports (ExcelExporter, QualityGate, MetadataWriter) | Backend | 10 | ☐ | | At top of file |
| T3.4.3 | After build_deck(): call ExcelExporter.export() | Backend | 10 | ☐ | | Generate [client]_[month]_review_summary.xlsx |
| T3.4.4 | Call QualityGate.run() on final slides | Backend | 10 | ☐ | | Generate quality report |
| T3.4.5 | Export quality report to .txt file | Backend | 10 | ☐ | | [client]_[month]_quality_report.txt |
| T3.4.6 | Call MetadataWriter.write() | Backend | 10 | ☐ | | Generate [client]_[month]_meta.json |
| T3.4.7 | Add final logging summary (client, month, slide counts, quality, output files) | Backend | 10 | ☐ | | Helpful for CSM to see what was generated |
| T3.4.8 | Test end-to-end on 3 decks (verify all 5 outputs generated) | Backend | 10 | ☐ | | PPTX main, PPTX aux (if applicable), Excel, report, metadata |
| T3.4.9 | Verify pipeline doesn't crash if optional outputs fail (e.g., no aux deck) | Backend | 10 | ☐ | | Graceful fallback |
| T3.4.10 | Commit to repo | Backend | 10 | ☐ | | Git: "T3.4 pipeline integration" |

**Dependencies:** T3.1, T3.2, T3.3
**Acceptance Criteria:** All 5 outputs generated, tested on 3 decks, no crashes, final summary logged
**GitHub issue:** #159

---

## FINAL ACCEPTANCE & SIGN-OFF (Weeks 11-12)

### T4: Testing & Validation

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T4.1 | End-to-end test on 10 client decks (5 ARS-only, 3 TXN-only, 2 hybrid) | QA | 11 | ☐ | | Verify all features work together |
| T4.2 | CSM review workflow test (open Excel → review KPIs → approve) | CSM | 11 | ☐ | | Time it: target <15 min |
| T4.3 | Visual quality spot-check (fonts, colors, callouts, layout) | Designer | 11 | ☐ | | Compare to SLIDE_DESIGN.md standards |
| T4.4 | Chart quality spot-check (no axis label overlap, colors correct) | Backend | 11 | ☐ | | Verify style.py changes working |
| T4.5 | Action title spot-check (all have numbers, no generic templates) | Analyst | 11 | ☐ | | Review 20 random titles |
| T4.6 | Callout box spot-check (all have metric + denominator + comparison) | Analyst | 11 | ☐ | | Review 20 random callouts |
| T4.7 | Section consolidation spot-check (3-slide combos merged correctly) | Designer | 11 | ☐ | | Verify 2-up layout readable |
| T4.8 | Drop-if-empty spot-check (dropped slides logged with reason) | Analyst | 11 | ☐ | | Review logs for accuracy |
| T4.9 | Quality gate spot-check (all 10 checks pass on clean decks) | QA | 11 | ☐ | | Run on 3 sample decks |
| T4.10 | Performance testing (deck generation <5min, Excel <1min, report <30sec) | Backend | 11-12 | ☐ | | Measure actual times |
| T4.11 | Documentation review (SLIDE_DESIGN.md, templates, specs all complete?) | Designer | 12 | ☐ | | Verify no gaps |
| T4.12 | CSM training (walkthrough of workflow, review checklist) | CSM | 12 | ☐ | | Prepare CSM for go-live |

**Dependencies:** All T1-T3 tasks complete
**Acceptance Criteria:** All 10 tests pass, CSM can execute workflow in <15 min, visual quality approved
**GitHub issue:** #160 (combined with T5)

---

### T5: Documentation & Handoff

| Task ID | Task | Assignee | Week | Status | % Done | Notes |
|---------|------|----------|------|--------|--------|-------|
| T5.1 | Finalize SLIDE_DESIGN.md (10-15 pages, all rules) | Designer | 12 | ☐ | | Single source of truth |
| T5.2 | Finalize docs/action_title_templates.md (28 templates, examples) | Analyst | 12 | ☐ | | Reusable for future sections |
| T5.3 | Finalize docs/slide_specs/ (7 files, all sections) | Analyst | 12 | ☐ | | Source of truth for slide content |
| T5.4 | Create IMPLEMENTATION_GUIDE.md (CSM workflow + how to modify system) | Backend | 12 | ☐ | | Step-by-step: run analysis → review Excel → approve deck |
| T5.5 | Create CODE_DOCUMENTATION.md (how each module works, entry points) | Backend | 12 | ☐ | | For developers extending system |
| T5.6 | Record video walkthrough (5-10 min: end-to-end CSM workflow) | CSM | 12 | ☐ | | For new team members |
| T5.7 | Prepare CSM quick-reference card (1 page: what to check in Excel, etc.) | CSM | 12 | ☐ | | Printable checklist |
| T5.8 | Update README.md in repo (high-level overview, links to docs) | Backend | 12 | ☐ | | Entry point for anyone new |
| T5.9 | Commit all documentation | Backend | 12 | ☐ | | Git: "T5 documentation and handoff" |
| T5.10 | CSM sign-off: system ready for 70-client portfolio | CSM | 12 | ☐ | | Approval to go live |

**Dependencies:** All T1-T4 tasks complete
**Acceptance Criteria:** All docs complete, CSM trained, sign-off received, ready for go-live
**GitHub issue:** #160 (combined with T4)

---

## WEEKLY SUMMARY TEMPLATE

Use this to track progress each week:

```
WEEK N SUMMARY
═════════════════════════════════════════════════════════════
Tier: [1, 2, or 3]
Completed Tasks: [count]
In Progress: [count]
Blocked/At Risk: [count]
% Complete: [overall %]

Highlights:
- [What went well]
- [What we shipped]

Blockers (if any):
- [Issue 1] → [mitigation]
- [Issue 2] → [mitigation]

Next Week Focus:
- [Task 1]
- [Task 2]
- [Task 3]
```

---

## NOTES & DEPENDENCIES

### Critical Path
1. **Tier 1** (Weeks 1-2): Design standards must be approved before template/styling work
2. **Tier 2** (Weeks 3-6): Action titles depend on template; section combos depend on design rules
3. **Tier 3** (Weeks 7-12): Depends on all Tier 1-2 features being complete

### No External Dependencies
- All code lives in ARS repo
- No new tools or libraries required (openpyxl already available)
- No stakeholder approvals needed except design standards (T1.1)

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Template changes break existing decks | Medium | High | Test on 5 decks before shipping |
| Action title data missing in ctx.results | Medium | Medium | Add fallback + log warning, never crash |
| Section combos don't render correctly | Low | Medium | Test on multiple sections, QA review |
| CSM finds workflow too complex | Low | Medium | Create video walkthrough + quick-ref card |
| Performance regression (deck takes >5min) | Low | Low | Baseline performance before optimizing |

---

## SUCCESS METRICS (End of Week 12)

- [ ] All 50+ tasks complete (100%)
- [ ] CSM can generate polished deck in <30 min (15 min review + 15 min QA)
- [ ] 100% of action titles have client-specific numbers
- [ ] 100% of callouts complete (metric + denominator + comparison)
- [ ] 100% of generated decks pass quality gate
- [ ] Main deck ≤25 slides (excluding appendix) via section consolidation
- [ ] 10 successful E2E tests on real client decks
- [ ] CSM trained + signed off on system

---

**END OF CHECKLIST**

---

## HOW TO MODIFY THIS CHECKLIST

1. **Add a task:** Insert row, assign to owner, estimate week
2. **Mark complete:** Change ☐ to ✓ in Status column
3. **Update % done:** Change value in % Done column
4. **Add notes:** Document blockers, learnings, changes to scope
5. **Weekly sync:** Copy "WEEKLY SUMMARY TEMPLATE" at end of week, commit to repo

Export to Excel for easier tracking if needed. Update this file weekly.
