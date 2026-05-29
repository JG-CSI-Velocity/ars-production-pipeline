# Velocity Pipeline — Reliability Improvement Plan

**Date:** 2026-05-29
**Scope:** Analysis Complete → PowerPoint Creation (highest ROI)
**Principle:** Improve what exists. Do not stray from current setup.

---

## Current State Assessment

### What Works

| Component | File | Status |
|-----------|------|--------|
| 5-stage pipeline (load → subset → analyze → generate → archive) | `pipeline/batch.py` | ✓ Functional |
| 25 ARS modules + 22 TXN sections | `analytics/` | ✓ Registered, running |
| Deck builder with 20-layout template | `output/deck_builder.py` | ✓ Builds PPTX |
| Headline generators for ~60 slide IDs | `output/headlines.py` | ⚠ Partial — many are `_noop` |
| Speaker notes generation | `output/notes.py` | ⚠ Generic template, not section-specific |
| SLIDE_MANIFEST.xlsx curation (Y/N/A) | `output/manifest.py` | ✓ Functional |
| Excel workbook output (one tab per analysis) | `pipeline/steps/generate.py` | ✓ Functional |
| FastAPI UI (Generate, Format, Results, History) | `05_UI/app.py` + `index.html` | ✓ Functional |
| Run manifest JSON (per-run metadata) | `pipeline/manifest.py` | ✓ Structured |
| Design system documented | `SLIDE_DESIGN.md` | ✓ McKinsey-grade spec written |

### What's Broken or Missing

| Gap | Impact | Root Cause | Fix Location |
|-----|--------|------------|--------------|
| **Many headline generators are `_noop`** | Slides get generic category titles instead of action titles | No insights data wired for those modules | `output/headlines.py` |
| **No callout boxes rendered** | SLIDE_DESIGN.md §7 defines them; deck_builder doesn't render them | `_add_slide()` methods don't create callout shapes | `output/deck_builder.py` |
| **No footer bands** | SLIDE_DESIGN.md §8 defines source/methodology + confidentiality footer; not rendered | Missing from `_add_slide()` | `output/deck_builder.py` |
| **Section dividers don't match spec** | Should be full-bleed navy with numbered sections per §9; currently basic text | `_add_section_slide()` uses default layout styling | `output/deck_builder.py` |
| **No section-level control in UI** | CSMs can't pick individual sections to run | `POST /api/run` only accepts `product` flag | `05_UI/app.py` + `index.html` |
| **No batch/scheduling** | Can't queue multiple clients or schedule monthly runs | Phase 17 not started | `05_UI/app.py` |
| **Chart styling inconsistent with design system** | SLIDE_DESIGN.md §5-6 defines precise color/typography rules; `charts/style.py` may diverge | Style defaults set per-module, not centrally enforced | `charts/style.py` |
| **No executive summary slide auto-generated** | SLIDE_DESIGN.md §2 requires it as slide 2; pipeline doesn't create one | No module produces it | New: `analytics/insights/exec_summary.py` |
| **Preamble slides hardcoded** | 13 intro/section/placeholder slides baked in | `deck_builder.py` inserts them statically | `output/deck_builder.py` |
| **TXN analysis performance (~1hr)** | Blocks CSM workflow | Large dataset + sequential script execution | `pipeline/batch.py` parallelization |

---

## Execution Plan

Maps directly to existing roadmap phases. No new architecture — just completing what's already designed.

### Stream 1: Phase 16 — Verification (BLOCKER)

**Why first:** Nothing else ships until the merged repo is confirmed working on the work PC.

| Step | Action | Owner | Deliverable |
|------|--------|-------|-------------|
| 16.1 | Pull current `dev` branch on work PC | JG | Clean `git pull` |
| 16.2 | Run `00_Formatting/run.py --month 2026.05 --csm James --client 1615` | JG | Formatted Excel in `02-Data-Ready for Analysis/` |
| 16.3 | Run `01_Analysis/run.py --month 2026.05 --csm James --client 1615` | JG | Excel + charts + PPTX in `01_Completed_Analysis/` |
| 16.4 | Run `01_Analysis/run.py --month 2026.05 --csm James --client 1615 --product txn` | JG | TXN deck separate from ARS deck |
| 16.5 | Verify PPTX opens clean in PowerPoint, slide count matches expected | JG | Screenshot or confirmation |
| 16.6 | Document any errors in `04_Logs/` and flag for fix | JG | Log files |

**Success gate:** All four commands complete without pipeline-breaking errors. Decks open in PowerPoint.

---

### Stream 2: Phase 18 — Slide Layout Refinement (HIGHEST ROI)

This is the formatting reliability stream. Every item maps to a gap between `SLIDE_DESIGN.md` and what `deck_builder.py` actually produces.

#### 18.1 — Callout Box Rendering

**Input:** `AnalysisResult.kpis` dict (already populated by many modules)
**Output:** Positioned callout shape on each content slide

**What to change in `deck_builder.py`:**

```
_add_slide() → after placing chart image:
  1. Check if content.kpis is non-empty
  2. Create a rounded-rectangle shape (callout box) per SLIDE_DESIGN.md §7
  3. Position: bottom-right of chart area (or configurable per slide_type)
  4. Hero number: first KPI value, 32pt bold, accent color
  5. Sub-label: KPI key text, 14pt semibold
  6. Max 2 lines of sub-label text
```

**Files touched:** `output/deck_builder.py` (method: `_add_screenshot_slide`, `_add_screenshot_kpi_slide`)
**Design reference:** SLIDE_DESIGN.md §7

#### 18.2 — Footer Band (Every Slide)

**Input:** `ctx.client` (name, month), slide number, `AnalysisResult.notes` (methodology)
**Output:** Two-line footer on every content slide

**What to change:**

```
_add_slide() → after all content placed:
  Line 1: Source/methodology (from result.notes or default), 9pt italic, #777777
  Line 2: "{Client Name} | {Month YYYY} | Slide {n} | STRICTLY CONFIDENTIAL", 8pt, #999999
  Position: bottom 0.4" of slide, full width, left-aligned
```

**Files touched:** `output/deck_builder.py` (new helper: `_add_footer_band()` called from `_add_slide`)
**Design reference:** SLIDE_DESIGN.md §8

#### 18.3 — Section Dividers

**Input:** Section name + number + lead-in sentence
**Output:** Full-bleed navy slide matching §9

**What to change:**

```
Current _add_section_slide() uses LAYOUT_SECTION (teal) or LAYOUT_SECTION_ALT
→ Switch to LAYOUT_SECTION_GRAY or custom:
  - Background: navy (#1B365D) full bleed
  - Section number: teal (#0D9488), 48pt bold, left-aligned
  - Section title: white, 36pt bold
  - Lead-in sentence: white, 18pt regular
  - No charts, no logos, no ornamentation
```

**Files touched:** `output/deck_builder.py` (method: `_add_section_slide`)
**Design reference:** SLIDE_DESIGN.md §9

#### 18.4 — Complete `_noop` Headline Generators

**Current state:** Many slide IDs in `HEADLINE_GENERATORS` map to `_noop` (returns empty string → falls back to generic title).

**Slide IDs currently returning `_noop`:**

```
ARS: A7.5, A7.6a, A7.6b, A7.10b, A7.13, A7.14, A7.15,
     A8.2, A8.3, A8.4b, A8.4c, A8.5, A8.6, A8.7,
     A8.10, A8.11, A8.12, A8.13, A1b,
     A18, A18.1, A18.2, A18.3, A19, A19.1, A19.2,
     A20, A20.1, A20.2, A20.3
```

**Pattern for each:** Same as existing generators:
1. Check which insights keys the analytics module populates in `ctx.results`
2. Write a generator function that formats those values into an action title
3. Follow SLIDE_DESIGN.md §1.2: title is the insight, not the category

**Files touched:** `output/headlines.py` (add ~30 generator functions)
**Dependency:** Each module must populate `ctx.results[key]` with the right insights dict

#### 18.5 — Section-Specific Speaker Notes

**Current state:** `output/notes.py` uses a single generic template for all slides.

**Improvement:** Add section-specific talking points:

```python
# Instead of generic "What actions has the credit union taken?"
# → Section-specific prompts:
SECTION_TALKING_POINTS = {
    "dctr": [
        "Which branches have the lowest DCTR? What's their activation process?",
        "Is there a new-account onboarding flow that includes debit card activation?",
    ],
    "attrition": [
        "What's driving closures in the highest-attrition segments?",
        "Are there retention campaigns targeting at-risk accounts?",
    ],
    "reg_e": [
        "How is Reg E opt-in being presented during account opening?",
        "What's the branch-level variation in opt-in rates?",
    ],
    # ... per section
}
```

**Files touched:** `output/notes.py`

#### 18.6 — Chart Style Alignment

**Current state:** `charts/style.py` sets defaults; individual modules may override.
**Target:** Enforce SLIDE_DESIGN.md §5-6 centrally.

**Key enforcements:**
- Color palette: Navy #1E3D59, Teal #17A2B8, Positive #28A745, Negative #DC3545
- Rate+volume combo: volume = muted gray columns, rate = teal line width 3
- Max 4 colors per chart (besides neutrals)
- Zero-volume categories dropped (not empty columns)
- Font: Arial 11-12pt for axes, 11pt bold for data labels

**Files touched:** `charts/style.py` (centralize), individual analytics modules (remove overrides)

---

### Stream 3: Phase 17 — E2E Orchestration (SCALABILITY)

#### 17.1 — Section-Level Control

**Current CLI:** `python run.py --product ars` (runs all 25 modules)
**Target CLI:** `python run.py --product ars --sections dctr,attrition,value`

**What to change:**

```
01_Analysis/run.py:
  Add --sections argument (comma-separated list)
  Pass to runner as module_ids filter

pipeline/batch.py → _build_steps():
  analyze_step already accepts module_ids
  Wire --sections → module_ids mapping

05_UI/app.py → POST /api/run:
  Add "sections" parameter
  Pass through to run.py subprocess call
```

**Section → module_id mapping** (new file: `03_Config/section_registry.json`):

```json
{
  "overview":   ["overview_eligibility", "overview_composition"],
  "dctr":       ["dctr_trends", "dctr_branches", "dctr_funnel", "dctr_segment", "dctr_elig"],
  "reg_e":      ["reg_e_optin", "reg_e_branches", "reg_e_dimensions"],
  "attrition":  ["attrition_rates", "attrition_demographics", "attrition_revenue"],
  "mailer":     ["mailer_response", "mailer_cohort", "mailer_reach", "mailer_lift"],
  "value":      ["value_debit", "value_rege"],
  "insights":   ["insights_conclusions"],
  "competition": ["competition_detection", "competition_wallet"]
}
```

**UI change:** Add multi-select checkboxes on Generate tab below product selector.

#### 17.2 — Batch Client Processing

**Current:** One client at a time via UI.
**Target:** Select multiple clients, queue them, process sequentially or in parallel.

**What exists already:** `pipeline/batch.py` has `run_batch()` with `max_workers` parameter and `use_local_temp` for network drive optimization.

**What to add:**

```
05_UI/app.py:
  POST /api/batch → accepts list of client_ids
  Queues them via run_batch()
  Returns batch_id for polling

05_UI/index.html:
  Multi-select on Generate tab (checkboxes next to each client)
  "Run Selected" button
  Batch progress view (table: client | status | duration | slides)
```

#### 17.3 — Scheduling

**Current:** Manual trigger only.
**Target:** CSMs set up monthly recurring runs.

**What to add:**

```
05_UI/app.py:
  POST /api/schedules → create schedule (csm, client_id, product, sections, day_of_month)
  GET /api/schedules → list active schedules
  DELETE /api/schedules/{id} → remove schedule
  Background thread: check schedules daily, trigger runs on matching day

03_Config/schedules.json → persistent schedule storage
```

**UI:** Schedules tab already exists in `index.html` (currently placeholder). Wire it up.

#### 17.4 — API Response Caching

**Current:** Every dropdown load scans M: drive directories.
**Target:** Cache CSM list, months, clients for 5 minutes.

**What to add in `app.py`:**

```python
from functools import lru_cache
from time import time

_cache = {}
_cache_ttl = 300  # 5 minutes

def cached_api(key, fetch_fn):
    if key in _cache and (time() - _cache[key]["ts"]) < _cache_ttl:
        return _cache[key]["data"]
    data = fetch_fn()
    _cache[key] = {"data": data, "ts": time()}
    return data
```

Apply to: `/api/csms`, `/api/months`, `/api/clients`

---

### Stream 4: Phase 19 — Overnight Formatting Sweep (AUTOMATION)

**Current:** CSMs manually trigger formatting for each client.
**Target:** Auto-format all new data dumps on the 7th, 9th, and 11th of each month.

**Already designed in roadmap.** Implementation:

```
05_UI/app.py:
  Background thread (threading.Timer or APScheduler)
  On trigger dates: scan all CSM source folders for unformatted ZIPs
  Run 00_Formatting/run.py for each (skip existing)
  Log results to 04_Logs/overnight/
  
03_Config/overnight_whitelist.json:
  Start with opt-in CSMs only
  { "enabled_csms": ["JamesG", "Dan"] }
```

---

## Execution Sequence

```
Week 1:  Phase 16 (Verification) — BLOCKER
         ├── JG: work PC test, document results
         └── Fix any errors surfaced

Week 2-3: Phase 18 (Slide Refinement) — HIGHEST ROI
         ├── 18.1: Callout boxes
         ├── 18.2: Footer bands
         ├── 18.3: Section dividers
         ├── 18.4: Complete _noop headline generators (batched by section)
         ├── 18.5: Section-specific speaker notes
         └── 18.6: Chart style alignment

Week 4:  Phase 17.1 (Section-Level Control)
         ├── CLI --sections flag
         ├── section_registry.json
         └── UI multi-select

Week 5:  Phase 17.2-17.4 (Batch + Scheduling + Caching)
         ├── Batch client processing
         ├── Schedule creation/execution
         └── API caching

Week 6:  Phase 19 (Overnight Sweep)
         └── Background auto-formatting

```

---

## Success Criteria (Measurable)

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Slides with action titles (not generic) | ~40% | 95%+ | Count `_noop` generators remaining |
| Slides with callout boxes | 0% | 100% content slides | Visual audit of output deck |
| Slides with footer bands | 0% | 100% | Visual audit |
| Section dividers match SLIDE_DESIGN.md | No | Yes | Visual audit |
| Time to generate 1 client ARS deck | ~5 min | ~5 min (no regression) | Pipeline log elapsed_s |
| CSM can select individual sections | No | Yes | UI checkbox test |
| CSM can batch multiple clients | No | Yes | UI multi-select test |
| CSM can schedule monthly runs | No | Yes | Schedules tab functional |
| Overnight auto-formatting | No | Yes | Log files on 7th/9th/11th |

---

## Files Changed (Summary)

| File | Changes | Stream |
|------|---------|--------|
| `output/deck_builder.py` | Callout boxes, footer bands, section dividers | 18 |
| `output/headlines.py` | Complete ~30 `_noop` generators | 18 |
| `output/notes.py` | Section-specific talking points | 18 |
| `charts/style.py` | Centralize color/typography enforcement | 18 |
| `01_Analysis/run.py` | Add `--sections` argument | 17 |
| `pipeline/batch.py` | Wire section filtering | 17 |
| `05_UI/app.py` | Section control, batch, scheduling, caching | 17 |
| `05_UI/index.html` | Section checkboxes, batch UI, schedule wiring | 17 |
| `03_Config/section_registry.json` | New: section → module_id mapping | 17 |
| `03_Config/schedules.json` | New: persistent schedule storage | 17 |
| `03_Config/overnight_whitelist.json` | New: opt-in CSM list for auto-formatting | 19 |

---

## Constraints

- **No new frameworks.** Python 3.12, FastAPI, python-pptx, Matplotlib, openpyxl. That's the stack.
- **No new services.** Everything runs on the work PC at `M:\ARS\`.
- **Git workflow preserved.** feature → dev → main via `promote.bat`.
- **SLIDE_MANIFEST.xlsx remains operator-local.** Not tracked by git, not overwritten.
- **Backward compatible.** Running `python run.py` with no new flags produces the same output as today (plus formatting improvements).
