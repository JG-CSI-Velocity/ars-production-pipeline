"""CLI for the parity harness.

    python -m ars_parity capture --run-dir <dir> --client 1759 --month 2026.06 \
        --product ars --label golden
    python -m ars_parity check --client 1759 --month 2026.06 --product ars \
        [--prefix TXN-MERCH-] [--section txn.merchant]
    python -m ars_parity approve --section txn.merchant --by JG
    python -m ars_parity status

`capture` snapshots a completed run's artifacts. Run it once against the OLD
engine's output (--label golden), then against the NEW engine's output for
the same client/month (--label candidate). `check` diffs the two and records
the result against --section when given.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ars_engine.core.config import EngineConfig

from ars_parity import signoff
from ars_parity.capture import capture_run, load_snapshot, save_snapshot, snapshot_root
from ars_parity.compare import ComparePolicy, compare_snapshots, summarize


def _default_run_dir(client: str, month: str) -> Path | None:
    """Locate the completed-analysis dir for client/month via engine config."""
    cfg = EngineConfig.load()
    base = cfg.paths.analysis_dir
    if base is None or not base.exists():
        return None
    # Layout: 01_Completed_Analysis/<CSM>/<month>/<client>/
    matches = sorted(base.glob(f"*/{month}/{client}"))
    return matches[0] if matches else None


def cmd_capture(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir) if args.run_dir else _default_run_dir(args.client, args.month)
    if run_dir is None or not run_dir.exists():
        print(f"ERROR: run dir not found (pass --run-dir); tried {run_dir}")
        return 2
    snap = capture_run(run_dir, args.client, args.month, args.product, args.label)
    dest = save_snapshot(snap)
    print(
        f"captured {args.label}: {len(snap.slides)} slides, {len(snap.sheets)} sheets, "
        f"{len(snap.figures)} figures -> {dest}"
    )
    if not snap.figures:
        print(
            "NOTE: no figure data found. For chart-only parity, re-run the legacy "
            "pipeline with ARS_PARITY_CAPTURE=1 so ChartCapture dumps *.figdata.json."
        )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    g_dir = snapshot_root(args.client, args.month, args.product, "golden")
    c_dir = snapshot_root(args.client, args.month, args.product, "candidate")
    for d, label in ((g_dir, "golden"), (c_dir, "candidate")):
        if not (d / "meta.json").exists():
            print(f"ERROR: no {label} snapshot at {d} -- run capture first")
            return 2
    golden, candidate = load_snapshot(g_dir), load_snapshot(c_dir)

    overrides: dict = {}
    if args.tolerances and Path(args.tolerances).exists():
        overrides = json.loads(Path(args.tolerances).read_text(encoding="utf-8"))
    policy = ComparePolicy(
        rtol=args.rtol,
        column_overrides=overrides,
        slide_prefixes=tuple(args.prefix or ()),
    )
    diffs = compare_snapshots(golden, candidate, policy)
    print(summarize(diffs))

    if args.section:
        signoff.record_check(
            args.section, args.client, args.month,
            passed=not diffs, diff_count=len(diffs),
            divergence_reason=args.divergence_reason, divergence_by=args.divergence_by,
        )
        print(
            f"recorded check for {args.section}: "
            f"passing clients = {signoff.passing_clients(args.section) or 'none'}"
        )
    return 0 if not diffs else 1


def cmd_approve(args: argparse.Namespace) -> int:
    try:
        entry = signoff.approve(args.section, args.by)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"approved {args.section} by {args.by} at {entry['approved_at']}")
    print("next: set the section to \"new\" in 03_Config/engine_flags.json")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    status = signoff.load_status()
    if not status:
        print("no parity checks recorded yet")
        return 0
    for section_id in sorted(status):
        entry = status[section_id]
        ok = signoff.passing_clients(section_id)
        mark = "APPROVED" if entry.get("approved_by") else (
            "ready-for-approval" if len(ok) >= signoff.MIN_CLIENTS_FOR_APPROVAL else "in-progress"
        )
        print(f"{section_id:28s} {mark:20s} passing={ok}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ars_parity")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("capture", help="snapshot a completed run's artifacts")
    p.add_argument("--run-dir", help="run output dir (default: resolve via config)")
    p.add_argument("--client", required=True)
    p.add_argument("--month", required=True)
    p.add_argument("--product", default="ars", choices=["ars", "txn"])
    p.add_argument("--label", default="golden", choices=["golden", "candidate"])
    p.set_defaults(fn=cmd_capture)

    p = sub.add_parser("check", help="diff candidate snapshot against golden")
    p.add_argument("--client", required=True)
    p.add_argument("--month", required=True)
    p.add_argument("--product", default="ars", choices=["ars", "txn"])
    p.add_argument("--prefix", action="append", help="slide-id prefix filter (repeatable)")
    p.add_argument("--section", help="section_id to record the result against")
    p.add_argument("--rtol", type=float, default=1e-9)
    p.add_argument("--tolerances", help="JSON file of per-sheet/column rtol overrides")
    p.add_argument("--divergence-reason",
                   help="accept a failing check because the LEGACY number is wrong (document why)")
    p.add_argument("--divergence-by", help="who signed off on the divergence")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("approve", help="approve a section for cutover")
    p.add_argument("--section", required=True)
    p.add_argument("--by", required=True)
    p.set_defaults(fn=cmd_approve)

    p = sub.add_parser("status", help="show parity status for all sections")
    p.set_defaults(fn=cmd_status)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
