-- Transactional Intelligence Engine Snowflake load script
-- Run snowflake/001_foundation.sql and snowflake/002_transactional_intelligence_outputs.sql first.
USE SCHEMA out;

PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/file_ledger.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/intake_work_order.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/file_assembly_plan.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/monthly_file_requirements.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/layout_gap_report.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/source_layout_profile.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/layout_contract_draft_queue.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/layout_contract_export_manifest.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/intelligence_lineage_graph.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/engine_run_ledger.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/engine_readiness_assessment.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/account_month_features.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/account_intelligence_profile.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/model_rulebook.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/account_scoring_trace.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/pfi_verdicts.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/counterparty_signals.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/counterparty_summary.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/relationship_segments.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/segment_summary.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/opportunities.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/opportunity_portfolio.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/executive_scorecard.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/strategy_roadmap.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/action_plan.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/measurement_plan.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/campaign_targets.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/csm_review_queue.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analyst_validation_queue.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/marketing_activation_export.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/banker_call_list.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/data_team_load_plan.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/stakeholder_export_manifest.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/measurement_baseline.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/outcome_results.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/outcome_summary.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/intelligence_delta_report.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/consulting_insight_register.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/role_handoffs.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/operating_control_plane.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/user_interaction_map.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/production_readiness_backlog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_section_catalog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_script_catalog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_field_usage_catalog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_provenance_map.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_execution_map.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_domain_map.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_input_dependency_map.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_layout_coverage_matrix.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_data_team_backlog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_metric_validation_queue.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_visual_output_map.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_chart_spec_catalog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_chart_data_snapshot.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/intelligence_metric_catalog.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_section_evidence_review.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_requirement_matrix.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_consulting_playbook.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_insight_brief.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/client_meeting_deck_blueprint.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_review_board.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/analysis_package_index.csv @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/data_quality.json @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/insights.json @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/consulting_story.json @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/run_summary.json @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://01_Analysis/01_Completed_Intelligence/Demo/9999/2026.07_measurement_run/intake_profile.json @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118 AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- file_ledger.csv -> out.ti_file_ledger
COPY INTO out.ti_file_ledger
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/file_ledger.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- intake_work_order.csv -> out.ti_intake_work_order
COPY INTO out.ti_intake_work_order
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/intake_work_order.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- file_assembly_plan.csv -> out.ti_file_assembly_plan
COPY INTO out.ti_file_assembly_plan
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/file_assembly_plan.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- monthly_file_requirements.csv -> out.ti_monthly_file_requirements
COPY INTO out.ti_monthly_file_requirements
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/monthly_file_requirements.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- layout_gap_report.csv -> out.ti_layout_gap_report
COPY INTO out.ti_layout_gap_report
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/layout_gap_report.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- source_layout_profile.csv -> out.ti_source_layout_profile
COPY INTO out.ti_source_layout_profile
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/source_layout_profile.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- layout_contract_draft_queue.csv -> out.ti_layout_contract_draft_queue
COPY INTO out.ti_layout_contract_draft_queue
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/layout_contract_draft_queue.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- layout_contract_export_manifest.csv -> out.ti_layout_contract_export_manifest
COPY INTO out.ti_layout_contract_export_manifest
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/layout_contract_export_manifest.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- intelligence_lineage_graph.csv -> out.ti_intelligence_lineage_graph
COPY INTO out.ti_intelligence_lineage_graph
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/intelligence_lineage_graph.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- engine_run_ledger.csv -> out.ti_engine_run_ledger
COPY INTO out.ti_engine_run_ledger
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/engine_run_ledger.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- engine_readiness_assessment.csv -> out.ti_engine_readiness_assessment
COPY INTO out.ti_engine_readiness_assessment
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/engine_readiness_assessment.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- account_month_features.csv -> mart.ti_account_month_features
COPY INTO mart.ti_account_month_features
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/account_month_features.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- account_intelligence_profile.csv -> mart.ti_account_intelligence_profile
COPY INTO mart.ti_account_intelligence_profile
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/account_intelligence_profile.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- model_rulebook.csv -> out.ti_model_rulebook
COPY INTO out.ti_model_rulebook
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/model_rulebook.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- account_scoring_trace.csv -> out.ti_account_scoring_trace
COPY INTO out.ti_account_scoring_trace
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/account_scoring_trace.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- pfi_verdicts.csv -> mart.ti_pfi_verdicts
COPY INTO mart.ti_pfi_verdicts
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/pfi_verdicts.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- counterparty_signals.csv -> mart.ti_counterparty_signals
COPY INTO mart.ti_counterparty_signals
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/counterparty_signals.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- counterparty_summary.csv -> mart.ti_counterparty_summary
COPY INTO mart.ti_counterparty_summary
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/counterparty_summary.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- relationship_segments.csv -> mart.ti_relationship_segments
COPY INTO mart.ti_relationship_segments
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/relationship_segments.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- segment_summary.csv -> mart.ti_segment_summary
COPY INTO mart.ti_segment_summary
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/segment_summary.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- opportunities.csv -> mart.ti_opportunities
COPY INTO mart.ti_opportunities
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/opportunities.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- opportunity_portfolio.csv -> mart.ti_opportunity_portfolio
COPY INTO mart.ti_opportunity_portfolio
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/opportunity_portfolio.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- executive_scorecard.csv -> out.ti_executive_scorecard
COPY INTO out.ti_executive_scorecard
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/executive_scorecard.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- strategy_roadmap.csv -> out.ti_strategy_roadmap
COPY INTO out.ti_strategy_roadmap
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/strategy_roadmap.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- action_plan.csv -> out.ti_action_plan
COPY INTO out.ti_action_plan
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/action_plan.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- measurement_plan.csv -> out.ti_measurement_plan
COPY INTO out.ti_measurement_plan
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/measurement_plan.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- campaign_targets.csv -> out.ti_campaign_targets
COPY INTO out.ti_campaign_targets
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/campaign_targets.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- csm_review_queue.csv -> out.ti_csm_review_queue
COPY INTO out.ti_csm_review_queue
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/csm_review_queue.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analyst_validation_queue.csv -> out.ti_analyst_validation_queue
COPY INTO out.ti_analyst_validation_queue
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analyst_validation_queue.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- marketing_activation_export.csv -> out.ti_marketing_activation_export
COPY INTO out.ti_marketing_activation_export
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/marketing_activation_export.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- banker_call_list.csv -> out.ti_banker_call_list
COPY INTO out.ti_banker_call_list
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/banker_call_list.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- data_team_load_plan.csv -> out.ti_data_team_load_plan
COPY INTO out.ti_data_team_load_plan
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/data_team_load_plan.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- stakeholder_export_manifest.csv -> out.ti_stakeholder_export_manifest
COPY INTO out.ti_stakeholder_export_manifest
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/stakeholder_export_manifest.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- measurement_baseline.csv -> out.ti_measurement_baseline
COPY INTO out.ti_measurement_baseline
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/measurement_baseline.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- outcome_results.csv -> out.ti_outcome_results
COPY INTO out.ti_outcome_results
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/outcome_results.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- outcome_summary.csv -> out.ti_outcome_summary
COPY INTO out.ti_outcome_summary
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/outcome_summary.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- intelligence_delta_report.csv -> out.ti_intelligence_delta_report
COPY INTO out.ti_intelligence_delta_report
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/intelligence_delta_report.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- consulting_insight_register.csv -> out.ti_consulting_insight_register
COPY INTO out.ti_consulting_insight_register
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/consulting_insight_register.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- role_handoffs.csv -> out.ti_role_handoffs
COPY INTO out.ti_role_handoffs
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/role_handoffs.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- operating_control_plane.csv -> out.ti_operating_control_plane
COPY INTO out.ti_operating_control_plane
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/operating_control_plane.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- user_interaction_map.csv -> out.ti_user_interaction_map
COPY INTO out.ti_user_interaction_map
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/user_interaction_map.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- production_readiness_backlog.csv -> out.ti_production_readiness_backlog
COPY INTO out.ti_production_readiness_backlog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/production_readiness_backlog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_section_catalog.csv -> out.ti_analysis_section_catalog
COPY INTO out.ti_analysis_section_catalog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_section_catalog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_script_catalog.csv -> out.ti_analysis_script_catalog
COPY INTO out.ti_analysis_script_catalog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_script_catalog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_field_usage_catalog.csv -> out.ti_analysis_field_usage_catalog
COPY INTO out.ti_analysis_field_usage_catalog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_field_usage_catalog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_provenance_map.csv -> out.ti_analysis_provenance_map
COPY INTO out.ti_analysis_provenance_map
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_provenance_map.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_execution_map.csv -> out.ti_analysis_execution_map
COPY INTO out.ti_analysis_execution_map
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_execution_map.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_domain_map.csv -> out.ti_analysis_domain_map
COPY INTO out.ti_analysis_domain_map
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_domain_map.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_input_dependency_map.csv -> out.ti_analysis_input_dependency_map
COPY INTO out.ti_analysis_input_dependency_map
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_input_dependency_map.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_layout_coverage_matrix.csv -> out.ti_analysis_layout_coverage_matrix
COPY INTO out.ti_analysis_layout_coverage_matrix
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_layout_coverage_matrix.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_data_team_backlog.csv -> out.ti_analysis_data_team_backlog
COPY INTO out.ti_analysis_data_team_backlog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_data_team_backlog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_metric_validation_queue.csv -> out.ti_analysis_metric_validation_queue
COPY INTO out.ti_analysis_metric_validation_queue
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_metric_validation_queue.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_visual_output_map.csv -> out.ti_analysis_visual_output_map
COPY INTO out.ti_analysis_visual_output_map
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_visual_output_map.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_chart_spec_catalog.csv -> out.ti_analysis_chart_spec_catalog
COPY INTO out.ti_analysis_chart_spec_catalog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_chart_spec_catalog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_chart_data_snapshot.csv -> out.ti_analysis_chart_data_snapshot
COPY INTO out.ti_analysis_chart_data_snapshot
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_chart_data_snapshot.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- intelligence_metric_catalog.csv -> out.ti_intelligence_metric_catalog
COPY INTO out.ti_intelligence_metric_catalog
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/intelligence_metric_catalog.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_section_evidence_review.csv -> out.ti_analysis_section_evidence_review
COPY INTO out.ti_analysis_section_evidence_review
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_section_evidence_review.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_requirement_matrix.csv -> out.ti_analysis_requirement_matrix
COPY INTO out.ti_analysis_requirement_matrix
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_requirement_matrix.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_consulting_playbook.csv -> out.ti_analysis_consulting_playbook
COPY INTO out.ti_analysis_consulting_playbook
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_consulting_playbook.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_insight_brief.csv -> out.ti_analysis_insight_brief
COPY INTO out.ti_analysis_insight_brief
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_insight_brief.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- client_meeting_deck_blueprint.csv -> out.ti_client_meeting_deck_blueprint
COPY INTO out.ti_client_meeting_deck_blueprint
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/client_meeting_deck_blueprint.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_review_board.csv -> out.ti_analysis_review_board
COPY INTO out.ti_analysis_review_board
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_review_board.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- analysis_package_index.csv -> out.ti_analysis_package_index
COPY INTO out.ti_analysis_package_index
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/analysis_package_index.csv
FILE_FORMAT = (FORMAT_NAME = out.ti_csv_header)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = 'ABORT_STATEMENT';

-- data_quality.json -> out.ti_data_quality
INSERT INTO out.ti_data_quality (run_id, client_id, period_month, artifact_name, quality_payload)
SELECT 'ti_9999_2026_07_20260816010118', '9999', '2026.07', 'data_quality', $1
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/data_quality.json (FILE_FORMAT => out.ti_json);

-- insights.json -> out.ti_insights
INSERT INTO out.ti_insights (run_id, client_id, period_month, insight_id, insight_payload)
SELECT 'ti_9999_2026_07_20260816010118', '9999', '2026.07', $1:insight_id::STRING, $1
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/insights.json (FILE_FORMAT => out.ti_json_array);

-- consulting_story.json -> out.ti_consulting_story
INSERT INTO out.ti_consulting_story (run_id, client_id, period_month, artifact_name, story_payload)
SELECT 'ti_9999_2026_07_20260816010118', '9999', '2026.07', 'consulting_story', $1
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/consulting_story.json (FILE_FORMAT => out.ti_json);

-- run_summary.json -> out.ti_run_summary
INSERT INTO out.ti_run_summary (run_id, client_id, period_month, artifact_name, summary_payload)
SELECT 'ti_9999_2026_07_20260816010118', '9999', '2026.07', 'run_summary', $1
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/run_summary.json (FILE_FORMAT => out.ti_json);

-- intake_profile.json -> out.ti_intake_profile
INSERT INTO out.ti_intake_profile (run_id, client_id, period_month, file_name, profile_payload)
SELECT 'ti_9999_2026_07_20260816010118', '9999', '2026.07', $1:file_name::STRING, $1
FROM @raw.client_file_stage/transactional_intelligence/9999/2026_07/ti_9999_2026_07_20260816010118/intake_profile.json (FILE_FORMAT => out.ti_json_array);

