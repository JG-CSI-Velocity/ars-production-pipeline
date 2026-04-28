# Analysis Audit — 2026-04-27

Living log of audit findings against the ARS / TXN analysis pipeline (`01_Analysis/`). Each entry records direct script-read evidence, severity, and recommended fix. Branch at time of entry: `feature/html-review`.

---

## Entry 1 — TXN Pipeline Bypasses Denominator Framework

**Date:** 2026-04-27
**Auditor:** Claude (script read of `analytics/campaign/`, `analytics/general/`, `analytics/merchant/`, `analytics/mcc_code/`, `pipeline/steps/subsets.py`)
**Scope:** All TXN-section scripts (~330 of 365 analytics scripts) under `01_Analysis/00-Scripts/analytics/{campaign,general,merchant,mcc_code,...}`
**Severity:** HIGH — client-facing labeling defect + cross-deck denominator mismatch

### Summary

The denominator framework defined in `pipeline/steps/subsets.py` (Eligible / Eligible Personal / Eligible Business / Open) is correctly built and consumed by the registered ARS modules. The TXN pipeline does **not** consume it. TXN scripts operate on raw `combined_df` and `rewards_df` and compute their own ad-hoc denominators, producing client-facing KPI cards labeled "Eligible" / "% of portfolio" whose underlying values come from a different population than the ARS slides in the same deck.

### Confirmed denominator violations

**1. `general/02_portfolio_data.py:57` — unfiltered "Active Accounts"**
```python
total_accounts = combined_df['primary_account_num'].nunique()
```
Flows into `general/03_kpi_dashboard.py:7` as the headline **"Active Accounts"** card on the portfolio overview slide. Should anchor to Eligible (or Eligible-with-Debit, since the underlying TXN universe is SIG+PIN debit swipes per `general/02:13`).

**2. `merchant/01_merchant_data.py:18-22` — merchant share % uses raw TXN universe**
```python
total_txns_merch = len(combined_df)
total_accts_merch = combined_df['primary_account_num'].nunique()
merch_agg['acct_pct'] = merch_agg['unique_accounts'] / total_accts_merch * 100
```
"% of accounts shopping at Merchant X" denominator is every account with any TXN, not Eligible.

**3. `mcc_code/01_mcc_data.py:27-31` — same pattern as merchant**
```python
total_txns_all = len(combined_df)
total_accts_all = combined_df['primary_account_num'].nunique()
mcc_agg['acct_pct'] = mcc_agg['unique_accounts'] / total_accts_all * 100
```

**4. `campaign/02_campaign_kpi.py:21` — "Eligible" label is misleading**
```python
n_eligible = len(rewards_df) if 'rewards_df' in dir() else len(camp_acct)
```
The KPI card displays **"Eligible Accounts"** but the value is `len(rewards_df)` — every row in the rewards sheet, regardless of stat code, product code, or open status. Mail penetration % (`mailed/eligible`, line 27) and Portfolio Activation % (`responded/eligible`, line 126) inherit the wrong base. **This is a labeling lie on a client-facing card.**

**5. `campaign/04_campaign_penetration.py:20` — "Total portfolio" = rewards rows**
```python
total_population = len(_acct_col.unique())   # _acct_col = rewards_df['Acct Number']
```
Funnel chart and table labels read "% of portfolio" but the base is the rewards-sheet population, not the ARS portfolio. Misnaming repeats at lines 159, 234, 291, 300.

### Confirmed structural risks

**6. Namespace via `exec()` — variable shadowing risk.** `merch_agg` (`merchant/01:10`), `mcc_agg` (`mcc_code/01:18`), `camp_acct` (`campaign/01:32`), `combined_df`, `rewards_df`, `DATASET_MONTHS`, `GEN_COLORS` are all bare globals. `campaign/02:9` literally checks `if 'camp_acct' not in dir()`. Two sections defining the same name (`total_accounts`, `_resp_mask`) silently shadow with no error.

**7. Hardcoded campaign response classifiers.** `campaign/01:50-53` and `:61` lock to `'TH'`, `'NU 5+'`, `'NU 1-4'`. If any client uses different rewards taxonomy, every campaign rate silently returns 0 with no warning.

**8. Hardcoded debit transaction types.** `general/02:13`:
```python
DEBIT_TYPES = ['SIG', 'PIN']
```
Reasonable default but belongs in config — different processors use different transaction-type strings.

**9. Silent outlier clipping.** `merchant/01:74` caps coefficient-of-variation at 500% with no disclosure on the resulting chart:
```python
consistency_df['cv'] = consistency_df['cv'].clip(upper=500)
```
Acceptable only if chart legend states "CV capped at 500%."

### What works (do not regress)

- `pipeline/steps/subsets.py` is solid: explicit logging of denominator construction (lines 101-107, 117-122, 124-125), case-insensitive matching, fallback column auto-detection.
- ARS-side registered modules (`dctr/`, `attrition/`, `mailer/`, etc.) correctly consume `ctx.subsets.eligible_data` / `eligible_with_debit` / `open_accounts`.
- The framework upstream is correct; the failure is purely TXN-side scripts not bridging to it.

### Client-deck impact

A client comparing the ARS Eligible count (e.g. 12,400) to the Campaign "Eligible Accounts" card (e.g. 18,200) will see two different numbers under the same label in the same deck. The TXN portfolio overview's "Active Accounts" card may also exceed the ARS Eligible base — undermining the entire denominator narrative.

### Recommended fix (single highest-leverage change)

Inject the eligible account filter into the TXN namespace at the top of `txn_wrapper.py` execution:

```python
# In TxnWrapper.run() before exec'ing scripts:
eligible_acct_set = set(
    ctx.subsets.eligible_data['Acct Number'].astype(str).str.strip()
)
namespace['ELIGIBLE_ACCOUNTS'] = eligible_acct_set
namespace['combined_df'] = combined_df[
    combined_df['primary_account_num'].astype(str).str.strip().isin(eligible_acct_set)
]
namespace['rewards_df'] = rewards_df[
    rewards_df['Acct Number'].astype(str).str.strip().isin(eligible_acct_set)
]
```

This propagates to all 22 TXN sections without touching individual scripts. Follow-up work: rename labels (`general/03:7`, `campaign/02:48`) to reflect the now-correct denominator, and add a denominator-source assertion at the top of each TXN section (`assert ctx.subsets.eligible_data is not None`).

### Audit verdict

**Not client-ready.** The labeling defect (calling a non-eligible base "Eligible") is reportable. Recommend gating any client deck containing TXN slides until Fix 1 (eligible filter injection) ships and labels are corrected.

---

## Entry 2 — Deck Is Rich But Unfocused; 3-Story Compression Plan

**Date:** 2026-04-27
**Auditor:** Claude (review of `SLIDE_MAPPING.md`, current ARS + TXN + ICS + Deposits deck composition)
**Scope:** All deliverable slides across the 4 deck families
**Severity:** MEDIUM — not a defect, but a usability issue blocking effective client conversations
**Linked artifact:** `02_Presentations/CLIENT_DECK_PLAN.md`

### Summary

The unfiltered combined output is ~70-80 slides per client (ARS ~25, TXN ~30+, ICS 8, Deposits 8). A client cannot absorb that in a meeting. The analysis is rich and accurate (modulo Entry 1), but the deck has no narrative spine — every module gets a slide regardless of whether it advances a story the client cares about.

### Findings

**1. No story hierarchy in current assembly.** `SLIDE_MAPPING.md` "Deck Assembly Order" sequences modules by section (Overview → Card Usage → Risk → Campaign → Value), not by audience question. A CFO scanning the deck cannot answer "did the program work?" without flipping through 5 sections.

**2. Window-dressing modules occupy hero real estate.** Demographics, age bands, hourly heatmaps, MCC top-50, balance bands, full branch scorecards, account age curves, business-vs-personal splits, lifecycle, seasonal patterns — all currently render as full slides. Per CSM input these are reference-only and do not drive client decisions.

**3. ICS is conditional but not handled.** ICS data is present for some clients and absent for others. The current build produces ICS slides even when the analysis returns zero ICS accounts.

**4. Deposits deck is product-orphaned.** Lives in its own deck family but is closely related to ARS — most CSMs do not present it separately. Should be supplementary unless promoted.

### Recommended Structure (per `CLIENT_DECK_PLAN.md`)

Three critical stories, ordered by client priority:

1. **ARS Performance** — slides 4-14
2. **Competition** — slides 20-25
3. **Financial Services Leakage** — slides 26-31

ICS conditionally slotted between Story 1 and Story 2 (slides 15-19) when data present.

**Total: 32 slides without ICS / 38 with ICS.** Both under 40-slide cap.

### Supporting Deliverable: Supplementary Deck

Separate `.pptx` file `{client_id}_{month}_supplementary.pptx` containing every chart that ran but is not in the main manifest. Built by extending `run_sampler.py` to read the **inverse** of the main slide manifest. Audience: client-side analyst, not presented live.

### Dependencies

- **Entry 1 fix must ship first.** The hero slides (5, 21, 27, 34) depend on consistent denominators across ARS and TXN. Presenting the compressed deck before the eligible-filter injection lands would amplify the labeling defect rather than hide it.

### Implementation Effort

~2 days:
- Slide manifest JSON (1)
- Runner mode flags (`--mode=client` / `--mode=supplementary`) (2)
- 3 new combined-hero modules in `analytics/executive/` (3)
- 4 "So what" template slides driven by `insights.synthesis` (4)
- ICS conditional insert plumbing (5)
- Opportunity-stack waterfall (1 new chart) (6)

No net-new chart engineering beyond the waterfall. Existing chart code is reused.

### Audit verdict

**Approved direction, gated on Entry 1.** The compression plan is sound and addresses the usability gap. Recommend building the manifest + runner modes in parallel with the denominator fix, but holding any client presentation of the compressed deck until both ship.
