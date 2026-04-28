"""TXN Wrapper -- executes notebook-cell scripts as AnalysisModule instances.

Each TXN section (general, merchant, competition, etc.) has a folder of
numbered Python scripts that were converted from Jupyter notebook cells.
These scripts share a global namespace -- variables from earlier scripts
are available in later ones.

This wrapper:
1. Runs txn_setup/ scripts ONCE to establish shared state (CLIENT_ID, combined_df, etc.)
2. Shares the setup namespace across all 22 sections (no redundant data loading)
3. Runs each section's scripts in order (01_*.py, 02_*.py, ...)
4. Intercepts matplotlib figure saves to capture chart PNGs
5. Returns AnalysisResult objects for the deck builder

Usage:
    # Prepare shared namespace once (loads TXN files + ODD, builds combined_df)
    namespace = prepare_shared_namespace(ctx)

    # Run each section using the shared namespace
    for wrapper in discover_txn_sections():
        results = wrapper.run(ctx, shared_namespace=namespace)
"""

from __future__ import annotations

import io
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.pipeline.context import PipelineContext


# ---------------------------------------------------------------------------
# Chart capture -- intercept matplotlib savefig and plt.show
# ---------------------------------------------------------------------------

class ChartCapture:
    """Context manager that captures all matplotlib figures created during execution."""

    def __init__(self, output_dir: Path, prefix: str = ""):
        self.output_dir = output_dir
        self.prefix = prefix
        self.captured: list[Path] = []
        self._original_show = None
        self._original_savefig = None
        self._fig_count = 0

    def __enter__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._original_show = plt.show
        self._fig_count = 0

        # Replace plt.show() to save instead of display
        def _capture_show(*args, **kwargs):
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                self._fig_count += 1
                name = f"{self.prefix}_{self._fig_count:02d}.png"
                path = self.output_dir / name
                fig.savefig(path, dpi=150, bbox_inches="tight",
                            facecolor="white", edgecolor="none")
                self.captured.append(path)
                logger.debug("Captured chart: {name}", name=name)
            plt.close("all")

        plt.show = _capture_show
        return self

    def __exit__(self, *args):
        # Capture any remaining open figures
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            self._fig_count += 1
            name = f"{self.prefix}_{self._fig_count:02d}.png"
            path = self.output_dir / name
            try:
                fig.savefig(path, dpi=150, bbox_inches="tight",
                            facecolor="white", edgecolor="none")
                self.captured.append(path)
            except Exception as exc:
                logger.debug("Failed to save chart {name}: {err}", name=name, err=exc)
        plt.close("all")

        # Restore original plt.show
        if self._original_show:
            plt.show = self._original_show


# ---------------------------------------------------------------------------
# Script executor -- runs scripts in a shared namespace
# ---------------------------------------------------------------------------

def _execute_scripts(script_dir: Path, namespace: dict[str, Any],
                     chart_dir: Path, section_prefix: str) -> list[Path]:
    """Execute all .py scripts in a directory in sorted order, sharing a namespace.

    Returns list of captured chart paths.
    """
    scripts = sorted(script_dir.glob("*.py"))
    if not scripts:
        logger.warning("No .py scripts found in {dir}", dir=script_dir)
        return []

    all_charts: list[Path] = []

    for script_path in scripts:
        script_name = script_path.stem

        # Check for skip flag -- sections can set SKIP_SECTION = True
        # to bail out early (e.g., "No MCC data available")
        if namespace.get("SKIP_SECTION"):
            logger.info("  TXN skipping: {name} (SKIP_SECTION set)", name=script_name)
            continue

        logger.info("  TXN executing: {name}", name=script_name)

        with ChartCapture(chart_dir, prefix=f"{section_prefix}_{script_name}") as capture:
            try:
                code = script_path.read_text(encoding="utf-8")
                # Set __file__ so scripts can resolve relative paths
                namespace["__file__"] = str(script_path)
                exec(compile(code, str(script_path), "exec"), namespace)
            except Exception as exc:
                logger.error("  TXN script failed: {name}: {err}", name=script_name, err=exc)
                continue

        all_charts.extend(capture.captured)

    # Reset skip flag for next section
    namespace.pop("SKIP_SECTION", None)

    return all_charts


# ---------------------------------------------------------------------------
# TXN Section Wrapper
# ---------------------------------------------------------------------------

# Section metadata for all TXN folders
TXN_SECTIONS = {
    "general": {"display": "Portfolio Overview", "order": 100},
    "merchant": {"display": "Merchant Analysis", "order": 110},
    "mcc_code": {"display": "MCC Categories", "order": 120},
    "business_accts": {"display": "Business Accounts", "order": 130},
    "personal_accts": {"display": "Personal Accounts", "order": 140},
    "competition": {"display": "Competition", "order": 150},
    "financial_services": {"display": "Financial Services", "order": 160},
    "ics_acquisition": {"display": "ICS Acquisition", "order": 170},
    "campaign": {"display": "Campaign Analysis", "order": 180},
    "branch_txn": {"display": "Branch Performance", "order": 190},
    "transaction_type": {"display": "Transaction Type", "order": 200},
    "product": {"display": "Product Analysis", "order": 210},
    "attrition_txn": {"display": "Attrition (Velocity)", "order": 220},
    "balance": {"display": "Balance Analysis", "order": 230},
    "interchange": {"display": "Interchange Revenue", "order": 240},
    "rege_overdraft": {"display": "Reg E / Overdraft", "order": 250},
    "payroll": {"display": "Payroll & Direct Deposit", "order": 260},
    "relationship": {"display": "Relationship Depth", "order": 270},
    "segment_evolution": {"display": "Segment Evolution", "order": 280},
    "retention": {"display": "Retention Analysis", "order": 290},
    "engagement": {"display": "Engagement Migration", "order": 300},
    "executive": {"display": "Executive Scorecard", "order": 900},
}


class TXNSectionWrapper(AnalysisModule):
    """Wraps a TXN section folder as an AnalysisModule.

    Executes numbered scripts in a shared namespace, captures charts,
    returns AnalysisResult objects.
    """

    def __init__(self, section_name: str, section_dir: Path | str):
        self.section_name = section_name
        self.section_dir = Path(section_dir)
        meta = TXN_SECTIONS.get(section_name, {})

        self.module_id = f"txn.{section_name}"
        self.display_name = meta.get("display", section_name.replace("_", " ").title())
        self.section = "transaction"
        self.execution_order = meta.get("order", 500)
        self.required_columns = ()  # TXN scripts handle their own validation

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Check that section directory exists and has scripts."""
        errors = []
        if not self.section_dir.exists():
            errors.append(f"TXN section directory not found: {self.section_dir}")
        elif not list(self.section_dir.glob("*.py")):
            errors.append(f"No .py scripts in {self.section_dir}")
        return errors

    def run(self, ctx: PipelineContext,
            shared_namespace: dict[str, Any] | None = None) -> list[AnalysisResult]:
        """Execute all scripts in the section and capture results.

        Args:
            ctx: Pipeline context with client info and paths.
            shared_namespace: Pre-built namespace from prepare_shared_namespace().
                If provided, txn_setup is NOT re-run -- the namespace already
                contains combined_df, rewards_df, and all setup state.
                Each section gets a shallow copy so variable assignments in one
                section don't leak into the next, but DataFrames are shared
                (not duplicated in memory).
        """
        logger.info("TXN section: {name} ({dir})", name=self.display_name, dir=self.section_dir)

        if shared_namespace is not None:
            # Shallow copy: section scripts can add/reassign variables without
            # affecting other sections, but large DataFrames (combined_df,
            # rewards_df) are NOT duplicated -- they share the same memory.
            # Variables created by earlier sections (GEN_COLORS, demo_df, etc.)
            # ARE carried forward because later sections depend on them.
            namespace = shared_namespace.copy()
        else:
            # Legacy path: build namespace + run setup per section.
            # Only used if caller doesn't provide shared_namespace.
            namespace = _build_namespace(ctx)
            setup_dir = self.section_dir.parent / "txn_setup"
            if setup_dir.exists() and "_txn_setup_done" not in namespace:
                logger.info("  Running txn_setup...")
                _execute_scripts(setup_dir, namespace, ctx.paths.charts_dir, "txn_setup")
                namespace["_txn_setup_done"] = True

        # Run section scripts
        chart_dir = ctx.paths.charts_dir / self.section_name
        charts = _execute_scripts(self.section_dir, namespace, chart_dir, self.section_name)

        # Propagate new variables back to shared namespace so later sections
        # can use them (e.g., GEN_COLORS from general, demo_df, acct_txn_counts).
        if shared_namespace is not None:
            for key, val in namespace.items():
                if key not in shared_namespace:
                    shared_namespace[key] = val

        # Convert captured charts to AnalysisResult objects
        results = []
        for i, chart_path in enumerate(charts):
            slide_id = f"TXN-{self.section_name}-{i+1:02d}"
            results.append(AnalysisResult(
                slide_id=slide_id,
                title=f"{self.display_name}: {chart_path.stem.replace('_', ' ')}",
                chart_path=chart_path,
                layout_index=8,  # LAYOUT_CUSTOM
                slide_type="screenshot",
                success=True,
            ))

        logger.info("TXN section {name}: {n} charts captured", name=self.section_name, n=len(results))
        return results


def _build_namespace(ctx: PipelineContext) -> dict[str, Any]:
    """Build the shared namespace for TXN script execution.

    Pre-populates with common imports and pipeline context values
    so scripts don't need to import everything themselves.
    """
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    # Jupyter-compatible display() -- scripts converted from notebooks call this.
    # In a script context, just print the repr.
    def _display(*args, **kwargs):
        for a in args:
            if hasattr(a, 'to_string'):
                print(a.to_string())
            else:
                print(a)

    from collections import OrderedDict
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import FancyBboxPatch
    import matplotlib.dates as mdates
    import matplotlib.patheffects as pe
    import matplotlib.ticker as mticker
    import re as _re
    import json as _json
    import gc as _gc
    import seaborn as sns
    import warnings
    import time as _time
    warnings.filterwarnings('ignore')

    ns: dict[str, Any] = {
        # Common imports available to all scripts
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "GridSpec": GridSpec,
        "FancyBboxPatch": FancyBboxPatch,
        "LinearSegmentedColormap": LinearSegmentedColormap,
        "OrderedDict": OrderedDict,
        "mdates": mdates,
        "pe": pe,
        "mticker": mticker,
        "re": _re,
        "json": _json,
        "gc": _gc,
        "time": _time,
        "Path": Path,
        "os": os,
        "sys": sys,
        "warnings": warnings,
        # Jupyter compatibility
        "display": _display,
        # Pipeline context values
        "CLIENT_ID": ctx.client.client_id,
        "CLIENT_NAME": ctx.client.client_name,
        "MONTH": ctx.client.month,
        "CSM": ctx.client.assigned_csm,
        # Data (if loaded)
        "odd_df": ctx.data,
        # Builtins
        "__builtins__": __builtins__,
    }

    # Set environment variables so 02-file-config.py can read them.
    # CLIENT_ID: required for TXN file discovery in TXN Files/{CSM}/{client_id}/
    # CSM: required for TXN folder path and ODD file lookup
    # MONTH: required for ODD file lookup in {CSM}/{MONTH}/{client_id}/
    os.environ["CLIENT_ID"] = ctx.client.client_id
    os.environ["CSM"] = ctx.client.assigned_csm or ""
    os.environ["MONTH"] = ctx.client.month or ""

    return ns


def _optimize_combined_df(namespace: dict[str, Any]) -> None:
    """Reduce memory footprint of combined_df after txn_setup builds it.

    Converts low-cardinality string columns to categoricals and downcasts
    numeric columns. Operates in-place on the namespace's DataFrame.
    With millions of rows x 12 months, this can cut memory 50-70%.
    """
    import pandas as pd

    df = namespace.get("combined_df")
    if df is None or not isinstance(df, pd.DataFrame):
        return

    before_mb = df.memory_usage(deep=True).sum() / 1024**2

    # String columns that repeat heavily -- categorical saves ~90% per column
    categorical_candidates = [
        "transaction_type", "mcc_code", "merchant_name", "merchant_consolidated",
        "terminal_location_1", "terminal_location_2", "terminal_id",
        "merchant_id", "institution", "card_present", "transaction_code",
        "source_file", "business_flag",
    ]
    for col in categorical_candidates:
        if col in df.columns and df[col].dtype == "object":
            df[col] = df[col].astype("category")

    # Downcast numeric columns
    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")
    for col in df.select_dtypes(include=["int64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="integer")

    after_mb = df.memory_usage(deep=True).sum() / 1024**2
    logger.info(
        "combined_df optimized: {before:.0f} MB -> {after:.0f} MB ({pct:.0f}% reduction)",
        before=before_mb, after=after_mb,
        pct=(1 - after_mb / before_mb) * 100 if before_mb > 0 else 0,
    )


def _inject_eligible_filter(namespace: dict[str, Any], ctx: PipelineContext) -> None:
    """Filter combined_df and rewards_df to eligible accounts only.

    Why: TXN scripts compute rates against the raw TXN universe, producing
    KPI cards labeled "Eligible Accounts" whose underlying base does not
    match the ARS-side eligible denominator. This injection enforces the
    4-denominator framework (Eligible / Eligible Personal / Eligible
    Business / Open) defined in pipeline/steps/subsets.py.

    Exposes:
        ELIGIBLE_ACCOUNTS         set[str]      -- canonical eligible account IDs
        ELIGIBLE_FILTER_APPLIED   bool          -- True iff filtering happened
        combined_df               filtered      -- replaces unfiltered version
        rewards_df                filtered      -- replaces unfiltered version
        combined_df_all           original      -- pre-filter, escape hatch
        rewards_df_all            original      -- pre-filter, escape hatch

    No-ops (logs warning) if ctx.subsets.eligible_data is unavailable, so
    legacy clients without proper eligible config don't break the pipeline.
    """
    if ctx.subsets is None or ctx.subsets.eligible_data is None:
        logger.warning(
            "Eligible filter NOT applied -- ctx.subsets.eligible_data is unavailable. "
            "TXN denominators will use unfiltered combined_df. Check client EligibleStatusCodes config."
        )
        namespace["ELIGIBLE_ACCOUNTS"] = set()
        namespace["ELIGIBLE_FILTER_APPLIED"] = False
        return

    elig_df = ctx.subsets.eligible_data

    acct_col = None
    for candidate in ("Acct Number", " Acct Number", "Account Number", "AcctNumber"):
        if candidate in elig_df.columns:
            acct_col = candidate
            break
    if acct_col is None:
        logger.warning(
            "Eligible filter NOT applied -- no recognized account column in eligible_data. "
            "Columns: {cols}",
            cols=list(elig_df.columns)[:15],
        )
        namespace["ELIGIBLE_ACCOUNTS"] = set()
        namespace["ELIGIBLE_FILTER_APPLIED"] = False
        return

    eligible_set = set(elig_df[acct_col].astype(str).str.strip())
    namespace["ELIGIBLE_ACCOUNTS"] = eligible_set
    namespace["ELIGIBLE_FILTER_APPLIED"] = True

    combined = namespace.get("combined_df")
    if combined is not None and hasattr(combined, "columns") and "primary_account_num" in combined.columns:
        namespace["combined_df_all"] = combined
        before = len(combined)
        mask = combined["primary_account_num"].astype(str).str.strip().isin(eligible_set)
        namespace["combined_df"] = combined[mask]
        after = len(namespace["combined_df"])
        logger.info(
            "combined_df filtered to eligible: {before:,} -> {after:,} rows ({pct:.1f}% retained)",
            before=before, after=after,
            pct=(after / before * 100) if before > 0 else 0,
        )

    rewards = namespace.get("rewards_df")
    if rewards is not None and hasattr(rewards, "columns"):
        rewards_acct_col = None
        for candidate in ("Acct Number", " Acct Number", "Account Number"):
            if candidate in rewards.columns:
                rewards_acct_col = candidate
                break
        if rewards_acct_col is not None:
            namespace["rewards_df_all"] = rewards
            before = len(rewards)
            mask = rewards[rewards_acct_col].astype(str).str.strip().isin(eligible_set)
            namespace["rewards_df"] = rewards[mask]
            after = len(namespace["rewards_df"])
            logger.info(
                "rewards_df filtered to eligible: {before:,} -> {after:,} rows ({pct:.1f}% retained)",
                before=before, after=after,
                pct=(after / before * 100) if before > 0 else 0,
            )


def prepare_shared_namespace(ctx: PipelineContext) -> dict[str, Any]:
    """Build namespace and run txn_setup ONCE for all sections.

    This is the key optimization: txn_setup reads all TXN files from disk
    (millions of rows x up to 12 months), concatenates them into combined_df,
    loads the ODD file, and merges. Previously this ran 22 times (once per
    section). Now it runs once and the namespace is shared.

    After txn_setup builds combined_df + rewards_df, the eligible filter is
    applied so all downstream TXN scripts compute rates against the correct
    denominator (see _inject_eligible_filter).

    Returns:
        Fully initialized namespace with combined_df, rewards_df, helper
        functions, and all setup state. Callers pass this to
        TXNSectionWrapper.run(ctx, shared_namespace=namespace).
    """
    t0 = time.time()
    namespace = _build_namespace(ctx)

    setup_dir = Path(__file__).parent / "txn_setup"
    if not setup_dir.exists():
        logger.warning("txn_setup directory not found at {dir}", dir=setup_dir)
        return namespace

    logger.info("Running txn_setup once for all sections...")
    _execute_scripts(setup_dir, namespace, ctx.paths.charts_dir, "txn_setup")
    namespace["_txn_setup_done"] = True

    # Optimize memory after the heavy data loading
    _optimize_combined_df(namespace)

    # Apply 4-denominator framework to TXN data (Audit 2026-04-27 Entry 1)
    _inject_eligible_filter(namespace, ctx)

    elapsed = time.time() - t0
    row_count = 0
    df = namespace.get("combined_df")
    if df is not None and hasattr(df, "__len__"):
        row_count = len(df)
    logger.info(
        "txn_setup complete: {rows:,} rows in {sec:.1f}s",
        rows=row_count, sec=elapsed,
    )

    return namespace


# ---------------------------------------------------------------------------
# Discovery -- find all TXN sections and create wrappers
# ---------------------------------------------------------------------------

def discover_txn_sections(analytics_dir: Path | str = None) -> list[TXNSectionWrapper]:
    """Find all TXN section folders and create wrapper instances.

    Returns wrappers sorted by execution order.
    """
    if analytics_dir is None:
        analytics_dir = Path(__file__).parent

    analytics_dir = Path(analytics_dir)
    wrappers = []

    for section_name, meta in TXN_SECTIONS.items():
        section_dir = analytics_dir / section_name
        if section_dir.exists() and list(section_dir.glob("*.py")):
            wrappers.append(TXNSectionWrapper(section_name, section_dir))

    wrappers.sort(key=lambda w: w.execution_order)
    logger.info("Discovered {n} TXN sections", n=len(wrappers))
    return wrappers
