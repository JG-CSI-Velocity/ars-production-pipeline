# ARS Analytics Data Quality Audit

**Generated:** 2026-04-17
**Branch:** feature/data-quality-audit
**Scope:** 01_Analysis/00-Scripts/analytics/ (27 folders)
**Method:** Static code audit using data-quality-audit + metric-reconciliation skill methodology

## Context Summary

- **Known critical bug:** DCTR denominator mismatch — pipeline reports ~30% against the authoritative Jupyter notebook's ~80%+.
- **Root cause hypothesis (confirmed by code):** every DCTR rate is calculated against `ctx.subsets.eligible_data` (the output of the multi-stage eligibility funnel in `overview/eligibility.py`). `eligible_data` is a *narrowed subset* — Open Accounts ∩ Eligible Stat Code ∩ Eligible Product Code ∩ (optional) Mailable — and the notebook's denominator is broader (likely all open accounts, or total customer population).
- **Secondary discovery:** Reg E rates use an even narrower denominator (`eligible_personal` AND has-debit-card), which is a legitimate product-level framing *but* is labelled simply "Reg E Opt-In Rate" on the slides without that qualifier — so the slide reader sees a number that looks like a portfolio rate but is really a conditional rate.
- **Tertiary discovery:** the Insights "Impact Story" modules (S1–S8) and Value modules (A11.*) read these narrowed rates as multipliers, so every dollar figure built on top of `value_1.delta * hist_dctr`, `opt_in_rate * ...`, etc. propagates the denominator bias downstream.
- Goal: surface every similar risk so they can be fixed before the next client ship.

## Methodology

Two passes per file: first, a structural read of every analysis module in `dctr/`, `rege/`, `value/`, `attrition/`, `insights/`, `overview/`, `mailer/`; second, a targeted grep across the TXN-style folders (`balance/`, `payroll/`, `product/`, `personal_accts/`, `business_accts/`, `retention/`, `interchange/`, etc.) for every call site that computes a rate, share, or penetration. For each site we captured: which DataFrame is the denominator, whether that DataFrame was narrowed by an earlier filter step, how nulls are handled, and which downstream module consumes the result. The module-class folders (`dctr/`, `rege/`, `value/`, `attrition/`, `insights/`, `overview/`, `mailer/`) all plug into a single `PipelineContext`; the 10-step TXN-style folders (`balance/`, `campaign/`, `competition/`, `financial_services/`, `general/`, `ics_acquisition/`, `payroll/`, `product/`, `relationship/`, `retention/`, `segment_evolution/`, plus the `*_accts/`, `*_txn/`, `merchant/`, `mcc_code/`, `transaction_type/`, `interchange/`, `rege_overdraft/`, `executive/` collections) operate on `rewards_df` / `combined_df` and build their own per-analysis DataFrames.

## Key Findings

1. **[CRITICAL] DCTR denominator is `eligible_data` everywhere.** Every rate computed in `dctr/penetration.py`, `dctr/branches.py`, `dctr/trends.py`, `dctr/overlays.py`, `dctr/_helpers.py` uses `ctx.subsets.eligible_data` (or a further-filtered slice of it) as denominator. The eligibility filter chain (`overview/eligibility.py:39–128`) drops accounts by Stat Code, Product Code, and optional Mailable flag — each stage is lossy and the combined drop is large. If the notebook divides by all open accounts (or a broader base), then the pipeline will systematically report a *lower* DCTR than the notebook. This matches the reported 30% vs. 80% gap exactly.

2. **[CRITICAL] Reg E rate denominator is `eligible_personal AND has_debit`.** `rege/_helpers.py:135–183` builds `base = eligible_personal[debit_mask]`. Every Reg E rate (A8.1, A8.2, A8.3, A8.4a/b/c/d, A8.5, A8.6, A8.7, A8.10, A8.11, A8.12, A8.13) divides opt-ins by this narrow base. If the business intent is "what fraction of our debit-card holders have opted in", this is correct; if it is "what fraction of our customers are opted in" (which the slide titles imply: "Overall Reg E Status", "Reg E Opt-In Rate") it is wrong and smaller than the true number.

3. **[HIGH] Value module (A11.1 / A11.2) inherits the denominator bias.** `value/analysis.py:353–365` reads `dctr_1.insights.overall_dctr` and `dctr_3.insights.dctr` as `hist_dctr` / `l12m_dctr`, then multiplies `awo * delta * hist_dctr` to get "Revenue Opportunity at Historical DCTR". Because `hist_dctr` is artificially low (from finding 1), the computed opportunity is also artificially low. Same cascade exists for `hist_rege` / `l12m_rege` in `_reg_e_value` (lines 571–580).

4. **[HIGH] Impact Story (S1–S8) compounds the bias.** `insights/synthesis.py` and `insights/conclusions.py` read `value_1`, `value_2`, `reg_e_1`, `dctr_1`, `dctr_9` results directly. `S1 revenue gap`, `S4 branch gap`, `S5 debit cascade`, `S6 opportunity map`, `S7 what-if +5pp DCTR`, `S8 executive summary` all produce "dollar-per-year" numbers that carry the denominator error into the final client-facing narrative — and the headline dollar number is the most memorable artifact on the deck.

5. **[HIGH] A7.7 / A7.8 funnel uses `len(data)` as total but `len(eligible_data)` as pivot.** `dctr/funnel.py:74–94` computes `through = td / ta * 100` where `ta = len(data)` (good, all rows), but `dctr_e = td / te * 100` where `te = len(eligible_data)`. Inside the slide, the "through rate" (total → debit) and "DCTR (eligible)" are shown together and the reader cannot tell which denominator applies to which label. The funnel chart itself is internally consistent, but the summary stats `ctx.results["dctr_funnel"]` surface `dctr_eligible` under a label that downstream code may treat as "the DCTR".

6. **[HIGH] `insights/branch_scorecard.py` recomputes DCTR and attrition with inconsistent denominators.** `_build_branch_data` (lines 30–101) uses the *raw* `data` DataFrame (not `eligible_data`) and divides by `n_total = len(branch_data)` — meaning this module produces a *different* DCTR than DCTR-9. Additionally, attrition is detected via `Stat Code == "C"` (line 77) which is a single-snapshot status code, not a historical closure count, and therefore misses every closure that has already been re-coded by the core. The scorecard is likely off from both DCTR-9 and A9.1.

7. **[MEDIUM] `insights/dormant.py` mixes denominators in the same slide.** Line 284: `total_eligible = len(ctx.subsets.eligible_data) if ctx.subsets else len(data)` — the function silently falls back from `eligible_data` to `data`, and the resulting `pct` label ("% of Eligible") becomes misleading when the fallback path runs. Also, `_find_dormant_accounts` uses `df[bal_col].quantile(0.75)` against the *full passed-in df* but then filters on `no_debit` — the quartile is computed before the debit filter, so "top quartile balance" refers to all accounts, not the no-debit subset (which may be defensible, but is undocumented).

8. **[MEDIUM] Multiple TXN-style files compute rates with `.mean()` on boolean columns, which silently drops NaN.** Examples: `payroll/05_payroll_by_demographics.py:113` `payroll_df['has_payroll'].mean() * 100`, `payroll/08_pfi_composite_score.py:231` `subset['has_payroll'].mean() * 100`, `payroll/09_pfi_vs_competitor.py:46` `pfi_comp.groupby('pfi_tier')['has_competitor'].mean() * 100`. If `has_payroll` is ever NaN for a row, that row is excluded from the denominator but may be miscounted at the row-count level — a classic silent narrowing.

9. **[MEDIUM] `rege/_helpers.py:45–59` silently drops all rows without a Reg E column.** Lines 48–50 in `dctr/_helpers.py:53–59` (imported by Reg E): if the debit column is missing, `debit_mask` returns an all-False Series of the same length rather than raising — downstream `rege(df[debit_mask(df)], col, opts)` will then operate on an empty base and return rate = 0.0 with no log. This is hidden division-by-effectively-zero and produces a "0% opt-in" headline without any warning.

10. **[LOW] `rege/_helpers.py:163` hard-fails if no personal-with-debit accounts exist** (`raise ValueError("No personal accounts with debit cards")`). Correct behaviour, but the failure is silent at the slide level because `_safe()` swallows it and emits an `AnalysisResult(success=False)`. A small single-client institution with zero personal debit cards will ship a deck with a quiet Reg E blank and no top-level warning.

## Detailed Findings (by folder)

### dctr/
CRITICAL. Every file here treats `ctx.subsets.eligible_data` as the canonical population.

- `dctr/penetration.py:235` `_historical` — DCTR-1 / overall_dctr divides by `len(ed)`.
- `dctr/penetration.py:241–249` — DCTR-1 notes publish "Overall: {overall_dctr:.1%}" using the narrow denominator, then S7 / S8 use it as the "current DCTR".
- `dctr/penetration.py:256–294` — DCTR-2 ("Open vs Eligible") at least exposes both `open_dctr` (divided by `len(oa)`, correct) and `eligible_dctr`. Good — this slide is the only place in DCTR where the full-population rate is even computed.
- `dctr/penetration.py:307–345` — DCTR-3 L12M divides by `len(el12)` which is eligible AND L12M. Double narrowing.
- `dctr/_helpers.py:65–75` `dctr()` — clean, takes DataFrame and returns `(total, with_debit, total/with_debit)`. The bug is *what* DataFrame is passed, not this function.
- `dctr/_helpers.py:186–198` `filter_l12m` — narrows by `Date Opened ∈ [start, end]` silently. This is labelled "L12M" but if a caller passes `eligible_data` it becomes "eligible AND L12M" without any relabelling.
- `dctr/_helpers.py:229` `detect_debit_col(valid)` — fine, uses first matching column.
- `dctr/_helpers.py:465–475` `crosstab_dctr` — reindexes by row_order/col_order which silently drops "Unknown" categories; the `coverage` insight (line 428) exposes this ratio but the pivot does not.
- `dctr/funnel.py:74–94` — funnel stages use `len(data)` as top (good), then `len(eligible_data)` as denominator for `dctr_e`. Mixed denominators in one function.
- `dctr/funnel.py:276–280` `_eligible_vs_non` — computes `non_elig = l12m_open[~l12m_open.index.isin(l12m_elig.index)]` which is honest: explicit "non-eligible" population. Good pattern.
- `dctr/branches.py:61, 127, 190, 244, 430, 498` — all six branch-level analyses use `eligible_data`. DCTR-9 best/worst branch rankings (used in S4) all inherit the denominator bias.
- `dctr/trends.py:293, 580, 664` — segment trends, seasonality, vintage all narrow to `eligible_data`.
- `dctr/overlays.py:60, 154, 270, 299, 345` — account-age, holder-age, balance-range, and crosstabs all narrow to `eligible_data`.

### rege/
CRITICAL. Narrower still: `eligible_personal ∩ has_debit`.

- `rege/_helpers.py:135–183` `reg_e_base` — returns `(base, base_l12m, col, opts)` where `base = eligible_personal[debit_mask]`. This is the single choke point. If the intent is "Reg E opt-in among personal debit holders", the label on every A8 slide needs to say so; if it's "Reg E opt-in among customers", the denominator is wrong.
- `rege/_helpers.py:95–104` `rege()` — `t = len(df); oi = len(df[df[col].isin(opt_list)])`. Clean, but `df[col]` NaN values fall to the "not opted in" bucket (via `.isin` returning False) without comment.
- `rege/status.py:59–168` A8.1 — `r_all` label: "opt-in rate". No qualifier that this is among debit holders only.
- `rege/status.py:328–474` A8.3 — L12M monthly rates all divide by the narrow base. The "historical" reference line on the chart (line 366) is also the narrow-base rate.
- `rege/dimensions.py:198–280` A8.5 by account age; line 219 `age_df['Opted In'] / age_df['Total Accounts']` where Total Accounts is narrow base.
- `rege/dimensions.py:527–585` A8.10 funnel — stages are (Open → Eligible → Eligible w/Debit → Personal w/Debit → Personal w/Reg E). The funnel itself is internally consistent because each stage is a monotonically shrinking count, but the downstream `reg_e_rate = personal_w_rege / personal_w_debit` (line 558) — again, the narrow base.
- `rege/branches.py:45–69` `_branch_rates` — per-branch opt-in still uses the narrow base.
- `rege/branches.py:215–222` `_branch_scatter` — `avg_rate` computed as weighted average of narrow-base rates; inherits the bias.

### value/
HIGH. Downstream of DCTR/Reg E.

- `value/analysis.py:257–434` A11.1 Debit card value. Revenue calc itself is sound (groupby `_has_debit`, sum NSF/OD and IC, compute delta per account). But the "Potential Revenue Opportunity" scenarios on lines 363–365 multiply `awo * delta * hist_dctr` — where `hist_dctr` is the narrowed-denominator rate from DCTR-1. A correct `hist_dctr` (full-population) would yield a higher opportunity number.
- `value/analysis.py:353–359` — fallback when DCTR-1 missing: recomputes `hist_dctr = w_ep / t_ep` using `ep = ctx.subsets.eligible_personal`. Still narrow.
- `value/analysis.py:438–649` A11.2 Reg E value. Same pattern. `hist_rege = re1.get("opt_in_rate", ...)` pulls the narrow-base Reg E rate, and the fallback on line 575 (`aw / total` where `total = aw + awo`) is calculated on the already-narrowed `active` base.
- `value/analysis.py:285–299` Date-Closed active filter — if `Date Closed` is missing, everything falls through to `active = df.copy()`. If `Date Closed` exists but contains NaT for open accounts, those accounts are retained (correct). But if `Date Closed` is stored as a string like "1900-01-01" for open accounts (some core systems do this), the date-parsing will succeed and `active` will silently exclude real open accounts.

### attrition/
MEDIUM. Mostly clean — uses `all_data` (not `eligible_data`) as denominator.

- `attrition/rates.py:42–55` A9.1 — `overall_rate = n_closed / total` with `total = len(all_data)`. Correct denominator.
- `attrition/rates.py:69–77` L12M attrition — `l12m_open_start = len(all_data[...closed in window or still open])`. Approximation, but documented.
- `attrition/dimensions.py:55–90` A9.4 by branch — explicit comment "Denominator: accounts open at start of L12M window". Good.
- `attrition/dimensions.py:76` — `l12m_base = pd.concat([open_accts, l12m_closed])` — simple and honest.
- `attrition/dimensions.py:171–215` A9.4b first-year close rate — `fy_df["First-Year Close Rate"] = fy_df["Closed"] / fy_df["Opened"].replace(0, 1)` — the `replace(0,1)` is a silent div-by-zero fix; probably fine since branches with 0 opens wouldn't appear, but worth noting.
- `attrition/impact.py:62–68` A9.9 Debit retention — denominators are `debit_mask.sum()` and `(~debit_mask).sum()` on `all_data`. Correct.
- `attrition/impact.py:186–199` A9.10 mailer retention — denominators are per-group; `Never Mailed` group is anyone with no Mail column populated, which is correct but depends on mail columns being NaN-for-no-mail rather than 0-for-no-mail.
- `attrition/impact.py:547–563` A9.13 ARS eligibility — correct use of `all_copy["_ars_eligible"]` as a group flag (not a filter).

### insights/
HIGH. Inherits bias from upstream.

- `insights/_data.py` — safe accessors with zero-valued defaults on missing keys. Problem: when an upstream module fails or hasn't run, the default is 0 or 0.0, which silently zeros out the downstream dollar calculation. Look at `get_value_1` line 32–48: if `value_1` never got populated, the S1 "Revenue Gap" chart will produce `$0` with no error.
- `insights/branch_scorecard.py:30–101` — reimplements DCTR/Reg E/attrition against raw `data` (not eligible_data). Divergent denominator from DCTR-9/A9.4/A8.4a.
- `insights/branch_scorecard.py:77` — attrition via `Stat Code == "C"` is a snapshot; A9.1 uses `Date Closed.notna()` which is cumulative. These two sources disagree.
- `insights/branch_scorecard.py:83–86` — Reg E detected by sorting columns alphabetically (`rege_cols[-1]`), which will mis-pick "Dec25" over "Jan26" (same bug `rege/_helpers.py:119–132` already fixed with chronological sort). Confirmed: this file uses the alphabetical pick, not chronological.
- `insights/dormant.py:284` — `total_eligible` silent fallback to `len(data)`.
- `insights/dormant.py:66–68` — `q75 = df[bal_col].quantile(0.75)` computed on full `df` before the debit filter; "top quartile" then means "top quartile of everyone", not "top quartile of non-debit holders".
- `insights/synthesis.py:55–152` S1 — builds `debit_gap = v1["accts_without"] * v1["delta"]`. `v1["accts_without"]` came from `value_1` which came from A11.1 which came from `eligible_personal` — narrow denominator for accts_without.
- `insights/synthesis.py:160–292` S2 — `preventable_closures = round(closed * retention_lift)`. `closed` is from A9.1 (correct, full population), `retention_lift` is from A9.9 (correct). This one is actually fine.
- `insights/synthesis.py:452–555` S4 — `gap_accounts = round(total_accounts * (median_dctr - worst_dctr))` where `total_accounts = a3.get("eligible_accounts", d1.get("total_accounts", 0))`. Eligible_accounts here is explicit.
- `insights/conclusions.py:172–319` S7 — `new_accounts = round(total_accounts * 0.05)` where `total_accounts = d1.get("total_accounts", 0)` which is the narrow base's `total_accounts`. "5 points of DCTR = +N accounts" therefore also undercounts.
- `insights/effectiveness.py:66–127` A18.1 — pulls `hist_dctr`, `l12m_dctr` from upstream ctx.results — inherits the bias.
- `insights/effectiveness.py:209–294` A18.3 — industry benchmarks comparison. Compares `cu_dctr` (narrow base) against `bench_active = 0.663`. If the true CU DCTR is 80% but we report 30%, the benchmark comparison slide shows the CU *below* PULSE when in reality it is *above* — this is the exact failure mode that will embarrass the analyst in front of the client.
- `insights/effectiveness.py:32` `_BENCHMARKS_PATH` — path is `parents[4] / "config" / "benchmarks.json"`. Dependency on repo layout; if the file is not found, falls back to defaults (line 52–58).

### overview/
MEDIUM.

- `overview/eligibility.py:39–128` A3 Eligibility Funnel. This is the ground truth for how `eligible_data` is constructed. The stages are: Total → Open Accounts → + Eligible Stat Code → + Eligible Product Code → (optional) + Mailable → ELIGIBLE → Personal/Business split. Each stage's drop-off is calculated transparently. This file is *not* the problem — the problem is that every other module treats stage 5/6 output (`eligible_data`) as "the customer base".
- `overview/eligibility.py:85–102` — `Drop-off %` at each stage is a conditional rate (drop / previous stage). Correct.
- `overview/product_codes.py`, `overview/stat_codes.py` — not audited in detail; these appear to be breakdowns of product/stat code distribution, no rate issues.

### mailer/
MEDIUM.

- `mailer/impact.py:42–170` A15.1 Market Reach. `penetration = n_responders / n_eligible * 100` where `n_eligible = len(eligible_with_debit)`. So this is "responders as % of debit holders", which is the right conceptual frame for a debit-card mailer campaign.
- `mailer/impact.py:243–244` A15.3/4 — reads `open_accounts` and `eligible_data` both; chart `penetration_rate` uses `eligible_data` as denominator. Label says "penetration". Acceptable given business context.
- `mailer/reach.py:73–105` `_organic_activation` — detects debit holders who were never mailed, uses full `data` as the base. Explicit and correct.
- `mailer/reach.py:91` — `has_debit = data[data[debit_col].isin(["Yes", "Y", True, 1])]`. Note: list includes `True` and `1` (booleans/ints); while `dctr/_helpers.py:42` uses `_DEBIT_YES_VALUES = frozenset(("YES", "Y", "D", "DC", "DEBIT"))` (strings only). The two modules therefore disagree on what counts as "has debit": a boolean `True` row will be "yes" to the mailer module and "no" to the DCTR module.
- `mailer/reach.py:426` — `n_eligible = len(ctx.subsets.eligible_data) if ctx.subsets else 0`. Narrow denominator.
- `mailer/cohort.py`, `mailer/response.py`, `mailer/insights.py` — not audited in detail; mailer logic is pair-discovery based and generally operates on `data`.

### executive/
MEDIUM.

- `executive/01_scorecard_data.py` — aggregates top KPIs from other DataFrames (`attrition_df`, `balance_df`, etc.). Lines 16–58: divides `_at_risk / _total_attrition` where `_total_attrition = len(attrition_df)`. This is the full attrition dataset, correct.
- Potential bug: if `attrition_df` or `balance_df` is not yet in namespace, the whole KPI block silently skips (line 60). Slide output will be missing cards with no warning visible on the deck.
- `executive/02_scorecard_dashboard.py`, `03_strategic_priorities.py`, `04_opportunity_waterfall.py`, `05_action_roadmap.py` — not audited in detail; downstream of `scorecard_df`.

### balance/, payroll/, product/, interchange/, merchant/, mcc_code/, personal_accts/, business_accts/, branch_txn/, transaction_type/, ics_acquisition/, relationship/, retention/, segment_evolution/, general/, campaign/, competition/, financial_services/, attrition_txn/, rege_overdraft/, mailer/, txn_setup/
LOW–MEDIUM. TXN-style scripts that ingest `rewards_df` / `combined_df` from an upstream notebook cell. Denominator is typically the full loaded dataset, not a filtered subset. But several risks noted:

- `balance/01_balance_data.py:127` — `zero_bal_pct = zero_bal_count / total_accounts * 100`. `total_accounts = len(balance_df)` where `balance_df` is `rewards_df[available_cols]` — full dataset. OK.
- `balance/06_deposit_flight_risk.py:12–13` — `high_bal = balance_df[balance_df['Curr Bal'] >= 25_000]; flight_risk = high_bal[high_bal['bal_delta'] < 0]`. Explicit double filter. Counts reported are absolute — no rate bug.
- `balance/08_pfi_scoring.py:112–113` — `tier_counts = pfi_df['pfi_tier'].value_counts(); tier_pcts = tier_counts / tier_counts.sum() * 100`. Denominator = all pfi tiers. OK.
- `payroll/01_payroll_data.py:261–263` — `pct_payroll = n_payroll / n_total` with `n_total = len(payroll_df)`. OK.
- `payroll/05_payroll_by_demographics.py:113` — `overall_pct = payroll_df['has_payroll'].mean() * 100`. Silently drops NaN `has_payroll` rows from denominator (pandas `.mean()` on bool cast to float treats NaN as missing, not as 0). LOW risk if `has_payroll` is always populated; flag to verify.
- `retention/02_retention_kpi.py:14` — `_closed_rate = _closed / _total * 100`. Denominator is full `retention_df`. OK.
- `retention/01_retention_data.py:146` — `health_status` is assigned by `_classify_health`, which is a custom classifier. Rows where the classifier returns NaN (because spend columns are all NaN) silently become a missing category and drop out of downstream rates.
- `campaign/04_campaign_penetration.py:94–95` — `single_responders = int((_resp_success_counts[_resp_mask] == 1).sum())` — absolute counts; no rate bug detected.
- `ics_acquisition/01_ics_data.py:73–76` — builds `ics_df` and `non_ics_df` as disjoint subsets. Downstream `.py` files likely compute `len(ics_df) / (len(ics_df) + len(non_ics_df))`, which is valid.
- `segment_evolution/01_segment_data.py:53` — `seg_evo_df = rewards_df[keep_cols]`. Full dataset.
- `general/`, `product/`, `merchant/`, `mcc_code/`, `personal_accts/`, `business_accts/`, `branch_txn/`, `transaction_type/`, `competition/`, `financial_services/`, `attrition_txn/`, `rege_overdraft/`, `relationship/` — structurally similar to `balance/` and `payroll/`: operate on `rewards_df` as the base, compute shares that divide by `len(df)` or `df[col].sum()`. No systematic denominator bug detected, but the audit could not read every file in full; any file that introduces a `df[df[...] == X]` filter before a rate calc should be reviewed.
- `txn_setup/` — ingest + merchant-consolidation scripts, no rate calculations in the analytics sense.
- `mailer/` (TXN-style overlap with module `mailer/`) — the `01_Analysis/00-Scripts/analytics/mailer/` folder is the module version; the TXN version is the Jupyter cells. Denominators already audited above.

## Denominator Reference Table

| File | Line | Metric name | Current denominator | Should be | Severity |
|---|---|---|---|---|---|
| dctr/penetration.py | 238 | DCTR-1 overall_dctr | eligible_data | Full open/customer population (notebook) | CRITICAL |
| dctr/penetration.py | 266–280 | DCTR-2 open vs eligible | both; eligible side uses eligible_data | Explicit — and it correctly shows both | OK (this one's fine) |
| dctr/penetration.py | 311–319 | DCTR-3 L12M dctr | filter_l12m(eligible_data) | filter_l12m(open_accounts) or full pop | CRITICAL |
| dctr/penetration.py | 355–367 | DCTR-4/5 P/B dctr | eligible_personal/business | Open personal/business | CRITICAL |
| dctr/penetration.py | 475–491 | DCTR-6/7 P/B L12M | eligible_personal/business filtered L12M | Same rationale as DCTR-3 | CRITICAL |
| dctr/funnel.py | 95 | A7.7 through = td / ta | ta = len(data) | correct | OK |
| dctr/funnel.py | 95 | A7.7 dctr_e = td / te | te = len(eligible_data) | arguably mislabelled | HIGH |
| dctr/funnel.py | 198 | A7.8 L12M through | len(l12m_all) | correct | OK |
| dctr/funnel.py | 283–288 | A7.9 e_dctr, n_dctr | split: eligible vs non-eligible (explicit) | correct | OK |
| dctr/branches.py | 60–66 | DCTR-9 best/worst branch | branch_dctr(eligible_data) | branch_dctr(open_accounts) | CRITICAL |
| dctr/branches.py | 210–222 | DCTR-16 12M Take Rate | eligible_data filtered monthly | should flow from full pop | CRITICAL |
| dctr/branches.py | 268–277 | A7.10a merged | eligible_data | open accounts | CRITICAL |
| dctr/branches.py | 452 | A7.10b L12M branch DCTR | branch_dctr(el12) from eligible_data | open accounts | CRITICAL |
| dctr/branches.py | 525–531 | A7.13 heatmap | eligible_data | open accounts | CRITICAL |
| dctr/trends.py | 55–86 | A7.4 segment trends | aggregates dctr_4/5/6/7 (all narrow) | narrow roots | CRITICAL |
| dctr/trends.py | 300–314 | A7.6a L12M monthly trend | el12 ← eligible_data | open | CRITICAL |
| dctr/trends.py | 609–617 | A7.14 seasonality | eligible_data | open | CRITICAL |
| dctr/trends.py | 691–705 | A7.15 vintage | eligible_data | open | CRITICAL |
| dctr/overlays.py | 64–69 | DCTR-10 by account age | eligible_data by_dimension | open_accounts | CRITICAL |
| dctr/overlays.py | 160–165 | DCTR-11 by holder age | eligible_data by_dimension | open_accounts | CRITICAL |
| dctr/overlays.py | 276–281 | DCTR-12 by balance | eligible_data by_dimension | open_accounts | CRITICAL |
| dctr/overlays.py | 310–325 | DCTR-13 crosstab holder×balance | eligible_data | open_accounts | CRITICAL |
| dctr/overlays.py | 352–368 | DCTR-14 crosstab age×balance | eligible_data | open_accounts | CRITICAL |
| rege/_helpers.py | 161 | reg_e_base base | eligible_personal[debit_mask] | depends on intent — label slide | CRITICAL |
| rege/status.py | 63–66 | A8.1 all-time / L12M | rege(base, ...) where base is narrow | depends on intent | CRITICAL |
| rege/status.py | 196–209 | A8.2 yearly rate | rege on narrow base filtered by year | depends | CRITICAL |
| rege/status.py | 348–362 | A8.3 L12M monthly | base_l12m | depends | CRITICAL |
| rege/status.py | 364–366 | A8.3 historical_rate | rege(base) all-time | depends | CRITICAL |
| rege/status.py | 496–512 | A8.12 24-month trend | groupby Year_Month on base | depends | CRITICAL |
| rege/dimensions.py | 208–221 | A8.5 account age | rege on base slice | depends | CRITICAL |
| rege/dimensions.py | 302–318 | A8.6 holder age (hist + l12m) | rege on base / base_l12m | depends | CRITICAL |
| rege/dimensions.py | 458–472 | A8.7 product code | rege on base slice | depends | CRITICAL |
| rege/dimensions.py | 558 | A8.10 rege_rate | personal_w_rege / personal_w_debit | depends | CRITICAL |
| rege/dimensions.py | 654 | A8.11 L12M rege_rate | rege_l12m / p_wd_l12m | depends | CRITICAL |
| rege/branches.py | 56–68 | A8.4a/b/c/d per-branch | _branch_rates(base) | depends | CRITICAL |
| rege/branches.py | 484–492 | A8.13 Rate = oi/t per month×branch | base_l12m grouped | depends | CRITICAL |
| value/analysis.py | 344 | A11.1 rpw / rpwo | groupby has_debit on active personal | OK as comparison | OK |
| value/analysis.py | 363–364 | A11.1 pot_hist / pot_l12m | awo * delta * hist_dctr (narrow) | awo * delta * correct_dctr | HIGH |
| value/analysis.py | 562–563 | A11.2 rpw / rpwo | groupby Has_RegE on active debit | OK | OK |
| value/analysis.py | 578–580 | A11.2 pot_hist / pot_l12m | awo * delta * hist_rege (narrow) | depends on intent | HIGH |
| attrition/rates.py | 42 | A9.1 overall_rate | n_closed / len(all_data) | correct | OK |
| attrition/rates.py | 77 | A9.1 l12m_rate | l12m_closed / l12m_open_start | correct (explicit) | OK |
| attrition/dimensions.py | 90 | A9.4 branch_df Attrition Rate | Closed / Total from l12m_base | correct | OK |
| attrition/dimensions.py | 181 | A9.4b First-Year Close Rate | Closed / Opened (replace 0 with 1) | correct except div-guard | LOW |
| attrition/dimensions.py | 294 | A9.5 Attrition Rate by product | closed_by / total_by on all_data | correct | OK |
| attrition/dimensions.py | 377 | A9.6 Personal/Business rate | n_closed / total of subset | correct | OK |
| attrition/dimensions.py | 487 | A9.7 by tenure | Closed / Total | correct | OK |
| attrition/dimensions.py | 585 | A9.8 by balance | Closed / Total | correct | OK |
| attrition/impact.py | 67–75 | A9.9 attrition by debit | debit_mask on all_data | correct | OK |
| attrition/impact.py | 190–198 | A9.10 by mailer group | all_copy _mail_group groupby | correct | OK |
| attrition/impact.py | 295 | A9.11 est annual revenue lost | last_spend * ic_rate * 12 | correct | OK |
| attrition/impact.py | 553–563 | A9.13 ARS-eligible vs non | ars_eligible flag on all_data | correct | OK |
| insights/branch_scorecard.py | 70–79 | A19.1 dctr, attrition, rege | len(branch_data) = raw data per branch | conflicts with DCTR-9/A9.4 | HIGH |
| insights/branch_scorecard.py | 77 | A19.1 attrition | Stat Code == "C" snapshot | Date Closed notna() cumulative | HIGH |
| insights/branch_scorecard.py | 83–85 | A19.1 Reg E | alphabetical `rege_cols[-1]` | chronological (see rege/_helpers.py) | MEDIUM |
| insights/dormant.py | 118 | A20.1 pct | n_dormant / total_eligible with fallback | fully specified | MEDIUM |
| insights/dormant.py | 67–68 | A20.1 top quartile | quantile(0.75) on full df | arguably should be on no_debit subset | LOW |
| insights/synthesis.py | 59–62 | S1 debit_gap, rege_gap | v1/v2 delta × accts_without | inherits CRITICAL bias | HIGH |
| insights/synthesis.py | 180–182 | S2 preventable_closures | closed * retention_lift | OK | OK |
| insights/synthesis.py | 476–479 | S4 gap_accounts | total_accounts * (median - worst) | inherits CRITICAL bias | HIGH |
| insights/synthesis.py | 571–577 | S5 debit cascade | per-stream multiplications | inherits CRITICAL bias | HIGH |
| insights/conclusions.py | 201–206 | S7 +5pp DCTR scenario | total_accounts * 0.05 | inherits CRITICAL bias | HIGH |
| insights/conclusions.py | 334–336 | S8 action 1/2/3 | pot_l12m values from v1/v2 | inherits CRITICAL bias | HIGH |
| insights/effectiveness.py | 75–76 | A18.1 dctr progression | hist/l12m from ctx.results | inherits CRITICAL bias | HIGH |
| insights/effectiveness.py | 219–228 | A18.3 benchmarks | CU DCTR narrow vs benchmark 66.3% | compares apples to oranges | HIGH |
| mailer/impact.py | 84–85 | A15.1 resp_rate / penetration | n_resp/n_mailed, n_resp/n_eligible_with_debit | explicit; label driven | OK |
| mailer/reach.py | 91 | organic has_debit | isin(['Yes','Y',True,1]) | diverges from dctr helpers | LOW |
| mailer/reach.py | 426 | A17.2 penetration | uniques / eligible_data | depends on intent | MEDIUM |
| overview/eligibility.py | 86–127 | A3 Drop-off % | per-stage conditional rate | correct | OK |
| executive/01_scorecard_data.py | 22 | exec % at risk | _at_risk / _total_attrition | correct | OK |
| executive/01_scorecard_data.py | 43–45 | exec $ at risk | sum of last_12mo_spend | correct | OK |
| balance/01_balance_data.py | 127 | zero_bal_pct | zero_bal / total_accounts (= len(balance_df)) | correct | OK |
| payroll/01_payroll_data.py | 263 | pct_payroll | n_payroll / n_total | correct | OK |
| payroll/05_payroll_by_demographics.py | 113 | overall_pct | has_payroll.mean() * 100 | NaN-drop silent | LOW |
| payroll/08_pfi_composite_score.py | 231 | Has Payroll | has_payroll.mean() * 100 | NaN-drop silent | LOW |
| payroll/09_pfi_vs_competitor.py | 46 | comp_pct_by_tier | groupby.mean() * 100 | NaN-drop silent | LOW |
| retention/02_retention_kpi.py | 14 | closed_rate | _closed / _total | correct | OK |
| retention/02_retention_kpi.py | 44 | at_risk % | _at_risk / _total * 100 | correct | OK |

## Recommendations

Format: concrete + actionable. Priority follows the severity scheme above. No implementation plans — the user prioritizes the fix order.

1. **Pick a canonical denominator and codify it.** Before any fix, the user must declare: for DCTR, is the denominator (a) all records in `data`, (b) all open accounts, (c) all personal+open accounts, or (d) eligible_data? The notebook's denominator (whichever one it uses) is the truth and should become `ctx.subsets.canonical_dctr_base` (or similar), used by every DCTR module. A single reference, chosen once.

2. **Expose every denominator in the slide.** Every DCTR/Reg E/value/insights slide that ships a rate should include, in small type, the denominator count and label (e.g., "78% of 24,301 open personal accounts"). The DCTR-2 slide ("Open vs Eligible") is the one existing example — the user should extend that pattern to every rate slide.

3. **Reconcile with notebook before next ship.** Run one client through both the notebook and the pipeline, export every rate from every slide into a single reconciliation sheet, and diff. Any rate that differs by >0.5pp is a candidate bug, not a rounding artifact.

4. **Split "product-rate" from "portfolio-rate" slides in Reg E.** If `eligible_personal ∩ has_debit` is the intended Reg E denominator, rename every A8 slide title and chart subtitle to say "Reg E Opt-In among Personal Debit Holders". If the true metric is portfolio-level, change the denominator in `rege/_helpers.py:161` to `eligible_personal` (without the debit mask) and re-run.

5. **Fix `insights/branch_scorecard.py` to pull from upstream results, not recompute.** The current file diverges from DCTR-9, A9.4, and A8.4. Consuming `ctx.results["dctr_9"]`, `ctx.results["attrition_4"]`, and `ctx.results["reg_e_4"]` directly guarantees the scorecard matches the detail slides.

6. **Fix the alphabetical Reg E column pick in `insights/branch_scorecard.py:83–85`.** Replace with `detect_reg_e_column(data)` from `rege/_helpers.py`.

7. **Audit the dormant high-balance slide (A20.1).** Decide whether "top quartile" is among all accounts or among no-debit accounts; fix `insights/dormant.py:66–68` to match the chosen frame, and update the chart label accordingly.

8. **Tighten silent-drop behavior in the `_safe` wrappers.** In `dctr/penetration.py:37–50`, `rege/status.py:23–36`, `attrition/_helpers.py._safe`, and all other `_safe()` implementations, when an analysis module fails *and* the failure mode is "missing required column" or "empty subset", the `AnalysisResult(success=False)` should surface to a top-level warning log. Right now a single-client deck can ship with 3 or 4 empty slides that carry no visible error.

9. **Standardize the "has debit" test.** `dctr/_helpers.py:42` uses string-only values; `insights/dormant.py:62`, `insights/branch_scorecard.py:71`, `mailer/reach.py:91`, `insights/dormant.py:62` use lists that mix strings, booleans, and ints. Consolidate into one helper (extend `dctr/_helpers.py:debit_mask` to handle booleans) and have all callers use it.

10. **Guard the null-dropping `.mean()` pattern in payroll & PFI files.** Review `payroll/05_payroll_by_demographics.py:113`, `payroll/08_pfi_composite_score.py:231`, `payroll/09_pfi_vs_competitor.py:46`. If `has_payroll` / `has_competitor` is ever NaN, those accounts must be explicitly categorized (defaulting to False is the safer choice) before the `.mean()`.

11. **Validate the Date Closed-as-string failure mode in `value/analysis.py:289–295`.** Add an assertion (or a log line) that `active` has the expected row count after the Date Closed filter, compared to `len(df)`. If >5% of rows get dropped by this filter silently, log a warning.

12. **Publish a small "rate methodology" page for the deck.** One appendix slide at the end of the client deck listing the denominators for DCTR, Reg E, Attrition, Value — so the client never has to ask "what's this rate over?"

## Limitations

- Static audit only — no actual data flowed through these cells during this audit. Every finding is based on code read; a small number ("LOW risk if has_payroll always populated") require a one-run check against a real client dataset to confirm.
- Denominator correctness depends on business intent, which is only confirmed for DCTR (notebook truth). Reg E's "eligible_personal ∩ has_debit" denominator may be intentional; this audit flags it as suspicious but defers the call.
- Some filter steps may be intentional narrowing (e.g., "personal DCTR only looks at personal accounts"). Flagged both types; user decides which are bugs.
- Only the primary file of each module-class folder was read in full. Secondary files (`_helpers.py`, `__init__.py`) were read selectively.
- The 10-step TXN-style folders (22 of the 27 total) were audited via grep + spot reads of key files. A per-file line-by-line review would likely surface a few more LOW-severity NaN-drop or silent-filter risks, but is unlikely to change the CRITICAL/HIGH findings.
- Charts and PNG-rendering code is not the audit target; we only read it when it was mixed into the rate-calculation path (which is common given the file structure).

## Next Steps

1. Hold a short working session with the notebook author to lock the canonical DCTR denominator. All fixes gate on this decision.
2. Once the denominator is fixed, re-run one full client and diff the A11/S1/S4/S5/S6/S7/S8 dollar outputs against the current deck — the dollar numbers will change materially.
3. Open a P0 fix PR for `dctr/_helpers.py` / `dctr/penetration.py` that introduces the canonical base. The surface area change is small because every call site reads `ctx.subsets.eligible_data` — a context-level swap gets most of the way.
4. Separately, decide the Reg E denominator question and reword A8 slide titles if the current frame is kept.
5. Fix `insights/branch_scorecard.py` to consume upstream results (P1).
6. Spike a CI reconciliation check: for each client run, export a `rates_audit.csv` with every rate + its denominator count, and diff against the prior run. Drift > 1pp triggers a review.
7. Add the "rate methodology" appendix slide to every client deck.
