# Implementation Guide — ARS Slide Design System

**Audience:** the CSM running the pipeline on the work PC at `M:\ARS\`.
**Parent issue:** #160 (T4+T5).
**Companion docs:** `ARS_SLIDE_DESIGN_CHECKLIST.md`, `SLIDE_DESIGN.md`, `phase-18-operator-guide.md`.

## What got built

This guide covers the slide design system rollout from PRD #145. The full system breaks into three tiers; everything noted below ships on `pipeline-improvement`.

| Tier | Tickets | What it does |
|---|---|---|
| Tier 1 | #146–#149 | Locks the design spec, audits the template, aligns chart palette + helpers, introduces the structured `CalloutBox` |
| Tier 2 | #150–#155 | 28-template action title catalog + dynamic populator + section dashboard combos + product-mode preambles + per-section specs + structured drop-if-empty |
| Tier 3 | #156–#159 | CSM Excel review summary, 10-check automated quality gate, run-metadata JSON, pipeline integration (5 outputs per run) |

After every run the operator now gets:

```
M:\ARS\01_Analysis\01_Completed_Analysis\<csm>\<month>\<client>\
├── <client>_<month>_ars_deck.pptx           ← main PPTX
├── <client>_<month>_ars_aux_deck.pptx       ← aux PPTX (if applicable)
├── <client>_<month>_review_summary.xlsx     ← 4-sheet CSM review summary
├── <client>_<month>_quality_report.txt      ← pass/fail on 10 checks
├── <client>_<month>_quality_report.json     ← same, machine-readable
├── <client>_<month>_meta.json               ← run audit trail
└── <client>_<month>_run_report.json         ← per-slide success status (legacy)
```

## CSM workflow

The CSM always works through the UI; nothing below requires a terminal.

### Before the run
1. Confirm the data dump for the client is in `M:\<CSM>\OD Data Dumps\<month>\<client_id>_ODDD.zip` (or use the manual data-drop button on the Format tab).
2. Open the UI at `http://localhost:8000` (double-click `Start Here.bat` if it isn't running).

### Running a client
1. **Generate tab.**
2. Pick CSM / Month / Client / Product (typically ARS or Combined).
3. Optional: expand **Sections** to deselect any sections the client doesn't need.
4. Optional: enable **Local copy** if you want the deck saved to a fast local folder in addition to M:.
5. Click **Format + Analyze + Build PPTX**.
6. Watch the run-log card. When complete you'll see:
   - A green completion summary with deck slide count
   - The Tier 3 outputs listed at the bottom of the log (`Review summary: ...`, `Quality gate: PASS (10/10 checks)`, `Metadata: ...`)
   - Any soft failures listed in the errors-only side pane (enable **Split view**)

### Reviewing the output
1. **Open the deck first.** Visually scan that title slide → section dividers → callouts → footer band all look right.
2. **Open `[client]_[month]_review_summary.xlsx`.** Four tabs:
   - **Slide Inventory** — every slide that landed plus every drop. Filter by Status = "dropped" to see what was excluded and why.
   - **KPI Summary** — the headline metrics. Cross-check against your gut sense of the client.
   - **Callout Text** — every callout's metric + value + denominator + comparison. This is the fastest way to spot a number that doesn't pass the smell test.
   - **Data Quality Flags** — high-severity items in light red. If there's anything here, address before sending the deck.
3. **Open `[client]_[month]_quality_report.txt`.** Look at the top line:
   - `Overall: PASS` → safe to send pending the visual check
   - `Overall: FAIL` → scan the FAIL lines below; the gate prints the specific reason for every failure
4. If anything's wrong: fix and rerun. The cache invalidation on run-start + run-complete (Phase 17.4) means the dropdown picks up the new run immediately.

### Performance targets

| Step | Target | Where to check |
|---|---|---|
| Format + Analyze | ~5 min (ARS), ~1 hr (TXN/Combined) | Run log elapsed timer |
| Review summary Excel | < 1 min | "Review summary:" line in run log |
| Quality report | < 30 s | "Quality gate:" line in run log |
| Metadata JSON | < 5 s | "Metadata:" line in run log |

If any of these regress materially, file a ticket — the optimizations needed are different per step.

## Operator-blocked items from T4+T5

These were called out in the checklist but require the operator (not code) to land:

- **T4.1 E2E on 10 client decks (5 ARS, 3 TXN, 2 hybrid).** Run the picks on real clients and confirm visual + quality-gate pass.
- **T4.2 Time the CSM workflow.** Target <15 min from "Run" click to "deck approved". The Tier 3 outputs are designed to compress the verification step.
- **T4.3–T4.9 Spot checks.** Visually verify fonts, colors, callouts, dividers, drops on a sample of slides. Anything off → log it as a bug against the relevant Tier 1/2 ticket.
- **T4.12 + T5.10 CSM sign-off.** Approve the system for the 70-client portfolio. Until this happens SLIDE_DESIGN.md §15 remains "pending" and the operator should treat the rollout as soft-launch.
- **T5.6 Video walkthrough.** Record yourself doing one client end-to-end so new operators have something to follow.
- **T5.7 Quick-reference card.** A one-page printable CSM checklist (open Excel review summary, scan Slide Inventory, scan KPI Summary, check Data Quality Flags, approve/reject). Can be derived from this guide's "Reviewing the output" section.

## Updating the system

| Change | Edit | Who |
|---|---|---|
| Slide title wording | `docs/action_title_templates.md` | Analyst |
| Slide-id → template mapping | `01_Analysis/00-Scripts/output/deck_builder.py::_SLIDE_TEMPLATE_MAP` | Backend |
| Section colors | `01_Analysis/00-Scripts/shared/charts.py::SECTION_COLORS` | Backend |
| Combo patterns | `01_Analysis/00-Scripts/output/section_consolidator.py::COMBO_PATTERNS` | Backend |
| Preamble content | `01_Analysis/00-Scripts/output/deck_builder.py::_preamble_ars/_preamble_txn/_preamble_hybrid` | Backend |
| Quality checks | `01_Analysis/00-Scripts/output/quality_gate.py` | Backend |
| Drop rules | `01_Analysis/00-Scripts/pipeline/steps/generate.py::detect_section_drops` | Backend |
| Design rules | `SLIDE_DESIGN.md` | Designer (+ CSM sign-off) |

Edit-rule: **SLIDE_DESIGN.md is authoritative.** Any code that deviates from the doc is a bug in the code, not the doc. Sequence is always: update the doc → CSM signoff → update the code.
