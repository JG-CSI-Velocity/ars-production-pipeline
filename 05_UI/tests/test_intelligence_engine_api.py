"""FastAPI coverage for the transactional intelligence engine surface."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient


def _stage_intelligence_inputs(app_module, *, csm="TestCSM", month="2026.04", client_id="9999"):
    ready = app_module.READY_FOR_ANALYSIS / csm / month / client_id
    txn_dir = ready / "trans"
    txn_dir.mkdir(parents=True, exist_ok=True)

    accounts = pd.DataFrame([
        {
            "account_id": "A1",
            "Avg Bal": 7200,
            "Debit?": "Y",
            "Business?": "N",
            "Branch": "Main",
            "Product Code": "CHK",
            "Date Opened": "2023-01-01",
            "Stat Code": "A",
        },
        {
            "account_id": "A2",
            "Avg Bal": 1200,
            "Debit?": "N",
            "Business?": "N",
            "Branch": "West",
            "Product Code": "SAV",
            "Date Opened": "2024-01-01",
            "Stat Code": "A",
        },
    ])
    odd = ready / f"{client_id}_ODD_formatted.xlsx"
    accounts.to_excel(odd, index=False)

    transactions = pd.DataFrame([
        {
            "account_id": "A1",
            "transaction_date": "2026-04-03",
            "amount": 2500,
            "description": "ADP payroll direct deposit",
            "transaction_type": "ACH credit",
        },
        {
            "account_id": "A1",
            "transaction_date": "2026-04-04",
            "amount": -1250,
            "description": "Chase external transfer",
            "transaction_type": "ACH debit",
        },
        {
            "account_id": "A1",
            "transaction_date": "2026-04-05",
            "amount": -85,
            "description": "Debit card purchase grocery",
            "transaction_type": "card",
        },
        {
            "account_id": "A2",
            "transaction_date": "2026-04-05",
            "amount": -700,
            "description": "Rocket Mortgage payment",
            "transaction_type": "ACH debit",
        },
    ])
    txn = txn_dir / f"{client_id}_TRAN.csv"
    transactions.to_csv(txn, index=False)
    return {"csm": csm, "month": month, "client_id": client_id, "odd": odd, "txn": txn}


def _write_client_config(app_module, client_id="9999"):
    app_module.CONFIG_PATH.write_text(json.dumps({
        client_id: {
            "ClientName": "Sample Credit Union",
            "ICRate": 0.015,
        },
    }))


def test_intelligence_ui_surfaces_analysis_catalog(app_module):
    index_html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
    assert "See The Analysis" in index_html
    assert "All Sections" in index_html
    assert "Charts/Graphs" in index_html
    assert "iPrimaryActions" in index_html
    assert "analysis_review_board.csv" in index_html
    assert "analysis_chart_data_snapshot.csv" in index_html
    assert "intelligence_metric_catalog.csv" in index_html
    assert "analysis_feature_derivation_catalog.csv" in index_html
    assert "Feature Derivation Catalog" in index_html

    client = TestClient(app_module.app)
    docs = client.get("/docs/modules.html")
    assert docs.status_code == 200
    assert "Analysis Modules Browser" in docs.text


def test_files_endpoint_reports_intelligence_readiness(app_module):
    staged = _stage_intelligence_inputs(app_module)
    client = TestClient(app_module.app)

    r = client.get(f"/api/files/{staged['csm']}/{staged['month']}/{staged['client_id']}")

    assert r.status_code == 200
    body = r.json()
    assert body["odd"]["status"] == "ready"
    assert body["transactions"]["status"] == "ready"
    assert body["transactions"]["count"] == 1
    assert body["intelligence"]["status"] == "missing"


def test_intelligence_engine_writes_operator_artifacts(app_module):
    staged = _stage_intelligence_inputs(app_module)
    _write_client_config(app_module)
    run_id = "test_intelligence"
    app_module.runs[run_id] = {
        "status": "running",
        "client_id": staged["client_id"],
        "csm": staged["csm"],
        "month": staged["month"],
        "product": "intelligence",
        "started": "2026-08-15T10:00:00",
        "progress": 0,
        "current_step": "Starting",
        "log": [],
    }

    app_module._run_intelligence_engine(
        run_id,
        staged["csm"],
        staged["month"],
        staged["client_id"],
    )

    assert app_module.runs[run_id]["status"] == "complete"
    out_dir = app_module.COMPLETED_INTELLIGENCE / staged["csm"] / staged["month"] / staged["client_id"]
    expected = {
        "transactional_intelligence_package.xlsx",
        "executive_brief.html",
        "data_quality_report.html",
        "transactional_intelligence_client_story.html",
        "transactional_intelligence_intake_cockpit.html",
        "intake_profile.json",
        "intake_work_order.csv",
        "file_assembly_plan.csv",
        "monthly_file_requirements.csv",
        "layout_gap_report.csv",
        "layout_contract_draft_queue.csv",
        "layout_contract_export_manifest.csv",
        "intelligence_lineage_graph.csv",
        "engine_run_ledger.csv",
        "account_intelligence_profile.csv",
        "model_rulebook.csv",
        "account_scoring_trace.csv",
        "snowflake_manifest.json",
        "snowflake_load.sql",
        "README_SNOWFLAKE.html",
        "engine_readiness_assessment.csv",
        "account_month_features.csv",
        "pfi_verdicts.csv",
        "counterparty_signals.csv",
        "counterparty_summary.csv",
        "relationship_segments.csv",
        "segment_summary.csv",
        "opportunities.csv",
        "opportunity_portfolio.csv",
        "executive_scorecard.csv",
        "strategy_roadmap.csv",
        "action_plan.csv",
        "measurement_plan.csv",
        "campaign_targets.csv",
        "csm_review_queue.csv",
        "analyst_validation_queue.csv",
        "marketing_activation_export.csv",
        "banker_call_list.csv",
        "data_team_load_plan.csv",
        "stakeholder_export_manifest.csv",
        "measurement_baseline.csv",
        "outcome_results.csv",
        "outcome_summary.csv",
        "intelligence_delta_report.csv",
        "consulting_insight_register.csv",
        "role_handoffs.csv",
        "operating_control_plane.csv",
        "user_interaction_map.csv",
        "production_readiness_backlog.csv",
        "analysis_section_catalog.csv",
        "analysis_script_catalog.csv",
        "analysis_provenance_map.csv",
        "analysis_execution_map.csv",
        "analysis_visual_output_map.csv",
        "analysis_chart_spec_catalog.csv",
        "analysis_chart_data_snapshot.csv",
        "intelligence_metric_catalog.csv",
        "analysis_feature_derivation_catalog.csv",
        "analysis_consulting_playbook.csv",
        "analysis_insight_brief.csv",
        "client_meeting_deck_blueprint.csv",
        "analysis_review_board.csv",
        "analysis_package_index.csv",
        "consulting_story.json",
        "insights.json",
        "run_summary.json",
    }
    assert expected.issubset({p.name for p in out_dir.iterdir()})

    summary = json.loads((out_dir / "run_summary.json").read_text())
    assert summary["feature_rows"] > 0
    assert summary["opportunity_rows"] > 0
    assert summary["insight_count"] > 0
    assert summary["operating_control_plane_rows"] > 0
    assert summary["monthly_file_requirements_rows"] > 0
    assert summary["layout_contract_draft_queue_rows"] > 0
    assert summary["layout_contract_export_manifest_rows"] > 0
    assert summary["intelligence_lineage_graph_rows"] > 0
    assert summary["analysis_feature_derivation_catalog_rows"] > 0
    client_story_html = (out_dir / "transactional_intelligence_client_story.html").read_text(encoding="utf-8")
    intake_cockpit_html = (out_dir / "transactional_intelligence_intake_cockpit.html").read_text(encoding="utf-8")
    assert "Transactional Intelligence Client Story" in client_story_html
    assert "Client Conversation Guide" in client_story_html
    assert "Meeting Run Of Show" in client_story_html
    assert "Activation Exports" in client_story_html
    assert "Measurement Plan" in client_story_html
    assert "Monthly Client File Intake Cockpit" in intake_cockpit_html
    assert "Monthly Requirement Status" in intake_cockpit_html
    assert "Snowflake Load Readiness" in intake_cockpit_html
    assert "Layout Contract Draft Queue" in intake_cockpit_html


def test_intelligence_run_endpoint_and_outputs_endpoint(app_module):
    staged = _stage_intelligence_inputs(app_module)
    _write_client_config(app_module)
    client = TestClient(app_module.app)

    r = client.post(
        "/api/intelligence/run",
        params={"csm": staged["csm"], "month": staged["month"], "client_id": staged["client_id"]},
    )

    assert r.status_code == 200
    run_id = r.json()["run_id"]
    for _ in range(50):
        status = app_module.runs[run_id]["status"]
        if status != "running":
            break
        time.sleep(0.1)

    assert app_module.runs[run_id]["status"] == "complete"
    out = client.get(
        f"/api/intelligence/outputs/{staged['csm']}/{staged['month']}/{staged['client_id']}"
    )
    assert out.status_code == 200
    body = out.json()
    names = {f["name"] for f in body["files"]}
    assert "transactional_intelligence_package.xlsx" in names
    assert "executive_brief.html" in names
    assert "transactional_intelligence_client_story.html" in names
    assert "transactional_intelligence_intake_cockpit.html" in names
    assert "snowflake_load.sql" in names
    assert "action_plan.csv" in names
    assert "intake_work_order.csv" in names
    assert "file_assembly_plan.csv" in names
    assert "monthly_file_requirements.csv" in names
    assert "layout_gap_report.csv" in names
    assert "layout_contract_draft_queue.csv" in names
    assert "layout_contract_export_manifest.csv" in names
    assert any(name.startswith("layout_contract_drafts/") and name.endswith(".yml") for name in names)
    assert "intelligence_lineage_graph.csv" in names
    assert "engine_run_ledger.csv" in names
    assert "account_intelligence_profile.csv" in names
    assert "model_rulebook.csv" in names
    assert "account_scoring_trace.csv" in names
    assert "counterparty_signals.csv" in names
    assert "counterparty_summary.csv" in names
    assert "relationship_segments.csv" in names
    assert "segment_summary.csv" in names
    assert "executive_scorecard.csv" in names
    assert "strategy_roadmap.csv" in names
    assert "consulting_insight_register.csv" in names
    assert "intelligence_delta_report.csv" in names
    assert "role_handoffs.csv" in names
    assert "operating_control_plane.csv" in names
    assert "user_interaction_map.csv" in names
    assert "production_readiness_backlog.csv" in names
    assert "analysis_section_catalog.csv" in names
    assert "analysis_script_catalog.csv" in names
    assert "analysis_provenance_map.csv" in names
    assert "analysis_execution_map.csv" in names
    assert "analysis_chart_data_snapshot.csv" in names
    assert "intelligence_metric_catalog.csv" in names
    assert "analysis_feature_derivation_catalog.csv" in names
    assert "analysis_consulting_playbook.csv" in names
    assert "analysis_insight_brief.csv" in names
    assert "client_meeting_deck_blueprint.csv" in names
    assert "analysis_review_board.csv" in names
    assert "analysis_package_index.csv" in names
    assert "csm_review_queue.csv" in names
    assert "analyst_validation_queue.csv" in names
    assert "marketing_activation_export.csv" in names
    assert "banker_call_list.csv" in names
    assert "data_team_load_plan.csv" in names
    assert "stakeholder_export_manifest.csv" in names
    assert "consulting_story.json" in names
    assert body["summary"]["opportunity_rows"] > 0
    assert body["summary"]["counterparty_signal_rows"] > 0
    assert body["summary"]["counterparty_summary_rows"] > 0
    assert body["summary"]["relationship_segment_rows"] > 0
    assert body["summary"]["segment_summary_rows"] > 0
    assert body["summary"]["executive_scorecard_rows"] > 0
    assert body["summary"]["strategy_roadmap_rows"] > 0
    assert body["summary"]["consulting_insight_register_rows"] > 0
    assert body["summary"]["intelligence_delta_report_rows"] > 0
    assert body["summary"]["intake_work_order_rows"] > 0
    assert body["summary"]["file_assembly_plan_rows"] > 0
    assert body["summary"]["monthly_file_requirements_rows"] > 0
    assert body["summary"]["layout_gap_report_rows"] > 0
    assert body["summary"]["layout_contract_draft_queue_rows"] > 0
    assert body["summary"]["layout_contract_export_manifest_rows"] > 0
    assert body["summary"]["intelligence_lineage_graph_rows"] > 0
    assert body["summary"]["engine_run_ledger_rows"] > 0
    assert body["summary"]["account_intelligence_profile_rows"] > 0
    assert body["summary"]["model_rulebook_rows"] > 0
    assert body["summary"]["account_scoring_trace_rows"] > 0
    assert body["summary"]["intake_readiness_status"] == "ready"
    assert body["summary"]["action_plan_rows"] > 0
    assert body["summary"]["role_handoff_rows"] > 0
    assert body["summary"]["operating_control_plane_rows"] > 0
    assert body["summary"]["user_interaction_map_rows"] > 0
    assert body["summary"]["production_readiness_backlog_rows"] > 0
    assert body["summary"]["analysis_section_catalog_rows"] > 0
    assert body["summary"]["analysis_script_catalog_rows"] > 0
    assert body["summary"]["analysis_provenance_map_rows"] > 0
    assert body["summary"]["analysis_execution_map_rows"] > 0
    assert body["summary"]["analysis_chart_data_snapshot_rows"] > 0
    assert body["summary"]["intelligence_metric_catalog_rows"] > 0
    assert body["summary"]["analysis_feature_derivation_catalog_rows"] > 0
    assert body["summary"]["analysis_consulting_playbook_rows"] > 0
    assert body["summary"]["analysis_insight_brief_rows"] > 0
    assert body["summary"]["client_meeting_deck_blueprint_rows"] > 0
    assert body["summary"]["analysis_review_board_rows"] > 0
    assert body["summary"]["analysis_package_index_rows"] > 0
    assert body["summary"]["campaign_target_rows"] > 0
    assert body["summary"]["csm_review_queue_rows"] > 0
    assert body["summary"]["analyst_validation_queue_rows"] > 0
    assert body["summary"]["marketing_activation_export_rows"] > 0
    assert body["summary"]["banker_call_list_rows"] > 0
    assert body["summary"]["data_team_load_plan_rows"] > 0
    assert body["summary"]["stakeholder_export_manifest_rows"] > 0
    assert body["summary"]["measurement_baseline_rows"] > 0
    assert body["action_plan"]
    assert body["intake_work_order"]
    assert body["file_assembly_plan"]
    assert body["monthly_file_requirements"]
    assert {"input_family", "monthly_status", "target_snowflake_layer", "data_team_action"}.issubset(
        body["monthly_file_requirements"][0]
    )
    assert body["layout_gap_report"]
    assert body["layout_contract_draft_queue"]
    assert {"file_name", "proposed_contract_id", "contract_action", "data_team_action"}.issubset(
        body["layout_contract_draft_queue"][0]
    )
    assert body["layout_contract_export_manifest"]
    assert {"proposed_contract_id", "yaml_relative_path", "yaml_ready", "data_team_action"}.issubset(
        body["layout_contract_export_manifest"][0]
    )
    assert body["intelligence_lineage_graph"]
    assert {"lineage_stage", "source_node_type", "target_node_type", "relationship"}.issubset(
        body["intelligence_lineage_graph"][0]
    )
    assert body["engine_run_ledger"]
    assert body["account_intelligence_profile"]
    assert body["model_rulebook"]
    assert body["account_scoring_trace"]
    assert body["counterparty_signals"]
    assert body["counterparty_summary"]
    assert body["relationship_segments"]
    assert body["segment_summary"]
    assert body["executive_scorecard"]
    assert body["strategy_roadmap"]
    assert body["consulting_insight_register"]
    assert body["intelligence_delta_report"]
    assert body["role_handoffs"]
    assert body["operating_control_plane"]
    assert {"workflow_lane", "role", "open_first", "next_action"}.issubset(
        body["operating_control_plane"][0]
    )
    assert body["user_interaction_map"]
    assert {"user_role", "primary_screen", "file_name", "decision_supported", "owner_next_action"}.issubset(
        body["user_interaction_map"][0]
    )
    assert body["production_readiness_backlog"]
    assert {"workstream", "priority_band", "problem_statement", "required_action"}.issubset(
        body["production_readiness_backlog"][0]
    )
    assert body["analysis_section_catalog"]
    assert body["analysis_script_catalog"]
    assert body["analysis_provenance_map"]
    assert body["analysis_execution_map"]
    assert body["analysis_chart_data_snapshot"]
    assert {"source_section_id", "data_artifact", "data_status", "insight_callout"}.issubset(
        body["analysis_chart_data_snapshot"][0]
    )
    assert body["intelligence_metric_catalog"]
    assert {"metric_id", "source_artifact", "source_field", "validation_status", "csm_interpretation"}.issubset(
        body["intelligence_metric_catalog"][0]
    )
    assert body["analysis_feature_derivation_catalog"]
    assert {
        "analysis_field_key",
        "derived_output_lineage",
        "base_input_requirements",
        "snowflake_expression_hint",
    }.issubset(body["analysis_feature_derivation_catalog"][0])
    assert body["analysis_consulting_playbook"]
    assert {"source_section_id", "client_story_role", "primary_output_file", "csm_talk_track"}.issubset(
        body["analysis_consulting_playbook"][0]
    )
    assert body["analysis_insight_brief"]
    assert {"source_section_id", "headline_insight", "data_caveat", "recommended_client_question"}.issubset(
        body["analysis_insight_brief"][0]
    )
    assert body["client_meeting_deck_blueprint"]
    assert {"blueprint_rank", "meeting_phase", "slide_title", "decision_prompt", "blueprint_status"}.issubset(
        body["client_meeting_deck_blueprint"][0]
    )
    assert body["analysis_review_board"]
    assert {"source_section_id", "what_is_analyzed", "chart_count", "headline_insight", "review_status"}.issubset(
        body["analysis_review_board"][0]
    )
    assert body["analysis_package_index"]
    assert body["consulting_story"]["story_arc"]
    assert body["measurement_plan"]
    assert body["campaign_targets"]
    assert body["csm_review_queue"]
    assert body["analyst_validation_queue"]
    assert body["marketing_activation_export"]
    assert body["banker_call_list"]
    assert body["data_team_load_plan"]
    assert body["stakeholder_export_manifest"]
    assert body["measurement_baseline"]
    assert body["quality"]["transaction_rows"] == 4


def test_intelligence_run_uses_prior_package_for_outcomes(app_module):
    prior = _stage_intelligence_inputs(app_module, month="2026.03")
    current = _stage_intelligence_inputs(app_module, month="2026.04")
    _write_client_config(app_module)

    prior_run = "prior_intelligence"
    app_module.runs[prior_run] = {
        "status": "running",
        "client_id": prior["client_id"],
        "csm": prior["csm"],
        "month": prior["month"],
        "product": "intelligence",
        "started": "2026-08-15T10:00:00",
        "progress": 0,
        "current_step": "Starting",
        "log": [],
    }
    app_module._run_intelligence_engine(prior_run, prior["csm"], prior["month"], prior["client_id"])
    assert app_module.runs[prior_run]["status"] == "complete"

    current_run = "current_intelligence"
    app_module.runs[current_run] = {
        "status": "running",
        "client_id": current["client_id"],
        "csm": current["csm"],
        "month": current["month"],
        "product": "intelligence",
        "started": "2026-08-15T10:05:00",
        "progress": 0,
        "current_step": "Starting",
        "log": [],
    }
    app_module._run_intelligence_engine(current_run, current["csm"], current["month"], current["client_id"])

    assert app_module.runs[current_run]["status"] == "complete"
    assert any("Prior measurement package" in line for line in app_module.runs[current_run]["log"])
    out_dir = app_module.COMPLETED_INTELLIGENCE / current["csm"] / current["month"] / current["client_id"]
    outcomes = pd.read_csv(out_dir / "outcome_results.csv")
    summary = pd.read_csv(out_dir / "outcome_summary.csv")
    delta = pd.read_csv(out_dir / "intelligence_delta_report.csv")
    assert len(outcomes) > 0
    assert len(summary) > 0
    assert len(delta) > 0
    assert "baseline_run" not in set(delta["delta_type"])
