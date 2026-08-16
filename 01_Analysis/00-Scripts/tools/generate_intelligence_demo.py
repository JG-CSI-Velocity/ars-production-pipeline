"""Generate a concrete Transactional Intelligence Engine demo package.

This is analysis plumbing, not UI. It creates synthetic account and
transaction files, runs the actual intelligence engine, and writes the CSV,
JSON, and Snowflake package artifacts a client run would produce.

Usage:
    python 01_Analysis/00-Scripts/tools/generate_intelligence_demo.py
"""

from __future__ import annotations

import argparse
from html import escape
import inspect
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

import pandas as pd

_SCRIPTS = Path(__file__).resolve().parents[1]
_REPO = Path(__file__).resolve().parents[3]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from ars_engine.intelligence import (  # noqa: E402
    EngineConfig,
    build_account_intelligence_profile,
    build_account_month_features,
    build_account_scoring_trace,
    build_action_plan,
    build_analysis_chart_data_snapshot,
    build_analysis_consulting_playbook,
    build_analysis_execution_map,
    build_analysis_insight_brief,
    build_analysis_layout_coverage_matrix,
    build_analysis_package_index,
    build_analysis_provenance_map,
    build_analysis_review_board,
    build_analysis_section_evidence_review,
    build_analysis_script_catalog,
    build_analysis_section_catalog,
    build_campaign_targets,
    build_consulting_insight_register,
    build_consulting_story,
    build_counterparty_signals,
    build_counterparty_summary,
    build_client_meeting_deck_blueprint,
    build_engine_run_ledger,
    build_stakeholder_exports,
    build_executive_scorecard,
    build_intelligence_delta_report,
    build_intelligence_lineage_graph,
    build_intelligence_metric_catalog,
    build_intake_work_order,
    build_layout_contract_draft_queue,
    build_layout_contract_export_manifest,
    build_layout_gap_report,
    build_measurement_baseline,
    build_measurement_plan,
    build_model_rulebook,
    build_monthly_file_requirements,
    build_operating_control_plane,
    build_opportunity_portfolio,
    build_outcome_summary,
    build_production_readiness_backlog,
    build_relationship_segments,
    build_role_handoffs,
    build_segment_summary,
    build_strategy_roadmap,
    build_user_interaction_map,
    classify_pfi,
    evaluate_outcomes,
    profile_input_files,
    run_transactional_intelligence,
    score_opportunities,
    write_snowflake_package,
)


CLIENT_ID = "9999"
CLIENT_NAME = "Demo Community Credit Union"


ARTIFACT_GUIDE = {
    "file_ledger.csv": ("Intake", "Which raw files were used, size/hash, and inferred type."),
    "intake_profile.json": ("Intake", "Detected layout, headers, sample rows, and best contract match."),
    "intake_work_order.csv": ("Intake", "Operator decision: use file, map file, hold file, or request replacement."),
    "file_assembly_plan.csv": ("Intake", "Engine loading plan: selected account file, transaction files, supporting files, skipped duplicates, and held files."),
    "monthly_file_requirements.csv": ("Intake", "Monthly checklist of expected input families, received/selected files, Snowflake targets, contract actions, missing fields, affected analyses, and data-team next actions."),
    "layout_gap_report.csv": ("Intake", "Field-level layout analysis: matched fields, missing required fields, suggested source columns/positions, and remediation actions."),
    "source_layout_profile.csv": ("Intake", "Source-column profile for every received file, with canonical mappings, role guesses, proposed contract IDs, and mapping actions."),
    "layout_contract_draft_queue.csv": ("Intake", "File-level contract action queue with proposed contract IDs, missing fields, alias-map drafts, YAML stubs, analyst questions, and data-team next actions."),
    "layout_contract_export_manifest.csv": ("Intake", "Promotable contract export manifest pointing each proposed contract ID to its generated YAML file and data-team promotion action."),
    "intelligence_lineage_graph.csv": ("Audit", "End-to-end lineage edge graph linking raw files, contracts, fields, analysis sections, outputs, visuals, action plays, roles, and decisions."),
    "data_quality.json": ("Trust", "Coverage, match rate, row counts, quality score, and warnings."),
    "engine_run_ledger.csv": ("Audit", "Operator ledger by run stage with owner, status, row count, artifacts, Snowflake targets, and next action."),
    "engine_readiness_assessment.csv": ("Audit", "Run-level go/no-go assessment by readiness area, owner, client-use status, blockers, validation counts, proof artifacts, and next action."),
    "account_month_features.csv": ("Feature mart", "One row per account/month with behavior features."),
    "account_intelligence_profile.csv": ("Account Intelligence", "Consolidated account diagnosis with segment, PFI, counterparties, top play, target status, recommended action, and evidence."),
    "model_rulebook.csv": ("Model Governance", "Rule catalog with scoring families, threshold logic, evidence fields, owner role, source artifacts, and consulting use."),
    "account_scoring_trace.csv": ("Model Governance", "Account-month explainability trace for PFI, segment, top opportunity, feature evidence, thresholds, reason codes, and decision narrative."),
    "pfi_verdicts.csv": ("PFI", "Primary/split/competitor-primary verdict, score, confidence, reasons."),
    "counterparty_signals.csv": ("Counterparty", "Account-level counterparties detected from transaction text."),
    "counterparty_summary.csv": ("Counterparty", "Counterparty rollup by category, direction, accounts, and strategic relevance."),
    "relationship_segments.csv": ("Segmentation", "Consulting-ready relationship segment and next-best motion per account."),
    "segment_summary.csv": ("Segmentation", "Segment rollup: account counts, value, risk, and action themes."),
    "opportunities.csv": ("Opportunity", "Ranked account-level opportunities with reason codes."),
    "opportunity_portfolio.csv": ("Strategy", "Portfolio-level plays: target accounts, value, confidence, owners."),
    "executive_scorecard.csv": ("Executive", "Domain scorecard for meeting story and strategic focus."),
    "strategy_roadmap.csv": ("Strategy", "Sequenced roadmap: now, next, later initiatives and proof metrics."),
    "action_plan.csv": ("Action", "CSM/marketing/banker-ready play plan with channels and talk tracks."),
    "measurement_plan.csv": ("Measurement", "How each action will be measured, including metric and window."),
    "campaign_targets.csv": ("Activation", "Account-level export list for campaigns or banker outreach."),
    "csm_review_queue.csv": ("Execution", "CSM-facing prioritized account review queue with evidence and recommended action."),
    "analyst_validation_queue.csv": ("Execution", "Analyst QA queue for warnings, layout blockers, and account confidence checks."),
    "marketing_activation_export.csv": ("Execution", "Campaign-tool audience export with action IDs, measurement groups, channels, and reason codes."),
    "banker_call_list.csv": ("Execution", "High-touch banker/branch outreach list with talk track and account evidence."),
    "data_team_load_plan.csv": ("Execution", "Data-team file load readiness and layout remediation plan."),
    "stakeholder_export_manifest.csv": ("Execution", "Manifest of role-specific exports, row counts, use cases, and first actions."),
    "measurement_baseline.csv": ("Measurement", "Baseline metrics by action for future outcome comparison."),
    "outcome_results.csv": ("Outcome", "Account-level pre/post outcome results when prior targets exist."),
    "outcome_summary.csv": ("Outcome", "Action-level outcome rollup: response rate, lift, deltas, interpretation."),
    "intelligence_delta_report.csv": ("Outcome", "Month-over-month movement report across quality, account profiles, opportunities, and portfolio plays."),
    "insights.json": ("Insight", "Structured insight objects for decks, APIs, and consulting briefs."),
    "consulting_insight_register.csv": ("Insight", "Tabular consulting register tying insights, scorecard signals, story steps, evidence, rules, owners, actions, and next decisions."),
    "role_handoffs.csv": ("Operating model", "What the CSM, analyst, banker, marketing, and exec do next."),
    "operating_control_plane.csv": ("Operating model", "Role-by-role control plane showing workflow lane, operating question, status, open-first artifact, blockers, exports, and next action."),
    "user_interaction_map.csv": ("Operating model", "Role-to-output interaction manifest showing who opens which artifact, where, why, row count, Snowflake target, downstream use, and next action."),
    "production_readiness_backlog.csv": ("Productization", "Owner-ready backlog consolidating readiness findings, data mapping gaps, metric validation needs, layout contract work, analysis review blockers, user delivery blockers, acceptance criteria, and Snowflake targets."),
    "analysis_section_catalog.csv": ("Analysis IP", "Section-level map of current ARS/TXN analysis sections to engine layers and opportunity types."),
    "analysis_script_catalog.csv": ("Analysis IP", "Script-level inventory with source paths, inferred topics, and output roles."),
    "analysis_field_usage_catalog.csv": ("Analysis IP", "Static code-evidence catalog of fields referenced by the existing analysis scripts."),
    "analysis_provenance_map.csv": ("Analysis IP", "Opportunity-to-section bridge showing which existing analyses support each engine recommendation."),
    "analysis_execution_map.csv": ("Analysis IP", "Section-by-section evidence map showing required inputs, scripts, generated outputs, row counts, missing evidence, and analyst next step."),
    "analysis_domain_map.csv": ("Analysis IP", "Domain-level rollup of sections, business questions, inputs, evidence readiness, and next decisions."),
    "analysis_input_dependency_map.csv": ("Data strategy", "Input-family dependency map showing minimum fields, layout readiness, Snowflake design decisions, and analyst next steps."),
    "analysis_layout_coverage_matrix.csv": ("Data strategy", "Field-level bridge from actual script references to layout/contract evidence, coverage status, and analyst/data-team actions."),
    "analysis_data_team_backlog.csv": ("Data strategy", "Grouped data-team backlog that turns hard analysis field blockers into prioritized layout, contract, and Snowflake modeling work."),
    "analysis_metric_validation_queue.csv": ("Data strategy", "Grouped analyst validation queue for derived outputs, aliases, direct-load fields, and rule-based fields that need definition or lineage approval."),
    "analysis_visual_output_map.csv": ("Analysis IP", "Section-to-output catalog showing what each analysis supports, what visual/chart/table surface to show, readiness, scripts, proof artifacts, and next actions."),
    "analysis_chart_spec_catalog.csv": ("Analysis IP", "Render-ready chart/table/story specs with source artifact, chart type, x/y/series fields, sort hints, readiness, and proof artifacts."),
    "analysis_chart_data_snapshot.csv": ("Analysis IP", "Machine-readable backing data for every chart spec: row counts, top data points, sample records, numeric summaries, status, and insight callout."),
    "intelligence_metric_catalog.csv": ("Semantic Layer", "Semantic catalog tying chart/output fields to business definitions, aggregation methods, validation status, model rules, sample values, Snowflake expression hints, and CSM interpretation."),
    "analysis_section_evidence_review.csv": ("Analysis IP", "Concise section-level evidence review with status, generated outputs, field coverage counts, blockers, and next steps."),
    "analysis_requirement_matrix.csv": ("Analysis IP", "Section-level requirement matrix showing required inputs, current layout readiness, generated outputs, and consulting/data-team questions."),
    "analysis_consulting_playbook.csv": ("Story", "Section-level consulting playbook showing what each analysis proves, which chart/output to open, the CSM talk track, validation focus, data dependency, and marketing use."),
    "analysis_insight_brief.csv": ("Story", "Data-backed section brief combining chart callouts, semantic metrics, validation caveats, CSM talk track, recommended client question, proof artifacts, and next actions."),
    "client_meeting_deck_blueprint.csv": ("Story", "Ordered client meeting/deck sequence with phase, slide title, message, decision prompt, source artifact, evidence caveat, owner, and follow-up action."),
    "analysis_review_board.csv": ("Analysis IP", "One-row-per-section board showing what is analyzed, scripts, charts/graphs, metrics, insight, caveat, client question, Snowflake target, and meeting-story placement."),
    "consulting_story.json": ("Story", "Narrative arc, headline, proof points, risks, and next meeting ask."),
    "run_summary.json": ("Audit", "Row counts and run summary for package validation."),
    "analysis_package_index.csv": ("Audit", "Run-level artifact inventory with layer, consumer, row count, target table, primary key, purpose, and local path."),
    "snowflake_manifest.json": ("Warehouse", "File-to-table manifest for Snowflake loading and lineage."),
    "snowflake_load.sql": ("Warehouse", "PUT/COPY SQL to load generated artifacts into Snowflake."),
    "README_SNOWFLAKE.html": ("Warehouse", "HTML instructions for loading the package into Snowflake."),
}


FUNCTIONS = [
    build_intake_work_order,
    build_layout_gap_report,
    build_layout_contract_draft_queue,
    build_layout_contract_export_manifest,
    build_monthly_file_requirements,
    build_intelligence_lineage_graph,
    build_analysis_chart_data_snapshot,
    build_intelligence_metric_catalog,
    build_analysis_consulting_playbook,
    build_analysis_insight_brief,
    build_client_meeting_deck_blueprint,
    build_analysis_review_board,
    build_account_month_features,
    build_account_intelligence_profile,
    build_model_rulebook,
    build_account_scoring_trace,
    classify_pfi,
    build_counterparty_signals,
    build_counterparty_summary,
    score_opportunities,
    build_relationship_segments,
    build_segment_summary,
    build_opportunity_portfolio,
    build_executive_scorecard,
    build_strategy_roadmap,
    build_action_plan,
    build_measurement_plan,
    build_campaign_targets,
    build_stakeholder_exports,
    build_engine_run_ledger,
    build_measurement_baseline,
    evaluate_outcomes,
    build_outcome_summary,
    build_intelligence_delta_report,
    build_consulting_insight_register,
    build_role_handoffs,
    build_operating_control_plane,
    build_user_interaction_map,
    build_production_readiness_backlog,
    build_analysis_package_index,
    build_analysis_section_catalog,
    build_analysis_script_catalog,
    build_analysis_layout_coverage_matrix,
    build_analysis_section_evidence_review,
    build_analysis_provenance_map,
    build_analysis_execution_map,
    build_consulting_story,
    run_transactional_intelligence,
    write_snowflake_package,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic Transactional Intelligence analysis package.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=_REPO / "01_Analysis" / "01_Completed_Intelligence" / "Demo",
        help="Root folder for generated demo outputs.",
    )
    parser.add_argument("--clean", action="store_true", help="Delete the demo output root before regenerating.")
    args = parser.parse_args()

    if args.clean and args.output_root.exists():
        shutil.rmtree(args.output_root)

    package_root = args.output_root / CLIENT_ID
    raw_dir = package_root / "raw_inputs"
    june_dir = package_root / "2026.06_planning_run"
    july_dir = package_root / "2026.07_measurement_run"
    for path in (raw_dir, june_dir, july_dir):
        path.mkdir(parents=True, exist_ok=True)

    accounts_june = _accounts_june()
    accounts_july = _accounts_july()
    tx_june = _transactions_june()
    tx_july = _transactions_july()

    account_june_path = raw_dir / "9999_ODD_accounts_2026.06.csv"
    account_july_path = raw_dir / "9999_ODD_accounts_2026.07.csv"
    txn_june_path = raw_dir / "9999_transactions_2026.06.csv"
    txn_july_path = raw_dir / "9999_transactions_2026.07.csv"
    branch_june_path = raw_dir / "9999_branch_roster_2026.06.csv"
    suppression_july_path = raw_dir / "9999_marketing_suppressions_2026.07.csv"
    accounts_june.to_csv(account_june_path, index=False)
    accounts_july.to_csv(account_july_path, index=False)
    tx_june.to_csv(txn_june_path, index=False)
    tx_july.to_csv(txn_july_path, index=False)
    _branch_roster().to_csv(branch_june_path, index=False)
    _marketing_suppressions().to_csv(suppression_july_path, index=False)

    june_cfg = EngineConfig(client_id=CLIENT_ID, client_name=CLIENT_NAME, period_month="2026.06")
    june_outputs = run_transactional_intelligence(
        accounts=accounts_june,
        transactions=tx_june,
        input_files=[account_june_path, txn_june_path, branch_june_path],
        config=june_cfg,
    )
    june_artifacts = june_outputs.write(june_dir)
    june_artifacts.update(
        write_snowflake_package(june_outputs, june_dir, config=june_cfg, artifact_paths=june_artifacts)
    )

    july_cfg = EngineConfig(client_id=CLIENT_ID, client_name=CLIENT_NAME, period_month="2026.07")
    july_outputs = run_transactional_intelligence(
        accounts=accounts_july,
        transactions=tx_july,
        input_files=[account_july_path, txn_july_path, suppression_july_path],
        prior_campaign_targets=june_outputs.campaign_targets,
        prior_measurement_baseline=june_outputs.measurement_baseline,
        prior_account_intelligence_profile=june_outputs.account_intelligence_profile,
        prior_opportunities=june_outputs.opportunities,
        prior_opportunity_portfolio=june_outputs.opportunity_portfolio,
        prior_data_quality=june_outputs.data_quality,
        config=july_cfg,
    )
    july_artifacts = july_outputs.write(july_dir)
    july_artifacts.update(
        write_snowflake_package(july_outputs, july_dir, config=july_cfg, artifact_paths=july_artifacts)
    )

    _write_package_readme(package_root, raw_dir, june_dir, july_dir, june_outputs, july_outputs)
    _write_launchpad_html(package_root, raw_dir, june_dir, july_dir, june_outputs, july_outputs)
    _write_intake_cockpit_html(package_root, raw_dir, july_dir, july_outputs)
    _write_client_story_html(package_root, july_dir, july_outputs)
    _write_actuals_html(package_root, raw_dir, june_dir, july_dir, june_outputs, july_outputs)
    _write_analysis_dashboard_html(package_root, raw_dir, june_dir, july_dir, june_outputs, july_outputs)
    _write_analysis_workbench_html(package_root, july_dir, july_outputs)
    _write_lineage_map_html(package_root, july_dir, july_outputs)
    _write_section_drilldown_pages(package_root, july_dir, july_outputs)
    _write_analysis_chart_gallery_html(package_root, july_dir, july_outputs)

    print(f"Wrote demo analysis package: {package_root}")
    print(f"  Raw inputs: {raw_dir}")
    print(f"  June planning outputs: {june_dir}")
    print(f"  July measurement outputs: {july_dir}")
    print(f"  Launchpad: {package_root / 'transactional_intelligence_launchpad.html'}")
    print(f"  Intake cockpit: {package_root / 'transactional_intelligence_intake_cockpit.html'}")
    print(f"  Client story: {package_root / 'transactional_intelligence_client_story.html'}")
    print(f"  Actuals report: {package_root / 'transactional_intelligence_actuals.html'}")
    print(f"  Analysis dashboard: {package_root / 'transactional_intelligence_analysis_dashboard.html'}")
    print(f"  Analysis workbench: {package_root / 'transactional_intelligence_analysis_workbench.html'}")
    print(f"  Lineage map: {package_root / 'transactional_intelligence_lineage_map.html'}")
    print(f"  Section drilldowns: {package_root / 'transactional_intelligence_section_drilldowns.html'}")
    print(f"  Chart gallery: {package_root / 'transactional_intelligence_chart_gallery.html'}")
    return 0


def _accounts_june() -> pd.DataFrame:
    rows = [
        ["1001", "A", "CHK", "2020-01-15", 18000, "Y", "N", "Main"],
        ["1001", "A", "SAV", "2020-01-15", 18000, "Y", "N", "Main"],
        ["1002", "A", "SAV", "2024-03-10", 650, "N", "N", "North"],
        ["1003", "A", "BUS", "2019-08-03", 23000, "Y", "Y", "Downtown"],
        ["1004", "A", "CHK", "2021-11-22", 8200, "N", "N", "South"],
        ["1005", "A", "CHK", "2023-02-18", 1400, "Y", "N", "Main"],
        ["1006", "A", "CHK", "2022-07-01", 450, "Y", "N", "North"],
        ["1007", "A", "MMA", "2018-05-09", 7600, "N", "N", "West"],
        ["1008", "A", "CHK", "2025-01-04", 1300, "Y", "N", "South"],
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Account Number",
            "Stat Code",
            "Product Code",
            "Date Opened",
            "Avg Bal",
            "Debit?",
            "Business?",
            "Branch",
        ],
    )


def _accounts_july() -> pd.DataFrame:
    rows = [
        ["1001", "A", "CHK", "2020-01-15", 18150, "Y", "N", "Main"],
        ["1001", "A", "SAV", "2020-01-15", 18150, "Y", "N", "Main"],
        ["1002", "A", "CHK", "2024-03-10", 1850, "Y", "N", "North"],
        ["1003", "A", "BUS", "2019-08-03", 24200, "Y", "Y", "Downtown"],
        ["1004", "A", "CHK", "2021-11-22", 8300, "Y", "N", "South"],
        ["1005", "A", "CHK", "2023-02-18", 1600, "Y", "N", "Main"],
        ["1006", "A", "CHK", "2022-07-01", 980, "Y", "N", "North"],
        ["1006", "A", "SAV", "2022-07-01", 980, "Y", "N", "North"],
        ["1007", "A", "MMA", "2018-05-09", 7900, "Y", "N", "West"],
        ["1008", "A", "CHK", "2025-01-04", 1500, "Y", "N", "South"],
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Account Number",
            "Stat Code",
            "Product Code",
            "Date Opened",
            "Avg Bal",
            "Debit?",
            "Business?",
            "Branch",
        ],
    )


def _transactions_june() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["1001", "2026-06-03", 3600, "ADP Payroll Direct Deposit", "ACH Credit"],
            ["1001", "2026-06-17", 3600, "ADP Payroll Direct Deposit", "ACH Credit"],
            ["1001", "2026-06-04", -86, "Kroger Grocery", "Debit Card"],
            ["1001", "2026-06-08", -3200, "Chase Bank Transfer", "ACH Debit"],
            ["1001", "2026-06-12", -1800, "Rocket Mortgage Payment", "ACH Debit"],
            ["1001", "2026-06-25", -500, "Fidelity Brokerage Transfer", "ACH Debit"],
            ["1002", "2026-06-10", 1200, "Remote Deposit", "ACH Credit"],
            ["1002", "2026-06-12", -700, "Wells Fargo Payment", "ACH Debit"],
            ["1003", "2026-06-03", 7200, "Stripe Merchant Settlement", "ACH Credit"],
            ["1003", "2026-06-07", -8500, "Bank of America Transfer", "ACH Debit"],
            ["1003", "2026-06-14", -1500, "State Farm Insurance", "ACH Debit"],
            ["1003", "2026-06-22", -225, "Office Depot", "Debit Card"],
            ["1005", "2026-06-05", 3200, "Paychex Payroll", "ACH Credit"],
            ["1005", "2026-06-08", -95, "Target", "Debit Card"],
            ["1005", "2026-06-18", -140, "Costco", "Debit Card"],
            ["1006", "2026-06-02", 900, "Mobile Deposit", "ACH Credit"],
            ["1006", "2026-06-06", -400, "Capital One Credit Card", "ACH Debit"],
            ["1006", "2026-06-16", -300, "Discover Card Payment", "ACH Debit"],
            ["1006", "2026-06-21", -120, "Venmo Transfer", "ACH Debit"],
            ["1007", "2026-06-09", -2000, "Ally Bank Transfer", "ACH Debit"],
            ["1007", "2026-06-19", -350, "SoFi Student Loan", "ACH Debit"],
            ["1008", "2026-06-05", -45, "Shell Fuel", "Debit Card"],
            ["1008", "2026-06-15", -38, "Pharmacy", "Debit Card"],
        ],
        columns=["primary_account_num", "transaction_date", "amount", "description", "transaction_type"],
    )


def _branch_roster() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["Main", "Downtown", "manager_a@example.com"],
            ["North", "Northside", "manager_b@example.com"],
            ["South", "South Market", "manager_c@example.com"],
        ],
        columns=["Branch", "Market", "Manager Email"],
    )


def _marketing_suppressions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["1004", "Do not email"],
            ["1007", "Branch managed only"],
        ],
        columns=["Account Number", "Suppression Reason"],
    )


def _transactions_july() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["1001", "2026-07-03", 3600, "ADP Payroll Direct Deposit", "ACH Credit"],
            ["1001", "2026-07-17", 3600, "ADP Payroll Direct Deposit", "ACH Credit"],
            ["1001", "2026-07-05", -105, "Kroger Grocery", "Debit Card"],
            ["1001", "2026-07-09", -900, "Chase Bank Transfer", "ACH Debit"],
            ["1001", "2026-07-12", -1800, "Rocket Mortgage Payment", "ACH Debit"],
            ["1002", "2026-07-02", 2450, "ADP Payroll Direct Deposit", "ACH Credit"],
            ["1002", "2026-07-06", -145, "Walmart", "Debit Card"],
            ["1002", "2026-07-14", -72, "Gas Station", "Debit Card"],
            ["1002", "2026-07-26", -62, "Grocery Store", "Debit Card"],
            ["1003", "2026-07-03", 7600, "Stripe Merchant Settlement", "ACH Credit"],
            ["1003", "2026-07-07", -1200, "Bank of America Transfer", "ACH Debit"],
            ["1003", "2026-07-21", -260, "Office Depot", "Debit Card"],
            ["1004", "2026-07-03", -110, "Grocery Store", "Debit Card"],
            ["1004", "2026-07-10", -95, "Fuel Center", "Debit Card"],
            ["1004", "2026-07-18", -130, "Home Improvement", "Debit Card"],
            ["1005", "2026-07-05", 3200, "Paychex Payroll", "ACH Credit"],
            ["1005", "2026-07-08", -125, "Target", "Debit Card"],
            ["1005", "2026-07-18", -180, "Costco", "Debit Card"],
            ["1006", "2026-07-02", 1500, "Mobile Deposit", "ACH Credit"],
            ["1006", "2026-07-06", -100, "Capital One Credit Card", "ACH Debit"],
            ["1006", "2026-07-17", -60, "Venmo Transfer", "ACH Debit"],
            ["1007", "2026-07-04", 1800, "Gusto Payroll", "ACH Credit"],
            ["1007", "2026-07-09", -280, "SoFi Student Loan", "ACH Debit"],
            ["1007", "2026-07-20", -95, "Debit Card Purchase", "Debit Card"],
            ["1008", "2026-07-05", -70, "Shell Fuel", "Debit Card"],
            ["1008", "2026-07-11", -84, "Grocery Store", "Debit Card"],
            ["1008", "2026-07-24", -65, "Restaurant", "Debit Card"],
        ],
        columns=["primary_account_num", "transaction_date", "amount", "description", "transaction_type"],
    )


def _write_package_readme(
    package_root: Path,
    raw_dir: Path,
    june_dir: Path,
    july_dir: Path,
    june_outputs: Any,
    july_outputs: Any,
) -> None:
    rows = _artifact_rows(june_dir, july_dir)
    _write_package_readme_html(
        package_root,
        raw_dir,
        june_dir,
        july_dir,
        rows,
        _function_rows(),
        _analysis_section_counts(),
        june_outputs,
        july_outputs,
    )


def _write_package_readme_html(
    package_root: Path,
    raw_dir: Path,
    june_dir: Path,
    july_dir: Path,
    artifact_rows: list[dict[str, Any]],
    functions: list[dict[str, Any]],
    sections: dict[str, int],
    june_outputs: Any,
    july_outputs: Any,
) -> None:
    raw_rows = "".join(
        "<tr>"
        f"<td><a href='{_file_url(path)}'>{escape(path.name)}</a></td>"
        f"<td>{escape(_repo_rel(path))}</td>"
        "</tr>"
        for path in sorted(raw_dir.glob("*"))
        if path.is_file()
    )
    function_rows = "".join(
        "<tr>"
        f"<td><code>{escape(item['name'])}</code></td>"
        f"<td><a href='{_file_url(Path(item['path']))}'>{escape(_repo_rel(Path(item['path'])))}:{item['line']}</a></td>"
        f"<td>{escape(item['purpose'])}</td>"
        "</tr>"
        for item in functions
    )
    artifact_table_rows = "".join(
        "<tr>"
        f"<td><code>{escape(item['file'])}</code></td>"
        f"<td>{escape(item['layer'])}</td>"
        f"<td><a href='{_file_url(item['june_path'])}'>{item['june_rows']}</a></td>"
        f"<td><a href='{_file_url(item['july_path'])}'>{item['july_rows']}</a></td>"
        f"<td>{escape(item['purpose'])}</td>"
        "</tr>"
        for item in artifact_rows
    )
    section_rows = "".join(
        f"<tr><td><code>{escape(section)}</code></td><td>{count}</td></tr>"
        for section, count in sections.items()
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Actual Analysis Package</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #14213d; background: #f6f7f9; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 32px 0 12px; font-size: 20px; }}
    p {{ line-height: 1.45; }}
    a {{ color: #155eef; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef1f5; border: 1px solid #d9dee8; border-radius: 4px; padding: 2px 5px; }}
    .small {{ color: #5f6b7a; font-size: 13px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }}
    .metric {{ background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #5f6b7a; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 5px; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0; }}
    .links a {{ border: 1px solid #d9dee8; background: #fff; border-radius: 6px; padding: 8px 10px; font-size: 13px; }}
    .scroll {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9dee8; }}
    th, td {{ border-bottom: 1px solid #e6e9ef; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #edf2f8; color: #344054; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    @media (max-width: 860px) {{ main {{ padding: 18px; }} .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 560px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Transactional Intelligence Actual Analysis Package</h1>
  <p class="small">Synthetic client {CLIENT_ID}. This package is generated from raw files so the analysis can be inspected end to end.</p>
  <nav class="links">
    <a href="{_file_url(package_root / "transactional_intelligence_launchpad.html")}">Open launchpad</a>
    <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
    <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
    <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Analysis dashboard</a>
    <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
    <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Section drilldowns</a>
    <a href="{_file_url(package_root / "transactional_intelligence_lineage_map.html")}">Lineage map</a>
    <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
    <a href="{_file_url(package_root / "transactional_intelligence_actuals.html")}">Actuals tables</a>
    <a href="{_file_url(july_dir / "README_SNOWFLAKE.html")}">July Snowflake readme</a>
    <a href="{_file_url(june_dir / "README_SNOWFLAKE.html")}">June Snowflake readme</a>
  </nav>

  <section class="grid" aria-label="Package metrics">
    <div class="metric"><span>June opportunities</span><strong>{len(june_outputs.opportunities)}</strong></div>
    <div class="metric"><span>June targets</span><strong>{len(june_outputs.campaign_targets)}</strong></div>
    <div class="metric"><span>July outcomes</span><strong>{len(july_outputs.outcome_results)}</strong></div>
    <div class="metric"><span>July quality</span><strong>{escape(str(july_outputs.data_quality.get("quality_score")))}</strong></div>
  </section>

  <h2>Raw Inputs</h2>
  <div class="scroll"><table><thead><tr><th>File</th><th>Path</th></tr></thead><tbody>{raw_rows}</tbody></table></div>

  <h2>What Ran</h2>
  <div class="scroll"><table><thead><tr><th>Function</th><th>Source</th><th>Purpose</th></tr></thead><tbody>{function_rows}</tbody></table></div>

  <h2>Output Artifacts</h2>
  <div class="scroll"><table><thead><tr><th>Artifact</th><th>Layer</th><th>June rows</th><th>July rows</th><th>Purpose</th></tr></thead><tbody>{artifact_table_rows}</tbody></table></div>

  <h2>Existing Analysis Sections In Repo</h2>
  <div class="scroll"><table><thead><tr><th>Section folder</th><th>Script count</th></tr></thead><tbody>{section_rows}</tbody></table></div>
</main>
</body>
</html>
"""
    (package_root / "README.html").write_text(html, encoding="utf-8")


def _write_launchpad_html(
    package_root: Path,
    raw_dir: Path,
    june_dir: Path,
    july_dir: Path,
    june_outputs: Any,
    july_outputs: Any,
) -> None:
    role_cards = [
        {
            "role": "Executive / product owner",
            "question": "Is the intelligence package ready to use with the client?",
            "open_first": package_root / "transactional_intelligence_analysis_dashboard.html",
            "open_label": "Open dashboard",
            "use": "Review quality, scorecard, top plays, readiness, and the meeting story before client handoff.",
            "files": [
                july_dir / "executive_scorecard.csv",
                july_dir / "engine_readiness_assessment.csv",
                july_dir / "production_readiness_backlog.csv",
            ],
        },
        {
            "role": "CSM",
            "question": "What is the client story and what do we ask them to do next?",
            "open_first": package_root / "transactional_intelligence_client_story.html",
            "open_label": "Open client story",
            "use": "Use the story arc, proof points, decision prompts, action plan, and exports to run the strategy conversation.",
            "files": [
                july_dir / "analysis_insight_brief.csv",
                july_dir / "client_meeting_deck_blueprint.csv",
                july_dir / "analysis_review_board.csv",
                july_dir / "csm_review_queue.csv",
            ],
        },
        {
            "role": "Analyst",
            "question": "What exactly is being analyzed and what needs validation?",
            "open_first": package_root / "transactional_intelligence_section_drilldowns.html",
            "open_label": "Open section drilldowns",
            "use": "Inspect every section, script evidence, charts, metric lineage, caveats, and validation queues.",
            "files": [
                july_dir / "analysis_chart_spec_catalog.csv",
                july_dir / "analysis_chart_data_snapshot.csv",
                july_dir / "intelligence_metric_catalog.csv",
                july_dir / "analysis_metric_validation_queue.csv",
            ],
        },
        {
            "role": "Data / Snowflake",
            "question": "What files load, what contracts are missing, and what blockers remain?",
            "open_first": package_root / "transactional_intelligence_intake_cockpit.html",
            "open_label": "Open intake cockpit",
            "use": "Confirm monthly files, select fallback extracts, promote contracts, load Snowflake, and clear mapping blockers.",
            "files": [
                july_dir / "snowflake_manifest.json",
                july_dir / "snowflake_load.sql",
                july_dir / "file_assembly_plan.csv",
                july_dir / "layout_contract_draft_queue.csv",
                july_dir / "monthly_file_requirements.csv",
                july_dir / "production_readiness_backlog.csv",
            ],
        },
        {
            "role": "Marketing / banker teams",
            "question": "Which audiences or accounts should be activated?",
            "open_first": july_dir / "marketing_activation_export.csv",
            "open_label": "Open activation export",
            "use": "Launch campaign audiences, preserve action and measurement IDs, and use banker call lists for high-touch outreach.",
            "files": [
                july_dir / "campaign_targets.csv",
                july_dir / "marketing_activation_export.csv",
                july_dir / "banker_call_list.csv",
                july_dir / "measurement_plan.csv",
            ],
        },
    ]
    card_html = "".join(_launchpad_role_card(card) for card in role_cards)
    metrics = [
        ("Raw files", len(list(raw_dir.glob("*")))),
        ("Analysis sections", len(july_outputs.analysis_review_board)),
        ("Charts / specs", len(july_outputs.analysis_chart_spec_catalog)),
        ("Semantic metrics", len(july_outputs.intelligence_metric_catalog)),
        ("Backlog items", len(july_outputs.production_readiness_backlog)),
        ("Package artifacts", len(july_outputs.analysis_package_index)),
    ]
    metric_html = "".join(_metric(label, value) for label, value in metrics)
    top_backlog = july_outputs.production_readiness_backlog.sort_values(["priority_band", "backlog_rank"]).head(18)
    role_interactions = july_outputs.user_interaction_map.head(24)
    package_rows = july_outputs.analysis_package_index[
        july_outputs.analysis_package_index["artifact_name"].isin(
            [
                "analysis_review_board",
                "analysis_insight_brief",
                "client_meeting_deck_blueprint",
                "analysis_chart_data_snapshot",
                "intelligence_metric_catalog",
                "production_readiness_backlog",
                "snowflake_manifest",
            ]
        )
    ] if not july_outputs.analysis_package_index.empty else pd.DataFrame()
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Launchpad</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #111827; background: #f6f8fb; }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 0 0 12px; font-size: 19px; }}
    h3 {{ margin: 0 0 7px; font-size: 15px; }}
    p {{ margin: 0; line-height: 1.45; }}
    a {{ color: #155eef; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef2f7; border: 1px solid #d8dee8; border-radius: 4px; padding: 2px 5px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee8; }}
    th, td {{ border-bottom: 1px solid #e7ebf2; padding: 8px 9px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background: #eef3f8; color: #344054; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }}
    .eyebrow {{ color: #64748b; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; margin-bottom: 6px; }}
    .subtle {{ color: #64748b; font-size: 13px; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; max-width: 760px; }}
    .nav a, .link-row a {{ border: 1px solid #d8dee8; background: #fff; border-radius: 6px; padding: 7px 9px; font-size: 13px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }}
    .metric {{ background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 12px; min-height: 78px; }}
    .metric span {{ display: block; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 8px; }}
    .flow {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }}
    .step {{ background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 12px; min-height: 96px; }}
    .step b {{ display: block; font-size: 13px; margin-bottom: 5px; }}
    .step span {{ color: #64748b; font-size: 12px; line-height: 1.35; }}
    .role-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 16px 0; }}
    .role {{ background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 14px; display: grid; gap: 10px; }}
    .role-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }}
    .role-title {{ font-weight: 700; font-size: 16px; }}
    .question {{ color: #475467; font-size: 13px; }}
    .link-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .section {{ background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; margin-top: 16px; }}
    .scroll {{ overflow-x: auto; }}
    @media (max-width: 1080px) {{ .metric-grid, .flow {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} .role-grid {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 680px) {{ main {{ padding: 16px; }} .topline {{ display: block; }} .nav {{ justify-content: flex-start; margin-top: 12px; }} .metric-grid, .flow {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Open this first</div>
      <h1>Transactional Intelligence Launchpad</h1>
      <p class="subtle">Role-based starting point for using the generated analysis package, outputs, and Snowflake handoff.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "README.html")}">Package README</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">All analysis sections</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(july_dir / "README_SNOWFLAKE.html")}">Snowflake readme</a>
    </nav>
  </div>

  <section class="metric-grid">{metric_html}</section>

  <section class="flow" aria-label="Workflow">
    <div class="step"><b>1. Intake</b><span>Confirm files, layouts, selected account/transaction inputs, and monthly requirements.</span></div>
    <div class="step"><b>2. Analyze</b><span>Open section drilldowns to inspect what each analysis does and which outputs/charts it creates.</span></div>
    <div class="step"><b>3. Story</b><span>Use insight briefs and the meeting blueprint to build the client consulting narrative.</span></div>
    <div class="step"><b>4. Readiness</b><span>Clear production backlog items or qualify caveats before client-facing use.</span></div>
    <div class="step"><b>5. Load</b><span>Stage generated CSV/JSON artifacts and run Snowflake load SQL with row-count checks.</span></div>
    <div class="step"><b>6. Activate</b><span>Export targets, preserve measurement IDs, and compare outcomes next period.</span></div>
  </section>

  <section class="role-grid">{card_html}</section>

  <section class="section">
    <h2>Role Interaction Map</h2>
    <p class="subtle">Who opens what, where, why, and what action comes next.</p>
    <div class="scroll">{_df_table(role_interactions, ["user_role", "workflow_lane", "primary_screen", "file_name", "decision_supported", "owner_next_action", "client_use_status"], 24)}</div>
  </section>

  <section class="section">
    <h2>Top Production Backlog</h2>
    <p class="subtle">The first blockers to clear before calling this repeatable, Snowflake-ready, and client-facing.</p>
    <div class="scroll">{_df_table(top_backlog, ["backlog_rank", "priority_band", "workstream", "owner_role", "problem_statement", "required_action", "acceptance_criteria"], 18)}</div>
  </section>

  <section class="section">
    <h2>Core Output Files</h2>
    <p class="subtle">The most important package artifacts for analysis review, story, charting, and productization.</p>
    <div class="scroll">{_df_table(package_rows, ["artifact_name", "analysis_layer", "primary_consumer", "row_count", "target_table", "purpose"], 18)}</div>
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_launchpad.html").write_text(html, encoding="utf-8")


def _launchpad_role_card(card: dict[str, Any]) -> str:
    file_links = "".join(
        f"<a href='{_file_url(path)}'>{escape(path.name)}</a>"
        for path in card["files"]
        if path.exists()
    )
    return (
        "<article class='role'>"
        "<div class='role-head'>"
        f"<div><div class='role-title'>{escape(card['role'])}</div>"
        f"<p class='question'>{escape(card['question'])}</p></div>"
        f"<a href='{_file_url(card['open_first'])}'>{escape(card['open_label'])}</a>"
        "</div>"
        f"<p>{escape(card['use'])}</p>"
        f"<div class='link-row'>{file_links}</div>"
        "</article>"
    )


def _write_client_story_html(
    package_root: Path,
    july_dir: Path,
    july_outputs: Any,
) -> None:
    story = july_outputs.consulting_story or {}
    data_quality = july_outputs.data_quality or {}
    action_plan = july_outputs.action_plan.copy()
    meeting_blueprint = july_outputs.client_meeting_deck_blueprint.copy()
    insight_brief = july_outputs.analysis_insight_brief.copy()
    scorecard = july_outputs.executive_scorecard.copy()
    roadmap = july_outputs.strategy_roadmap.copy()
    csm_queue = july_outputs.csm_review_queue.copy()
    marketing_export = july_outputs.marketing_activation_export.copy()
    banker_list = july_outputs.banker_call_list.copy()
    stakeholder_exports = july_outputs.stakeholder_export_manifest.copy()
    measurement_plan = july_outputs.measurement_plan.copy()
    outcome_summary = july_outputs.outcome_summary.copy()
    role_handoffs = july_outputs.role_handoffs.copy()
    production_backlog = july_outputs.production_readiness_backlog.copy()
    caveats = insight_brief[
        insight_brief.get("brief_status", pd.Series(dtype=object)).map(lambda value: _clean_cell(value) != "client_story_ready")
    ].head(12) if not insight_brief.empty and "brief_status" in insight_brief.columns else insight_brief.head(0)
    delivery_backlog = production_backlog[
        production_backlog.get("workstream", pd.Series(dtype=object)).isin(
            ["Analysis readiness", "User delivery", "Metric validation"]
        )
    ].head(20) if not production_backlog.empty and "workstream" in production_backlog.columns else pd.DataFrame()
    story_arc = pd.DataFrame(story.get("story_arc", []))
    conversation = story.get("recommended_conversation", [])
    questions = story.get("consulting_questions", [])
    metrics = [
        ("Quality score", data_quality.get("quality_score", "--")),
        ("Action plays", len(action_plan)),
        ("Meeting rows", len(meeting_blueprint)),
        ("CSM accounts", len(csm_queue)),
        ("Marketing targets", len(marketing_export)),
        ("Banker calls", len(banker_list)),
        ("Outcome rows", len(outcome_summary)),
        ("Open caveats", len(caveats)),
    ]
    metric_html = "".join(_metric(label, value) for label, value in metrics)

    direct_links = _intake_direct_links(
        [
            ("Consulting story JSON", july_dir / "consulting_story.json"),
            ("Client meeting blueprint", july_dir / "client_meeting_deck_blueprint.csv"),
            ("Analysis insight brief", july_dir / "analysis_insight_brief.csv"),
            ("Action plan", july_dir / "action_plan.csv"),
            ("Campaign targets", july_dir / "campaign_targets.csv"),
            ("CSM review queue", july_dir / "csm_review_queue.csv"),
            ("Marketing export", july_dir / "marketing_activation_export.csv"),
            ("Banker call list", july_dir / "banker_call_list.csv"),
            ("Measurement plan", july_dir / "measurement_plan.csv"),
            ("Outcome summary", july_dir / "outcome_summary.csv"),
            ("Production backlog", july_dir / "production_readiness_backlog.csv"),
        ]
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Client Story</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #64748b;
      --line: #d8dee8;
      --panel: #ffffff;
      --wash: #f5f7fb;
      --blue: #155eef;
      --green: #047857;
      --amber: #b45309;
      --red: #b42318;
      --teal: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--wash); }}
    main {{ max-width: 1360px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 31px; line-height: 1.12; }}
    h2 {{ margin: 0 0 10px; font-size: 18px; }}
    h3 {{ margin: 0 0 8px; font-size: 15px; }}
    p {{ margin: 0; line-height: 1.45; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef2f7; border: 1px solid var(--line); border-radius: 4px; padding: 2px 5px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ border-bottom: 1px solid #e7ebf2; padding: 8px 9px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background: #eef3f8; color: #344054; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .topline {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--muted); text-transform: uppercase; letter-spacing: .08em; font-size: 12px; margin-bottom: 6px; }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; max-width: 860px; }}
    .nav a, .link-grid a {{ border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 7px 9px; font-size: 13px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 78px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 8px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin-top: 16px; }}
    .story-hero {{ background: #ffffff; border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin-top: 12px; }}
    .hero-title {{ font-size: 24px; font-weight: 700; margin-bottom: 8px; }}
    .grid-2 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; align-items: start; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; align-items: start; }}
    .card-list {{ display: grid; gap: 10px; }}
    .story-card {{ border: 1px solid #e2e8f0; background: #fbfcfe; border-radius: 8px; padding: 12px; }}
    .story-card b {{ display: block; margin-bottom: 5px; }}
    .story-card .links {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
    .story-card .links a, .story-card .links span {{ border: 1px solid var(--line); border-radius: 5px; padding: 4px 6px; font-size: 11px; background: #fff; }}
    .question-list {{ margin: 0; padding-left: 18px; color: #334155; line-height: 1.5; }}
    .scroll {{ overflow-x: auto; }}
    .link-grid {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .status-note {{ border-left: 4px solid var(--amber); background: #fff7ed; padding: 12px; border-radius: 6px; color: #7c2d12; }}
    @media (max-width: 1120px) {{ .metric-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }} .grid-2, .grid-3 {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 700px) {{ main {{ padding: 16px; }} .topline {{ display: block; }} .nav {{ justify-content: flex-start; margin-top: 12px; }} .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">CSM / consulting delivery</div>
      <h1>Transactional Intelligence Client Story</h1>
      <p class="subtle">A CSM-facing run-of-show: what to say, what proof to show, what caveats to carry, which exports to hand off, and how the next measurement loop closes.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_launchpad.html")}">Launchpad</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Analysis dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Section drilldowns</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
    </nav>
  </div>

  <section class="story-hero">
    <div class="hero-title">{escape(_clean_cell(story.get("headline")) or "Transactional Intelligence Story")}</div>
    <p>{escape(_clean_cell(story.get("executive_summary")) or "No executive summary generated.")}</p>
  </section>

  <section class="metric-grid">{metric_html}</section>

  <section class="grid-2">
    <div class="panel">
      <h2>Client Conversation Guide</h2>
      {_story_card_list(conversation)}
    </div>
    <div class="panel">
      <h2>Decision Questions</h2>
      {_question_list(questions)}
    </div>
  </section>

  <section class="panel">
    <h2>Story Arc</h2>
    <p class="subtle">These are the proof-backed steps for the client conversation.</p>
    {_story_arc_cards(story_arc, july_dir)}
  </section>

  <section class="grid-2">
    <section class="panel">
      <h2>Top Plays And Talk Track</h2>
      <div class="scroll">{_df_table(action_plan, ["priority_rank", "play_name", "objective", "target_accounts", "expected_value", "confidence", "owner_role", "recommended_channel", "next_step", "talk_track"], 8)}</div>
    </section>
    <section class="panel">
      <h2>Executive Scorecard And Roadmap</h2>
      <div class="scroll">{_df_table(scorecard, ["domain", "score", "rag_status", "evidence_summary", "recommended_focus"], 10)}</div>
      <div class="scroll" style="margin-top:12px;">{_df_table(roadmap, ["phase", "initiative", "owner_role", "proof_metric", "source_artifacts"], 8)}</div>
    </section>
  </section>

  <section class="panel">
    <h2>Meeting Run Of Show</h2>
    <p class="subtle">Use this as the deck or meeting sequence: message, decision prompt, source artifact, chart type, caveat, and follow-up action.</p>
    <div class="scroll">{_df_table(meeting_blueprint, ["blueprint_rank", "meeting_phase", "slide_type", "slide_title", "primary_message", "decision_prompt", "source_artifact", "visual_title", "data_caveat", "follow_up_action", "blueprint_status"], 36)}</div>
  </section>

  <section class="grid-2">
    <section class="panel">
      <h2>Proof And Caveats</h2>
      <p class="subtle">What can be said externally, and what needs qualification before the meeting.</p>
      <div class="scroll">{_df_table(insight_brief, ["source_section_id", "display_name", "brief_status", "headline_insight", "primary_evidence", "data_caveat", "recommended_client_question"], 18)}</div>
      <div class="status-note" style="margin-top:12px;">Open caveats should be stated as analysis qualifications, not hidden. The proof artifacts are linked in the CSVs and section drilldowns.</div>
    </section>
    <section class="panel">
      <h2>Open Delivery Risks</h2>
      <div class="scroll">{_df_table(delivery_backlog, ["backlog_rank", "priority_band", "workstream", "owner_role", "problem_statement", "required_action", "client_use_status"], 20)}</div>
    </section>
  </section>

  <section class="grid-3">
    <section class="panel">
      <h2>CSM Review Queue</h2>
      <div class="scroll">{_df_table(csm_queue, ["review_rank", "account_id", "relationship_segment", "pfi_verdict", "top_play_name", "top_priority_score", "recommended_action", "evidence_summary"], 12)}</div>
    </section>
    <section class="panel">
      <h2>Activation Exports</h2>
      <div class="scroll">{_df_table(stakeholder_exports, ["artifact_name", "file_name", "primary_role", "row_count", "use_case", "first_action", "status"], 8)}</div>
      <div class="scroll" style="margin-top:12px;">{_df_table(marketing_export, ["account_id", "play_name", "measurement_group", "target_status", "recommended_channel", "priority_score", "reason_codes", "primary_metric"], 12)}</div>
    </section>
    <section class="panel">
      <h2>Banker Call List</h2>
      <div class="scroll">{_df_table(banker_list, ["call_rank", "account_id", "branch", "relationship_segment", "top_play_name", "recommended_action", "talk_track", "top_counterparties"], 12)}</div>
    </section>
  </section>

  <section class="grid-2">
    <section class="panel">
      <h2>Measurement Plan</h2>
      <div class="scroll">{_df_table(measurement_plan, ["measurement_id", "play_name", "opportunity_type", "primary_metric", "measurement_window", "test_group_definition", "success_definition"], 12)}</div>
    </section>
    <section class="panel">
      <h2>Outcome Readout</h2>
      <div class="scroll">{_df_table(outcome_summary, ["play_name", "target_accounts", "test_outcome_accounts", "test_outcome_rate", "lift_vs_holdout", "measurement_status", "interpretation"], 12)}</div>
    </section>
  </section>

  <section class="panel">
    <h2>Role Handoffs And Direct Files</h2>
    <div class="grid-2">
      <div class="scroll">{_df_table(role_handoffs, ["role", "decision_owned", "outputs_used", "export_artifact", "first_action", "handoff_to", "success_metric", "status"], 12)}</div>
      <div>{direct_links}</div>
    </div>
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_client_story.html").write_text(html, encoding="utf-8")


def _write_intake_cockpit_html(
    package_root: Path,
    raw_dir: Path,
    july_dir: Path,
    july_outputs: Any,
) -> None:
    file_ledger = july_outputs.file_ledger.copy()
    intake_work_order = july_outputs.intake_work_order.copy()
    assembly_plan = july_outputs.file_assembly_plan.copy()
    monthly_requirements = july_outputs.monthly_file_requirements.copy()
    layout_gaps = july_outputs.layout_gap_report.copy()
    source_layout = july_outputs.source_layout_profile.copy()
    contract_drafts = july_outputs.layout_contract_draft_queue.copy()
    contract_exports = july_outputs.layout_contract_export_manifest.copy()
    load_plan = july_outputs.data_team_load_plan.copy()
    backlog = july_outputs.production_readiness_backlog.copy()

    raw_file_count = len([path for path in raw_dir.glob("*") if path.is_file()])
    selected_load_count = _truthy_count(assembly_plan.get("load_flag", pd.Series(dtype=object)))
    expected_family_count = len(monthly_requirements)
    selected_family_count = _count_equals(monthly_requirements, "monthly_status", "selected_for_load")
    layout_review_count = expected_family_count - selected_family_count
    missing_field_count = _numeric_sum(monthly_requirements, "missing_required_field_count")
    contract_export_count = len(contract_exports)
    intake_backlog = _intake_backlog(backlog)
    snowflake_targets = _unique_pipe_values(monthly_requirements.get("target_snowflake_layer", pd.Series(dtype=object)))
    snowflake_targets.extend(_unique_pipe_values(load_plan.get("target_snowflake_layer", pd.Series(dtype=object))))
    snowflake_target_count = len(dict.fromkeys(snowflake_targets))

    direct_links = _intake_direct_links(
        [
            ("Snowflake readme", july_dir / "README_SNOWFLAKE.html"),
            ("Snowflake manifest", july_dir / "snowflake_manifest.json"),
            ("Snowflake load SQL", july_dir / "snowflake_load.sql"),
            ("Monthly requirements CSV", july_dir / "monthly_file_requirements.csv"),
            ("File assembly plan CSV", july_dir / "file_assembly_plan.csv"),
            ("Data team load plan CSV", july_dir / "data_team_load_plan.csv"),
            ("Layout gap report CSV", july_dir / "layout_gap_report.csv"),
            ("Source layout profile CSV", july_dir / "source_layout_profile.csv"),
            ("Contract draft queue CSV", july_dir / "layout_contract_draft_queue.csv"),
            ("Contract export manifest CSV", july_dir / "layout_contract_export_manifest.csv"),
            ("Production backlog CSV", july_dir / "production_readiness_backlog.csv"),
        ]
    )
    raw_input_links = _intake_direct_links([(path.name, path) for path in sorted(raw_dir.glob("*")) if path.is_file()])
    monthly_status = _count_table(monthly_requirements, "monthly_status", "input_family_count")
    load_readiness = _count_table(load_plan, "load_readiness", "file_count")
    contract_actions = _count_table(contract_drafts, "contract_action", "draft_count")
    gap_summary = _layout_gap_summary(layout_gaps)
    source_summary = _count_table(source_layout, "canonical_mapping_status", "source_column_count")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monthly Client File Intake Cockpit</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #64748b;
      --line: #d8dee8;
      --panel: #ffffff;
      --wash: #f5f7fb;
      --blue: #155eef;
      --green: #047857;
      --amber: #b45309;
      --red: #b42318;
      --teal: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--wash); }}
    main {{ max-width: 1360px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 30px; line-height: 1.12; }}
    h2 {{ margin: 0 0 10px; font-size: 18px; }}
    h3 {{ margin: 0 0 8px; font-size: 15px; }}
    p {{ margin: 0; line-height: 1.45; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef2f7; border: 1px solid var(--line); border-radius: 4px; padding: 2px 5px; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ border-bottom: 1px solid #e7ebf2; padding: 8px 9px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background: #eef3f8; color: #344054; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .topline {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--muted); text-transform: uppercase; letter-spacing: .08em; font-size: 12px; margin-bottom: 6px; }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .nav {{ display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; max-width: 780px; }}
    .nav a, .link-grid a {{ border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 7px 9px; font-size: 13px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px; margin: 16px 0; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 78px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 8px; }}
    .process {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; margin: 14px 0 0; }}
    .step {{ border: 1px solid var(--line); background: #fbfcfe; border-radius: 8px; padding: 11px; min-height: 92px; }}
    .step b {{ display: block; font-size: 13px; margin-bottom: 5px; }}
    .step span {{ color: var(--muted); font-size: 12px; line-height: 1.35; }}
    .grid-2 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; align-items: start; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; align-items: start; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin-top: 16px; }}
    .role-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .role-card b {{ display: block; margin-bottom: 6px; }}
    .link-grid {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .scroll {{ overflow-x: auto; }}
    .bar-row {{ display: grid; grid-template-columns: 180px minmax(100px, 1fr) 70px; gap: 9px; align-items: center; min-height: 26px; margin: 7px 0; }}
    .bar-label {{ overflow-wrap: anywhere; font-size: 12px; }}
    .bar-track {{ height: 14px; border: 1px solid #d5dbe5; background: #f2f4f7; border-radius: 3px; overflow: hidden; }}
    .bar-fill {{ display: block; height: 100%; background: var(--blue); }}
    .bar-fill.green {{ background: var(--green); }}
    .bar-fill.amber {{ background: var(--amber); }}
    .bar-fill.teal {{ background: var(--teal); }}
    .bar-value {{ color: var(--muted); font-size: 12px; text-align: right; }}
    @media (max-width: 1120px) {{
      .metric-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
      .process {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 700px) {{
      main {{ padding: 16px; }}
      .topline {{ display: block; }}
      .nav {{ justify-content: flex-start; margin-top: 12px; }}
      .metric-grid, .process {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .bar-row {{ grid-template-columns: 1fr; gap: 4px; }}
      .bar-value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Monthly intake / Snowflake readiness</div>
      <h1>Monthly Client File Intake Cockpit</h1>
      <p class="subtle">Use this when a client sends monthly files with no API: confirm what arrived, decide what loads, identify modified/fallback extracts, promote layout contracts, and clear the Snowflake work queue.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_launchpad.html")}">Launchpad</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Analysis dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(july_dir / "README_SNOWFLAKE.html")}">Snowflake readme</a>
      <a href="{_file_url(july_dir / "snowflake_load.sql")}">Load SQL</a>
      <a href="{_file_url(july_dir / "production_readiness_backlog.csv")}">Backlog CSV</a>
    </nav>
  </div>

  <section class="metric-grid" aria-label="Intake metrics">
    {_metric("Raw files received", raw_file_count)}
    {_metric("Files selected to load", selected_load_count)}
    {_metric("Expected file families", expected_family_count)}
    {_metric("Families selected", selected_family_count)}
    {_metric("Layout review families", layout_review_count)}
    {_metric("Missing required fields", missing_field_count)}
    {_metric("Contract exports", contract_export_count)}
    {_metric("Snowflake targets", snowflake_target_count)}
  </section>

  <section class="panel">
    <h2>Operational Intake Process</h2>
    <div class="process">
      <div class="step"><b>1. Receive</b><span>Client sends monthly account, transaction, and support files.</span></div>
      <div class="step"><b>2. Profile</b><span>Detect delimiter, headers, row counts, source family, and contract match.</span></div>
      <div class="step"><b>3. Decide</b><span>Use, hold, review candidate layout, or ask for a replacement extract.</span></div>
      <div class="step"><b>4. Assemble</b><span>Select account and transaction inputs for the engine run.</span></div>
      <div class="step"><b>5. Contract</b><span>Promote existing contracts or create/edit client-specific YAML drafts.</span></div>
      <div class="step"><b>6. Load</b><span>Stage selected files and generated outputs to Snowflake targets.</span></div>
      <div class="step"><b>7. Clear</b><span>Resolve intake, mapping, metric, and client-use blockers from the backlog.</span></div>
    </div>
  </section>

  <section class="grid-3">
    <div class="role-card"><b>CSM</b><p class="subtle">Confirm which files the client sent, request missing layouts, and document whether fallback extracts such as modified ODD can be used.</p></div>
    <div class="role-card"><b>Analyst</b><p class="subtle">Review candidate layouts, unresolved fields, and whether analysis caveats must be attached before client-facing use.</p></div>
    <div class="role-card"><b>Data / Snowflake</b><p class="subtle">Promote contracts, load selected files, validate row counts, and clear target-table blockers before production use.</p></div>
  </section>

  <section class="panel">
    <h2>Direct Files</h2>
    <p class="subtle">Open these when operating the monthly file drop or handing work to the data team.</p>
    {direct_links}
    <h3 style="margin-top:16px;">Raw Inputs</h3>
    {raw_input_links}
  </section>

  <section class="grid-2">
    <section class="panel">
      <h2>Monthly Requirement Status</h2>
      {_intake_bar_chart(monthly_status, "monthly_status", "input_family_count", "green")}
      <div class="scroll" style="margin-top:12px;">{_df_table(monthly_requirements, ["input_family", "display_name", "requirement_level", "monthly_status", "received_file_count", "selected_file_count", "missing_required_field_count", "target_snowflake_layer", "data_team_action", "analyst_question"], 12)}</div>
    </section>
    <section class="panel">
      <h2>Snowflake Load Readiness</h2>
      {_intake_bar_chart(load_readiness, "load_readiness", "file_count", "teal")}
      <div class="scroll" style="margin-top:12px;">{_df_table(load_plan, ["load_rank", "file_name", "source_family", "contract_id", "assembly_role", "load_flag", "target_engine_input", "target_snowflake_layer", "load_readiness", "operator_action"], 12)}</div>
    </section>
  </section>

  <section class="panel">
    <h2>Received Files And Assembly Decisions</h2>
    <div class="grid-2">
      <div>
        <h3>Intake Work Order</h3>
        <div class="scroll">{_df_table(intake_work_order, ["priority_rank", "file_name", "source_family", "contract_id", "match_status", "match_score", "intake_decision", "severity", "assigned_role", "operator_action", "missing_required_fields"], 20)}</div>
      </div>
      <div>
        <h3>File Assembly Plan</h3>
        <div class="scroll">{_df_table(assembly_plan, ["file_name", "source_family", "contract_id", "match_status", "intake_decision", "assembly_role", "load_flag", "target_engine_input", "target_snowflake_layer", "operator_action"], 20)}</div>
      </div>
    </div>
  </section>

  <section class="grid-2">
    <section class="panel">
      <h2>Layout Gap Summary</h2>
      {_intake_bar_chart(gap_summary, "mapping_status", "field_count", "amber")}
      <div class="scroll" style="margin-top:12px;">{_df_table(layout_gaps, ["file_name", "source_family", "contract_id", "canonical_field", "required_flag", "mapping_status", "suggested_source_column", "confidence", "remediation_action"], 30)}</div>
    </section>
    <section class="panel">
      <h2>Source Layout Profile</h2>
      {_intake_bar_chart(source_summary, "canonical_mapping_status", "source_column_count", "teal")}
      <div class="scroll" style="margin-top:12px;">{_df_table(source_layout, ["file_name", "source_column", "source_position", "matched_canonical_fields", "canonical_mapping_status", "proposed_input_family", "proposed_contract_id", "mapping_action"], 30)}</div>
    </section>
  </section>

  <section class="grid-2">
    <section class="panel">
      <h2>Layout Contract Draft Queue</h2>
      {_intake_bar_chart(contract_actions, "contract_action", "draft_count", "amber")}
      <div class="scroll" style="margin-top:12px;">{_df_table(contract_drafts, ["draft_rank", "file_name", "priority_band", "contract_action", "current_contract_id", "proposed_contract_id", "missing_required_fields", "matched_canonical_fields", "data_team_action", "analyst_question"], 30)}</div>
    </section>
    <section class="panel">
      <h2>Contract Export Manifest</h2>
      <p class="subtle">YAML files listed here are ready for data-team review and promotion.</p>
      <div class="scroll" style="margin-top:12px;">{_df_table(contract_exports, ["export_rank", "file_name", "priority_band", "proposed_contract_id", "yaml_relative_path", "yaml_ready", "target_snowflake_layer", "data_team_action", "analyst_question"], 30)}</div>
    </section>
  </section>

  <section class="panel">
    <h2>Intake And Snowflake Production Backlog</h2>
    <p class="subtle">Filtered to Monthly intake and Data contracts / Snowflake workstreams from the generated productization backlog.</p>
    <div class="scroll">{_df_table(intake_backlog, ["backlog_rank", "priority_band", "workstream", "readiness_area", "owner_role", "problem_statement", "required_action", "acceptance_criteria", "affected_sections", "affected_outputs", "snowflake_targets", "client_use_status"], 60)}</div>
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_intake_cockpit.html").write_text(html, encoding="utf-8")


def _write_actuals_html(
    package_root: Path,
    raw_dir: Path,
    june_dir: Path,
    july_dir: Path,
    june_outputs: Any,
    july_outputs: Any,
) -> None:
    artifact_rows = _artifact_rows(june_dir, july_dir)
    functions = _function_rows()
    sections = _analysis_section_counts()
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Actual Analysis</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #14213d; background: #f6f7f9; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 32px 0 12px; font-size: 20px; }}
    h3 {{ margin: 20px 0 8px; font-size: 15px; }}
    p {{ line-height: 1.45; }}
    code {{ background: #eef1f5; padding: 2px 5px; border-radius: 4px; }}
    a {{ color: #155eef; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .panel {{ background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 18px; margin: 16px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .metric {{ background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #5f6b7a; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9dee8; border-radius: 8px; overflow: hidden; }}
    th, td {{ border-bottom: 1px solid #e6e9ef; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #edf2f8; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #344054; }}
    tr:last-child td {{ border-bottom: 0; }}
    .flow {{ display: grid; grid-template-columns: repeat(7, minmax(100px, 1fr)); gap: 8px; align-items: stretch; }}
    .step {{ background: #fff; border: 1px solid #cfd7e3; border-radius: 8px; padding: 12px; min-height: 76px; }}
    .step b {{ display: block; font-size: 13px; margin-bottom: 6px; }}
    .step small {{ color: #5f6b7a; line-height: 1.35; }}
    .sample {{ overflow-x: auto; margin-bottom: 18px; }}
    .small {{ color: #5f6b7a; font-size: 13px; }}
    @media (max-width: 900px) {{ .grid, .flow {{ grid-template-columns: 1fr 1fr; }} main {{ padding: 18px; }} }}
    @media (max-width: 560px) {{ .grid, .flow {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Transactional Intelligence Actual Analysis</h1>
  <p class="small">Synthetic client {CLIENT_ID}. This page points to the real scripts and the generated analysis outputs.</p>
  <p class="small">
    <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Open the visual analysis dashboard</a> |
    <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Open the client story</a> |
    <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Open the intake cockpit</a> |
    <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Open section drilldowns</a> |
    <a href="{_file_url(package_root / "transactional_intelligence_lineage_map.html")}">Open the lineage map</a>
  </p>

  <section class="grid">
    <div class="metric"><span>June opportunity rows</span><strong>{len(june_outputs.opportunities)}</strong></div>
    <div class="metric"><span>June campaign target rows</span><strong>{len(june_outputs.campaign_targets)}</strong></div>
    <div class="metric"><span>July outcome rows</span><strong>{len(july_outputs.outcome_results)}</strong></div>
    <div class="metric"><span>July quality score</span><strong>{escape(str(july_outputs.data_quality.get("quality_score")))}</strong></div>
  </section>

  <h2>Analysis Flow</h2>
  <section class="flow">
    <div class="step"><b>1. Raw files</b><small>ODD/account CSV and monthly transaction CSV.</small></div>
    <div class="step"><b>2. Intake</b><small>Profile layouts, match contracts, create work order.</small></div>
    <div class="step"><b>3. Features</b><small>Build account-month behavior, balance, payroll, external FI, merchant features.</small></div>
    <div class="step"><b>4. Intelligence</b><small>PFI verdicts, counterparties, segments, opportunities.</small></div>
    <div class="step"><b>5. Strategy</b><small>Portfolio plays, scorecard, roadmap, action plan.</small></div>
    <div class="step"><b>6. Activation</b><small>Campaign target list and measurement baseline.</small></div>
    <div class="step"><b>7. Outcomes</b><small>Next-period account behavior is compared to prior targets.</small></div>
  </section>

  <h2>Raw Inputs</h2>
  {_raw_inputs_table(raw_dir)}

  <h2>Actual Analysis Functions</h2>
  {_functions_table(functions)}

  <h2>Generated Output Files</h2>
  {_artifact_table(artifact_rows)}

  <h2>Analysis Evidence Review</h2>
  <p class="small">This section is generated from the actual analysis maps and field coverage outputs. It shows which sections are supported now, which need validation, and which are blocked by layout mapping.</p>
  <h3>Section Evidence Review</h3>
  <div class="sample">{_df_table(july_outputs.analysis_section_evidence_review, ["source_section_id", "domain_name", "display_name", "section_review_status", "evidence_status", "mapped_field_count", "review_field_count", "blocker_field_count", "analysis_summary", "analyst_next_step", "data_team_next_step"], 30)}</div>
  <h3>Analysis Consulting Playbook</h3>
  <div class="sample">{_df_table(july_outputs.analysis_consulting_playbook, ["source_section_id", "domain_name", "client_story_role", "primary_output_file", "primary_chart_type", "stakeholder_owner", "csm_talk_track", "analyst_validation_focus", "data_team_dependency"], 30)}</div>
  <h3>Analysis Insight Brief</h3>
  <div class="sample">{_df_table(july_outputs.analysis_insight_brief, ["source_section_id", "domain_name", "brief_status", "headline_insight", "primary_evidence", "data_caveat", "recommended_client_question"], 30)}</div>
  <h3>Client Meeting Deck Blueprint</h3>
  <div class="sample">{_df_table(july_outputs.client_meeting_deck_blueprint, ["blueprint_rank", "meeting_phase", "slide_type", "slide_title", "decision_prompt", "blueprint_status", "source_artifact"], 42)}</div>
  <h3>Analysis Review Board</h3>
  <div class="sample">{_df_table(july_outputs.analysis_review_board, ["source_section_id", "display_name", "what_is_analyzed", "chart_count", "primary_chart_type", "metric_count", "headline_insight", "recommended_client_question", "meeting_phase_refs", "review_status"], 30)}</div>
  <h3>Intelligence Metric Catalog</h3>
  <div class="sample">{_df_table(july_outputs.intelligence_metric_catalog, ["metric_id", "metric_family", "source_artifact", "source_field", "field_role", "chart_usage_count", "validation_status", "csm_interpretation"], 36)}</div>
  <h3>Analysis Chart Data Snapshots</h3>
  <div class="sample">{_df_table(july_outputs.analysis_chart_data_snapshot, ["source_section_id", "chart_title", "chart_type", "data_artifact", "plotted_row_count", "source_row_count", "data_status", "top_label", "top_value", "insight_callout"], 30)}</div>
  <h3>Field/Layout Coverage Blockers</h3>
  <div class="sample">{_df_table(july_outputs.analysis_layout_coverage_matrix[july_outputs.analysis_layout_coverage_matrix["coverage_severity"].eq("blocker")], ["source_section_id", "input_family_hint", "field_key", "reference_count", "coverage_status", "analyst_action", "data_team_action"], 24)}</div>
  <h3>Analysis Requirement Matrix</h3>
  <div class="sample">{_df_table(july_outputs.analysis_requirement_matrix, ["source_section_id", "domain_name", "required_input_families", "current_layout_readiness", "layout_blockers", "generated_output_files", "snowflake_design_action"], 30)}</div>

  <h2>Sample Output Rows</h2>
  <h3>June Opportunity Portfolio</h3>
  <div class="sample">{_df_table(june_outputs.opportunity_portfolio, ["priority_rank", "play_name", "target_accounts", "expected_value", "confidence", "next_step"], 10)}</div>
  <h3>June Counterparty Summary</h3>
  <div class="sample">{_df_table(june_outputs.counterparty_summary, ["counterparty_name", "counterparty_category", "direction", "account_count", "total_amount", "top_relationship_signal", "strategy_relevance"], 12)}</div>
  <h3>File Assembly Plan</h3>
  <div class="sample">{_df_table(june_outputs.file_assembly_plan, ["file_name", "source_family", "intake_decision", "assembly_role", "load_flag", "assembly_reason"], 12)}</div>
  <h3>Monthly File Requirements</h3>
  <div class="sample">{_df_table(june_outputs.monthly_file_requirements, ["input_family", "display_name", "requirement_level", "monthly_status", "received_file_names", "selected_file_names", "target_snowflake_layer", "data_team_action"], 12)}</div>
  <h3>Layout Gap Report</h3>
  <div class="sample">{_df_table(june_outputs.layout_gap_report, ["file_name", "contract_id", "canonical_field", "mapping_status", "suggested_source_column", "remediation_action"], 18)}</div>
  <h3>Layout Contract Draft Queue</h3>
  <div class="sample">{_df_table(june_outputs.layout_contract_draft_queue, ["draft_rank", "file_name", "priority_band", "contract_action", "proposed_contract_id", "missing_required_fields", "data_team_action"], 12)}</div>
  <h3>Layout Contract Exports</h3>
  <div class="sample">{_df_table(june_outputs.layout_contract_export_manifest, ["export_rank", "file_name", "priority_band", "proposed_contract_id", "yaml_relative_path", "target_snowflake_layer", "data_team_action"], 12)}</div>
  <h3>Intelligence Lineage Graph</h3>
  <div class="sample">{_df_table(july_outputs.intelligence_lineage_graph, ["lineage_stage", "source_node_type", "source_label", "relationship", "target_node_type", "target_label", "edge_status", "owner_role", "next_action"], 30)}</div>
  <h3>Engine Run Ledger</h3>
  <div class="sample">{_df_table(june_outputs.engine_run_ledger, ["ledger_rank", "run_stage", "owner_role", "status", "metric_name", "metric_value", "operator_action"], 12)}</div>
  <h3>Analysis Package Index</h3>
  <div class="sample">{_df_table(june_outputs.analysis_package_index, ["artifact_name", "analysis_layer", "primary_consumer", "row_count", "target_table", "purpose"], 18)}</div>
  <h3>Account Intelligence Profile</h3>
  <div class="sample">{_df_table(june_outputs.account_intelligence_profile, ["account_id", "relationship_segment", "pfi_verdict", "top_play_name", "top_counterparties", "recommended_action", "evidence_summary"], 12)}</div>
  <h3>Model Rulebook</h3>
  <div class="sample">{_df_table(june_outputs.model_rulebook, ["rule_id", "rule_family", "rule_name", "condition", "thresholds", "outputs"], 18)}</div>
  <h3>Account Scoring Trace</h3>
  <div class="sample">{_df_table(june_outputs.account_scoring_trace, ["account_id", "pfi_verdict", "relationship_segment", "top_opportunity_type", "top_priority_score", "decision_trace"], 12)}</div>
  <h3>Operating Control Plane</h3>
  <div class="sample">{_df_table(june_outputs.operating_control_plane, ["workflow_lane", "role", "operating_question", "client_use_status", "open_first", "blocker_summary", "next_action"], 12)}</div>
  <h3>User Interaction Map</h3>
  <div class="sample">{_df_table(june_outputs.user_interaction_map, ["user_role", "workflow_lane", "primary_screen", "file_name", "decision_supported", "owner_next_action", "delivery_mode", "client_use_status"], 24)}</div>
  <h3>Production Readiness Backlog</h3>
  <div class="sample">{_df_table(july_outputs.production_readiness_backlog, ["backlog_rank", "priority_band", "workstream", "owner_role", "problem_statement", "required_action", "affected_outputs", "client_use_status"], 30)}</div>
  <h3>Stakeholder Export Manifest</h3>
  <div class="sample">{_df_table(june_outputs.stakeholder_export_manifest, ["artifact_name", "primary_role", "row_count", "use_case", "first_action", "status"], 12)}</div>
  <h3>CSM Review Queue</h3>
  <div class="sample">{_df_table(june_outputs.csm_review_queue, ["review_rank", "account_id", "relationship_segment", "top_play_name", "top_priority_score", "recommended_action"], 12)}</div>
  <h3>Consulting Insight Register</h3>
  <div class="sample">{_df_table(june_outputs.consulting_insight_register, ["insight_id", "insight_type", "domain", "finding", "evidence_status", "recommended_action", "next_decision"], 16)}</div>
  <h3>June Campaign Targets</h3>
  <div class="sample">{_df_table(june_outputs.campaign_targets, ["play_name", "account_id", "priority_score", "expected_value", "measurement_group", "target_status", "reason_codes"], 12)}</div>
  <h3>July Outcome Summary</h3>
  <div class="sample">{_df_table(july_outputs.outcome_summary, ["play_name", "target_accounts", "test_outcome_accounts", "test_outcome_rate", "avg_delta_txn_count", "avg_delta_external_fi_amount", "interpretation"], 10)}</div>
  <h3>July Intelligence Delta Report</h3>
  <div class="sample">{_df_table(july_outputs.intelligence_delta_report, ["delta_type", "entity_type", "account_id", "opportunity_type", "metric_name", "movement_direction", "evidence_summary"], 16)}</div>
  <h3>Analysis Section Catalog</h3>
  <div class="sample">{_df_table(june_outputs.analysis_section_catalog, ["source_section_id", "display_name", "script_count", "analysis_family", "intelligence_layers", "supports_opportunity_types"], 14)}</div>
  <h3>Opportunity Provenance Map</h3>
  <div class="sample">{_df_table(june_outputs.analysis_provenance_map, ["opportunity_type", "source_section_id", "display_name", "analysis_family", "script_count", "contribution"], 14)}</div>
  <h3>Analysis Execution Map</h3>
  <div class="sample">{_df_table(june_outputs.analysis_execution_map, ["source_section_id", "analysis_family", "primary_engine_outputs", "available_engine_outputs", "evidence_status", "analyst_next_step"], 16)}</div>
  <h3>July Consulting Story</h3>
  <div class="sample">{_story_block(july_outputs.consulting_story)}</div>

  <h2>Existing Analysis Section Inventory</h2>
  {_sections_table(sections)}
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_actuals.html").write_text(html, encoding="utf-8")


def _write_analysis_dashboard_html(
    package_root: Path,
    raw_dir: Path,
    june_dir: Path,
    july_dir: Path,
    june_outputs: Any,
    july_outputs: Any,
) -> None:
    domain_rows = _analysis_domain_rows(
        july_outputs.analysis_domain_map,
        july_outputs.analysis_section_evidence_review,
    )
    metrics = {
        "raw_files": len(list(raw_dir.glob("*.csv"))),
        "domains": len(domain_rows),
        "sections": len(july_outputs.analysis_section_evidence_review),
        "field_checks": len(july_outputs.analysis_layout_coverage_matrix),
        "artifacts": len(july_outputs.analysis_package_index),
        "opportunities": len(july_outputs.opportunity_portfolio),
        "counterparties": len(july_outputs.counterparty_summary),
        "outcomes": len(july_outputs.outcome_summary),
    }
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Analysis Dashboard</title>
  <style>
    :root {{
      --ink: #101828;
      --muted: #667085;
      --line: #d8dee8;
      --panel: #ffffff;
      --wash: #f5f7fb;
      --blue: #155eef;
      --teal: #0f766e;
      --green: #047857;
      --amber: #b45309;
      --red: #c2410c;
      --violet: #6d28d9;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--wash); }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 28px; line-height: 1.15; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; }}
    p {{ margin: 0; line-height: 1.45; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef2f7; border: 1px solid #d8dee8; border-radius: 4px; padding: 2px 5px; white-space: nowrap; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ border-bottom: 1px solid #e7ebf2; padding: 8px 9px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background: #eef3f8; color: #344054; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .nav {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; font-size: 13px; }}
    .nav a {{ border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 7px 9px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px; margin: 16px 0 18px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 82px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 8px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .stack {{ display: grid; gap: 14px; }}
    .dashboard-grid {{ display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr); gap: 16px; align-items: start; }}
    .chart-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 16px; }}
    .flow-map {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }}
    .flow-node {{ min-height: 88px; border: 1px solid var(--line); background: #fbfcfe; border-radius: 8px; padding: 12px; position: relative; }}
    .flow-node b {{ display: block; font-size: 13px; margin-bottom: 6px; }}
    .flow-node small {{ display: block; color: var(--muted); font-size: 12px; line-height: 1.35; }}
    .flow-node:not(:last-child)::after {{ content: "->"; position: absolute; right: -9px; top: 34px; color: var(--muted); font-size: 13px; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 8px 0 4px; color: var(--muted); font-size: 12px; }}
    .legend span::before {{ content: ""; display: inline-block; width: 10px; height: 10px; margin-right: 6px; border-radius: 2px; vertical-align: -1px; background: var(--blue); }}
    .legend .mapped::before {{ background: var(--green); }}
    .legend .review::before {{ background: var(--amber); }}
    .legend .blocked::before {{ background: var(--red); }}
    .legend .ready::before {{ background: var(--green); }}
    .legend .validate::before {{ background: var(--amber); }}
    .bar-row {{ display: grid; grid-template-columns: 178px minmax(90px, 1fr) 86px; gap: 10px; align-items: center; min-height: 28px; margin: 8px 0; }}
    .bar-label {{ font-size: 12px; overflow-wrap: anywhere; }}
    .bar-value {{ color: var(--muted); font-size: 12px; text-align: right; }}
    .bar-track {{ height: 16px; border: 1px solid #d5dbe5; background: #f2f4f7; border-radius: 3px; overflow: hidden; display: flex; }}
    .bar-fill {{ display: block; min-width: 0; height: 100%; background: var(--blue); }}
    .bar-fill.teal {{ background: var(--teal); }}
    .bar-fill.violet {{ background: var(--violet); }}
    .seg.mapped {{ background: var(--green); }}
    .seg.review {{ background: var(--amber); }}
    .seg.blocked {{ background: var(--red); }}
    .seg.ready {{ background: var(--green); }}
    .seg.validate {{ background: var(--amber); }}
    .domain-list {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
    .domain-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .domain-card header {{ display: flex; justify-content: space-between; gap: 8px; align-items: flex-start; margin-bottom: 8px; }}
    .domain-card h3 {{ font-size: 15px; margin: 0; }}
    .status {{ display: inline-block; border-radius: 999px; padding: 3px 7px; font-size: 11px; background: #eef2f7; color: #344054; white-space: nowrap; }}
    .status.blocked {{ background: #fff1f0; color: var(--red); }}
    .status.validate {{ background: #fff7ed; color: var(--amber); }}
    .status.ready {{ background: #ecfdf3; color: var(--green); }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }}
    .chip-row a, .chip-row span {{ border: 1px solid var(--line); border-radius: 5px; padding: 4px 6px; background: #fbfcfe; font-size: 11px; color: #344054; }}
    details {{ margin-top: 10px; }}
    summary {{ cursor: pointer; color: var(--blue); font-size: 12px; }}
    .scroll {{ overflow-x: auto; }}
    .section-table td:nth-child(6), .section-table td:nth-child(7) {{ min-width: 210px; }}
    @media (max-width: 1100px) {{
      .metric-grid {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
      .dashboard-grid, .chart-grid, .domain-list {{ grid-template-columns: 1fr; }}
      .flow-map {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .flow-node::after {{ display: none; }}
    }}
    @media (max-width: 620px) {{
      main {{ padding: 16px; }}
      .topline {{ display: block; }}
      .nav {{ justify-content: flex-start; margin-top: 12px; }}
      .metric-grid, .flow-map {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .bar-row {{ grid-template-columns: 1fr; gap: 4px; }}
      .bar-value {{ text-align: left; }}
    }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Synthetic client {CLIENT_ID} / July measurement run</div>
      <h1>Transactional Intelligence Analysis Dashboard</h1>
      <p class="subtle">Visual map of what the repo analyzes, what data is required, what charts are produced, and where field/layout blockers remain.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_actuals.html")}">Actuals tables</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Section drilldowns</a>
      <a href="{_file_url(package_root / "transactional_intelligence_lineage_map.html")}">Lineage map</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(package_root / "README.html")}">Package README</a>
      <a href="{_file_url(july_dir / "analysis_section_evidence_review.csv")}">Section evidence CSV</a>
      <a href="{_file_url(july_dir / "analysis_layout_coverage_matrix.csv")}">Field coverage CSV</a>
    </nav>
  </div>

  <section class="metric-grid" aria-label="Run metrics">
    {_metric("Raw files", metrics["raw_files"])}
    {_metric("Analysis domains", metrics["domains"])}
    {_metric("Analysis sections", metrics["sections"])}
    {_metric("Field checks", metrics["field_checks"])}
    {_metric("Output artifacts", metrics["artifacts"])}
    {_metric("Portfolio plays", metrics["opportunities"])}
    {_metric("Counterparties", metrics["counterparties"])}
    {_metric("Outcome rows", metrics["outcomes"])}
  </section>

  <section class="panel">
    <h2>Overall Engine Process</h2>
    <div class="flow-map">
      <div class="flow-node"><b>1. Monthly file drop</b><small>Client sends account, transaction, and support files. Current demo has {metrics["raw_files"]} CSV files.</small></div>
      <div class="flow-node"><b>2. Layout intelligence</b><small>Profile source columns, match contracts, expose missing mappings, and create data-team actions.</small></div>
      <div class="flow-node"><b>3. Feature mart</b><small>Build account-month behavior for balances, credits, spend, payroll, external FI, and activity.</small></div>
      <div class="flow-node"><b>4. Analysis domains</b><small>Map 20+ repo sections into {metrics["domains"]} business intelligence domains and {metrics["sections"]} section reviews.</small></div>
      <div class="flow-node"><b>5. Strategy outputs</b><small>Create opportunities, scorecards, roadmap, action plan, campaign targets, and role handoffs.</small></div>
      <div class="flow-node"><b>6. Measurement loop</b><small>Compare next-period behavior to prior targets and turn results into the consulting story.</small></div>
    </div>
  </section>

  <section class="dashboard-grid" style="margin-top: 16px;">
    <div class="stack">
      <section class="panel">
        <h2>Field Coverage By Analysis Domain</h2>
        <p class="subtle">Each bar is built from actual script field references compared to current layout and contract evidence.</p>
        {_domain_field_coverage_chart(domain_rows)}
      </section>
      <section class="panel">
        <h2>Section Readiness By Domain</h2>
        <p class="subtle">This is the external-use status of each analysis section, not just whether a chart can be generated.</p>
        {_domain_section_status_chart(domain_rows)}
      </section>
    </div>
    <div class="stack">
      <section class="panel">
        <h2>Data Being Analyzed</h2>
        {_source_layout_chart(july_outputs.source_layout_profile)}
        <div class="scroll" style="margin-top:12px;">{_df_table(july_outputs.layout_contract_draft_queue, ["file_name", "priority_band", "contract_action", "proposed_contract_id", "target_snowflake_layer"], 8)}</div>
      </section>
      <section class="panel">
        <h2>Output Package Shape</h2>
        {_package_layer_chart(july_outputs.analysis_package_index)}
      </section>
    </div>
  </section>

  <section class="chart-grid">
    <section class="panel">
      <h2>Opportunity Portfolio</h2>
      {_opportunity_chart(july_outputs.opportunity_portfolio)}
    </section>
    <section class="panel">
      <h2>Top Counterparties</h2>
      {_counterparty_chart(july_outputs.counterparty_summary)}
    </section>
    <section class="panel">
      <h2>Measured Outcomes</h2>
      {_outcome_chart(july_outputs.outcome_summary)}
    </section>
    <section class="panel">
      <h2>Executive Scorecard</h2>
      {_scorecard_chart(july_outputs.executive_scorecard)}
    </section>
  </section>

  <section style="margin-top: 16px;">
    <h2>What Each Analysis Domain Is Doing</h2>
    {_domain_analysis_cards(domain_rows, july_dir)}
  </section>

  <section class="panel" style="margin-top: 16px;">
    <h2>Section Evidence Map</h2>
    <p class="subtle">One row per analysis section: the business question, external-use status, field coverage, blockers, and generated artifacts.</p>
    {_section_evidence_table(july_outputs.analysis_section_evidence_review)}
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_analysis_dashboard.html").write_text(html, encoding="utf-8")


def _write_analysis_workbench_html(
    package_root: Path,
    july_dir: Path,
    july_outputs: Any,
) -> None:
    coverage = july_outputs.analysis_layout_coverage_matrix.copy()
    sections = july_outputs.analysis_section_evidence_review.copy()
    backlog = july_outputs.analysis_data_team_backlog.copy()
    validation_queue = july_outputs.analysis_metric_validation_queue.copy()
    visual_map = july_outputs.analysis_visual_output_map.copy()
    chart_specs = july_outputs.analysis_chart_spec_catalog.copy()
    chart_snapshots = july_outputs.analysis_chart_data_snapshot.copy()
    metric_catalog = july_outputs.intelligence_metric_catalog.copy()
    playbook = july_outputs.analysis_consulting_playbook.copy()
    insight_brief = july_outputs.analysis_insight_brief.copy()
    meeting_blueprint = july_outputs.client_meeting_deck_blueprint.copy()
    analysis_board = july_outputs.analysis_review_board.copy()
    user_interaction_map = july_outputs.user_interaction_map.copy()
    production_backlog = july_outputs.production_readiness_backlog.copy()
    readiness = july_outputs.engine_readiness_assessment.copy()
    blockers = coverage[coverage["coverage_severity"].eq("blocker")].copy() if not coverage.empty else pd.DataFrame()
    derived = coverage[coverage["coverage_status"].eq("derived_engine_output_validate")].copy() if not coverage.empty else pd.DataFrame()
    review_only = coverage[coverage["coverage_severity"].eq("review")].copy() if not coverage.empty else pd.DataFrame()
    section_blockers = sections[sections["blocker_field_count"].fillna(0).gt(0)].copy() if not sections.empty else pd.DataFrame()
    metrics = {
        "blocker_fields": len(backlog) if not backlog.empty else len(blockers),
        "blocker_sections": len(section_blockers),
        "derived_fields": int(validation_queue["validation_type"].astype(str).eq("derived_output_lineage").sum()) if not validation_queue.empty else len(derived),
        "review_fields": len(validation_queue) if not validation_queue.empty else len(review_only),
        "validated_sections": int(sections["section_review_status"].astype(str).str.contains("validate").sum()) if not sections.empty else 0,
        "playbook_sections": len(playbook),
        "insight_briefs": len(insight_brief),
        "meeting_blueprint": len(meeting_blueprint),
        "analysis_board_sections": len(analysis_board),
        "user_interactions": len(user_interaction_map),
        "production_backlog": len(production_backlog),
        "semantic_metrics": len(metric_catalog),
        "chart_snapshots": len(chart_snapshots),
    }
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Analysis Workbench</title>
  <style>
    :root {{
      --ink: #101828;
      --muted: #667085;
      --line: #d8dee8;
      --panel: #ffffff;
      --wash: #f5f7fb;
      --blue: #155eef;
      --green: #047857;
      --amber: #b45309;
      --red: #c2410c;
      --purple: #6d28d9;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--wash); }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 28px; line-height: 1.15; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; }}
    h3 {{ margin: 18px 0 8px; font-size: 14px; }}
    p {{ margin: 0; line-height: 1.45; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef2f7; border: 1px solid #d8dee8; border-radius: 4px; padding: 2px 5px; white-space: nowrap; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ border-bottom: 1px solid #e7ebf2; padding: 8px 9px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background: #eef3f8; color: #344054; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .nav {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; font-size: 13px; }}
    .nav a {{ border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 7px 9px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 16px 0 18px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 82px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 8px; }}
    .layout {{ display: grid; grid-template-columns: minmax(0, .9fr) minmax(460px, 1.1fr); gap: 16px; align-items: start; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .stack {{ display: grid; gap: 16px; }}
    .scroll {{ overflow-x: auto; }}
    .bar-row {{ display: grid; grid-template-columns: 164px minmax(90px, 1fr) 76px; gap: 10px; align-items: center; min-height: 28px; margin: 8px 0; }}
    .bar-label {{ font-size: 12px; overflow-wrap: anywhere; }}
    .bar-value {{ color: var(--muted); font-size: 12px; text-align: right; }}
    .bar-track {{ height: 16px; border: 1px solid #d5dbe5; background: #f2f4f7; border-radius: 3px; overflow: hidden; }}
    .bar-fill {{ display: block; height: 100%; background: var(--blue); }}
    .red {{ background: var(--red); }}
    .amber {{ background: var(--amber); }}
    .purple {{ background: var(--purple); }}
    .decision-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
    .decision {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fbfcfe; }}
    .decision b {{ display: block; font-size: 13px; margin-bottom: 5px; }}
    .decision small {{ display: block; color: var(--muted); line-height: 1.35; }}
    @media (max-width: 1050px) {{ .layout, .decision-grid {{ grid-template-columns: 1fr; }} .metric-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
    @media (max-width: 620px) {{ main {{ padding: 16px; }} .topline {{ display: block; }} .nav {{ justify-content: flex-start; margin-top: 12px; }} .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .bar-row {{ grid-template-columns: 1fr; gap: 4px; }} .bar-value {{ text-align: left; }} }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Synthetic client {CLIENT_ID} / analysis triage</div>
      <h1>Transactional Intelligence Analysis Workbench</h1>
      <p class="subtle">Operational view of remaining field-layout blockers, derived-output validation, and section-level next actions.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Section drilldowns</a>
      <a href="{_file_url(package_root / "transactional_intelligence_lineage_map.html")}">Lineage map</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(package_root / "README.html")}">Package README</a>
      <a href="{_file_url(july_dir / "engine_readiness_assessment.csv")}">Readiness CSV</a>
      <a href="{_file_url(july_dir / "analysis_visual_output_map.csv")}">Visual map CSV</a>
      <a href="{_file_url(july_dir / "analysis_chart_spec_catalog.csv")}">Chart specs CSV</a>
      <a href="{_file_url(july_dir / "analysis_chart_data_snapshot.csv")}">Chart data CSV</a>
      <a href="{_file_url(july_dir / "intelligence_metric_catalog.csv")}">Metric catalog CSV</a>
      <a href="{_file_url(july_dir / "analysis_insight_brief.csv")}">Insight brief CSV</a>
      <a href="{_file_url(july_dir / "client_meeting_deck_blueprint.csv")}">Meeting blueprint CSV</a>
      <a href="{_file_url(july_dir / "analysis_review_board.csv")}">Review board CSV</a>
      <a href="{_file_url(july_dir / "user_interaction_map.csv")}">User interaction CSV</a>
      <a href="{_file_url(july_dir / "production_readiness_backlog.csv")}">Production backlog CSV</a>
      <a href="{_file_url(july_dir / "analysis_data_team_backlog.csv")}">Data-team backlog CSV</a>
      <a href="{_file_url(july_dir / "analysis_metric_validation_queue.csv")}">Metric validation CSV</a>
      <a href="{_file_url(july_dir / "analysis_layout_coverage_matrix.csv")}">Field coverage CSV</a>
      <a href="{_file_url(july_dir / "analysis_section_evidence_review.csv")}">Section evidence CSV</a>
      <a href="{_file_url(july_dir / "analysis_consulting_playbook.csv")}">Consulting playbook CSV</a>
    </nav>
  </div>

  <section class="metric-grid" aria-label="Triage metrics">
    {_metric("Hard blocker fields", metrics["blocker_fields"])}
    {_metric("Blocked sections", metrics["blocker_sections"])}
    {_metric("Derived fields", metrics["derived_fields"])}
    {_metric("Review fields", metrics["review_fields"])}
    {_metric("Insight briefs", metrics["insight_briefs"])}
    {_metric("Meeting rows", metrics["meeting_blueprint"])}
    {_metric("Review board", metrics["analysis_board_sections"])}
    {_metric("User map rows", metrics["user_interactions"])}
    {_metric("Backlog rows", metrics["production_backlog"])}
    {_metric("Semantic metrics", metrics["semantic_metrics"])}
    {_metric("Chart snapshots", metrics["chart_snapshots"])}
  </section>

  <section class="panel" style="margin-bottom:16px;">
    <h2>Engine Readiness Assessment</h2>
    <p class="subtle">One compact go/no-go table for whether the run is ready for consulting use, Snowflake productization, activation, or measurement.</p>
    {_workbench_readiness_table(readiness)}
  </section>

  <section class="panel" style="margin-bottom:16px;">
    <h2>User Interaction Map</h2>
    <p class="subtle">Role-by-role answer to what each person opens, what decision it supports, how the data is delivered, and what action happens next.</p>
    {_workbench_user_interaction_table(user_interaction_map)}
  </section>

  <section class="panel" style="margin-bottom:16px;">
    <h2>Production Readiness Backlog</h2>
    <p class="subtle">The concrete work queue for turning the analysis engine into a repeatable Snowflake-backed, client-facing product.</p>
    {_workbench_production_backlog_table(production_backlog)}
  </section>

  <section class="layout">
    <div class="stack">
      <section class="panel">
        <h2>Blockers By Input Family</h2>
        <p class="subtle">Reference-weighted blocker count. These are the source layouts that should be mapped first.</p>
        {_workbench_count_chart(blockers, "input_family_hint", "reference_count", "red")}
      </section>
      <section class="panel">
        <h2>Coverage Status Mix</h2>
        <p class="subtle">Shows how the engine now separates hard mapping issues from derived evidence and validation work.</p>
        {_workbench_count_chart(coverage, "coverage_status", "reference_count", "purple")}
      </section>
      <section class="panel">
        <h2>Decision Rules</h2>
        <div class="decision-grid">
          <div class="decision"><b>Map now</b><small>Fields marked <code>input_family_needs_mapping</code> or <code>client_layout_needed</code> need client/source layout work before external use.</small></div>
          <div class="decision"><b>Validate lineage</b><small><code>derived_engine_output_validate</code> means the engine produces usable evidence, but the metric definition and Snowflake lineage need approval.</small></div>
          <div class="decision"><b>Confirm aliases</b><small><code>not_in_contract_validate_alias</code> means the file may already carry the field under a local name or optional contract column.</small></div>
          <div class="decision"><b>Document rules</b><small><code>rule_based_validate_with_client</code> means the field is taxonomy or model logic rather than a literal client column.</small></div>
        </div>
      </section>
    </div>
    <div class="stack">
      <section class="panel">
        <h2>Analysis Review Board</h2>
        <p class="subtle">One row per analysis section combining what is analyzed, scripts, charts/graphs, metrics, insight, caveat, client question, and meeting-story placement.</p>
        {_workbench_analysis_review_board_table(analysis_board)}
      </section>
      <section class="panel">
        <h2>Analysis Consulting Playbook</h2>
        <p class="subtle">How each analysis section turns into a client-story role, proof chart/output, CSM talk track, analyst focus, and data-team dependency.</p>
        {_workbench_playbook_table(playbook)}
      </section>
      <section class="panel">
        <h2>Analysis Insight Brief</h2>
        <p class="subtle">One CSM/analyst-ready row per section: headline, evidence, caveat, and the next client question.</p>
        {_workbench_insight_brief_table(insight_brief)}
      </section>
      <section class="panel">
        <h2>Client Meeting Deck Blueprint</h2>
        <p class="subtle">Ordered story sequence for the client conversation: opening, scorecard, analysis proof, actions, roadmap, measurement, and handoffs.</p>
        {_workbench_meeting_blueprint_table(meeting_blueprint)}
      </section>
      <section class="panel">
        <h2>Intelligence Metric Catalog</h2>
        <p class="subtle">The semantic layer behind the analysis: metric definition, source artifact/field, field role, validation status, and CSM interpretation.</p>
        {_workbench_metric_catalog_table(metric_catalog)}
      </section>
      <section class="panel">
        <h2>Analysis Visual Output Map</h2>
        <p class="subtle">What each analysis section can show: generated artifact, chart/table/story surface, readiness, scripts, and proof artifacts.</p>
        {_workbench_visual_map_table(visual_map)}
      </section>
      <section class="panel">
        <h2>Analysis Chart Specs</h2>
        <p class="subtle">Render-ready specs showing the source artifact, chart type, x/y/series fields, owner, and readiness for chart/table/story generation.</p>
        {_workbench_chart_spec_table(chart_specs)}
      </section>
      <section class="panel">
        <h2>Chart Data Snapshots</h2>
        <p class="subtle">Machine-readable backing data behind each chart spec: plotted rows, top data point, source row count, data status, and callout.</p>
        {_workbench_chart_snapshot_table(chart_snapshots)}
      </section>
      <section class="panel">
        <h2>Priority Data-Team Backlog</h2>
        <p class="subtle">Durable output table grouped by input family and field, sorted by priority and script-reference weight.</p>
        {_workbench_backlog_output_table(backlog, blockers)}
      </section>
      <section class="panel">
        <h2>Derived Evidence Validation Queue</h2>
        <p class="subtle">Durable output table for derived, alias, direct-load, and rule-based fields that need lineage or definition approval.</p>
        {_workbench_validation_output_table(validation_queue, derived)}
      </section>
    </div>
  </section>

  <section class="panel" style="margin-top:16px;">
    <h2>Section-Level Triage</h2>
    <p class="subtle">One row per analysis section with blocker counts, review counts, top fields, and the data-team next step.</p>
    {_workbench_section_table(sections)}
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_analysis_workbench.html").write_text(html, encoding="utf-8")


def _write_lineage_map_html(
    package_root: Path,
    july_dir: Path,
    july_outputs: Any,
) -> None:
    lineage = july_outputs.intelligence_lineage_graph.copy()
    if lineage.empty:
        stage_summary = pd.DataFrame(columns=["lineage_stage", "edge_count", "ready_or_review_edges"])
    else:
        stage_summary = (
            lineage.assign(
                ready_or_review_edges=lineage["edge_status"].astype(str).str.contains(
                    "ready|P2|client|qualified|validation|required",
                    case=False,
                    na=False,
                )
            )
            .groupby("lineage_stage", as_index=False)
            .agg(edge_count=("edge_rank", "count"), ready_or_review_edges=("ready_or_review_edges", "sum"))
            .sort_values("lineage_stage")
        )
    nodes = set(lineage["source_node_id"].dropna().astype(str)) | set(lineage["target_node_id"].dropna().astype(str)) if not lineage.empty else set()
    output_edges = lineage[lineage["target_node_type"].eq("engine_output")] if not lineage.empty else pd.DataFrame()
    role_edges = lineage[lineage["target_node_type"].isin(["role", "operating_decision"])] if not lineage.empty else pd.DataFrame()
    field_edges = lineage[lineage["source_node_type"].isin(["source_column", "canonical_field"])] if not lineage.empty else pd.DataFrame()
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Lineage Map</title>
  <style>
    :root {{ --ink:#172033; --muted:#667085; --panel:#fff; --line:#d9dee8; --bg:#f5f7fb; --blue:#155eef; --green:#087443; --amber:#b54708; --red:#b42318; }}
    body {{ margin:0; font-family: Arial, Helvetica, sans-serif; color:var(--ink); background:var(--bg); }}
    main {{ max-width:1280px; margin:0 auto; padding:28px; }}
    .topline {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-start; }}
    .eyebrow {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }}
    h1 {{ margin:6px 0 8px; font-size:32px; }}
    h2 {{ margin:0 0 10px; font-size:18px; }}
    .subtle {{ color:var(--muted); line-height:1.45; }}
    .nav {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:flex-end; }}
    .nav a {{ color:var(--blue); background:#fff; border:1px solid var(--line); border-radius:6px; padding:8px 10px; text-decoration:none; font-size:13px; }}
    .metric-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:18px 0; }}
    .metric {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .metric span {{ display:block; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
    .metric strong {{ display:block; font-size:24px; margin-top:4px; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; margin-top:16px; }}
    .stage-grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .stage-card {{ border:1px solid var(--line); border-radius:8px; padding:12px; background:#fff; }}
    .stage-card b {{ display:block; font-size:13px; margin-bottom:6px; }}
    .stage-card small {{ color:var(--muted); display:block; line-height:1.35; }}
    .scroll {{ overflow-x:auto; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); }}
    th,td {{ border-bottom:1px solid #e6e9ef; padding:9px 10px; text-align:left; vertical-align:top; font-size:13px; }}
    th {{ background:#edf2f8; color:#344054; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }}
    tr:last-child td {{ border-bottom:0; }}
    @media (max-width:900px) {{ main {{ padding:18px; }} .topline {{ display:block; }} .nav {{ justify-content:flex-start; margin-top:12px; }} .metric-grid,.stage-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
    @media (max-width:560px) {{ .metric-grid,.stage-grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Synthetic client {CLIENT_ID} / lineage</div>
      <h1>Transactional Intelligence Lineage Map</h1>
      <p class="subtle">End-to-end graph from raw monthly files to canonical fields, analysis sections, generated outputs, charts, action plays, role handoffs, and operating decisions.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Section drilldowns</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(package_root / "transactional_intelligence_actuals.html")}">Actuals tables</a>
      <a href="{_file_url(july_dir / "intelligence_lineage_graph.csv")}">Lineage CSV</a>
    </nav>
  </div>

  <section class="metric-grid">
    {_metric("Lineage edges", len(lineage))}
    {_metric("Graph nodes", len(nodes))}
    {_metric("Stages", lineage["lineage_stage"].nunique() if not lineage.empty else 0)}
    {_metric("Analysis sections", lineage["analysis_section_id"].replace("", pd.NA).dropna().nunique() if not lineage.empty else 0)}
  </section>

  <section class="panel">
    <h2>Lineage Stages</h2>
    {_lineage_stage_cards(stage_summary)}
  </section>

  <section class="panel">
    <h2>File To Decision Edge Sample</h2>
    <div class="scroll">{_df_table(lineage, ["lineage_stage", "source_node_type", "source_label", "relationship", "target_node_type", "target_label", "edge_status", "owner_role", "next_action"], 70)}</div>
  </section>

  <section class="panel">
    <h2>Field And Analysis Dependencies</h2>
    <div class="scroll">{_df_table(field_edges, ["lineage_stage", "source_label", "relationship", "target_label", "edge_status", "analysis_section_id", "input_family", "field_key", "next_action"], 50)}</div>
  </section>

  <section class="panel">
    <h2>Analysis Sections To Outputs</h2>
    <div class="scroll">{_df_table(output_edges, ["source_label", "relationship", "target_label", "edge_status", "business_question", "target_table", "next_action"], 50)}</div>
  </section>

  <section class="panel">
    <h2>Outputs To Roles And Decisions</h2>
    <div class="scroll">{_df_table(role_edges, ["lineage_stage", "source_label", "relationship", "target_label", "edge_status", "owner_role", "business_question", "next_action"], 50)}</div>
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_lineage_map.html").write_text(html, encoding="utf-8")


def _write_section_drilldown_pages(
    package_root: Path,
    july_dir: Path,
    july_outputs: Any,
) -> None:
    sections = july_outputs.analysis_section_evidence_review.copy()
    visual_map = july_outputs.analysis_visual_output_map.copy()
    chart_specs = july_outputs.analysis_chart_spec_catalog.copy()
    chart_snapshots = july_outputs.analysis_chart_data_snapshot.copy()
    metric_catalog = july_outputs.intelligence_metric_catalog.copy()
    playbook = july_outputs.analysis_consulting_playbook.copy()
    insight_brief = july_outputs.analysis_insight_brief.copy()
    coverage = july_outputs.analysis_layout_coverage_matrix.copy()
    lineage = july_outputs.intelligence_lineage_graph.copy()
    scripts = july_outputs.analysis_script_catalog.copy()
    execution = july_outputs.analysis_execution_map.copy()
    section_dir = package_root / "analysis_sections"
    section_dir.mkdir(parents=True, exist_ok=True)
    index_rows = []

    if sections is not None and not sections.empty:
        for row in sections.sort_values(["review_rank", "domain_name", "source_section_id"]).to_dict("records"):
            section_id = _clean_cell(row.get("source_section_id"))
            if not section_id:
                continue
            slug = _html_slug(section_id)
            page_path = section_dir / f"{slug}.html"
            section_visuals = _section_rows(visual_map, section_id, "source_section_id")
            section_specs = _section_rows(chart_specs, section_id, "source_section_id")
            section_snapshots = _section_rows(chart_snapshots, section_id, "source_section_id")
            section_metrics = _section_metric_rows(metric_catalog, section_id)
            section_playbook = _section_rows(playbook, section_id, "source_section_id")
            section_brief = _section_rows(insight_brief, section_id, "source_section_id")
            section_coverage = _section_rows(coverage, section_id, "source_section_id")
            section_lineage = _section_rows(lineage, section_id, "analysis_section_id")
            section_scripts = _section_rows(scripts, section_id, "source_section_id")
            section_execution = _section_rows(execution, section_id, "source_section_id")
            _write_single_section_drilldown_html(
                page_path,
                package_root,
                july_dir,
                july_outputs,
                row,
                section_visuals,
                section_specs,
                section_snapshots,
                section_metrics,
                section_playbook,
                section_brief,
                section_coverage,
                section_lineage,
                section_scripts,
                section_execution,
            )
            index_rows.append(
                {
                    "source_section_id": section_id,
                    "domain_name": _clean_cell(row.get("domain_name")),
                    "display_name": _clean_cell(row.get("display_name")),
                    "status": _clean_cell(row.get("section_review_status")),
                    "charts": len(section_specs),
                    "outputs": len(_section_output_names(row, section_visuals)),
                    "scripts": len(section_scripts),
                    "mapped": int(_to_float(row.get("mapped_field_count"))),
                    "review": int(_to_float(row.get("review_field_count"))),
                    "blocked": int(_to_float(row.get("blocker_field_count"))),
                    "page": page_path,
                }
            )

    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Analysis Section Drilldowns</title>
  <style>
    {_section_drilldown_css()}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Synthetic client {CLIENT_ID} / analysis sections</div>
      <h1>Analysis Section Drilldowns</h1>
      <p class="subtle">One inspectable page per analysis section. Each page shows the consulting question, supporting scripts, generated outputs, chart previews, field coverage, blockers, and lineage edges.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_lineage_map.html")}">Lineage map</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(package_root / "README.html")}">Package README</a>
      <a href="{_file_url(july_dir / "analysis_section_evidence_review.csv")}">Section evidence CSV</a>
      <a href="{_file_url(july_dir / "analysis_consulting_playbook.csv")}">Consulting playbook CSV</a>
      <a href="{_file_url(july_dir / "analysis_insight_brief.csv")}">Insight brief CSV</a>
      <a href="{_file_url(july_dir / "analysis_chart_data_snapshot.csv")}">Chart data CSV</a>
      <a href="{_file_url(july_dir / "intelligence_metric_catalog.csv")}">Metric catalog CSV</a>
    </nav>
  </div>

  <section class="metric-grid">
    {_metric("Analysis sections", len(index_rows))}
    {_metric("Chart specs", len(chart_specs))}
    {_metric("Chart data rows", len(chart_snapshots))}
    {_metric("Playbook rows", len(playbook))}
    {_metric("Field checks", len(coverage))}
    {_metric("Lineage edges", len(lineage))}
  </section>

  <section class="panel">
    <h2>Section Index</h2>
    <p class="subtle">Open a section to inspect what the engine is analyzing and which charts or outputs it can produce from the current file drop.</p>
    {_section_index_table(index_rows)}
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_section_drilldowns.html").write_text(index_html, encoding="utf-8")


def _write_single_section_drilldown_html(
    page_path: Path,
    package_root: Path,
    july_dir: Path,
    july_outputs: Any,
    section: dict[str, Any],
    visual_map: pd.DataFrame,
    chart_specs: pd.DataFrame,
    chart_snapshots: pd.DataFrame,
    metric_catalog: pd.DataFrame,
    playbook: pd.DataFrame,
    insight_brief: pd.DataFrame,
    coverage: pd.DataFrame,
    lineage: pd.DataFrame,
    scripts: pd.DataFrame,
    execution: pd.DataFrame,
) -> None:
    section_id = _clean_cell(section.get("source_section_id"))
    display_name = _clean_cell(section.get("display_name")) or section_id
    status = _clean_cell(section.get("section_review_status"))
    output_names = _section_output_names(section, visual_map)
    blocker_rows = coverage[coverage["coverage_severity"].eq("blocker")].copy() if not coverage.empty and "coverage_severity" in coverage else pd.DataFrame()
    review_rows = coverage[coverage["coverage_severity"].eq("review")].copy() if not coverage.empty and "coverage_severity" in coverage else pd.DataFrame()
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(display_name)} Analysis Drilldown</title>
  <style>
    {_section_drilldown_css()}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Analysis section / <code>{escape(section_id)}</code></div>
      <h1>{escape(display_name)}</h1>
      <p class="subtle">{escape(_clean_cell(section.get("analysis_summary")) or "Section-level evidence generated from the current engine run.")}</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">All sections</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_chart_gallery.html")}">Chart gallery</a>
      <a href="{_file_url(july_dir / "analysis_section_evidence_review.csv")}">Section evidence CSV</a>
    </nav>
  </div>

  <section class="metric-grid">
    {_metric("Output artifacts", len(output_names))}
    {_metric("Chart specs", len(chart_specs))}
    {_metric("Metrics", len(metric_catalog))}
    {_metric("Source scripts", len(scripts))}
    {_metric("Mapped fields", section.get("mapped_field_count"))}
    {_metric("Review fields", section.get("review_field_count"))}
    {_metric("Blocker fields", section.get("blocker_field_count"))}
  </section>

  <section class="split">
    <article class="panel">
      <h2>What This Analyzes</h2>
      <dl class="facts">
        <dt>Status</dt><dd>{_status_badge(status)}</dd>
        <dt>Domain</dt><dd>{escape(_clean_cell(section.get("domain_name")))}</dd>
        <dt>Family</dt><dd>{escape(_clean_cell(section.get("analysis_family")))}</dd>
        <dt>Business question</dt><dd>{escape(_clean_cell(section.get("business_question")))}</dd>
        <dt>Consulting question</dt><dd>{escape(_clean_cell(section.get("consulting_question")))}</dd>
        <dt>Consulting use</dt><dd>{escape(_clean_cell(section.get("consulting_use")))}</dd>
      </dl>
    </article>
    <article class="panel">
      <h2>How To Use It</h2>
      <dl class="facts">
        <dt>Required inputs</dt><dd>{escape(_clean_cell(section.get("required_input_families")))}</dd>
        <dt>Layout readiness</dt><dd>{escape(_clean_cell(section.get("current_layout_readiness")))}</dd>
        <dt>Layout blockers</dt><dd>{escape(_clean_cell(section.get("layout_blockers")) or "None")}</dd>
        <dt>Analyst next step</dt><dd>{escape(_clean_cell(section.get("analyst_next_step")))}</dd>
        <dt>Data-team next step</dt><dd>{escape(_clean_cell(section.get("data_team_next_step")))}</dd>
        <dt>CSM question</dt><dd>{escape(_clean_cell(section.get("csm_review_question")))}</dd>
      </dl>
    </article>
  </section>

  <section class="panel">
    <h2>Consulting Playbook</h2>
    <p class="subtle">Story role, proof surface, CSM talk track, analyst validation focus, and data-team dependency for this section.</p>
    <div class="scroll">{_df_table(playbook, ["client_story_role", "meeting_moment", "primary_output_file", "primary_chart_type", "stakeholder_owner", "csm_talk_track", "analyst_validation_focus", "data_team_dependency", "marketing_activation_use"], 10)}</div>
  </section>

  <section class="panel">
    <h2>Insight Brief</h2>
    <p class="subtle">Data-backed section summary for the CSM and analyst: headline, evidence, caveat, and next client question.</p>
    <div class="scroll">{_df_table(insight_brief, ["brief_status", "headline_insight", "primary_evidence", "data_caveat", "recommended_client_question", "analyst_next_step", "data_team_next_step"], 10)}</div>
  </section>

  <section class="panel">
    <h2>Generated Outputs</h2>
    <p class="subtle">Files and Snowflake targets this section contributes to in the July measurement run.</p>
    <div class="chip-row">{_artifact_links(output_names, july_dir)}</div>
    <div class="scroll" style="margin-top:12px;">{_df_table(visual_map, ["output_file", "target_table", "visual_family", "visual_type", "visual_mode", "chart_readiness_status", "proof_artifacts"], 30)}</div>
  </section>

  <section class="panel">
    <h2>Charts And Graphs</h2>
    <p class="subtle">Rendered from <code>analysis_chart_spec_catalog.csv</code> against the generated output artifacts. These are the charts the engine knows this section can produce.</p>
    <div class="gallery compact">{_chart_gallery_cards(chart_specs, july_outputs)}</div>
  </section>

  <section class="panel">
    <h2>Chart Data Snapshots</h2>
    <p class="subtle">Backing rows and callouts for this section's chart specs, generated from the same output artifacts used by the rendered previews.</p>
    <div class="scroll">{_df_table(chart_snapshots, ["chart_title", "chart_type", "data_artifact", "plotted_row_count", "source_row_count", "data_status", "top_label", "top_value", "insight_callout"], 30)}</div>
  </section>

  <section class="panel">
    <h2>Metric Catalog</h2>
    <p class="subtle">Semantic metric rows used by this section: business definition, source field, field role, validation status, and CSM interpretation.</p>
    <div class="scroll">{_df_table(metric_catalog, ["metric_id", "metric_family", "source_artifact", "source_field", "field_role", "chart_usage_count", "validation_status", "business_definition", "csm_interpretation"], 30)}</div>
  </section>

  <section class="split">
    <article class="panel">
      <h2>Source Scripts</h2>
      <p class="subtle">Repo scripts currently mapped to this section.</p>
      {_section_script_table(scripts, visual_map)}
    </article>
    <article class="panel">
      <h2>Execution Evidence</h2>
      <p class="subtle">How this section maps into engine outputs and current generated row counts.</p>
      <div class="scroll">{_df_table(execution, ["source_path", "required_input_families", "runnable_script_count", "generated_output_files", "generated_row_count", "output_row_counts", "evidence_status", "analyst_next_step"], 10)}</div>
    </article>
  </section>

  <section class="panel">
    <h2>Field Coverage And Blockers</h2>
    <p class="subtle">Actual field references from the section scripts compared to current layout and contract coverage.</p>
    <div class="coverage-grid">
      <div>{_section_coverage_chart(coverage)}</div>
      <div class="scroll">{_df_table(blocker_rows if not blocker_rows.empty else review_rows, ["input_family_hint", "field_key", "reference_count", "script_count", "coverage_status", "coverage_severity", "analyst_action", "data_team_action"], 28)}</div>
    </div>
  </section>

  <section class="panel">
    <h2>Lineage Edges</h2>
    <p class="subtle">Where this section sits in the engine graph: inputs, fields, generated outputs, charts, actions, roles, and decisions.</p>
    <div class="scroll">{_df_table(lineage, ["lineage_stage", "source_node_type", "source_label", "relationship", "target_node_type", "target_label", "edge_status", "owner_role", "output_artifact", "next_action"], 70)}</div>
  </section>
</main>
</body>
</html>
"""
    page_path.write_text(html, encoding="utf-8")


def _section_drilldown_css() -> str:
    return """
    :root { --ink:#101828; --muted:#667085; --line:#d8dee8; --panel:#fff; --wash:#f5f7fb; --blue:#155eef; --teal:#0f766e; --green:#047857; --amber:#b45309; --red:#c2410c; --violet:#6d28d9; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:var(--wash); }
    main { max-width:1360px; margin:0 auto; padding:24px; }
    h1 { margin:0; font-size:28px; line-height:1.15; }
    h2 { margin:0 0 12px; font-size:18px; }
    h3 { margin:0 0 8px; font-size:14px; }
    p { margin:0; line-height:1.45; }
    a { color:var(--blue); text-decoration:none; }
    a:hover { text-decoration:underline; }
    code { background:#eef2f7; border:1px solid #d8dee8; border-radius:4px; padding:2px 5px; white-space:nowrap; }
    table { width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); }
    th,td { border-bottom:1px solid #e7ebf2; padding:8px 9px; text-align:left; vertical-align:top; font-size:12px; }
    th { background:#eef3f8; color:#344054; font-size:11px; text-transform:uppercase; letter-spacing:.04em; }
    tr:last-child td { border-bottom:0; }
    .topline { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:18px; }
    .eyebrow { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; font-weight:700; }
    .subtle,.small { color:var(--muted); font-size:13px; }
    .nav { display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end; font-size:13px; }
    .nav a { border:1px solid var(--line); background:var(--panel); border-radius:6px; padding:7px 9px; }
    .metric-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; margin:16px 0 18px; }
    .metric { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px; min-height:78px; }
    .metric span { display:block; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.05em; }
    .metric strong { display:block; font-size:24px; margin-top:8px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; margin-top:16px; }
    .split { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; align-items:start; }
    .coverage-grid { display:grid; grid-template-columns:minmax(280px,.75fr) minmax(0,1.25fr); gap:16px; align-items:start; }
    .facts { display:grid; grid-template-columns:150px minmax(0,1fr); gap:10px 14px; margin:0; }
    .facts dt { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
    .facts dd { margin:0; font-size:13px; line-height:1.45; }
    .status { display:inline-block; border-radius:999px; padding:3px 7px; font-size:11px; background:#eef2f7; color:#344054; white-space:nowrap; }
    .status.blocked,.status.qualified_by_layout_blockers { background:#fff1f0; color:var(--red); }
    .status.validate,.status.validation_required { background:#fff7ed; color:var(--amber); }
    .status.ready,.status.client_ready { background:#ecfdf3; color:var(--green); }
    .chip-row { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
    .chip-row a,.chip-row span { border:1px solid var(--line); border-radius:5px; padding:4px 6px; background:#fbfcfe; font-size:11px; color:#344054; }
    .scroll { overflow-x:auto; }
    .gallery { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:12px; }
    .gallery.compact .chart-card { min-height:280px; }
    .chart-card { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; min-height:320px; }
    .chart-card header { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:10px; }
    .chart-card h2 { font-size:16px; line-height:1.25; }
    .meta { display:flex; flex-wrap:wrap; gap:6px; margin:9px 0 12px; }
    .meta span { border:1px solid var(--line); background:#fbfcfe; border-radius:5px; padding:4px 6px; font-size:11px; color:#344054; }
    .bar-row { display:grid; grid-template-columns:minmax(132px,.9fr) minmax(100px,1.4fr) 86px; gap:10px; align-items:center; min-height:28px; margin:7px 0; }
    .bar-label { font-size:12px; overflow-wrap:anywhere; }
    .bar-track { height:16px; border:1px solid #d5dbe5; background:#f2f4f7; border-radius:3px; overflow:hidden; }
    .bar-fill { display:block; height:100%; background:var(--blue); }
    .bar-fill.teal { background:var(--teal); }
    .bar-fill.violet { background:var(--violet); }
    .bar-fill.red { background:var(--red); }
    .bar-value { color:var(--muted); font-size:12px; text-align:right; }
    .story-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
    .story-card { border:1px solid var(--line); background:#fbfcfe; border-radius:7px; padding:9px; font-size:12px; }
    @media (max-width:980px) { .topline { display:block; } .nav { justify-content:flex-start; margin-top:12px; } .metric-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } .split,.coverage-grid,.gallery { grid-template-columns:1fr; } }
    @media (max-width:620px) { main { padding:16px; } .metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } .facts { grid-template-columns:1fr; } .bar-row { grid-template-columns:1fr; gap:4px; } .bar-value { text-align:left; } .story-grid { grid-template-columns:1fr; } }
    """


def _section_rows(df: pd.DataFrame, section_id: str, column: str) -> pd.DataFrame:
    if df is None or df.empty or column not in df.columns:
        return pd.DataFrame()
    return df[df[column].fillna("").astype(str).eq(section_id)].copy()


def _section_metric_rows(df: pd.DataFrame, section_id: str) -> pd.DataFrame:
    if df is None or df.empty or "used_by_sections" not in df.columns:
        return pd.DataFrame()
    needle = f"|{section_id}|"
    mask = df["used_by_sections"].fillna("").astype(str).map(lambda value: needle in f"|{value}|")
    return df[mask].copy()


def _html_slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _clean_cell(value).lower()).strip("_")
    return slug or "section"


def _section_output_names(section: dict[str, Any], visual_map: pd.DataFrame) -> list[str]:
    values = _split_pipe(section.get("generated_output_files"))
    if visual_map is not None and not visual_map.empty and "output_file" in visual_map.columns:
        values.extend(_unique_pipe_values(visual_map["output_file"]))
    seen = set()
    names = []
    for value in values:
        item = _clean_cell(value)
        if item and item not in seen:
            seen.add(item)
            names.append(item)
    return names


def _section_index_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p class='subtle'>No analysis sections generated.</p>"
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td><a href='{_file_url(row['page'])}'><code>{escape(row['source_section_id'])}</code></a></td>"
            f"<td>{escape(row['domain_name'])}</td>"
            f"<td>{escape(row['display_name'])}</td>"
            f"<td>{_status_badge(row['status'])}</td>"
            f"<td>{row['scripts']}</td>"
            f"<td>{row['outputs']}</td>"
            f"<td>{row['charts']}</td>"
            f"<td>{row['mapped']} / {row['review']} / {row['blocked']}</td>"
            "</tr>"
        )
    return (
        "<div class='scroll'><table><thead><tr>"
        "<th>Section</th><th>Domain</th><th>Name</th><th>Status</th><th>Scripts</th><th>Outputs</th><th>Charts</th><th>Mapped / review / blocked fields</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _section_script_table(scripts: pd.DataFrame, visual_map: pd.DataFrame) -> str:
    if scripts is None or scripts.empty:
        script_names = []
        if visual_map is not None and not visual_map.empty and "source_scripts" in visual_map.columns:
            script_names = _unique_pipe_values(visual_map["source_scripts"])
        if not script_names:
            return "<p class='subtle'>No source scripts mapped.</p>"
        rows = "".join(f"<tr><td><code>{escape(name)}</code></td></tr>" for name in script_names)
        return "<div class='scroll'><table><thead><tr><th>Script</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
    body = []
    for row in scripts.sort_values(["runnable_flag", "script_order", "script_name"], ascending=[False, True, True]).to_dict("records"):
        source_path = _clean_cell(row.get("source_path"))
        path = Path(source_path)
        absolute_path = path if path.is_absolute() else _REPO / path
        source_link = (
            f"<a href='{_file_url(absolute_path)}'>{escape(source_path)}</a>"
            if source_path and absolute_path.exists()
            else escape(source_path)
        )
        body.append(
            "<tr>"
            f"<td><code>{escape(_clean_cell(row.get('script_name')))}</code></td>"
            f"<td>{source_link}</td>"
            f"<td>{escape(_clean_cell(row.get('inferred_topic')))}</td>"
            f"<td>{escape(_clean_cell(row.get('output_role')))}</td>"
            f"<td>{escape(_clean_cell(row.get('runnable_flag')))}</td>"
            "</tr>"
        )
    return (
        "<div class='scroll'><table><thead><tr>"
        "<th>Script</th><th>Source path</th><th>Topic</th><th>Output role</th><th>Runnable</th>"
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _section_coverage_chart(coverage: pd.DataFrame) -> str:
    if coverage is None or coverage.empty or "coverage_status" not in coverage.columns:
        return "<p class='subtle'>No field coverage rows.</p>"
    counts = (
        coverage.groupby("coverage_status", dropna=False)["reference_count"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )
    maximum = max((_to_float(value) for value in counts), default=1.0)
    rows = []
    for label, value in counts.items():
        label_text = _clean_cell(label)
        color = "red" if "needed" in label_text or "mapping" in label_text else "violet" if "validate" in label_text else "teal"
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(label_text)}</div>"
            f"<div class='bar-track'><span class='bar-fill {color}' style='width:{_pct(value, maximum)}%'></span></div>"
            f"<div class='bar-value'>{_format_count(value)}</div>"
            "</div>"
        )
    return "".join(rows)


def _write_analysis_chart_gallery_html(
    package_root: Path,
    july_dir: Path,
    july_outputs: Any,
) -> None:
    chart_specs = july_outputs.analysis_chart_spec_catalog.copy()
    visual_map = july_outputs.analysis_visual_output_map.copy()
    metrics = {
        "specs": len(chart_specs),
        "chart_types": chart_specs["chart_type"].nunique() if not chart_specs.empty else 0,
        "sections": chart_specs["source_section_id"].nunique() if not chart_specs.empty else 0,
        "ready_columns": int(chart_specs["required_columns_present"].astype(bool).sum()) if not chart_specs.empty else 0,
    }
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Transactional Intelligence Chart Gallery</title>
  <style>
    :root {{
      --ink: #101828;
      --muted: #667085;
      --line: #d8dee8;
      --panel: #ffffff;
      --wash: #f5f7fb;
      --blue: #155eef;
      --teal: #0f766e;
      --amber: #b45309;
      --red: #c2410c;
      --green: #047857;
      --violet: #6d28d9;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: var(--ink); background: var(--wash); }}
    main {{ max-width: 1360px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 28px; line-height: 1.15; }}
    h2 {{ margin: 0; font-size: 17px; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; }}
    p {{ margin: 0; line-height: 1.45; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #eef2f7; border: 1px solid #d8dee8; border-radius: 4px; padding: 2px 5px; white-space: nowrap; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); }}
    th, td {{ border-bottom: 1px solid #e7ebf2; padding: 7px 8px; text-align: left; vertical-align: top; font-size: 12px; }}
    th {{ background: #eef3f8; color: #344054; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .topline {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }}
    .eyebrow {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 6px; }}
    .subtle {{ color: var(--muted); font-size: 12px; }}
    .nav {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; font-size: 13px; }}
    .nav a {{ border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 7px 9px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 16px 0 18px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 78px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 8px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }}
    .gallery {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 16px; }}
    .chart-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 360px; }}
    .chart-card header {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 10px; }}
    .chart-card h2 {{ font-size: 16px; line-height: 1.25; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 9px 0 12px; }}
    .meta span {{ border: 1px solid var(--line); background: #fbfcfe; border-radius: 5px; padding: 4px 6px; font-size: 11px; color: #344054; }}
    .status {{ border-radius: 999px; padding: 4px 8px; font-size: 11px; white-space: nowrap; background: #eef2f7; color: #344054; }}
    .status.qualified_by_layout_blockers {{ background: #fff1f0; color: var(--red); }}
    .status.validation_required {{ background: #fff7ed; color: var(--amber); }}
    .status.client_ready {{ background: #ecfdf3; color: var(--green); }}
    .bar-row {{ display: grid; grid-template-columns: minmax(132px, .9fr) minmax(100px, 1.4fr) 86px; gap: 10px; align-items: center; min-height: 28px; margin: 7px 0; }}
    .bar-label {{ font-size: 12px; overflow-wrap: anywhere; }}
    .bar-track {{ height: 16px; border: 1px solid #d5dbe5; background: #f2f4f7; border-radius: 3px; overflow: hidden; }}
    .bar-fill {{ display: block; height: 100%; background: var(--blue); }}
    .bar-fill.teal {{ background: var(--teal); }}
    .bar-fill.violet {{ background: var(--violet); }}
    .bar-value {{ color: var(--muted); font-size: 12px; text-align: right; }}
    .story-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .story-card {{ border: 1px solid var(--line); background: #fbfcfe; border-radius: 7px; padding: 9px; font-size: 12px; }}
    .scroll {{ overflow-x: auto; }}
    .spec-table {{ margin-top: 12px; }}
    @media (max-width: 980px) {{ .gallery {{ grid-template-columns: 1fr; }} .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 620px) {{ main {{ padding: 16px; }} .topline {{ display: block; }} .nav {{ justify-content: flex-start; margin-top: 12px; }} .metric-grid {{ grid-template-columns: 1fr; }} .bar-row {{ grid-template-columns: 1fr; gap: 4px; }} .bar-value {{ text-align: left; }} .story-grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <div class="topline">
    <div>
      <div class="eyebrow">Synthetic client {CLIENT_ID} / chart previews</div>
      <h1>Transactional Intelligence Chart Gallery</h1>
      <p class="subtle">Rendered previews from <code>analysis_chart_spec_catalog.csv</code> using the actual generated July output artifacts.</p>
    </div>
    <nav class="nav">
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_dashboard.html")}">Dashboard</a>
      <a href="{_file_url(package_root / "transactional_intelligence_client_story.html")}">Client story</a>
      <a href="{_file_url(package_root / "transactional_intelligence_intake_cockpit.html")}">Intake cockpit</a>
      <a href="{_file_url(package_root / "transactional_intelligence_analysis_workbench.html")}">Analysis workbench</a>
      <a href="{_file_url(package_root / "transactional_intelligence_section_drilldowns.html")}">Section drilldowns</a>
      <a href="{_file_url(package_root / "transactional_intelligence_lineage_map.html")}">Lineage map</a>
      <a href="{_file_url(package_root / "README.html")}">Package README</a>
      <a href="{_file_url(july_dir / "analysis_chart_spec_catalog.csv")}">Chart specs CSV</a>
      <a href="{_file_url(july_dir / "analysis_visual_output_map.csv")}">Visual map CSV</a>
    </nav>
  </div>

  <section class="metric-grid" aria-label="Chart gallery metrics">
    {_metric("Chart specs", metrics["specs"])}
    {_metric("Chart types", metrics["chart_types"])}
    {_metric("Sections covered", metrics["sections"])}
    {_metric("Column-ready specs", metrics["ready_columns"])}
  </section>

  <section class="panel">
    <h2>Chart Spec Summary</h2>
    <p class="subtle">These previews are intentionally simple. The important part is the contract: each row declares exactly which artifact and fields should feed the eventual UI, dashboard, deck, or BI chart.</p>
    <div class="spec-table">{_chart_spec_summary_table(chart_specs)}</div>
  </section>

  <section class="gallery">
    {_chart_gallery_cards(chart_specs, july_outputs)}
  </section>

  <section class="panel" style="margin-top:16px;">
    <h2>Visual Output Map</h2>
    <p class="subtle">The upstream map that tells the engine which analysis sections support which outputs and whether they are ready, qualified, or waiting on validation.</p>
    <div class="scroll">{_df_table(visual_map, ["source_section_id", "domain_name", "output_file", "visual_family", "visual_type", "chart_readiness_status", "proof_artifacts"], 40)}</div>
  </section>
</main>
</body>
</html>
"""
    (package_root / "transactional_intelligence_chart_gallery.html").write_text(html, encoding="utf-8")


def _chart_spec_summary_table(chart_specs: pd.DataFrame) -> str:
    if chart_specs is None or chart_specs.empty:
        return "<p class='subtle'>No chart specs generated.</p>"
    summary = (
        chart_specs.groupby(["chart_type", "render_owner", "chart_readiness_status"], dropna=False)
        .size()
        .reset_index(name="spec_count")
        .sort_values(["spec_count", "chart_type"], ascending=[False, True])
    )
    return "<div class='scroll'>" + _df_table(
        summary,
        ["chart_type", "render_owner", "chart_readiness_status", "spec_count"],
        30,
    ) + "</div>"


def _chart_gallery_cards(chart_specs: pd.DataFrame, outputs: Any) -> str:
    if chart_specs is None or chart_specs.empty:
        return "<article class='chart-card'><p class='subtle'>No chart specs generated.</p></article>"
    view = chart_specs.sort_values(
        ["chart_readiness_status", "chart_type", "source_section_id"],
        na_position="last",
    ).head(36)
    cards = []
    for spec in view.to_dict("records"):
        status = _clean_cell(spec.get("chart_readiness_status"))
        title = _clean_cell(spec.get("chart_title")) or _clean_cell(spec.get("source_section_id"))
        cards.append(
            "<article class='chart-card'>"
            "<header>"
            f"<h2>{escape(title)}</h2>"
            f"<span class='status {escape(status)}'>{escape(status.replace('_', ' ') or 'unknown')}</span>"
            "</header>"
            "<div class='meta'>"
            f"<span>{escape(_clean_cell(spec.get('chart_type')))}</span>"
            f"<span>{escape(_clean_cell(spec.get('output_file')))}</span>"
            f"<span>{escape(_clean_cell(spec.get('render_owner')))}</span>"
            f"<span>x: {escape(_clean_cell(spec.get('x_field')) or '--')}</span>"
            f"<span>y: {escape(_clean_cell(spec.get('y_field')) or '--')}</span>"
            "</div>"
            f"{_render_chart_preview(spec, outputs)}"
            "</article>"
        )
    return "".join(cards)


def _render_chart_preview(spec: dict[str, Any], outputs: Any) -> str:
    df = _output_dataframe_for_artifact(outputs, spec.get("data_artifact") or spec.get("output_file"))
    if df is None or df.empty:
        return "<p class='subtle'>No source rows available for this artifact.</p>"
    chart_type = _clean_cell(spec.get("chart_type"))
    if chart_type in {"bar", "horizontal_bar", "ranked_bar", "stacked_bar", "lift_bar", "donut"}:
        return _render_bar_preview(df, spec)
    if chart_type == "story_cards":
        return _render_story_preview(df, spec)
    return _render_table_preview(df, spec)


def _render_bar_preview(df: pd.DataFrame, spec: dict[str, Any]) -> str:
    x_field = _clean_cell(spec.get("x_field"))
    y_field = _clean_cell(spec.get("y_field"))
    series_field = _clean_cell(spec.get("series_field"))
    if not x_field or x_field not in df.columns or not y_field or y_field not in df.columns:
        return _render_table_preview(df, spec)
    view = df.copy()
    view["_chart_value"] = pd.to_numeric(view[y_field], errors="coerce").fillna(0)
    view["_abs_value"] = view["_chart_value"].abs()
    view = view.sort_values("_abs_value", ascending=False).head(_top_n(spec, default=8))
    max_value = max((_to_float(value) for value in view["_abs_value"]), default=1.0)
    rows = []
    for item in view.to_dict("records"):
        label = _clean_cell(item.get(x_field))
        if series_field and series_field in df.columns:
            label = f"{label} / {_clean_cell(item.get(series_field))}"
        value = _to_float(item.get("_chart_value"))
        value_text = _format_chart_value(value, y_field)
        color_class = "teal" if "rate" in y_field or "lift" in y_field else "violet" if "amount" in y_field or "value" in y_field else ""
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(label)}</div>"
            f"<div class='bar-track'><span class='bar-fill {color_class}' style='width:{_pct(abs(value), max_value)}%'></span></div>"
            f"<div class='bar-value'>{escape(value_text)}</div>"
            "</div>"
        )
    return "".join(rows) or "<p class='subtle'>No numeric chart values.</p>"


def _render_story_preview(df: pd.DataFrame, spec: dict[str, Any]) -> str:
    label_field = _clean_cell(spec.get("label_field"))
    x_field = _clean_cell(spec.get("x_field"))
    fields = [field for field in [x_field, label_field] if field and field in df.columns]
    if not fields:
        return _render_table_preview(df, spec)
    view = df.head(_top_n(spec, default=6))
    cards = []
    for item in view.to_dict("records"):
        heading = _clean_cell(item.get(fields[0]))
        body = _clean_cell(item.get(fields[-1]))
        cards.append(
            "<div class='story-card'>"
            f"<b>{escape(heading or 'Story')}</b>"
            f"<p class='subtle'>{escape(body)}</p>"
            "</div>"
        )
    return "<div class='story-grid'>" + "".join(cards) + "</div>"


def _render_table_preview(df: pd.DataFrame, spec: dict[str, Any]) -> str:
    desired = _unique_pipe_values(
        [
            _clean_cell(spec.get("x_field")),
            _clean_cell(spec.get("y_field")),
            _clean_cell(spec.get("series_field")),
            _clean_cell(spec.get("label_field")),
            _clean_cell(spec.get("value_field")),
            _clean_cell(spec.get("color_field")),
        ]
    )
    columns = [column for column in desired if column in df.columns]
    if not columns:
        columns = list(df.columns[: min(6, len(df.columns))])
    return "<div class='scroll'>" + _df_table(df, columns, min(_top_n(spec, default=8), 12)) + "</div>"


def _output_dataframe_for_artifact(outputs: Any, artifact_name: Any) -> pd.DataFrame:
    key = _clean_cell(artifact_name).removesuffix(".csv").removesuffix(".json")
    value = getattr(outputs, key, pd.DataFrame())
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        rows = value.get("story_arc") if key == "consulting_story" else None
        if isinstance(rows, list):
            return pd.DataFrame(rows)
        return pd.DataFrame([value])
    return pd.DataFrame()


def _top_n(spec: dict[str, Any], *, default: int) -> int:
    value = int(_to_float(spec.get("top_n"), default=default))
    return max(1, min(value, 50))


def _format_chart_value(value: float, field_name: str) -> str:
    key = field_name.lower()
    if "rate" in key or "lift" in key:
        return _percent(value)
    if "amount" in key or "value" in key or "balance" in key:
        return _currency(value)
    return _format_count(value)


def _workbench_count_chart(df: pd.DataFrame, label_col: str, value_col: str, color_class: str) -> str:
    if df is None or df.empty or label_col not in df or value_col not in df:
        return "<p class='subtle'>No rows.</p>"
    counts = df.groupby(label_col, dropna=False)[value_col].sum().sort_values(ascending=False).head(10)
    maximum = max((_to_float(value) for value in counts), default=1.0)
    rows = []
    for label, value in counts.items():
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(_clean_cell(label))}</div>"
            f"<div class='bar-track'><span class='bar-fill {color_class}' style='width:{_pct(value, maximum)}%'></span></div>"
            f"<div class='bar-value'>{_format_count(value)}</div>"
            "</div>"
        )
    return "".join(rows)


def _workbench_readiness_table(readiness: pd.DataFrame) -> str:
    if readiness is None or readiness.empty:
        return "<p class='subtle'>No readiness assessment generated.</p>"
    return "<div class='scroll'>" + _df_table(
        readiness,
        [
            "readiness_area",
            "owner_role",
            "readiness_status",
            "client_use_status",
            "severity",
            "blocker_count",
            "validation_count",
            "evidence_summary",
            "next_action",
        ],
        20,
    ) + "</div>"


def _workbench_user_interaction_table(user_interaction_map: pd.DataFrame) -> str:
    if user_interaction_map is None or user_interaction_map.empty:
        return "<p class='subtle'>No user interaction map generated.</p>"
    view = user_interaction_map.sort_values(["interaction_rank"]).head(50)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "user_role",
            "workflow_lane",
            "primary_screen",
            "file_name",
            "delivery_mode",
            "decision_supported",
            "owner_next_action",
            "client_use_status",
        ],
        50,
    ) + "</div>"


def _workbench_production_backlog_table(production_backlog: pd.DataFrame) -> str:
    if production_backlog is None or production_backlog.empty:
        return "<p class='subtle'>No production readiness backlog generated.</p>"
    view = production_backlog.sort_values(["backlog_rank"]).head(60)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "backlog_rank",
            "priority_band",
            "workstream",
            "owner_role",
            "problem_statement",
            "required_action",
            "acceptance_criteria",
            "affected_outputs",
            "client_use_status",
        ],
        60,
    ) + "</div>"


def _workbench_analysis_review_board_table(analysis_board: pd.DataFrame) -> str:
    if analysis_board is None or analysis_board.empty:
        return "<p class='subtle'>No analysis review board generated.</p>"
    view = analysis_board.sort_values(["review_status", "domain_name", "source_section_id"]).head(40)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "display_name",
            "what_is_analyzed",
            "chart_count",
            "primary_chart_type",
            "metric_count",
            "headline_insight",
            "recommended_client_question",
            "meeting_phase_refs",
            "review_status",
        ],
        40,
    ) + "</div>"


def _workbench_playbook_table(playbook: pd.DataFrame) -> str:
    if playbook is None or playbook.empty:
        return "<p class='subtle'>No consulting playbook generated.</p>"
    view = playbook.sort_values(["output_readiness_status", "domain_name", "source_section_id"]).head(36)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "client_story_role",
            "primary_output_file",
            "primary_chart_type",
            "stakeholder_owner",
            "csm_talk_track",
            "analyst_validation_focus",
            "data_team_dependency",
        ],
        36,
    ) + "</div>"


def _workbench_metric_catalog_table(metric_catalog: pd.DataFrame) -> str:
    if metric_catalog is None or metric_catalog.empty:
        return "<p class='subtle'>No semantic metric catalog generated.</p>"
    view = metric_catalog.sort_values(["validation_status", "metric_family", "metric_id"]).head(48)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "metric_id",
            "metric_family",
            "source_artifact",
            "source_field",
            "field_role",
            "chart_usage_count",
            "validation_status",
            "csm_interpretation",
        ],
        48,
    ) + "</div>"


def _workbench_insight_brief_table(insight_brief: pd.DataFrame) -> str:
    if insight_brief is None or insight_brief.empty:
        return "<p class='subtle'>No analysis insight brief generated.</p>"
    view = insight_brief.sort_values(["brief_status", "domain_name", "source_section_id"]).head(36)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "brief_status",
            "headline_insight",
            "primary_evidence",
            "data_caveat",
            "recommended_client_question",
            "analyst_next_step",
        ],
        36,
    ) + "</div>"


def _workbench_meeting_blueprint_table(meeting_blueprint: pd.DataFrame) -> str:
    if meeting_blueprint is None or meeting_blueprint.empty:
        return "<p class='subtle'>No client meeting deck blueprint generated.</p>"
    view = meeting_blueprint.sort_values(["blueprint_rank"]).head(60)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "blueprint_rank",
            "meeting_phase",
            "slide_type",
            "slide_title",
            "decision_prompt",
            "blueprint_status",
            "source_artifact",
            "follow_up_action",
        ],
        60,
    ) + "</div>"


def _workbench_visual_map_table(visual_map: pd.DataFrame) -> str:
    if visual_map is None or visual_map.empty:
        return "<p class='subtle'>No visual output map generated.</p>"
    view = visual_map.sort_values(["chart_readiness_status", "domain_name", "source_section_id"]).head(36)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "domain_name",
            "output_file",
            "visual_family",
            "visual_type",
            "chart_readiness_status",
            "source_scripts",
            "proof_artifacts",
        ],
        36,
    ) + "</div>"


def _workbench_chart_spec_table(chart_specs: pd.DataFrame) -> str:
    if chart_specs is None or chart_specs.empty:
        return "<p class='subtle'>No chart specs generated.</p>"
    view = chart_specs.sort_values(["chart_readiness_status", "domain_name", "source_section_id"]).head(36)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "output_file",
            "chart_type",
            "x_field",
            "y_field",
            "series_field",
            "required_columns_present",
            "render_owner",
            "chart_readiness_status",
        ],
        36,
    ) + "</div>"


def _workbench_chart_snapshot_table(chart_snapshots: pd.DataFrame) -> str:
    if chart_snapshots is None or chart_snapshots.empty:
        return "<p class='subtle'>No chart data snapshots generated.</p>"
    view = chart_snapshots.sort_values(["data_status", "source_section_id", "spec_rank"]).head(36)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "chart_title",
            "chart_type",
            "data_artifact",
            "plotted_row_count",
            "source_row_count",
            "data_status",
            "top_label",
            "top_value",
            "insight_callout",
        ],
        36,
    ) + "</div>"


def _workbench_backlog_output_table(backlog: pd.DataFrame, blockers: pd.DataFrame) -> str:
    if backlog is None or backlog.empty:
        return _workbench_backlog_table(blockers)
    return "<div class='scroll'>" + _df_table(
        backlog,
        [
            "priority_band",
            "input_family",
            "field_key",
            "coverage_status",
            "reference_count",
            "affected_section_count",
            "affected_sections",
            "example_scripts",
            "snowflake_design_action",
        ],
        30,
    ) + "</div>"


def _workbench_validation_output_table(validation_queue: pd.DataFrame, derived: pd.DataFrame) -> str:
    if validation_queue is None or validation_queue.empty:
        return _workbench_derived_table(derived)
    return "<div class='scroll'>" + _df_table(
        validation_queue,
        [
            "priority_band",
            "validation_type",
            "input_family",
            "field_key",
            "coverage_status",
            "reference_count",
            "affected_section_count",
            "derived_lineage",
            "validation_decision",
        ],
        30,
    ) + "</div>"


def _workbench_backlog_table(blockers: pd.DataFrame) -> str:
    if blockers is None or blockers.empty:
        return "<p class='subtle'>No hard blockers.</p>"
    grouped = (
        blockers.groupby(["input_family_hint", "field_key", "coverage_status"], dropna=False)
        .agg(
            reference_count=("reference_count", "sum"),
            section_count=("source_section_id", "nunique"),
            affected_sections=("source_section_id", lambda values: "|".join(sorted({_clean_cell(value) for value in values if _clean_cell(value)})[:8])),
            example_scripts=("example_scripts", lambda values: "|".join(_unique_pipe_values(list(values))[:8])),
            data_team_action=("data_team_action", "first"),
        )
        .reset_index()
        .sort_values(["reference_count", "section_count"], ascending=False)
    )
    return "<div class='scroll'>" + _df_table(
        grouped,
        [
            "input_family_hint",
            "field_key",
            "coverage_status",
            "reference_count",
            "section_count",
            "affected_sections",
            "example_scripts",
            "data_team_action",
        ],
        30,
    ) + "</div>"


def _workbench_derived_table(derived: pd.DataFrame) -> str:
    if derived is None or derived.empty:
        return "<p class='subtle'>No derived evidence rows.</p>"
    grouped = (
        derived.groupby(["input_family_hint", "field_key"], dropna=False)
        .agg(
            reference_count=("reference_count", "sum"),
            section_count=("source_section_id", "nunique"),
            affected_sections=("source_section_id", lambda values: "|".join(sorted({_clean_cell(value) for value in values if _clean_cell(value)})[:8])),
            derived_lineage=("matched_source_columns", lambda values: "|".join(_unique_pipe_values(list(values))[:10])),
            analyst_action=("analyst_action", "first"),
        )
        .reset_index()
        .sort_values(["reference_count", "section_count"], ascending=False)
    )
    return "<div class='scroll'>" + _df_table(
        grouped,
        [
            "input_family_hint",
            "field_key",
            "reference_count",
            "section_count",
            "affected_sections",
            "derived_lineage",
            "analyst_action",
        ],
        30,
    ) + "</div>"


def _workbench_section_table(sections: pd.DataFrame) -> str:
    if sections is None or sections.empty:
        return "<p class='subtle'>No section rows.</p>"
    view = sections.sort_values(["blocker_field_count", "review_field_count"], ascending=False)
    return "<div class='scroll'>" + _df_table(
        view,
        [
            "source_section_id",
            "domain_name",
            "display_name",
            "section_review_status",
            "mapped_field_count",
            "review_field_count",
            "blocker_field_count",
            "top_blocker_fields",
            "top_review_fields",
            "data_team_next_step",
        ],
        30,
    ) + "</div>"


def _analysis_domain_rows(domain_map: pd.DataFrame, section_review: pd.DataFrame) -> list[dict[str, Any]]:
    domain_lookup: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    if domain_map is not None and not domain_map.empty:
        for item in domain_map.sort_values("domain_rank").to_dict("records"):
            name = _clean_cell(item.get("domain_name"))
            if name:
                domain_lookup[name] = item
                order.append(name)
    if section_review is not None and not section_review.empty:
        for name in section_review["domain_name"].dropna().astype(str).unique():
            if name not in order:
                order.append(name)

    rows = []
    for name in order:
        domain = domain_lookup.get(name, {})
        review_rows = (
            section_review[section_review["domain_name"].astype(str).eq(name)].copy()
            if section_review is not None and not section_review.empty
            else pd.DataFrame()
        )
        mapped = int(review_rows["mapped_field_count"].sum()) if "mapped_field_count" in review_rows else 0
        needs_review = int(review_rows["review_field_count"].sum()) if "review_field_count" in review_rows else 0
        blocked = int(review_rows["blocker_field_count"].sum()) if "blocker_field_count" in review_rows else 0
        status_counts = {"ready": 0, "validate": 0, "blocked": 0}
        if not review_rows.empty and "section_review_status" in review_rows:
            for status in review_rows["section_review_status"].fillna(""):
                status_counts[_section_status_bucket(status)] += 1
        outputs = _unique_pipe_values(
            review_rows["generated_output_files"] if "generated_output_files" in review_rows else [],
            _clean_cell(domain.get("generated_output_files")),
        )
        sections = []
        if not review_rows.empty:
            for item in review_rows.sort_values("review_rank").to_dict("records"):
                sections.append(
                    {
                        "id": _clean_cell(item.get("source_section_id")),
                        "name": _clean_cell(item.get("display_name")),
                        "status": _clean_cell(item.get("section_review_status")),
                    }
                )
        rows.append(
            {
                "domain": name,
                "rank": int(_to_float(domain.get("domain_rank"), default=len(rows) + 1)),
                "business_question": _clean_cell(domain.get("business_question")),
                "consulting_use": _clean_cell(domain.get("consulting_use")),
                "required_inputs": _clean_cell(domain.get("required_input_families")),
                "next_decision": _clean_cell(domain.get("next_decision")),
                "section_count": len(review_rows) if not review_rows.empty else int(_to_float(domain.get("section_count"), default=0)),
                "mapped": mapped,
                "review": needs_review,
                "blocked": blocked,
                "total_fields": mapped + needs_review + blocked,
                "ready_sections": status_counts["ready"],
                "validate_sections": status_counts["validate"],
                "blocked_sections": status_counts["blocked"],
                "outputs": outputs,
                "sections": sections,
            }
        )
    return rows


def _domain_field_coverage_chart(rows: list[dict[str, Any]]) -> str:
    legend = "<div class='legend'><span class='mapped'>Mapped</span><span class='review'>Needs review</span><span class='blocked'>Blocked</span></div>"
    body = []
    for row in rows:
        total = max(row["total_fields"], 1)
        body.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(row['domain'])}</div>"
            "<div class='bar-track'>"
            f"<span class='bar-fill seg mapped' style='width:{_pct(row['mapped'], total)}%'></span>"
            f"<span class='bar-fill seg review' style='width:{_pct(row['review'], total)}%'></span>"
            f"<span class='bar-fill seg blocked' style='width:{_pct(row['blocked'], total)}%'></span>"
            "</div>"
            f"<div class='bar-value'>{row['mapped']}/{row['review']}/{row['blocked']}</div>"
            "</div>"
        )
    return legend + "".join(body)


def _domain_section_status_chart(rows: list[dict[str, Any]]) -> str:
    legend = "<div class='legend'><span class='ready'>Ready</span><span class='validate'>Validate</span><span class='blocked'>Blocked</span></div>"
    body = []
    for row in rows:
        total = max(row["ready_sections"] + row["validate_sections"] + row["blocked_sections"], 1)
        body.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(row['domain'])}</div>"
            "<div class='bar-track'>"
            f"<span class='bar-fill seg ready' style='width:{_pct(row['ready_sections'], total)}%'></span>"
            f"<span class='bar-fill seg validate' style='width:{_pct(row['validate_sections'], total)}%'></span>"
            f"<span class='bar-fill seg blocked' style='width:{_pct(row['blocked_sections'], total)}%'></span>"
            "</div>"
            f"<div class='bar-value'>{row['ready_sections']}/{row['validate_sections']}/{row['blocked_sections']}</div>"
            "</div>"
        )
    return legend + "".join(body)


def _source_layout_chart(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No source layout profile rows.</p>"
    counts = df["canonical_mapping_status"].fillna("unknown").value_counts().to_dict()
    rows = _count_chart_rows(counts)
    table = _df_table(
        df,
        ["file_name", "source_column", "matched_canonical_fields", "canonical_mapping_status", "column_role_guess", "mapping_action"],
        12,
    )
    return rows + "<div class='scroll' style='margin-top:12px;'>" + table + "</div>"


def _package_layer_chart(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No package index rows.</p>"
    counts = df["analysis_layer"].fillna("Unknown").value_counts().to_dict()
    return _count_chart_rows(counts)


def _opportunity_chart(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No opportunity portfolio rows.</p>"
    view = df.sort_values("expected_value", ascending=False).head(8)
    max_value = max((_to_float(value) for value in view["expected_value"]), default=1)
    rows = []
    for item in view.to_dict("records"):
        value = _to_float(item.get("expected_value"))
        label = _clean_cell(item.get("play_name"))
        accounts = int(_to_float(item.get("target_accounts")))
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(label)}<br><span class='subtle'>{accounts} accounts</span></div>"
            f"<div class='bar-track'><span class='bar-fill teal' style='width:{_pct(value, max_value)}%'></span></div>"
            f"<div class='bar-value'>{_currency(value)}</div>"
            "</div>"
        )
    return "".join(rows)


def _counterparty_chart(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No counterparty summary rows.</p>"
    view = df.assign(_abs_amount=df["total_amount"].map(lambda value: abs(_to_float(value)))).sort_values("_abs_amount", ascending=False).head(8)
    max_value = max((_to_float(value) for value in view["_abs_amount"]), default=1)
    rows = []
    for item in view.to_dict("records"):
        value = _to_float(item.get("_abs_amount"))
        label = _clean_cell(item.get("counterparty_name"))
        category = _clean_cell(item.get("counterparty_category"))
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(label)}<br><span class='subtle'>{escape(category)}</span></div>"
            f"<div class='bar-track'><span class='bar-fill violet' style='width:{_pct(value, max_value)}%'></span></div>"
            f"<div class='bar-value'>{_currency(value)}</div>"
            "</div>"
        )
    return "".join(rows)


def _outcome_chart(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No outcome summary rows.</p>"
    view = df.sort_values("test_outcome_rate", ascending=False).head(8)
    rows = []
    for item in view.to_dict("records"):
        rate = _to_float(item.get("test_outcome_rate"))
        label = _clean_cell(item.get("play_name"))
        targets = int(_to_float(item.get("target_accounts")))
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(label)}<br><span class='subtle'>{targets} targets</span></div>"
            f"<div class='bar-track'><span class='bar-fill teal' style='width:{_pct(rate, 1)}%'></span></div>"
            f"<div class='bar-value'>{_percent(rate)}</div>"
            "</div>"
        )
    return "".join(rows)


def _scorecard_chart(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No executive scorecard rows.</p>"
    view = df.sort_values("score", ascending=False).head(8)
    rows = []
    for item in view.to_dict("records"):
        score = _to_float(item.get("score"))
        domain = _clean_cell(item.get("domain"))
        status = _clean_cell(item.get("rag_status"))
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(domain)}<br>{_status_badge(status)}</div>"
            f"<div class='bar-track'><span class='bar-fill' style='width:{_pct(score, 100)}%'></span></div>"
            f"<div class='bar-value'>{score:,.1f}</div>"
            "</div>"
        )
    return "".join(rows)


def _lineage_stage_cards(stage_summary: pd.DataFrame) -> str:
    if stage_summary is None or stage_summary.empty:
        return "<p class='subtle'>No lineage stages generated.</p>"
    cards = []
    for row in stage_summary.to_dict("records"):
        stage = _clean_cell(row.get("lineage_stage"))
        edge_count = int(_to_float(row.get("edge_count")))
        ready_count = int(_to_float(row.get("ready_or_review_edges")))
        cards.append(
            "<div class='stage-card'>"
            f"<b>{escape(stage)}</b>"
            f"<small>{edge_count:,} edge(s); {ready_count:,} ready/review edge(s)</small>"
            "</div>"
        )
    return "<div class='stage-grid'>" + "".join(cards) + "</div>"


def _domain_analysis_cards(rows: list[dict[str, Any]], output_dir: Path) -> str:
    cards = []
    for row in rows:
        status = _domain_status(row)
        output_links = _artifact_links(row["outputs"], output_dir)
        section_lines = "".join(
            "<tr>"
            f"<td><code>{escape(section['id'])}</code></td>"
            f"<td>{escape(section['name'])}</td>"
            f"<td>{_status_badge(section['status'])}</td>"
            "</tr>"
            for section in row["sections"]
        )
        cards.append(
            "<article class='domain-card'>"
            "<header>"
            f"<h3>{escape(row['domain'])}</h3>"
            f"{_status_badge(status)}"
            "</header>"
            f"<p class='subtle'>{escape(row['business_question'])}</p>"
            "<div class='bar-row' style='grid-template-columns: 96px minmax(90px, 1fr) 74px;'>"
            "<div class='bar-label'>Fields</div>"
            "<div class='bar-track'>"
            f"<span class='bar-fill seg mapped' style='width:{_pct(row['mapped'], max(row['total_fields'], 1))}%'></span>"
            f"<span class='bar-fill seg review' style='width:{_pct(row['review'], max(row['total_fields'], 1))}%'></span>"
            f"<span class='bar-fill seg blocked' style='width:{_pct(row['blocked'], max(row['total_fields'], 1))}%'></span>"
            "</div>"
            f"<div class='bar-value'>{row['total_fields']}</div>"
            "</div>"
            f"<p class='subtle'><b>Inputs:</b> {escape(row['required_inputs'])}</p>"
            f"<p class='subtle'><b>Consulting use:</b> {escape(row['consulting_use'])}</p>"
            f"<p class='subtle'><b>Next decision:</b> {escape(row['next_decision'])}</p>"
            f"<div class='chip-row'>{output_links}</div>"
            "<details>"
            f"<summary>{row['section_count']} analysis sections</summary>"
            "<div class='scroll' style='margin-top:8px;'>"
            "<table><thead><tr><th>Section</th><th>Name</th><th>Status</th></tr></thead><tbody>"
            f"{section_lines}"
            "</tbody></table>"
            "</div>"
            "</details>"
            "</article>"
        )
    return "<div class='domain-list'>" + "".join(cards) + "</div>"


def _section_evidence_table(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "<p class='subtle'>No section evidence rows.</p>"
    columns = [
        "source_section_id",
        "domain_name",
        "display_name",
        "section_review_status",
        "mapped_field_count",
        "review_field_count",
        "blocker_field_count",
        "business_question",
        "top_blocker_fields",
        "generated_output_files",
    ]
    return "<div class='scroll section-table'>" + _df_table(df, columns, 30) + "</div>"


def _count_chart_rows(counts: dict[str, int]) -> str:
    if not counts:
        return "<p class='subtle'>No rows.</p>"
    maximum = max(counts.values()) or 1
    rows = []
    for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(str(label))}</div>"
            f"<div class='bar-track'><span class='bar-fill' style='width:{_pct(count, maximum)}%'></span></div>"
            f"<div class='bar-value'>{count}</div>"
            "</div>"
        )
    return "".join(rows)


def _artifact_links(names: list[str], output_dir: Path) -> str:
    if not names:
        return "<span>No generated files</span>"
    links = []
    for name in names[:10]:
        path = output_dir / name
        if path.exists():
            links.append(f"<a href='{_file_url(path)}'>{escape(name)}</a>")
        else:
            links.append(f"<span>{escape(name)}</span>")
    if len(names) > 10:
        links.append(f"<span>+{len(names) - 10} more</span>")
    return "".join(links)


def _truthy_count(series: pd.Series) -> int:
    if series is None or series.empty:
        return 0
    return int(series.map(lambda value: _clean_cell(value).lower() in {"true", "1", "yes", "y"}).sum())


def _count_equals(df: pd.DataFrame, column: str, value: str) -> int:
    if df is None or df.empty or column not in df.columns:
        return 0
    return int(df[column].map(lambda item: _clean_cell(item) == value).sum())


def _numeric_sum(df: pd.DataFrame, column: str) -> int:
    if df is None or df.empty or column not in df.columns:
        return 0
    return int(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _count_table(df: pd.DataFrame, group_column: str, value_column: str) -> pd.DataFrame:
    if df is None or df.empty or group_column not in df.columns:
        return pd.DataFrame(columns=[group_column, value_column])
    grouped = (
        df.assign(**{group_column: df[group_column].map(lambda value: _clean_cell(value) or "blank")})
        .groupby(group_column, dropna=False)
        .size()
        .reset_index(name=value_column)
        .sort_values(value_column, ascending=False)
    )
    return grouped


def _layout_gap_summary(layout_gaps: pd.DataFrame) -> pd.DataFrame:
    if layout_gaps is None or layout_gaps.empty or "mapping_status" not in layout_gaps.columns:
        return pd.DataFrame(columns=["mapping_status", "field_count"])
    return (
        layout_gaps.assign(mapping_status=layout_gaps["mapping_status"].map(lambda value: _clean_cell(value) or "blank"))
        .groupby("mapping_status", dropna=False)
        .size()
        .reset_index(name="field_count")
        .sort_values("field_count", ascending=False)
    )


def _intake_backlog(backlog: pd.DataFrame) -> pd.DataFrame:
    if backlog is None or backlog.empty or "workstream" not in backlog.columns:
        return pd.DataFrame()
    workstreams = {"Monthly intake", "Data contracts / Snowflake"}
    view = backlog[backlog["workstream"].isin(workstreams)].copy()
    if view.empty:
        return view
    return view.sort_values(["priority_band", "backlog_rank"]).head(80)


def _intake_direct_links(items: list[tuple[str, Path]]) -> str:
    links = []
    for label, path in items:
        if path.exists():
            links.append(f"<a href='{_file_url(path)}'>{escape(label)}</a>")
    return "<div class='link-grid'>" + "".join(links) + "</div>"


def _intake_bar_chart(df: pd.DataFrame, label_col: str, value_col: str, color_class: str) -> str:
    if df is None or df.empty or label_col not in df.columns or value_col not in df.columns:
        return "<p class='subtle'>No rows.</p>"
    maximum = max((_to_float(value) for value in df[value_col]), default=1.0)
    rows = []
    for item in df.head(12).to_dict("records"):
        label = _clean_cell(item.get(label_col))
        value = _to_float(item.get(value_col))
        rows.append(
            "<div class='bar-row'>"
            f"<div class='bar-label'>{escape(label)}</div>"
            f"<div class='bar-track'><span class='bar-fill {color_class}' style='width:{_pct(value, maximum)}%'></span></div>"
            f"<div class='bar-value'>{_format_count(value)}</div>"
            "</div>"
        )
    return "".join(rows)


def _story_card_list(items: list[Any]) -> str:
    if not items:
        return "<p class='subtle'>No conversation guide generated.</p>"
    cards = []
    for index, item in enumerate(items, start=1):
        cards.append(
            "<div class='story-card'>"
            f"<b>{index}. {escape(_clean_cell(item))}</b>"
            "</div>"
        )
    return "<div class='card-list'>" + "".join(cards) + "</div>"


def _question_list(items: list[Any]) -> str:
    if not items:
        return "<p class='subtle'>No decision questions generated.</p>"
    return "<ol class='question-list'>" + "".join(
        f"<li>{escape(_clean_cell(item))}</li>" for item in items
    ) + "</ol>"


def _story_arc_cards(story_arc: pd.DataFrame, output_dir: Path) -> str:
    if story_arc is None or story_arc.empty:
        return "<p class='subtle'>No story arc generated.</p>"
    cards = []
    for row in story_arc.to_dict("records"):
        artifact_names = _split_pipe(row.get("artifact"))
        cards.append(
            "<article class='story-card'>"
            f"<b>{escape(_clean_cell(row.get('step')))}</b>"
            f"<p>{escape(_clean_cell(row.get('summary')))}</p>"
            f"<div class='links'>{_artifact_links(artifact_names, output_dir)}</div>"
            "</article>"
        )
    return "<div class='card-list'>" + "".join(cards) + "</div>"


def _metric(label: str, value: Any) -> str:
    return f"<div class='metric'><span>{escape(label)}</span><strong>{escape(_format_count(value))}</strong></div>"


def _domain_status(row: dict[str, Any]) -> str:
    if row["blocked_sections"]:
        return "blocked"
    if row["validate_sections"]:
        return "validate"
    return "ready"


def _status_badge(status: str) -> str:
    bucket = _section_status_bucket(status)
    label = _status_label(status, bucket)
    return f"<span class='status {bucket}'>{escape(label)}</span>"


def _section_status_bucket(status: Any) -> str:
    value = _clean_cell(status).lower()
    if "blocked" in value:
        return "blocked"
    if "validate" in value or "review" in value or "qualified" in value:
        return "validate"
    return "ready"


def _status_label(status: Any, bucket: str) -> str:
    value = _clean_cell(status)
    if value:
        return value.replace("_", " ")
    return {"ready": "ready", "validate": "validate", "blocked": "blocked"}[bucket]


def _unique_pipe_values(series: Any, fallback: str = "") -> list[str]:
    values: list[str] = []
    if fallback:
        values.extend(_split_pipe(fallback))
    if isinstance(series, pd.Series):
        for item in series.dropna():
            values.extend(_split_pipe(item))
    elif isinstance(series, list):
        values.extend(series)
    seen = set()
    unique = []
    for value in values:
        item = _clean_cell(value)
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _split_pipe(value: Any) -> list[str]:
    text = _clean_cell(value)
    if not text:
        return []
    return [item.strip() for item in text.split("|") if item.strip()]


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value)
    return "" if text.lower() == "nan" else text


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct(value: Any, maximum: Any) -> float:
    denominator = _to_float(maximum, default=1.0)
    if denominator <= 0:
        return 0.0
    return max(0.0, min(100.0, round((_to_float(value) / denominator) * 100, 1)))


def _currency(value: Any) -> str:
    return f"${_to_float(value):,.0f}"


def _percent(value: Any) -> str:
    return f"{_to_float(value) * 100:,.0f}%"


def _format_count(value: Any) -> str:
    return f"{_to_float(value):,.0f}"


def _artifact_rows(june_dir: Path, july_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for name, (layer, purpose) in ARTIFACT_GUIDE.items():
        june_path = june_dir / name
        july_path = july_dir / name
        rows.append(
            {
                "file": name,
                "layer": layer,
                "purpose": purpose,
                "june_path": june_path,
                "july_path": july_path,
                "june_rows": _row_count(june_path),
                "july_rows": _row_count(july_path),
            }
        )
    return rows


def _function_rows() -> list[dict[str, Any]]:
    purposes = {
        "build_intake_work_order": "Turns layout profiling into operator decisions.",
        "build_layout_gap_report": "Analyzes canonical field coverage and mapping gaps for every received file.",
        "build_layout_contract_draft_queue": "Rolls source-column evidence into one layout-contract action, alias map, and YAML draft per received file.",
        "build_layout_contract_export_manifest": "Turns layout-contract draft rows into a manifest of generated YAML files that can be promoted into data contracts.",
        "build_monthly_file_requirements": "Creates the monthly data-team checklist of expected input families, received files, selected files, Snowflake targets, contract actions, and missing field work.",
        "build_intelligence_lineage_graph": "Creates end-to-end lineage edges from raw files through analysis outputs, charts, actions, roles, and decisions.",
        "build_analysis_chart_data_snapshot": "Materializes the top data points, sample records, row counts, numeric summary, and callout behind every chart spec.",
        "build_intelligence_metric_catalog": "Creates the semantic metric catalog tying chart/output fields to definitions, source artifacts, validation status, model rules, and CSM interpretation.",
        "build_analysis_consulting_playbook": "Maps each analysis section to the client story role, proof chart/output, CSM talk track, analyst validation focus, and data-team dependency.",
        "build_analysis_insight_brief": "Creates a data-backed CSM/analyst brief per section using chart callouts, semantic metrics, caveats, and next questions.",
        "build_client_meeting_deck_blueprint": "Creates the ordered client meeting/deck sequence from story, scorecard, section briefs, actions, roadmap, measurement, and handoffs.",
        "build_analysis_review_board": "Rolls each analysis section into one review row with scripts, chart/graph outputs, metrics, insights, caveats, Snowflake targets, and meeting-story placement.",
        "build_account_month_features": "Creates the canonical account-month feature table.",
        "build_account_intelligence_profile": "Consolidates account-level diagnosis, evidence, top play, and recommended action.",
        "build_model_rulebook": "Catalogs rule families, thresholds, source artifacts, evidence fields, and consulting use.",
        "build_account_scoring_trace": "Creates account-level explainability rows that trace PFI, segment, and top-play decisions.",
        "classify_pfi": "Scores primary/split/competitor-primary relationship status.",
        "build_counterparty_signals": "Extracts named payroll, competitor, payment, and lender counterparties.",
        "build_counterparty_summary": "Rolls counterparties up for strategy and threat diagnosis.",
        "score_opportunities": "Creates ranked account-level opportunity rows.",
        "build_relationship_segments": "Names relationship state and next-best motion by account.",
        "build_segment_summary": "Aggregates relationship segments for consulting prioritization.",
        "build_opportunity_portfolio": "Converts account opportunities into strategic plays.",
        "build_executive_scorecard": "Builds domain-level RAG/status scorecard.",
        "build_strategy_roadmap": "Sequences consulting actions into now/next/later roadmap.",
        "build_action_plan": "Creates role-owned actions, channels, and talk tracks.",
        "build_measurement_plan": "Defines test design, primary metrics, and measurement windows.",
        "build_campaign_targets": "Exports account-level activation audiences.",
        "build_stakeholder_exports": "Creates role-specific execution exports for CSM, analyst, marketing, banker, and data-team use.",
        "build_engine_run_ledger": "Creates the operator-facing run ledger across intake, scoring, consulting, exports, and warehouse handoff.",
        "build_measurement_baseline": "Stores baseline metrics by action for later comparison.",
        "evaluate_outcomes": "Compares prior targets to current account-month behavior.",
        "build_outcome_summary": "Aggregates measured outcomes by action.",
        "build_intelligence_delta_report": "Compares the current package to a prior package across quality, accounts, opportunities, and portfolio movement.",
        "build_consulting_insight_register": "Creates a tabular consulting register across opportunity insights, scorecard signals, story steps, evidence, and next decisions.",
        "build_role_handoffs": "Maps output artifacts to CSM, analyst, banker, marketing, exec next steps.",
        "build_operating_control_plane": "Creates the role-by-role control plane for decisions, open-first artifacts, blockers, exports, and next actions.",
        "build_user_interaction_map": "Creates the role-to-output manifest showing what each user opens, how data is delivered, which decision it supports, and what happens next.",
        "build_production_readiness_backlog": "Creates the productization work queue across readiness blockers, data mapping, metric validation, layout contracts, analysis review, user delivery, acceptance criteria, and Snowflake targets.",
        "build_analysis_package_index": "Creates the package artifact inventory across files, layers, consumers, row counts, and Snowflake targets.",
        "build_analysis_section_catalog": "Maps existing ARS/TXN analysis sections to engine layers and opportunity types.",
        "build_analysis_script_catalog": "Inventories current analysis scripts with source paths, topics, and output roles.",
        "build_analysis_provenance_map": "Links opportunity models back to the analysis sections that support them.",
        "build_analysis_execution_map": "Maps each analysis section to current-run evidence, generated outputs, missing evidence, and analyst next steps.",
        "build_analysis_layout_coverage_matrix": "Compares actual script field references to current layout and contract evidence.",
        "build_analysis_section_evidence_review": "Summarizes each analysis section's evidence, output support, field coverage, blockers, and next steps.",
        "build_consulting_story": "Creates the narrative arc for client conversation.",
        "run_transactional_intelligence": "Runs the complete analysis pipeline.",
        "write_snowflake_package": "Writes manifest and SQL for Snowflake loading.",
    }
    rows = []
    for func in FUNCTIONS:
        path = Path(inspect.getsourcefile(func) or "")
        line = inspect.getsourcelines(func)[1]
        rows.append(
            {
                "name": func.__name__,
                "path": path,
                "line": line,
                "purpose": purposes.get(func.__name__, ""),
            }
        )
    return rows


def _analysis_section_counts() -> dict[str, int]:
    analytics_dir = _REPO / "01_Analysis" / "00-Scripts" / "analytics"
    counts = {}
    for path in sorted(analytics_dir.iterdir()):
        if path.is_dir() and not path.name.startswith("__"):
            counts[path.name] = len(list(path.glob("*.py")))
    return counts


def _raw_inputs_table(raw_dir: Path) -> str:
    rows = []
    for path in sorted(raw_dir.glob("*.csv")):
        rows.append(
            "<tr>"
            f"<td><a href='{_file_url(path)}'>{escape(path.name)}</a></td>"
            f"<td>{_row_count(path)}</td>"
            f"<td>{escape(_repo_rel(path))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>File</th><th>Rows</th><th>Path</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _functions_table(functions: list[dict[str, Any]]) -> str:
    rows = []
    for item in functions:
        path = Path(item["path"])
        rows.append(
            "<tr>"
            f"<td><code>{escape(item['name'])}</code></td>"
            f"<td><a href='{_file_url(path)}'>{escape(_repo_rel(path))}:{item['line']}</a></td>"
            f"<td>{escape(item['purpose'])}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Function</th><th>Source</th><th>Purpose</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _artifact_table(rows_data: list[dict[str, Any]]) -> str:
    rows = []
    for item in rows_data:
        rows.append(
            "<tr>"
            f"<td><code>{escape(item['file'])}</code></td>"
            f"<td>{escape(item['layer'])}</td>"
            f"<td><a href='{_file_url(item['june_path'])}'>{item['june_rows']}</a></td>"
            f"<td><a href='{_file_url(item['july_path'])}'>{item['july_rows']}</a></td>"
            f"<td>{escape(item['purpose'])}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Artifact</th><th>Layer</th><th>June rows</th><th>July rows</th><th>Purpose</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _sections_table(sections: dict[str, int]) -> str:
    rows = [
        f"<tr><td><code>{escape(section)}</code></td><td>{count}</td></tr>"
        for section, count in sections.items()
    ]
    return "<table><thead><tr><th>Section folder</th><th>Script count</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _df_table(df: pd.DataFrame, columns: list[str], limit: int) -> str:
    if df is None or df.empty:
        return "<p class='small'>No rows.</p>"
    view = df[[col for col in columns if col in df.columns]].head(limit).copy()
    header = "".join(f"<th>{escape(str(col))}</th>" for col in view.columns)
    body_rows = []
    for row in view.to_dict("records"):
        body_rows.append(
            "<tr>" + "".join(f"<td>{escape(_fmt(value))}</td>" for value in row.values()) + "</tr>"
        )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _story_block(story: dict[str, Any]) -> str:
    headline = escape(str(story.get("headline", "")))
    summary = escape(str(story.get("executive_summary", "")))
    arc = story.get("story_arc", [])
    rows = []
    for item in arc:
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('step', '')))}</td>"
            f"<td>{escape(str(item.get('summary', '')))}</td>"
            f"<td><code>{escape(str(item.get('artifact', '')))}</code></td>"
            "</tr>"
        )
    table = "<table><thead><tr><th>Story step</th><th>Summary</th><th>Artifact</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    return f"<div class='panel'><h3>{headline}</h3><p>{summary}</p>{table}</div>"


def _row_count(path: Path) -> int:
    if not path.exists():
        return 0
    if path.suffix.lower() == ".csv":
        return len(pd.read_csv(path))
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return len(data) if isinstance(data, list) else 1
    return 1


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(_REPO))
    except ValueError:
        return str(path)


def _fmt(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
