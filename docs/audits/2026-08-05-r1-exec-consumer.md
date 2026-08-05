# Exec-Consumer Audit — "Marcus" (Client Executive / CSI Account Executive)

- **Persona:** Bank/CU executive receiving the monthly ARS/TXN results deck, plus the CSI AE presenting it
- **Date:** 2026-08-05 (round 1)
- **Scope:** Deck-definition artifacts only (no pipeline run): `docs/SLIDE_SPECS_ARS.md`, `SLIDE_DESIGN.md`, `SLIDE_MAPPING.md`, `docs/slide_specs/*.yml`, `docs/EQUATION_DICTIONARY.md`, `docs/deck/txn-deck-review.md`, `docs/deck/txn-followups.md`, `01_Analysis/00-Scripts/output/{deck_builder.py, headlines.py, notes.py, deck_qa.py}`. Reference `.pptx` binaries not parsed.

The question I am asking of every artifact: *if I am paying for this program, does this deck tell me what happened, why, what it's worth, and what to do — before I stop reading?*

---

## Findings

### 1. The most important slides in the deck are blank by design
- **Severity:** DEAL-BREAKER
- **Where:** `deck_builder.py:_build_preamble_slides` (P02 Agenda, P04 Executive Summary, P05 Monthly Revenue, P06 ARS Lift Matrix, P11 All Program Results); `deck_qa.py` `_OPERATOR_FILLED` whitelist; "Summary & Key Takeaways" divider at `deck_builder.py:2607` with no content slides behind it.
- **What the exec experiences:** The slides an executive actually reads — Executive Summary, Monthly Revenue, the Lift Matrix, and the closing Summary — are generated as title-only placeholders the operator fills by hand from a separate PowerPoint. The QA gate explicitly whitelists them as "blank is intended." If the operator is rushed, the deck ships with an empty Executive Summary and a "Summary & Key Takeaways" divider that leads directly into the Appendix. Everything the pipeline is good at (auto-computed numbers, locked formulas) is in the middle 40 slides; everything the exec cares about most is the manual, unverified part.
- **Suggested change:** Auto-draft the Executive Summary from the same `ctx.results` that already feed `headlines.py` (S1–S8 and A11.x produce exactly the 3–5 bullets `SLIDE_DESIGN.md` §2 calls for: gap, attrition cost, ROI, top action). Operator edits a draft instead of authoring from scratch. Put real content (the S8 action plan) behind the "Summary & Key Takeaways" divider. Change `deck_qa` from whitelisting these blanks to flagging them as "MAJOR: exec summary not populated" so a blank one can't ship silently.

### 2. TXN deck is a data dump, not a story: 339 slides against a 150 budget and a 60-slide QA cap
- **Severity:** DEAL-BREAKER
- **Where:** `docs/deck/txn-deck-review.md` (run 1776: 339 slides; Competition 90, Campaign 76, near-identical 10–13-slide Merchant/MCC/Business/Personal sections); `deck_qa.py` `MAX_SLIDES = 60`; `SLIDE_DESIGN.md` §2 hard rule "main deck ≤ 25 slides."
- **What the exec experiences:** Three contradictory length standards coexist (25 / 60 / 339), and the generated TXN deck violates all of them. Competition alone emits 8 slides each for `26_spend_scatter`, `28_spend_vs_frequency`, `29_wallet_share` — per-segment cell explosions of the same chart. The review doc that was supposed to fix this is a KEEP/NIX worksheet where nearly every verdict is still `_TBD_` (dated 2026-04-28, untouched). An exec receiving 339 slides concludes the vendor doesn't know which 15 numbers matter — which undermines trust in all of them.
- **Suggested change:** Lock the review doc's global rule G4 to a real number (25 main + appendix), implement the already-specified G6 (drop-if-empty) and G7 (auxiliary deck for NIX slides), and collapse each per-segment cell family to one small-multiples slide (the fix already written for `24_segment_heatmap` in `txn-followups.md` — apply the pattern to 25/26/28/29). The Mailer Performance ancillary-deck pattern (`_build_mailer_performance_deck`) is the proven template: main deck gets the recent story, the rest gets its own file.

### 3. Titles: the design standard is insight-first, but the code mostly ships metric-labels — and even good headlines land in speaker notes, not on the slide
- **Severity:** MAJOR
- **Where:** `SLIDE_DESIGN.md` §1.2 (action titles) and `docs/slide_specs/*.yml` (genuinely good: "L12M DCTR of {rate} trails historical by {gap}pp; 3 branches drive {share} of the gap") vs `headlines.py` generators; `SLIDE_LAYOUT_MAP` in `deck_builder.py` routing nearly every slide to the bare `screenshot` builder (title-less full-page PNG).
- **What the exec experiences:** Three tiers exist. (a) The YAML specs are exactly right — sentence, magnitude, driver, so-what. (b) `headlines.py` mostly produces flat descriptors: "Personal TTM take rate at 34.2%", "Attrition varies across 12 branches" (that one says literally nothing), and ~30 slide IDs are `_noop` — they fall back to the label title. (c) The layout map sends almost everything to `screenshot`, so even a generated headline reaches only Presenter View — the exec looking at the printed slide sees a bare chart PNG with the chart's own generic title. The standard exists on paper; the audience never sees it.
- **Suggested change:** Rewire `SLIDE_LAYOUT_MAP` entries from `screenshot` to the existing `chart_narrative` / `kpi_hero` builders (they exist and work — see `_build_chart_narrative_slide`) so the headline is the slide title. Upgrade the "varies across N" family (`_attrition_4`, `_dctr_13/14`) to name the extreme: "Branch X attrition 2.3× portfolio — 4 branches drive 60% of closures." Kill the pattern of headlining a count of segments; a segment count is never a finding.

### 4. Trust: denominator labels disagree with what the code divides by, and the deck's own dictionary says so
- **Severity:** MAJOR
- **Where:** `docs/EQUATION_DICTIONARY.md`: attrition.yml labels rates "Eligible" but code stamps `L12M Exposure` (full book, all products); A11.2 labeled Eligible, actual base Eligible-Personal-w/Debit; `competition.yml` stamps `denominator_label: Eligible` but wallet share is a within-account share; TXN eligible filter "no-ops silently" when `eligible_data` is unavailable and "TXN does not run the rate audit, so these denominators are not machine-verified."
- **What the exec experiences:** This is precisely the class of question a numerate exec asks first: "34% of *what*?" The four-layer denominator law is a genuinely strong answer — but only where enforced (ARS + stamped slides). On the TXN side the footer can say "Eligible" while the rate was computed on the raw transaction universe, and nobody would know. The owner has already caught this class twice (Reg E funnel percentages against the wrong base; attrition collapsing to ~100 closures — both in `SLIDE_SPECS_ARS.md` "Known corrections"). Each catch by the client costs more credibility than ten correct slides earn back.
- **Suggested change:** Extend the ARS `audit.py` rate audit (or a spec-vs-stamp consistency check) to TXN; make the eligible-filter no-op a loud manifest WARN that prints on the slide footer ("base: all TXN accounts — eligibility file unavailable"), never a silent fallback. Relabel attrition's base honestly ("all accounts exposed during L12M") — the exposure base is defensible, the mislabel is not.

### 5. Trust: zero-shaped fallbacks can put confident zeros in front of the client
- **Severity:** MAJOR
- **Where:** `EQUATION_DICTIONARY.md` on rege: "`rege.yml` reads `reg_e_2.insights.l12m_opt_in` … those keys are not produced (accessors fall back to zero-shaped defaults)"; insights section: `_data._safe` "ships zeros, never crashes the deck"; the A9.9 case (0.0% with-debit, 4/14,642, because debit flags are blanked at close) shipped in deck 1759; `deck_qa.py` `zero_denominator` / `implausible_split` checks.
- **What the exec experiences:** A slide asserting "$0 opportunity" or "0.0% vs 29.2% retention" with full production polish. The A9.9 artifact is the archetype: a data-lifecycle quirk (flags blanked at close) rendered as a dramatic business finding. The repair story is half-done: `deck_qa` now catches zero denominators and implausible 0-vs-big splits *in rendered text*, but it explicitly cannot see numbers baked into chart PNGs — which is where most numbers live, because everything is a screenshot slide. And the design philosophy of "ship zeros, never crash" is exactly backwards for an exec audience: a missing slide is a scheduling problem; a wrong zero is a credibility problem.
- **Suggested change:** Flip the failure mode — a spec input that resolves to a zero-shaped default should drop the slide to the appendix with a manifest WARN, not render a hero "$0". Fix the rege.yml key mismatch (it is a known, named bug). Add run-side (pre-render) versions of `zero_denominator`/`implausible_split` on `ctx.results` so the checks see the numbers before they are rasterized into PNGs.

### 6. Trust: revenue-opportunity numbers jumped ~4.3× between decks with no on-slide explanation
- **Severity:** MAJOR
- **Where:** `docs/SLIDE_SPECS_ARS.md` Insights row: ic_rate fallback changed 0.0015 → 0.0065, "revenue-opportunity numbers will be ~4.3× HIGHER than prior decks. This is intentional (owner rule)."
- **What the exec experiences:** Last quarter the branch-opportunity slide said $700K; this quarter the same slide says $3M on similar volumes. The change is documented as intentional in an internal spec file the client will never see. The first question in the meeting will be "what changed?", and the AE presenting has nothing on the slide to point at. Methodology changes that move headline dollars need to be announced *in the deck*, once, the month they land.
- **Suggested change:** For one reporting cycle, add a footnote to A18/A19/S-series value slides: "Interchange assumption updated to 0.65% (client-config rate; prior decks used a conservative placeholder)." The methodology footer band defined in `SLIDE_DESIGN.md` §3 is the natural home; it currently exists in the spec but the screenshot builder renders no footer at all.

### 7. Analyst artifacts occupy main-deck slots: cross-tabs, dual-axis overlays, unreadable scatters, and "Account 1..N" charts
- **Severity:** MAJOR
- **Where:** DCTR-13/14/15 cross-tab grids (headline: "adoption varies across N demographic segments"); A7.13–A7.15 heatmap/seasonality/vintage cuts; `txn-followups.md`: `26_spend_scatter` "horrible scaling, no value", `24_account_age_bar` "line chart inside the bar chart is weird", `25_at_risk_accounts` y-labels hardcoded "Account {i+1}" — "slide is not actionable"; the diagnostic pair `financial_services_01_config` / `02_identify` (configuration echo) rendered as client-facing slides.
- **What the exec experiences:** Slides that answer an analyst's question ("did we check the interaction of age × balance?") rather than an executive's ("where do I put my next dollar?"). The at-risk-accounts slide is the sharpest case: it names a genuinely valuable list — high-balance members showing competitor behavior — then anonymizes it into "Account 1, Account 2…" so nothing can be done with it. A config-echo slide (`01_config`) tells the client which merchant list the vendor used; that's an appendix/methodology item at best.
- **Suggested change:** Default all cross-tab, distribution, and diagnostic outputs to the appendix/aux deck (`DCTR_APPENDIX_IDS` is the existing mechanism — extend the pattern to TXN). For `25_at_risk_accounts`, adopt the option already written in `txn-followups.md`: keep the anonymized slide, ship the companion CSV of real account IDs — that turns a wall chart into a call list, the single most actionable artifact in the whole deck.

### 8. Narrative arc exists in code and is genuinely good — but the "diagnosis" acts have no diagnosis slides
- **Severity:** MINOR
- **Where:** `deck_builder.py` `SECTION_ORDER` (Situation → Complication → Resolution comments) and `_SECTION_LABELS` (question-phrased: "How Big Is This Program?", "What Is the Revenue Impact?", "What Should We Do Next?").
- **What the exec experiences:** The skeleton is right — question-phrased dividers are exactly what a consulting deck does, and value/insights land last as the payoff. But inside each "Operational KPI" act, slides are ordered by module registration, not by finding; DCTR runs snapshot → funnel → branch → age with no "here's why the rate moved" beat. The story reads: *what happened* (many times, in many cuts) → *what it's worth* → *what to do*, with the *why* implied but never stated. The sag point is mid-deck DCTR/Reg E cuts, where 6–9 same-shaped rate charts arrive in a row.
- **Suggested change:** One synthesis slide per KPI section, placed first after the divider: the DCTR-MAIN-1 spec (rate, gap, top-3 branch drivers, $ value) already *is* that slide — wire it so it leads the section, and let the supporting cuts follow or drop to appendix. Three "MAIN" slides per section is the right budget; the YAMLs already define them.

### 9. Speaker notes give the AE nothing client-specific to say
- **Severity:** MINOR
- **Where:** `output/notes.py` — every slide gets the identical two talking points: "What actions has the credit union taken on this metric since last review?" / "How does this compare to their strategic goals?"
- **What the exec experiences:** Indirectly: an AE who flips to Presenter View for help finds boilerplate, so the presentation defaults to reading charts aloud. The KEY FINDING line (restated headline) is useful; the talking points are filler that will be identical on slide 8 and slide 38.
- **Suggested change:** Generate one slide-specific prompt from the same insights dict the headline used ("Ask: Elm St is 9pp below portfolio — staffing or demographics?"). Where no specific prompt can be computed, emit nothing — an empty notes field is more honest than a template question.

### 10. Recommendations exist but arrive as totals, not decisions
- **Severity:** MINOR
- **Where:** S8 spec ("Three-action plan targeting {combined} in combined value"), `TXN-executive-5` ("{n_actions} prioritized initiatives totaling ${total_impact}"), `interchange 10_action_summary` and `rege_overdraft 10_action_summary` (compute action tables but are display-only — never make a slide, per `EQUATION_DICTIONARY.md`).
- **What the exec experiences:** The closing slides say "3 actions worth $1.2M" but the per-action content — what, who, by when, worth how much each — is either buried in a screenshot table or computed and then dropped (the two `10_action_summary` cells produce exactly the right content and it never reaches the deck). A recommendation without an owner and a sequence is a number, not a plan.
- **Suggested change:** Promote the action-summary outputs to a real closing slide per `SLIDE_DESIGN.md` §2 item 7 ("Summary of recommendations — sized by impact, sequenced"): one row per action, impact $, effort, first step. This is the natural home for the so-what of every upstream section, and most of the computation already exists.

### 11. Length discipline: the standards documents themselves disagree
- **Severity:** POLISH
- **Where:** `SLIDE_DESIGN.md` ("main deck ≤ 25"), `deck_qa.py` (`MAX_SLIDES = 60`, "good decks run ~40"), `txn-deck-review.md` ("budget 150", actual 339).
- **What the exec experiences:** Nothing directly — but the team building the deck has three different definitions of done, and the widest one always wins. The ARS deck at ~39–40 is defensible with the ancillary-mailer split; the number to fix is the TXN target.
- **Suggested change:** Declare one law in `SLIDE_DESIGN.md` (it claims to be the single source of truth): main ≤ 25, main+appendix ≤ 60, everything else to aux decks. Align `deck_qa` thresholds and the review-doc budget to it. Cut order for TXN: (1) per-segment cell explosions in Competition/Campaign, (2) the four near-identical Merchant/MCC/Business/Personal sections down to one comparative section, (3) diagnostic/config slides, (4) any slide whose headline generator is `_noop` — if the pipeline can't state its finding, the deck can't either.

---

## The 5 changes that would most raise perceived deck value

1. **Auto-draft the Executive Summary and Action Plan from `ctx.results`** (Findings 1, 10). The numbers already exist; putting them on the two slides an exec actually reads converts pipeline strength into perceived value directly.
2. **Rewire `SLIDE_LAYOUT_MAP` from `screenshot` to `chart_narrative`/`kpi_hero` so insight headlines appear ON slides** (Finding 3). The single highest polish-per-line-of-code change: the builders and headline generators both exist; only the routing is missing.
3. **Enforce the 25/60 length law and demote cross-tabs, per-segment explosions, and diagnostics to appendix/aux decks** (Findings 2, 7, 11). Every cut slide raises the average value of the survivors.
4. **Close the denominator-label gap on TXN and make zero-fallbacks drop slides instead of rendering $0** (Findings 4, 5). Trust is the product; a client who catches one wrong base re-audits everything, and the owner has already caught two.
5. **Footnote the ic_rate methodology change for one cycle and render the methodology footer band on every content slide** (Finding 6). A one-line footnote pre-empts the hardest question in the room and makes every number self-defending.
