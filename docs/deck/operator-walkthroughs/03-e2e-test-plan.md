# Walkthrough 3 — End-to-end test plan (T4)

**Who:** CSM owner
**Time:** ~3 hours of compute (most of it unattended waiting for runs to finish) + 1 hour of active review
**Output:** filled-in `e2e-test-results.md` (template below) committed to `docs/deck/operator-walkthroughs/`
**Why:** before the system runs against the 70-client portfolio it has to prove out on 10 real clients including the harder cases (TXN, combined, edge-case mailer cohorts).

This walkthrough covers T4.1, T4.2, T4.3-T4.9 (spot checks), T4.10 (performance), T4.11 (doc review), T4.12 (CSM training).

---

## Pick the 10 clients

You need:
- **5 ARS-only clients** — covering at least one with a small portfolio (<2,000 eligible), one with no recent mailer campaign, one with high Reg E penetration, one with high attrition, one with multiple branches
- **3 TXN-only clients**
- **2 hybrid (combined ARS + TXN)**

If you don't have 10 candidates that hit these specifically, pick the closest available and note the mismatch in the results file.

Document your choices before running anything:

```
| # | Client ID | Client name        | Product | Why this client                           |
|---|-----------|--------------------|---------|-------------------------------------------|
| 1 | 1615      | Guardians CU       | ARS     | Multi-branch, average DCTR                |
| 2 | 1745      | Foothills FCU      | ARS     | High Reg E penetration                    |
| 3 | ...       | ...                | ...     | ...                                       |
```

---

## Run the test matrix

For each of the 10 clients, run via the UI Generate tab. **One client at a time**, not via batch mode — you want to see each run in isolation.

For each run record:

| Field | Where to find it |
|---|---|
| Start time | wall-clock when you click Run |
| End time | wall-clock when the run-log card shows complete |
| Total elapsed | end − start |
| Soft failures | "Errors-only" split-view panel count |
| Slide count (main) | run-log "Slide MANIFEST: main=N" line |
| Quality gate verdict | run-log "Quality gate: PASS/FAIL (N/10 checks)" line |
| Review summary review time | how long it took YOU to spot-check the Excel file |

Performance acceptance criteria (T4.10):
- ARS deck ≤ 5 min from click to "complete"
- TXN deck ≤ 60 min
- Combined deck ≤ 90 min
- Excel review summary ≤ 1 min after deck finishes
- Quality report ≤ 30 sec after deck finishes
- CSM review of the Excel ≤ 15 min per client

---

## Spot checks per client (T4.3-T4.9)

For each client's deck open it in PowerPoint and confirm:

- [ ] **T4.3 Visual quality** — titles all Arial 24pt navy, callouts bottom-right, footer band visible, no fallback Calibri
- [ ] **T4.4 Chart quality** — no axis label overlap, section colors applied (DCTR teal, Reg E purple, etc.), no axis title says "Values"
- [ ] **T4.5 Action titles** — pick 20 random titles across the deck. Every one contains at least one number, or is a recognized fallback. Generic titles like "DCTR by branch" are failures.
- [ ] **T4.6 Callouts** — pick 20 random callouts. Every one has metric + value at minimum. Bonus: every one has denominator + comparison.
- [ ] **T4.7 Section consolidation** — find the DCTR section. If three-slide pattern was eligible to merge, you should see one combo_2up slide instead of three individual slides; the three originals should be in the aux deck.
- [ ] **T4.8 Drop-if-empty** — open the `quality_report.txt`. Look for the `drops_logged` check. It should be PASS and the detail should list `N drop(s) recorded with structured reasons`.
- [ ] **T4.9 Quality gate** — every check in the report should be PASS, or the FAILs should be expected for the client (e.g. `preamble_correct` may fail if a TXN run uses ARS preamble length; flag the test as expected-fail rather than fix the code)

---

## Documentation review (T4.11)

After running 10 clients, open these in order:

1. `SLIDE_DESIGN.md` — is anything in the actual decks inconsistent with the rules here?
2. `docs/action_title_templates.md` — did any template's fallback fire on a client where you expected real data? That's a missing `ctx.results` path; file a ticket.
3. `docs/slide_specs/<section>.md` — do the specs match what slides actually rendered for each section?
4. `docs/deck/IMPLEMENTATION_GUIDE.md` — is the CSM workflow as documented? Anything you actually did that isn't covered?
5. `docs/deck/CODE_DOCUMENTATION.md` — accurate? Find one extension point and confirm the steps work.

Note any doc-vs-reality gaps; file each as a ticket against the relevant module.

---

## CSM training (T4.12)

The IMPLEMENTATION_GUIDE.md is the training doc. Walk a teammate through:

1. Run a client end-to-end
2. Open the 4-sheet Excel review summary
3. Read the quality report
4. Open the deck
5. Identify which slides came from a combo (the title style is different)
6. Approve or reject

Time them. Target is <15 min from "Run" click to a confident approve/reject. If they're over, the bottleneck is usually the Excel review — that's the muscle to build first.

---

## Results template

Copy this into a new file `docs/deck/operator-walkthroughs/e2e-test-results.md` and fill it in as you go.

```
# E2E test results — slide design system rollout

**Operator:** James
**Test window:** 2026-MM-DD to 2026-MM-DD
**Branch tested:** pipeline-improvement @ <commit-sha>

## Client matrix

| # | Client ID | Name | Product | Elapsed | Soft fails | Slides (main) | Quality | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | ... | ... | ARS | 4:32 | 0 | 24 | 10/10 PASS | clean |
| 2 | ... | ... | ARS | ... | ... | ... | ... | ... |
| ... |

## Performance summary

- ARS median elapsed: ___ min (target ≤ 5)
- TXN median elapsed: ___ min (target ≤ 60)
- Hybrid median elapsed: ___ min (target ≤ 90)
- Excel review time median: ___ min (target ≤ 15)

## Quality gate pass rate

- 10/10 PASS on N of 10 clients
- Failing checks (with client + reason): ...

## Spot-check failures

(One bullet per finding, with slide_id + client_id + what was wrong)

## Doc-vs-reality gaps

(One bullet per gap, with link to the doc + observed difference)

## Go/no-go recommendation

[ ] GO — system ready for 70-client portfolio
[ ] HOLD — issues blocking go-live: ...
```

Commit + push when done:

```
git add docs/deck/operator-walkthroughs/e2e-test-results.md
git commit -m "test(slide-system): T4 E2E results across 10 clients"
git push
```
