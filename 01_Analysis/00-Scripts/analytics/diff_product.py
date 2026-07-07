"""Equivalence diff: exec product/ cells  vs  the transaction.product module.

The safety net for the exec->module migration. Runs BOTH paths on the same real
data and compares the numbers (not the rendered PNGs -- matplotlib pixels won't
match; the aggregations must):

    Path B (new): ProductAnalysis().run(ctx) reading ctx.txn
    Path A (old): the exec product/ cells via TXNSectionWrapper, reading the
                  shared namespace

Both derive from a single step_txn_load(ctx), so they start from identical data.
Identical numbers => the migration is validated and the exec cells can be retired
(a later, operator-gated step). Divergence => a real bug to fix before retiring
anything.

This only runs where the TXN files live (the work machine / M:\\ARS). Usage:

    python -m ars_analysis.analytics.diff_product \\
        --csm JSMITH --month 2025.01 --client 12345 \\
        --odd "M:\\...\\formatted_odd.xlsx" --output-dir "M:\\...\\out"

Exit code 0 = PASS (numbers identical within tolerance), 1 = FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# --- numeric columns compared per table --------------------------------------
_AGG_COLS = ["txn_count", "unique_accounts", "total_spend", "avg_spend",
             "median_spend", "txn_pct", "spend_pct", "acct_pct", "txn_per_account"]
_MONTHLY_COLS = ["txn_count", "month_total", "share_pct"]
_TOL = 1e-6  # relative+absolute tolerance for float compares


def _build_shared_ctx(args):
    """Build the shared PipelineContext exactly as 01_Analysis/run.py does."""
    from shared.context import PipelineContext

    y, m = args.month.split(".")
    analysis_date = datetime(int(y), int(m), 1).date()
    out = Path(args.output_dir) if args.output_dir else Path("diff_out")
    out.mkdir(parents=True, exist_ok=True)

    ctx = PipelineContext(
        client_id=args.client,
        client_name=args.client_name or args.client,
        csm=args.csm,
        analysis_date=analysis_date,
        output_dir=out,
        input_files={"oddd": str(Path(args.odd))} if args.odd else {},
        client_config={"config_path": args.config or "", "client_id": args.client},
    )
    ctx.compute_l12m_window()
    return ctx


def _run_new(ars_ctx):
    """Path B -- new module. Returns (prod_agg, prod_monthly, total_accts_prod)."""
    from ars_analysis.analytics.transaction.product import ProductAnalysis

    ProductAnalysis().run(ars_ctx)
    bucket = ars_ctx.results.get("transaction.product", {})
    tables = bucket.get("tables", {})
    ins = bucket.get("insights", {})
    return (
        tables.get("prod_agg", pd.DataFrame()),
        tables.get("prod_monthly", pd.DataFrame()),
        int(ins.get("total_accts_prod", 0)),
    )


def _run_old(ars_ctx, ns):
    """Path A -- exec product/ cells. Returns (prod_agg, prod_monthly, total_accts_prod).

    Seeds the namespace with the shared TXN theme so cell 01's styled-table block
    (which references GEN_COLORS) doesn't NameError and zero out prod_agg. In
    production the `general` section supplies these globals via execution order;
    seeding reproduces that exact condition for the numeric path without running
    all 30 general cells.
    """
    from ars_analysis.analytics.txn_wrapper import TXNSectionWrapper
    from ars_analysis.shared import txn_theme

    analytics_dir = Path(__file__).resolve().parent
    ns_old = ns.copy()
    # Seed the general-theme globals the product cells expect.
    for name in (
        "GEN_COLORS", "BRACKET_PALETTE", "ENGAGE_PALETTE", "ENGAGE_ORDER",
        "GEN_TITLE_Y", "GEN_SUBTITLE_Y", "GEN_TOP_PAD",
        "gen_fmt_pct", "gen_fmt_count", "gen_fmt_dollar", "gen_fmt_index",
        "gen_clean_axes",
    ):
        ns_old[name] = getattr(txn_theme, name)

    wrapper = TXNSectionWrapper("product", analytics_dir / "product")
    wrapper.run(ars_ctx, shared_namespace=ns_old)

    return (
        ns_old.get("prod_agg", pd.DataFrame()),
        ns_old.get("prod_monthly", pd.DataFrame()),
        int(ns_old.get("total_accts_prod", 0)),
    )


def _diff_frame(old: pd.DataFrame, new: pd.DataFrame, keys: list[str],
                cols: list[str], name: str) -> dict:
    """Align two frames on keys and compare numeric cols. Returns a report dict."""
    if old.empty or new.empty:
        return {"table": name, "ok": old.empty and new.empty,
                "note": f"old_empty={old.empty} new_empty={new.empty}"}

    o = old.set_index(keys).sort_index()
    n = new.set_index(keys).sort_index()
    if list(o.index) != list(n.index):
        only_old = [k for k in o.index if k not in set(n.index)]
        only_new = [k for k in n.index if k not in set(o.index)]
        return {"table": name, "ok": False, "note": "row keys differ",
                "only_old": [str(x) for x in only_old][:20],
                "only_new": [str(x) for x in only_new][:20]}

    mismatches = []
    for col in cols:
        if col not in o.columns or col not in n.columns:
            mismatches.append({"col": col, "note": "missing in one side"})
            continue
        ov = pd.to_numeric(o[col], errors="coerce")
        nv = pd.to_numeric(n[col], errors="coerce")
        close = pd.Series(
            [abs(a - b) <= _TOL + _TOL * abs(b) if pd.notna(a) and pd.notna(b) else (pd.isna(a) and pd.isna(b))
             for a, b in zip(ov, nv)],
            index=ov.index,
        )
        if not close.all():
            bad = (~close)
            examples = []
            for k in list(o.index[bad.values])[:5]:
                examples.append({"key": str(k), "old": float(ov.loc[k]), "new": float(nv.loc[k])})
            mismatches.append({"col": col, "n_bad": int((~close).sum()), "examples": examples})

    return {"table": name, "ok": not mismatches, "rows": len(o), "mismatches": mismatches}


def diff(args) -> dict:
    from runner import _build_txn_context
    from ars_analysis.pipeline.steps.txn_load import step_txn_load

    shared_ctx = _build_shared_ctx(args)
    ars_ctx = _build_txn_context(shared_ctx)

    # Build combined/rewards ONCE; both paths share it.
    ns = step_txn_load(ars_ctx)

    # Run the NEW module first, on pristine ctx.txn (exec cell 01 mutates combined_df).
    new_agg, new_monthly, new_accts = _run_new(ars_ctx)
    old_agg, old_monthly, old_accts = _run_old(ars_ctx, ns)

    report = {
        "client_id": args.client,
        "month": args.month,
        "tables": [
            _diff_frame(old_agg, new_agg, ["product_label"], _AGG_COLS, "prod_agg"),
            _diff_frame(old_monthly, new_monthly, ["year_month", "product_label"],
                        _MONTHLY_COLS, "prod_monthly"),
        ],
        "scalars": {
            "total_accts_prod": {"old": old_accts, "new": new_accts,
                                 "ok": old_accts == new_accts},
        },
    }
    report["ok"] = (
        all(t["ok"] for t in report["tables"])
        and report["scalars"]["total_accts_prod"]["ok"]
    )
    return report


def _print_report(report: dict) -> None:
    status = "PASS" if report["ok"] else "FAIL"
    print("=" * 64)
    print(f"  PRODUCT MIGRATION EQUIVALENCE DIFF: {status}")
    print(f"  client={report['client_id']}  month={report['month']}")
    print("=" * 64)
    for t in report["tables"]:
        mark = "OK " if t["ok"] else "XX "
        print(f"  [{mark}] {t['table']}: {t.get('rows', '-')} rows")
        if not t["ok"]:
            if "note" in t:
                print(f"         note: {t['note']}")
            for mm in t.get("mismatches", []):
                print(f"         col {mm.get('col')}: {mm.get('n_bad', '?')} mismatched "
                      f"-> {mm.get('examples', mm.get('note'))}")
    sc = report["scalars"]["total_accts_prod"]
    print(f"  [{'OK ' if sc['ok'] else 'XX '}] total_accts_prod: old={sc['old']} new={sc['new']}")
    print("=" * 64)


def _bootstrap_imports() -> None:
    """Mirror 01_Analysis/run.py: put 00-Scripts on path + alias ars_analysis.

    Lets this run as a plain script (python .../analytics/diff_product.py) with
    the same import surface the pipeline uses, without needing a pre-set alias.
    """
    import types

    scripts_dir = Path(__file__).resolve().parent.parent  # .../00-Scripts
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    if "ars_analysis" not in sys.modules:
        pkg = types.ModuleType("ars_analysis")
        pkg.__path__ = [str(scripts_dir)]
        pkg.__package__ = "ars_analysis"
        sys.modules["ars_analysis"] = pkg


def main() -> int:
    _bootstrap_imports()
    p = argparse.ArgumentParser(description="Equivalence diff: exec product cells vs module")
    p.add_argument("--csm", required=True)
    p.add_argument("--month", required=True, help="YYYY.MM")
    p.add_argument("--client", required=True)
    p.add_argument("--client-name", default="")
    p.add_argument("--odd", default="", help="Path to the formatted ODD file")
    p.add_argument("--config", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--json", default="", help="Optional path to write the JSON report")
    args = p.parse_args()

    report = diff(args)
    _print_report(report)

    out_json = Path(args.json) if args.json else (Path(args.output_dir or ".") / "product_diff_report.json")
    try:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"  JSON report: {out_json}")
    except OSError as exc:
        print(f"  (could not write JSON report: {exc})")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
