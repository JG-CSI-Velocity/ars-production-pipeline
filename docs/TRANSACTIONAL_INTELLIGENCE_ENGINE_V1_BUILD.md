# Transactional Intelligence Engine V1 Build

Browser HTML build view: [`engine-build.html`](engine-build.html)

This is the first working code layer for the Transactional Intelligence Engine. It does not replace the existing ARS/TXN analysis sections. It creates the reusable product layer those sections need.

## What Was Built

Package:

```text
01_Analysis/00-Scripts/ars_engine/intelligence/
```

Core module:

```text
ars_engine.intelligence.engine
```

CLI:

```text
ars_engine.intelligence.cli
```

Tests:

```text
01_Analysis/00-Scripts/tests/test_transactional_intelligence_engine.py
```

## Engine Flow

```text
Account file + transaction files
  -> intake profile + file ledger
  -> intake work order
  -> file assembly plan
  -> data quality score
  -> account-month feature mart
  -> PFI verdicts
  -> counterparty signals + counterparty summary
  -> relationship segments + segment summary
  -> ranked opportunities
  -> executive scorecard + strategy roadmap
  -> opportunity portfolio + action plan + measurement plan
  -> campaign targets + baseline snapshot
  -> outcome results + outcome summary
  -> standardized insight objects
  -> analysis section catalog + provenance map
  -> consulting story + role handoff map
  -> CSV/JSON/Excel/HTML/Snowflake outputs
```

## Outputs

When the engine runs, it writes:

| Artifact | Purpose |
|---|---|
| `intake_profile.json` | File-drop profiling: delimiter/header detection, contract match, missing required fields, row estimates |
| `intake_work_order.csv` | Operator triage table for each client file: use, map, ignore, repair, or create layout contract |
| `file_assembly_plan.csv` | Engine loading plan for a monthly file drop: selected account file, selected transaction files, supporting files, duplicates, and held files |
| `layout_gap_report.csv` | Field-level file layout analysis: canonical fields, matched/missing status, suggested source column or position, and remediation action |
| `source_layout_profile.csv` | Source-column layout profile showing every received column/position, matched canonical fields, role guesses, proposed input family, proposed contract id, and mapping action |
| `file_ledger.csv` | Source file lineage: path, type, size, modified time, hash |
| `data_quality.json` | Coverage, mapped columns, account match rate, warnings, confidence |
| `engine_run_ledger.csv` | Operator run ledger by stage: owner, status, row count, key metric, input/output artifacts, Snowflake targets, evidence summary, blocking issue, and next action |
| `engine_readiness_assessment.csv` | Run-level go/no-go assessment by readiness area, owner, client-use status, blocker count, validation count, proof artifacts, and next action |
| `account_month_features.csv` | Reusable account-month feature mart |
| `account_intelligence_profile.csv` | Consolidated account-level diagnosis: relationship segment, PFI, top counterparties, top play, target status, recommended action, evidence summary |
| `model_rulebook.csv` | Rule catalog showing scoring families, conditions, thresholds, evidence fields, source artifacts, owner role, and consulting use |
| `account_scoring_trace.csv` | Account-month explainability trace showing the exact PFI, segment, top opportunity, feature evidence, thresholds, reason codes, recommended action, and decision narrative |
| `pfi_verdicts.csv` | Account-level PFI status, score, confidence, reason codes |
| `counterparty_signals.csv` | Account-month payroll, external FI, financial-services, and merchant counterparty signals |
| `counterparty_summary.csv` | Client/month counterparty rollup for payroll proof, competitor leakage, lender relationships, and merchant behavior |
| `relationship_segments.csv` | Account-level financial-life segment, lifecycle stage, risk, readiness score, and next-best motion |
| `segment_summary.csv` | Segment-level rollup for consulting strategy and dashboard review |
| `opportunities.csv` | Ranked action opportunities with expected value and priority |
| `opportunity_portfolio.csv` | Aggregated strategic plays: target counts, expected value, confidence, owner, channel, next step |
| `executive_scorecard.csv` | Executive RAG scorecard across trust, primacy, competitive risk, activation, retention, economics, measurement, and outcomes |
| `strategy_roadmap.csv` | Now/Next/Later strategy roadmap with owner, dependency, source signal, and proof metric |
| `action_plan.csv` | CSM/consulting playbook rows: objective, audience, talk track, target list, status |
| `role_handoffs.csv` | Operating map for the owner, CSM, analyst, marketing, client team, and data team |
| `measurement_plan.csv` | Per-play measurement design: holdout guidance, test counts, primary metric, 30/60/90 windows |
| `campaign_targets.csv` | Account-level execution list with deterministic test/holdout assignment and baseline behavior |
| `csm_review_queue.csv` | CSM-facing prioritized account review queue with top play, expected value, recommended action, and evidence |
| `analyst_validation_queue.csv` | Analyst QA queue for data warnings, layout blockers, and account confidence review |
| `marketing_activation_export.csv` | Campaign-tool audience export with action/measurement IDs, test/holdout group, channel, reason codes, and metric |
| `banker_call_list.csv` | Banker/branch outreach list with talk track, top counterparties, account evidence, and action linkage |
| `data_team_load_plan.csv` | Data-team load readiness plan joining file assembly decisions to layout blockers and remediation actions |
| `stakeholder_export_manifest.csv` | Manifest of role-specific exports, row counts, primary role, use case, first action, and readiness |
| `measurement_baseline.csv` | Aggregated pre-campaign baseline by action/measurement ID |
| `outcome_results.csv` | Account-level comparison of prior targets to current behavior |
| `outcome_summary.csv` | Action-level measured outcome rates, deltas, and holdout lift when available |
| `intelligence_delta_report.csv` | Month-over-month movement report comparing current outputs to the prior package across quality score, account profiles, opportunity targets, and portfolio value/count changes |
| `insights.json` | Standardized insight objects for decks, dashboards, APIs, or Snowflake |
| `consulting_insight_register.csv` | Tabular consulting register tying opportunity insights, scorecard signals, and story steps to evidence artifacts, section readiness, model rules, owners, actions, measurement IDs, questions, and next decisions |
| `analysis_section_catalog.csv` | Section-level catalog of existing ARS/TXN analysis IP, mapped to intelligence layers, engine outputs, opportunity types, and consulting use |
| `analysis_script_catalog.csv` | Script-level inventory of the current analysis library, including source paths, inferred topics, and output roles |
| `analysis_field_usage_catalog.csv` | Static code-evidence catalog of field references parsed from analysis scripts, including source line number, inferred input family, canonical field hint, and evidence context |
| `analysis_provenance_map.csv` | Opportunity-to-section provenance bridge showing which current analysis sections support each engine recommendation |
| `analysis_execution_map.csv` | Section-by-section execution/evidence map showing required inputs, discovered scripts, generated outputs, row counts, missing evidence, consulting question, and analyst next step |
| `analysis_domain_map.csv` | Domain-level analysis map that rolls sections into business questions, required input families, evidence readiness, intelligence products, opportunity types, layout dependencies, and next decisions |
| `analysis_input_dependency_map.csv` | Canonical input-family map showing minimum fields, source candidates, dependent domains/sections, contract status, file-drop readiness, layout gaps, Snowflake design decision, and analyst next step |
| `analysis_layout_coverage_matrix.csv` | Field-level bridge from actual script references to input families, layout/contract mapping status, matched source columns, and analyst/data-team actions |
| `analysis_data_team_backlog.csv` | Prioritized data-team queue turning hard analysis field blockers into layout, contract, and Snowflake modeling work items |
| `analysis_metric_validation_queue.csv` | Analyst validation queue for derived outputs, aliases, direct-load fields, and rule-based metrics that need definition or lineage approval |
| `analysis_visual_output_map.csv` | Section-to-output visual catalog showing what each analysis section supports, which chart/table/story surface to show, readiness, scripts, and proof artifacts |
| `analysis_chart_spec_catalog.csv` | Render-ready chart/table/story specs showing source artifact, chart type, x/y/series fields, sort hints, readiness, and proof artifacts |
| `analysis_section_evidence_review.csv` | Concise section-level review of each analysis section's business question, generated outputs, field coverage counts, blockers, review status, and analyst/data-team next steps |
| `analysis_requirement_matrix.csv` | Section-level requirement matrix tying each analysis section to its domain, scripts, required input families, minimum fields, current layout readiness, generated outputs, CSM/data-team questions, and Snowflake design action |
| `consulting_story.json` | Executive summary, story arc, recommended conversation, top plays, and analyst notes |
| `run_summary.json` | Run counts and quality summary |
| `analysis_package_index.csv` | Self-describing artifact inventory: layer, consumer, row count, Snowflake target, primary key, purpose, and local path |
| `transactional_intelligence_package.xlsx` | Analyst workbook across story, role handoffs, insights, opportunities, PFI, features, and file ledger |
| `executive_brief.html` | CSM/consultant story review page with operating handoff |
| `data_quality_report.html` | Data readiness and mapped-column review page |
| `snowflake_manifest.json` | Warehouse load manifest |
| `snowflake_load.sql` | Snowflake `PUT`/load script for this run's artifacts |
| `README_SNOWFLAKE.html` | HTML data-team handoff instructions |

## Current V1 Analyses

| Analysis | What it does |
|---|---|
| Data confidence | Checks account/transaction row counts, mapped columns, transaction months, account match rate, and warnings |
| Intake profiling | Profiles every staged file and matches it to YAML data contracts |
| Intake work order | Converts file-profile results into analyst/data-team actions for usable, candidate, unsupported, or broken files |
| File-drop assembly | Selects the best account/ODD file and all usable transaction files from a monthly folder while preserving skipped/supporting files for lineage |
| Account-month features | Builds activity, spend, credits, payroll, external FI, financial-services, merchant, balance, debit, product, and engagement features |
| PFI v0 | Classifies `Primary with us`, `Split`, `Competitor-primary`, or `No verdict` |
| Counterparty intelligence | Normalizes transaction descriptions into counterparties, categories, relationship signals, recurrence, and strategic relevance |
| Relationship segmentation | Converts behavior/PFI into reusable financial-life segments and lifecycle motions |
| Opportunity scoring | Scores impact x addressability x confidence x urgency |
| Opportunity portfolio | Aggregates account-level scores into named strategic plays |
| Executive scorecard | Summarizes strategy health with RAG statuses and recommended focus areas |
| Strategy roadmap | Converts top plays and scorecard gaps into Now/Next/Later execution priorities |
| Action plan | Converts plays into owner/channel/next-step consulting rows |
| Role handoff map | Tells each operator what decision they own, what file they use, and what they do next |
| Measurement plan | Defines holdout or pre/post measurement for each play |
| Campaign targets | Produces account-level lists ready for campaign or banker execution |
| Measurement baseline | Captures pre-campaign metrics for later outcome comparison |
| Outcome results | Compares prior target accounts to current account-month behavior |
| Outcome summary | Rolls measured outcomes up by action and test/control group |
| Insight registry | Aggregates opportunities into standardized product insights |
| Analysis catalog | Inventories the existing ARS/TXN analysis sections and scripts so the engine can trace recommendations back to source analysis |
| Field usage catalog | Parses actual analysis scripts to expose which account, transaction, campaign, balance, product, and counterparty fields the code appears to use |
| Provenance map | Connects each opportunity model to the current analysis sections used as supporting evidence |
| Analysis domain map | Groups the 30 section inventory into sellable intelligence domains and marks which domains are V1-ready versus layout-dependent |
| Input dependency map | Shows which canonical input families each domain depends on, which seed contracts exist, and which client layouts still need mapping before Snowflake table design |
| Analysis requirement matrix | Gives analysts and data teams one section-level checklist for scripts, business question, minimum fields, current layout blockers, generated outputs, and warehouse action |
| Analysis visual output map | Shows which generated artifacts, charts, tables, or story views each section can support and whether those views are client-ready, validation-required, or layout-qualified |
| Analysis chart spec catalog | Turns the visual output map into render-ready chart specs with source artifact, chart type, x/y/series fields, ownership, and readiness |
| Consulting story | Turns findings into executive summary, story arc, client questions, and next steps |
| Warehouse handoff | Writes a Snowflake manifest and load SQL for durable history |
| Engine readiness assessment | Produces the go/no-go table for consulting use, Snowflake productization, activation, validation, and measurement |

## Opportunity Types

The V1 engine currently scores:

- Payroll conversion.
- Debit activation.
- Deposit retention.
- Competitor win-back.
- Dormant reactivation.
- Relationship expansion.
- Attrition prevention.

## CLI Usage

From the repo root:

For a monthly folder drop, let the engine profile and assemble usable files:

```bash
PYTHONPATH=01_Analysis/00-Scripts .venv/bin/python -m ars_engine.intelligence.cli \
  --input-dir path/to/client/month/file_drop \
  --contract-dir path/to/client/layout_contracts \
  --recursive \
  --client-id 1759 \
  --client-name "Example CU" \
  --month 2026.06 \
  --output /tmp/ti-engine-run
```

The generated `file_assembly_plan.csv` shows which file became the account input, which files became transaction inputs, and which files were held as unsupported, duplicate, or mapping-needed. The generated `layout_gap_report.csv` shows the field-level diagnosis for each received file: what maps cleanly, what required fields are missing, and what the analyst/data team has to fix.

For explicit file selection:

```bash
PYTHONPATH=01_Analysis/00-Scripts .venv/bin/python -m ars_engine.intelligence.cli \
  --accounts path/to/odd_or_accounts.xlsx \
  --transactions path/to/transactions_1.csv \
  --transactions path/to/transactions_2.csv \
  --client-id 1759 \
  --client-name "Example CU" \
  --month 2026.06 \
  --output /tmp/ti-engine-run
```

The `--transactions` flag can be repeated for monthly files. Supported file types are `.csv`, `.xlsx`, `.xlsm`, `.xls`, and `.parquet`.

To measure outcomes from a prior playbook run, pass the previous target and baseline files:

```bash
PYTHONPATH=01_Analysis/00-Scripts .venv/bin/python -m ars_engine.intelligence.cli \
  --accounts path/to/current_accounts.xlsx \
  --transactions path/to/current_transactions.csv \
  --prior-campaign-targets path/to/prior/campaign_targets.csv \
  --prior-measurement-baseline path/to/prior/measurement_baseline.csv \
  --client-id 1759 \
  --month 2026.07 \
  --output /tmp/ti-engine-run-2026-07
```

The browser Intelligence run auto-detects the latest prior package for the same CSM/client before the selected month and uses it when available.

## Python Usage

```python
import pandas as pd
from ars_engine.intelligence import EngineConfig, run_transactional_intelligence

accounts = pd.read_excel("account_file.xlsx")
transactions = pd.read_csv("transactions.csv")

outputs = run_transactional_intelligence(
    accounts=accounts,
    transactions=transactions,
    contract_dir="data_contracts",
    config=EngineConfig(client_id="1759", period_month="2026.06"),
)
outputs.write("completed_intelligence/1759/2026.06")
```

## Snowflake Path

The Python engine remains the fast experimentation layer while Snowflake becomes the durable history and product source of truth. The repo now includes:

- `snowflake/001_foundation.sql` for schemas, raw intake, contracts, canonical tables, marts, and general outputs.
- `snowflake/002_transactional_intelligence_outputs.sql` for exact V1 engine artifact targets.
- Per-run generated `snowflake_manifest.json`, `snowflake_load.sql`, and `README_SNOWFLAKE.html`.

Current Snowflake targets:

| Table | Source |
|---|---|
| `out.ti_intake_profile` | `intake_profile.json` |
| `out.ti_intake_work_order` | `intake_work_order.csv` |
| `out.ti_file_assembly_plan` | `file_assembly_plan.csv` |
| `out.ti_layout_gap_report` | `layout_gap_report.csv` |
| `out.ti_file_ledger` | `file_ledger.csv` |
| `out.ti_data_quality` | `data_quality.json` |
| `out.ti_engine_run_ledger` | `engine_run_ledger.csv` |
| `out.ti_engine_readiness_assessment` | `engine_readiness_assessment.csv` |
| `mart.ti_account_month_features` | `account_month_features.csv` |
| `mart.ti_account_intelligence_profile` | `account_intelligence_profile.csv` |
| `out.ti_model_rulebook` | `model_rulebook.csv` |
| `out.ti_account_scoring_trace` | `account_scoring_trace.csv` |
| `mart.ti_pfi_verdicts` | `pfi_verdicts.csv` |
| `mart.ti_counterparty_signals` | `counterparty_signals.csv` |
| `mart.ti_counterparty_summary` | `counterparty_summary.csv` |
| `mart.ti_relationship_segments` | `relationship_segments.csv` |
| `mart.ti_segment_summary` | `segment_summary.csv` |
| `mart.ti_opportunities` | `opportunities.csv` |
| `mart.ti_opportunity_portfolio` | `opportunity_portfolio.csv` |
| `out.ti_executive_scorecard` | `executive_scorecard.csv` |
| `out.ti_strategy_roadmap` | `strategy_roadmap.csv` |
| `out.ti_action_plan` | `action_plan.csv` |
| `out.ti_role_handoffs` | `role_handoffs.csv` |
| `out.ti_measurement_plan` | `measurement_plan.csv` |
| `out.ti_campaign_targets` | `campaign_targets.csv` |
| `out.ti_csm_review_queue` | `csm_review_queue.csv` |
| `out.ti_analyst_validation_queue` | `analyst_validation_queue.csv` |
| `out.ti_marketing_activation_export` | `marketing_activation_export.csv` |
| `out.ti_banker_call_list` | `banker_call_list.csv` |
| `out.ti_data_team_load_plan` | `data_team_load_plan.csv` |
| `out.ti_stakeholder_export_manifest` | `stakeholder_export_manifest.csv` |
| `out.ti_measurement_baseline` | `measurement_baseline.csv` |
| `out.ti_outcome_results` | `outcome_results.csv` |
| `out.ti_outcome_summary` | `outcome_summary.csv` |
| `out.ti_intelligence_delta_report` | `intelligence_delta_report.csv` |
| `out.ti_insights` | `insights.json` |
| `out.ti_consulting_insight_register` | `consulting_insight_register.csv` |
| `out.ti_analysis_section_catalog` | `analysis_section_catalog.csv` |
| `out.ti_analysis_script_catalog` | `analysis_script_catalog.csv` |
| `out.ti_analysis_provenance_map` | `analysis_provenance_map.csv` |
| `out.ti_analysis_execution_map` | `analysis_execution_map.csv` |
| `out.ti_analysis_domain_map` | `analysis_domain_map.csv` |
| `out.ti_analysis_input_dependency_map` | `analysis_input_dependency_map.csv` |
| `out.ti_analysis_layout_coverage_matrix` | `analysis_layout_coverage_matrix.csv` |
| `out.ti_analysis_data_team_backlog` | `analysis_data_team_backlog.csv` |
| `out.ti_analysis_metric_validation_queue` | `analysis_metric_validation_queue.csv` |
| `out.ti_analysis_visual_output_map` | `analysis_visual_output_map.csv` |
| `out.ti_analysis_chart_spec_catalog` | `analysis_chart_spec_catalog.csv` |
| `out.ti_analysis_section_evidence_review` | `analysis_section_evidence_review.csv` |
| `out.ti_analysis_requirement_matrix` | `analysis_requirement_matrix.csv` |
| `out.ti_consulting_story` | `consulting_story.json` |
| `out.ti_run_summary` | `run_summary.json` |
| `out.ti_analysis_package_index` | `analysis_package_index.csv` |
| `out.ti_artifact` | workbook, HTML, SQL, and handoff artifacts |

## Verification

Focused test run:

```text
.venv/bin/python -m pytest 01_Analysis/00-Scripts/tests/test_transactional_intelligence_engine.py -q
```

Result:

```text
6 passed
```
