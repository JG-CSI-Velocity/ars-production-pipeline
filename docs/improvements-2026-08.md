# Improvement Backlog — 2026-08 Review

Produced during the 2026-08-05 full-repo review (issue triage + e2e test +
persona audits). Three buckets: **iterations** (sharpen what exists),
**efficiencies** (same output, less cost), and **new analyses** (net-new value
for the client deck). Items marked `[v3]` should land in the rewrite waves
rather than the legacy engine.

---

## 1. Iterations on what exists

### 1.1 Drop-don't-zero slide policy
When a section's data gates off (no mailer data, no Reg E column), slides ship
title-only or with confident $0/0.0% stats. Policy change: a slide whose
producer returned no usable frame is *dropped* and listed on a single "Not
included this month (and why)" appendix slide. Kills the empty_body class and
the zero-shaped-fallback class in one move. `[v3: make it a section-contract
rule — a Section either yields a complete slide or a skip-with-reason]`

### 1.2 Auto-drafted Executive Summary
The most-read slide is currently a blank the operator fills by hand. Everything
needed is already in `ctx.results` (rates, deltas, opportunity dollars).
Auto-draft 4-6 bullets (top movement, top risk, top opportunity, program ROI
line) and let the operator edit — never present a blank. UI: "Regenerate
summary" button on the Generate tab.

### 1.3 Headlines onto slides, not just notes
Insight-first titles exist in the YAML specs, but most slide IDs route to the
bare `screenshot` builder, so computed headlines land in speaker notes only.
Rewire `SLIDE_LAYOUT_MAP` to the `chart_narrative` builder (already exists) for
the main-deck slide IDs. (Ref: `reference_deck_slide_building_blocks`.)

### 1.4 Deck length law
Enforce the 25-slide main / 60-with-appendix budget mechanically: section
budgets in the registry, overflow demoted to appendix, QA gate fails on budget
breach (it already checks 60). The 339-slide TXN deck makes the product look
unedited.

### 1.5 Min-N floors + shared branch-name mapping (from #250)
One shared helper for branch display names (three implementations disagree
today) and one MIN_BRANCH_N constant applied to every best/worst/top-10
ranking. Small, kills a whole embarrassment class ("1-account branch at 100%").

### 1.6 ic_rate / assumption-change footnotes
When a config assumption (ic_rate, NSF fee) differs from the prior run's
manifest, stamp an automatic footnote on affected slides: "Assumes X¢
interchange (was Y¢ in May)". The 4.3× opportunity-dollar jump should never
reach a client meeting unexplained.

---

## 2. Efficiencies

### 2.1 Kill the run-twice pattern (ARS then TXN)
The two products load the same ODD separately. `[v3]` already solves storage
(DuckDB staging); until cutover, `run_modules` shows the pattern — one load,
N section decks. Extend to full ARS+TXN combined runs from the UI.

### 2.2 Incremental TXN month append
A new month adds one file, yet the 12-month combined_df rebuilds from scratch
whenever any file is newer than the cache. Store per-file parquet keyed by
content hash (v3 staging already does exactly this) so a monthly run only
parses the new file. `[v3: freebie after odd_store/txn ports]`

### 2.3 Chart render pool
Matplotlib rendering is single-threaded per section; sections are independent
after txn_setup. A 4-worker process pool over *sections* (not scripts) would
cut wall-clock on the 8-core work PC meaningfully. Measure first via the stage
timings in run_manifest (added in #254) before committing.

### 2.4 One venv contract
This review found the dev venv missing seaborn/httpx (32 test failures) — now
declared as the `[test]` extra. Follow-through: CI job should `pip install
-e .[test]` so the declared contract is what CI actually exercises.

### 2.5 Delete the `_TBD_` review docs or finish them
`docs/deck/txn-deck-review.md` KEEP/NIX columns are all `_TBD_`. Either run the
review (it gates 1.4) or delete the file — a half-filled review document reads
as abandoned quality control.

---

## 3. New analyses (highest value)

### 3.1 Peer benchmarking layer ("vs. your peer group")
Every metric today is client-vs-itself. The shop runs the same pipeline for
many FIs; aggregate anonymized distributions (median/quartiles of DCTR, Reg E
opt-in, attrition, interchange per active card) into a peer file, and every
headline gains "…vs 62% peer median". Single biggest credibility upgrade an
exec sees. Needs: a small cross-client aggregate store `[v3: DuckDB makes this
trivial]` + an anonymization rule (min 5 FIs per cell).

### 3.2 Deposit-flight early warning (leading, not lagging)
Attrition reports who already left. The TXN data shows who is *leaving*:
direct-deposit stopped, external-transfer (ACH out to Chase/Ally/fintech)
ramping, card spend migrating. Score accounts on 90-day trajectory; output =
one slide (count + $ at risk + trend) plus an actionable branch-level list in
`cross_sell_lists/`. Reuses competition merchant tagging + payroll detection —
mostly assembly, not new detection.

### 3.3 Primacy score
Banks care about "primary financial institution" status. Combine: direct
deposit present, debit swipes/month ≥ N, bill-pay/ACH origin, balance
stability → one 0-100 primacy score per account. Trend it monthly; segment the
deck's rate metrics by primacy tier. This reframes the whole deck from "cards
issued" to "relationships owned" — and it's computable from data already
loaded. (The PFI proposal in docs/pfi/ is this idea; promote it from parked
HTML to a v3 section spec.)

### 3.4 Cohort-quality read on the mailer program
The mailer analysis answers "did they respond"; it should answer "were they
worth acquiring": 6/12-month survival, balance build, swipe activation by
acquisition cohort vs branch-opened controls. ICS_cohort already computes
survival machinery (lifelines) — generalize it from ICS to any acquisition
source. Directly monetizes the program the shop sells.

### 3.5 Interchange yield decomposition
Interchange $ = swipes × $/swipe × interchange rate. Decompose monthly change
into volume / ticket-size / mix (PIN-vs-sig) components so the deck can say
*why* interchange moved, not just that it did. Small module; big "so what".

### 3.6 Anomaly sentry (ops, not deck)
A post-run check comparing every headline metric to the client's own history
(z-score on 12-month series). Anything |z| > 3 gets flagged in the UI run
report before a human presents it. Catches the "27K competitors" and
"0.4% mailer lift" class automatically. Cheap: history lives in run manifests.

---

## Sequencing recommendation

1. **Now (legacy, small):** 1.1 drop-don't-zero, 1.3 headline rewiring, 1.5
   min-N + branch helper, 1.6 assumption footnotes, 3.6 anomaly sentry.
2. **Wave 1-adjacent `[v3]`:** 1.2 exec summary, 2.2 incremental append, 3.5
   interchange decomposition (good pilot section for the new engine).
3. **After v3 store exists:** 3.1 peer benchmarks, 3.2 deposit-flight, 3.3
   primacy score (they all want the DuckDB cross-client store).
