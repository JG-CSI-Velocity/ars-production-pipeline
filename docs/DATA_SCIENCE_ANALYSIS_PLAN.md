# Data Science Analysis Plan for the Transactional Intelligence Engine

Browser HTML review view: [`data-science-analysis-plan.html`](data-science-analysis-plan.html)

V1 engine build: [`TRANSACTIONAL_INTELLIGENCE_ENGINE_V1_BUILD.md`](TRANSACTIONAL_INTELLIGENCE_ENGINE_V1_BUILD.md)

This is a data-scientist review of the current analysis sections and a plan for what the Transactional Intelligence Engine should analyze next.

## Evidence Reviewed

- `01_Analysis/00-Scripts/analytics/registry.py` defines 25 ARS modules across overview, DCTR, Reg E, attrition, value, mailer, and insights.
- `01_Analysis/00-Scripts/analytics/txn_wrapper.py` defines 23 TXN sections, including general, merchant, MCC, competition, financial services, campaign, balance, payroll, relationship, retention, engagement, and executive.
- `01_Analysis/00-Scripts/tools/sections.json` is the committed unified section registry.
- `docs/MODULES.md` documents the denominator framework, result handoff, and ARS/TXN module behavior.
- `docs/EQUATION_DICTIONARY.md` documents source-level equations, denominators, and slide output.
- `docs/ANALYSIS_SECTION_SUMMARY.md` summarizes each current analysis section.

## Data Scientist Verdict

The current repo already has a strong descriptive analytics library. It answers many "what happened?" and "where is the issue?" questions through charts, tables, rates, trends, action summaries, and some campaign lift logic.

For a true transactional intelligence engine, the next step is to move from section-level chart production to reusable account-level intelligence:

```text
Current pattern:
  source files -> section chart/table -> deck

Target pattern:
  source files -> canonical account-month features -> models/verdicts
  -> standardized insight objects -> ranked action lists -> measured outcomes
```

The most important data-science gap is not another chart. It is a shared feature, label, confidence, and outcome layer that every section can use.

## What Exists Today

| Capability | Current sections | Data-science assessment |
|---|---|---|
| Portfolio foundation | ARS overview, TXN general, product, business/personal | Good base counts and segmentation. Needs persistent client/month coverage and confidence scores. |
| Debit and Reg E performance | DCTR, Reg E, Reg E/Overdraft, interchange | Strong rate framework. Needs propensity, expected value, compliance-safe targeting, and post-action measurement. |
| Campaign measurement | Mailer, TXN campaign | Good early lift/DID foundation. Needs consistent holdouts, uplift modeling, and outcome persistence by action type. |
| Competitive leakage | competition, financial_services | Valuable merchant/counterparty detection. Needs account-level external relationship graph and share-of-wallet proxy. |
| Payroll and primacy | payroll, balance, relationship | Strong seed for PFI. Needs one formal PFI model with reason codes, confidence, and monthly transitions. |
| Lifecycle and retention | attrition, attrition_txn, retention, engagement, segment_evolution | Rich risk views. Needs survival/hazard modeling, calibrated churn labels, and early-warning feature store. |
| Revenue/value | value, interchange, executive | Useful sizing. Needs expected value per account and ranked action-level economics. |
| Executive synthesis | insights, executive | Good story layer. Should become a renderer of standardized insight objects, not a recomputation layer. |

## Engine Analyses I Would Build

### 1. Data Coverage and Confidence Analysis

Before modeling behavior, the engine should grade the monthly data.

| Analysis | Purpose | Output |
|---|---|---|
| File completeness score | Are all expected files present for this client/month? | `data_quality.file_monthly` |
| Layout coverage | Which fields are present, missing, renamed, or client-specific? | contract pass/fail plus warnings |
| Account match rate | How much TXN data links to ODD/account data? | account coverage score |
| Transaction coverage | How many months, rows, accounts, and activity types are usable? | transaction coverage score |
| Merchant normalization coverage | What share of transaction volume receives a clean counterparty/category? | taxonomy confidence |
| Insight confidence | How much should we trust each downstream recommendation? | high/medium/low confidence reason codes |

This becomes the trust layer for every insight.

### 2. Account-Month Feature Mart

The engine needs one reusable feature table. Every analysis should read from it instead of rebuilding local variables.

Recommended grain:

```text
client_id + period_month + account_id
```

Core features:

| Feature family | Examples |
|---|---|
| Activity | active days, transaction count, debit swipes, spend, ACH count, PIN/signature mix |
| Income/payroll | recurring credit amount, cadence, employer/processor, payroll consistency, payroll change |
| Balance/liquidity | average balance, balance trend, volatility, low-balance days, deposit flight signal |
| External FI movement | competitor inflows/outflows, recency, amount, frequency, number of external FIs |
| Merchant/category behavior | top merchants, category concentration, recurring merchants, subscription/debt/lender flags |
| Relationship depth | product count, tenure, debit status, branch, engagement tier, personal/business |
| Campaign exposure | mailed, response, wave, offer, control group, outcome window |
| Risk/outcome labels | dormant next month, attrited, activated, payroll converted, balance retained |

This feature mart is the center of the data science engine.

### 3. Financial-Life Understanding

Transactions should be converted into a profile of the customer's financial life.

| Inference | What to detect |
|---|---|
| Income stream | Payroll-like credits, employer/processor, consistency, volatility |
| External banking | Transfers to banks/CUs/fintechs, competitor intensity, split-wallet behavior |
| Debt and obligations | Mortgage, auto loan, credit card, student loan, BNPL, insurance, subscriptions |
| Liquidity pressure | Balance decline, overdraft/OD limit signals, high obligation burden, cash flow volatility |
| Lifestyle/category profile | Grocery, fuel, travel, healthcare, SMB, subscription, digital wallet behavior |
| Life events | New account ramp, income change, bill change, relocation/branch change, dormancy transition |

Start with explainable rules and merchant taxonomies. Add supervised models only after labels and validation data exist.

### 4. PFI and Relationship Intelligence

PFI should be the flagship model.

Recommended verdicts:

```text
Primary with us | Split relationship | Competitor-primary | No verdict
```

Recommended inputs:

| Signal | Meaning |
|---|---|
| Payroll with us vs elsewhere | Who receives the main income relationship? |
| Balance retained | Does the account hold meaningful liquidity? |
| Internal activity | Is the account used for everyday financial activity? |
| External FI movement | Are balances and payments moving to another institution? |
| Financial-services leakage | Are loans, cards, BNPL, brokerage, insurance, or mortgage relationships elsewhere? |
| Engagement trend | Is the relationship strengthening or weakening? |
| Data confidence | Is the transaction/account coverage strong enough to make a verdict? |

Each PFI verdict should include confidence and reason codes:

```text
PFI: Competitor-primary
Confidence: High
Reasons:
  - recurring external payroll detected
  - high monthly outflow to Chase
  - low balance retained with us
  - debit activity declining for 3 months
```

### 5. Opportunity Models

The engine should produce one ranked opportunity table per client/month.

| Opportunity model | Target | Primary outcome |
|---|---|---|
| Payroll conversion | Accounts with payroll elsewhere or no detected direct deposit | New/converted direct deposit |
| Debit activation | Eligible accounts with no or weak debit behavior | First swipe, active debit use, interchange lift |
| Deposit retention | High-balance or declining-balance accounts with external FI movement | Retained balance, reduced outflow |
| Competitor win-back | Accounts with high competitor intensity | Reduced competitor transfer share, deeper relationship |
| Dormant reactivation | Previously active accounts with activity decay | Recovered activity within 30/60/90 days |
| Relationship expansion | Single-product or thin-relationship accounts | Additional product or usage depth |
| Reg E/overdraft education | Eligible debit accounts not opted in or with relevant behavior | Compliance-safe education/opt-in journey |
| Merchant/category growth | Strong spend category but weak product relationship | Card usage, rewards engagement, category growth |
| Attrition prevention | High-risk accounts before closure or dormancy | Account retained, activity stabilized |
| Branch opportunity | Branches with concentrated gaps or high local leakage | Branch-managed outreach list |

Every opportunity should produce:

- Account/customer id.
- Opportunity type.
- Expected value.
- Priority score.
- Confidence.
- Reason codes.
- Recommended action.
- Suppression flags.
- Measurement/control assignment.

### 6. Causal Measurement and Uplift

Campaign analysis should become a standard measurement layer, not a separate one-off section.

Minimum methods:

| Method | Use case |
|---|---|
| Random holdout | Best option when campaign design allows it. |
| Difference-in-differences | Before/after measurement against comparison group. |
| Propensity matching | Create comparable non-targeted controls when no holdout exists. |
| Uplift modeling | Rank accounts by incremental response, not raw response likelihood. |
| Persistence analysis | Measure whether behavior remains after 30/60/90 days. |

The goal is not only "who responded?" It is "who changed because we acted?"

### 7. Insight Registry

The insight object should become the product unit.

Required fields:

| Field group | Examples |
|---|---|
| Identity | insight_id, client_id, period_month, domain, section_id |
| Population | eligible population, affected accounts, filters |
| Finding | metric, current value, benchmark, delta, trend |
| Value | opportunity amount, revenue/deposit/risk basis, assumptions |
| Confidence | score, reasons, source coverage, data warnings |
| Action | recommended action, channel, offer/message, owner |
| Targeting | target list ref, priority score, reason codes, suppressions |
| Evidence | source tables, source sections, model version, run id |
| Measurement | outcome metric, control assignment, measurement window |

Decks, dashboards, APIs, CSVs, and executive summaries should render this same object.

## Section-by-Section Data Science Upgrade

| Current section/domain | Keep | Upgrade |
|---|---|---|
| Overview/general/product | Base counts, eligibility, account mix | Add file/account coverage, segment health, benchmarkable client profile |
| DCTR | Penetration, L12M, branch/segment cuts | Add activation propensity, expected interchange lift, reason-coded activation list |
| Reg E/Rege Overdraft | Opt-in rates, trend, OD exposure | Add compliant education eligibility, risk/value bands, action outcome tracking |
| Attrition/Retention | Closure rates, velocity, dormancy funnel | Add survival model, leading indicators, calibrated retention-risk score |
| Mailer/Campaign | Reach, response, DID/lift | Add standard holdout design, uplift model, persistence and next-campaign learning |
| Merchant/MCC/Transaction Type | Top merchants, categories, concentration | Add recurring merchant role, merchant taxonomy confidence, category opportunity |
| Competition/Financial Services | External FI and leakage detection | Add external relationship graph, competitor intensity, share-of-wallet proxy |
| Payroll | Payroll detection, payroll value, PFI inputs | Add income stability, external payroll leakage, conversion propensity |
| Balance | Balance bands, deposit flight risk, PFI scoring | Add liquidity volatility, retained-balance risk, deposit retention model |
| Relationship | Product depth, cross-sell, next-best product | Add relationship graph, expected product fit, action priority |
| Segment Evolution/Engagement | Tier movement and migration | Add Markov transition model, upgrade/downgrade prediction, intervention triggers |
| Executive/Insights | Scorecard, priorities, roadmap | Convert to insight registry renderer and opportunity portfolio manager |

## First Analyses to Run

1. **Data confidence baseline.** Quantify which clients/months are model-ready.
2. **Account-month feature mart.** Create the reusable table that all models share.
3. **PFI v0.** Build explainable account-level primacy verdicts and transitions.
4. **Payroll leakage.** Detect external payroll and rank conversion opportunities.
5. **Competitor leakage graph.** Map external FI movement by account, competitor, category, amount, and recency.
6. **Deposit flight early warning.** Identify balance decline plus external movement before attrition.
7. **Dormancy and attrition survival.** Predict risk windows and leading indicators.
8. **Debit activation value.** Rank eligible no/low-debit accounts by activation likelihood and expected value.
9. **Campaign uplift.** Estimate incremental effect, not just response.
10. **Next-best action.** Combine all opportunity scores into one ranked action list.

## Python vs Snowflake vs Tool

| Layer | Best near-term home | Reason |
|---|---|---|
| Existing section logic | Python | Preserve working IP and speed of iteration. |
| Feature experiments | Python | Faster modeling, diagnostics, and notebooks/scripts. |
| Raw/stage/core tables | Snowflake | Durable monthly history, scalable joins, lineage. |
| Account-month mart | Snowflake plus Python definitions | Reusable across runs, models, dashboards, and exports. |
| Model scoring | Python first, Snowflake later if needed | Easier validation first; operationalize after stable. |
| Insight registry | Snowflake table plus JSON export | Product source of truth. |
| Review/action workflow | Better tool/app | Clients need to review, suppress, approve, export, and measure actions. |

## 90-Day Build Plan

### Days 1-30: Foundation

- Create file ledger and data-quality scoring.
- Define account-month feature mart.
- Map each current section to required inputs, generated features, and output insight objects.
- Add insight object schema and JSON/CSV output prototype.
- Preserve existing Python runs as the calculation source while the mart is being shaped.

### Days 31-60: First Models

- Build PFI v0 with reason codes and confidence.
- Build payroll leakage opportunity.
- Build competitor intensity and external FI graph.
- Build deposit-flight and dormancy early-warning scores.
- Produce action lists with expected value and suppression flags.

### Days 61-90: Measurement and Productization

- Standardize holdout/control assignment.
- Add campaign uplift and persistence measurement.
- Backtest PFI/risk scores against past retention/activity outcomes where history exists.
- Store insight registry outputs in Snowflake-ready tables.
- Add browser/app review surfaces for executive insights and action lists.

## Definition of Good

The engine is working when every monthly run can produce:

- A data-confidence score for the client/month.
- A reusable account-month feature table.
- Account-level PFI verdicts with reason codes.
- A ranked opportunity portfolio.
- Action lists with expected value, confidence, and suppressions.
- A measurement plan for each campaign/action.
- Outcome reporting that proves whether the recommendation worked.

That is the line between a strong reporting workflow and a true transactional intelligence engine.
