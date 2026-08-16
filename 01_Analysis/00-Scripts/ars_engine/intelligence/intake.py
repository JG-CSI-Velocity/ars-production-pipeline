"""File-drop profiling and contract matching for intelligence runs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import fnmatch
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd
import yaml


TEXT_SUFFIXES = {".csv", ".txt", ".dat", ""}
EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xls"}
PARQUET_SUFFIXES = {".parquet"}
SUPPORTED_INPUT_SUFFIXES = TEXT_SUFFIXES | EXCEL_SUFFIXES | PARQUET_SUFFIXES


@dataclass(frozen=True)
class ContractMatch:
    contract_id: str
    display_name: str
    source_family: str
    score: float
    matched_fields: list[str]
    missing_required_fields: list[str]


@dataclass(frozen=True)
class FileDropAssembly:
    """Selected files and review tables for one client/month file drop."""

    input_files: list[Path]
    account_file: Path | None
    transaction_files: list[Path]
    supporting_files: list[Path]
    profile: list[dict[str, Any]]
    work_order: pd.DataFrame
    assembly_plan: pd.DataFrame
    layout_gap_report: pd.DataFrame = field(default_factory=pd.DataFrame)


def discover_input_files(input_dir: Path | str, *, recursive: bool = False) -> list[Path]:
    """Discover supported files in a monthly client file drop."""
    root = Path(input_dir)
    if not root.exists():
        return []
    pattern = "**/*" if recursive else "*"
    files: list[Path] = []
    for path in root.glob(pattern):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.name.startswith("~$"):
            continue
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_INPUT_SUFFIXES:
            files.append(path)
    return sorted(files, key=lambda item: str(item).lower())


def assemble_file_drop(
    input_dir: Path | str,
    *,
    recursive: bool = False,
    contract_dir: Path | str | None = None,
) -> FileDropAssembly:
    """Profile a folder and select account/transaction files for analysis."""
    input_files = discover_input_files(input_dir, recursive=recursive)
    profile = profile_input_files(input_files, contract_dir=contract_dir)
    work_order = build_intake_work_order(profile)
    assembly_plan = build_file_assembly_plan(work_order)
    layout_gap_report = build_layout_gap_report(profile, contract_dir=contract_dir)
    account_file = _selected_path(assembly_plan, "selected_account")
    transaction_files = _selected_paths(assembly_plan, "selected_transaction")
    supporting_files = _selected_paths(assembly_plan, "supporting")
    return FileDropAssembly(
        input_files=input_files,
        account_file=account_file,
        transaction_files=transaction_files,
        supporting_files=supporting_files,
        profile=profile,
        work_order=work_order,
        assembly_plan=assembly_plan,
        layout_gap_report=layout_gap_report,
    )


def profile_input_files(
    paths: Iterable[Path | str],
    *,
    contract_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Profile file-drop inputs and match them to known layout contracts."""
    contracts = load_layout_contracts(contract_dir)
    profiles = []
    for raw in paths:
        path = Path(raw)
        profile = _profile_one_file(path)
        match = best_contract_match(profile, contracts)
        if match:
            profile["contract_match"] = {
                "contract_id": match.contract_id,
                "display_name": match.display_name,
                "source_family": match.source_family,
                "score": match.score,
                "matched_fields": match.matched_fields,
                "missing_required_fields": match.missing_required_fields,
                "status": "matched" if match.score >= 0.60 else "candidate",
            }
        else:
            profile["contract_match"] = {
                "contract_id": "",
                "display_name": "",
                "source_family": "unknown",
                "score": 0.0,
                "matched_fields": [],
                "missing_required_fields": [],
                "status": "unmatched",
            }
        profiles.append(profile)
    return profiles


def build_intake_work_order(profile: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert file profiles into operator actions before analysis trust review."""
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(profile, start=1):
        match = item.get("contract_match") or {}
        warnings = item.get("profile_warnings") or []
        status = str(match.get("status") or "unmatched")
        source_family = str(match.get("source_family") or "unknown")
        missing = match.get("missing_required_fields") or []
        decision, action, role, load_target, severity = _intake_decision(
            exists=bool(item.get("exists")),
            status=status,
            source_family=source_family,
            missing_required=missing,
            warnings=warnings,
        )
        rows.append(
            {
                "priority_rank": index,
                "file_name": item.get("file_name", ""),
                "source_path": item.get("source_path", ""),
                "detected_format": item.get("detected_format", ""),
                "delimiter": item.get("delimiter", ""),
                "estimated_rows": item.get("estimated_rows", 0),
                "source_family": source_family,
                "contract_id": match.get("contract_id", ""),
                "match_status": status,
                "match_score": match.get("score", 0.0),
                "intake_decision": decision,
                "severity": severity,
                "assigned_role": role,
                "operator_action": action,
                "load_target": load_target,
                "matched_fields": "|".join(match.get("matched_fields") or []),
                "missing_required_fields": "|".join(missing),
                "profile_warnings": "|".join(str(warning) for warning in warnings),
            }
        )
    if not rows:
        return _empty_intake_work_order()
    return pd.DataFrame(rows).sort_values(
        ["severity", "match_score", "estimated_rows"],
        ascending=[False, True, False],
    ).reset_index(drop=True)


def build_file_assembly_plan(work_order: pd.DataFrame) -> pd.DataFrame:
    """Describe which profiled files are loaded, skipped, or held for review."""
    if work_order is None or work_order.empty:
        return _empty_file_assembly_plan()

    df = work_order.copy().reset_index(drop=True)
    account_candidates = df[df["intake_decision"].eq("use_as_account_file")].copy()
    selected_account_path = ""
    if not account_candidates.empty:
        best = account_candidates.sort_values(
            ["match_score", "estimated_rows", "file_name"],
            ascending=[False, False, True],
        ).iloc[0]
        selected_account_path = str(best.get("source_path", ""))

    rows: list[dict[str, Any]] = []
    selected_transaction_count = int(df["intake_decision"].eq("use_as_transaction_file").sum())
    for item in df.to_dict("records"):
        decision = str(item.get("intake_decision", ""))
        source_path = str(item.get("source_path", ""))
        source_family = str(item.get("source_family", "unknown"))
        assembly_role, load_flag, reason = _assembly_decision(
            decision=decision,
            source_path=source_path,
            selected_account_path=selected_account_path,
        )
        rows.append(
            {
                "file_name": item.get("file_name", ""),
                "source_path": source_path,
                "source_family": source_family,
                "contract_id": item.get("contract_id", ""),
                "match_status": item.get("match_status", ""),
                "match_score": item.get("match_score", 0.0),
                "estimated_rows": item.get("estimated_rows", 0),
                "intake_decision": decision,
                "assembly_role": assembly_role,
                "load_flag": load_flag,
                "load_order": _assembly_order(assembly_role),
                "assembly_reason": reason,
                "target_engine_input": _target_engine_input(assembly_role),
                "target_snowflake_layer": item.get("load_target", ""),
                "selected_account_file": selected_account_path,
                "selected_transaction_file_count": selected_transaction_count,
                "operator_action": item.get("operator_action", ""),
                "model_version": "file_assembly_v0_rules",
            }
        )
    return pd.DataFrame(rows, columns=_file_assembly_plan_columns()).sort_values(
        ["load_order", "match_score", "estimated_rows"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


def build_layout_gap_report(
    profile: list[dict[str, Any]],
    *,
    contract_dir: Path | str | None = None,
) -> pd.DataFrame:
    """Create a field-level contract gap report for profiled input files."""
    if not profile:
        return _empty_layout_gap_report()

    contracts = {str(contract.get("contract_id") or ""): contract for contract in load_layout_contracts(contract_dir)}
    rows: list[dict[str, Any]] = []
    for item in profile:
        match = item.get("contract_match") or {}
        contract_id = str(match.get("contract_id") or "")
        contract = contracts.get(contract_id)
        base = {
            "file_name": item.get("file_name", ""),
            "source_path": item.get("source_path", ""),
            "source_family": match.get("source_family", "unknown"),
            "contract_id": contract_id,
            "match_status": match.get("status", "unmatched"),
            "match_score": match.get("score", 0.0),
            "sample_headers": _sample_headers(item),
            "model_version": "layout_gap_v0_rules",
        }

        if not contract:
            rows.append(
                {
                    **base,
                    "canonical_field": "",
                    "required_flag": False,
                    "data_type": "",
                    "mapping_status": "contract_needed",
                    "suggested_source_column": "",
                    "suggested_source_position": pd.NA,
                    "confidence": 0.0,
                    "remediation_action": "Create or select a layout contract before loading this file.",
                }
            )
            continue

        for canonical, spec in (contract.get("canonical_fields") or {}).items():
            mapping = _suggest_field_mapping(item, str(canonical), spec or {}, contract)
            required = bool((spec or {}).get("required"))
            if mapping["confidence"] > 0:
                status = "matched"
                action = "Use mapped source field."
            elif required:
                status = "missing_required"
                action = "Map or request required field before loading this file."
            else:
                status = "missing_optional"
                action = "Leave null for V1 or map when the source provides it."
            rows.append(
                {
                    **base,
                    "canonical_field": canonical,
                    "required_flag": required,
                    "data_type": (spec or {}).get("type", ""),
                    "mapping_status": status,
                    "suggested_source_column": mapping["source_column"],
                    "suggested_source_position": mapping["source_position"],
                    "confidence": mapping["confidence"],
                    "remediation_action": action,
                }
            )

    if not rows:
        return _empty_layout_gap_report()
    return pd.DataFrame(rows, columns=_layout_gap_report_columns()).sort_values(
        ["file_name", "required_flag", "mapping_status", "canonical_field"],
        ascending=[True, False, True, True],
    ).reset_index(drop=True)


def summarize_intake_work_order(work_order: pd.DataFrame) -> dict[str, Any]:
    """Create a compact readiness summary from an intake work order."""
    if work_order is None or work_order.empty:
        return {
            "file_count": 0,
            "usable_files": 0,
            "mapping_needed_files": 0,
            "blocking_files": 0,
            "transaction_files": 0,
            "account_files": 0,
            "readiness_status": "no_files_profiled",
        }
    decisions = work_order["intake_decision"].astype(str)
    families = work_order["source_family"].astype(str)
    blocking = int(decisions.isin({"replace_file", "map_required_fields"}).sum())
    mapping_needed = int(decisions.isin({"map_required_fields", "create_or_update_layout_contract"}).sum())
    usable = int(decisions.isin({"use_as_account_file", "use_as_transaction_file", "use_as_supporting_file"}).sum())
    return {
        "file_count": int(len(work_order)),
        "usable_files": usable,
        "mapping_needed_files": mapping_needed,
        "blocking_files": blocking,
        "transaction_files": int(families.eq("transaction").sum()),
        "account_files": int(families.isin({"odd", "account"}).sum()),
        "unmatched_files": int(decisions.eq("create_or_update_layout_contract").sum()),
        "readiness_status": "ready" if blocking == 0 and usable > 0 else "needs_intake_review",
    }


def summarize_file_assembly_plan(assembly_plan: pd.DataFrame) -> dict[str, Any]:
    """Create compact counts from a file assembly plan."""
    if assembly_plan is None or assembly_plan.empty:
        return {
            "selected_account_files": 0,
            "selected_transaction_files": 0,
            "supporting_files": 0,
            "held_files": 0,
            "assembly_status": "no_files_selected",
        }
    roles = assembly_plan["assembly_role"].astype(str)
    selected_accounts = int(roles.eq("selected_account").sum())
    selected_transactions = int(roles.eq("selected_transaction").sum())
    held_files = int(roles.isin({"needs_mapping", "needs_replacement", "not_loaded", "duplicate_account"}).sum())
    return {
        "selected_account_files": selected_accounts,
        "selected_transaction_files": selected_transactions,
        "supporting_files": int(roles.eq("supporting").sum()),
        "held_files": held_files,
        "assembly_status": "ready" if (selected_accounts or selected_transactions) and held_files == 0 else "needs_review",
    }


def summarize_layout_gap_report(layout_gap_report: pd.DataFrame) -> dict[str, Any]:
    """Create compact layout remediation counts from the field-level report."""
    if layout_gap_report is None or layout_gap_report.empty:
        return {
            "layout_missing_required_fields": 0,
            "layout_files_with_missing_required": 0,
            "layout_contract_needed_files": 0,
            "layout_ready_fields": 0,
            "layout_status": "no_layouts_profiled",
        }
    statuses = layout_gap_report["mapping_status"].astype(str)
    missing_required = int(statuses.eq("missing_required").sum())
    files_with_missing = int(
        layout_gap_report.loc[statuses.eq("missing_required"), "source_path"].dropna().astype(str).nunique()
    )
    contract_needed = int(
        layout_gap_report.loc[statuses.eq("contract_needed"), "source_path"].dropna().astype(str).nunique()
    )
    return {
        "layout_missing_required_fields": missing_required,
        "layout_files_with_missing_required": files_with_missing,
        "layout_contract_needed_files": contract_needed,
        "layout_ready_fields": int(statuses.eq("matched").sum()),
        "layout_status": "ready" if missing_required == 0 and contract_needed == 0 else "needs_mapping",
    }


def write_intake_profile(profile: list[dict[str, Any]], output_dir: Path | str) -> Path:
    """Persist the file-drop profile for analyst and data-team review."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "intake_profile.json"
    path.write_text(json.dumps(profile, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def _intake_decision(
    *,
    exists: bool,
    status: str,
    source_family: str,
    missing_required: list[Any],
    warnings: list[Any],
) -> tuple[str, str, str, str, int]:
    if not exists or any(str(warning).startswith("profile_error") for warning in warnings):
        return (
            "replace_file",
            "Replace or repair the source file before this run is trusted.",
            "Analyst",
            "",
            4,
        )
    if "unsupported_suffix" in warnings:
        return (
            "create_or_update_layout_contract",
            "Confirm whether this file should feed the engine, then add a layout contract or mark it supporting-only.",
            "Data / analyst",
            "",
            3,
        )
    if missing_required and status == "matched":
        return (
            "map_required_fields",
            "Map the missing required field(s) or request a corrected extract from the client.",
            "Data / analyst",
            "",
            4,
        )
    if status == "matched":
        if source_family == "transaction":
            return (
                "use_as_transaction_file",
                "Load into the transaction feature build for this period.",
                "Engine",
                "raw.transactions",
                1,
            )
        if source_family in {"odd", "account"}:
            return (
                "use_as_account_file",
                "Load as the account/ODD input for relationship and eligibility features.",
                "Engine",
                "raw.accounts",
                1,
            )
        return (
            "use_as_supporting_file",
            "Keep as a supporting source with lineage; review before adding it to scoring.",
            "Analyst",
            "raw.supporting_files",
            1,
        )
    if status == "candidate":
        return (
            "confirm_candidate_layout",
            "Review the candidate layout match before using this file in scoring.",
            "Data / analyst",
            "",
            2,
        )
    return (
        "create_or_update_layout_contract",
        "Create a layout contract, map this extract to ODD/transaction fields, or mark it out of scope.",
        "Data / analyst",
        "",
        3,
    )


def _empty_intake_work_order() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "priority_rank",
            "file_name",
            "source_path",
            "detected_format",
            "delimiter",
            "estimated_rows",
            "source_family",
            "contract_id",
            "match_status",
            "match_score",
            "intake_decision",
            "severity",
            "assigned_role",
            "operator_action",
            "load_target",
            "matched_fields",
            "missing_required_fields",
            "profile_warnings",
        ]
    )


def _empty_file_assembly_plan() -> pd.DataFrame:
    return pd.DataFrame(columns=_file_assembly_plan_columns())


def _empty_layout_gap_report() -> pd.DataFrame:
    return pd.DataFrame(columns=_layout_gap_report_columns())


def _file_assembly_plan_columns() -> list[str]:
    return [
        "file_name",
        "source_path",
        "source_family",
        "contract_id",
        "match_status",
        "match_score",
        "estimated_rows",
        "intake_decision",
        "assembly_role",
        "load_flag",
        "load_order",
        "assembly_reason",
        "target_engine_input",
        "target_snowflake_layer",
        "selected_account_file",
        "selected_transaction_file_count",
        "operator_action",
        "model_version",
    ]


def _layout_gap_report_columns() -> list[str]:
    return [
        "file_name",
        "source_path",
        "source_family",
        "contract_id",
        "match_status",
        "match_score",
        "canonical_field",
        "required_flag",
        "data_type",
        "mapping_status",
        "suggested_source_column",
        "suggested_source_position",
        "confidence",
        "remediation_action",
        "sample_headers",
        "model_version",
    ]


def _suggest_field_mapping(
    profile: dict[str, Any],
    canonical: str,
    spec: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    headers = [str(col).strip() for col in profile.get("header_columns") or []]
    aliases = [canonical, *(spec.get("aliases") or [])]
    for alias in aliases:
        source_column, position = _matched_header(headers, alias)
        if source_column:
            return {
                "source_column": source_column,
                "source_position": position,
                "confidence": 1.0,
            }

    for pattern in spec.get("pattern_aliases") or []:
        source_column, position = _matched_pattern(headers, str(pattern))
        if source_column:
            return {
                "source_column": source_column,
                "source_position": position,
                "confidence": 0.9,
            }

    source_position = spec.get("source_position")
    if (
        bool(contract.get("match", {}).get("positional"))
        and profile.get("header_mode") == "positional"
        and source_position is not None
        and int(source_position) < int(profile.get("column_count") or 0)
    ):
        return {
            "source_column": f"position_{int(source_position)}",
            "source_position": int(source_position),
            "confidence": 0.75,
        }

    return {
        "source_column": "",
        "source_position": pd.NA,
        "confidence": 0.0,
    }


def _matched_header(headers: list[str], alias: str) -> tuple[str, int | Any]:
    normalized = _norm(alias)
    for index, header in enumerate(headers):
        if _norm(header) == normalized:
            return header, index
    return "", pd.NA


def _matched_pattern(headers: list[str], pattern: str) -> tuple[str, int | Any]:
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return "", pd.NA
    for index, header in enumerate(headers):
        if regex.search(header):
            return header, index
    return "", pd.NA


def _sample_headers(profile: dict[str, Any]) -> str:
    headers = [str(col).strip() for col in profile.get("header_columns") or []]
    if headers:
        suffix = "|..." if len(headers) > 12 else ""
        return "|".join(headers[:12]) + suffix
    return f"positional_columns={int(profile.get('column_count') or 0)}"


def _assembly_decision(
    *,
    decision: str,
    source_path: str,
    selected_account_path: str,
) -> tuple[str, bool, str]:
    if decision == "use_as_account_file":
        if source_path == selected_account_path:
            return "selected_account", True, "Best matched account/ODD file selected for account dimensions."
        return "duplicate_account", False, "Another account/ODD file scored higher and was selected."
    if decision == "use_as_transaction_file":
        return "selected_transaction", True, "Matched transaction file selected for transaction feature build."
    if decision == "use_as_supporting_file":
        return "supporting", False, "Supporting file retained for lineage but not used in V1 scoring."
    if decision == "map_required_fields":
        return "needs_mapping", False, "Required fields are missing; map layout before loading."
    if decision == "replace_file":
        return "needs_replacement", False, "File is missing, unreadable, or damaged."
    return "not_loaded", False, "Layout is not confirmed for V1 scoring."


def _assembly_order(role: str) -> int:
    order = {
        "selected_account": 1,
        "selected_transaction": 2,
        "supporting": 3,
        "duplicate_account": 4,
        "needs_mapping": 5,
        "needs_replacement": 6,
        "not_loaded": 7,
    }
    return order.get(role, 99)


def _target_engine_input(role: str) -> str:
    if role == "selected_account":
        return "accounts"
    if role == "selected_transaction":
        return "transactions"
    return ""


def _selected_path(assembly_plan: pd.DataFrame, role: str) -> Path | None:
    paths = _selected_paths(assembly_plan, role)
    return paths[0] if paths else None


def _selected_paths(assembly_plan: pd.DataFrame, role: str) -> list[Path]:
    if assembly_plan is None or assembly_plan.empty:
        return []
    rows = assembly_plan[assembly_plan["assembly_role"].eq(role)]
    return [Path(value) for value in rows["source_path"].dropna().astype(str) if value]


def load_layout_contracts(contract_dir: Path | str | None = None) -> list[dict[str, Any]]:
    """Load YAML contracts from data_contracts/."""
    root = Path(contract_dir) if contract_dir else _default_contract_dir()
    if not root or not root.exists():
        return []
    contracts: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if isinstance(data, dict) and data.get("contract_id") and data.get("match") and data.get("canonical_fields"):
            data["_contract_path"] = str(path)
            contracts.append(data)
    return contracts


def best_contract_match(profile: dict[str, Any], contracts: list[dict[str, Any]]) -> ContractMatch | None:
    """Return the strongest contract match for a profiled file."""
    if not contracts:
        return None
    scored = [_score_contract(profile, contract) for contract in contracts]
    scored = [match for match in scored if match.score > 0]
    if not scored:
        return None
    return sorted(scored, key=lambda item: item.score, reverse=True)[0]


def _profile_one_file(path: Path) -> dict[str, Any]:
    exists = path.exists()
    suffix = path.suffix.lower()
    stat = path.stat() if exists else None
    profile: dict[str, Any] = {
        "source_path": str(path),
        "file_name": path.name,
        "suffix": suffix,
        "exists": exists,
        "size_bytes": int(stat.st_size) if stat else 0,
        "sha256": _hash_file(path) if exists and path.is_file() else "",
        "detected_format": _detected_format(path),
        "delimiter": "",
        "header_columns": [],
        "column_count": 0,
        "estimated_rows": 0,
        "profile_warnings": [],
    }
    if not exists or not path.is_file():
        profile["profile_warnings"].append("file_missing")
        return profile
    try:
        if suffix in TEXT_SUFFIXES:
            _profile_text_file(path, profile)
        elif suffix in EXCEL_SUFFIXES:
            _profile_excel_file(path, profile)
        elif suffix in PARQUET_SUFFIXES:
            _profile_parquet_file(path, profile)
        else:
            profile["profile_warnings"].append("unsupported_suffix")
    except Exception as exc:
        profile["profile_warnings"].append(f"profile_error:{exc}")
    return profile


def _profile_text_file(path: Path, profile: dict[str, Any]) -> None:
    sample = path.read_text(encoding="utf-8", errors="replace")[:65536]
    if not sample.strip():
        profile["profile_warnings"].append("empty_file")
        return
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|;")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = "," if "," in sample else "\t" if "\t" in sample else "|"
    profile["delimiter"] = {
        "\t": "tab",
        ",": "comma",
        "|": "pipe",
        ";": "semicolon",
    }.get(delimiter, delimiter)

    reader = csv.reader(sample.splitlines(), delimiter=delimiter)
    rows = [row for _, row in zip(range(10), reader)]
    if not rows:
        return
    first = [str(col).strip() for col in rows[0]]
    has_header = _looks_like_header(first)
    profile["header_columns"] = first if has_header else []
    profile["column_count"] = len(first) if has_header else max(len(row) for row in rows)
    profile["header_mode"] = "header_row" if has_header else "positional"
    profile["estimated_rows"] = max(_count_lines(path) - (1 if has_header else 0), 0)


def _profile_excel_file(path: Path, profile: dict[str, Any]) -> None:
    df = pd.read_excel(path, nrows=25)
    profile["header_columns"] = [str(col).strip() for col in df.columns]
    profile["column_count"] = len(df.columns)
    profile["header_mode"] = "header_row"
    profile["estimated_rows"] = len(pd.read_excel(path, usecols=[0]))


def _profile_parquet_file(path: Path, profile: dict[str, Any]) -> None:
    df = pd.read_parquet(path)
    profile["header_columns"] = [str(col).strip() for col in df.columns]
    profile["column_count"] = len(df.columns)
    profile["header_mode"] = "header_row"
    profile["estimated_rows"] = len(df)


def _score_contract(profile: dict[str, Any], contract: dict[str, Any]) -> ContractMatch:
    match_cfg = contract.get("match") or {}
    fields = contract.get("canonical_fields") or {}
    filename = profile.get("file_name", "")
    suffix = str(profile.get("suffix") or "").lower().lstrip(".") or "none"
    headers = {_norm(col) for col in profile.get("header_columns") or []}

    filename_hit = any(fnmatch.fnmatch(filename.lower(), pattern.lower()) for pattern in match_cfg.get("filename_patterns", []))
    extension_hit = suffix in {str(ext).lower().lstrip(".") for ext in match_cfg.get("extensions", [])}

    matched_fields = []
    missing_required = []
    for canonical, spec in fields.items():
        aliases = [canonical, *(spec.get("aliases") or [])]
        patterns = spec.get("pattern_aliases") or []
        alias_hit = any(_norm(alias) in headers for alias in aliases)
        pattern_hit = any(_pattern_matches(pattern, profile.get("header_columns") or []) for pattern in patterns)
        positional_hit = (
            bool(contract.get("match", {}).get("positional"))
            and profile.get("header_mode") == "positional"
            and spec.get("source_position") is not None
            and (
            int(spec.get("source_position") or 0) < int(profile.get("column_count") or 0)
            )
        )
        if alias_hit or pattern_hit or positional_hit:
            matched_fields.append(canonical)
        elif spec.get("required"):
            missing_required.append(canonical)

    required_total = max(sum(1 for spec in fields.values() if spec.get("required")), 1)
    required_matched = required_total - len(missing_required)
    required_score = required_matched / required_total
    field_score = len(matched_fields) / max(len(fields), 1)
    score = (
        (0.25 if filename_hit else 0.0)
        + (0.10 if extension_hit else 0.0)
        + (0.40 * required_score)
        + (0.25 * field_score)
    )
    if missing_required:
        score = min(score, 0.79)
    return ContractMatch(
        contract_id=contract.get("contract_id", ""),
        display_name=contract.get("display_name", ""),
        source_family=contract.get("source_family", "unknown"),
        score=round(score, 3),
        matched_fields=sorted(matched_fields),
        missing_required_fields=sorted(missing_required),
    )


def _detected_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in EXCEL_SUFFIXES:
        return "excel"
    if suffix in PARQUET_SUFFIXES:
        return "parquet"
    if suffix in TEXT_SUFFIXES:
        return "text"
    return "unknown"


def _looks_like_header(values: list[str]) -> bool:
    if len(values) < 2:
        return False
    alpha = sum(bool(re.search(r"[A-Za-z]", value)) for value in values)
    numeric = sum(bool(re.fullmatch(r"[-+]?[\d,.]+", value.strip())) for value in values)
    return alpha >= max(1, len(values) // 2) and numeric <= len(values) // 3


def _count_lines(path: Path) -> int:
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pattern_matches(pattern: str, headers: list[str]) -> bool:
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return False
    return any(regex.search(str(header)) for header in headers)


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _default_contract_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data_contracts"
        if candidate.exists():
            return candidate
    return here.parents[4] / "data_contracts"
