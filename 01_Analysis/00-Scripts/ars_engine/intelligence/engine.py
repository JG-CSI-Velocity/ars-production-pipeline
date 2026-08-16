"""V1 transactional intelligence engine.

The existing pipeline is excellent at section-level analytics. This module
creates the product layer those sections need: reusable account-month features,
PFI verdicts, ranked opportunity records, and insight objects that can render
to decks, dashboards, CSVs, APIs, or Snowflake tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import csv
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

from ars_engine.intelligence.catalog import (
    build_analysis_field_usage_catalog,
    build_analysis_provenance_map,
    build_analysis_script_catalog,
    build_analysis_section_catalog,
)
from ars_engine.intelligence.intake import (
    build_file_assembly_plan,
    build_intake_work_order,
    build_layout_gap_report,
    profile_input_files,
    summarize_file_assembly_plan,
    summarize_intake_work_order,
    summarize_layout_gap_report,
    write_intake_profile,
)


ACCOUNT_ID_COLUMNS = (
    "account_id",
    "account",
    "account number",
    "account_number",
    "account_num",
    "primary_account_num",
    "primary account number",
    "member account",
    "acct",
    "acct_no",
)
DATE_COLUMNS = (
    "transaction_date",
    "transaction date",
    "posted_date",
    "post date",
    "effective_date",
    "date",
    "tran date",
)
AMOUNT_COLUMNS = (
    "amount",
    "transaction_amount",
    "transaction amount",
    "txn_amount",
    "tran amount",
    "amt",
)
MERCHANT_COLUMNS = (
    "merchant",
    "merchant_name",
    "merchant name",
    "description",
    "transaction_description",
    "transaction description",
    "memo",
    "payee",
    "counterparty",
)
TYPE_COLUMNS = (
    "transaction_type",
    "transaction type",
    "txn_type",
    "type",
    "channel",
    "tran code",
)
BALANCE_COLUMNS = (
    "avg bal",
    "average balance",
    "avg balance",
    "current balance",
    "balance",
    "available balance",
)
DEBIT_COLUMNS = (
    "debit?",
    "dc indicator",
    "debit indicator",
    "has_debit",
    "has debit",
    "debit_card",
    "debit card",
)
BUSINESS_COLUMNS = ("business?", "business", "business flag", "is_business")
BRANCH_COLUMNS = ("branch", "branch name", "branch_name", "branch number", "branch_num")
PRODUCT_COLUMNS = ("product code", "product_code", "prod code", "prod desc", "product")
DATE_OPENED_COLUMNS = ("date opened", "date_opened", "open date", "opened date")
STATUS_COLUMNS = ("stat code", "status", "account status", "status code")

PAYROLL_TERMS = (
    "payroll",
    "pay check",
    "paycheck",
    "salary",
    "direct deposit",
    "direct dep",
    "dir dep",
    "adp",
    "paychex",
    "gusto",
    "workday",
    "paylocity",
    "paycor",
)
EXTERNAL_FI_TERMS = (
    "bank",
    "credit union",
    "chase",
    "wells fargo",
    "bank of america",
    "bofa",
    "citi",
    "citibank",
    "capital one",
    "ally",
    "sofi",
    "paypal",
    "venmo",
    "cash app",
    "zelle",
    "robinhood",
    "fidelity",
    "vanguard",
    "american express",
    "discover",
)
FINANCIAL_SERVICE_TERMS = (
    "mortgage",
    "loan",
    "lending",
    "insurance",
    "credit card",
    "auto finance",
    "student loan",
    "affirm",
    "klarna",
    "afterpay",
    "rocket mortgage",
    "quicken loans",
    "synchrony",
)

SOURCE_SECTIONS_BY_OPPORTUNITY = {
    "payroll_conversion": ["txn.payroll", "txn.relationship", "txn.competition"],
    "debit_activation": ["ars.dctr", "txn.interchange", "txn.general"],
    "deposit_retention": ["txn.balance", "txn.competition", "txn.relationship"],
    "competitor_winback": ["txn.competition", "txn.financial_services"],
    "dormant_reactivation": ["txn.retention", "txn.engagement", "txn.attrition_txn"],
    "relationship_expansion": ["txn.relationship", "txn.financial_services"],
    "attrition_prevention": ["ars.attrition", "txn.attrition_txn", "txn.retention"],
}

ANALYSIS_DOMAIN_DEFINITIONS = [
    {
        "domain_id": "portfolio_foundation",
        "domain_name": "Portfolio Foundation",
        "business_question": "What is the usable account base and how is it structured?",
        "sections": [
            "ars.overview",
            "txn.general",
            "txn.product",
            "txn.business_accts",
            "txn.personal_accts",
        ],
        "required_input_families": ["accounts", "product_relationship"],
        "intelligence_products": ["data_quality", "account_month_features", "executive_scorecard"],
        "consulting_use": "Establish denominators, eligibility, account mix, and benchmarkable portfolio profile.",
    },
    {
        "domain_id": "spend_merchant_channel",
        "domain_name": "Spend, Merchant, and Channel",
        "business_question": "Where is activity concentrating, changing, or leaking?",
        "sections": ["txn.merchant", "txn.mcc_code", "txn.transaction_type", "txn.branch_txn"],
        "required_input_families": ["accounts", "transactions", "counterparty_taxonomy"],
        "intelligence_products": ["counterparty_signals", "counterparty_summary", "relationship_segments"],
        "consulting_use": "Explain merchant concentration, category behavior, channel migration, and branch-owned action.",
    },
    {
        "domain_id": "competitive_leakage",
        "domain_name": "Competitive Leakage",
        "business_question": "Which outside institutions and ecosystems are capturing wallet share?",
        "sections": ["txn.competition", "txn.financial_services"],
        "required_input_families": ["accounts", "transactions", "counterparty_taxonomy"],
        "intelligence_products": ["counterparty_signals", "pfi_verdicts", "opportunities"],
        "consulting_use": "Detect external FI pressure, lender relationships, fintech activity, and win-back opportunity.",
    },
    {
        "domain_id": "primacy_payroll_relationship",
        "domain_name": "Primacy, Payroll, and Relationship",
        "business_question": "Who owns the relationship and where is primacy weak?",
        "sections": ["txn.payroll", "txn.relationship", "txn.balance"],
        "required_input_families": ["accounts", "transactions", "balances", "product_relationship"],
        "intelligence_products": ["account_month_features", "pfi_verdicts", "relationship_segments", "opportunities"],
        "consulting_use": "Connect payroll, balances, product depth, and external movement to primacy diagnosis.",
    },
    {
        "domain_id": "retention_lifecycle",
        "domain_name": "Retention and Lifecycle",
        "business_question": "Who is degrading, dormant, at risk, or ready to upgrade?",
        "sections": [
            "ars.attrition",
            "txn.attrition_txn",
            "txn.retention",
            "txn.engagement",
            "txn.segment_evolution",
        ],
        "required_input_families": ["accounts", "transactions", "outcomes"],
        "intelligence_products": ["relationship_segments", "segment_summary", "opportunities", "outcome_summary"],
        "consulting_use": "Prioritize save lists, dormant reactivation, engagement intervention, and lifecycle strategy.",
    },
    {
        "domain_id": "debit_reg_e_revenue",
        "domain_name": "Debit, Reg E, and Revenue",
        "business_question": "Where is card, overdraft, interchange, or modeled value opportunity?",
        "sections": ["ars.dctr", "ars.rege", "txn.rege_overdraft", "txn.interchange", "ars.value"],
        "required_input_families": ["accounts", "transactions", "balances"],
        "intelligence_products": ["opportunities", "opportunity_portfolio", "strategy_roadmap", "measurement_plan"],
        "consulting_use": "Size activation, compliant education, interchange, and revenue/value plays.",
    },
    {
        "domain_id": "campaign_cohort_measurement",
        "domain_name": "Campaign and Cohort Measurement",
        "business_question": "Which actions changed behavior and what should be targeted next?",
        "sections": ["ars.mailer", "txn.campaign", "txn.ics_acquisition", "txn.ICS_cohort"],
        "required_input_families": ["accounts", "transactions", "campaign_history", "outcomes", "suppressions"],
        "intelligence_products": ["campaign_targets", "measurement_baseline", "outcome_results", "outcome_summary"],
        "consulting_use": "Standardize target lists, holdouts, response, lift, persistence, and next-campaign learning.",
    },
    {
        "domain_id": "executive_synthesis",
        "domain_name": "Executive Synthesis",
        "business_question": "What is the story, decision, priority, and roadmap?",
        "sections": ["ars.insights", "txn.executive"],
        "required_input_families": ["accounts", "transactions"],
        "intelligence_products": ["insights", "consulting_story", "executive_scorecard", "strategy_roadmap"],
        "consulting_use": "Roll technical analysis into board-ready priorities, decisions, and action roadmap.",
    },
]

INPUT_FAMILY_DEFINITIONS = {
    "accounts": {
        "display_name": "Account / ODD",
        "canonical_role": "Defines the account denominator, eligibility, product mix, and relationship base.",
        "minimum_fields": "account_id|status_or_open_flag|product_code|date_opened|balance_or_avg_balance",
        "optional_fields": "date_closed|branch_id|account_holder_age|business_flag|has_debit|reg_e_status",
        "source_candidates": "ODD extract|core account extract|modified ODD fallback",
        "current_contract_status": "seed_contract_available:account.odd_extract.v1",
        "snowflake_design_decision": "Stage raw client layouts first; promote stable account fields into core account dimension after layout validation.",
    },
    "transactions": {
        "display_name": "Transactions",
        "canonical_role": "Powers behavior, spend, merchant, payroll, competitor, channel, and retention signals.",
        "minimum_fields": "account_id|transaction_date|amount|transaction_type|merchant_or_description",
        "optional_fields": "mcc_code|terminal_location|merchant_id|institution|card_present|transaction_code",
        "source_candidates": "raw tran file|monthly transaction extract|card/ACH/check extracts",
        "current_contract_status": "seed_contract_available:txn.velocity_standard.v1",
        "snowflake_design_decision": "Keep raw file lineage; normalize to transaction fact only after account key and date/amount mappings are proven.",
    },
    "balances": {
        "display_name": "Balance / Liquidity",
        "canonical_role": "Supports deposit retention, PFI, liquidity pressure, Reg E, and value sizing.",
        "minimum_fields": "account_id|period_month|current_balance_or_avg_balance",
        "optional_fields": "available_balance|low_balance_days|balance_band|balance_trend",
        "source_candidates": "ODD balance columns|separate balance extract|core daily/monthly balance file",
        "current_contract_status": "client_specific_or_odd_derived",
        "snowflake_design_decision": "Do not assume a separate balance fact until client layouts show whether balances are embedded or separately supplied.",
    },
    "product_relationship": {
        "display_name": "Product / Relationship",
        "canonical_role": "Supports product depth, cross-sell, single-product risk, and household/member relationship context.",
        "minimum_fields": "account_id|product_code|open_date|status",
        "optional_fields": "member_id|household_id|product_group|tenure|relationship_value",
        "source_candidates": "ODD product fields|core relationship file|household/member extract",
        "current_contract_status": "client_specific_contract_needed",
        "snowflake_design_decision": "Model as relationship dimensions only after join keys and household/member grain are confirmed.",
    },
    "counterparty_taxonomy": {
        "display_name": "Counterparty / Taxonomy",
        "canonical_role": "Converts raw descriptions into payroll, competitor, lender, merchant, and ecosystem meaning.",
        "minimum_fields": "raw_description_or_merchant|normalized_counterparty|counterparty_category",
        "optional_fields": "brand_family|competitor_tier|payroll_processor_flag|lender_category|taxonomy_confidence",
        "source_candidates": "engine rules|merchant normalization table|client-approved taxonomy overrides",
        "current_contract_status": "internal_rules_plus_client_validation",
        "snowflake_design_decision": "Persist rule version and confidence; allow client overrides without rewriting raw transactions.",
    },
    "campaign_history": {
        "display_name": "Campaign History",
        "canonical_role": "Supports targeting, exposure, response, holdout, uplift, and persistence measurement.",
        "minimum_fields": "account_id|campaign_id_or_wave|targeted_flag|campaign_date",
        "optional_fields": "offer|channel|control_flag|response_flag|response_date|creative|segment",
        "source_candidates": "mailer file|campaign audience export|marketing platform report",
        "current_contract_status": "client_specific_contract_needed",
        "snowflake_design_decision": "Create campaign fact only after audience, wave, response, and control semantics are mapped.",
    },
    "suppressions": {
        "display_name": "Suppression / Compliance",
        "canonical_role": "Prevents bad outreach and defines which opportunities are actually addressable.",
        "minimum_fields": "account_id|suppression_reason",
        "optional_fields": "effective_date|expiration_date|channel|source_system|compliance_category",
        "source_candidates": "do-not-contact file|closed/suppressed account list|marketing suppression export",
        "current_contract_status": "client_specific_contract_needed",
        "snowflake_design_decision": "Keep suppressions as an activation-control table joined late to targets and exports.",
    },
    "outcomes": {
        "display_name": "Outcome History",
        "canonical_role": "Measures whether an action produced activation, conversion, retention, or value change.",
        "minimum_fields": "account_id|measurement_period|outcome_metric",
        "optional_fields": "measurement_id|campaign_id|test_control_group|baseline_value|current_value|conversion_date",
        "source_candidates": "derived current-month features|campaign response file|future outcome extract",
        "current_contract_status": "derived_first_then_contract_when_available",
        "snowflake_design_decision": "Derive from monthly feature history first; add explicit outcome extracts when clients provide them.",
    },
}

ARTIFACT_LAYER_MAP = {
    "file_ledger": ("Intake", "Data team"),
    "intake_profile": ("Intake", "Data team"),
    "intake_work_order": ("Intake", "Analyst"),
    "file_assembly_plan": ("Intake", "Analyst"),
    "monthly_file_requirements": ("Intake", "Data team"),
    "layout_gap_report": ("Intake", "Data team"),
    "source_layout_profile": ("Intake", "Data team"),
    "layout_contract_draft_queue": ("Intake", "Data team"),
    "layout_contract_export_manifest": ("Intake", "Data team"),
    "intelligence_lineage_graph": ("Audit", "Analyst"),
    "data_quality": ("Trust", "Analyst"),
    "engine_run_ledger": ("Audit", "Data team"),
    "engine_readiness_assessment": ("Audit", "Owner"),
    "analysis_package_index": ("Audit", "Analyst"),
    "model_rulebook": ("Model Governance", "Analyst"),
    "account_scoring_trace": ("Model Governance", "Analyst"),
    "account_month_features": ("Feature mart", "Data science"),
    "account_intelligence_profile": ("Account Intelligence", "CSM"),
    "pfi_verdicts": ("PFI", "CSM"),
    "counterparty_signals": ("Counterparty", "Analyst"),
    "counterparty_summary": ("Counterparty", "Consultant"),
    "relationship_segments": ("Segmentation", "Consultant"),
    "segment_summary": ("Segmentation", "Consultant"),
    "opportunities": ("Opportunity", "Analyst"),
    "opportunity_portfolio": ("Strategy", "CSM"),
    "executive_scorecard": ("Executive", "Executive"),
    "strategy_roadmap": ("Strategy", "Consultant"),
    "action_plan": ("Action", "CSM"),
    "measurement_plan": ("Measurement", "Analyst"),
    "campaign_targets": ("Activation", "Marketing"),
    "csm_review_queue": ("Execution", "CSM"),
    "analyst_validation_queue": ("Execution", "Analyst"),
    "marketing_activation_export": ("Execution", "Marketing"),
    "banker_call_list": ("Execution", "Client bankers"),
    "data_team_load_plan": ("Execution", "Data team"),
    "stakeholder_export_manifest": ("Execution", "CSM"),
    "measurement_baseline": ("Measurement", "Analyst"),
    "outcome_results": ("Outcome", "Analyst"),
    "outcome_summary": ("Outcome", "CSM"),
    "intelligence_delta_report": ("Outcome", "CSM"),
    "insights": ("Insight", "Consultant"),
    "consulting_insight_register": ("Insight", "Consultant"),
    "role_handoffs": ("Operating model", "CSM"),
    "operating_control_plane": ("Operating model", "CSM"),
    "user_interaction_map": ("Operating model", "CSM"),
    "production_readiness_backlog": ("Productization", "Owner"),
    "analysis_section_catalog": ("Analysis IP", "Analyst"),
    "analysis_script_catalog": ("Analysis IP", "Data science"),
    "analysis_field_usage_catalog": ("Analysis IP", "Data science"),
    "analysis_provenance_map": ("Analysis IP", "Consultant"),
    "analysis_execution_map": ("Analysis IP", "Analyst"),
    "analysis_domain_map": ("Analysis IP", "Consultant"),
    "analysis_input_dependency_map": ("Data strategy", "Data team"),
    "analysis_layout_coverage_matrix": ("Data strategy", "Analyst"),
    "analysis_feature_derivation_catalog": ("Semantic Layer", "Data science"),
    "analysis_data_team_backlog": ("Data strategy", "Data team"),
    "analysis_metric_validation_queue": ("Data strategy", "Analyst"),
    "analysis_visual_output_map": ("Analysis IP", "CSM"),
    "analysis_chart_spec_catalog": ("Analysis IP", "Data science"),
    "analysis_chart_data_snapshot": ("Analysis IP", "BI / Product UI"),
    "intelligence_metric_catalog": ("Semantic Layer", "Data science"),
    "analysis_section_evidence_review": ("Analysis IP", "Consultant"),
    "analysis_requirement_matrix": ("Analysis IP", "Analyst"),
    "analysis_consulting_playbook": ("Story", "CSM"),
    "analysis_insight_brief": ("Story", "CSM"),
    "client_meeting_deck_blueprint": ("Story", "CSM"),
    "analysis_review_board": ("Analysis IP", "CSM"),
    "consulting_story": ("Story", "Consultant"),
    "run_summary": ("Audit", "Analyst"),
}

OPPORTUNITY_PLAYBOOK = {
    "payroll_conversion": {
        "play_name": "Primary Banking Conversion",
        "audience_definition": "Accounts with external money movement or credits but no payroll detected.",
        "owner_role": "CSM plus retail banking",
        "channel": "Email plus banker follow-up",
        "next_step": "Create a direct-deposit conversion audience and review top balances with branch managers.",
        "primary_metric": "new_direct_deposit_or_payroll_detected",
    },
    "debit_activation": {
        "play_name": "Debit Activation",
        "audience_definition": "Low-card-usage or no-card accounts with active relationship evidence.",
        "owner_role": "CSM plus marketing",
        "channel": "Digital campaign",
        "next_step": "Launch debit activation messaging with wallet provisioning or usage incentive.",
        "primary_metric": "new_or_increased_debit_usage",
    },
    "deposit_retention": {
        "play_name": "Deposit Retention",
        "audience_definition": "High-balance accounts showing external FI outflow.",
        "owner_role": "CSM plus branch leadership",
        "channel": "Banker call list",
        "next_step": "Route top households to branch or banker retention outreach.",
        "primary_metric": "retained_balance",
    },
    "competitor_winback": {
        "play_name": "Competitor Winback",
        "audience_definition": "Accounts with repeated external FI activity or competitor-primary PFI verdicts.",
        "owner_role": "CSM plus marketing",
        "channel": "Segmented win-back campaign",
        "next_step": "Prioritize consolidation offers for accounts with repeated competitor movement.",
        "primary_metric": "reduced_external_fi_transfer_share",
    },
    "dormant_reactivation": {
        "play_name": "Dormant Reactivation",
        "audience_definition": "Low-activity accounts with balance or product evidence.",
        "owner_role": "CSM plus lifecycle marketing",
        "channel": "Lifecycle campaign",
        "next_step": "Create a reactivation audience and test digital/card usage prompts.",
        "primary_metric": "recovered_transaction_activity",
    },
    "relationship_expansion": {
        "play_name": "Relationship Expansion",
        "audience_definition": "Thin relationships with external financial activity.",
        "owner_role": "CSM plus retail banking",
        "channel": "Next-best-product outreach",
        "next_step": "Review top thin-relationship accounts for targeted product expansion.",
        "primary_metric": "new_product_or_relationship_depth",
    },
    "attrition_prevention": {
        "play_name": "Attrition Prevention",
        "audience_definition": "Split or competitor-primary relationships with weak internal activity.",
        "owner_role": "CSM plus retention team",
        "channel": "Save-list outreach",
        "next_step": "Escalate highest-risk relationships to a retention save list.",
        "primary_metric": "account_retained_and_activity_stabilized",
    },
}


DERIVED_OUTPUT_FIELD_ALIASES = {
    "account_count": {"account_count", "target_accounts", "test_accounts", "active_accounts"},
    "accounts": {"account_count", "target_accounts", "test_accounts", "active_accounts"},
    "active_accounts": {"account_count", "target_accounts", "test_accounts", "active_accounts"},
    "n_accounts": {"account_count", "target_accounts", "test_accounts", "active_accounts"},
    "unique_accounts": {"account_count", "target_accounts", "test_accounts", "active_accounts"},
    "amount": {"amount", "total_amount", "net_amount", "credit_amount", "debit_amount", "expected_value"},
    "amount_bracket": {"spend_amount", "total_amount", "expected_value"},
    "avg_amount": {"avg_ticket_amount", "avg_ticket", "spend_per_txn"},
    "avg_monthly_spend": {"spend_amount", "avg_delta_spend_amount", "baseline_total_spend"},
    "avg_monthly_spend_per_acct": {"spend_amount", "baseline_total_spend"},
    "avg_monthly_swipes": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_monthly_txns": {"txn_count", "baseline_avg_txn_count"},
    "avg_pin_ticket": {"avg_pin_ticket", "pin_amount", "pin_txn_count"},
    "avg_sig_ratio": {"sig_ratio", "sig_txn_count", "card_txn_count"},
    "avg_sig_ticket": {"avg_sig_ticket", "sig_amount", "sig_txn_count"},
    "avg_spend": {"spend_amount", "avg_delta_spend_amount", "baseline_total_spend"},
    "avg_spend_acct": {"spend_amount", "baseline_total_spend"},
    "avg_spend_per_account": {"spend_amount", "baseline_total_spend"},
    "avg_spend_per_acct": {"spend_amount", "baseline_total_spend"},
    "avg_spend_per_swipe": {"spend_per_txn", "avg_ticket_amount", "spend_amount", "txn_count"},
    "avg_spend_velocity": {"spend_amount", "avg_delta_spend_amount"},
    "avg_swipes": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_swipes_12m": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_swipes_3m": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_swipes_acct": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_swipes_per_account": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_swipes_per_acct": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "avg_swipes_raw": {"txn_count", "card_txn_count"},
    "avg_txn": {"txn_count", "avg_delta_txn_count", "baseline_avg_txn_count"},
    "avg_txn_count": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "avg_txns": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "avg_txns_per_month": {"txn_count", "avg_delta_txn_count", "baseline_avg_txn_count"},
    "baseline_value": {"baseline_expected_value", "baseline_total_spend", "baseline_total_credit"},
    "campaign_outcome": {"test_outcome_rate", "test_outcome_accounts", "measurement_status"},
    "category": {"counterparty_category", "opportunity_type", "segment_group"},
    "category_count": {"counterparty_category", "opportunity_count"},
    "category_label": {"counterparty_category", "opportunity_type"},
    "competitor_signal": {
        "external_fi_count",
        "external_fi_amount",
        "external_intensity",
        "external_score",
        "relationship_signal",
        "reason_codes",
        "top_relationship_signal",
    },
    "cumulative_txn_pct": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "credit_amt": {"credit_amount", "avg_delta_credit_amount", "baseline_total_credit"},
    "current_value": {"metric_value", "measured_expected_value"},
    "debit_status": {"has_debit"},
    "did_spend_lift": {"avg_delta_spend_amount", "test_outcome_rate", "measurement_status"},
    "did_swipes_lift": {"avg_delta_txn_count", "test_outcome_rate", "measurement_status"},
    "external_amount": {"external_fi_amount", "avg_delta_external_fi_amount"},
    "first_transaction": {"first_txn_date", "first_seen"},
    "first_txn": {"first_txn_date", "first_seen"},
    "first_txn_date": {"first_txn_date", "first_seen"},
    "group": {"measurement_group", "segment_group"},
    "has_debit_or_debit_activity": {"has_debit"},
    "has_pin": {"has_pin", "pin_txn_count", "pin_ratio"},
    "has_sig": {"has_sig", "sig_txn_count", "sig_ratio"},
    "if_all_sig_interchange": {"sig_interchange_est", "sig_amount"},
    "is_pin": {"has_pin", "pin_txn_count", "pin_ratio"},
    "is_sig": {"has_sig", "sig_txn_count", "sig_ratio"},
    "last_12_mon_spend": {"spend_amount", "baseline_total_spend"},
    "last_12_mon_swipes": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "last_12mo_spend": {"spend_amount", "baseline_total_spend"},
    "last_12mo_swipes": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "last_3_mon_spend": {"spend_amount", "avg_delta_spend_amount"},
    "last_3_mon_swipes": {"txn_count", "card_txn_count", "avg_delta_txn_count"},
    "last_3mo_avg_spend": {"spend_amount", "avg_delta_spend_amount"},
    "last_3mo_spend": {"spend_amount", "avg_delta_spend_amount"},
    "last_3mo_swipes": {"txn_count", "card_txn_count", "avg_delta_txn_count"},
    "last_spend": {"spend_amount", "avg_delta_spend_amount"},
    "last_transaction": {"last_seen"},
    "last_txn": {"last_txn_date", "last_seen"},
    "last_txn_date": {"last_seen"},
    "latest_txn_growth": {"avg_delta_txn_count", "txn_count"},
    "m1_total_spend": {"spend_amount", "baseline_total_spend"},
    "m1_total_swipes": {"txn_count", "card_txn_count"},
    "m3_total_spend": {"spend_amount", "avg_delta_spend_amount"},
    "m3_total_swipes": {"txn_count", "card_txn_count", "avg_delta_txn_count"},
    "m6_total_spend": {"spend_amount", "baseline_total_spend"},
    "m6_total_swipes": {"txn_count", "card_txn_count"},
    "merchant": {"counterparty_name", "unique_merchants"},
    "median_spend": {"spend_amount", "baseline_total_spend"},
    "median_spend_per_account": {"spend_amount", "baseline_total_spend"},
    "median_spend_per_acct": {"spend_amount", "baseline_total_spend"},
    "median_swipes": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "median_swipes_per_account": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "median_swipes_per_acct": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "month_spend": {"spend_amount", "baseline_total_spend"},
    "monthly_spend": {"spend_amount", "avg_delta_spend_amount"},
    "monthly_spend_12": {"spend_amount", "baseline_total_spend"},
    "monthly_spend_3": {"spend_amount", "avg_delta_spend_amount"},
    "monthly_swipes12": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "monthly_swipes3": {"txn_count", "card_txn_count", "avg_delta_txn_count"},
    "monthly_swipes_12": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "monthly_swipes_3": {"txn_count", "card_txn_count", "avg_delta_txn_count"},
    "monthly_txn_rate": {"txn_count", "avg_delta_txn_count"},
    "monthly_txns": {"txn_count", "avg_delta_txn_count", "baseline_avg_txn_count"},
    "monthlyspend12": {"spend_amount", "baseline_total_spend"},
    "monthlyspend3": {"spend_amount", "avg_delta_spend_amount"},
    "monthlyswipes12": {"txn_count", "card_txn_count", "baseline_avg_txn_count"},
    "monthlyswipes3": {"txn_count", "card_txn_count", "avg_delta_txn_count"},
    "oddd_12mo_spend": {"spend_amount", "baseline_total_spend"},
    "oddd_3mo_spend": {"spend_amount", "avg_delta_spend_amount"},
    "oddd_total_spend": {"spend_amount", "baseline_total_spend"},
    "payroll_signal": {"payroll_detected", "payroll_count", "payroll_amount"},
    "pct_pin": {"pin_ratio", "pin_txn_count", "card_txn_count"},
    "pct_sig": {"sig_ratio", "sig_txn_count", "card_txn_count"},
    "pin": {"pin_txn_count", "pin_amount", "pin_ratio"},
    "pin_count": {"pin_txn_count"},
    "pin_dollars": {"pin_amount"},
    "pin_ic": {"pin_interchange_est"},
    "pin_interchange": {"pin_interchange_est"},
    "pin_num": {"pin_txn_count"},
    "pin_preference": {"pin_ratio", "pin_txn_count"},
    "pin_ratio": {"pin_ratio"},
    "pin_txns": {"pin_txn_count"},
    "post_spend": {"spend_amount", "avg_delta_spend_amount"},
    "pre_close_monthly_spend": {"spend_amount", "avg_delta_spend_amount"},
    "pre_spend": {"baseline_total_spend", "spend_amount"},
    "pre_swipes": {"baseline_avg_txn_count", "txn_count", "card_txn_count"},
    "prev_txn": {"first_txn_date", "last_txn_date"},
    "post_swipes": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "prior_3mo_avg_spend": {"spend_amount", "baseline_total_spend"},
    "recent_spend": {"spend_amount", "avg_delta_spend_amount"},
    "recent_txn": {"last_txn_date", "last_seen", "txn_count"},
    "sig": {"sig_txn_count", "sig_amount", "sig_ratio"},
    "sig_count": {"sig_txn_count"},
    "sig_d2": {"sig_txn_count", "sig_ratio"},
    "sig_dollars": {"sig_amount"},
    "sig_ic": {"sig_interchange_est"},
    "sig_interchange": {"sig_interchange_est"},
    "sig_num": {"sig_txn_count"},
    "sig_pct": {"sig_ratio"},
    "sig_ratio": {"sig_ratio"},
    "sig_ratio_pct": {"sig_ratio"},
    "sig_share_pct": {"sig_ratio"},
    "sig_txns": {"sig_txn_count"},
    "spend": {"spend_amount", "avg_delta_spend_amount", "baseline_total_spend"},
    "spend_acct_month": {"spend_amount", "baseline_total_spend"},
    "spend_band": {"spend_amount", "engagement_tier"},
    "spend_decline": {"avg_delta_spend_amount", "test_outcome_rate"},
    "spend_growth": {"avg_delta_spend_amount", "spend_amount"},
    "spend_growth_m1_m3": {"avg_delta_spend_amount", "spend_amount"},
    "spend_growth_m3_m6": {"avg_delta_spend_amount", "spend_amount"},
    "spend_per_acct_month": {"spend_amount"},
    "spend_per_mo": {"spend_amount", "avg_delta_spend_amount", "baseline_total_spend"},
    "spend_per_swipe": {"spend_per_txn", "avg_ticket_amount", "spend_amount", "txn_count"},
    "spend_pct": {"spend_amount"},
    "spend_per_acct_mo": {"spend_amount"},
    "spend_share_pct": {"spend_amount", "total_amount"},
    "spend_slope": {"avg_delta_spend_amount", "spend_amount"},
    "spend_tier": {"engagement_tier", "spend_amount"},
    "spend_velocity": {"avg_delta_spend_amount", "spend_amount"},
    "status_code": {"account_status", "target_status", "status"},
    "swipe_velocity": {"txn_count", "avg_delta_txn_count"},
    "swipe": {"txn_count", "card_txn_count"},
    "swipe_cat12": {"txn_count", "card_txn_count", "engagement_tier"},
    "swipe_cat3": {"txn_count", "card_txn_count", "engagement_tier"},
    "swipe_growth_m1_m3": {"avg_delta_txn_count", "txn_count"},
    "swipe_growth_m3_m6": {"avg_delta_txn_count", "txn_count"},
    "swipes": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "swipecat12": {"txn_count", "card_txn_count", "engagement_tier"},
    "swipecat3": {"txn_count", "card_txn_count", "engagement_tier"},
    "swiped": {"txn_count", "card_txn_count", "has_debit"},
    "total_credit": {"credit_amount", "baseline_total_credit", "avg_delta_credit_amount"},
    "total_l12m_spend": {"spend_amount", "baseline_total_spend"},
    "total_l12m_swipes": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "total_pin_count": {"pin_txn_count"},
    "total_pin_dollars": {"pin_amount"},
    "total_sig_count": {"sig_txn_count"},
    "total_sig_dollars": {"sig_amount"},
    "total_spend": {"spend_amount", "total_amount", "baseline_total_spend", "avg_delta_spend_amount"},
    "total_swipes": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "total_transactions": {"txn_count", "transaction_count", "target_accounts"},
    "total_txn": {"txn_count", "transaction_count"},
    "total_txn_count": {"txn_count", "transaction_count"},
    "total_txns": {"txn_count", "transaction_count"},
    "transaction_count": {"txn_count", "transaction_count"},
    "transactions": {"txn_count", "transaction_count"},
    "txn_count": {"txn_count", "transaction_count"},
    "txn_growth": {"avg_delta_txn_count", "txn_count"},
    "txn_index": {"txn_count", "active_days"},
    "txn_avg_amount": {"avg_ticket_amount", "spend_per_txn"},
    "txn_rolling": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "txns_account": {"txn_count", "transaction_count"},
    "txns_acct_month": {"txn_count", "transaction_count"},
    "txns_month": {"txn_count", "transaction_count"},
    "txns_per_acct": {"txn_count", "transaction_count"},
    "txn_pct": {"txn_count", "transaction_count"},
    "txn_per_account": {"txn_count", "transaction_count"},
    "txns": {"txn_count", "transaction_count"},
    "txns_per_acct_mo": {"txn_count", "avg_delta_txn_count"},
    "txns_per_month": {"txn_count", "transaction_count", "avg_delta_txn_count"},
    "your_spend": {"spend_amount", "total_amount"},
    "your_txns": {"txn_count", "transaction_count"},
}

DERIVED_FEATURE_SEARCH_OUTPUTS = (
    "account_month_features.csv",
    "campaign_targets.csv",
    "measurement_baseline.csv",
    "outcome_summary.csv",
    "counterparty_signals.csv",
    "counterparty_summary.csv",
    "relationship_segments.csv",
    "segment_summary.csv",
    "opportunities.csv",
    "opportunity_portfolio.csv",
    "executive_scorecard.csv",
    "pfi_verdicts.csv",
)


@dataclass(frozen=True)
class EngineConfig:
    """Runtime knobs for a transactional intelligence run."""

    client_id: str = ""
    client_name: str = ""
    period_month: str | None = None
    high_balance_threshold: float = 5000.0
    payroll_min_amount: float = 500.0
    external_fi_amount_threshold: float = 500.0
    active_txn_threshold: int = 10
    strong_txn_threshold: int = 30
    low_activity_txn_threshold: int = 3
    interchange_rate: float = 0.015


@dataclass
class EngineOutputs:
    """All V1 engine outputs for one run."""

    file_ledger: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_quality: dict[str, Any] = field(default_factory=dict)
    intake_profile: list[dict[str, Any]] = field(default_factory=list)
    intake_work_order: pd.DataFrame = field(default_factory=pd.DataFrame)
    file_assembly_plan: pd.DataFrame = field(default_factory=pd.DataFrame)
    monthly_file_requirements: pd.DataFrame = field(default_factory=pd.DataFrame)
    layout_gap_report: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_layout_profile: pd.DataFrame = field(default_factory=pd.DataFrame)
    layout_contract_draft_queue: pd.DataFrame = field(default_factory=pd.DataFrame)
    layout_contract_export_manifest: pd.DataFrame = field(default_factory=pd.DataFrame)
    intelligence_lineage_graph: pd.DataFrame = field(default_factory=pd.DataFrame)
    engine_run_ledger: pd.DataFrame = field(default_factory=pd.DataFrame)
    engine_readiness_assessment: pd.DataFrame = field(default_factory=pd.DataFrame)
    account_month_features: pd.DataFrame = field(default_factory=pd.DataFrame)
    account_intelligence_profile: pd.DataFrame = field(default_factory=pd.DataFrame)
    model_rulebook: pd.DataFrame = field(default_factory=pd.DataFrame)
    account_scoring_trace: pd.DataFrame = field(default_factory=pd.DataFrame)
    pfi_verdicts: pd.DataFrame = field(default_factory=pd.DataFrame)
    counterparty_signals: pd.DataFrame = field(default_factory=pd.DataFrame)
    counterparty_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    relationship_segments: pd.DataFrame = field(default_factory=pd.DataFrame)
    segment_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    opportunities: pd.DataFrame = field(default_factory=pd.DataFrame)
    opportunity_portfolio: pd.DataFrame = field(default_factory=pd.DataFrame)
    executive_scorecard: pd.DataFrame = field(default_factory=pd.DataFrame)
    strategy_roadmap: pd.DataFrame = field(default_factory=pd.DataFrame)
    action_plan: pd.DataFrame = field(default_factory=pd.DataFrame)
    measurement_plan: pd.DataFrame = field(default_factory=pd.DataFrame)
    campaign_targets: pd.DataFrame = field(default_factory=pd.DataFrame)
    csm_review_queue: pd.DataFrame = field(default_factory=pd.DataFrame)
    analyst_validation_queue: pd.DataFrame = field(default_factory=pd.DataFrame)
    marketing_activation_export: pd.DataFrame = field(default_factory=pd.DataFrame)
    banker_call_list: pd.DataFrame = field(default_factory=pd.DataFrame)
    data_team_load_plan: pd.DataFrame = field(default_factory=pd.DataFrame)
    stakeholder_export_manifest: pd.DataFrame = field(default_factory=pd.DataFrame)
    measurement_baseline: pd.DataFrame = field(default_factory=pd.DataFrame)
    outcome_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    outcome_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    intelligence_delta_report: pd.DataFrame = field(default_factory=pd.DataFrame)
    insights: list[dict[str, Any]] = field(default_factory=list)
    consulting_insight_register: pd.DataFrame = field(default_factory=pd.DataFrame)
    role_handoffs: pd.DataFrame = field(default_factory=pd.DataFrame)
    operating_control_plane: pd.DataFrame = field(default_factory=pd.DataFrame)
    user_interaction_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    production_readiness_backlog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_section_catalog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_script_catalog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_field_usage_catalog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_provenance_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_execution_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_domain_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_input_dependency_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_layout_coverage_matrix: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_feature_derivation_catalog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_data_team_backlog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_metric_validation_queue: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_visual_output_map: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_chart_spec_catalog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_chart_data_snapshot: pd.DataFrame = field(default_factory=pd.DataFrame)
    intelligence_metric_catalog: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_section_evidence_review: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_requirement_matrix: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_consulting_playbook: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_insight_brief: pd.DataFrame = field(default_factory=pd.DataFrame)
    client_meeting_deck_blueprint: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_review_board: pd.DataFrame = field(default_factory=pd.DataFrame)
    analysis_package_index: pd.DataFrame = field(default_factory=pd.DataFrame)
    consulting_story: dict[str, Any] = field(default_factory=dict)

    def write(self, output_dir: Path | str) -> dict[str, str]:
        """Write CSV/JSON outputs and return paths by artifact name."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        paths = {
            "file_ledger": out / "file_ledger.csv",
            "data_quality": out / "data_quality.json",
            "intake_profile": out / "intake_profile.json",
            "intake_work_order": out / "intake_work_order.csv",
            "file_assembly_plan": out / "file_assembly_plan.csv",
            "monthly_file_requirements": out / "monthly_file_requirements.csv",
            "layout_gap_report": out / "layout_gap_report.csv",
            "source_layout_profile": out / "source_layout_profile.csv",
            "layout_contract_draft_queue": out / "layout_contract_draft_queue.csv",
            "layout_contract_export_manifest": out / "layout_contract_export_manifest.csv",
            "intelligence_lineage_graph": out / "intelligence_lineage_graph.csv",
            "engine_run_ledger": out / "engine_run_ledger.csv",
            "engine_readiness_assessment": out / "engine_readiness_assessment.csv",
            "account_month_features": out / "account_month_features.csv",
            "account_intelligence_profile": out / "account_intelligence_profile.csv",
            "model_rulebook": out / "model_rulebook.csv",
            "account_scoring_trace": out / "account_scoring_trace.csv",
            "pfi_verdicts": out / "pfi_verdicts.csv",
            "counterparty_signals": out / "counterparty_signals.csv",
            "counterparty_summary": out / "counterparty_summary.csv",
            "relationship_segments": out / "relationship_segments.csv",
            "segment_summary": out / "segment_summary.csv",
            "opportunities": out / "opportunities.csv",
            "opportunity_portfolio": out / "opportunity_portfolio.csv",
            "executive_scorecard": out / "executive_scorecard.csv",
            "strategy_roadmap": out / "strategy_roadmap.csv",
            "action_plan": out / "action_plan.csv",
            "measurement_plan": out / "measurement_plan.csv",
            "campaign_targets": out / "campaign_targets.csv",
            "csm_review_queue": out / "csm_review_queue.csv",
            "analyst_validation_queue": out / "analyst_validation_queue.csv",
            "marketing_activation_export": out / "marketing_activation_export.csv",
            "banker_call_list": out / "banker_call_list.csv",
            "data_team_load_plan": out / "data_team_load_plan.csv",
            "stakeholder_export_manifest": out / "stakeholder_export_manifest.csv",
            "measurement_baseline": out / "measurement_baseline.csv",
            "outcome_results": out / "outcome_results.csv",
            "outcome_summary": out / "outcome_summary.csv",
            "intelligence_delta_report": out / "intelligence_delta_report.csv",
            "insights": out / "insights.json",
            "consulting_insight_register": out / "consulting_insight_register.csv",
            "role_handoffs": out / "role_handoffs.csv",
            "operating_control_plane": out / "operating_control_plane.csv",
            "user_interaction_map": out / "user_interaction_map.csv",
            "production_readiness_backlog": out / "production_readiness_backlog.csv",
            "analysis_section_catalog": out / "analysis_section_catalog.csv",
            "analysis_script_catalog": out / "analysis_script_catalog.csv",
            "analysis_field_usage_catalog": out / "analysis_field_usage_catalog.csv",
            "analysis_provenance_map": out / "analysis_provenance_map.csv",
            "analysis_execution_map": out / "analysis_execution_map.csv",
            "analysis_domain_map": out / "analysis_domain_map.csv",
            "analysis_input_dependency_map": out / "analysis_input_dependency_map.csv",
            "analysis_layout_coverage_matrix": out / "analysis_layout_coverage_matrix.csv",
            "analysis_feature_derivation_catalog": out / "analysis_feature_derivation_catalog.csv",
            "analysis_data_team_backlog": out / "analysis_data_team_backlog.csv",
            "analysis_metric_validation_queue": out / "analysis_metric_validation_queue.csv",
            "analysis_visual_output_map": out / "analysis_visual_output_map.csv",
            "analysis_chart_spec_catalog": out / "analysis_chart_spec_catalog.csv",
            "analysis_chart_data_snapshot": out / "analysis_chart_data_snapshot.csv",
            "intelligence_metric_catalog": out / "intelligence_metric_catalog.csv",
            "analysis_section_evidence_review": out / "analysis_section_evidence_review.csv",
            "analysis_requirement_matrix": out / "analysis_requirement_matrix.csv",
            "analysis_consulting_playbook": out / "analysis_consulting_playbook.csv",
            "analysis_insight_brief": out / "analysis_insight_brief.csv",
            "client_meeting_deck_blueprint": out / "client_meeting_deck_blueprint.csv",
            "analysis_review_board": out / "analysis_review_board.csv",
            "analysis_package_index": out / "analysis_package_index.csv",
            "consulting_story": out / "consulting_story.json",
            "run_summary": out / "run_summary.json",
        }
        self.file_ledger.to_csv(paths["file_ledger"], index=False)
        self.intake_work_order.to_csv(paths["intake_work_order"], index=False)
        self.file_assembly_plan.to_csv(paths["file_assembly_plan"], index=False)
        self.monthly_file_requirements.to_csv(paths["monthly_file_requirements"], index=False)
        self.layout_gap_report.to_csv(paths["layout_gap_report"], index=False)
        self.source_layout_profile.to_csv(paths["source_layout_profile"], index=False)
        self.layout_contract_draft_queue.to_csv(paths["layout_contract_draft_queue"], index=False)
        self.layout_contract_export_manifest.to_csv(paths["layout_contract_export_manifest"], index=False)
        _write_layout_contract_draft_files(
            self.layout_contract_draft_queue,
            self.layout_contract_export_manifest,
            out / "layout_contract_drafts",
        )
        self.intelligence_lineage_graph.to_csv(paths["intelligence_lineage_graph"], index=False)
        self.engine_run_ledger.to_csv(paths["engine_run_ledger"], index=False)
        self.engine_readiness_assessment.to_csv(paths["engine_readiness_assessment"], index=False)
        self.account_month_features.to_csv(paths["account_month_features"], index=False)
        self.account_intelligence_profile.to_csv(paths["account_intelligence_profile"], index=False)
        self.model_rulebook.to_csv(paths["model_rulebook"], index=False)
        self.account_scoring_trace.to_csv(paths["account_scoring_trace"], index=False)
        self.pfi_verdicts.to_csv(paths["pfi_verdicts"], index=False)
        self.counterparty_signals.to_csv(paths["counterparty_signals"], index=False)
        self.counterparty_summary.to_csv(paths["counterparty_summary"], index=False)
        self.relationship_segments.to_csv(paths["relationship_segments"], index=False)
        self.segment_summary.to_csv(paths["segment_summary"], index=False)
        self.opportunities.to_csv(paths["opportunities"], index=False)
        self.opportunity_portfolio.to_csv(paths["opportunity_portfolio"], index=False)
        self.executive_scorecard.to_csv(paths["executive_scorecard"], index=False)
        self.strategy_roadmap.to_csv(paths["strategy_roadmap"], index=False)
        self.action_plan.to_csv(paths["action_plan"], index=False)
        self.measurement_plan.to_csv(paths["measurement_plan"], index=False)
        self.campaign_targets.to_csv(paths["campaign_targets"], index=False)
        self.csm_review_queue.to_csv(paths["csm_review_queue"], index=False)
        self.analyst_validation_queue.to_csv(paths["analyst_validation_queue"], index=False)
        self.marketing_activation_export.to_csv(paths["marketing_activation_export"], index=False)
        self.banker_call_list.to_csv(paths["banker_call_list"], index=False)
        self.data_team_load_plan.to_csv(paths["data_team_load_plan"], index=False)
        self.stakeholder_export_manifest.to_csv(paths["stakeholder_export_manifest"], index=False)
        self.measurement_baseline.to_csv(paths["measurement_baseline"], index=False)
        self.outcome_results.to_csv(paths["outcome_results"], index=False)
        self.outcome_summary.to_csv(paths["outcome_summary"], index=False)
        self.intelligence_delta_report.to_csv(paths["intelligence_delta_report"], index=False)
        self.consulting_insight_register.to_csv(paths["consulting_insight_register"], index=False)
        self.role_handoffs.to_csv(paths["role_handoffs"], index=False)
        self.operating_control_plane.to_csv(paths["operating_control_plane"], index=False)
        self.user_interaction_map.to_csv(paths["user_interaction_map"], index=False)
        self.production_readiness_backlog.to_csv(paths["production_readiness_backlog"], index=False)
        self.analysis_section_catalog.to_csv(paths["analysis_section_catalog"], index=False)
        self.analysis_script_catalog.to_csv(paths["analysis_script_catalog"], index=False)
        self.analysis_field_usage_catalog.to_csv(paths["analysis_field_usage_catalog"], index=False)
        self.analysis_provenance_map.to_csv(paths["analysis_provenance_map"], index=False)
        self.analysis_execution_map.to_csv(paths["analysis_execution_map"], index=False)
        self.analysis_domain_map.to_csv(paths["analysis_domain_map"], index=False)
        self.analysis_input_dependency_map.to_csv(paths["analysis_input_dependency_map"], index=False)
        self.analysis_layout_coverage_matrix.to_csv(paths["analysis_layout_coverage_matrix"], index=False)
        self.analysis_feature_derivation_catalog.to_csv(paths["analysis_feature_derivation_catalog"], index=False)
        self.analysis_data_team_backlog.to_csv(paths["analysis_data_team_backlog"], index=False)
        self.analysis_metric_validation_queue.to_csv(paths["analysis_metric_validation_queue"], index=False)
        self.analysis_visual_output_map.to_csv(paths["analysis_visual_output_map"], index=False)
        self.analysis_chart_spec_catalog.to_csv(paths["analysis_chart_spec_catalog"], index=False)
        self.analysis_chart_data_snapshot.to_csv(paths["analysis_chart_data_snapshot"], index=False)
        self.intelligence_metric_catalog.to_csv(paths["intelligence_metric_catalog"], index=False)
        self.analysis_section_evidence_review.to_csv(paths["analysis_section_evidence_review"], index=False)
        self.analysis_requirement_matrix.to_csv(paths["analysis_requirement_matrix"], index=False)
        self.analysis_consulting_playbook.to_csv(paths["analysis_consulting_playbook"], index=False)
        self.analysis_insight_brief.to_csv(paths["analysis_insight_brief"], index=False)
        self.client_meeting_deck_blueprint.to_csv(paths["client_meeting_deck_blueprint"], index=False)
        self.analysis_review_board.to_csv(paths["analysis_review_board"], index=False)
        write_intake_profile(self.intake_profile, out)
        paths["data_quality"].write_text(
            json.dumps(self.data_quality, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        paths["insights"].write_text(
            json.dumps(self.insights, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        paths["consulting_story"].write_text(
            json.dumps(self.consulting_story, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        summary = {
            "file_count": len(self.file_ledger),
            "intake_work_order_rows": len(self.intake_work_order),
            "file_assembly_plan_rows": len(self.file_assembly_plan),
            "monthly_file_requirements_rows": len(self.monthly_file_requirements),
            "layout_gap_report_rows": len(self.layout_gap_report),
            "source_layout_profile_rows": len(self.source_layout_profile),
            "layout_contract_draft_queue_rows": len(self.layout_contract_draft_queue),
            "layout_contract_export_manifest_rows": len(self.layout_contract_export_manifest),
            "intelligence_lineage_graph_rows": len(self.intelligence_lineage_graph),
            "engine_run_ledger_rows": len(self.engine_run_ledger),
            "engine_readiness_assessment_rows": len(self.engine_readiness_assessment),
            "feature_rows": len(self.account_month_features),
            "account_intelligence_profile_rows": len(self.account_intelligence_profile),
            "model_rulebook_rows": len(self.model_rulebook),
            "account_scoring_trace_rows": len(self.account_scoring_trace),
            "pfi_rows": len(self.pfi_verdicts),
            "counterparty_signal_rows": len(self.counterparty_signals),
            "counterparty_summary_rows": len(self.counterparty_summary),
            "relationship_segment_rows": len(self.relationship_segments),
            "segment_summary_rows": len(self.segment_summary),
            "opportunity_rows": len(self.opportunities),
            "portfolio_rows": len(self.opportunity_portfolio),
            "executive_scorecard_rows": len(self.executive_scorecard),
            "strategy_roadmap_rows": len(self.strategy_roadmap),
            "action_plan_rows": len(self.action_plan),
            "measurement_plan_rows": len(self.measurement_plan),
            "campaign_target_rows": len(self.campaign_targets),
            "csm_review_queue_rows": len(self.csm_review_queue),
            "analyst_validation_queue_rows": len(self.analyst_validation_queue),
            "marketing_activation_export_rows": len(self.marketing_activation_export),
            "banker_call_list_rows": len(self.banker_call_list),
            "data_team_load_plan_rows": len(self.data_team_load_plan),
            "stakeholder_export_manifest_rows": len(self.stakeholder_export_manifest),
            "measurement_baseline_rows": len(self.measurement_baseline),
            "outcome_result_rows": len(self.outcome_results),
            "outcome_summary_rows": len(self.outcome_summary),
            "intelligence_delta_report_rows": len(self.intelligence_delta_report),
            "insight_count": len(self.insights),
            "consulting_insight_register_rows": len(self.consulting_insight_register),
            "role_handoff_rows": len(self.role_handoffs),
            "operating_control_plane_rows": len(self.operating_control_plane),
            "user_interaction_map_rows": len(self.user_interaction_map),
            "production_readiness_backlog_rows": len(self.production_readiness_backlog),
            "analysis_section_catalog_rows": len(self.analysis_section_catalog),
            "analysis_script_catalog_rows": len(self.analysis_script_catalog),
            "analysis_field_usage_catalog_rows": len(self.analysis_field_usage_catalog),
            "analysis_provenance_map_rows": len(self.analysis_provenance_map),
            "analysis_execution_map_rows": len(self.analysis_execution_map),
            "analysis_domain_map_rows": len(self.analysis_domain_map),
            "analysis_input_dependency_map_rows": len(self.analysis_input_dependency_map),
            "analysis_layout_coverage_matrix_rows": len(self.analysis_layout_coverage_matrix),
            "analysis_feature_derivation_catalog_rows": len(self.analysis_feature_derivation_catalog),
            "analysis_data_team_backlog_rows": len(self.analysis_data_team_backlog),
            "analysis_metric_validation_queue_rows": len(self.analysis_metric_validation_queue),
            "analysis_visual_output_map_rows": len(self.analysis_visual_output_map),
            "analysis_chart_spec_catalog_rows": len(self.analysis_chart_spec_catalog),
            "analysis_chart_data_snapshot_rows": len(self.analysis_chart_data_snapshot),
            "intelligence_metric_catalog_rows": len(self.intelligence_metric_catalog),
            "analysis_section_evidence_review_rows": len(self.analysis_section_evidence_review),
            "analysis_requirement_matrix_rows": len(self.analysis_requirement_matrix),
            "analysis_consulting_playbook_rows": len(self.analysis_consulting_playbook),
            "analysis_insight_brief_rows": len(self.analysis_insight_brief),
            "client_meeting_deck_blueprint_rows": len(self.client_meeting_deck_blueprint),
            "analysis_review_board_rows": len(self.analysis_review_board),
            "analysis_package_index_rows": 0,
            "consulting_story_sections": len(self.consulting_story.get("story_arc", [])),
            "intake_file_count": len(self.intake_profile),
            "matched_contract_count": sum(
                1 for item in self.intake_profile
                if item.get("contract_match", {}).get("status") == "matched"
            ),
            "quality_score": self.data_quality.get("quality_score"),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        summary.update({
            f"intake_{key}": value
            for key, value in summarize_intake_work_order(self.intake_work_order).items()
        })
        summary.update({
            f"assembly_{key}": value
            for key, value in summarize_file_assembly_plan(self.file_assembly_plan).items()
        })
        summary.update(summarize_layout_gap_report(self.layout_gap_report))
        paths["run_summary"].write_text(
            json.dumps(summary, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        self.analysis_package_index = build_analysis_package_index(self, paths)
        summary["analysis_package_index_rows"] = len(self.analysis_package_index)
        paths["run_summary"].write_text(
            json.dumps(summary, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        self.analysis_package_index = build_analysis_package_index(self, paths)
        self.analysis_package_index.to_csv(paths["analysis_package_index"], index=False)
        return {name: str(path) for name, path in paths.items()}


def run_transactional_intelligence(
    *,
    accounts: pd.DataFrame | None = None,
    transactions: pd.DataFrame | None = None,
    input_files: Iterable[Path | str] | None = None,
    contract_dir: Path | str | None = None,
    prior_campaign_targets: pd.DataFrame | None = None,
    prior_measurement_baseline: pd.DataFrame | None = None,
    prior_account_intelligence_profile: pd.DataFrame | None = None,
    prior_opportunities: pd.DataFrame | None = None,
    prior_opportunity_portfolio: pd.DataFrame | None = None,
    prior_data_quality: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> EngineOutputs:
    """Run the V1 engine on already-loaded account and transaction data."""
    cfg = config or EngineConfig()
    files = list(input_files or [])
    file_ledger = build_file_ledger(files)
    intake_profile = profile_input_files(files, contract_dir=contract_dir)
    intake_work_order = build_intake_work_order(intake_profile)
    file_assembly_plan = build_file_assembly_plan(intake_work_order)
    layout_gap_report = build_layout_gap_report(intake_profile, contract_dir=contract_dir)
    source_layout_profile = build_source_layout_profile(
        intake_profile,
        intake_work_order,
        layout_gap_report,
        cfg,
    )
    layout_contract_draft_queue = build_layout_contract_draft_queue(
        source_layout_profile,
        layout_gap_report,
        intake_work_order,
        cfg,
    )
    layout_contract_export_manifest = build_layout_contract_export_manifest(
        layout_contract_draft_queue,
        cfg,
    )
    features = build_account_month_features(accounts, transactions, cfg)
    pfi = classify_pfi(features, cfg)
    counterparty_signals = build_counterparty_signals(transactions, cfg)
    counterparty_summary = build_counterparty_summary(counterparty_signals, cfg)
    opportunities = score_opportunities(features, pfi, cfg)
    relationship_segments = build_relationship_segments(features, pfi, opportunities, cfg)
    segment_summary = build_segment_summary(relationship_segments, opportunities, cfg)
    data_quality = assess_data_quality(accounts, transactions, features, file_ledger)
    opportunity_portfolio = build_opportunity_portfolio(opportunities, cfg)
    action_plan = build_action_plan(opportunity_portfolio, cfg)
    measurement_plan = build_measurement_plan(action_plan, cfg)
    campaign_targets = build_campaign_targets(opportunities, action_plan, measurement_plan, features, pfi, cfg)
    account_intelligence_profile = build_account_intelligence_profile(
        features,
        pfi,
        relationship_segments,
        counterparty_signals,
        opportunities,
        campaign_targets,
        cfg,
    )
    model_rulebook = build_model_rulebook(cfg)
    account_scoring_trace = build_account_scoring_trace(
        features,
        pfi,
        relationship_segments,
        account_intelligence_profile,
        opportunities,
        cfg,
    )
    measurement_baseline = build_measurement_baseline(campaign_targets, cfg)
    outcome_results = evaluate_outcomes(prior_campaign_targets, features, pfi, cfg)
    outcome_summary = build_outcome_summary(outcome_results, prior_measurement_baseline, cfg)
    intelligence_delta_report = build_intelligence_delta_report(
        account_intelligence_profile,
        opportunities,
        opportunity_portfolio,
        data_quality,
        prior_account_intelligence_profile=prior_account_intelligence_profile,
        prior_opportunities=prior_opportunities,
        prior_opportunity_portfolio=prior_opportunity_portfolio,
        prior_data_quality=prior_data_quality,
        config=cfg,
    )
    executive_scorecard = build_executive_scorecard(
        features,
        pfi,
        relationship_segments,
        segment_summary,
        opportunity_portfolio,
        action_plan,
        measurement_plan,
        campaign_targets,
        outcome_summary,
        data_quality,
        cfg,
    )
    strategy_roadmap = build_strategy_roadmap(
        executive_scorecard,
        action_plan,
        segment_summary,
        opportunity_portfolio,
        measurement_plan,
        cfg,
    )
    insights = generate_insights(opportunities, data_quality, cfg)
    analysis_section_catalog = build_analysis_section_catalog()
    analysis_script_catalog = build_analysis_script_catalog()
    analysis_field_usage_catalog = build_analysis_field_usage_catalog()
    analysis_provenance_map = build_analysis_provenance_map(SOURCE_SECTIONS_BY_OPPORTUNITY)
    role_handoffs = build_role_handoffs(
        action_plan,
        measurement_plan,
        campaign_targets,
        opportunity_portfolio,
        data_quality,
        cfg,
    )
    stakeholder_exports = build_stakeholder_exports(
        account_intelligence_profile,
        campaign_targets,
        action_plan,
        file_assembly_plan,
        layout_gap_report,
        data_quality,
        cfg,
    )
    consulting_story = build_consulting_story(
        opportunity_portfolio,
        action_plan,
        outcome_summary,
        insights,
        data_quality,
        cfg,
    )
    generated_artifacts = {
        "data_quality": data_quality,
        "account_month_features": features,
        "account_intelligence_profile": account_intelligence_profile,
        "model_rulebook": model_rulebook,
        "account_scoring_trace": account_scoring_trace,
        "pfi_verdicts": pfi,
        "counterparty_signals": counterparty_signals,
        "counterparty_summary": counterparty_summary,
        "relationship_segments": relationship_segments,
        "segment_summary": segment_summary,
        "opportunities": opportunities,
        "opportunity_portfolio": opportunity_portfolio,
        "executive_scorecard": executive_scorecard,
        "strategy_roadmap": strategy_roadmap,
        "action_plan": action_plan,
        "measurement_plan": measurement_plan,
        "campaign_targets": campaign_targets,
        "measurement_baseline": measurement_baseline,
        "outcome_results": outcome_results,
        "outcome_summary": outcome_summary,
        "intelligence_delta_report": intelligence_delta_report,
        "insights": insights,
        "role_handoffs": role_handoffs,
        "consulting_story": consulting_story,
    }
    analysis_execution_map = build_analysis_execution_map(
        analysis_section_catalog,
        analysis_script_catalog,
        analysis_provenance_map,
        model_rulebook,
        generated_artifacts,
        data_quality,
        cfg,
    )
    analysis_domain_map = build_analysis_domain_map(
        analysis_section_catalog,
        analysis_script_catalog,
        analysis_provenance_map,
        analysis_execution_map,
        data_quality,
        cfg,
    )
    analysis_input_dependency_map = build_analysis_input_dependency_map(
        analysis_domain_map,
        analysis_execution_map,
        layout_gap_report,
        file_assembly_plan,
        data_quality,
        cfg,
    )
    monthly_file_requirements = build_monthly_file_requirements(
        analysis_input_dependency_map,
        file_assembly_plan,
        layout_gap_report,
        layout_contract_draft_queue,
        source_layout_profile,
        cfg,
    )
    analysis_requirement_matrix = build_analysis_requirement_matrix(
        analysis_section_catalog,
        analysis_script_catalog,
        analysis_execution_map,
        analysis_domain_map,
        analysis_input_dependency_map,
        cfg,
    )
    analysis_layout_coverage_matrix = build_analysis_layout_coverage_matrix(
        analysis_field_usage_catalog,
        analysis_requirement_matrix,
        analysis_input_dependency_map,
        layout_gap_report,
        generated_artifacts,
        cfg,
    )
    analysis_feature_derivation_catalog = build_analysis_feature_derivation_catalog(
        analysis_layout_coverage_matrix,
        analysis_input_dependency_map,
        cfg,
    )
    analysis_section_evidence_review = build_analysis_section_evidence_review(
        analysis_execution_map,
        analysis_requirement_matrix,
        analysis_field_usage_catalog,
        analysis_layout_coverage_matrix,
        cfg,
    )
    analysis_data_team_backlog = build_analysis_data_team_backlog(analysis_layout_coverage_matrix, cfg)
    analysis_metric_validation_queue = build_analysis_metric_validation_queue(analysis_layout_coverage_matrix, cfg)
    analysis_visual_output_map = build_analysis_visual_output_map(
        analysis_execution_map,
        analysis_section_evidence_review,
        analysis_script_catalog,
        analysis_layout_coverage_matrix,
        cfg,
    )
    analysis_chart_spec_catalog = build_analysis_chart_spec_catalog(
        analysis_visual_output_map,
        generated_artifacts,
        cfg,
    )
    analysis_chart_data_snapshot = build_analysis_chart_data_snapshot(
        analysis_chart_spec_catalog,
        generated_artifacts,
        cfg,
    )
    intelligence_metric_catalog = build_intelligence_metric_catalog(
        analysis_chart_spec_catalog,
        analysis_chart_data_snapshot,
        analysis_metric_validation_queue,
        model_rulebook,
        generated_artifacts,
        cfg,
    )
    analysis_consulting_playbook = build_analysis_consulting_playbook(
        analysis_section_evidence_review,
        analysis_visual_output_map,
        analysis_chart_spec_catalog,
        analysis_requirement_matrix,
        cfg,
    )
    analysis_insight_brief = build_analysis_insight_brief(
        analysis_section_evidence_review,
        analysis_consulting_playbook,
        analysis_chart_data_snapshot,
        intelligence_metric_catalog,
        analysis_requirement_matrix,
        cfg,
    )
    client_meeting_deck_blueprint = build_client_meeting_deck_blueprint(
        consulting_story,
        executive_scorecard,
        strategy_roadmap,
        action_plan,
        measurement_plan,
        analysis_insight_brief,
        intelligence_metric_catalog,
        stakeholder_exports["stakeholder_export_manifest"],
        data_quality,
        cfg,
    )
    analysis_review_board = build_analysis_review_board(
        analysis_section_catalog,
        analysis_execution_map,
        analysis_visual_output_map,
        analysis_chart_spec_catalog,
        analysis_chart_data_snapshot,
        intelligence_metric_catalog,
        analysis_consulting_playbook,
        analysis_insight_brief,
        client_meeting_deck_blueprint,
        analysis_requirement_matrix,
        cfg,
    )
    consulting_insight_register = build_consulting_insight_register(
        insights,
        consulting_story,
        opportunity_portfolio,
        executive_scorecard,
        action_plan,
        measurement_plan,
        analysis_execution_map,
        model_rulebook,
        data_quality,
        cfg,
    )
    engine_run_ledger = build_engine_run_ledger(
        file_ledger=file_ledger,
        intake_work_order=intake_work_order,
        file_assembly_plan=file_assembly_plan,
        layout_gap_report=layout_gap_report,
        source_layout_profile=source_layout_profile,
        layout_contract_draft_queue=layout_contract_draft_queue,
        data_quality=data_quality,
        account_month_features=features,
        account_intelligence_profile=account_intelligence_profile,
        model_rulebook=model_rulebook,
        account_scoring_trace=account_scoring_trace,
        pfi_verdicts=pfi,
        opportunities=opportunities,
        opportunity_portfolio=opportunity_portfolio,
        action_plan=action_plan,
        campaign_targets=campaign_targets,
        intelligence_delta_report=intelligence_delta_report,
        analysis_execution_map=analysis_execution_map,
        analysis_domain_map=analysis_domain_map,
        analysis_input_dependency_map=analysis_input_dependency_map,
        analysis_layout_coverage_matrix=analysis_layout_coverage_matrix,
        analysis_data_team_backlog=analysis_data_team_backlog,
        analysis_metric_validation_queue=analysis_metric_validation_queue,
        analysis_visual_output_map=analysis_visual_output_map,
        analysis_chart_spec_catalog=analysis_chart_spec_catalog,
        analysis_chart_data_snapshot=analysis_chart_data_snapshot,
        intelligence_metric_catalog=intelligence_metric_catalog,
        analysis_section_evidence_review=analysis_section_evidence_review,
        analysis_requirement_matrix=analysis_requirement_matrix,
        analysis_consulting_playbook=analysis_consulting_playbook,
        analysis_insight_brief=analysis_insight_brief,
        client_meeting_deck_blueprint=client_meeting_deck_blueprint,
        analysis_field_usage_catalog=analysis_field_usage_catalog,
        consulting_insight_register=consulting_insight_register,
        stakeholder_export_manifest=stakeholder_exports["stakeholder_export_manifest"],
        config=cfg,
    )
    engine_readiness_assessment = build_engine_readiness_assessment(
        file_ledger=file_ledger,
        intake_work_order=intake_work_order,
        file_assembly_plan=file_assembly_plan,
        layout_gap_report=layout_gap_report,
        layout_contract_draft_queue=layout_contract_draft_queue,
        data_quality=data_quality,
        account_month_features=features,
        account_intelligence_profile=account_intelligence_profile,
        opportunity_portfolio=opportunity_portfolio,
        campaign_targets=campaign_targets,
        outcome_summary=outcome_summary,
        stakeholder_export_manifest=stakeholder_exports["stakeholder_export_manifest"],
        analysis_section_evidence_review=analysis_section_evidence_review,
        analysis_consulting_playbook=analysis_consulting_playbook,
        analysis_data_team_backlog=analysis_data_team_backlog,
        analysis_metric_validation_queue=analysis_metric_validation_queue,
        intelligence_metric_catalog=intelligence_metric_catalog,
        analysis_insight_brief=analysis_insight_brief,
        client_meeting_deck_blueprint=client_meeting_deck_blueprint,
        engine_run_ledger=engine_run_ledger,
        config=cfg,
    )
    operating_control_plane = build_operating_control_plane(
        role_handoffs,
        engine_readiness_assessment,
        stakeholder_exports["stakeholder_export_manifest"],
        executive_scorecard,
        strategy_roadmap,
        action_plan,
        analysis_section_evidence_review,
        data_quality,
        artifact_row_counts={
            "campaign_targets": len(campaign_targets),
            "campaign_targets.csv": len(campaign_targets),
            "transactional_intelligence_package.xlsx": 1,
            "executive_brief.html": 1,
            "snowflake_load.sql": 1,
        },
        config=cfg,
    )
    user_interaction_map = build_user_interaction_map(
        role_handoffs,
        operating_control_plane,
        stakeholder_exports["stakeholder_export_manifest"],
        analysis_review_board,
        client_meeting_deck_blueprint,
        engine_readiness_assessment,
        stakeholder_exports["data_team_load_plan"],
        action_plan,
        measurement_plan,
        config=cfg,
    )
    production_readiness_backlog = build_production_readiness_backlog(
        engine_readiness_assessment,
        analysis_data_team_backlog,
        analysis_metric_validation_queue,
        layout_contract_draft_queue,
        layout_contract_export_manifest,
        monthly_file_requirements,
        analysis_review_board,
        user_interaction_map,
        config=cfg,
    )
    intelligence_lineage_graph = build_intelligence_lineage_graph(
        file_assembly_plan=file_assembly_plan,
        source_layout_profile=source_layout_profile,
        layout_contract_draft_queue=layout_contract_draft_queue,
        analysis_input_dependency_map=analysis_input_dependency_map,
        analysis_layout_coverage_matrix=analysis_layout_coverage_matrix,
        analysis_execution_map=analysis_execution_map,
        analysis_visual_output_map=analysis_visual_output_map,
        analysis_chart_spec_catalog=analysis_chart_spec_catalog,
        analysis_chart_data_snapshot=analysis_chart_data_snapshot,
        intelligence_metric_catalog=intelligence_metric_catalog,
        analysis_insight_brief=analysis_insight_brief,
        client_meeting_deck_blueprint=client_meeting_deck_blueprint,
        analysis_review_board=analysis_review_board,
        user_interaction_map=user_interaction_map,
        production_readiness_backlog=production_readiness_backlog,
        action_plan=action_plan,
        role_handoffs=role_handoffs,
        operating_control_plane=operating_control_plane,
        config=cfg,
    )
    return EngineOutputs(
        file_ledger=file_ledger,
        data_quality=data_quality,
        intake_profile=intake_profile,
        intake_work_order=intake_work_order,
        file_assembly_plan=file_assembly_plan,
        monthly_file_requirements=monthly_file_requirements,
        layout_gap_report=layout_gap_report,
        source_layout_profile=source_layout_profile,
        layout_contract_draft_queue=layout_contract_draft_queue,
        layout_contract_export_manifest=layout_contract_export_manifest,
        intelligence_lineage_graph=intelligence_lineage_graph,
        engine_run_ledger=engine_run_ledger,
        engine_readiness_assessment=engine_readiness_assessment,
        account_month_features=features,
        account_intelligence_profile=account_intelligence_profile,
        model_rulebook=model_rulebook,
        account_scoring_trace=account_scoring_trace,
        pfi_verdicts=pfi,
        counterparty_signals=counterparty_signals,
        counterparty_summary=counterparty_summary,
        relationship_segments=relationship_segments,
        segment_summary=segment_summary,
        opportunities=opportunities,
        opportunity_portfolio=opportunity_portfolio,
        executive_scorecard=executive_scorecard,
        strategy_roadmap=strategy_roadmap,
        action_plan=action_plan,
        measurement_plan=measurement_plan,
        campaign_targets=campaign_targets,
        csm_review_queue=stakeholder_exports["csm_review_queue"],
        analyst_validation_queue=stakeholder_exports["analyst_validation_queue"],
        marketing_activation_export=stakeholder_exports["marketing_activation_export"],
        banker_call_list=stakeholder_exports["banker_call_list"],
        data_team_load_plan=stakeholder_exports["data_team_load_plan"],
        stakeholder_export_manifest=stakeholder_exports["stakeholder_export_manifest"],
        measurement_baseline=measurement_baseline,
        outcome_results=outcome_results,
        outcome_summary=outcome_summary,
        intelligence_delta_report=intelligence_delta_report,
        insights=insights,
        consulting_insight_register=consulting_insight_register,
        role_handoffs=role_handoffs,
        operating_control_plane=operating_control_plane,
        user_interaction_map=user_interaction_map,
        production_readiness_backlog=production_readiness_backlog,
        analysis_section_catalog=analysis_section_catalog,
        analysis_script_catalog=analysis_script_catalog,
        analysis_field_usage_catalog=analysis_field_usage_catalog,
        analysis_provenance_map=analysis_provenance_map,
        analysis_execution_map=analysis_execution_map,
        analysis_domain_map=analysis_domain_map,
        analysis_input_dependency_map=analysis_input_dependency_map,
        analysis_layout_coverage_matrix=analysis_layout_coverage_matrix,
        analysis_feature_derivation_catalog=analysis_feature_derivation_catalog,
        analysis_data_team_backlog=analysis_data_team_backlog,
        analysis_metric_validation_queue=analysis_metric_validation_queue,
        analysis_visual_output_map=analysis_visual_output_map,
        analysis_chart_spec_catalog=analysis_chart_spec_catalog,
        analysis_chart_data_snapshot=analysis_chart_data_snapshot,
        intelligence_metric_catalog=intelligence_metric_catalog,
        analysis_section_evidence_review=analysis_section_evidence_review,
        analysis_requirement_matrix=analysis_requirement_matrix,
        analysis_consulting_playbook=analysis_consulting_playbook,
        analysis_insight_brief=analysis_insight_brief,
        client_meeting_deck_blueprint=client_meeting_deck_blueprint,
        analysis_review_board=analysis_review_board,
        consulting_story=consulting_story,
    )


def build_analysis_package_index(
    outputs: EngineOutputs,
    artifact_paths: dict[str, Path | str],
) -> pd.DataFrame:
    """Build an analyst-readable index of every generated engine artifact."""
    contract = _load_output_contract()
    artifacts = contract.get("artifacts") or {}
    rows: list[dict[str, Any]] = []
    for index, artifact_name in enumerate(artifact_paths, start=1):
        path = Path(artifact_paths[artifact_name])
        meta = artifacts.get(artifact_name, {})
        layer, consumer = ARTIFACT_LAYER_MAP.get(artifact_name, ("Other", "Analyst"))
        primary_key = meta.get("primary_key") or []
        rows.append(
            {
                "package_order": index,
                "artifact_name": artifact_name,
                "file_name": path.name,
                "artifact_format": path.suffix.lower().lstrip(".") or "file",
                "analysis_layer": layer,
                "primary_consumer": consumer,
                "row_count": _artifact_row_count(outputs, artifact_name, path),
                "file_exists": path.exists(),
                "file_size_bytes": int(path.stat().st_size) if path.exists() else 0,
                "target_table": meta.get("target_table", ""),
                "primary_key": "|".join(str(item) for item in primary_key),
                "purpose": meta.get("purpose", ""),
                "local_path": str(path),
                "package_index_version": "analysis_package_index_v0",
            }
        )
    return pd.DataFrame(rows, columns=_analysis_package_index_columns())


def _analysis_package_index_columns() -> list[str]:
    return [
        "package_order",
        "artifact_name",
        "file_name",
        "artifact_format",
        "analysis_layer",
        "primary_consumer",
        "row_count",
        "file_exists",
        "file_size_bytes",
        "target_table",
        "primary_key",
        "purpose",
        "local_path",
        "package_index_version",
    ]


def _artifact_row_count(outputs: EngineOutputs, artifact_name: str, path: Path) -> int:
    value = getattr(outputs, artifact_name, None)
    if isinstance(value, pd.DataFrame):
        return int(len(value))
    if isinstance(value, list):
        return int(len(value))
    if isinstance(value, dict):
        return 1 if value else 0
    if path.suffix.lower() == ".csv" and path.exists():
        try:
            return max(sum(1 for _ in path.open("r", encoding="utf-8")) - 1, 0)
        except Exception:
            return 0
    if path.suffix.lower() == ".json" and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        if isinstance(data, list):
            return len(data)
        return 1 if data else 0
    if path.exists():
        return 1
    return 0


def _target_table_for_artifact(artifact_name: str) -> str:
    contract = _load_output_contract()
    artifacts = contract.get("artifacts") or {}
    key = _trace_text(artifact_name).removesuffix(".csv").removesuffix(".json")
    meta = artifacts.get(key, {})
    return _trace_text(meta.get("target_table"))


def _delivery_mode_for_file(file_name: str) -> str:
    suffix = Path(_trace_text(file_name)).suffix.lower()
    if suffix == ".csv":
        return "csv_export"
    if suffix == ".xlsx":
        return "workbook_download"
    if suffix == ".html":
        return "html_view"
    if suffix == ".sql":
        return "snowflake_load_script"
    if suffix == ".json":
        return "json_artifact"
    return "artifact_download"


def _load_output_contract() -> dict[str, Any]:
    path = _default_output_contract_path()
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _default_output_contract_path() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data_contracts" / "intelligence_outputs.v1.yml"
        if candidate.exists():
            return candidate
    return here.parents[4] / "data_contracts" / "intelligence_outputs.v1.yml"


def build_engine_run_ledger(
    *,
    file_ledger: pd.DataFrame,
    intake_work_order: pd.DataFrame,
    file_assembly_plan: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    source_layout_profile: pd.DataFrame,
    layout_contract_draft_queue: pd.DataFrame,
    data_quality: dict[str, Any],
    account_month_features: pd.DataFrame,
    account_intelligence_profile: pd.DataFrame,
    model_rulebook: pd.DataFrame,
    account_scoring_trace: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    opportunities: pd.DataFrame,
    opportunity_portfolio: pd.DataFrame,
    action_plan: pd.DataFrame,
    campaign_targets: pd.DataFrame,
    intelligence_delta_report: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    analysis_domain_map: pd.DataFrame,
    analysis_input_dependency_map: pd.DataFrame,
    analysis_layout_coverage_matrix: pd.DataFrame,
    analysis_data_team_backlog: pd.DataFrame,
    analysis_metric_validation_queue: pd.DataFrame,
    analysis_visual_output_map: pd.DataFrame,
    analysis_chart_spec_catalog: pd.DataFrame,
    analysis_chart_data_snapshot: pd.DataFrame,
    intelligence_metric_catalog: pd.DataFrame,
    analysis_section_evidence_review: pd.DataFrame,
    analysis_requirement_matrix: pd.DataFrame,
    analysis_consulting_playbook: pd.DataFrame,
    analysis_insight_brief: pd.DataFrame,
    client_meeting_deck_blueprint: pd.DataFrame,
    analysis_field_usage_catalog: pd.DataFrame,
    consulting_insight_register: pd.DataFrame,
    stakeholder_export_manifest: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Build a tabular operator ledger for the monthly engine run."""
    cfg = config or EngineConfig()
    intake_summary = summarize_intake_work_order(intake_work_order)
    assembly_summary = summarize_file_assembly_plan(file_assembly_plan)
    layout_summary = summarize_layout_gap_report(layout_gap_report)
    quality_score = float(data_quality.get("quality_score", 0) or 0)
    warning_count = len(data_quality.get("warnings") or [])
    analysis_counts = (
        analysis_execution_map["evidence_status"].value_counts().to_dict()
        if analysis_execution_map is not None and not analysis_execution_map.empty and "evidence_status" in analysis_execution_map
        else {}
    )
    analysis_status = _run_ledger_analysis_status(analysis_counts)
    rows = [
        _engine_run_ledger_row(
            cfg,
            rank=1,
            run_stage="intake",
            stage_name="File discovery and work order",
            owner_role="Data team",
            status=str(intake_summary.get("readiness_status", "unknown")),
            row_count=len(intake_work_order),
            metric_name="files_profiled",
            metric_value=intake_summary.get("file_count", 0),
            input_artifacts="monthly_client_file_drop",
            output_artifacts="file_ledger.csv|intake_profile.json|intake_work_order.csv",
            snowflake_targets="out.ti_file_ledger|out.ti_intake_profile|out.ti_intake_work_order",
            evidence_summary=(
                f"{intake_summary.get('file_count', 0)} file(s) profiled; "
                f"{intake_summary.get('usable_files', 0)} usable; "
                f"{intake_summary.get('blocking_files', 0)} blocking."
            ),
            operator_action="Review files marked for mapping, replacement, or layout-contract creation.",
            blocking_issue="" if intake_summary.get("readiness_status") == "ready" else "intake_review_required",
            source_artifacts="file_ledger.csv|intake_work_order.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=2,
            run_stage="assembly",
            stage_name="Account and transaction file selection",
            owner_role="Analyst",
            status=str(assembly_summary.get("assembly_status", "unknown")),
            row_count=len(file_assembly_plan),
            metric_name="selected_inputs",
            metric_value=(
                f"accounts={assembly_summary.get('selected_account_files', 0)};"
                f"transactions={assembly_summary.get('selected_transaction_files', 0)}"
            ),
            input_artifacts="intake_work_order.csv",
            output_artifacts="file_assembly_plan.csv",
            snowflake_targets="out.ti_file_assembly_plan",
            evidence_summary=(
                f"{assembly_summary.get('selected_account_files', 0)} account file(s), "
                f"{assembly_summary.get('selected_transaction_files', 0)} transaction file(s), "
                f"{assembly_summary.get('held_files', 0)} held file(s)."
            ),
            operator_action="Confirm selected account and transaction files before interpreting scored outputs.",
            blocking_issue="" if assembly_summary.get("assembly_status") == "ready" else "file_selection_review_required",
            source_artifacts="file_assembly_plan.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=3,
            run_stage="layout_mapping",
            stage_name="Layout and contract coverage",
            owner_role="Data team",
            status=str(layout_summary.get("layout_status", "unknown")),
            row_count=len(layout_gap_report),
            metric_name="missing_required_fields",
            metric_value=layout_summary.get("layout_missing_required_fields", 0),
            input_artifacts="intake_profile.json",
            output_artifacts="layout_gap_report.csv|source_layout_profile.csv|layout_contract_draft_queue.csv",
            snowflake_targets=(
                "out.ti_layout_gap_report|out.ti_source_layout_profile|"
                "out.ti_layout_contract_draft_queue"
            ),
            evidence_summary=(
                f"{layout_summary.get('layout_ready_fields', 0)} matched field(s); "
                f"{layout_summary.get('layout_missing_required_fields', 0)} missing required field(s); "
                f"{layout_summary.get('layout_contract_needed_files', 0)} contract-needed file(s); "
                f"{len(source_layout_profile)} source layout profile row(s); "
                f"{len(layout_contract_draft_queue)} contract draft action(s)."
            ),
            operator_action="Map missing required fields or add layout contracts before re-running.",
            blocking_issue="" if layout_summary.get("layout_status") == "ready" else "layout_mapping_required",
            source_artifacts="layout_gap_report.csv|source_layout_profile.csv|layout_contract_draft_queue.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=4,
            run_stage="quality_gate",
            stage_name="Data quality and trust gate",
            owner_role="Analyst",
            status="ready" if quality_score >= 70 and warning_count == 0 else "review",
            row_count=1 if data_quality else 0,
            metric_name="quality_score",
            metric_value=round(quality_score, 1),
            input_artifacts="accounts|transactions|file_ledger.csv",
            output_artifacts="data_quality.json",
            snowflake_targets="out.ti_data_quality",
            evidence_summary=(
                f"Quality score {quality_score:.1f}; "
                f"confidence={data_quality.get('confidence', 'unknown')}; "
                f"{warning_count} warning(s)."
            ),
            operator_action="Resolve warnings before presenting findings if score is below the review threshold.",
            blocking_issue="" if quality_score >= 70 else "quality_score_below_review_threshold",
            source_artifacts="data_quality.json",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=5,
            run_stage="feature_build",
            stage_name="Account-month feature mart",
            owner_role="Data science",
            status="ready" if len(account_month_features) else "missing",
            row_count=len(account_month_features),
            metric_name="feature_rows",
            metric_value=len(account_month_features),
            input_artifacts="accounts|transactions",
            output_artifacts="account_month_features.csv",
            snowflake_targets="mart.ti_account_month_features",
            evidence_summary=f"{len(account_month_features)} account-month feature row(s) generated.",
            operator_action="Use feature rows as the base table for scoring, trace, dashboards, and Snowflake marts.",
            blocking_issue="" if len(account_month_features) else "no_features_generated",
            source_artifacts="account_month_features.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=6,
            run_stage="scoring",
            stage_name="PFI, relationship, and opportunity scoring",
            owner_role="Analyst",
            status="ready" if len(account_scoring_trace) and len(opportunities) else "review",
            row_count=len(account_scoring_trace),
            metric_name="opportunity_rows",
            metric_value=len(opportunities),
            input_artifacts="account_month_features.csv",
            output_artifacts="pfi_verdicts.csv|account_intelligence_profile.csv|account_scoring_trace.csv|opportunities.csv|opportunity_portfolio.csv",
            snowflake_targets="mart.ti_pfi_verdicts|mart.ti_account_intelligence_profile|out.ti_account_scoring_trace|mart.ti_opportunities|mart.ti_opportunity_portfolio",
            evidence_summary=(
                f"{len(pfi_verdicts)} PFI row(s); {len(account_intelligence_profile)} profile row(s); "
                f"{len(opportunities)} opportunity row(s); {len(opportunity_portfolio)} portfolio row(s)."
            ),
            operator_action="Sample scoring trace and rulebook before approving client recommendations.",
            blocking_issue="" if len(account_scoring_trace) else "missing_scoring_trace",
            source_artifacts="model_rulebook.csv|account_scoring_trace.csv|opportunities.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=7,
            run_stage="monthly_delta",
            stage_name="Month-over-month intelligence movement",
            owner_role="CSM + Analyst",
            status="baseline" if _delta_report_is_baseline(intelligence_delta_report) else "ready",
            row_count=len(intelligence_delta_report),
            metric_name="delta_rows",
            metric_value=len(intelligence_delta_report),
            input_artifacts="prior_intelligence_package|current_intelligence_package",
            output_artifacts="intelligence_delta_report.csv",
            snowflake_targets="out.ti_intelligence_delta_report",
            evidence_summary=f"{len(intelligence_delta_report)} month-over-month delta row(s) generated.",
            operator_action="Review movement before deciding whether to continue, suppress, or escalate plays.",
            blocking_issue="" if len(intelligence_delta_report) else "delta_report_missing",
            source_artifacts="intelligence_delta_report.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=8,
            run_stage="analysis_governance",
            stage_name="Analysis section and rule evidence",
            owner_role="Analyst",
            status=analysis_status,
            row_count=len(analysis_execution_map),
            metric_name="analysis_sections_mapped",
            metric_value=len(analysis_execution_map),
            input_artifacts="analysis_section_catalog.csv|analysis_script_catalog.csv|analysis_field_usage_catalog.csv|model_rulebook.csv",
            output_artifacts="analysis_execution_map.csv|analysis_domain_map.csv|analysis_input_dependency_map.csv|analysis_layout_coverage_matrix.csv|analysis_data_team_backlog.csv|analysis_metric_validation_queue.csv|analysis_visual_output_map.csv|analysis_chart_spec_catalog.csv|analysis_chart_data_snapshot.csv|intelligence_metric_catalog.csv|analysis_section_evidence_review.csv|analysis_requirement_matrix.csv|analysis_consulting_playbook.csv|analysis_insight_brief.csv|analysis_field_usage_catalog.csv|analysis_provenance_map.csv|model_rulebook.csv",
            snowflake_targets="out.ti_analysis_execution_map|out.ti_analysis_domain_map|out.ti_analysis_input_dependency_map|out.ti_analysis_layout_coverage_matrix|out.ti_analysis_data_team_backlog|out.ti_analysis_metric_validation_queue|out.ti_analysis_visual_output_map|out.ti_analysis_chart_spec_catalog|out.ti_analysis_chart_data_snapshot|out.ti_intelligence_metric_catalog|out.ti_analysis_section_evidence_review|out.ti_analysis_requirement_matrix|out.ti_analysis_consulting_playbook|out.ti_analysis_insight_brief|out.ti_analysis_field_usage_catalog|out.ti_analysis_provenance_map|out.ti_model_rulebook",
            evidence_summary=(
                f"{analysis_counts.get('ready', 0)} ready section(s); "
                f"{analysis_counts.get('partial', 0)} partial section(s); "
                f"{analysis_counts.get('missing', 0)} missing section(s); "
                f"{len(analysis_domain_map)} domain map row(s); "
                f"{len(analysis_input_dependency_map)} input dependency row(s); "
                f"{len(analysis_layout_coverage_matrix)} field/layout coverage row(s); "
                f"{len(analysis_data_team_backlog)} data-team backlog row(s); "
                f"{len(analysis_metric_validation_queue)} metric validation row(s); "
                f"{len(analysis_visual_output_map)} visual output row(s); "
                f"{len(analysis_chart_spec_catalog)} chart spec row(s); "
                f"{len(analysis_chart_data_snapshot)} chart data snapshot row(s); "
                f"{len(intelligence_metric_catalog)} semantic metric row(s); "
                f"{len(analysis_section_evidence_review)} section evidence review row(s); "
                f"{len(analysis_requirement_matrix)} requirement row(s); "
                f"{len(analysis_consulting_playbook)} consulting playbook row(s); "
                f"{len(analysis_insight_brief)} insight brief row(s); "
                f"{len(analysis_field_usage_catalog)} script field reference row(s)."
            ),
            operator_action="Use the execution, domain, input dependency, visual output, chart spec, metric catalog, insight brief, playbook, backlog, validation, layout coverage, and requirement maps to explain analysis support, story use, and layout gaps.",
            blocking_issue="" if analysis_status in {"ready", "partial"} else "analysis_evidence_review_required",
            source_artifacts="analysis_execution_map.csv|analysis_domain_map.csv|analysis_input_dependency_map.csv|analysis_layout_coverage_matrix.csv|analysis_data_team_backlog.csv|analysis_metric_validation_queue.csv|analysis_visual_output_map.csv|analysis_chart_spec_catalog.csv|analysis_chart_data_snapshot.csv|intelligence_metric_catalog.csv|analysis_section_evidence_review.csv|analysis_requirement_matrix.csv|analysis_consulting_playbook.csv|analysis_insight_brief.csv|analysis_field_usage_catalog.csv|analysis_provenance_map.csv|model_rulebook.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=9,
            run_stage="consulting_package",
            stage_name="Consulting insight and story layer",
            owner_role="CSM",
            status="ready" if len(consulting_insight_register) else "missing",
            row_count=len(consulting_insight_register),
            metric_name="consulting_insights",
            metric_value=len(consulting_insight_register),
            input_artifacts="insights.json|executive_scorecard.csv|consulting_story.json",
            output_artifacts="consulting_insight_register.csv|consulting_story.json|client_meeting_deck_blueprint.csv|executive_scorecard.csv|strategy_roadmap.csv",
            snowflake_targets="out.ti_consulting_insight_register|out.ti_consulting_story|out.ti_client_meeting_deck_blueprint|out.ti_executive_scorecard|out.ti_strategy_roadmap",
            evidence_summary=(
                f"{len(consulting_insight_register)} consulting insight register row(s); "
                f"{len(client_meeting_deck_blueprint)} client meeting blueprint row(s) generated."
            ),
            operator_action="Choose the client story, lead play, meeting sequence, and next decision from the insight register and deck blueprint.",
            blocking_issue="" if len(consulting_insight_register) else "no_consulting_register_generated",
            source_artifacts="consulting_insight_register.csv|consulting_story.json|client_meeting_deck_blueprint.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=10,
            run_stage="stakeholder_exports",
            stage_name="Role-specific exports",
            owner_role="CSM",
            status="ready" if len(stakeholder_export_manifest) else "missing",
            row_count=len(stakeholder_export_manifest),
            metric_name="export_manifest_rows",
            metric_value=len(stakeholder_export_manifest),
            input_artifacts="account_intelligence_profile.csv|campaign_targets.csv|action_plan.csv",
            output_artifacts="csm_review_queue.csv|analyst_validation_queue.csv|marketing_activation_export.csv|banker_call_list.csv|data_team_load_plan.csv|stakeholder_export_manifest.csv",
            snowflake_targets="out.ti_csm_review_queue|out.ti_analyst_validation_queue|out.ti_marketing_activation_export|out.ti_banker_call_list|out.ti_data_team_load_plan|out.ti_stakeholder_export_manifest",
            evidence_summary=f"{len(stakeholder_export_manifest)} stakeholder export row(s) documented.",
            operator_action="Route each export to its owning role and preserve action_id/measurement_id through activation.",
            blocking_issue="" if len(stakeholder_export_manifest) else "stakeholder_exports_missing",
            source_artifacts="stakeholder_export_manifest.csv|role_handoffs.csv",
        ),
        _engine_run_ledger_row(
            cfg,
            rank=11,
            run_stage="warehouse_handoff",
            stage_name="Snowflake package readiness",
            owner_role="Data / Snowflake",
            status="ready_for_package_write",
            row_count=0,
            metric_name="warehouse_package_files",
            metric_value=3,
            input_artifacts="generated_engine_outputs",
            output_artifacts="snowflake_manifest.json|snowflake_load.sql|README_SNOWFLAKE.html",
            snowflake_targets="out.ti_run_summary|out.ti_artifact",
            evidence_summary="Warehouse package is generated after CSV/JSON artifacts are written.",
            operator_action="Run foundation DDL, stage files, execute snowflake_load.sql, and validate row counts.",
            blocking_issue="",
            source_artifacts="snowflake_manifest.json|snowflake_load.sql|README_SNOWFLAKE.html",
        ),
    ]
    return pd.DataFrame(rows, columns=_engine_run_ledger_columns())


def build_engine_readiness_assessment(
    *,
    file_ledger: pd.DataFrame,
    intake_work_order: pd.DataFrame,
    file_assembly_plan: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    layout_contract_draft_queue: pd.DataFrame,
    data_quality: dict[str, Any],
    account_month_features: pd.DataFrame,
    account_intelligence_profile: pd.DataFrame,
    opportunity_portfolio: pd.DataFrame,
    campaign_targets: pd.DataFrame,
    outcome_summary: pd.DataFrame,
    stakeholder_export_manifest: pd.DataFrame,
    analysis_section_evidence_review: pd.DataFrame,
    analysis_consulting_playbook: pd.DataFrame,
    analysis_data_team_backlog: pd.DataFrame,
    analysis_metric_validation_queue: pd.DataFrame,
    intelligence_metric_catalog: pd.DataFrame,
    analysis_insight_brief: pd.DataFrame,
    client_meeting_deck_blueprint: pd.DataFrame,
    engine_run_ledger: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create the run-level go/no-go table for operators and productization."""
    cfg = config or EngineConfig()
    intake_summary = summarize_intake_work_order(intake_work_order)
    assembly_summary = summarize_file_assembly_plan(file_assembly_plan)
    layout_summary = summarize_layout_gap_report(layout_gap_report)
    quality_score = float(data_quality.get("quality_score") or 0)
    blocker_sections = _sum_frame_column(analysis_section_evidence_review, "blocker_field_count")
    review_sections = _sum_frame_column(analysis_section_evidence_review, "review_field_count")
    data_backlog_count = len(analysis_data_team_backlog) if analysis_data_team_backlog is not None else 0
    metric_validation_count = len(analysis_metric_validation_queue) if analysis_metric_validation_queue is not None else 0
    layout_blocker_count = int(layout_summary.get("layout_missing_required_fields", 0) or 0) + int(
        layout_summary.get("layout_contract_needed_files", 0) or 0
    )
    rows = [
        _engine_readiness_row(
            cfg,
            rank=1,
            readiness_area="monthly_file_drop",
            engine_layer="Intake",
            owner_role="Analyst / Data team",
            readiness_status=_intake_readiness_status(file_ledger, intake_summary),
            client_use_status="production_ready" if intake_summary.get("readiness_status") == "ready" else "internal_review",
            severity=0 if intake_summary.get("readiness_status") == "ready" else 2,
            evidence_metric="files_profiled",
            evidence_value=len(file_ledger),
            blocker_count=int(intake_summary.get("blocking_files", 0) or 0),
            validation_count=int(intake_summary.get("review_files", 0) or 0),
            evidence_summary=(
                f"{len(file_ledger)} file(s) inventoried; "
                f"{intake_summary.get('usable_files', 0)} usable; "
                f"{intake_summary.get('blocking_files', 0)} blocking."
            ),
            blocking_issue="" if intake_summary.get("readiness_status") == "ready" else "intake_review_required",
            next_action="Load selected files or resolve files marked for mapping, replacement, or layout-contract creation.",
            proof_artifacts="file_ledger.csv|intake_profile.json|intake_work_order.csv|file_assembly_plan.csv",
            snowflake_targets="out.ti_file_ledger|out.ti_intake_profile|out.ti_intake_work_order|out.ti_file_assembly_plan",
        ),
        _engine_readiness_row(
            cfg,
            rank=2,
            readiness_area="layout_contracts",
            engine_layer="Data strategy",
            owner_role="Data team",
            readiness_status="ready" if layout_blocker_count == 0 else "layout_mapping_required",
            client_use_status="production_ready" if layout_blocker_count == 0 else "blocks_full_snowflake_productization",
            severity=0 if layout_blocker_count == 0 else 3,
            evidence_metric="layout_blockers",
            evidence_value=layout_blocker_count,
            blocker_count=layout_blocker_count,
            validation_count=int(layout_summary.get("layout_contract_needed_files", 0) or 0),
            evidence_summary=(
                f"{layout_summary.get('layout_ready_fields', 0)} matched field(s); "
                f"{layout_summary.get('layout_missing_required_fields', 0)} missing required field(s); "
                f"{layout_summary.get('layout_contract_needed_files', 0)} contract-needed file(s); "
                f"{len(layout_contract_draft_queue)} layout contract draft action(s)."
            ),
            blocking_issue="" if layout_blocker_count == 0 else "layout_mapping_required",
            next_action="Promote matched layouts; map missing required fields and create contracts for client-specific files.",
            proof_artifacts="layout_gap_report.csv|source_layout_profile.csv|layout_contract_draft_queue.csv|data_team_load_plan.csv",
            snowflake_targets=(
                "out.ti_layout_gap_report|out.ti_source_layout_profile|"
                "out.ti_layout_contract_draft_queue|out.ti_data_team_load_plan"
            ),
        ),
        _engine_readiness_row(
            cfg,
            rank=3,
            readiness_area="core_feature_mart",
            engine_layer="Feature mart",
            owner_role="Data science",
            readiness_status=_core_feature_readiness_status(account_month_features, quality_score),
            client_use_status="client_ready" if quality_score >= 80 and len(account_month_features) else "analyst_review",
            severity=0 if quality_score >= 80 and len(account_month_features) else 2,
            evidence_metric="quality_score",
            evidence_value=quality_score,
            blocker_count=0 if len(account_month_features) else 1,
            validation_count=len(data_quality.get("warnings", []) or []),
            evidence_summary=(
                f"{len(account_month_features)} feature row(s); quality score {quality_score:.0f}; "
                f"{len(data_quality.get('warnings', []) or [])} warning(s)."
            ),
            blocking_issue="" if len(account_month_features) else "feature_mart_empty",
            next_action="Use account-month features for scoring when quality is acceptable; review warnings before external claims.",
            proof_artifacts="account_month_features.csv|data_quality.json|engine_run_ledger.csv",
            snowflake_targets="mart.ti_account_month_features|out.ti_data_quality|out.ti_engine_run_ledger",
        ),
        _engine_readiness_row(
            cfg,
            rank=4,
            readiness_area="intelligence_outputs",
            engine_layer="Account Intelligence",
            owner_role="CSM / Consultant",
            readiness_status="ready" if len(account_intelligence_profile) and len(opportunity_portfolio) else "missing_intelligence_outputs",
            client_use_status="client_ready" if len(account_intelligence_profile) and len(opportunity_portfolio) else "blocked",
            severity=0 if len(account_intelligence_profile) and len(opportunity_portfolio) else 3,
            evidence_metric="account_profiles",
            evidence_value=len(account_intelligence_profile),
            blocker_count=0 if len(account_intelligence_profile) and len(opportunity_portfolio) else 1,
            validation_count=0,
            evidence_summary=(
                f"{len(account_intelligence_profile)} account profile row(s); "
                f"{len(opportunity_portfolio)} portfolio play row(s); "
                f"{len(client_meeting_deck_blueprint)} client meeting blueprint row(s)."
            ),
            blocking_issue="" if len(account_intelligence_profile) and len(opportunity_portfolio) else "opportunity_outputs_missing",
            next_action="Use profile, portfolio, action plan, story artifacts, and meeting blueprint to run the client strategy conversation.",
            proof_artifacts="account_intelligence_profile.csv|opportunity_portfolio.csv|action_plan.csv|consulting_story.json|client_meeting_deck_blueprint.csv",
            snowflake_targets="mart.ti_account_intelligence_profile|mart.ti_opportunity_portfolio|out.ti_action_plan|out.ti_consulting_story|out.ti_client_meeting_deck_blueprint",
        ),
        _engine_readiness_row(
            cfg,
            rank=5,
            readiness_area="analysis_evidence_map",
            engine_layer="Analysis IP",
            owner_role="Analyst",
            readiness_status=_analysis_evidence_readiness_status(blocker_sections, review_sections),
            client_use_status="qualified_external_use" if blocker_sections else "client_ready",
            severity=2 if blocker_sections else 1 if review_sections else 0,
            evidence_metric="section_field_blockers",
            evidence_value=blocker_sections,
            blocker_count=blocker_sections,
            validation_count=review_sections,
            evidence_summary=(
                f"{len(analysis_section_evidence_review)} section evidence row(s); "
                f"{len(analysis_consulting_playbook)} consulting playbook row(s); "
                f"{len(analysis_insight_brief)} insight brief row(s); "
                f"{len(client_meeting_deck_blueprint)} meeting blueprint row(s); "
                f"{len(intelligence_metric_catalog)} semantic metric row(s); "
                f"{blocker_sections} blocker field reference(s); {review_sections} review field reference(s)."
            ),
            blocking_issue="" if blocker_sections == 0 else "analysis_layout_blockers_open",
            next_action="Use section evidence for the story, but qualify or hold sections with open layout blockers.",
            proof_artifacts="analysis_section_evidence_review.csv|analysis_consulting_playbook.csv|analysis_insight_brief.csv|client_meeting_deck_blueprint.csv|intelligence_metric_catalog.csv|analysis_layout_coverage_matrix.csv|analysis_requirement_matrix.csv",
            snowflake_targets="out.ti_analysis_section_evidence_review|out.ti_analysis_consulting_playbook|out.ti_analysis_insight_brief|out.ti_client_meeting_deck_blueprint|out.ti_intelligence_metric_catalog|out.ti_analysis_layout_coverage_matrix|out.ti_analysis_requirement_matrix",
        ),
        _engine_readiness_row(
            cfg,
            rank=6,
            readiness_area="data_team_backlog",
            engine_layer="Data strategy",
            owner_role="Data team",
            readiness_status="ready" if data_backlog_count == 0 else "open_data_mapping_backlog",
            client_use_status="production_ready" if data_backlog_count == 0 else "blocks_full_snowflake_productization",
            severity=0 if data_backlog_count == 0 else 3,
            evidence_metric="backlog_items",
            evidence_value=data_backlog_count,
            blocker_count=data_backlog_count,
            validation_count=0,
            evidence_summary=f"{data_backlog_count} grouped data-team backlog item(s).",
            blocking_issue="" if data_backlog_count == 0 else "data_team_backlog_open",
            next_action="Resolve P0/P1 layout, contract, and Snowflake modeling work items before claiming full repeatability.",
            proof_artifacts="analysis_data_team_backlog.csv|layout_gap_report.csv|source_layout_profile.csv",
            snowflake_targets="out.ti_analysis_data_team_backlog|out.ti_layout_gap_report|out.ti_source_layout_profile",
        ),
        _engine_readiness_row(
            cfg,
            rank=7,
            readiness_area="metric_validation",
            engine_layer="Model Governance",
            owner_role="Analyst",
            readiness_status="ready" if metric_validation_count == 0 else "metric_validation_required",
            client_use_status="client_ready" if metric_validation_count == 0 else "qualified_external_use",
            severity=0 if metric_validation_count == 0 else 2,
            evidence_metric="validation_items",
            evidence_value=metric_validation_count,
            blocker_count=0,
            validation_count=metric_validation_count,
            evidence_summary=f"{metric_validation_count} grouped metric validation item(s).",
            blocking_issue="" if metric_validation_count == 0 else "metric_validation_queue_open",
            next_action="Validate derived outputs, aliases, direct-load fields, and rule-based metrics before external claims.",
            proof_artifacts="analysis_metric_validation_queue.csv|intelligence_metric_catalog.csv|model_rulebook.csv|account_scoring_trace.csv",
            snowflake_targets="out.ti_analysis_metric_validation_queue|out.ti_intelligence_metric_catalog|out.ti_model_rulebook|out.ti_account_scoring_trace",
        ),
        _engine_readiness_row(
            cfg,
            rank=8,
            readiness_area="activation_exports",
            engine_layer="Execution",
            owner_role="CSM / Marketing / Banker",
            readiness_status="ready" if len(stakeholder_export_manifest) and len(campaign_targets) else "activation_exports_missing",
            client_use_status="client_ready" if len(stakeholder_export_manifest) and len(campaign_targets) else "blocked",
            severity=0 if len(stakeholder_export_manifest) and len(campaign_targets) else 3,
            evidence_metric="campaign_targets",
            evidence_value=len(campaign_targets),
            blocker_count=0 if len(stakeholder_export_manifest) and len(campaign_targets) else 1,
            validation_count=0,
            evidence_summary=(
                f"{len(campaign_targets)} target row(s); "
                f"{len(stakeholder_export_manifest)} stakeholder export manifest row(s)."
            ),
            blocking_issue="" if len(stakeholder_export_manifest) and len(campaign_targets) else "activation_exports_missing",
            next_action="Route target, CSM, marketing, and banker files to owners with action_id and measurement_id preserved.",
            proof_artifacts="campaign_targets.csv|stakeholder_export_manifest.csv|csm_review_queue.csv|marketing_activation_export.csv|banker_call_list.csv",
            snowflake_targets="out.ti_campaign_targets|out.ti_stakeholder_export_manifest|out.ti_csm_review_queue|out.ti_marketing_activation_export|out.ti_banker_call_list",
        ),
        _engine_readiness_row(
            cfg,
            rank=9,
            readiness_area="outcome_measurement",
            engine_layer="Measurement",
            owner_role="Analyst / CSM",
            readiness_status="ready" if len(outcome_summary) else "no_prior_measurement_yet",
            client_use_status="client_ready" if len(outcome_summary) else "planning_ready",
            severity=0,
            evidence_metric="outcome_summary_rows",
            evidence_value=len(outcome_summary),
            blocker_count=0,
            validation_count=0 if len(outcome_summary) else 1,
            evidence_summary=(
                f"{len(outcome_summary)} measured outcome summary row(s); "
                f"{int(assembly_summary.get('selected_account_files', 0) or 0) + int(assembly_summary.get('selected_transaction_files', 0) or 0) + int(assembly_summary.get('supporting_files', 0) or 0)} loadable file(s) in current assembly."
            ),
            blocking_issue="",
            next_action="For first-run clients, establish baselines and holdouts; for recurring clients, compare against prior target lists.",
            proof_artifacts="measurement_plan.csv|measurement_baseline.csv|outcome_results.csv|outcome_summary.csv",
            snowflake_targets="out.ti_measurement_plan|out.ti_measurement_baseline|out.ti_outcome_results|out.ti_outcome_summary",
        ),
        _engine_readiness_row(
            cfg,
            rank=10,
            readiness_area="snowflake_handoff",
            engine_layer="Warehouse",
            owner_role="Data / Snowflake",
            readiness_status=_snowflake_handoff_readiness_status(layout_blocker_count, data_backlog_count, metric_validation_count),
            client_use_status="production_ready" if layout_blocker_count == 0 and data_backlog_count == 0 else "package_ready_with_known_gaps",
            severity=0 if layout_blocker_count == 0 and data_backlog_count == 0 else 2,
            evidence_metric="ledger_stages",
            evidence_value=len(engine_run_ledger),
            blocker_count=layout_blocker_count + data_backlog_count,
            validation_count=metric_validation_count,
            evidence_summary=(
                f"{len(engine_run_ledger)} run ledger stage(s); "
                f"{layout_blocker_count + data_backlog_count} Snowflake/data blocker(s); "
                f"{metric_validation_count} validation item(s)."
            ),
            blocking_issue="" if layout_blocker_count == 0 and data_backlog_count == 0 else "warehouse_package_has_known_gaps",
            next_action="Run DDL, load package files, validate row counts, then resolve backlog and validation queues by priority.",
            proof_artifacts="snowflake_manifest.json|snowflake_load.sql|README_SNOWFLAKE.html|analysis_package_index.csv",
            snowflake_targets="out.ti_artifact|out.ti_run_summary|out.ti_engine_readiness_assessment",
        ),
    ]
    return pd.DataFrame(rows, columns=_engine_readiness_assessment_columns())


def build_analysis_execution_map(
    analysis_section_catalog: pd.DataFrame,
    analysis_script_catalog: pd.DataFrame,
    analysis_provenance_map: pd.DataFrame,
    model_rulebook: pd.DataFrame,
    generated_artifacts: dict[str, Any],
    data_quality: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Map each existing analysis section to run evidence and next analyst action."""
    cfg = config or EngineConfig()
    if analysis_section_catalog is None or analysis_section_catalog.empty:
        return _empty_analysis_execution_map()

    contract_artifacts = (_load_output_contract().get("artifacts") or {})
    scripts_by_section = _scripts_by_section(analysis_script_catalog)
    provenance_by_section = _provenance_by_section(analysis_provenance_map)
    rules_by_opportunity = _rules_by_opportunity(model_rulebook)
    quality = data_quality or {}
    rows: list[dict[str, Any]] = []

    for index, section in enumerate(analysis_section_catalog.to_dict("records"), start=1):
        section_id = _trace_text(section.get("source_section_id"))
        product = _trace_text(section.get("product"))
        primary_outputs = _split_tokens(section.get("primary_engine_outputs"))
        available_outputs: list[str] = []
        missing_outputs: list[str] = []
        output_files: list[str] = []
        output_tables: list[str] = []
        output_row_counts: list[str] = []
        total_rows = 0

        for artifact_name in primary_outputs:
            row_count = _generated_artifact_row_count(generated_artifacts.get(artifact_name))
            meta = contract_artifacts.get(artifact_name, {})
            file_name = meta.get("file") or _default_artifact_file_name(artifact_name)
            target_table = meta.get("target_table", "")
            output_row_counts.append(f"{artifact_name}:{row_count}")
            if row_count > 0:
                available_outputs.append(artifact_name)
                output_files.append(str(file_name))
                if target_table:
                    output_tables.append(str(target_table))
                total_rows += row_count
            else:
                missing_outputs.append(artifact_name)

        input_readiness = _section_input_readiness(section_id, product, quality)
        evidence_status = _analysis_evidence_status(
            primary_outputs=primary_outputs,
            available_outputs=available_outputs,
            missing_outputs=missing_outputs,
            input_readiness=input_readiness,
        )
        opportunity_types = _split_tokens(section.get("supports_opportunity_types"))
        model_rule_ids = [
            rule_id
            for opportunity_type in opportunity_types
            for rule_id in rules_by_opportunity.get(opportunity_type, [])
        ]
        script_rows = scripts_by_section.get(section_id, [])
        script_names = [_trace_text(row.get("script_name")) for row in script_rows if _trace_text(row.get("script_name"))]
        runnable_count = sum(1 for row in script_rows if _trace_bool(row.get("runnable_flag")))
        source_artifacts = ["analysis_section_catalog.csv", "analysis_script_catalog.csv"]
        if output_files:
            source_artifacts.extend(output_files)

        rows.append(
            {
                "execution_rank": index,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "source_section_id": section_id,
                "product": product,
                "display_name": _trace_text(section.get("display_name")),
                "analysis_family": _trace_text(section.get("analysis_family")) or "unmapped",
                "intelligence_layers": _trace_text(section.get("intelligence_layers")),
                "source_path": _trace_text(section.get("source_path")),
                "required_input_families": _required_input_families(section_id, product),
                "input_readiness": input_readiness,
                "configured_script_count": _safe_int_value(section.get("configured_module_count")),
                "discovered_script_count": _safe_int_value(section.get("script_count"), default=len(script_rows)),
                "runnable_script_count": _safe_int_value(section.get("runnable_script_count"), default=runnable_count),
                "representative_scripts": "|".join(script_names[:8]),
                "primary_engine_outputs": "|".join(primary_outputs),
                "available_engine_outputs": "|".join(available_outputs),
                "missing_engine_outputs": "|".join(missing_outputs),
                "generated_output_files": "|".join(dict.fromkeys(output_files)),
                "generated_target_tables": "|".join(dict.fromkeys(output_tables)),
                "generated_row_count": total_rows,
                "output_row_counts": "|".join(output_row_counts),
                "evidence_status": evidence_status,
                "supported_opportunity_types": "|".join(opportunity_types),
                "model_rule_ids": "|".join(dict.fromkeys(model_rule_ids)),
                "provenance_contributions": "|".join(provenance_by_section.get(section_id, [])),
                "consulting_question": _consulting_question_for_section(section_id, section.get("analysis_family")),
                "consulting_use": _trace_text(section.get("consulting_use")),
                "analyst_next_step": _analysis_next_step(
                    evidence_status=evidence_status,
                    section_name=_trace_text(section.get("display_name")) or section_id,
                    available_outputs=available_outputs,
                    missing_outputs=missing_outputs,
                    input_readiness=input_readiness,
                ),
                "source_artifacts": "|".join(dict.fromkeys(source_artifacts)),
                "model_version": "analysis_execution_map_v0",
            }
        )

    return pd.DataFrame(rows, columns=_analysis_execution_map_columns()).sort_values(
        ["evidence_status", "product", "source_section_id"],
        ascending=[True, True, True],
    ).reset_index(drop=True)


def build_analysis_domain_map(
    analysis_section_catalog: pd.DataFrame,
    analysis_script_catalog: pd.DataFrame,
    analysis_provenance_map: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    data_quality: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Roll section-level analysis inventory into sellable intelligence domains."""
    cfg = config or EngineConfig()
    if analysis_section_catalog is None or analysis_section_catalog.empty:
        return _empty_analysis_domain_map()

    sections_by_id = _records_by_key(analysis_section_catalog, "source_section_id")
    execution_by_id = _records_by_key(analysis_execution_map, "source_section_id")
    scripts_by_section = _scripts_by_section(analysis_script_catalog)
    provenance_by_section = _provenance_by_section(analysis_provenance_map)
    rows: list[dict[str, Any]] = []

    for rank, definition in enumerate(ANALYSIS_DOMAIN_DEFINITIONS, start=1):
        section_ids = list(definition["sections"])
        section_rows = [sections_by_id.get(section_id, {}) for section_id in section_ids]
        execution_rows = [execution_by_id.get(section_id, {}) for section_id in section_ids]
        present_section_ids = [section_id for section_id in section_ids if section_id in sections_by_id]
        required_inputs = list(definition["required_input_families"])

        status_counts = _status_counts(execution_rows, expected_count=len(section_ids))
        primary_outputs = _unique_tokens(
            list(definition.get("intelligence_products") or [])
            + [
                token
                for row in section_rows
                for token in _split_tokens(row.get("primary_engine_outputs"))
            ]
        )
        generated_files = _unique_tokens(
            [
                token
                for row in execution_rows
                for token in _split_tokens(row.get("generated_output_files"))
            ]
        )
        generated_tables = _unique_tokens(
            [
                token
                for row in execution_rows
                for token in _split_tokens(row.get("generated_target_tables"))
            ]
        )
        opportunity_types = _unique_tokens(
            [
                token
                for row in section_rows
                for token in _split_tokens(row.get("supports_opportunity_types"))
            ]
        )
        model_rule_ids = _unique_tokens(
            [
                token
                for row in execution_rows
                for token in _split_tokens(row.get("model_rule_ids"))
            ]
        )
        analysis_families = _unique_tokens(
            [_trace_text(row.get("analysis_family")) for row in section_rows]
        )
        intelligence_layers = _unique_tokens(
            [
                token
                for row in section_rows
                for token in _split_tokens(row.get("intelligence_layers"))
            ]
        )
        script_count = sum(_safe_int_value(row.get("script_count")) for row in section_rows)
        runnable_count = sum(_safe_int_value(row.get("runnable_script_count")) for row in section_rows)
        discovered_runtime_scripts = sum(len(scripts_by_section.get(section_id, [])) for section_id in section_ids)
        generated_row_count = sum(_safe_int_value(row.get("generated_row_count")) for row in execution_rows)
        input_readiness = _domain_input_readiness(required_inputs, status_counts, data_quality or {})
        evidence_status = _domain_evidence_status(status_counts, generated_row_count)
        provenance = _unique_tokens(
            [
                token
                for section_id in section_ids
                for token in provenance_by_section.get(section_id, [])
            ]
        )

        rows.append(
            {
                "domain_rank": rank,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "domain_id": definition["domain_id"],
                "domain_name": definition["domain_name"],
                "business_question": definition["business_question"],
                "source_section_ids": "|".join(present_section_ids or section_ids),
                "section_count": len(present_section_ids),
                "script_count": script_count,
                "runnable_script_count": runnable_count,
                "discovered_runtime_script_count": discovered_runtime_scripts,
                "analysis_families": "|".join(analysis_families),
                "intelligence_layers": "|".join(intelligence_layers),
                "required_input_families": "|".join(required_inputs),
                "input_readiness": input_readiness,
                "evidence_status": evidence_status,
                "ready_sections": status_counts.get("ready", 0),
                "partial_sections": status_counts.get("partial", 0),
                "blocked_sections": status_counts.get("blocked_by_input", 0),
                "missing_sections": status_counts.get("missing", 0),
                "inventory_only_sections": status_counts.get("inventory_only", 0),
                "primary_engine_outputs": "|".join(primary_outputs),
                "generated_output_files": "|".join(generated_files),
                "generated_target_tables": "|".join(generated_tables),
                "generated_row_count": generated_row_count,
                "opportunity_types": "|".join(opportunity_types),
                "model_rule_ids": "|".join(model_rule_ids),
                "provenance_contributions": "|".join(provenance),
                "consulting_use": definition["consulting_use"],
                "what_can_be_built_now": _domain_build_now_text(evidence_status, primary_outputs, generated_files),
                "waits_for_client_layouts": _domain_layout_wait_text(required_inputs),
                "next_decision": _domain_next_decision(
                    definition["domain_name"],
                    input_readiness,
                    evidence_status,
                    required_inputs,
                ),
                "source_artifacts": "analysis_section_catalog.csv|analysis_script_catalog.csv|analysis_execution_map.csv|analysis_provenance_map.csv",
                "model_version": "analysis_domain_map_v0",
            }
        )

    return pd.DataFrame(rows, columns=_analysis_domain_map_columns())


def build_analysis_input_dependency_map(
    analysis_domain_map: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    file_assembly_plan: pd.DataFrame,
    data_quality: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Map canonical input families to the analysis domains that depend on them."""
    cfg = config or EngineConfig()
    domain_rows = analysis_domain_map.to_dict("records") if analysis_domain_map is not None and not analysis_domain_map.empty else []
    execution_rows = analysis_execution_map.to_dict("records") if analysis_execution_map is not None and not analysis_execution_map.empty else []
    quality = data_quality or {}
    rows: list[dict[str, Any]] = []

    for rank, (family, definition) in enumerate(INPUT_FAMILY_DEFINITIONS.items(), start=1):
        dependent_domains = [
            _trace_text(row.get("domain_id"))
            for row in domain_rows
            if family in _split_tokens(row.get("required_input_families"))
        ]
        dependent_domain_names = [
            _trace_text(row.get("domain_name"))
            for row in domain_rows
            if family in _split_tokens(row.get("required_input_families"))
        ]
        dependent_sections = _unique_tokens(
            [
                token
                for row in domain_rows
                if family in _split_tokens(row.get("required_input_families"))
                for token in _split_tokens(row.get("source_section_ids"))
            ]
        )
        section_runtime_rows = [
            row
            for row in execution_rows
            if _trace_text(row.get("source_section_id")) in set(dependent_sections)
        ]
        matched_file_count = _family_file_count(file_assembly_plan, family, selected_only=False)
        selected_file_count = _family_file_count(file_assembly_plan, family, selected_only=True)
        missing_required = _family_layout_count(layout_gap_report, family, "missing_required")
        contract_needed = _family_contract_needed_count(layout_gap_report, family)
        readiness = _input_family_readiness(
            family=family,
            matched_file_count=matched_file_count,
            selected_file_count=selected_file_count,
            missing_required_count=missing_required,
            contract_needed_count=contract_needed,
            data_quality=quality,
        )

        rows.append(
            {
                "dependency_rank": rank,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "input_family": family,
                "display_name": definition["display_name"],
                "canonical_role": definition["canonical_role"],
                "minimum_fields": definition["minimum_fields"],
                "optional_fields": definition["optional_fields"],
                "source_candidates": definition["source_candidates"],
                "dependent_domains": "|".join(_unique_tokens(dependent_domains)),
                "dependent_domain_names": "|".join(_unique_tokens(dependent_domain_names)),
                "dependent_sections": "|".join(dependent_sections),
                "dependent_section_count": len(dependent_sections),
                "dependent_script_count": sum(_safe_int_value(row.get("discovered_script_count")) for row in section_runtime_rows),
                "current_contract_status": definition["current_contract_status"],
                "current_run_readiness": readiness,
                "matched_file_count": matched_file_count,
                "selected_file_count": selected_file_count,
                "missing_required_field_count": missing_required,
                "contract_needed_file_count": contract_needed,
                "layout_mapping_status": _layout_mapping_status(readiness, missing_required, contract_needed),
                "snowflake_design_decision": definition["snowflake_design_decision"],
                "analyst_next_step": _input_dependency_next_step(family, readiness),
                "source_artifacts": "analysis_domain_map.csv|analysis_execution_map.csv|layout_gap_report.csv|file_assembly_plan.csv|data_quality.json",
                "model_version": "analysis_input_dependency_map_v0",
            }
        )

    return pd.DataFrame(rows, columns=_analysis_input_dependency_map_columns())


def build_monthly_file_requirements(
    analysis_input_dependency_map: pd.DataFrame,
    file_assembly_plan: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    layout_contract_draft_queue: pd.DataFrame,
    source_layout_profile: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create the monthly data-team checklist by expected input family."""
    cfg = config or EngineConfig()
    dependencies = _records_by_key(analysis_input_dependency_map, "input_family")
    draft_family_by_file = _lineage_draft_family_by_file(layout_contract_draft_queue)
    rows: list[dict[str, Any]] = []

    for rank, (family, definition) in enumerate(INPUT_FAMILY_DEFINITIONS.items(), start=1):
        dependency = dependencies.get(family, {})
        assembly_rows = _monthly_requirement_assembly_rows(file_assembly_plan, family, draft_family_by_file)
        draft_rows = _monthly_requirement_draft_rows(layout_contract_draft_queue, family)
        layout_rows = _monthly_requirement_layout_rows(
            layout_gap_report,
            source_layout_profile,
            family,
            draft_family_by_file,
        )
        file_names = _unique_tokens(
            [
                *[_trace_text(row.get("file_name")) for row in assembly_rows],
                *[_trace_text(row.get("file_name")) for row in draft_rows],
                *[_trace_text(row.get("file_name")) for row in layout_rows],
            ]
        )
        selected_rows = [row for row in assembly_rows if _truthy(row.get("load_flag"))]
        selected_file_names = _unique_tokens([_trace_text(row.get("file_name")) for row in selected_rows])
        selected_contracts = _unique_tokens(
            [
                *[_trace_text(row.get("contract_id")) for row in selected_rows],
                *[_trace_text(row.get("proposed_contract_id")) for row in draft_rows if _trace_text(row.get("contract_action")) == "promote_existing_contract"],
            ]
        )
        contract_actions = _unique_tokens([_trace_text(row.get("contract_action")) for row in draft_rows])
        priority_bands = _unique_tokens([_trace_text(row.get("priority_band")) for row in draft_rows])
        missing_fields = _unique_tokens(
            [
                token
                for row in layout_rows
                if _trace_text(row.get("mapping_status")) == "missing_required"
                for token in [_trace_text(row.get("canonical_field"))]
            ]
            + [
                token
                for row in draft_rows
                for token in _split_tokens(row.get("missing_required_fields"))
            ]
        )
        target_layer = _monthly_requirement_target_layer(family, selected_rows, draft_rows)
        status = _monthly_requirement_status(
            family=family,
            dependency=dependency,
            file_names=file_names,
            selected_file_names=selected_file_names,
            missing_fields=missing_fields,
            contract_actions=contract_actions,
        )
        rows.append(
            {
                "requirement_rank": rank,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "input_family": family,
                "display_name": definition["display_name"],
                "requirement_level": _monthly_requirement_level(family, dependency),
                "monthly_status": status,
                "canonical_role": definition["canonical_role"],
                "minimum_fields": definition["minimum_fields"],
                "optional_fields": definition["optional_fields"],
                "source_candidates": definition["source_candidates"],
                "dependent_domain_names": _trace_text(dependency.get("dependent_domain_names")),
                "dependent_sections": _trace_text(dependency.get("dependent_sections")),
                "dependent_section_count": _safe_int_value(dependency.get("dependent_section_count")),
                "received_file_count": len(file_names),
                "selected_file_count": len(selected_file_names),
                "received_file_names": "|".join(file_names),
                "selected_file_names": "|".join(selected_file_names),
                "selected_contract_ids": "|".join(selected_contracts),
                "contract_actions": "|".join(contract_actions),
                "priority_bands": "|".join(priority_bands),
                "missing_required_field_count": len(missing_fields),
                "missing_required_fields": "|".join(missing_fields),
                "current_run_readiness": _trace_text(dependency.get("current_run_readiness")),
                "layout_mapping_status": _trace_text(dependency.get("layout_mapping_status")),
                "target_snowflake_layer": target_layer,
                "snowflake_design_decision": definition["snowflake_design_decision"],
                "data_team_action": _monthly_requirement_data_team_action(
                    family=family,
                    status=status,
                    target_layer=target_layer,
                    missing_fields=missing_fields,
                    contract_actions=contract_actions,
                    file_names=file_names,
                ),
                "analyst_question": _monthly_requirement_analyst_question(family, status, dependency),
                "source_artifacts": "analysis_input_dependency_map.csv|file_assembly_plan.csv|layout_gap_report.csv|layout_contract_draft_queue.csv|source_layout_profile.csv",
                "model_version": "monthly_file_requirements_v0",
            }
        )

    return pd.DataFrame(rows, columns=_monthly_file_requirements_columns())


def build_analysis_requirement_matrix(
    analysis_section_catalog: pd.DataFrame,
    analysis_script_catalog: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    analysis_domain_map: pd.DataFrame,
    analysis_input_dependency_map: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create one section-level row linking analysis, fields, layouts, and outputs."""
    cfg = config or EngineConfig()
    if analysis_section_catalog is None or analysis_section_catalog.empty:
        return _empty_analysis_requirement_matrix()

    execution_by_section = _records_by_key(analysis_execution_map, "source_section_id")
    domains_by_section = _domains_by_section(analysis_domain_map)
    input_dependency_by_family = _records_by_key(analysis_input_dependency_map, "input_family")
    scripts_by_section = _scripts_by_section(analysis_script_catalog)
    rows: list[dict[str, Any]] = []

    for rank, section in enumerate(analysis_section_catalog.to_dict("records"), start=1):
        section_id = _trace_text(section.get("source_section_id"))
        product = _trace_text(section.get("product"))
        execution = execution_by_section.get(section_id, {})
        domain = domains_by_section.get(section_id, {})
        section_inputs = _split_tokens(execution.get("required_input_families")) or _split_tokens(
            _required_input_families(section_id, product)
        )
        domain_inputs = _split_tokens(domain.get("required_input_families"))
        input_families = _unique_tokens(section_inputs + domain_inputs)
        dependency_rows = [
            input_dependency_by_family.get(family, {})
            for family in input_families
            if input_dependency_by_family.get(family)
        ]
        readiness_pairs = [
            f"{family}={_trace_text(input_dependency_by_family.get(family, {}).get('current_run_readiness')) or 'unknown'}"
            for family in input_families
        ]
        contract_pairs = [
            f"{family}={_trace_text(input_dependency_by_family.get(family, {}).get('current_contract_status')) or 'unknown'}"
            for family in input_families
        ]
        scripts = scripts_by_section.get(section_id, [])
        script_names = [_trace_text(row.get("script_name")) for row in scripts if _trace_text(row.get("script_name"))]
        layout_blockers = _requirement_layout_blockers(input_families, input_dependency_by_family)
        minimum_fields = _fields_by_family(input_families, input_dependency_by_family, "minimum_fields")
        optional_fields = _fields_by_family(input_families, input_dependency_by_family, "optional_fields")

        rows.append(
            {
                "requirement_rank": rank,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "domain_id": _trace_text(domain.get("domain_id")),
                "domain_name": _trace_text(domain.get("domain_name")),
                "source_section_id": section_id,
                "product": product,
                "display_name": _trace_text(section.get("display_name")),
                "analysis_family": _trace_text(section.get("analysis_family")) or "unmapped",
                "business_question": _trace_text(domain.get("business_question")),
                "consulting_question": _trace_text(execution.get("consulting_question")) or _trace_text(domain.get("business_question")),
                "source_path": _trace_text(section.get("source_path")),
                "script_count": _safe_int_value(section.get("script_count"), default=len(scripts)),
                "runnable_script_count": _safe_int_value(section.get("runnable_script_count")),
                "representative_scripts": "|".join(script_names[:10]),
                "section_required_input_families": "|".join(section_inputs),
                "domain_required_input_families": "|".join(domain_inputs),
                "required_input_families": "|".join(input_families),
                "minimum_required_fields": "|".join(minimum_fields),
                "optional_enrichment_fields": "|".join(optional_fields),
                "source_candidates": "|".join(_fields_by_family(input_families, input_dependency_by_family, "source_candidates")),
                "contract_status_by_input": "|".join(contract_pairs),
                "current_layout_readiness": "|".join(readiness_pairs),
                "layout_blockers": "|".join(layout_blockers),
                "current_engine_outputs": _trace_text(execution.get("available_engine_outputs")),
                "missing_engine_outputs": _trace_text(execution.get("missing_engine_outputs")),
                "generated_output_files": _trace_text(execution.get("generated_output_files")),
                "generated_target_tables": _trace_text(execution.get("generated_target_tables")),
                "evidence_status": _trace_text(execution.get("evidence_status")),
                "supported_opportunity_types": _trace_text(section.get("supports_opportunity_types")),
                "model_rule_ids": _trace_text(execution.get("model_rule_ids")),
                "consulting_use": _trace_text(section.get("consulting_use")),
                "analyst_next_step": _trace_text(execution.get("analyst_next_step")),
                "data_team_question": _requirement_data_team_question(input_families, dependency_rows),
                "csm_review_question": _requirement_csm_question(section, execution, domain),
                "snowflake_design_action": _requirement_snowflake_action(input_families, dependency_rows),
                "source_artifacts": "analysis_section_catalog.csv|analysis_script_catalog.csv|analysis_execution_map.csv|analysis_domain_map.csv|analysis_input_dependency_map.csv",
                "model_version": "analysis_requirement_matrix_v0",
            }
        )

    return pd.DataFrame(rows, columns=_analysis_requirement_matrix_columns()).sort_values(
        ["domain_id", "source_section_id"],
        na_position="last",
    ).reset_index(drop=True)


def build_analysis_layout_coverage_matrix(
    analysis_field_usage_catalog: pd.DataFrame,
    analysis_requirement_matrix: pd.DataFrame,
    analysis_input_dependency_map: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    generated_artifacts: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Join script field evidence to current input-family and layout readiness."""
    cfg = config or EngineConfig()
    if analysis_field_usage_catalog is None or analysis_field_usage_catalog.empty:
        return _empty_analysis_layout_coverage_matrix()

    requirements_by_section = _records_by_key(analysis_requirement_matrix, "source_section_id")
    input_dependency_by_family = _records_by_key(analysis_input_dependency_map, "input_family")
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}

    for usage in analysis_field_usage_catalog.to_dict("records"):
        section_id = _trace_text(usage.get("source_section_id"))
        family_hints = _split_tokens(usage.get("input_family_hint")) or ["unknown"]
        canonical_hint = _trace_text(usage.get("canonical_field_hint"))
        normalized_field = _trace_text(usage.get("normalized_field"))
        field_key = canonical_hint or normalized_field or _trace_text(usage.get("field_reference")) or "unknown"
        for family in family_hints:
            key = (section_id, family, field_key)
            item = grouped.setdefault(
                key,
                {
                    "source_section_id": section_id,
                    "input_family_hint": family,
                    "field_key": field_key,
                    "canonical_hints": set(),
                    "normalized_fields": set(),
                    "field_references": set(),
                    "script_names": set(),
                    "source_paths": set(),
                    "line_numbers": set(),
                    "reference_count": 0,
                },
            )
            if canonical_hint:
                item["canonical_hints"].add(canonical_hint)
            if normalized_field:
                item["normalized_fields"].add(normalized_field)
            field_reference = _trace_text(usage.get("field_reference"))
            if field_reference:
                item["field_references"].add(field_reference)
            script_name = _trace_text(usage.get("script_name"))
            if script_name:
                item["script_names"].add(script_name)
            source_path = _trace_text(usage.get("source_path"))
            if source_path:
                item["source_paths"].add(source_path)
            line_number = _safe_int_value(usage.get("line_number"))
            if line_number:
                item["line_numbers"].add(line_number)
            item["reference_count"] += 1

    rows: list[dict[str, Any]] = []
    for (section_id, family, field_key), item in grouped.items():
        requirement = requirements_by_section.get(section_id, {})
        input_dependency = input_dependency_by_family.get(family, {})
        layout_matches = _layout_matches_for_analysis_field(
            layout_gap_report,
            family=family,
            field_key=field_key,
            canonical_hints=item["canonical_hints"],
            normalized_fields=item["normalized_fields"],
        )
        output_matches = _derived_output_matches_for_analysis_field(
            requirement,
            generated_artifacts,
            field_key=field_key,
            canonical_hints=item["canonical_hints"],
            normalized_fields=item["normalized_fields"],
        )
        readiness = _trace_text(input_dependency.get("current_run_readiness")) or "unknown"
        contract_status = _trace_text(input_dependency.get("current_contract_status")) or "unknown"
        layout_mapping_status = _trace_text(input_dependency.get("layout_mapping_status")) or "unknown"
        coverage_status = _analysis_layout_coverage_status(layout_matches, output_matches, readiness, field_key)
        coverage_severity = _analysis_layout_coverage_severity(coverage_status)
        missing_required_count = sum(
            1
            for row in layout_matches
            if _trace_text(row.get("mapping_status")) == "missing_required"
            and _trace_bool(row.get("required_flag"))
        )
        canonical_hints = _sorted_texts(item["canonical_hints"])
        line_numbers = sorted(item["line_numbers"])

        rows.append(
            {
                "coverage_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "source_section_id": section_id,
                "domain_id": _trace_text(requirement.get("domain_id")),
                "domain_name": _trace_text(requirement.get("domain_name")),
                "display_name": _trace_text(requirement.get("display_name")),
                "input_family_hint": family,
                "field_key": field_key,
                "canonical_field_hint": "|".join(canonical_hints),
                "example_field_references": "|".join(_sorted_texts(item["field_references"])[:8]),
                "reference_count": int(item["reference_count"]),
                "script_count": len(item["script_names"]),
                "example_scripts": "|".join(_sorted_texts(item["script_names"])[:8]),
                "example_line_numbers": "|".join(str(number) for number in line_numbers[:12]),
                "current_run_readiness": readiness,
                "contract_status": contract_status,
                "layout_mapping_status": layout_mapping_status,
                "layout_contract_fields": "|".join(
                    _unique_tokens(_layout_contract_fields(layout_matches) + _derived_output_fields(output_matches))
                ),
                "matched_source_columns": "|".join(
                    _unique_tokens(
                        _layout_matched_source_columns(layout_matches) + _derived_output_lineage(output_matches)
                    )
                ),
                "missing_required_count": missing_required_count,
                "coverage_status": coverage_status,
                "coverage_severity": coverage_severity,
                "analyst_action": _analysis_layout_analyst_action(coverage_status, section_id, family, field_key),
                "data_team_action": _analysis_layout_data_team_action(coverage_status, family, field_key),
                "source_artifacts": "analysis_field_usage_catalog.csv|analysis_requirement_matrix.csv|analysis_input_dependency_map.csv|layout_gap_report.csv",
                "model_version": "analysis_layout_coverage_matrix_v0",
            }
        )

    if not rows:
        return _empty_analysis_layout_coverage_matrix()

    severity_order = {"blocker": 0, "review": 1, "ready": 2}
    df = pd.DataFrame(rows, columns=_analysis_layout_coverage_matrix_columns()).sort_values(
        by=["coverage_severity", "source_section_id", "input_family_hint", "field_key"],
        key=lambda col: col.map(severity_order).fillna(3) if col.name == "coverage_severity" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["coverage_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_feature_derivation_catalog(
    analysis_layout_coverage_matrix: pd.DataFrame,
    analysis_input_dependency_map: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Catalog analysis fields that are satisfied by derived engine outputs."""
    cfg = config or EngineConfig()
    if analysis_layout_coverage_matrix is None or analysis_layout_coverage_matrix.empty:
        return _empty_analysis_feature_derivation_catalog()

    dependencies = _records_by_key(analysis_input_dependency_map, "input_family")
    rows: list[dict[str, Any]] = []
    derived_rows = analysis_layout_coverage_matrix[
        analysis_layout_coverage_matrix["coverage_status"].astype(str).eq("derived_engine_output_validate")
    ]
    for row in derived_rows.to_dict("records"):
        lineage = _derived_lineage_values(_split_tokens(row.get("matched_source_columns")))
        if not lineage:
            continue
        family = _trace_text(row.get("input_family_hint"))
        dependency = dependencies.get(family, {})
        rows.append(
            {
                "derivation_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "source_section_id": _trace_text(row.get("source_section_id")),
                "domain_id": _trace_text(row.get("domain_id")),
                "domain_name": _trace_text(row.get("domain_name")),
                "display_name": _trace_text(row.get("display_name")),
                "input_family_hint": family,
                "analysis_field_key": _trace_text(row.get("field_key")),
                "example_field_references": _trace_text(row.get("example_field_references")),
                "reference_count": _safe_int_value(row.get("reference_count")),
                "derived_output_lineage": "|".join(lineage),
                "derived_artifacts": "|".join(_derived_lineage_artifacts(lineage)),
                "derived_fields": "|".join(_derived_lineage_fields(lineage)),
                "base_input_requirements": _trace_text(dependency.get("minimum_fields")),
                "contract_status": _trace_text(row.get("contract_status")),
                "current_run_readiness": _trace_text(row.get("current_run_readiness")),
                "validation_status": "validation_required",
                "snowflake_expression_hint": _derivation_snowflake_expression_hint(lineage),
                "analyst_action": _derivation_analyst_action(row),
                "data_team_action": _derivation_data_team_action(row, dependency, lineage),
                "source_artifacts": "analysis_layout_coverage_matrix.csv|analysis_input_dependency_map.csv|generated_engine_outputs",
                "model_version": "analysis_feature_derivation_catalog_v0",
            }
        )

    if not rows:
        return _empty_analysis_feature_derivation_catalog()
    df = pd.DataFrame(rows, columns=_analysis_feature_derivation_catalog_columns()).sort_values(
        ["source_section_id", "input_family_hint", "analysis_field_key"],
        na_position="last",
    ).reset_index(drop=True)
    df["derivation_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_section_evidence_review(
    analysis_execution_map: pd.DataFrame,
    analysis_requirement_matrix: pd.DataFrame,
    analysis_field_usage_catalog: pd.DataFrame,
    analysis_layout_coverage_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a concise section-level review of analysis evidence and layout risk."""
    cfg = config or EngineConfig()
    if analysis_execution_map is None or analysis_execution_map.empty:
        return _empty_analysis_section_evidence_review()

    requirements_by_section = _records_by_key(analysis_requirement_matrix, "source_section_id")
    field_usage_by_section = _field_usage_by_section(analysis_field_usage_catalog)
    coverage_by_section = _layout_coverage_by_section(analysis_layout_coverage_matrix)
    rows: list[dict[str, Any]] = []

    for rank, execution in enumerate(analysis_execution_map.to_dict("records"), start=1):
        section_id = _trace_text(execution.get("source_section_id"))
        requirement = requirements_by_section.get(section_id, {})
        field_usage = field_usage_by_section.get(section_id, {})
        coverage = coverage_by_section.get(section_id, {})
        mapped_count = _safe_int_value(coverage.get("ready"))
        review_count = _safe_int_value(coverage.get("review"))
        blocker_count = _safe_int_value(coverage.get("blocker"))
        evidence_status = _trace_text(execution.get("evidence_status")) or "unknown"
        review_status = _section_review_status(evidence_status, mapped_count, review_count, blocker_count)

        rows.append(
            {
                "review_rank": rank,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "source_section_id": section_id,
                "domain_id": _trace_text(requirement.get("domain_id")),
                "domain_name": _trace_text(requirement.get("domain_name")),
                "display_name": _trace_text(execution.get("display_name")),
                "analysis_family": _trace_text(execution.get("analysis_family")),
                "business_question": _trace_text(requirement.get("business_question")),
                "consulting_question": _trace_text(execution.get("consulting_question"))
                or _trace_text(requirement.get("consulting_question")),
                "evidence_status": evidence_status,
                "section_review_status": review_status,
                "required_input_families": _trace_text(requirement.get("required_input_families"))
                or _trace_text(execution.get("required_input_families")),
                "current_layout_readiness": _trace_text(requirement.get("current_layout_readiness")),
                "layout_blockers": _trace_text(requirement.get("layout_blockers")),
                "generated_output_files": _trace_text(execution.get("generated_output_files")),
                "generated_target_tables": _trace_text(execution.get("generated_target_tables")),
                "generated_row_count": _safe_int_value(execution.get("generated_row_count")),
                "field_reference_count": _safe_int_value(field_usage.get("field_reference_count")),
                "distinct_field_count": _safe_int_value(field_usage.get("distinct_field_count")),
                "mapped_field_count": mapped_count,
                "review_field_count": review_count,
                "blocker_field_count": blocker_count,
                "top_blocker_fields": "|".join(coverage.get("top_blocker_fields", [])),
                "top_review_fields": "|".join(coverage.get("top_review_fields", [])),
                "analysis_summary": _section_analysis_summary(execution, requirement, review_status),
                "consulting_use": _trace_text(requirement.get("consulting_use")) or _trace_text(execution.get("consulting_use")),
                "analyst_next_step": _section_evidence_analyst_action(execution, review_status, blocker_count, review_count),
                "data_team_next_step": _section_evidence_data_team_action(requirement, coverage, blocker_count, review_count),
                "csm_review_question": _trace_text(requirement.get("csm_review_question")),
                "source_artifacts": "analysis_execution_map.csv|analysis_requirement_matrix.csv|analysis_field_usage_catalog.csv|analysis_layout_coverage_matrix.csv",
                "model_version": "analysis_section_evidence_review_v0",
            }
        )

    if not rows:
        return _empty_analysis_section_evidence_review()

    status_order = {
        "data_mapping_blocked": 0,
        "validate_before_external_use": 1,
        "usable_with_qualification": 2,
        "sellable_now": 3,
        "inventory_only": 4,
    }
    df = pd.DataFrame(rows, columns=_analysis_section_evidence_review_columns()).sort_values(
        by=["section_review_status", "domain_id", "source_section_id"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "section_review_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["review_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_data_team_backlog(
    analysis_layout_coverage_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Group hard layout blockers into a data-team action queue."""
    cfg = config or EngineConfig()
    if analysis_layout_coverage_matrix is None or analysis_layout_coverage_matrix.empty:
        return _empty_analysis_data_team_backlog()

    blockers = analysis_layout_coverage_matrix[
        analysis_layout_coverage_matrix["coverage_severity"].fillna("").astype(str).eq("blocker")
    ].copy()
    if blockers.empty:
        return _empty_analysis_data_team_backlog()

    rows: list[dict[str, Any]] = []
    grouped = blockers.groupby(["input_family_hint", "field_key", "coverage_status"], dropna=False)
    for _, group in grouped:
        reference_count = int(group["reference_count"].fillna(0).sum())
        section_ids = _sorted_texts(group["source_section_id"])
        domain_names = _sorted_texts(group["domain_name"])
        row = group.sort_values("reference_count", ascending=False).iloc[0]
        input_family = _trace_text(row.get("input_family_hint")) or "unknown"
        field_key = _trace_text(row.get("field_key")) or "unknown"
        coverage_status = _trace_text(row.get("coverage_status")) or "unknown"
        rows.append(
            {
                "backlog_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "input_family": input_family,
                "field_key": field_key,
                "coverage_status": coverage_status,
                "priority_band": _data_team_backlog_priority(reference_count, len(section_ids), coverage_status),
                "reference_count": reference_count,
                "affected_section_count": len(section_ids),
                "affected_sections": "|".join(section_ids[:12]),
                "affected_domains": "|".join(domain_names[:8]),
                "example_scripts": "|".join(_unique_pipe_values(group["example_scripts"].dropna().astype(str).tolist())[:12]),
                "example_field_references": "|".join(_unique_pipe_values(group["example_field_references"].dropna().astype(str).tolist())[:12]),
                "current_run_readiness": "|".join(_sorted_texts(group["current_run_readiness"])),
                "layout_mapping_status": "|".join(_sorted_texts(group["layout_mapping_status"])),
                "contract_status": "|".join(_sorted_texts(group["contract_status"])),
                "data_team_action": _trace_text(row.get("data_team_action")),
                "analyst_action": _trace_text(row.get("analyst_action")),
                "snowflake_design_action": _data_team_backlog_snowflake_action(input_family, field_key, coverage_status),
                "source_artifacts": "analysis_layout_coverage_matrix.csv|analysis_section_evidence_review.csv|analysis_requirement_matrix.csv",
                "model_version": "analysis_data_team_backlog_v0",
            }
        )

    if not rows:
        return _empty_analysis_data_team_backlog()
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    df = pd.DataFrame(rows, columns=_analysis_data_team_backlog_columns()).sort_values(
        by=["priority_band", "reference_count", "affected_section_count", "input_family", "field_key"],
        ascending=[True, False, False, True, True],
        key=lambda col: col.map(priority_order).fillna(9) if col.name == "priority_band" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["backlog_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_metric_validation_queue(
    analysis_layout_coverage_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Group derived, alias, and rule-based coverage into an analyst validation queue."""
    cfg = config or EngineConfig()
    if analysis_layout_coverage_matrix is None or analysis_layout_coverage_matrix.empty:
        return _empty_analysis_metric_validation_queue()

    review_statuses = {
        "derived_engine_output_validate",
        "not_in_contract_validate_alias",
        "needs_mapping_review",
        "rule_based_validate_with_client",
        "loaded_directly_unprofiled",
        "derived_from_account_data_validate",
    }
    queue = analysis_layout_coverage_matrix[
        analysis_layout_coverage_matrix["coverage_status"].fillna("").astype(str).isin(review_statuses)
    ].copy()
    if queue.empty:
        return _empty_analysis_metric_validation_queue()

    rows: list[dict[str, Any]] = []
    grouped = queue.groupby(["input_family_hint", "field_key", "coverage_status"], dropna=False)
    for _, group in grouped:
        reference_count = int(group["reference_count"].fillna(0).sum())
        section_ids = _sorted_texts(group["source_section_id"])
        domain_names = _sorted_texts(group["domain_name"])
        row = group.sort_values("reference_count", ascending=False).iloc[0]
        coverage_status = _trace_text(row.get("coverage_status")) or "unknown"
        field_key = _trace_text(row.get("field_key")) or "unknown"
        input_family = _trace_text(row.get("input_family_hint")) or "unknown"
        rows.append(
            {
                "validation_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "input_family": input_family,
                "field_key": field_key,
                "coverage_status": coverage_status,
                "validation_type": _metric_validation_type(coverage_status),
                "priority_band": _metric_validation_priority(reference_count, len(section_ids), coverage_status),
                "reference_count": reference_count,
                "affected_section_count": len(section_ids),
                "affected_sections": "|".join(section_ids[:12]),
                "affected_domains": "|".join(domain_names[:8]),
                "derived_lineage": "|".join(_derived_lineage_values(group["matched_source_columns"].dropna().astype(str).tolist())[:12]),
                "candidate_contract_fields": "|".join(_unique_pipe_values(group["layout_contract_fields"].dropna().astype(str).tolist())[:12]),
                "example_scripts": "|".join(_unique_pipe_values(group["example_scripts"].dropna().astype(str).tolist())[:12]),
                "analyst_action": _trace_text(row.get("analyst_action")),
                "data_team_action": _trace_text(row.get("data_team_action")),
                "validation_decision": _metric_validation_decision(coverage_status),
                "source_artifacts": "analysis_layout_coverage_matrix.csv|analysis_section_evidence_review.csv|analysis_requirement_matrix.csv",
                "model_version": "analysis_metric_validation_queue_v0",
            }
        )

    if not rows:
        return _empty_analysis_metric_validation_queue()
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    df = pd.DataFrame(rows, columns=_analysis_metric_validation_queue_columns()).sort_values(
        by=["priority_band", "reference_count", "affected_section_count", "input_family", "field_key"],
        ascending=[True, False, False, True, True],
        key=lambda col: col.map(priority_order).fillna(9) if col.name == "priority_band" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["validation_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_visual_output_map(
    analysis_execution_map: pd.DataFrame,
    analysis_section_evidence_review: pd.DataFrame,
    analysis_script_catalog: pd.DataFrame,
    analysis_layout_coverage_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Map each analysis section to concrete output surfaces and visual views."""
    cfg = config or EngineConfig()
    if analysis_execution_map is None or analysis_execution_map.empty:
        return _empty_analysis_visual_output_map()

    evidence_by_section = _records_by_key(analysis_section_evidence_review, "source_section_id")
    script_lookup = _analysis_scripts_by_section(analysis_script_catalog)
    field_lookup = _analysis_fields_by_section(analysis_layout_coverage_matrix)
    rows: list[dict[str, Any]] = []
    for execution in analysis_execution_map.sort_values("execution_rank").to_dict("records"):
        section_id = _trace_text(execution.get("source_section_id"))
        if not section_id:
            continue
        evidence = evidence_by_section.get(section_id, {})
        output_files = _split_tokens(execution.get("generated_output_files"))
        target_tables = _split_tokens(execution.get("generated_target_tables"))
        if not output_files:
            output_files = ["analysis_inventory_only"]
        source_scripts = script_lookup.get(section_id, [])
        section_fields = field_lookup.get(section_id, {})
        for output_index, output_file in enumerate(output_files):
            target_table = target_tables[output_index] if output_index < len(target_tables) else ""
            visual_family, visual_type, visual_mode = _visual_surface_for_output(output_file)
            blocker_count = _safe_int_value(evidence.get("blocker_field_count"))
            review_count = _safe_int_value(evidence.get("review_field_count"))
            readiness_status = _visual_readiness_status(
                _trace_text(evidence.get("section_review_status")),
                _trace_text(execution.get("evidence_status")),
                blocker_count,
                review_count,
            )
            rows.append(
                {
                    "visual_rank": 0,
                    "client_id": cfg.client_id,
                    "period_month": _period_label(cfg.period_month),
                    "source_section_id": section_id,
                    "domain_id": _trace_text(evidence.get("domain_id")),
                    "domain_name": _trace_text(evidence.get("domain_name")),
                    "display_name": _trace_text(execution.get("display_name")) or _trace_text(evidence.get("display_name")),
                    "analysis_family": _trace_text(execution.get("analysis_family")) or _trace_text(evidence.get("analysis_family")),
                    "business_question": _trace_text(evidence.get("business_question")),
                    "consulting_question": _trace_text(execution.get("consulting_question")) or _trace_text(evidence.get("consulting_question")),
                    "output_file": output_file,
                    "target_table": target_table,
                    "visual_family": visual_family,
                    "visual_type": visual_type,
                    "visual_mode": visual_mode,
                    "visual_title": _visual_title_for_output(
                        _trace_text(execution.get("display_name")) or section_id,
                        output_file,
                    ),
                    "chart_readiness_status": readiness_status,
                    "evidence_status": _trace_text(execution.get("evidence_status")),
                    "section_review_status": _trace_text(evidence.get("section_review_status")),
                    "field_reference_count": _safe_int_value(evidence.get("field_reference_count")),
                    "blocker_field_count": blocker_count,
                    "review_field_count": review_count,
                    "source_scripts": "|".join(source_scripts[:12]),
                    "source_fields_to_validate": "|".join(_unique_pipe_values([
                        _trace_text(evidence.get("top_blocker_fields")),
                        _trace_text(evidence.get("top_review_fields")),
                    ])[:12]),
                    "csm_use": _trace_text(evidence.get("consulting_use")) or _trace_text(execution.get("consulting_use")),
                    "analyst_action": _trace_text(evidence.get("analyst_next_step")) or _trace_text(execution.get("analyst_next_step")),
                    "data_team_action": _trace_text(evidence.get("data_team_next_step")),
                    "proof_artifacts": _visual_proof_artifacts(output_file, section_fields),
                    "source_artifacts": "analysis_execution_map.csv|analysis_section_evidence_review.csv|analysis_script_catalog.csv|analysis_layout_coverage_matrix.csv",
                    "model_version": "analysis_visual_output_map_v0",
                }
            )

    if not rows:
        return _empty_analysis_visual_output_map()
    status_order = {
        "client_ready": 0,
        "validation_required": 1,
        "qualified_by_layout_blockers": 2,
        "partial_or_inventory": 3,
    }
    df = pd.DataFrame(rows, columns=_analysis_visual_output_map_columns()).sort_values(
        by=["chart_readiness_status", "domain_name", "source_section_id", "visual_rank"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "chart_readiness_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["visual_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_chart_spec_catalog(
    analysis_visual_output_map: pd.DataFrame,
    generated_artifacts: dict[str, Any] | None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create chart/table/story rendering specs from the analysis visual map."""
    cfg = config or EngineConfig()
    if analysis_visual_output_map is None or analysis_visual_output_map.empty:
        return _empty_analysis_chart_spec_catalog()

    artifact_frames = _generated_artifact_dataframes_by_file(generated_artifacts)
    rows: list[dict[str, Any]] = []
    for visual in analysis_visual_output_map.sort_values("visual_rank").to_dict("records"):
        output_file = _trace_text(visual.get("output_file"))
        frame = artifact_frames.get(output_file)
        if frame is None:
            frame = artifact_frames.get(output_file.removesuffix(".csv"))
        columns = list(frame.columns) if isinstance(frame, pd.DataFrame) and not frame.empty else []
        spec = _chart_spec_for_visual(visual, columns)
        required = _unique_pipe_values([spec.get("x_field"), spec.get("y_field"), spec.get("series_field")])
        missing_required = [field for field in required if field and field not in columns]
        rows.append(
            {
                "spec_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "source_section_id": _trace_text(visual.get("source_section_id")),
                "domain_name": _trace_text(visual.get("domain_name")),
                "display_name": _trace_text(visual.get("display_name")),
                "output_file": output_file,
                "target_table": _trace_text(visual.get("target_table")),
                "visual_family": _trace_text(visual.get("visual_family")),
                "visual_type": _trace_text(visual.get("visual_type")),
                "visual_mode": _trace_text(visual.get("visual_mode")),
                "chart_title": _trace_text(visual.get("visual_title")),
                "chart_type": spec["chart_type"],
                "data_artifact": output_file,
                "x_field": spec["x_field"],
                "y_field": spec["y_field"],
                "series_field": spec["series_field"],
                "label_field": spec["label_field"],
                "value_field": spec["value_field"],
                "color_field": spec["color_field"],
                "filter_hint": spec["filter_hint"],
                "sort_hint": spec["sort_hint"],
                "top_n": spec["top_n"],
                "available_columns": "|".join(columns),
                "required_columns_present": not missing_required,
                "missing_required_columns": "|".join(missing_required),
                "chart_readiness_status": _trace_text(visual.get("chart_readiness_status")),
                "render_owner": _chart_render_owner(_trace_text(visual.get("visual_mode"))),
                "csm_use": _trace_text(visual.get("csm_use")),
                "analyst_action": _trace_text(visual.get("analyst_action")),
                "proof_artifacts": _trace_text(visual.get("proof_artifacts")),
                "source_artifacts": "analysis_visual_output_map.csv|analysis_package_index.csv|generated_engine_outputs",
                "model_version": "analysis_chart_spec_catalog_v0",
            }
        )

    if not rows:
        return _empty_analysis_chart_spec_catalog()
    df = pd.DataFrame(rows, columns=_analysis_chart_spec_catalog_columns()).sort_values(
        by=["chart_readiness_status", "domain_name", "source_section_id", "spec_rank"],
        na_position="last",
    ).reset_index(drop=True)
    df["spec_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_chart_data_snapshot(
    analysis_chart_spec_catalog: pd.DataFrame,
    generated_artifacts: dict[str, Any] | None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Materialize compact data snapshots behind each analysis chart spec."""
    cfg = config or EngineConfig()
    if analysis_chart_spec_catalog is None or analysis_chart_spec_catalog.empty:
        return _empty_analysis_chart_data_snapshot()

    artifact_frames = _generated_artifact_dataframes_by_file(generated_artifacts)
    rows: list[dict[str, Any]] = []
    for spec in analysis_chart_spec_catalog.sort_values("spec_rank").to_dict("records"):
        artifact_name = _trace_text(spec.get("data_artifact")) or _trace_text(spec.get("output_file"))
        frame = artifact_frames.get(artifact_name)
        if frame is None and artifact_name.endswith(".csv"):
            frame = artifact_frames.get(artifact_name.removesuffix(".csv"))
        snapshot = _chart_data_snapshot_for_spec(spec, frame)
        rows.append(
            {
                "snapshot_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "spec_rank": _safe_int_value(spec.get("spec_rank")),
                "source_section_id": _trace_text(spec.get("source_section_id")),
                "domain_name": _trace_text(spec.get("domain_name")),
                "display_name": _trace_text(spec.get("display_name")),
                "chart_title": _trace_text(spec.get("chart_title")),
                "chart_type": _trace_text(spec.get("chart_type")),
                "data_artifact": artifact_name,
                "target_table": _trace_text(spec.get("target_table")),
                "x_field": _trace_text(spec.get("x_field")),
                "y_field": _trace_text(spec.get("y_field")),
                "series_field": _trace_text(spec.get("series_field")),
                "label_field": _trace_text(spec.get("label_field")),
                "value_field": _trace_text(spec.get("value_field")),
                "color_field": _trace_text(spec.get("color_field")),
                "sort_hint": _trace_text(spec.get("sort_hint")),
                "top_n": _safe_int_value(spec.get("top_n")),
                "source_row_count": snapshot["source_row_count"],
                "plotted_row_count": snapshot["plotted_row_count"],
                "x_cardinality": snapshot["x_cardinality"],
                "series_cardinality": snapshot["series_cardinality"],
                "numeric_total": snapshot["numeric_total"],
                "numeric_avg": snapshot["numeric_avg"],
                "numeric_min": snapshot["numeric_min"],
                "numeric_max": snapshot["numeric_max"],
                "top_label": snapshot["top_label"],
                "top_value": snapshot["top_value"],
                "top_series": snapshot["top_series"],
                "top_data_points_json": snapshot["top_data_points_json"],
                "sample_records_json": snapshot["sample_records_json"],
                "data_status": snapshot["data_status"],
                "chart_readiness_status": _trace_text(spec.get("chart_readiness_status")),
                "render_owner": _trace_text(spec.get("render_owner")),
                "insight_callout": snapshot["insight_callout"],
                "csm_use": _trace_text(spec.get("csm_use")),
                "analyst_action": _trace_text(spec.get("analyst_action")),
                "proof_artifacts": _trace_text(spec.get("proof_artifacts")),
                "source_artifacts": "analysis_chart_spec_catalog.csv|generated_engine_outputs",
                "model_version": "analysis_chart_data_snapshot_v0",
            }
        )

    if not rows:
        return _empty_analysis_chart_data_snapshot()
    status_order = {"data_ready": 0, "empty_artifact": 1, "missing_required_columns": 2, "missing_artifact": 3}
    df = pd.DataFrame(rows, columns=_analysis_chart_data_snapshot_columns()).sort_values(
        by=["data_status", "source_section_id", "spec_rank"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "data_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["snapshot_rank"] = range(1, len(df) + 1)
    return df


def build_intelligence_metric_catalog(
    analysis_chart_spec_catalog: pd.DataFrame,
    analysis_chart_data_snapshot: pd.DataFrame,
    analysis_metric_validation_queue: pd.DataFrame,
    model_rulebook: pd.DataFrame,
    generated_artifacts: dict[str, Any] | None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a semantic metric catalog from chart specs, snapshots, rules, and validation queues."""
    cfg = config or EngineConfig()
    if analysis_chart_spec_catalog is None or analysis_chart_spec_catalog.empty:
        return _empty_intelligence_metric_catalog()

    artifact_frames = _generated_artifact_dataframes_by_file(generated_artifacts)
    validation_lookup = _metric_catalog_validation_lookup(analysis_metric_validation_queue)
    rule_lookup = _metric_catalog_rule_lookup(model_rulebook)
    snapshot_by_spec = _metric_catalog_snapshots_by_spec(analysis_chart_data_snapshot)
    rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    field_roles = [
        ("dimension", "x_field"),
        ("measure", "y_field"),
        ("series", "series_field"),
        ("label", "label_field"),
        ("value", "value_field"),
        ("color", "color_field"),
    ]

    for spec in analysis_chart_spec_catalog.sort_values("spec_rank").to_dict("records"):
        artifact = _trace_text(spec.get("data_artifact")) or _trace_text(spec.get("output_file"))
        if not artifact:
            continue
        spec_rank = _safe_int_value(spec.get("spec_rank"))
        snapshot = snapshot_by_spec.get(spec_rank, {})
        for role, column_name in field_roles:
            field_name = _trace_text(spec.get(column_name))
            if not field_name:
                continue
            key = (artifact, field_name)
            record = rows_by_key.setdefault(
                key,
                {
                    "source_artifact": artifact,
                    "source_field": field_name,
                    "target_tables": [],
                    "roles": [],
                    "spec_ranks": [],
                    "sections": [],
                    "chart_types": [],
                    "chart_titles": [],
                    "output_files": [],
                    "data_statuses": [],
                    "callouts": [],
                    "top_labels": [],
                    "top_values": [],
                    "top_series": [],
                    "source_row_counts": [],
                    "plotted_row_counts": [],
                    "numeric_totals": [],
                    "numeric_avgs": [],
                    "numeric_mins": [],
                    "numeric_maxes": [],
                },
            )
            _metric_catalog_append_unique(record["roles"], role)
            _metric_catalog_append_unique(record["spec_ranks"], spec_rank)
            _metric_catalog_append_unique(record["sections"], _trace_text(spec.get("source_section_id")))
            _metric_catalog_append_unique(record["chart_types"], _trace_text(spec.get("chart_type")))
            _metric_catalog_append_unique(record["chart_titles"], _trace_text(spec.get("chart_title")))
            _metric_catalog_append_unique(record["output_files"], _trace_text(spec.get("output_file")))
            _metric_catalog_append_unique(record["target_tables"], _trace_text(spec.get("target_table")))
            _metric_catalog_append_unique(record["data_statuses"], _trace_text(snapshot.get("data_status")))
            _metric_catalog_append_unique(record["callouts"], _trace_text(snapshot.get("insight_callout")))
            _metric_catalog_append_unique(record["top_labels"], _trace_text(snapshot.get("top_label")))
            _metric_catalog_append_unique(record["top_values"], _trace_text(snapshot.get("top_value")))
            _metric_catalog_append_unique(record["top_series"], _trace_text(snapshot.get("top_series")))
            _metric_catalog_append_numeric(record["source_row_counts"], snapshot.get("source_row_count"))
            _metric_catalog_append_numeric(record["plotted_row_counts"], snapshot.get("plotted_row_count"))
            if role in {"measure", "value"}:
                _metric_catalog_append_numeric(record["numeric_totals"], snapshot.get("numeric_total"))
                _metric_catalog_append_numeric(record["numeric_avgs"], snapshot.get("numeric_avg"))
                _metric_catalog_append_numeric(record["numeric_mins"], snapshot.get("numeric_min"))
                _metric_catalog_append_numeric(record["numeric_maxes"], snapshot.get("numeric_max"))

    rows: list[dict[str, Any]] = []
    for record in rows_by_key.values():
        artifact = record["source_artifact"]
        field_name = record["source_field"]
        roles = [str(role) for role in record["roles"] if _trace_text(role)]
        metric_id = _metric_catalog_id(artifact, field_name)
        field_key = _layout_field_key(field_name)
        validation_matches = _metric_catalog_matches(validation_lookup, artifact, field_name)
        rule_matches = rule_lookup.get(field_key, [])
        metric_family = _metric_catalog_family(field_name, artifact, roles)
        validation_status = _metric_catalog_validation_status(validation_matches, record["data_statuses"], roles)
        rows.append(
            {
                "metric_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "metric_id": metric_id,
                "metric_name": _metric_catalog_name(field_name),
                "metric_family": metric_family,
                "business_definition": _metric_catalog_business_definition(field_name, artifact, metric_family, roles),
                "metric_grain": _metric_catalog_grain(artifact, roles),
                "source_artifact": artifact,
                "target_table": "|".join(_sorted_texts(record["target_tables"])),
                "source_field": field_name,
                "field_role": "|".join(_sorted_texts(roles)),
                "aggregation_method": _metric_catalog_aggregation_method(field_name, roles),
                "data_type": _metric_catalog_data_type(artifact_frames, artifact, field_name),
                "chart_usage_count": len(record["spec_ranks"]),
                "section_usage_count": len(_sorted_texts(record["sections"])),
                "used_by_sections": "|".join(_sorted_texts(record["sections"])),
                "used_by_chart_types": "|".join(_sorted_texts(record["chart_types"])),
                "used_by_outputs": "|".join(_sorted_texts(record["output_files"])),
                "model_rule_ids": "|".join(_metric_catalog_rule_ids(rule_matches)),
                "validation_status": validation_status,
                "validation_owner": _metric_catalog_validation_owner(validation_status, metric_family, roles),
                "validation_queue_refs": "|".join(_metric_catalog_validation_refs(validation_matches)),
                "sample_value": _metric_catalog_sample_value(record, roles),
                "sample_period": _period_label(cfg.period_month),
                "numeric_total": _metric_catalog_numeric_summary(record["numeric_totals"], "sum"),
                "numeric_avg": _metric_catalog_numeric_summary(record["numeric_avgs"], "avg"),
                "numeric_min": _metric_catalog_numeric_summary(record["numeric_mins"], "min"),
                "numeric_max": _metric_catalog_numeric_summary(record["numeric_maxes"], "max"),
                "source_row_count_max": _metric_catalog_numeric_summary(record["source_row_counts"], "max"),
                "plotted_row_count_max": _metric_catalog_numeric_summary(record["plotted_row_counts"], "max"),
                "chart_callout": _first_nonempty(record["callouts"]),
                "snowflake_expression_hint": _metric_catalog_snowflake_expression_hint(field_name, artifact, roles),
                "csm_interpretation": _metric_catalog_csm_interpretation(field_name, metric_family, roles),
                "data_team_action": _metric_catalog_data_team_action(validation_status, artifact, field_name),
                "source_artifacts": (
                    "analysis_chart_spec_catalog.csv|analysis_chart_data_snapshot.csv|"
                    "analysis_metric_validation_queue.csv|model_rulebook.csv|generated_engine_outputs"
                ),
                "model_version": "intelligence_metric_catalog_v0",
            }
        )

    if not rows:
        return _empty_intelligence_metric_catalog()
    status_order = {
        "validation_required": 0,
        "data_issue_review": 1,
        "defined_by_engine": 2,
        "dimension_reference": 3,
    }
    df = pd.DataFrame(rows, columns=_intelligence_metric_catalog_columns()).sort_values(
        by=["validation_status", "metric_family", "metric_id"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "validation_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["metric_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_consulting_playbook(
    analysis_section_evidence_review: pd.DataFrame,
    analysis_visual_output_map: pd.DataFrame,
    analysis_chart_spec_catalog: pd.DataFrame,
    analysis_requirement_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Turn analysis evidence into a section-level consulting and output playbook."""
    cfg = config or EngineConfig()
    if analysis_section_evidence_review is None or analysis_section_evidence_review.empty:
        return _empty_analysis_consulting_playbook()

    requirements_by_section = _records_by_key(analysis_requirement_matrix, "source_section_id")
    visuals_by_section = _records_grouped_by_key(analysis_visual_output_map, "source_section_id")
    chart_specs_by_section = _records_grouped_by_key(analysis_chart_spec_catalog, "source_section_id")
    rows: list[dict[str, Any]] = []

    source = analysis_section_evidence_review.sort_values(
        "review_rank" if "review_rank" in analysis_section_evidence_review.columns else "source_section_id"
    )
    for evidence in source.to_dict("records"):
        section_id = _trace_text(evidence.get("source_section_id"))
        if not section_id:
            continue
        requirement = requirements_by_section.get(section_id, {})
        primary_chart = _playbook_primary_chart_spec(chart_specs_by_section.get(section_id, []))
        primary_visual = _playbook_primary_visual(visuals_by_section.get(section_id, []), primary_chart)
        blocker_count = _safe_int_value(evidence.get("blocker_field_count"))
        review_count = _safe_int_value(evidence.get("review_field_count"))
        section_status = _trace_text(evidence.get("section_review_status")) or "unknown"
        chart_status = _trace_text(primary_chart.get("chart_readiness_status")) or _trace_text(
            primary_visual.get("chart_readiness_status")
        )
        output_file = _trace_text(primary_chart.get("output_file")) or _trace_text(primary_visual.get("output_file"))
        target_table = _trace_text(primary_chart.get("target_table")) or _trace_text(primary_visual.get("target_table"))
        chart_title = _trace_text(primary_chart.get("chart_title")) or _trace_text(primary_visual.get("visual_title"))
        chart_type = _trace_text(primary_chart.get("chart_type")) or _trace_text(primary_visual.get("visual_type"))
        generated_outputs = _unique_tokens(
            [
                evidence.get("generated_output_files"),
                primary_visual.get("output_file"),
                primary_chart.get("output_file"),
            ]
        )
        target_tables = _unique_tokens(
            [
                evidence.get("generated_target_tables"),
                primary_visual.get("target_table"),
                primary_chart.get("target_table"),
            ]
        )
        story_role = _playbook_story_role(evidence, requirement, section_status)
        stakeholder_owner = _playbook_stakeholder_owner(section_status, chart_status, blocker_count, review_count)
        rows.append(
            {
                "playbook_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "domain_id": _trace_text(evidence.get("domain_id")),
                "domain_name": _trace_text(evidence.get("domain_name")),
                "source_section_id": section_id,
                "display_name": _trace_text(evidence.get("display_name")),
                "analysis_family": _trace_text(evidence.get("analysis_family")),
                "business_question": _trace_text(evidence.get("business_question")),
                "consulting_question": _trace_text(evidence.get("consulting_question"))
                or _trace_text(requirement.get("consulting_question")),
                "client_story_role": story_role,
                "meeting_moment": _playbook_meeting_moment(story_role, section_status),
                "primary_business_claim": _playbook_business_claim(evidence, requirement, story_role),
                "recommended_storyline": _playbook_storyline(evidence, requirement, story_role),
                "primary_chart_title": chart_title,
                "primary_chart_type": chart_type,
                "primary_output_file": output_file,
                "primary_target_table": target_table,
                "output_readiness_status": chart_status or section_status,
                "section_review_status": section_status,
                "evidence_status": _trace_text(evidence.get("evidence_status")),
                "generated_output_files": "|".join(generated_outputs),
                "generated_target_tables": "|".join(target_tables),
                "generated_row_count": _safe_int_value(evidence.get("generated_row_count")),
                "field_reference_count": _safe_int_value(evidence.get("field_reference_count")),
                "mapped_field_count": _safe_int_value(evidence.get("mapped_field_count")),
                "review_field_count": review_count,
                "blocker_field_count": blocker_count,
                "top_blocker_fields": _trace_text(evidence.get("top_blocker_fields")),
                "top_review_fields": _trace_text(evidence.get("top_review_fields")),
                "stakeholder_owner": stakeholder_owner,
                "csm_talk_track": _playbook_csm_talk_track(evidence, story_role, chart_title, output_file),
                "analyst_validation_focus": _playbook_analyst_focus(evidence, chart_status, review_count),
                "data_team_dependency": _playbook_data_dependency(evidence, requirement, blocker_count),
                "marketing_activation_use": _playbook_marketing_use(evidence, output_file, story_role),
                "snowflake_design_action": _trace_text(requirement.get("snowflake_design_action")),
                "proof_artifacts": "|".join(
                    _unique_tokens(
                        [
                            output_file,
                            primary_chart.get("proof_artifacts"),
                            primary_visual.get("proof_artifacts"),
                            "analysis_section_evidence_review.csv",
                            "analysis_chart_spec_catalog.csv",
                        ]
                    )
                ),
                "source_artifacts": "analysis_section_evidence_review.csv|analysis_visual_output_map.csv|analysis_chart_spec_catalog.csv|analysis_requirement_matrix.csv",
                "model_version": "analysis_consulting_playbook_v0",
            }
        )

    if not rows:
        return _empty_analysis_consulting_playbook()
    status_order = {
        "client_ready": 0,
        "validation_required": 1,
        "qualified_by_layout_blockers": 2,
        "partial_or_inventory": 3,
        "data_mapping_blocked": 4,
    }
    df = pd.DataFrame(rows, columns=_analysis_consulting_playbook_columns()).sort_values(
        by=["output_readiness_status", "domain_name", "source_section_id"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "output_readiness_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["playbook_rank"] = range(1, len(df) + 1)
    return df


def build_analysis_insight_brief(
    analysis_section_evidence_review: pd.DataFrame,
    analysis_consulting_playbook: pd.DataFrame,
    analysis_chart_data_snapshot: pd.DataFrame,
    intelligence_metric_catalog: pd.DataFrame,
    analysis_requirement_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Build a concise, data-backed consulting brief for each analysis section."""
    cfg = config or EngineConfig()
    if analysis_section_evidence_review is None or analysis_section_evidence_review.empty:
        return _empty_analysis_insight_brief()

    playbook_by_section = _records_by_key(analysis_consulting_playbook, "source_section_id")
    requirement_by_section = _records_by_key(analysis_requirement_matrix, "source_section_id")
    snapshots_by_section = _records_grouped_by_key(analysis_chart_data_snapshot, "source_section_id")
    metrics_by_section = _insight_brief_metrics_by_section(intelligence_metric_catalog)
    rows: list[dict[str, Any]] = []

    source = analysis_section_evidence_review.sort_values(
        "review_rank" if "review_rank" in analysis_section_evidence_review.columns else "source_section_id"
    )
    for evidence in source.to_dict("records"):
        section_id = _trace_text(evidence.get("source_section_id"))
        if not section_id:
            continue
        playbook = playbook_by_section.get(section_id, {})
        requirement = requirement_by_section.get(section_id, {})
        snapshots = snapshots_by_section.get(section_id, [])
        metrics = metrics_by_section.get(section_id, [])
        primary_snapshot = _insight_brief_primary_snapshot(snapshots)
        primary_metrics = _insight_brief_primary_metrics(metrics)
        blocker_count = _safe_int_value(evidence.get("blocker_field_count"))
        review_count = _safe_int_value(evidence.get("review_field_count"))
        validation_metric_count = sum(
            1 for metric in metrics if _trace_text(metric.get("validation_status")) == "validation_required"
        )
        chart_count = len(snapshots)
        ready_chart_count = sum(1 for row in snapshots if _trace_text(row.get("data_status")) == "data_ready")
        output_file = _trace_text(playbook.get("primary_output_file")) or _trace_text(primary_snapshot.get("data_artifact"))
        chart_title = _trace_text(playbook.get("primary_chart_title")) or _trace_text(primary_snapshot.get("chart_title"))
        chart_type = _trace_text(playbook.get("primary_chart_type")) or _trace_text(primary_snapshot.get("chart_type"))
        chart_status = _trace_text(primary_snapshot.get("data_status"))
        rows.append(
            {
                "brief_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "domain_id": _trace_text(evidence.get("domain_id")),
                "domain_name": _trace_text(evidence.get("domain_name")),
                "source_section_id": section_id,
                "display_name": _trace_text(evidence.get("display_name")),
                "analysis_family": _trace_text(evidence.get("analysis_family")),
                "brief_status": _insight_brief_status(blocker_count, review_count, validation_metric_count, ready_chart_count),
                "section_review_status": _trace_text(evidence.get("section_review_status")),
                "output_readiness_status": _trace_text(playbook.get("output_readiness_status")),
                "business_question": _trace_text(evidence.get("business_question")),
                "consulting_question": _trace_text(evidence.get("consulting_question"))
                or _trace_text(requirement.get("consulting_question")),
                "what_is_analyzed": _insight_brief_focus(evidence, requirement),
                "headline_insight": _insight_brief_headline(evidence, playbook, primary_snapshot),
                "primary_evidence": _insight_brief_primary_evidence(evidence, primary_snapshot, ready_chart_count, chart_count),
                "primary_chart_title": chart_title,
                "primary_chart_type": chart_type,
                "primary_output_file": output_file,
                "chart_data_status": chart_status or ("data_ready" if ready_chart_count else "no_chart_data"),
                "chart_count": chart_count,
                "data_ready_chart_count": ready_chart_count,
                "metric_count": len(metrics),
                "primary_metric_ids": "|".join(_trace_text(metric.get("metric_id")) for metric in primary_metrics if _trace_text(metric.get("metric_id"))),
                "primary_metrics": _insight_brief_metric_names(primary_metrics),
                "metric_definitions": _insight_brief_metric_definitions(primary_metrics),
                "sample_values": _insight_brief_sample_values(primary_metrics),
                "data_caveat": _insight_brief_data_caveat(blocker_count, review_count, validation_metric_count, ready_chart_count, chart_count),
                "csm_talk_track": _trace_text(playbook.get("csm_talk_track")),
                "recommended_client_question": _insight_brief_client_question(evidence, playbook, requirement),
                "analyst_next_step": _trace_text(playbook.get("analyst_validation_focus"))
                or _trace_text(evidence.get("analyst_next_step")),
                "data_team_next_step": _trace_text(playbook.get("data_team_dependency"))
                or _trace_text(evidence.get("data_team_next_step")),
                "marketing_activation_use": _trace_text(playbook.get("marketing_activation_use")),
                "proof_artifacts": "|".join(
                    _unique_tokens(
                        [
                            output_file,
                            primary_snapshot.get("data_artifact"),
                            playbook.get("proof_artifacts"),
                            evidence.get("source_artifacts"),
                            "analysis_chart_data_snapshot.csv",
                            "intelligence_metric_catalog.csv",
                        ]
                    )
                ),
                "source_artifacts": "analysis_section_evidence_review.csv|analysis_consulting_playbook.csv|analysis_chart_data_snapshot.csv|intelligence_metric_catalog.csv|analysis_requirement_matrix.csv",
                "model_version": "analysis_insight_brief_v0",
            }
        )

    if not rows:
        return _empty_analysis_insight_brief()
    status_order = {
        "client_ready": 0,
        "qualified_by_validation": 1,
        "qualified_by_layout_blockers": 2,
        "missing_chart_data": 3,
    }
    df = pd.DataFrame(rows, columns=_analysis_insight_brief_columns()).sort_values(
        by=["brief_status", "domain_name", "source_section_id"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "brief_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["brief_rank"] = range(1, len(df) + 1)
    return df


def build_client_meeting_deck_blueprint(
    consulting_story: dict[str, Any],
    executive_scorecard: pd.DataFrame,
    strategy_roadmap: pd.DataFrame,
    action_plan: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    analysis_insight_brief: pd.DataFrame,
    intelligence_metric_catalog: pd.DataFrame,
    stakeholder_export_manifest: pd.DataFrame,
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create an ordered CSM/client meeting blueprint from generated intelligence outputs."""
    cfg = config or EngineConfig()
    rows: list[dict[str, Any]] = []

    def add_row(
        *,
        meeting_phase: str,
        slide_type: str,
        slide_title: str,
        primary_message: str,
        decision_prompt: str,
        audience_role: str,
        owner_role: str,
        source_artifact: str,
        source_section_id: str = "",
        domain_name: str = "",
        visual_title: str = "",
        chart_type: str = "",
        chart_data_status: str = "",
        primary_metric_ids: str = "",
        metric_summary: str = "",
        data_caveat: str = "",
        talk_track: str = "",
        follow_up_action: str = "",
        activation_export: str = "",
        proof_artifacts: str = "",
    ) -> None:
        rows.append(
            {
                "blueprint_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "meeting_phase": meeting_phase,
                "slide_type": slide_type,
                "slide_title": _trace_text(slide_title),
                "primary_message": _trace_text(primary_message),
                "decision_prompt": _trace_text(decision_prompt),
                "audience_role": _trace_text(audience_role),
                "owner_role": _trace_text(owner_role),
                "source_section_id": _trace_text(source_section_id),
                "domain_name": _trace_text(domain_name),
                "source_artifact": _trace_text(source_artifact),
                "visual_title": _trace_text(visual_title),
                "chart_type": _trace_text(chart_type),
                "chart_data_status": _trace_text(chart_data_status),
                "primary_metric_ids": _trace_text(primary_metric_ids),
                "metric_summary": _trace_text(metric_summary),
                "data_caveat": _trace_text(data_caveat),
                "talk_track": _trace_text(talk_track),
                "follow_up_action": _trace_text(follow_up_action),
                "activation_export": _trace_text(activation_export),
                "blueprint_status": _meeting_blueprint_status(chart_data_status, data_caveat, data_quality),
                "proof_artifacts": _trace_text(proof_artifacts),
                "source_artifacts": "consulting_story.json|executive_scorecard.csv|strategy_roadmap.csv|action_plan.csv|measurement_plan.csv|analysis_insight_brief.csv|intelligence_metric_catalog.csv|stakeholder_export_manifest.csv",
                "model_version": "client_meeting_deck_blueprint_v0",
            }
        )

    story = consulting_story or {}
    add_row(
        meeting_phase="Opening",
        slide_type="executive_summary",
        slide_title="Transactional Intelligence Executive Summary",
        primary_message=_trace_text(story.get("executive_summary")) or _trace_text(story.get("headline")),
        decision_prompt="Align on the relationship opportunities, data caveats, and actions to prioritize this month.",
        audience_role="Executive / CSM",
        owner_role="CSM",
        source_artifact="consulting_story.json",
        data_caveat=_meeting_blueprint_quality_caveat(data_quality),
        talk_track=_trace_text(story.get("headline")),
        follow_up_action="Use the remaining blueprint rows to walk from proof to decision to activation.",
        proof_artifacts="consulting_story.json|data_quality.json",
    )

    for scorecard in _meeting_blueprint_records(executive_scorecard, ["rag_status", "domain"], limit=8):
        domain = _trace_text(scorecard.get("domain"))
        metric_display = _trace_text(scorecard.get("metric_display")) or _trace_text(scorecard.get("metric_value"))
        add_row(
            meeting_phase="Executive Scorecard",
            slide_type="scorecard",
            slide_title=f"Scorecard: {domain}",
            primary_message=f"{domain}: {metric_display} ({_trace_text(scorecard.get('rag_status'))}).",
            decision_prompt=_trace_text(scorecard.get("recommended_focus")) or "Which domain should receive executive focus first?",
            audience_role="Executive",
            owner_role="CSM",
            source_artifact="executive_scorecard.csv",
            domain_name=domain,
            metric_summary=_trace_text(scorecard.get("metric_name")),
            data_caveat=_meeting_blueprint_quality_caveat(data_quality),
            follow_up_action=_trace_text(scorecard.get("recommended_focus")),
            proof_artifacts="executive_scorecard.csv|consulting_story.json",
        )

    for brief in _meeting_blueprint_records(analysis_insight_brief, ["brief_status", "domain_name", "source_section_id"], limit=30):
        add_row(
            meeting_phase=_meeting_blueprint_analysis_phase(brief),
            slide_type="analysis_insight",
            slide_title=_trace_text(brief.get("display_name")) or _trace_text(brief.get("source_section_id")),
            primary_message=_trace_text(brief.get("headline_insight")),
            decision_prompt=_trace_text(brief.get("recommended_client_question")),
            audience_role="CSM / Analyst / Client sponsor",
            owner_role="CSM",
            source_artifact="analysis_insight_brief.csv",
            source_section_id=_trace_text(brief.get("source_section_id")),
            domain_name=_trace_text(brief.get("domain_name")),
            visual_title=_trace_text(brief.get("primary_chart_title")),
            chart_type=_trace_text(brief.get("primary_chart_type")),
            chart_data_status=_trace_text(brief.get("chart_data_status")),
            primary_metric_ids=_trace_text(brief.get("primary_metric_ids")),
            metric_summary=_trace_text(brief.get("primary_metrics")),
            data_caveat=_trace_text(brief.get("data_caveat")),
            talk_track=_trace_text(brief.get("csm_talk_track")),
            follow_up_action=_trace_text(brief.get("analyst_next_step")),
            proof_artifacts=_trace_text(brief.get("proof_artifacts")),
        )

    for action in _meeting_blueprint_records(action_plan, ["priority_rank"], limit=12):
        add_row(
            meeting_phase="Action Plan",
            slide_type="recommended_action",
            slide_title=f"Action: {_trace_text(action.get('play_name'))}",
            primary_message=_trace_text(action.get("objective")) or _trace_text(action.get("next_step")),
            decision_prompt=f"Approve owner, audience, and channel for {_trace_text(action.get('play_name'))}.",
            audience_role="CSM / Marketing / Banker",
            owner_role=_trace_text(action.get("owner_role")) or "CSM",
            source_artifact="action_plan.csv",
            primary_metric_ids=_trace_text(action.get("primary_metric")),
            metric_summary=f"{_safe_int_value(action.get('target_accounts'))} target account(s); expected value {_trace_text(action.get('expected_value'))}.",
            data_caveat=_trace_text(action.get("risk_or_dependency")),
            talk_track=_trace_text(action.get("talk_track")),
            follow_up_action=_trace_text(action.get("next_step")),
            activation_export=_trace_text(action.get("action_id")),
            proof_artifacts="action_plan.csv|campaign_targets.csv|measurement_plan.csv",
        )

    for roadmap in _meeting_blueprint_records(strategy_roadmap, ["priority_rank"], limit=8):
        add_row(
            meeting_phase="Roadmap",
            slide_type="roadmap",
            slide_title=f"{_trace_text(roadmap.get('phase'))}: {_trace_text(roadmap.get('initiative'))}",
            primary_message=_trace_text(roadmap.get("source_signal")) or _trace_text(roadmap.get("initiative_type")),
            decision_prompt=_trace_text(roadmap.get("decision_needed")) or "Confirm timing, owner, and proof metric for this roadmap item.",
            audience_role="Executive / CSM",
            owner_role=_trace_text(roadmap.get("owner_role")) or "CSM",
            source_artifact="strategy_roadmap.csv",
            metric_summary=_trace_text(roadmap.get("proof_metric")),
            follow_up_action=_trace_text(roadmap.get("next_step")),
            proof_artifacts="strategy_roadmap.csv|executive_scorecard.csv|action_plan.csv",
        )

    for measurement in _meeting_blueprint_records(measurement_plan, ["priority_rank", "play_name"], limit=12):
        add_row(
            meeting_phase="Measurement",
            slide_type="measurement_plan",
            slide_title=f"Measure: {_trace_text(measurement.get('play_name'))}",
            primary_message=_trace_text(measurement.get("success_definition")) or _trace_text(measurement.get("primary_metric")),
            decision_prompt="Confirm baseline, holdout, measurement window, and outcome owner.",
            audience_role="CSM / Analyst",
            owner_role=_trace_text(measurement.get("owner_role")) or "Analyst",
            source_artifact="measurement_plan.csv",
            primary_metric_ids=_trace_text(measurement.get("primary_metric")),
            metric_summary=_trace_text(measurement.get("measurement_windows")),
            follow_up_action=_trace_text(measurement.get("next_step")),
            activation_export=_trace_text(measurement.get("measurement_id")),
            proof_artifacts="measurement_plan.csv|measurement_baseline.csv|outcome_summary.csv",
        )

    for export in _meeting_blueprint_records(stakeholder_export_manifest, ["export_rank"], limit=8):
        add_row(
            meeting_phase="Handoff",
            slide_type="stakeholder_export",
            slide_title=f"Export: {_trace_text(export.get('primary_role'))}",
            primary_message=_trace_text(export.get("use_case")),
            decision_prompt=f"Confirm {_trace_text(export.get('primary_role'))} owns {_trace_text(export.get('file_name'))}.",
            audience_role=_trace_text(export.get("primary_role")),
            owner_role=_trace_text(export.get("primary_role")),
            source_artifact="stakeholder_export_manifest.csv",
            data_caveat=_trace_text(export.get("status")),
            follow_up_action=_trace_text(export.get("first_action")),
            activation_export=_trace_text(export.get("file_name")),
            proof_artifacts="stakeholder_export_manifest.csv|role_handoffs.csv",
        )

    if not rows:
        return _empty_client_meeting_deck_blueprint()
    return pd.DataFrame(rows, columns=_client_meeting_deck_blueprint_columns())


def build_analysis_review_board(
    analysis_section_catalog: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    analysis_visual_output_map: pd.DataFrame,
    analysis_chart_spec_catalog: pd.DataFrame,
    analysis_chart_data_snapshot: pd.DataFrame,
    intelligence_metric_catalog: pd.DataFrame,
    analysis_consulting_playbook: pd.DataFrame,
    analysis_insight_brief: pd.DataFrame,
    client_meeting_deck_blueprint: pd.DataFrame,
    analysis_requirement_matrix: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a one-row-per-section review surface for analysis, charts, and story use."""
    cfg = config or EngineConfig()
    section_records = _records_by_key(analysis_section_catalog, "source_section_id")
    execution_records = _records_by_key(analysis_execution_map, "source_section_id")
    requirement_records = _records_by_key(analysis_requirement_matrix, "source_section_id")
    playbook_records = _records_by_key(analysis_consulting_playbook, "source_section_id")
    brief_records = _records_by_key(analysis_insight_brief, "source_section_id")
    visual_groups = _records_grouped_by_key(analysis_visual_output_map, "source_section_id")
    chart_groups = _records_grouped_by_key(analysis_chart_spec_catalog, "source_section_id")
    snapshot_groups = _records_grouped_by_key(analysis_chart_data_snapshot, "source_section_id")
    meeting_groups = _records_grouped_by_key(client_meeting_deck_blueprint, "source_section_id")
    metric_groups = _analysis_board_metrics_by_section(intelligence_metric_catalog)

    section_ids = _analysis_board_section_ids(
        section_records,
        execution_records,
        requirement_records,
        playbook_records,
        brief_records,
        visual_groups,
        chart_groups,
        snapshot_groups,
        meeting_groups,
        metric_groups,
    )
    if not section_ids:
        return _empty_analysis_review_board()

    rows: list[dict[str, Any]] = []
    for section_id in section_ids:
        section = section_records.get(section_id, {})
        execution = execution_records.get(section_id, {})
        requirement = requirement_records.get(section_id, {})
        playbook = playbook_records.get(section_id, {})
        brief = brief_records.get(section_id, {})
        visuals = visual_groups.get(section_id, [])
        charts = chart_groups.get(section_id, [])
        snapshots = snapshot_groups.get(section_id, [])
        metrics = metric_groups.get(section_id, [])
        meeting_rows = meeting_groups.get(section_id, [])
        chart_statuses = _unique_tokens([row.get("chart_readiness_status") for row in [*charts, *snapshots, *visuals]])
        data_statuses = _unique_tokens([row.get("data_status") for row in snapshots])
        validation_statuses = _unique_tokens([row.get("validation_status") for row in metrics])
        output_files = _unique_tokens([
            requirement.get("generated_output_files"),
            playbook.get("generated_output_files"),
            execution.get("available_engine_outputs"),
            *[row.get("output_file") for row in visuals],
            *[row.get("output_file") for row in charts],
        ])
        target_tables = _unique_tokens([
            playbook.get("generated_target_tables"),
            *[row.get("target_table") for row in visuals],
            *[row.get("target_table") for row in charts],
            *[row.get("target_table") for row in snapshots],
        ])
        chart_titles = _unique_tokens([row.get("chart_title") for row in [*charts, *snapshots]])
        chart_types = _unique_tokens([row.get("chart_type") for row in [*charts, *snapshots]])
        meeting_titles = _unique_tokens([row.get("slide_title") for row in meeting_rows])
        meeting_phases = _unique_tokens([row.get("meeting_phase") for row in meeting_rows])
        first_meeting_rank = min(
            [_safe_int_value(row.get("blueprint_rank"), default=0) for row in meeting_rows if _safe_int_value(row.get("blueprint_rank"), default=0)],
            default=0,
        )
        row = {
            "review_rank": len(rows) + 1,
            "client_id": cfg.client_id,
            "period_month": _period_label(cfg.period_month),
            "source_section_id": section_id,
            "product": _first_nonempty([section.get("product"), requirement.get("product"), execution.get("product")]),
            "display_name": _first_nonempty([section.get("display_name"), brief.get("display_name"), playbook.get("display_name")]),
            "domain_name": _first_nonempty([brief.get("domain_name"), playbook.get("domain_name"), requirement.get("domain_name")]),
            "analysis_family": _first_nonempty([section.get("analysis_family"), brief.get("analysis_family"), playbook.get("analysis_family")]),
            "intelligence_layers": _first_nonempty([section.get("intelligence_layers"), execution.get("intelligence_layers")]),
            "what_is_analyzed": _first_nonempty([brief.get("what_is_analyzed"), playbook.get("primary_business_claim"), section.get("consulting_use")]),
            "business_question": _first_nonempty([brief.get("business_question"), playbook.get("business_question"), requirement.get("business_question")]),
            "consulting_question": _first_nonempty([brief.get("consulting_question"), playbook.get("consulting_question"), requirement.get("consulting_question")]),
            "client_story_role": _trace_text(playbook.get("client_story_role")),
            "section_review_status": _first_nonempty([brief.get("section_review_status"), playbook.get("section_review_status"), execution.get("evidence_status")]),
            "output_readiness_status": _first_nonempty([brief.get("output_readiness_status"), playbook.get("output_readiness_status"), requirement.get("current_layout_readiness")]),
            "input_readiness": _first_nonempty([execution.get("input_readiness"), requirement.get("current_layout_readiness")]),
            "script_count": _safe_int_value(_first_nonempty([requirement.get("script_count"), section.get("script_count"), execution.get("discovered_script_count")])),
            "runnable_script_count": _safe_int_value(_first_nonempty([requirement.get("runnable_script_count"), section.get("runnable_script_count"), execution.get("runnable_script_count")])),
            "representative_scripts": _first_nonempty([requirement.get("representative_scripts"), execution.get("representative_scripts"), section.get("script_files")]),
            "required_input_families": _first_nonempty([requirement.get("required_input_families"), execution.get("required_input_families")]),
            "primary_engine_outputs": _first_nonempty([section.get("primary_engine_outputs"), execution.get("primary_engine_outputs")]),
            "available_engine_outputs": _trace_text(execution.get("available_engine_outputs")),
            "missing_engine_outputs": _first_nonempty([requirement.get("missing_engine_outputs"), execution.get("missing_engine_outputs")]),
            "generated_output_files": "|".join(output_files),
            "snowflake_targets": "|".join(target_tables),
            "visual_count": len(visuals),
            "chart_count": len(charts),
            "data_snapshot_count": len(snapshots),
            "data_ready_chart_count": sum(1 for row in snapshots if _trace_text(row.get("data_status")) == "data_ready"),
            "chart_types": "|".join(chart_types),
            "chart_titles": "|".join(chart_titles),
            "chart_readiness_statuses": "|".join(chart_statuses),
            "chart_data_statuses": "|".join(data_statuses),
            "primary_output_file": _first_nonempty([brief.get("primary_output_file"), playbook.get("primary_output_file"), output_files[0] if output_files else ""]),
            "primary_chart_title": _first_nonempty([brief.get("primary_chart_title"), playbook.get("primary_chart_title"), chart_titles[0] if chart_titles else ""]),
            "primary_chart_type": _first_nonempty([brief.get("primary_chart_type"), playbook.get("primary_chart_type"), chart_types[0] if chart_types else ""]),
            "metric_count": len(metrics),
            "primary_metric_ids": _first_nonempty([brief.get("primary_metric_ids"), "|".join(_unique_tokens([row.get("metric_id") for row in metrics])[:8])]),
            "primary_metrics": _first_nonempty([brief.get("primary_metrics"), "|".join(_unique_tokens([row.get("metric_name") for row in metrics])[:8])]),
            "metric_validation_statuses": "|".join(validation_statuses),
            "headline_insight": _trace_text(brief.get("headline_insight")),
            "primary_evidence": _trace_text(brief.get("primary_evidence")),
            "data_caveat": _trace_text(brief.get("data_caveat")),
            "recommended_client_question": _first_nonempty([brief.get("recommended_client_question"), requirement.get("csm_review_question")]),
            "meeting_phase_refs": "|".join(meeting_phases),
            "meeting_slide_count": len(meeting_rows),
            "first_meeting_rank": first_meeting_rank,
            "meeting_titles": "|".join(meeting_titles),
            "csm_talk_track": _first_nonempty([brief.get("csm_talk_track"), playbook.get("csm_talk_track")]),
            "analyst_next_step": _first_nonempty([brief.get("analyst_next_step"), playbook.get("analyst_validation_focus"), requirement.get("analyst_next_step")]),
            "data_team_next_step": _first_nonempty([brief.get("data_team_next_step"), playbook.get("data_team_dependency"), requirement.get("data_team_question")]),
            "marketing_activation_use": _first_nonempty([brief.get("marketing_activation_use"), playbook.get("marketing_activation_use")]),
            "snowflake_design_action": _first_nonempty([playbook.get("snowflake_design_action"), requirement.get("snowflake_design_action")]),
            "proof_artifacts": _analysis_board_proof_artifacts(brief, playbook, visuals, charts, snapshots, meeting_rows),
            "source_artifacts": _analysis_board_source_artifacts(section, execution, requirement, brief, playbook, meeting_rows),
            "review_status": "",
            "model_version": "analysis_review_board_v0",
        }
        row["review_status"] = _analysis_board_review_status(row)
        rows.append(row)

    status_order = {
        "blocked_by_layout": 1,
        "needs_metric_validation": 2,
        "qualified_with_caveat": 3,
        "client_story_ready": 4,
        "inventory_only": 5,
    }
    df = pd.DataFrame(rows, columns=_analysis_review_board_columns()).sort_values(
        by=["review_status", "domain_name", "source_section_id"],
        key=lambda col: col.map(status_order).fillna(9) if col.name == "review_status" else col,
        na_position="last",
    ).reset_index(drop=True)
    df["review_rank"] = range(1, len(df) + 1)
    return df


def build_account_intelligence_profile(
    features: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    relationship_segments: pd.DataFrame,
    counterparty_signals: pd.DataFrame,
    opportunities: pd.DataFrame,
    campaign_targets: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create the account-level diagnosis view used by CSMs and analysts."""
    cfg = config or EngineConfig()
    if features is None or features.empty:
        return _empty_account_intelligence_profile()

    base_cols = [
        "account_id",
        "period_month",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "balance",
        "has_debit",
        "branch",
        "product_code",
        "product_count",
        "external_intensity",
        "payroll_detected",
        "engagement_tier",
    ]
    profile = features[[col for col in base_cols if col in features.columns]].copy()

    if pfi_verdicts is not None and not pfi_verdicts.empty:
        pfi_cols = ["account_id", "period_month", "pfi_verdict", "pfi_score", "confidence", "reason_codes"]
        profile = profile.merge(
            pfi_verdicts[[col for col in pfi_cols if col in pfi_verdicts.columns]],
            on=["account_id", "period_month"],
            how="left",
        )

    if relationship_segments is not None and not relationship_segments.empty:
        segment_cols = [
            "account_id",
            "period_month",
            "relationship_segment",
            "segment_group",
            "lifecycle_stage",
            "risk_level",
            "opportunity_readiness_score",
            "next_best_motion",
            "segment_reason_codes",
        ]
        profile = profile.merge(
            relationship_segments[[col for col in segment_cols if col in relationship_segments.columns]],
            on=["account_id", "period_month"],
            how="left",
        )

    opportunity_rollup = _account_opportunity_rollup(opportunities)
    if not opportunity_rollup.empty:
        profile = profile.merge(opportunity_rollup, on=["account_id", "period_month"], how="left")

    counterparty_rollup = _account_counterparty_rollup(counterparty_signals)
    if not counterparty_rollup.empty:
        profile = profile.merge(counterparty_rollup, on=["account_id", "period_month"], how="left")

    target_rollup = _account_target_rollup(campaign_targets)
    if not target_rollup.empty:
        profile = profile.merge(target_rollup, on=["account_id", "period_month"], how="left")

    defaults: dict[str, Any] = {
        "pfi_verdict": "No verdict",
        "pfi_score": 0.0,
        "confidence": "low",
        "reason_codes": "",
        "relationship_segment": "Unclassified",
        "segment_group": "Review",
        "lifecycle_stage": "",
        "risk_level": "unknown",
        "opportunity_readiness_score": 0.0,
        "next_best_motion": "Review relationship manually.",
        "segment_reason_codes": "",
        "top_opportunity_type": "",
        "top_play_name": "",
        "top_priority_score": 0.0,
        "top_expected_value": 0.0,
        "opportunity_count": 0,
        "total_expected_value": 0.0,
        "recommended_action": "",
        "opportunity_reason_codes": "",
        "top_counterparties": "",
        "payroll_counterparties": "",
        "external_fi_counterparties": "",
        "financial_services_counterparties": "",
        "target_status": "",
        "measurement_group": "",
        "owner_role": "",
        "recommended_channel": "",
        "action_id": "",
        "measurement_id": "",
    }
    for col, default in defaults.items():
        if col not in profile.columns:
            profile[col] = default
        profile[col] = profile[col].fillna(default)

    numeric_cols = [
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "balance",
        "product_count",
        "external_intensity",
        "pfi_score",
        "opportunity_readiness_score",
        "top_priority_score",
        "top_expected_value",
        "opportunity_count",
        "total_expected_value",
    ]
    for col in numeric_cols:
        if col in profile.columns:
            profile[col] = pd.to_numeric(profile[col], errors="coerce").fillna(0.0)

    rows: list[dict[str, Any]] = []
    for row in profile.to_dict("records"):
        rows.append(
            {
                "profile_id": f"{cfg.client_id}:{row.get('period_month', '')}:{row.get('account_id', '')}",
                "client_id": cfg.client_id,
                "account_id": row.get("account_id", ""),
                "period_month": row.get("period_month", ""),
                "relationship_segment": row.get("relationship_segment", ""),
                "segment_group": row.get("segment_group", ""),
                "lifecycle_stage": row.get("lifecycle_stage", ""),
                "risk_level": row.get("risk_level", ""),
                "pfi_verdict": row.get("pfi_verdict", "No verdict"),
                "pfi_score": round(float(row.get("pfi_score", 0) or 0), 1),
                "confidence": row.get("confidence", "low"),
                "engagement_tier": row.get("engagement_tier", ""),
                "balance": round(float(row.get("balance", 0) or 0), 2),
                "txn_count": int(float(row.get("txn_count", 0) or 0)),
                "active_days": int(float(row.get("active_days", 0) or 0)),
                "payroll_detected": bool(row.get("payroll_detected", False)),
                "payroll_amount": round(float(row.get("payroll_amount", 0) or 0), 2),
                "external_fi_count": int(float(row.get("external_fi_count", 0) or 0)),
                "external_fi_amount": round(float(row.get("external_fi_amount", 0) or 0), 2),
                "external_intensity": round(float(row.get("external_intensity", 0) or 0), 3),
                "product_count": int(float(row.get("product_count", 0) or 0)),
                "has_debit": bool(row.get("has_debit", False)),
                "branch": row.get("branch", ""),
                "product_code": row.get("product_code", ""),
                "top_counterparties": row.get("top_counterparties", ""),
                "payroll_counterparties": row.get("payroll_counterparties", ""),
                "external_fi_counterparties": row.get("external_fi_counterparties", ""),
                "financial_services_counterparties": row.get("financial_services_counterparties", ""),
                "top_opportunity_type": row.get("top_opportunity_type", ""),
                "top_play_name": row.get("top_play_name", ""),
                "top_priority_score": round(float(row.get("top_priority_score", 0) or 0), 1),
                "top_expected_value": round(float(row.get("top_expected_value", 0) or 0), 2),
                "opportunity_count": int(float(row.get("opportunity_count", 0) or 0)),
                "total_expected_value": round(float(row.get("total_expected_value", 0) or 0), 2),
                "target_status": row.get("target_status", ""),
                "measurement_group": row.get("measurement_group", ""),
                "owner_role": row.get("owner_role", ""),
                "recommended_channel": row.get("recommended_channel", ""),
                "recommended_action": row.get("recommended_action", "") or row.get("next_best_motion", ""),
                "next_best_motion": row.get("next_best_motion", ""),
                "action_id": row.get("action_id", ""),
                "measurement_id": row.get("measurement_id", ""),
                "evidence_summary": _account_profile_evidence(row),
                "reason_codes": _join_unique_tokens(
                    row.get("reason_codes", ""),
                    row.get("segment_reason_codes", ""),
                    row.get("opportunity_reason_codes", ""),
                ),
                "source_artifacts": (
                    "account_month_features.csv|pfi_verdicts.csv|relationship_segments.csv|"
                    "counterparty_signals.csv|opportunities.csv|campaign_targets.csv"
                ),
                "model_version": "account_intelligence_profile_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=_account_intelligence_profile_columns()).sort_values(
        ["top_priority_score", "total_expected_value", "account_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def build_model_rulebook(config: EngineConfig | None = None) -> pd.DataFrame:
    """Create the analyst-facing catalog of scoring rules, thresholds, and outputs."""
    cfg = config or EngineConfig()
    rows: list[dict[str, Any]] = []

    def add(
        *,
        rule_id: str,
        rule_family: str,
        rule_name: str,
        applies_to: str,
        condition: str,
        thresholds: str,
        outputs: str,
        evidence_fields: str,
        source_artifacts: str,
        owner_role: str,
        consulting_use: str,
        model_version: str,
    ) -> None:
        rows.append(
            {
                "rule_id": rule_id,
                "rule_family": rule_family,
                "rule_name": rule_name,
                "applies_to": applies_to,
                "condition": condition,
                "thresholds": thresholds,
                "outputs": outputs,
                "evidence_fields": evidence_fields,
                "source_artifacts": source_artifacts,
                "owner_role": owner_role,
                "consulting_use": consulting_use,
                "model_version": model_version,
            }
        )

    add(
        rule_id="pfi.score_components",
        rule_family="PFI",
        rule_name="PFI Component Scores",
        applies_to="account_month_features",
        condition="Always calculated for every account-month feature row.",
        thresholds=(
            "payroll_score uses payroll_count > 0 and payroll_amount / payroll_min_amount; "
            "activity_score uses txn_count / strong_txn_threshold; balance_score uses balance / high_balance_threshold; "
            "depth_score uses product_count / 3; external_score uses external FI count and amount."
        ),
        outputs="internal_score|external_score|pfi_score|confidence_score",
        evidence_fields="txn_count|payroll_count|payroll_amount|balance|product_count|external_fi_count|external_fi_amount|matched_account",
        source_artifacts="account_month_features.csv",
        owner_role="Data science",
        consulting_use="Shows whether the relationship appears anchored internally or pulled by outside institutions.",
        model_version="pfi_v0_rules",
    )
    add(
        rule_id="pfi.primary_with_us",
        rule_family="PFI",
        rule_name="Primary With Us Verdict",
        applies_to="pfi_verdicts",
        condition="internal_score >= 0.60 and external_score < 0.35",
        thresholds="internal_score>=0.60|external_score<0.35",
        outputs="pfi_verdict=Primary with us",
        evidence_fields="internal_score|external_score|payroll_count|txn_count|balance|product_count",
        source_artifacts="account_month_features.csv|pfi_verdicts.csv",
        owner_role="CSM",
        consulting_use="Protect payroll-primary households and monitor for external pull.",
        model_version="pfi_v0_rules",
    )
    add(
        rule_id="pfi.competitor_primary",
        rule_family="PFI",
        rule_name="Competitor-Primary Verdict",
        applies_to="pfi_verdicts",
        condition="external_score >= 0.55 and internal_score < 0.45",
        thresholds="external_score>=0.55|internal_score<0.45",
        outputs="pfi_verdict=Competitor-primary",
        evidence_fields="internal_score|external_score|external_fi_count|external_fi_amount|txn_count",
        source_artifacts="account_month_features.csv|pfi_verdicts.csv",
        owner_role="CSM",
        consulting_use="Prioritize consolidation, win-back, or save-list strategy.",
        model_version="pfi_v0_rules",
    )
    add(
        rule_id="pfi.split",
        rule_family="PFI",
        rule_name="Split Relationship Verdict",
        applies_to="pfi_verdicts",
        condition="internal_score >= 0.45 and external_score >= 0.25, or external_score >= 0.35",
        thresholds="internal_score>=0.45 and external_score>=0.25|external_score>=0.35",
        outputs="pfi_verdict=Split",
        evidence_fields="internal_score|external_score|external_fi_count|external_fi_amount|payroll_count",
        source_artifacts="account_month_features.csv|pfi_verdicts.csv",
        owner_role="CSM",
        consulting_use="Identify split-wallet relationships with defendable growth or retention potential.",
        model_version="pfi_v0_rules",
    )
    add(
        rule_id="pfi.confidence",
        rule_family="PFI",
        rule_name="PFI Confidence Label",
        applies_to="pfi_verdicts",
        condition="confidence_score buckets based on account match, transaction count, payroll, external FI, and product depth evidence.",
        thresholds="high>=0.75|medium>=0.45|low<0.45",
        outputs="confidence=high|medium|low",
        evidence_fields="matched_account|txn_count|payroll_count|external_fi_count|product_count",
        source_artifacts="account_month_features.csv|pfi_verdicts.csv",
        owner_role="Analyst",
        consulting_use="Separates presentation-ready findings from rows requiring analyst validation.",
        model_version="pfi_v0_rules",
    )
    add(
        rule_id="opportunity.priority_score",
        rule_family="Opportunity",
        rule_name="Opportunity Priority Score",
        applies_to="opportunities",
        condition="Every created opportunity is scored as 100 * impact_score * addressability_score * confidence_score * urgency_score.",
        thresholds="addressability=0.95 when account matched else 0.65; branch evidence adds up to 0.05; priority_score must be > 0",
        outputs="priority_score|expected_value|impact_score|addressability_score|confidence_score|urgency_score",
        evidence_fields="expected_value|matched_account|branch|confidence_score|opportunity_type",
        source_artifacts="account_month_features.csv|pfi_verdicts.csv|opportunities.csv",
        owner_role="Data science",
        consulting_use="Ranks which account-level opportunities should be acted on first.",
        model_version="opportunity_v0_rules",
    )

    opportunity_conditions = {
        "payroll_conversion": (
            f"payroll_count == 0 and (external_fi_count > 0 or credit_amount >= {cfg.payroll_min_amount:g})",
            f"payroll_min_amount={cfg.payroll_min_amount:g}",
            "payroll_count|credit_amount|external_fi_count|external_fi_amount",
        ),
        "debit_activation": (
            f"(has_debit is false or spend_amount < 250) and txn_count <= {cfg.active_txn_threshold}",
            f"active_txn_threshold={cfg.active_txn_threshold}|spend_amount<250",
            "has_debit|spend_amount|txn_count|credit_amount",
        ),
        "deposit_retention": (
            f"balance >= {cfg.high_balance_threshold:g} and external_fi_amount >= {cfg.external_fi_amount_threshold:g}",
            f"high_balance_threshold={cfg.high_balance_threshold:g}|external_fi_amount_threshold={cfg.external_fi_amount_threshold:g}",
            "balance|external_fi_amount|external_fi_count",
        ),
        "competitor_winback": (
            "external_fi_count >= 2 or pfi_verdict in Split, Competitor-primary",
            "external_fi_count>=2|pfi_verdict in Split or Competitor-primary",
            "external_fi_count|external_fi_amount|pfi_verdict",
        ),
        "dormant_reactivation": (
            f"txn_count <= {cfg.low_activity_txn_threshold} and (balance > 100 or product_count > 0)",
            f"low_activity_txn_threshold={cfg.low_activity_txn_threshold}|balance>100|product_count>0",
            "txn_count|balance|product_count",
        ),
        "relationship_expansion": (
            "product_count <= 1 and (financial_services_count > 0 or external_fi_count > 0)",
            "product_count<=1|financial_services_count>0|external_fi_count>0",
            "product_count|financial_services_count|external_fi_count|external_fi_amount",
        ),
        "attrition_prevention": (
            f"pfi_verdict in Split, Competitor-primary and txn_count <= {cfg.active_txn_threshold}",
            f"active_txn_threshold={cfg.active_txn_threshold}|pfi_verdict in Split or Competitor-primary",
            "pfi_verdict|txn_count|balance|external_fi_amount",
        ),
    }
    for opportunity_type, playbook in OPPORTUNITY_PLAYBOOK.items():
        condition, thresholds, fields = opportunity_conditions.get(
            opportunity_type,
            ("Configured opportunity rule.", "Configured thresholds.", "account_month_features"),
        )
        add(
            rule_id=f"opportunity.{opportunity_type}",
            rule_family="Opportunity",
            rule_name=playbook.get("play_name", opportunity_type.replace("_", " ").title()),
            applies_to="opportunities|campaign_targets|action_plan",
            condition=condition,
            thresholds=thresholds,
            outputs=f"opportunity_type={opportunity_type}|play_name={playbook.get('play_name', '')}|primary_metric={playbook.get('primary_metric', '')}",
            evidence_fields=fields,
            source_artifacts="account_month_features.csv|pfi_verdicts.csv|opportunities.csv",
            owner_role=playbook.get("owner_role", "CSM"),
            consulting_use=playbook.get("next_step", "Review ranked accounts for action."),
            model_version="opportunity_v0_rules",
        )

    segment_rules = [
        (
            "relationship.primary_payroll",
            "Primary Payroll Relationship",
            "pfi_verdict == Primary with us and payroll_detected is true",
            "pfi_verdict=Primary with us|payroll_detected=true",
            "segment_group=Retain|risk_level=low",
            "pfi_verdict|payroll_detected|payroll_amount",
            "Protect payroll relationship and deepen product usage.",
        ),
        (
            "relationship.split_wallet",
            "Split Wallet / Competitor Pull",
            "pfi_verdict in Split, Competitor-primary and external_intensity >= 0.30",
            "external_intensity>=0.30|pfi_verdict in Split or Competitor-primary",
            "segment_group=Win Back|risk_level=high_or_medium",
            "pfi_verdict|external_intensity|external_fi_amount",
            "Prioritize consolidation or retention outreach.",
        ),
        (
            "relationship.primary_conversion",
            "Primary Banking Conversion Candidate",
            f"top_opportunity_type == payroll_conversion or no payroll with money movement >= {cfg.payroll_min_amount:g}",
            f"payroll_min_amount={cfg.payroll_min_amount:g}|external_fi_count>0",
            "segment_group=Grow|risk_level=medium",
            "top_opportunity_type|payroll_detected|external_fi_count|credit_amount",
            "Target for direct deposit or primary banking conversion.",
        ),
        (
            "relationship.external_financial_services",
            "External Lending / Financial Services Relationship",
            "financial_services_count > 0 and product_count <= 1",
            "financial_services_count>0|product_count<=1",
            "segment_group=Expand|risk_level=medium",
            "financial_services_count|product_count|external_fi_count",
            "Review for lending or relationship expansion offer.",
        ),
        (
            "relationship.dormant_save",
            "Dormant Save Candidate",
            f"txn_count <= {cfg.low_activity_txn_threshold} and relationship value is present",
            f"low_activity_txn_threshold={cfg.low_activity_txn_threshold}|balance>100 or product_count>0",
            "segment_group=Reactivate|risk_level=high",
            "txn_count|balance|product_count",
            "Queue for reactivation or save-list outreach.",
        ),
        (
            "relationship.engagement_activation",
            "Engagement Activation Candidate",
            f"(has_debit is false or txn_count <= {cfg.active_txn_threshold}) and balance >= 0",
            f"active_txn_threshold={cfg.active_txn_threshold}",
            "segment_group=Activate|risk_level=medium",
            "has_debit|txn_count|balance",
            "Prompt debit, wallet, or digital engagement.",
        ),
        (
            "relationship.engaged_core",
            "Engaged Core Relationship",
            "pfi_verdict == Primary with us after higher-priority segment rules are checked",
            "pfi_verdict=Primary with us",
            "segment_group=Retain|risk_level=low",
            "pfi_verdict|txn_count|payroll_detected",
            "Maintain relationship and monitor for expansion signals.",
        ),
        (
            "relationship.low_signal",
            "Low Signal / Monitor",
            "Fallback when no stronger segment rule is met",
            "No higher-priority segment rule met",
            "segment_group=Monitor|risk_level=unknown",
            "txn_count|payroll_detected|external_fi_count|balance|product_count",
            "Monitor until stronger behavior appears or add more data.",
        ),
    ]
    for rule_id, name, condition, thresholds, outputs, fields, consulting_use in segment_rules:
        add(
            rule_id=rule_id,
            rule_family="Relationship Segment",
            rule_name=name,
            applies_to="relationship_segments|account_intelligence_profile",
            condition=condition,
            thresholds=thresholds,
            outputs=outputs,
            evidence_fields=fields,
            source_artifacts="account_month_features.csv|pfi_verdicts.csv|opportunities.csv|relationship_segments.csv",
            owner_role="Consultant",
            consulting_use=consulting_use,
            model_version="relationship_segment_v0_rules",
        )

    add(
        rule_id="relationship.readiness_score",
        rule_family="Relationship Segment",
        rule_name="Opportunity Readiness Score",
        applies_to="relationship_segments",
        condition="Calculated for every segment row using top priority, confidence, and expected value.",
        thresholds="readiness_score=min(top_priority_score + confidence_score*20 + min(total_expected_value/500,20),100)",
        outputs="opportunity_readiness_score",
        evidence_fields="top_priority_score|confidence_score|total_expected_value",
        source_artifacts="relationship_segments.csv|opportunities.csv",
        owner_role="Consultant",
        consulting_use="Identifies which segments are ready for immediate action versus observation.",
        model_version="relationship_segment_v0_rules",
    )

    add(
        rule_id="execution.stakeholder_exports",
        rule_family="Execution",
        rule_name="Stakeholder Export Creation",
        applies_to="csm_review_queue|analyst_validation_queue|marketing_activation_export|banker_call_list|data_team_load_plan",
        condition="Generated from account profile, campaign targets, action plan, file assembly, layout gaps, and data-quality warnings.",
        thresholds="CSM and banker queues prioritize top_priority_score and value; analyst queue includes warnings and low-confidence/high-priority rows.",
        outputs="role-specific CSV exports",
        evidence_fields="top_priority_score|risk_level|confidence|target_status|layout_gap_actions|quality_warnings",
        source_artifacts="account_intelligence_profile.csv|campaign_targets.csv|action_plan.csv|file_assembly_plan.csv|layout_gap_report.csv|data_quality.json",
        owner_role="CSM",
        consulting_use="Turns the analysis into work queues for the CSM, analyst, marketing team, banker team, and data team.",
        model_version="stakeholder_export_v0_rules",
    )

    return pd.DataFrame(rows, columns=_model_rulebook_columns())


def build_account_scoring_trace(
    features: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    relationship_segments: pd.DataFrame,
    account_intelligence_profile: pd.DataFrame,
    opportunities: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create one explainability row per account-month scoring decision."""
    cfg = config or EngineConfig()
    if features is None or features.empty:
        return _empty_account_scoring_trace()

    base_cols = [
        "account_id",
        "period_month",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "external_intensity",
        "financial_services_count",
        "balance",
        "product_count",
        "has_debit",
        "payroll_detected",
        "engagement_tier",
        "branch",
        "product_code",
    ]
    trace = features[[col for col in base_cols if col in features.columns]].copy()
    for key in ["account_id", "period_month"]:
        if key not in trace.columns:
            trace[key] = ""

    if pfi_verdicts is not None and not pfi_verdicts.empty:
        pfi_cols = [
            "account_id",
            "period_month",
            "pfi_verdict",
            "pfi_score",
            "internal_score",
            "external_score",
            "confidence",
            "confidence_score",
            "reason_codes",
        ]
        pfi = pfi_verdicts[[col for col in pfi_cols if col in pfi_verdicts.columns]].copy()
        if "reason_codes" in pfi.columns:
            pfi = pfi.rename(columns={"reason_codes": "pfi_reason_codes"})
        trace = trace.merge(pfi, on=["account_id", "period_month"], how="left")

    if relationship_segments is not None and not relationship_segments.empty:
        segment_cols = [
            "account_id",
            "period_month",
            "relationship_segment",
            "segment_group",
            "lifecycle_stage",
            "risk_level",
            "opportunity_readiness_score",
            "segment_reason_codes",
        ]
        trace = trace.merge(
            relationship_segments[[col for col in segment_cols if col in relationship_segments.columns]],
            on=["account_id", "period_month"],
            how="left",
        )

    opportunity_rollup = _account_scoring_opportunity_rollup(opportunities)
    if not opportunity_rollup.empty:
        trace = trace.merge(opportunity_rollup, on=["account_id", "period_month"], how="left")

    if account_intelligence_profile is not None and not account_intelligence_profile.empty:
        profile_cols = [
            "profile_id",
            "account_id",
            "period_month",
            "target_status",
            "measurement_group",
            "owner_role",
            "recommended_channel",
            "recommended_action",
            "next_best_motion",
            "evidence_summary",
        ]
        trace = trace.merge(
            account_intelligence_profile[[col for col in profile_cols if col in account_intelligence_profile.columns]],
            on=["account_id", "period_month"],
            how="left",
        )

    defaults: dict[str, Any] = {
        "profile_id": "",
        "pfi_verdict": "No verdict",
        "pfi_score": 0.0,
        "internal_score": 0.0,
        "external_score": 0.0,
        "confidence": "low",
        "confidence_score": 0.0,
        "pfi_reason_codes": "",
        "relationship_segment": "Unclassified",
        "segment_group": "Review",
        "lifecycle_stage": "",
        "risk_level": "unknown",
        "opportunity_readiness_score": 0.0,
        "segment_reason_codes": "",
        "top_opportunity_type": "",
        "top_play_name": "",
        "top_priority_score": 0.0,
        "top_expected_value": 0.0,
        "opportunity_count": 0,
        "total_expected_value": 0.0,
        "opportunity_reason_codes": "",
        "all_opportunity_types": "",
        "top_opportunity_source_sections": "",
        "target_status": "",
        "measurement_group": "",
        "owner_role": "",
        "recommended_channel": "",
        "recommended_action": "",
        "top_recommended_action": "",
        "next_best_motion": "",
        "evidence_summary": "",
        "branch": "",
        "product_code": "",
        "engagement_tier": "",
        "has_debit": False,
        "payroll_detected": False,
    }
    for col, default in defaults.items():
        if col not in trace.columns:
            trace[col] = default
        trace[col] = trace[col].fillna(default)

    numeric_cols = [
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "external_intensity",
        "financial_services_count",
        "balance",
        "product_count",
        "pfi_score",
        "internal_score",
        "external_score",
        "confidence_score",
        "opportunity_readiness_score",
        "top_priority_score",
        "top_expected_value",
        "opportunity_count",
        "total_expected_value",
    ]
    for col in numeric_cols:
        if col not in trace.columns:
            trace[col] = 0.0
        trace[col] = pd.to_numeric(trace[col], errors="coerce").fillna(0.0)

    pfi_thresholds = (
        "Primary with us: internal_score>=0.60 and external_score<0.35; "
        "Competitor-primary: external_score>=0.55 and internal_score<0.45; "
        "Split: internal_score>=0.45 and external_score>=0.25, or external_score>=0.35"
    )
    rows: list[dict[str, Any]] = []
    for row in trace.to_dict("records"):
        account_id = _trace_text(row.get("account_id"))
        period_month = _trace_text(row.get("period_month"))
        top_opportunity_type = _trace_text(row.get("top_opportunity_type"))
        recommended_action = (
            _trace_text(row.get("recommended_action"))
            or _trace_text(row.get("top_recommended_action"))
            or _trace_text(row.get("next_best_motion"))
        )
        segment_reason_codes = _trace_text(row.get("segment_reason_codes"))
        opportunity_reason_codes = _trace_text(row.get("opportunity_reason_codes"))
        rows.append(
            {
                "trace_id": f"{cfg.client_id}:{period_month}:{account_id}:trace",
                "client_id": cfg.client_id,
                "account_id": account_id,
                "period_month": period_month,
                "profile_id": _trace_text(row.get("profile_id")),
                "pfi_verdict": _trace_text(row.get("pfi_verdict")) or "No verdict",
                "pfi_score": round(float(row.get("pfi_score", 0) or 0), 1),
                "internal_score": round(float(row.get("internal_score", 0) or 0), 3),
                "external_score": round(float(row.get("external_score", 0) or 0), 3),
                "confidence": _trace_text(row.get("confidence")) or "low",
                "confidence_score": round(float(row.get("confidence_score", 0) or 0), 3),
                "pfi_reason_codes": _trace_text(row.get("pfi_reason_codes")),
                "pfi_thresholds": pfi_thresholds,
                "relationship_segment": _trace_text(row.get("relationship_segment")) or "Unclassified",
                "segment_group": _trace_text(row.get("segment_group")) or "Review",
                "lifecycle_stage": _trace_text(row.get("lifecycle_stage")),
                "risk_level": _trace_text(row.get("risk_level")) or "unknown",
                "opportunity_readiness_score": round(float(row.get("opportunity_readiness_score", 0) or 0), 1),
                "segment_reason_codes": segment_reason_codes,
                "segment_rule": _segment_trace_rule(segment_reason_codes),
                "top_opportunity_type": top_opportunity_type,
                "top_play_name": _trace_text(row.get("top_play_name")),
                "top_priority_score": round(float(row.get("top_priority_score", 0) or 0), 1),
                "top_expected_value": round(float(row.get("top_expected_value", 0) or 0), 2),
                "opportunity_count": int(float(row.get("opportunity_count", 0) or 0)),
                "total_expected_value": round(float(row.get("total_expected_value", 0) or 0), 2),
                "opportunity_reason_codes": opportunity_reason_codes,
                "opportunity_rule": _opportunity_trace_rule(top_opportunity_type, cfg),
                "all_opportunity_types": _trace_text(row.get("all_opportunity_types")),
                "txn_count": int(float(row.get("txn_count", 0) or 0)),
                "active_days": int(float(row.get("active_days", 0) or 0)),
                "spend_amount": round(float(row.get("spend_amount", 0) or 0), 2),
                "credit_amount": round(float(row.get("credit_amount", 0) or 0), 2),
                "payroll_count": int(float(row.get("payroll_count", 0) or 0)),
                "payroll_amount": round(float(row.get("payroll_amount", 0) or 0), 2),
                "external_fi_count": int(float(row.get("external_fi_count", 0) or 0)),
                "external_fi_amount": round(float(row.get("external_fi_amount", 0) or 0), 2),
                "external_intensity": round(float(row.get("external_intensity", 0) or 0), 3),
                "financial_services_count": int(float(row.get("financial_services_count", 0) or 0)),
                "balance": round(float(row.get("balance", 0) or 0), 2),
                "product_count": int(float(row.get("product_count", 0) or 0)),
                "has_debit": _trace_bool(row.get("has_debit")),
                "payroll_detected": _trace_bool(row.get("payroll_detected")),
                "engagement_tier": _trace_text(row.get("engagement_tier")),
                "branch": _trace_text(row.get("branch")),
                "product_code": _trace_text(row.get("product_code")),
                "target_status": _trace_text(row.get("target_status")),
                "measurement_group": _trace_text(row.get("measurement_group")),
                "owner_role": _trace_text(row.get("owner_role")),
                "recommended_channel": _trace_text(row.get("recommended_channel")),
                "recommended_action": recommended_action,
                "evidence_summary": _trace_text(row.get("evidence_summary")),
                "decision_trace": _account_decision_trace(row, recommended_action),
                "source_artifacts": (
                    "account_month_features.csv|pfi_verdicts.csv|relationship_segments.csv|"
                    "account_intelligence_profile.csv|opportunities.csv"
                ),
                "source_sections": _trace_text(row.get("top_opportunity_source_sections")),
                "model_version": "account_scoring_trace_v0_rules",
            }
        )

    return pd.DataFrame(rows, columns=_account_scoring_trace_columns()).sort_values(
        ["top_priority_score", "total_expected_value", "account_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def build_stakeholder_exports(
    account_intelligence_profile: pd.DataFrame,
    campaign_targets: pd.DataFrame,
    action_plan: pd.DataFrame,
    file_assembly_plan: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> dict[str, pd.DataFrame]:
    """Build role-specific extracts that make the analysis operational."""
    cfg = config or EngineConfig()
    exports = {
        "csm_review_queue": build_csm_review_queue(account_intelligence_profile, cfg),
        "analyst_validation_queue": build_analyst_validation_queue(
            account_intelligence_profile,
            layout_gap_report,
            data_quality,
            cfg,
        ),
        "marketing_activation_export": build_marketing_activation_export(campaign_targets, cfg),
        "banker_call_list": build_banker_call_list(account_intelligence_profile, action_plan, cfg),
        "data_team_load_plan": build_data_team_load_plan(file_assembly_plan, layout_gap_report, cfg),
    }
    exports["stakeholder_export_manifest"] = build_stakeholder_export_manifest(exports, cfg)
    return exports


def build_csm_review_queue(
    account_intelligence_profile: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create the compact CSM queue for client strategy review."""
    cfg = config or EngineConfig()
    columns = _csm_review_queue_columns()
    if account_intelligence_profile is None or account_intelligence_profile.empty:
        return pd.DataFrame(columns=columns)

    df = account_intelligence_profile.copy()
    df["top_priority_score"] = pd.to_numeric(df.get("top_priority_score", 0), errors="coerce").fillna(0.0)
    df["total_expected_value"] = pd.to_numeric(df.get("total_expected_value", 0), errors="coerce").fillna(0.0)
    rows: list[dict[str, Any]] = []
    ranked = df.sort_values(
        ["top_priority_score", "total_expected_value", "account_id"],
        ascending=[False, False, True],
    )
    for rank, row in enumerate(ranked.to_dict("records"), start=1):
        rows.append(
            {
                "review_rank": rank,
                "client_id": cfg.client_id,
                "period_month": row.get("period_month", cfg.period_month),
                "account_id": row.get("account_id", ""),
                "relationship_segment": row.get("relationship_segment", ""),
                "risk_level": row.get("risk_level", ""),
                "pfi_verdict": row.get("pfi_verdict", ""),
                "top_play_name": row.get("top_play_name", ""),
                "top_priority_score": row.get("top_priority_score", 0.0),
                "total_expected_value": row.get("total_expected_value", 0.0),
                "recommended_action": row.get("recommended_action", ""),
                "evidence_summary": row.get("evidence_summary", ""),
                "owner_role": row.get("owner_role", ""),
                "recommended_channel": row.get("recommended_channel", ""),
                "source_profile_id": row.get("profile_id", ""),
                "model_version": "stakeholder_export_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_marketing_activation_export(
    campaign_targets: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a clean audience export for campaign tools."""
    cfg = config or EngineConfig()
    columns = _marketing_activation_export_columns()
    if campaign_targets is None or campaign_targets.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []
    for row in campaign_targets.to_dict("records"):
        rows.append(
            {
                "client_id": cfg.client_id,
                "period_month": row.get("period_month", cfg.period_month),
                "action_id": row.get("action_id", ""),
                "measurement_id": row.get("measurement_id", ""),
                "account_id": row.get("account_id", ""),
                "play_name": row.get("play_name", ""),
                "opportunity_type": row.get("opportunity_type", ""),
                "target_rank_within_play": row.get("target_rank_within_play", ""),
                "measurement_group": row.get("measurement_group", ""),
                "target_status": row.get("target_status", ""),
                "recommended_channel": row.get("recommended_channel", ""),
                "priority_score": row.get("priority_score", 0.0),
                "expected_value": row.get("expected_value", 0.0),
                "confidence": row.get("confidence", ""),
                "reason_codes": row.get("reason_codes", ""),
                "primary_metric": row.get("primary_metric", ""),
                "branch": row.get("branch", ""),
                "product_code": row.get("product_code", ""),
                "model_version": "stakeholder_export_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_banker_call_list(
    account_intelligence_profile: pd.DataFrame,
    action_plan: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a high-touch banker/branch follow-up list."""
    cfg = config or EngineConfig()
    columns = _banker_call_list_columns()
    if account_intelligence_profile is None or account_intelligence_profile.empty:
        return pd.DataFrame(columns=columns)

    df = account_intelligence_profile.copy()
    if action_plan is not None and not action_plan.empty:
        action_cols = ["opportunity_type", "talk_track", "next_step"]
        df = df.merge(
            action_plan[[col for col in action_cols if col in action_plan.columns]],
            left_on="top_opportunity_type",
            right_on="opportunity_type",
            how="left",
            suffixes=("", "_action"),
        )

    banker_types = {
        "deposit_retention",
        "competitor_winback",
        "attrition_prevention",
        "relationship_expansion",
        "payroll_conversion",
    }
    mask = df["top_opportunity_type"].astype(str).isin(banker_types)
    channel_mask = df.get("recommended_channel", pd.Series("", index=df.index)).astype(str).str.contains(
        "banker|branch|follow-up|call",
        case=False,
        regex=True,
        na=False,
    )
    selected = df[mask | channel_mask].copy()
    if selected.empty:
        selected = df.sort_values(["top_priority_score", "total_expected_value"], ascending=[False, False]).head(25)

    selected["top_priority_score"] = pd.to_numeric(selected.get("top_priority_score", 0), errors="coerce").fillna(0.0)
    selected["total_expected_value"] = pd.to_numeric(selected.get("total_expected_value", 0), errors="coerce").fillna(0.0)
    rows: list[dict[str, Any]] = []
    for rank, row in enumerate(
        selected.sort_values(["top_priority_score", "total_expected_value"], ascending=[False, False]).to_dict("records"),
        start=1,
    ):
        rows.append(
            {
                "call_rank": rank,
                "client_id": cfg.client_id,
                "period_month": row.get("period_month", cfg.period_month),
                "account_id": row.get("account_id", ""),
                "branch": row.get("branch", ""),
                "relationship_segment": row.get("relationship_segment", ""),
                "risk_level": row.get("risk_level", ""),
                "pfi_verdict": row.get("pfi_verdict", ""),
                "top_play_name": row.get("top_play_name", ""),
                "top_priority_score": row.get("top_priority_score", 0.0),
                "total_expected_value": row.get("total_expected_value", 0.0),
                "recommended_action": row.get("recommended_action", ""),
                "talk_track": row.get("talk_track", "") or row.get("next_step", ""),
                "top_counterparties": row.get("top_counterparties", ""),
                "evidence_summary": row.get("evidence_summary", ""),
                "action_id": row.get("action_id", ""),
                "measurement_id": row.get("measurement_id", ""),
                "model_version": "stakeholder_export_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_analyst_validation_queue(
    account_intelligence_profile: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create analyst QA items before a package is trusted for client use."""
    cfg = config or EngineConfig()
    columns = _analyst_validation_queue_columns()
    rows: list[dict[str, Any]] = []

    for index, warning in enumerate(data_quality.get("warnings") or [], start=1):
        rows.append(
            _validation_item(
                cfg,
                item_rank=len(rows) + 1,
                severity="warning",
                item_type="data_quality_warning",
                item_id=f"data_quality:{index}",
                issue=str(warning),
                recommended_action="Review the warning and document whether it affects client-facing interpretation.",
                source_artifact="data_quality.json",
            )
        )

    if layout_gap_report is not None and not layout_gap_report.empty:
        gaps = layout_gap_report[
            layout_gap_report["mapping_status"].astype(str).isin(["missing_required", "contract_needed"])
        ].copy()
        for row in gaps.to_dict("records"):
            rows.append(
                _validation_item(
                    cfg,
                    item_rank=len(rows) + 1,
                    severity="error" if row.get("mapping_status") == "missing_required" else "warning",
                    item_type="layout_gap",
                    item_id=f"{row.get('file_name', '')}:{row.get('canonical_field', '')}",
                    issue=(
                        f"{row.get('file_name', '')} has {row.get('mapping_status', '')} "
                        f"for {row.get('canonical_field', '') or 'layout contract'}."
                    ),
                    recommended_action=row.get("remediation_action", ""),
                    source_artifact="layout_gap_report.csv",
                )
            )

    if account_intelligence_profile is not None and not account_intelligence_profile.empty:
        df = account_intelligence_profile.copy()
        df["top_priority_score"] = pd.to_numeric(df.get("top_priority_score", 0), errors="coerce").fillna(0.0)
        risky = df[
            df["confidence"].astype(str).str.lower().isin(["low", "medium"])
            & df["top_priority_score"].ge(25)
        ].head(25)
        for row in risky.to_dict("records"):
            rows.append(
                _validation_item(
                    cfg,
                    item_rank=len(rows) + 1,
                    severity="review",
                    item_type="account_confidence_review",
                    item_id=str(row.get("profile_id", row.get("account_id", ""))),
                    issue=(
                        f"Account {row.get('account_id', '')} has {row.get('confidence', '')} confidence "
                        f"with priority score {row.get('top_priority_score', 0)}."
                    ),
                    recommended_action="Sample the account evidence and confirm the play before client use.",
                    source_artifact="account_intelligence_profile.csv",
                )
            )

    if not rows:
        rows.append(
            _validation_item(
                cfg,
                item_rank=1,
                severity="info",
                item_type="validation_status",
                item_id=f"{cfg.client_id}:{cfg.period_month}:validation",
                issue="No blocking validation issues detected by V1 rules.",
                recommended_action="Proceed with normal analyst sample review.",
                source_artifact="run_summary.json",
            )
        )
    return pd.DataFrame(rows, columns=columns)


def build_data_team_load_plan(
    file_assembly_plan: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a data-team view of file load readiness and mapping blockers."""
    cfg = config or EngineConfig()
    columns = _data_team_load_plan_columns()
    if file_assembly_plan is None or file_assembly_plan.empty:
        return pd.DataFrame(columns=columns)

    gap_counts = pd.DataFrame(columns=["source_path", "missing_required_count", "contract_needed_count", "layout_gap_actions"])
    if layout_gap_report is not None and not layout_gap_report.empty:
        gaps = layout_gap_report.copy()
        gaps["missing_required_flag"] = gaps["mapping_status"].astype(str).eq("missing_required")
        gaps["contract_needed_flag"] = gaps["mapping_status"].astype(str).eq("contract_needed")
        gap_counts = gaps.groupby("source_path", as_index=False).agg(
            missing_required_count=("missing_required_flag", "sum"),
            contract_needed_count=("contract_needed_flag", "sum"),
            layout_gap_actions=("remediation_action", _join_unique),
        )

    df = file_assembly_plan.merge(gap_counts, on="source_path", how="left")
    for col in ["missing_required_count", "contract_needed_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["layout_gap_actions"] = df["layout_gap_actions"].fillna("")
    rows: list[dict[str, Any]] = []
    for row in df.to_dict("records"):
        load_flag = bool(row.get("load_flag", False))
        blocker_count = int(row.get("missing_required_count", 0) or 0) + int(row.get("contract_needed_count", 0) or 0)
        rows.append(
            {
                "load_rank": row.get("load_order", ""),
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "file_name": row.get("file_name", ""),
                "source_path": row.get("source_path", ""),
                "source_family": row.get("source_family", ""),
                "contract_id": row.get("contract_id", ""),
                "assembly_role": row.get("assembly_role", ""),
                "load_flag": load_flag,
                "target_engine_input": row.get("target_engine_input", ""),
                "target_snowflake_layer": row.get("target_snowflake_layer", ""),
                "missing_required_count": row.get("missing_required_count", 0),
                "contract_needed_count": row.get("contract_needed_count", 0),
                "load_readiness": "ready_to_load" if load_flag and blocker_count == 0 else "hold_for_review",
                "operator_action": row.get("operator_action", ""),
                "layout_gap_actions": row.get("layout_gap_actions", ""),
                "model_version": "stakeholder_export_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_source_layout_profile(
    intake_profile: list[dict[str, Any]],
    intake_work_order: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a source-column profile for layout mapping and contract authoring."""
    cfg = config or EngineConfig()
    columns = _source_layout_profile_columns()
    if not intake_profile:
        return pd.DataFrame(columns=columns)

    work_order_by_path = _records_by_key(intake_work_order, "source_path")
    layout_matches = _layout_matches_by_source_column(layout_gap_report)
    missing_required_by_path = _missing_required_fields_by_path(layout_gap_report)
    rows: list[dict[str, Any]] = []

    for item in intake_profile:
        source_path = _trace_text(item.get("source_path"))
        work_order = work_order_by_path.get(source_path, {})
        match = item.get("contract_match") or {}
        source_family = _trace_text(work_order.get("source_family")) or _trace_text(match.get("source_family")) or "unknown"
        source_columns = _profile_source_columns(item)
        if not source_columns:
            source_columns = [("", pd.NA)]

        for source_column, source_position in source_columns:
            key = (source_path, _trace_text(source_column), _safe_int_value(source_position, default=-1))
            mapped_rows = layout_matches.get(key, [])
            mapped_canonical_fields = _sorted_texts(row.get("canonical_field") for row in mapped_rows)
            mapping_statuses = _sorted_texts(row.get("mapping_status") for row in mapped_rows)
            data_types = _sorted_texts(row.get("data_type") for row in mapped_rows)
            confidence = max([float(row.get("confidence", 0) or 0) for row in mapped_rows] or [0.0])
            required_flag = any(_trace_bool(row.get("required_flag")) for row in mapped_rows)
            proposed_input_family = _proposed_input_family(source_family, item, source_column)
            column_role_guess = _source_column_role_guess(source_column)
            canonical_status = _canonical_mapping_status(
                mapped_canonical_fields=mapped_canonical_fields,
                match_status=_trace_text(match.get("status")),
                intake_decision=_trace_text(work_order.get("intake_decision")),
            )
            rows.append(
                {
                    "profile_rank": len(rows) + 1,
                    "client_id": cfg.client_id,
                    "period_month": _period_label(cfg.period_month),
                    "file_name": _trace_text(item.get("file_name")),
                    "source_path": source_path,
                    "detected_format": _trace_text(item.get("detected_format")),
                    "delimiter": _trace_text(item.get("delimiter")),
                    "header_mode": _trace_text(item.get("header_mode")),
                    "column_count": _safe_int_value(item.get("column_count")),
                    "estimated_rows": _safe_int_value(item.get("estimated_rows")),
                    "source_family": source_family,
                    "contract_id": _trace_text(work_order.get("contract_id")) or _trace_text(match.get("contract_id")),
                    "match_status": _trace_text(work_order.get("match_status")) or _trace_text(match.get("status")),
                    "match_score": float(work_order.get("match_score", match.get("score", 0)) or 0),
                    "intake_decision": _trace_text(work_order.get("intake_decision")),
                    "source_column": _trace_text(source_column),
                    "source_position": source_position,
                    "source_column_key": _layout_field_key(source_column),
                    "matched_canonical_fields": "|".join(mapped_canonical_fields),
                    "canonical_mapping_status": canonical_status,
                    "required_flag": required_flag,
                    "data_type": "|".join(data_types),
                    "confidence": round(confidence, 3),
                    "column_role_guess": column_role_guess,
                    "proposed_input_family": proposed_input_family,
                    "missing_required_fields": "|".join(missing_required_by_path.get(source_path, [])),
                    "proposed_contract_id": _proposed_contract_id(source_family, item),
                    "mapping_action": _source_layout_mapping_action(
                        canonical_status=canonical_status,
                        source_family=source_family,
                        source_column=_trace_text(source_column),
                        column_role_guess=column_role_guess,
                    ),
                    "source_artifacts": "intake_profile.json|intake_work_order.csv|layout_gap_report.csv",
                    "model_version": "source_layout_profile_v0",
                }
            )

    return pd.DataFrame(rows, columns=columns)


def build_layout_contract_draft_queue(
    source_layout_profile: pd.DataFrame,
    layout_gap_report: pd.DataFrame,
    intake_work_order: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Roll source-column evidence up to one layout-contract action per file."""
    cfg = config or EngineConfig()
    columns = _layout_contract_draft_queue_columns()
    if source_layout_profile is None or source_layout_profile.empty:
        return pd.DataFrame(columns=columns)

    work_order_by_path = _records_by_key(intake_work_order, "source_path")
    gap_rows_by_path = _layout_gap_rows_by_path(layout_gap_report)
    rows: list[dict[str, Any]] = []

    for source_path, group in source_layout_profile.groupby("source_path", dropna=False):
        group = group.copy()
        first = group.iloc[0].to_dict()
        source_path_text = _trace_text(source_path) or _trace_text(first.get("source_path"))
        work_order = work_order_by_path.get(source_path_text, {})
        source_columns = _ordered_source_columns(group)
        matched_fields = _source_profile_matched_fields(group)
        raw_missing_required = _contract_missing_required_fields(group, gap_rows_by_path.get(source_path_text, []))
        unmapped_columns = _source_profile_unmapped_columns(group)
        proposed_family = _contract_draft_input_family(first, source_columns, matched_fields)
        missing_required = _contract_draft_missing_required(raw_missing_required, matched_fields, proposed_family)
        match_status = _trace_text(work_order.get("match_status")) or _trace_text(first.get("match_status"))
        intake_decision = _trace_text(work_order.get("intake_decision")) or _trace_text(first.get("intake_decision"))
        current_contract_id = _trace_text(work_order.get("contract_id")) or _trace_text(first.get("contract_id"))
        contract_action = _contract_draft_action(
            match_status=match_status,
            intake_decision=intake_decision,
            missing_required=missing_required,
            current_contract_id=current_contract_id,
        )
        proposed_contract_id = _contract_draft_id(
            proposed_family=proposed_family,
            file_name=_trace_text(first.get("file_name")),
            current_contract_id=current_contract_id,
            match_status=match_status,
            contract_action=contract_action,
        )
        priority_band = _contract_draft_priority(contract_action, missing_required)
        alias_map = _layout_contract_alias_map(group)
        draft_yaml = _layout_contract_draft_yaml(
            proposed_contract_id=proposed_contract_id,
            proposed_family=proposed_family,
            first=first,
            matched_fields=matched_fields,
            source_columns=source_columns,
            alias_map=alias_map,
        )
        rows.append(
            {
                "draft_rank": 0,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "file_name": _trace_text(first.get("file_name")),
                "source_path": source_path_text,
                "source_family": _trace_text(first.get("source_family")) or proposed_family,
                "detected_format": _trace_text(first.get("detected_format")),
                "delimiter": _trace_text(first.get("delimiter")),
                "header_mode": _trace_text(first.get("header_mode")),
                "estimated_rows": _safe_int_value(first.get("estimated_rows")),
                "match_status": match_status,
                "match_score": float(work_order.get("match_score", first.get("match_score", 0)) or 0),
                "current_contract_id": current_contract_id,
                "proposed_contract_id": proposed_contract_id,
                "contract_action": contract_action,
                "priority_band": priority_band,
                "missing_required_fields": "|".join(missing_required),
                "matched_canonical_fields": "|".join(matched_fields),
                "unmapped_source_columns": "|".join(unmapped_columns),
                "source_columns": "|".join(source_columns),
                "draft_alias_map": json.dumps(alias_map, sort_keys=True),
                "draft_yaml": draft_yaml,
                "data_team_action": _contract_draft_data_team_action(
                    contract_action=contract_action,
                    proposed_contract_id=proposed_contract_id,
                    missing_required=missing_required,
                    proposed_family=proposed_family,
                ),
                "analyst_question": _contract_draft_analyst_question(
                    contract_action=contract_action,
                    proposed_family=proposed_family,
                    file_name=_trace_text(first.get("file_name")),
                ),
                "target_snowflake_layer": _contract_draft_target_layer(
                    proposed_family=proposed_family,
                    work_order=work_order,
                ),
                "source_artifacts": "source_layout_profile.csv|layout_gap_report.csv|intake_work_order.csv",
                "model_version": "layout_contract_draft_queue_v0_rules",
            }
        )

    if not rows:
        return pd.DataFrame(columns=columns)
    out = pd.DataFrame(rows, columns=columns)
    out["_priority_sort"] = out["priority_band"].map({"P0": 0, "P1": 1, "P2": 2}).fillna(9)
    out = out.sort_values(
        ["_priority_sort", "match_status", "estimated_rows", "file_name"],
        ascending=[True, True, False, True],
    ).drop(columns=["_priority_sort"]).reset_index(drop=True)
    out["draft_rank"] = range(1, len(out) + 1)
    return out


def build_layout_contract_export_manifest(
    layout_contract_draft_queue: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a file manifest for promotable layout contract YAML drafts."""
    cfg = config or EngineConfig()
    columns = _layout_contract_export_manifest_columns()
    if layout_contract_draft_queue is None or layout_contract_draft_queue.empty:
        return pd.DataFrame(columns=columns)

    seen_stems: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    for row in layout_contract_draft_queue.to_dict("records"):
        proposed_contract_id = _trace_text(row.get("proposed_contract_id")) or _layout_contract_export_fallback_id(row)
        yaml_file_name = _layout_contract_export_file_name(proposed_contract_id, row, seen_stems)
        draft_yaml = _trace_text(row.get("draft_yaml"))
        rows.append(
            {
                "export_rank": int(row.get("draft_rank") or len(rows) + 1),
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "file_name": _trace_text(row.get("file_name")),
                "source_path": _trace_text(row.get("source_path")),
                "source_family": _trace_text(row.get("source_family")),
                "proposed_contract_id": proposed_contract_id,
                "contract_action": _trace_text(row.get("contract_action")),
                "priority_band": _trace_text(row.get("priority_band")),
                "yaml_file_name": yaml_file_name,
                "yaml_relative_path": f"layout_contract_drafts/{yaml_file_name}",
                "yaml_ready": bool(draft_yaml),
                "target_snowflake_layer": _trace_text(row.get("target_snowflake_layer")),
                "missing_required_fields": _trace_text(row.get("missing_required_fields")),
                "matched_canonical_fields": _trace_text(row.get("matched_canonical_fields")),
                "data_team_action": _trace_text(row.get("data_team_action")),
                "analyst_question": _trace_text(row.get("analyst_question")),
                "source_artifacts": "layout_contract_draft_queue.csv|source_layout_profile.csv|layout_gap_report.csv",
                "model_version": "layout_contract_export_manifest_v0",
            }
        )

    return pd.DataFrame(rows, columns=columns)


def build_stakeholder_export_manifest(
    exports: dict[str, pd.DataFrame],
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Describe which role should use each stakeholder export."""
    cfg = config or EngineConfig()
    specs = {
        "csm_review_queue": (
            "CSM",
            "Client strategy review and meeting prep.",
            "Choose the top plays and account examples for the client conversation.",
        ),
        "analyst_validation_queue": (
            "Analyst",
            "Quality assurance and exception review.",
            "Resolve blockers and sample high-priority lower-confidence accounts.",
        ),
        "marketing_activation_export": (
            "Marketing",
            "Campaign/audience upload.",
            "Load test and holdout groups while preserving action_id and measurement_id.",
        ),
        "banker_call_list": (
            "Client bankers",
            "High-touch account outreach.",
            "Use the talk track and evidence summary for banker follow-up.",
        ),
        "data_team_load_plan": (
            "Data team",
            "Monthly file load and mapping readiness.",
            "Load ready files and resolve mapping blockers.",
        ),
    }
    rows: list[dict[str, Any]] = []
    for rank, (artifact_name, (role, use_case, first_action)) in enumerate(specs.items(), start=1):
        table = exports.get(artifact_name, pd.DataFrame())
        rows.append(
            {
                "export_rank": rank,
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "artifact_name": artifact_name,
                "file_name": f"{artifact_name}.csv",
                "primary_role": role,
                "row_count": int(len(table)),
                "use_case": use_case,
                "first_action": first_action,
                "status": "ready" if len(table) else "empty",
                "model_version": "stakeholder_export_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=_stakeholder_export_manifest_columns())


def build_file_ledger(paths: Iterable[Path | str]) -> pd.DataFrame:
    """Create a source-file ledger for lineage and quality review."""
    rows: list[dict[str, Any]] = []
    for raw in paths:
        path = Path(raw)
        exists = path.exists()
        stat = path.stat() if exists else None
        rows.append(
            {
                "source_path": str(path),
                "file_name": path.name,
                "file_type": _infer_file_type(path),
                "suffix": path.suffix.lower(),
                "exists": exists,
                "size_bytes": int(stat.st_size) if stat else 0,
                "modified_at": (
                    datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
                    if stat
                    else ""
                ),
                "sha256": _hash_file(path) if exists and path.is_file() else "",
            }
        )
    return pd.DataFrame(rows)


def build_account_month_features(
    accounts: pd.DataFrame | None,
    transactions: pd.DataFrame | None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Build the canonical account-month feature mart for V1 scoring."""
    cfg = config or EngineConfig()
    account_dim = _account_dimensions(accounts)
    tx_features = _transaction_features(transactions)

    if tx_features.empty and account_dim.empty:
        return _empty_features()

    if tx_features.empty:
        period = _period_label(cfg.period_month)
        base = account_dim.copy()
        base["period_month"] = period
        for col in _transaction_feature_columns():
            base[col] = 0
    else:
        base = tx_features.copy()
        if not account_dim.empty:
            base = base.merge(account_dim, on="account_id", how="left", indicator="_account_match")
            base["matched_account"] = base["_account_match"].eq("both")
            base = base.drop(columns=["_account_match"])
        else:
            base["matched_account"] = False

    if not account_dim.empty and not tx_features.empty:
        period = _period_label(cfg.period_month) or str(tx_features["period_month"].max())
        missing_accounts = account_dim[~account_dim["account_id"].isin(tx_features["account_id"])].copy()
        if not missing_accounts.empty:
            missing_accounts["period_month"] = period
            for col in _transaction_feature_columns():
                missing_accounts[col] = 0
            missing_accounts["matched_account"] = True
            base = pd.concat([base, missing_accounts], ignore_index=True, sort=False)

    defaults = {
        "balance": 0.0,
        "has_debit": False,
        "business_flag": False,
        "branch": "",
        "product_code": "",
        "product_count": 0,
        "account_status": "",
        "date_opened": pd.NaT,
        "matched_account": False,
    }
    for col, default in defaults.items():
        if col not in base.columns:
            base[col] = default

    for col in _transaction_feature_columns():
        if col not in base.columns:
            base[col] = 0

    base["account_id"] = base["account_id"].astype(str)
    base["period_month"] = base["period_month"].fillna(_period_label(cfg.period_month))
    base["balance"] = pd.to_numeric(base["balance"], errors="coerce").fillna(0.0)
    base["product_count"] = pd.to_numeric(base["product_count"], errors="coerce").fillna(0).astype(int)
    base["txn_count"] = pd.to_numeric(base["txn_count"], errors="coerce").fillna(0).astype(int)
    base["active_days"] = pd.to_numeric(base["active_days"], errors="coerce").fillna(0).astype(int)
    base["external_intensity"] = _safe_ratio(
        base["external_fi_amount"],
        base["spend_amount"].abs() + base["credit_amount"].abs() + 1,
    ).clip(0, 1)
    base["payroll_detected"] = base["payroll_count"].fillna(0).astype(float).gt(0)
    base["engagement_tier"] = np.select(
        [
            base["txn_count"].ge(cfg.strong_txn_threshold),
            base["txn_count"].ge(cfg.active_txn_threshold),
            base["txn_count"].ge(cfg.low_activity_txn_threshold),
            base["txn_count"].gt(0),
        ],
        ["High", "Medium", "Low", "Very Low"],
        default="Dormant",
    )
    base["feature_version"] = "ti_v1"

    ordered = [
        "account_id",
        "period_month",
        "matched_account",
        "txn_count",
        "active_days",
        "first_txn_date",
        "last_txn_date",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "card_txn_count",
        "card_amount",
        "pin_txn_count",
        "pin_amount",
        "sig_txn_count",
        "sig_amount",
        "has_pin",
        "has_sig",
        "pin_ratio",
        "sig_ratio",
        "avg_ticket_amount",
        "spend_per_txn",
        "avg_pin_ticket",
        "avg_sig_ticket",
        "pin_interchange_est",
        "sig_interchange_est",
        "unique_merchants",
        "balance",
        "has_debit",
        "business_flag",
        "branch",
        "product_code",
        "product_count",
        "account_status",
        "date_opened",
        "external_intensity",
        "payroll_detected",
        "engagement_tier",
        "feature_version",
    ]
    return base[[col for col in ordered if col in base.columns]].sort_values(
        ["period_month", "account_id"]
    ).reset_index(drop=True)


def build_counterparty_signals(
    transactions: pd.DataFrame | None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Build account-month counterparty signals from transaction descriptions."""
    cfg = config or EngineConfig()
    if transactions is None or transactions.empty:
        return _empty_counterparty_signals()
    account_col = _find_column(transactions, ACCOUNT_ID_COLUMNS)
    date_col = _find_column(transactions, DATE_COLUMNS)
    amount_col = _find_column(transactions, AMOUNT_COLUMNS)
    if account_col is None or date_col is None or amount_col is None:
        return _empty_counterparty_signals()

    merchant_col = _find_column(transactions, MERCHANT_COLUMNS)
    type_col = _find_column(transactions, TYPE_COLUMNS)
    df = transactions.copy()
    df["account_id"] = df[account_col].astype(str).str.strip()
    df["transaction_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["amount"] = _numeric(df[amount_col])
    df = df[df["account_id"].ne("") & df["transaction_date"].notna()]
    if df.empty:
        return _empty_counterparty_signals()

    merchant_text = df[merchant_col].astype(str).fillna("") if merchant_col else pd.Series("", index=df.index)
    type_text = df[type_col].astype(str).fillna("") if type_col else pd.Series("", index=df.index)
    df["_text"] = (merchant_text + " " + type_text).str.lower()
    df["period_month"] = df["transaction_date"].dt.to_period("M").astype(str)
    df["counterparty_name"] = merchant_text.apply(_normalize_counterparty_name)
    df["counterparty_category"] = df.apply(_counterparty_category, axis=1)
    df["direction"] = np.where(df["amount"].ge(0), "credit", "debit")
    df["_credit_amount"] = np.where(df["amount"].ge(0), df["amount"].abs(), 0.0)
    df["_debit_amount"] = np.where(df["amount"].lt(0), df["amount"].abs(), 0.0)
    df["_abs_amount"] = df["amount"].abs()

    grouped = df.groupby(
        ["account_id", "period_month", "counterparty_name", "counterparty_category", "direction"],
        dropna=False,
    ).agg(
        transaction_count=("amount", "size"),
        active_days=("transaction_date", lambda s: int(s.dt.date.nunique())),
        total_amount=("_abs_amount", "sum"),
        net_amount=("amount", "sum"),
        credit_amount=("_credit_amount", "sum"),
        debit_amount=("_debit_amount", "sum"),
        avg_ticket=("_abs_amount", "mean"),
        first_seen=("transaction_date", "min"),
        last_seen=("transaction_date", "max"),
    ).reset_index()

    grouped["client_id"] = cfg.client_id
    grouped["signal_id"] = grouped.apply(
        lambda row: (
            f"{cfg.client_id}:{row['period_month']}:{row['account_id']}:"
            f"{_slug(row['counterparty_name'])}:{row['counterparty_category']}:{row['direction']}"
        ),
        axis=1,
    )
    grouped["recurrence_score"] = grouped.apply(
        lambda row: round(min((float(row["transaction_count"]) / 6.0) + (float(row["active_days"]) / 6.0), 1.0), 3),
        axis=1,
    )
    grouped["signal_strength"] = grouped.apply(_counterparty_signal_strength, axis=1)
    grouped["relationship_signal"] = grouped.apply(_counterparty_relationship_signal, axis=1)
    grouped["confidence"] = grouped.apply(_counterparty_confidence, axis=1)
    grouped["model_version"] = "counterparty_signal_v0_rules"
    ordered = [
        "signal_id",
        "client_id",
        "account_id",
        "period_month",
        "counterparty_name",
        "counterparty_category",
        "direction",
        "transaction_count",
        "active_days",
        "total_amount",
        "net_amount",
        "credit_amount",
        "debit_amount",
        "avg_ticket",
        "first_seen",
        "last_seen",
        "recurrence_score",
        "signal_strength",
        "relationship_signal",
        "confidence",
        "model_version",
    ]
    return grouped[ordered].sort_values(
        ["signal_strength", "total_amount", "transaction_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def build_counterparty_summary(
    counterparty_signals: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Aggregate account-level counterparties into client strategy rows."""
    cfg = config or EngineConfig()
    if counterparty_signals is None or counterparty_signals.empty:
        return _empty_counterparty_summary()

    df = counterparty_signals.copy()
    for col in ["transaction_count", "total_amount", "net_amount", "credit_amount", "debit_amount", "signal_strength"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    rows: list[dict[str, Any]] = []
    for keys, group in df.groupby(
        ["period_month", "counterparty_name", "counterparty_category", "direction"],
        dropna=False,
    ):
        period_month, counterparty_name, category, direction = keys
        top_signals = _top_tokens(group["relationship_signal"], limit=2)
        rows.append(
            {
                "counterparty_id": f"{cfg.client_id}:{period_month}:{_slug(counterparty_name)}:{category}:{direction}",
                "client_id": cfg.client_id,
                "period_month": period_month,
                "counterparty_name": counterparty_name,
                "counterparty_category": category,
                "direction": direction,
                "account_count": int(group["account_id"].nunique()),
                "transaction_count": int(group["transaction_count"].sum()),
                "total_amount": round(float(group["total_amount"].sum()), 2),
                "net_amount": round(float(group["net_amount"].sum()), 2),
                "credit_amount": round(float(group["credit_amount"].sum()), 2),
                "debit_amount": round(float(group["debit_amount"].sum()), 2),
                "avg_signal_strength": round(float(group["signal_strength"].mean()), 1),
                "top_relationship_signal": top_signals[0] if top_signals else "",
                "signal_mix": "|".join(top_signals),
                "strategy_relevance": _counterparty_strategy_relevance(str(category), str(direction)),
                "first_seen": group["first_seen"].min(),
                "last_seen": group["last_seen"].max(),
                "model_version": "counterparty_summary_v0_rules",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["total_amount", "account_count", "transaction_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def classify_pfi(features: pd.DataFrame, config: EngineConfig | None = None) -> pd.DataFrame:
    """Classify account-month PFI status with reason codes and confidence."""
    cfg = config or EngineConfig()
    rows: list[dict[str, Any]] = []
    for row in features.to_dict("records"):
        txn_count = float(row.get("txn_count", 0) or 0)
        payroll_amount = float(row.get("payroll_amount", 0) or 0)
        payroll_count = float(row.get("payroll_count", 0) or 0)
        balance = max(float(row.get("balance", 0) or 0), 0.0)
        product_count = max(float(row.get("product_count", 0) or 0), 0.0)
        external_count = float(row.get("external_fi_count", 0) or 0)
        external_amount = float(row.get("external_fi_amount", 0) or 0)
        matched = bool(row.get("matched_account", False))

        activity_score = min(txn_count / max(cfg.strong_txn_threshold, 1), 1.0)
        payroll_score = 0.0
        if payroll_count > 0:
            payroll_score = min(payroll_amount / max(cfg.payroll_min_amount * 2, 1), 1.0)
            payroll_score = max(payroll_score, 0.75)
        balance_score = min(balance / max(cfg.high_balance_threshold, 1), 1.0)
        depth_score = min(product_count / 3.0, 1.0)
        external_score = min(
            ((external_count / 5.0) + (external_amount / max(cfg.high_balance_threshold, 1))) / 2,
            1.0,
        )
        internal_score = (
            0.35 * payroll_score
            + 0.25 * activity_score
            + 0.20 * balance_score
            + 0.20 * depth_score
        )

        if txn_count == 0 and not matched:
            verdict = "No verdict"
        elif internal_score >= 0.60 and external_score < 0.35:
            verdict = "Primary with us"
        elif external_score >= 0.55 and internal_score < 0.45:
            verdict = "Competitor-primary"
        elif internal_score >= 0.45 and external_score >= 0.25:
            verdict = "Split"
        elif external_score >= 0.35:
            verdict = "Split"
        else:
            verdict = "No verdict"

        evidence_score = (
            (0.30 if matched else 0.0)
            + min(txn_count / 10.0, 0.35)
            + (0.20 if payroll_count > 0 else 0.0)
            + min((external_count + product_count) / 10.0, 0.15)
        )
        confidence = _confidence_label(evidence_score)
        reasons = _pfi_reasons(
            payroll_count=payroll_count,
            activity_score=activity_score,
            balance=balance,
            product_count=product_count,
            external_count=external_count,
            external_amount=external_amount,
            matched=matched,
        )
        pfi_score = round(max(min((internal_score - 0.30 * external_score) * 100, 100), 0), 1)

        rows.append(
            {
                "account_id": row.get("account_id", ""),
                "period_month": row.get("period_month", ""),
                "pfi_verdict": verdict,
                "pfi_score": pfi_score,
                "internal_score": round(internal_score, 3),
                "external_score": round(external_score, 3),
                "confidence": confidence,
                "confidence_score": round(evidence_score, 3),
                "reason_codes": "|".join(reasons),
                "model_version": "pfi_v0_rules",
            }
        )
    return pd.DataFrame(rows)


def build_relationship_segments(
    features: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    opportunities: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Classify each account-month into a reusable financial-life segment."""
    cfg = config or EngineConfig()
    if features.empty:
        return _empty_relationship_segments()

    joined = features.copy()
    if pfi_verdicts is not None and not pfi_verdicts.empty:
        joined = joined.merge(
            pfi_verdicts[
                [
                    "account_id",
                    "period_month",
                    "pfi_verdict",
                    "pfi_score",
                    "internal_score",
                    "external_score",
                    "confidence",
                    "confidence_score",
                ]
            ],
            on=["account_id", "period_month"],
            how="left",
        )

    opportunity_rollup = _opportunity_rollup(opportunities)
    if not opportunity_rollup.empty:
        joined = joined.merge(opportunity_rollup, on=["account_id", "period_month"], how="left")

    defaults = {
        "pfi_verdict": "No verdict",
        "pfi_score": 0.0,
        "internal_score": 0.0,
        "external_score": 0.0,
        "confidence": "low",
        "confidence_score": 0.0,
        "top_opportunity_type": "",
        "top_priority_score": 0.0,
        "opportunity_count": 0,
        "total_expected_value": 0.0,
    }
    for col, value in defaults.items():
        if col not in joined.columns:
            joined[col] = value
        joined[col] = joined[col].fillna(value)

    rows: list[dict[str, Any]] = []
    for row in joined.to_dict("records"):
        segment = _relationship_segment_for_row(row, cfg)
        readiness_score = _segment_readiness_score(row)
        rows.append(
            {
                "segment_id": f"{cfg.client_id}:{row.get('period_month', '')}:{row.get('account_id', '')}",
                "client_id": cfg.client_id,
                "account_id": row.get("account_id", ""),
                "period_month": row.get("period_month", ""),
                "relationship_segment": segment["relationship_segment"],
                "segment_group": segment["segment_group"],
                "lifecycle_stage": segment["lifecycle_stage"],
                "risk_level": segment["risk_level"],
                "pfi_verdict": row.get("pfi_verdict", "No verdict"),
                "pfi_score": round(float(row.get("pfi_score", 0) or 0), 1),
                "confidence": row.get("confidence", "low"),
                "engagement_tier": row.get("engagement_tier", ""),
                "payroll_detected": bool(row.get("payroll_detected", False)),
                "external_intensity": round(float(row.get("external_intensity", 0) or 0), 3),
                "balance": round(float(row.get("balance", 0) or 0), 2),
                "txn_count": int(float(row.get("txn_count", 0) or 0)),
                "product_count": int(float(row.get("product_count", 0) or 0)),
                "has_debit": bool(row.get("has_debit", False)),
                "top_opportunity_type": row.get("top_opportunity_type", ""),
                "top_priority_score": round(float(row.get("top_priority_score", 0) or 0), 1),
                "opportunity_count": int(float(row.get("opportunity_count", 0) or 0)),
                "total_expected_value": round(float(row.get("total_expected_value", 0) or 0), 2),
                "opportunity_readiness_score": readiness_score,
                "next_best_motion": segment["next_best_motion"],
                "segment_reason_codes": "|".join(segment["segment_reason_codes"]),
                "model_version": "relationship_segment_v0_rules",
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["opportunity_readiness_score", "total_expected_value", "account_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def build_segment_summary(
    relationship_segments: pd.DataFrame,
    opportunities: pd.DataFrame | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Aggregate financial-life segments for strategy and dashboard review."""
    cfg = config or EngineConfig()
    if relationship_segments.empty:
        return _empty_segment_summary()

    rows: list[dict[str, Any]] = []
    for keys, group in relationship_segments.groupby(
        ["relationship_segment", "segment_group", "lifecycle_stage", "risk_level"],
        dropna=False,
    ):
        relationship_segment, segment_group, lifecycle_stage, risk_level = keys
        top_motion = _top_tokens(group["next_best_motion"], limit=1)
        top_reasons = _top_tokens(group["segment_reason_codes"], limit=6)
        rows.append(
            {
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "relationship_segment": relationship_segment,
                "segment_group": segment_group,
                "lifecycle_stage": lifecycle_stage,
                "risk_level": risk_level,
                "account_count": int(group["account_id"].nunique()),
                "avg_pfi_score": round(float(group["pfi_score"].mean()), 1),
                "avg_external_intensity": round(float(group["external_intensity"].mean()), 3),
                "avg_balance": round(float(group["balance"].mean()), 2),
                "payroll_accounts": int(group["payroll_detected"].fillna(False).sum()),
                "total_expected_value": round(float(group["total_expected_value"].sum()), 2),
                "avg_readiness_score": round(float(group["opportunity_readiness_score"].mean()), 1),
                "top_next_best_motion": top_motion[0] if top_motion else "",
                "top_reason_codes": "|".join(top_reasons),
                "model_version": "segment_summary_v0_rules",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["total_expected_value", "account_count", "avg_readiness_score"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def score_opportunities(
    features: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create ranked account-level opportunities from features and PFI verdicts."""
    cfg = config or EngineConfig()
    if features.empty:
        return _empty_opportunities()

    joined = features.merge(
        pfi_verdicts[
            [
                "account_id",
                "period_month",
                "pfi_verdict",
                "confidence",
                "confidence_score",
                "reason_codes",
            ]
        ],
        on=["account_id", "period_month"],
        how="left",
    )
    rows: list[dict[str, Any]] = []
    for row in joined.to_dict("records"):
        account_id = str(row.get("account_id", ""))
        period_month = str(row.get("period_month", ""))
        confidence_score = float(row.get("confidence_score", 0.25) or 0.25)
        addressability = 0.95 if bool(row.get("matched_account", False)) else 0.65
        if row.get("branch"):
            addressability = min(addressability + 0.05, 1.0)

        def add(
            opportunity_type: str,
            expected_value: float,
            urgency: float,
            reasons: list[str],
            action: str,
        ) -> None:
            impact = _impact_score(expected_value)
            priority = round(100 * impact * addressability * confidence_score * urgency, 1)
            if priority <= 0:
                return
            rows.append(
                {
                    "opportunity_id": f"{period_month}:{account_id}:{opportunity_type}",
                    "client_id": cfg.client_id,
                    "account_id": account_id,
                    "period_month": period_month,
                    "opportunity_type": opportunity_type,
                    "expected_value": round(float(expected_value), 2),
                    "priority_score": priority,
                    "impact_score": round(impact, 3),
                    "addressability_score": round(addressability, 3),
                    "confidence_score": round(confidence_score, 3),
                    "urgency_score": round(urgency, 3),
                    "confidence": row.get("confidence", "low"),
                    "pfi_verdict": row.get("pfi_verdict", "No verdict"),
                    "reason_codes": "|".join(reasons),
                    "recommended_action": action,
                    "source_sections": "|".join(SOURCE_SECTIONS_BY_OPPORTUNITY.get(opportunity_type, [])),
                    "model_version": "opportunity_v0_rules",
                }
            )

        txn_count = float(row.get("txn_count", 0) or 0)
        spend = float(row.get("spend_amount", 0) or 0)
        credit = float(row.get("credit_amount", 0) or 0)
        payroll_count = float(row.get("payroll_count", 0) or 0)
        balance = float(row.get("balance", 0) or 0)
        external_amount = float(row.get("external_fi_amount", 0) or 0)
        external_count = float(row.get("external_fi_count", 0) or 0)
        financial_count = float(row.get("financial_services_count", 0) or 0)
        product_count = float(row.get("product_count", 0) or 0)
        has_debit = bool(row.get("has_debit", False))
        pfi = str(row.get("pfi_verdict", "No verdict"))

        if payroll_count == 0 and (external_count > 0 or credit >= cfg.payroll_min_amount):
            add(
                "payroll_conversion",
                max(credit, external_amount, cfg.payroll_min_amount) * 0.02 * 12,
                0.90,
                ["no_payroll_detected", "external_money_movement"],
                "Target for direct-deposit or primary-banking conversion.",
            )

        if (not has_debit or spend < 250) and txn_count <= cfg.active_txn_threshold:
            add(
                "debit_activation",
                max(spend, credit * 0.10, 1000.0) * cfg.interchange_rate,
                0.65,
                ["weak_debit_activity", "eligible_account"],
                "Target for debit activation, wallet provisioning, or usage incentive.",
            )

        if balance >= cfg.high_balance_threshold and external_amount >= cfg.external_fi_amount_threshold:
            add(
                "deposit_retention",
                min(balance, external_amount * 6) * 0.01,
                0.95,
                ["high_balance", "external_fi_outflow"],
                "Route to banker or branch for deposit retention conversation.",
            )

        if external_count >= 2 or pfi in {"Split", "Competitor-primary"}:
            add(
                "competitor_winback",
                max(external_amount, 1000.0) * 0.015,
                0.85,
                ["competitor_intensity", pfi.lower().replace(" ", "_")],
                "Target with competitor win-back or relationship consolidation play.",
            )

        if txn_count <= cfg.low_activity_txn_threshold and (balance > 100 or product_count > 0):
            add(
                "dormant_reactivation",
                max(balance * 0.005, 25.0),
                0.70,
                ["low_activity", "reactivation_candidate"],
                "Target with reactivation message and digital/card usage prompt.",
            )

        if product_count <= 1 and (financial_count > 0 or external_count > 0):
            add(
                "relationship_expansion",
                max(financial_count * 250.0, external_amount * 0.01, 50.0),
                0.75,
                ["thin_relationship", "external_financial_activity"],
                "Target for next-best-product or relationship expansion offer.",
            )

        if pfi in {"Split", "Competitor-primary"} and txn_count <= cfg.active_txn_threshold:
            add(
                "attrition_prevention",
                max(balance * 0.01, external_amount * 0.02, 75.0),
                0.90,
                ["relationship_risk", "low_activity_or_competitor_pull"],
                "Prioritize for save outreach before dormancy or closure.",
            )

    if not rows:
        return _empty_opportunities()
    return pd.DataFrame(rows).sort_values(
        ["priority_score", "expected_value"], ascending=[False, False]
    ).reset_index(drop=True)


def build_opportunity_portfolio(
    opportunities: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Aggregate account-level opportunities into named strategic plays."""
    cfg = config or EngineConfig()
    if opportunities.empty:
        return _empty_opportunity_portfolio()

    rows: list[dict[str, Any]] = []
    for opportunity_type, group in opportunities.groupby("opportunity_type", sort=False):
        playbook = OPPORTUNITY_PLAYBOOK.get(opportunity_type, {})
        expected_value = float(group["expected_value"].sum())
        target_accounts = int(group["account_id"].nunique())
        priority = float(group["priority_score"].mean())
        high_priority = int(group[group["priority_score"].ge(50)]["account_id"].nunique())
        confidence_score = float(group["confidence_score"].mean())
        confidence = _confidence_label(confidence_score)
        reasons = _top_tokens(group["reason_codes"], limit=6)
        pfi_mix = _top_tokens(group["pfi_verdict"], limit=4)
        source_sections = sorted(
            {
                section
                for value in group["source_sections"].dropna().astype(str)
                for section in value.split("|")
                if section
            }
        )
        rows.append(
            {
                "portfolio_id": f"{cfg.client_id}:{cfg.period_month}:{opportunity_type}",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "opportunity_type": opportunity_type,
                "play_name": playbook.get("play_name", opportunity_type.replace("_", " ").title()),
                "target_accounts": target_accounts,
                "high_priority_accounts": high_priority,
                "expected_value": round(expected_value, 2),
                "avg_expected_value_per_account": round(expected_value / max(target_accounts, 1), 2),
                "avg_priority_score": round(priority, 1),
                "confidence": confidence,
                "confidence_score": round(confidence_score, 3),
                "top_reason_codes": "|".join(reasons),
                "pfi_mix": "|".join(pfi_mix),
                "source_sections": "|".join(source_sections),
                "audience_definition": playbook.get("audience_definition", "Ranked account opportunity audience."),
                "owner_role": playbook.get("owner_role", "CSM"),
                "recommended_channel": playbook.get("channel", "Review list"),
                "next_step": playbook.get("next_step", str(group.iloc[0].get("recommended_action", ""))),
                "primary_metric": playbook.get("primary_metric", _outcome_metric_for_opportunity(opportunity_type)),
                "model_version": "portfolio_v0_rules",
            }
        )

    portfolio = pd.DataFrame(rows).sort_values(
        ["expected_value", "target_accounts", "avg_priority_score"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    portfolio.insert(0, "priority_rank", range(1, len(portfolio) + 1))
    return portfolio


def build_executive_scorecard(
    features: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    relationship_segments: pd.DataFrame,
    segment_summary: pd.DataFrame,
    opportunity_portfolio: pd.DataFrame,
    action_plan: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    campaign_targets: pd.DataFrame,
    outcome_summary: pd.DataFrame,
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Build a RAG scorecard that turns engine outputs into strategy KPIs."""
    cfg = config or EngineConfig()
    account_count = _unique_count(features, "account_id")
    quality_score = float(data_quality.get("quality_score", 0) or 0)

    pfi_rows = len(pfi_verdicts) if pfi_verdicts is not None else 0
    primary_share = _pct(
        int(pfi_verdicts["pfi_verdict"].eq("Primary with us").sum()) if pfi_rows and "pfi_verdict" in pfi_verdicts else 0,
        pfi_rows,
    )
    competitor_share = _pct(
        int(pfi_verdicts["pfi_verdict"].isin(["Split", "Competitor-primary"]).sum()) if pfi_rows and "pfi_verdict" in pfi_verdicts else 0,
        pfi_rows,
    )
    activation_accounts = _segment_account_count(segment_summary, {"Activate", "Grow", "Expand"})
    high_risk_accounts = _segment_risk_count(relationship_segments, {"high"})
    opportunity_value = _sum_numeric(opportunity_portfolio, "expected_value")
    target_accounts = _unique_count(campaign_targets, "account_id")
    measurement_rows = len(measurement_plan) if measurement_plan is not None else 0
    measured_rows = len(outcome_summary) if outcome_summary is not None else 0
    measurement_readiness = _pct(measurement_rows, max(len(action_plan) if action_plan is not None else 0, 1))
    if measured_rows:
        avg_outcome_rate = round(float(pd.to_numeric(outcome_summary["test_outcome_rate"], errors="coerce").fillna(0).mean()) * 100, 1)
    else:
        avg_outcome_rate = None

    rows = [
        _scorecard_row(
            cfg,
            domain="Data Trust",
            metric_name="Monthly data readiness",
            metric_value=quality_score,
            metric_display=f"{quality_score:.1f}",
            benchmark="Green >= 80; Amber >= 65",
            score=quality_score,
            interpretation=(
                "Data coverage is strong enough for client presentation."
                if quality_score >= 80
                else "Review data warnings before client presentation."
            ),
            recommended_focus="Resolve intake/data-quality warnings first." if quality_score < 80 else "Proceed to relationship strategy review.",
            owner_role="Analyst",
            source_artifacts="data_quality.json|intake_work_order.csv",
        ),
        _scorecard_row(
            cfg,
            domain="Relationship Primacy",
            metric_name="Primary-with-us share",
            metric_value=primary_share,
            metric_display=f"{primary_share:.1f}%",
            benchmark="Green >= 50%; Amber >= 30%",
            score=min(primary_share * 2, 100),
            interpretation=f"{primary_share:.1f}% of scored account-months look primary with us.",
            recommended_focus="Protect payroll-primary households and watch for external pull.",
            owner_role="CSM",
            source_artifacts="pfi_verdicts.csv|relationship_segments.csv",
        ),
        _scorecard_row(
            cfg,
            domain="Competitive Risk",
            metric_name="Split or competitor-primary share",
            metric_value=competitor_share,
            metric_display=f"{competitor_share:.1f}%",
            benchmark="Green <= 20%; Amber <= 40%",
            score=max(100 - competitor_share * 2, 0),
            interpretation=f"{competitor_share:.1f}% of scored relationships show split-wallet or competitor-primary behavior.",
            recommended_focus="Prioritize competitor win-back and deposit-retention plays.",
            owner_role="CSM + Marketing",
            source_artifacts="pfi_verdicts.csv|segment_summary.csv|opportunity_portfolio.csv",
            inverse=True,
        ),
        _scorecard_row(
            cfg,
            domain="Activation",
            metric_name="Activation / growth audience",
            metric_value=activation_accounts,
            metric_display=f"{activation_accounts:,}",
            benchmark="Opportunity exists when > 0 accounts",
            score=100 if activation_accounts > 0 else 40,
            interpretation=f"{activation_accounts:,} account(s) sit in activation, growth, or expansion segment groups.",
            recommended_focus="Use segment summary to choose debit activation, payroll conversion, or relationship expansion.",
            owner_role="Marketing",
            source_artifacts="segment_summary.csv|campaign_targets.csv",
        ),
        _scorecard_row(
            cfg,
            domain="Retention Risk",
            metric_name="High-risk relationship accounts",
            metric_value=high_risk_accounts,
            metric_display=f"{high_risk_accounts:,}",
            benchmark="Lower is better; review all high-risk accounts",
            score=max(100 - _pct(high_risk_accounts, max(account_count, 1)) * 2, 0),
            interpretation=f"{high_risk_accounts:,} account(s) are tagged high-risk in relationship segmentation.",
            recommended_focus="Route high-risk segments to retention/save-list review.",
            owner_role="CSM + banker team",
            source_artifacts="relationship_segments.csv|action_plan.csv",
            inverse=True,
        ),
        _scorecard_row(
            cfg,
            domain="Opportunity Economics",
            metric_name="Modeled opportunity value",
            metric_value=opportunity_value,
            metric_display=f"${opportunity_value:,.0f}",
            benchmark="Green when actionable value exists",
            score=100 if opportunity_value > 0 and target_accounts > 0 else 35,
            interpretation=f"The current opportunity portfolio models ${opportunity_value:,.0f} across {target_accounts:,} target account(s).",
            recommended_focus="Use the top-ranked action plan rows to decide which value pool to pursue first.",
            owner_role="Executive / CSM",
            source_artifacts="opportunity_portfolio.csv|action_plan.csv",
        ),
        _scorecard_row(
            cfg,
            domain="Measurement",
            metric_name="Measurement design coverage",
            metric_value=measurement_readiness,
            metric_display=f"{measurement_readiness:.1f}%",
            benchmark="Green >= 90%; Amber >= 60%",
            score=measurement_readiness,
            interpretation=f"{measurement_rows:,} action play(s) have measurement rows.",
            recommended_focus="Preserve action_id and measurement_id through campaign execution.",
            owner_role="Marketing + Data",
            source_artifacts="measurement_plan.csv|measurement_baseline.csv",
        ),
        _scorecard_row(
            cfg,
            domain="Outcomes",
            metric_name="Measured outcome rate",
            metric_value=avg_outcome_rate if avg_outcome_rate is not None else "",
            metric_display=f"{avg_outcome_rate:.1f}%" if avg_outcome_rate is not None else "Not yet measured",
            benchmark="Measured on next run after campaign targets exist",
            score=avg_outcome_rate if avg_outcome_rate is not None else 50,
            interpretation=(
                f"Prior campaign targets show an average {avg_outcome_rate:.1f}% measured outcome rate."
                if avg_outcome_rate is not None
                else "No prior campaign package was available for outcome measurement."
            ),
            recommended_focus="Use this run as the baseline and compare outcomes next month." if avg_outcome_rate is None else "Scale plays with positive measured movement.",
            owner_role="CSM + Analyst",
            source_artifacts="outcome_summary.csv|campaign_targets.csv",
            neutral=avg_outcome_rate is None,
        ),
    ]
    return pd.DataFrame(rows)


def build_strategy_roadmap(
    executive_scorecard: pd.DataFrame,
    action_plan: pd.DataFrame,
    segment_summary: pd.DataFrame,
    opportunity_portfolio: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a Now/Next/Later execution roadmap from scorecard and action rows."""
    cfg = config or EngineConfig()
    rows: list[dict[str, Any]] = []

    for row in (action_plan.head(3).to_dict("records") if action_plan is not None and not action_plan.empty else []):
        rank = int(row.get("priority_rank", len(rows) + 1) or len(rows) + 1)
        phase = "Now" if rank == 1 else "Next"
        rows.append(
            {
                "roadmap_id": f"{cfg.client_id}:{cfg.period_month}:roadmap:{len(rows)+1}",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "phase": phase,
                "priority_rank": len(rows) + 1,
                "initiative": row.get("play_name", ""),
                "initiative_type": "action_play",
                "source_signal": row.get("opportunity_type", ""),
                "target_accounts": row.get("target_accounts", 0),
                "expected_value": row.get("expected_value", 0.0),
                "owner_role": row.get("owner_role", ""),
                "first_action": row.get("next_step", ""),
                "dependency": "Validate suppressions and preserve action_id in execution.",
                "proof_metric": _roadmap_metric(row, measurement_plan),
                "source_artifacts": "action_plan.csv|campaign_targets.csv|measurement_plan.csv",
                "status": row.get("status", "ready_for_review"),
                "model_version": "strategy_roadmap_v0_rules",
            }
        )

    weak_scorecard = executive_scorecard[
        executive_scorecard["rag_status"].astype(str).isin(["Red", "Amber"])
    ] if executive_scorecard is not None and not executive_scorecard.empty else pd.DataFrame()
    for row in weak_scorecard.head(3).to_dict("records"):
        rows.append(
            {
                "roadmap_id": f"{cfg.client_id}:{cfg.period_month}:roadmap:{len(rows)+1}",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "phase": "Next" if len(rows) < 4 else "Later",
                "priority_rank": len(rows) + 1,
                "initiative": f"Improve {row.get('domain', 'scorecard')} posture",
                "initiative_type": "scorecard_gap",
                "source_signal": row.get("metric_name", ""),
                "target_accounts": "",
                "expected_value": "",
                "owner_role": row.get("owner_role", ""),
                "first_action": row.get("recommended_focus", ""),
                "dependency": "Confirm source artifact and owner before client commitment.",
                "proof_metric": row.get("metric_name", ""),
                "source_artifacts": row.get("source_artifacts", ""),
                "status": "needs_strategy_review",
                "model_version": "strategy_roadmap_v0_rules",
            }
        )

    if not rows and segment_summary is not None and not segment_summary.empty:
        lead = segment_summary.iloc[0].to_dict()
        rows.append(
            {
                "roadmap_id": f"{cfg.client_id}:{cfg.period_month}:roadmap:1",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "phase": "Now",
                "priority_rank": 1,
                "initiative": f"Review {lead.get('relationship_segment', 'lead segment')}",
                "initiative_type": "segment_review",
                "source_signal": lead.get("segment_group", ""),
                "target_accounts": lead.get("account_count", 0),
                "expected_value": lead.get("total_expected_value", 0.0),
                "owner_role": "CSM + Analyst",
                "first_action": lead.get("top_next_best_motion", "Review segment summary."),
                "dependency": "Validate targetability and data confidence.",
                "proof_metric": "segment movement next month",
                "source_artifacts": "segment_summary.csv|relationship_segments.csv",
                "status": "ready_for_review",
                "model_version": "strategy_roadmap_v0_rules",
            }
        )
    return pd.DataFrame(rows) if rows else _empty_strategy_roadmap()


def build_action_plan(
    opportunity_portfolio: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Turn portfolio rows into campaign/consulting plays."""
    cfg = config or EngineConfig()
    if opportunity_portfolio.empty:
        return _empty_action_plan()

    rows: list[dict[str, Any]] = []
    for row in opportunity_portfolio.to_dict("records"):
        opportunity_type = str(row.get("opportunity_type", ""))
        playbook = OPPORTUNITY_PLAYBOOK.get(opportunity_type, {})
        rank = int(row.get("priority_rank", len(rows) + 1) or len(rows) + 1)
        target_accounts = int(row.get("target_accounts", 0) or 0)
        confidence = str(row.get("confidence", "low") or "low")
        rows.append(
            {
                "action_id": f"{cfg.client_id}:{cfg.period_month}:action:{rank}",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "priority_rank": rank,
                "play_name": row.get("play_name", opportunity_type.replace("_", " ").title()),
                "opportunity_type": opportunity_type,
                "objective": _action_objective(opportunity_type),
                "target_accounts": target_accounts,
                "expected_value": row.get("expected_value", 0.0),
                "confidence": confidence,
                "audience_definition": row.get("audience_definition", ""),
                "owner_role": row.get("owner_role", playbook.get("owner_role", "CSM")),
                "recommended_channel": row.get("recommended_channel", playbook.get("channel", "Review list")),
                "next_step": row.get("next_step", ""),
                "talk_track": _talk_track(opportunity_type, target_accounts, row.get("expected_value", 0.0)),
                "target_list_ref": f"opportunities.csv#{opportunity_type}",
                "measurement_id": f"{cfg.client_id}:{cfg.period_month}:measure:{rank}",
                "status": "ready_for_review" if confidence != "low" else "needs_data_review",
                "model_version": "action_plan_v0_rules",
            }
        )
    return pd.DataFrame(rows)


def build_measurement_plan(
    action_plan: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create measurement design rows for each recommended play."""
    cfg = config or EngineConfig()
    if action_plan.empty:
        return _empty_measurement_plan()

    rows: list[dict[str, Any]] = []
    for row in action_plan.to_dict("records"):
        opportunity_type = str(row.get("opportunity_type", ""))
        playbook = OPPORTUNITY_PLAYBOOK.get(opportunity_type, {})
        target_accounts = int(row.get("target_accounts", 0) or 0)
        holdout_pct = 0.10 if target_accounts >= 500 else 0.0
        holdout_accounts = int(round(target_accounts * holdout_pct))
        rows.append(
            {
                "measurement_id": row.get("measurement_id", ""),
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "action_id": row.get("action_id", ""),
                "play_name": row.get("play_name", ""),
                "opportunity_type": opportunity_type,
                "recommended_design": "holdout" if holdout_pct else "pre_post_or_matched_control",
                "holdout_pct": holdout_pct,
                "holdout_accounts": holdout_accounts,
                "test_accounts": max(target_accounts - holdout_accounts, 0),
                "primary_metric": playbook.get("primary_metric", _outcome_metric_for_opportunity(opportunity_type)),
                "secondary_metrics": "|".join(_secondary_metrics(opportunity_type)),
                "baseline_window": "prior_90d",
                "measurement_windows": "30d|60d|90d",
                "success_definition": _success_definition(opportunity_type),
                "model_version": "measurement_plan_v0_rules",
            }
        )
    return pd.DataFrame(rows)


def build_campaign_targets(
    opportunities: pd.DataFrame,
    action_plan: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    features: pd.DataFrame,
    pfi_verdicts: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create account-level target lists ready for campaign execution."""
    cfg = config or EngineConfig()
    if opportunities.empty or action_plan.empty:
        return _empty_campaign_targets()

    action_cols = [
        "action_id",
        "measurement_id",
        "priority_rank",
        "play_name",
        "opportunity_type",
        "owner_role",
        "recommended_channel",
        "status",
    ]
    target = opportunities.merge(
        action_plan[[col for col in action_cols if col in action_plan.columns]],
        on="opportunity_type",
        how="left",
        suffixes=("", "_action"),
    )

    metric_cols = [
        "account_id",
        "period_month",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "unique_merchants",
        "balance",
        "has_debit",
        "business_flag",
        "branch",
        "product_code",
        "product_count",
        "external_intensity",
        "payroll_detected",
        "engagement_tier",
    ]
    if not features.empty:
        target = target.merge(
            features[[col for col in metric_cols if col in features.columns]],
            on=["account_id", "period_month"],
            how="left",
            suffixes=("", "_feature"),
        )
    if not pfi_verdicts.empty:
        pfi_cols = ["account_id", "period_month", "pfi_score", "internal_score", "external_score"]
        target = target.merge(
            pfi_verdicts[[col for col in pfi_cols if col in pfi_verdicts.columns]],
            on=["account_id", "period_month"],
            how="left",
        )

    if not measurement_plan.empty:
        measurement_cols = ["measurement_id", "recommended_design", "holdout_pct", "primary_metric"]
        target = target.merge(
            measurement_plan[[col for col in measurement_cols if col in measurement_plan.columns]],
            on="measurement_id",
            how="left",
        )
    else:
        target["holdout_pct"] = 0.0
        target["recommended_design"] = "pre_post_or_matched_control"

    target = target.sort_values(
        ["priority_rank", "priority_score", "expected_value"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    target["target_rank_within_play"] = target.groupby("opportunity_type").cumcount() + 1
    target["measurement_group"] = target.apply(
        lambda row: _measurement_group(
            row.get("action_id", ""),
            row.get("account_id", ""),
            float(row.get("holdout_pct", 0) or 0),
        ),
        axis=1,
    )
    target["target_status"] = np.where(
        target["confidence"].astype(str).str.lower().eq("low"),
        "needs_review",
        "ready",
    )

    ordered = [
        "action_id",
        "measurement_id",
        "client_id",
        "period_month",
        "play_name",
        "opportunity_type",
        "target_rank_within_play",
        "account_id",
        "measurement_group",
        "target_status",
        "priority_score",
        "expected_value",
        "confidence",
        "pfi_verdict",
        "pfi_score",
        "reason_codes",
        "recommended_action",
        "owner_role",
        "recommended_channel",
        "primary_metric",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "unique_merchants",
        "balance",
        "has_debit",
        "business_flag",
        "branch",
        "product_code",
        "product_count",
        "external_intensity",
        "payroll_detected",
        "engagement_tier",
        "model_version",
    ]
    target["model_version"] = "campaign_targets_v0_rules"
    return target[[col for col in ordered if col in target.columns]]


def build_measurement_baseline(
    campaign_targets: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Aggregate baseline metrics by action for future outcome comparison."""
    cfg = config or EngineConfig()
    if campaign_targets.empty:
        return _empty_measurement_baseline()

    df = campaign_targets.copy()
    for col in [
        "expected_value",
        "priority_score",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_amount",
        "external_fi_amount",
        "balance",
        "external_intensity",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "payroll_detected" in df.columns:
        payroll = df["payroll_detected"].astype(str).str.lower().isin({"true", "1", "yes", "y"})
        df["_payroll_detected_int"] = payroll.astype(int)
    else:
        df["_payroll_detected_int"] = 0

    rows: list[dict[str, Any]] = []
    group_cols = ["measurement_id", "action_id", "play_name", "opportunity_type"]
    for keys, group in df.groupby(group_cols, dropna=False):
        measurement_id, action_id, play_name, opportunity_type = keys
        test_accounts = int(group[group["measurement_group"].eq("test")]["account_id"].nunique())
        control_accounts = int(group[group["measurement_group"].eq("holdout")]["account_id"].nunique())
        rows.append(
            {
                "measurement_id": measurement_id,
                "action_id": action_id,
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "play_name": play_name,
                "opportunity_type": opportunity_type,
                "target_accounts": int(group["account_id"].nunique()),
                "test_accounts": test_accounts,
                "control_accounts": control_accounts,
                "baseline_expected_value": round(float(group["expected_value"].sum()), 2),
                "baseline_avg_priority_score": round(float(group["priority_score"].mean()), 2),
                "baseline_total_spend": round(float(group.get("spend_amount", pd.Series(dtype=float)).sum()), 2),
                "baseline_total_credit": round(float(group.get("credit_amount", pd.Series(dtype=float)).sum()), 2),
                "baseline_total_external_fi_amount": round(float(group.get("external_fi_amount", pd.Series(dtype=float)).sum()), 2),
                "baseline_avg_txn_count": round(float(group.get("txn_count", pd.Series(dtype=float)).mean()), 2),
                "baseline_avg_active_days": round(float(group.get("active_days", pd.Series(dtype=float)).mean()), 2),
                "baseline_payroll_detected_accounts": int(group["_payroll_detected_int"].sum()),
                "baseline_avg_balance": round(float(group.get("balance", pd.Series(dtype=float)).mean()), 2),
                "baseline_window": "current_account_month",
                "future_outcome_join_key": f"{measurement_id}|account_id",
                "model_version": "measurement_baseline_v0_rules",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["baseline_expected_value", "target_accounts"],
        ascending=[False, False],
    ).reset_index(drop=True)


def evaluate_outcomes(
    prior_campaign_targets: pd.DataFrame | None,
    current_features: pd.DataFrame,
    current_pfi_verdicts: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Compare prior campaign targets to current-period account behavior."""
    cfg = config or EngineConfig()
    if prior_campaign_targets is None or prior_campaign_targets.empty or current_features.empty:
        return _empty_outcome_results()

    prior = prior_campaign_targets.copy()
    prior["account_id"] = prior["account_id"].astype(str)
    current = current_features.copy()
    current["account_id"] = current["account_id"].astype(str)
    keep_current = [
        "account_id",
        "period_month",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "unique_merchants",
        "balance",
        "has_debit",
        "product_count",
        "external_intensity",
        "payroll_detected",
        "engagement_tier",
    ]
    joined = prior.merge(
        current[[col for col in keep_current if col in current.columns]],
        on="account_id",
        how="left",
        suffixes=("_baseline", "_current"),
    )
    if "period_month_baseline" not in joined.columns and "period_month" in prior.columns:
        joined["period_month_baseline"] = prior["period_month"]
    if "period_month_current" not in joined.columns:
        joined["period_month_current"] = _period_label(cfg.period_month)

    if current_pfi_verdicts is not None and not current_pfi_verdicts.empty:
        pfi = current_pfi_verdicts.copy()
        pfi["account_id"] = pfi["account_id"].astype(str)
        joined = joined.merge(
            pfi[["account_id", "pfi_verdict", "pfi_score", "confidence"]].rename(
                columns={
                    "pfi_verdict": "current_pfi_verdict",
                    "pfi_score": "current_pfi_score",
                    "confidence": "current_pfi_confidence",
                }
            ),
            on="account_id",
            how="left",
        )

    for col in [
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "unique_merchants",
        "balance",
        "product_count",
        "external_intensity",
    ]:
        base_col = col if col in joined.columns else f"{col}_baseline"
        current_col = f"{col}_current"
        if base_col in joined.columns:
            joined[f"baseline_{col}"] = pd.to_numeric(joined[base_col], errors="coerce").fillna(0.0)
        else:
            joined[f"baseline_{col}"] = 0.0
        if current_col in joined.columns:
            joined[f"current_{col}"] = pd.to_numeric(joined[current_col], errors="coerce").fillna(0.0)
        else:
            joined[f"current_{col}"] = 0.0
        joined[f"delta_{col}"] = joined[f"current_{col}"] - joined[f"baseline_{col}"]

    joined["baseline_payroll_detected"] = _bool_column(joined, "payroll_detected")
    joined["current_payroll_detected"] = _bool_column(joined, "payroll_detected_current")
    joined["current_account_found"] = joined["period_month_current"].notna()
    joined["outcome_flag"] = joined.apply(_outcome_flag_for_row, axis=1)
    joined["outcome_status"] = np.where(joined["outcome_flag"], "improved", "not_yet_measured")

    ordered = [
        "measurement_id",
        "action_id",
        "client_id",
        "account_id",
        "play_name",
        "opportunity_type",
        "measurement_group",
        "period_month_baseline",
        "period_month_current",
        "target_status",
        "priority_score",
        "expected_value",
        "confidence",
        "pfi_verdict",
        "current_pfi_verdict",
        "current_pfi_score",
        "primary_metric",
        "baseline_txn_count",
        "current_txn_count",
        "delta_txn_count",
        "baseline_spend_amount",
        "current_spend_amount",
        "delta_spend_amount",
        "baseline_credit_amount",
        "current_credit_amount",
        "delta_credit_amount",
        "baseline_external_fi_amount",
        "current_external_fi_amount",
        "delta_external_fi_amount",
        "baseline_balance",
        "current_balance",
        "delta_balance",
        "baseline_payroll_detected",
        "current_payroll_detected",
        "current_account_found",
        "outcome_flag",
        "outcome_status",
    ]
    joined["client_id"] = cfg.client_id or joined.get("client_id", "")
    return joined[[col for col in ordered if col in joined.columns]].reset_index(drop=True)


def build_outcome_summary(
    outcome_results: pd.DataFrame,
    prior_measurement_baseline: pd.DataFrame | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Roll account-level outcome results up to each action/measurement."""
    cfg = config or EngineConfig()
    if outcome_results.empty:
        return _empty_outcome_summary()

    rows: list[dict[str, Any]] = []
    for keys, group in outcome_results.groupby(
        ["measurement_id", "action_id", "play_name", "opportunity_type"],
        dropna=False,
    ):
        measurement_id, action_id, play_name, opportunity_type = keys
        test = group[group["measurement_group"].astype(str).str.lower().eq("test")]
        holdout = group[group["measurement_group"].astype(str).str.lower().eq("holdout")]
        test_accounts = int(test["account_id"].nunique())
        holdout_accounts = int(holdout["account_id"].nunique())
        test_outcomes = int(test["outcome_flag"].fillna(False).sum()) if not test.empty else 0
        holdout_outcomes = int(holdout["outcome_flag"].fillna(False).sum()) if not holdout.empty else 0
        test_rate = test_outcomes / test_accounts if test_accounts else 0.0
        holdout_rate = holdout_outcomes / holdout_accounts if holdout_accounts else 0.0
        rows.append(
            {
                "measurement_id": measurement_id,
                "action_id": action_id,
                "client_id": cfg.client_id,
                "outcome_period_month": _period_label(cfg.period_month),
                "play_name": play_name,
                "opportunity_type": opportunity_type,
                "target_accounts": int(group["account_id"].nunique()),
                "test_accounts": test_accounts,
                "test_outcome_accounts": test_outcomes,
                "test_outcome_rate": round(test_rate, 4),
                "holdout_accounts": holdout_accounts,
                "holdout_outcome_accounts": holdout_outcomes,
                "holdout_outcome_rate": round(holdout_rate, 4),
                "lift_vs_holdout": round(test_rate - holdout_rate, 4) if holdout_accounts else None,
                "avg_delta_txn_count": round(float(group["delta_txn_count"].mean()), 3),
                "avg_delta_spend_amount": round(float(group["delta_spend_amount"].mean()), 2),
                "avg_delta_credit_amount": round(float(group["delta_credit_amount"].mean()), 2),
                "avg_delta_external_fi_amount": round(float(group["delta_external_fi_amount"].mean()), 2),
                "avg_delta_balance": round(float(group["delta_balance"].mean()), 2),
                "measured_expected_value": round(float(group["expected_value"].sum()), 2),
                "measurement_status": "measured_with_holdout" if holdout_accounts else "measured_pre_post",
                "interpretation": _outcome_interpretation(test_rate, holdout_rate, holdout_accounts),
                "model_version": "outcome_summary_v0_rules",
            }
        )

    summary = pd.DataFrame(rows)
    if prior_measurement_baseline is not None and not prior_measurement_baseline.empty:
        baseline = prior_measurement_baseline.copy()
        cols = [
            "measurement_id",
            "baseline_expected_value",
            "baseline_avg_priority_score",
            "baseline_total_spend",
            "baseline_total_credit",
            "baseline_total_external_fi_amount",
        ]
        summary = summary.merge(
            baseline[[col for col in cols if col in baseline.columns]],
            on="measurement_id",
            how="left",
        )
    return summary.sort_values(
        ["measured_expected_value", "target_accounts"],
        ascending=[False, False],
    ).reset_index(drop=True)


def build_intelligence_delta_report(
    account_intelligence_profile: pd.DataFrame,
    opportunities: pd.DataFrame,
    opportunity_portfolio: pd.DataFrame,
    data_quality: dict[str, Any],
    *,
    prior_account_intelligence_profile: pd.DataFrame | None = None,
    prior_opportunities: pd.DataFrame | None = None,
    prior_opportunity_portfolio: pd.DataFrame | None = None,
    prior_data_quality: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Compare current intelligence outputs to the prior monthly package."""
    cfg = config or EngineConfig()
    prior_period = _prior_period_from_frames(
        prior_account_intelligence_profile,
        prior_opportunities,
        prior_opportunity_portfolio,
    )
    current_period = _period_label(cfg.period_month)
    rows: list[dict[str, Any]] = []

    has_prior = any(
        [
            prior_account_intelligence_profile is not None and not prior_account_intelligence_profile.empty,
            prior_opportunities is not None and not prior_opportunities.empty,
            prior_opportunity_portfolio is not None and not prior_opportunity_portfolio.empty,
            bool(prior_data_quality),
        ]
    )
    if not has_prior:
        rows.append(
            _delta_report_row(
                cfg,
                rank=1,
                prior_period_month="",
                current_period_month=current_period,
                delta_type="baseline_run",
                entity_type="run",
                entity_id=f"{cfg.client_id}:{current_period}:baseline",
                account_id="",
                opportunity_type="",
                metric_name="prior_package",
                prior_value="",
                current_value="not_available",
                delta_value="",
                prior_status="missing",
                current_status="baseline_created",
                movement_direction="baseline",
                severity="info",
                evidence_summary="No prior intelligence package was supplied; this run becomes the comparison baseline.",
                recommended_action="Use this package as the baseline for next month's intelligence delta report.",
                source_artifacts="run_summary.json|analysis_package_index.csv",
            )
        )

    if prior_data_quality:
        prior_score = float(prior_data_quality.get("quality_score", 0) or 0)
        current_score = float(data_quality.get("quality_score", 0) or 0)
        rows.append(
            _delta_report_row(
                cfg,
                rank=len(rows) + 1,
                prior_period_month=prior_period,
                current_period_month=current_period,
                delta_type="quality_score_delta",
                entity_type="run",
                entity_id=f"{cfg.client_id}:{current_period}:quality",
                account_id="",
                opportunity_type="",
                metric_name="quality_score",
                prior_value=round(prior_score, 1),
                current_value=round(current_score, 1),
                delta_value=round(current_score - prior_score, 1),
                prior_status=str(prior_data_quality.get("confidence", "")),
                current_status=str(data_quality.get("confidence", "")),
                movement_direction=_movement_direction(current_score - prior_score, positive_label="improved", negative_label="declined"),
                severity="review" if current_score < 70 or current_score < prior_score else "info",
                evidence_summary=f"Quality score moved from {prior_score:.1f} to {current_score:.1f}.",
                recommended_action="Review data-quality warnings before comparing business movement." if current_score < 70 else "Use current quality score as sufficient context for movement review.",
                source_artifacts="data_quality.json",
            )
        )

    rows.extend(
        _portfolio_delta_rows(
            cfg,
            current_portfolio=opportunity_portfolio,
            prior_portfolio=prior_opportunity_portfolio,
            prior_period_month=prior_period,
            current_period_month=current_period,
            start_rank=len(rows) + 1,
        )
    )
    rows.extend(
        _account_profile_delta_rows(
            cfg,
            current_profile=account_intelligence_profile,
            prior_profile=prior_account_intelligence_profile,
            prior_period_month=prior_period,
            current_period_month=current_period,
            start_rank=len(rows) + 1,
        )
    )
    rows.extend(
        _opportunity_target_delta_rows(
            cfg,
            current_opportunities=opportunities,
            prior_opportunities=prior_opportunities,
            prior_period_month=prior_period,
            current_period_month=current_period,
            start_rank=len(rows) + 1,
        )
    )

    if not rows:
        return _empty_intelligence_delta_report()
    return pd.DataFrame(rows, columns=_intelligence_delta_report_columns()).reset_index(drop=True)


def generate_insights(
    opportunities: pd.DataFrame,
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> list[dict[str, Any]]:
    """Aggregate opportunity rows into standardized insight objects."""
    cfg = config or EngineConfig()
    insights: list[dict[str, Any]] = []
    if opportunities.empty:
        return [
            {
                "insight_id": "ti.no_ranked_opportunities",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "domain": "Executive Synthesis",
                "section_id": "ti.engine",
                "population": "all scored accounts",
                "finding": "No ranked opportunities crossed the V1 rule thresholds.",
                "metric_name": "opportunity_count",
                "current_value": 0,
                "affected_accounts": 0,
                "opportunity_amount": 0.0,
                "confidence": data_quality.get("confidence", "low"),
                "confidence_reasons": data_quality.get("warnings", []),
                "recommended_action": "Review data coverage and thresholds before campaign selection.",
                "source_sections": ["ti.engine"],
            }
        ]

    for opportunity_type, group in opportunities.groupby("opportunity_type", sort=False):
        affected = int(group["account_id"].nunique())
        total_value = float(group["expected_value"].sum())
        avg_priority = float(group["priority_score"].mean())
        confidence = _confidence_label(float(group["confidence_score"].mean()))
        top_reasons = _top_tokens(group["reason_codes"])
        action = str(group.iloc[0]["recommended_action"])
        source_sections = sorted(
            {
                section
                for value in group["source_sections"].dropna().astype(str)
                for section in value.split("|")
                if section
            }
        )
        insights.append(
            {
                "insight_id": f"ti.{opportunity_type}",
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "domain": _domain_for_opportunity(opportunity_type),
                "section_id": "ti.engine",
                "population": "ranked account opportunities",
                "finding": f"{affected} accounts qualify for {opportunity_type.replace('_', ' ')}.",
                "metric_name": "expected_value",
                "current_value": round(total_value, 2),
                "affected_accounts": affected,
                "opportunity_amount": round(total_value, 2),
                "priority_score": round(avg_priority, 1),
                "confidence": confidence,
                "confidence_reasons": top_reasons,
                "recommended_action": action,
                "target_list_ref": f"opportunities.csv#{opportunity_type}",
                "source_tables": ["mart.account_month_features", "mart.pfi_verdicts"],
                "source_sections": source_sections,
                "measurement": {
                    "recommended_design": "holdout_or_matched_control",
                    "windows": ["30d", "60d", "90d"],
                    "primary_metric": _outcome_metric_for_opportunity(opportunity_type),
                },
            }
        )
    return sorted(insights, key=lambda item: item.get("opportunity_amount", 0), reverse=True)


def build_role_handoffs(
    action_plan: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    campaign_targets: pd.DataFrame,
    opportunity_portfolio: pd.DataFrame,
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Describe how each operator uses the completed intelligence package."""
    cfg = config or EngineConfig()
    quality_score = data_quality.get("quality_score", 0) or 0
    target_accounts = _unique_count(campaign_targets, "account_id")
    action_count = len(action_plan) if action_plan is not None else 0
    top_play = _top_play_name(action_plan, opportunity_portfolio)
    csm_status = "ready_for_client_review" if quality_score >= 70 and action_count else "review_before_client_use"
    analyst_status = "review_warnings" if data_quality.get("warnings") else "ready"
    activation_status = "ready" if target_accounts else "needs_audience_review"

    rows = [
        {
            "handoff_id": f"{cfg.client_id}:{cfg.period_month}:owner",
            "client_id": cfg.client_id,
            "period_month": cfg.period_month,
            "role": "Executive / product owner",
            "role_type": "operator",
            "decision_owned": "Decide whether this run is ready to become the client-facing intelligence package.",
            "primary_screen": "Intelligence tab",
            "outputs_used": "run_summary.json|data_quality_report.html|executive_brief.html",
            "export_artifact": "transactional_intelligence_package.xlsx",
            "first_action": "Confirm quality score, warnings, and top plays before client handoff.",
            "handoff_to": "CSM|Analyst",
            "success_metric": "approved package with clear next-step owner",
            "status": csm_status,
            "model_version": "role_handoff_v0_rules",
        },
        {
            "handoff_id": f"{cfg.client_id}:{cfg.period_month}:csm",
            "client_id": cfg.client_id,
            "period_month": cfg.period_month,
            "role": "CSM",
            "role_type": "relationship",
            "decision_owned": "Choose the client story and the one to three plays to recommend.",
            "primary_screen": "Consulting Story",
            "outputs_used": "executive_brief.html|action_plan.csv|opportunity_portfolio.csv|outcome_summary.csv",
            "export_artifact": "executive_brief.html",
            "first_action": (
                f"Lead with {top_play} and align the client on owner, channel, and measurement."
                if top_play
                else "Review readiness and ask the analyst for opportunity validation."
            ),
            "handoff_to": "Marketing|Client bankers",
            "success_metric": "client approves prioritized actions",
            "status": csm_status,
            "model_version": "role_handoff_v0_rules",
        },
        {
            "handoff_id": f"{cfg.client_id}:{cfg.period_month}:analyst",
            "client_id": cfg.client_id,
            "period_month": cfg.period_month,
            "role": "Analyst",
            "role_type": "validation",
            "decision_owned": "Validate mappings, reason codes, opportunity scores, and data caveats.",
            "primary_screen": "Analysis Objects",
            "outputs_used": "data_quality_report.html|file_ledger.csv|account_month_features.csv|pfi_verdicts.csv|opportunities.csv",
            "export_artifact": "transactional_intelligence_package.xlsx",
            "first_action": "Sample top opportunities, inspect reason codes, and document data warnings.",
            "handoff_to": "CSM",
            "success_metric": "validated assumptions and documented limitations",
            "status": analyst_status,
            "model_version": "role_handoff_v0_rules",
        },
        {
            "handoff_id": f"{cfg.client_id}:{cfg.period_month}:marketing",
            "client_id": cfg.client_id,
            "period_month": cfg.period_month,
            "role": "Marketing",
            "role_type": "activation",
            "decision_owned": "Activate the selected audiences while preserving measurement design.",
            "primary_screen": "Action Plan",
            "outputs_used": "campaign_targets.csv|measurement_plan.csv|measurement_baseline.csv",
            "export_artifact": "campaign_targets.csv",
            "first_action": "Load ready targets, suppress holdout rows, and tag the campaign with action_id.",
            "handoff_to": "CSM|Data team",
            "success_metric": "campaign launched with action_id and measurement_id retained",
            "status": activation_status,
            "model_version": "role_handoff_v0_rules",
        },
        {
            "handoff_id": f"{cfg.client_id}:{cfg.period_month}:data",
            "client_id": cfg.client_id,
            "period_month": cfg.period_month,
            "role": "Data / Snowflake",
            "role_type": "warehouse",
            "decision_owned": "Load reusable intelligence tables and expose them for reporting or APIs.",
            "primary_screen": "Download Intelligence Outputs",
            "outputs_used": "snowflake_manifest.json|snowflake_load.sql|README_SNOWFLAKE.html",
            "export_artifact": "snowflake_load.sql",
            "first_action": "Stage files, run foundation SQL, then execute snowflake_load.sql.",
            "handoff_to": "Analyst|Reporting",
            "success_metric": "warehouse tables loaded with run_id lineage",
            "status": "ready",
            "model_version": "role_handoff_v0_rules",
        },
        {
            "handoff_id": f"{cfg.client_id}:{cfg.period_month}:client_team",
            "client_id": cfg.client_id,
            "period_month": cfg.period_month,
            "role": "Client bankers / branch team",
            "role_type": "execution",
            "decision_owned": "Act on the banker-call or outreach list for selected plays.",
            "primary_screen": "Action Plan",
            "outputs_used": "campaign_targets.csv|action_plan.csv",
            "export_artifact": "campaign_targets.csv",
            "first_action": "Work the highest-priority accounts first and record disposition by action_id.",
            "handoff_to": "CSM",
            "success_metric": "completed outreach and captured outcomes",
            "status": activation_status,
            "model_version": "role_handoff_v0_rules",
        },
    ]
    return pd.DataFrame(rows)


def build_operating_control_plane(
    role_handoffs: pd.DataFrame,
    engine_readiness_assessment: pd.DataFrame,
    stakeholder_export_manifest: pd.DataFrame,
    executive_scorecard: pd.DataFrame,
    strategy_roadmap: pd.DataFrame,
    action_plan: pd.DataFrame,
    analysis_section_evidence_review: pd.DataFrame,
    data_quality: dict[str, Any],
    artifact_row_counts: dict[str, int] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create the role-by-role operating map for using the engine output."""
    cfg = config or EngineConfig()
    if role_handoffs is None or role_handoffs.empty:
        return _empty_operating_control_plane()

    export_rows = _export_row_counts(stakeholder_export_manifest)
    export_rows.update(artifact_row_counts or {})
    quality_score = float(data_quality.get("quality_score", 0) or 0)
    warning_count = len(data_quality.get("warnings") or [])
    top_play = _top_play_name(action_plan, None) or _top_roadmap_initiative(strategy_roadmap)
    action_count = len(action_plan) if action_plan is not None else 0
    review_sections = _section_review_status_counts(analysis_section_evidence_review)
    scorecard_focus = _scorecard_focus(executive_scorecard)

    rows: list[dict[str, Any]] = []
    for index, handoff in enumerate(role_handoffs.to_dict("records"), start=1):
        role = _trace_text(handoff.get("role"))
        role_type = _trace_text(handoff.get("role_type"))
        export_artifact = _trace_text(handoff.get("export_artifact"))
        blockers = _control_plane_blockers(role, role_type, engine_readiness_assessment)
        export_row_count = _control_export_row_count(export_artifact, export_rows)
        current_status = _trace_text(handoff.get("status")) or "unknown"
        client_use_status = _control_client_use_status(current_status, blockers)
        priority_level = _control_priority_level(index, role_type, current_status, blockers)
        operating_question = _control_operating_question(role, role_type)
        evidence_summary = _control_evidence_summary(
            role_type=role_type,
            quality_score=quality_score,
            warning_count=warning_count,
            top_play=top_play,
            action_count=action_count,
            export_row_count=export_row_count,
            scorecard_focus=scorecard_focus,
            review_sections=review_sections,
        )
        rows.append(
            {
                "control_rank": index,
                "client_id": cfg.client_id,
                "period_month": cfg.period_month,
                "workflow_lane": _control_workflow_lane(role_type),
                "role": role,
                "role_type": role_type,
                "operating_question": operating_question,
                "decision_owned": _trace_text(handoff.get("decision_owned")),
                "current_status": current_status,
                "client_use_status": client_use_status,
                "priority_level": priority_level,
                "open_first": _control_open_first(handoff),
                "supporting_outputs": _trace_text(handoff.get("outputs_used")),
                "export_artifact": export_artifact,
                "export_row_count": export_row_count,
                "evidence_summary": evidence_summary,
                "blocker_summary": "|".join(blockers),
                "next_action": _trace_text(handoff.get("first_action")),
                "success_metric": _trace_text(handoff.get("success_metric")),
                "handoff_to": _trace_text(handoff.get("handoff_to")),
                "source_artifacts": _control_source_artifacts(handoff, blockers),
                "snowflake_targets": _control_snowflake_targets(role_type),
                "model_version": "operating_control_plane_v0",
            }
        )
    return pd.DataFrame(rows, columns=_operating_control_plane_columns())


def build_user_interaction_map(
    role_handoffs: pd.DataFrame,
    operating_control_plane: pd.DataFrame,
    stakeholder_export_manifest: pd.DataFrame,
    analysis_review_board: pd.DataFrame,
    client_meeting_deck_blueprint: pd.DataFrame,
    engine_readiness_assessment: pd.DataFrame,
    data_team_load_plan: pd.DataFrame,
    action_plan: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Map users and roles to the exact outputs, decisions, and data handoffs they use."""
    cfg = config or EngineConfig()
    rows: list[dict[str, Any]] = []
    export_rows = _export_row_counts(stakeholder_export_manifest)
    readiness_by_area = _records_by_key(engine_readiness_assessment, "readiness_area")

    def add_row(
        *,
        user_role: str,
        workflow_lane: str,
        interaction_stage: str,
        primary_screen: str,
        open_first: str,
        artifact_name: str,
        file_name: str,
        artifact_format: str = "",
        output_layer: str = "",
        row_count: Any = "",
        target_table: str = "",
        delivery_mode: str = "",
        decision_supported: str = "",
        analysis_or_data_question: str = "",
        evidence_summary: str = "",
        source_section_ids: str = "",
        chart_or_visual_refs: str = "",
        downstream_use: str = "",
        owner_next_action: str = "",
        client_use_status: str = "",
        blocker_summary: str = "",
        proof_artifacts: str = "",
        source_artifacts: str = "",
    ) -> None:
        file_text = _trace_text(file_name) or _trace_text(artifact_name)
        artifact_key = _slug_token(Path(file_text).stem or artifact_name)
        layer, _consumer = ARTIFACT_LAYER_MAP.get(artifact_key, (output_layer or "Operating model", user_role))
        rows.append(
            {
                "interaction_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "user_role": _trace_text(user_role),
                "workflow_lane": _trace_text(workflow_lane),
                "interaction_stage": _trace_text(interaction_stage),
                "primary_screen": _trace_text(primary_screen),
                "open_first": _trace_text(open_first),
                "artifact_name": artifact_key,
                "file_name": file_text,
                "artifact_format": _trace_text(artifact_format) or Path(file_text).suffix.lower().lstrip(".") or "table",
                "output_layer": _trace_text(output_layer) or layer,
                "row_count": _safe_int_value(row_count, default=0) if _trace_text(row_count) else "",
                "target_table": _trace_text(target_table) or _target_table_for_artifact(artifact_key),
                "delivery_mode": _trace_text(delivery_mode) or _delivery_mode_for_file(file_text),
                "decision_supported": _trace_text(decision_supported),
                "analysis_or_data_question": _trace_text(analysis_or_data_question),
                "evidence_summary": _trace_text(evidence_summary),
                "source_section_ids": _trace_text(source_section_ids),
                "chart_or_visual_refs": _trace_text(chart_or_visual_refs),
                "downstream_use": _trace_text(downstream_use),
                "owner_next_action": _trace_text(owner_next_action),
                "client_use_status": _trace_text(client_use_status),
                "blocker_summary": _trace_text(blocker_summary),
                "proof_artifacts": _trace_text(proof_artifacts),
                "source_artifacts": _trace_text(source_artifacts),
                "model_version": "user_interaction_map_v0",
            }
        )

    if operating_control_plane is not None and not operating_control_plane.empty:
        for row in operating_control_plane.to_dict("records"):
            export_artifact = _trace_text(row.get("export_artifact"))
            add_row(
                user_role=_trace_text(row.get("role")),
                workflow_lane=_trace_text(row.get("workflow_lane")),
                interaction_stage="open_control_lane",
                primary_screen=_trace_text(row.get("open_first")).split("->", 1)[0].strip() or "Intelligence tab",
                open_first=_trace_text(row.get("open_first")),
                artifact_name=export_artifact,
                file_name=export_artifact,
                row_count=row.get("export_row_count"),
                target_table=_trace_text(row.get("snowflake_targets")),
                delivery_mode="ui_download",
                decision_supported=_trace_text(row.get("decision_owned")),
                analysis_or_data_question=_trace_text(row.get("operating_question")),
                evidence_summary=_trace_text(row.get("evidence_summary")),
                downstream_use=_trace_text(row.get("success_metric")),
                owner_next_action=_trace_text(row.get("next_action")),
                client_use_status=_trace_text(row.get("client_use_status")),
                blocker_summary=_trace_text(row.get("blocker_summary")),
                proof_artifacts=_trace_text(row.get("supporting_outputs")),
                source_artifacts="operating_control_plane.csv|role_handoffs.csv",
            )

    if role_handoffs is not None and not role_handoffs.empty:
        for row in role_handoffs.to_dict("records"):
            for file_name in _unique_tokens([row.get("outputs_used"), row.get("export_artifact")])[:8]:
                add_row(
                    user_role=_trace_text(row.get("role")),
                    workflow_lane=_control_workflow_lane(_trace_text(row.get("role_type"))),
                    interaction_stage="role_handoff",
                    primary_screen=_trace_text(row.get("primary_screen")),
                    open_first=f"{_trace_text(row.get('primary_screen'))} -> {file_name}",
                    artifact_name=file_name,
                    file_name=file_name,
                    row_count=export_rows.get(file_name, ""),
                    delivery_mode="ui_download",
                    decision_supported=_trace_text(row.get("decision_owned")),
                    analysis_or_data_question=_trace_text(row.get("decision_owned")),
                    downstream_use=_trace_text(row.get("success_metric")),
                    owner_next_action=_trace_text(row.get("first_action")),
                    client_use_status=_trace_text(row.get("status")),
                    proof_artifacts=_trace_text(row.get("outputs_used")),
                    source_artifacts="role_handoffs.csv",
                )

    if stakeholder_export_manifest is not None and not stakeholder_export_manifest.empty:
        for row in stakeholder_export_manifest.to_dict("records"):
            file_name = _trace_text(row.get("file_name"))
            add_row(
                user_role=_trace_text(row.get("primary_role")),
                workflow_lane="Use export",
                interaction_stage="stakeholder_export",
                primary_screen="Downloads / Intelligence package",
                open_first=file_name,
                artifact_name=_trace_text(row.get("artifact_name")) or file_name,
                file_name=file_name,
                row_count=row.get("row_count"),
                delivery_mode="csv_export",
                decision_supported=_trace_text(row.get("use_case")),
                analysis_or_data_question=_trace_text(row.get("use_case")),
                downstream_use=_trace_text(row.get("use_case")),
                owner_next_action=_trace_text(row.get("first_action")),
                client_use_status=_trace_text(row.get("status")),
                proof_artifacts="stakeholder_export_manifest.csv",
                source_artifacts="stakeholder_export_manifest.csv",
            )

    if analysis_review_board is not None and not analysis_review_board.empty:
        for row in analysis_review_board.head(30).to_dict("records"):
            add_row(
                user_role="CSM / Analyst",
                workflow_lane="Review analysis",
                interaction_stage="analysis_section_review",
                primary_screen="Analysis Workbench",
                open_first="analysis_review_board.csv",
                artifact_name="analysis_review_board",
                file_name="analysis_review_board.csv",
                row_count=len(analysis_review_board),
                delivery_mode="html_workbench_and_csv",
                decision_supported=_trace_text(row.get("recommended_client_question")),
                analysis_or_data_question=_trace_text(row.get("what_is_analyzed")),
                evidence_summary=_trace_text(row.get("headline_insight")),
                source_section_ids=_trace_text(row.get("source_section_id")),
                chart_or_visual_refs=_trace_text(row.get("primary_chart_title")) or _trace_text(row.get("chart_titles")),
                downstream_use=_trace_text(row.get("client_story_role")),
                owner_next_action=_trace_text(row.get("analyst_next_step")) or _trace_text(row.get("data_team_next_step")),
                client_use_status=_trace_text(row.get("review_status")),
                blocker_summary=_trace_text(row.get("data_caveat")),
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                source_artifacts="analysis_review_board.csv",
            )

    if client_meeting_deck_blueprint is not None and not client_meeting_deck_blueprint.empty:
        for row in client_meeting_deck_blueprint.head(20).to_dict("records"):
            add_row(
                user_role=_trace_text(row.get("owner_role")) or "CSM",
                workflow_lane="Run client meeting",
                interaction_stage="meeting_story",
                primary_screen="Consulting Story / Meeting Blueprint",
                open_first="client_meeting_deck_blueprint.csv",
                artifact_name="client_meeting_deck_blueprint",
                file_name="client_meeting_deck_blueprint.csv",
                row_count=len(client_meeting_deck_blueprint),
                delivery_mode="html_workbench_and_csv",
                decision_supported=_trace_text(row.get("decision_prompt")),
                analysis_or_data_question=_trace_text(row.get("primary_message")),
                evidence_summary=_trace_text(row.get("metric_summary")),
                source_section_ids=_trace_text(row.get("source_section_id")),
                chart_or_visual_refs=_trace_text(row.get("visual_title")),
                downstream_use=_trace_text(row.get("meeting_phase")),
                owner_next_action=_trace_text(row.get("follow_up_action")),
                client_use_status=_trace_text(row.get("blueprint_status")),
                blocker_summary=_trace_text(row.get("data_caveat")),
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                source_artifacts="client_meeting_deck_blueprint.csv",
            )

    for readiness_area, row in readiness_by_area.items():
        add_row(
            user_role=_trace_text(row.get("owner_role")) or "Owner",
            workflow_lane="Approve readiness",
            interaction_stage="readiness_gate",
            primary_screen="Intelligence tab / Readiness",
            open_first="engine_readiness_assessment.csv",
            artifact_name="engine_readiness_assessment",
            file_name="engine_readiness_assessment.csv",
            row_count=len(engine_readiness_assessment) if engine_readiness_assessment is not None else "",
            delivery_mode="csv_export",
            decision_supported=f"Approve or resolve {readiness_area}.",
            analysis_or_data_question=_trace_text(row.get("evidence_summary")),
            evidence_summary=_trace_text(row.get("evidence_summary")),
            downstream_use=_trace_text(row.get("engine_layer")),
            owner_next_action=_trace_text(row.get("next_action")),
            client_use_status=_trace_text(row.get("client_use_status")),
            blocker_summary=_trace_text(row.get("blocking_issue")),
            proof_artifacts=_trace_text(row.get("proof_artifacts")),
            source_artifacts="engine_readiness_assessment.csv",
        )

    if not rows:
        return _empty_user_interaction_map()
    return pd.DataFrame(rows, columns=_user_interaction_map_columns())


def build_production_readiness_backlog(
    engine_readiness_assessment: pd.DataFrame,
    analysis_data_team_backlog: pd.DataFrame,
    analysis_metric_validation_queue: pd.DataFrame,
    layout_contract_draft_queue: pd.DataFrame,
    layout_contract_export_manifest: pd.DataFrame,
    monthly_file_requirements: pd.DataFrame,
    analysis_review_board: pd.DataFrame,
    user_interaction_map: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create one productization backlog across data, analysis, Snowflake, and delivery."""
    cfg = config or EngineConfig()
    columns = _production_readiness_backlog_columns()
    rows: list[dict[str, Any]] = []

    def add_row(
        *,
        workstream: str,
        priority_band: str,
        readiness_area: str,
        source_item_type: str,
        source_item_id: str,
        owner_role: str,
        problem_statement: str,
        business_impact: str,
        required_action: str,
        acceptance_criteria: str,
        blocking_artifacts: str = "",
        affected_sections: str = "",
        affected_outputs: str = "",
        snowflake_targets: str = "",
        client_use_status: str = "",
        proof_artifacts: str = "",
        source_artifacts: str = "",
    ) -> None:
        if not _trace_text(problem_statement) and not _trace_text(required_action):
            return
        rows.append(
            {
                "backlog_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "workstream": _trace_text(workstream),
                "priority_band": _production_backlog_priority(
                    priority_band,
                    client_use_status=client_use_status,
                    problem_statement=problem_statement,
                ),
                "readiness_area": _trace_text(readiness_area),
                "source_item_type": _trace_text(source_item_type),
                "source_item_id": _trace_text(source_item_id) or _slug_token(problem_statement)[:80],
                "owner_role": _trace_text(owner_role) or "Owner",
                "problem_statement": _trace_text(problem_statement),
                "business_impact": _trace_text(business_impact),
                "required_action": _trace_text(required_action),
                "acceptance_criteria": _trace_text(acceptance_criteria),
                "blocking_artifacts": _trace_text(blocking_artifacts),
                "affected_sections": _trace_text(affected_sections),
                "affected_outputs": _trace_text(affected_outputs),
                "snowflake_targets": _trace_text(snowflake_targets),
                "client_use_status": _trace_text(client_use_status),
                "proof_artifacts": _trace_text(proof_artifacts),
                "source_artifacts": _trace_text(source_artifacts),
                "model_version": "production_readiness_backlog_v0",
            }
        )

    if engine_readiness_assessment is not None and not engine_readiness_assessment.empty:
        for row in engine_readiness_assessment.to_dict("records"):
            readiness_status = _trace_text(row.get("readiness_status"))
            client_use_status = _trace_text(row.get("client_use_status"))
            blocking_issue = _trace_text(row.get("blocking_issue"))
            severity = _safe_int_value(row.get("severity"), default=0)
            if severity <= 0 and readiness_status == "ready" and client_use_status in {"client_ready", "production_ready"}:
                continue
            readiness_area = _trace_text(row.get("readiness_area"))
            evidence = _trace_text(row.get("evidence_summary"))
            add_row(
                workstream=_production_workstream_for_area(readiness_area),
                priority_band=_production_backlog_priority_from_readiness(severity, client_use_status, readiness_status),
                readiness_area=readiness_area,
                source_item_type="engine_readiness_assessment",
                source_item_id=readiness_area,
                owner_role=_trace_text(row.get("owner_role")),
                problem_statement=blocking_issue or f"{readiness_area} status is {readiness_status}.",
                business_impact=(
                    f"{_trace_text(row.get('engine_layer')) or 'Engine'} cannot be promoted cleanly while "
                    f"{readiness_area} is marked {client_use_status or readiness_status}."
                ),
                required_action=_trace_text(row.get("next_action")),
                acceptance_criteria=(
                    f"{readiness_area} is ready or explicitly approved with documented blockers, row counts, "
                    "proof artifacts, and Snowflake targets reconciled."
                ),
                blocking_artifacts=_trace_text(row.get("proof_artifacts")),
                affected_outputs=_trace_text(row.get("proof_artifacts")),
                snowflake_targets=_trace_text(row.get("snowflake_targets")),
                client_use_status=client_use_status,
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                source_artifacts="engine_readiness_assessment.csv",
            )

    if analysis_data_team_backlog is not None and not analysis_data_team_backlog.empty:
        for row in analysis_data_team_backlog.to_dict("records"):
            input_family = _trace_text(row.get("input_family"))
            field_key = _trace_text(row.get("field_key"))
            sections = _trace_text(row.get("affected_sections"))
            add_row(
                workstream="Data contracts / Snowflake",
                priority_band=_trace_text(row.get("priority_band")),
                readiness_area="analysis_field_mapping",
                source_item_type="analysis_data_team_backlog",
                source_item_id=f"{input_family}:{field_key}",
                owner_role="Data team",
                problem_statement=(
                    f"{input_family}.{field_key} is {_trace_text(row.get('coverage_status'))} "
                    f"for {row.get('affected_section_count')} section(s)."
                ),
                business_impact="The affected analysis cannot be fully rebuilt in Snowflake until the field mapping or derived model is resolved.",
                required_action=_trace_text(row.get("data_team_action")) or _trace_text(row.get("snowflake_design_action")),
                acceptance_criteria=(
                    "Canonical field is mapped, derived, or intentionally excluded; the coverage matrix reruns without "
                    "a blocker for the affected sections."
                ),
                blocking_artifacts=_trace_text(row.get("example_scripts")),
                affected_sections=sections,
                affected_outputs="analysis_layout_coverage_matrix.csv|analysis_input_dependency_map.csv",
                snowflake_targets="out.ti_analysis_layout_coverage_matrix|out.ti_analysis_input_dependency_map",
                client_use_status="blocks_full_snowflake_productization",
                proof_artifacts="analysis_data_team_backlog.csv|analysis_layout_coverage_matrix.csv",
                source_artifacts=_trace_text(row.get("source_artifacts")) or "analysis_data_team_backlog.csv",
            )

    if analysis_metric_validation_queue is not None and not analysis_metric_validation_queue.empty:
        for row in analysis_metric_validation_queue.to_dict("records"):
            input_family = _trace_text(row.get("input_family"))
            field_key = _trace_text(row.get("field_key"))
            validation_type = _trace_text(row.get("validation_type"))
            add_row(
                workstream="Metric validation",
                priority_band=_trace_text(row.get("priority_band")),
                readiness_area="metric_validation",
                source_item_type="analysis_metric_validation_queue",
                source_item_id=f"{input_family}:{field_key}:{validation_type}",
                owner_role="Analyst / Data science",
                problem_statement=f"{input_family}.{field_key} needs {validation_type} before external use.",
                business_impact="The metric can appear in the workbench, but the client story needs a validation caveat until lineage and definition are approved.",
                required_action=_trace_text(row.get("analyst_action")) or _trace_text(row.get("validation_decision")),
                acceptance_criteria="Metric definition, lineage, aggregation, and source fields are approved in the semantic metric catalog.",
                blocking_artifacts=_trace_text(row.get("example_scripts")),
                affected_sections=_trace_text(row.get("affected_sections")),
                affected_outputs="intelligence_metric_catalog.csv|analysis_insight_brief.csv",
                snowflake_targets="out.ti_intelligence_metric_catalog|out.ti_analysis_metric_validation_queue",
                client_use_status="qualified_external_use",
                proof_artifacts="analysis_metric_validation_queue.csv|intelligence_metric_catalog.csv",
                source_artifacts=_trace_text(row.get("source_artifacts")) or "analysis_metric_validation_queue.csv",
            )

    if layout_contract_draft_queue is not None and not layout_contract_draft_queue.empty:
        for row in layout_contract_draft_queue.to_dict("records"):
            file_name = _trace_text(row.get("file_name"))
            contract_id = _trace_text(row.get("proposed_contract_id"))
            add_row(
                workstream="Data contracts / Snowflake",
                priority_band=_trace_text(row.get("priority_band")),
                readiness_area="layout_contracts",
                source_item_type="layout_contract_draft_queue",
                source_item_id=contract_id or file_name,
                owner_role="Data team",
                problem_statement=(
                    f"{file_name} requires {_trace_text(row.get('contract_action')) or 'layout contract review'} "
                    f"before repeatable loading."
                ),
                business_impact="Client monthly files cannot become a repeatable Snowflake intake without a promoted layout contract.",
                required_action=_trace_text(row.get("data_team_action")),
                acceptance_criteria="YAML contract is reviewed, promoted, and tied to the intended Snowflake layer with required fields mapped.",
                blocking_artifacts=_trace_text(row.get("missing_required_fields")),
                affected_outputs="layout_contract_draft_queue.csv|layout_contract_export_manifest.csv|monthly_file_requirements.csv",
                snowflake_targets=_trace_text(row.get("target_snowflake_layer")),
                client_use_status="blocks_full_snowflake_productization",
                proof_artifacts="layout_contract_draft_queue.csv|layout_gap_report.csv|source_layout_profile.csv",
                source_artifacts=_trace_text(row.get("source_artifacts")) or "layout_contract_draft_queue.csv",
            )

    if layout_contract_export_manifest is not None and not layout_contract_export_manifest.empty:
        for row in layout_contract_export_manifest.to_dict("records"):
            if _trace_bool(row.get("yaml_ready")) and _trace_text(row.get("contract_action")) == "promote_existing_contract":
                continue
            contract_id = _trace_text(row.get("proposed_contract_id"))
            add_row(
                workstream="Data contracts / Snowflake",
                priority_band=_trace_text(row.get("priority_band")),
                readiness_area="layout_contract_export",
                source_item_type="layout_contract_export_manifest",
                source_item_id=contract_id,
                owner_role="Data team",
                problem_statement=f"Contract draft {contract_id} needs export review and promotion.",
                business_impact="The file layout exists as a draft, but is not yet a governed intake contract.",
                required_action=_trace_text(row.get("data_team_action")),
                acceptance_criteria="YAML file exists, is reviewed against sample source files, and is promoted into the contract directory.",
                blocking_artifacts=_trace_text(row.get("yaml_relative_path")),
                affected_outputs="layout_contract_drafts|layout_contract_export_manifest.csv",
                snowflake_targets=_trace_text(row.get("target_snowflake_layer")),
                client_use_status="blocks_full_snowflake_productization",
                proof_artifacts="layout_contract_export_manifest.csv",
                source_artifacts=_trace_text(row.get("source_artifacts")) or "layout_contract_export_manifest.csv",
            )

    if monthly_file_requirements is not None and not monthly_file_requirements.empty:
        for row in monthly_file_requirements.to_dict("records"):
            status = _trace_text(row.get("monthly_status"))
            missing_count = _safe_int_value(row.get("missing_required_field_count"))
            selected_count = _safe_int_value(row.get("selected_file_count"))
            if status in {"ready", "selected_for_load", "satisfied"} and missing_count == 0 and selected_count > 0:
                continue
            input_family = _trace_text(row.get("input_family"))
            add_row(
                workstream="Monthly intake",
                priority_band="P0" if missing_count or selected_count == 0 else "P2",
                readiness_area="monthly_file_requirements",
                source_item_type="monthly_file_requirements",
                source_item_id=input_family,
                owner_role="Data team / Analyst",
                problem_statement=f"{_trace_text(row.get('display_name')) or input_family} monthly requirement is {status or 'not satisfied'}.",
                business_impact="The dependent analysis sections may need extracts, layout fixes, or caveats until the monthly file requirement is satisfied.",
                required_action=_trace_text(row.get("data_team_action")) or _trace_text(row.get("analyst_question")),
                acceptance_criteria="Required monthly file is selected for load with required fields present or a documented fallback extract is approved.",
                blocking_artifacts=_trace_text(row.get("missing_required_fields")) or _trace_text(row.get("received_file_names")),
                affected_sections=_trace_text(row.get("dependent_sections")),
                affected_outputs="monthly_file_requirements.csv|file_assembly_plan.csv|layout_gap_report.csv",
                snowflake_targets=_trace_text(row.get("target_snowflake_layer")),
                client_use_status="internal_review",
                proof_artifacts="monthly_file_requirements.csv|file_assembly_plan.csv",
                source_artifacts=_trace_text(row.get("source_artifacts")) or "monthly_file_requirements.csv",
            )

    if analysis_review_board is not None and not analysis_review_board.empty:
        for row in analysis_review_board.to_dict("records"):
            review_status = _trace_text(row.get("review_status"))
            if review_status in {"client_story_ready", "ready"}:
                continue
            section_id = _trace_text(row.get("source_section_id"))
            add_row(
                workstream="Analysis readiness",
                priority_band=_production_backlog_priority_from_review(review_status),
                readiness_area="analysis_review_board",
                source_item_type="analysis_review_board",
                source_item_id=section_id,
                owner_role="CSM / Analyst",
                problem_statement=f"{section_id} is marked {review_status}: {_trace_text(row.get('data_caveat'))}",
                business_impact="The analysis can be reviewed internally, but the client story needs validation or layout caveats before it is presented as final.",
                required_action=_trace_text(row.get("analyst_next_step")) or _trace_text(row.get("data_team_next_step")),
                acceptance_criteria="Review status is client_story_ready with charts, metrics, caveats, and Snowflake targets reconciled.",
                blocking_artifacts=_trace_text(row.get("proof_artifacts")),
                affected_sections=section_id,
                affected_outputs=_trace_text(row.get("generated_output_files")) or _trace_text(row.get("primary_engine_outputs")),
                snowflake_targets=_trace_text(row.get("snowflake_targets")),
                client_use_status=review_status,
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                source_artifacts=_trace_text(row.get("source_artifacts")) or "analysis_review_board.csv",
            )

    if user_interaction_map is not None and not user_interaction_map.empty:
        for row in user_interaction_map.to_dict("records"):
            client_use_status = _trace_text(row.get("client_use_status"))
            if not _status_needs_backlog(client_use_status):
                continue
            file_name = _trace_text(row.get("file_name"))
            user_role = _trace_text(row.get("user_role"))
            add_row(
                workstream="User delivery",
                priority_band=_production_backlog_priority("", client_use_status=client_use_status),
                readiness_area="user_interaction_map",
                source_item_type="user_interaction_map",
                source_item_id=f"{user_role}:{file_name}:{_safe_int_value(row.get('interaction_rank'))}",
                owner_role=user_role,
                problem_statement=f"{user_role} interaction with {file_name} is {client_use_status}.",
                business_impact="The intended user can see the output path, but the workflow should not be treated as cleanly client-ready until the blocker is resolved or documented.",
                required_action=_trace_text(row.get("owner_next_action")),
                acceptance_criteria="Interaction is marked client_ready or production_ready, with delivery mode, proof artifacts, and next action confirmed.",
                blocking_artifacts=_trace_text(row.get("blocker_summary")),
                affected_sections=_trace_text(row.get("source_section_ids")),
                affected_outputs=file_name,
                snowflake_targets=_trace_text(row.get("target_table")),
                client_use_status=client_use_status,
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                source_artifacts=_trace_text(row.get("source_artifacts")) or "user_interaction_map.csv",
            )

    if not rows:
        return _empty_production_readiness_backlog()
    df = pd.DataFrame(rows, columns=columns)
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    df["_priority_sort"] = df["priority_band"].map(priority_order).fillna(9)
    df = df.sort_values(
        ["_priority_sort", "workstream", "readiness_area", "source_item_type", "source_item_id"],
        kind="stable",
    ).drop(columns=["_priority_sort"])
    df["backlog_rank"] = range(1, len(df) + 1)
    return df[columns]


def build_intelligence_lineage_graph(
    *,
    file_assembly_plan: pd.DataFrame,
    source_layout_profile: pd.DataFrame,
    layout_contract_draft_queue: pd.DataFrame,
    analysis_input_dependency_map: pd.DataFrame,
    analysis_layout_coverage_matrix: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    analysis_visual_output_map: pd.DataFrame,
    analysis_chart_spec_catalog: pd.DataFrame,
    analysis_chart_data_snapshot: pd.DataFrame,
    intelligence_metric_catalog: pd.DataFrame,
    analysis_insight_brief: pd.DataFrame,
    client_meeting_deck_blueprint: pd.DataFrame,
    analysis_review_board: pd.DataFrame,
    user_interaction_map: pd.DataFrame,
    production_readiness_backlog: pd.DataFrame,
    action_plan: pd.DataFrame,
    role_handoffs: pd.DataFrame,
    operating_control_plane: pd.DataFrame,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Build source-to-decision lineage edges for the intelligence engine."""
    cfg = config or EngineConfig()
    columns = _intelligence_lineage_graph_columns()
    rows: list[dict[str, Any]] = []
    draft_family_by_file = _lineage_draft_family_by_file(layout_contract_draft_queue)
    draft_target_by_file = _lineage_draft_target_by_file(layout_contract_draft_queue)

    def add_edge(
        *,
        lineage_stage: str,
        source_node_type: str,
        source_node_id: str,
        source_label: str,
        target_node_type: str,
        target_node_id: str,
        target_label: str,
        relationship: str,
        edge_status: str,
        owner_role: str,
        business_question: str = "",
        analysis_section_id: str = "",
        input_family: str = "",
        field_key: str = "",
        output_artifact: str = "",
        target_table: str = "",
        proof_artifacts: str = "",
        next_action: str = "",
        source_artifacts: str = "",
    ) -> None:
        if not _trace_text(source_node_id) or not _trace_text(target_node_id):
            return
        rows.append(
            {
                "edge_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "lineage_stage": lineage_stage,
                "source_node_type": source_node_type,
                "source_node_id": _trace_text(source_node_id),
                "source_label": _trace_text(source_label),
                "target_node_type": target_node_type,
                "target_node_id": _trace_text(target_node_id),
                "target_label": _trace_text(target_label),
                "relationship": relationship,
                "edge_status": _trace_text(edge_status),
                "owner_role": _trace_text(owner_role),
                "business_question": _trace_text(business_question),
                "analysis_section_id": _trace_text(analysis_section_id),
                "input_family": _trace_text(input_family),
                "field_key": _trace_text(field_key),
                "output_artifact": _trace_text(output_artifact),
                "target_table": _trace_text(target_table),
                "proof_artifacts": _trace_text(proof_artifacts),
                "next_action": _trace_text(next_action),
                "source_artifacts": _trace_text(source_artifacts),
                "model_version": "intelligence_lineage_graph_v0",
            }
        )

    if file_assembly_plan is not None and not file_assembly_plan.empty:
        for row in file_assembly_plan.to_dict("records"):
            file_name = _trace_text(row.get("file_name"))
            input_family = (
                _trace_text(row.get("target_engine_input"))
                or draft_family_by_file.get(file_name)
                or _lineage_family_from_source_family(row.get("source_family"))
            )
            target_table = _trace_text(row.get("target_snowflake_layer")) or draft_target_by_file.get(file_name, "")
            load_flag = _trace_bool(row.get("load_flag"))
            add_edge(
                lineage_stage="01_file_to_input",
                source_node_type="raw_file",
                source_node_id=f"file:{file_name}",
                source_label=file_name,
                target_node_type="input_family",
                target_node_id=f"input:{input_family}",
                target_label=input_family,
                relationship="loads_to_input_family" if load_flag else "review_before_load",
                edge_status="ready" if load_flag else _trace_text(row.get("assembly_role")) or _trace_text(row.get("intake_decision")),
                owner_role="Data team",
                input_family=input_family,
                target_table=target_table,
                proof_artifacts="file_assembly_plan.csv|intake_work_order.csv",
                next_action=_trace_text(row.get("operator_action")) or _trace_text(row.get("assembly_reason")),
                source_artifacts="file_assembly_plan.csv",
            )

    if layout_contract_draft_queue is not None and not layout_contract_draft_queue.empty:
        for row in layout_contract_draft_queue.to_dict("records"):
            file_name = _trace_text(row.get("file_name"))
            target_layer = _trace_text(row.get("target_snowflake_layer"))
            input_family = _lineage_family_from_target_layer(target_layer) or _lineage_family_from_source_family(row.get("source_family"))
            contract_id = _trace_text(row.get("proposed_contract_id"))
            add_edge(
                lineage_stage="02_file_to_contract",
                source_node_type="raw_file",
                source_node_id=f"file:{file_name}",
                source_label=file_name,
                target_node_type="layout_contract",
                target_node_id=f"contract:{contract_id}",
                target_label=contract_id,
                relationship=_trace_text(row.get("contract_action")) or "contract_review",
                edge_status=_trace_text(row.get("priority_band")) or _trace_text(row.get("match_status")),
                owner_role="Data team",
                input_family=input_family,
                target_table=target_layer,
                proof_artifacts="layout_contract_draft_queue.csv|source_layout_profile.csv",
                next_action=_trace_text(row.get("data_team_action")),
                source_artifacts="layout_contract_draft_queue.csv",
            )
            for field in _split_tokens(row.get("missing_required_fields")):
                add_edge(
                    lineage_stage="03_contract_to_required_field",
                    source_node_type="layout_contract",
                    source_node_id=f"contract:{contract_id}",
                    source_label=contract_id,
                    target_node_type="canonical_field",
                    target_node_id=f"field:{input_family}:{field}",
                    target_label=field,
                    relationship="requires_mapping",
                    edge_status="mapping_required",
                    owner_role="Data team",
                    input_family=input_family,
                    field_key=field,
                    target_table=target_layer,
                    proof_artifacts="layout_contract_draft_queue.csv|layout_gap_report.csv",
                    next_action=_trace_text(row.get("data_team_action")),
                    source_artifacts="layout_contract_draft_queue.csv",
                )

    if source_layout_profile is not None and not source_layout_profile.empty:
        for row in source_layout_profile.to_dict("records"):
            input_family = _trace_text(row.get("proposed_input_family")) or _lineage_family_from_source_family(row.get("source_family"))
            source_column = _trace_text(row.get("source_column"))
            for field in _split_tokens(row.get("matched_canonical_fields")):
                add_edge(
                    lineage_stage="04_source_field_to_canonical_field",
                    source_node_type="source_column",
                    source_node_id=f"source_column:{_trace_text(row.get('file_name'))}:{source_column}",
                    source_label=f"{_trace_text(row.get('file_name'))}:{source_column}",
                    target_node_type="canonical_field",
                    target_node_id=f"field:{input_family}:{field}",
                    target_label=field,
                    relationship="maps_to_canonical_field",
                    edge_status=_trace_text(row.get("canonical_mapping_status")),
                    owner_role="Data team",
                    input_family=input_family,
                    field_key=field,
                    target_table=_lineage_target_table_for_input(input_family),
                    proof_artifacts="source_layout_profile.csv|layout_gap_report.csv",
                    next_action=_trace_text(row.get("mapping_action")),
                    source_artifacts="source_layout_profile.csv",
                )

    if analysis_input_dependency_map is not None and not analysis_input_dependency_map.empty:
        for row in analysis_input_dependency_map.to_dict("records"):
            input_family = _trace_text(row.get("input_family"))
            for section_id in _split_tokens(row.get("dependent_sections")):
                add_edge(
                    lineage_stage="05_input_to_analysis_section",
                    source_node_type="input_family",
                    source_node_id=f"input:{input_family}",
                    source_label=_trace_text(row.get("display_name")) or input_family,
                    target_node_type="analysis_section",
                    target_node_id=f"section:{section_id}",
                    target_label=section_id,
                    relationship="required_by_analysis_section",
                    edge_status=_trace_text(row.get("current_run_readiness")),
                    owner_role="Analyst",
                    business_question=_trace_text(row.get("canonical_role")),
                    analysis_section_id=section_id,
                    input_family=input_family,
                    proof_artifacts="analysis_input_dependency_map.csv",
                    next_action=_trace_text(row.get("analyst_next_step")),
                    source_artifacts="analysis_input_dependency_map.csv",
                )

    if analysis_layout_coverage_matrix is not None and not analysis_layout_coverage_matrix.empty:
        for row in analysis_layout_coverage_matrix.to_dict("records"):
            section_id = _trace_text(row.get("source_section_id"))
            input_family = _trace_text(row.get("input_family_hint"))
            field_key = _trace_text(row.get("field_key"))
            add_edge(
                lineage_stage="06_field_to_analysis_section",
                source_node_type="canonical_field",
                source_node_id=f"field:{input_family}:{field_key}",
                source_label=field_key,
                target_node_type="analysis_section",
                target_node_id=f"section:{section_id}",
                target_label=_trace_text(row.get("display_name")) or section_id,
                relationship="referenced_by_script",
                edge_status=_trace_text(row.get("coverage_status")),
                owner_role="Data team" if _trace_text(row.get("coverage_severity")) == "blocker" else "Analyst",
                business_question=_trace_text(row.get("domain_name")),
                analysis_section_id=section_id,
                input_family=input_family,
                field_key=field_key,
                proof_artifacts=_trace_text(row.get("source_artifacts")),
                next_action=_trace_text(row.get("data_team_action")) or _trace_text(row.get("analyst_action")),
                source_artifacts="analysis_layout_coverage_matrix.csv",
            )

    if analysis_execution_map is not None and not analysis_execution_map.empty:
        for row in analysis_execution_map.to_dict("records"):
            section_id = _trace_text(row.get("source_section_id"))
            output_files = _split_tokens(row.get("generated_output_files"))
            target_tables = _split_tokens(row.get("generated_target_tables"))
            for index, output_file in enumerate(output_files):
                target_table = target_tables[index] if index < len(target_tables) else ""
                add_edge(
                    lineage_stage="07_section_to_engine_output",
                    source_node_type="analysis_section",
                    source_node_id=f"section:{section_id}",
                    source_label=_trace_text(row.get("display_name")) or section_id,
                    target_node_type="engine_output",
                    target_node_id=f"artifact:{output_file}",
                    target_label=output_file,
                    relationship="supports_output",
                    edge_status=_trace_text(row.get("evidence_status")),
                    owner_role="Analyst",
                    business_question=_trace_text(row.get("consulting_question")),
                    analysis_section_id=section_id,
                    output_artifact=output_file,
                    target_table=target_table,
                    proof_artifacts=_trace_text(row.get("source_artifacts")),
                    next_action=_trace_text(row.get("analyst_next_step")),
                    source_artifacts="analysis_execution_map.csv",
                )

    if analysis_visual_output_map is not None and not analysis_visual_output_map.empty:
        for row in analysis_visual_output_map.to_dict("records"):
            output_file = _trace_text(row.get("output_file"))
            section_id = _trace_text(row.get("source_section_id"))
            visual_id = f"{section_id}:{output_file}:{_trace_text(row.get('visual_type'))}"
            add_edge(
                lineage_stage="08_output_to_visual_surface",
                source_node_type="engine_output",
                source_node_id=f"artifact:{output_file}",
                source_label=output_file,
                target_node_type="visual_surface",
                target_node_id=f"visual:{visual_id}",
                target_label=_trace_text(row.get("visual_title")) or visual_id,
                relationship="renders_as_visual_surface",
                edge_status=_trace_text(row.get("chart_readiness_status")),
                owner_role="BI / Product UI",
                business_question=_trace_text(row.get("consulting_question")),
                analysis_section_id=section_id,
                output_artifact=output_file,
                target_table=_trace_text(row.get("target_table")),
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("analyst_action")),
                source_artifacts="analysis_visual_output_map.csv",
            )

    if analysis_chart_spec_catalog is not None and not analysis_chart_spec_catalog.empty:
        for row in analysis_chart_spec_catalog.to_dict("records"):
            output_file = _trace_text(row.get("output_file"))
            section_id = _trace_text(row.get("source_section_id"))
            chart_title = _trace_text(row.get("chart_title"))
            add_edge(
                lineage_stage="09_visual_surface_to_chart_spec",
                source_node_type="engine_output",
                source_node_id=f"artifact:{output_file}",
                source_label=output_file,
                target_node_type="chart_spec",
                target_node_id=f"chart:{section_id}:{output_file}:{_trace_text(row.get('chart_type'))}",
                target_label=chart_title,
                relationship="has_render_spec",
                edge_status=_trace_text(row.get("chart_readiness_status")),
                owner_role=_trace_text(row.get("render_owner")) or "BI / Product UI",
                business_question=_trace_text(row.get("csm_use")),
                analysis_section_id=section_id,
                output_artifact=output_file,
                target_table=_trace_text(row.get("target_table")),
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("analyst_action")),
                source_artifacts="analysis_chart_spec_catalog.csv",
            )

    if analysis_chart_data_snapshot is not None and not analysis_chart_data_snapshot.empty:
        for row in analysis_chart_data_snapshot.to_dict("records"):
            output_file = _trace_text(row.get("data_artifact"))
            section_id = _trace_text(row.get("source_section_id"))
            chart_type = _trace_text(row.get("chart_type"))
            snapshot_id = f"snapshot:{section_id}:{_safe_int_value(row.get('spec_rank'))}"
            add_edge(
                lineage_stage="10_chart_spec_to_chart_data",
                source_node_type="chart_spec",
                source_node_id=f"chart:{section_id}:{output_file}:{chart_type}",
                source_label=_trace_text(row.get("chart_title")) or chart_type,
                target_node_type="chart_data_snapshot",
                target_node_id=snapshot_id,
                target_label=_trace_text(row.get("top_label")) or _trace_text(row.get("data_status")) or snapshot_id,
                relationship="materializes_chart_data",
                edge_status=_trace_text(row.get("data_status")),
                owner_role=_trace_text(row.get("render_owner")) or "BI / Product UI",
                business_question=_trace_text(row.get("insight_callout")),
                analysis_section_id=section_id,
                output_artifact="analysis_chart_data_snapshot.csv",
                target_table="out.ti_analysis_chart_data_snapshot",
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("analyst_action")),
                source_artifacts="analysis_chart_data_snapshot.csv",
            )

    if intelligence_metric_catalog is not None and not intelligence_metric_catalog.empty:
        for row in intelligence_metric_catalog.to_dict("records"):
            metric_id = _trace_text(row.get("metric_id"))
            source_artifact = _trace_text(row.get("source_artifact"))
            source_field = _trace_text(row.get("source_field"))
            for section_id in _split_tokens(row.get("used_by_sections")) or ["engine_metric_catalog"]:
                add_edge(
                    lineage_stage="11_chart_data_to_metric",
                    source_node_type="chart_data_snapshot",
                    source_node_id=f"snapshot_metric:{source_artifact}:{source_field}:{section_id}",
                    source_label=f"{source_artifact}:{source_field}",
                    target_node_type="semantic_metric",
                    target_node_id=f"metric:{metric_id}",
                    target_label=_trace_text(row.get("metric_name")) or metric_id,
                    relationship="defines_semantic_metric",
                    edge_status=_trace_text(row.get("validation_status")),
                    owner_role=_trace_text(row.get("validation_owner")) or "Data science",
                    business_question=_trace_text(row.get("business_definition")),
                    analysis_section_id=section_id,
                    field_key=source_field,
                    output_artifact="intelligence_metric_catalog.csv",
                    target_table="out.ti_intelligence_metric_catalog",
                    proof_artifacts=_trace_text(row.get("source_artifacts")),
                    next_action=_trace_text(row.get("data_team_action")),
                    source_artifacts="intelligence_metric_catalog.csv",
                )

    if analysis_insight_brief is not None and not analysis_insight_brief.empty:
        for row in analysis_insight_brief.to_dict("records"):
            section_id = _trace_text(row.get("source_section_id"))
            brief_id = f"brief:{section_id}"
            metric_ids = _split_tokens(row.get("primary_metric_ids")) or ["section_context"]
            for metric_id in metric_ids:
                source_type = "semantic_metric" if metric_id != "section_context" else "analysis_section"
                source_id = f"metric:{metric_id}" if metric_id != "section_context" else f"section:{section_id}"
                add_edge(
                    lineage_stage="12_metric_to_insight_brief",
                    source_node_type=source_type,
                    source_node_id=source_id,
                    source_label=metric_id if metric_id != "section_context" else section_id,
                    target_node_type="section_insight_brief",
                    target_node_id=brief_id,
                    target_label=_trace_text(row.get("headline_insight")) or section_id,
                    relationship="summarizes_for_consulting_use",
                    edge_status=_trace_text(row.get("brief_status")),
                    owner_role="CSM",
                    business_question=_trace_text(row.get("consulting_question")),
                    analysis_section_id=section_id,
                    output_artifact="analysis_insight_brief.csv",
                    target_table="out.ti_analysis_insight_brief",
                    proof_artifacts=_trace_text(row.get("proof_artifacts")),
                    next_action=_trace_text(row.get("analyst_next_step")),
                    source_artifacts="analysis_insight_brief.csv",
                )

    if client_meeting_deck_blueprint is not None and not client_meeting_deck_blueprint.empty:
        for row in client_meeting_deck_blueprint.to_dict("records"):
            source_artifact = _trace_text(row.get("source_artifact"))
            section_id = _trace_text(row.get("source_section_id"))
            blueprint_id = f"meeting:{_safe_int_value(row.get('blueprint_rank'))}"
            source_type, source_id, source_label = _meeting_blueprint_lineage_source(row)
            add_edge(
                lineage_stage="13_source_to_client_meeting_blueprint",
                source_node_type=source_type,
                source_node_id=source_id,
                source_label=source_label,
                target_node_type="client_meeting_blueprint",
                target_node_id=blueprint_id,
                target_label=_trace_text(row.get("slide_title")) or blueprint_id,
                relationship="sequenced_for_client_meeting",
                edge_status=_trace_text(row.get("blueprint_status")),
                owner_role=_trace_text(row.get("owner_role")) or "CSM",
                business_question=_trace_text(row.get("decision_prompt")),
                analysis_section_id=section_id,
                output_artifact="client_meeting_deck_blueprint.csv",
                target_table="out.ti_client_meeting_deck_blueprint",
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("follow_up_action")),
                source_artifacts=source_artifact or "client_meeting_deck_blueprint.csv",
            )

    if analysis_review_board is not None and not analysis_review_board.empty:
        for row in analysis_review_board.to_dict("records"):
            section_id = _trace_text(row.get("source_section_id"))
            review_id = f"analysis_review:{section_id}"
            add_edge(
                lineage_stage="14_section_to_analysis_review_board",
                source_node_type="analysis_section",
                source_node_id=f"section:{section_id}",
                source_label=_trace_text(row.get("display_name")) or section_id,
                target_node_type="analysis_review_board",
                target_node_id=review_id,
                target_label=_trace_text(row.get("headline_insight")) or _trace_text(row.get("what_is_analyzed")) or section_id,
                relationship="rolls_up_section_for_analysis_review",
                edge_status=_trace_text(row.get("review_status")),
                owner_role="CSM / Analyst",
                business_question=_trace_text(row.get("recommended_client_question")) or _trace_text(row.get("consulting_question")),
                analysis_section_id=section_id,
                output_artifact="analysis_review_board.csv",
                target_table="out.ti_analysis_review_board",
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("analyst_next_step")) or _trace_text(row.get("data_team_next_step")),
                source_artifacts=_trace_text(row.get("source_artifacts")),
            )

    if action_plan is not None and not action_plan.empty:
        for row in action_plan.to_dict("records"):
            action_id = _trace_text(row.get("action_id"))
            add_edge(
                lineage_stage="10_output_to_action_play",
                source_node_type="engine_output",
                source_node_id="artifact:opportunities.csv",
                source_label="opportunities.csv",
                target_node_type="action_play",
                target_node_id=f"action:{action_id}",
                target_label=_trace_text(row.get("play_name")),
                relationship="prioritized_into_action_play",
                edge_status=_trace_text(row.get("status")),
                owner_role=_trace_text(row.get("owner_role")),
                business_question=_trace_text(row.get("objective")),
                output_artifact="action_plan.csv",
                target_table="out.ti_action_plan",
                proof_artifacts="opportunities.csv|opportunity_portfolio.csv|action_plan.csv",
                next_action=_trace_text(row.get("next_step")),
                source_artifacts="action_plan.csv",
            )

    if role_handoffs is not None and not role_handoffs.empty:
        for row in role_handoffs.to_dict("records"):
            role = _trace_text(row.get("role"))
            outputs = _split_tokens(row.get("outputs_used")) + _split_tokens(row.get("export_artifact"))
            for output_file in dict.fromkeys(outputs):
                add_edge(
                    lineage_stage="11_output_to_role",
                    source_node_type="engine_output",
                    source_node_id=f"artifact:{output_file}",
                    source_label=output_file,
                    target_node_type="role",
                    target_node_id=f"role:{role}",
                    target_label=role,
                    relationship="used_by_role",
                    edge_status=_trace_text(row.get("status")),
                    owner_role=role,
                    business_question=_trace_text(row.get("decision_owned")),
                    output_artifact=output_file,
                    proof_artifacts="role_handoffs.csv",
                    next_action=_trace_text(row.get("first_action")),
                    source_artifacts="role_handoffs.csv",
                )

    if operating_control_plane is not None and not operating_control_plane.empty:
        for row in operating_control_plane.to_dict("records"):
            role = _trace_text(row.get("role"))
            decision = _trace_text(row.get("decision_owned"))
            add_edge(
                lineage_stage="12_role_to_decision",
                source_node_type="role",
                source_node_id=f"role:{role}",
                source_label=role,
                target_node_type="operating_decision",
                target_node_id=f"decision:{_slug_token(role)}:{_slug_token(decision)[:80]}",
                target_label=decision,
                relationship="owns_decision",
                edge_status=_trace_text(row.get("client_use_status")) or _trace_text(row.get("current_status")),
                owner_role=role,
                business_question=_trace_text(row.get("operating_question")),
                output_artifact=_trace_text(row.get("export_artifact")),
                target_table=_trace_text(row.get("snowflake_targets")),
                proof_artifacts=_trace_text(row.get("source_artifacts")),
                next_action=_trace_text(row.get("next_action")),
                source_artifacts="operating_control_plane.csv",
            )

    if user_interaction_map is not None and not user_interaction_map.empty:
        for row in user_interaction_map.to_dict("records"):
            rank = _safe_int_value(row.get("interaction_rank"))
            add_edge(
                lineage_stage="15_decision_to_user_interaction",
                source_node_type="operating_decision",
                source_node_id=f"decision:{_slug_token(row.get('user_role'))}:{_slug_token(row.get('decision_supported'))[:80]}",
                source_label=_trace_text(row.get("decision_supported")),
                target_node_type="user_interaction",
                target_node_id=f"interaction:{rank}",
                target_label=f"{_trace_text(row.get('user_role'))}: {_trace_text(row.get('file_name'))}",
                relationship="delivered_as_user_artifact",
                edge_status=_trace_text(row.get("client_use_status")),
                owner_role=_trace_text(row.get("user_role")),
                business_question=_trace_text(row.get("analysis_or_data_question")),
                analysis_section_id=_trace_text(row.get("source_section_ids")),
                output_artifact="user_interaction_map.csv",
                target_table="out.ti_user_interaction_map",
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("owner_next_action")),
                source_artifacts=_trace_text(row.get("source_artifacts")) or "user_interaction_map.csv",
            )

    if production_readiness_backlog is not None and not production_readiness_backlog.empty:
        for row in production_readiness_backlog.to_dict("records"):
            source_item_type = _trace_text(row.get("source_item_type")) or "readiness_source"
            source_item_id = _trace_text(row.get("source_item_id")) or f"backlog:{_safe_int_value(row.get('backlog_rank'))}"
            add_edge(
                lineage_stage="16_readiness_to_production_backlog",
                source_node_type=source_item_type,
                source_node_id=f"{source_item_type}:{source_item_id}",
                source_label=source_item_id,
                target_node_type="production_backlog_item",
                target_node_id=f"backlog:{_safe_int_value(row.get('backlog_rank'))}",
                target_label=_trace_text(row.get("problem_statement")) or source_item_id,
                relationship="creates_productization_work_item",
                edge_status=_trace_text(row.get("priority_band")),
                owner_role=_trace_text(row.get("owner_role")),
                business_question=_trace_text(row.get("business_impact")),
                analysis_section_id=_trace_text(row.get("affected_sections")),
                output_artifact="production_readiness_backlog.csv",
                target_table="out.ti_production_readiness_backlog",
                proof_artifacts=_trace_text(row.get("proof_artifacts")),
                next_action=_trace_text(row.get("required_action")),
                source_artifacts=_trace_text(row.get("source_artifacts")) or "production_readiness_backlog.csv",
            )

    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns)


def build_consulting_story(
    opportunity_portfolio: pd.DataFrame,
    action_plan: pd.DataFrame,
    outcome_summary: pd.DataFrame,
    insights: list[dict[str, Any]],
    data_quality: dict[str, Any],
    config: EngineConfig | None = None,
) -> dict[str, Any]:
    """Create the narrative layer that turns analysis outputs into consulting."""
    cfg = config or EngineConfig()
    quality_score = data_quality.get("quality_score")
    confidence = data_quality.get("confidence", "unknown")
    warnings = data_quality.get("warnings") or []
    top_actions = (
        action_plan.head(3).to_dict(orient="records")
        if action_plan is not None and not action_plan.empty
        else []
    )
    top_portfolio = (
        opportunity_portfolio.head(3).to_dict(orient="records")
        if opportunity_portfolio is not None and not opportunity_portfolio.empty
        else []
    )
    headline = "Transactional intelligence package is ready for review."
    if top_actions:
        headline = f"{top_actions[0].get('play_name', 'Top play')} is the lead relationship play."

    outcome_message = "No prior campaign package was available for outcome measurement."
    if outcome_summary is not None and not outcome_summary.empty:
        top_outcome = outcome_summary.iloc[0].to_dict()
        rate = float(top_outcome.get("test_outcome_rate", 0) or 0)
        outcome_message = (
            f"{top_outcome.get('play_name', 'The lead play')} measured "
            f"{rate:.1%} outcome conversion for test accounts; "
            f"{top_outcome.get('interpretation', 'review movement before scaling')}."
        )

    story_arc = [
        {
            "step": "Data readiness",
            "summary": (
                f"Quality score {quality_score if quality_score is not None else 'unknown'} "
                f"with {confidence} confidence and {len(warnings)} warning(s)."
            ),
            "artifact": "data_quality_report.html",
        },
        {
            "step": "Behavioral signals",
            "summary": "Account-month features summarize payroll, debit use, balances, external FI movement, engagement, and relationship depth.",
            "artifact": "account_month_features.csv",
        },
        {
            "step": "Relationship diagnosis",
            "summary": "PFI verdicts separate primary, split, competitor-primary, and no-verdict relationships with reason codes.",
            "artifact": "pfi_verdicts.csv",
        },
        {
            "step": "Opportunity portfolio",
            "summary": _portfolio_summary(top_portfolio),
            "artifact": "opportunity_portfolio.csv",
        },
        {
            "step": "Action and activation",
            "summary": _action_summary(top_actions),
            "artifact": "action_plan.csv|campaign_targets.csv",
        },
        {
            "step": "Measurement loop",
            "summary": outcome_message,
            "artifact": "measurement_plan.csv|outcome_summary.csv",
        },
    ]
    return {
        "story_version": "consulting_story_v0_rules",
        "client_id": cfg.client_id,
        "client_name": cfg.client_name,
        "period_month": _period_label(cfg.period_month),
        "headline": headline,
        "executive_summary": _executive_summary(
            top_actions=top_actions,
            quality_score=quality_score,
            confidence=confidence,
            warnings=warnings,
            outcome_message=outcome_message,
        ),
        "recommended_conversation": [
            "Start with data confidence and what the file coverage can support.",
            "Explain the top relationship behavior, not just the top chart.",
            "Recommend one to three action plays with owners, channels, and measurement.",
            "Agree on campaign or banker execution and the next monthly outcome readout.",
        ],
        "consulting_questions": [
            "Which play is most aligned to the client's current growth or retention priority?",
            "Who owns activation: marketing, branch leadership, banker team, or CSM follow-up?",
            "What suppressions, compliance exclusions, or branch assignments are required before launch?",
            "How will outcomes be captured back into next month's run?",
        ],
        "top_plays": top_actions,
        "top_opportunity_portfolio": top_portfolio,
        "story_arc": story_arc,
        "analyst_notes": warnings or ["No material data quality warnings generated by the V1 engine."],
        "measurement_message": outcome_message,
        "source_artifacts": [
            "data_quality.json",
            "opportunity_portfolio.csv",
            "action_plan.csv",
            "campaign_targets.csv",
            "measurement_plan.csv",
            "outcome_summary.csv",
        ],
        "insight_count": len(insights or []),
    }


def build_consulting_insight_register(
    insights: list[dict[str, Any]],
    consulting_story: dict[str, Any],
    opportunity_portfolio: pd.DataFrame,
    executive_scorecard: pd.DataFrame,
    action_plan: pd.DataFrame,
    measurement_plan: pd.DataFrame,
    analysis_execution_map: pd.DataFrame,
    model_rulebook: pd.DataFrame,
    data_quality: dict[str, Any] | None = None,
    config: EngineConfig | None = None,
) -> pd.DataFrame:
    """Create a tabular consulting register from insights, evidence, and actions."""
    cfg = config or EngineConfig()
    rows: list[dict[str, Any]] = []
    quality = data_quality or {}
    portfolio_by_type = _records_by_key(opportunity_portfolio, "opportunity_type")
    action_by_type = _records_by_key(action_plan, "opportunity_type")
    measurement_by_type = _records_by_key(measurement_plan, "opportunity_type")
    evidence_by_section = _evidence_by_section(analysis_execution_map)
    rules_by_opportunity = _rules_by_opportunity(model_rulebook)

    for insight in insights or []:
        source_sections = [_trace_text(section) for section in insight.get("source_sections", []) if _trace_text(section)]
        opportunity_type = _opportunity_type_from_insight(insight)
        portfolio = portfolio_by_type.get(opportunity_type, {})
        action = action_by_type.get(opportunity_type, {})
        measurement = measurement_by_type.get(opportunity_type, {})
        evidence = _evidence_summary_for_sections(source_sections, evidence_by_section)
        rows.append(
            {
                "insight_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "insight_id": _trace_text(insight.get("insight_id")) or f"ti.insight.{len(rows) + 1}",
                "insight_type": "opportunity",
                "domain": _trace_text(insight.get("domain")),
                "source_section_ids": "|".join(source_sections),
                "opportunity_type": opportunity_type,
                "play_name": _trace_text(portfolio.get("play_name")) or opportunity_type.replace("_", " ").title(),
                "finding": _trace_text(insight.get("finding")),
                "metric_name": _trace_text(insight.get("metric_name")),
                "metric_value": insight.get("current_value", ""),
                "metric_display": _insight_metric_display(insight.get("metric_name"), insight.get("current_value")),
                "affected_accounts": _safe_int_value(insight.get("affected_accounts")),
                "expected_value": round(float(insight.get("opportunity_amount", 0) or 0), 2),
                "priority_score": round(float(insight.get("priority_score", portfolio.get("avg_priority_score", 0)) or 0), 1),
                "confidence": _trace_text(insight.get("confidence")) or _trace_text(portfolio.get("confidence")),
                "evidence_status": evidence["status"],
                "evidence_artifacts": evidence["artifacts"] or "opportunities.csv|opportunity_portfolio.csv|insights.json",
                "source_rules": "|".join(rules_by_opportunity.get(opportunity_type, [])),
                "recommended_action": _trace_text(action.get("next_step")) or _trace_text(insight.get("recommended_action")),
                "owner_role": _trace_text(action.get("owner_role")) or _trace_text(portfolio.get("owner_role")),
                "recommended_channel": _trace_text(action.get("recommended_channel")) or _trace_text(portfolio.get("recommended_channel")),
                "action_id": _trace_text(action.get("action_id")),
                "measurement_id": _trace_text(action.get("measurement_id")) or _trace_text(measurement.get("measurement_id")),
                "primary_metric": _trace_text(measurement.get("primary_metric")) or _trace_text((insight.get("measurement") or {}).get("primary_metric")),
                "consulting_question": evidence["question"] or _consulting_question_for_opportunity(opportunity_type),
                "next_decision": _next_decision_for_insight(
                    opportunity_type=opportunity_type,
                    owner_role=_trace_text(action.get("owner_role")) or _trace_text(portfolio.get("owner_role")),
                    evidence_status=evidence["status"],
                ),
                "target_list_ref": _trace_text(action.get("target_list_ref")) or _trace_text(insight.get("target_list_ref")),
                "source_artifacts": "insights.json|opportunity_portfolio.csv|action_plan.csv|measurement_plan.csv|analysis_execution_map.csv",
                "model_version": "consulting_insight_register_v0",
            }
        )

    for scorecard in _scorecard_register_rows(executive_scorecard):
        rows.append(
            {
                "insight_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "insight_id": scorecard["insight_id"],
                "insight_type": "scorecard",
                "domain": scorecard["domain"],
                "source_section_ids": "",
                "opportunity_type": "",
                "play_name": "",
                "finding": scorecard["finding"],
                "metric_name": scorecard["metric_name"],
                "metric_value": scorecard["metric_value"],
                "metric_display": scorecard["metric_display"],
                "affected_accounts": "",
                "expected_value": "",
                "priority_score": scorecard["score"],
                "confidence": quality.get("confidence", ""),
                "evidence_status": scorecard["rag_status"],
                "evidence_artifacts": scorecard["source_artifacts"],
                "source_rules": "",
                "recommended_action": scorecard["recommended_action"],
                "owner_role": scorecard["owner_role"],
                "recommended_channel": "Consulting review",
                "action_id": "",
                "measurement_id": "",
                "primary_metric": scorecard["metric_name"],
                "consulting_question": f"What decision should we make about {scorecard['domain']}?",
                "next_decision": scorecard["recommended_action"],
                "target_list_ref": "",
                "source_artifacts": "executive_scorecard.csv|data_quality.json",
                "model_version": "consulting_insight_register_v0",
            }
        )

    for story_row in _story_arc_register_rows(consulting_story):
        rows.append(
            {
                "insight_rank": len(rows) + 1,
                "client_id": cfg.client_id,
                "period_month": _period_label(cfg.period_month),
                "insight_id": story_row["insight_id"],
                "insight_type": "story_step",
                "domain": "Consulting Story",
                "source_section_ids": "",
                "opportunity_type": "",
                "play_name": story_row["step"],
                "finding": story_row["summary"],
                "metric_name": "",
                "metric_value": "",
                "metric_display": "",
                "affected_accounts": "",
                "expected_value": "",
                "priority_score": "",
                "confidence": quality.get("confidence", ""),
                "evidence_status": "story_ready",
                "evidence_artifacts": story_row["artifact"],
                "source_rules": "",
                "recommended_action": story_row["next_step"],
                "owner_role": "CSM",
                "recommended_channel": "Client strategy conversation",
                "action_id": "",
                "measurement_id": "",
                "primary_metric": "",
                "consulting_question": story_row["question"],
                "next_decision": story_row["next_step"],
                "target_list_ref": "",
                "source_artifacts": "consulting_story.json",
                "model_version": "consulting_insight_register_v0",
            }
        )

    if not rows:
        return _empty_consulting_insight_register()
    return pd.DataFrame(rows, columns=_consulting_insight_register_columns()).reset_index(drop=True)


def assess_data_quality(
    accounts: pd.DataFrame | None,
    transactions: pd.DataFrame | None,
    features: pd.DataFrame,
    file_ledger: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Grade input coverage and feature readiness for downstream insights."""
    account_cols = _mapped_columns(accounts, {"account_id": ACCOUNT_ID_COLUMNS}) if accounts is not None else {}
    txn_cols = (
        _mapped_columns(
            transactions,
            {
                "account_id": ACCOUNT_ID_COLUMNS,
                "transaction_date": DATE_COLUMNS,
                "amount": AMOUNT_COLUMNS,
                "merchant": MERCHANT_COLUMNS,
            },
        )
        if transactions is not None
        else {}
    )
    warnings: list[str] = []
    account_rows = int(len(accounts)) if accounts is not None else 0
    transaction_rows = int(len(transactions)) if transactions is not None else 0
    feature_rows = int(len(features))
    match_rate = float(features["matched_account"].mean()) if "matched_account" in features and feature_rows else 0.0
    months = int(features["period_month"].nunique()) if "period_month" in features and feature_rows else 0

    if account_rows == 0:
        warnings.append("missing_account_file")
    if transaction_rows == 0:
        warnings.append("missing_transaction_file")
    for key in ("account_id", "transaction_date", "amount"):
        if transaction_rows and not txn_cols.get(key):
            warnings.append(f"missing_transaction_{key}")
    if account_rows and not account_cols.get("account_id"):
        warnings.append("missing_account_id")
    if transaction_rows and account_rows and match_rate < 0.80:
        warnings.append("low_account_match_rate")
    if transaction_rows and months < 3:
        warnings.append("short_transaction_history")

    score_parts = [
        1.0 if account_rows else 0.0,
        1.0 if transaction_rows else 0.0,
        1.0 if txn_cols.get("account_id") else 0.0,
        1.0 if txn_cols.get("transaction_date") else 0.0,
        1.0 if txn_cols.get("amount") else 0.0,
        min(match_rate, 1.0) if account_rows and transaction_rows else 0.0,
        min(months / 6.0, 1.0) if transaction_rows else 0.0,
    ]
    quality_score = round(100 * (sum(score_parts) / len(score_parts)), 1)
    return {
        "quality_score": quality_score,
        "confidence": _confidence_label(quality_score / 100),
        "warnings": warnings,
        "account_rows": account_rows,
        "transaction_rows": transaction_rows,
        "feature_rows": feature_rows,
        "account_match_rate": round(match_rate, 4),
        "transaction_months": months,
        "mapped_account_columns": account_cols,
        "mapped_transaction_columns": txn_cols,
        "file_count": int(len(file_ledger)) if file_ledger is not None else 0,
    }


def read_input_table(path: Path | str) -> pd.DataFrame:
    """Read a supported local input file for the CLI."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in {".csv", ".txt", ".dat", ""}:
        return _read_text_input_table(p)
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(p)
    if suffix == ".parquet":
        return pd.read_parquet(p)
    raise ValueError(f"Unsupported input file type: {p}")


def _read_text_input_table(path: Path) -> pd.DataFrame:
    sample = path.read_text(encoding="utf-8", errors="replace")[:65536]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t|;").delimiter
    except csv.Error:
        delimiter = "," if "," in sample else "\t" if "\t" in sample else "|"

    try:
        df = pd.read_csv(path, sep=delimiter)
    except Exception:
        df = pd.DataFrame()
    if not df.empty and (_has_core_transaction_columns(df) or _find_column(df, ACCOUNT_ID_COLUMNS)):
        return df

    for candidate in _positional_text_candidates(path, delimiter):
        positional = _best_positional_transaction_frame(candidate)
        if positional is not None:
            return positional
    if not df.empty:
        return df
    raise ValueError(f"Could not parse delimited text file: {path}")


def _positional_text_candidates(path: Path, delimiter: str) -> list[pd.DataFrame]:
    candidates: list[pd.DataFrame] = []
    for skiprows in (0, 1):
        try:
            frame = pd.read_csv(path, sep=delimiter, header=None, skiprows=skiprows)
        except Exception:
            continue
        if not frame.empty:
            candidates.append(frame)
    return candidates


def _has_core_transaction_columns(df: pd.DataFrame) -> bool:
    return (
        _find_column(df, ACCOUNT_ID_COLUMNS) is not None
        and _find_column(df, DATE_COLUMNS) is not None
        and _find_column(df, AMOUNT_COLUMNS) is not None
    )


def _best_positional_transaction_frame(df: pd.DataFrame) -> pd.DataFrame | None:
    if df.empty or len(df.columns) < 4:
        return None
    candidates = [df]
    if len(df) > 1:
        candidates.append(df.iloc[1:].reset_index(drop=True))
    scored = []
    for candidate in candidates:
        if candidate.empty:
            continue
        date_score = pd.to_datetime(candidate.iloc[:, 0], errors="coerce").notna().mean()
        amount_score = pd.to_numeric(candidate.iloc[:, 3], errors="coerce").notna().mean()
        scored.append((float(date_score) + float(amount_score), candidate))
    if not scored:
        return None
    score, best = max(scored, key=lambda item: item[0])
    if score < 1.0:
        return None
    return _standardize_positional_transaction_columns(best)


def _standardize_positional_transaction_columns(df: pd.DataFrame) -> pd.DataFrame:
    names = [
        "transaction_date",
        "primary_account_num",
        "transaction_type",
        "amount",
        "mcc_code",
        "merchant_name",
        "terminal_location_1",
        "terminal_location_2",
        "terminal_id",
        "merchant_id",
        "institution",
        "card_present",
        "transaction_code",
    ]
    out = df.copy()
    out.columns = [names[index] if index < len(names) else f"extra_{index}" for index in range(len(out.columns))]
    return out


def _account_dimensions(accounts: pd.DataFrame | None) -> pd.DataFrame:
    if accounts is None or accounts.empty:
        return pd.DataFrame()
    account_col = _find_column(accounts, ACCOUNT_ID_COLUMNS)
    if account_col is None:
        return pd.DataFrame()
    df = accounts.copy()
    df["account_id"] = df[account_col].astype(str).str.strip()
    df = df[df["account_id"].ne("")]

    balance_col = _find_column(df, BALANCE_COLUMNS)
    debit_col = _find_column(df, DEBIT_COLUMNS)
    business_col = _find_column(df, BUSINESS_COLUMNS)
    branch_col = _find_column(df, BRANCH_COLUMNS)
    product_col = _find_column(df, PRODUCT_COLUMNS)
    opened_col = _find_column(df, DATE_OPENED_COLUMNS)
    status_col = _find_column(df, STATUS_COLUMNS)

    df["_balance"] = _numeric(df[balance_col]) if balance_col else 0.0
    df["_has_debit"] = _truthy_series(df[debit_col]) if debit_col else False
    df["_business_flag"] = _truthy_series(df[business_col]) if business_col else False
    df["_branch"] = df[branch_col].astype(str).str.strip() if branch_col else ""
    df["_product_code"] = df[product_col].astype(str).str.strip() if product_col else ""
    df["_date_opened"] = pd.to_datetime(df[opened_col], errors="coerce") if opened_col else pd.NaT
    df["_account_status"] = df[status_col].astype(str).str.strip() if status_col else ""

    grouped = df.groupby("account_id", dropna=False).agg(
        balance=("_balance", "max"),
        has_debit=("_has_debit", "max"),
        business_flag=("_business_flag", "max"),
        branch=("_branch", _first_non_empty),
        product_code=("_product_code", _join_unique),
        product_count=("_product_code", lambda s: int(s.replace("", np.nan).dropna().nunique())),
        date_opened=("_date_opened", "min"),
        account_status=("_account_status", _first_non_empty),
    )
    return grouped.reset_index()


def _transaction_features(transactions: pd.DataFrame | None) -> pd.DataFrame:
    if transactions is None or transactions.empty:
        return pd.DataFrame()
    account_col = _find_column(transactions, ACCOUNT_ID_COLUMNS)
    date_col = _find_column(transactions, DATE_COLUMNS)
    amount_col = _find_column(transactions, AMOUNT_COLUMNS)
    if account_col is None or date_col is None or amount_col is None:
        return pd.DataFrame()

    merchant_col = _find_column(transactions, MERCHANT_COLUMNS)
    type_col = _find_column(transactions, TYPE_COLUMNS)
    df = transactions.copy()
    df["account_id"] = df[account_col].astype(str).str.strip()
    df["transaction_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["amount"] = _numeric(df[amount_col])
    df = df[df["account_id"].ne("") & df["transaction_date"].notna()]
    if df.empty:
        return pd.DataFrame()

    merchant_text = df[merchant_col].astype(str) if merchant_col else ""
    type_text = df[type_col].astype(str) if type_col else ""
    df["_text"] = (merchant_text + " " + type_text).str.lower()
    df["period_month"] = df["transaction_date"].dt.to_period("M").astype(str)
    df["_is_credit"] = df["amount"].gt(0) | df["_text"].str.contains(
        r"credit|deposit|ach credit|direct dep", regex=True, na=False
    )
    df["_is_debit"] = df["amount"].lt(0) | df["_text"].str.contains(
        r"debit|purchase|pos|withdrawal|card|payment|ach debit", regex=True, na=False
    )
    df["_is_payroll"] = df["_is_credit"] & _contains_any(df["_text"], PAYROLL_TERMS)
    df["_is_external_fi"] = _contains_any(df["_text"], EXTERNAL_FI_TERMS)
    df["_is_financial_services"] = _contains_any(df["_text"], FINANCIAL_SERVICE_TERMS)
    df["_is_pin"] = df["_text"].str.contains(r"\bpin\b|pin[-_\s]?debit", regex=True, na=False)
    df["_is_sig"] = df["_text"].str.contains(
        r"\bsig\b|signature|signature[-_\s]?debit|credit[-_\s]?card",
        regex=True,
        na=False,
    )
    df["_is_card"] = df["_is_pin"] | df["_is_sig"] | df["_text"].str.contains(
        r"\bcard\b|debit[-_\s]?card|\bpurchase\b|\bpos\b",
        regex=True,
        na=False,
    )
    df["_merchant"] = merchant_text.astype(str).str.strip() if merchant_col else ""
    df["_spend_amount"] = np.where(df["_is_debit"], df["amount"].abs(), 0.0)
    df["_credit_amount"] = np.where(df["_is_credit"], df["amount"].abs(), 0.0)
    df["_payroll_amount"] = np.where(df["_is_payroll"], df["amount"].abs(), 0.0)
    df["_external_amount"] = np.where(df["_is_external_fi"], df["amount"].abs(), 0.0)
    df["_card_amount"] = np.where(df["_is_card"] & df["_is_debit"], df["amount"].abs(), 0.0)
    df["_pin_amount"] = np.where(df["_is_pin"] & df["_is_debit"], df["amount"].abs(), 0.0)
    df["_sig_amount"] = np.where(df["_is_sig"] & df["_is_debit"], df["amount"].abs(), 0.0)

    grouped = df.groupby(["account_id", "period_month"], dropna=False).agg(
        txn_count=("amount", "size"),
        active_days=("transaction_date", lambda s: int(s.dt.date.nunique())),
        first_txn_date=("transaction_date", "min"),
        last_txn_date=("transaction_date", "max"),
        spend_amount=("_spend_amount", "sum"),
        credit_amount=("_credit_amount", "sum"),
        net_amount=("amount", "sum"),
        payroll_count=("_is_payroll", "sum"),
        payroll_amount=("_payroll_amount", "sum"),
        external_fi_count=("_is_external_fi", "sum"),
        external_fi_amount=("_external_amount", "sum"),
        financial_services_count=("_is_financial_services", "sum"),
        card_txn_count=("_is_card", "sum"),
        card_amount=("_card_amount", "sum"),
        pin_txn_count=("_is_pin", "sum"),
        pin_amount=("_pin_amount", "sum"),
        sig_txn_count=("_is_sig", "sum"),
        sig_amount=("_sig_amount", "sum"),
        unique_merchants=("_merchant", lambda s: int(s.replace("", np.nan).dropna().nunique())),
    )
    grouped = grouped.reset_index()
    grouped["first_txn_date"] = pd.to_datetime(grouped["first_txn_date"], errors="coerce").dt.date.astype(str)
    grouped["last_txn_date"] = pd.to_datetime(grouped["last_txn_date"], errors="coerce").dt.date.astype(str)
    grouped["has_pin"] = grouped["pin_txn_count"].fillna(0).astype(float).gt(0)
    grouped["has_sig"] = grouped["sig_txn_count"].fillna(0).astype(float).gt(0)
    grouped["pin_ratio"] = _safe_ratio(grouped["pin_txn_count"], grouped["card_txn_count"]).clip(0, 1)
    grouped["sig_ratio"] = _safe_ratio(grouped["sig_txn_count"], grouped["card_txn_count"]).clip(0, 1)
    grouped["avg_ticket_amount"] = _safe_ratio(grouped["spend_amount"], grouped["txn_count"])
    grouped["spend_per_txn"] = grouped["avg_ticket_amount"]
    grouped["avg_pin_ticket"] = _safe_ratio(grouped["pin_amount"], grouped["pin_txn_count"])
    grouped["avg_sig_ticket"] = _safe_ratio(grouped["sig_amount"], grouped["sig_txn_count"])
    grouped["pin_interchange_est"] = grouped["pin_amount"] * 0.005
    grouped["sig_interchange_est"] = grouped["sig_amount"] * 0.015
    return grouped


def _mapped_columns(df: pd.DataFrame, groups: dict[str, Iterable[str]]) -> dict[str, str]:
    return {key: _find_column(df, candidates) or "" for key, candidates in groups.items()}


def _find_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    if df is None or df.empty:
        return None
    normalized = {_norm_col(col): col for col in df.columns}
    for cand in candidates:
        key = _norm_col(cand)
        if key in normalized:
            return normalized[key]
    for cand in candidates:
        key = _norm_col(cand)
        for normed, original in normalized.items():
            if key and (key in normed or normed in key):
                return original
    return None


def _norm_col(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0.0)


def _truthy_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().isin(
        {"Y", "YES", "TRUE", "T", "1", "D", "DC", "DEBIT", "HAS DEBIT"}
    )


def _contains_any(series: pd.Series, terms: Iterable[str]) -> pd.Series:
    escaped = [re.escape(term.lower()) for term in terms]
    return series.astype(str).str.lower().str.contains("|".join(escaped), regex=True, na=False)


def _transaction_feature_columns() -> list[str]:
    return [
        "txn_count",
        "active_days",
        "first_txn_date",
        "last_txn_date",
        "spend_amount",
        "credit_amount",
        "net_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "financial_services_count",
        "card_txn_count",
        "card_amount",
        "pin_txn_count",
        "pin_amount",
        "sig_txn_count",
        "sig_amount",
        "has_pin",
        "has_sig",
        "pin_ratio",
        "sig_ratio",
        "avg_ticket_amount",
        "spend_per_txn",
        "avg_pin_ticket",
        "avg_sig_ticket",
        "pin_interchange_est",
        "sig_interchange_est",
        "unique_merchants",
    ]


def _normalize_counterparty_name(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none"}:
        return "Unknown Counterparty"
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b(pos|ach|debit|credit|purchase|payment|transfer|withdrawal|deposit)\b", "", text, flags=re.I)
    text = re.sub(r"[^A-Za-z0-9& .'-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -.")
    if not text:
        return "Unknown Counterparty"
    return text[:80].title()


def _counterparty_category(row: pd.Series) -> str:
    text = str(row.get("_text", "") or "").lower()
    amount = float(row.get("amount", 0) or 0)
    if amount >= 0 and any(term in text for term in PAYROLL_TERMS):
        return "payroll"
    if any(term in text for term in FINANCIAL_SERVICE_TERMS):
        return "financial_services"
    if any(term in text for term in EXTERNAL_FI_TERMS):
        return "external_fi"
    if str(row.get("counterparty_name", "") or "") == "Unknown Counterparty":
        return "unknown"
    return "merchant"


def _counterparty_signal_strength(row: pd.Series) -> float:
    total_amount = float(row.get("total_amount", 0) or 0)
    txn_count = float(row.get("transaction_count", 0) or 0)
    recurrence = float(row.get("recurrence_score", 0) or 0)
    category = str(row.get("counterparty_category", "") or "")
    base = min(total_amount / 2500.0, 1.0) * 45
    activity = min(txn_count / 6.0, 1.0) * 25
    recurrence_part = recurrence * 20
    category_bonus = 10 if category in {"payroll", "external_fi", "financial_services"} else 0
    return round(min(base + activity + recurrence_part + category_bonus, 100), 1)


def _counterparty_relationship_signal(row: pd.Series) -> str:
    category = str(row.get("counterparty_category", "") or "")
    direction = str(row.get("direction", "") or "")
    if category == "payroll" and direction == "credit":
        return "income_source"
    if category == "external_fi" and direction == "debit":
        return "external_outflow_or_competitor_pull"
    if category == "external_fi" and direction == "credit":
        return "external_inflow_or_funding_source"
    if category == "financial_services":
        return "external_obligation_or_product_relationship"
    if category == "merchant":
        return "spend_relationship"
    return "unclassified_counterparty"


def _counterparty_confidence(row: pd.Series) -> str:
    category = str(row.get("counterparty_category", "") or "")
    txn_count = float(row.get("transaction_count", 0) or 0)
    recurrence = float(row.get("recurrence_score", 0) or 0)
    if category in {"payroll", "external_fi", "financial_services"} and (txn_count >= 2 or recurrence >= 0.5):
        return "high"
    if category != "unknown" and txn_count >= 2:
        return "medium"
    return "low"


def _counterparty_strategy_relevance(category: str, direction: str) -> str:
    if category == "payroll" and direction == "credit":
        return "primacy_proof"
    if category == "external_fi" and direction == "debit":
        return "competitor_or_deposit_leakage"
    if category == "external_fi" and direction == "credit":
        return "external_funding_relationship"
    if category == "financial_services":
        return "external_product_or_obligation"
    if category == "merchant":
        return "spend_behavior"
    return "review"


def _pct(num: float, den: float) -> float:
    return round(100 * float(num or 0) / max(float(den or 0), 1.0), 1)


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "unknown"


def _sum_numeric(df: pd.DataFrame | None, column: str) -> float:
    if df is None or df.empty or column not in df.columns:
        return 0.0
    return round(float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum()), 2)


def _segment_account_count(segment_summary: pd.DataFrame | None, groups: set[str]) -> int:
    if segment_summary is None or segment_summary.empty or "segment_group" not in segment_summary.columns:
        return 0
    df = segment_summary[segment_summary["segment_group"].astype(str).isin(groups)]
    if df.empty or "account_count" not in df.columns:
        return 0
    return int(pd.to_numeric(df["account_count"], errors="coerce").fillna(0).sum())


def _segment_risk_count(relationship_segments: pd.DataFrame | None, risk_levels: set[str]) -> int:
    if relationship_segments is None or relationship_segments.empty or "risk_level" not in relationship_segments.columns:
        return 0
    df = relationship_segments[relationship_segments["risk_level"].astype(str).str.lower().isin(risk_levels)]
    return int(df["account_id"].nunique()) if "account_id" in df.columns else int(len(df))


def _scorecard_row(
    cfg: EngineConfig,
    *,
    domain: str,
    metric_name: str,
    metric_value: Any,
    metric_display: str,
    benchmark: str,
    score: float,
    interpretation: str,
    recommended_focus: str,
    owner_role: str,
    source_artifacts: str,
    inverse: bool = False,
    neutral: bool = False,
) -> dict[str, Any]:
    score_value = round(float(score or 0), 1)
    return {
        "scorecard_id": f"{cfg.client_id}:{cfg.period_month}:scorecard:{_slug(domain)}",
        "client_id": cfg.client_id,
        "period_month": _period_label(cfg.period_month),
        "domain": domain,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "metric_display": metric_display,
        "benchmark": benchmark,
        "score": score_value,
        "rag_status": _rag_status(score_value, inverse=inverse, neutral=neutral),
        "interpretation": interpretation,
        "recommended_focus": recommended_focus,
        "owner_role": owner_role,
        "source_artifacts": source_artifacts,
        "model_version": "executive_scorecard_v0_rules",
    }


def _rag_status(score: float, *, inverse: bool = False, neutral: bool = False) -> str:
    if neutral:
        return "Gray"
    if inverse:
        if score >= 60:
            return "Green"
        if score >= 30:
            return "Amber"
        return "Red"
    if score >= 80:
        return "Green"
    if score >= 60:
        return "Amber"
    return "Red"


def _roadmap_metric(row: dict[str, Any], measurement_plan: pd.DataFrame | None) -> str:
    measurement_id = row.get("measurement_id", "")
    if measurement_plan is not None and not measurement_plan.empty and measurement_id:
        match = measurement_plan[measurement_plan["measurement_id"].astype(str).eq(str(measurement_id))]
        if not match.empty:
            metric = match.iloc[0].get("primary_metric", "")
            if metric:
                return str(metric)
    return _outcome_metric_for_opportunity(str(row.get("opportunity_type", "")))


def _opportunity_rollup(opportunities: pd.DataFrame | None) -> pd.DataFrame:
    if opportunities is None or opportunities.empty:
        return pd.DataFrame(
            columns=[
                "account_id",
                "period_month",
                "top_opportunity_type",
                "top_priority_score",
                "opportunity_count",
                "total_expected_value",
            ]
        )
    ranked = opportunities.sort_values(
        ["account_id", "period_month", "priority_score", "expected_value"],
        ascending=[True, True, False, False],
    )
    top = ranked.groupby(["account_id", "period_month"], as_index=False).first()[
        ["account_id", "period_month", "opportunity_type", "priority_score"]
    ].rename(
        columns={
            "opportunity_type": "top_opportunity_type",
            "priority_score": "top_priority_score",
        }
    )
    totals = ranked.groupby(["account_id", "period_month"], as_index=False).agg(
        opportunity_count=("opportunity_id", "nunique"),
        total_expected_value=("expected_value", "sum"),
    )
    return top.merge(totals, on=["account_id", "period_month"], how="left")


def _account_opportunity_rollup(opportunities: pd.DataFrame | None) -> pd.DataFrame:
    if opportunities is None or opportunities.empty:
        return pd.DataFrame(
            columns=[
                "account_id",
                "period_month",
                "top_opportunity_type",
                "top_play_name",
                "top_priority_score",
                "top_expected_value",
                "opportunity_count",
                "total_expected_value",
                "recommended_action",
                "opportunity_reason_codes",
            ]
        )

    ranked = opportunities.copy().sort_values(
        ["account_id", "period_month", "priority_score", "expected_value"],
        ascending=[True, True, False, False],
    )
    rows: list[dict[str, Any]] = []
    for keys, group in ranked.groupby(["account_id", "period_month"], dropna=False):
        account_id, period_month = keys
        top = group.iloc[0]
        opportunity_type = str(top.get("opportunity_type", ""))
        playbook = OPPORTUNITY_PLAYBOOK.get(opportunity_type, {})
        rows.append(
            {
                "account_id": account_id,
                "period_month": period_month,
                "top_opportunity_type": opportunity_type,
                "top_play_name": playbook.get("play_name", opportunity_type.replace("_", " ").title()),
                "top_priority_score": round(float(top.get("priority_score", 0) or 0), 1),
                "top_expected_value": round(float(top.get("expected_value", 0) or 0), 2),
                "opportunity_count": int(group["opportunity_id"].nunique()) if "opportunity_id" in group else len(group),
                "total_expected_value": round(float(pd.to_numeric(group["expected_value"], errors="coerce").fillna(0).sum()), 2),
                "recommended_action": top.get("recommended_action", ""),
                "opportunity_reason_codes": "|".join(_top_tokens(group["reason_codes"], limit=5)) if "reason_codes" in group else "",
            }
        )
    return pd.DataFrame(rows)


def _account_counterparty_rollup(counterparty_signals: pd.DataFrame | None) -> pd.DataFrame:
    if counterparty_signals is None or counterparty_signals.empty:
        return pd.DataFrame(
            columns=[
                "account_id",
                "period_month",
                "top_counterparties",
                "payroll_counterparties",
                "external_fi_counterparties",
                "financial_services_counterparties",
            ]
        )

    df = counterparty_signals.copy()
    for col in ["signal_strength", "total_amount", "transaction_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df = df.sort_values(
        ["account_id", "period_month", "signal_strength", "total_amount", "transaction_count"],
        ascending=[True, True, False, False, False],
    )

    rows: list[dict[str, Any]] = []
    for keys, group in df.groupby(["account_id", "period_month"], dropna=False):
        account_id, period_month = keys
        rows.append(
            {
                "account_id": account_id,
                "period_month": period_month,
                "top_counterparties": _counterparty_list(group, limit=3),
                "payroll_counterparties": _counterparty_list(
                    group[group["counterparty_category"].astype(str).eq("payroll")],
                    limit=3,
                ),
                "external_fi_counterparties": _counterparty_list(
                    group[group["counterparty_category"].astype(str).eq("external_fi")],
                    limit=3,
                ),
                "financial_services_counterparties": _counterparty_list(
                    group[group["counterparty_category"].astype(str).eq("financial_services")],
                    limit=3,
                ),
            }
        )
    return pd.DataFrame(rows)


def _account_target_rollup(campaign_targets: pd.DataFrame | None) -> pd.DataFrame:
    if campaign_targets is None or campaign_targets.empty:
        return pd.DataFrame(
            columns=[
                "account_id",
                "period_month",
                "target_status",
                "measurement_group",
                "owner_role",
                "recommended_channel",
                "action_id",
                "measurement_id",
            ]
        )

    df = campaign_targets.copy()
    if "priority_score" in df.columns:
        df["priority_score"] = pd.to_numeric(df["priority_score"], errors="coerce").fillna(0.0)
    else:
        df["priority_score"] = 0.0
    if "priority_rank" in df.columns:
        df["priority_rank"] = pd.to_numeric(df["priority_rank"], errors="coerce").fillna(9999)
    else:
        df["priority_rank"] = 9999
    rows: list[dict[str, Any]] = []
    for keys, group in df.sort_values(
        ["account_id", "period_month", "priority_rank", "priority_score"],
        ascending=[True, True, True, False],
    ).groupby(["account_id", "period_month"], dropna=False):
        account_id, period_month = keys
        top = group.iloc[0]
        rows.append(
            {
                "account_id": account_id,
                "period_month": period_month,
                "target_status": top.get("target_status", ""),
                "measurement_group": top.get("measurement_group", ""),
                "owner_role": top.get("owner_role", ""),
                "recommended_channel": top.get("recommended_channel", ""),
                "action_id": top.get("action_id", ""),
                "measurement_id": top.get("measurement_id", ""),
            }
        )
    return pd.DataFrame(rows)


def _counterparty_list(group: pd.DataFrame, *, limit: int) -> str:
    if group is None or group.empty:
        return ""
    items: list[str] = []
    for row in group.head(limit).to_dict("records"):
        name = str(row.get("counterparty_name", "")).strip()
        if not name:
            continue
        category = str(row.get("counterparty_category", "")).strip()
        amount = _story_money(row.get("total_amount", 0))
        items.append(f"{name} ({category}, {amount})" if category else f"{name} ({amount})")
    return "|".join(items)


def _relationship_segment_for_row(row: dict[str, Any], cfg: EngineConfig) -> dict[str, Any]:
    txn_count = float(row.get("txn_count", 0) or 0)
    balance = float(row.get("balance", 0) or 0)
    product_count = float(row.get("product_count", 0) or 0)
    external_count = float(row.get("external_fi_count", 0) or 0)
    external_amount = float(row.get("external_fi_amount", 0) or 0)
    external_intensity = float(row.get("external_intensity", 0) or 0)
    financial_count = float(row.get("financial_services_count", 0) or 0)
    credit_amount = float(row.get("credit_amount", 0) or 0)
    payroll = bool(row.get("payroll_detected", False))
    has_debit = bool(row.get("has_debit", False))
    pfi = str(row.get("pfi_verdict", "No verdict") or "No verdict")
    top_opp = str(row.get("top_opportunity_type", "") or "")

    if pfi == "Primary with us" and payroll:
        return {
            "relationship_segment": "Primary Payroll Relationship",
            "segment_group": "Retain",
            "lifecycle_stage": "Protect",
            "risk_level": "low",
            "next_best_motion": "Protect payroll relationship and deepen product usage.",
            "segment_reason_codes": ["payroll_detected", "primary_with_us"],
        }
    if pfi in {"Split", "Competitor-primary"} and external_intensity >= 0.30:
        return {
            "relationship_segment": "Split Wallet / Competitor Pull",
            "segment_group": "Win Back",
            "lifecycle_stage": "Recover",
            "risk_level": "high" if pfi == "Competitor-primary" else "medium",
            "next_best_motion": "Prioritize consolidation or retention outreach.",
            "segment_reason_codes": ["external_fi_intensity", pfi.lower().replace(" ", "_")],
        }
    if top_opp == "payroll_conversion" or (not payroll and (external_count > 0 or credit_amount >= cfg.payroll_min_amount)):
        return {
            "relationship_segment": "Primary Banking Conversion Candidate",
            "segment_group": "Grow",
            "lifecycle_stage": "Convert",
            "risk_level": "medium",
            "next_best_motion": "Target for direct deposit or primary banking conversion.",
            "segment_reason_codes": ["no_payroll_detected", "money_movement_present"],
        }
    if financial_count > 0 and product_count <= 1:
        return {
            "relationship_segment": "External Lending / Financial Services Relationship",
            "segment_group": "Expand",
            "lifecycle_stage": "Cross-sell",
            "risk_level": "medium",
            "next_best_motion": "Review for lending or relationship expansion offer.",
            "segment_reason_codes": ["external_financial_service", "thin_relationship"],
        }
    if txn_count <= cfg.low_activity_txn_threshold and (balance > 100 or product_count > 0):
        return {
            "relationship_segment": "Dormant Save Candidate",
            "segment_group": "Reactivate",
            "lifecycle_stage": "Save",
            "risk_level": "high",
            "next_best_motion": "Queue for reactivation or save-list outreach.",
            "segment_reason_codes": ["low_activity", "relationship_value_present"],
        }
    if (not has_debit or txn_count <= cfg.active_txn_threshold) and balance >= 0:
        return {
            "relationship_segment": "Engagement Activation Candidate",
            "segment_group": "Activate",
            "lifecycle_stage": "Activate",
            "risk_level": "medium",
            "next_best_motion": "Prompt debit, wallet, or digital engagement.",
            "segment_reason_codes": ["weak_debit_or_activity", "eligible_account"],
        }
    if pfi == "Primary with us":
        return {
            "relationship_segment": "Engaged Core Relationship",
            "segment_group": "Retain",
            "lifecycle_stage": "Deepen",
            "risk_level": "low",
            "next_best_motion": "Maintain relationship and monitor for expansion signals.",
            "segment_reason_codes": ["primary_with_us", "active_relationship"],
        }
    return {
        "relationship_segment": "Low Signal / Monitor",
        "segment_group": "Monitor",
        "lifecycle_stage": "Monitor",
        "risk_level": "unknown",
        "next_best_motion": "Monitor until stronger behavior appears or add more data.",
        "segment_reason_codes": ["insufficient_signal"],
    }


def _segment_readiness_score(row: dict[str, Any]) -> float:
    priority = float(row.get("top_priority_score", 0) or 0)
    confidence = float(row.get("confidence_score", 0) or 0)
    expected_value = float(row.get("total_expected_value", 0) or 0)
    value_score = min(expected_value / 500.0, 20.0)
    return round(min(priority + (confidence * 20.0) + value_score, 100.0), 1)


def _unique_count(df: pd.DataFrame | None, column: str) -> int:
    if df is None or df.empty or column not in df.columns:
        return 0
    return int(df[column].nunique())


def _top_play_name(action_plan: pd.DataFrame | None, portfolio: pd.DataFrame | None) -> str:
    if action_plan is not None and not action_plan.empty and "play_name" in action_plan.columns:
        return str(action_plan.iloc[0].get("play_name", "") or "")
    if portfolio is not None and not portfolio.empty and "play_name" in portfolio.columns:
        return str(portfolio.iloc[0].get("play_name", "") or "")
    return ""


def _portfolio_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No opportunity portfolio rows crossed the current V1 thresholds."
    lead = rows[0]
    return (
        f"{lead.get('play_name', 'The lead play')} covers "
        f"{int(float(lead.get('target_accounts', 0) or 0)):,} account(s) with "
        f"{_story_money(lead.get('expected_value'))} in modeled value."
    )


def _action_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No action plan was generated; validate file coverage and scoring thresholds."
    lead = rows[0]
    return (
        f"Start with {lead.get('play_name', 'the lead play')} owned by "
        f"{lead.get('owner_role', 'the client team')}; next step: "
        f"{lead.get('next_step', 'review the target list')}."
    )


def _executive_summary(
    *,
    top_actions: list[dict[str, Any]],
    quality_score: Any,
    confidence: str,
    warnings: list[Any],
    outcome_message: str,
) -> str:
    quality_text = quality_score if quality_score is not None else "unknown"
    if not top_actions:
        return (
            f"The run produced a quality score of {quality_text} with {confidence} confidence, "
            "but no action plan crossed V1 thresholds. Review data coverage, warnings, and "
            "opportunity thresholds before client presentation."
        )
    lead = top_actions[0]
    return (
        f"The lead recommendation is {lead.get('play_name', 'the top play')} for "
        f"{int(float(lead.get('target_accounts', 0) or 0)):,} target account(s), "
        f"supported by a quality score of {quality_text} and {confidence} confidence. "
        f"{len(warnings)} data warning(s) should be reviewed before presentation. "
        f"{outcome_message}"
    )


def _story_money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _empty_features() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "account_id",
            "period_month",
            "matched_account",
            *_transaction_feature_columns(),
            "balance",
            "has_debit",
            "business_flag",
            "branch",
            "product_code",
            "product_count",
            "account_status",
            "date_opened",
            "external_intensity",
            "payroll_detected",
            "engagement_tier",
            "feature_version",
        ]
    )


def _empty_account_intelligence_profile() -> pd.DataFrame:
    return pd.DataFrame(columns=_account_intelligence_profile_columns())


def _csm_review_queue_columns() -> list[str]:
    return [
        "review_rank",
        "client_id",
        "period_month",
        "account_id",
        "relationship_segment",
        "risk_level",
        "pfi_verdict",
        "top_play_name",
        "top_priority_score",
        "total_expected_value",
        "recommended_action",
        "evidence_summary",
        "owner_role",
        "recommended_channel",
        "source_profile_id",
        "model_version",
    ]


def _marketing_activation_export_columns() -> list[str]:
    return [
        "client_id",
        "period_month",
        "action_id",
        "measurement_id",
        "account_id",
        "play_name",
        "opportunity_type",
        "target_rank_within_play",
        "measurement_group",
        "target_status",
        "recommended_channel",
        "priority_score",
        "expected_value",
        "confidence",
        "reason_codes",
        "primary_metric",
        "branch",
        "product_code",
        "model_version",
    ]


def _banker_call_list_columns() -> list[str]:
    return [
        "call_rank",
        "client_id",
        "period_month",
        "account_id",
        "branch",
        "relationship_segment",
        "risk_level",
        "pfi_verdict",
        "top_play_name",
        "top_priority_score",
        "total_expected_value",
        "recommended_action",
        "talk_track",
        "top_counterparties",
        "evidence_summary",
        "action_id",
        "measurement_id",
        "model_version",
    ]


def _analyst_validation_queue_columns() -> list[str]:
    return [
        "item_rank",
        "client_id",
        "period_month",
        "severity",
        "item_type",
        "item_id",
        "issue",
        "recommended_action",
        "source_artifact",
        "model_version",
    ]


def _data_team_load_plan_columns() -> list[str]:
    return [
        "load_rank",
        "client_id",
        "period_month",
        "file_name",
        "source_path",
        "source_family",
        "contract_id",
        "assembly_role",
        "load_flag",
        "target_engine_input",
        "target_snowflake_layer",
        "missing_required_count",
        "contract_needed_count",
        "load_readiness",
        "operator_action",
        "layout_gap_actions",
        "model_version",
    ]


def _source_layout_profile_columns() -> list[str]:
    return [
        "profile_rank",
        "client_id",
        "period_month",
        "file_name",
        "source_path",
        "detected_format",
        "delimiter",
        "header_mode",
        "column_count",
        "estimated_rows",
        "source_family",
        "contract_id",
        "match_status",
        "match_score",
        "intake_decision",
        "source_column",
        "source_position",
        "source_column_key",
        "matched_canonical_fields",
        "canonical_mapping_status",
        "required_flag",
        "data_type",
        "confidence",
        "column_role_guess",
        "proposed_input_family",
        "missing_required_fields",
        "proposed_contract_id",
        "mapping_action",
        "source_artifacts",
        "model_version",
    ]


def _layout_contract_draft_queue_columns() -> list[str]:
    return [
        "draft_rank",
        "client_id",
        "period_month",
        "file_name",
        "source_path",
        "source_family",
        "detected_format",
        "delimiter",
        "header_mode",
        "estimated_rows",
        "match_status",
        "match_score",
        "current_contract_id",
        "proposed_contract_id",
        "contract_action",
        "priority_band",
        "missing_required_fields",
        "matched_canonical_fields",
        "unmapped_source_columns",
        "source_columns",
        "draft_alias_map",
        "draft_yaml",
        "data_team_action",
        "analyst_question",
        "target_snowflake_layer",
        "source_artifacts",
        "model_version",
    ]


def _layout_contract_export_manifest_columns() -> list[str]:
    return [
        "export_rank",
        "client_id",
        "period_month",
        "file_name",
        "source_path",
        "source_family",
        "proposed_contract_id",
        "contract_action",
        "priority_band",
        "yaml_file_name",
        "yaml_relative_path",
        "yaml_ready",
        "target_snowflake_layer",
        "missing_required_fields",
        "matched_canonical_fields",
        "data_team_action",
        "analyst_question",
        "source_artifacts",
        "model_version",
    ]


def _intelligence_lineage_graph_columns() -> list[str]:
    return [
        "edge_rank",
        "client_id",
        "period_month",
        "lineage_stage",
        "source_node_type",
        "source_node_id",
        "source_label",
        "target_node_type",
        "target_node_id",
        "target_label",
        "relationship",
        "edge_status",
        "owner_role",
        "business_question",
        "analysis_section_id",
        "input_family",
        "field_key",
        "output_artifact",
        "target_table",
        "proof_artifacts",
        "next_action",
        "source_artifacts",
        "model_version",
    ]


def _stakeholder_export_manifest_columns() -> list[str]:
    return [
        "export_rank",
        "client_id",
        "period_month",
        "artifact_name",
        "file_name",
        "primary_role",
        "row_count",
        "use_case",
        "first_action",
        "status",
        "model_version",
    ]


def _validation_item(
    cfg: EngineConfig,
    *,
    item_rank: int,
    severity: str,
    item_type: str,
    item_id: str,
    issue: str,
    recommended_action: str,
    source_artifact: str,
) -> dict[str, Any]:
    return {
        "item_rank": item_rank,
        "client_id": cfg.client_id,
        "period_month": cfg.period_month,
        "severity": severity,
        "item_type": item_type,
        "item_id": item_id,
        "issue": issue,
        "recommended_action": recommended_action,
        "source_artifact": source_artifact,
        "model_version": "stakeholder_export_v0_rules",
    }


def _account_intelligence_profile_columns() -> list[str]:
    return [
        "profile_id",
        "client_id",
        "account_id",
        "period_month",
        "relationship_segment",
        "segment_group",
        "lifecycle_stage",
        "risk_level",
        "pfi_verdict",
        "pfi_score",
        "confidence",
        "engagement_tier",
        "balance",
        "txn_count",
        "active_days",
        "payroll_detected",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "external_intensity",
        "product_count",
        "has_debit",
        "branch",
        "product_code",
        "top_counterparties",
        "payroll_counterparties",
        "external_fi_counterparties",
        "financial_services_counterparties",
        "top_opportunity_type",
        "top_play_name",
        "top_priority_score",
        "top_expected_value",
        "opportunity_count",
        "total_expected_value",
        "target_status",
        "measurement_group",
        "owner_role",
        "recommended_channel",
        "recommended_action",
        "next_best_motion",
        "action_id",
        "measurement_id",
        "evidence_summary",
        "reason_codes",
        "source_artifacts",
        "model_version",
    ]


def _model_rulebook_columns() -> list[str]:
    return [
        "rule_id",
        "rule_family",
        "rule_name",
        "applies_to",
        "condition",
        "thresholds",
        "outputs",
        "evidence_fields",
        "source_artifacts",
        "owner_role",
        "consulting_use",
        "model_version",
    ]


def _account_scoring_trace_columns() -> list[str]:
    return [
        "trace_id",
        "client_id",
        "account_id",
        "period_month",
        "profile_id",
        "pfi_verdict",
        "pfi_score",
        "internal_score",
        "external_score",
        "confidence",
        "confidence_score",
        "pfi_reason_codes",
        "pfi_thresholds",
        "relationship_segment",
        "segment_group",
        "lifecycle_stage",
        "risk_level",
        "opportunity_readiness_score",
        "segment_reason_codes",
        "segment_rule",
        "top_opportunity_type",
        "top_play_name",
        "top_priority_score",
        "top_expected_value",
        "opportunity_count",
        "total_expected_value",
        "opportunity_reason_codes",
        "opportunity_rule",
        "all_opportunity_types",
        "txn_count",
        "active_days",
        "spend_amount",
        "credit_amount",
        "payroll_count",
        "payroll_amount",
        "external_fi_count",
        "external_fi_amount",
        "external_intensity",
        "financial_services_count",
        "balance",
        "product_count",
        "has_debit",
        "payroll_detected",
        "engagement_tier",
        "branch",
        "product_code",
        "target_status",
        "measurement_group",
        "owner_role",
        "recommended_channel",
        "recommended_action",
        "evidence_summary",
        "decision_trace",
        "source_artifacts",
        "source_sections",
        "model_version",
    ]


def _engine_run_ledger_columns() -> list[str]:
    return [
        "ledger_rank",
        "client_id",
        "period_month",
        "run_stage",
        "stage_name",
        "owner_role",
        "status",
        "row_count",
        "metric_name",
        "metric_value",
        "input_artifacts",
        "output_artifacts",
        "snowflake_targets",
        "evidence_summary",
        "operator_action",
        "blocking_issue",
        "source_artifacts",
        "model_version",
    ]


def _empty_engine_run_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=_engine_run_ledger_columns())


def _engine_readiness_assessment_columns() -> list[str]:
    return [
        "assessment_rank",
        "client_id",
        "period_month",
        "readiness_area",
        "engine_layer",
        "owner_role",
        "readiness_status",
        "client_use_status",
        "severity",
        "evidence_metric",
        "evidence_value",
        "blocker_count",
        "validation_count",
        "evidence_summary",
        "blocking_issue",
        "next_action",
        "proof_artifacts",
        "snowflake_targets",
        "model_version",
    ]


def _empty_engine_readiness_assessment() -> pd.DataFrame:
    return pd.DataFrame(columns=_engine_readiness_assessment_columns())


def _operating_control_plane_columns() -> list[str]:
    return [
        "control_rank",
        "client_id",
        "period_month",
        "workflow_lane",
        "role",
        "role_type",
        "operating_question",
        "decision_owned",
        "current_status",
        "client_use_status",
        "priority_level",
        "open_first",
        "supporting_outputs",
        "export_artifact",
        "export_row_count",
        "evidence_summary",
        "blocker_summary",
        "next_action",
        "success_metric",
        "handoff_to",
        "source_artifacts",
        "snowflake_targets",
        "model_version",
    ]


def _empty_operating_control_plane() -> pd.DataFrame:
    return pd.DataFrame(columns=_operating_control_plane_columns())


def _engine_run_ledger_row(
    cfg: EngineConfig,
    *,
    rank: int,
    run_stage: str,
    stage_name: str,
    owner_role: str,
    status: str,
    row_count: int,
    metric_name: str,
    metric_value: Any,
    input_artifacts: str,
    output_artifacts: str,
    snowflake_targets: str,
    evidence_summary: str,
    operator_action: str,
    blocking_issue: str,
    source_artifacts: str,
) -> dict[str, Any]:
    return {
        "ledger_rank": rank,
        "client_id": cfg.client_id,
        "period_month": _period_label(cfg.period_month),
        "run_stage": run_stage,
        "stage_name": stage_name,
        "owner_role": owner_role,
        "status": status,
        "row_count": int(row_count),
        "metric_name": metric_name,
        "metric_value": metric_value,
        "input_artifacts": input_artifacts,
        "output_artifacts": output_artifacts,
        "snowflake_targets": snowflake_targets,
        "evidence_summary": evidence_summary,
        "operator_action": operator_action,
        "blocking_issue": blocking_issue,
        "source_artifacts": source_artifacts,
        "model_version": "engine_run_ledger_v0",
    }


def _engine_readiness_row(
    cfg: EngineConfig,
    *,
    rank: int,
    readiness_area: str,
    engine_layer: str,
    owner_role: str,
    readiness_status: str,
    client_use_status: str,
    severity: int,
    evidence_metric: str,
    evidence_value: Any,
    blocker_count: int,
    validation_count: int,
    evidence_summary: str,
    blocking_issue: str,
    next_action: str,
    proof_artifacts: str,
    snowflake_targets: str,
) -> dict[str, Any]:
    return {
        "assessment_rank": rank,
        "client_id": cfg.client_id,
        "period_month": _period_label(cfg.period_month),
        "readiness_area": readiness_area,
        "engine_layer": engine_layer,
        "owner_role": owner_role,
        "readiness_status": readiness_status,
        "client_use_status": client_use_status,
        "severity": int(severity),
        "evidence_metric": evidence_metric,
        "evidence_value": evidence_value,
        "blocker_count": int(blocker_count),
        "validation_count": int(validation_count),
        "evidence_summary": evidence_summary,
        "blocking_issue": blocking_issue,
        "next_action": next_action,
        "proof_artifacts": proof_artifacts,
        "snowflake_targets": snowflake_targets,
        "model_version": "engine_readiness_assessment_v0",
    }


def _intake_readiness_status(file_ledger: pd.DataFrame, intake_summary: dict[str, Any]) -> str:
    if file_ledger is None or file_ledger.empty:
        return "direct_input_loaded"
    if intake_summary.get("readiness_status") == "ready":
        return "ready"
    return "intake_review_required"


def _core_feature_readiness_status(account_month_features: pd.DataFrame, quality_score: float) -> str:
    if account_month_features is None or account_month_features.empty:
        return "feature_mart_empty"
    if quality_score < 70:
        return "quality_review_required"
    return "ready"


def _analysis_evidence_readiness_status(blocker_count: int, review_count: int) -> str:
    if blocker_count > 0:
        return "analysis_supported_with_layout_blockers"
    if review_count > 0:
        return "validate_before_external_use"
    return "ready"


def _snowflake_handoff_readiness_status(
    layout_blocker_count: int,
    data_backlog_count: int,
    metric_validation_count: int,
) -> str:
    if layout_blocker_count == 0 and data_backlog_count == 0 and metric_validation_count == 0:
        return "ready"
    if layout_blocker_count == 0 and data_backlog_count == 0:
        return "ready_with_metric_validation"
    return "package_ready_with_known_gaps"


def _production_backlog_priority(
    priority_band: str,
    *,
    client_use_status: str = "",
    problem_statement: str = "",
) -> str:
    explicit = _trace_text(priority_band).upper()
    if explicit in {"P0", "P1", "P2", "P3"}:
        return explicit
    text = " ".join(
        token.lower()
        for token in [client_use_status, problem_statement]
        if _trace_text(token)
    )
    if any(token in text for token in ["block", "missing", "required", "cannot", "not satisfied"]):
        return "P0"
    if any(token in text for token in ["qualified", "review", "validation", "known_gaps", "caveat"]):
        return "P1"
    if any(token in text for token in ["planning", "partial", "approved", "documented"]):
        return "P2"
    return "P3"


def _production_backlog_priority_from_readiness(
    severity: int,
    client_use_status: str,
    readiness_status: str,
) -> str:
    if severity >= 3 or "block" in _trace_text(client_use_status).lower():
        return "P0"
    if severity >= 2:
        return "P1"
    if _trace_text(readiness_status) != "ready":
        return "P2"
    return "P3"


def _production_backlog_priority_from_review(review_status: str) -> str:
    text = _trace_text(review_status).lower()
    if "layout" in text or "block" in text:
        return "P0"
    if "validation" in text or "review" in text:
        return "P1"
    return "P2"


def _production_workstream_for_area(readiness_area: str) -> str:
    area = _trace_text(readiness_area)
    if area in {"layout_contracts", "data_team_backlog", "snowflake_handoff"}:
        return "Data contracts / Snowflake"
    if area in {"metric_validation", "analysis_evidence_map"}:
        return "Metric validation"
    if area in {"monthly_file_drop", "core_feature_mart"}:
        return "Monthly intake"
    if area in {"activation_exports", "outcome_measurement"}:
        return "Activation / measurement"
    if area in {"intelligence_outputs"}:
        return "Client delivery"
    return "Productization"


def _status_needs_backlog(status: str) -> bool:
    text = _trace_text(status).lower()
    if not text:
        return False
    ready_statuses = {"ready", "client_ready", "production_ready", "planning_ready", "complete"}
    if text in ready_statuses:
        return False
    return any(
        token in text
        for token in [
            "block",
            "review",
            "qualified",
            "validation",
            "gap",
            "partial",
            "missing",
            "known",
            "required",
            "open",
            "needs",
        ]
    )


def _sum_frame_column(df: pd.DataFrame | None, column: str) -> int:
    if df is None or df.empty or column not in df:
        return 0
    return int(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _run_ledger_analysis_status(analysis_counts: dict[str, Any]) -> str:
    if not analysis_counts:
        return "missing"
    if analysis_counts.get("blocked_by_input", 0) or analysis_counts.get("missing", 0):
        return "review"
    if analysis_counts.get("partial", 0):
        return "partial"
    return "ready"


def _export_row_counts(stakeholder_export_manifest: pd.DataFrame | None) -> dict[str, int]:
    if (
        stakeholder_export_manifest is None
        or stakeholder_export_manifest.empty
        or "artifact_name" not in stakeholder_export_manifest
    ):
        return {}
    rows: dict[str, int] = {}
    for row in stakeholder_export_manifest.to_dict("records"):
        artifact = _trace_text(row.get("artifact_name"))
        if not artifact:
            continue
        try:
            count = int(float(row.get("row_count", 0) or 0))
        except (TypeError, ValueError):
            count = 0
        rows[artifact] = count
        rows[f"{artifact}.csv"] = count
    return rows


def _control_export_row_count(export_artifact: str, export_rows: dict[str, int]) -> int:
    if not export_artifact:
        return 0
    if export_artifact in export_rows:
        return export_rows[export_artifact]
    key = export_artifact.removesuffix(".csv").removesuffix(".xlsx").removesuffix(".html").removesuffix(".sql")
    if key in export_rows:
        return export_rows[key]
    if export_artifact.endswith((".xlsx", ".html", ".sql")):
        return 1
    return 0


def _control_plane_blockers(
    role: str,
    role_type: str,
    engine_readiness_assessment: pd.DataFrame | None,
) -> list[str]:
    if engine_readiness_assessment is None or engine_readiness_assessment.empty:
        return []
    role_key = f"{role} {role_type}".lower()
    area_patterns = {
        "operator": ("monthly_file_drop", "data_quality", "intelligence_outputs", "analysis_evidence_map"),
        "relationship": ("intelligence_outputs", "activation_exports", "outcome_measurement"),
        "validation": ("data_quality", "analysis_evidence_map", "metric_validation"),
        "activation": ("activation_exports", "outcome_measurement"),
        "warehouse": ("layout_contracts", "data_team_backlog", "snowflake_handoff"),
        "execution": ("activation_exports", "outcome_measurement"),
    }
    selected_areas = area_patterns.get(role_type, ())
    blockers: list[str] = []
    for row in engine_readiness_assessment.to_dict("records"):
        issue = _trace_text(row.get("blocking_issue"))
        if not issue:
            continue
        area = _trace_text(row.get("readiness_area"))
        owner = _trace_text(row.get("owner_role")).lower()
        include = area in selected_areas
        if "data" in role_key and ("data" in owner or area in {"layout_contracts", "data_team_backlog", "snowflake_handoff"}):
            include = True
        if "analyst" in role_key and ("analyst" in owner or area in {"data_quality", "analysis_evidence_map", "metric_validation"}):
            include = True
        if include:
            blockers.append(f"{area}:{issue}")
    return blockers


def _control_client_use_status(current_status: str, blockers: list[str]) -> str:
    if blockers:
        return "qualified_use_with_open_blockers"
    if current_status in {"ready", "ready_for_client_review"}:
        return "ready_for_client_use"
    if current_status in {"review_before_client_use", "review_warnings", "needs_audience_review"}:
        return "review_before_client_use"
    return "internal_use"


def _control_priority_level(index: int, role_type: str, current_status: str, blockers: list[str]) -> str:
    if blockers:
        return "blocker"
    if current_status.startswith("review") or current_status.startswith("needs"):
        return "review"
    if index <= 2 or role_type in {"operator", "relationship"}:
        return "primary"
    return "secondary"


def _control_workflow_lane(role_type: str) -> str:
    return {
        "operator": "Approve package",
        "relationship": "Shape client story",
        "validation": "Validate analysis",
        "activation": "Activate audiences",
        "warehouse": "Load and publish data",
        "execution": "Execute outreach",
    }.get(role_type, "Operate engine")


def _control_operating_question(role: str, role_type: str) -> str:
    role_key = f"{role} {role_type}".lower()
    if "executive" in role_key or role_type == "operator":
        return "Is this run ready to become the client-facing intelligence package?"
    if "csm" in role_key or role_type == "relationship":
        return "What is the client story, lead play, and next meeting ask?"
    if "analyst" in role_key or role_type == "validation":
        return "Are the mappings, model rules, caveats, and evidence defensible?"
    if "marketing" in role_key or role_type == "activation":
        return "Which audience should be activated and how will measurement IDs survive execution?"
    if "snowflake" in role_key or role_type == "warehouse":
        return "Which generated tables should be loaded and what gaps remain before full productization?"
    if "banker" in role_key or role_type == "execution":
        return "Which accounts should receive outreach first and what should the team say?"
    return "What decision does this role own in the monthly intelligence workflow?"


def _control_open_first(handoff: dict[str, Any]) -> str:
    primary_screen = _trace_text(handoff.get("primary_screen"))
    export_artifact = _trace_text(handoff.get("export_artifact"))
    outputs = _trace_text(handoff.get("outputs_used"))
    if primary_screen and export_artifact:
        return f"{primary_screen} -> {export_artifact}"
    return primary_screen or export_artifact or outputs


def _control_source_artifacts(handoff: dict[str, Any], blockers: list[str]) -> str:
    outputs = _trace_text(handoff.get("outputs_used"))
    blocker_artifacts = "|".join(item.split(":", 1)[0] for item in blockers)
    return "|".join(item for item in [outputs, blocker_artifacts] if item)


def _control_snowflake_targets(role_type: str) -> str:
    if role_type == "warehouse":
        return "out.ti_operating_control_plane|out.ti_analysis_package_index|mart.ti_account_intelligence_profile"
    if role_type in {"activation", "execution"}:
        return "out.ti_operating_control_plane|out.ti_campaign_targets|out.ti_marketing_activation_export|out.ti_banker_call_list"
    if role_type == "validation":
        return "out.ti_operating_control_plane|out.ti_analyst_validation_queue|out.ti_analysis_section_evidence_review"
    if role_type == "relationship":
        return "out.ti_operating_control_plane|out.ti_consulting_insight_register|out.ti_action_plan"
    return "out.ti_operating_control_plane"


def _control_evidence_summary(
    *,
    role_type: str,
    quality_score: float,
    warning_count: int,
    top_play: str,
    action_count: int,
    export_row_count: int,
    scorecard_focus: str,
    review_sections: dict[str, int],
) -> str:
    if role_type in {"operator", "relationship"}:
        focus = f"; focus={scorecard_focus}" if scorecard_focus else ""
        play = f"; lead_play={top_play}" if top_play else ""
        return f"quality={quality_score:.1f}; warnings={warning_count}; action_rows={action_count}{play}{focus}"
    if role_type == "validation":
        review_bits = ",".join(f"{key}={value}" for key, value in sorted(review_sections.items()))
        return f"quality={quality_score:.1f}; warnings={warning_count}; section_review={review_bits or 'none'}"
    if role_type in {"activation", "execution"}:
        return f"export_rows={export_row_count}; action_rows={action_count}; lead_play={top_play or 'review action plan'}"
    if role_type == "warehouse":
        return "snowflake_manifest.json and snowflake_load.sql are generated with row-count lineage."
    return f"quality={quality_score:.1f}; warnings={warning_count}; export_rows={export_row_count}"


def _scorecard_focus(executive_scorecard: pd.DataFrame | None) -> str:
    if executive_scorecard is None or executive_scorecard.empty:
        return ""
    df = executive_scorecard.copy()
    if "rag_status" in df:
        weak = df[df["rag_status"].astype(str).isin(["Red", "Amber"])]
        if not weak.empty:
            row = weak.iloc[0]
            return _trace_text(row.get("recommended_focus")) or _trace_text(row.get("domain"))
    row = df.iloc[0]
    return _trace_text(row.get("recommended_focus")) or _trace_text(row.get("domain"))


def _top_roadmap_initiative(strategy_roadmap: pd.DataFrame | None) -> str:
    if strategy_roadmap is None or strategy_roadmap.empty:
        return ""
    return _trace_text(strategy_roadmap.iloc[0].get("initiative"))


def _section_review_status_counts(analysis_section_evidence_review: pd.DataFrame | None) -> dict[str, int]:
    if (
        analysis_section_evidence_review is None
        or analysis_section_evidence_review.empty
        or "section_review_status" not in analysis_section_evidence_review
    ):
        return {}
    return {
        str(key): int(value)
        for key, value in analysis_section_evidence_review["section_review_status"].value_counts().to_dict().items()
    }


def _intelligence_delta_report_columns() -> list[str]:
    return [
        "delta_rank",
        "client_id",
        "prior_period_month",
        "current_period_month",
        "delta_type",
        "entity_type",
        "entity_id",
        "account_id",
        "opportunity_type",
        "metric_name",
        "prior_value",
        "current_value",
        "delta_value",
        "prior_status",
        "current_status",
        "movement_direction",
        "severity",
        "evidence_summary",
        "recommended_action",
        "source_artifacts",
        "model_version",
    ]


def _empty_intelligence_delta_report() -> pd.DataFrame:
    return pd.DataFrame(columns=_intelligence_delta_report_columns())


def _delta_report_row(
    cfg: EngineConfig,
    *,
    rank: int,
    prior_period_month: str,
    current_period_month: str,
    delta_type: str,
    entity_type: str,
    entity_id: str,
    account_id: str,
    opportunity_type: str,
    metric_name: str,
    prior_value: Any,
    current_value: Any,
    delta_value: Any,
    prior_status: str,
    current_status: str,
    movement_direction: str,
    severity: str,
    evidence_summary: str,
    recommended_action: str,
    source_artifacts: str,
) -> dict[str, Any]:
    return {
        "delta_rank": rank,
        "client_id": cfg.client_id,
        "prior_period_month": prior_period_month,
        "current_period_month": current_period_month,
        "delta_type": delta_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "account_id": account_id,
        "opportunity_type": opportunity_type,
        "metric_name": metric_name,
        "prior_value": prior_value,
        "current_value": current_value,
        "delta_value": delta_value,
        "prior_status": prior_status,
        "current_status": current_status,
        "movement_direction": movement_direction,
        "severity": severity,
        "evidence_summary": evidence_summary,
        "recommended_action": recommended_action,
        "source_artifacts": source_artifacts,
        "model_version": "intelligence_delta_report_v0",
    }


def _prior_period_from_frames(*frames: pd.DataFrame | None) -> str:
    for frame in frames:
        if frame is None or frame.empty or "period_month" not in frame.columns:
            continue
        values = [_trace_text(value) for value in frame["period_month"].dropna().tolist()]
        if values:
            return _period_label(values[0])
    return ""


def _movement_direction(delta: float, *, positive_label: str = "increased", negative_label: str = "decreased") -> str:
    if delta > 0:
        return positive_label
    if delta < 0:
        return negative_label
    return "unchanged"


def _delta_report_is_baseline(delta_report: pd.DataFrame | None) -> bool:
    if delta_report is None or delta_report.empty or "delta_type" not in delta_report.columns:
        return False
    return set(delta_report["delta_type"].dropna().astype(str)) == {"baseline_run"}


def _portfolio_delta_rows(
    cfg: EngineConfig,
    *,
    current_portfolio: pd.DataFrame,
    prior_portfolio: pd.DataFrame | None,
    prior_period_month: str,
    current_period_month: str,
    start_rank: int,
) -> list[dict[str, Any]]:
    if prior_portfolio is None or prior_portfolio.empty or current_portfolio is None or current_portfolio.empty:
        return []
    current = _records_by_key(current_portfolio, "opportunity_type")
    prior = _records_by_key(prior_portfolio, "opportunity_type")
    rows: list[dict[str, Any]] = []
    for opportunity_type in sorted(set(current) | set(prior)):
        current_row = current.get(opportunity_type, {})
        prior_row = prior.get(opportunity_type, {})
        current_value = float(current_row.get("expected_value", 0) or 0)
        prior_value = float(prior_row.get("expected_value", 0) or 0)
        current_accounts = _safe_int_value(current_row.get("target_accounts"))
        prior_accounts = _safe_int_value(prior_row.get("target_accounts"))
        delta_value = current_value - prior_value
        if not current_row:
            delta_type = "portfolio_play_removed"
            movement = "removed"
            severity = "review"
        elif not prior_row:
            delta_type = "portfolio_play_added"
            movement = "added"
            severity = "info"
        elif delta_value or current_accounts != prior_accounts:
            delta_type = "portfolio_play_changed"
            movement = _movement_direction(delta_value)
            severity = "review" if delta_value < 0 else "info"
        else:
            continue
        rows.append(
            _delta_report_row(
                cfg,
                rank=start_rank + len(rows),
                prior_period_month=prior_period_month,
                current_period_month=current_period_month,
                delta_type=delta_type,
                entity_type="opportunity_portfolio",
                entity_id=opportunity_type,
                account_id="",
                opportunity_type=opportunity_type,
                metric_name="expected_value",
                prior_value=round(prior_value, 2),
                current_value=round(current_value, 2),
                delta_value=round(delta_value, 2),
                prior_status=f"target_accounts={prior_accounts}",
                current_status=f"target_accounts={current_accounts}",
                movement_direction=movement,
                severity=severity,
                evidence_summary=(
                    f"{opportunity_type} moved from {_story_money(prior_value)} across {prior_accounts} account(s) "
                    f"to {_story_money(current_value)} across {current_accounts} account(s)."
                ),
                recommended_action="Review play economics and account-count movement before changing strategy.",
                source_artifacts="opportunity_portfolio.csv",
            )
        )
    return rows


def _account_profile_delta_rows(
    cfg: EngineConfig,
    *,
    current_profile: pd.DataFrame,
    prior_profile: pd.DataFrame | None,
    prior_period_month: str,
    current_period_month: str,
    start_rank: int,
) -> list[dict[str, Any]]:
    if prior_profile is None or prior_profile.empty or current_profile is None or current_profile.empty:
        return []
    current = _records_by_key(current_profile, "account_id")
    prior = _records_by_key(prior_profile, "account_id")
    rows: list[dict[str, Any]] = []
    for account_id in sorted(set(current) | set(prior)):
        current_row = current.get(account_id, {})
        prior_row = prior.get(account_id, {})
        if not current_row:
            rows.append(
                _delta_report_row(
                    cfg,
                    rank=start_rank + len(rows),
                    prior_period_month=prior_period_month,
                    current_period_month=current_period_month,
                    delta_type="account_removed",
                    entity_type="account",
                    entity_id=account_id,
                    account_id=account_id,
                    opportunity_type=_trace_text(prior_row.get("top_opportunity_type")),
                    metric_name="account_presence",
                    prior_value="present",
                    current_value="missing",
                    delta_value="",
                    prior_status=_trace_text(prior_row.get("relationship_segment")),
                    current_status="not_in_current_profile",
                    movement_direction="removed",
                    severity="review",
                    evidence_summary=f"Account {account_id} was present in the prior profile but not the current profile.",
                    recommended_action="Confirm whether the account closed, was filtered out, or failed to map.",
                    source_artifacts="account_intelligence_profile.csv",
                )
            )
            continue
        if not prior_row:
            rows.append(
                _delta_report_row(
                    cfg,
                    rank=start_rank + len(rows),
                    prior_period_month=prior_period_month,
                    current_period_month=current_period_month,
                    delta_type="account_added",
                    entity_type="account",
                    entity_id=account_id,
                    account_id=account_id,
                    opportunity_type=_trace_text(current_row.get("top_opportunity_type")),
                    metric_name="account_presence",
                    prior_value="missing",
                    current_value="present",
                    delta_value="",
                    prior_status="not_in_prior_profile",
                    current_status=_trace_text(current_row.get("relationship_segment")),
                    movement_direction="added",
                    severity="info",
                    evidence_summary=f"Account {account_id} is new in the current profile.",
                    recommended_action="Review whether the account should enter activation, retention, or monitoring workflows.",
                    source_artifacts="account_intelligence_profile.csv",
                )
            )
            continue

        changed_fields = [
            field for field in ["pfi_verdict", "relationship_segment", "risk_level", "top_opportunity_type"]
            if _trace_text(prior_row.get(field)) != _trace_text(current_row.get(field))
        ]
        prior_priority = float(prior_row.get("top_priority_score", 0) or 0)
        current_priority = float(current_row.get("top_priority_score", 0) or 0)
        prior_value = float(prior_row.get("total_expected_value", 0) or 0)
        current_value = float(current_row.get("total_expected_value", 0) or 0)
        priority_delta = current_priority - prior_priority
        value_delta = current_value - prior_value
        if not changed_fields and abs(priority_delta) < 0.1 and abs(value_delta) < 0.01:
            continue
        rows.append(
            _delta_report_row(
                cfg,
                rank=start_rank + len(rows),
                prior_period_month=prior_period_month,
                current_period_month=current_period_month,
                delta_type="account_profile_changed",
                entity_type="account",
                entity_id=account_id,
                account_id=account_id,
                opportunity_type=_trace_text(current_row.get("top_opportunity_type")),
                metric_name="profile_change",
                prior_value=_profile_state_text(prior_row),
                current_value=_profile_state_text(current_row),
                delta_value=f"priority_delta={priority_delta:.1f};value_delta={value_delta:.2f}",
                prior_status=_trace_text(prior_row.get("risk_level")),
                current_status=_trace_text(current_row.get("risk_level")),
                movement_direction=_movement_direction(value_delta or priority_delta),
                severity="review" if _trace_text(current_row.get("risk_level")).lower() == "high" else "info",
                evidence_summary=f"Account {account_id} changed fields: {', '.join(changed_fields) if changed_fields else 'score/value only'}.",
                recommended_action="Inspect account scoring trace before changing outreach status.",
                source_artifacts="account_intelligence_profile.csv|account_scoring_trace.csv",
            )
        )
    return rows


def _opportunity_target_delta_rows(
    cfg: EngineConfig,
    *,
    current_opportunities: pd.DataFrame,
    prior_opportunities: pd.DataFrame | None,
    prior_period_month: str,
    current_period_month: str,
    start_rank: int,
) -> list[dict[str, Any]]:
    if prior_opportunities is None or prior_opportunities.empty or current_opportunities is None or current_opportunities.empty:
        return []
    current = _opportunity_records_by_account_type(current_opportunities)
    prior = _opportunity_records_by_account_type(prior_opportunities)
    rows: list[dict[str, Any]] = []
    for key in sorted(set(current) | set(prior)):
        account_id, opportunity_type = key.split("|", 1)
        current_row = current.get(key, {})
        prior_row = prior.get(key, {})
        prior_priority = float(prior_row.get("priority_score", 0) or 0)
        current_priority = float(current_row.get("priority_score", 0) or 0)
        priority_delta = current_priority - prior_priority
        if not current_row:
            delta_type = "opportunity_target_removed"
            movement = "removed"
            severity = "info"
        elif not prior_row:
            delta_type = "opportunity_target_added"
            movement = "added"
            severity = "review" if current_priority >= 50 else "info"
        elif abs(priority_delta) >= 5:
            delta_type = "opportunity_priority_changed"
            movement = _movement_direction(priority_delta)
            severity = "review" if current_priority >= 50 or priority_delta < 0 else "info"
        else:
            continue
        rows.append(
            _delta_report_row(
                cfg,
                rank=start_rank + len(rows),
                prior_period_month=prior_period_month,
                current_period_month=current_period_month,
                delta_type=delta_type,
                entity_type="account_opportunity",
                entity_id=key,
                account_id=account_id,
                opportunity_type=opportunity_type,
                metric_name="priority_score",
                prior_value=round(prior_priority, 1),
                current_value=round(current_priority, 1),
                delta_value=round(priority_delta, 1),
                prior_status=_trace_text(prior_row.get("pfi_verdict")),
                current_status=_trace_text(current_row.get("pfi_verdict")),
                movement_direction=movement,
                severity=severity,
                evidence_summary=f"{opportunity_type} for account {account_id} moved from priority {prior_priority:.1f} to {current_priority:.1f}.",
                recommended_action="Review target-list movement before suppressing, adding, or escalating the account.",
                source_artifacts="opportunities.csv|campaign_targets.csv",
            )
        )
    return rows


def _profile_state_text(row: dict[str, Any]) -> str:
    return (
        f"pfi={_trace_text(row.get('pfi_verdict'))};"
        f"segment={_trace_text(row.get('relationship_segment'))};"
        f"risk={_trace_text(row.get('risk_level'))};"
        f"top_play={_trace_text(row.get('top_play_name'))}"
    )


def _opportunity_records_by_account_type(opportunities: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if opportunities is None or opportunities.empty:
        return {}
    records: dict[str, dict[str, Any]] = {}
    for row in opportunities.to_dict("records"):
        account_id = _trace_text(row.get("account_id"))
        opportunity_type = _trace_text(row.get("opportunity_type"))
        if account_id and opportunity_type:
            records[f"{account_id}|{opportunity_type}"] = row
    return records


def _analysis_execution_map_columns() -> list[str]:
    return [
        "execution_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "product",
        "display_name",
        "analysis_family",
        "intelligence_layers",
        "source_path",
        "required_input_families",
        "input_readiness",
        "configured_script_count",
        "discovered_script_count",
        "runnable_script_count",
        "representative_scripts",
        "primary_engine_outputs",
        "available_engine_outputs",
        "missing_engine_outputs",
        "generated_output_files",
        "generated_target_tables",
        "generated_row_count",
        "output_row_counts",
        "evidence_status",
        "supported_opportunity_types",
        "model_rule_ids",
        "provenance_contributions",
        "consulting_question",
        "consulting_use",
        "analyst_next_step",
        "source_artifacts",
        "model_version",
    ]


def _analysis_domain_map_columns() -> list[str]:
    return [
        "domain_rank",
        "client_id",
        "period_month",
        "domain_id",
        "domain_name",
        "business_question",
        "source_section_ids",
        "section_count",
        "script_count",
        "runnable_script_count",
        "discovered_runtime_script_count",
        "analysis_families",
        "intelligence_layers",
        "required_input_families",
        "input_readiness",
        "evidence_status",
        "ready_sections",
        "partial_sections",
        "blocked_sections",
        "missing_sections",
        "inventory_only_sections",
        "primary_engine_outputs",
        "generated_output_files",
        "generated_target_tables",
        "generated_row_count",
        "opportunity_types",
        "model_rule_ids",
        "provenance_contributions",
        "consulting_use",
        "what_can_be_built_now",
        "waits_for_client_layouts",
        "next_decision",
        "source_artifacts",
        "model_version",
    ]


def _analysis_input_dependency_map_columns() -> list[str]:
    return [
        "dependency_rank",
        "client_id",
        "period_month",
        "input_family",
        "display_name",
        "canonical_role",
        "minimum_fields",
        "optional_fields",
        "source_candidates",
        "dependent_domains",
        "dependent_domain_names",
        "dependent_sections",
        "dependent_section_count",
        "dependent_script_count",
        "current_contract_status",
        "current_run_readiness",
        "matched_file_count",
        "selected_file_count",
        "missing_required_field_count",
        "contract_needed_file_count",
        "layout_mapping_status",
        "snowflake_design_decision",
        "analyst_next_step",
        "source_artifacts",
        "model_version",
    ]


def _monthly_file_requirements_columns() -> list[str]:
    return [
        "requirement_rank",
        "client_id",
        "period_month",
        "input_family",
        "display_name",
        "requirement_level",
        "monthly_status",
        "canonical_role",
        "minimum_fields",
        "optional_fields",
        "source_candidates",
        "dependent_domain_names",
        "dependent_sections",
        "dependent_section_count",
        "received_file_count",
        "selected_file_count",
        "received_file_names",
        "selected_file_names",
        "selected_contract_ids",
        "contract_actions",
        "priority_bands",
        "missing_required_field_count",
        "missing_required_fields",
        "current_run_readiness",
        "layout_mapping_status",
        "target_snowflake_layer",
        "snowflake_design_decision",
        "data_team_action",
        "analyst_question",
        "source_artifacts",
        "model_version",
    ]


def _analysis_requirement_matrix_columns() -> list[str]:
    return [
        "requirement_rank",
        "client_id",
        "period_month",
        "domain_id",
        "domain_name",
        "source_section_id",
        "product",
        "display_name",
        "analysis_family",
        "business_question",
        "consulting_question",
        "source_path",
        "script_count",
        "runnable_script_count",
        "representative_scripts",
        "section_required_input_families",
        "domain_required_input_families",
        "required_input_families",
        "minimum_required_fields",
        "optional_enrichment_fields",
        "source_candidates",
        "contract_status_by_input",
        "current_layout_readiness",
        "layout_blockers",
        "current_engine_outputs",
        "missing_engine_outputs",
        "generated_output_files",
        "generated_target_tables",
        "evidence_status",
        "supported_opportunity_types",
        "model_rule_ids",
        "consulting_use",
        "analyst_next_step",
        "data_team_question",
        "csm_review_question",
        "snowflake_design_action",
        "source_artifacts",
        "model_version",
    ]


def _analysis_layout_coverage_matrix_columns() -> list[str]:
    return [
        "coverage_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "domain_id",
        "domain_name",
        "display_name",
        "input_family_hint",
        "field_key",
        "canonical_field_hint",
        "example_field_references",
        "reference_count",
        "script_count",
        "example_scripts",
        "example_line_numbers",
        "current_run_readiness",
        "contract_status",
        "layout_mapping_status",
        "layout_contract_fields",
        "matched_source_columns",
        "missing_required_count",
        "coverage_status",
        "coverage_severity",
        "analyst_action",
        "data_team_action",
        "source_artifacts",
        "model_version",
    ]


def _analysis_feature_derivation_catalog_columns() -> list[str]:
    return [
        "derivation_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "domain_id",
        "domain_name",
        "display_name",
        "input_family_hint",
        "analysis_field_key",
        "example_field_references",
        "reference_count",
        "derived_output_lineage",
        "derived_artifacts",
        "derived_fields",
        "base_input_requirements",
        "contract_status",
        "current_run_readiness",
        "validation_status",
        "snowflake_expression_hint",
        "analyst_action",
        "data_team_action",
        "source_artifacts",
        "model_version",
    ]


def _analysis_data_team_backlog_columns() -> list[str]:
    return [
        "backlog_rank",
        "client_id",
        "period_month",
        "input_family",
        "field_key",
        "coverage_status",
        "priority_band",
        "reference_count",
        "affected_section_count",
        "affected_sections",
        "affected_domains",
        "example_scripts",
        "example_field_references",
        "current_run_readiness",
        "layout_mapping_status",
        "contract_status",
        "data_team_action",
        "analyst_action",
        "snowflake_design_action",
        "source_artifacts",
        "model_version",
    ]


def _analysis_metric_validation_queue_columns() -> list[str]:
    return [
        "validation_rank",
        "client_id",
        "period_month",
        "input_family",
        "field_key",
        "coverage_status",
        "validation_type",
        "priority_band",
        "reference_count",
        "affected_section_count",
        "affected_sections",
        "affected_domains",
        "derived_lineage",
        "candidate_contract_fields",
        "example_scripts",
        "analyst_action",
        "data_team_action",
        "validation_decision",
        "source_artifacts",
        "model_version",
    ]


def _analysis_visual_output_map_columns() -> list[str]:
    return [
        "visual_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "domain_id",
        "domain_name",
        "display_name",
        "analysis_family",
        "business_question",
        "consulting_question",
        "output_file",
        "target_table",
        "visual_family",
        "visual_type",
        "visual_mode",
        "visual_title",
        "chart_readiness_status",
        "evidence_status",
        "section_review_status",
        "field_reference_count",
        "blocker_field_count",
        "review_field_count",
        "source_scripts",
        "source_fields_to_validate",
        "csm_use",
        "analyst_action",
        "data_team_action",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _analysis_chart_spec_catalog_columns() -> list[str]:
    return [
        "spec_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "domain_name",
        "display_name",
        "output_file",
        "target_table",
        "visual_family",
        "visual_type",
        "visual_mode",
        "chart_title",
        "chart_type",
        "data_artifact",
        "x_field",
        "y_field",
        "series_field",
        "label_field",
        "value_field",
        "color_field",
        "filter_hint",
        "sort_hint",
        "top_n",
        "available_columns",
        "required_columns_present",
        "missing_required_columns",
        "chart_readiness_status",
        "render_owner",
        "csm_use",
        "analyst_action",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _analysis_chart_data_snapshot_columns() -> list[str]:
    return [
        "snapshot_rank",
        "client_id",
        "period_month",
        "spec_rank",
        "source_section_id",
        "domain_name",
        "display_name",
        "chart_title",
        "chart_type",
        "data_artifact",
        "target_table",
        "x_field",
        "y_field",
        "series_field",
        "label_field",
        "value_field",
        "color_field",
        "sort_hint",
        "top_n",
        "source_row_count",
        "plotted_row_count",
        "x_cardinality",
        "series_cardinality",
        "numeric_total",
        "numeric_avg",
        "numeric_min",
        "numeric_max",
        "top_label",
        "top_value",
        "top_series",
        "top_data_points_json",
        "sample_records_json",
        "data_status",
        "chart_readiness_status",
        "render_owner",
        "insight_callout",
        "csm_use",
        "analyst_action",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _intelligence_metric_catalog_columns() -> list[str]:
    return [
        "metric_rank",
        "client_id",
        "period_month",
        "metric_id",
        "metric_name",
        "metric_family",
        "business_definition",
        "metric_grain",
        "source_artifact",
        "target_table",
        "source_field",
        "field_role",
        "aggregation_method",
        "data_type",
        "chart_usage_count",
        "section_usage_count",
        "used_by_sections",
        "used_by_chart_types",
        "used_by_outputs",
        "model_rule_ids",
        "validation_status",
        "validation_owner",
        "validation_queue_refs",
        "sample_value",
        "sample_period",
        "numeric_total",
        "numeric_avg",
        "numeric_min",
        "numeric_max",
        "source_row_count_max",
        "plotted_row_count_max",
        "chart_callout",
        "snowflake_expression_hint",
        "csm_interpretation",
        "data_team_action",
        "source_artifacts",
        "model_version",
    ]


def _analysis_section_evidence_review_columns() -> list[str]:
    return [
        "review_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "domain_id",
        "domain_name",
        "display_name",
        "analysis_family",
        "business_question",
        "consulting_question",
        "evidence_status",
        "section_review_status",
        "required_input_families",
        "current_layout_readiness",
        "layout_blockers",
        "generated_output_files",
        "generated_target_tables",
        "generated_row_count",
        "field_reference_count",
        "distinct_field_count",
        "mapped_field_count",
        "review_field_count",
        "blocker_field_count",
        "top_blocker_fields",
        "top_review_fields",
        "analysis_summary",
        "consulting_use",
        "analyst_next_step",
        "data_team_next_step",
        "csm_review_question",
        "source_artifacts",
        "model_version",
    ]


def _analysis_consulting_playbook_columns() -> list[str]:
    return [
        "playbook_rank",
        "client_id",
        "period_month",
        "domain_id",
        "domain_name",
        "source_section_id",
        "display_name",
        "analysis_family",
        "business_question",
        "consulting_question",
        "client_story_role",
        "meeting_moment",
        "primary_business_claim",
        "recommended_storyline",
        "primary_chart_title",
        "primary_chart_type",
        "primary_output_file",
        "primary_target_table",
        "output_readiness_status",
        "section_review_status",
        "evidence_status",
        "generated_output_files",
        "generated_target_tables",
        "generated_row_count",
        "field_reference_count",
        "mapped_field_count",
        "review_field_count",
        "blocker_field_count",
        "top_blocker_fields",
        "top_review_fields",
        "stakeholder_owner",
        "csm_talk_track",
        "analyst_validation_focus",
        "data_team_dependency",
        "marketing_activation_use",
        "snowflake_design_action",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _analysis_insight_brief_columns() -> list[str]:
    return [
        "brief_rank",
        "client_id",
        "period_month",
        "domain_id",
        "domain_name",
        "source_section_id",
        "display_name",
        "analysis_family",
        "brief_status",
        "section_review_status",
        "output_readiness_status",
        "business_question",
        "consulting_question",
        "what_is_analyzed",
        "headline_insight",
        "primary_evidence",
        "primary_chart_title",
        "primary_chart_type",
        "primary_output_file",
        "chart_data_status",
        "chart_count",
        "data_ready_chart_count",
        "metric_count",
        "primary_metric_ids",
        "primary_metrics",
        "metric_definitions",
        "sample_values",
        "data_caveat",
        "csm_talk_track",
        "recommended_client_question",
        "analyst_next_step",
        "data_team_next_step",
        "marketing_activation_use",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _client_meeting_deck_blueprint_columns() -> list[str]:
    return [
        "blueprint_rank",
        "client_id",
        "period_month",
        "meeting_phase",
        "slide_type",
        "slide_title",
        "primary_message",
        "decision_prompt",
        "audience_role",
        "owner_role",
        "source_section_id",
        "domain_name",
        "source_artifact",
        "visual_title",
        "chart_type",
        "chart_data_status",
        "primary_metric_ids",
        "metric_summary",
        "data_caveat",
        "talk_track",
        "follow_up_action",
        "activation_export",
        "blueprint_status",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _analysis_review_board_columns() -> list[str]:
    return [
        "review_rank",
        "client_id",
        "period_month",
        "source_section_id",
        "product",
        "display_name",
        "domain_name",
        "analysis_family",
        "intelligence_layers",
        "what_is_analyzed",
        "business_question",
        "consulting_question",
        "client_story_role",
        "section_review_status",
        "output_readiness_status",
        "input_readiness",
        "script_count",
        "runnable_script_count",
        "representative_scripts",
        "required_input_families",
        "primary_engine_outputs",
        "available_engine_outputs",
        "missing_engine_outputs",
        "generated_output_files",
        "snowflake_targets",
        "visual_count",
        "chart_count",
        "data_snapshot_count",
        "data_ready_chart_count",
        "chart_types",
        "chart_titles",
        "chart_readiness_statuses",
        "chart_data_statuses",
        "primary_output_file",
        "primary_chart_title",
        "primary_chart_type",
        "metric_count",
        "primary_metric_ids",
        "primary_metrics",
        "metric_validation_statuses",
        "headline_insight",
        "primary_evidence",
        "data_caveat",
        "recommended_client_question",
        "meeting_phase_refs",
        "meeting_slide_count",
        "first_meeting_rank",
        "meeting_titles",
        "csm_talk_track",
        "analyst_next_step",
        "data_team_next_step",
        "marketing_activation_use",
        "snowflake_design_action",
        "proof_artifacts",
        "source_artifacts",
        "review_status",
        "model_version",
    ]


def _user_interaction_map_columns() -> list[str]:
    return [
        "interaction_rank",
        "client_id",
        "period_month",
        "user_role",
        "workflow_lane",
        "interaction_stage",
        "primary_screen",
        "open_first",
        "artifact_name",
        "file_name",
        "artifact_format",
        "output_layer",
        "row_count",
        "target_table",
        "delivery_mode",
        "decision_supported",
        "analysis_or_data_question",
        "evidence_summary",
        "source_section_ids",
        "chart_or_visual_refs",
        "downstream_use",
        "owner_next_action",
        "client_use_status",
        "blocker_summary",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _production_readiness_backlog_columns() -> list[str]:
    return [
        "backlog_rank",
        "client_id",
        "period_month",
        "workstream",
        "priority_band",
        "readiness_area",
        "source_item_type",
        "source_item_id",
        "owner_role",
        "problem_statement",
        "business_impact",
        "required_action",
        "acceptance_criteria",
        "blocking_artifacts",
        "affected_sections",
        "affected_outputs",
        "snowflake_targets",
        "client_use_status",
        "proof_artifacts",
        "source_artifacts",
        "model_version",
    ]


def _empty_analysis_domain_map() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_domain_map_columns())


def _empty_analysis_input_dependency_map() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_input_dependency_map_columns())


def _empty_analysis_layout_coverage_matrix() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_layout_coverage_matrix_columns())


def _empty_analysis_feature_derivation_catalog() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_feature_derivation_catalog_columns())


def _empty_analysis_data_team_backlog() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_data_team_backlog_columns())


def _empty_analysis_metric_validation_queue() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_metric_validation_queue_columns())


def _empty_analysis_visual_output_map() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_visual_output_map_columns())


def _empty_analysis_chart_spec_catalog() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_chart_spec_catalog_columns())


def _empty_analysis_chart_data_snapshot() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_chart_data_snapshot_columns())


def _empty_intelligence_metric_catalog() -> pd.DataFrame:
    return pd.DataFrame(columns=_intelligence_metric_catalog_columns())


def _empty_analysis_section_evidence_review() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_section_evidence_review_columns())


def _empty_analysis_consulting_playbook() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_consulting_playbook_columns())


def _empty_analysis_insight_brief() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_insight_brief_columns())


def _empty_client_meeting_deck_blueprint() -> pd.DataFrame:
    return pd.DataFrame(columns=_client_meeting_deck_blueprint_columns())


def _empty_analysis_review_board() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_review_board_columns())


def _empty_user_interaction_map() -> pd.DataFrame:
    return pd.DataFrame(columns=_user_interaction_map_columns())


def _empty_production_readiness_backlog() -> pd.DataFrame:
    return pd.DataFrame(columns=_production_readiness_backlog_columns())


def _empty_analysis_requirement_matrix() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_requirement_matrix_columns())


def _consulting_insight_register_columns() -> list[str]:
    return [
        "insight_rank",
        "client_id",
        "period_month",
        "insight_id",
        "insight_type",
        "domain",
        "source_section_ids",
        "opportunity_type",
        "play_name",
        "finding",
        "metric_name",
        "metric_value",
        "metric_display",
        "affected_accounts",
        "expected_value",
        "priority_score",
        "confidence",
        "evidence_status",
        "evidence_artifacts",
        "source_rules",
        "recommended_action",
        "owner_role",
        "recommended_channel",
        "action_id",
        "measurement_id",
        "primary_metric",
        "consulting_question",
        "next_decision",
        "target_list_ref",
        "source_artifacts",
        "model_version",
    ]


def _empty_analysis_execution_map() -> pd.DataFrame:
    return pd.DataFrame(columns=_analysis_execution_map_columns())


def _unique_tokens(values: Iterable[Any]) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str) and "|" in value:
            candidates = value.split("|")
        else:
            candidates = [value]
        for candidate in candidates:
            cleaned = _trace_text(candidate)
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            tokens.append(cleaned)
    return tokens


def _unique_pipe_values(values: Iterable[Any]) -> list[str]:
    return _unique_tokens(values)


def _metric_catalog_append_unique(values: list[Any], value: Any) -> None:
    cleaned = _trace_text(value)
    if cleaned and cleaned not in {_trace_text(item) for item in values}:
        values.append(value)


def _metric_catalog_append_numeric(values: list[float], value: Any) -> None:
    try:
        if value is None or pd.isna(value):
            return
    except (TypeError, ValueError):
        pass
    try:
        values.append(float(value))
    except (TypeError, ValueError, OverflowError):
        return


def _metric_catalog_snapshots_by_spec(analysis_chart_data_snapshot: pd.DataFrame | None) -> dict[int, dict[str, Any]]:
    if analysis_chart_data_snapshot is None or analysis_chart_data_snapshot.empty or "spec_rank" not in analysis_chart_data_snapshot:
        return {}
    records: dict[int, dict[str, Any]] = {}
    for row in analysis_chart_data_snapshot.to_dict("records"):
        spec_rank = _safe_int_value(row.get("spec_rank"))
        if spec_rank and spec_rank not in records:
            records[spec_rank] = row
    return records


def _metric_catalog_id(source_artifact: str, source_field: str) -> str:
    artifact_key = _slug_token(Path(_trace_text(source_artifact)).stem or "artifact")
    field_key = _slug_token(_layout_field_key(source_field) or source_field or "metric")
    return f"{artifact_key}.{field_key}"


def _metric_catalog_name(source_field: str) -> str:
    text = _trace_text(source_field).replace("_", " ").replace("-", " ").strip()
    return re.sub(r"\s+", " ", text).title() if text else "Unnamed Metric"


def _metric_catalog_family(source_field: str, source_artifact: str, roles: list[str]) -> str:
    field_key = _layout_field_key(source_field)
    artifact_key = _layout_field_key(source_artifact)
    role_set = set(roles)
    if role_set and role_set <= {"dimension", "series", "label", "color"}:
        return "chart_dimension"
    if any(token in field_key for token in ("quality", "blocker", "validation", "readiness", "coverage", "warning")):
        return "data_quality"
    if any(token in field_key for token in ("campaign", "target", "action", "measurement", "outcome", "lift", "response")):
        return "activation_measurement"
    if any(token in field_key for token in ("pfi", "payroll", "external", "competitor", "merchant", "counterparty", "relationship")):
        return "relationship_signal"
    if any(token in field_key for token in ("score", "priority", "confidence", "rank", "risk")):
        return "score"
    if any(token in field_key for token in ("amount", "value", "balance", "revenue", "spend", "credit", "debit", "income", "fee")):
        return "money_value"
    if any(token in field_key for token in ("count", "accounts", "transactions", "txn", "swipes", "active", "rows")):
        return "volume_count"
    if any(token in field_key for token in ("rate", "pct", "percent", "share", "ratio")):
        return "rate"
    if any(token in field_key for token in ("status", "type", "category", "segment", "tier", "verdict", "group")):
        return "classification"
    if "scorecard" in artifact_key:
        return "score"
    return "engine_metric"


def _metric_catalog_business_definition(source_field: str, source_artifact: str, metric_family: str, roles: list[str]) -> str:
    field_key = _layout_field_key(source_field)
    artifact = _trace_text(source_artifact)
    if metric_family == "chart_dimension":
        return f"Chart grouping field used to slice or label analysis output rows from {artifact}."
    if "priority_score" in field_key:
        return "Engine priority score used to rank accounts, plays, or actions for follow-up."
    if "expected_value" in field_key or field_key.endswith("value"):
        return "Modeled economic value attached to a relationship opportunity, segment, or action."
    if "pfi_score" in field_key:
        return "Primary Financial Institution score summarizing internal relationship strength versus external pull."
    if "pfi_verdict" in field_key:
        return "Relationship diagnosis classifying whether the client appears primary, split, or competitor-primary."
    if "payroll" in field_key:
        return "Payroll signal showing direct-deposit or income-like relationship evidence."
    if "external_fi" in field_key or "competitor" in field_key:
        return "External institution signal used to detect leakage, competitive pressure, or split relationships."
    if "balance" in field_key:
        return "Deposit balance or liquidity proxy used for retention, value, and relationship depth analysis."
    if "spend" in field_key or "debit" in field_key:
        return "Card or debit activity signal used for engagement, interchange, and activation analysis."
    if "txn" in field_key or "transaction" in field_key:
        return "Transaction activity volume used to describe engagement, dormancy, or behavioral momentum."
    if "outcome" in field_key or "lift" in field_key or "response" in field_key:
        return "Measurement field used to evaluate campaign, action, or holdout performance."
    if metric_family == "data_quality":
        return "Governance metric used to decide whether the analysis is ready, blocked, or needs validation."
    return f"Metric field `{source_field}` generated by `{artifact}` and used by analysis outputs."


def _metric_catalog_grain(source_artifact: str, roles: list[str]) -> str:
    artifact = _trace_text(source_artifact).removesuffix(".csv")
    if artifact == "account_month_features":
        return "account_id + period_month"
    if artifact in {"account_intelligence_profile", "pfi_verdicts", "relationship_segments"}:
        return "account_id + period_month"
    if artifact in {"opportunities", "campaign_targets", "outcome_results"}:
        return "account_id + action/opportunity"
    if artifact in {"opportunity_portfolio", "action_plan", "measurement_plan", "outcome_summary"}:
        return "play/action"
    if artifact in {"counterparty_summary", "counterparty_signals"}:
        return "counterparty/account"
    if artifact.startswith("analysis_"):
        return "analysis section/output"
    if roles and set(roles) <= {"dimension", "series", "label", "color"}:
        return "chart dimension"
    return "generated artifact row"


def _metric_catalog_aggregation_method(source_field: str, roles: list[str]) -> str:
    field_key = _layout_field_key(source_field)
    if set(roles) and set(roles) <= {"dimension", "series", "label", "color"}:
        return "group_by_dimension"
    if field_key.endswith("_id") or field_key in {"account_id", "action_id", "measurement_id", "period_month"}:
        return "dimension_or_join_key"
    if any(token in field_key for token in ("rate", "pct", "percent", "share", "ratio", "score", "confidence")):
        return "average_or_weighted_average"
    if any(token in field_key for token in ("count", "accounts", "transactions", "txn", "swipes", "rows")):
        return "sum"
    if any(token in field_key for token in ("amount", "value", "balance", "revenue", "spend", "credit", "debit")):
        return "sum_and_average"
    if field_key.startswith("has_") or field_key.endswith("_detected") or field_key.endswith("_flag"):
        return "boolean_count_rate"
    return "inspect_chart_context"


def _metric_catalog_data_type(artifact_frames: dict[str, pd.DataFrame], source_artifact: str, source_field: str) -> str:
    frame = artifact_frames.get(source_artifact)
    if frame is None and source_artifact.endswith(".csv"):
        frame = artifact_frames.get(source_artifact.removesuffix(".csv"))
    if frame is None or source_field not in frame.columns:
        return "unknown"
    dtype = frame[source_field].dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype) or pd.api.types.is_numeric_dtype(dtype):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    return "string"


def _metric_catalog_validation_lookup(analysis_metric_validation_queue: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    if analysis_metric_validation_queue is None or analysis_metric_validation_queue.empty:
        return {}
    lookup: dict[str, list[dict[str, Any]]] = {}

    def add(key: str, row: dict[str, Any]) -> None:
        cleaned = _trace_text(key)
        if not cleaned:
            return
        lookup.setdefault(cleaned, []).append(row)

    for row in analysis_metric_validation_queue.to_dict("records"):
        add(_layout_field_key(row.get("field_key")), row)
        for token in [*(_split_tokens(row.get("candidate_contract_fields"))), *(_split_tokens(row.get("derived_lineage")))]:
            for key in _metric_catalog_token_lookup_keys(token):
                add(key, row)
    return lookup


def _metric_catalog_token_lookup_keys(token: Any) -> set[str]:
    text = _trace_text(token)
    if text.startswith("derived:"):
        text = text.removeprefix("derived:")
    if not text:
        return set()
    if ":" in text:
        artifact, field = text.rsplit(":", 1)
        return _metric_catalog_lookup_keys(artifact, field)
    return {_layout_field_key(text)}


def _metric_catalog_lookup_keys(source_artifact: str, source_field: str) -> set[str]:
    artifact = _trace_text(source_artifact)
    artifact_stem = Path(artifact).stem
    field = _trace_text(source_field)
    field_key = _layout_field_key(field)
    keys = {field_key, field}
    for artifact_key in {artifact, artifact_stem}:
        if artifact_key:
            keys.add(f"{artifact_key}:{field}")
            keys.add(f"{artifact_key}:{field_key}")
    return {key for key in keys if key}


def _metric_catalog_matches(
    validation_lookup: dict[str, list[dict[str, Any]]],
    source_artifact: str,
    source_field: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in _metric_catalog_lookup_keys(source_artifact, source_field):
        for row in validation_lookup.get(key, []):
            row_key = f"{_trace_text(row.get('validation_rank'))}:{_trace_text(row.get('field_key'))}"
            if row_key in seen:
                continue
            seen.add(row_key)
            matches.append(row)
    return matches


def _metric_catalog_rule_lookup(model_rulebook: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    if model_rulebook is None or model_rulebook.empty:
        return {}
    lookup: dict[str, list[dict[str, Any]]] = {}
    for row in model_rulebook.to_dict("records"):
        tokens = [*_split_tokens(row.get("outputs")), *_split_tokens(row.get("evidence_fields"))]
        for token in tokens:
            field = _metric_catalog_rule_field(token)
            key = _layout_field_key(field)
            if key:
                lookup.setdefault(key, []).append(row)
    return lookup


def _metric_catalog_rule_field(token: Any) -> str:
    text = _trace_text(token)
    if not text:
        return ""
    text = text.rsplit(":", 1)[-1]
    return re.split(r"[<>=!\s]+", text, maxsplit=1)[0].strip()


def _metric_catalog_rule_ids(rule_matches: list[dict[str, Any]]) -> list[str]:
    return _sorted_texts(row.get("rule_id") for row in rule_matches)


def _metric_catalog_validation_status(validation_matches: list[dict[str, Any]], data_statuses: list[Any], roles: list[str]) -> str:
    if validation_matches:
        return "validation_required"
    statuses = {_trace_text(status) for status in data_statuses if _trace_text(status)}
    if statuses and statuses != {"data_ready"}:
        return "data_issue_review"
    if set(roles) and set(roles) <= {"dimension", "series", "label", "color"}:
        return "dimension_reference"
    return "defined_by_engine"


def _metric_catalog_validation_owner(validation_status: str, metric_family: str, roles: list[str]) -> str:
    if validation_status == "validation_required":
        return "Analyst"
    if validation_status == "data_issue_review":
        return "Data team"
    if metric_family in {"score", "relationship_signal", "activation_measurement"}:
        return "Data science"
    if set(roles) and set(roles) <= {"dimension", "series", "label", "color"}:
        return "BI / Product UI"
    return "Data science"


def _metric_catalog_validation_refs(validation_matches: list[dict[str, Any]]) -> list[str]:
    return _sorted_texts(
        f"validation_rank={row.get('validation_rank')}:field={row.get('field_key')}:type={row.get('validation_type')}"
        for row in validation_matches
    )


def _metric_catalog_sample_value(record: dict[str, Any], roles: list[str]) -> str:
    role_set = set(roles)
    if role_set <= {"dimension", "label"}:
        value = _first_nonempty(record.get("top_labels", []))
    elif role_set <= {"series", "color"}:
        value = _first_nonempty(record.get("top_series", []))
    else:
        value = _first_nonempty(record.get("top_values", [])) or _first_nonempty(record.get("top_labels", []))
    return value


def _metric_catalog_numeric_summary(values: list[float], method: str) -> float | str:
    if not values:
        return ""
    if method == "sum":
        result = sum(values)
    elif method == "avg":
        result = sum(values) / len(values)
    elif method == "min":
        result = min(values)
    else:
        result = max(values)
    return round(float(result), 4)


def _metric_catalog_snowflake_expression_hint(source_field: str, source_artifact: str, roles: list[str]) -> str:
    field_ref = f'"{_trace_text(source_field).upper()}"'
    method = _metric_catalog_aggregation_method(source_field, roles)
    if method == "group_by_dimension":
        return f"SELECT {field_ref}, COUNT(*) FROM {{table}} GROUP BY {field_ref}"
    if method == "sum":
        return f"SUM(TRY_TO_DOUBLE({field_ref}))"
    if method == "sum_and_average":
        return f"SUM(TRY_TO_DOUBLE({field_ref})) and AVG(TRY_TO_DOUBLE({field_ref}))"
    if method == "average_or_weighted_average":
        return f"AVG(TRY_TO_DOUBLE({field_ref}))"
    if method == "boolean_count_rate":
        return f"COUNT_IF({field_ref}) / NULLIF(COUNT(*), 0)"
    if method == "dimension_or_join_key":
        return f"Use {field_ref} as a join/filter key from {_trace_text(source_artifact)}"
    return f"Review {_trace_text(source_artifact)}.{_trace_text(source_field)} in chart context"


def _metric_catalog_csm_interpretation(source_field: str, metric_family: str, roles: list[str]) -> str:
    field_key = _layout_field_key(source_field)
    if metric_family == "chart_dimension":
        return "Use this as the slice, segment, or label when explaining the chart."
    if "priority_score" in field_key:
        return "Higher values should be reviewed first because the engine sees stronger action potential."
    if "expected_value" in field_key:
        return "Use this as directional value sizing, not booked revenue."
    if "pfi" in field_key:
        return "Use this to explain relationship primacy and whether the client is winning or sharing the account."
    if "external" in field_key or "competitor" in field_key:
        return "Use this to discuss leakage, competitor pull, and consolidation opportunities."
    if "payroll" in field_key:
        return "Use this to identify primary-banking opportunity or payroll retention proof."
    if metric_family == "activation_measurement":
        return "Use this to connect the strategy to audience execution and measured outcomes."
    if metric_family == "data_quality":
        return "Use this internally to qualify whether the output is client-ready."
    return "Use this metric as supporting evidence for the section's chart or table."


def _metric_catalog_data_team_action(validation_status: str, source_artifact: str, source_field: str) -> str:
    if validation_status == "validation_required":
        return f"Validate `{source_field}` lineage in `{source_artifact}` before promoting it as a client-facing metric."
    if validation_status == "data_issue_review":
        return f"Review chart-data readiness for `{source_artifact}` and confirm `{source_field}` is populated."
    if validation_status == "dimension_reference":
        return f"Keep `{source_field}` available as a BI grouping/filter field in `{source_artifact}`."
    return f"Maintain `{source_field}` in `{source_artifact}` output contracts and Snowflake load tests."


def _insight_brief_metrics_by_section(metric_catalog: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    if metric_catalog is None or metric_catalog.empty or "used_by_sections" not in metric_catalog:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in metric_catalog.to_dict("records"):
        for section_id in _split_tokens(row.get("used_by_sections")):
            grouped.setdefault(section_id, []).append(row)
    return grouped


def _insight_brief_primary_snapshot(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {}
    def sort_key(row: dict[str, Any]) -> tuple[int, int, int]:
        status_rank = 0 if _trace_text(row.get("data_status")) == "data_ready" else 1
        plotted = _safe_int_value(row.get("plotted_row_count"))
        source_rows = _safe_int_value(row.get("source_row_count"))
        return (status_rank, -plotted, -source_rows)
    return sorted(snapshots, key=sort_key)[0]


def _insight_brief_primary_metrics(metrics: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
        family = _trace_text(row.get("metric_family"))
        role = _trace_text(row.get("field_role"))
        validation = _trace_text(row.get("validation_status"))
        measure_rank = 0 if family not in {"chart_dimension", "classification"} or any(
            part in {"measure", "value"} for part in _split_tokens(role)
        ) else 1
        validation_rank = {"defined_by_engine": 0, "validation_required": 1, "dimension_reference": 2}.get(validation, 3)
        usage = _safe_int_value(row.get("chart_usage_count"))
        return (measure_rank, validation_rank, -usage, _trace_text(row.get("metric_id")))
    return sorted(metrics, key=sort_key)[:limit]


def _insight_brief_status(
    blocker_count: int,
    review_count: int,
    validation_metric_count: int,
    ready_chart_count: int,
) -> str:
    if ready_chart_count <= 0:
        return "missing_chart_data"
    if blocker_count > 0:
        return "qualified_by_layout_blockers"
    if review_count > 0 or validation_metric_count > 0:
        return "qualified_by_validation"
    return "client_ready"


def _insight_brief_focus(evidence: dict[str, Any], requirement: dict[str, Any]) -> str:
    question = _trace_text(evidence.get("business_question")) or _trace_text(requirement.get("business_question"))
    outputs = _trace_text(evidence.get("generated_output_files")) or _trace_text(requirement.get("generated_outputs"))
    if question and outputs:
        return f"{question} Evidence is generated through {outputs}."
    if question:
        return question
    return _trace_text(evidence.get("analysis_summary")) or "Section-level transaction intelligence evidence."


def _insight_brief_headline(
    evidence: dict[str, Any],
    playbook: dict[str, Any],
    primary_snapshot: dict[str, Any],
) -> str:
    return (
        _trace_text(primary_snapshot.get("insight_callout"))
        or _trace_text(playbook.get("primary_business_claim"))
        or _trace_text(playbook.get("recommended_storyline"))
        or _trace_text(evidence.get("analysis_summary"))
    )


def _insight_brief_primary_evidence(
    evidence: dict[str, Any],
    primary_snapshot: dict[str, Any],
    ready_chart_count: int,
    chart_count: int,
) -> str:
    row_count = _safe_int_value(evidence.get("generated_row_count"))
    plotted = _safe_int_value(primary_snapshot.get("plotted_row_count"))
    source_rows = _safe_int_value(primary_snapshot.get("source_row_count"))
    parts = [
        f"{row_count} generated output row(s)" if row_count else "",
        f"{ready_chart_count}/{chart_count} chart snapshot(s) data-ready" if chart_count else "",
        f"primary chart plots {plotted} of {source_rows} source row(s)" if source_rows else "",
    ]
    return "; ".join(part for part in parts if part)


def _insight_brief_metric_names(metrics: list[dict[str, Any]]) -> str:
    return "|".join(
        f"{_trace_text(row.get('metric_name'))} ({_trace_text(row.get('source_artifact'))}:{_trace_text(row.get('source_field'))})"
        for row in metrics
        if _trace_text(row.get("metric_name"))
    )


def _insight_brief_metric_definitions(metrics: list[dict[str, Any]]) -> str:
    return "|".join(
        f"{_trace_text(row.get('metric_name'))}: {_trace_text(row.get('business_definition'))}"
        for row in metrics
        if _trace_text(row.get("metric_name")) and _trace_text(row.get("business_definition"))
    )


def _insight_brief_sample_values(metrics: list[dict[str, Any]]) -> str:
    return "|".join(
        f"{_trace_text(row.get('metric_name'))}={_trace_text(row.get('sample_value'))}"
        for row in metrics
        if _trace_text(row.get("metric_name")) and _trace_text(row.get("sample_value"))
    )


def _insight_brief_data_caveat(
    blocker_count: int,
    review_count: int,
    validation_metric_count: int,
    ready_chart_count: int,
    chart_count: int,
) -> str:
    if ready_chart_count <= 0:
        return "Hold this section until chart backing data is generated or mapped."
    if blocker_count > 0:
        return f"Qualify externally: {blocker_count} layout blocker field reference(s) remain open."
    if review_count > 0 or validation_metric_count > 0:
        return (
            f"Usable with caveats: {review_count} review field reference(s) and "
            f"{validation_metric_count} semantic metric validation item(s) need approval."
        )
    if chart_count and ready_chart_count == chart_count:
        return "Client-ready based on generated outputs and data-ready chart snapshots."
    return "Review any non-ready chart snapshots before using this section externally."


def _insight_brief_client_question(
    evidence: dict[str, Any],
    playbook: dict[str, Any],
    requirement: dict[str, Any],
) -> str:
    question = (
        _trace_text(evidence.get("csm_review_question"))
        or _trace_text(requirement.get("csm_question"))
        or _trace_text(playbook.get("consulting_question"))
        or _trace_text(evidence.get("consulting_question"))
    )
    if question:
        return question
    story_role = _trace_text(playbook.get("client_story_role"))
    if story_role == "economic_opportunity":
        return "Which opportunity should be sized, prioritized, and turned into an action plan first?"
    if story_role == "measurement_proof":
        return "Which campaign or play should be measured next against holdout or baseline behavior?"
    if story_role == "data_caveat":
        return "Which data definition or source layout needs client confirmation before this can be used externally?"
    return "What decision should this analysis support in the next client conversation?"


def _meeting_blueprint_records(df: pd.DataFrame | None, sort_columns: list[str], limit: int) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    available = [col for col in sort_columns if col in df.columns]
    source = df.sort_values(available, na_position="last") if available else df
    return source.head(limit).to_dict("records")


def _meeting_blueprint_quality_caveat(data_quality: dict[str, Any]) -> str:
    score = data_quality.get("quality_score")
    warnings = data_quality.get("warnings") or []
    confidence = _trace_text(data_quality.get("confidence")) or "unknown"
    if warnings:
        return f"Quality score {score}; confidence {confidence}; review {len(warnings)} warning(s)."
    return f"Quality score {score}; confidence {confidence}."


def _meeting_blueprint_status(chart_data_status: str, data_caveat: str, data_quality: dict[str, Any]) -> str:
    caveat = _trace_text(data_caveat).lower()
    chart_status = _trace_text(chart_data_status)
    warnings = data_quality.get("warnings") or []
    if chart_status and chart_status != "data_ready":
        return "chart_review_required"
    if "blocker" in caveat or "hold" in caveat:
        return "qualified_by_data_caveat"
    if "review" in caveat or "validation" in caveat or warnings:
        return "qualified_for_meeting"
    return "meeting_ready"


def _meeting_blueprint_analysis_phase(brief: dict[str, Any]) -> str:
    status = _trace_text(brief.get("brief_status"))
    domain = _trace_text(brief.get("domain_name"))
    if status == "qualified_by_layout_blockers":
        return "Analysis Caveats"
    if "Measurement" in domain or "Campaign" in domain:
        return "Measurement Proof"
    if "Competitive" in domain or "Primacy" in domain or "Retention" in domain:
        return "Relationship Intelligence"
    return "Analysis Proof"


def _meeting_blueprint_lineage_source(row: dict[str, Any]) -> tuple[str, str, str]:
    source_artifact = _trace_text(row.get("source_artifact"))
    section_id = _trace_text(row.get("source_section_id"))
    slide_type = _trace_text(row.get("slide_type"))
    if source_artifact == "analysis_insight_brief.csv" and section_id:
        return ("section_insight_brief", f"brief:{section_id}", section_id)
    if source_artifact == "action_plan.csv":
        action_id = _trace_text(row.get("activation_export")) or _slug_token(row.get("slide_title"))
        return ("action_play", f"action:{action_id}", _trace_text(row.get("slide_title")))
    if source_artifact == "executive_scorecard.csv":
        domain = _trace_text(row.get("domain_name")) or _slug_token(row.get("slide_title"))
        return ("engine_output", "artifact:executive_scorecard.csv", domain)
    if source_artifact == "strategy_roadmap.csv":
        return ("engine_output", "artifact:strategy_roadmap.csv", _trace_text(row.get("slide_title")))
    if source_artifact == "measurement_plan.csv":
        measurement_id = _trace_text(row.get("activation_export")) or _slug_token(row.get("slide_title"))
        return ("engine_output", f"artifact:measurement_plan.csv:{measurement_id}", _trace_text(row.get("slide_title")))
    if source_artifact == "stakeholder_export_manifest.csv":
        return ("engine_output", "artifact:stakeholder_export_manifest.csv", _trace_text(row.get("slide_title")))
    if slide_type == "executive_summary":
        return ("story", "story:consulting_story", _trace_text(row.get("slide_title")))
    return ("engine_output", f"artifact:{source_artifact or 'unknown'}", _trace_text(row.get("slide_title")))


def _first_nonempty(values: Iterable[Any]) -> str:
    for value in values:
        text = _trace_text(value)
        if text:
            return text
    return ""


def _derived_lineage_values(values: Iterable[Any]) -> list[str]:
    values = _unique_pipe_values(values)
    derived_values = [value for value in values if value.startswith("derived:")]
    return derived_values or values


def _derived_lineage_parts(value: Any) -> tuple[str, str]:
    text = _trace_text(value)
    if text.startswith("derived:"):
        text = text.removeprefix("derived:")
    if ":" in text:
        artifact, field = text.rsplit(":", 1)
        return _trace_text(artifact), _trace_text(field)
    if "." in text:
        artifact, field = text.rsplit(".", 1)
        return _trace_text(artifact), _trace_text(field)
    return "", _trace_text(text)


def _derived_lineage_artifacts(lineage: Iterable[Any]) -> list[str]:
    return _sorted_texts(_derived_lineage_parts(value)[0] for value in lineage)


def _derived_lineage_fields(lineage: Iterable[Any]) -> list[str]:
    return _sorted_texts(_derived_lineage_parts(value)[1] for value in lineage)


def _derivation_snowflake_expression_hint(lineage: Iterable[Any]) -> str:
    expressions: list[str] = []
    for artifact, field in (_derived_lineage_parts(value) for value in lineage):
        if not field:
            continue
        table = _artifact_target_table_hint(artifact)
        if table:
            expressions.append(f"{table}.{field}")
        else:
            expressions.append(field)
    return "|".join(_unique_tokens(expressions))


def _artifact_target_table_hint(artifact_name: str) -> str:
    artifact = _trace_text(artifact_name)
    if not artifact:
        return ""
    meta = (_load_output_contract().get("artifacts") or {}).get(artifact, {})
    return _trace_text(meta.get("target_table"))


def _derivation_analyst_action(row: dict[str, Any]) -> str:
    field_key = _trace_text(row.get("field_key"))
    section = _trace_text(row.get("source_section_id"))
    return (
        f"Validate that derived engine field(s) reproduce historical analysis field `{field_key}`"
        f" for section {section}; confirm definition before client-facing use."
    )


def _derivation_data_team_action(row: dict[str, Any], dependency: dict[str, Any], lineage: Iterable[Any]) -> str:
    family = _trace_text(row.get("input_family_hint"))
    fields = "|".join(_derived_lineage_fields(lineage))
    minimum_fields = _trace_text(dependency.get("minimum_fields"))
    return (
        f"Materialize or expose derived field(s) {fields} from {family or 'engine outputs'}; "
        f"confirm base input coverage: {minimum_fields or 'see input dependency map'}."
    )


def _data_team_backlog_priority(reference_count: int, section_count: int, coverage_status: str) -> str:
    if coverage_status == "client_layout_needed" or reference_count >= 100 or section_count >= 5:
        return "P0"
    if reference_count >= 25 or section_count >= 2:
        return "P1"
    if reference_count >= 5:
        return "P2"
    return "P3"


def _metric_validation_priority(reference_count: int, section_count: int, coverage_status: str) -> str:
    if coverage_status == "derived_engine_output_validate" and (reference_count >= 100 or section_count >= 5):
        return "P0"
    if reference_count >= 25 or section_count >= 2:
        return "P1"
    if reference_count >= 5:
        return "P2"
    return "P3"


def _metric_validation_type(coverage_status: str) -> str:
    return {
        "derived_engine_output_validate": "derived_output_lineage",
        "not_in_contract_validate_alias": "contract_alias_review",
        "rule_based_validate_with_client": "rule_or_taxonomy_review",
        "loaded_directly_unprofiled": "direct_load_lineage",
        "derived_from_account_data_validate": "derived_account_data",
        "needs_mapping_review": "mapping_review",
    }.get(coverage_status, "analyst_review")


def _metric_validation_decision(coverage_status: str) -> str:
    if coverage_status == "derived_engine_output_validate":
        return "Validate metric definition, source lineage, and whether the derived output can be used externally."
    if coverage_status == "not_in_contract_validate_alias":
        return "Confirm whether this is a valid client-file alias, then add it to the contract or mark it optional."
    if coverage_status == "rule_based_validate_with_client":
        return "Review the rule or taxonomy with the client before using this field in recommendations."
    if coverage_status == "loaded_directly_unprofiled":
        return "Back-map the direct-load field to the monthly source file and add profiling evidence."
    if coverage_status == "derived_from_account_data_validate":
        return "Decide whether the field should remain derived from account data or become a sourced mart field."
    if coverage_status == "needs_mapping_review":
        return "Decide whether this reference maps to an existing source field, a derived metric, or a deprecated script assumption."
    return "Review the field definition and decide whether it is source-backed, derived, optional, or deprecated."


def _data_team_backlog_snowflake_action(input_family: str, field_key: str, coverage_status: str) -> str:
    display_name = INPUT_FAMILY_DEFINITIONS.get(input_family, {}).get("display_name", input_family)
    if coverage_status == "client_layout_needed":
        return f"Create or attach the client-specific {display_name} layout contract before modeling {field_key}."
    if coverage_status == "input_family_needs_mapping":
        return f"Map {field_key} into the raw/stage {display_name} contract or define it as a derived mart field."
    if coverage_status == "contract_needed":
        return f"Add {field_key} to a versioned {display_name} contract and Snowflake staging target."
    if coverage_status == "missing_required":
        return f"Locate {field_key} in the client file drop and expose it through the {display_name} staging table."
    return f"Review whether {field_key} belongs in raw/stage {display_name}, a derived mart, or analyst-only metadata."


def _analysis_scripts_by_section(analysis_script_catalog: pd.DataFrame | None) -> dict[str, list[str]]:
    if analysis_script_catalog is None or analysis_script_catalog.empty or "source_section_id" not in analysis_script_catalog:
        return {}
    scripts: dict[str, list[str]] = {}
    for section_id, group in analysis_script_catalog.groupby("source_section_id", dropna=False):
        scripts[_trace_text(section_id)] = _sorted_texts(group.get("script_name", []))
    return scripts


def _analysis_fields_by_section(analysis_layout_coverage_matrix: pd.DataFrame | None) -> dict[str, dict[str, list[str]]]:
    if analysis_layout_coverage_matrix is None or analysis_layout_coverage_matrix.empty:
        return {}
    fields: dict[str, dict[str, list[str]]] = {}
    for section_id, group in analysis_layout_coverage_matrix.groupby("source_section_id", dropna=False):
        fields[_trace_text(section_id)] = {
            "blockers": _sorted_texts(
                group.loc[
                    group["coverage_severity"].astype(str).eq("blocker"),
                    "field_key",
                ]
                if "coverage_severity" in group and "field_key" in group
                else []
            ),
            "review": _sorted_texts(
                group.loc[
                    group["coverage_severity"].astype(str).eq("review"),
                    "field_key",
                ]
                if "coverage_severity" in group and "field_key" in group
                else []
            ),
        }
    return fields


def _playbook_primary_chart_spec(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    status_order = {
        "client_ready": 0,
        "validation_required": 1,
        "qualified_by_layout_blockers": 2,
        "partial_or_inventory": 3,
    }
    chart_order = {
        "rag_scorecard": 0,
        "portfolio_bar": 1,
        "lift_bar": 2,
        "ranked_bar": 3,
        "horizontal_bar": 4,
        "stacked_bar": 5,
        "line": 6,
        "target_table": 7,
        "detail_table": 8,
    }
    return sorted(
        records,
        key=lambda row: (
            status_order.get(_trace_text(row.get("chart_readiness_status")), 9),
            0 if _trace_bool(row.get("required_columns_present")) else 1,
            chart_order.get(_trace_text(row.get("chart_type")), 9),
            _safe_int_value(row.get("spec_rank"), default=9999),
        ),
    )[0]


def _chart_data_snapshot_for_spec(spec: dict[str, Any], frame: pd.DataFrame | None) -> dict[str, Any]:
    fields = _chart_snapshot_fields(spec)
    y_field = _trace_text(spec.get("y_field"))
    x_field = _trace_text(spec.get("x_field"))
    series_field = _trace_text(spec.get("series_field"))
    top_n = max(_safe_int_value(spec.get("top_n"), default=10), 1)

    if frame is None:
        return _empty_chart_snapshot_payload("missing_artifact", f"No generated data artifact found for {_trace_text(spec.get('data_artifact'))}.")
    if frame.empty:
        return _empty_chart_snapshot_payload("empty_artifact", "The generated artifact exists but has no rows.")

    missing_fields = [field for field in fields if field and field not in frame.columns]
    if missing_fields:
        payload = _empty_chart_snapshot_payload(
            "missing_required_columns",
            f"Missing chart field(s): {', '.join(missing_fields)}.",
        )
        payload["source_row_count"] = int(len(frame))
        return payload

    view = frame.copy()
    if y_field and y_field in view.columns:
        view["_snapshot_numeric"] = pd.to_numeric(view[y_field], errors="coerce")
        if view["_snapshot_numeric"].notna().any():
            view["_snapshot_abs"] = view["_snapshot_numeric"].abs()
            ascending = _trace_text(spec.get("sort_hint")).endswith("_asc")
            sort_column = "_snapshot_numeric" if ascending else "_snapshot_abs"
            view = view.sort_values(sort_column, ascending=ascending, na_position="last")
    elif x_field and x_field in view.columns:
        view = view.sort_values(x_field, ascending=True, na_position="last")

    plotted = view.head(top_n).copy()
    numeric = pd.to_numeric(frame[y_field], errors="coerce") if y_field and y_field in frame.columns else pd.Series(dtype=float)
    numeric = numeric.dropna()
    top_record = plotted.iloc[0].to_dict() if not plotted.empty else {}
    top_label = _chart_snapshot_top_label(top_record, x_field, spec)
    top_value = _chart_snapshot_top_value(top_record, y_field)
    top_series = _trace_text(top_record.get(series_field)) if series_field and series_field in frame.columns else ""
    point_fields = [field for field in fields if field in plotted.columns]

    return {
        "source_row_count": int(len(frame)),
        "plotted_row_count": int(len(plotted)),
        "x_cardinality": int(frame[x_field].nunique(dropna=True)) if x_field and x_field in frame.columns else 0,
        "series_cardinality": int(frame[series_field].nunique(dropna=True)) if series_field and series_field in frame.columns else 0,
        "numeric_total": float(numeric.sum()) if not numeric.empty else "",
        "numeric_avg": float(numeric.mean()) if not numeric.empty else "",
        "numeric_min": float(numeric.min()) if not numeric.empty else "",
        "numeric_max": float(numeric.max()) if not numeric.empty else "",
        "top_label": top_label,
        "top_value": top_value,
        "top_series": top_series,
        "top_data_points_json": _chart_snapshot_records_json(plotted, point_fields, limit=min(top_n, 12)),
        "sample_records_json": _chart_snapshot_records_json(frame, point_fields or list(frame.columns[:6]), limit=5),
        "data_status": "data_ready",
        "insight_callout": _chart_snapshot_callout(spec, len(frame), len(plotted), top_label, top_value, top_series, numeric),
    }


def _chart_snapshot_fields(spec: dict[str, Any]) -> list[str]:
    return _unique_tokens(
        [
            spec.get("x_field"),
            spec.get("y_field"),
            spec.get("series_field"),
            spec.get("label_field"),
            spec.get("value_field"),
            spec.get("color_field"),
        ]
    )


def _empty_chart_snapshot_payload(status: str, callout: str) -> dict[str, Any]:
    return {
        "source_row_count": 0,
        "plotted_row_count": 0,
        "x_cardinality": 0,
        "series_cardinality": 0,
        "numeric_total": "",
        "numeric_avg": "",
        "numeric_min": "",
        "numeric_max": "",
        "top_label": "",
        "top_value": "",
        "top_series": "",
        "top_data_points_json": "[]",
        "sample_records_json": "[]",
        "data_status": status,
        "insight_callout": callout,
    }


def _chart_snapshot_top_label(record: dict[str, Any], x_field: str, spec: dict[str, Any]) -> str:
    if x_field and x_field in record:
        return _trace_text(record.get(x_field))
    label_field = _trace_text(spec.get("label_field"))
    if label_field and label_field in record:
        return _trace_text(record.get(label_field))
    return ""


def _chart_snapshot_top_value(record: dict[str, Any], y_field: str) -> str:
    if not y_field or y_field not in record:
        return ""
    value = record.get(y_field)
    number = pd.to_numeric(pd.Series([value]), errors="coerce").dropna()
    if not number.empty:
        return _chart_snapshot_format_value(float(number.iloc[0]), y_field)
    return _trace_text(value)


def _chart_snapshot_format_value(value: float, field_name: str) -> str:
    if math.isnan(value) or math.isinf(value):
        return ""
    key = _layout_field_key(field_name)
    if "rate" in key or "pct" in key or "lift" in key:
        return f"{value * 100:.1f}%" if abs(value) <= 1.5 else f"{value:.1f}"
    if "amount" in key or "value" in key or "balance" in key:
        return f"${value:,.0f}"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _chart_snapshot_records_json(df: pd.DataFrame, fields: list[str], *, limit: int) -> str:
    if df is None or df.empty or not fields:
        return "[]"
    fields = [field for field in fields if field in df.columns]
    if not fields:
        return "[]"
    records = df[fields].head(limit).replace({np.nan: None}).to_dict("records")
    return json.dumps(records, default=_json_default, ensure_ascii=True)


def _chart_snapshot_callout(
    spec: dict[str, Any],
    source_rows: int,
    plotted_rows: int,
    top_label: str,
    top_value: str,
    top_series: str,
    numeric: pd.Series,
) -> str:
    chart_title = _trace_text(spec.get("chart_title")) or _trace_text(spec.get("source_section_id")) or "Chart"
    y_field = _trace_text(spec.get("y_field"))
    if top_label and top_value:
        suffix = f" in {top_series}" if top_series else ""
        return f"{chart_title}: {top_label}{suffix} leads on {y_field or 'value'} at {top_value} across {source_rows} source row(s)."
    if not numeric.empty:
        return f"{chart_title}: {plotted_rows} plotted row(s) from {source_rows} source row(s), total {y_field or 'value'} {_chart_snapshot_format_value(float(numeric.sum()), y_field)}."
    return f"{chart_title}: {plotted_rows} preview row(s) available from {source_rows} source row(s)."


def _playbook_primary_visual(records: list[dict[str, Any]], chart_spec: dict[str, Any]) -> dict[str, Any]:
    if not records:
        return {}
    output_file = _trace_text(chart_spec.get("output_file"))
    if output_file:
        for row in records:
            if _trace_text(row.get("output_file")) == output_file:
                return row
    status_order = {
        "client_ready": 0,
        "validation_required": 1,
        "qualified_by_layout_blockers": 2,
        "partial_or_inventory": 3,
    }
    return sorted(
        records,
        key=lambda row: (
            status_order.get(_trace_text(row.get("chart_readiness_status")), 9),
            _safe_int_value(row.get("visual_rank"), default=9999),
        ),
    )[0]


def _playbook_story_role(evidence: dict[str, Any], requirement: dict[str, Any], section_status: str) -> str:
    domain = _trace_text(evidence.get("domain_id") or requirement.get("domain_id"))
    family = _trace_text(evidence.get("analysis_family") or requirement.get("analysis_family"))
    if section_status == "data_mapping_blocked":
        return "data_caveat"
    if domain == "campaign_cohort_measurement" or "campaign" in family or "measurement" in family:
        return "measurement_proof"
    if domain in {"competitive_leakage", "primacy_payroll_relationship"}:
        return "relationship_diagnosis"
    if domain == "debit_reg_e_revenue" or "value" in family:
        return "economic_opportunity"
    if domain == "retention_lifecycle" or "retention" in family:
        return "risk_and_lifecycle"
    if domain == "executive_synthesis":
        return "executive_synthesis"
    if domain == "portfolio_foundation":
        return "portfolio_context"
    return "supporting_analysis"


def _playbook_meeting_moment(story_role: str, section_status: str) -> str:
    if section_status == "data_mapping_blocked":
        return "Use in appendix or data-readiness discussion before making external claims."
    return {
        "portfolio_context": "Open the client conversation with denominator, mix, and eligibility context.",
        "relationship_diagnosis": "Use after the opening context to explain primacy, leakage, and relationship pressure.",
        "economic_opportunity": "Use when prioritizing revenue, card, overdraft, or modeled value actions.",
        "risk_and_lifecycle": "Use when deciding save-list, reactivation, or lifecycle intervention priorities.",
        "measurement_proof": "Use when proving campaign design, baseline, response, holdout, or lift.",
        "executive_synthesis": "Use to close with priority, decision, owner, and next-step alignment.",
    }.get(story_role, "Use as supporting evidence when the client asks how the recommendation was derived.")


def _playbook_business_claim(
    evidence: dict[str, Any],
    requirement: dict[str, Any],
    story_role: str,
) -> str:
    display = _trace_text(evidence.get("display_name")) or _trace_text(evidence.get("source_section_id"))
    question = _trace_text(evidence.get("consulting_question") or requirement.get("consulting_question"))
    if question:
        return f"{display} is the evidence layer for: {question}"
    return f"{display} supports the {story_role.replace('_', ' ')} part of the client story."


def _playbook_storyline(
    evidence: dict[str, Any],
    requirement: dict[str, Any],
    story_role: str,
) -> str:
    use = _trace_text(evidence.get("consulting_use") or requirement.get("consulting_use"))
    outputs = _trace_text(evidence.get("generated_output_files"))
    if use and outputs:
        return f"Use {outputs} to {use[0].lower() + use[1:] if len(use) > 1 else use}."
    if outputs:
        return f"Use {outputs} as the proof surface for {story_role.replace('_', ' ')}."
    return _trace_text(evidence.get("analysis_summary")) or "Use this section as analysis inventory until outputs are available."


def _playbook_stakeholder_owner(
    section_status: str,
    chart_status: str,
    blocker_count: int,
    review_count: int,
) -> str:
    if blocker_count > 0 or section_status == "data_mapping_blocked":
        return "Data team + Analyst"
    if review_count > 0 or chart_status == "validation_required":
        return "Analyst"
    if section_status in {"sellable_now", "usable_with_qualification"}:
        return "CSM / Consultant"
    return "Analyst"


def _playbook_csm_talk_track(
    evidence: dict[str, Any],
    story_role: str,
    chart_title: str,
    output_file: str,
) -> str:
    display = _trace_text(evidence.get("display_name")) or _trace_text(evidence.get("source_section_id"))
    chart_ref = chart_title or output_file or "the mapped engine output"
    if _safe_int_value(evidence.get("blocker_field_count")) > 0:
        return f"Use {display} as directional context only; note the unresolved data mapping before client-facing claims."
    return f"Use {chart_ref} to explain how {display} supports the {story_role.replace('_', ' ')} recommendation."


def _playbook_analyst_focus(evidence: dict[str, Any], chart_status: str, review_count: int) -> str:
    if _safe_int_value(evidence.get("blocker_field_count")) > 0:
        fields = _trace_text(evidence.get("top_blocker_fields")) or "the blocker fields"
        return f"Resolve or qualify {fields} before marking this section client-ready."
    if review_count > 0 or chart_status == "validation_required":
        fields = _trace_text(evidence.get("top_review_fields")) or "the review fields and chart spec"
        return f"Validate {fields}, then confirm the output can be used externally."
    return "Confirm the chart/output agrees with the section summary and keep this as client-ready proof."


def _playbook_data_dependency(
    evidence: dict[str, Any],
    requirement: dict[str, Any],
    blocker_count: int,
) -> str:
    if blocker_count > 0:
        fields = _trace_text(evidence.get("top_blocker_fields")) or "unmapped fields"
        return f"Map or contract {fields}; { _trace_text(evidence.get('data_team_next_step')) }".strip()
    action = _trace_text(requirement.get("data_team_question")) or _trace_text(evidence.get("data_team_next_step"))
    return action or "No immediate data-team dependency beyond normal monthly load validation."


def _playbook_marketing_use(evidence: dict[str, Any], output_file: str, story_role: str) -> str:
    outputs = _trace_text(evidence.get("generated_output_files")) + "|" + output_file
    if any(token in outputs for token in ["campaign_targets", "marketing_activation_export"]):
        return "Use to shape target audience, holdout, offer/channel logic, or activation export."
    if story_role in {"relationship_diagnosis", "economic_opportunity", "risk_and_lifecycle"}:
        return "Use to choose campaign theme, banker follow-up lane, or segment-specific next action."
    if story_role == "measurement_proof":
        return "Use to explain baseline, response, lift, or persistence measurement."
    return "Use as supporting context, not as a direct activation list."


def _visual_surface_for_output(output_file: str) -> tuple[str, str, str]:
    key = _layout_field_key(str(output_file).removesuffix(".csv").removesuffix(".json"))
    if key in {"executive_scorecard"}:
        return "Executive story", "rag_scorecard", "scorecard"
    if key in {"strategy_roadmap"}:
        return "Executive story", "roadmap_timeline", "timeline"
    if key in {"consulting_story", "insights", "consulting_insight_register"}:
        return "Consulting story", "story_cards", "story"
    if key in {"opportunity_portfolio"}:
        return "Opportunity strategy", "portfolio_bar_chart", "chart"
    if key in {"opportunities"}:
        return "Opportunity strategy", "ranked_opportunity_table", "table"
    if key in {"campaign_targets", "marketing_activation_export", "banker_call_list", "csm_review_queue"}:
        return "Activation", "target_list", "table"
    if key in {"measurement_plan", "measurement_baseline", "outcome_results", "outcome_summary"}:
        return "Measurement", "lift_or_baseline_view", "chart"
    if key in {"pfi_verdicts"}:
        return "Primacy", "pfi_distribution", "chart"
    if key in {"relationship_segments", "segment_summary"}:
        return "Segmentation", "segment_distribution", "chart"
    if key in {"counterparty_signals", "counterparty_summary"}:
        return "Counterparty intelligence", "counterparty_rank_or_network", "chart"
    if key in {"account_month_features", "account_intelligence_profile"}:
        return "Account intelligence", "account_profile_or_feature_view", "table"
    if key in {"model_rulebook", "account_scoring_trace"}:
        return "Model governance", "rule_or_scoring_trace", "table"
    if key.startswith("analysis_"):
        return "Analysis governance", "analysis_evidence_table", "table"
    if key in {"data_quality", "layout_gap_report", "engine_readiness_assessment"}:
        return "Readiness", "readiness_or_quality_table", "table"
    return "Analysis inventory", "artifact_table", "table"


def _visual_title_for_output(section_name: str, output_file: str) -> str:
    _, visual_type, _ = _visual_surface_for_output(output_file)
    label = visual_type.replace("_", " ").title()
    artifact = str(output_file).replace("_", " ").replace(".csv", "").replace(".json", "").title()
    return f"{section_name}: {label} from {artifact}"


def _visual_readiness_status(
    section_review_status: str,
    evidence_status: str,
    blocker_count: int,
    review_count: int,
) -> str:
    if blocker_count > 0 or section_review_status == "data_mapping_blocked":
        return "qualified_by_layout_blockers"
    if review_count > 0 or "validate" in section_review_status:
        return "validation_required"
    if evidence_status == "ready" or section_review_status == "sellable_now":
        return "client_ready"
    return "partial_or_inventory"


def _visual_proof_artifacts(output_file: str, section_fields: dict[str, list[str]]) -> str:
    artifacts = [
        output_file,
        "analysis_execution_map.csv",
        "analysis_section_evidence_review.csv",
    ]
    if section_fields.get("blockers"):
        artifacts.append("analysis_data_team_backlog.csv")
    if section_fields.get("review"):
        artifacts.append("analysis_metric_validation_queue.csv")
    return "|".join(_unique_pipe_values(artifacts))


def _chart_spec_for_visual(visual: dict[str, Any], columns: list[str]) -> dict[str, Any]:
    visual_type = _trace_text(visual.get("visual_type"))
    visual_mode = _trace_text(visual.get("visual_mode"))
    output_file = _trace_text(visual.get("output_file"))
    key = _layout_field_key(output_file.removesuffix(".csv").removesuffix(".json"))

    if visual_type == "rag_scorecard":
        return _chart_spec(
            "horizontal_bar",
            columns,
            x_candidates=["domain", "metric_name"],
            y_candidates=["score", "metric_value"],
            series_candidates=["rag_status"],
            label_candidates=["metric_display", "interpretation"],
            color_candidates=["rag_status"],
            sort_hint="score_desc",
            top_n=12,
        )
    if visual_type == "roadmap_timeline":
        return _chart_spec(
            "timeline_table",
            columns,
            x_candidates=["phase"],
            y_candidates=["initiative"],
            series_candidates=["owner_role"],
            label_candidates=["proof_metric", "source_signal"],
            color_candidates=["phase"],
            sort_hint="phase_order",
            top_n=12,
        )
    if visual_type == "portfolio_bar_chart":
        return _chart_spec(
            "bar",
            columns,
            x_candidates=["play_name", "opportunity_type"],
            y_candidates=["target_accounts", "expected_value", "avg_priority_score"],
            series_candidates=["confidence", "owner_role"],
            label_candidates=["next_step", "primary_metric"],
            color_candidates=["confidence"],
            sort_hint="target_accounts_desc",
            top_n=10,
        )
    if visual_type == "ranked_opportunity_table":
        return _chart_spec(
            "ranked_table",
            columns,
            x_candidates=["opportunity_type", "account_id"],
            y_candidates=["priority_score", "expected_value"],
            series_candidates=["pfi_verdict", "confidence"],
            label_candidates=["recommended_action", "reason_codes"],
            color_candidates=["confidence"],
            sort_hint="priority_score_desc",
            top_n=25,
        )
    if visual_type == "target_list":
        return _chart_spec(
            "target_table",
            columns,
            x_candidates=["account_id", "play_name"],
            y_candidates=["priority_score", "expected_value"],
            series_candidates=["measurement_group", "target_status"],
            label_candidates=["recommended_action", "reason_codes"],
            color_candidates=["target_status", "measurement_group"],
            sort_hint="priority_score_desc",
            top_n=50,
        )
    if visual_type == "lift_or_baseline_view":
        return _chart_spec(
            "lift_bar",
            columns,
            x_candidates=["play_name", "measurement_id", "action_id"],
            y_candidates=["lift_vs_holdout", "test_outcome_rate", "baseline_avg_priority_score", "target_accounts"],
            series_candidates=["measurement_status", "opportunity_type"],
            label_candidates=["interpretation", "primary_metric"],
            color_candidates=["measurement_status"],
            sort_hint="lift_desc",
            top_n=12,
        )
    if visual_type == "pfi_distribution":
        return _chart_spec(
            "donut",
            columns,
            x_candidates=["pfi_verdict", "confidence"],
            y_candidates=["account_count", "pfi_score", "score"],
            series_candidates=["confidence"],
            label_candidates=["reason_codes"],
            color_candidates=["pfi_verdict"],
            sort_hint="account_count_desc",
            top_n=8,
        )
    if visual_type == "segment_distribution":
        return _chart_spec(
            "stacked_bar",
            columns,
            x_candidates=["relationship_segment", "segment_group"],
            y_candidates=["account_count", "total_expected_value", "avg_readiness_score"],
            series_candidates=["risk_level", "lifecycle_stage"],
            label_candidates=["top_next_best_motion", "top_reason_codes"],
            color_candidates=["risk_level"],
            sort_hint="account_count_desc",
            top_n=12,
        )
    if visual_type == "counterparty_rank_or_network":
        return _chart_spec(
            "ranked_bar",
            columns,
            x_candidates=["counterparty_name", "counterparty_category"],
            y_candidates=["account_count", "total_amount", "transaction_count"],
            series_candidates=["counterparty_category", "top_relationship_signal"],
            label_candidates=["strategy_relevance", "signal_mix"],
            color_candidates=["counterparty_category"],
            sort_hint="account_count_desc",
            top_n=15,
        )
    if visual_type == "story_cards":
        return _chart_spec(
            "story_cards",
            columns,
            x_candidates=["story_step", "title", "insight_id", "domain"],
            y_candidates=["priority_score", "metric_value"],
            series_candidates=["insight_type", "owner_role"],
            label_candidates=["summary", "finding", "recommended_action"],
            color_candidates=["insight_type"],
            sort_hint="story_order",
            top_n=12,
        )
    if visual_type in {"account_profile_or_feature_view", "rule_or_scoring_trace", "analysis_evidence_table", "readiness_or_quality_table"}:
        return _chart_spec(
            "detail_table",
            columns,
            x_candidates=["account_id", "readiness_area", "source_section_id", "rule_id"],
            y_candidates=["priority_score", "score", "blocker_count", "validation_count"],
            series_candidates=["status", "risk_level", "readiness_status", "rule_family"],
            label_candidates=["recommended_action", "next_action", "decision_trace"],
            color_candidates=["status", "risk_level", "readiness_status"],
            sort_hint="rank_asc",
            top_n=50,
        )
    if visual_mode == "scorecard":
        chart_type = "scorecard"
    elif visual_mode == "timeline":
        chart_type = "timeline_table"
    elif visual_mode == "story":
        chart_type = "story_cards"
    elif key.endswith("summary"):
        chart_type = "summary_table"
    else:
        chart_type = "table"
    return _chart_spec(
        chart_type,
        columns,
        x_candidates=["display_name", "source_section_id", "domain_name", "account_id"],
        y_candidates=["row_count", "score", "priority_score", "account_count"],
        series_candidates=["status", "confidence", "owner_role"],
        label_candidates=["summary", "recommended_action", "next_step"],
        color_candidates=["status", "confidence"],
        sort_hint="rank_asc",
        top_n=25,
    )


def _chart_spec(
    chart_type: str,
    columns: list[str],
    *,
    x_candidates: list[str],
    y_candidates: list[str],
    series_candidates: list[str],
    label_candidates: list[str],
    color_candidates: list[str],
    sort_hint: str,
    top_n: int,
) -> dict[str, Any]:
    return {
        "chart_type": chart_type,
        "x_field": _first_existing_column(columns, x_candidates),
        "y_field": _first_existing_column(columns, y_candidates),
        "series_field": _first_existing_column(columns, series_candidates),
        "label_field": _first_existing_column(columns, label_candidates),
        "value_field": _first_existing_column(columns, y_candidates),
        "color_field": _first_existing_column(columns, color_candidates),
        "filter_hint": "",
        "sort_hint": sort_hint,
        "top_n": top_n,
    }


def _first_existing_column(columns: list[str], candidates: list[str]) -> str:
    column_set = set(columns)
    for candidate in candidates:
        if candidate in column_set:
            return candidate
    return ""


def _chart_render_owner(visual_mode: str) -> str:
    if visual_mode in {"chart", "scorecard", "timeline"}:
        return "BI / Product UI"
    if visual_mode == "story":
        return "Consultant / CSM"
    return "Analyst"


def _status_counts(execution_rows: list[dict[str, Any]], *, expected_count: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    observed = 0
    for row in execution_rows:
        status = _trace_text(row.get("evidence_status"))
        if not status:
            continue
        observed += 1
        counts[status] = counts.get(status, 0) + 1
    missing_inventory = max(expected_count - observed, 0)
    if missing_inventory:
        counts["inventory_only"] = counts.get("inventory_only", 0) + missing_inventory
    return counts


def _domain_input_readiness(
    required_inputs: list[str],
    status_counts: dict[str, int],
    data_quality: dict[str, Any],
) -> str:
    account_rows = _safe_int_value(data_quality.get("account_rows"))
    transaction_rows = _safe_int_value(data_quality.get("transaction_rows"))
    missing: list[str] = []
    if "accounts" in required_inputs and account_rows <= 0:
        missing.append("accounts")
    if "transactions" in required_inputs and transaction_rows <= 0:
        missing.append("transactions")
    if missing:
        return "missing_" + "_and_".join(missing)
    if status_counts.get("blocked_by_input", 0):
        return "section_blocked_by_input"
    layout_dependencies = [family for family in required_inputs if family not in {"accounts", "transactions"}]
    if layout_dependencies:
        return "v1_ready_layouts_unconfirmed"
    return "ready"


def _domain_evidence_status(status_counts: dict[str, int], generated_row_count: int) -> str:
    if status_counts.get("blocked_by_input", 0):
        return "blocked_by_input"
    if status_counts.get("ready", 0) and not any(
        status_counts.get(key, 0) for key in ("partial", "missing", "inventory_only")
    ):
        return "ready"
    if status_counts.get("ready", 0) or status_counts.get("partial", 0) or generated_row_count > 0:
        return "partial"
    if status_counts.get("inventory_only", 0):
        return "inventory_only"
    return "missing"


def _domain_build_now_text(evidence_status: str, outputs: list[str], files: list[str]) -> str:
    if evidence_status == "blocked_by_input":
        return "Inventory only until the required account and transaction inputs are mapped."
    if files:
        return f"Use generated run evidence from {', '.join(files[:6])}."
    if outputs:
        return f"Map section outputs into {', '.join(outputs[:6])}."
    return "Inventory scripts and decide which outputs become engine evidence."


def _domain_layout_wait_text(required_inputs: list[str]) -> str:
    dependencies = [family for family in required_inputs if family not in {"accounts", "transactions"}]
    if not dependencies:
        return "Confirm account and transaction layouts before final warehouse persistence."
    display_names = [
        INPUT_FAMILY_DEFINITIONS.get(family, {}).get("display_name", family)
        for family in dependencies
    ]
    return f"Client-specific layout confirmation needed for {', '.join(display_names)}."


def _domain_next_decision(
    domain_name: str,
    input_readiness: str,
    evidence_status: str,
    required_inputs: list[str],
) -> str:
    if input_readiness.startswith("missing_"):
        return f"Map the missing core inputs before interpreting {domain_name}."
    if evidence_status in {"ready", "partial"} and input_readiness == "v1_ready_layouts_unconfirmed":
        return f"Review V1 {domain_name} evidence, then confirm client layouts for {', '.join(required_inputs)}."
    if evidence_status == "ready":
        return f"Use {domain_name} in the consulting story and action prioritization."
    if evidence_status == "inventory_only":
        return f"Decide which {domain_name} scripts should become standardized insight outputs."
    return f"Review {domain_name} evidence gaps before using the domain externally."


def _family_file_count(file_assembly_plan: pd.DataFrame | None, family: str, *, selected_only: bool) -> int:
    if file_assembly_plan is None or file_assembly_plan.empty or "source_family" not in file_assembly_plan:
        return 0
    aliases = _source_family_aliases(family)
    if not aliases:
        return 0
    df = file_assembly_plan[file_assembly_plan["source_family"].astype(str).isin(aliases)]
    if selected_only and "assembly_role" in df:
        selected_roles = {"selected_account", "selected_transaction", "supporting"}
        df = df[df["assembly_role"].astype(str).isin(selected_roles)]
    return int(len(df))


def _family_layout_count(layout_gap_report: pd.DataFrame | None, family: str, status: str) -> int:
    if layout_gap_report is None or layout_gap_report.empty or "source_family" not in layout_gap_report:
        return 0
    aliases = _source_family_aliases(family)
    if not aliases:
        return 0
    df = layout_gap_report[layout_gap_report["source_family"].astype(str).isin(aliases)]
    if "mapping_status" not in df:
        return 0
    return int(df["mapping_status"].astype(str).eq(status).sum())


def _family_contract_needed_count(layout_gap_report: pd.DataFrame | None, family: str) -> int:
    if layout_gap_report is None or layout_gap_report.empty or "source_family" not in layout_gap_report:
        return 0
    aliases = _source_family_aliases(family)
    if not aliases:
        return 0
    df = layout_gap_report[layout_gap_report["source_family"].astype(str).isin(aliases)]
    if df.empty or "mapping_status" not in df or "source_path" not in df:
        return 0
    return int(
        df.loc[df["mapping_status"].astype(str).eq("contract_needed"), "source_path"]
        .dropna()
        .astype(str)
        .nunique()
    )


def _source_family_aliases(family: str) -> set[str]:
    return {
        "accounts": {"account", "odd"},
        "transactions": {"transaction"},
        "balances": {"balance", "balances", "odd", "account"},
        "product_relationship": {"relationship", "product", "odd", "account"},
        "counterparty_taxonomy": {"taxonomy", "merchant", "counterparty"},
        "campaign_history": {"campaign", "campaign_history", "mailer"},
        "suppressions": {"suppression", "suppressions"},
        "outcomes": {"outcome", "outcomes", "campaign"},
    }.get(family, set())


def _monthly_requirement_assembly_rows(
    file_assembly_plan: pd.DataFrame | None,
    family: str,
    draft_family_by_file: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    if file_assembly_plan is None or file_assembly_plan.empty:
        return []
    aliases = _source_family_aliases(family)
    draft_family_by_file = draft_family_by_file or {}
    rows: list[dict[str, Any]] = []
    for row in file_assembly_plan.to_dict("records"):
        file_name = _trace_text(row.get("file_name"))
        draft_family = draft_family_by_file.get(file_name, "")
        if family == "transactions" and draft_family and draft_family != "transactions":
            continue
        raw_family = _trace_text(row.get("source_family")).lower()
        lineage_family = _lineage_family_from_source_family(raw_family)
        target_family = _lineage_family_from_target_layer(row.get("target_snowflake_layer"))
        if family in {lineage_family, target_family} or raw_family in aliases:
            rows.append(row)
    return rows


def _monthly_requirement_draft_rows(layout_contract_draft_queue: pd.DataFrame | None, family: str) -> list[dict[str, Any]]:
    if layout_contract_draft_queue is None or layout_contract_draft_queue.empty:
        return []
    aliases = _source_family_aliases(family)
    rows: list[dict[str, Any]] = []
    for row in layout_contract_draft_queue.to_dict("records"):
        raw_family = _trace_text(row.get("source_family")).lower()
        target_family = _lineage_family_from_target_layer(row.get("target_snowflake_layer"))
        if target_family and target_family != family:
            continue
        contract_id = _trace_text(row.get("proposed_contract_id")).lower()
        if (
            family == target_family
            or raw_family in aliases
            or _contract_id_matches_family(contract_id, family)
        ):
            rows.append(row)
    return rows


def _monthly_requirement_layout_rows(
    layout_gap_report: pd.DataFrame | None,
    source_layout_profile: pd.DataFrame | None,
    family: str,
    draft_family_by_file: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    aliases = _source_family_aliases(family)
    draft_family_by_file = draft_family_by_file or {}
    rows: list[dict[str, Any]] = []
    if layout_gap_report is not None and not layout_gap_report.empty:
        for row in layout_gap_report.to_dict("records"):
            file_name = _trace_text(row.get("file_name"))
            draft_family = draft_family_by_file.get(file_name, "")
            if family == "transactions" and draft_family and draft_family != "transactions":
                continue
            raw_family = _trace_text(row.get("source_family")).lower()
            if raw_family in aliases or _lineage_family_from_source_family(raw_family) == family:
                rows.append(row)
    if source_layout_profile is not None and not source_layout_profile.empty:
        for row in source_layout_profile.to_dict("records"):
            file_name = _trace_text(row.get("file_name"))
            draft_family = draft_family_by_file.get(file_name, "")
            if family == "transactions" and draft_family and draft_family != "transactions":
                continue
            raw_family = _trace_text(row.get("source_family")).lower()
            proposed_family = _trace_text(row.get("proposed_input_family")).lower()
            target_family = _lineage_family_from_source_family(proposed_family)
            if raw_family in aliases or proposed_family == family or target_family == family:
                rows.append(row)
    return rows


def _contract_id_matches_family(contract_id: str, family: str) -> bool:
    if not contract_id:
        return False
    return {
        "accounts": contract_id.startswith("account."),
        "transactions": contract_id.startswith("txn."),
        "campaign_history": contract_id.startswith("campaign."),
        "suppressions": contract_id.startswith("suppression."),
        "outcomes": contract_id.startswith("outcome."),
        "balances": contract_id.startswith("balance."),
    }.get(family, False)


def _monthly_requirement_target_layer(
    family: str,
    selected_rows: list[dict[str, Any]],
    draft_rows: list[dict[str, Any]],
) -> str:
    selected_targets = _unique_tokens([_trace_text(row.get("target_snowflake_layer")) for row in selected_rows])
    if selected_targets:
        return selected_targets[0]
    draft_targets = _unique_tokens([_trace_text(row.get("target_snowflake_layer")) for row in draft_rows])
    if draft_targets:
        return draft_targets[0]
    return _lineage_target_table_for_input(family)


def _monthly_requirement_level(family: str, dependency: dict[str, Any]) -> str:
    contract_status = _trace_text(dependency.get("current_contract_status")).lower()
    dependent_count = _safe_int_value(dependency.get("dependent_section_count"))
    if family in {"accounts", "transactions"}:
        return "core_required"
    if "internal_rules" in contract_status:
        return "rules_required"
    if "derived" in contract_status:
        return "derived_or_future_extract"
    if dependent_count > 0:
        return "analysis_required"
    return "optional_supporting"


def _monthly_requirement_status(
    *,
    family: str,
    dependency: dict[str, Any],
    file_names: list[str],
    selected_file_names: list[str],
    missing_fields: list[str],
    contract_actions: list[str],
) -> str:
    contract_status = _trace_text(dependency.get("current_contract_status")).lower()
    run_readiness = _trace_text(dependency.get("current_run_readiness")).lower()
    blocking_actions = {"map_required_fields", "repair_or_replace_source_file"}
    review_actions = {"review_candidate_contract", "create_new_layout_contract", "update_existing_contract"}
    if family == "counterparty_taxonomy" and not file_names:
        return "rules_validation_required"
    if "loaded_directly_no_file_profile" in run_readiness:
        return "loaded_directly_no_profile"
    if "derived" in contract_status or "derived" in run_readiness:
        return "derive_now_or_accept_future_extract"
    if selected_file_names and not missing_fields and not (set(contract_actions) & blocking_actions):
        return "selected_for_load"
    if selected_file_names and missing_fields:
        return "selected_mapping_required"
    if file_names and set(contract_actions) & blocking_actions:
        return "mapping_required"
    if file_names and set(contract_actions) & review_actions:
        return "layout_review_required"
    if file_names:
        return "received_not_selected"
    if _safe_int_value(dependency.get("dependent_section_count")) > 0:
        return "missing_from_file_drop"
    return "not_expected_this_month"


def _monthly_requirement_data_team_action(
    *,
    family: str,
    status: str,
    target_layer: str,
    missing_fields: list[str],
    contract_actions: list[str],
    file_names: list[str],
) -> str:
    display = INPUT_FAMILY_DEFINITIONS.get(family, {}).get("display_name", family)
    if status == "selected_for_load":
        return f"Load {display} to {target_layer}; preserve file and contract lineage."
    if status == "selected_mapping_required":
        return f"Map required field(s) {', '.join(missing_fields)} before promoting {display} to {target_layer}."
    if status == "mapping_required":
        return f"Resolve mapping action(s) {', '.join(contract_actions)} for {display} before this family can support production analysis."
    if status == "layout_review_required":
        return f"Review and promote the candidate layout for {display}; received file(s): {', '.join(file_names)}."
    if status == "received_not_selected":
        return f"Confirm whether received {display} file(s) should be loaded, used as supporting lineage, or held out."
    if status == "loaded_directly_no_profile":
        return f"Attach the source file path for {display} in the next run so intake, hash, and layout lineage are complete."
    if status == "rules_validation_required":
        return "Validate counterparty taxonomy rules and any client-specific merchant overrides before external claims."
    if status == "derive_now_or_accept_future_extract":
        return f"Use derived engine evidence for {display} now; add a client extract contract if the client starts sending this file."
    if status == "missing_from_file_drop":
        return f"Request a {display} file or explicitly qualify analysis sections that depend on it."
    return f"No {display} file action is required for this monthly run."


def _monthly_requirement_analyst_question(family: str, status: str, dependency: dict[str, Any]) -> str:
    display = INPUT_FAMILY_DEFINITIONS.get(family, {}).get("display_name", family)
    dependent_sections = _trace_text(dependency.get("dependent_sections"))
    if status in {"missing_from_file_drop", "layout_review_required", "mapping_required", "selected_mapping_required"}:
        return f"Can we use {display} externally for these sections, or should they be caveated: {dependent_sections}?"
    if status == "rules_validation_required":
        return "Which counterparty categories, competitor names, and payroll processors need client-specific approval?"
    if status == "derive_now_or_accept_future_extract":
        return f"Is derived {display} evidence sufficient, or should the client send an explicit extract?"
    return f"Does {display} need any client-specific caveat for this run?"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _trace_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    return bool(value)


def _layout_matches_for_analysis_field(
    layout_gap_report: pd.DataFrame | None,
    *,
    family: str,
    field_key: str,
    canonical_hints: Iterable[Any],
    normalized_fields: Iterable[Any],
) -> list[dict[str, Any]]:
    if layout_gap_report is None or layout_gap_report.empty or "canonical_field" not in layout_gap_report:
        return []

    candidate_keys = {
        _layout_field_key(value)
        for value in [field_key, *list(canonical_hints), *list(normalized_fields)]
        if _trace_text(value)
    }
    if not candidate_keys:
        return []

    df = layout_gap_report
    aliases = _source_family_aliases(family)
    if aliases and "source_family" in df:
        df = df[df["source_family"].astype(str).isin(aliases)]
    if df.empty:
        return []

    matches: list[dict[str, Any]] = []
    for row in df.to_dict("records"):
        canonical_field = _layout_field_key(row.get("canonical_field"))
        if canonical_field in candidate_keys:
            matches.append(row)
    return matches


def _derived_output_matches_for_analysis_field(
    requirement: dict[str, Any],
    generated_artifacts: dict[str, Any] | None,
    *,
    field_key: str,
    canonical_hints: Iterable[Any],
    normalized_fields: Iterable[Any],
) -> list[dict[str, str]]:
    artifact_by_file = _generated_artifact_dataframes_by_file(generated_artifacts)
    if not artifact_by_file:
        return []

    output_files = _split_tokens(requirement.get("generated_output_files"))
    if not output_files:
        output_files = sorted(name for name in artifact_by_file if name.endswith(".csv"))
    output_files = _unique_tokens([*output_files, *DERIVED_FEATURE_SEARCH_OUTPUTS])

    candidate_keys = _analysis_output_candidate_keys(field_key, canonical_hints, normalized_fields)
    if not candidate_keys:
        return []

    matches: list[dict[str, str]] = []
    for output_file in output_files:
        artifact = artifact_by_file.get(output_file)
        if artifact is None:
            artifact = artifact_by_file.get(output_file.removesuffix(".csv"))
        if artifact is None or artifact.empty:
            continue
        for column in artifact.columns:
            column_key = _layout_field_key(column)
            if column_key in candidate_keys:
                matches.append(
                    {
                        "artifact_name": output_file,
                        "output_field": _trace_text(column),
                    }
                )
    return matches


def _generated_artifact_dataframes_by_file(
    generated_artifacts: dict[str, Any] | None,
) -> dict[str, pd.DataFrame]:
    if not generated_artifacts:
        return {}
    artifacts: dict[str, pd.DataFrame] = {}
    for artifact_name, value in generated_artifacts.items():
        if not isinstance(value, pd.DataFrame):
            continue
        key = _trace_text(artifact_name)
        if not key:
            continue
        artifacts[key] = value
        artifacts[f"{key}.csv"] = value
    return artifacts


def _analysis_output_candidate_keys(
    field_key: str,
    canonical_hints: Iterable[Any],
    normalized_fields: Iterable[Any],
) -> set[str]:
    candidate_keys = {
        _layout_field_key(value)
        for value in [field_key, *list(canonical_hints), *list(normalized_fields)]
        if _trace_text(value)
    }
    for key in list(candidate_keys):
        candidate_keys.update(_layout_field_key(alias) for alias in DERIVED_OUTPUT_FIELD_ALIASES.get(key, set()))
    return {key for key in candidate_keys if key}


def _derived_output_fields(output_matches: list[dict[str, str]]) -> list[str]:
    return _sorted_texts(
        f"{match.get('artifact_name')}:{match.get('output_field')}"
        for match in output_matches
        if _trace_text(match.get("artifact_name")) and _trace_text(match.get("output_field"))
    )


def _derived_output_lineage(output_matches: list[dict[str, str]]) -> list[str]:
    return _sorted_texts(
        f"derived:{match.get('artifact_name')}:{match.get('output_field')}"
        for match in output_matches
        if _trace_text(match.get("artifact_name")) and _trace_text(match.get("output_field"))
    )


def _analysis_layout_coverage_status(
    layout_matches: list[dict[str, Any]],
    output_matches: list[dict[str, str]],
    current_run_readiness: str,
    field_key: str,
) -> str:
    if not _trace_text(field_key) or _trace_text(field_key) == "unknown":
        return "needs_canonical_review"
    mapping_statuses = {_trace_text(row.get("mapping_status")) for row in layout_matches}
    if "matched" in mapping_statuses:
        return "mapped"
    if output_matches:
        return "derived_engine_output_validate"
    if "missing_required" in mapping_statuses:
        return "missing_required"
    if "contract_needed" in mapping_statuses:
        return "contract_needed"
    if current_run_readiness == "loaded_directly_no_file_profile":
        return "loaded_directly_unprofiled"
    if current_run_readiness == "partly_derived_from_account_data":
        return "derived_from_account_data_validate"
    if current_run_readiness == "mapped_from_file_drop":
        return "not_in_contract_validate_alias"
    if current_run_readiness == "internal_rules_active_validate_with_client":
        return "rule_based_validate_with_client"
    if current_run_readiness == "needs_field_mapping":
        return "input_family_needs_mapping"
    if current_run_readiness == "contract_needed":
        return "contract_needed"
    if current_run_readiness == "client_layout_needed":
        return "client_layout_needed"
    if current_run_readiness == "profiled_not_selected":
        return "profiled_not_selected"
    return "needs_mapping_review"


def _analysis_layout_coverage_severity(coverage_status: str) -> str:
    if coverage_status == "mapped":
        return "ready"
    if coverage_status in {
        "missing_required",
        "contract_needed",
        "input_family_needs_mapping",
        "client_layout_needed",
    }:
        return "blocker"
    return "review"


def _analysis_layout_analyst_action(
    coverage_status: str,
    section_id: str,
    family: str,
    field_key: str,
) -> str:
    label = f"{section_id} / {family} / {field_key}"
    if coverage_status == "mapped":
        return f"Use {label} as currently supported evidence, then sample output reasonableness."
    if coverage_status == "loaded_directly_unprofiled":
        return f"Treat {label} as available in this Python run but unproven against the client file layout."
    if coverage_status == "rule_based_validate_with_client":
        return f"Review {label} taxonomy/rule logic with the client before using it as a consulting claim."
    if coverage_status == "derived_from_account_data_validate":
        return f"Validate whether {label} should remain derived or become a sourced Snowflake field."
    if coverage_status == "derived_engine_output_validate":
        return f"Use {label} as engine-derived evidence only after validating the metric definition and output lineage."
    return f"Hold or qualify {label} until the layout mapping issue is resolved."


def _analysis_layout_data_team_action(coverage_status: str, family: str, field_key: str) -> str:
    display_name = INPUT_FAMILY_DEFINITIONS.get(family, {}).get("display_name", family)
    if coverage_status == "mapped":
        return f"Promote {field_key} from {display_name} into the canonical staging contract when stable."
    if coverage_status == "missing_required":
        return f"Find or map the required {field_key} column in the {display_name} source layout."
    if coverage_status == "contract_needed":
        return f"Create a layout contract for {display_name} before loading {field_key}."
    if coverage_status == "client_layout_needed":
        return f"Request or profile the client {display_name} layout before promising {field_key}."
    if coverage_status == "input_family_needs_mapping":
        return f"Complete required-field mapping for {display_name}; include {field_key} if present."
    if coverage_status == "not_in_contract_validate_alias":
        return f"Check whether {field_key} is an alias or optional field in the selected {display_name} file."
    if coverage_status == "loaded_directly_unprofiled":
        return f"Back-map direct-load field {field_key} to the actual monthly {display_name} file."
    if coverage_status == "rule_based_validate_with_client":
        return f"Version and document the rule source for {field_key}; no client file field may exist."
    if coverage_status == "derived_engine_output_validate":
        return f"Document {field_key} as a derived mart/output field and trace it back to the required {display_name} source inputs."
    return f"Review whether {field_key} belongs in the {display_name} contract."


def _layout_contract_fields(layout_matches: list[dict[str, Any]]) -> list[str]:
    return _sorted_texts(row.get("canonical_field") for row in layout_matches)


def _layout_matched_source_columns(layout_matches: list[dict[str, Any]]) -> list[str]:
    return _sorted_texts(
        row.get("suggested_source_column")
        for row in layout_matches
        if _trace_text(row.get("mapping_status")) == "matched"
    )


def _layout_field_key(value: Any) -> str:
    text = _trace_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _sorted_texts(values: Iterable[Any]) -> list[str]:
    return sorted({_trace_text(value) for value in values if _trace_text(value)})


def _profile_source_columns(profile: dict[str, Any]) -> list[tuple[str, int | Any]]:
    headers = [_trace_text(col) for col in profile.get("header_columns") or [] if _trace_text(col)]
    if headers:
        return [(header, index) for index, header in enumerate(headers)]
    column_count = _safe_int_value(profile.get("column_count"))
    return [(f"position_{index}", index) for index in range(column_count)]


def _layout_matches_by_source_column(layout_gap_report: pd.DataFrame | None) -> dict[tuple[str, str, int], list[dict[str, Any]]]:
    matches: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    if layout_gap_report is None or layout_gap_report.empty:
        return matches
    for row in layout_gap_report.to_dict("records"):
        if _trace_text(row.get("mapping_status")) != "matched":
            continue
        source_path = _trace_text(row.get("source_path"))
        source_column = _trace_text(row.get("suggested_source_column"))
        source_position = _safe_int_value(row.get("suggested_source_position"), default=-1)
        if not source_path or not source_column:
            continue
        matches.setdefault((source_path, source_column, source_position), []).append(row)
    return matches


def _missing_required_fields_by_path(layout_gap_report: pd.DataFrame | None) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    if layout_gap_report is None or layout_gap_report.empty:
        return missing
    rows = layout_gap_report[layout_gap_report["mapping_status"].astype(str).eq("missing_required")]
    for source_path, group in rows.groupby("source_path", dropna=False):
        missing[_trace_text(source_path)] = _sorted_texts(group["canonical_field"].tolist())
    return missing


def _canonical_mapping_status(
    *,
    mapped_canonical_fields: list[str],
    match_status: str,
    intake_decision: str,
) -> str:
    if mapped_canonical_fields:
        return "matched"
    if intake_decision == "map_required_fields":
        return "source_file_needs_required_mapping"
    if match_status == "candidate":
        return "candidate_contract_review"
    if intake_decision == "create_or_update_layout_contract" or match_status in {"unmatched", ""}:
        return "contract_needed"
    if intake_decision == "replace_file":
        return "file_repair_needed"
    return "unmapped_source_column"


def _source_column_role_guess(source_column: Any) -> str:
    key = _layout_field_key(source_column)
    if not key:
        return "unknown"
    if key in {"account", "acct", "account_id", "account_number", "primary_account_num"} or "acct" in key:
        return "account_id"
    if "transaction_date" in key or key in {"date", "post_date", "posted_date", "trans_date"}:
        return "transaction_date"
    if key in {"amount", "amt", "transaction_amount", "txn_amount"} or key.endswith("_amount"):
        return "amount"
    if "merchant" in key or "description" in key or "payee" in key or "counterparty" in key:
        return "merchant_or_description"
    if "transaction_type" in key or key in {"type", "txn_type", "tran_code", "channel"}:
        return "transaction_type"
    if "balance" in key or key in {"avg_bal", "avg_balance"}:
        return "balance"
    if "product" in key or key in {"prod_code", "product_code"}:
        return "product_code"
    if "status" in key or key in {"stat_code", "status_code"}:
        return "status_or_open_flag"
    if "debit" in key:
        return "has_debit"
    if "branch" in key:
        return "branch_id"
    if "campaign" in key or "mailer" in key or "wave" in key:
        return "campaign_history_field"
    if "suppress" in key or "do_not_contact" in key or "opt_out" in key:
        return "suppression_field"
    if "mcc" in key:
        return "mcc_code"
    return "unknown"


def _proposed_input_family(source_family: str, profile: dict[str, Any], source_column: Any) -> str:
    family_map = {
        "odd": "accounts",
        "account": "accounts",
        "transaction": "transactions",
        "balance": "balances",
        "campaign": "campaign_history",
        "suppression": "suppressions",
        "outcome": "outcomes",
    }
    if source_family in family_map:
        return family_map[source_family]
    text = " ".join([
        _trace_text(profile.get("file_name")),
        " ".join(_trace_text(col) for col in profile.get("header_columns") or []),
        _trace_text(source_column),
    ]).lower()
    if any(term in text for term in ("suppress", "do not contact", "opt out")):
        return "suppressions"
    if any(term in text for term in ("campaign", "mailer", "wave", "offer")):
        return "campaign_history"
    if any(term in text for term in ("tran", "transaction", "payment", "debit", "credit", "amount")):
        return "transactions"
    if any(term in text for term in ("balance", "account", "odd", "product")):
        return "accounts"
    return "unknown"


def _proposed_contract_id(source_family: str, profile: dict[str, Any]) -> str:
    current = _trace_text((profile.get("contract_match") or {}).get("contract_id"))
    status = _trace_text((profile.get("contract_match") or {}).get("status"))
    if current and status in {"matched", "candidate"}:
        return current
    input_family = _proposed_input_family(source_family, profile, "")
    family_slug = {
        "accounts": "account",
        "transactions": "txn",
        "campaign_history": "campaign",
        "suppressions": "suppression",
        "outcomes": "outcome",
    }.get(input_family, "client")
    file_slug = _slug_token(Path(_trace_text(profile.get("file_name"))).stem) or "layout"
    return f"{family_slug}.{file_slug}.v1"


def _source_layout_mapping_action(
    *,
    canonical_status: str,
    source_family: str,
    source_column: str,
    column_role_guess: str,
) -> str:
    label = source_column or "source column"
    if canonical_status == "matched":
        return f"Preserve mapped lineage for {label}; validate row counts before promotion."
    if canonical_status == "source_file_needs_required_mapping":
        return f"Map missing required fields before using {label} in the engine."
    if canonical_status == "candidate_contract_review":
        return f"Review whether {label} belongs in the candidate {source_family} contract."
    if canonical_status == "contract_needed":
        return f"Create or extend a layout contract; start by mapping {label} as {column_role_guess} if appropriate."
    if canonical_status == "file_repair_needed":
        return f"Repair or replace the source file before mapping {label}."
    return f"Decide whether {label} is ignored, optional enrichment, or maps to {column_role_guess}."


def _slug_token(value: Any) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", _trace_text(value).lower())).strip("_")


def _layout_contract_export_fallback_id(row: dict[str, Any]) -> str:
    family = _slug_token(row.get("source_family")) or "client_file"
    file_stem = _slug_token(Path(_trace_text(row.get("file_name"))).stem)
    return f"{family}.{file_stem or 'layout'}.v1"


def _layout_contract_export_file_name(
    proposed_contract_id: str,
    row: dict[str, Any],
    seen_stems: dict[str, int],
) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", _trace_text(proposed_contract_id)).strip("._-")
    if not stem:
        stem = _layout_contract_export_fallback_id(row)
    if not stem:
        stem = "layout_contract"
    seen_count = seen_stems.get(stem, 0) + 1
    seen_stems[stem] = seen_count
    if seen_count > 1:
        stem = f"{stem}_{seen_count}"
    return f"{stem}.yml"


def _write_layout_contract_draft_files(
    layout_contract_draft_queue: pd.DataFrame,
    layout_contract_export_manifest: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if (
        layout_contract_draft_queue is None
        or layout_contract_draft_queue.empty
        or layout_contract_export_manifest is None
        or layout_contract_export_manifest.empty
    ):
        return

    drafts_by_key: dict[tuple[str, str], str] = {}
    drafts_by_contract: dict[str, str] = {}
    for row in layout_contract_draft_queue.to_dict("records"):
        contract_id = _trace_text(row.get("proposed_contract_id")) or _layout_contract_export_fallback_id(row)
        file_name = _trace_text(row.get("file_name"))
        draft_yaml = _trace_text(row.get("draft_yaml"))
        if not draft_yaml:
            continue
        drafts_by_key[(contract_id, file_name)] = draft_yaml
        drafts_by_contract.setdefault(contract_id, draft_yaml)

    for row in layout_contract_export_manifest.to_dict("records"):
        contract_id = _trace_text(row.get("proposed_contract_id"))
        file_name = _trace_text(row.get("file_name"))
        yaml_file_name = _trace_text(row.get("yaml_file_name"))
        if not yaml_file_name:
            continue
        draft_yaml = drafts_by_key.get((contract_id, file_name)) or drafts_by_contract.get(contract_id, "")
        if not draft_yaml:
            continue
        (output_dir / yaml_file_name).write_text(draft_yaml.rstrip() + "\n", encoding="utf-8")


def _layout_gap_rows_by_path(layout_gap_report: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if layout_gap_report is None or layout_gap_report.empty or "source_path" not in layout_gap_report.columns:
        return grouped
    for row in layout_gap_report.to_dict("records"):
        source_path = _trace_text(row.get("source_path"))
        if source_path:
            grouped.setdefault(source_path, []).append(row)
    return grouped


def _lineage_family_from_source_family(value: Any) -> str:
    family = _trace_text(value).lower()
    if family in {"odd", "account", "accounts"}:
        return "accounts"
    if family in {"transaction", "transactions", "txn"}:
        return "transactions"
    if family in {"campaign", "campaign_history"}:
        return "campaign_history"
    if family in {"suppression", "suppressions"}:
        return "suppressions"
    if family in {"outcome", "outcomes"}:
        return "outcomes"
    if family in {"balance", "balances"}:
        return "balances"
    return family or "supporting_files"


def _lineage_draft_family_by_file(layout_contract_draft_queue: pd.DataFrame | None) -> dict[str, str]:
    families: dict[str, str] = {}
    if layout_contract_draft_queue is None or layout_contract_draft_queue.empty:
        return families
    for row in layout_contract_draft_queue.to_dict("records"):
        file_name = _trace_text(row.get("file_name"))
        family = _lineage_family_from_target_layer(row.get("target_snowflake_layer")) or _lineage_family_from_source_family(
            row.get("source_family")
        )
        if file_name and family:
            families[file_name] = family
    return families


def _lineage_draft_target_by_file(layout_contract_draft_queue: pd.DataFrame | None) -> dict[str, str]:
    targets: dict[str, str] = {}
    if layout_contract_draft_queue is None or layout_contract_draft_queue.empty:
        return targets
    for row in layout_contract_draft_queue.to_dict("records"):
        file_name = _trace_text(row.get("file_name"))
        target = _trace_text(row.get("target_snowflake_layer"))
        if file_name and target:
            targets[file_name] = target
    return targets


def _lineage_family_from_target_layer(value: Any) -> str:
    target = _trace_text(value).lower()
    if target.endswith("accounts"):
        return "accounts"
    if target.endswith("transactions"):
        return "transactions"
    if target.endswith("campaign_history"):
        return "campaign_history"
    if target.endswith("suppressions"):
        return "suppressions"
    if target.endswith("outcomes"):
        return "outcomes"
    if target.endswith("balances"):
        return "balances"
    if target.endswith("supporting_files"):
        return "supporting_files"
    return ""


def _lineage_target_table_for_input(input_family: str) -> str:
    return {
        "accounts": "raw.accounts",
        "transactions": "raw.transactions",
        "campaign_history": "raw.campaign_history",
        "suppressions": "raw.suppressions",
        "outcomes": "raw.outcomes",
        "balances": "raw.balances",
    }.get(_trace_text(input_family), "raw.supporting_files")


def _ordered_source_columns(group: pd.DataFrame) -> list[str]:
    if group is None or group.empty:
        return []
    rows = sorted(
        group.to_dict("records"),
        key=lambda row: (_safe_int_value(row.get("source_position"), default=999999), _trace_text(row.get("source_column"))),
    )
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        source_column = _trace_text(row.get("source_column"))
        if source_column and source_column not in seen:
            columns.append(source_column)
            seen.add(source_column)
    return columns


def _source_profile_matched_fields(group: pd.DataFrame) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()
    if group is None or group.empty or "matched_canonical_fields" not in group.columns:
        return fields
    for value in group["matched_canonical_fields"].tolist():
        for field in _split_tokens(value):
            if field not in seen:
                fields.append(field)
                seen.add(field)
    return sorted(fields)


def _contract_missing_required_fields(group: pd.DataFrame, gap_rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()
    if group is not None and not group.empty and "missing_required_fields" in group.columns:
        for value in group["missing_required_fields"].tolist():
            for field in _split_tokens(value):
                if field not in seen:
                    fields.append(field)
                    seen.add(field)
    for row in gap_rows:
        if _trace_text(row.get("mapping_status")) != "missing_required":
            continue
        field = _trace_text(row.get("canonical_field"))
        if field and field not in seen:
            fields.append(field)
            seen.add(field)
    return sorted(fields)


def _source_profile_unmapped_columns(group: pd.DataFrame) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    if group is None or group.empty:
        return columns
    for row in group.to_dict("records"):
        source_column = _trace_text(row.get("source_column"))
        if not source_column or source_column in seen:
            continue
        status = _trace_text(row.get("canonical_mapping_status"))
        if status != "matched":
            columns.append(source_column)
            seen.add(source_column)
    return columns


def _contract_draft_input_family(first: dict[str, Any], source_columns: list[str], matched_fields: list[str]) -> str:
    file_name = _trace_text(first.get("file_name")).lower()
    source_family = _trace_text(first.get("source_family")).lower()
    text = " ".join([file_name, source_family, *source_columns, *matched_fields]).lower()
    if source_family in {"odd", "account"}:
        return "accounts"
    if any(term in text for term in ("suppress", "suppression", "do_not_contact", "do not contact", "opt_out", "opt out")):
        return "suppressions"
    if any(term in text for term in ("campaign", "mailer", "offer", "wave")):
        return "campaign_history"
    if any(term in text for term in ("outcome", "conversion", "response", "funded", "opened")):
        return "outcomes"
    if any(
        field in matched_fields
        for field in ("balance", "avg_balance", "product_code", "stat_code", "status_code", "has_debit", "date_opened")
    ):
        return "accounts"
    if source_family == "transaction" or any(
        field in matched_fields for field in ("transaction_date", "amount", "transaction_type", "merchant_name")
    ):
        return "transactions"
    return "unknown"


def _contract_draft_action(
    *,
    match_status: str,
    intake_decision: str,
    missing_required: list[str],
    current_contract_id: str,
) -> str:
    if intake_decision == "replace_file":
        return "repair_or_replace_source_file"
    if match_status == "candidate":
        return "review_candidate_contract"
    if missing_required:
        return "map_required_fields"
    if match_status == "matched" and current_contract_id:
        return "promote_existing_contract"
    if current_contract_id:
        return "update_existing_contract"
    return "create_new_layout_contract"


def _contract_draft_priority(contract_action: str, missing_required: list[str]) -> str:
    if contract_action in {"repair_or_replace_source_file", "map_required_fields"}:
        return "P0"
    if contract_action in {"review_candidate_contract", "create_new_layout_contract", "update_existing_contract"}:
        return "P1"
    if missing_required:
        return "P0"
    return "P2"


def _contract_draft_missing_required(
    raw_missing_required: list[str],
    matched_fields: list[str],
    proposed_family: str,
) -> list[str]:
    required = set(_contract_required_fields(proposed_family))
    matched = set(matched_fields)
    if not required:
        return sorted(set(raw_missing_required))
    return sorted((set(raw_missing_required) & required) | (required - matched))


def _contract_draft_id(
    *,
    proposed_family: str,
    file_name: str,
    current_contract_id: str,
    match_status: str,
    contract_action: str,
) -> str:
    if current_contract_id and match_status == "matched" and contract_action == "promote_existing_contract":
        return current_contract_id
    family_slug = {
        "accounts": "account",
        "transactions": "txn",
        "campaign_history": "campaign",
        "suppressions": "suppression",
        "outcomes": "outcome",
    }.get(proposed_family, "client")
    stem = _slug_token(Path(file_name).stem) or "layout"
    return f"{family_slug}.{stem}.draft.v1"


def _layout_contract_alias_map(group: pd.DataFrame) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {}
    if group is None or group.empty:
        return aliases
    for row in group.to_dict("records"):
        source_column = _trace_text(row.get("source_column"))
        if not source_column:
            continue
        fields = _split_tokens(row.get("matched_canonical_fields"))
        if not fields:
            guess = _trace_text(row.get("column_role_guess"))
            if guess and guess != "unknown":
                fields = [guess]
        for field in fields:
            aliases.setdefault(field, [])
            if source_column not in aliases[field]:
                aliases[field].append(source_column)
    return {field: sorted(columns) for field, columns in sorted(aliases.items())}


def _layout_contract_draft_yaml(
    *,
    proposed_contract_id: str,
    proposed_family: str,
    first: dict[str, Any],
    matched_fields: list[str],
    source_columns: list[str],
    alias_map: dict[str, list[str]],
) -> str:
    canonical_fields: dict[str, dict[str, Any]] = {}
    required = set(_contract_required_fields(proposed_family))
    for field in sorted(set(matched_fields) | set(alias_map) | required):
        canonical_fields[field] = {
            "type": _contract_field_type(field),
            "required": field in required,
            "aliases": alias_map.get(field, []),
        }
    stub = {
        "contract_id": proposed_contract_id,
        "source_family": _contract_source_family(proposed_family),
        "display_name": Path(_trace_text(first.get("file_name"))).stem.replace("_", " ").title() or "Client file layout",
        "version": "1",
        "status": "draft",
        "match": {
            "filename_patterns": [Path(_trace_text(first.get("file_name"))).name],
            "required_headers_any": source_columns[:6],
        },
        "canonical_fields": canonical_fields,
    }
    return yaml.safe_dump(stub, sort_keys=False, allow_unicode=False).strip()


def _contract_required_fields(proposed_family: str) -> list[str]:
    return {
        "accounts": ["account_id"],
        "transactions": ["account_id", "transaction_date", "amount", "transaction_type"],
        "campaign_history": ["account_id"],
        "suppressions": ["account_id"],
        "outcomes": ["account_id"],
    }.get(proposed_family, [])


def _contract_source_family(proposed_family: str) -> str:
    return {
        "accounts": "account",
        "transactions": "transaction",
        "campaign_history": "campaign",
        "suppressions": "suppression",
        "outcomes": "outcome",
    }.get(proposed_family, "unknown")


def _contract_field_type(field: str) -> str:
    key = _layout_field_key(field)
    if "date" in key:
        return "date"
    if key in {"amount", "balance"} or key.endswith("_amount") or key.endswith("_balance"):
        return "number"
    if key.startswith("has_") or key.endswith("_flag"):
        return "boolean"
    return "string"


def _contract_draft_data_team_action(
    *,
    contract_action: str,
    proposed_contract_id: str,
    missing_required: list[str],
    proposed_family: str,
) -> str:
    if contract_action == "repair_or_replace_source_file":
        return "Repair the source file or request a replacement before this file enters the engine."
    if contract_action == "review_candidate_contract":
        return f"Confirm whether this file belongs to {proposed_family}; if yes, promote or edit {proposed_contract_id}."
    if contract_action == "map_required_fields":
        return f"Map required field(s) {', '.join(missing_required)} in {proposed_contract_id} before Snowflake promotion."
    if contract_action == "promote_existing_contract":
        return f"Reuse the existing contract and publish this layout lineage to Snowflake."
    if contract_action == "update_existing_contract":
        return f"Update {proposed_contract_id} with accepted aliases and required-field coverage."
    return f"Create {proposed_contract_id}, then rerun intake to verify field coverage."


def _contract_draft_analyst_question(contract_action: str, proposed_family: str, file_name: str) -> str:
    if contract_action == "promote_existing_contract":
        return f"Should {file_name} be included in this month's analysis package or kept as supporting lineage?"
    if proposed_family == "suppressions":
        return "Which campaign, banker, or marketing exports must honor this suppression file?"
    if proposed_family == "campaign_history":
        return "Which prior campaigns, offers, or waves should this file join to measurement?"
    if proposed_family == "outcomes":
        return "Which action IDs, accounts, and dates define a measurable outcome?"
    if proposed_family == "transactions":
        return "Does this extract represent raw transactions or a modified transaction-derived summary?"
    if proposed_family == "accounts":
        return "Is this the authoritative ODD/account file for eligibility and relationship features?"
    return "Is this file in scope for the engine, supporting lineage, or out of scope?"


def _contract_draft_target_layer(proposed_family: str, work_order: dict[str, Any]) -> str:
    load_target = _trace_text(work_order.get("load_target"))
    if load_target:
        return load_target
    return {
        "accounts": "raw.accounts",
        "transactions": "raw.transactions",
        "campaign_history": "raw.campaign_history",
        "suppressions": "raw.suppressions",
        "outcomes": "raw.outcomes",
    }.get(proposed_family, "raw.supporting_files")


def _field_usage_by_section(analysis_field_usage_catalog: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if (
        analysis_field_usage_catalog is None
        or analysis_field_usage_catalog.empty
        or "source_section_id" not in analysis_field_usage_catalog
    ):
        return {}
    grouped: dict[str, dict[str, Any]] = {}
    for section_id, rows in analysis_field_usage_catalog.groupby("source_section_id", dropna=False):
        section = _trace_text(section_id)
        if not section:
            continue
        field_values = rows.get("canonical_field_hint", pd.Series(dtype=str)).fillna("").astype(str)
        normalized_values = rows.get("normalized_field", pd.Series(dtype=str)).fillna("").astype(str)
        distinct_fields = {
            value
            for value in list(field_values) + list(normalized_values)
            if value and value.lower() != "nan"
        }
        grouped[section] = {
            "field_reference_count": len(rows),
            "distinct_field_count": len(distinct_fields),
        }
    return grouped


def _layout_coverage_by_section(analysis_layout_coverage_matrix: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if (
        analysis_layout_coverage_matrix is None
        or analysis_layout_coverage_matrix.empty
        or "source_section_id" not in analysis_layout_coverage_matrix
    ):
        return {}
    grouped: dict[str, dict[str, Any]] = {}
    for section_id, rows in analysis_layout_coverage_matrix.groupby("source_section_id", dropna=False):
        section = _trace_text(section_id)
        if not section:
            continue
        severity_counts = rows["coverage_severity"].fillna("").astype(str).value_counts().to_dict()
        blocker_fields = _top_coverage_fields(rows, "blocker")
        review_fields = _top_coverage_fields(rows, "review")
        grouped[section] = {
            "ready": int(severity_counts.get("ready", 0)),
            "review": int(severity_counts.get("review", 0)),
            "blocker": int(severity_counts.get("blocker", 0)),
            "top_blocker_fields": blocker_fields,
            "top_review_fields": review_fields,
        }
    return grouped


def _top_coverage_fields(rows: pd.DataFrame, severity: str, limit: int = 8) -> list[str]:
    if rows.empty or "coverage_severity" not in rows or "field_key" not in rows:
        return []
    filtered = rows[rows["coverage_severity"].fillna("").astype(str).eq(severity)]
    if filtered.empty:
        return []
    counts = (
        filtered.groupby("field_key", dropna=False)["reference_count"]
        .sum()
        .sort_values(ascending=False)
    )
    return [_trace_text(field) for field in counts.head(limit).index if _trace_text(field)]


def _section_review_status(
    evidence_status: str,
    mapped_field_count: int,
    review_field_count: int,
    blocker_field_count: int,
) -> str:
    if blocker_field_count:
        return "data_mapping_blocked"
    if evidence_status in {"missing", "blocked_by_input"}:
        return "data_mapping_blocked"
    if evidence_status == "inventory_only":
        return "inventory_only"
    if review_field_count:
        return "validate_before_external_use"
    if evidence_status == "ready" and mapped_field_count:
        return "sellable_now"
    if evidence_status in {"ready", "partial"}:
        return "usable_with_qualification"
    return "validate_before_external_use"


def _section_analysis_summary(
    execution: dict[str, Any],
    requirement: dict[str, Any],
    review_status: str,
) -> str:
    display_name = _trace_text(execution.get("display_name")) or _trace_text(execution.get("source_section_id"))
    domain_name = _trace_text(requirement.get("domain_name")) or "unmapped domain"
    outputs = _split_tokens(execution.get("generated_output_files"))
    if review_status == "sellable_now":
        qualifier = "has generated evidence and mapped field coverage"
    elif review_status == "validate_before_external_use":
        qualifier = "has generated evidence but needs field/layout validation before external claims"
    elif review_status == "data_mapping_blocked":
        qualifier = "is blocked or qualified by unresolved layout coverage"
    elif review_status == "inventory_only":
        qualifier = "is inventoried but not yet converted into runnable engine evidence"
    else:
        qualifier = "is usable only with explicit qualification"
    output_text = f" Outputs: {', '.join(outputs[:4])}." if outputs else ""
    return f"{display_name} supports {domain_name} and {qualifier}.{output_text}"


def _section_evidence_analyst_action(
    execution: dict[str, Any],
    review_status: str,
    blocker_count: int,
    review_count: int,
) -> str:
    next_step = _trace_text(execution.get("analyst_next_step"))
    if review_status == "sellable_now":
        return next_step or "Use this section in the consulting story and sample the output rows."
    if blocker_count:
        return f"Resolve or qualify {blocker_count} field-layout blocker(s) before using this section externally."
    if review_count:
        return f"Validate {review_count} review field(s), then decide whether this section can be client-facing."
    return next_step or "Review evidence and decide whether this section should become a standard engine output."


def _section_evidence_data_team_action(
    requirement: dict[str, Any],
    coverage: dict[str, Any],
    blocker_count: int,
    review_count: int,
) -> str:
    blockers = _trace_text(requirement.get("layout_blockers"))
    if blocker_count:
        top_fields = ", ".join(coverage.get("top_blocker_fields", [])[:5])
        suffix = f" Top fields: {top_fields}." if top_fields else ""
        return f"Map or contract unresolved layout fields for this section.{suffix}"
    if review_count:
        top_fields = ", ".join(coverage.get("top_review_fields", [])[:5])
        suffix = f" Review fields: {top_fields}." if top_fields else ""
        return f"Validate aliases, derived fields, and rule-based fields before Snowflake promotion.{suffix}"
    if blockers:
        return f"Confirm section-level layout blockers are cleared: {blockers}."
    return "No field-level blocker found; preserve source lineage and promote stable fields only after layout validation."


def _input_family_readiness(
    *,
    family: str,
    matched_file_count: int,
    selected_file_count: int,
    missing_required_count: int,
    contract_needed_count: int,
    data_quality: dict[str, Any],
) -> str:
    if missing_required_count:
        return "needs_field_mapping"
    if contract_needed_count:
        return "contract_needed"
    if selected_file_count:
        return "mapped_from_file_drop"
    if family == "accounts" and _safe_int_value(data_quality.get("account_rows")) > 0:
        return "loaded_directly_no_file_profile"
    if family == "transactions" and _safe_int_value(data_quality.get("transaction_rows")) > 0:
        return "loaded_directly_no_file_profile"
    if family == "balances" and _safe_int_value(data_quality.get("account_rows")) > 0:
        return "partly_derived_from_account_data"
    if family == "counterparty_taxonomy":
        return "internal_rules_active_validate_with_client"
    if matched_file_count:
        return "profiled_not_selected"
    return "client_layout_needed"


def _layout_mapping_status(readiness: str, missing_required_count: int, contract_needed_count: int) -> str:
    if missing_required_count:
        return "needs_required_field_mapping"
    if contract_needed_count:
        return "needs_layout_contract"
    if readiness in {"mapped_from_file_drop", "loaded_directly_no_file_profile", "partly_derived_from_account_data"}:
        return "usable_for_v1"
    if readiness == "internal_rules_active_validate_with_client":
        return "rules_active_client_validation_needed"
    return "not_yet_mapped"


def _input_dependency_next_step(family: str, readiness: str) -> str:
    display_name = INPUT_FAMILY_DEFINITIONS.get(family, {}).get("display_name", family)
    if readiness == "needs_field_mapping":
        return f"Map missing required fields for {display_name} before this family is warehouse-ready."
    if readiness == "contract_needed":
        return f"Create or select a layout contract for {display_name}."
    if readiness == "mapped_from_file_drop":
        return f"Validate row counts and join keys for {display_name}; then promote stable fields to Snowflake."
    if readiness == "loaded_directly_no_file_profile":
        return f"Current run loaded {display_name} directly; profile the actual client file layout before warehouse design."
    if readiness == "internal_rules_active_validate_with_client":
        return "Review merchant/counterparty rules with the client and preserve rule-version lineage."
    if readiness == "partly_derived_from_account_data":
        return "Confirm whether balances are embedded in ODD/account files or supplied as a separate extract."
    return f"Ask whether the monthly file drop includes {display_name}, then add a layout contract if it does."


def _domains_by_section(analysis_domain_map: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if analysis_domain_map is None or analysis_domain_map.empty or "source_section_ids" not in analysis_domain_map:
        return {}
    domains: dict[str, dict[str, Any]] = {}
    for row in analysis_domain_map.to_dict("records"):
        for section_id in _split_tokens(row.get("source_section_ids")):
            if section_id and section_id not in domains:
                domains[section_id] = row
    return domains


def _fields_by_family(
    input_families: list[str],
    input_dependency_by_family: dict[str, dict[str, Any]],
    field_name: str,
) -> list[str]:
    values: list[str] = []
    for family in input_families:
        row = input_dependency_by_family.get(family, {})
        value = _trace_text(row.get(field_name))
        if not value:
            fallback = INPUT_FAMILY_DEFINITIONS.get(family, {}).get(field_name, "")
            value = _trace_text(fallback)
        if value:
            values.append(f"{family}:{value}")
    return values


def _requirement_layout_blockers(
    input_families: list[str],
    input_dependency_by_family: dict[str, dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    review_statuses = {
        "needs_field_mapping",
        "contract_needed",
        "client_layout_needed",
        "profiled_not_selected",
        "internal_rules_active_validate_with_client",
    }
    for family in input_families:
        readiness = _trace_text(input_dependency_by_family.get(family, {}).get("current_run_readiness"))
        if readiness in review_statuses:
            blockers.append(f"{family}={readiness}")
    return blockers


def _requirement_data_team_question(
    input_families: list[str],
    dependency_rows: list[dict[str, Any]],
) -> str:
    unresolved = [
        _trace_text(row.get("display_name"))
        for row in dependency_rows
        if _trace_text(row.get("current_run_readiness")) in {
            "needs_field_mapping",
            "contract_needed",
            "client_layout_needed",
            "profiled_not_selected",
        }
    ]
    if unresolved:
        return f"Can the monthly file drop map {', '.join(unresolved)} with reliable join keys and required fields?"
    names = [
        INPUT_FAMILY_DEFINITIONS.get(family, {}).get("display_name", family)
        for family in input_families
    ]
    return f"Do the mapped {', '.join(names)} fields remain stable enough for repeatable Snowflake loads?"


def _requirement_csm_question(
    section: dict[str, Any],
    execution: dict[str, Any],
    domain: dict[str, Any],
) -> str:
    question = _trace_text(execution.get("consulting_question")) or _trace_text(domain.get("business_question"))
    if question:
        return question
    return f"What client decision should {_trace_text(section.get('display_name')) or 'this section'} support?"


def _requirement_snowflake_action(
    input_families: list[str],
    dependency_rows: list[dict[str, Any]],
) -> str:
    blockers = [
        row
        for row in dependency_rows
        if _trace_text(row.get("current_run_readiness")) in {
            "needs_field_mapping",
            "contract_needed",
            "client_layout_needed",
        }
    ]
    if blockers:
        names = [_trace_text(row.get("display_name")) for row in blockers]
        return f"Do not finalize durable facts for this section until {', '.join(names)} layouts are mapped."
    actions = _unique_tokens(
        _trace_text(row.get("snowflake_design_decision"))
        for row in dependency_rows
        if _trace_text(row.get("snowflake_design_decision"))
    )
    if actions:
        return " | ".join(actions[:3])
    return f"Stage raw files for {', '.join(input_families)} and promote only validated canonical fields."


def _empty_consulting_insight_register() -> pd.DataFrame:
    return pd.DataFrame(columns=_consulting_insight_register_columns())


def _empty_account_scoring_trace() -> pd.DataFrame:
    return pd.DataFrame(columns=_account_scoring_trace_columns())


def _records_by_key(df: pd.DataFrame | None, key: str) -> dict[str, dict[str, Any]]:
    if df is None or df.empty or key not in df.columns:
        return {}
    records: dict[str, dict[str, Any]] = {}
    for row in df.to_dict("records"):
        value = _trace_text(row.get(key))
        if value and value not in records:
            records[value] = row
    return records


def _records_grouped_by_key(df: pd.DataFrame | None, key: str) -> dict[str, list[dict[str, Any]]]:
    if df is None or df.empty or key not in df.columns:
        return {}
    records: dict[str, list[dict[str, Any]]] = {}
    for row in df.to_dict("records"):
        value = _trace_text(row.get(key))
        if value:
            records.setdefault(value, []).append(row)
    return records


def _analysis_board_metrics_by_section(
    intelligence_metric_catalog: pd.DataFrame | None,
) -> dict[str, list[dict[str, Any]]]:
    if intelligence_metric_catalog is None or intelligence_metric_catalog.empty:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in intelligence_metric_catalog.to_dict("records"):
        for section_id in _split_tokens(row.get("used_by_sections")):
            grouped.setdefault(section_id, []).append(row)
    return grouped


def _analysis_board_section_ids(*collections: Any) -> list[str]:
    ids: set[str] = set()
    for collection in collections:
        if isinstance(collection, dict):
            ids.update(_trace_text(key) for key in collection.keys() if _trace_text(key))
    return sorted(ids)


def _analysis_board_proof_artifacts(
    brief: dict[str, Any],
    playbook: dict[str, Any],
    visuals: list[dict[str, Any]],
    charts: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    meeting_rows: list[dict[str, Any]],
) -> str:
    return "|".join(_unique_tokens([
        brief.get("proof_artifacts"),
        playbook.get("proof_artifacts"),
        *[row.get("proof_artifacts") for row in visuals],
        *[row.get("proof_artifacts") for row in charts],
        *[row.get("proof_artifacts") for row in snapshots],
        *[row.get("proof_artifacts") for row in meeting_rows],
        "analysis_review_board.csv",
    ]))


def _analysis_board_source_artifacts(
    section: dict[str, Any],
    execution: dict[str, Any],
    requirement: dict[str, Any],
    brief: dict[str, Any],
    playbook: dict[str, Any],
    meeting_rows: list[dict[str, Any]],
) -> str:
    return "|".join(_unique_tokens([
        section.get("source_artifacts"),
        section.get("source_path"),
        execution.get("source_artifacts"),
        execution.get("source_path"),
        requirement.get("source_artifacts"),
        brief.get("source_artifacts"),
        playbook.get("source_artifacts"),
        *[row.get("source_artifacts") for row in meeting_rows],
    ]))


def _analysis_board_review_status(row: dict[str, Any]) -> str:
    joined = "|".join(
        _trace_text(row.get(key))
        for key in [
            "section_review_status",
            "output_readiness_status",
            "input_readiness",
            "chart_readiness_statuses",
            "chart_data_statuses",
            "metric_validation_statuses",
        ]
    ).lower()
    if any(token in joined for token in ("blocker", "missing_required", "client_layout_needed", "missing_artifact")):
        return "blocked_by_layout"
    if any(token in joined for token in ("validation_required", "validate", "review")):
        return "needs_metric_validation"
    if _trace_text(row.get("data_caveat")) or "qualified" in joined:
        return "qualified_with_caveat"
    if _safe_int_value(row.get("meeting_slide_count")) > 0 and _safe_int_value(row.get("chart_count")) > 0:
        return "client_story_ready"
    return "inventory_only"


def _evidence_by_section(analysis_execution_map: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if analysis_execution_map is None or analysis_execution_map.empty or "source_section_id" not in analysis_execution_map:
        return {}
    return {
        _trace_text(row.get("source_section_id")): row
        for row in analysis_execution_map.to_dict("records")
        if _trace_text(row.get("source_section_id"))
    }


def _evidence_summary_for_sections(
    source_sections: list[str],
    evidence_by_section: dict[str, dict[str, Any]],
) -> dict[str, str]:
    if not source_sections:
        return {"status": "engine_only", "artifacts": "", "question": ""}
    statuses: list[str] = []
    artifacts: list[str] = []
    questions: list[str] = []
    for section_id in source_sections:
        row = evidence_by_section.get(section_id, {})
        status = _trace_text(row.get("evidence_status"))
        if status:
            statuses.append(status)
        artifacts.extend(_split_tokens(row.get("generated_output_files")))
        question = _trace_text(row.get("consulting_question"))
        if question:
            questions.append(question)
    if not statuses:
        status = "unmapped"
    elif all(item == "ready" for item in statuses):
        status = "ready"
    elif "blocked_by_input" in statuses:
        status = "blocked_by_input"
    elif any(item in {"ready", "partial"} for item in statuses):
        status = "partial"
    else:
        status = statuses[0]
    return {
        "status": status,
        "artifacts": "|".join(dict.fromkeys(artifacts)),
        "question": questions[0] if questions else "",
    }


def _opportunity_type_from_insight(insight: dict[str, Any]) -> str:
    insight_id = _trace_text(insight.get("insight_id"))
    if insight_id.startswith("ti."):
        return insight_id.split(".", 1)[1]
    target_ref = _trace_text(insight.get("target_list_ref"))
    if "#" in target_ref:
        return target_ref.rsplit("#", 1)[1]
    return ""


def _insight_metric_display(metric_name: Any, value: Any) -> str:
    metric = _trace_text(metric_name)
    if value == "":
        return ""
    if metric in {"expected_value", "opportunity_amount"}:
        return _story_money(value)
    try:
        return f"{float(value):,.1f}"
    except (TypeError, ValueError):
        return _trace_text(value)


def _scorecard_register_rows(executive_scorecard: pd.DataFrame | None) -> list[dict[str, Any]]:
    if executive_scorecard is None or executive_scorecard.empty:
        return []
    rows: list[dict[str, Any]] = []
    for row in executive_scorecard.to_dict("records"):
        domain = _trace_text(row.get("domain"))
        rows.append(
            {
                "insight_id": f"scorecard.{_slug(domain)}",
                "domain": domain,
                "finding": _trace_text(row.get("interpretation")),
                "metric_name": _trace_text(row.get("metric_name")),
                "metric_value": row.get("metric_value", ""),
                "metric_display": _trace_text(row.get("metric_display")),
                "score": round(float(row.get("score", 0) or 0), 1),
                "rag_status": _trace_text(row.get("rag_status")),
                "recommended_action": _trace_text(row.get("recommended_focus")),
                "owner_role": _trace_text(row.get("owner_role")),
                "source_artifacts": _trace_text(row.get("source_artifacts")),
            }
        )
    return rows


def _story_arc_register_rows(consulting_story: dict[str, Any] | None) -> list[dict[str, str]]:
    story = consulting_story or {}
    rows: list[dict[str, str]] = []
    for index, row in enumerate(story.get("story_arc", []) or [], start=1):
        step = _trace_text(row.get("step")) or f"Story step {index}"
        rows.append(
            {
                "insight_id": f"story.{index}",
                "step": step,
                "summary": _trace_text(row.get("summary")),
                "artifact": _trace_text(row.get("artifact")),
                "question": _story_question_for_step(step),
                "next_step": _story_next_step_for_step(step),
            }
        )
    return rows


def _story_question_for_step(step: str) -> str:
    text = step.lower()
    if "readiness" in text:
        return "Can we trust this run enough to discuss it with the client?"
    if "signals" in text:
        return "What behavior explains the relationship opportunity?"
    if "diagnosis" in text:
        return "Which relationship states should shape the client conversation?"
    if "opportunity" in text:
        return "Which play deserves priority and why?"
    if "action" in text:
        return "Who owns activation and what file do they use?"
    if "measurement" in text:
        return "How will we prove whether the action worked?"
    return f"What decision does {step} support?"


def _story_next_step_for_step(step: str) -> str:
    text = step.lower()
    if "readiness" in text:
        return "Review quality score, warnings, and file coverage before client use."
    if "signals" in text:
        return "Use features and counterparties to explain the behavior pattern."
    if "diagnosis" in text:
        return "Inspect PFI, segments, and scoring trace for the highest-priority accounts."
    if "opportunity" in text:
        return "Select one to three plays for client recommendation."
    if "action" in text:
        return "Assign owner, channel, and export artifact."
    if "measurement" in text:
        return "Keep action_id and measurement_id through activation and next-month outcomes."
    return f"Review {step} evidence."


def _consulting_question_for_opportunity(opportunity_type: str) -> str:
    return {
        "payroll_conversion": "Which accounts can be converted into primary banking relationships?",
        "debit_activation": "Which active accounts can increase debit or wallet usage?",
        "deposit_retention": "Which balances need proactive retention outreach?",
        "competitor_winback": "Which relationships show enough competitor pull to justify consolidation outreach?",
        "dormant_reactivation": "Which low-activity relationships still have enough value to save?",
        "relationship_expansion": "Which thin relationships show external financial-life evidence worth deepening?",
        "attrition_prevention": "Which split or competitor-primary relationships need save-list intervention?",
    }.get(opportunity_type, "Which client decision does this opportunity support?")


def _next_decision_for_insight(*, opportunity_type: str, owner_role: str, evidence_status: str) -> str:
    if evidence_status in {"blocked_by_input", "missing"}:
        return "Validate missing evidence before client recommendation."
    playbook = OPPORTUNITY_PLAYBOOK.get(opportunity_type, {})
    owner = owner_role or playbook.get("owner_role", "CSM")
    next_step = playbook.get("next_step", "Review the ranked target list.")
    return f"{owner}: {next_step}"


def _scripts_by_section(analysis_script_catalog: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    if analysis_script_catalog is None or analysis_script_catalog.empty or "source_section_id" not in analysis_script_catalog:
        return {}
    sort_cols = [col for col in ["source_section_id", "script_order", "script_name"] if col in analysis_script_catalog.columns]
    df = analysis_script_catalog.sort_values(sort_cols, na_position="last") if sort_cols else analysis_script_catalog
    grouped: dict[str, list[dict[str, Any]]] = {}
    for section_id, group in df.groupby("source_section_id", dropna=False):
        grouped[_trace_text(section_id)] = group.to_dict("records")
    return grouped


def _provenance_by_section(analysis_provenance_map: pd.DataFrame | None) -> dict[str, list[str]]:
    if analysis_provenance_map is None or analysis_provenance_map.empty or "source_section_id" not in analysis_provenance_map:
        return {}
    grouped: dict[str, list[str]] = {}
    for row in analysis_provenance_map.to_dict("records"):
        section_id = _trace_text(row.get("source_section_id"))
        opportunity_type = _trace_text(row.get("opportunity_type"))
        contribution = _trace_text(row.get("contribution"))
        if not section_id:
            continue
        value = f"{opportunity_type}: {contribution}" if opportunity_type and contribution else contribution or opportunity_type
        if value:
            grouped.setdefault(section_id, []).append(value)
    return grouped


def _rules_by_opportunity(model_rulebook: pd.DataFrame | None) -> dict[str, list[str]]:
    if model_rulebook is None or model_rulebook.empty or "rule_id" not in model_rulebook:
        return {}
    grouped: dict[str, list[str]] = {}
    for rule_id in model_rulebook["rule_id"].dropna().astype(str):
        if not rule_id.startswith("opportunity."):
            continue
        opportunity_type = rule_id.split(".", 1)[1]
        if opportunity_type == "priority_score":
            continue
        grouped.setdefault(opportunity_type, []).append(rule_id)
    return grouped


def _split_tokens(value: Any) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for token in str(value or "").split("|"):
        cleaned = token.strip()
        if not cleaned or cleaned in seen or cleaned.lower() == "nan":
            continue
        seen.add(cleaned)
        tokens.append(cleaned)
    return tokens


def _generated_artifact_row_count(value: Any) -> int:
    if isinstance(value, pd.DataFrame):
        return int(len(value))
    if isinstance(value, list):
        return int(len(value))
    if isinstance(value, dict):
        return 1 if value else 0
    if value is None:
        return 0
    return 1


def _default_artifact_file_name(artifact_name: str) -> str:
    if artifact_name in {"data_quality", "insights", "consulting_story", "run_summary", "intake_profile"}:
        return f"{artifact_name}.json"
    return f"{artifact_name}.csv"


def _required_input_families(section_id: str, product: str) -> str:
    section = section_id.lower()
    if section in {"ars.mailer", "txn.campaign", "txn.ics_acquisition", "txn.ics_cohort"}:
        return "accounts|transactions|campaign_history"
    if product == "txn" or section.startswith("txn."):
        return "accounts|transactions"
    if product == "ars" or section.startswith("ars."):
        return "accounts"
    return "accounts|transactions"


def _section_input_readiness(section_id: str, product: str, data_quality: dict[str, Any]) -> str:
    account_rows = int(float(data_quality.get("account_rows", 0) or 0))
    transaction_rows = int(float(data_quality.get("transaction_rows", 0) or 0))
    required = set(_required_input_families(section_id, product).split("|"))
    missing: list[str] = []
    if "accounts" in required and account_rows <= 0:
        missing.append("accounts")
    if "transactions" in required and transaction_rows <= 0:
        missing.append("transactions")
    if missing:
        return "missing_" + "_and_".join(missing)
    return "ready"


def _analysis_evidence_status(
    *,
    primary_outputs: list[str],
    available_outputs: list[str],
    missing_outputs: list[str],
    input_readiness: str,
) -> str:
    if input_readiness != "ready":
        return "blocked_by_input"
    if not primary_outputs:
        return "inventory_only"
    if available_outputs and not missing_outputs:
        return "ready"
    if available_outputs:
        return "partial"
    return "missing"


def _consulting_question_for_section(section_id: str, analysis_family: Any) -> str:
    family = _trace_text(analysis_family)
    questions = {
        "portfolio_foundation": "What is the addressable base and how trustworthy is the data?",
        "debit_activation": "Where can debit usage, card economics, or wallet engagement be increased?",
        "overdraft_reg_e": "Where are compliant education, opt-in, or overdraft behavior opportunities?",
        "retention": "Which relationships are moving toward dormancy, attrition, or save-list risk?",
        "economics": "Where is the modeled financial value large enough to prioritize action?",
        "campaign_measurement": "Which prior or planned actions can be measured with a credible baseline?",
        "executive_synthesis": "What story should leadership hear and what decision should they make?",
        "transaction_portfolio": "What transaction behavior patterns define the current portfolio?",
        "merchant_behavior": "Which merchants or counterparties explain behavior, concentration, or leakage?",
        "category_behavior": "Which spend categories define wallet behavior and opportunity?",
        "business_relationships": "How do business relationships behave differently and what action channel fits?",
        "consumer_relationships": "How do consumer relationships behave across lifecycle and engagement states?",
        "competitive_leakage": "Where is money leaving to competitors and what win-back play fits?",
        "external_financial_life": "Which external financial relationships reveal lending or consolidation opportunity?",
        "acquisition": "Which acquisition cohorts become valuable, retained relationships?",
        "cohort_activation": "Which cohorts activate, deepen, or drop off after acquisition?",
        "branch_strategy": "Which branch-owned relationships need outreach or market-level action?",
        "payment_behavior": "How is payment-channel usage changing and where is activation needed?",
        "product_behavior": "Which products reveal depth, cross-sell, or attrition signals?",
        "deposit_retention": "Which balances are at risk from external movement or competitor pull?",
        "card_economics": "Where can card economics improve through debit activation or mix shift?",
        "payroll_primacy": "Which accounts show payroll, primacy, or direct-deposit conversion opportunity?",
        "relationship_depth": "Which relationships can be deepened based on product and external-life evidence?",
        "engagement_migration": "Which accounts or segments are upgrading, degrading, or ready for intervention?",
    }
    return questions.get(family, f"What decision does {section_id} support in this run?")


def _analysis_next_step(
    *,
    evidence_status: str,
    section_name: str,
    available_outputs: list[str],
    missing_outputs: list[str],
    input_readiness: str,
) -> str:
    if evidence_status == "blocked_by_input":
        return f"Resolve {input_readiness.replace('_', ' ')} before using {section_name}."
    if evidence_status == "ready":
        return f"Review {section_name} using {', '.join(available_outputs)}."
    if evidence_status == "partial":
        return (
            f"Use available evidence from {', '.join(available_outputs)} and validate missing "
            f"outputs: {', '.join(missing_outputs)}."
        )
    if evidence_status == "missing":
        return f"No current-run evidence was produced for {section_name}; inspect inputs or section mapping."
    return f"Inventory scripts for {section_name} and decide whether to map them into engine outputs."


def _account_scoring_opportunity_rollup(opportunities: pd.DataFrame | None) -> pd.DataFrame:
    columns = [
        "account_id",
        "period_month",
        "top_opportunity_type",
        "top_play_name",
        "top_priority_score",
        "top_expected_value",
        "opportunity_count",
        "total_expected_value",
        "opportunity_reason_codes",
        "all_opportunity_types",
        "top_opportunity_source_sections",
        "top_recommended_action",
    ]
    if opportunities is None or opportunities.empty:
        return pd.DataFrame(columns=columns)

    ranked = opportunities.copy().sort_values(
        ["account_id", "period_month", "priority_score", "expected_value"],
        ascending=[True, True, False, False],
    )
    rows: list[dict[str, Any]] = []
    for keys, group in ranked.groupby(["account_id", "period_month"], dropna=False):
        account_id, period_month = keys
        top = group.iloc[0]
        opportunity_type = _trace_text(top.get("opportunity_type"))
        playbook = OPPORTUNITY_PLAYBOOK.get(opportunity_type, {})
        rows.append(
            {
                "account_id": account_id,
                "period_month": period_month,
                "top_opportunity_type": opportunity_type,
                "top_play_name": playbook.get("play_name", opportunity_type.replace("_", " ").title()),
                "top_priority_score": round(float(top.get("priority_score", 0) or 0), 1),
                "top_expected_value": round(float(top.get("expected_value", 0) or 0), 2),
                "opportunity_count": int(group["opportunity_id"].nunique()) if "opportunity_id" in group else len(group),
                "total_expected_value": round(float(pd.to_numeric(group["expected_value"], errors="coerce").fillna(0).sum()), 2),
                "opportunity_reason_codes": _trace_text(top.get("reason_codes")),
                "all_opportunity_types": "|".join(
                    dict.fromkeys(
                        _trace_text(value)
                        for value in group["opportunity_type"].tolist()
                        if _trace_text(value)
                    )
                ),
                "top_opportunity_source_sections": _trace_text(top.get("source_sections")),
                "top_recommended_action": _trace_text(top.get("recommended_action")),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _trace_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _trace_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(value)


def _safe_int_value(value: Any, default: int = 0) -> int:
    try:
        if value is None or pd.isna(value):
            return int(default)
    except (TypeError, ValueError):
        pass
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return int(default)


def _segment_trace_rule(reason_codes: str) -> str:
    if not reason_codes:
        return "No relationship segment reason codes were produced."
    return f"Segment selected from reason codes: {reason_codes}."


def _opportunity_trace_rule(opportunity_type: str, cfg: EngineConfig) -> str:
    if opportunity_type == "payroll_conversion":
        return f"No payroll detected with external money movement or credit >= {cfg.payroll_min_amount:g}."
    if opportunity_type == "debit_activation":
        return f"Weak debit or low transaction activity with txn_count <= {cfg.active_txn_threshold}."
    if opportunity_type == "deposit_retention":
        return f"Balance >= {cfg.high_balance_threshold:g} and external FI amount >= {cfg.external_fi_amount_threshold:g}."
    if opportunity_type == "competitor_winback":
        return "External FI count >= 2 or PFI verdict is Split/Competitor-primary."
    if opportunity_type == "dormant_reactivation":
        return f"Txn_count <= {cfg.low_activity_txn_threshold} with balance or product value present."
    if opportunity_type == "relationship_expansion":
        return "Product_count <= 1 with external financial activity or financial-services counterparties."
    if opportunity_type == "attrition_prevention":
        return f"Split/competitor-primary relationship with txn_count <= {cfg.active_txn_threshold}."
    return "No top opportunity crossed the current V1 thresholds."


def _account_decision_trace(row: dict[str, Any], recommended_action: str) -> str:
    pfi_reasons = _trace_text(row.get("pfi_reason_codes")) or "limited_evidence"
    segment_reasons = _trace_text(row.get("segment_reason_codes")) or "no_segment_reasons"
    opportunity_reasons = _trace_text(row.get("opportunity_reason_codes")) or "no_opportunity_reasons"
    top_play = _trace_text(row.get("top_play_name")) or "No top play"
    action = (recommended_action or "Review manually").rstrip(".")
    return (
        f"PFI={_trace_text(row.get('pfi_verdict')) or 'No verdict'} "
        f"(internal={float(row.get('internal_score', 0) or 0):.3f}, "
        f"external={float(row.get('external_score', 0) or 0):.3f}, "
        f"confidence={_trace_text(row.get('confidence')) or 'low'}, reasons={pfi_reasons}); "
        f"segment={_trace_text(row.get('relationship_segment')) or 'Unclassified'} "
        f"(readiness={float(row.get('opportunity_readiness_score', 0) or 0):.1f}, "
        f"risk={_trace_text(row.get('risk_level')) or 'unknown'}, reasons={segment_reasons}); "
        f"top_play={top_play} "
        f"(priority={float(row.get('top_priority_score', 0) or 0):.1f}, "
        f"expected_value={_story_money(row.get('top_expected_value', 0))}, "
        f"reasons={opportunity_reasons}); action={action}."
    )


def _empty_counterparty_signals() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "signal_id",
            "client_id",
            "account_id",
            "period_month",
            "counterparty_name",
            "counterparty_category",
            "direction",
            "transaction_count",
            "active_days",
            "total_amount",
            "net_amount",
            "credit_amount",
            "debit_amount",
            "avg_ticket",
            "first_seen",
            "last_seen",
            "recurrence_score",
            "signal_strength",
            "relationship_signal",
            "confidence",
            "model_version",
        ]
    )


def _empty_counterparty_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "counterparty_id",
            "client_id",
            "period_month",
            "counterparty_name",
            "counterparty_category",
            "direction",
            "account_count",
            "transaction_count",
            "total_amount",
            "net_amount",
            "credit_amount",
            "debit_amount",
            "avg_signal_strength",
            "top_relationship_signal",
            "signal_mix",
            "strategy_relevance",
            "first_seen",
            "last_seen",
            "model_version",
        ]
    )


def _empty_relationship_segments() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "segment_id",
            "client_id",
            "account_id",
            "period_month",
            "relationship_segment",
            "segment_group",
            "lifecycle_stage",
            "risk_level",
            "pfi_verdict",
            "pfi_score",
            "confidence",
            "engagement_tier",
            "payroll_detected",
            "external_intensity",
            "balance",
            "txn_count",
            "product_count",
            "has_debit",
            "top_opportunity_type",
            "top_priority_score",
            "opportunity_count",
            "total_expected_value",
            "opportunity_readiness_score",
            "next_best_motion",
            "segment_reason_codes",
            "model_version",
        ]
    )


def _empty_segment_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "client_id",
            "period_month",
            "relationship_segment",
            "segment_group",
            "lifecycle_stage",
            "risk_level",
            "account_count",
            "avg_pfi_score",
            "avg_external_intensity",
            "avg_balance",
            "payroll_accounts",
            "total_expected_value",
            "avg_readiness_score",
            "top_next_best_motion",
            "top_reason_codes",
            "model_version",
        ]
    )


def _empty_opportunities() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "opportunity_id",
            "client_id",
            "account_id",
            "period_month",
            "opportunity_type",
            "expected_value",
            "priority_score",
            "impact_score",
            "addressability_score",
            "confidence_score",
            "urgency_score",
            "confidence",
            "pfi_verdict",
            "reason_codes",
            "recommended_action",
            "source_sections",
            "model_version",
        ]
    )


def _empty_opportunity_portfolio() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "priority_rank",
            "portfolio_id",
            "client_id",
            "period_month",
            "opportunity_type",
            "play_name",
            "target_accounts",
            "high_priority_accounts",
            "expected_value",
            "avg_expected_value_per_account",
            "avg_priority_score",
            "confidence",
            "confidence_score",
            "top_reason_codes",
            "pfi_mix",
            "source_sections",
            "audience_definition",
            "owner_role",
            "recommended_channel",
            "next_step",
            "primary_metric",
            "model_version",
        ]
    )


def _empty_executive_scorecard() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "scorecard_id",
            "client_id",
            "period_month",
            "domain",
            "metric_name",
            "metric_value",
            "metric_display",
            "benchmark",
            "score",
            "rag_status",
            "interpretation",
            "recommended_focus",
            "owner_role",
            "source_artifacts",
            "model_version",
        ]
    )


def _empty_strategy_roadmap() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "roadmap_id",
            "client_id",
            "period_month",
            "phase",
            "priority_rank",
            "initiative",
            "initiative_type",
            "source_signal",
            "target_accounts",
            "expected_value",
            "owner_role",
            "first_action",
            "dependency",
            "proof_metric",
            "source_artifacts",
            "status",
            "model_version",
        ]
    )


def _empty_action_plan() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "action_id",
            "client_id",
            "period_month",
            "priority_rank",
            "play_name",
            "opportunity_type",
            "objective",
            "target_accounts",
            "expected_value",
            "confidence",
            "audience_definition",
            "owner_role",
            "recommended_channel",
            "next_step",
            "talk_track",
            "target_list_ref",
            "measurement_id",
            "status",
            "model_version",
        ]
    )


def _empty_measurement_plan() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "measurement_id",
            "client_id",
            "period_month",
            "action_id",
            "play_name",
            "opportunity_type",
            "recommended_design",
            "holdout_pct",
            "holdout_accounts",
            "test_accounts",
            "primary_metric",
            "secondary_metrics",
            "baseline_window",
            "measurement_windows",
            "success_definition",
            "model_version",
        ]
    )


def _empty_campaign_targets() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "action_id",
            "measurement_id",
            "client_id",
            "period_month",
            "play_name",
            "opportunity_type",
            "target_rank_within_play",
            "account_id",
            "measurement_group",
            "target_status",
            "priority_score",
            "expected_value",
            "confidence",
            "pfi_verdict",
            "pfi_score",
            "reason_codes",
            "recommended_action",
            "owner_role",
            "recommended_channel",
            "primary_metric",
            "txn_count",
            "active_days",
            "spend_amount",
            "credit_amount",
            "net_amount",
            "payroll_count",
            "payroll_amount",
            "external_fi_count",
            "external_fi_amount",
            "financial_services_count",
            "unique_merchants",
            "balance",
            "has_debit",
            "business_flag",
            "branch",
            "product_code",
            "product_count",
            "external_intensity",
            "payroll_detected",
            "engagement_tier",
            "model_version",
        ]
    )


def _empty_measurement_baseline() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "measurement_id",
            "action_id",
            "client_id",
            "period_month",
            "play_name",
            "opportunity_type",
            "target_accounts",
            "test_accounts",
            "control_accounts",
            "baseline_expected_value",
            "baseline_avg_priority_score",
            "baseline_total_spend",
            "baseline_total_credit",
            "baseline_total_external_fi_amount",
            "baseline_avg_txn_count",
            "baseline_avg_active_days",
            "baseline_payroll_detected_accounts",
            "baseline_avg_balance",
            "baseline_window",
            "future_outcome_join_key",
            "model_version",
        ]
    )


def _empty_outcome_results() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "measurement_id",
            "action_id",
            "client_id",
            "account_id",
            "play_name",
            "opportunity_type",
            "measurement_group",
            "period_month_baseline",
            "period_month_current",
            "target_status",
            "priority_score",
            "expected_value",
            "confidence",
            "pfi_verdict",
            "current_pfi_verdict",
            "current_pfi_score",
            "primary_metric",
            "baseline_txn_count",
            "current_txn_count",
            "delta_txn_count",
            "baseline_spend_amount",
            "current_spend_amount",
            "delta_spend_amount",
            "baseline_credit_amount",
            "current_credit_amount",
            "delta_credit_amount",
            "baseline_external_fi_amount",
            "current_external_fi_amount",
            "delta_external_fi_amount",
            "baseline_balance",
            "current_balance",
            "delta_balance",
            "baseline_payroll_detected",
            "current_payroll_detected",
            "current_account_found",
            "outcome_flag",
            "outcome_status",
        ]
    )


def _empty_outcome_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "measurement_id",
            "action_id",
            "client_id",
            "outcome_period_month",
            "play_name",
            "opportunity_type",
            "target_accounts",
            "test_accounts",
            "test_outcome_accounts",
            "test_outcome_rate",
            "holdout_accounts",
            "holdout_outcome_accounts",
            "holdout_outcome_rate",
            "lift_vs_holdout",
            "avg_delta_txn_count",
            "avg_delta_spend_amount",
            "avg_delta_credit_amount",
            "avg_delta_external_fi_amount",
            "avg_delta_balance",
            "measured_expected_value",
            "measurement_status",
            "interpretation",
            "model_version",
        ]
    )


def _safe_ratio(num: Any, den: Any) -> pd.Series:
    n = pd.to_numeric(num, errors="coerce").fillna(0.0)
    d = pd.to_numeric(den, errors="coerce").replace(0, np.nan)
    return (n / d).fillna(0.0)


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _pfi_reasons(
    *,
    payroll_count: float,
    activity_score: float,
    balance: float,
    product_count: float,
    external_count: float,
    external_amount: float,
    matched: bool,
) -> list[str]:
    reasons: list[str] = []
    if matched:
        reasons.append("account_match")
    if payroll_count > 0:
        reasons.append("payroll_detected")
    if activity_score >= 0.5:
        reasons.append("strong_activity")
    if balance >= 5000:
        reasons.append("meaningful_balance")
    if product_count > 1:
        reasons.append("multi_product")
    if external_count > 0:
        reasons.append("external_fi_activity")
    if external_amount >= 1000:
        reasons.append("material_external_amount")
    return reasons or ["limited_evidence"]


def _impact_score(value: float) -> float:
    value = max(float(value or 0), 0.0)
    if value == 0:
        return 0.0
    return min(math.log1p(value) / math.log1p(25000.0), 1.0)


def _period_label(value: str | None) -> str:
    if not value:
        return pd.Timestamp.today().to_period("M").strftime("%Y-%m")
    cleaned = str(value).strip().replace(".", "-")
    try:
        return pd.Period(cleaned, freq="M").strftime("%Y-%m")
    except ValueError:
        return cleaned


def _infer_file_type(path: Path) -> str:
    name = path.name.lower()
    if "odd" in name:
        return "odd"
    if "tran" in name or "txn" in name:
        return "transaction"
    if "deferred" in name:
        return "deferred_revenue"
    if "campaign" in name or "mailer" in name:
        return "campaign"
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        return "workbook"
    return "unknown"


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_non_empty(series: pd.Series) -> str:
    for value in series:
        if pd.notna(value) and str(value).strip():
            return str(value).strip()
    return ""


def _join_unique(series: pd.Series) -> str:
    values = sorted({str(value).strip() for value in series if pd.notna(value) and str(value).strip()})
    return "|".join(values)


def _join_unique_tokens(*values: object) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for value in values:
        for token in str(value or "").split("|"):
            cleaned = token.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            tokens.append(cleaned)
    return "|".join(tokens)


def _top_tokens(series: pd.Series, limit: int = 5) -> list[str]:
    counts: dict[str, int] = {}
    for value in series.dropna().astype(str):
        for token in value.split("|"):
            if token:
                counts[token] = counts.get(token, 0) + 1
    return [token for token, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _account_profile_evidence(row: dict[str, Any]) -> str:
    payroll = "payroll detected" if bool(row.get("payroll_detected", False)) else "no payroll detected"
    parts = [
        str(row.get("pfi_verdict", "No verdict")),
        str(row.get("relationship_segment", "Unclassified")),
        f"{int(float(row.get('txn_count', 0) or 0))} txns",
        payroll,
        f"external FI {_story_money(row.get('external_fi_amount', 0))}",
    ]
    counterparties = str(row.get("top_counterparties", "") or "").strip()
    if counterparties:
        parts.append(f"top counterparties: {counterparties}")
    opportunity = str(row.get("top_play_name", "") or "").strip()
    if opportunity:
        parts.append(f"top play: {opportunity}")
    return "; ".join(part for part in parts if part)


def _domain_for_opportunity(opportunity_type: str) -> str:
    if opportunity_type in {"payroll_conversion", "relationship_expansion"}:
        return "Relationship and Primacy"
    if opportunity_type in {"competitor_winback", "deposit_retention"}:
        return "Competitive Leakage"
    if opportunity_type in {"debit_activation"}:
        return "Revenue and Value"
    if opportunity_type in {"dormant_reactivation", "attrition_prevention"}:
        return "Lifecycle and Retention"
    return "Executive Synthesis"


def _outcome_metric_for_opportunity(opportunity_type: str) -> str:
    return {
        "payroll_conversion": "new_direct_deposit_or_payroll_detected",
        "debit_activation": "new_or_increased_debit_usage",
        "deposit_retention": "retained_balance",
        "competitor_winback": "reduced_external_fi_transfer_share",
        "dormant_reactivation": "recovered_transaction_activity",
        "relationship_expansion": "new_product_or_relationship_depth",
        "attrition_prevention": "account_retained_and_activity_stabilized",
    }.get(opportunity_type, "behavior_change")


def _action_objective(opportunity_type: str) -> str:
    return {
        "payroll_conversion": "Move external income or credits into a primary banking relationship.",
        "debit_activation": "Increase active debit usage and interchange contribution.",
        "deposit_retention": "Protect high-balance relationships showing external movement.",
        "competitor_winback": "Reduce competitor capture and consolidate financial activity.",
        "dormant_reactivation": "Restore measurable transaction activity before dormancy deepens.",
        "relationship_expansion": "Grow thin relationships with next-best-product outreach.",
        "attrition_prevention": "Stabilize at-risk accounts before balance runoff or closure.",
    }.get(opportunity_type, "Convert scored behavior into a targeted action.")


def _talk_track(opportunity_type: str, target_accounts: int, expected_value: Any) -> str:
    value = _money(expected_value)
    label = opportunity_type.replace("_", " ")
    return (
        f"{target_accounts:,} account(s) show {label} behavior with {value} in modeled value. "
        "Review data confidence, approve the target list, and measure movement over 30/60/90 days."
    )


def _secondary_metrics(opportunity_type: str) -> list[str]:
    return {
        "payroll_conversion": ["deposit_amount", "credit_frequency", "pfi_score"],
        "debit_activation": ["swipe_count", "spend_amount", "interchange_revenue"],
        "deposit_retention": ["balance_retained", "external_fi_amount", "banker_contact_rate"],
        "competitor_winback": ["external_fi_count", "external_fi_amount", "relationship_depth"],
        "dormant_reactivation": ["txn_count", "active_days", "digital_or_card_activity"],
        "relationship_expansion": ["product_count", "financial_services_count", "pfi_score"],
        "attrition_prevention": ["account_retained", "txn_count", "balance_retained"],
    }.get(opportunity_type, ["target_behavior_change"])


def _success_definition(opportunity_type: str) -> str:
    metric = _outcome_metric_for_opportunity(opportunity_type)
    return f"Primary success is a statistically or directionally meaningful lift in {metric} versus baseline or holdout."


def _measurement_group(action_id: Any, account_id: Any, holdout_pct: float) -> str:
    if holdout_pct <= 0:
        return "test"
    key = f"{action_id}|{account_id}".encode("utf-8", errors="ignore")
    bucket = int(sha256(key).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "holdout" if bucket < holdout_pct else "test"


def _bool_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    return df[column].astype(str).str.lower().isin({"true", "1", "yes", "y"})


def _outcome_flag_for_row(row: pd.Series) -> bool:
    opportunity_type = str(row.get("opportunity_type", ""))
    if not bool(row.get("current_account_found", False)):
        return False
    delta_txn = float(row.get("delta_txn_count", 0) or 0)
    delta_spend = float(row.get("delta_spend_amount", 0) or 0)
    delta_credit = float(row.get("delta_credit_amount", 0) or 0)
    delta_external = float(row.get("delta_external_fi_amount", 0) or 0)
    delta_balance = float(row.get("delta_balance", 0) or 0)
    baseline_balance = float(row.get("baseline_balance", 0) or 0)
    current_payroll = bool(row.get("current_payroll_detected", False))
    baseline_payroll = bool(row.get("baseline_payroll_detected", False))
    current_product_count = float(row.get("current_product_count", 0) or 0)
    baseline_product_count = float(row.get("baseline_product_count", 0) or 0)

    if opportunity_type == "payroll_conversion":
        return current_payroll and not baseline_payroll
    if opportunity_type == "debit_activation":
        return delta_spend > 0 or delta_txn >= 3
    if opportunity_type == "deposit_retention":
        return delta_balance >= 0 or (baseline_balance > 0 and row.get("current_balance", 0) >= baseline_balance * 0.90)
    if opportunity_type == "competitor_winback":
        return delta_external < 0
    if opportunity_type == "dormant_reactivation":
        return delta_txn > 0
    if opportunity_type == "relationship_expansion":
        return current_product_count > baseline_product_count or delta_credit > 0
    if opportunity_type == "attrition_prevention":
        return bool(row.get("current_account_found", False)) and (delta_txn >= 0 or delta_balance >= -max(baseline_balance * 0.10, 100))
    return any(value > 0 for value in (delta_txn, delta_spend, delta_credit, delta_balance))


def _outcome_interpretation(test_rate: float, holdout_rate: float, holdout_accounts: int) -> str:
    if holdout_accounts:
        lift = test_rate - holdout_rate
        if lift > 0.02:
            return "Positive lift versus holdout."
        if lift < -0.02:
            return "Underperformed holdout; review targeting and offer."
        return "Flat versus holdout; continue monitoring or refine audience."
    if test_rate > 0:
        return "Outcome activity detected; no holdout available, compare with prior baseline."
    return "No measured outcome yet; continue monitoring."


def _money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return str(value)
