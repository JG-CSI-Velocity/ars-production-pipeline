# Module Reference

The pipeline's calculators and the DataFrames they read from. Use this when you need to know **what a rate divides by**, **which DataFrame slice a module touches**, or **where a downstream consumer (Insights, Value, the Scorecard) gets its inputs**.

For run instructions, see [`../README.md`](../README.md). For slide IDs → layouts → headlines, see [`../SLIDE_MAPPING.md`](../SLIDE_MAPPING.md).

---

## 1. The denominator framework (LAW)

Every rate the pipeline ships divides by one of four canonical bases. This is enforced at run time by `pipeline/steps/audit.py`, which writes `rates_audit.csv` next to the run manifest and stamps an `AnomalyFlag(WARN)` on the manifest for any rate that breaks the rule.

| Label | What it means | Used by |
|---|---|---|
| **Eligible** | Open accounts that match the client's `EligibleStatusCodes` × `EligibleProductCodes` | DCTR, Attrition, Value, Mailer, Insights — the default |
| **Eligible Personal** | Eligible filtered to `Business? != Y` | personal-only metrics |
| **Eligible Personal w/Debit** | Eligible Personal filtered to `has_debit` | Reg E (consumer-only by regulation; opt-in governs ATM/one-time **debit** overdraft, so the base is debit holders -- owner decision 2026-06-11) |
| **Eligible Business** | Eligible filtered to `Business? == Y` | Business-only sub-views |
| **Open** | Date Closed is blank OR Stat Code starts with `O` | Reference framing only — allowed as a primary denominator on `DCTR-2` (methodology slide) and flagged anywhere else |

**Why this matters**: before W1 (PR #161), DCTR on the deck read ~30% while the notebook read ~80% for the same client. The difference was the denominator: deck used Eligible, notebook used Open. Codifying the law and auditing every rate per run prevents silent drift between consumers.

A module records its denominator by stamping `denominator_label` and `denominator_n` on the `AnalysisResult`. If left blank, `audit.py` infers the default from the slide-ID prefix (see `DEFAULT_BY_PREFIX` in `pipeline/steps/audit.py`).

---

## 2. Shared DataFrame vocabulary

`ctx.subsets` (a `DataSubsets` dataclass; see `pipeline/context.py`) holds the canonical slices, built once by `pipeline/steps/subsets.py` and zero-copy under pandas Copy-on-Write.

| `ctx.subsets.*` | Definition | Built by |
|---|---|---|
| `open_accounts` | `Stat Code` starts with `O` **OR** `Date Closed` is blank | `step_subsets` row 47–80 |
| `eligible_data` | `open_accounts` ∩ `Stat Code ∈ EligibleStatusCodes` ∩ `Product Code ∈ EligibleProductCodes` | `step_subsets` row 86–125 |
| `eligible_personal` | `eligible_data` filtered to `Business?` ∉ (Yes, Y) | `step_subsets` row 128–135 |
| `eligible_business` | `eligible_data` filtered to `Business?` ∈ (Yes, Y) | same |
| `eligible_with_debit` | `eligible_data` filtered to debit-indicator ∈ (D, DC, Debit, Yes, Y) — column auto-detected | `step_subsets` row 137–160 |
| `last_12_months` | `Date Opened` ≥ start of (today minus 12 complete months) | `step_subsets` row 162–180 |

The auto-detected debit column is also stashed on `ctx.debit_column` for downstream modules. `analytics/dctr/_helpers.py::debit_mask(df, col)` is the canonical "has debit?" predicate — accepts strings (`Yes`/`Y`/`D`), booleans, and integers uniformly, and **every module that filters on debit must use it** to keep the vocabulary unified.

---

## 3. The result handoff

Each module writes one entry per slide (or per intermediate metric) into `ctx.results[<key>]`, a dict. Downstream consumers — Insights, Value, the run scorecard — read those keys back via the safe accessors in `analytics/insights/_data.py`. If a key is missing, the accessor returns a zero-shaped dict so the consumer never crashes; the silently-zero metric shows up as a fail on the scorecard instead.

Pattern:

```python
# In dctr/penetration.py
ctx.results["dctr_1"] = {"yearly": yearly, "decade": decade, "insights": ins}

# In insights/_data.py
def get_dctr_1(ctx):
    r = ctx.results.get("dctr_1", {})
    return r.get("insights", {"overall_dctr": 0, "recent_dctr": 0, "total_accounts": 0})
```

Insights / Value / Scorecard never recompute from raw `ctx.data` — that was the bug that prompted #144 item 2.5. The single-writer rule keeps downstream consumers honest.

---

## 4. ARS modules (25 across 7 sections)

Each entry below covers what dataframe slice the module reads, what it calculates, the slide IDs it emits, and the `ctx.results` keys it produces for downstream consumers.

### 4.1 Overview — `analytics/overview/`

| Reads | Writes (`ctx.results`) | Slide IDs | Denominator |
|---|---|---|---|
| `subsets.open_accounts`, `subsets.eligible_data`, `subsets.eligible_personal`, `subsets.eligible_business` | `a1`, `a3` | `A1`, `A1b`, `A3` | Open (counts only) |

**Calculators**:

- `A1` — total open, eligible, personal/business split, eligibility rate
- `A1b` — companion split view
- `A3` — eligibility funnel: `total_accounts → open → eligible`, with the funnel rates

No rates are gated by the denominator law here — these slides report counts and the eligibility rate (which is a structural ratio, not a rate-of-X).

### 4.2 Debit Card Take Rate (DCTR) — `analytics/dctr/`

The largest ARS section. 28 slides, 5 calculator submodules.

| Reads | Writes (`ctx.results`) | Slide IDs |
|---|---|---|
| `subsets.eligible_data`, `subsets.open_accounts`, `subsets.eligible_personal`, `subsets.eligible_business`, `subsets.eligible_with_debit` | `dctr_1` … `dctr_16`, `dctr_funnel`, `dctr_l12m_funnel`, `dctr_elig_vs_non`, `dctr_branch_trend`, `dctr_segment_trends` | `DCTR-1` … `DCTR-16`, `A7.4` … `A7.15` |

**Calculators** (anchor: `dctr/penetration.py`):

- `DCTR-1` — **Historical DCTR**. `has_debit ∩ Eligible / Eligible`. Denominator label: `Eligible`.
- `DCTR-2` — **Open vs Eligible methodology slide**. Companion view that runs the same numerator against `Open` to explain why the canonical Eligible denominator is the right one. Denominator label: `Open` (whitelisted).
- `DCTR-3` — **L12M DCTR**. Same as DCTR-1, restricted to accounts opened in the last 12 complete months. Branch ships an `Eligible L12M` companion alongside.
- `DCTR-4..8` — segment cuts (personal vs business, holder age, account age, channel).
- `DCTR-9` — **Branch DCTR**. Per-branch rate from `eligible_data` joined to `BranchMapping`. Surfaces best/worst branch + spread.
- `DCTR-10..16` — branch deep-dives (trend, funnel, holder cohort breakdowns).

**Calculator pattern** — every rate computes as `numerator / canonical_base` and is rounded only at presentation time. The unrounded value is what gets stamped on the `AnalysisResult`'s `denominator_n` and what the scorecard / audit consume.

Helpers: `dctr/_helpers.py::debit_mask` (the universal has-debit predicate), `analyze_historical_dctr` (yearly/decade aggregator).

### 4.3 Reg E / Overdraft — `analytics/rege/`

13 slides. Reg E is regulated to consumer accounts only and the opt-in governs debit-card overdraft, so the denominator is always **Eligible Personal w/Debit**.

| Reads | Writes (`ctx.results`) | Slide IDs | Denominator |
|---|---|---|---|
| `subsets.eligible_personal`, `subsets.eligible_data`, `subsets.eligible_with_debit`, `subsets.last_12_months`, `subsets.open_accounts` | `reg_e_1` … `reg_e_13` | `A8.1` … `A8.13` | `Eligible Personal w/Debit` |

**Calculators** (anchor: `rege/penetration.py`, helpers in `rege/_helpers.py`):

- `A8.1` — **Reg E opt-in rate**. `opted_in_codes ∩ eligible_personal / eligible_personal`. Reads `Reg E Code [YYYY-MM]` columns; column-of-record selected by `detect_reg_e_column()` which **sorts by parsed date and takes the most recent**, not by alphabetical order (the historical bug from audit item 2.6).
- `A8.2..6` — opt-in trends (monthly), segment cuts (holder age, channel), branch breakdown.
- `A8.4a/b/c` — three-pane Reg E by holder cohort.
- `A8.7..13` — overdraft analyses: NSF revenue per opted-in vs opted-out account, recapture potential.

**Why `Eligible Personal w/Debit`** — the post-2010 Reg E amendment applies to consumer overdraft only, and the opt-in decision specifically governs ATM / one-time **debit** transactions. Owner decision (2026-06-11): the rate base is `eligible_personal ∩ has_debit` (`reg_e_base()` in `_helpers.py`), superseding the earlier reading that kept the base at `Eligible Personal`.

### 4.4 Attrition — `analytics/attrition/`

17 slides. Closure rates and the cohort/revenue impact.

| Reads | Writes (`ctx.results`) | Slide IDs | Denominator |
|---|---|---|---|
| `ctx.data` (uses its own Date Closed filter) | `attrition_1` … `attrition_13`, `attrition_cohort`, `attrition_cohort_monthly`, `_attrition_data` | `A9.0` … `A9.13` | `Eligible` |

**Calculators** (anchor: `attrition/penetration.py`):

- `A9.0/0b` — agenda / methodology preamble.
- `A9.1` — **Overall attrition rate**. `closed_during_period / total_at_start`. Returns `overall_rate`, `l12m_rate`, `total`, `closed`.
- `A9.2..8` — by holder cohort, by account age, by branch, channel.
- `A9.9` — **Debit retention lift**: difference in closure rate between debit holders and non-holders.
- `A9.10` — **Mailer retention lift**: same idea for mailer responders.
- `A9.11` — **Revenue impact**: dollars lost = `closed accounts × avg revenue/account/year`. Returns `total_lost`, `avg_lost`.
- `A9.12` — **Velocity** (rolling 12-month attrition trend).
- `A9.13` — branch heatmap.

Attrition is the section most heavily consumed downstream: Insights (`S2` uplift), Value (`A11.2`), and the scorecard's "retention" verdict all pull from `attrition_1`, `attrition_9`, `attrition_11`, `attrition_12`.

### 4.5 Value — `analytics/value/`

2 slides. Translates DCTR and Reg E gaps into dollars.

| Reads | Writes (`ctx.results`) | Slide IDs | Denominator |
|---|---|---|---|
| `subsets.eligible_personal`, upstream `ctx.results["dctr_1"]`, `ctx.results["reg_e_1"]` | `value_1`, `value_2` | `A11.1`, `A11.2` | `Eligible` |

**Calculators**:

- `A11.1` — **Debit card value gap**. Compares revenue/account between debit holders and non-holders × the population that would convert at historical DCTR vs L12M DCTR vs 100%. Returns `delta`, `accts_with`, `accts_without`, `rev_per_with`, `rev_per_without`, `hist_dctr`, `l12m_dctr`, plus three "potential" recapture numbers (`pot_hist`, `pot_l12m`, `pot_100`).
- `A11.2` — **Reg E value gap**. Same pattern, opt-in rate × NSF/OD revenue/account.

Value does NOT recompute the rates — it pulls from `ctx.results["dctr_1"]` and `ctx.results["reg_e_1"]` via `_data.py` accessors. If those upstreams failed, Value gets zeros and prints a SOFT FAILURE on the scorecard.

### 4.6 Mailer Campaign — `analytics/mailer/`

21 slides. The most data-hungry ARS section.

| Reads | Writes (`ctx.results`) | Slide IDs |
|---|---|---|
| `subsets.open_accounts`, `subsets.eligible_data`, `subsets.eligible_with_debit`, raw `ctx.data` (mailer columns) | `market_reach`, `revenue_attribution`, `pre_post_delta`, `monthly_summaries`, `aggregate_summary`, `reach_cumulative`, `rate_trend`, `a16_spend_traj`, `account_age`, `spend_share`, `_mailer_pairs` | `A12`, `A13`, `A13.5`, `A13.6`, `A13.Agg`, `A14.2`, `A15.1` … `A15.4`, `A16`, `A16.1` … `A16.6`, `A17`, `A17.1`, `A17.2`, `A17.3` |

**Calculators** (anchor: `mailer/reach.py`):

- `A12/A13` — mailer overview and per-month detail tables.
- `A14.2` — response funnel.
- `A15.1` — **Market reach**: `n_responders / n_eligible`. The cumulative-reach chart on `A17.1` shares this base.
- `A15.2` — segment lift.
- `A15.3` — **Revenue attribution**: incremental interchange from responders. Returns `resp_ic`, `non_ic`, `incremental_total`.
- `A15.4` — **Pre/post spend delta**: response cohort spend before vs after, vs non-response control. Returns `resp_pre`, `resp_post`, `resp_delta`, `non_pre`, `non_post`, `non_delta`.
- `A16.x` — spend trajectory by cohort over time.
- `A17.x` — cumulative reach + summary charts (cache-adopted via chart-cache infrastructure; see `docs/chart-cache-adoption.md`).

Denominator: `Eligible` (the mailable subset is numerator framing, not a denominator narrowing).

### 4.7 Insights — `analytics/insights/`

18 slides. Pure synthesis — reads from `ctx.results` written by every other section, never recomputes from raw data.

| Reads | Writes (`ctx.results`) | Slide IDs |
|---|---|---|
| `subsets.eligible_data` (for population context), upstream `ctx.results["dctr_*"]`, `["reg_e_*"]`, `["attrition_*"]`, `["value_*"]`, `["market_reach"]`, `["revenue_attribution"]`, `["pre_post_delta"]`, `["a3"]` | `dormant`, `synthesis`, `branch_scorecard`, others | `S1` … `S8` (story slides), `A18`, `A18.1/2`, `A19`, `A19.1/2`, `A20`, `A20.1` … `A20.3` |

**Calculators**:

- `S1` — **Revenue Gap waterfall**: DCTR potential + Reg E potential + mailer recapture, summed and bridged. Pulls from `get_value_1`, `get_value_2`, `get_revenue_attribution`.
- `S2` — **Uplift narrative**: retention + acquisition story.
- `S3..S8` — successive cuts of the same story (branch, cohort, segment).
- `A18.x` — synthesis pages.
- `A19.x` — **Branch scorecard**. Reads `dctr_branches`, `rege_branches`, `attrition_branches` from `ctx.results` so the scorecard can't diverge from the section pages — fixes audit item 2.5.
- `A20.x` — **Dormant opportunity**. Reads from `analytics/insights/dormant.py`. The top-quartile-balance cut documented in audit item 2.7 still computes `q75` on **all accounts** and then applies the threshold to the no-debit slice; the intentional interpretation is "accounts in the top 25% of the whole portfolio by balance who don't have a debit card."

Failure handling: every accessor (`_data.py::get_*`) returns a zero-shaped default if upstream is missing, and `_data.py::_safe(fn, label, ctx)` wraps every analysis to convert exceptions into a failed `AnalysisResult` + an `AnomalyFlag(WARN)` on the run manifest. Insights never crashes the deck — it just ships zeros and a SOFT FAILURE line.

---

## 5. TXN sections (22)

TXN scripts are notebook-cell style (numbered files executed by `txn_wrapper.py`), not the `AnalysisModule` ABC. Each section folder contains numbered scripts that run in order; `txn_exports.py` declares which variables each script exposes to `ctx.results`.

| Section | Display name | Scripts | Headline metrics |
|---|---|---:|---|
| `general` | Portfolio Overview | 30 | Portfolio KPIs, demographics, ARS-swipe segmentation |
| `merchant` | Merchant Analysis | 14 | Top merchants, concentration (top-N share), trends |
| `mcc_code` | MCC Categories | 15 | Spend by MCC category, seasonality (12-month window) |
| `business_accts` | Business Accounts | 14 | Business spend patterns + lifecycle |
| `personal_accts` | Personal Accounts | 14 | Consumer spend patterns + lifecycle |
| `competition` | Competition | 46 | Wallet share, at-risk accounts, CU/bank scatter, BNPL audit |
| `financial_services` | Financial Services | 20 | FI leakage, brand-root detection |
| `ics_acquisition` | ICS Acquisition | 10 | Channel attribution |
| `campaign` | Campaign Analysis | 43 | TXN-side mailer cohort lift |
| `branch_txn` | Branch Performance | 10 | Branch-level spend (joins to `BranchMapping`) |
| `transaction_type` | Transaction Type | 16 | PIN / SIG / ACH channel mix |
| `product` | Product Analysis | 10 | Product-level spend |
| `attrition_txn` | Attrition (Velocity) | 12 | Velocity-based risk score |
| `balance` | Balance Analysis | 10 | Balance-band cuts |
| `interchange` | Interchange Revenue | 10 | PIN vs SIG revenue per swipe |
| `rege_overdraft` | Reg E / Overdraft | 10 | Opt-in trends from TXN data |
| `payroll` | Payroll & Direct Deposit | 10 | DD detection, PFI scoring (`.str[]` cast guarded) |
| `relationship` | Relationship Depth | 10 | Cross-product holdings |
| `segment_evolution` | Segment Evolution | 8 | Engagement-tier migration |
| `retention` | Retention Analysis | 7 | Churn / dormancy |
| `engagement` | Engagement Migration | 6 | Monthly tier classification |
| `executive` | Executive Scorecard | 5 | KPI scorecard, action roadmap |
| `cross_cohort` | (helper) | 12 | Reusable cohort joins; not a deck section |

**TXN data foundation** lives in `analytics/txn_setup/` (10 scripts): file loading, merchant-name consolidation (`standardize_merchant_name` runs a 3-pass address suffix stripper, then prefix-based normalization), parquet cache write-through. Per-client competitor rules in `analytics/competition/01_competitor_config.py`.

**Slide IDs**: TXN slides emit IDs of the form `TXN-{section_code}-NN` (e.g. `TXN-CO-01` for competition slide 1). The section_code is the short prefix declared on each `TXN_SECTIONS` entry; this is what `SLIDE_MANIFEST.xlsx` matches against for `Keep?` decisions.

---

## 6. Cross-cutting calculators

| Helper | Where | What |
|---|---|---|
| `debit_mask(df, col)` | `analytics/dctr/_helpers.py` | Universal "is debit holder?" predicate — accepts strings/booleans/ints. Every module that filters on debit MUST use this. |
| `detect_reg_e_column(df)` | `analytics/rege/_helpers.py` | Returns the most-recent-by-date `Reg E Code [YYYY-MM]` column. **Not alphabetical** — alphabetical order was the audit-2.6 bug. |
| `reg_e_base(ctx)` | `analytics/rege/_helpers.py` | Returns `(base_df, base_l12m_df, reg_e_col, opt_list)` — the canonical Reg E inputs every Reg E slide reads. |
| `BranchMapping` | `03_Config/clients_config.json` → `analytics/shared/branch_mapping.py` | Per-client `"branch_id" → "Branch Name"` dict. Branch Performance + Branch Scorecard + branch DCTR all read this. |
| `step_subsets` | `pipeline/steps/subsets.py` | Builds `ctx.subsets`. Auto-detects `Stat Code` / `Date Closed` / `Debit?` column names from a candidate list. |
| `step_audit` | `pipeline/steps/audit.py` | Writes `rates_audit.csv`; flags every `denominator_label` that breaks the LAW. |
| `chart-cache` | `analytics/_chart_cache.py` + `docs/chart-cache-adoption.md` | Content-hash PNG cache. Adopted on `A7.2`, `A8.1`, `A9.1`, `S1`, `A17.1`; rest of the chart sites pending. |

---

## 7. Adding a new analytics module

1. Create `analytics/<section>/<n>_<name>.py`. Subclass `AnalysisModule` from `analytics/base.py`.
2. Declare `module_id`, `display_name`, `section` (must be one of the `SectionName` Literal options — extend that Literal if you're adding a wholly new section).
3. Declare `required_columns` and (optionally) `required_ctx_keys`. `validate()` will run before `run()` and short-circuit with a clean error if a column is missing — and it'll auto-accept any equivalent in `_FLEXIBLE_COLUMNS` (e.g. `Debit?` matches `DC Indicator`).
4. Implement `run(ctx) → list[AnalysisResult]`. For each result that ships a rate, stamp `denominator_label` and `denominator_n` — the audit step will then validate it against the LAW automatically.
5. If downstream sections need a result, also write it to `ctx.results["<module_id>_<n>"]` so the `_data.py` accessor pattern can read it.
6. Register the module in `analytics/registry.py`.
7. Add a test under `01_Analysis/00-Scripts/tests/`. The W1 audit framework expects every rate to have a matching `denominator_label`; tests catch regressions on that automatically.

For deeper architectural patterns (run manifest, scorecard, error capture, anomaly flags), see [`../CONTRIBUTING.md`](../CONTRIBUTING.md).
