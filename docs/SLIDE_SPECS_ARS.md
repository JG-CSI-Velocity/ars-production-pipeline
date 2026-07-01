# ARS Slide Specifications

**Purpose:** one row per slide — population (which accounts), calculation
(the formula), source columns, provenance, and how much to trust it. Anything
marked **UNAUDITED** has never been line-by-line verified against owner
expectations.

**Trust levels**
- `LOCKED` — formula enforced by a synthetic-data test; cannot silently change
- `Note` — provenance for a past behavior change (commit noted); verify if in doubt
- `UNAUDITED` — ported from notebooks, never owner-verified; treat with suspicion

**Populations (the four bases)**
| Base | Definition | Built in |
|---|---|---|
| **Total** | every row in the ODD (open + closed, all products) | `ctx.data` (load.py) |
| **Open** | `Stat Code` starts with "O" OR `Date Closed` blank | `subsets.open_accounts` |
| **Eligible** | Open ∩ eligible stat codes ∩ eligible product codes (client config, normalized) | `subsets.eligible_data` |
| **Eligible Personal w/Debit** | Eligible ∩ `Business? ∉ {YES,Y}` ∩ has debit card | `rege/_helpers.reg_e_base()` |
| **L12M Exposure** (attrition only) | opened ≤ window end AND not closed before window start; **full book** (all products) | `attrition/_helpers.l12m_attrition()` |

L12M window = last 12 *complete* calendar months (`ctx.start_date..ctx.end_date`).

---

## Overview

| Slide | What it shows | Population | Calculation | Status |
|---|---|---|---|---|
| A1 | Account status composition | Total | counts by `Stat Code`, eligible flagged | **skipped from deck** (covered by exec dashboard) |
| A1b | Product mix, Personal vs Business stacked bar | Total | counts by `Product Code` × `Business?` | **Note** — chart is NEW (was Excel-only) and slide was un-skipped (`cb7312a`, `10a556e`). Top-12 codes + Other; ✓ marks eligible product codes |
| A3 | Eligibility funnel | Total → Eligible | stage counts: Total → Open → +stat → +product → ELIGIBLE; **bar %s = share of Total Accounts** (eligibility rate is defined against total) | **Note** — was an ax.table screenshot; now true funnel; un-skipped (`cb7312a`) |

## DCTR (A7.x / DCTR-x)

Core formula everywhere: `dctr(df) = accounts with debit ÷ accounts in df`
(debit = `Debit?` ∈ {YES,Y,TRUE,1,D,DC,DEBIT} via `shared/debit.py`).

| Slide | Population | Calculation | Status |
|---|---|---|---|
| DCTR-1/2/6/7/8 | Eligible (DCTR-2 also Open, allow-listed) | rate tables by year/L12M | Excel-only detail; DCTR-1 skipped from deck. UNAUDITED beyond denominator law |
| DCTR-3 | Eligible | TTM snapshot bars + narrative | UNAUDITED (reviewed: acceptable) |
| DCTR-4/5 | Eligible Personal / Business | historical rate bars | UNAUDITED; appendix |
| DCTR-9 | Eligible by `Branch` | branch rates, top 10 | UNAUDITED |
| DCTR-10/11 | Eligible by account/holder age | rate by age bucket (merged slide) | UNAUDITED |
| A7.4 | Eligible P/B × Historical/TTM | 4-bar comparison (merged w/ A7.6a) | UNAUDITED |
| A7.6a | Eligible opened per L12M month | monthly Overall/Personal/Business DCTR lines + volume bars | **Note** (`59603d5`): legend was WRONG (said "Historical/TTM" for Overall/Personal lines) — relabeled; brand colors |
| A7.7/A7.8 | Total→Open→Eligible→w/Debit | funnel w/ Personal/Business split (custom renderer, NOT draw_funnel) | unchanged; UNAUDITED |
| A7.10a | Eligible per branch, L12M | volume bars + DCTR dots + portfolio avg line | **Note** (`59603d5`): colors only; math untouched |
| A7.5/6b/9/10b/13/14/15 | Eligible cuts | decade/seasonality/vintage/heatmap | UNAUDITED; appendix |

## Reg E (A8.x)

**Owner rule (locked):** opt-in rate = personal w/ Reg E ÷ **Eligible Personal
w/Debit**. Opt-in codes from client config; latest `Reg E Code {Mon}{yy}`
column auto-detected.

| Slide | Population | Calculation | Status |
|---|---|---|---|
| ALL A8.x rates | Eligible Personal w/Debit | opted-in ÷ base | **Note** (`9d7c84c`): base previously did NOT filter to debit holders — every A8 rate had a larger denominator. `LOCKED` by test (2 opt-in / 4 debit holders = 50%) |
| A8.1 | base, all-time vs L12M | two donuts | base change above; donut layout unchanged |
| A8.3 | base opened per L12M month | monthly opt-in line + volume bars + historical ref line | base change + brand colors (`a9615e5`) |
| A8.10/A8.11 | Open→Eligible→w/Debit→Personal w/Debit→w/Reg E | funnel; **bar %s = conversion from the PREVIOUS stage** (final bar = the owner's opt-in rate) | **Revised twice**: rebuilt on draw_funnel (`a9615e5`), then % basis corrected after owner review (`1b8e1ea`). A8.10's "Personal w/Debit" stage previously wasn't debit-filtered (could exceed prior stage) — fixed |
| A8.2/4b/4c/5/6/7/12/13 | base cuts | year/decade/branch/age/product | base change applies; otherwise colors only |

## Attrition (A9.x)

**Closed** = `Date Closed` parses. **Population = FULL BOOK (all products)** —
the eligible-products scoping forced earlier collapsed real counts and was
reverted shortly after (`1b8e1ea`); opt-in via `ARS_ATTRITION_ELIGIBLE_ONLY=1`.

**One L12M rate everywhere (LOCKED):** closures in window ÷ L12M Exposure
base. Previously A9.0/A9.1/A9.4 used three different denominators.

| Slide | Calculation | Status |
|---|---|---|
| A9.0 | L12M opens/closes/net tiles + monthly trend; attrition tile = standardized rate; first-year closes capped at window end | **Note** (`10a556e`); LOCKED |
| A9.1 | headline = standardized L12M rate; lifetime share demoted to context (was presented as "Overall Attrition Rate" and graded red on the exec dashboard forever) | **Note**; LOCKED |
| A9.2 | closure duration distribution (lifespan buckets of closed) | audited correct; unchanged |
| A9.3+A9.6 (merged) | open-vs-closed profile + P/B split; A9.6 now L12M + normalized `Business?` matching (exact 'Yes'/'No' match previously zeroed Y/N data) | **Note**; LOCKED |
| A9.4/4b/4c | branch cuts on the standardized base; 4b closures bounded to window | **Note** |
| A9.5 | by product, L12M (was lifetime share) | **Note** |
| A9.7 | closure hazard by tenure: closures with lifespan in bucket ÷ accounts that SURVIVED INTO bucket (old version could exceed 100%) | **Note**; LOCKED |
| A9.8 | by balance tier, L12M; stale-closed-balance caveat | **Note** |
| A9.9/A9.10 | debit/mailer retention comparison on L12M window (was lifetime — old closures piled into the comparison group) | **Note** |
| A9.11 | revenue lost = last NONZERO monthly spend (chronological — was ALPHABETICAL month order) × ic_rate × 12, L12M closures only (was all history) | **Note**; LOCKED |
| A9.12 | monthly closures + 3-mo MA | audited correct; unchanged |
| A9.13 | eligible-products vs other-products L12M comparison (was circular via stat codes) | **Note** |

## Value (A11.x)

| Slide | Calculation | Status |
|---|---|---|
| A11.1/A11.2 | debit-card / Reg E value: `nsf_od_fee` + ic_rate math | **ic_rate Note** (`8006e4f`): client config wins, fallback 0.0065 (was unset → could zero out). Otherwise UNAUDITED |

## Mailer (A12–A17)

| Slide | Calculation | Status |
|---|---|---|
| A13.{month} | monthly summary: mailed/responded by segment + commentary sentences (PR #189) | **Note** (owner PR #189): MoM delta removed, commentary added, navy title. **KNOWN BAD: commentary text renders mid-slide — layout fix outstanding** |
| A12.{month}.Swipes/.Spend | responder swipes/spend per month | **routing Note** (`3dcff3e`): archived to appendix every month (combo replaces them in main) |
| A16.7.{month} | combo Spend+Swipes trajectory, Responder vs Non-Responder per segment, M0 line | **New** (PR #189) + hotfixes: capped to 2 most recent waves, 5 standard segments only (`aa4b075`); kill switch = `SKIP_COMBO.flag` at M:\ARS or `ARS_SKIP_COMBO=1` (`45f32b5`). |
| A13.Agg / A13.5 / A13.6 / A14.x / A15.3 / A16.x / A17.1 | aggregate/revisit/attribution/cohort/reach | UNAUDITED (A15.3 ic_rate rule applies). **The reported ARS hang is in this section (module 18 ≈ mailer.response) — unresolved, need run-log lines** |

## Insights (S1–S8, A18–A20)

| Slide | Calculation | Status |
|---|---|---|
| A18 effectiveness, A19 branch scorecard | ROI/opportunity math | **ic_rate Note**: fallback was **0.0015**, now 0.0065 → **revenue-opportunity numbers will be ~4.3× HIGHER than prior decks. This is intentional (owner rule).** Otherwise UNAUDITED |
| S1–S8, A20 | synthesis/conclusions/dormant | UNAUDITED |

## ICS

| Slide | Status |
|---|---|
| ICS module | UNAUDITED — not yet reviewed |

---

## Known corrections (owner-found)

1. **Reg E funnel bar %s used Open Accounts as the denominator for every stage**
   (the draw_funnel default), hiding the defined opt-in rate. Fixed `1b8e1ea`.
2. **Attrition counts collapsed to ~100 L12M closures** — the population had been
   scoped to eligible product codes. Reverted to full book (`1b8e1ea`); scoping is
   now opt-in only via `ARS_ATTRITION_ELIGIBLE_ONLY=1`.
3. **Mailer commentary can render mid-slide** (PR #189 layout interaction) — open
   caveat; layout fix outstanding.

## Going forward: the Excel-first contract

One sheet at a time: owner sends the analysis Excel sheet → slide is built to
spec on the CSI template → owner approves → THEN it is wired into the pipeline
and its numbers locked as a test. **Nothing editorial ships without explicit
owner approval.** Approved slides get a `LOCKED (owner)` status in this file.
