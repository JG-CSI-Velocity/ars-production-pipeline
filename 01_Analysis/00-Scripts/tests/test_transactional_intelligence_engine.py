from pathlib import Path
import json

import pandas as pd

from ars_engine.intelligence.cli import main as intelligence_cli_main
from ars_engine.intelligence import (
    EngineConfig,
    assemble_file_drop,
    build_analysis_provenance_map,
    build_analysis_script_catalog,
    build_analysis_section_catalog,
    build_intake_work_order,
    build_account_month_features,
    build_counterparty_signals,
    build_counterparty_summary,
    build_file_assembly_plan,
    build_relationship_segments,
    build_segment_summary,
    build_layout_gap_report,
    classify_pfi,
    profile_input_files,
    read_input_table,
    run_transactional_intelligence,
    score_opportunities,
    write_snowflake_package,
)
from tools.generate_intelligence_demo import main as generate_intelligence_demo_main

REPO_ROOT = Path(__file__).resolve().parents[3]


def _accounts():
    return pd.DataFrame(
        [
            {
                "Account Number": "100",
                "Avg Bal": 12000,
                "Debit?": "Y",
                "Business?": "N",
                "Branch": "Main",
                "Product Code": "CHK",
                "Date Opened": "2020-01-01",
            },
            {
                "Account Number": "200",
                "Avg Bal": 250,
                "Debit?": "N",
                "Business?": "N",
                "Branch": "West",
                "Product Code": "SAV",
                "Date Opened": "2024-03-10",
            },
            {
                "Account Number": "300",
                "Avg Bal": 8000,
                "Debit?": "Y",
                "Business?": "Y",
                "Branch": "Main",
                "Product Code": "BUS",
                "Date Opened": "2022-06-05",
            },
        ]
    )


def _transactions():
    return pd.DataFrame(
        [
            {
                "primary_account_num": "100",
                "transaction_date": "2026-06-03",
                "amount": 3500,
                "description": "ADP Payroll Direct Deposit",
                "transaction_type": "ACH Credit",
            },
            {
                "primary_account_num": "100",
                "transaction_date": "2026-06-05",
                "amount": -95,
                "description": "Grocery Store",
                "transaction_type": "Debit Card",
            },
            {
                "primary_account_num": "100",
                "transaction_date": "2026-06-08",
                "amount": -2200,
                "description": "Chase Bank Transfer",
                "transaction_type": "ACH Debit",
            },
            {
                "primary_account_num": "200",
                "transaction_date": "2026-06-10",
                "amount": 800,
                "description": "Remote Deposit",
                "transaction_type": "ACH Credit",
            },
            {
                "primary_account_num": "200",
                "transaction_date": "2026-06-12",
                "amount": -100,
                "description": "Wells Fargo Payment",
                "transaction_type": "ACH Debit",
            },
            {
                "primary_account_num": "300",
                "transaction_date": "2026-06-14",
                "amount": -1250,
                "description": "Rocket Mortgage",
                "transaction_type": "ACH Debit",
            },
        ]
    )


def _write_custom_contract_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "odd_extract.v1.yml").write_text(
        (REPO_ROOT / "data_contracts" / "odd_extract.v1.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (path / "txn_client_payments.v1.yml").write_text(
        """
contract_id: txn.client_payments.v1
source_family: transaction
display_name: Client payments transaction file
version: "1"
status: draft
match:
  filename_patterns:
    - "*payments*"
  extensions:
    - csv
  header:
    mode: header_row
    header_row: 1
  positional: false
canonical_fields:
  transaction_date:
    required: true
    type: date
    aliases: ["transaction_date"]
  account_id:
    required: true
    type: string
    aliases: ["primary_account_num"]
  transaction_type:
    required: true
    type: string
    aliases: ["transaction_type"]
  amount:
    required: true
    type: decimal
    aliases: ["amount"]
  merchant_name:
    required: false
    type: string
    aliases: ["description"]
""".lstrip(),
        encoding="utf-8",
    )
    return path


def test_feature_mart_detects_payroll_external_fi_and_account_match():
    features = build_account_month_features(
        _accounts(),
        _transactions(),
        EngineConfig(client_id="test", period_month="2026.06"),
    )

    acct_100 = features[features["account_id"] == "100"].iloc[0]
    acct_200 = features[features["account_id"] == "200"].iloc[0]

    assert acct_100["period_month"] == "2026-06"
    assert bool(acct_100["matched_account"]) is True
    assert acct_100["payroll_count"] == 1
    assert acct_100["external_fi_count"] == 1
    assert acct_100["card_txn_count"] == 1
    assert acct_100["card_amount"] == 95
    assert acct_100["pin_txn_count"] == 0
    assert acct_100["sig_txn_count"] == 0
    assert acct_100["avg_ticket_amount"] > 0
    assert bool(acct_100["payroll_detected"]) is True
    assert bool(acct_200["has_debit"]) is False


def test_pfi_and_opportunities_are_reason_coded():
    cfg = EngineConfig(client_id="test", period_month="2026.06")
    features = build_account_month_features(_accounts(), _transactions(), cfg)
    pfi = classify_pfi(features, cfg)
    counterparty_signals = build_counterparty_signals(_transactions(), cfg)
    counterparty_summary = build_counterparty_summary(counterparty_signals, cfg)
    opportunities = score_opportunities(features, pfi, cfg)
    segments = build_relationship_segments(features, pfi, opportunities, cfg)
    segment_summary = build_segment_summary(segments, opportunities, cfg)

    assert {"account_id", "pfi_verdict", "confidence", "reason_codes"}.issubset(pfi.columns)
    assert pfi["pfi_verdict"].isin(
        ["Primary with us", "Split", "Competitor-primary", "No verdict"]
    ).all()
    assert not opportunities.empty
    assert {"opportunity_type", "priority_score", "recommended_action"}.issubset(
        opportunities.columns
    )
    assert "deposit_retention" in set(opportunities["opportunity_type"])
    assert opportunities["priority_score"].is_monotonic_decreasing
    assert not counterparty_signals.empty
    assert not counterparty_summary.empty
    assert {"counterparty_name", "counterparty_category", "relationship_signal"}.issubset(
        counterparty_signals.columns
    )
    assert {"payroll", "external_fi", "financial_services"} & set(counterparty_signals["counterparty_category"])
    assert {"account_count", "total_amount", "strategy_relevance"}.issubset(counterparty_summary.columns)
    assert not segments.empty
    assert not segment_summary.empty
    assert {"relationship_segment", "segment_group", "next_best_motion"}.issubset(segments.columns)
    assert {"Primary Banking Conversion Candidate", "External Lending / Financial Services Relationship"} & set(
        segments["relationship_segment"]
    )
    assert {"account_count", "total_expected_value", "top_next_best_motion"}.issubset(segment_summary.columns)


def test_engine_writes_expected_artifacts(tmp_path: Path):
    outputs = run_transactional_intelligence(
        accounts=_accounts(),
        transactions=_transactions(),
        config=EngineConfig(client_id="test", period_month="2026.06"),
    )
    written = outputs.write(tmp_path)

    assert outputs.data_quality["transaction_rows"] == 6
    assert outputs.insights
    assert not outputs.counterparty_signals.empty
    assert not outputs.counterparty_summary.empty
    assert not outputs.account_intelligence_profile.empty
    assert not outputs.engine_run_ledger.empty
    assert not outputs.model_rulebook.empty
    assert not outputs.account_scoring_trace.empty
    assert not outputs.relationship_segments.empty
    assert not outputs.segment_summary.empty
    assert not outputs.opportunity_portfolio.empty
    assert not outputs.executive_scorecard.empty
    assert not outputs.strategy_roadmap.empty
    assert not outputs.action_plan.empty
    assert not outputs.measurement_plan.empty
    assert not outputs.campaign_targets.empty
    assert not outputs.csm_review_queue.empty
    assert not outputs.analyst_validation_queue.empty
    assert not outputs.marketing_activation_export.empty
    assert not outputs.banker_call_list.empty
    assert not outputs.stakeholder_export_manifest.empty
    assert not outputs.measurement_baseline.empty
    assert outputs.outcome_results.empty
    assert outputs.outcome_summary.empty
    assert not outputs.intelligence_delta_report.empty
    assert not outputs.consulting_insight_register.empty
    assert not outputs.role_handoffs.empty
    assert not outputs.operating_control_plane.empty
    assert not outputs.user_interaction_map.empty
    assert not outputs.production_readiness_backlog.empty
    assert not outputs.analysis_section_catalog.empty
    assert not outputs.analysis_script_catalog.empty
    assert not outputs.analysis_field_usage_catalog.empty
    assert not outputs.analysis_provenance_map.empty
    assert not outputs.analysis_execution_map.empty
    assert not outputs.analysis_domain_map.empty
    assert not outputs.analysis_input_dependency_map.empty
    assert not outputs.monthly_file_requirements.empty
    assert not outputs.analysis_layout_coverage_matrix.empty
    assert not outputs.analysis_feature_derivation_catalog.empty
    assert not outputs.analysis_data_team_backlog.empty
    assert not outputs.analysis_metric_validation_queue.empty
    assert not outputs.analysis_visual_output_map.empty
    assert not outputs.analysis_chart_spec_catalog.empty
    assert not outputs.analysis_chart_data_snapshot.empty
    assert not outputs.intelligence_metric_catalog.empty
    assert not outputs.analysis_section_evidence_review.empty
    assert not outputs.analysis_requirement_matrix.empty
    assert not outputs.analysis_consulting_playbook.empty
    assert not outputs.analysis_insight_brief.empty
    assert not outputs.client_meeting_deck_blueprint.empty
    assert not outputs.analysis_review_board.empty
    assert not outputs.engine_readiness_assessment.empty
    assert outputs.consulting_story["headline"]
    assert outputs.consulting_story["story_arc"]
    assert {"play_name", "target_accounts", "next_step"}.issubset(outputs.opportunity_portfolio.columns)
    assert {"account_id", "relationship_segment", "top_play_name", "recommended_action", "evidence_summary"}.issubset(
        outputs.account_intelligence_profile.columns
    )
    assert outputs.account_intelligence_profile["evidence_summary"].str.len().gt(0).all()
    assert {"run_stage", "status", "operator_action", "output_artifacts"}.issubset(
        outputs.engine_run_ledger.columns
    )
    assert {"intake", "scoring", "warehouse_handoff"} <= set(outputs.engine_run_ledger["run_stage"])
    assert {"readiness_area", "readiness_status", "client_use_status", "next_action"}.issubset(
        outputs.engine_readiness_assessment.columns
    )
    assert {"monthly_file_drop", "analysis_evidence_map", "snowflake_handoff"} <= set(
        outputs.engine_readiness_assessment["readiness_area"]
    )
    assert {"rule_id", "rule_family", "condition", "thresholds", "evidence_fields"}.issubset(
        outputs.model_rulebook.columns
    )
    assert {"PFI", "Opportunity", "Relationship Segment"} <= set(outputs.model_rulebook["rule_family"])
    assert {"trace_id", "account_id", "pfi_verdict", "top_opportunity_type", "decision_trace"}.issubset(
        outputs.account_scoring_trace.columns
    )
    assert outputs.account_scoring_trace["decision_trace"].str.len().gt(0).all()
    assert {"domain", "rag_status", "recommended_focus"}.issubset(outputs.executive_scorecard.columns)
    assert {"phase", "initiative", "proof_metric"}.issubset(outputs.strategy_roadmap.columns)
    assert "Data Trust" in set(outputs.executive_scorecard["domain"])
    assert {"action_id", "talk_track", "measurement_id"}.issubset(outputs.action_plan.columns)
    assert {"role", "decision_owned", "export_artifact", "first_action"}.issubset(outputs.role_handoffs.columns)
    assert {
        "workflow_lane",
        "role",
        "operating_question",
        "client_use_status",
        "open_first",
        "blocker_summary",
        "next_action",
    }.issubset(outputs.operating_control_plane.columns)
    assert {"Approve package", "Shape client story", "Load and publish data"} <= set(
        outputs.operating_control_plane["workflow_lane"]
    )
    assert "out.ti_operating_control_plane" in "|".join(outputs.operating_control_plane["snowflake_targets"])
    assert {
        "user_role",
        "workflow_lane",
        "primary_screen",
        "file_name",
        "decision_supported",
        "delivery_mode",
        "owner_next_action",
    }.issubset(outputs.user_interaction_map.columns)
    assert {"CSM", "Analyst"} & set(outputs.user_interaction_map["user_role"])
    assert "analysis_review_board.csv" in set(outputs.user_interaction_map["file_name"])
    assert {
        "workstream",
        "priority_band",
        "owner_role",
        "problem_statement",
        "required_action",
        "acceptance_criteria",
        "affected_outputs",
        "client_use_status",
    }.issubset(outputs.production_readiness_backlog.columns)
    assert {"P0", "P1"} & set(outputs.production_readiness_backlog["priority_band"])
    assert "analysis_review_board" in set(outputs.production_readiness_backlog["source_item_type"])
    assert {"source_section_id", "script_count", "analysis_family", "supports_opportunity_types"}.issubset(
        outputs.analysis_section_catalog.columns
    )
    assert {"source_section_id", "script_name", "source_path", "output_role"}.issubset(
        outputs.analysis_script_catalog.columns
    )
    assert {"field_reference", "input_family_hint", "canonical_field_hint", "line_number"}.issubset(
        outputs.analysis_field_usage_catalog.columns
    )
    assert "txn.payroll" in set(outputs.analysis_field_usage_catalog["source_section_id"])
    assert {"amount", "transaction_date", "primary_account_num"} & set(
        outputs.analysis_field_usage_catalog["field_reference"]
    )
    assert {"accounts", "transactions"} <= set(outputs.analysis_field_usage_catalog["input_family_hint"])
    assert {"opportunity_type", "source_section_id", "contribution"}.issubset(
        outputs.analysis_provenance_map.columns
    )
    assert {"source_section_id", "primary_engine_outputs", "evidence_status", "analyst_next_step"}.issubset(
        outputs.analysis_execution_map.columns
    )
    assert {"domain_id", "business_question", "required_input_families", "waits_for_client_layouts"}.issubset(
        outputs.analysis_domain_map.columns
    )
    assert {"portfolio_foundation", "competitive_leakage", "campaign_cohort_measurement"} <= set(
        outputs.analysis_domain_map["domain_id"]
    )
    assert outputs.analysis_domain_map["waits_for_client_layouts"].str.len().gt(0).all()
    assert {"input_family", "minimum_fields", "current_contract_status", "snowflake_design_decision"}.issubset(
        outputs.analysis_input_dependency_map.columns
    )
    assert {"accounts", "transactions", "campaign_history", "suppressions"} <= set(
        outputs.analysis_input_dependency_map["input_family"]
    )
    accounts_dep = outputs.analysis_input_dependency_map[
        outputs.analysis_input_dependency_map["input_family"].eq("accounts")
    ].iloc[0]
    campaign_dep = outputs.analysis_input_dependency_map[
        outputs.analysis_input_dependency_map["input_family"].eq("campaign_history")
    ].iloc[0]
    assert accounts_dep["current_run_readiness"] == "loaded_directly_no_file_profile"
    assert campaign_dep["current_run_readiness"] == "client_layout_needed"
    assert {
        "input_family",
        "requirement_level",
        "monthly_status",
        "received_file_names",
        "selected_file_names",
        "target_snowflake_layer",
        "data_team_action",
    }.issubset(outputs.monthly_file_requirements.columns)
    assert {"accounts", "transactions", "campaign_history", "suppressions"} <= set(
        outputs.monthly_file_requirements["input_family"]
    )
    account_req = outputs.monthly_file_requirements[
        outputs.monthly_file_requirements["input_family"].eq("accounts")
    ].iloc[0]
    campaign_req = outputs.monthly_file_requirements[
        outputs.monthly_file_requirements["input_family"].eq("campaign_history")
    ].iloc[0]
    assert account_req["monthly_status"] == "loaded_directly_no_profile"
    assert campaign_req["monthly_status"] == "missing_from_file_drop"
    assert {"source_section_id", "field_key", "coverage_status", "data_team_action"}.issubset(
        outputs.analysis_layout_coverage_matrix.columns
    )
    assert "txn.payroll" in set(outputs.analysis_layout_coverage_matrix["source_section_id"])
    assert {"mapped", "loaded_directly_unprofiled", "client_layout_needed"} & set(
        outputs.analysis_layout_coverage_matrix["coverage_status"]
    )
    assert "derived_engine_output_validate" in set(outputs.analysis_layout_coverage_matrix["coverage_status"])
    derived_payroll = outputs.analysis_layout_coverage_matrix[
        outputs.analysis_layout_coverage_matrix["source_section_id"].eq("txn.payroll")
        & outputs.analysis_layout_coverage_matrix["field_key"].eq("payroll_signal")
    ]
    assert not derived_payroll.empty
    assert "derived_engine_output_validate" in set(derived_payroll["coverage_status"])
    assert derived_payroll["matched_source_columns"].str.contains("derived:").any()
    assert {
        "source_section_id",
        "analysis_field_key",
        "derived_output_lineage",
        "derived_fields",
        "base_input_requirements",
        "snowflake_expression_hint",
    }.issubset(outputs.analysis_feature_derivation_catalog.columns)
    assert "payroll_signal" in set(outputs.analysis_feature_derivation_catalog["analysis_field_key"])
    assert outputs.analysis_feature_derivation_catalog["derived_output_lineage"].str.contains("derived:").any()
    assert {"input_family", "field_key", "priority_band", "data_team_action", "snowflake_design_action"}.issubset(
        outputs.analysis_data_team_backlog.columns
    )
    assert {"transactions", "campaign_history"} & set(outputs.analysis_data_team_backlog["input_family"])
    assert {"input_family", "field_key", "validation_type", "validation_decision"}.issubset(
        outputs.analysis_metric_validation_queue.columns
    )
    assert "derived_output_lineage" in set(outputs.analysis_metric_validation_queue["validation_type"])
    assert {"source_section_id", "output_file", "visual_type", "chart_readiness_status", "proof_artifacts"}.issubset(
        outputs.analysis_visual_output_map.columns
    )
    assert {"chart", "table", "story"} & set(outputs.analysis_visual_output_map["visual_mode"])
    assert {"source_section_id", "output_file", "chart_type", "x_field", "required_columns_present"}.issubset(
        outputs.analysis_chart_spec_catalog.columns
    )
    assert outputs.analysis_chart_spec_catalog["required_columns_present"].astype(bool).any()
    assert {"bar", "horizontal_bar", "ranked_bar", "stacked_bar", "target_table", "detail_table"} & set(
        outputs.analysis_chart_spec_catalog["chart_type"]
    )
    assert {
        "source_section_id",
        "chart_title",
        "data_artifact",
        "source_row_count",
        "plotted_row_count",
        "top_data_points_json",
        "data_status",
        "insight_callout",
    }.issubset(outputs.analysis_chart_data_snapshot.columns)
    assert "data_ready" in set(outputs.analysis_chart_data_snapshot["data_status"])
    assert outputs.analysis_chart_data_snapshot["insight_callout"].str.len().gt(0).all()
    assert {
        "metric_id",
        "metric_family",
        "source_artifact",
        "source_field",
        "field_role",
        "aggregation_method",
        "validation_status",
        "csm_interpretation",
    }.issubset(outputs.intelligence_metric_catalog.columns)
    assert {"defined_by_engine", "validation_required", "dimension_reference"} & set(
        outputs.intelligence_metric_catalog["validation_status"]
    )
    assert "priority_score" in set(outputs.intelligence_metric_catalog["source_field"])
    assert {"source_section_id", "section_review_status", "analysis_summary", "data_team_next_step"}.issubset(
        outputs.analysis_section_evidence_review.columns
    )
    assert "txn.payroll" in set(outputs.analysis_section_evidence_review["source_section_id"])
    assert {"data_mapping_blocked", "validate_before_external_use", "sellable_now"} & set(
        outputs.analysis_section_evidence_review["section_review_status"]
    )
    assert {"source_section_id", "minimum_required_fields", "current_layout_readiness", "snowflake_design_action"}.issubset(
        outputs.analysis_requirement_matrix.columns
    )
    payroll_req = outputs.analysis_requirement_matrix[
        outputs.analysis_requirement_matrix["source_section_id"].eq("txn.payroll")
    ].iloc[0]
    campaign_req = outputs.analysis_requirement_matrix[
        outputs.analysis_requirement_matrix["source_section_id"].eq("txn.campaign")
    ].iloc[0]
    assert "transactions:account_id" in payroll_req["minimum_required_fields"]
    assert "balances" in payroll_req["required_input_families"]
    assert "client_layout_needed" in campaign_req["layout_blockers"]
    assert "Do not finalize durable facts" in campaign_req["snowflake_design_action"]
    assert {
        "source_section_id",
        "client_story_role",
        "primary_output_file",
        "csm_talk_track",
        "analyst_validation_focus",
        "data_team_dependency",
        "marketing_activation_use",
    }.issubset(outputs.analysis_consulting_playbook.columns)
    assert "txn.payroll" in set(outputs.analysis_consulting_playbook["source_section_id"])
    assert {"relationship_diagnosis", "data_caveat", "economic_opportunity", "measurement_proof"} & set(
        outputs.analysis_consulting_playbook["client_story_role"]
    )
    assert {
        "source_section_id",
        "brief_status",
        "headline_insight",
        "primary_evidence",
        "data_caveat",
        "recommended_client_question",
    }.issubset(outputs.analysis_insight_brief.columns)
    assert "txn.payroll" in set(outputs.analysis_insight_brief["source_section_id"])
    assert outputs.analysis_insight_brief["headline_insight"].str.len().gt(0).all()
    assert {
        "blueprint_rank",
        "meeting_phase",
        "slide_type",
        "slide_title",
        "primary_message",
        "decision_prompt",
        "blueprint_status",
        "source_artifact",
    }.issubset(outputs.client_meeting_deck_blueprint.columns)
    assert {"Opening", "Analysis Proof", "Action Plan", "Measurement"} <= set(
        outputs.client_meeting_deck_blueprint["meeting_phase"]
    )
    assert outputs.client_meeting_deck_blueprint["slide_title"].str.len().gt(0).all()
    assert {
        "source_section_id",
        "what_is_analyzed",
        "chart_count",
        "metric_count",
        "headline_insight",
        "recommended_client_question",
        "meeting_phase_refs",
        "review_status",
    }.issubset(outputs.analysis_review_board.columns)
    assert "txn.payroll" in set(outputs.analysis_review_board["source_section_id"])
    assert outputs.analysis_review_board["what_is_analyzed"].str.len().gt(0).all()
    assert {"ready", "partial"} & set(outputs.analysis_execution_map["evidence_status"])
    assert "txn.payroll" in set(outputs.analysis_execution_map["source_section_id"])
    assert "txn.payroll" in set(outputs.analysis_section_catalog["source_section_id"])
    assert "payroll_conversion" in set(outputs.analysis_provenance_map["opportunity_type"])
    assert {"primary_metric", "measurement_windows", "success_definition"}.issubset(outputs.measurement_plan.columns)
    assert {"account_id", "measurement_group", "target_status"}.issubset(outputs.campaign_targets.columns)
    assert {"delta_type", "entity_type", "movement_direction", "recommended_action"}.issubset(
        outputs.intelligence_delta_report.columns
    )
    assert "baseline_run" in set(outputs.intelligence_delta_report["delta_type"])
    assert {"insight_id", "insight_type", "evidence_artifacts", "next_decision"}.issubset(
        outputs.consulting_insight_register.columns
    )
    assert {"opportunity", "scorecard", "story_step"} <= set(outputs.consulting_insight_register["insight_type"])
    assert {"account_id", "top_play_name", "evidence_summary"}.issubset(outputs.csm_review_queue.columns)
    assert {"severity", "item_type", "recommended_action"}.issubset(outputs.analyst_validation_queue.columns)
    assert {"account_id", "measurement_group", "target_status"}.issubset(outputs.marketing_activation_export.columns)
    assert {"account_id", "talk_track", "evidence_summary"}.issubset(outputs.banker_call_list.columns)
    assert {"file_name", "load_readiness", "missing_required_count"}.issubset(outputs.data_team_load_plan.columns)
    assert {"artifact_name", "primary_role", "row_count"}.issubset(outputs.stakeholder_export_manifest.columns)
    assert {
        "file_name",
        "proposed_contract_id",
        "contract_action",
        "draft_yaml",
        "data_team_action",
    }.issubset(outputs.layout_contract_draft_queue.columns)
    assert {
        "proposed_contract_id",
        "yaml_relative_path",
        "yaml_ready",
        "data_team_action",
    }.issubset(outputs.layout_contract_export_manifest.columns)
    assert {
        "lineage_stage",
        "source_node_type",
        "target_node_type",
        "relationship",
        "edge_status",
        "next_action",
    }.issubset(outputs.intelligence_lineage_graph.columns)
    assert not outputs.intelligence_lineage_graph.empty
    assert {"baseline_expected_value", "baseline_avg_txn_count", "future_outcome_join_key"}.issubset(
        outputs.measurement_baseline.columns
    )
    assert set(written) == {
        "file_ledger",
        "data_quality",
        "intake_profile",
        "intake_work_order",
        "file_assembly_plan",
        "monthly_file_requirements",
        "layout_gap_report",
        "source_layout_profile",
        "layout_contract_draft_queue",
        "layout_contract_export_manifest",
        "intelligence_lineage_graph",
        "engine_run_ledger",
        "engine_readiness_assessment",
        "account_month_features",
        "account_intelligence_profile",
        "model_rulebook",
        "account_scoring_trace",
        "pfi_verdicts",
        "counterparty_signals",
        "counterparty_summary",
        "relationship_segments",
        "segment_summary",
        "opportunities",
        "opportunity_portfolio",
        "executive_scorecard",
        "strategy_roadmap",
        "action_plan",
        "measurement_plan",
        "campaign_targets",
        "csm_review_queue",
        "analyst_validation_queue",
        "marketing_activation_export",
        "banker_call_list",
        "data_team_load_plan",
        "stakeholder_export_manifest",
        "measurement_baseline",
        "outcome_results",
        "outcome_summary",
        "intelligence_delta_report",
        "consulting_insight_register",
        "insights",
        "role_handoffs",
        "operating_control_plane",
        "user_interaction_map",
        "production_readiness_backlog",
        "analysis_section_catalog",
        "analysis_script_catalog",
        "analysis_field_usage_catalog",
        "analysis_provenance_map",
        "analysis_execution_map",
        "analysis_domain_map",
        "analysis_input_dependency_map",
        "analysis_layout_coverage_matrix",
        "analysis_feature_derivation_catalog",
        "analysis_data_team_backlog",
        "analysis_metric_validation_queue",
        "analysis_visual_output_map",
        "analysis_chart_spec_catalog",
        "analysis_chart_data_snapshot",
        "intelligence_metric_catalog",
        "analysis_section_evidence_review",
        "analysis_requirement_matrix",
        "analysis_consulting_playbook",
        "analysis_insight_brief",
        "client_meeting_deck_blueprint",
        "analysis_review_board",
        "analysis_package_index",
        "consulting_story",
        "run_summary",
    }
    for path in written.values():
        assert Path(path).exists()
    assert not outputs.analysis_package_index.empty
    assert {"artifact_name", "analysis_layer", "primary_consumer", "row_count", "target_table", "purpose"}.issubset(
        outputs.analysis_package_index.columns
    )
    assert "opportunities" in set(outputs.analysis_package_index["artifact_name"])
    assert "mart.ti_opportunities" in set(outputs.analysis_package_index["target_table"])
    assert "account_intelligence_profile" in set(outputs.analysis_package_index["artifact_name"])
    assert "engine_run_ledger" in set(outputs.analysis_package_index["artifact_name"])
    assert "engine_readiness_assessment" in set(outputs.analysis_package_index["artifact_name"])
    assert "model_rulebook" in set(outputs.analysis_package_index["artifact_name"])
    assert "account_scoring_trace" in set(outputs.analysis_package_index["artifact_name"])
    assert "intelligence_delta_report" in set(outputs.analysis_package_index["artifact_name"])
    assert "consulting_insight_register" in set(outputs.analysis_package_index["artifact_name"])
    assert "operating_control_plane" in set(outputs.analysis_package_index["artifact_name"])
    assert "user_interaction_map" in set(outputs.analysis_package_index["artifact_name"])
    assert "production_readiness_backlog" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_field_usage_catalog" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_execution_map" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_domain_map" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_input_dependency_map" in set(outputs.analysis_package_index["artifact_name"])
    assert "monthly_file_requirements" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_layout_coverage_matrix" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_feature_derivation_catalog" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_data_team_backlog" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_metric_validation_queue" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_visual_output_map" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_chart_spec_catalog" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_chart_data_snapshot" in set(outputs.analysis_package_index["artifact_name"])
    assert "intelligence_metric_catalog" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_section_evidence_review" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_requirement_matrix" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_consulting_playbook" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_insight_brief" in set(outputs.analysis_package_index["artifact_name"])
    assert "client_meeting_deck_blueprint" in set(outputs.analysis_package_index["artifact_name"])
    assert "analysis_review_board" in set(outputs.analysis_package_index["artifact_name"])
    assert "source_layout_profile" in set(outputs.analysis_package_index["artifact_name"])
    assert "layout_contract_draft_queue" in set(outputs.analysis_package_index["artifact_name"])
    assert "intelligence_lineage_graph" in set(outputs.analysis_package_index["artifact_name"])
    assert "marketing_activation_export" in set(outputs.analysis_package_index["artifact_name"])


def test_intake_profile_matches_odd_and_transaction_contracts(tmp_path: Path):
    odd = tmp_path / "9999_ODD_formatted.xlsx"
    accounts = _accounts().copy()
    accounts["Stat Code"] = "A"
    accounts.to_excel(odd, index=False)
    txn = tmp_path / "9999_TRAN.csv"
    _transactions().to_csv(txn, index=False)

    profile = profile_input_files([odd, txn])
    work_order = build_intake_work_order(profile)
    assembly_plan = build_file_assembly_plan(work_order)
    layout_gap_report = build_layout_gap_report(profile)

    matches = {item["file_name"]: item["contract_match"]["contract_id"] for item in profile}
    assert matches[odd.name] == "account.odd_extract.v1"
    assert matches[txn.name] == "txn.velocity_standard.v1"
    assert all(item["contract_match"]["status"] == "matched" for item in profile)
    assert not work_order.empty
    assert not assembly_plan.empty
    assert not layout_gap_report.empty
    assert set(work_order["intake_decision"]) == {"use_as_account_file", "use_as_transaction_file"}
    assert {"selected_account", "selected_transaction"} <= set(assembly_plan["assembly_role"])
    assert {"file_name", "intake_decision", "operator_action", "load_target"}.issubset(work_order.columns)
    assert {"canonical_field", "mapping_status", "suggested_source_column"}.issubset(
        layout_gap_report.columns
    )
    assert "missing_required" not in set(layout_gap_report["mapping_status"])


def test_snowflake_package_writes_manifest_and_load_sql(tmp_path: Path):
    cfg = EngineConfig(client_id="9999", client_name="Sample CU", period_month="2026.06")
    outputs = run_transactional_intelligence(
        accounts=_accounts(),
        transactions=_transactions(),
        input_files=[],
        config=cfg,
    )
    artifacts = outputs.write(tmp_path)
    snowflake = write_snowflake_package(outputs, tmp_path, config=cfg, artifact_paths=artifacts, run_id="ti_test")

    manifest_path = Path(snowflake["snowflake_manifest"])
    sql_path = Path(snowflake["snowflake_load_sql"])
    readme_html_path = Path(snowflake["snowflake_readme_html"])
    assert manifest_path.exists()
    assert sql_path.exists()
    assert readme_html_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "ti_test"
    assert any(f["target_table"] == "mart.ti_opportunities" for f in manifest["files"])
    readme_html = readme_html_path.read_text(encoding="utf-8")
    assert "<title>Snowflake Load Package</title>" in readme_html
    assert "mart.ti_opportunities" in readme_html
    sql = sql_path.read_text(encoding="utf-8")
    assert "mart.ti_account_month_features" in sql
    assert "mart.ti_account_intelligence_profile" in sql
    assert "out.ti_model_rulebook" in sql
    assert "out.ti_account_scoring_trace" in sql
    assert "mart.ti_counterparty_signals" in sql
    assert "mart.ti_counterparty_summary" in sql
    assert "mart.ti_relationship_segments" in sql
    assert "mart.ti_segment_summary" in sql
    assert "mart.ti_opportunity_portfolio" in sql
    assert "out.ti_executive_scorecard" in sql
    assert "out.ti_strategy_roadmap" in sql
    assert "out.ti_action_plan" in sql
    assert "out.ti_measurement_plan" in sql
    assert "out.ti_campaign_targets" in sql
    assert "out.ti_csm_review_queue" in sql
    assert "out.ti_analyst_validation_queue" in sql
    assert "out.ti_marketing_activation_export" in sql
    assert "out.ti_banker_call_list" in sql
    assert "out.ti_data_team_load_plan" in sql
    assert "out.ti_stakeholder_export_manifest" in sql
    assert "out.ti_measurement_baseline" in sql
    assert "out.ti_outcome_results" in sql
    assert "out.ti_outcome_summary" in sql
    assert "out.ti_intelligence_delta_report" in sql
    assert "out.ti_consulting_insight_register" in sql
    assert "out.ti_role_handoffs" in sql
    assert "out.ti_operating_control_plane" in sql
    assert "out.ti_user_interaction_map" in sql
    assert "out.ti_production_readiness_backlog" in sql
    assert "out.ti_analysis_section_catalog" in sql
    assert "out.ti_analysis_script_catalog" in sql
    assert "out.ti_analysis_field_usage_catalog" in sql
    assert "out.ti_analysis_provenance_map" in sql
    assert "out.ti_analysis_execution_map" in sql
    assert "out.ti_analysis_domain_map" in sql
    assert "out.ti_analysis_input_dependency_map" in sql
    assert "out.ti_analysis_layout_coverage_matrix" in sql
    assert "out.ti_analysis_feature_derivation_catalog" in sql
    assert "out.ti_analysis_data_team_backlog" in sql
    assert "out.ti_analysis_metric_validation_queue" in sql
    assert "out.ti_analysis_visual_output_map" in sql
    assert "out.ti_analysis_chart_spec_catalog" in sql
    assert "out.ti_analysis_chart_data_snapshot" in sql
    assert "out.ti_intelligence_metric_catalog" in sql
    assert "out.ti_analysis_section_evidence_review" in sql
    assert "out.ti_analysis_requirement_matrix" in sql
    assert "out.ti_analysis_consulting_playbook" in sql
    assert "out.ti_analysis_insight_brief" in sql
    assert "out.ti_client_meeting_deck_blueprint" in sql
    assert "out.ti_analysis_review_board" in sql
    assert "out.ti_analysis_package_index" in sql
    assert "out.ti_consulting_story" in sql
    assert "out.ti_intake_profile" in sql
    assert "out.ti_intake_work_order" in sql
    assert "out.ti_file_assembly_plan" in sql
    assert "out.ti_monthly_file_requirements" in sql
    assert "out.ti_layout_gap_report" in sql
    assert "out.ti_source_layout_profile" in sql
    assert "out.ti_layout_contract_draft_queue" in sql
    assert "out.ti_layout_contract_export_manifest" in sql
    assert "out.ti_intelligence_lineage_graph" in sql
    assert "out.ti_engine_readiness_assessment" in sql
    assert "out.ti_engine_run_ledger" in sql
    assert "COPY INTO mart.ti_opportunities" in sql


def test_file_drop_assembly_selects_files_and_reads_positional_transactions(tmp_path: Path):
    account_path = tmp_path / "9999_ODD_accounts.csv"
    accounts = _accounts().copy()
    accounts["Stat Code"] = "A"
    accounts.to_csv(account_path, index=False)
    raw_txn_path = tmp_path / "9999_velocity.ars.transactions.dat"
    raw_txn_path.write_text(
        "\n".join([
            "Velocity transaction export",
            "2026-06-03|100|ACH Credit|3500||ADP Payroll Direct Deposit|||||||",
            "2026-06-08|100|ACH Debit|-2200||Chase Bank Transfer|||||||",
            "2026-06-12|200|ACH Debit|-100||Wells Fargo Payment|||||||",
        ])
        + "\n",
        encoding="utf-8",
    )
    support = tmp_path / "9999_notes.csv"
    pd.DataFrame([{"note": "supporting only"}]).to_csv(support, index=False)

    assembly = assemble_file_drop(tmp_path)

    assert assembly.account_file == account_path
    assert raw_txn_path in assembly.transaction_files
    assert len(assembly.input_files) == 3
    assert "selected_account" in set(assembly.assembly_plan["assembly_role"])
    assert "selected_transaction" in set(assembly.assembly_plan["assembly_role"])
    assert "not_loaded" in set(assembly.assembly_plan["assembly_role"])
    assert not assembly.layout_gap_report.empty
    assert "missing_required" in set(assembly.layout_gap_report["mapping_status"])

    tx = read_input_table(raw_txn_path)
    assert {"transaction_date", "primary_account_num", "transaction_type", "amount", "merchant_name"}.issubset(tx.columns)
    outputs = run_transactional_intelligence(
        accounts=read_input_table(assembly.account_file),
        transactions=tx,
        input_files=assembly.input_files,
        config=EngineConfig(client_id="9999", period_month="2026.06"),
    )
    assert outputs.data_quality["transaction_rows"] == 3
    assert "selected_transaction" in set(outputs.file_assembly_plan["assembly_role"])
    assert not outputs.layout_gap_report.empty
    assert not outputs.account_intelligence_profile.empty
    assert not outputs.data_team_load_plan.empty
    assert not outputs.source_layout_profile.empty
    assert not outputs.layout_contract_draft_queue.empty
    assert not outputs.intelligence_lineage_graph.empty
    assert "position_0" in set(outputs.layout_gap_report["suggested_source_column"])
    assert "position_0" in set(outputs.source_layout_profile["source_column"])
    assert "promote_existing_contract" in set(outputs.layout_contract_draft_queue["contract_action"])
    assert "01_file_to_input" in set(outputs.intelligence_lineage_graph["lineage_stage"])
    assert "07_section_to_engine_output" in set(outputs.intelligence_lineage_graph["lineage_stage"])
    position_zero = outputs.source_layout_profile[
        outputs.source_layout_profile["source_column"].eq("position_0")
    ].iloc[0]
    assert "transaction_date" in position_zero["matched_canonical_fields"]


def test_engine_uses_custom_contract_dir_for_layout_outputs(tmp_path: Path):
    input_dir = tmp_path / "drop"
    input_dir.mkdir()
    contract_dir = _write_custom_contract_dir(tmp_path / "contracts")
    account_path = input_dir / "9999_ODD_accounts.csv"
    payments_path = input_dir / "9999_monthly_payments.csv"
    accounts = _accounts().copy()
    accounts["Stat Code"] = "A"
    accounts.to_csv(account_path, index=False)
    _transactions().to_csv(payments_path, index=False)

    assembly = assemble_file_drop(input_dir, contract_dir=contract_dir)
    assert assembly.account_file == account_path
    assert payments_path in assembly.transaction_files
    assert "txn.client_payments.v1" in set(assembly.layout_gap_report["contract_id"])

    outputs = run_transactional_intelligence(
        accounts=read_input_table(assembly.account_file),
        transactions=read_input_table(payments_path),
        input_files=assembly.input_files,
        contract_dir=contract_dir,
        config=EngineConfig(client_id="9999", period_month="2026.06"),
    )

    txn_layout = outputs.layout_gap_report[
        outputs.layout_gap_report["contract_id"].eq("txn.client_payments.v1")
    ]
    assert not txn_layout.empty
    assert "selected_transaction" in set(outputs.file_assembly_plan["assembly_role"])
    assert "txn.client_payments.v1" in set(outputs.intake_work_order["contract_id"])
    assert "missing_required" not in set(txn_layout["mapping_status"])
    assert "txn.client_payments.v1" in set(outputs.source_layout_profile["contract_id"])
    assert "txn.client_payments.v1" in set(outputs.layout_contract_draft_queue["proposed_contract_id"])
    assert "primary_account_num" in set(outputs.source_layout_profile["source_column"])


def test_cli_runs_monthly_file_drop_with_custom_contract_dir(tmp_path: Path, capsys):
    input_dir = tmp_path / "drop"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    contract_dir = _write_custom_contract_dir(tmp_path / "contracts")
    account_path = input_dir / "9999_ODD_accounts.csv"
    payments_path = input_dir / "9999_monthly_payments.csv"
    accounts = _accounts().copy()
    accounts["Stat Code"] = "A"
    accounts.to_csv(account_path, index=False)
    _transactions().to_csv(payments_path, index=False)

    result = intelligence_cli_main(
        [
            "--input-dir",
            str(input_dir),
            "--contract-dir",
            str(contract_dir),
            "--client-id",
            "9999",
            "--client-name",
            "Sample CU",
            "--month",
            "2026.06",
            "--output",
            str(output_dir),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "selected 1 account file(s) and 1 transaction file(s)" in captured.out
    assert (output_dir / "analysis_section_evidence_review.csv").exists()
    assert (output_dir / "analysis_layout_coverage_matrix.csv").exists()
    assert (output_dir / "analysis_feature_derivation_catalog.csv").exists()
    assert (output_dir / "analysis_data_team_backlog.csv").exists()
    assert (output_dir / "analysis_metric_validation_queue.csv").exists()
    assert (output_dir / "analysis_visual_output_map.csv").exists()
    assert (output_dir / "analysis_chart_spec_catalog.csv").exists()
    assert (output_dir / "analysis_chart_data_snapshot.csv").exists()
    assert (output_dir / "intelligence_metric_catalog.csv").exists()
    assert (output_dir / "analysis_consulting_playbook.csv").exists()
    assert (output_dir / "analysis_insight_brief.csv").exists()
    assert (output_dir / "client_meeting_deck_blueprint.csv").exists()
    assert (output_dir / "analysis_review_board.csv").exists()
    assert (output_dir / "user_interaction_map.csv").exists()
    assert (output_dir / "production_readiness_backlog.csv").exists()
    assert (output_dir / "source_layout_profile.csv").exists()
    assert (output_dir / "layout_contract_draft_queue.csv").exists()
    assert (output_dir / "layout_contract_export_manifest.csv").exists()
    assert (output_dir / "monthly_file_requirements.csv").exists()
    assert (output_dir / "intelligence_lineage_graph.csv").exists()
    assert (output_dir / "engine_readiness_assessment.csv").exists()
    assert (output_dir / "snowflake_manifest.json").exists()
    assert (output_dir / "README_SNOWFLAKE.html").exists()
    assembly_plan = pd.read_csv(output_dir / "file_assembly_plan.csv")
    layout_gap = pd.read_csv(output_dir / "layout_gap_report.csv")
    source_layout = pd.read_csv(output_dir / "source_layout_profile.csv")
    contract_drafts = pd.read_csv(output_dir / "layout_contract_draft_queue.csv")
    contract_exports = pd.read_csv(output_dir / "layout_contract_export_manifest.csv")
    monthly_requirements = pd.read_csv(output_dir / "monthly_file_requirements.csv")
    lineage = pd.read_csv(output_dir / "intelligence_lineage_graph.csv")
    production_backlog = pd.read_csv(output_dir / "production_readiness_backlog.csv")
    package_index = pd.read_csv(output_dir / "analysis_package_index.csv")
    assert "selected_transaction" in set(assembly_plan["assembly_role"])
    assert "txn.client_payments.v1" in set(layout_gap["contract_id"])
    assert "txn.client_payments.v1" in set(source_layout["contract_id"])
    assert "promote_existing_contract" in set(contract_drafts["contract_action"])
    assert "txn.client_payments.v1" in set(contract_exports["proposed_contract_id"])
    assert contract_exports["yaml_ready"].astype(bool).all()
    for rel_path in contract_exports["yaml_relative_path"]:
        assert (output_dir / rel_path).exists()
    assert {"accounts", "transactions", "campaign_history"} <= set(monthly_requirements["input_family"])
    assert "selected_for_load" in set(monthly_requirements["monthly_status"])
    account_draft = contract_drafts[contract_drafts["file_name"].eq("9999_ODD_accounts.csv")].iloc[0]
    assert "source_family: account" in account_draft["draft_yaml"]
    assert "source_family: outcome" not in account_draft["draft_yaml"]
    assert "11_output_to_role" in set(lineage["lineage_stage"])
    assert "16_readiness_to_production_backlog" in set(lineage["lineage_stage"])
    assert not production_backlog.empty
    assert {"workstream", "priority_band", "problem_statement", "acceptance_criteria"}.issubset(
        production_backlog.columns
    )
    assert "analysis_section_evidence_review" in set(package_index["artifact_name"])
    assert "analysis_feature_derivation_catalog" in set(package_index["artifact_name"])
    assert "analysis_data_team_backlog" in set(package_index["artifact_name"])
    assert "analysis_metric_validation_queue" in set(package_index["artifact_name"])
    assert "analysis_visual_output_map" in set(package_index["artifact_name"])
    assert "analysis_chart_spec_catalog" in set(package_index["artifact_name"])
    assert "analysis_chart_data_snapshot" in set(package_index["artifact_name"])
    assert "intelligence_metric_catalog" in set(package_index["artifact_name"])
    assert "analysis_consulting_playbook" in set(package_index["artifact_name"])
    assert "analysis_insight_brief" in set(package_index["artifact_name"])
    assert "client_meeting_deck_blueprint" in set(package_index["artifact_name"])
    assert "analysis_review_board" in set(package_index["artifact_name"])
    assert "user_interaction_map" in set(package_index["artifact_name"])
    assert "production_readiness_backlog" in set(package_index["artifact_name"])
    assert "engine_readiness_assessment" in set(package_index["artifact_name"])
    assert "source_layout_profile" in set(package_index["artifact_name"])
    assert "layout_contract_draft_queue" in set(package_index["artifact_name"])
    assert "layout_contract_export_manifest" in set(package_index["artifact_name"])
    assert "monthly_file_requirements" in set(package_index["artifact_name"])
    assert "intelligence_lineage_graph" in set(package_index["artifact_name"])


def test_demo_generator_writes_chart_gallery_html(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_intelligence_demo.py",
            "--output-root",
            str(tmp_path),
            "--clean",
        ],
    )

    result = generate_intelligence_demo_main()

    package_root = tmp_path / "9999"
    july_dir = package_root / "2026.07_measurement_run"
    launchpad = package_root / "transactional_intelligence_launchpad.html"
    client_story = package_root / "transactional_intelligence_client_story.html"
    intake_cockpit = package_root / "transactional_intelligence_intake_cockpit.html"
    gallery = package_root / "transactional_intelligence_chart_gallery.html"
    actuals = package_root / "transactional_intelligence_actuals.html"
    lineage_map = package_root / "transactional_intelligence_lineage_map.html"
    section_index = package_root / "transactional_intelligence_section_drilldowns.html"
    section_pages = package_root / "analysis_sections"
    assert result == 0
    assert launchpad.exists()
    assert client_story.exists()
    assert intake_cockpit.exists()
    assert gallery.exists()
    assert actuals.exists()
    assert lineage_map.exists()
    assert section_index.exists()
    assert section_pages.exists()
    assert (section_pages / "txn_payroll.html").exists()
    assert (july_dir / "analysis_chart_spec_catalog.csv").exists()
    assert (july_dir / "analysis_visual_output_map.csv").exists()
    assert (july_dir / "analysis_chart_data_snapshot.csv").exists()
    assert (july_dir / "intelligence_metric_catalog.csv").exists()
    assert (july_dir / "analysis_consulting_playbook.csv").exists()
    assert (july_dir / "analysis_insight_brief.csv").exists()
    assert (july_dir / "client_meeting_deck_blueprint.csv").exists()
    assert (july_dir / "analysis_review_board.csv").exists()
    assert (july_dir / "user_interaction_map.csv").exists()
    assert (july_dir / "production_readiness_backlog.csv").exists()
    assert (july_dir / "intelligence_lineage_graph.csv").exists()
    assert (july_dir / "monthly_file_requirements.csv").exists()
    assert (july_dir / "layout_contract_export_manifest.csv").exists()
    contract_exports = pd.read_csv(july_dir / "layout_contract_export_manifest.csv")
    assert not contract_exports.empty
    for rel_path in contract_exports["yaml_relative_path"]:
        assert (july_dir / rel_path).exists()
    monthly_requirements = pd.read_csv(july_dir / "monthly_file_requirements.csv")
    txn_req = monthly_requirements[monthly_requirements["input_family"].eq("transactions")].iloc[0]
    suppression_req = monthly_requirements[monthly_requirements["input_family"].eq("suppressions")].iloc[0]
    assert txn_req["monthly_status"] == "selected_for_load"
    assert "marketing_suppressions" not in str(txn_req["received_file_names"])
    assert suppression_req["monthly_status"] == "layout_review_required"
    launchpad_html = launchpad.read_text(encoding="utf-8")
    client_story_html = client_story.read_text(encoding="utf-8")
    intake_html = intake_cockpit.read_text(encoding="utf-8")
    html = gallery.read_text(encoding="utf-8")
    actuals_html = actuals.read_text(encoding="utf-8")
    lineage_html = lineage_map.read_text(encoding="utf-8")
    section_index_html = section_index.read_text(encoding="utf-8")
    payroll_html = (section_pages / "txn_payroll.html").read_text(encoding="utf-8")
    assert "Transactional Intelligence Launchpad" in launchpad_html
    assert "transactional_intelligence_client_story.html" in launchpad_html
    assert "transactional_intelligence_intake_cockpit.html" in launchpad_html
    assert "Executive / product owner" in launchpad_html
    assert "CSM" in launchpad_html
    assert "Analyst" in launchpad_html
    assert "Data / Snowflake" in launchpad_html
    assert "Top Production Backlog" in launchpad_html
    assert "Transactional Intelligence Client Story" in client_story_html
    assert "Client Conversation Guide" in client_story_html
    assert "Decision Questions" in client_story_html
    assert "Story Arc" in client_story_html
    assert "Top Plays And Talk Track" in client_story_html
    assert "Meeting Run Of Show" in client_story_html
    assert "Proof And Caveats" in client_story_html
    assert "Activation Exports" in client_story_html
    assert "Measurement Plan" in client_story_html
    assert "Outcome Readout" in client_story_html
    assert "client_meeting_deck_blueprint.csv" in client_story_html
    assert "analysis_insight_brief.csv" in client_story_html
    assert "campaign_targets.csv" in client_story_html
    assert "banker_call_list.csv" in client_story_html
    assert "transactional_intelligence_section_drilldowns.html" in launchpad_html
    assert "README_SNOWFLAKE.html" in launchpad_html
    assert "Monthly Client File Intake Cockpit" in intake_html
    assert "Operational Intake Process" in intake_html
    assert "Monthly Requirement Status" in intake_html
    assert "Snowflake Load Readiness" in intake_html
    assert "Received Files And Assembly Decisions" in intake_html
    assert "Layout Contract Draft Queue" in intake_html
    assert "Intake And Snowflake Production Backlog" in intake_html
    assert "monthly_file_requirements.csv" in intake_html
    assert "file_assembly_plan.csv" in intake_html
    assert "data_team_load_plan.csv" in intake_html
    assert "README_SNOWFLAKE.html" in intake_html
    assert "snowflake_load.sql" in intake_html
    assert "Transactional Intelligence Chart Gallery" in html
    assert "Transactional Intelligence Lineage Map" in lineage_html
    assert "Analysis Section Drilldowns" in section_index_html
    assert "txn.payroll" in section_index_html
    assert "Charts And Graphs" in payroll_html
    assert "Chart Data Snapshots" in payroll_html
    assert "Metric Catalog" in payroll_html
    assert "Consulting Playbook" in payroll_html
    assert "Insight Brief" in payroll_html
    assert "Client Meeting Deck Blueprint" in actuals_html
    assert "Analysis Review Board" in actuals_html
    assert "User Interaction Map" in actuals_html
    assert "Production Readiness Backlog" in actuals_html
    assert "analysis_consulting_playbook.csv" in actuals_html
    assert "analysis_insight_brief.csv" in actuals_html
    assert "client_meeting_deck_blueprint.csv" in actuals_html
    assert "analysis_review_board.csv" in actuals_html
    assert "user_interaction_map.csv" in actuals_html
    assert "production_readiness_backlog.csv" in actuals_html
    assert "analysis_chart_data_snapshot.csv" in actuals_html
    assert "intelligence_metric_catalog.csv" in actuals_html
    assert "Field Coverage And Blockers" in payroll_html
    assert "Lineage Edges" in payroll_html
    assert "intelligence_lineage_graph.csv" in lineage_html
    assert "analysis_chart_spec_catalog.csv" in html
    assert "chart-card" in html
    assert "bar-row" in html
    assert not list(package_root.rglob("README*.md"))


def test_analysis_catalog_maps_existing_sections_to_engine_provenance():
    section_catalog = build_analysis_section_catalog()
    script_catalog = build_analysis_script_catalog()
    provenance = build_analysis_provenance_map({
        "payroll_conversion": ["txn.payroll", "txn.relationship", "txn.competition"],
        "deposit_retention": ["txn.balance", "txn.competition", "txn.relationship"],
    })

    assert {"source_section_id", "primary_engine_outputs", "consulting_use"}.issubset(section_catalog.columns)
    assert {"txn.payroll", "txn.competition", "ars.dctr"} <= set(section_catalog["source_section_id"])
    assert script_catalog["script_name"].str.endswith(".py").all()
    assert script_catalog["source_path"].str.contains("01_Analysis/00-Scripts/analytics").any()
    payroll = section_catalog[section_catalog["source_section_id"].eq("txn.payroll")].iloc[0]
    assert "payroll_conversion" in payroll["supports_opportunity_types"]
    assert "pfi_verdicts" in payroll["primary_engine_outputs"]
    assert set(provenance["opportunity_type"]) == {"payroll_conversion", "deposit_retention"}
    assert "txn.balance" in set(provenance["source_section_id"])


def test_engine_measures_outcomes_from_prior_targets():
    prior_cfg = EngineConfig(client_id="test", period_month="2026.06")
    prior = run_transactional_intelligence(
        accounts=_accounts(),
        transactions=_transactions(),
        config=prior_cfg,
    )

    current_transactions = _transactions().copy()
    current_transactions["transaction_date"] = current_transactions["transaction_date"].str.replace(
        "2026-06", "2026-07", regex=False
    )
    current_transactions = pd.concat(
        [
            current_transactions,
            pd.DataFrame([
                {
                    "primary_account_num": "200",
                    "transaction_date": "2026-07-15",
                    "amount": 2200,
                    "description": "ADP Payroll Direct Deposit",
                    "transaction_type": "ACH Credit",
                },
                {
                    "primary_account_num": "200",
                    "transaction_date": "2026-07-16",
                    "amount": -400,
                    "description": "Debit Card Purchase",
                    "transaction_type": "Debit Card",
                },
            ]),
        ],
        ignore_index=True,
    )
    current = run_transactional_intelligence(
        accounts=_accounts(),
        transactions=current_transactions,
        prior_campaign_targets=prior.campaign_targets,
        prior_measurement_baseline=prior.measurement_baseline,
        prior_account_intelligence_profile=prior.account_intelligence_profile,
        prior_opportunities=prior.opportunities,
        prior_opportunity_portfolio=prior.opportunity_portfolio,
        prior_data_quality=prior.data_quality,
        config=EngineConfig(client_id="test", period_month="2026.07"),
    )

    assert not current.outcome_results.empty
    assert not current.outcome_summary.empty
    assert {"outcome_flag", "delta_txn_count", "current_pfi_verdict"}.issubset(current.outcome_results.columns)
    assert current.outcome_summary["target_accounts"].sum() > 0
    assert current.outcome_summary["measurement_status"].isin(
        ["measured_with_holdout", "measured_pre_post"]
    ).all()
    assert not current.intelligence_delta_report.empty
    assert "baseline_run" not in set(current.intelligence_delta_report["delta_type"])
    assert {"quality_score_delta", "account_profile_changed", "opportunity_priority_changed"} & set(
        current.intelligence_delta_report["delta_type"]
    )
