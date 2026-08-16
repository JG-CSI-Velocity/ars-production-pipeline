"""Snowflake-ready package generation for intelligence outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any

import pandas as pd

from ars_engine.intelligence.engine import EngineConfig, EngineOutputs


CSV_TARGETS = {
    "file_ledger": ("file_ledger.csv", "out.ti_file_ledger"),
    "intake_work_order": ("intake_work_order.csv", "out.ti_intake_work_order"),
    "file_assembly_plan": ("file_assembly_plan.csv", "out.ti_file_assembly_plan"),
    "monthly_file_requirements": ("monthly_file_requirements.csv", "out.ti_monthly_file_requirements"),
    "layout_gap_report": ("layout_gap_report.csv", "out.ti_layout_gap_report"),
    "source_layout_profile": ("source_layout_profile.csv", "out.ti_source_layout_profile"),
    "layout_contract_draft_queue": (
        "layout_contract_draft_queue.csv",
        "out.ti_layout_contract_draft_queue",
    ),
    "layout_contract_export_manifest": (
        "layout_contract_export_manifest.csv",
        "out.ti_layout_contract_export_manifest",
    ),
    "intelligence_lineage_graph": (
        "intelligence_lineage_graph.csv",
        "out.ti_intelligence_lineage_graph",
    ),
    "engine_run_ledger": ("engine_run_ledger.csv", "out.ti_engine_run_ledger"),
    "engine_readiness_assessment": (
        "engine_readiness_assessment.csv",
        "out.ti_engine_readiness_assessment",
    ),
    "account_month_features": ("account_month_features.csv", "mart.ti_account_month_features"),
    "account_intelligence_profile": ("account_intelligence_profile.csv", "mart.ti_account_intelligence_profile"),
    "model_rulebook": ("model_rulebook.csv", "out.ti_model_rulebook"),
    "account_scoring_trace": ("account_scoring_trace.csv", "out.ti_account_scoring_trace"),
    "pfi_verdicts": ("pfi_verdicts.csv", "mart.ti_pfi_verdicts"),
    "counterparty_signals": ("counterparty_signals.csv", "mart.ti_counterparty_signals"),
    "counterparty_summary": ("counterparty_summary.csv", "mart.ti_counterparty_summary"),
    "relationship_segments": ("relationship_segments.csv", "mart.ti_relationship_segments"),
    "segment_summary": ("segment_summary.csv", "mart.ti_segment_summary"),
    "opportunities": ("opportunities.csv", "mart.ti_opportunities"),
    "opportunity_portfolio": ("opportunity_portfolio.csv", "mart.ti_opportunity_portfolio"),
    "executive_scorecard": ("executive_scorecard.csv", "out.ti_executive_scorecard"),
    "strategy_roadmap": ("strategy_roadmap.csv", "out.ti_strategy_roadmap"),
    "action_plan": ("action_plan.csv", "out.ti_action_plan"),
    "measurement_plan": ("measurement_plan.csv", "out.ti_measurement_plan"),
    "campaign_targets": ("campaign_targets.csv", "out.ti_campaign_targets"),
    "csm_review_queue": ("csm_review_queue.csv", "out.ti_csm_review_queue"),
    "analyst_validation_queue": ("analyst_validation_queue.csv", "out.ti_analyst_validation_queue"),
    "marketing_activation_export": ("marketing_activation_export.csv", "out.ti_marketing_activation_export"),
    "banker_call_list": ("banker_call_list.csv", "out.ti_banker_call_list"),
    "data_team_load_plan": ("data_team_load_plan.csv", "out.ti_data_team_load_plan"),
    "stakeholder_export_manifest": ("stakeholder_export_manifest.csv", "out.ti_stakeholder_export_manifest"),
    "measurement_baseline": ("measurement_baseline.csv", "out.ti_measurement_baseline"),
    "outcome_results": ("outcome_results.csv", "out.ti_outcome_results"),
    "outcome_summary": ("outcome_summary.csv", "out.ti_outcome_summary"),
    "intelligence_delta_report": ("intelligence_delta_report.csv", "out.ti_intelligence_delta_report"),
    "consulting_insight_register": ("consulting_insight_register.csv", "out.ti_consulting_insight_register"),
    "role_handoffs": ("role_handoffs.csv", "out.ti_role_handoffs"),
    "operating_control_plane": ("operating_control_plane.csv", "out.ti_operating_control_plane"),
    "user_interaction_map": ("user_interaction_map.csv", "out.ti_user_interaction_map"),
    "production_readiness_backlog": (
        "production_readiness_backlog.csv",
        "out.ti_production_readiness_backlog",
    ),
    "analysis_section_catalog": ("analysis_section_catalog.csv", "out.ti_analysis_section_catalog"),
    "analysis_script_catalog": ("analysis_script_catalog.csv", "out.ti_analysis_script_catalog"),
    "analysis_field_usage_catalog": ("analysis_field_usage_catalog.csv", "out.ti_analysis_field_usage_catalog"),
    "analysis_provenance_map": ("analysis_provenance_map.csv", "out.ti_analysis_provenance_map"),
    "analysis_execution_map": ("analysis_execution_map.csv", "out.ti_analysis_execution_map"),
    "analysis_domain_map": ("analysis_domain_map.csv", "out.ti_analysis_domain_map"),
    "analysis_input_dependency_map": ("analysis_input_dependency_map.csv", "out.ti_analysis_input_dependency_map"),
    "analysis_layout_coverage_matrix": (
        "analysis_layout_coverage_matrix.csv",
        "out.ti_analysis_layout_coverage_matrix",
    ),
    "analysis_feature_derivation_catalog": (
        "analysis_feature_derivation_catalog.csv",
        "out.ti_analysis_feature_derivation_catalog",
    ),
    "analysis_data_team_backlog": (
        "analysis_data_team_backlog.csv",
        "out.ti_analysis_data_team_backlog",
    ),
    "analysis_metric_validation_queue": (
        "analysis_metric_validation_queue.csv",
        "out.ti_analysis_metric_validation_queue",
    ),
    "analysis_visual_output_map": (
        "analysis_visual_output_map.csv",
        "out.ti_analysis_visual_output_map",
    ),
    "analysis_chart_spec_catalog": (
        "analysis_chart_spec_catalog.csv",
        "out.ti_analysis_chart_spec_catalog",
    ),
    "analysis_chart_data_snapshot": (
        "analysis_chart_data_snapshot.csv",
        "out.ti_analysis_chart_data_snapshot",
    ),
    "intelligence_metric_catalog": (
        "intelligence_metric_catalog.csv",
        "out.ti_intelligence_metric_catalog",
    ),
    "analysis_section_evidence_review": (
        "analysis_section_evidence_review.csv",
        "out.ti_analysis_section_evidence_review",
    ),
    "analysis_requirement_matrix": ("analysis_requirement_matrix.csv", "out.ti_analysis_requirement_matrix"),
    "analysis_consulting_playbook": (
        "analysis_consulting_playbook.csv",
        "out.ti_analysis_consulting_playbook",
    ),
    "analysis_insight_brief": (
        "analysis_insight_brief.csv",
        "out.ti_analysis_insight_brief",
    ),
    "client_meeting_deck_blueprint": (
        "client_meeting_deck_blueprint.csv",
        "out.ti_client_meeting_deck_blueprint",
    ),
    "analysis_review_board": (
        "analysis_review_board.csv",
        "out.ti_analysis_review_board",
    ),
    "analysis_package_index": ("analysis_package_index.csv", "out.ti_analysis_package_index"),
}

JSON_TARGETS = {
    "data_quality": ("data_quality.json", "out.ti_data_quality"),
    "insights": ("insights.json", "out.ti_insights"),
    "consulting_story": ("consulting_story.json", "out.ti_consulting_story"),
    "run_summary": ("run_summary.json", "out.ti_run_summary"),
    "intake_profile": ("intake_profile.json", "out.ti_intake_profile"),
}


def write_snowflake_package(
    outputs: EngineOutputs,
    output_dir: Path | str,
    *,
    config: EngineConfig | None = None,
    artifact_paths: dict[str, str] | None = None,
    run_id: str | None = None,
) -> dict[str, str]:
    """Write Snowflake manifest and load SQL for a completed engine run."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = config or EngineConfig()
    resolved_run_id = run_id or _run_id(cfg, out)
    artifacts = artifact_paths or {}
    stage_prefix = f"transactional_intelligence/{_clean(cfg.client_id or 'unknown')}/{_clean(cfg.period_month or 'unknown')}/{resolved_run_id}"
    manifest = _manifest(outputs, out, cfg=cfg, run_id=resolved_run_id, stage_prefix=stage_prefix, artifacts=artifacts)

    manifest_path = out / "snowflake_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=_json_default) + "\n", encoding="utf-8")

    sql_path = out / "snowflake_load.sql"
    sql_path.write_text(_load_sql(manifest), encoding="utf-8")

    readme_html_path = out / "README_SNOWFLAKE.html"
    readme_html_path.write_text(_readme_html(manifest), encoding="utf-8")

    return {
        "snowflake_manifest": str(manifest_path),
        "snowflake_load_sql": str(sql_path),
        "snowflake_readme": str(readme_html_path),
        "snowflake_readme_html": str(readme_html_path),
    }


def _manifest(
    outputs: EngineOutputs,
    output_dir: Path,
    *,
    cfg: EngineConfig,
    run_id: str,
    stage_prefix: str,
    artifacts: dict[str, str],
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for name, (filename, target_table) in CSV_TARGETS.items():
        path = output_dir / filename
        df = getattr(outputs, name if name != "account_month_features" else "account_month_features")
        files.append(_file_entry(name, path, target_table, stage_prefix, row_count=len(df), file_format="csv"))
    for name, (filename, target_table) in JSON_TARGETS.items():
        path = output_dir / filename
        files.append(_file_entry(name, path, target_table, stage_prefix, row_count=_json_row_count(path), file_format="json"))
    for name, path_text in sorted(artifacts.items()):
        path = Path(path_text)
        if path.name in {entry["file_name"] for entry in files}:
            continue
        files.append(_file_entry(name, path, "out.ti_artifact", stage_prefix, row_count=1, file_format="artifact"))

    return {
        "manifest_version": "transactional_intelligence_snowflake.v1",
        "run_id": run_id,
        "client_id": cfg.client_id,
        "client_name": cfg.client_name,
        "period_month": cfg.period_month,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": "raw.client_file_stage",
        "stage_prefix": stage_prefix,
        "requires": ["snowflake/001_foundation.sql", "snowflake/002_transactional_intelligence_outputs.sql"],
        "files": files,
        "row_counts": {
            "file_ledger": len(outputs.file_ledger),
            "intake_work_order": len(outputs.intake_work_order),
            "file_assembly_plan": len(outputs.file_assembly_plan),
            "monthly_file_requirements": len(outputs.monthly_file_requirements),
            "layout_gap_report": len(outputs.layout_gap_report),
            "source_layout_profile": len(outputs.source_layout_profile),
            "layout_contract_draft_queue": len(outputs.layout_contract_draft_queue),
            "layout_contract_export_manifest": len(outputs.layout_contract_export_manifest),
            "intelligence_lineage_graph": len(outputs.intelligence_lineage_graph),
            "engine_run_ledger": len(outputs.engine_run_ledger),
            "engine_readiness_assessment": len(outputs.engine_readiness_assessment),
            "account_month_features": len(outputs.account_month_features),
            "account_intelligence_profile": len(outputs.account_intelligence_profile),
            "model_rulebook": len(outputs.model_rulebook),
            "account_scoring_trace": len(outputs.account_scoring_trace),
            "pfi_verdicts": len(outputs.pfi_verdicts),
            "counterparty_signals": len(outputs.counterparty_signals),
            "counterparty_summary": len(outputs.counterparty_summary),
            "relationship_segments": len(outputs.relationship_segments),
            "segment_summary": len(outputs.segment_summary),
            "opportunities": len(outputs.opportunities),
            "opportunity_portfolio": len(outputs.opportunity_portfolio),
            "executive_scorecard": len(outputs.executive_scorecard),
            "strategy_roadmap": len(outputs.strategy_roadmap),
            "action_plan": len(outputs.action_plan),
            "measurement_plan": len(outputs.measurement_plan),
            "campaign_targets": len(outputs.campaign_targets),
            "csm_review_queue": len(outputs.csm_review_queue),
            "analyst_validation_queue": len(outputs.analyst_validation_queue),
            "marketing_activation_export": len(outputs.marketing_activation_export),
            "banker_call_list": len(outputs.banker_call_list),
            "data_team_load_plan": len(outputs.data_team_load_plan),
            "stakeholder_export_manifest": len(outputs.stakeholder_export_manifest),
            "measurement_baseline": len(outputs.measurement_baseline),
            "outcome_results": len(outputs.outcome_results),
            "outcome_summary": len(outputs.outcome_summary),
            "intelligence_delta_report": len(outputs.intelligence_delta_report),
            "consulting_insight_register": len(outputs.consulting_insight_register),
            "role_handoffs": len(outputs.role_handoffs),
            "operating_control_plane": len(outputs.operating_control_plane),
            "user_interaction_map": len(outputs.user_interaction_map),
            "production_readiness_backlog": len(outputs.production_readiness_backlog),
            "analysis_section_catalog": len(outputs.analysis_section_catalog),
            "analysis_script_catalog": len(outputs.analysis_script_catalog),
            "analysis_field_usage_catalog": len(outputs.analysis_field_usage_catalog),
            "analysis_provenance_map": len(outputs.analysis_provenance_map),
            "analysis_execution_map": len(outputs.analysis_execution_map),
            "analysis_domain_map": len(outputs.analysis_domain_map),
            "analysis_input_dependency_map": len(outputs.analysis_input_dependency_map),
            "analysis_layout_coverage_matrix": len(outputs.analysis_layout_coverage_matrix),
            "analysis_feature_derivation_catalog": len(outputs.analysis_feature_derivation_catalog),
            "analysis_data_team_backlog": len(outputs.analysis_data_team_backlog),
            "analysis_metric_validation_queue": len(outputs.analysis_metric_validation_queue),
            "analysis_visual_output_map": len(outputs.analysis_visual_output_map),
            "analysis_chart_spec_catalog": len(outputs.analysis_chart_spec_catalog),
            "analysis_chart_data_snapshot": len(outputs.analysis_chart_data_snapshot),
            "intelligence_metric_catalog": len(outputs.intelligence_metric_catalog),
            "analysis_section_evidence_review": len(outputs.analysis_section_evidence_review),
            "analysis_requirement_matrix": len(outputs.analysis_requirement_matrix),
            "analysis_consulting_playbook": len(outputs.analysis_consulting_playbook),
            "analysis_insight_brief": len(outputs.analysis_insight_brief),
            "client_meeting_deck_blueprint": len(outputs.client_meeting_deck_blueprint),
            "analysis_review_board": len(outputs.analysis_review_board),
            "analysis_package_index": len(outputs.analysis_package_index),
            "consulting_story": 1 if outputs.consulting_story else 0,
            "insights": len(outputs.insights),
        },
        "quality_score": outputs.data_quality.get("quality_score"),
    }


def _file_entry(
    artifact_name: str,
    path: Path,
    target_table: str,
    stage_prefix: str,
    *,
    row_count: int,
    file_format: str,
) -> dict[str, Any]:
    return {
        "artifact_name": artifact_name,
        "file_name": path.name,
        "local_path": str(path),
        "stage_path": f"@raw.client_file_stage/{stage_prefix}/{path.name}",
        "target_table": target_table,
        "file_format": file_format,
        "row_count": int(row_count),
        "exists": path.exists(),
    }


def _load_sql(manifest: dict[str, Any]) -> str:
    client_id = _sql_string(manifest.get("client_id", ""))
    period_month = _sql_string(manifest.get("period_month", ""))
    run_id = _sql_string(manifest.get("run_id", ""))
    lines = [
        "-- Transactional Intelligence Engine Snowflake load script",
        "-- Run snowflake/001_foundation.sql and snowflake/002_transactional_intelligence_outputs.sql first.",
        "USE SCHEMA out;",
        "",
    ]
    for file in manifest["files"]:
        if file["file_format"] == "artifact":
            continue
        lines.append(f"PUT file://{_escape_put_path(file['local_path'])} {file['stage_path'].rsplit('/', 1)[0]} AUTO_COMPRESS=FALSE OVERWRITE=TRUE;")
    lines.append("")

    for file in manifest["files"]:
        target = file["target_table"]
        stage_path = file["stage_path"]
        fmt = file["file_format"]
        artifact = _sql_string(file["artifact_name"])
        if fmt == "csv":
            lines.extend([
                f"-- {file['file_name']} -> {target}",
                f"COPY INTO {target}",
                f"FROM {stage_path}",
                "FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)",
                "MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE",
                "ON_ERROR = 'ABORT_STATEMENT';",
                "",
            ])
        elif file["artifact_name"] == "insights":
            lines.extend([
                f"-- {file['file_name']} -> {target}",
                f"INSERT INTO {target} (run_id, client_id, period_month, insight_id, insight_payload)",
                f"SELECT {run_id}, {client_id}, {period_month}, $1:insight_id::STRING, $1",
                f"FROM {stage_path} (FILE_FORMAT => out.ti_json_array);",
                "",
            ])
        elif file["artifact_name"] == "intake_profile":
            lines.extend([
                f"-- {file['file_name']} -> {target}",
                f"INSERT INTO {target} (run_id, client_id, period_month, file_name, profile_payload)",
                f"SELECT {run_id}, {client_id}, {period_month}, $1:file_name::STRING, $1",
                f"FROM {stage_path} (FILE_FORMAT => out.ti_json_array);",
                "",
            ])
        else:
            payload_col = {
                "data_quality": "quality_payload",
                "run_summary": "summary_payload",
                "consulting_story": "story_payload",
            }.get(file["artifact_name"], "payload")
            lines.extend([
                f"-- {file['file_name']} -> {target}",
                f"INSERT INTO {target} (run_id, client_id, period_month, artifact_name, {payload_col})",
                f"SELECT {run_id}, {client_id}, {period_month}, {artifact}, $1",
                f"FROM {stage_path} (FILE_FORMAT => out.ti_json);",
                "",
            ])

    artifact_rows = [file for file in manifest["files"] if file["file_format"] == "artifact"]
    if artifact_rows:
        lines.append("-- Register non-table artifacts for lineage and downloads.")
        for file in artifact_rows:
            lines.append(
                "INSERT INTO out.ti_artifact "
                "(run_id, client_id, period_month, artifact_name, artifact_type, local_path, stage_path) "
                f"VALUES ({run_id}, {client_id}, {period_month}, {_sql_string(file['artifact_name'])}, "
                f"{_sql_string(Path(file['file_name']).suffix.lstrip('.') or 'file')}, "
                f"{_sql_string(file['local_path'])}, {_sql_string(file['stage_path'])});"
            )
    lines.append("")
    return "\n".join(lines)


def _readme(manifest: dict[str, Any]) -> str:
    file_rows = "\n".join(
        f"- `{f['file_name']}` -> `{f['target_table']}` ({f['row_count']} row(s))"
        for f in manifest["files"]
    )
    return f"""# Snowflake Load Package

Run ID: `{manifest['run_id']}`

Client: `{manifest.get('client_id', '')}`

Period: `{manifest.get('period_month', '')}`

1. Run `snowflake/001_foundation.sql`.
2. Run `snowflake/002_transactional_intelligence_outputs.sql`.
3. Run `snowflake_load.sql` from this output folder in SnowSQL or a Snowflake worksheet with local file access configured.

## Files

{file_rows}
"""


def _readme_html(manifest: dict[str, Any]) -> str:
    file_rows = "\n".join(
        "<tr>"
        f"<td><code>{escape(str(f['file_name']))}</code></td>"
        f"<td><code>{escape(str(f['target_table']))}</code></td>"
        f"<td>{int(f['row_count'])}</td>"
        f"<td>{escape(str(f['file_format']))}</td>"
        "</tr>"
        for f in manifest["files"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Snowflake Load Package</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #14213d; background: #f6f7f9; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1 {{ margin: 0 0 10px; font-size: 28px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    p, li {{ line-height: 1.45; }}
    code {{ background: #eef1f5; border: 1px solid #d9dee8; border-radius: 4px; padding: 2px 5px; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }}
    .metric {{ background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #5f6b7a; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .metric strong {{ display: block; font-size: 20px; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d9dee8; }}
    th, td {{ border-bottom: 1px solid #e6e9ef; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #edf2f8; color: #344054; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    @media (max-width: 760px) {{ main {{ padding: 18px; }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Snowflake Load Package</h1>
  <section class="grid" aria-label="Package metadata">
    <div class="metric"><span>Run ID</span><strong>{escape(str(manifest['run_id']))}</strong></div>
    <div class="metric"><span>Client</span><strong>{escape(str(manifest.get('client_id', '')))}</strong></div>
    <div class="metric"><span>Period</span><strong>{escape(str(manifest.get('period_month', '')))}</strong></div>
  </section>

  <h2>Load Steps</h2>
  <ol>
    <li>Run <code>snowflake/001_foundation.sql</code>.</li>
    <li>Run <code>snowflake/002_transactional_intelligence_outputs.sql</code>.</li>
    <li>Run <code>snowflake_load.sql</code> from this output folder in SnowSQL or a Snowflake worksheet with local file access configured.</li>
  </ol>

  <h2>Files</h2>
  <table>
    <thead><tr><th>File</th><th>Target table</th><th>Rows</th><th>Format</th></tr></thead>
    <tbody>{file_rows}</tbody>
  </table>
</main>
</body>
</html>
"""


def _run_id(cfg: EngineConfig, output_dir: Path) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"ti_{_clean(cfg.client_id or output_dir.name)}_{_clean(cfg.period_month or 'period')}_{stamp}"


def _clean(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_") or "unknown"


def _json_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if isinstance(data, list):
        return len(data)
    return 1


def _escape_put_path(path_text: str) -> str:
    return path_text.replace(" ", "\\ ")


def _sql_string(value: object) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return str(value)
