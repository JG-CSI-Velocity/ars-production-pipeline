# Analysis Section Summary

Browser HTML section view: [`analysis-section-summary.html`](analysis-section-summary.html)

Data science review and analysis plan: [`DATA_SCIENCE_ANALYSIS_PLAN.md`](DATA_SCIENCE_ANALYSIS_PLAN.md)

Quick reference for what each analysis section does and how a run moves from raw files to finished deliverables. For deeper module-level formulas and denominator rules, see [MODULES.md](MODULES.md). For the full pipeline diagram, see [WORKFLOW_MAP.md](WORKFLOW_MAP.md).

## Overall Step Process

1. **Select the run scope** - The UI or CLI identifies the CSM, month, client, and product (`ars`, `txn`, or `combined`).
2. **Format source files** - Raw ODD files are retrieved, normalized, and written as ready-for-analysis Excel workbooks; optional TXN, deferred revenue, and workbook side files are staged with the client.
3. **Load and validate data** - The analysis runner loads the formatted ODD, validates required columns, parses dates, applies client config, and derives missing monthly spend/swipe fields when possible.
4. **Build reusable subsets** - The runner creates canonical account slices: open accounts, eligible accounts, personal/business splits, debit holders, and last-12-month cohorts.
5. **Run analytics sections** - ARS modules run from the class registry; TXN sections run after a shared `txn_setup` namespace loads and prepares transaction data. Each section writes charts, tables, `ctx.results`, and manifest status.
6. **Generate deliverables** - Empty slides are dropped, then the run report, analysis workbook, main deck, and optional auxiliary deck are built from the slide manifest.
7. **Audit and package output** - The pipeline writes the denominator audit, run scorecard, diagnostics, and final deck/workbook files into the completed analysis and presentation folders.

## ARS Sections

| Section | Concise summary |
|---|---|
| Overview | Establishes the account base: status/product-code coverage, open vs eligible counts, and personal/business mix. |
| DCTR | Measures debit card take rate across history, recent cohorts, branches, funnels, and customer segments. |
| Reg E | Measures consumer debit overdraft opt-in status, branch/dimension patterns, and related overdraft exposure. |
| Attrition | Quantifies account closure and retention patterns by cohort, segment, branch, debit status, mailer response, and revenue impact. |
| Value | Converts debit and Reg E performance gaps into revenue opportunity using upstream section results. |
| Mailer | Evaluates campaign reach, response, cohort lift, revenue attribution, spend persistence, and responder/control behavior. |
| Insights | Synthesizes upstream ARS results into executive story slides, conclusions, effectiveness views, branch scorecards, and dormant opportunity. |

## TXN Setup

| Section | Concise summary |
|---|---|
| TXN Setup | Shared preparation step for TXN runs: discovers files, configures inputs, combines transactions, standardizes merchants, imports ODD/account data, and exposes common DataFrames for all TXN sections. |

## TXN Sections

| Section | Concise summary |
|---|---|
| Portfolio Overview | Establishes transaction portfolio KPIs, spend/swipe trends, demographics, lifecycle, engagement, and broad action themes. |
| Merchant Analysis | Identifies top merchants, merchant concentration, growth, volatility, lifecycle patterns, new entrants, and merchant-level actions. |
| MCC Categories | Summarizes spend and activity by MCC category, including mix, trends, concentration, seasonality, demographics, and diversity. |
| Business Accounts | Profiles business-account transaction behavior across top merchants, concentration, growth, lifecycle, age, engagement, and actions. |
| Personal Accounts | Profiles consumer-account transaction behavior across top merchants, trends, concentration, lifecycle, portfolio comparison, and actions. |
| Competition | Measures external wallet-share pressure, competitor threats, category leaders, segment risk, BNPL/core/bank views, and exportable action lists. |
| Financial Services | Detects financial-services leakage by category, merchant, recency, account mix, combinations, and opportunity size. |
| ICS Acquisition | Evaluates ICS acquisition performance across channels, merchant preferences, monthly trends, engagement, retention, and portfolio comparison. |
| ICS Cohort | Compares ICS and non-ICS cohorts across source, product/stat mix, debit coverage, age, balance, activity, activation, retention, closure, and branch patterns. |
| Campaign Analysis | Measures TXN-side campaign performance with response cohorts, DID/counterfactual lift, swipe migration, spend persistence, revenue cascade, and spend-shift views. |
| Branch Performance | Ranks branches by transaction activity, merchant mix, spend concentration, trends, business/personal mix, spend profile, and action opportunities. |
| Transaction Type | Analyzes channel mix across PIN, signature, ACH, check, and related payment channels, including migration and deep-dive patterns. |
| Product Analysis | Breaks transaction activity down by product, including distribution, spend profile, trend, merchant heatmap, business/personal split, and engagement. |
| Attrition (Velocity) | Scores transaction-based attrition risk, progression, risk drivers, early warnings, and at-risk export lists. |
| Balance Analysis | Connects balances to activity, balance bands, deposit flight risk, PFI scoring, demographics, and competitor comparison. |
| Interchange Revenue | Quantifies PIN/signature revenue mix, interchange opportunity, PIN-heavy accounts, and merchant/product/demographic revenue patterns. |
| Reg E / Overdraft | Uses TXN-side data to analyze opt-in trends, migration, overdraft limits, revenue exposure, demographics, and balance relationships. |
| Payroll & Direct Deposit | Detects payroll/direct-deposit behavior, processor mix, payroll value, retention, demographics, PFI score, and competitor comparison. |
| Relationship Depth | Measures cross-product depth, single-product risk, cross-sell opportunities, relationship value, leakage, demographics, and next-best product. |
| Segment Evolution | Tracks movement across engagement segments, including upgraders/degraders, migration matrix, campaign relationship, prediction, and action summary. |
| Retention Analysis | Measures transaction retention, churn by segment, attrition cost, dormancy funnel, early warnings, and retention actions. |
| Engagement Migration | Tracks month-to-month engagement tier movement, migration matrix, net flow, segment shifts, and related actions. |
| Executive Scorecard | Rolls TXN findings into an executive scorecard, strategic priorities, opportunity waterfall, and action roadmap. |
