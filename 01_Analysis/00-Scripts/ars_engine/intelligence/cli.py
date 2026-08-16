"""CLI for the V1 transactional intelligence engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ars_engine.intelligence.intake import assemble_file_drop
from ars_engine.intelligence.engine import (
    EngineConfig,
    read_input_table,
    run_transactional_intelligence,
)
from ars_engine.intelligence.warehouse import write_snowflake_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the V1 Transactional Intelligence Engine on account and transaction files."
    )
    parser.add_argument("--accounts", type=Path, help="ODD/account file (.csv, .xlsx, .parquet)")
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Folder containing a monthly client file drop. The engine profiles files and selects usable inputs.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When used with --input-dir, discover files recursively.",
    )
    parser.add_argument(
        "--contract-dir",
        type=Path,
        help="Folder of YAML layout contracts to use instead of the default data_contracts directory.",
    )
    parser.add_argument(
        "--transactions",
        type=Path,
        action="append",
        default=[],
        help="Transaction file. Repeat for multiple monthly files.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--client-id", default="", help="Client id")
    parser.add_argument("--client-name", default="", help="Client name")
    parser.add_argument("--month", default="", help="Reporting month, YYYY.MM or YYYY-MM")
    parser.add_argument("--prior-campaign-targets", type=Path, help="Prior campaign_targets.csv for outcome measurement")
    parser.add_argument("--prior-measurement-baseline", type=Path, help="Prior measurement_baseline.csv for outcome measurement")
    parser.add_argument("--prior-package-dir", type=Path, help="Prior intelligence output folder for month-over-month delta reporting")
    parser.add_argument("--high-balance-threshold", type=float, default=5000.0)
    parser.add_argument("--interchange-rate", type=float, default=0.015)
    args = parser.parse_args(argv)

    discovered_files: list[Path] = []
    selected_account = None
    selected_transactions: list[Path] = []
    if args.input_dir:
        assembly = assemble_file_drop(args.input_dir, recursive=args.recursive, contract_dir=args.contract_dir)
        discovered_files = assembly.input_files
        selected_account = assembly.account_file
        selected_transactions = assembly.transaction_files
        print(
            "File-drop assembly selected "
            f"{1 if selected_account else 0} account file(s) and "
            f"{len(selected_transactions)} transaction file(s) from {len(discovered_files)} discovered file(s)."
        )

    account_path = args.accounts or selected_account
    transaction_paths = args.transactions or selected_transactions
    accounts = read_input_table(account_path) if account_path else None
    tx_frames = [read_input_table(path) for path in transaction_paths]
    transactions = pd.concat(tx_frames, ignore_index=True, sort=False) if tx_frames else None
    prior_campaign_targets = read_input_table(args.prior_campaign_targets) if args.prior_campaign_targets else None
    prior_measurement_baseline = read_input_table(args.prior_measurement_baseline) if args.prior_measurement_baseline else None
    prior_account_intelligence_profile = _optional_prior_table(args.prior_package_dir, "account_intelligence_profile.csv")
    prior_opportunities = _optional_prior_table(args.prior_package_dir, "opportunities.csv")
    prior_opportunity_portfolio = _optional_prior_table(args.prior_package_dir, "opportunity_portfolio.csv")
    prior_data_quality = _optional_prior_json(args.prior_package_dir, "data_quality.json")
    if args.prior_package_dir:
        if prior_campaign_targets is None:
            prior_campaign_targets = _optional_prior_table(args.prior_package_dir, "campaign_targets.csv")
        if prior_measurement_baseline is None:
            prior_measurement_baseline = _optional_prior_table(args.prior_package_dir, "measurement_baseline.csv")
    input_files = _unique_paths([*discovered_files, *[path for path in [account_path, *transaction_paths] if path is not None]])
    config = EngineConfig(
        client_id=args.client_id,
        client_name=args.client_name,
        period_month=args.month or None,
        high_balance_threshold=args.high_balance_threshold,
        interchange_rate=args.interchange_rate,
    )
    outputs = run_transactional_intelligence(
        accounts=accounts,
        transactions=transactions,
        input_files=input_files,
        contract_dir=args.contract_dir,
        prior_campaign_targets=prior_campaign_targets,
        prior_measurement_baseline=prior_measurement_baseline,
        prior_account_intelligence_profile=prior_account_intelligence_profile,
        prior_opportunities=prior_opportunities,
        prior_opportunity_portfolio=prior_opportunity_portfolio,
        prior_data_quality=prior_data_quality,
        config=config,
    )
    written = outputs.write(args.output)
    written.update(write_snowflake_package(outputs, args.output, config=config, artifact_paths=written))
    print(f"Transactional Intelligence Engine wrote {len(written)} artifacts to {args.output}")
    for name, path in written.items():
        print(f"  {name}: {path}")
    return 0


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(Path(path).resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(Path(path))
    return unique


def _optional_prior_table(prior_dir: Path | None, filename: str) -> pd.DataFrame | None:
    if not prior_dir:
        return None
    path = prior_dir / filename
    if not path.exists():
        return None
    return read_input_table(path)


def _optional_prior_json(prior_dir: Path | None, filename: str) -> dict | None:
    if not prior_dir:
        return None
    path = prior_dir / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
