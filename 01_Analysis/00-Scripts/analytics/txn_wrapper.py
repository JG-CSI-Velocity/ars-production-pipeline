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
        # Capture any remaining open figures left behind when a script ended
        # without calling plt.show() (or crashed mid-render). Savefig errors
        # here used to be DEBUG-level silent drops -- upgraded to WARNING so
        # partial-chart losses don't disappear from the run report.
        self.save_errors: list[str] = []
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
                msg = f"{name}: {type(exc).__name__}: {str(exc)[:120]}"
                logger.warning("Chart save failed in __exit__: {msg}", msg=msg)
                self.save_errors.append(msg)
        plt.close("all")

        # Restore original plt.show
        if self._original_show:
            plt.show = self._original_show


# ---------------------------------------------------------------------------
# Script executor -- runs scripts in a shared namespace
# ---------------------------------------------------------------------------

@dataclass
class ScriptFailure:
    """One failed script execution. Surfaced so the summary shows real status."""
    script_name: str
    error_type: str
    error_msg: str


def _execute_scripts(script_dir: Path, namespace: dict[str, Any],
                     chart_dir: Path, section_prefix: str
                     ) -> tuple[list[Path], list[ScriptFailure]]:
    """Execute all .py scripts in a directory in sorted order, sharing a namespace.

    Returns:
        (captured_charts, failures). Failures used to be silently logged-only,
        which made the TXN summary report ``22/22 OK'' when there were actual
        crashes. Callers MUST propagate failures to the section-level summary
        so users see them.
    """
    scripts = sorted(script_dir.glob("*.py"))
    if not scripts:
        logger.warning("No .py scripts found in {dir}", dir=script_dir)
        return [], []

    all_charts: list[Path] = []
    failures: list[ScriptFailure] = []

    # Preserve the parent namespace's __file__ so we can restore it after this
    # batch finishes. Without this, the last script's __file__ leaks into
    # the next section and any subsequent `Path(__file__).parent` is wrong.
    saved_file = namespace.get("__file__")

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
                namespace["__file__"] = str(script_path)
                exec(compile(code, str(script_path), "exec"), namespace)
            except Exception as exc:
                logger.error("  TXN script failed: {name}: {err}", name=script_name, err=exc)
                failures.append(ScriptFailure(
                    script_name=script_name,
                    error_type=type(exc).__name__,
                    error_msg=str(exc)[:200],
                ))
                # Do NOT `continue` here -- falling through lets the ChartCapture
                # __exit__ run, which closes any partially-created figures. The
                # next loop iteration proceeds to the next script.

        all_charts.extend(capture.captured)

        # Memory hygiene between scripts. Campaign section was hitting ``bad
        # allocation'' and ``not enough free memory for image buffer'' because
        # matplotlib figures accumulated across 30+ scripts. plt.close('all')
        # + gc.collect() at the boundary releases those buffers.
        try:
            plt.close("all")
        except Exception:
            pass
        try:
            import gc
            gc.collect()
        except Exception:
            pass

    # Restore/clean up __file__ so it doesn't leak to the next section
    if saved_file is None:
        namespace.pop("__file__", None)
    else:
        namespace["__file__"] = saved_file

    # Reset skip flag for next section
    namespace.pop("SKIP_SECTION", None)

    return all_charts, failures


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
        # Populated by .run() so runner.py can print real per-section status
        # instead of always saying ``OK''. Was a silent ERROR-log-only before.
        self.failures: list[ScriptFailure] = []

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
                _setup_charts, _setup_failures = _execute_scripts(
                    setup_dir, namespace, ctx.paths.charts_dir, "txn_setup",
                )
                if _setup_failures:
                    logger.error(
                        "txn_setup had {n} failed scripts: {names}",
                        n=len(_setup_failures),
                        names=", ".join(f.script_name for f in _setup_failures),
                    )
                namespace["_txn_setup_done"] = True

        # Run section scripts
        chart_dir = ctx.paths.charts_dir / self.section_name
        charts, self.failures = _execute_scripts(
            self.section_dir, namespace, chart_dir, self.section_name,
        )

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

        if self.failures:
            logger.warning(
                "TXN section {name}: {n} charts captured, {f} script(s) FAILED ({names})",
                name=self.section_name, n=len(results),
                f=len(self.failures),
                names=", ".join(f.script_name for f in self.failures),
            )
        else:
            logger.info(
                "TXN section {name}: {n} charts captured",
                name=self.section_name, n=len(results),
            )
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


def prepare_shared_namespace(ctx: PipelineContext) -> dict[str, Any]:
    """Build namespace and run txn_setup ONCE for all sections.

    This is the key optimization: txn_setup reads all TXN files from disk
    (millions of rows x up to 12 months), concatenates them into combined_df,
    loads the ODD file, and merges. Previously this ran 22 times (once per
    section). Now it runs once and the namespace is shared.

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
    _charts, setup_failures = _execute_scripts(
        setup_dir, namespace, ctx.paths.charts_dir, "txn_setup",
    )
    if setup_failures:
        # txn_setup failures are CRITICAL -- combined_df may not exist and
        # every downstream section will fail. Log loudly but keep going so
        # later diagnostics still run and the user can see the chain.
        logger.error(
            "txn_setup FAILURES ({n}): {names} -- downstream sections likely broken",
            n=len(setup_failures),
            names=", ".join(f.script_name for f in setup_failures),
        )
        namespace["_txn_setup_failures"] = setup_failures
    namespace["_txn_setup_done"] = True

    # Optimize memory after the heavy data loading
    _optimize_combined_df(namespace)

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
