# TXN Deck Review — 2026-04-28

Source: GitHub issue #98, log `1776_20260428_140324.log` (run 1776, 2026-04-28).
Total slides generated: **339** (budget 150). 22 TXN sections + 13 ARS preamble slides prepended by `deck_builder.py:_build_preamble_slides`.

**Purpose:** Single-pass review to decide per-slide: KEEP / NIX / CONDENSE / COMBINE / FIX / NEW. Output of this doc becomes the implementation spec for deck_builder + manifest changes. No code changes until this doc is locked.

Verdict legend: `KEEP` `NIX` `CONDENSE` (combo already exists) `COMBINE` (merge with sibling) `FIX` (data/format issue) `NEW` (add slide here).

---

## 0. Global Rules

Decisions that cut across all sections. Fill these in first.

| # | Rule | Decision |
|---|------|----------|
| G1 | Preamble in TXN-only mode: title slide says 'Account Revenue Solution' — should be TXN-specific (e.g. 'Transaction Insights Report'). | _TBD_ |
| G2 | Divider font sizes are inconsistent. **Mailer Summaries divider (P10) font size wins** — apply to all dividers. | Confirmed |
| G3 | Mode handling: TXN-only vs ARS+TXN vs ARS-only — preamble must branch on mode. | _TBD_ |
| G4 | Slide budget: target ___ slides for TXN-only deck (currently 339). | _TBD_ |
| G5 | Combos already exist for response slides — flag all combo-redundant slides as CONDENSE. | _TBD_ |

---

## 1. Preamble (P01–P13)

Source: `01_Analysis/00-Scripts/output/deck_builder.py:1363` (`_build_preamble_slides`).

| # | ID | Current title | Wired to | TXN-only verdict | ARS+TXN verdict |
|---|----|---------------|----------|------------------|-----------------|
| 1 | P01 | `{client}` — Account Revenue Solution \| `{month}` | Static title | _TBD_ | _TBD_ |
| 2 | P02 | Agenda → Executive KPI Dashboard | `_build_executive_kpi` | _TBD_ | _TBD_ |
| 3 | P03 | `{client}` — Program Performance \| `{month}` | Divider | _TBD_ | _TBD_ |
| 4 | P04 | Executive Summary | Manual table | _TBD_ | _TBD_ |
| 5 | P05 | Monthly Revenue – Last 12 Months | Blank | _TBD_ | _TBD_ |
| 6 | P06 | ARS Lift Matrix | Blank | _TBD_ | _TBD_ |
| 7 | P07 | `{client}` — ARS Mailer Revisit \| `{month}` | Divider | _TBD_ | _TBD_ |
| 8 | P08 | ARS Mailer Revisit – Swipes | A12 Swipes | _TBD_ | _TBD_ |
| 9 | P09 | ARS Mailer Revisit – Spend | A12 Spend | _TBD_ | _TBD_ |
| 10 | P10 | Mailer Summaries — `{client}` \| `{month}` | Divider (font reference) | _TBD_ | _TBD_ |
| 11 | P11 | All Program Results — `{client}` \| `{month}` | Blank | _TBD_ | _TBD_ |
| 12 | P12 | Program Responses to Date | A13.5 | _TBD_ | _TBD_ |
| 13 | P13 | Data Check Overview (...heavy users) | Blank | _TBD_ | _TBD_ |

**Open questions:**
- TXN-only title text? (e.g., 'Transaction Insights Report' / 'Portfolio Transaction Review')
- Which preamble slides survive in TXN-only mode? (Likely P05/P06/P07/P08/P09/P10/P11/P12 are ARS-specific.)

---

## 2. Sections (22)

### 1. Portfolio Overview — 19 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `general_03_kpi_dashboard_01.png` | `03_kpi_dashboard` | _TBD_ |  |
| 2 | `general_04_monthly_trend_01.png` | `04_monthly_trend` | _TBD_ |  |
| 3 | `general_07_bracket_bar_01.png` | `07_bracket_bar` | _TBD_ |  |
| 4 | `general_08_bracket_donut_01.png` | `08_bracket_donut` | _TBD_ |  |
| 5 | `general_10_bracket_trend_01.png` | `10_bracket_trend` | _TBD_ |  |
| 6 | `general_12_hourly_heatmap_01.png` | `12_hourly_heatmap` | _TBD_ |  |
| 7 | `general_13_age_time_patterns_01.png` | `13_age_time_patterns` | _TBD_ |  |
| 8 | `general_14_age_spending_profile_01.png` | `14_age_spending_profile` | _TBD_ |  |
| 9 | `general_15_age_bracket_comparison_01.png` | `15_age_bracket_comparison` | _TBD_ |  |
| 10 | `general_16_biz_personal_split_01.png` | `16_biz_personal_split` | _TBD_ |  |
| 11 | `general_18_engagement_bar_01.png` | `18_engagement_bar` | _TBD_ |  |
| 12 | `general_19_seasonal_index_01.png` | `19_seasonal_index` | _TBD_ |  |
| 13 | `general_20_merchant_concentration_01.png` | `20_merchant_concentration` | _TBD_ |  |
| 14 | `general_21_growth_scorecard_01.png` | `21_growth_scorecard` | _TBD_ |  |
| 15 | `general_24_account_age_bar_01.png` | `24_account_age_bar` | _TBD_ |  |
| 16 | `general_25_time_to_first_txn_01.png` | `25_time_to_first_txn` | _TBD_ |  |
| 17 | `general_26_spend_by_account_age_01.png` | `26_spend_by_account_age` | _TBD_ |  |
| 18 | `general_27_new_account_profile_01.png` | `27_new_account_profile` | _TBD_ |  |
| 19 | `general_30_ars_swipe_segmentation_01.png` | `30_ars_swipe_segmentation` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 2. Merchant Analysis — 10 slides (FAIL: 08_merchant_volatility)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `merchant_02_merchant_kpi_01.png` | `02_merchant_kpi` | _TBD_ |  |
| 2 | `merchant_03_merchant_top20_bar_01.png` | `03_merchant_top20_bar` | _TBD_ |  |
| 3 | `merchant_04_merchant_donut_01.png` | `04_merchant_donut` | _TBD_ |  |
| 4 | `merchant_05_merchant_concentration_01.png` | `05_merchant_concentration` | _TBD_ |  |
| 5 | `merchant_06_merchant_trend_01.png` | `06_merchant_trend` | _TBD_ |  |
| 6 | `merchant_07_merchant_growth_01.png` | `07_merchant_growth` | _TBD_ |  |
| 7 | `merchant_09_merchant_lifecycle_01.png` | `09_merchant_lifecycle` | _TBD_ |  |
| 8 | `merchant_10_merchant_by_biz_personal_01.png` | `10_merchant_by_biz_personal` | _TBD_ |  |
| 9 | `merchant_11_merchant_by_age_01.png` | `11_merchant_by_age` | _TBD_ |  |
| 10 | `merchant_12_merchant_by_engagement_01.png` | `12_merchant_by_engagement` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 3. MCC Categories — 13 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `mcc_code_02_mcc_kpi_01.png` | `code_02_mcc_kpi` | _TBD_ |  |
| 2 | `mcc_code_03_mcc_top20_bar_01.png` | `code_03_mcc_top20_bar` | _TBD_ |  |
| 3 | `mcc_code_04_mcc_donut_01.png` | `code_04_mcc_donut` | _TBD_ |  |
| 4 | `mcc_code_05_mcc_three_panel_01.png` | `code_05_mcc_three_panel` | _TBD_ |  |
| 5 | `mcc_code_06_mcc_concentration_01.png` | `code_06_mcc_concentration` | _TBD_ |  |
| 6 | `mcc_code_07_mcc_trend_01.png` | `code_07_mcc_trend` | _TBD_ |  |
| 7 | `mcc_code_08_mcc_by_age_band_01.png` | `code_08_mcc_by_age_band` | _TBD_ |  |
| 8 | `mcc_code_09_mcc_by_account_age_01.png` | `code_09_mcc_by_account_age` | _TBD_ |  |
| 9 | `mcc_code_10_mcc_by_engagement_01.png` | `code_10_mcc_by_engagement` | _TBD_ |  |
| 10 | `mcc_code_11_mcc_by_biz_personal_01.png` | `code_11_mcc_by_biz_personal` | _TBD_ |  |
| 11 | `mcc_code_12_mcc_seasonal_01.png` | `code_12_mcc_seasonal` | _TBD_ |  |
| 12 | `mcc_code_13_mcc_diversity_01.png` | `code_13_mcc_diversity` | _TBD_ |  |
| 13 | `mcc_code_14_mcc_spend_profile_01.png` | `code_14_mcc_spend_profile` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 4. Business Accounts — 11 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `business_accts_02_business_kpi_01.png` | `accts_02_business_kpi` | _TBD_ |  |
| 2 | `business_accts_03_business_top20_bar_01.png` | `accts_03_business_top20_bar` | _TBD_ |  |
| 3 | `business_accts_04_business_donut_01.png` | `accts_04_business_donut` | _TBD_ |  |
| 4 | `business_accts_05_business_concentration_01.png` | `accts_05_business_concentration` | _TBD_ |  |
| 5 | `business_accts_06_business_trend_01.png` | `accts_06_business_trend` | _TBD_ |  |
| 6 | `business_accts_07_business_growth_01.png` | `accts_07_business_growth` | _TBD_ |  |
| 7 | `business_accts_08_business_volatility_01.png` | `accts_08_business_volatility` | _TBD_ |  |
| 8 | `business_accts_09_business_lifecycle_01.png` | `accts_09_business_lifecycle` | _TBD_ |  |
| 9 | `business_accts_10_business_vs_portfolio_01.png` | `accts_10_business_vs_portfolio` | _TBD_ |  |
| 10 | `business_accts_11_business_by_age_01.png` | `accts_11_business_by_age` | _TBD_ |  |
| 11 | `business_accts_12_business_by_engagement_01.png` | `accts_12_business_by_engagement` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 5. Personal Accounts — 11 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `personal_accts_02_personal_kpi_01.png` | `accts_02_personal_kpi` | _TBD_ |  |
| 2 | `personal_accts_03_personal_top20_bar_01.png` | `accts_03_personal_top20_bar` | _TBD_ |  |
| 3 | `personal_accts_04_personal_donut_01.png` | `accts_04_personal_donut` | _TBD_ |  |
| 4 | `personal_accts_05_personal_concentration_01.png` | `accts_05_personal_concentration` | _TBD_ |  |
| 5 | `personal_accts_06_personal_trend_01.png` | `accts_06_personal_trend` | _TBD_ |  |
| 6 | `personal_accts_07_personal_growth_01.png` | `accts_07_personal_growth` | _TBD_ |  |
| 7 | `personal_accts_08_personal_volatility_01.png` | `accts_08_personal_volatility` | _TBD_ |  |
| 8 | `personal_accts_09_personal_lifecycle_01.png` | `accts_09_personal_lifecycle` | _TBD_ |  |
| 9 | `personal_accts_10_personal_vs_portfolio_01.png` | `accts_10_personal_vs_portfolio` | _TBD_ |  |
| 10 | `personal_accts_11_personal_by_age_01.png` | `accts_11_personal_by_age` | _TBD_ |  |
| 11 | `personal_accts_12_personal_by_engagement_01.png` | `accts_12_personal_by_engagement` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 6. Competition — 90 slides (OK (pruned 15 cells))

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `competition_02_competitor_detection_01.png` | `02_competitor_detection` | _TBD_ |  |
| 2 | `competition_02_competitor_detection_02.png` | `02_competitor_detection` | _TBD_ |  |
| 3 | `competition_02_competitor_detection_03.png` | `02_competitor_detection` | _TBD_ |  |
| 4 | `competition_07_kpi_dashboard_01.png` | `07_kpi_dashboard` | _TBD_ |  |
| 5 | `competition_08_top_competitors_bar_01.png` | `08_top_competitors_bar` | _TBD_ |  |
| 6 | `competition_09_category_donut_01.png` | `09_category_donut` | _TBD_ |  |
| 7 | `competition_10_biz_vs_personal_01.png` | `10_biz_vs_personal` | _TBD_ |  |
| 8 | `competition_11_monthly_trend_01.png` | `11_monthly_trend` | _TBD_ |  |
| 9 | `competition_12_bubble_chart_01.png` | `12_bubble_chart` | _TBD_ |  |
| 10 | `competition_13_threat_quadrant_01.png` | `13_threat_quadrant` | _TBD_ |  |
| 11 | `competition_14_engagement_scatter_01.png` | `14_engagement_scatter` | _TBD_ |  |
| 12 | `competition_15_momentum_01.png` | `15_momentum` | _TBD_ |  |
| 13 | `competition_16_opportunity_01.png` | `16_opportunity` | _TBD_ |  |
| 14 | `competition_17_total_spend_01.png` | `17_total_spend` | _TBD_ |  |
| 15 | `competition_18_competition_aggregate_01.png` | `18_competition_aggregate` | _TBD_ |  |
| 16 | `competition_18_competition_aggregate_02.png` | `18_competition_aggregate` | _TBD_ |  |
| 17 | `competition_22_segment_top_competitors_01.png` | `22_segment_top_competitors` | _TBD_ |  |
| 18 | `competition_23_segment_by_category_01.png` | `23_segment_by_category` | _TBD_ |  |
| 19 | `competition_23_segment_by_category_02.png` | `23_segment_by_category` | _TBD_ |  |
| 20 | `competition_23_segment_by_category_03.png` | `23_segment_by_category` | _TBD_ |  |
| 21 | `competition_23_segment_by_category_04.png` | `23_segment_by_category` | _TBD_ |  |
| 22 | `competition_23_segment_by_category_05.png` | `23_segment_by_category` | _TBD_ |  |
| 23 | `competition_23_segment_by_category_06.png` | `23_segment_by_category` | _TBD_ |  |
| 24 | `competition_24_segment_heatmap_01.png` | `24_segment_heatmap` | _TBD_ |  |
| 25 | `competition_24_segment_heatmap_02.png` | `24_segment_heatmap` | _TBD_ |  |
| 26 | `competition_24_segment_heatmap_03.png` | `24_segment_heatmap` | _TBD_ |  |
| 27 | `competition_24_segment_heatmap_04.png` | `24_segment_heatmap` | _TBD_ |  |
| 28 | `competition_25_at_risk_accounts_01.png` | `25_at_risk_accounts` | _TBD_ |  |
| 29 | `competition_25_at_risk_accounts_02.png` | `25_at_risk_accounts` | _TBD_ |  |
| 30 | `competition_25_at_risk_accounts_03.png` | `25_at_risk_accounts` | _TBD_ |  |
| 31 | `competition_25_at_risk_accounts_04.png` | `25_at_risk_accounts` | _TBD_ |  |
| 32 | `competition_25_at_risk_accounts_05.png` | `25_at_risk_accounts` | _TBD_ |  |
| 33 | `competition_25_at_risk_accounts_06.png` | `25_at_risk_accounts` | _TBD_ |  |
| 34 | `competition_26_spend_scatter_01.png` | `26_spend_scatter` | _TBD_ |  |
| 35 | `competition_26_spend_scatter_02.png` | `26_spend_scatter` | _TBD_ |  |
| 36 | `competition_26_spend_scatter_03.png` | `26_spend_scatter` | _TBD_ |  |
| 37 | `competition_26_spend_scatter_04.png` | `26_spend_scatter` | _TBD_ |  |
| 38 | `competition_26_spend_scatter_05.png` | `26_spend_scatter` | _TBD_ |  |
| 39 | `competition_26_spend_scatter_06.png` | `26_spend_scatter` | _TBD_ |  |
| 40 | `competition_26_spend_scatter_07.png` | `26_spend_scatter` | _TBD_ |  |
| 41 | `competition_26_spend_scatter_08.png` | `26_spend_scatter` | _TBD_ |  |
| 42 | `competition_27_recency_analysis_01.png` | `27_recency_analysis` | _TBD_ |  |
| 43 | `competition_28_spend_vs_frequency_01.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 44 | `competition_28_spend_vs_frequency_02.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 45 | `competition_28_spend_vs_frequency_03.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 46 | `competition_28_spend_vs_frequency_04.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 47 | `competition_28_spend_vs_frequency_05.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 48 | `competition_28_spend_vs_frequency_06.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 49 | `competition_28_spend_vs_frequency_07.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 50 | `competition_28_spend_vs_frequency_08.png` | `28_spend_vs_frequency` | _TBD_ |  |
| 51 | `competition_29_wallet_share_01.png` | `29_wallet_share` | _TBD_ |  |
| 52 | `competition_29_wallet_share_02.png` | `29_wallet_share` | _TBD_ |  |
| 53 | `competition_29_wallet_share_03.png` | `29_wallet_share` | _TBD_ |  |
| 54 | `competition_29_wallet_share_04.png` | `29_wallet_share` | _TBD_ |  |
| 55 | `competition_29_wallet_share_05.png` | `29_wallet_share` | _TBD_ |  |
| 56 | `competition_29_wallet_share_06.png` | `29_wallet_share` | _TBD_ |  |
| 57 | `competition_29_wallet_share_07.png` | `29_wallet_share` | _TBD_ |  |
| 58 | `competition_29_wallet_share_08.png` | `29_wallet_share` | _TBD_ |  |
| 59 | `competition_30_category_leaders_01.png` | `30_category_leaders` | _TBD_ |  |
| 60 | `competition_31_spend_ranking_01.png` | `31_spend_ranking` | _TBD_ |  |
| 61 | `competition_32_material_threats_01.png` | `32_material_threats` | _TBD_ |  |
| 62 | `competition_33_non_bank_threats_01.png` | `33_non_bank_threats` | _TBD_ |  |
| 63 | `competition_35_competitor_count_distribution_01.png` | `35_competitor_count_distribution` | _TBD_ |  |
| 64 | `competition_60_banks_only_kpi_01.png` | `60_banks_only_kpi` | _TBD_ |  |
| 65 | `competition_60_core_competition_kpi_01.png` | `60_core_competition_kpi` | _TBD_ |  |
| 66 | `competition_61_banks_only_donut_01.png` | `61_banks_only_donut` | _TBD_ |  |
| 67 | `competition_61_core_competition_donut_01.png` | `61_core_competition_donut` | _TBD_ |  |
| 68 | `competition_62_banks_only_top10_01.png` | `62_banks_only_top10` | _TBD_ |  |
| 69 | `competition_62_core_competition_top10_01.png` | `62_core_competition_top10` | _TBD_ |  |
| 70 | `competition_65_banks_only_deep_dive_01.png` | `65_banks_only_deep_dive` | _TBD_ |  |
| 71 | `competition_65_banks_only_deep_dive_02.png` | `65_banks_only_deep_dive` | _TBD_ |  |
| 72 | `competition_65_banks_only_deep_dive_03.png` | `65_banks_only_deep_dive` | _TBD_ |  |
| 73 | `competition_65_banks_only_deep_dive_04.png` | `65_banks_only_deep_dive` | _TBD_ |  |
| 74 | `competition_65_banks_only_deep_dive_05.png` | `65_banks_only_deep_dive` | _TBD_ |  |
| 75 | `competition_65_banks_only_deep_dive_06.png` | `65_banks_only_deep_dive` | _TBD_ |  |
| 76 | `competition_65_core_competition_deep_dive_01.png` | `65_core_competition_deep_dive` | _TBD_ |  |
| 77 | `competition_65_core_competition_deep_dive_02.png` | `65_core_competition_deep_dive` | _TBD_ |  |
| 78 | `competition_65_core_competition_deep_dive_03.png` | `65_core_competition_deep_dive` | _TBD_ |  |
| 79 | `competition_65_core_competition_deep_dive_04.png` | `65_core_competition_deep_dive` | _TBD_ |  |
| 80 | `competition_65_core_competition_deep_dive_05.png` | `65_core_competition_deep_dive` | _TBD_ |  |
| 81 | `competition_65_core_competition_deep_dive_06.png` | `65_core_competition_deep_dive` | _TBD_ |  |
| 82 | `competition_66_core_bnpl_share_01.png` | `66_core_bnpl_share` | _TBD_ |  |
| 83 | `competition_66_core_bnpl_share_02.png` | `66_core_bnpl_share` | _TBD_ |  |
| 84 | `competition_66_core_bnpl_share_03.png` | `66_core_bnpl_share` | _TBD_ |  |
| 85 | `competition_66_core_bnpl_share_04.png` | `66_core_bnpl_share` | _TBD_ |  |
| 86 | `competition_67_core_bnpl_threats_01.png` | `67_core_bnpl_threats` | _TBD_ |  |
| 87 | `competition_67_core_bnpl_threats_02.png` | `67_core_bnpl_threats` | _TBD_ |  |
| 88 | `competition_70_banking_vs_ecosystems_01.png` | `70_banking_vs_ecosystems` | _TBD_ |  |
| 89 | `competition_70_banking_vs_ecosystems_02.png` | `70_banking_vs_ecosystems` | _TBD_ |  |
| 90 | `competition_70_banking_vs_ecosystems_03.png` | `70_banking_vs_ecosystems` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 7. Financial Services — 15 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `financial_services_01_config_01.png` | `services_01_config` | _TBD_ |  |
| 2 | `financial_services_02_identify_01.png` | `services_02_identify` | _TBD_ |  |
| 3 | `financial_services_06_kpi_dashboard_01.png` | `services_06_kpi_dashboard` | _TBD_ |  |
| 4 | `financial_services_07_category_accounts_bar_01.png` | `services_07_category_accounts_bar` | _TBD_ |  |
| 5 | `financial_services_08_category_activity_donut_01.png` | `services_08_category_activity_donut` | _TBD_ |  |
| 6 | `financial_services_09_top_merchants_01.png` | `services_09_top_merchants` | _TBD_ |  |
| 7 | `financial_services_10_recency_heatmap_01.png` | `services_10_recency_heatmap` | _TBD_ |  |
| 8 | `financial_services_11_monthly_trend_01.png` | `services_11_monthly_trend` | _TBD_ |  |
| 9 | `financial_services_12_multi_product_01.png` | `services_12_multi_product` | _TBD_ |  |
| 10 | `financial_services_13_category_combinations_01.png` | `services_13_category_combinations` | _TBD_ |  |
| 11 | `financial_services_14_leakage_intensity_01.png` | `services_14_leakage_intensity` | _TBD_ |  |
| 12 | `financial_services_15_biz_vs_personal_01.png` | `services_15_biz_vs_personal` | _TBD_ |  |
| 13 | `financial_services_16_recency_by_category_01.png` | `services_16_recency_by_category` | _TBD_ |  |
| 14 | `financial_services_17_new_vs_recurring_01.png` | `services_17_new_vs_recurring` | _TBD_ |  |
| 15 | `financial_services_18_opportunity_waterfall_01.png` | `services_18_opportunity_waterfall` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 8. ICS Acquisition — 0 slides (NO CHARTS)

_No charts captured. NIX section, FIX data feed, or repurpose._

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 9. Campaign Analysis — 76 slides (OK (pruned 18 cells))

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `campaign_02_campaign_kpi_01.png` | `02_campaign_kpi` | _TBD_ |  |
| 2 | `campaign_03_campaign_response_grouping_01.png` | `03_campaign_response_grouping` | _TBD_ |  |
| 3 | `campaign_03_campaign_response_grouping_02.png` | `03_campaign_response_grouping` | _TBD_ |  |
| 4 | `campaign_03_campaign_response_grouping_03.png` | `03_campaign_response_grouping` | _TBD_ |  |
| 5 | `campaign_04_campaign_penetration_01.png` | `04_campaign_penetration` | _TBD_ |  |
| 6 | `campaign_04_campaign_penetration_02.png` | `04_campaign_penetration` | _TBD_ |  |
| 7 | `campaign_05_response_by_wave_01.png` | `05_response_by_wave` | _TBD_ |  |
| 8 | `campaign_05_response_by_wave_02.png` | `05_response_by_wave` | _TBD_ |  |
| 9 | `campaign_05_response_by_wave_03.png` | `05_response_by_wave` | _TBD_ |  |
| 10 | `campaign_05_response_by_wave_04.png` | `05_response_by_wave` | _TBD_ |  |
| 11 | `campaign_05_response_by_wave_05.png` | `05_response_by_wave` | _TBD_ |  |
| 12 | `campaign_05_response_by_wave_06.png` | `05_response_by_wave` | _TBD_ |  |
| 13 | `campaign_06_response_rate_trend_01.png` | `06_response_rate_trend` | _TBD_ |  |
| 14 | `campaign_06_response_rate_trend_02.png` | `06_response_rate_trend` | _TBD_ |  |
| 15 | `campaign_07_response_ladder_01.png` | `07_response_ladder` | _TBD_ |  |
| 16 | `campaign_07_response_ladder_02.png` | `07_response_ladder` | _TBD_ |  |
| 17 | `campaign_07_response_ladder_03.png` | `07_response_ladder` | _TBD_ |  |
| 18 | `campaign_07_response_ladder_04.png` | `07_response_ladder` | _TBD_ |  |
| 19 | `campaign_07_response_ladder_05.png` | `07_response_ladder` | _TBD_ |  |
| 20 | `campaign_08_response_revenue_attribution_01.png` | `08_response_revenue_attribution` | _TBD_ |  |
| 21 | `campaign_11_cohort_lift_kpi_01.png` | `11_cohort_lift_kpi` | _TBD_ |  |
| 22 | `campaign_12_cohort_before_after_01.png` | `12_cohort_before_after` | _TBD_ |  |
| 23 | `campaign_13_cohort_did_lift_01.png` | `13_cohort_did_lift` | _TBD_ |  |
| 24 | `campaign_14_cohort_spend_persistence_01.png` | `14_cohort_spend_persistence` | _TBD_ |  |
| 25 | `campaign_15_cohort_cumulative_spend_01.png` | `15_cohort_cumulative_spend` | _TBD_ |  |
| 26 | `campaign_16_cohort_counterfactual_01.png` | `16_cohort_counterfactual` | _TBD_ |  |
| 27 | `campaign_17_swipe_kpi_01.png` | `17_swipe_kpi` | _TBD_ |  |
| 28 | `campaign_18_swipe_did_lift_01.png` | `18_swipe_did_lift` | _TBD_ |  |
| 29 | `campaign_19_swipe_response_tiers_01.png` | `19_swipe_response_tiers` | _TBD_ |  |
| 30 | `campaign_20_swipe_trend_01.png` | `20_swipe_trend` | _TBD_ |  |
| 31 | `campaign_21_swipe_migration_matrix_01.png` | `21_swipe_migration_matrix` | _TBD_ |  |
| 32 | `campaign_24_segment_spend_comparison_01.png` | `24_segment_spend_comparison` | _TBD_ |  |
| 33 | `campaign_24_segment_spend_comparison_02.png` | `24_segment_spend_comparison` | _TBD_ |  |
| 34 | `campaign_24_segment_spend_comparison_03.png` | `24_segment_spend_comparison` | _TBD_ |  |
| 35 | `campaign_24_segment_spend_comparison_04.png` | `24_segment_spend_comparison` | _TBD_ |  |
| 36 | `campaign_24_segment_spend_comparison_05.png` | `24_segment_spend_comparison` | _TBD_ |  |
| 37 | `campaign_24_segment_spend_comparison_06.png` | `24_segment_spend_comparison` | _TBD_ |  |
| 38 | `campaign_25_segment_swipe_comparison_01.png` | `25_segment_swipe_comparison` | _TBD_ |  |
| 39 | `campaign_25_segment_swipe_comparison_02.png` | `25_segment_swipe_comparison` | _TBD_ |  |
| 40 | `campaign_25_segment_swipe_comparison_03.png` | `25_segment_swipe_comparison` | _TBD_ |  |
| 41 | `campaign_25_segment_swipe_comparison_04.png` | `25_segment_swipe_comparison` | _TBD_ |  |
| 42 | `campaign_25_segment_swipe_comparison_05.png` | `25_segment_swipe_comparison` | _TBD_ |  |
| 43 | `campaign_25_segment_swipe_comparison_06.png` | `25_segment_swipe_comparison` | _TBD_ |  |
| 44 | `campaign_26_segment_spend_lines_01.png` | `26_segment_spend_lines` | _TBD_ |  |
| 45 | `campaign_26_segment_spend_lines_02.png` | `26_segment_spend_lines` | _TBD_ |  |
| 46 | `campaign_26_segment_spend_lines_03.png` | `26_segment_spend_lines` | _TBD_ |  |
| 47 | `campaign_26_segment_spend_lines_04.png` | `26_segment_spend_lines` | _TBD_ |  |
| 48 | `campaign_26_segment_spend_lines_05.png` | `26_segment_spend_lines` | _TBD_ |  |
| 49 | `campaign_26_segment_spend_lines_06.png` | `26_segment_spend_lines` | _TBD_ |  |
| 50 | `campaign_27_segment_swipe_lines_01.png` | `27_segment_swipe_lines` | _TBD_ |  |
| 51 | `campaign_27_segment_swipe_lines_02.png` | `27_segment_swipe_lines` | _TBD_ |  |
| 52 | `campaign_27_segment_swipe_lines_03.png` | `27_segment_swipe_lines` | _TBD_ |  |
| 53 | `campaign_27_segment_swipe_lines_04.png` | `27_segment_swipe_lines` | _TBD_ |  |
| 54 | `campaign_27_segment_swipe_lines_05.png` | `27_segment_swipe_lines` | _TBD_ |  |
| 55 | `campaign_27_segment_swipe_lines_06.png` | `27_segment_swipe_lines` | _TBD_ |  |
| 56 | `campaign_28_segment_combo_lines_01.png` | `28_segment_combo_lines` | _TBD_ |  |
| 57 | `campaign_28_segment_combo_lines_02.png` | `28_segment_combo_lines` | _TBD_ |  |
| 58 | `campaign_28_segment_combo_lines_03.png` | `28_segment_combo_lines` | _TBD_ |  |
| 59 | `campaign_28_segment_combo_lines_04.png` | `28_segment_combo_lines` | _TBD_ |  |
| 60 | `campaign_28_segment_combo_lines_05.png` | `28_segment_combo_lines` | _TBD_ |  |
| 61 | `campaign_28_segment_combo_lines_06.png` | `28_segment_combo_lines` | _TBD_ |  |
| 62 | `campaign_29_segment_slope_proof_01.png` | `29_segment_slope_proof` | _TBD_ |  |
| 63 | `campaign_31_responder_ticket_chart_01.png` | `31_responder_ticket_chart` | _TBD_ |  |
| 64 | `campaign_31_responder_ticket_chart_02.png` | `31_responder_ticket_chart` | _TBD_ |  |
| 65 | `campaign_31_responder_ticket_chart_03.png` | `31_responder_ticket_chart` | _TBD_ |  |
| 66 | `campaign_32_responder_timing_chart_01.png` | `32_responder_timing_chart` | _TBD_ |  |
| 67 | `campaign_32_responder_timing_chart_02.png` | `32_responder_timing_chart` | _TBD_ |  |
| 68 | `campaign_32_responder_timing_chart_03.png` | `32_responder_timing_chart` | _TBD_ |  |
| 69 | `campaign_34_responder_account_age_chart_01.png` | `34_responder_account_age_chart` | _TBD_ |  |
| 70 | `campaign_36_responder_holder_age_chart_01.png` | `36_responder_holder_age_chart` | _TBD_ |  |
| 71 | `campaign_37_program_effectiveness_01.png` | `37_program_effectiveness` | _TBD_ |  |
| 72 | `campaign_38_mailer_program_proof_01.png` | `38_mailer_program_proof` | _TBD_ |  |
| 73 | `campaign_39_revenue_cascade_01.png` | `39_revenue_cascade` | _TBD_ |  |
| 74 | `campaign_40_opportunity_map_01.png` | `40_opportunity_map` | _TBD_ |  |
| 75 | `campaign_41_what_if_scenario_01.png` | `41_what_if_scenario` | _TBD_ |  |
| 76 | `campaign_42_campaign_summary_slide_01.png` | `42_campaign_summary_slide` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 10. Branch Performance — 8 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `branch_txn_02_branch_kpi_01.png` | `txn_02_branch_kpi` | _TBD_ |  |
| 2 | `branch_txn_03_branch_top_bar_01.png` | `txn_03_branch_top_bar` | _TBD_ |  |
| 3 | `branch_txn_04_branch_spend_comparison_01.png` | `txn_04_branch_spend_comparison` | _TBD_ |  |
| 4 | `branch_txn_05_branch_concentration_01.png` | `txn_05_branch_concentration` | _TBD_ |  |
| 5 | `branch_txn_06_branch_merchant_heatmap_01.png` | `txn_06_branch_merchant_heatmap` | _TBD_ |  |
| 6 | `branch_txn_07_branch_monthly_trend_01.png` | `txn_07_branch_monthly_trend` | _TBD_ |  |
| 7 | `branch_txn_08_branch_biz_personal_mix_01.png` | `txn_08_branch_biz_personal_mix` | _TBD_ |  |
| 8 | `branch_txn_09_branch_spend_profile_01.png` | `txn_09_branch_spend_profile` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 11. Transaction Type — 9 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `transaction_type_02_txn_type_kpi_01.png` | `type_02_txn_type_kpi` | _TBD_ |  |
| 2 | `transaction_type_03_txn_type_split_01.png` | `type_03_txn_type_split` | _TBD_ |  |
| 3 | `transaction_type_04_txn_type_merchant_01.png` | `type_04_txn_type_merchant` | _TBD_ |  |
| 4 | `transaction_type_05_txn_type_trend_01.png` | `type_05_txn_type_trend` | _TBD_ |  |
| 5 | `transaction_type_05b_total_spend_volume_01.png` | `type_05b_total_spend_volume` | _TBD_ |  |
| 6 | `transaction_type_06_txn_type_by_bracket_01.png` | `type_06_txn_type_by_bracket` | _TBD_ |  |
| 7 | `transaction_type_07_txn_type_by_age_01.png` | `type_07_txn_type_by_age` | _TBD_ |  |
| 8 | `transaction_type_13_multi_channel_engagement_01.png` | `type_13_multi_channel_engagement` | _TBD_ |  |
| 9 | `transaction_type_14_ars_channel_bridge_01.png` | `type_14_ars_channel_bridge` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 12. Product Analysis — 8 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `product_02_product_kpi_01.png` | `02_product_kpi` | _TBD_ |  |
| 2 | `product_03_product_distribution_01.png` | `03_product_distribution` | _TBD_ |  |
| 3 | `product_04_product_donut_01.png` | `04_product_donut` | _TBD_ |  |
| 4 | `product_05_product_spend_profile_01.png` | `05_product_spend_profile` | _TBD_ |  |
| 5 | `product_06_product_monthly_trend_01.png` | `06_product_monthly_trend` | _TBD_ |  |
| 6 | `product_07_product_merchant_heatmap_01.png` | `07_product_merchant_heatmap` | _TBD_ |  |
| 7 | `product_08_product_biz_personal_01.png` | `08_product_biz_personal` | _TBD_ |  |
| 8 | `product_09_product_by_engagement_01.png` | `09_product_by_engagement` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 13. Attrition (Velocity) — 9 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `attrition_txn_02_attrition_kpi_01.png` | `txn_02_attrition_kpi` | _TBD_ |  |
| 2 | `attrition_txn_03_risk_distribution_01.png` | `txn_03_risk_distribution` | _TBD_ |  |
| 3 | `attrition_txn_04_velocity_scatter_01.png` | `txn_04_velocity_scatter` | _TBD_ |  |
| 4 | `attrition_txn_05_monthly_progression_01.png` | `txn_05_monthly_progression` | _TBD_ |  |
| 5 | `attrition_txn_06_risk_by_demographics_01.png` | `txn_06_risk_by_demographics` | _TBD_ |  |
| 6 | `attrition_txn_07_risk_by_product_01.png` | `txn_07_risk_by_product` | _TBD_ |  |
| 7 | `attrition_txn_08_risk_by_competitor_01.png` | `txn_08_risk_by_competitor` | _TBD_ |  |
| 8 | `attrition_txn_09_early_warning_01.png` | `txn_09_early_warning` | _TBD_ |  |
| 9 | `attrition_txn_10_dormancy_progression_01.png` | `txn_10_dormancy_progression` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 14. Balance Analysis — 8 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `balance_02_balance_kpi_01.png` | `02_balance_kpi` | _TBD_ |  |
| 2 | `balance_03_balance_distribution_01.png` | `03_balance_distribution` | _TBD_ |  |
| 3 | `balance_04_balance_bands_bar_01.png` | `04_balance_bands_bar` | _TBD_ |  |
| 4 | `balance_05_balance_vs_activity_01.png` | `05_balance_vs_activity` | _TBD_ |  |
| 5 | `balance_06_deposit_flight_risk_01.png` | `06_deposit_flight_risk` | _TBD_ |  |
| 6 | `balance_07_balance_by_demographics_01.png` | `07_balance_by_demographics` | _TBD_ |  |
| 7 | `balance_08_pfi_scoring_01.png` | `08_pfi_scoring` | _TBD_ |  |
| 8 | `balance_09_balance_vs_competitor_01.png` | `09_balance_vs_competitor` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 15. Interchange Revenue — 9 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `interchange_02_interchange_kpi_01.png` | `02_interchange_kpi` | _TBD_ |  |
| 2 | `interchange_03_pin_sig_trend_01.png` | `03_pin_sig_trend` | _TBD_ |  |
| 3 | `interchange_04_pin_sig_ratio_01.png` | `04_pin_sig_ratio` | _TBD_ |  |
| 4 | `interchange_05_revenue_waterfall_01.png` | `05_revenue_waterfall` | _TBD_ |  |
| 5 | `interchange_06_pin_heavy_accounts_01.png` | `06_pin_heavy_accounts` | _TBD_ |  |
| 6 | `interchange_07_interchange_by_demographics_01.png` | `07_interchange_by_demographics` | _TBD_ |  |
| 7 | `interchange_08_interchange_by_merchant_01.png` | `08_interchange_by_merchant` | _TBD_ |  |
| 8 | `interchange_09_interchange_by_product_01.png` | `09_interchange_by_product` | _TBD_ |  |
| 9 | `interchange_10_action_summary_01.png` | `10_action_summary` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 16. Reg E / Overdraft — 9 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `rege_overdraft_02_rege_kpi_01.png` | `overdraft_02_rege_kpi` | _TBD_ |  |
| 2 | `rege_overdraft_03_optin_trend_01.png` | `overdraft_03_optin_trend` | _TBD_ |  |
| 3 | `rege_overdraft_04_optin_migration_01.png` | `overdraft_04_optin_migration` | _TBD_ |  |
| 4 | `rege_overdraft_05_od_limit_distribution_01.png` | `overdraft_05_od_limit_distribution` | _TBD_ |  |
| 5 | `rege_overdraft_06_od_limit_trend_01.png` | `overdraft_06_od_limit_trend` | _TBD_ |  |
| 6 | `rege_overdraft_07_rege_by_demographics_01.png` | `overdraft_07_rege_by_demographics` | _TBD_ |  |
| 7 | `rege_overdraft_08_rege_revenue_exposure_01.png` | `overdraft_08_rege_revenue_exposure` | _TBD_ |  |
| 8 | `rege_overdraft_09_rege_vs_balance_01.png` | `overdraft_09_rege_vs_balance` | _TBD_ |  |
| 9 | `rege_overdraft_10_action_summary_01.png` | `overdraft_10_action_summary` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 17. Payroll & Direct Deposit — 8 slides (FAIL: 06_payroll_processors, 10_action_summary)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `payroll_02_payroll_kpi_01.png` | `02_payroll_kpi` | _TBD_ |  |
| 2 | `payroll_03_payroll_distribution_01.png` | `03_payroll_distribution` | _TBD_ |  |
| 3 | `payroll_04_payroll_value_01.png` | `04_payroll_value` | _TBD_ |  |
| 4 | `payroll_05_payroll_by_demographics_01.png` | `05_payroll_by_demographics` | _TBD_ |  |
| 5 | `payroll_07_payroll_retention_01.png` | `07_payroll_retention` | _TBD_ |  |
| 6 | `payroll_08_pfi_composite_score_01.png` | `08_pfi_composite_score` | _TBD_ |  |
| 7 | `payroll_09_pfi_vs_competitor_01.png` | `09_pfi_vs_competitor` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 18. Relationship Depth — 7 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `relationship_02_relationship_kpi_01.png` | `02_relationship_kpi` | _TBD_ |  |
| 2 | `relationship_03_product_count_bar_01.png` | `03_product_count_bar` | _TBD_ |  |
| 3 | `relationship_04_single_product_risk_01.png` | `04_single_product_risk` | _TBD_ |  |
| 4 | `relationship_05_cross_sell_matrix_01.png` | `05_cross_sell_matrix` | _TBD_ |  |
| 5 | `relationship_06_relationship_value_01.png` | `06_relationship_value` | _TBD_ |  |
| 6 | `relationship_07_leakage_opportunity_01.png` | `07_leakage_opportunity` | _TBD_ |  |
| 7 | `relationship_08_relationship_by_demographics_01.png` | `08_relationship_by_demographics` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 19. Segment Evolution — 6 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `segment_evolution_02_segment_kpi_01.png` | `evolution_02_segment_kpi` | _TBD_ |  |
| 2 | `segment_evolution_03_segment_distribution_01.png` | `evolution_03_segment_distribution` | _TBD_ |  |
| 3 | `segment_evolution_04_migration_matrix_01.png` | `evolution_04_migration_matrix` | _TBD_ |  |
| 4 | `segment_evolution_05_upgraders_vs_degraders_01.png` | `evolution_05_upgraders_vs_degraders` | _TBD_ |  |
| 5 | `segment_evolution_06_segment_vs_campaign_01.png` | `evolution_06_segment_vs_campaign` | _TBD_ |  |
| 6 | `segment_evolution_07_segment_prediction_01.png` | `evolution_07_segment_prediction` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 20. Retention Analysis — 6 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `retention_02_retention_kpi_01.png` | `02_retention_kpi` | _TBD_ |  |
| 2 | `retention_03_churn_by_segment_01.png` | `03_churn_by_segment` | _TBD_ |  |
| 3 | `retention_03_churn_by_segment_02.png` | `03_churn_by_segment` | _TBD_ |  |
| 4 | `retention_04_attrition_cost_01.png` | `04_attrition_cost` | _TBD_ |  |
| 5 | `retention_05_dormancy_funnel_01.png` | `05_dormancy_funnel` | _TBD_ |  |
| 6 | `retention_06_early_warning_01.png` | `06_early_warning` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 21. Engagement Migration — 5 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `engagement_02_migration_kpi_01.png` | `02_migration_kpi` | _TBD_ |  |
| 2 | `engagement_03_migration_matrix_01.png` | `03_migration_matrix` | _TBD_ |  |
| 3 | `engagement_04_net_flow_01.png` | `04_net_flow` | _TBD_ |  |
| 4 | `engagement_05_migration_by_segment_01.png` | `05_migration_by_segment` | _TBD_ |  |
| 5 | `engagement_05_migration_by_segment_02.png` | `05_migration_by_segment` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

### 22. Executive Scorecard — 2 slides (OK)

| # | Chart file | Source script | Verdict | Note |
|---|------------|---------------|---------|------|
| 1 | `executive_02_scorecard_dashboard_01.png` | `02_scorecard_dashboard` | _TBD_ |  |
| 2 | `executive_04_opportunity_waterfall_01.png` | `04_opportunity_waterfall` | _TBD_ |  |

**Section-level decisions:**
- Keep section in TXN-only mode? _TBD_
- Condense / combine candidates: _TBD_
- New slides to add here: _TBD_

---

## 3. New Sections to Add

| Proposed name | Purpose | Sources / data | Slot |
|---------------|---------|----------------|------|
| _TBD_ | _TBD_ | _TBD_ | _TBD_ |

---

## 4. Failures to Triage

| Section | Script | Action |
|---------|--------|--------|
| Merchant Analysis | `08_merchant_volatility` | _TBD_ |
| Payroll & Direct Deposit | `06_payroll_processors` | _TBD_ |
| Payroll & Direct Deposit | `10_action_summary` | _TBD_ |
| ICS Acquisition | (entire section, 0 charts) | _TBD_ |

---

## 5. Open Questions / Parking Lot

- 
