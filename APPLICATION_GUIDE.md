# Phase 18 Patch Application Guide

**Branch name:** `feature/phase-18-slide-refinement`

```bash
cd M:\ARS
git checkout dev
git pull origin dev
git checkout -b feature/phase-18-slide-refinement
```

---

## File 1: `phase_18_deck_builder.py`

**Target:** `01_Analysis/00-Scripts/output/deck_builder.py`

This file contains 5 changes. Apply them in order.

### Change 1: Add `_add_callout_box` method

**Where:** Inside `class DeckBuilder`, after the `_add_fitted_picture` method.

**Action:** Copy the `_add_callout_box` method from the patch file and paste it as a new method on the `DeckBuilder` class. Add `from pptx.enum.shapes import MSO_SHAPE` to the imports at the top of the file if not already present.

### Change 2: Add `_add_footer_band` method

**Where:** Inside `class DeckBuilder`, after `_add_callout_box`.

**Action:** Copy the `_add_footer_band` method from the patch file and paste it as a new method.

### Change 3: Replace `_build_section_slide` method

**Where:** Inside `class DeckBuilder`, find the existing `_build_section_slide` method.

**Action:** Replace the entire method body with the version from the patch file. The new version:
- Removes all placeholders
- Sets navy background programmatically
- Parses 3-line title format (number\ntitle\nlead-in)
- Draws section number in teal, title in white, lead-in in white

### Change 4: Replace `_add_slide` method

**Where:** Inside `class DeckBuilder`, find the existing `_add_slide` method.

**Action:** Replace the entire method with the version from the patch file. The new version adds three parameters (`slide_number`, `client_name`, `month`) and calls `_add_callout_box` + `_add_footer_band` after the builder dispatch.

### Change 5: Replace `build` method

**Where:** Inside `class DeckBuilder`, find the existing `build` method.

**Action:** Replace with the version from the patch file. The new version:
- Accepts `client_name` and `month` parameters
- Passes `slide_number=i+1`, `client_name`, `month` to each `_add_slide` call

### Change 6: Update `build_deck()` caller

**Where:** Module-level `build_deck(ctx)` function (NOT on the class). Find the line:

```python
result = builder.build(all_slides, str(pptx_path))
```

**Action:** Change to:

```python
result = builder.build(
    all_slides,
    str(pptx_path),
    client_name=ctx.client.client_name,
    month=ctx.client.month,
)
```

### Change 7: Add section number/lead-in constants

**Where:** Near the top of `deck_builder.py`, after the `_SECTION_LABELS` dict (or after `_SECTION_MAP`).

**Action:** Add these two dicts:

```python
_SECTION_NUMBERS = {
    "overview": "01",
    "dctr": "02",
    "rege": "03",
    "attrition": "04",
    "mailer": "05",
    "value": "06",
    "insights": "07",
    "competition": "08",
    "ics": "09",
}

_SECTION_LEAD_INS = {
    "overview": "Portfolio composition, eligibility, and program scope.",
    "dctr": "Current penetration, where opportunity sits, and what closing the gap is worth.",
    "rege": "Opt-in rates, branch variation, and revenue impact of Reg E enrollment.",
    "attrition": "Who is leaving, what it costs, and where retention efforts should focus.",
    "mailer": "Campaign response rates, cohort lift, and mailer program ROI.",
    "value": "Revenue attribution — what a debit card and Reg E opt-in are worth.",
    "insights": "Synthesis, recommendations, and quantified action plan.",
    "competition": "Competitor detection, wallet share analysis, and market positioning.",
    "ics": "Invitation Checking System acquisition channels and conversion.",
}
```

### Change 8: Update section divider creation

**Where:** Wherever section divider `SlideContent` objects are created (in `build_deck()` or `_build_preamble_slides`). Look for patterns like:

```python
SlideContent(
    slide_type="section",
    title=f"SECTION: {label}\n...",
    layout_index=LAYOUT_SECTION_ALT,
)
```

**Action:** Change to:

```python
section_num = _SECTION_NUMBERS.get(section_key, "")
lead_in = _SECTION_LEAD_INS.get(section_key, "")
label = _SECTION_LABELS.get(section_key, section_key.title())

SlideContent(
    slide_type="section",
    title=f"{section_num}\n{label}\n{lead_in}",
    layout_index=LAYOUT_SECTION,
)
```

---

## File 2: `phase_18_notes.py`

**Target:** `01_Analysis/00-Scripts/output/notes.py`

**Action:** Replace the entire file with `phase_18_notes.py`. This is a complete drop-in replacement. The public API (`generate_notes()`) has the exact same signature — no callers need to change.

**What changed:**
- Added `_SECTION_TALKING_POINTS` dict with 2-3 targeted prompts per section
- Added `_SLIDE_SECTION_MAP` to resolve slide_id → section
- `generate_notes()` now outputs section-specific talking points instead of generic ones
- Fallback to generic prompts for unmapped slide IDs (backward compatible)

---

## File 3: `section_registry.json`

**Target:** `03_Config/section_registry.json` (NEW FILE)

**Action:** Copy `section_registry.json` to `M:\ARS\03_Config\section_registry.json`.

**Purpose:** Provides the section → slide_prefix mapping needed for Phase 17.1 (section-level control via `--sections` CLI flag). Not wired yet — this is the config; the CLI wiring comes in the Phase 17 branch.

---

## Verification

After applying all patches:

```bash
cd M:\ARS\01_Analysis\00-Scripts
python -m pytest tests/ -q
```

Then run a real client:

```bash
cd M:\ARS\01_Analysis
python run.py --month 2026.05 --csm James --client 1615
```

**What to check in the output deck:**
1. Content slides have a teal callout box (bottom-right) with hero KPI number
2. Content slides have a two-line footer (source + confidentiality)
3. Section dividers have navy background, teal section number, white title + lead-in
4. Speaker notes contain section-specific talking points (check in Presenter View)

**What should NOT change:**
- Title slides (no callout, no footer)
- Total slide count (same as before)
- Chart images (unchanged — formatting is additive)
- Excel workbook output (unchanged)

---

## Commit

```bash
git add 01_Analysis/00-Scripts/output/deck_builder.py
git add 01_Analysis/00-Scripts/output/notes.py
git add 03_Config/section_registry.json
git commit -m "feat(deck): Phase 18.1-18.5 — callout boxes, footer bands, section dividers, speaker notes"
git push -u origin feature/phase-18-slide-refinement
```

Then merge to `dev`, soak test, and `promote.bat` to `main` when ready.
