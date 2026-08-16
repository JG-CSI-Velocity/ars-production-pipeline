"""Analysis-section catalog and provenance builders.

The transactional intelligence engine needs to preserve the existing ARS/TXN
analysis IP instead of hiding it behind a new scoring layer. These builders
create structured metadata that connects engine outputs back to the section
folders and scripts that support each recommendation.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd


CATALOG_VERSION = "analysis_catalog_v0"

FIELD_USAGE_VERSION = "analysis_field_usage_v0"

FIELD_TOKEN_HINTS = {
    "account",
    "acct",
    "member",
    "household",
    "primary_account_num",
    "transaction",
    "txn",
    "date",
    "month",
    "amount",
    "spend",
    "swipe",
    "merchant",
    "mcc",
    "counterparty",
    "category",
    "branch",
    "product",
    "prod",
    "status",
    "stat",
    "balance",
    "bal",
    "business",
    "personal",
    "age",
    "debit",
    "credit",
    "pin",
    "sig",
    "payroll",
    "competitor",
    "mail",
    "resp",
    "response",
    "offer",
    "campaign",
    "wave",
    "control",
    "holdout",
    "group",
    "segment",
    "score",
    "risk",
    "reg e",
    "overdraft",
    "opened",
    "closed",
    "source",
    "channel",
}

NON_FIELD_METHOD_NAMES = {
    "all",
    "any",
    "count",
    "first",
    "last",
    "max",
    "mean",
    "median",
    "min",
    "nunique",
    "size",
    "std",
    "sum",
}

NON_FIELD_TARGET_HINTS = (
    "color",
    "colors",
    "palette",
    "keyword",
    "keywords",
    "pattern",
    "patterns",
    "label",
    "labels",
    "title",
    "caption",
    "prune",
    "skip",
)

NON_FIELD_SUBSCRIPT_BASES = {
    "GEN_COLORS",
    "CATEGORY_PALETTE",
    "COLORS",
    "PALETTE",
    "FONT",
    "FONTS",
    "STYLE",
    "THEME",
    "ctx.results",
}


SECTION_STRATEGY: dict[str, dict[str, str]] = {
    "ars.overview": {
        "analysis_family": "portfolio_foundation",
        "intelligence_layers": "data_trust|feature_mart",
        "engine_outputs": "data_quality|account_month_features|executive_scorecard",
        "consulting_use": "Define account base, eligibility, product mix, and open-account denominator.",
    },
    "ars.dctr": {
        "analysis_family": "debit_activation",
        "intelligence_layers": "feature_mart|opportunity_scoring|activation",
        "engine_outputs": "opportunities|opportunity_portfolio|campaign_targets",
        "consulting_use": "Support debit activation plays, card penetration gaps, and usage incentives.",
    },
    "ars.rege": {
        "analysis_family": "overdraft_reg_e",
        "intelligence_layers": "feature_mart|opportunity_scoring|activation",
        "engine_outputs": "executive_scorecard|strategy_roadmap|action_plan",
        "consulting_use": "Frame compliant Reg E and overdraft education opportunities.",
    },
    "ars.attrition": {
        "analysis_family": "retention",
        "intelligence_layers": "relationship_diagnosis|opportunity_scoring|measurement",
        "engine_outputs": "relationship_segments|opportunities|outcome_summary",
        "consulting_use": "Support attrition prevention and save-list prioritization.",
    },
    "ars.value": {
        "analysis_family": "economics",
        "intelligence_layers": "opportunity_scoring|strategy",
        "engine_outputs": "opportunities|opportunity_portfolio|executive_scorecard",
        "consulting_use": "Translate behavior gaps into modeled value and executive business case.",
    },
    "ars.mailer": {
        "analysis_family": "campaign_measurement",
        "intelligence_layers": "activation|measurement|outcomes",
        "engine_outputs": "campaign_targets|measurement_baseline|outcome_summary",
        "consulting_use": "Connect campaign exposure, response, lift, and persistence to action design.",
    },
    "ars.insights": {
        "analysis_family": "executive_synthesis",
        "intelligence_layers": "insight_registry|consulting_story",
        "engine_outputs": "insights|consulting_story|strategy_roadmap",
        "consulting_use": "Render standardized findings into executive narrative and decision flow.",
    },
    "txn.general": {
        "analysis_family": "transaction_portfolio",
        "intelligence_layers": "data_trust|feature_mart|segmentation",
        "engine_outputs": "account_month_features|relationship_segments|executive_scorecard",
        "consulting_use": "Describe transaction portfolio health, activity mix, and broad action themes.",
    },
    "txn.merchant": {
        "analysis_family": "merchant_behavior",
        "intelligence_layers": "counterparty|feature_mart|opportunity_scoring",
        "engine_outputs": "counterparty_signals|counterparty_summary|opportunities",
        "consulting_use": "Expose merchant concentration, volatility, growth, and behavior patterns.",
    },
    "txn.mcc_code": {
        "analysis_family": "category_behavior",
        "intelligence_layers": "counterparty|feature_mart|segmentation",
        "engine_outputs": "counterparty_summary|account_month_features|relationship_segments",
        "consulting_use": "Explain spend category mix, concentration, and category-level opportunity.",
    },
    "txn.business_accts": {
        "analysis_family": "business_relationships",
        "intelligence_layers": "feature_mart|segmentation|strategy",
        "engine_outputs": "account_month_features|relationship_segments|strategy_roadmap",
        "consulting_use": "Separate business-account behaviors, risks, and owner/channel motions.",
    },
    "txn.personal_accts": {
        "analysis_family": "consumer_relationships",
        "intelligence_layers": "feature_mart|segmentation|strategy",
        "engine_outputs": "account_month_features|relationship_segments|strategy_roadmap",
        "consulting_use": "Separate consumer-account behaviors, risks, and lifecycle opportunities.",
    },
    "txn.competition": {
        "analysis_family": "competitive_leakage",
        "intelligence_layers": "counterparty|pfi|opportunity_scoring",
        "engine_outputs": "counterparty_signals|pfi_verdicts|opportunities",
        "consulting_use": "Detect competitor movement, external FI pressure, and win-back audiences.",
    },
    "txn.financial_services": {
        "analysis_family": "external_financial_life",
        "intelligence_layers": "counterparty|relationship_diagnosis|opportunity_scoring",
        "engine_outputs": "counterparty_summary|relationship_segments|opportunities",
        "consulting_use": "Find external loans, mortgage, cards, brokerage, insurance, and leakage.",
    },
    "txn.ics_acquisition": {
        "analysis_family": "acquisition",
        "intelligence_layers": "feature_mart|activation|measurement",
        "engine_outputs": "campaign_targets|measurement_plan|outcome_summary",
        "consulting_use": "Analyze acquisition channels, engagement, retention, and portfolio fit.",
    },
    "txn.ICS_cohort": {
        "analysis_family": "cohort_activation",
        "intelligence_layers": "feature_mart|segmentation|measurement",
        "engine_outputs": "account_month_features|relationship_segments|outcome_summary",
        "consulting_use": "Compare cohort activation, source, product mix, balance, closure, and retention.",
    },
    "txn.campaign": {
        "analysis_family": "campaign_measurement",
        "intelligence_layers": "activation|measurement|outcomes",
        "engine_outputs": "campaign_targets|measurement_baseline|outcome_results|outcome_summary",
        "consulting_use": "Measure response, lift, counterfactuals, persistence, and spend shift.",
    },
    "txn.branch_txn": {
        "analysis_family": "branch_strategy",
        "intelligence_layers": "feature_mart|strategy|activation",
        "engine_outputs": "account_month_features|strategy_roadmap|campaign_targets",
        "consulting_use": "Rank branch gaps and route branch-owned outreach opportunities.",
    },
    "txn.transaction_type": {
        "analysis_family": "payment_behavior",
        "intelligence_layers": "feature_mart|segmentation",
        "engine_outputs": "account_month_features|relationship_segments|executive_scorecard",
        "consulting_use": "Explain payment-channel mix, migration, and card/payment behavior changes.",
    },
    "txn.product": {
        "analysis_family": "product_behavior",
        "intelligence_layers": "feature_mart|relationship_diagnosis|strategy",
        "engine_outputs": "account_month_features|relationship_segments|opportunity_portfolio",
        "consulting_use": "Break behavior down by product and expose product-level growth paths.",
    },
    "txn.attrition_txn": {
        "analysis_family": "retention",
        "intelligence_layers": "relationship_diagnosis|opportunity_scoring|activation",
        "engine_outputs": "relationship_segments|opportunities|campaign_targets",
        "consulting_use": "Create transaction-based early warning and at-risk export lists.",
    },
    "txn.balance": {
        "analysis_family": "deposit_retention",
        "intelligence_layers": "feature_mart|pfi|opportunity_scoring",
        "engine_outputs": "account_month_features|pfi_verdicts|opportunities",
        "consulting_use": "Connect balances, external movement, PFI, and deposit flight risk.",
    },
    "txn.interchange": {
        "analysis_family": "card_economics",
        "intelligence_layers": "feature_mart|opportunity_scoring|strategy",
        "engine_outputs": "account_month_features|opportunities|opportunity_portfolio",
        "consulting_use": "Size debit activation, PIN/signature mix, and interchange opportunity.",
    },
    "txn.rege_overdraft": {
        "analysis_family": "overdraft_reg_e",
        "intelligence_layers": "feature_mart|strategy|measurement",
        "engine_outputs": "executive_scorecard|strategy_roadmap|measurement_plan",
        "consulting_use": "Evaluate overdraft exposure, opt-in migration, limits, and risk/value bands.",
    },
    "txn.payroll": {
        "analysis_family": "payroll_primacy",
        "intelligence_layers": "feature_mart|pfi|opportunity_scoring",
        "engine_outputs": "account_month_features|pfi_verdicts|opportunities",
        "consulting_use": "Detect direct deposit, processors, payroll value, retention, and conversion opportunity.",
    },
    "txn.relationship": {
        "analysis_family": "relationship_depth",
        "intelligence_layers": "relationship_diagnosis|segmentation|opportunity_scoring",
        "engine_outputs": "relationship_segments|segment_summary|opportunities",
        "consulting_use": "Measure product depth, cross-sell, leakage, relationship value, and next-best product.",
    },
    "txn.segment_evolution": {
        "analysis_family": "engagement_migration",
        "intelligence_layers": "segmentation|measurement|strategy",
        "engine_outputs": "relationship_segments|segment_summary|strategy_roadmap",
        "consulting_use": "Track engagement movement, upgraders/degraders, and intervention triggers.",
    },
    "txn.retention": {
        "analysis_family": "retention",
        "intelligence_layers": "relationship_diagnosis|opportunity_scoring|measurement",
        "engine_outputs": "relationship_segments|opportunities|outcome_summary",
        "consulting_use": "Measure churn, dormancy progression, attrition cost, and retention actions.",
    },
    "txn.engagement": {
        "analysis_family": "engagement_migration",
        "intelligence_layers": "segmentation|strategy|measurement",
        "engine_outputs": "relationship_segments|strategy_roadmap|outcome_summary",
        "consulting_use": "Track month-to-month engagement tier movement and net flow.",
    },
    "txn.executive": {
        "analysis_family": "executive_synthesis",
        "intelligence_layers": "insight_registry|strategy|consulting_story",
        "engine_outputs": "executive_scorecard|strategy_roadmap|consulting_story",
        "consulting_use": "Roll transaction findings into executive priorities, scorecard, and roadmap.",
    },
}


def build_analysis_section_catalog(repo_root: Path | str | None = None) -> pd.DataFrame:
    """Build one row per ARS/TXN analysis section in the repository."""
    root = _repo_root(repo_root)
    rows: list[dict[str, Any]] = []
    for item in _section_rows(root):
        section_id = str(item.get("section_id", ""))
        folder = str(item.get("folder") or section_id.split(".", 1)[-1])
        folder_path = root / "01_Analysis" / "00-Scripts" / "analytics" / folder
        script_files = _script_files(folder_path)
        strategy = SECTION_STRATEGY.get(section_id, {})
        opportunity_types = _opportunity_types_for_section(section_id)
        rows.append(
            {
                "source_section_id": section_id,
                "product": item.get("product", ""),
                "display_name": item.get("display_name", section_id),
                "folder": folder,
                "source_path": _rel(root, folder_path),
                "slide_code": item.get("slide_code", ""),
                "configured_module_count": item.get("module_count"),
                "script_count": len(script_files),
                "runnable_script_count": sum(1 for path in script_files if _is_runnable(path)),
                "analysis_family": strategy.get("analysis_family", "unmapped"),
                "intelligence_layers": strategy.get("intelligence_layers", ""),
                "primary_engine_outputs": strategy.get("engine_outputs", ""),
                "supports_opportunity_types": "|".join(opportunity_types),
                "consulting_use": strategy.get("consulting_use", "Review section outputs for supporting evidence."),
                "script_files": "|".join(path.name for path in script_files),
                "catalog_version": CATALOG_VERSION,
            }
        )
    return pd.DataFrame(rows, columns=_section_catalog_columns()).sort_values(
        ["product", "source_section_id"]
    ).reset_index(drop=True)


def build_analysis_script_catalog(repo_root: Path | str | None = None) -> pd.DataFrame:
    """Build one row per analysis script, inferred from current section folders."""
    root = _repo_root(repo_root)
    sections = {row["section_id"]: row for row in _section_rows(root)}
    rows: list[dict[str, Any]] = []
    for section_id, item in sections.items():
        folder = str(item.get("folder") or section_id.split(".", 1)[-1])
        folder_path = root / "01_Analysis" / "00-Scripts" / "analytics" / folder
        for script_path in _script_files(folder_path):
            topic = _script_topic(script_path.name)
            rows.append(
                {
                    "source_section_id": section_id,
                    "product": item.get("product", ""),
                    "display_name": item.get("display_name", section_id),
                    "folder": folder,
                    "script_order": _script_order(script_path.name),
                    "script_name": script_path.name,
                    "source_path": _rel(root, script_path),
                    "inferred_topic": topic,
                    "output_role": _output_role(script_path.name, topic),
                    "runnable_flag": _is_runnable(script_path),
                    "catalog_version": CATALOG_VERSION,
                }
            )
    return pd.DataFrame(rows, columns=_script_catalog_columns()).sort_values(
        ["source_section_id", "script_order", "script_name"],
        na_position="last",
    ).reset_index(drop=True)


def build_analysis_field_usage_catalog(repo_root: Path | str | None = None) -> pd.DataFrame:
    """Build a script-derived field reference catalog for layout mapping work.

    This is static evidence from the Python analysis files. It does not prove
    every client extract has these fields; it tells analysts which field names
    the existing analysis code appears to reference.
    """
    root = _repo_root(repo_root)
    sections = {row["section_id"]: row for row in _section_rows(root)}
    rows: list[dict[str, Any]] = []
    for section_id, item in sections.items():
        folder = str(item.get("folder") or section_id.split(".", 1)[-1])
        folder_path = root / "01_Analysis" / "00-Scripts" / "analytics" / folder
        for script_path in _script_files(folder_path):
            for ref in _script_field_references(script_path):
                rows.append(
                    {
                        "source_section_id": section_id,
                        "product": item.get("product", ""),
                        "display_name": item.get("display_name", section_id),
                        "folder": folder,
                        "script_name": script_path.name,
                        "source_path": _rel(root, script_path),
                        "line_number": ref["line_number"],
                        "field_reference": ref["field_reference"],
                        "normalized_field": _normalize_field_name(ref["field_reference"]),
                        "input_family_hint": _field_input_family_hint(ref["field_reference"]),
                        "canonical_field_hint": _canonical_field_hint(ref["field_reference"]),
                        "evidence_context": ref["evidence_context"],
                        "extraction_method": ref["extraction_method"],
                        "catalog_version": FIELD_USAGE_VERSION,
                    }
                )
    if not rows:
        return pd.DataFrame(columns=_field_usage_catalog_columns())
    df = pd.DataFrame(rows, columns=_field_usage_catalog_columns())
    return (
        df.drop_duplicates(
            subset=[
                "source_section_id",
                "script_name",
                "line_number",
                "field_reference",
                "evidence_context",
            ]
        )
        .sort_values(["source_section_id", "script_name", "line_number", "field_reference"])
        .reset_index(drop=True)
    )


def build_analysis_provenance_map(
    source_sections_by_opportunity: dict[str, Iterable[str]] | None = None,
    repo_root: Path | str | None = None,
) -> pd.DataFrame:
    """Map each opportunity model to the existing analysis sections it uses."""
    root = _repo_root(repo_root)
    section_catalog = build_analysis_section_catalog(root)
    sections = {
        row["source_section_id"]: row
        for row in section_catalog.to_dict(orient="records")
    }
    rows: list[dict[str, Any]] = []
    for opportunity_type, section_ids in sorted((source_sections_by_opportunity or {}).items()):
        for section_id in section_ids:
            section = sections.get(section_id, {})
            rows.append(
                {
                    "opportunity_type": opportunity_type,
                    "source_section_id": section_id,
                    "product": section.get("product", section_id.split(".", 1)[0]),
                    "display_name": section.get("display_name", section_id),
                    "analysis_family": section.get("analysis_family", "unmapped"),
                    "intelligence_layers": section.get("intelligence_layers", ""),
                    "primary_engine_outputs": section.get("primary_engine_outputs", ""),
                    "script_count": section.get("script_count", 0),
                    "source_path": section.get(
                        "source_path",
                        _rel(root, root / "01_Analysis" / "00-Scripts" / "analytics" / section_id.split(".", 1)[-1]),
                    ),
                    "contribution": _opportunity_contribution(opportunity_type, section_id),
                    "catalog_version": CATALOG_VERSION,
                }
            )
    return pd.DataFrame(rows, columns=_provenance_columns()).reset_index(drop=True)


def _section_rows(root: Path) -> list[dict[str, Any]]:
    sections_path = root / "01_Analysis" / "00-Scripts" / "tools" / "sections.json"
    if sections_path.exists():
        data = json.loads(sections_path.read_text(encoding="utf-8"))
        return [
            {
                "section_id": row.get("section_id", ""),
                "product": row.get("product", ""),
                "display_name": row.get("display_name", row.get("section_id", "")),
                "folder": row.get("section_id", "").split(".", 1)[-1],
                "slide_code": row.get("slide_code", ""),
                "module_count": row.get("module_count"),
            }
            for row in data
        ]

    analytics_dir = root / "01_Analysis" / "00-Scripts" / "analytics"
    rows = []
    for folder in sorted(path for path in analytics_dir.iterdir() if path.is_dir()):
        if folder.name.startswith("__"):
            continue
        product = "ars" if folder.name in {"overview", "dctr", "rege", "attrition", "value", "mailer", "insights"} else "txn"
        rows.append(
            {
                "section_id": f"{product}.{folder.name}",
                "product": product,
                "display_name": folder.name.replace("_", " ").title(),
                "folder": folder.name,
                "slide_code": "",
                "module_count": None,
            }
        )
    return rows


def _script_files(folder_path: Path) -> list[Path]:
    if not folder_path.exists():
        return []
    return sorted(path for path in folder_path.glob("*.py") if path.name != "__init__.py")


def _is_runnable(path: Path) -> bool:
    name = path.name
    if name.startswith("_") or name == "__init__.py":
        return False
    return True


def _script_field_references(path: Path) -> list[dict[str, Any]]:
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="latin-1")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    refs: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            base_name = _node_name(node.value)
            if base_name in NON_FIELD_SUBSCRIPT_BASES:
                continue
            value = _literal_string_from_slice(node.slice)
            if _looks_like_field_reference(value):
                refs.append(
                    _field_ref(
                        node,
                        value,
                        evidence_context=f"subscript:{base_name or 'unknown'}",
                        extraction_method="ast_subscript",
                    )
                )
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in {"agg", "groupby", "merge", "sort_values", "pivot_table", "drop", "rename", "assign"}:
                for value in _string_constants(node):
                    if _looks_like_field_reference(value):
                        refs.append(
                            _field_ref(
                                node,
                                value,
                                evidence_context=f"call:{call_name}",
                                extraction_method="ast_call_constant",
                            )
                        )
        elif isinstance(node, ast.Assign):
            target_name = "|".join(_assignment_target_names(node.targets)).lower()
            if not _assignment_may_define_fields(target_name):
                continue
            for value in _string_constants(node.value):
                if _looks_like_field_reference(value):
                    refs.append(
                        _field_ref(
                            node,
                            value,
                            evidence_context=f"assignment:{target_name or 'unknown'}",
                            extraction_method="ast_assignment_constant",
                        )
                    )
    return refs


def _field_ref(
    node: ast.AST,
    value: str,
    *,
    evidence_context: str,
    extraction_method: str,
) -> dict[str, Any]:
    return {
        "line_number": int(getattr(node, "lineno", 0) or 0),
        "field_reference": value.strip(),
        "evidence_context": evidence_context,
        "extraction_method": extraction_method,
    }


def _literal_string_from_slice(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Index):  # pragma: no cover - py<3.9 compatibility
        return _literal_string_from_slice(node.value)
    return ""


def _node_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _node_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Subscript):
        return _node_name(node.value)
    return ""


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _string_constants(node: ast.AST) -> list[str]:
    values: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.append(child.value)
    return values


def _assignment_target_names(targets: list[ast.expr]) -> list[str]:
    names: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Tuple):
            names.extend(_assignment_target_names(list(target.elts)))
        elif isinstance(target, ast.Subscript):
            names.append(_node_name(target.value))
    return names


def _assignment_may_define_fields(target_name: str) -> bool:
    if not target_name:
        return False
    if any(token in target_name for token in NON_FIELD_TARGET_HINTS):
        return False
    return any(token in target_name for token in ("col", "field", "map", "rename", "group", "agg", "metric"))


def _looks_like_field_reference(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text or len(text) > 80 or "\n" in text:
        return False
    lowered = text.lower()
    if lowered in NON_FIELD_METHOD_NAMES:
        return False
    if lowered.startswith("#") or lowered.startswith("$") or re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        return False
    if any(part in lowered for part in (".png", ".jpg", ".csv", ".xlsx", ".html", "http://", "https://")):
        return False
    words = re.findall(r"[a-zA-Z0-9#?]+", lowered)
    if len(words) > 8:
        return False
    normalized = _normalize_field_name(text)
    if not normalized:
        return False
    return any(token in lowered or token in normalized for token in FIELD_TOKEN_HINTS)


def _normalize_field_name(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("#", "num")
    text = text.replace("?", " flag")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _field_input_family_hint(value: str) -> str:
    text = _normalize_field_name(value)
    tokens = set(text.split("_"))
    if any(token in text for token in ("mail", "resp", "response", "offer", "campaign", "wave", "control", "holdout")):
        return "campaign_history"
    if any(token in text for token in ("merchant", "mcc", "counterparty", "competitor", "category")):
        return "transactions|counterparty_taxonomy"
    if any(token in text for token in ("transaction", "txn", "amount", "spend", "swipe", "credit", "debit")):
        return "transactions"
    if tokens & {"pin", "sig"}:
        return "transactions"
    if any(token in text for token in ("balance", "bal")):
        return "balances"
    if any(token in text for token in ("product", "prod", "household", "member")):
        return "product_relationship"
    if any(token in text for token in ("branch", "account", "acct", "status", "stat", "business", "personal", "age", "opened", "closed")):
        return "accounts"
    if "payroll" in text:
        return "transactions|counterparty_taxonomy"
    return "unknown"


def _canonical_field_hint(value: str) -> str:
    text = _normalize_field_name(value)
    if text in {"acct_number", "acct", "account", "account_number", "primary_account_num"}:
        return "account_id"
    if "primary_account" in text or text.endswith("_account_num"):
        return "account_id"
    if "transaction_date" in text or text in {"date", "dt", "post_date"}:
        return "transaction_date"
    if "date_opened" in text or "open_date" in text or "opened_date" in text:
        return "date_opened"
    if "date_closed" in text or "close_date" in text or "closed_date" in text:
        return "date_closed"
    if text in {"amount", "amt", "transaction_amount"}:
        return "amount"
    if "merchant" in text:
        return "merchant_name"
    if "mcc" in text:
        return "mcc_code"
    if "transaction_type" in text or text in {"type", "txn_type"}:
        return "transaction_type"
    if "balance" in text or text.endswith("_bal") or "avg_bal" in text:
        return "avg_balance"
    if "branch" in text:
        return "branch_id"
    if "product" in text or "prod" in text:
        return "product_code"
    if "business" in text:
        return "business_flag"
    if "debit" in text:
        return "has_debit_or_debit_activity"
    if "mail" in text or "offer" in text or "response" in text or "resp" in text:
        return "campaign_history_field"
    if "payroll" in text:
        return "payroll_signal"
    if "competitor" in text:
        return "competitor_signal"
    if "status" in text or "stat" in text:
        return "status_code"
    if "age" in text:
        return "age_or_tenure"
    return ""


def _script_order(name: str) -> int | None:
    match = re.match(r"^(\d+)[_-]", name)
    return int(match.group(1)) if match else None


def _script_topic(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"^\d+[_-]", "", stem)
    return stem.replace("_", " ").strip() or stem


def _output_role(name: str, topic: str) -> str:
    text = f"{name} {topic}".lower()
    if any(term in text for term in ("config", "setup", "normalize", "helpers", "data", "build")):
        return "data_prep"
    if any(term in text for term in ("kpi", "scorecard", "dashboard", "summary")):
        return "kpi_or_summary"
    if any(term in text for term in ("trend", "migration", "lifecycle", "cohort", "retention", "survival")):
        return "trend_or_cohort"
    if any(term in text for term in ("action", "export", "list", "opportunity", "waterfall", "roadmap")):
        return "action_or_strategy"
    if any(term in text for term in ("bar", "donut", "heatmap", "scatter", "chart", "vis")):
        return "visual_evidence"
    return "analysis"


def _opportunity_types_for_section(section_id: str) -> list[str]:
    opportunities = {
        "payroll_conversion": ["txn.payroll", "txn.relationship", "txn.competition"],
        "debit_activation": ["ars.dctr", "txn.interchange", "txn.general"],
        "deposit_retention": ["txn.balance", "txn.competition", "txn.relationship"],
        "competitor_winback": ["txn.competition", "txn.financial_services"],
        "dormant_reactivation": ["txn.retention", "txn.engagement", "txn.attrition_txn"],
        "relationship_expansion": ["txn.relationship", "txn.financial_services"],
        "attrition_prevention": ["ars.attrition", "txn.attrition_txn", "txn.retention"],
    }
    return [opportunity for opportunity, sections in opportunities.items() if section_id in sections]


def _opportunity_contribution(opportunity_type: str, section_id: str) -> str:
    if opportunity_type == "payroll_conversion":
        return "Payroll, relationship, and competitor evidence used to identify primacy conversion candidates."
    if opportunity_type == "debit_activation":
        return "Debit penetration, card economics, and portfolio activity evidence used to rank activation targets."
    if opportunity_type == "deposit_retention":
        return "Balance, external FI, and relationship-depth evidence used to flag deposit flight risk."
    if opportunity_type == "competitor_winback":
        return "Competitor and financial-services leakage evidence used to prioritize consolidation plays."
    if opportunity_type == "dormant_reactivation":
        return "Retention and engagement migration evidence used to find accounts before full dormancy."
    if opportunity_type == "relationship_expansion":
        return "Relationship-depth and external-product evidence used for next-best-product outreach."
    if opportunity_type == "attrition_prevention":
        return "Attrition and retention evidence used to prioritize save outreach."
    return f"{section_id} supports {opportunity_type} scoring."


def _repo_root(repo_root: Path | str | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[4]


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def _section_catalog_columns() -> list[str]:
    return [
        "source_section_id",
        "product",
        "display_name",
        "folder",
        "source_path",
        "slide_code",
        "configured_module_count",
        "script_count",
        "runnable_script_count",
        "analysis_family",
        "intelligence_layers",
        "primary_engine_outputs",
        "supports_opportunity_types",
        "consulting_use",
        "script_files",
        "catalog_version",
    ]


def _script_catalog_columns() -> list[str]:
    return [
        "source_section_id",
        "product",
        "display_name",
        "folder",
        "script_order",
        "script_name",
        "source_path",
        "inferred_topic",
        "output_role",
        "runnable_flag",
        "catalog_version",
    ]


def _field_usage_catalog_columns() -> list[str]:
    return [
        "source_section_id",
        "product",
        "display_name",
        "folder",
        "script_name",
        "source_path",
        "line_number",
        "field_reference",
        "normalized_field",
        "input_family_hint",
        "canonical_field_hint",
        "evidence_context",
        "extraction_method",
        "catalog_version",
    ]


def _provenance_columns() -> list[str]:
    return [
        "opportunity_type",
        "source_section_id",
        "product",
        "display_name",
        "analysis_family",
        "intelligence_layers",
        "primary_engine_outputs",
        "script_count",
        "source_path",
        "contribution",
        "catalog_version",
    ]
