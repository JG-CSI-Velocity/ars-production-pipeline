# TXN Deck — Follow-ups

Tracked separately from `txn-deck-review.md` so the review doc stays focused on KEEP/NIX decisions. Items here are real implementation work (chart logic, data splits, visual fixes) that go beyond deck assembly.

---

## Section 1 — Portfolio Overview

| Script | Issue | Action |
|--------|-------|--------|
| `25_time_to_first_txn` | Output is wrong; needs splits by ARS responders / ICS accounts / Non-product accounts. Valuable as product vs non-product comparison. | Rework chart logic to emit 3 split series. |
| `26_spend_by_account_age` | Needs visual/data improvement (unspecified). | Triage — define what "improve" means before implementation. |
| `27_new_account_profile` | Needs visual/data improvement (unspecified). | Triage. |
| `30_ars_swipe_segmentation` | Needs visual/data improvement (unspecified). | Triage. |
| `24_account_age_bar` | Line chart inside the bar chart is "weird". | Fix overlay/dual-axis rendering. |

---

## Section 2 — Merchant Analysis

| Script | Issue | Action |
|--------|-------|--------|
| `09_merchant_lifecycle` | "New merchant" data label/legend is misleading. | Fix labels/legend so the slide can be kept in main deck. |
| `08_merchant_volatility` | Script failed during run. | Triage failure, decide repair vs retire. |
| Layout master (any slide) | Title/subtitle overlap on the layout used by `10_merchant_by_biz_personal`. | Fix in layout master per G8 — affects every slide using that layout. |

---

## Section 3 — MCC Categories

| Script | Issue | Action |
|--------|-------|--------|
| `12_mcc_seasonal` | Calc is wrong. | Fix seasonal calc, then promote out of auxiliary. |
| `14_mcc_spend_profile` | Data is wrong + chart is distorted. | Fix data pull and chart rendering, then promote out of auxiliary. |
| `11_mcc_by_biz_personal`, `13_mcc_diversity` | Title/subtitle overlap (layout master). | Tracked under G8 — single layout master fix. |

---

## Sections 4 & 5 — Business / Personal Accounts

| Script | Issue | Action |
|--------|-------|--------|
| `08_business_volatility`, `08_personal_volatility` | Visual QA — Section 2's volatility script failed; confirm these run and look right. | Spot-check; promote out if any issues. |
| `09_business_lifecycle`, `09_personal_lifecycle` | Watch for the same "new" data label issue seen in `09_merchant_lifecycle`. | Verify labels read correctly; fix if same bug. |

---

## Section 6 — Competition

| Script | Issue | Action |
|--------|-------|--------|
| `25_at_risk_accounts` | Y-tick labels hardcoded as `"Account {i+1}"` (positional) — slide is not actionable. | Decide: (a) show real account ID, or (b) keep synthetic label and emit companion CSV export with real IDs. |
| `25_at_risk_accounts` | Display needs redesign — current bar chart is hard to read. | Redesign visualization. |
| `26_spend_scatter` | Horrible scaling, no value. | All cells → aux. Fix axis scaling / log transform / outlier handling, then re-evaluate. |
| `28_spend_vs_frequency` | Assumed same scaling issue (confirm). | If confirmed: all cells → aux + same scaling fix as `26`. |
| `29_wallet_share` | Currently emits one slide per cell. | Add filter: show only top competitor per segment AND only when that leader is in the top 10 overall. |
| `24_segment_heatmap` | 4 cells produce 4 separate slides. | Combine into single slide with segments distinguished (small-multiples or unified grid). |
| `02_competitor_detection` | 3 detection slides — first is paired with KPI dashboard, second + third combined. | New slide builder: A1 = detection_01 + 07_kpi_dashboard; A2 = detection_02 + detection_03. |
| `12_bubble_chart` | Competitive landscape — scaling needs improvement. | Fix axis scaling. |
| `13_threat_quadrant` | Scaling needs improvement; combine with `16_opportunity`. | Fix scaling + new combined builder: threat quadrant + winback opportunity on one slide. |
| `27_recency_analysis` | X-axis labels overlap. | Fix label rotation / spacing. (Slide is going to aux, but fix before any future promotion.) |
| `17_total_spend` | Filename misleading — script is actually "Competitor Engagement Depth" (transaction-share buckets). | Rename script to `17_engagement_depth` for clarity (no slide-level change). |

---

## Future Analysis (parked)

| Idea | Origin | Notes |
|------|--------|-------|
| Buyer personas with confidence levels | Section 2 question | Larger analytical product, not deck-level. Needs its own scoping session — what defines a persona, what data feeds it, how confidence is computed/displayed. |

---

## Global / Engine

| Item | Source | Action |
|------|--------|--------|
| Drop-if-empty rule (G6) | Section 0 | Implement runtime check in deck_builder: skip slide if its DataFrame is empty. |
| Auxiliary deck (G7) | Section 0 | Build secondary PPTX containing all NO-verdict slides; produced alongside main deck. |
| TXN-only preamble (G1, G3) | Section 1 | Branch `_build_preamble_slides` on mode. TXN-only returns only P01 (TXN title), P02 (KPI), P03 (Program Performance divider). |
| Divider font (G2) | Section 0 | Standardize all divider layouts to Mailer Summaries (P10) font size. |
