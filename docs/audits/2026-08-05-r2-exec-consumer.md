# Exec-Consumer Audit — "Marcus" (Client Executive / CSI Account Executive) — Round 2

- **Persona:** Bank/CU executive receiving the monthly deck, plus the CSI AE presenting it
- **Date:** 2026-08-05 (round 2, fresh eyes)
- **Scope:** Verify the round-1 trust-layer dispositions in current code; assess the #263
  routing decision; sanity-check the #263 checklist; new findings on the QA gate and
  headline path.
- **Method:** Code read of `deck_qa.py`, `pipeline/steps/audit.py`, `analytics/value/analysis.py`,
  `analytics/txn_wrapper.py`, `output/deck_builder.py`, `output/headlines.py`,
  `05_UI/app.py`, `05_UI/index.html`; the numeric-sanity regexes were executed against
  constructed slide texts (results reproduced below); `gh issue view 263` read verbatim.

---

## Part 1 — Verification verdicts

### V1. deck_qa `check_numeric_sanity` — would it catch the A9.6 0/0 bar and the A9.9 0%-vs-29% split?

**Verdict: NO for the artifacts as they actually shipped; the check's live coverage today is close to zero. The real protection is the appendix demotion, not the QA gate.**

The checks themselves are correctly written for what they claim to do
(`01_Analysis/00-Scripts/output/deck_qa.py:155-179`): `zero_denominator` matches any
`(n / 0)` in rendered text; `implausible_split` fires when one `pct (n/d)` pair on a
slide is exactly 0.0% and another is >= 20%. I executed the regexes against constructed
slide texts:

| Constructed slide text | Result |
|---|---|
| `"Closure rate: 0.0% (0 / 0)"` | CAUGHT (zero_denominator) |
| `"With debit: 0.0% (4 / 14,642)"` + `"Without: 29.2% (4,231 / 14,499)"` same slide | CAUGHT (implausible_split) |
| `"With debit retention: 0.0%"` + `"Without: 29.2%"` (plain %, no n/d pair) | **SLIPS THROUGH** (by design, deck_qa.py:161-163) |
| `"With debit: 0.03% (4 / 14,642)"` vs `"29.2% (...)"` (near-zero, not exactly 0.0) | **SLIPS THROUGH** |
| `"0.0% (0 / 8,000)"` vs `"18.0% (...)"` (split below the 20% bar) | **SLIPS THROUGH** |
| The two arms on two different slides | **SLIPS THROUGH** (per-slide accumulator, deck_qa.py:166) |
| `"Total Opportunity: $0"` hero stat | **SLIPS THROUGH** (no dollar-zero check at all) |
| Any number baked into a chart PNG | **SLIPS THROUGH** (documented, deck_qa.py:52-53) |

The decisive fact: **the actual A9.6 and A9.9 numbers were never pptx text.** The
`"x% (n / d)"` stat strings are matplotlib bar annotations rendered inside the PNG —
`analytics/attrition/impact.py:65,112` and `analytics/attrition/dimensions.py:460`
(`f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})"` passed to `ax.text`/bar labels).
A9.6 routes to the bare `screenshot` builder and A9.9 to `screenshot_kpi`
(`deck_builder.py:1351,1354`), so the slide-text surface deck_qa reads never contains
those stats. I then searched every deck-text producer (kpis, spec callouts, footers,
`docs/slide_specs/*.yml`) for the `"x% (n / d)"` shape: **nothing currently emits it
into a text frame.** The pattern exists only in PNG annotations and stdout logs. So
`check_numeric_sanity` guards a text format that no current builder writes — it is
regression insurance for future spec callouts, not a gate on today's deck.

What actually protects the client this month is `ATTRITION_APPENDIX_IDS`
(`deck_builder.py:1491-1504`): A9.6 and A9.9 are demoted to the appendix, with an
explicit comment on A9.9 ("debit flags are blanked at close... Misleading in the main
story"). That is a hand-placed patch on two known slide IDs, not a systemic check.
The run-side pre-render version of these checks on `ctx.results` (round 1's suggested
fix) does not exist anywhere in the codebase.

Also note the gate's teeth: `_run_deck_qa` (`deck_builder.py:2273-2327`) is invoked on
both main and aux builds (lines 2443, 2758) but is explicitly advisory — "a deck that
exists beats no deck." A FAIL writes `<stem>_quality_report.txt`, a manifest flag, and
a stdout line; the deck still lands in the delivery folder with nothing on or in the
file marking it as failed.

### V2. `pipeline/steps/audit.py` + `analytics/value/analysis.py` — the A11 relabel

**Verdict: A11.1 genuinely fixed; A11.2 is still one layer off, and the audit now
certifies the mislabel as compliant.**

- **A11.1 (Debit Card Value): confirmed fixed.** `value/analysis.py:440-453` stamps
  `denominator_label="Eligible Personal"` plus `denominator_n`, with a comment citing
  the r1 data-engineer finding. The base (`ctx.subsets.eligible_personal` narrowed to
  L12M-active) matches the label. Good.
- **A11.2 (Reg E Value): NOT fixed.** The computation base is
  `ep[_is_debit_yes(ep[dc_col])]` — eligible personal **with a debit card**
  (`value/analysis.py:466-488`). Under the 4-layer law that is
  "Eligible Personal w/Debit" (exactly the base audit.py itself assigns to every A8/Reg E
  slide at `audit.py:58-62`). But the A11.2 `AnalysisResult` at
  `value/analysis.py:662-670` stamps **no** `denominator_label`, so the audit falls back
  to the `"A11"` prefix default `"Eligible Personal"` (`audit.py:74-77` — whose comment
  even asserts "A11.1, A11.2"). Because "Eligible Personal" is in `LAW_LABELS`, the row
  is written to `rates_audit.csv` as `framework_compliant=True`. This is the precise
  defect class round 1 flagged ("34% of what?"), now with a machine-generated
  certificate saying it's fine. That is worse than an unaudited mislabel: the audit
  trail an AE would point to in the room vouches for the wrong base.
- **The audit itself is real and wired**: `step_audit` runs after every deck build
  (`pipeline/steps/generate.py:230-234`), writes `rates_audit{_txn}.csv`, and raises a
  run-level WARN on violations (`audit.py:229-238`), surfaced in the scorecard and UI.

### V3. `txn_wrapper._flag_eligible_noop` — does the flag reach anything an exec-facing artifact shows?

**Verdict: the flag reliably reaches the operator; it never reaches the exec. And the
TXN rate audit remains effectively empty.**

The plumbing is sound and I traced it end to end:
`_flag_eligible_noop` (`txn_wrapper.py:745-762`) → `ctx.manifest.flag(WARN, ...)` →
run-level `anomaly_flags` in `run_manifest*.json` (`pipeline/manifest.py:177-184,203`)
→ `/api/run_quality` collects run-level and section flags (`05_UI/app.py:1359-1384`)
→ the Run Quality panel renders them (`05_UI/index.html:824-834, 1975-2031`). Both
no-op branches are covered (eligible_data unavailable, `txn_wrapper.py:785-794`; no
recognized account column, `:804-812`). Good, honest wiring — for the operator.

Three gaps from the exec's chair:

1. **No exec-facing artifact carries the flag.** The deck footer machinery exists —
   `_build_screenshot_slide` renders `footer_source` when a spec supplies one
   (`deck_builder.py:534-546,668`) — but nothing conditions footer text on
   `ELIGIBLE_FILTER_APPLIED`. A TXN slide footer can say "Eligible" while the WARN
   sits in a JSON file the client will never see. (The disposition admits this is
   OPEN; confirmed accurate.)
2. **The TXN rate audit is nominally wired but sees nothing.** TXN results are built
   with no `kpis` and no `denominator_label` (`txn_wrapper.py:548-555`), so
   `_looks_like_rate` returns False for every TXN slide (`audit.py:130-144`) and
   `rates_audit_txn.csv` is skipped with "no rate-bearing slides found"
   (`audit.py:210-212`). The `"TXN-"` prefix default at `audit.py:113` is dead code in
   practice. Round 1's "TXN denominators are not machine-verified" is still true.
3. **Manifest shadowing (minor):** `/api/run_quality` reads
   `_newest_artifact(analysis_dir, "run_manifest*.json")` (`app.py:1359`). ARS and TXN
   manifests share the folder with different suffixes; whichever run finished last
   wins the panel. An ARS re-run after a TXN run hides the TXN eligible-noop WARN.

---

## Part 2 — Was routing findings 1/2/3/5/7 to issue #263 the right call?

Short answer from the exec's chair: **routing was right for 1, 2, 3, and 7. For 5 it is
right only because the two known instances are individually patched — and one piece of
the codebase has since moved in the wrong direction.**

- **Finding 1 (blank exec slides) — routing defensible.** Auto-drafted prose that goes
  in front of a client absolutely needs JG's sign-off; a wrong auto-summary is worse
  than a blank one the operator fills. One more manual cycle is the same risk profile
  as every prior month. **But:** while the decision sits parked, the whitelist grew —
  commit `06a7428` added "All Program Results" and "Data Check Overview" to
  `_OPERATOR_FILLED` (`deck_qa.py:41-46`). #263 proposes flipping the whitelist into a
  flag; each addition entrenches the opposite policy and widens the substring-match
  hole (see N4).
- **Finding 2 (339-slide TXN deck) — routing right, urgency wrong.** Unilaterally
  cutting client deliverables without owner sign-off would repeat the trust failure
  this repo has already litigated. But the gating artifact
  (`docs/deck/txn-deck-review.md` KEEP/NIX) has been `_TBD_` since 2026-04-28 — three
  months. If a TXN deck ships to a client this cycle at 339 slides, that is a
  deal-breaker landing in a client's inbox while the fix waits on a worksheet nobody
  is filling in. #263 needs a date on the KEEP/NIX pass, or an interim mechanical cap
  (aux-deck overflow) that changes no verdicts, only packaging.
- **Finding 3 (headlines) — routing right.** Presentation taste; owner's call; no new
  wrong numbers ship because of it.
- **Finding 5 (zero-shaped fallbacks) — the closest call, and I accept it only with
  caveats.** The specific known instances are individually handled: A9.6/A9.9 demoted
  to appendix, the rege.yml key mismatch is genuinely fixed
  (`docs/slide_specs/rege.yml:14-24` now points at the real `reg_e_1` keys, with a
  correct None-vs-zero guard), and G6 drop-if-empty runs before every deliverable
  (`generate.py:210-215`). But the *class* is open: G6 drops slides with **no chart
  and no excel_data** — a zero-shaped default that still renders a chart is a "usable
  frame" and sails through, and V1 shows the QA gate cannot see numbers in PNGs. One
  more cycle is acceptable because every *known* $0 path is patched; a second new
  instance this month would ship undetected. That residual risk should be stated in
  #263, not implied.
- **Finding 7 (analyst artifacts) — routing right,** same owner-gating logic as 2. One
  omission noted below.

The trust-layer/deck-composition split itself was the correct cut: labels, flags, and
QA checks changed nothing a client sees and shipped; everything that changes the
artifact waits for the owner. That is the right instinct. The failure mode to watch is
#263 becoming a parking lot — four checkboxes, zero comments, no assignee, no
milestone as of today.

---

## Part 3 — #263 checklist fidelity

The issue text is unusually good: operator/exec-outcome framing, correct mechanisms
named (`SLIDE_LAYOUT_MAP`, `chart_narrative`/`kpi_hero`, KEEP/NIX gate), and the
closing sentence ("a deck that opens with a filled summary... never shows a made-up
zero") is exactly the exec-value statement round 1 asked for. Four fidelity gaps:

1. **"Drop-don't-zero" is narrower than round 1's ask.** The checkbox covers "a slide
   whose producer returned **no usable frame**." Round 1's finding 5 was about
   producers that return a *zero-shaped but usable* frame (`_safe` "ships zeros, never
   crashes"). A rendered $0 chart is a usable frame; the checklist as written would be
   satisfiable without touching the actual failure mode. The checkbox should say:
   "a spec input that resolves to a zero-shaped default drops the slide," per the
   original wording.
2. **Run-side pre-render sanity checks are missing entirely.** Round 1 asked for
   `zero_denominator`/`implausible_split` on `ctx.results` before rasterization. Given
   V1's conclusion (the pptx-text checks have ~zero live coverage), this is the only
   version of the check that can work, and it appears in neither #263 nor the
   dispositions' deferred list.
3. **The at-risk-accounts companion CSV (finding 7's most actionable item) is absent.**
   `25_at_risk_accounts` anonymized to "Account 1..N" plus a real-ID CSV was round 1's
   single highest-value artifact suggestion; #263's KEEP/NIX line doesn't carry it.
4. **Minor:** the length-law checkbox cites 25/60 correctly but doesn't name the
   third contradictory standard (`txn-deck-review.md` budget 150) that needs to be
   collapsed into the same law, and it should state who owns unblocking the `_TBD_`
   KEEP/NIX worksheet and by when.

---

## Part 4 — New findings (round 2)

### N1. A11.2 mislabel is now machine-certified compliant
- **Severity: MAJOR** (trust-layer; same class the owner has caught twice before)
- **Where:** `analytics/value/analysis.py:662-670` (no `denominator_label` stamp;
  base built at `:466-488` is eligible-personal-with-debit),
  `pipeline/steps/audit.py:74-77` (A11 default "Eligible Personal"; comment asserts it
  covers A11.2).
- The one-line fix (stamp `denominator_label="Eligible Personal w/Debit"` +
  `denominator_n=len(base)` on the A11.2 result, and correct the audit.py comment) is
  the same shape as the A11.1 fix already merged, needs no owner decision, and closes
  a false-positive in the audit trail the AE would otherwise cite in the room.

### N2. The numeric-sanity gate has no live surface to inspect
- **Severity: MAJOR** (a gate that appears to exist but guards an empty set)
- **Where:** `deck_qa.py:54-58,155-179`; producers at `attrition/impact.py:65,112`,
  `attrition/dimensions.py:460` (PNG-side); no pptx-text producer emits the
  `"x% (n / d)"` shape (searched `output/`, `analytics/`, `docs/slide_specs/`).
- Consequence: the r1 disposition line "deck_qa zero-denominator/implausible-split
  checks landed" is technically true and practically inert. Anyone reading the
  dispositions table would believe the A9.6/A9.9 class is gated; it is not — it is
  hand-demoted per slide ID. Either (a) implement the run-side pre-render check on
  `ctx.results` (where `attrition_9.retention_lift`, closure counts, and bases exist
  as numbers), or (b) have spec callouts adopt the `pct (n/d)` format so the existing
  check gains a surface. (a) is strictly stronger.

### N3. The headline generator will confidently narrate the A9.9 artifact if it ever resurfaces
- **Severity: MINOR** (currently fenced by the appendix demotion)
- **Where:** `output/headlines.py:219-224` — `_attrition_9` renders
  "Debit cardholders close {lift} less often -- cards drive retention" from
  `retention_lift = without_rate - with_rate` with only a not-None/NaN guard. The
  known artifact (debit flags blanked at close → with_rate = 0) produces the *maximal*
  lift and the most confident possible causal headline. A9.9 sits one
  SLIDE_MANIFEST.xlsx "Keep? Y" decision away from the main deck
  (`deck_builder.py:1967-1971` honors manifest keeps). Guard suggestion: suppress or
  soften the headline when `with_rate == 0` or lift exceeds a plausibility bound —
  that's the run-side check N2 asks for, applied to the headline path.

### N4. `_OPERATOR_FILLED` is a substring match on title text, and it is growing
- **Severity: MINOR**
- **Where:** `deck_qa.py:41-46,128-131`. Any title-only slide whose title *contains*
  "monthly revenue", "ars lift", "agenda", etc. is skipped by `empty_body`. A generated
  content slide titled "Monthly Revenue Trend" that loses its chart is silently
  whitelisted as operator-filled. Commit `06a7428` added two more entries while #263
  (which proposes inverting this whitelist into a MAJOR flag) sits undecided. Interim
  hardening: match on exact expected preamble titles or slide index range, not
  substrings; freeze the list until #263 is decided.

### N5. Deck QA FAIL never marks the deliverable
- **Severity: MINOR** (operator-process risk with exec-facing consequence)
- **Where:** `deck_builder.py:2283-2327`. A FAIL writes a sibling
  `*_quality_report.txt`, a manifest flag, and a stdout line — but the .pptx lands in
  the same delivery folder with a clean filename. A rushed operator (the exact persona
  round 1's Dana findings describe) can attach a FAIL deck to an email without ever
  seeing the panel. Cheap option consistent with "a deck that exists beats no deck":
  suffix the filename (`..._QA-FAIL.pptx`) or emit the deck into a `needs_review/`
  subfolder on CRITICAL findings; the UI completion card already has the data.

### N6. Run Quality panel shows only the newest manifest — TXN warnings can be shadowed
- **Severity: POLISH**
- **Where:** `05_UI/app.py:1359` (`run_manifest*.json` glob, newest wins) vs
  per-product suffixed manifests (`pipeline/manifest.py:156`). An ARS re-run after a
  TXN run in the same client/month hides the TXN eligible-noop WARN from the panel.
  Merge flags from all matching manifests, or scope the glob by the product being
  viewed.

### N7. TXN slides are invisible to the rate audit (restated precisely)
- **Severity: MAJOR** (already OPEN in dispositions; restated because the mechanism
  matters for how it gets fixed)
- **Where:** `txn_wrapper.py:548-555` (results carry no kpis/labels) +
  `audit.py:130-144`. Fixing this is not "run the audit for TXN" (it already runs);
  it is "make TXN results carry rate metadata" — which the txn_exports adapter
  (`expose_to_ctx_results`, `txn_wrapper.py:176-224`) already positions: exported
  insight keys per script are the natural place to declare each section's rate and
  base so `_looks_like_rate` has something to see.

---

## Bottom line

The trust-layer round did land real things: the rates audit runs on every build, the
rege.yml key bug is dead, A11.1 is honestly labeled, the eligible-noop is loudly
flagged to the operator, and the two named zero-artifacts are out of the main deck.
But the two headline claims I was asked to verify hardest both come back qualified:
the numeric-sanity gate could not have caught the artifacts it is named after (they
live in PNGs, and no current slide text matches its pattern), and the A11.x relabel
fixed one of two slides while the audit now certifies the other's wrong label. The
#263 routing was the right governance call; its checklist needs four amendments
(zero-shaped-frame wording, run-side checks, the at-risk CSV, a KEEP/NIX deadline)
and the issue needs an owner and a date before the next monthly cycle ships.

**Do-now list (no owner decision required):** N1 (A11.2 stamp — one line, same shape
as the merged A11.1 fix), N4 freeze/harden the whitelist match, N6 manifest merge.
**Fold into #263:** N2 (run-side sanity checks), N3 (headline guard), N5 (FAIL
marking), checklist amendments above.
