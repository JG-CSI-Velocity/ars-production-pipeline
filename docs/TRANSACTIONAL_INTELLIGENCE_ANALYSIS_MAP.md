# Transactional Intelligence Analysis Map

HTML review map: [`transactional-intelligence-analysis-map.html`](transactional-intelligence-analysis-map.html)

This map is intentionally **not** a Snowflake table design. The repo does not yet know every client import layout, monthly file name, join key, delimiter, or field position. The point of this map is to define the analysis engine first, then let the file contracts and warehouse tables follow the analysis.

## What Is Known

The repo already contains a real analysis estate:

| Inventory | Count |
|---|---:|
| Registered analysis sections | 30 |
| Script catalog rows | 407 |
| Runnable scripts | 402 |
| ARS sections | 7 |
| TXN sections | 23 |

Primary sources:

- `01_Analysis/00-Scripts/tools/sections.json`
- `01_Analysis/00-Scripts/analytics/`
- `01_Analysis/00-Scripts/ars_engine/intelligence/catalog.py`
- `01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_execution_map.csv`

Generated run artifacts:

- `analysis_domain_map.csv` groups the analysis estate into intelligence domains, business questions, required inputs, evidence status, and next decisions.
- `analysis_input_dependency_map.csv` maps canonical input families to minimum fields, source candidates, dependent sections, layout status, and Snowflake design decisions.
- `analysis_requirement_matrix.csv` gives one row per analysis section with scripts, business question, required input families, minimum fields, current layout readiness, generated outputs, CSM/data-team questions, and Snowflake design action.
- `analysis_field_usage_catalog.csv` parses the actual Python analysis scripts and records field references with line numbers, inferred input family, and canonical field hints. It is code evidence, not proof that a client file contains those fields.
- `analysis_layout_coverage_matrix.csv` joins the actual script field references to the current layout/contract evidence so each analysis field is marked mapped, directly loaded but unprofiled, missing, client-layout-needed, rule-based, or needing review.
- `analysis_section_evidence_review.csv` rolls the field/layout evidence back up to one row per analysis section with a concise status, summary, blockers, and analyst/data-team next steps.

## What Is Unknown Until Client Layouts Arrive

Each client may send up to 15 files per month. Some will match current assumptions, some will not. Before table design is final, the engine has to identify:

| Dependency | What Must Be Mapped |
|---|---|
| Monthly file inventory | Which files are account, transaction, campaign, balance, branch, suppression, reference, or unsupported files |
| Layout | Delimiter, header row, positional fields, renamed fields, blank columns, merged exports |
| Join keys | Account id, member id, household id, card id, campaign id, branch id |
| Time grain | Transaction date, report month, campaign wave, account open/close dates |
| Required fields | Account status, product, balance, transaction date, amount, transaction type, merchant/counterparty |
| Optional enrichment | MCC, payroll flags, Reg E, debit flag, branch, age, business/personal, campaign/control groups |
| Quality | Match rate, missing required fields, coverage months, duplicate rows, confidence |

This is why the build should not start by inventing final warehouse tables. It should start by mapping the analysis to canonical input families.

## Overall Step Process

```text
Client monthly file drop
  -> file inventory and layout profiling
  -> contract mapping and gap report
  -> canonical input families
  -> account-month feature mart
  -> analysis domains
  -> intelligence products
  -> action lists and measurement
  -> consulting story and executive output
```

## Canonical Input Families

| Input Family | Examples | Why It Matters |
|---|---|---|
| Account / ODD | account id, status, product, open/close date, branch, age, business flag, debit flag, Reg E, balance | Defines denominator, eligibility, segments, product mix, and relationship base |
| Transactions | account id, date, amount, type, merchant, MCC, terminal, card present, transaction code | Powers behavior, merchant, channel, payroll, competitor, and retention signals |
| Balance / Liquidity | current balance, average balance, balance bands, balance trend | Powers deposit retention, PFI, liquidity pressure, and value sizing |
| Product / Relationship | product holdings, household/member grouping, tenure, relationship depth | Powers cross-sell, single-product risk, and next-best product |
| Counterparty / Taxonomy | merchant normalization, competitor FI rules, payroll processors, lender categories | Converts raw descriptions into financial-life meaning |
| Campaign History | audience, wave, offer, channel, response, control/holdout | Powers campaign measurement, uplift, persistence, and next campaign targeting |
| Suppression / Compliance | do-not-contact, closed accounts, opt-outs, eligibility restrictions | Prevents bad outreach and defines addressability |
| Outcome History | next-month behavior, activation, conversion, retained balance, churn | Measures whether the recommendation worked |

## Analysis Domains

| Domain | Current Sections | Business Question | Primary Engine Products |
|---|---|---|---|
| Portfolio Foundation | `ars.overview`, `txn.general`, `txn.product`, `txn.business_accts`, `txn.personal_accts` | What is the usable account base and how is it structured? | `data_quality`, `account_month_features`, `executive_scorecard` |
| Spend / Merchant / Channel | `txn.merchant`, `txn.mcc_code`, `txn.transaction_type`, `txn.branch_txn` | Where is activity concentrating, changing, or leaking? | `counterparty_signals`, `counterparty_summary`, `relationship_segments` |
| Competitive Leakage | `txn.competition`, `txn.financial_services` | Which external institutions, lenders, fintechs, and ecosystems are capturing wallet share? | `counterparty_signals`, `pfi_verdicts`, `opportunities` |
| Primacy / Payroll / Relationship | `txn.payroll`, `txn.relationship`, `txn.balance` | Who owns the relationship and where is primacy weak? | `account_month_features`, `pfi_verdicts`, `relationship_segments`, `opportunities` |
| Retention / Lifecycle | `ars.attrition`, `txn.attrition_txn`, `txn.retention`, `txn.engagement`, `txn.segment_evolution` | Who is degrading, dormant, at risk, or ready to upgrade? | `relationship_segments`, `segment_summary`, `opportunities`, `outcome_summary` |
| Debit / Reg E / Revenue | `ars.dctr`, `ars.rege`, `txn.rege_overdraft`, `txn.interchange`, `ars.value` | Where is card, overdraft, interchange, or modeled value opportunity? | `opportunities`, `opportunity_portfolio`, `strategy_roadmap`, `measurement_plan` |
| Campaign / Cohort Measurement | `ars.mailer`, `txn.campaign`, `txn.ics_acquisition`, `txn.ICS_cohort` | Which actions changed behavior and what should be targeted next? | `campaign_targets`, `measurement_baseline`, `outcome_results`, `outcome_summary` |
| Executive Synthesis | `ars.insights`, `txn.executive` | What is the story, decision, priority, and roadmap? | `insights`, `consulting_story`, `executive_scorecard`, `strategy_roadmap` |

## Intelligence Products

The analysis sections should feed durable intelligence products:

| Product | Purpose |
|---|---|
| Data readiness | File ledger, layout gap, match rate, confidence, blocker list |
| Feature mart | Account-month behavior used by all downstream analysis |
| Counterparty graph | Merchant, payroll, competitor, lender, payment ecosystem, recurring relationship signals |
| PFI verdict | Primary with us, split, competitor-primary, or no verdict with reason codes |
| Relationship segment | Financial-life segment, risk, lifecycle, readiness, next-best motion |
| Opportunity model | Ranked account-level opportunities with value, priority, confidence, and action |
| Action package | CSM queue, banker list, marketing export, suppressions, measurement plan |
| Insight registry | Standardized consulting findings with evidence, recommendation, owner, and proof metric |
| Outcome layer | Baselines, test/control results, lift, persistence, and month-over-month delta |

## Build Rule

Python should remain the near-term analysis workbench because the existing scripts and rule logic already live there. Snowflake should become the durable history and consumption layer only after the file-layout contracts and canonical input families are validated.

Practical order:

1. Map file drops to canonical input families.
2. Produce `layout_gap_report.csv` and `data_team_load_plan.csv`.
3. Review `analysis_input_dependency_map.csv` to decide which file layouts are known, inferred, or still client-specific.
4. Build/validate `account_month_features.csv`.
5. Review `analysis_field_usage_catalog.csv` to see the actual fields referenced by the scripts.
6. Review `analysis_layout_coverage_matrix.csv` to compare those script fields against the current client layout and contract evidence.
7. Review `analysis_section_evidence_review.csv` to decide which section-level analyses are sellable now, need validation, or are blocked by layout mapping.
8. Run the analysis domains against those features and review `analysis_domain_map.csv`.
9. Review `analysis_requirement_matrix.csv` to decide which section-level analyses are safe to sell, validate, or rebuild.
10. Produce intelligence products and consulting outputs.
11. Then persist stable facts and marts to Snowflake.
