# Deck Blueprint -- ARS Exec Narrative Rebuild

Generated: 2026-04-17. Read-only research output. Grounded in:
- `02_Powerpoint/sections/*.py` (9 section modules + preamble)
- `01_Analysis/00-Scripts/analytics/` (7 analytics folders)
- `SLIDE_MAPPING.md`

Narrative arc: Open -> Truth -> Diagnosis (Engagement / Targeting / Ecosystem) -> Opportunity -> Plan -> Close. Three personas (Non-User, Climber, Decliner) appear as a single bridge slide between Diagnosis and Plan. Deeper persona content lives in an optional appendix module.

---

## 1. Slide inventory (what exists)

Inventory below is the set of slide IDs each section module actively owns (prefixes + layout_map + dynamic children). Mailer month slides are represented as templates; actual IDs are expanded at runtime per client month. Preamble slides P01-P13 are manual / placeholder and are not data-driven.

| section | slide_id | current label | analytics folder | chart type |
|---|---|---|---|---|
| preamble | P01 | Master title | -- | title |
| preamble | P02 | Agenda | -- | blank |
| preamble | P03 | Program Performance divider | -- | divider |
| preamble | P04 | Executive Summary (placeholder) | -- | blank |
| preamble | P05 | Monthly Revenue -- L12M | -- | blank (manual) |
| preamble | P06 | ARS Lift Matrix | -- | blank (manual) |
| preamble | P07 | ARS Mailer Revisit divider | -- | divider |
| preamble | P08 | Mailer Revisit -- Swipes | wired to A12.{month}.Swipes | screenshot |
| preamble | P09 | Mailer Revisit -- Spend | wired to A12.{month}.Spend | screenshot |
| preamble | P10 | Mailer Summaries divider | -- | divider |
| preamble | P11 | All Program Results (paste) | -- | blank |
| preamble | P12 | Program Responses to Date | wired to A13.5 | screenshot |
| preamble | P13 | Data Check Overview | -- | blank |
| overview | A1 | Account Composition | overview/stat_codes | horizontal bar (SKIP) |
| overview | A1b | Product Code Distribution | overview/product_codes | horizontal bar (SKIP) |
| overview | A3 | Eligibility Funnel | overview/eligibility | KPI + funnel (SKIP) |
| dctr | DCTR-1 | Historical DCTR | dctr/penetration | stacked bar (SKIP) |
| dctr | DCTR-2 | DCTR: Open vs Eligible | dctr/penetration | bar comparison |
| dctr | DCTR-3 | DCTR Snapshot: Open -> TTM | dctr/penetration | 4-bar narrative chart |
| dctr | DCTR-4 | Personal Historical DCTR | dctr/penetration | bar |
| dctr | DCTR-5 | Business Historical DCTR | dctr/penetration | bar |
| dctr | DCTR-6 | Personal L12M DCTR | dctr/penetration | bar |
| dctr | DCTR-7 | Business L12M DCTR | dctr/penetration | bar |
| dctr | DCTR-8 | DCTR Summary Table | dctr/penetration | table/KPI |
| dctr | DCTR-9 | DCTR by Branch | dctr/branches | ranked hbar |
| dctr | DCTR-10 | PIN vs SIG Volume | dctr/overlays | stacked bar |
| dctr | DCTR-11 | PIN vs SIG Spend | dctr/overlays | stacked bar |
| dctr | DCTR-12 | Swipe intensity | dctr/overlays | bar |
| dctr | DCTR-13 | Swipe buckets | dctr/overlays | histogram |
| dctr | DCTR-14 | Transactor vs Inactive | dctr/overlays | bar |
| dctr | DCTR-15 | Branch dormancy | dctr/branches | ranked hbar |
| dctr | DCTR-16 | Branch ranking detail | dctr/branches | ranked hbar |
| dctr | A7.4 | L12M DCTR line | dctr/trends | line trend |
| dctr | A7.5 | Seasonality | dctr/trends | line (appx) |
| dctr | A7.6a | DCTR trajectory | dctr/trends | line |
| dctr | A7.6b | DCTR trajectory alt | dctr/trends | line (appx) |
| dctr | A7.7 | Funnel: all-time | dctr/funnel | funnel |
| dctr | A7.8 | Funnel: TTM | dctr/funnel | funnel |
| dctr | A7.9 | Funnel delta | dctr/funnel | funnel (appx) |
| dctr | A7.10a | Branch scatter / ranked | dctr/branches | scatter/hbar |
| dctr | A7.10b | Branch detail | dctr/branches | bar (appx) |
| dctr | A7.10c | Branch KPI | dctr/branches | KPI (appx) |
| dctr | A7.11 | DCTR by account age | dctr/trends (age) | grouped bar |
| dctr | A7.12 | DCTR by holder age | dctr/trends (age) | grouped bar |
| dctr | A7.13 | DCTR dormant detail | dctr/branches | bar (appx) |
| dctr | A7.14 | Monthly activity trend | dctr/trends | line (appx) |
| dctr | A7.15 | Late-stage trend | dctr/trends | line (appx) |
| rege | A8.1 | Overall Reg E Status | rege/status | stacked bar (appx) |
| rege | A8.2 | Reg E Historical | rege/status | line (appx) |
| rege | A8.3 | Reg E L12M Monthly | rege/status | line |
| rege | A8.4a | Reg E by Branch (Hist vs L12M) | rege/branches | hbar |
| rege | A8.4b | Reg E Branch vertical | rege/branches | vbar |
| rege | A8.4c | Reg E Branch scatter | rege/branches | scatter (appx) |
| rege | A8.5 | Reg E by Account Age | rege/dimensions | grouped bar |
| rege | A8.6 | Reg E by Holder Age | rege/dimensions | grouped bar |
| rege | A8.7 | Reg E by Product Code | rege/dimensions | hbar (appx) |
| rege | A8.10 | All-Time Funnel with Reg E | rege/dimensions | funnel |
| rege | A8.11 | L12M Funnel with Reg E | rege/dimensions | funnel |
| rege | A8.12 | Reg E 24-Month Trend | rege/status | line (appx) |
| rege | A8.13 | Branch x Month pivot | rege/branches | heatmap |
| attrition | A9.1 | Overall Attrition Rate | attrition/rates | KPI |
| attrition | A9.2 | Closure Duration | attrition/rates | bar (appx) |
| attrition | A9.3 | Open vs Closed | attrition/rates | comparison bar |
| attrition | A9.4 | Attrition by Branch | attrition/dimensions | hbar (appx) |
| attrition | A9.5 | Attrition by Product | attrition/dimensions | bar (appx) |
| attrition | A9.6 | Personal vs Business | attrition/dimensions | grouped bar |
| attrition | A9.7 | Attrition by Tenure | attrition/dimensions | bar (appx) |
| attrition | A9.8 | Attrition by Balance | attrition/dimensions | bar (appx) |
| attrition | A9.9 | Debit Card Retention Effect | attrition/impact | KPI + bar |
| attrition | A9.10 | Mailer Program Retention | attrition/impact | KPI + bar |
| attrition | A9.11 | Revenue Impact of Attrition | attrition/impact | waterfall |
| attrition | A9.12 | Attrition Velocity | attrition/impact | line |
| attrition | A9.13 | ARS vs Non-ARS Retention | attrition/impact | comparison (appx) |
| mailer | A12.{month}.Swipes | Mail Campaign Swipes | mailer/insights | grouped bar (per-month) |
| mailer | A12.{month}.Spend | Mail Campaign Spend | mailer/insights | grouped bar (per-month) |
| mailer | A13.{month} | Monthly Summary | mailer/response | donut + bar + numbers |
| mailer | A13.5 | Responder Count Trend | mailer/response | line |
| mailer | A13.6 | Response Rate Trend | mailer/response | line (appx) |
| mailer | A13.Agg | All-Time Mailer Summary | mailer/response | composite |
| mailer | A14.2 | Responder Account Age | mailer/response | bar |
| mailer | A15.1 | Market Reach | mailer/impact | hbar |
| mailer | A15.2 | Spend Share / Composition | mailer/impact | stacked bar |
| mailer | A15.3 | Revenue Attribution | mailer/impact | waterfall |
| mailer | A15.4 | Pre/Post Spend Delta | mailer/impact | before/after bar |
| mailer | A15.{month} | Per-month Impact (dynamic) | mailer/response | composite |
| mailer | A16.1 | Responder Spend Trajectory | mailer/cohort | line |
| mailer | A16.2 | Responder Swipe Trajectory | mailer/cohort | line |
| mailer | A16.3 | Per-Segment Spend Trajectory | mailer/cohort | line |
| mailer | A16.4 | Per-Segment Swipe Trajectory | mailer/cohort | line |
| mailer | A16.5 | Spend Direction Change | mailer/cohort | diverging bar |
| mailer | A16.6 | Cohort Size & Retention | mailer/cohort | bar |
| mailer | A17.1 | Cumulative Program Reach | mailer/reach | line |
| mailer | A17.2 | Program Penetration Rate | mailer/reach | line |
| mailer | A17.3 | Organic vs Program Activation | mailer/reach | line |
| value | A11.1 | Value of a Debit Card | value/analysis | KPI + waterfall |
| value | A11.2 | Value of Reg E Opt-In | value/analysis | KPI + waterfall |
| insights | S1 | The Revenue Gap | insights/synthesis | horizontal waterfall |
| insights | S2 | The Cost of Walking Away | insights/synthesis | comparison bar |
| insights | S3 | The Mailer Program Works | insights/synthesis | before/after + delta |
| insights | S4 | Branch Performance Gap | insights/synthesis | hbar ranked |
| insights | S5 | The Debit Card Cascade | insights/synthesis | cascade / flow |
| insights | S6 | Combined Opportunity Map | insights/conclusions | scatter/matrix |
| insights | S7 | What If: +5 Points of DCTR | insights/conclusions | bar + delta |
| insights | S8 | Executive Summary | insights/conclusions | summary grid |
| insights | A18.1 | DCTR Progression (effectiveness) | insights/effectiveness | line |
| insights | A18.2 | Cumulative Value Delivered | insights/effectiveness | line |
| insights | A18.3 | Industry Benchmark Comparison | insights/effectiveness | comparison bar |
| insights | A19.1 | Branch Performance Scorecard | insights/branch_scorecard | heatmap / scorecard |
| insights | A19.2 | Branch Opportunity Map | insights/branch_scorecard | scatter |
| insights | A20.1 | Dormant Opportunity Summary | insights/dormant | KPI + bar |
| insights | A20.2 | At-Risk Member Identification | insights/dormant | bar |
| insights | A20.3 | Targeting Priority Matrix | insights/dormant | quadrant scatter |
| transaction | TXN-* | (planned, not yet in analytics) | -- | -- |
| ics | ICS-* | (planned, not yet in analytics) | -- | -- |

Totals: approximately **~95 data slides** today across the 7 active analytics folders (DCTR 25, Reg E 11, Attrition 11, Mailer 22 + per-month expansions, Overview 3 currently skipped, Value 2, Insights 13) + 13 preamble slides. Transaction and ICS sections are registered but produce nothing yet.

---

## 2. Narrative mapping (where each slide goes)

Legend: **reuse** = drop the existing chart into the new section unchanged; **rework** = same underlying analysis but needs a new headline and/or simplified visual; **new** = new slide (see section 3).

### 2.1 Open

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| P01 | preamble | Title slide | reuse | Client name + program month |
| P02 | preamble | Agenda (Truth / Diagnosis / Opportunity / Plan) | rework | Rewrite to match 4-beat arc |
| NEW-OPEN-1 | -- | "What you'll leave with" executive expectation | new | Optional, can fold into P02 |

### 2.2 Truth

Truth is one or two slides. The claim: your customers ARE spending. Use Jupyter-notebook debit penetration (80%+), not pipeline DCTR (30%).

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| NEW-TRUTH-1 | -- | Executive reframe: "Your customers are spending" (single sentence) | new | Text-only headline slide |
| NEW-TRUTH-2 | -- | Headline penetration bar (notebook denominator) | new | Needs notebook-derived number, NOT DCTR-3 |
| A17.1 | mailer/reach | Supporting: program reach trajectory | reuse | Shows program is already active |
| A13.Agg | mailer/response | Supporting: all-time response totals | reuse | Proof of scale |

### 2.3 Diagnosis / Engagement Gap

Theme: "They are spending, but not enough are active with YOU." Owner of the Non-User persona.

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| DCTR-3 | dctr | TTM DCTR snapshot (4-bar) | rework | Reframe headline around "active with you". Flag denominator (see section 5). |
| A7.7 + A7.8 | dctr (merged) | Funnel: Historical vs TTM | reuse | Already merged; shows activation fall-off |
| DCTR-9 / A7.10a | dctr/branches | Branch dispersion -- who is not activating | reuse | Pick the cleaner of the two for main deck |
| DCTR-14 | dctr/overlays | Transactor vs Inactive mix | reuse | Quantifies the non-user population |
| A9.9 | attrition/impact | Debit retention effect (non-users churn faster) | reuse | Links engagement gap to downstream risk |

### 2.4 Diagnosis / Targeting Gap

Theme: "The right people aren't being reached." Owner of the Climber persona.

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| A7.11 + A7.12 (merged) | dctr | DCTR by account age / holder age | reuse | Already merged |
| A8.5 + A8.6 (merged) | rege | Reg E by account age / holder age | reuse | Already merged |
| A14.2 | mailer/response | Responder Account Age | reuse | Who *does* respond today |
| A19.2 | insights/branch_scorecard | Branch Opportunity Map | reuse | Where the highest-leverage targets sit |
| A20.3 | insights/dormant | Targeting Priority Matrix | reuse | Directly feeds Climber persona |

### 2.5 Diagnosis / Ecosystem Gap

Theme: "Customers are bleeding around the edges." Owner of the Decliner persona (placed here; alternative placement in Opportunity is noted in open questions).

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| A9.1 | attrition/rates | Overall attrition KPI | reuse | Sets the ecosystem-leakage number |
| A9.3 | attrition/rates | Open vs Closed profile | reuse | Who leaves |
| A9.6 | attrition/dimensions | Personal vs Business attrition | reuse | Profile split |
| A9.12 | attrition/impact | Attrition velocity | reuse | Rate of leakage |
| A20.1 | insights/dormant | Dormant opportunity (at-risk population) | reuse | The decliner population |
| A20.2 | insights/dormant | At-Risk Member Identification | reuse | Who to save |

### 2.6 Persona bridge (between Diagnosis and Plan)

Single slide in the main deck. Deeper per-persona content is in section 6.

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| NEW-PERSONA-BRIDGE | -- | Meet the three customer types | new | 3 cards (Non-User / Climber / Decliner) w/ sizing + 1 data point each |

### 2.7 Opportunity

Theme: "Here is the size of the prize."

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| NEW-OPP-1 | -- | Total addressable spend (headline $) | new | Can derive from value/analysis + notebook debit penetration |
| S1 | insights/synthesis | Revenue Gap waterfall | rework | Rework to use notebook denominator; current version uses pipeline DCTR |
| S7 | insights/conclusions | What If: +5 Points of DCTR | rework | Same -- reframe input numbers |
| A11.1 | value/analysis | Value of a Debit Card | rework | Flag denominator (see section 5) |
| A11.2 | value/analysis | Value of Reg E Opt-In | reuse | Reg E denominator is cleaner |
| S6 | insights/conclusions | Combined Opportunity Map | reuse | Good "where to play" visual |

### 2.8 Plan

Theme: "Here is what we will do together."

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| NEW-PLAN-1 | -- | 3-5 Strategic Pillars | new | Maps pillars to Engagement / Targeting / Ecosystem gaps |
| S3 | insights/synthesis | Mailer program works (proof pillar) | reuse | Evidence for "keep doing this" |
| A15.1 | mailer/impact | Market reach (pillar: scale) | reuse | Evidence for "expand the mailer" |
| A15.3 | mailer/impact | Revenue attribution (pillar: mailer ROI) | reuse | Justifies continued investment |
| A15.4 | mailer/impact | Pre/post spend delta | reuse | Shows program lift |
| A16.1 | mailer/cohort | Responder spend trajectory | reuse | Proves durability |
| A9.10 | attrition/impact | Mailer retention (pillar: retention) | reuse | Ties plan back to ecosystem gap |
| A18.3 | insights/effectiveness | Industry benchmark comparison | reuse | Frames pillar targets |

### 2.9 Close

| slide_id | source section | role in new narrative | reuse / rework / new | notes |
|---|---|---|---|---|
| S8 | insights/conclusions | Executive Summary grid | rework | Rework bullets to match new 4-beat narrative |
| NEW-CLOSE-1 | -- | Final takeaway / next-step CTA | new | One-sentence close + contact |

**Mapping summary:** roughly 40 of ~95 existing data slides map cleanly into the new main deck (the rest go to appendix or the optional persona module). 7 new slides are required.

---

## 3. New slides required

All 7 "new" slides below can be produced from existing analytics except where noted.

| # | Title | Purpose (question it answers) | Data inputs | Source | Placement |
|---|---|---|---|---|---|
| 1 | **Executive Reframe** | "The real story isn't `your customers aren't spending` -- it's that they are spending, just not with you." | One headline number: debit penetration from Jupyter notebook (80%+) | Needs notebook export -- NOT pipeline DCTR. Requires a one-time CSV/value handoff from the notebook, then a text/KPI slide | Truth (first) |
| 2 | **True Debit Penetration** | Shows the notebook-derived customer-level debit penetration vs the pipeline's account-level DCTR | Notebook number (numerator = customers transacting anywhere; denominator = total customers) | Can be produced by adding a new analytics cell that reads the notebook output or by loading the notebook's intermediate parquet. Not derivable from current DCTR cells, which use eligible-account denominator | Truth (second) |
| 3 | **Persona Bridge** | Introduces Non-User / Climber / Decliner with sizing + one-line data point per persona | Sizing: counts from dctr penetration (non-user), A20.x dormant + attrition rates (decliner), A14.2 responder age + A7.11 account-age DCTR (climber) | Producible from existing analytics; new composite layout (3 cards) | Between Diagnosis and Plan |
| 4 | **Total Addressable Spend** | Size of the prize in dollars | value/analysis A11.1 (`accts_without * delta`) recalculated with notebook denominator; plus Reg E gap from A11.2 | Needs a re-derivation of `accts_without` using notebook-truth population -- the current value module hard-codes eligible-personal base | Opportunity (first) |
| 5 | **3-5 Strategic Pillars** | What we will do, mapped to the three gaps | Pillar text (not data); ideally one supporting number per pillar | Text slide; numbers can be pulled from S3, A15.1, A18.3. Supporting metrics exist | Plan (first) |
| 6 | **Final Takeaway / CTA** | One-sentence close + next step | Text only | Text slide | Close (last) |
| 7 | **Updated Agenda (4-beat)** | New arc signposting (Truth / Diagnosis / Opportunity / Plan) | Text only; replaces P02 | Text; rework of existing P02 placeholder | Open |

**What is genuinely missing from analytics:** slides 1, 2, and 4 all require a customer-level (not account-level) debit penetration number. That number does not exist in the current analytics cells. See section 5 and section 7.

---

## 4. Slides cut or moved to appendix

Main-deck cuts (move to appendix so they are still available on demand):

| slide_id | why it is cut from main |
|---|---|
| A1, A1b, A3 | Portfolio composition and eligibility funnel -- already skipped by `overview.py` today; keep skipped |
| DCTR-1 | Historical DCTR duplicates DCTR-3's TTM narrative; already in `skip_ids` |
| DCTR-4, DCTR-5, DCTR-6, DCTR-7 | Personal/Business DCTR splits -- too granular for exec deck |
| DCTR-8 | DCTR summary table -- replaced by Truth slide |
| DCTR-10, DCTR-11, DCTR-12, DCTR-13 | PIN/SIG and swipe detail -- operational, not strategic |
| DCTR-15, DCTR-16 | Branch dormancy detail -- keep one branch slide, appendix the rest |
| A7.5, A7.6b, A7.9, A7.10b, A7.10c, A7.13, A7.14, A7.15 | Already in `dctr._APPENDIX_IDS`; keep there |
| A8.1, A8.2, A8.4b, A8.4c, A8.7, A8.12, A8.13 | Already appendix-flagged in `rege.py` or low signal for exec audience |
| A8.3, A8.10, A8.11 | Monthly / funnel Reg E detail -- appendix unless Reg E is the client focus |
| A9.2, A9.4, A9.5, A9.7, A9.8, A9.13 | Already in `attrition._APPENDIX_IDS`; keep there |
| A9.11 | Revenue impact waterfall -- partially duplicates S1; keep one, appendix the other |
| A13.{month} (older than 2 most recent) | Already auto-appendixed by `_consolidate_mailer` |
| A13.6 | Already appendix-flagged |
| A15.2 | Spend share overlaps A15.3 attribution -- pick one |
| A16.2, A16.3, A16.4, A16.5, A16.6 | Cohort detail -- move to persona module (climber/decliner) |
| A17.2, A17.3 | Reach detail -- keep A17.1 only |
| A18.1, A18.2 | Effectiveness detail -- keep A18.3 (benchmark) only |
| A19.1 | Branch scorecard full table -- keep A19.2 map only |
| S2 | Cost of Walking Away -- consolidate into Ecosystem Gap or appendix |
| S4 | Branch Performance Gap -- overlaps A19.2 |
| S5 | Debit Card Cascade -- strong slide, keep optional for cascade-focused clients |

---

## 5. Denominator audit

Any slide whose headline implies a "customers are spending / penetration / activation" rate is at risk of understating the real number because the pipeline uses an **account-level** DCTR over `eligible_data` (a filtered subset), while the notebook uses a **customer-level** debit penetration across the full member base. The first yields ~30%, the second ~80%+.

| slide_id | source file | claim | denominator used | status |
|---|---|---|---|---|
| DCTR-1 | dctr/penetration.py:241 | "Historical DCTR X%" | `ctx.subsets.eligible_data` | PIPELINE DCTR (30%) -- UNSAFE |
| DCTR-2 | dctr/penetration.py:297 | "Open vs Eligible DCTR" | both `open_accounts` and `eligible_data` | PIPELINE DCTR -- headline must not be reused as "customers are spending" |
| DCTR-3 | dctr/penetration.py:338 | "TTM DCTR X%" (4-bar narrative) | `filter_l12m(eligible_data)` | PIPELINE DCTR -- UNSAFE as Truth slide |
| DCTR-4/5/6/7 | dctr/penetration.py:444-494 | Personal / Business DCTR | eligible-P / eligible-B subsets | PIPELINE DCTR |
| DCTR-9 | dctr/branches.py:113 | "Branch X% DCTR" | branch-level eligible subset | PIPELINE DCTR |
| A7.4, A7.6a, A7.6b | dctr/trends.py | Monthly DCTR trend | eligible subset | PIPELINE DCTR |
| A7.7 / A7.8 | dctr/funnel.py | Activation funnel | `eligible_data` | PIPELINE DCTR |
| A7.10a / A7.10b | dctr/branches.py | Branch ranking | eligible subset | PIPELINE DCTR |
| A7.11, A7.12 | dctr/trends.py (age) | DCTR by age | eligible subset | PIPELINE DCTR |
| A11.1 | value/analysis.py:267 | "Value of a debit card" -- multiplies `accts_without * delta` | `eligible_personal` | PIPELINE DCTR (indirectly -- `accts_without` is sized off eligible) |
| S1 | insights/synthesis.py:55 | "Revenue Gap" -- uses `value_1.accts_without` | `eligible_personal` via value_1 | PIPELINE DCTR downstream -- UNSAFE as Opportunity headline |
| S7 | insights/conclusions.py:194 | "What If +5 points of DCTR" -- multiplies pipeline DCTR delta | eligible subset | PIPELINE DCTR -- if used, annotate explicitly |
| A18.1 | insights/effectiveness.py:323 | DCTR progression | eligible subset | PIPELINE DCTR |
| A18.3 | insights/effectiveness.py:352 | Industry benchmark vs our DCTR | eligible subset | PIPELINE DCTR -- benchmark comparison is only valid if both use the same denominator; verify before using |

**Clean slides** (no penetration claim, or uses a denominator that is not the disputed one):
- All Reg E slides (A8.*) -- Reg E numerator/denominator are internally consistent; flag only the "Reg E + debit" combined funnel (A8.10/A8.11) which inherits DCTR assumptions.
- All attrition slides (A9.*) -- attrition rates are account churn, not penetration.
- All mailer slides (A12-A17) -- response rates are numerator/denominator within the mail universe.
- A11.2 Reg E value -- Reg E denominator not in dispute.

**Recommendation:** any slide in the PIPELINE DCTR column above that is retained in the main deck must either (a) be reworked to use the notebook customer-level number, or (b) carry an explicit footnote naming the denominator. The Truth slide and Opportunity headline must use the notebook number.

---

## 6. Optional persona deep-dive module

Separate appendix pack, toggled per client. Not in the core deck. Each persona gets 3-5 slides.

### 6.1 Non-User (maps to Engagement Gap)

| # | Slide | Source analytics |
|---|---|---|
| 1 | Non-User sizing (count, % of portfolio) | dctr/penetration (complement of DCTR-3) |
| 2 | Non-user profile (age / tenure / balance) | dctr/trends (age) + attrition/dimensions (tenure/balance) |
| 3 | Where they live (branch dispersion) | dctr/branches A7.10a |
| 4 | Dormant population overlap | insights/dormant A20.1, A20.2 |
| 5 | Activation unlock value | value/analysis A11.1 (requires denominator fix) |

### 6.2 Climber (maps to Targeting Gap)

| # | Slide | Source analytics |
|---|---|---|
| 1 | Who responds today (mailer responder profile) | mailer/response A14.2 |
| 2 | Responder spend trajectory | mailer/cohort A16.1 |
| 3 | Per-segment trajectory (which climbers climb most) | mailer/cohort A16.3 |
| 4 | Spend direction change | mailer/cohort A16.5 |
| 5 | Branch opportunity map (where climbers are concentrated) | insights/branch_scorecard A19.2 |

### 6.3 Decliner (maps to Ecosystem / Retention)

| # | Slide | Source analytics |
|---|---|---|
| 1 | Decliner sizing + velocity | attrition/rates A9.1, attrition/impact A9.12 |
| 2 | Decliner profile (tenure / product / balance) | attrition/dimensions A9.5, A9.7, A9.8 |
| 3 | What retains them (debit card retention effect) | attrition/impact A9.9 |
| 4 | Mailer retention lift | attrition/impact A9.10 |
| 5 | At-risk targeting matrix | insights/dormant A20.2, A20.3 |

---

## 7. Open questions

1. **Decliner placement (Diagnosis/Ecosystem vs Opportunity).** Current blueprint puts Decliner under Ecosystem Gap inside Diagnosis because the data (A9.*, A20.*) reads as "here is what is breaking." If the narrative wants Decliner to be a "save-the-save" growth lever, it belongs under Opportunity. Confirm before plan is frozen.

2. **Source of the notebook truth number.** Slides Truth-1, Truth-2, Opp-1, and the reworked S1/S7/A11.1 all depend on a customer-level debit penetration number from the Jupyter notebook. Where is that number today -- is there a parquet/CSV export that the pipeline can read, or does a new one-time handoff need to land in `01_Analysis/` first? Without it, the rebuild ships with the pipeline-DCTR number it was meant to replace.

3. **Insights S-slide selection.** Eight S1-S8 slides exist. The blueprint reuses S1, S3, S6, S7, S8 and sends S2, S4, S5 to appendix. S5 (Debit Card Cascade) is a strong narrative slide and could replace one of the Plan pillars if the Plan section leans on the "one activation = three revenue streams" story. Confirm which way to lean.

4. **Mailer month depth in main deck.** The existing pipeline auto-puts the 2 most recent mailer months in main and the rest in appendix. The new narrative probably only wants the most recent month in Plan (as evidence) and sends the rest to appendix. Confirm: keep 2 months in main, or drop to 1?

5. **Transaction and ICS sections.** Both are registered but produce no slides today (`analytics/transaction` and `analytics/ics` do not exist yet). The blueprint assumes they are out of scope for the rebuild. Confirm -- if TXN content is arriving soon it may reshape Diagnosis/Ecosystem.

6. **Benchmark slide (A18.3).** Industry benchmark comparison is a strong Plan slide, but only if both sides of the comparison use the same denominator. Needs verification before it lands in Plan.

7. **Agenda slide form.** Replace P02 with a new 4-beat agenda (Truth / Diagnosis / Opportunity / Plan), or fold the agenda into a narrative first-slide and drop P02 entirely? Either works; confirm for the production template.
