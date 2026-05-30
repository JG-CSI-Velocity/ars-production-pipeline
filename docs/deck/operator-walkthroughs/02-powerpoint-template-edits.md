# Walkthrough 2 — PowerPoint master-slide edits to 2025-CSI-PPT-Template.pptx (T1.2)

**Who:** anyone with PowerPoint installed
**Time:** ~45 minutes the first time; ~10 minutes for incremental tweaks
**Output:** updated `01_Analysis/00-Scripts/output/template/2025-CSI-PPT-Template.pptx` committed and pushed
**Why:** programmatic rendering covers most of the design rules, but a few rules (title font on layouts that don't have a programmatic override, locked margins, picture placeholder positions) live in the template master and have to be set in PowerPoint.

Read `docs/deck/TEMPLATE_LAYOUT_AUDIT.md` once before starting — it's the source of truth for which subtasks need PowerPoint and which are already programmatic.

---

## Step 0 — Pull, back up, open

```
git pull
```

Make a backup before you touch anything:

```
copy 01_Analysis\00-Scripts\output\template\2025-CSI-PPT-Template.pptx 01_Analysis\00-Scripts\output\template\2025-CSI-PPT-Template-backup.pptx
```

Open `01_Analysis\00-Scripts\output\template\2025-CSI-PPT-Template.pptx` in PowerPoint.

Switch to **Slide Master view:** View ribbon → **Slide Master**. The left rail shows the master at top, then all 20 layouts beneath.

---

## Step 1 — T1.2.3: title placeholder font on all 20 layouts

For each of the 20 layouts in the left rail:

1. Click the layout in the left rail
2. Click into the **title** placeholder (the box at the top of the layout)
3. Select all text in the placeholder (Ctrl+A inside the box)
4. On the Home ribbon set:
   - Font: **Arial**
   - Size: **24** (matches SLIDE_DESIGN.md §4)
   - Bold: **on**
   - Color: **#1E3D59** (Home ribbon → font color dropdown → More Colors → Custom tab → Hex `1E3D59`)
5. Move to the next layout

Layouts 4 (`LAYOUT_SECTION`), 5 (`LAYOUT_SECTION_ALT`), 6 (`LAYOUT_SECTION_GRAY`) — the section divider layouts — are programmatically overridden at render time (`_build_section_slide` paints navy background + sized text directly). You can skip these or do them anyway as belt-and-braces.

Layouts 17-19 (RPE/ARS/ICS title slides) are branded — leave their existing title font/size/color **alone**. Just confirm you didn't accidentally change them.

---

## Step 2 — T1.2.4: footnote placeholder (optional — programmatic covers this)

`_add_footer_band` paints the footer directly on every non-title/section slide. The placeholder is only relevant if someone authors a slide outside the pipeline.

If you want belt-and-braces, on each layout that doesn't already have one:

1. Insert ribbon → Text Box
2. Draw at `left=0.5"`, `top=7.0"`, `width=12.33"`, `height=0.5"`
3. Font Arial 8pt, color `#999999`
4. Right-click → Format Shape → Size & Properties → check "Lock aspect ratio" and uncheck "Allow text to overflow shape" (PowerPoint doesn't have a true lock; this minimizes accidental moves)

Otherwise skip this step.

---

## Step 3 — T1.2.5: lock margins to 0.5" all sides

PowerPoint doesn't have a "lock layout" command. The closest you get:

1. On each layout, click any content placeholder (title, body, picture)
2. Format ribbon → Size & Properties → confirm position is `left ≥ 0.5"`, `top ≥ 0.5"`, and (slide width 13.33" − left − width) ≥ 0.5", same for height
3. If any placeholder violates the rule, drag it to the right position with the Position fields

This is a discipline check, not a software constraint. The audit doc lists this as "MANUAL discipline check" for that reason.

---

## Step 4 — T1.2.8: verify picture margins on layouts 13, 14, 15

These layouts are used by `multi_screenshot` and combo_2up. Confirm placeholder positions match what the code expects:

| Layout | Picture placeholder positions |
|---|---|
| 13 — Picture with Content | one picture: `left=4.5"`, `top=1.0"`, `width=8.0"`, `height=5.0"` |
| 14 — 2 Pictures with Content | two pictures, each `top=1.5"`, `height=5.5"`. Left: `left=0.5"`, `width=5.5"`. Right: `left=6.5"`, `width=5.5"` |
| 15 — 3 Pictures with Content | three pictures at `top=1.5"`, `height=5.5"`. Left: `left=0.5"`. Middle: `left=4.5"`. Right: `left=8.5"`. Each `width=3.0"` |

For each layout: click each picture placeholder → Format ribbon → Size & Properties → adjust to match the table.

---

## Step 5 — Save and close Slide Master view

1. View ribbon → **Close Master View** (or Slide Master ribbon → Close Master View)
2. File → Save As → confirm the path is `01_Analysis\00-Scripts\output\template\2025-CSI-PPT-Template.pptx`
3. Confirm the file size is still under **2 MB** (right-click the file in Explorer → Properties). If it grew, you accidentally embedded something — undo until it shrinks back, or restore the backup.

---

## Step 6 — Smoke-test on a recent client (T1.2.9)

In the UI, run a recent client whose deck you trust visually. Open the resulting PPTX and confirm:

- [ ] Titles render in Arial 24pt bold navy on all content slides
- [ ] Footer band appears at the bottom of every content slide
- [ ] Section dividers are full-bleed navy (these are programmatic — should be unchanged)
- [ ] Multi-picture slides (DCTR branch comparison, mailer summary, etc.) have pictures at the right positions
- [ ] No placeholders are visibly shifted from where you set them

If anything looks wrong, restore the backup and try again.

---

## Step 7 — T1.2.10 + T1.2.11: commit

```
git add 01_Analysis\00-Scripts\output\template\2025-CSI-PPT-Template.pptx
git commit -m "feat(template): T1.2 master-slide edits per layout audit (#147)"
git push
```

Delete the backup once you've confirmed the new template is good:

```
del 01_Analysis\00-Scripts\output\template\2025-CSI-PPT-Template-backup.pptx
```

---

## When to redo this

- You change `SLIDE_DESIGN.md §4` (typography) — redo Step 1
- You add a new content slide layout that the pipeline uses — add the title font to it (Step 1) and verify picture positions if it has pictures (Step 4)
- You see titles falling back to Calibri or some other font in a shipped deck — Step 1 didn't take on that layout; redo it
