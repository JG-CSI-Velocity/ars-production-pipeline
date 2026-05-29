# Velocity Pipeline — Reliability Improvement Plan

**Date:** 2026-05-29
**Scope:** Analysis → PowerPoint, end-to-end, operator-PC-only
**Operator environment:** Windows, `M:\ARS\`, UI launched by `Start Here.bat`
**Principle:** Every diagnostic, fix, and run is reachable from the UI. Improve what exists. No new frameworks, no new services.

---

## Current State

### What works (don't break it)

| Component | File | Status |
|---|---|---|
| 5-stage pipeline (load → subset → analyze → generate → archive) | `01_Analysis/00-Scripts/pipeline/batch.py` | Functional |
| 25 ARS modules + 22 TXN sections | `01_Analysis/00-Scripts/analytics/` | Registered, running |
| Deck builder (20-layout template) | `01_Analysis/00-Scripts/output/deck_builder.py` | Builds PPTX |
| Headline generators (~60 slide IDs) | `01_Analysis/00-Scripts/output/headlines.py` | Partial — 31 still `_noop` |
| Speaker notes | `01_Analysis/00-Scripts/output/notes.py` | Generic template, not section-specific |
| SLIDE_MANIFEST.xlsx curation (Y/N/A) | `01_Analysis/00-Scripts/output/manifest.py` | Functional, wired to deck_builder |
| FastAPI UI (Generate, Format, Results, History) | `05_UI/app.py` + `05_UI/index.html` | Functional |
| Run manifest JSON (per-run metadata) | `01_Analysis/00-Scripts/pipeline/manifest.py` | Structured |
| Design spec | `docs/SLIDE_DESIGN.md` | McKinsey-grade spec written |

### What's missing or broken

| Gap | Impact | Root cause | Fix location |
|---|---|---|---|
| 31 `_noop` headline generators | Slides get generic category titles | No insights data wired for those modules | `output/headlines.py` |
| No callout boxes | SLIDE_DESIGN §7 defines them; not rendered | `_add_slide` doesn't create callout shapes | `output/deck_builder.py` |
| No footer bands | SLIDE_DESIGN §8 defines source + confidentiality footer; not rendered | Missing from `_add_slide` | `output/deck_builder.py` |
| Section dividers don't match spec | Should be full-bleed navy w/ numbered sections (§9); currently plain title-layout | `_build_section_slide` uses default placeholder styling | `output/deck_builder.py` |
| No section-level control in UI | CSMs can't pick individual sections to run | `POST /api/run` only accepts `product` flag | `05_UI/app.py` + `05_UI/index.html` |
| No batch / multi-client run | Can't queue multiple clients from UI | Single-client form only | `05_UI/app.py` + `05_UI/index.html` |
| No scheduled / recurring runs | CSMs trigger every cycle manually | None — needs Task Scheduler (see Stream 17.3) | Windows Task Scheduler + `/api/run` |
| Overnight formatting sweep | Auto-format new data dumps on 7th/9th/11th | None — needs Task Scheduler | Windows Task Scheduler + `/api/format-sweep` |
| Chart styling inconsistent | `charts/style.py` defaults overridden per-module | Style enforcement is per-module | `output/charts/style.py` |
| TXN analysis runs ~1hr | Blocks CSM workflow | Sequential script execution + large dataset | `pipeline/batch.py` parallel modules |

---

## Execution streams

### Stream 1 — Verification (BLOCKER, all UI clicks)

Nothing else ships until the merged `pipeline-improvement` branch is confirmed working on the operator PC. Every step below is in the UI.

1. **Pull on the work PC.** Open GitHub Desktop → repo `ars-production-pipeline` → fetch and pull `pipeline-improvement` into `M:\ARS\`.
2. **Close the existing Velocity Pipeline terminal window** (this stops the running `app.py`).
3. **Double-click `Start Here.bat`** at `M:\ARS\`. Wait for the browser to open `http://localhost:8000`.
4. **Hard-refresh the browser** with Ctrl+Shift+R so any HTML/JS changes load.
5. **Run an ARS verification client:** Generate tab → CSM = James → Month = 2026.05 → Client = 1615 → Product = ARS → Run. Wait for the run to finish in the Results tab.
6. **Run the same client as TXN:** Generate tab → Product = TXN → Run.
7. **Open both decks from the Results tab.** Confirm they open in PowerPoint with no broken slides.
8. **Report:** screenshot of Results tab + slide counts. If any module errored, the History tab surfaces it; no log-tailing required.

**Success gate:** Both decks open clean. Slide counts match expected. No red error rows on the History tab.

---

### Stream 2 — Phase 18: Slide Layout Refinement (HIGHEST ROI)

This is the formatting reliability stream. Every item closes a gap between `docs/SLIDE_DESIGN.md` and what `deck_builder.py` actually produces. Operator-facing: nothing changes in the UI — the same Generate-tab run produces a better deck.

#### 18.1 — Callout box rendering

- **Input:** `AnalysisResult.kpis` dict (already populated by many modules)
- **Output:** rounded-rectangle callout on each content slide, bottom-right by default
- **Hero number:** first non-`subtitle` KPI, 32pt bold, teal `#0D9488`
- **Sub-label:** KPI key text, 14pt semibold navy, then optional second KPI line 12pt
- **Files touched:** `01_Analysis/00-Scripts/output/deck_builder.py` (new method `_add_callout_box`, called from `_add_slide`)
- **Slide types affected:** `screenshot`, `multi_screenshot`. `screenshot_kpi` excluded (already renders KPIs).
- **Design ref:** `docs/SLIDE_DESIGN.md` §7

#### 18.2 — Footer band on every content slide

- **Line 1:** source/methodology — 9pt italic, `#777777`
- **Line 2:** `{Client Name}  |  {Month YYYY}  |  Slide {n}  |  STRICTLY CONFIDENTIAL` — 8pt, `#999999`
- **Position:** bottom 0.4" of slide, full width
- **Skipped on:** `title`, `section` slide types
- **Files touched:** `output/deck_builder.py` (new method `_add_footer_band`; `_add_slide` and `build` accept `slide_number`, `client_name`, `month`; `build_deck` threads them in from `ctx.client`)
- **Design ref:** `docs/SLIDE_DESIGN.md` §8

#### 18.3 — Section dividers

- Full-bleed navy `#1B365D` background
- Section number teal `#0D9488`, 48pt bold (e.g. `02`)
- Section title white, 36pt bold
- Lead-in sentence white, 18pt regular
- No charts, no logos
- **Files touched:** `output/deck_builder.py` (`_build_section_slide` replaced; `_section_divider()` helper in `build_deck` updated to emit 3-line title `"{num}\n{label}\n{lead_in}"`)
- **Design ref:** `docs/SLIDE_DESIGN.md` §9

#### 18.4 — Complete `_noop` headline generators

Current `_noop` slide IDs (31 total, verified in `headlines.py:570–636`):

```
A1b, A7.5, A7.6a, A7.6b, A7.10b, A7.13, A7.14, A7.15,
A8.2, A8.3, A8.4b, A8.4c, A8.5, A8.6, A8.7, A8.10, A8.11, A8.12, A8.13,
A18, A18.1, A18.2, A18.3, A19, A19.1, A19.2, A20, A20.1, A20.2, A20.3
```

For each: inspect the matching analytics module, see which insights keys it populates in `ctx.results`, and write a generator that formats those into an action title (SLIDE_DESIGN §1.2 — title is the insight, not the category).

- **Files touched:** `output/headlines.py` (full replacement — see `docs/deck/phase-18-patches/headlines_replacement.py`). Generators for every `_noop` slide are implemented with utility helpers (`_fmt_pct`, `_fmt_currency`, `_trend_word`, `_try_adaptive`) and fall back gracefully on missing data.
- **Dependency:** each generator assumes the matching analytics module populates the expected insights keys. Modules that don't yet emit those keys will fall through to the headline's default-title fallback — file follow-ups per module as gaps surface during Stream-1 verification.

#### 18.5 — Section-specific speaker notes

Replace generic `output/notes.py` template with section-keyed talking points (2–3 prompts per section, mapped via slide_id prefix). Backward-compatible signature.

- **Files touched:** `output/notes.py` (full replacement, public API unchanged)
- **Verify before deploying:** the active import is `from ars_analysis.output.notes import generate_notes` (`deck_builder.py:1598`). Confirm `ars_analysis.output.notes` resolves to `01_Analysis/00-Scripts/output/notes.py` on the work PC (`python -c "import ars_analysis.output.notes; print(ars_analysis.output.notes.__file__)"`). If it points to a stale install, the replacement won't take effect.

#### 18.6 — Chart style alignment

Centralize SLIDE_DESIGN §5–6 enforcement in `output/charts/style.py`:

- Palette: Navy `#1E3D59`, Teal `#17A2B8`, Positive `#28A745`, Negative `#DC3545`
- Rate+volume combo: volume = muted gray columns, rate = teal line width 3
- Max 4 colors per chart (excluding neutrals)
- Zero-volume categories dropped, not rendered as empty columns
- Font: Arial 11–12pt axes, 11pt bold data labels

**Files touched:** `output/charts/style.py` (centralize), individual analytics modules (remove per-module overrides).

---

### Stream 3 — Phase 17: E2E Orchestration

#### 17.1 — Section-level control

- New config: `03_Config/section_registry.json` (section → slide_prefix mapping). See `03_Config/section_registry.json` for the canonical mapping.
- CLI: `01_Analysis/run.py` accepts `--sections dctr,attrition,value` (comma-separated).
- Pipeline: `pipeline/batch.py` already supports `module_ids`; wire `--sections` → module IDs via the registry.
- **UI:** Generate tab gets a multi-select checkbox group below the product selector, populated from `/api/sections` (new endpoint that reads the registry). `POST /api/run` accepts a `sections` parameter and passes it through.

#### 17.2 — Batch multi-client run

- `pipeline/batch.py` already has `run_batch()` with `max_workers` + `use_local_temp`.
- **API:** `POST /api/batch` accepts `client_ids: list[str]`. Returns `batch_id`.
- **API:** `GET /api/batch/{batch_id}` returns per-client status for polling.
- **UI:** Generate tab gets checkboxes next to each client. "Run Selected" button. New Batch Progress panel (table: client | status | duration | slides).

#### 17.3 — Scheduled / recurring runs

**Architecture:** Windows Task Scheduler triggers an HTTP call to `app.py`. An in-app background thread is not viable — `Start Here.bat` stops `app.py` when the terminal closes, so an in-process scheduler wouldn't fire on days the CSM isn't at the machine.

Two pieces:

1. **In the UI (Schedules tab — currently placeholder):**
   - Form to create a schedule: CSM, client_id(s), product, sections, day_of_month, hour.
   - `POST /api/schedules` persists to `03_Config/schedules.json`.
   - `GET /api/schedules` lists active schedules.
   - `DELETE /api/schedules/{id}` removes one.
   - `POST /api/schedules/{id}/run` fires the schedule's run on demand (also the endpoint Task Scheduler hits).
2. **In Windows Task Scheduler (one-time setup per work PC):**
   - One task that runs daily at 06:00. Action: `powershell -Command "Invoke-RestMethod -Method POST -Uri http://localhost:8000/api/schedules/run-due"`.
   - The `/api/schedules/run-due` endpoint reads `schedules.json`, picks the entries whose `day_of_month` matches today, and queues them via `run_batch()`.
   - **Pre-req:** `Start Here.bat` must be running at the scheduled hour. Document this; consider a follow-up phase to convert `app.py` to a Windows Service so it stays up across reboots.

#### 17.4 — API response caching

`/api/csms`, `/api/months`, `/api/clients` scan M: drive directories on every dropdown load. Add a 5-minute TTL cache in `app.py`:

```python
_cache = {}
_cache_ttl_sec = 300

def _cached(key, fetch):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit["ts"] < _cache_ttl_sec:
        return hit["data"]
    data = fetch()
    _cache[key] = {"data": data, "ts": now}
    return data
```

Single-process FastAPI on Windows — no thread-safety concerns at this volume.

---

### Stream 4 — Phase 19: Overnight Formatting Sweep

**Same architecture pattern as 17.3:** Windows Task Scheduler triggers an HTTP endpoint.

- **API:** `POST /api/format-sweep` scans all opt-in CSM source folders for unformatted ZIPs, runs `00_Formatting/run.py` for each (skips existing outputs), writes results to `04_Logs/overnight/{date}.json`.
- **Config:** `03_Config/overnight_whitelist.json`: `{ "enabled_csms": ["James", "Dan"] }`. Start opt-in only.
- **Task Scheduler:** one task running on the 7th, 9th, 11th of each month at 02:00. Action: same `Invoke-RestMethod` pattern as 17.3.
- **UI:** new Sweep tab shows last sweep date, file counts, errors. `GET /api/format-sweep/history`.
- **Pre-req:** `Start Here.bat` running at the scheduled hour. Same caveat as 17.3.

---

## Execution sequence

| Week | Stream | Deliverables |
|---|---|---|
| 1 | Stream 1 (Verification) | Operator confirms `pipeline-improvement` runs clean for client 1615 (ARS + TXN). |
| 2–3 | Stream 2 (Phase 18) | Callout boxes, footer bands, section dividers, ~31 headline generators, section notes, chart style. |
| 4 | Stream 3.1 (Section control) | `section_registry.json`, `--sections` flag, UI checkboxes. |
| 5 | Stream 3.2–3.4 (Batch, schedule, cache) | Batch UI, schedule UI + Task Scheduler hook, dropdown caching. |
| 6 | Stream 4 (Overnight sweep) | `/api/format-sweep`, opt-in whitelist, Task Scheduler config doc. |

---

## Success criteria (measurable, all visible in UI)

| Metric | Current | Target | How operator verifies |
|---|---|---|---|
| Slides with action titles (not generic) | ~40% | 95%+ | Open deck, scan slide titles |
| Slides with callout boxes | 0% | 100% of content slides | Visual audit |
| Slides with footer bands | 0% | 100% content | Visual audit |
| Section dividers match SLIDE_DESIGN §9 | No | Yes | Visual audit |
| Time to generate 1 ARS deck | ~5 min | ~5 min (no regression) | Results tab `elapsed_s` |
| CSM can select individual sections | No | Yes | Section checkboxes on Generate tab |
| CSM can batch multiple clients | No | Yes | Multi-select + Run Selected |
| CSM can schedule monthly runs | No | Yes | Schedules tab + Task Scheduler firing |
| Overnight auto-formatting | No | Yes | Sweep tab shows last 3 sweep dates with file counts |

---

## Files changed (summary)

| File | Changes | Stream |
|---|---|---|
| `01_Analysis/00-Scripts/output/deck_builder.py` | Callout boxes, footer bands, section dividers, `_add_slide`/`build` signatures | 18 |
| `01_Analysis/00-Scripts/output/headlines.py` | 31 `_noop` → real generators | 18 |
| `01_Analysis/00-Scripts/output/notes.py` | Section-keyed talking points (full replacement) | 18 |
| `01_Analysis/00-Scripts/output/charts/style.py` | Centralize palette + typography | 18 |
| `01_Analysis/run.py` | `--sections` flag | 17 |
| `01_Analysis/00-Scripts/pipeline/batch.py` | Wire section → module_ids | 17 |
| `05_UI/app.py` | `/api/sections`, `/api/batch*`, `/api/schedules*`, `/api/format-sweep*`, dropdown caching | 17, 19 |
| `05_UI/index.html` | Section checkboxes, batch UI, Schedules tab wired, Sweep tab | 17, 19 |
| `03_Config/section_registry.json` | NEW: section → slide_prefix mapping | 17 |
| `03_Config/schedules.json` | NEW: persisted schedules | 17 |
| `03_Config/overnight_whitelist.json` | NEW: opt-in CSM list | 19 |
| `docs/deck/phase-18-patches/deck_builder_patch.py` | Reference patch for deck_builder (callout, footer, section divider) | 18 |
| `docs/deck/phase-18-patches/notes_replacement.py` | Full replacement for `output/notes.py` (section-keyed talking points) | 18 |
| `docs/deck/phase-18-patches/headlines_replacement.py` | Full replacement for `output/headlines.py` (all 31 `_noop` generators implemented) | 18 |
| `docs/deck/task-scheduler-setup.md` | One-time Task Scheduler config for 17.3 + Stream 4 | 17, 19 |

---

## Constraints

- **No new frameworks.** Python 3.12, FastAPI, python-pptx, Matplotlib, openpyxl.
- **No new services.** Everything runs on the work PC at `M:\ARS\`. Scheduling delegates to Windows Task Scheduler hitting `localhost:8000`.
- **UI-first.** Every Stream-3 and Stream-4 capability is reachable from `index.html`. No new CLI requirements for operators.
- **Git workflow preserved.** `pipeline-improvement` → `dev` → `main` via `promote.bat`.
- **SLIDE_MANIFEST.xlsx remains operator-local.** Not tracked, not overwritten.
- **Backward-compatible defaults.** A no-arg `/api/run` call produces the same deck as today, plus the Phase 18 formatting improvements.

---

## Known caveats

- **Scheduling depends on `Start Here.bat` being open.** Task Scheduler can launch it if missing (Action: `cmd /c "M:\ARS\Start Here.bat"`), but that opens a fresh terminal window each time. A follow-up phase should convert `app.py` to a Windows Service (via `nssm` or `pywin32`) so it survives reboots and runs headless.
- **`value` is not a standalone section at runtime.** `build_deck()` distributes A10/A11 slides into the `dctr` and `rege` sections (`_section_main["value"] = []`). The section registry reflects this — `value` is listed for completeness but selecting it alone yields no slides until the routing is changed.
- **TXN sub-sections in the registry are aspirational.** `_SECTION_MAP` currently lumps everything TXN under one `"transaction"` section. The 8 `txn_*` entries in `section_registry.json` describe the intended decomposition; wiring them through `build_deck`'s grouping is a follow-up.
