# 2025-CSI-PPT-Template.pptx — Layout Audit (T1.2)

**Issue:** #147
**Source of truth:** SLIDE_DESIGN.md (locked per #146).
**Operator action required:** items marked **MANUAL** below need direct PowerPoint edits to `2025-CSI-PPT-Template.pptx`. Everything else is handled by the programmatic rendering path and does not require touching the .pptx file.

---

## The 20 layouts

Indexed against `output/deck_builder.py` constants:

| # | Constant | Layout name | Title? | Body? | Used by |
|---|---|---|---|---|---|
| 0 | `LAYOUT_TITLE_DARK` | Title Slide (dark) | yes | subtitle | Title page only |
| 1 | `LAYOUT_TITLE` | Title Slide Reverse (light) | yes | subtitle | TXN/Hybrid title (T2.4) |
| 2 | `LAYOUT_CONTENT` | Title and Content | yes | body | Content fallback |
| 3 | `LAYOUT_CONTENT_ALT` | Title and Content (alt) | yes | body | Content fallback |
| 4 | `LAYOUT_SECTION` | 2_Section Header | yes | body | Section dividers (overridden programmatically) |
| 5 | `LAYOUT_SECTION_ALT` | 5_Section Header alt | yes | body | Unused |
| 6 | `LAYOUT_SECTION_GRAY` | 3_Section Header Gray | yes | body | Unused |
| 7 | `LAYOUT_TITLE_VARIANT` | 2_Title Slide | yes | subtitle | End/Q&A |
| 8 | `LAYOUT_CUSTOM` | Custom Layout | yes | open canvas | **Primary content layout** |
| 9 | `LAYOUT_TWO_CONTENT` | Two Content | yes | l/r | Multi-screenshot |
| 10 | `LAYOUT_COMPARISON` | Comparison | yes | l/r | Comparison slides |
| 11 | `LAYOUT_BLANK` | Blank | — | — | Blank fallback |
| 12 | `LAYOUT_BULLETS` | Content with Bullets | yes | l/r | Summary slides |
| 13 | `LAYOUT_PICTURE` | Picture with Content | yes | body+pic | Picture slides |
| 14 | `LAYOUT_2_PICTURES` | 2 Pictures | yes | l/r pics | Multi-pic |
| 15 | `LAYOUT_3_PICTURES` | 3 Pictures | yes | grid | Multi-pic |
| 16 | `LAYOUT_WIDE_TITLE` | 1_Title and Content | yes | wide body | Wide title |
| 17 | `LAYOUT_TITLE_RPE` | 1_Title Slide RPE | yes | branded | Master title |
| 18 | `LAYOUT_TITLE_ARS` | 4_Title Slide ARS | yes | branded | ARS section |
| 19 | `LAYOUT_TITLE_ICS` | 5_Title Slide ICS | yes | branded | ICS section |

---

## Audit results per T1.2 subtask

### T1.2.3 — Title placeholder 28pt bold navy on all 20 layouts

**Programmatic coverage:** Title text is set via `slide.shapes.title.text = …` in `_set_title()` and `_build_title_slide()`, but font size + color come from the layout's placeholder formatting. So this rule **does need template edits** to land for any slide where a master title is used.

**MANUAL action for the operator:**
1. Open `01_Analysis/00-Scripts/output/template/2025-CSI-PPT-Template.pptx` in PowerPoint
2. View → Slide Master
3. For each of the 20 layouts, click into the title placeholder and set:
   - Font: **Arial**
   - Size: **24pt** (SLIDE_DESIGN.md §4 spec; PRD's 28pt is rounded; keep 24pt as committed)
   - Weight: **Bold**
   - Color: `#1E3D59`
4. Close Slide Master, save the template

**Programmatic safety net:** title placement for the section divider (#4) is fully overridden by `_build_section_slide` (paints navy background + sized text programmatically) — that one is bulletproof regardless of the master-slide setting. Other layouts inherit whatever the master defines.

### T1.2.4 — Footnote placeholder (8pt gray, locked) on all 20 layouts

**Programmatic coverage:** Done. `_add_footer_band` paints both footer lines on every non-title/non-section slide via `add_textbox()` directly on the slide canvas (not the placeholder). So this rule is **covered programmatically** — the layout-level footnote placeholder is belt-and-braces.

**MANUAL action (optional):** if the operator wants the placeholder also present for slides built outside the pipeline (manually authored), repeat the slide-master edit:
- Add a text-frame placeholder at the bottom of every layout
- Position: `left=0.5"`, `top=7.0"`, `width=12.33"`, `height=0.5"`
- Font: Arial 8pt, color `#999999`
- Lock the placeholder so manual editing doesn't shift it

### T1.2.5 — Lock margins to 0.5" all sides

**Programmatic coverage:** N/A — operator-side template lock.

**MANUAL action:** Slide Master → for each layout, ensure the content placeholders sit within `0.5"` margins on all four sides. PowerPoint doesn't have a "lock" gesture; this is a discipline check.

### T1.2.6 — Section divider layout: 32pt bold navy

**Programmatic coverage:** Done. `_build_section_slide` (b0ff9d6) paints the navy background + section number (48pt teal) + section title (36pt white bold) + lead-in (18pt white) directly, ignoring whatever the master layout says. The PRD's "32pt bold navy" is overridden in favor of SLIDE_DESIGN.md §9's full-bleed navy treatment — captured in the doc, can be reverted if the operator wants the PRD shape literally.

**No MANUAL action required.**

### T1.2.7 — KPI/callout layouts: pre-defined box areas (lower-right)

**Programmatic coverage:** Done. `CalloutBoxBuilder.render` (T1.4 / #149) computes anchor positions programmatically and avoids picture-bounds collisions. The layout-level box area would only be cosmetic.

**No MANUAL action required.**

### T1.2.8 — Picture layouts 13/14/15: consistent margins + alignment

**Programmatic coverage:** Partial. `_get_single_positioning` and `_get_multi_positioning` set image insertion points per layout. The template-level placeholder positions are only consulted if the programmatic positioning isn't applied.

**MANUAL action (recommended):** verify in Slide Master that picture placeholders in layouts 13-15 use the same margins as `_get_*_positioning` returns. Concretely:
- Layout 13 (Picture with Content): picture should be `left=4.5"`, `top=1.0"`, `width=8.0"`, `height=5.0"`
- Layout 14 (2 Pictures): each picture `top=1.5"`, `height=5.5"`, widths `5.5"` each side
- Layout 15 (3 Pictures): grid 1.5" top, 1.5"/4.5"/7.5" left positions, 3" wide each

### T1.2.9 — Test on 5 sample slides from past decks

**Operator action.** Run the existing UI Generate flow on 5 representative past clients (one DCTR-heavy, one Reg-E-heavy, one mailer-heavy, one TXN-only, one combined) and verify visually:
- Titles render in Arial 24pt bold navy (or your chosen 28pt if you updated the master)
- Footer band appears bottom of every content slide
- Section dividers are full-bleed navy
- Callout boxes are bottom-right with no chart overlap
- Picture margins are consistent

Capture screenshots into `docs/deck/audit-screenshots/` if the operator wants a visual baseline for regression checks later.

### T1.2.10 — Save updated template, verify <2MB

**Operator action.** After any manual edits, save and confirm the .pptx is still under 2MB. If it grew, check for embedded images that were added by mistake.

### T1.2.11 — Commit template changes

**Operator action.** `git add` the updated `output/template/2025-CSI-PPT-Template.pptx` and commit.

---

## Summary

| Subtask | Status | Who |
|---|---|---|
| T1.2.1 backup template | Required pre-step | Operator |
| T1.2.2 inventory 20 layouts | **Done** (this doc) | Code |
| T1.2.3 title placeholder 24pt bold navy | **MANUAL** required for non-section layouts; section divider is programmatic | Operator (master-slide edit) |
| T1.2.4 footnote placeholder 8pt gray | Covered programmatically; manual is optional | Code (operator optional) |
| T1.2.5 lock 0.5" margins | **MANUAL** discipline check | Operator |
| T1.2.6 section divider 32pt bold navy | Programmatically overridden to §9 full-bleed | Code |
| T1.2.7 KPI/callout box areas | Programmatic via T1.4 | Code |
| T1.2.8 picture margins | Partial programmatic; verify master matches | Operator (verify) |
| T1.2.9 test on 5 past decks | **Operator** | Operator |
| T1.2.10 save + size check | **Operator** | Operator |
| T1.2.11 commit | **Operator** | Operator |

Net delta: 4 sub-tasks need the operator at PowerPoint (T1.2.3, T1.2.5, T1.2.8 verify, T1.2.9 test + T1.2.10/11 commit). The other 7 are either done programmatically (Phase 18 baseline) or noted as optional.
