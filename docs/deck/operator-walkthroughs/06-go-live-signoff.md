# Walkthrough 6 — Go-live sign-off (T5.10)

**Who:** CSM owner
**Time:** 30 minutes (mostly reading)
**Output:** filled-in `go-live-signoff.md` in this directory, committed and pushed; #145 comment recording the approval; CHECKLIST T5.10 box checked
**Why:** the last gate before the system runs on the full 70-client portfolio. By signing off you're confirming you've validated everything below and you accept ownership of the production workflow.

This is not ceremonial — if any item below isn't true, **don't sign off**. Open tickets for each gap and finish the rollout properly.

---

## What you're signing off on

This is the contract. Read each bullet; check the box if it's true today; leave it unchecked if it isn't.

### Design contract (Tier 1)

- [ ] **SLIDE_DESIGN.md is locked** at version 1.0 with my sign-off in §15 (Walkthrough 1).
- [ ] **Template master-slide edits** per Walkthrough 2 are landed in `01_Analysis/00-Scripts/output/template/2025-CSI-PPT-Template.pptx` and committed.
- [ ] **Chart palette** matches §5 — I've verified by running a client and confirming primary navy is `#1E3D59`, accent teal `#17A2B8`, and section accents per §5.1.
- [ ] **Callout boxes** appear on every chart slide of a sample client deck with hero KPI rendered correctly.

### Intelligent assembly (Tier 2)

- [ ] **Action title catalog** at `docs/action_title_templates.md` has 28 templates and I've reviewed them for client-realistic language.
- [ ] **Populator works** — at least 90% of slides in a sample run carry a number-bearing action title (no generic fallbacks). Hand-checked across 5 ARS runs.
- [ ] **Section combos** merge as expected — DCTR section in a sample client deck shows one combo_2up slide instead of the three source slides, and the three originals appear in the aux deck.
- [ ] **Preamble variants** — confirmed ARS preamble = 13 slides, TXN = 5, Hybrid = 8 in one sample run per mode.
- [ ] **Section specs** at `docs/slide_specs/<section>.md` are accurate for the current pipeline output.
- [ ] **Drop-if-empty** — ran a sample with a section that should drop (e.g. ARS run with no ICS data) and confirmed the section absence is recorded in `ctx.dropped_slides` with the right reason.

### Automation + QA (Tier 3)

- [ ] **Excel review summary** writes correctly — 4 sheets populated, sheet 4 surfaces high-severity flags in light red.
- [ ] **Quality gate** runs to completion in <30s and reports 10/10 PASS on at least 7 of 10 E2E test clients (Walkthrough 3).
- [ ] **Metadata JSON** is valid JSON, contains every field documented in `output/metadata_writer.py`, and survives a `json.loads()` round-trip.
- [ ] **Pipeline integration** — every run produces all 5 output files, or a missing file is explained by a logged failure.

### E2E testing (Walkthrough 3)

- [ ] **10 client decks** tested per `03-e2e-test-plan.md` (5 ARS, 3 TXN, 2 hybrid)
- [ ] **Performance** acceptable across all 10:
   - ARS median elapsed ≤ 5 min
   - TXN median elapsed ≤ 60 min
   - Hybrid median elapsed ≤ 90 min
- [ ] **CSM review workflow** times in at <15 min per client
- [ ] **Spot checks** all pass — fonts, colors, callouts, dividers, drops, action titles (T4.3–T4.9)

### Handoff (Walkthroughs 4–5)

- [ ] **Video walkthrough** recorded (Walkthrough 4) and either committed as mp4 or URL in README
- [ ] **Quick-reference card** at `docs/deck/operator-walkthroughs/05-csm-quick-reference-card.md` printed and posted at workstation
- [ ] **Team trained** — at least one teammate has completed the workflow end-to-end without my help, in <15 min

### Open issues review

- [ ] All Tier 1–3 sub-issues (#146–#160) are closed.
- [ ] Open issues filed during E2E testing (Walkthrough 3 "Spot-check failures" + "Doc-vs-reality gaps") are either fixed or have a decided disposition (defer / accept / fix-later with owner).
- [ ] No high-severity bug is open against `output/deck_builder.py`, `output/action_title_populator.py`, `output/quality_gate.py`, or `pipeline/steps/generate.py`.

---

## Sign-off

If every box above is checked, copy this block into a new file `docs/deck/operator-walkthroughs/go-live-signoff.md`, fill in the date and your name, commit, push.

```markdown
# Go-live sign-off

**System:** ARS Slide Design System v1.0
**Signed off by:** James Gilmore (CSM owner)
**Date:** 2026-MM-DD
**Branch at sign-off:** pipeline-improvement @ <commit-sha>
**Scope:** Production runs for the full 70-client portfolio

I have validated the rollout per docs/deck/operator-walkthroughs/06-go-live-signoff.md.
All sub-issues #146-#160 are closed. E2E test results are in
docs/deck/operator-walkthroughs/e2e-test-results.md. Video walkthrough
is at <path or URL>. Quick-reference card has been distributed.

The system is approved for production use against the 70-client
portfolio starting <month>.

Known caveats / deferrals:
- (List any deferred design decisions, known gaps with workarounds,
  follow-up tickets to land within N weeks. If none, write "none".)
```

Commit and push:

```
git pull
git add docs/deck/operator-walkthroughs/go-live-signoff.md
git commit -m "sign(go-live): approve slide design system v1.0 (T5.10 / #160)"
git push
```

Then comment on the parent issue:

```
gh issue reopen 145 --comment "Go-live signed off — see docs/deck/operator-walkthroughs/go-live-signoff.md"
gh issue close 145 --comment "Production launch approved by CSM."
```

---

## If you can't sign off today

That's fine and is the right call if any box is unchecked.

For each unchecked box, do one of these:

| Severity | Action |
|---|---|
| Cosmetic gap | File a ticket against the relevant module; **don't block sign-off** if the system still ships acceptable decks |
| Functional bug | File a ticket; **block sign-off** until it's fixed |
| Design ambiguity | Add a deferred-decision row to SLIDE_DESIGN.md §15 with the open question; sign off with the deferral noted explicitly |

Bring this doc back when the blockers are resolved.

---

## After sign-off — what changes

- The system officially supports the 70-client portfolio.
- Operator workflow is governed by `docs/deck/IMPLEMENTATION_GUIDE.md`.
- Bug intake: GitHub issues against this repo. Tag them with the affected Tier (1/2/3) so the right person looks.
- Quarterly review: re-run E2E (Walkthrough 3) every quarter to catch drift. Bump SLIDE_DESIGN.md version if any rule changes.
