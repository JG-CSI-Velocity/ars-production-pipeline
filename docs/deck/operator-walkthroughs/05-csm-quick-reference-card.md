# CSM Quick Reference — One-page checklist

> **How to print:** open this file in any markdown previewer (VS Code, Marked, Typora, GitHub web view) and File → Print → A4 portrait. The whole card fits on one side.

---

## Before the run
- [ ] Velocity Pipeline open at `http://localhost:8000` (if not — double-click `Start Here.bat`)
- [ ] Data dump for the client is in `M:\<CSM>\OD Data Dumps\<month>\` **OR** use the Format tab's manual data-drop button
- [ ] Browser hard-refreshed if you just pulled new code (Ctrl + Shift + R)

## Running
- [ ] Generate tab → CSM, Month, Client picked
- [ ] Product = ARS / TXN / Combined per the engagement
- [ ] (Optional) expand **Sections** and uncheck anything you don't want
- [ ] Click **Format + Analyze + Build PPTX**
- [ ] **Split view** toggle ON so errors-only side panel is visible

## When the run finishes — five files written

In `M:\ARS\01_Analysis\01_Completed_Analysis\<csm>\<month>\<client>\`:

| File | What it's for |
|---|---|
| `<client>_<month>_ars_deck.pptx` | **The deck** — what you ship to the client |
| `<client>_<month>_ars_aux_deck.pptx` | Detail slides routed away from main deck |
| `<client>_<month>_review_summary.xlsx` | **You verify here first** |
| `<client>_<month>_quality_report.txt` | Pass/fail on 10 checks |
| `<client>_<month>_meta.json` | Audit trail |

## Review the Excel — 4 sheets, in this order

**Sheet 1: Slide Inventory.** Filter Status column.
- "ok" rows: slide is in the deck
- "dropped" rows: slide was excluded; check Drop reason column

**Sheet 2: KPI Summary.** Eyeball the values.
- DCTR, Reg E, Attrition: feel right for this client?
- Value column populated for each metric you expect

**Sheet 3: Callout Text.** Every callout printed.
- Every Metric + Value populated
- (Bonus) Denominator + Comparison populated

**Sheet 4: Data Quality Flags.** Light red = high-severity.
- ANY high-severity row → fix before sending

## Quality report — read top to bottom
- `Overall: PASS` → safe to send pending visual check
- `Overall: FAIL` → scan FAIL lines, address each

## Open the deck — visual check
- [ ] Titles are Arial 24pt navy (not Calibri)
- [ ] Every action title has at least one **number** in it
- [ ] Callout box bottom-right of every chart slide
- [ ] Footer band at bottom of every content slide
- [ ] Section dividers full-bleed navy w/ section number + lead-in

## Approve when
- [ ] Quality report PASS
- [ ] No high-severity flags in Excel sheet 4
- [ ] Callouts on sheet 3 all populated
- [ ] Visual check above all pass

## Reject (and file ticket) when
- ANY action title is generic (no number, not a known fallback)
- ANY callout missing metric+value
- KPI Summary value doesn't match your gut
- Quality report FAIL on a check you don't expect

## Emergency stop
- Red **Stop** button on Generate tab → confirm dialog → SIGTERM → SIGKILL fallback after 3s

## Where things live
- Operator workflow → `docs/deck/IMPLEMENTATION_GUIDE.md`
- Design rules → `SLIDE_DESIGN.md` at repo root
- Module docs (devs) → `docs/deck/CODE_DOCUMENTATION.md`
- 12-week PRD checklist → `docs/deck/ARS_SLIDE_DESIGN_CHECKLIST.md`

---
*Generated as part of T5.7. Update this card when SLIDE_DESIGN.md version bumps.*
