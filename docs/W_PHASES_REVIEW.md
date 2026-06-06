# W-phases review checklist

Four independent PRs are open against `main`. Each is branched off `main` and touches a disjoint set of files, so they merge in any order — but the verification each one needs is different. This doc is the single place to track what to test, in what order, and what success looks like.

**Work-PC reminder:** git doesn't run on `M:\ARS\` (network share blocks it). Use the **ZIP download** workflow per `SETUP.md` — download the merged branch as a ZIP from GitHub, extract over `M:\ARS\`, restart `Start Here.bat`, hard-refresh the browser.

---

## Recommended merge order

W1 → W2 → W3 → W4. Each builds on the prior wave's contract (law → brand → specs → UI). But none of them break if you merge in a different order — they're file-disjoint.

| # | PR | Wave | Risk | Smoke time |
|---|---|---|---|---|
| 1 | [#161](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/161) | W1 | Low | 5 min on one client |
| 2 | [#162](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/162) | W2 | Low | Visual check after one client |
| 3 | [#163](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/163) | W3 | Medium | One client + open the deck |
| 4 | [#164](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/164) | W4 | Medium | Two back-to-back runs + UI clicks |

---

## PR #161 — W1 Denominator-law enforcement

### What to check

- [ ] Run **any** ARS client through Generate. Wait for completion.
- [ ] Confirm `01_Analysis\01_Completed_Analysis\<CSM>\<period>\<client>\rates_audit.csv` exists.
- [ ] Open `run_scorecard.md` from the same directory — look for a "Denominator law" line in the anomaly flags section.
- [ ] Open `run_manifest.json` and confirm `sections[*].anomaly_flags` exists (may be `[]` on a clean run).

### Expected on first run

- `rates_audit.csv` will have **many** rows with `framework_compliant=False`. **That's not a regression.** It's the punch list — those are slides whose modules haven't stamped `denominator_label` yet. Defaults from the prefix registry catch the well-known ones (`dctr_*`, `rege_*`, etc.); the rest show empty labels until follow-up commits populate them.
- The headline numbers on the deck (DCTR rate, Reg E rate, attrition rate) should be **unchanged** from before W1. W1 enforces the law, doesn't change the math.

### Red flags

- DCTR rate jumps from ~30% to ~80% → the W1 changes broke the eligible-data path. Roll back W1.
- `branch_scorecard fallback fired` shows up in anomaly flags for every client → `ctx.subsets.eligible_data` isn't getting populated upstream. Check `pipeline/steps/subsets.py:97-99`.

### Configurable

- `pipeline/steps/audit.py:OPEN_ALLOWLIST` currently only allows `dctr_2` to use `Open` as primary denominator. If your deck legitimately frames `Open` on other slides, add them here **before** merging or the scorecard flags will be noisy.
- `pipeline/steps/audit.py:DEFAULT_BY_PREFIX` is the slide_id → denominator-label default map. Add prefixes here as the deck shape evolves.

---

## PR #162 — W2 Brand authority

### What to check

- [ ] After merging, open a fresh deck (run any client). Every navy element should be `#1A1A1A`.
- [ ] Open the analysis Excel (`<id>_<month>_analysis.xlsx`). Header row should be `#1A1A1A` navy with white text.
- [ ] Open the UI at `localhost:8000`. The header bar should look identical to before — same hex, just sourced from `brand.py`.
- [ ] Inspect any chart in `charts/*.png` — categorical series should use `CHART_PALETTE` order (navy → orange → green → red → ...).

### Expected

- No visual difference if everything was already on the canonical CSI navy. Substantial difference if any chart was rendering off-brand colors (`#1E3D59`, `#2E4057`, `#1B365D` — these were the divergent navies; all 5 now collapse to `#1A1A1A`).

### Red flags

- Chart background color changed unexpectedly → check `shared/charts.py` re-export of `COLORS`.
- UI header bar went black or white → `--dark` CSS var was overridden somewhere.

---

## PR #163 — W3 Slide design system

### What to check

- [ ] Run any client with a complete ODD (DCTR, Reg E, attrition all populated).
- [ ] Open the deck. Find any slide whose ID maps to a spec (DCTR-MAIN-1/2/3, REGE-MAIN-1/2, OVERVIEW-MAIN-1, ATTRITION-MAIN-1/2, VALUE-MAIN-1, INSIGHTS-MAIN-1/6/8, MAILER-MAIN-AGG/REACH).
- [ ] Confirm the slide has:
  1. An **action title** at top (a complete sentence with a number, not a category like "DCTR Overall")
  2. A **callout box** at bottom-center with a hero number in CSI orange (`#F15D22`)
  3. A **footer band** at the very bottom with source attribution
- [ ] Confirm callout colors are accent orange (not navy or teal).

### Expected

- ~14 slides get the action-slide layout. Everything else falls back to today's behavior (legacy `_build_screenshot_slide`).
- Different clients should produce **different sentences with different numbers** on the same slide_id. If two clients give identical action titles, the spec isn't binding to `ctx.results` correctly — check the input dotted-path in the YAML matches what the analytics module is actually writing.

### Red flags

- Action title shows literal `{l12m_rate:.0%}` instead of a percentage → input didn't resolve. Check the module is writing the key (`ctx.results.dctr_3.insights.dctr` must exist).
- Callout overlaps the chart → the chart isn't shrinking to make room. Check `_build_screenshot_slide` `max_height` logic (line ~530).

### Configurable

- All specs live in `docs/slide_specs/*.yml`. Edit a `action_title` template and re-run; no Python change needed.
- `competition.yml` + `txn_exec.yml` are intentionally stubs — they need a TXN-results adapter first (documented inline). Don't expect spec-driven titles on those sections yet.

---

## PR #164 — W4 CSM experience

### What to check

1. **Run Quality panel** (the W1+W4 integration)
   - [ ] Run any client. After completion, scroll down on the Generate tab.
   - [ ] Look for the "Run Quality" panel below the warnings section.
   - [ ] Confirm: verdict badge (Ship / Investigate / Review flags), rates audited count, law violations count, anomaly flags count, manifest status.
   - [ ] Click "Anomaly flags" details — should list any WARN flags.
   - [ ] Click "Denominator-law violations" details — should list non-compliant slides.

2. **Deck Shape editor**
   - [ ] Switch to Results tab → click **Deck Shape** button (top-right of page).
   - [ ] Panel opens with every slide from `SLIDE_MANIFEST.xlsx`. Counts in the header should match what the manifest summary line shows in the pipeline log.
   - [ ] Filter for "DCTR" — only DCTR slides show.
   - [ ] Toggle any slide's decision (Y → A → N → blank). The Save button enables.
   - [ ] Click **Save**. Wait for the success message.
   - [ ] Open `SLIDE_MANIFEST.xlsx` in Excel — confirm the change persisted.
   - [ ] Click **Rebuild deck**. Wait ~5-10 seconds.
   - [ ] Open the rewritten `.pptx` in `02_Presentations\<CSM>\<period>\<client>\` — confirm slide shape reflects the new decisions.

3. **Format-tab checklist parity**
   - [ ] Switch to Format tab. Pick a CSM + period that has raw ODDs.
   - [ ] Click **Format ODD Files**. Confirm the 5-stage checklist appears (Locate → Unzip → Format → Stage → Save).
   - [ ] On completion, confirm the completion card appears with stat tiles and shortcut buttons.

4. **ODD temp-copy cache**
   - [ ] Run any client.
   - [ ] In the log, look for "Copying \<name\> to local temp for faster read..." on the first run.
   - [ ] Re-run the same client immediately (without restarting `Start Here.bat`).
   - [ ] In the log, look for "Cache hit: reusing local copy of \<name\>" on the second run.
   - [ ] Second run should complete materially faster (3-5 min savings on the M: share).

### Expected

- Run Quality panel hides itself silently if a run is from before W1 merged (no `rates_audit.csv`). Backward compatible.
- Deck Shape editor works whether or not the manifest file exists. Missing manifest → "SLIDE_MANIFEST.xlsx not found" message.
- ODD cache invalidates when source mtime changes. Re-format the ODD → cache miss on next analysis run.

### Red flags

- Rebuild deck endpoint returns 404 → `run_report.json` for this client+period is from a pre-W4 run (no `chart_path` field). Re-run the full analysis once after W4 merges to regenerate.
- Save manifest returns 400 → check browser console; payload shape is `{updates: {slide_id: decision}}`, not a raw dict.

---

## Combined success criteria

After all four PRs are merged and one full end-to-end client run completes:

- [ ] DCTR rate on slide DCTR-MAIN-1 is unchanged from pre-W1 deck (~30% Eligible-anchored)
- [ ] All navy elements in the deck and UI are `#1A1A1A` exactly
- [ ] At least one slide shows a spec-driven action title with embedded numbers
- [ ] Completion card shows a Run Quality verdict with N violations + N flags
- [ ] Deck Shape editor opens, saves, and triggers Rebuild without errors
- [ ] Second back-to-back run of the same client hits the ODD cache

If all six boxes are green, all four waves are landing as designed.

---

## Test counts at merge time

| Suite | Before W1 | After all four | Delta |
|---|---|---|---|
| `01_Analysis/00-Scripts/tests/` | 56 | 64 | +8 |
| `05_UI/tests/` | 0 | 7 | +7 (new harness) |
| **Total** | **56** | **71** | **+15** |

All green at every step.

---

## Remaining work after these four PRs

1. **Chart-PNG content-hash cache** — sized for its own PR. Hook at every chart call site (not at `save_chart_png` where the figure is already rendered). Foundation in flight on `feat/chart-cache` if/when it lands.
2. **TXN-results adapter** for competition + txn_exec sections — would unblock the final 2 slide specs.
3. **Per-month mailer generator** (`MAILER-MONTH-Jan26`, etc.) — walks `ctx.results.monthly_summaries`, doesn't need new infra.
4. **Stamp `denominator_label` on the 40+ ARS modules** to drive the W1 audit's `framework_compliant=False` count toward zero. Each module is a small commit.
