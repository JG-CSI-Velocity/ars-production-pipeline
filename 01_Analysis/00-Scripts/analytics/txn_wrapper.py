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


class _NullCM:
    def __enter__(self): return None
    def __exit__(self, *a): return False


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


# ---------------------------------------------------------------------------
# TXN-results adapter (docs/txn-results-adapter-design.md)
# ---------------------------------------------------------------------------


def _extract_script_number(filename: str) -> int | None:
    """01_foo.py -> 1; 70_banking_vs_ecosystems.py -> 70; unprefixed -> None."""
    stem = filename.rsplit(".", 1)[0]
    head = stem.split("_", 1)[0]
    try:
        return int(head)
    except (TypeError, ValueError):
        return None


def expose_to_ctx_results(
    ctx: PipelineContext | None,
    namespace: dict[str, Any],
    section: str,
    script_number: int,
    script_path: Path,
) -> None:
    """Copy declared exports from `namespace` into ctx.results.

    Called after each TXN script finishes execution. Looks up
    (section, script_number) in SECTION_EXPORTS; for every variable name
    declared, reads it from the namespace and stamps it on
    ctx.results[f"{section}_{script_number}"]. Silently skips variables
    that aren't in the namespace -- they may not exist if the script
    failed partway through.

    No-op when ctx is None (e.g. txn_setup runs with a stub ctx).
    """
    if ctx is None:
        return
    try:
        from ars_analysis.analytics.txn_exports import get_exports
    except Exception:
        return

    spec = get_exports(section, script_number)
    if spec is None:
        return  # No declared exports -- not an error.

    key = f"{section}_{script_number}"
    if not hasattr(ctx, "results") or ctx.results is None:
        return
    bucket = ctx.results.setdefault(key, {})
    bucket.setdefault("insights", {})
    bucket.setdefault("tables", {})
    bucket["script"] = script_path.name

    for var in spec.get("insights", []):
        if var in namespace:
            bucket["insights"][var] = namespace[var]
        else:
            logger.debug(
                "TXN export miss: {section}/{n} expected '{var}' not in namespace",
                section=section, n=script_number, var=var,
            )

    for var in spec.get("tables", []):
        if var in namespace:
            bucket["tables"][var] = namespace[var]


def _execute_scripts(script_dir: Path, namespace: dict[str, Any],
                     chart_dir: Path, section_prefix: str,
                     section_recorder: object = None,
                     manifest_meta: dict[str, str] | None = None,
                     ctx: PipelineContext | None = None,
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

    # Per-script skip patterns (prefix-match on script name). Configured by
    # earlier cells to prune duplicate / optional cells without deleting code.
    # Example: competition/01 sets SKIP_SCRIPT_PATTERNS=['60_', '61_', '62_']
    # when SLIDE_MODE='standard' to drop the parallel banks-only / core-
    # competition variants (each a ~5-slide duplicate view of 07-09). Keeps
    # the deep-dive cells available for clients who want them via
    # SLIDE_MODE='deep'.
    skip_patterns = namespace.get("SKIP_SCRIPT_PATTERNS", [])

    for script_path in scripts:
        script_name = script_path.stem

        # Check for skip flag -- sections can set SKIP_SECTION = True
        # to bail out early (e.g., "No MCC data available")
        if namespace.get("SKIP_SECTION"):
            logger.info("  TXN skipping: {name} (SKIP_SECTION set)", name=script_name)
            continue

        # Check script-level skip patterns
        if any(script_name.startswith(pat) for pat in skip_patterns):
            logger.info(
                "  TXN skipping: {name} (matches SKIP_SCRIPT_PATTERNS)",
                name=script_name,
            )
            continue

        logger.info("  TXN executing: {name}", name=script_name)

        with ChartCapture(chart_dir, prefix=f"{section_prefix}_{script_name}") as capture:
            import sys as _sys
            import time as _time
            from ars_analysis.pipeline.manifest import ScriptRecord, ScriptStatus
            from ars_analysis.pipeline import error_capture as _ec

            _t0 = _time.monotonic()
            _failed = False
            try:
                code = script_path.read_text(encoding="utf-8")
                namespace["__file__"] = str(script_path)
                exec(compile(code, str(script_path), "exec"), namespace)
                # TXN-results adapter: after the script settles, copy any
                # declared variables out of the shared namespace into
                # ctx.results so the slide_spec renderer can bind to them.
                # See docs/txn-results-adapter-design.md + analytics/txn_exports.py.
                _script_number = _extract_script_number(script_path.name)
                if _script_number is not None and ctx is not None:
                    expose_to_ctx_results(
                        ctx, namespace, section_prefix, _script_number, script_path,
                    )
            except Exception as exc:
                _failed = True
                logger.error("  TXN script failed: {name}: {err}", name=script_name, err=exc)
                failures.append(ScriptFailure(
                    script_name=script_name,
                    error_type=type(exc).__name__,
                    error_msg=str(exc)[:200],
                ))
                if section_recorder is not None:
                    meta = manifest_meta or {}
                    fields = _ec.capture_exception(
                        exc, _sys.exc_info()[2],
                        section_name=section_prefix,
                        script_name=script_name,
                        client_id=meta.get("client_id", ""),
                        month=meta.get("month", ""),
                    )
                    section_recorder.record_script(ScriptRecord(
                        name=script_name,
                        status=ScriptStatus.FAILED,
                        elapsed_s=round(_time.monotonic() - _t0, 2),
                        **fields,
                    ))
                # Do NOT `continue` here -- falling through lets the ChartCapture
                # __exit__ run, which closes any partially-created figures. The
                # next loop iteration proceeds to the next script.

            if not _failed and section_recorder is not None:
                section_recorder.record_script(ScriptRecord(
                    name=script_name,
                    status=ScriptStatus.OK,
                    elapsed_s=round(_time.monotonic() - _t0, 2),
                    slides=len(capture.captured) if hasattr(capture, "captured") else 0,
                ))

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

    # Reset skip flags for next section -- each section controls its own
    # pruning via its own 01_*.py setting SKIP_SCRIPT_PATTERNS.
    namespace.pop("SKIP_SECTION", None)
    namespace.pop("SKIP_SCRIPT_PATTERNS", None)

    return all_charts, failures


# ---------------------------------------------------------------------------
# TXN Section Wrapper
# ---------------------------------------------------------------------------

# Section metadata for all TXN folders
# `code` is the short prefix used in runtime slide_ids (TXN-{code}-NN) and
# must match the prefix the operator types in SLIDE_MANIFEST.xlsx -- otherwise
# Keep? Y/A/N decisions silently no-op for this section. Codes for the 19
# template-listed TXN sheets come from SLIDE_MANIFEST.template.xlsx; the three
# without template entries (BUS / PERS / ICSA) are assigned here for symmetry.
TXN_SECTIONS = {
    "general": {"display": "Portfolio Overview", "order": 100, "code": "GEN"},
    "merchant": {"display": "Merchant Analysis", "order": 110, "code": "MERCH"},
    "mcc_code": {"display": "MCC Categories", "order": 120, "code": "MCC"},
    "business_accts": {"display": "Business Accounts", "order": 130, "code": "BUS"},
    "personal_accts": {"display": "Personal Accounts", "order": 140, "code": "PERS"},
    "competition": {"display": "Competition", "order": 150, "code": "COMP"},
    "financial_services": {"display": "Financial Services", "order": 160, "code": "FIN"},
    "ics_acquisition": {"display": "ICS Acquisition", "order": 170, "code": "ICSA"},
    "campaign": {"display": "Campaign Analysis", "order": 180, "code": "CAMP"},
    "branch_txn": {"display": "Branch Performance", "order": 190, "code": "BR"},
    "transaction_type": {"display": "Transaction Type", "order": 200, "code": "TT"},
    "product": {"display": "Product Analysis", "order": 210, "code": "PROD"},
    "attrition_txn": {"display": "Attrition (Velocity)", "order": 220, "code": "ATR"},
    "balance": {"display": "Balance Analysis", "order": 230, "code": "BAL"},
    "interchange": {"display": "Interchange Revenue", "order": 240, "code": "IC"},
    "rege_overdraft": {"display": "Reg E / Overdraft", "order": 250, "code": "REGE"},
    "payroll": {"display": "Payroll & Direct Deposit", "order": 260, "code": "PAY"},
    "relationship": {"display": "Relationship Depth", "order": 270, "code": "REL"},
    "segment_evolution": {"display": "Segment Evolution", "order": 280, "code": "SEG"},
    "retention": {"display": "Retention Analysis", "order": 290, "code": "RET"},
    "engagement": {"display": "Engagement Migration", "order": 300, "code": "ENG"},
    "executive": {"display": "Executive Scorecard", "order": 900, "code": "EXEC"},
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
        # Short slide-id prefix used in TXN-{code}-NN; must match SLIDE_MANIFEST.xlsx.
        # Fallback for unmapped sections: upper-case section_name (deterministic, won't crash).
        self.section_code = meta.get("code", section_name.upper())
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
                    ctx=ctx,
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
        _mf = getattr(ctx, "manifest", None)
        _section_cm = _mf.start_section(self.display_name) if _mf is not None else _NullCM()
        _manifest_meta = {
            "client_id": getattr(ctx.client, "client_id", ""),
            "month": getattr(ctx.client, "month", ""),
        } if _mf is not None else None

        with _section_cm as _sec:
            _recorder = _sec if _mf is not None else None
            charts, self.failures = _execute_scripts(
                self.section_dir, namespace, chart_dir, self.section_name,
                section_recorder=_recorder, manifest_meta=_manifest_meta,
                ctx=ctx,
            )
            # Record slide count + flag if zero slides on a section that expected them
            if _mf is not None and _recorder is not None:
                _recorder.set_slides(len(charts))
                if len(charts) == 0 and len(self.failures) == 0:
                    # Section produced nothing without errors -- worth flagging
                    from ars_analysis.pipeline.manifest import FlagLevel
                    _recorder.flag(FlagLevel.INFO, "section produced 0 slides without errors")

        # Propagate new variables back to shared namespace so later sections
        # can use them (e.g., GEN_COLORS from general, demo_df, acct_txn_counts).
        if shared_namespace is not None:
            for key, val in namespace.items():
                if key not in shared_namespace:
                    shared_namespace[key] = val

        # Convert captured charts to AnalysisResult objects
        results = []
        for i, chart_path in enumerate(charts):
            slide_id = f"TXN-{self.section_code}-{i+1:02d}"
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
    _charts, setup_failures = _execute_scripts(
        setup_dir, namespace, ctx.paths.charts_dir, "txn_setup",
        ctx=ctx,
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

    # Apply 4-denominator framework to TXN data (Audit 2026-04-27 Entry 1)
    _inject_eligible_filter(namespace, ctx)

    elapsed = time.time() - t0
    row_count = 0
    df = namespace.get("combined_df")
    if df is not None and hasattr(df, "__len__"):
        row_count = len(df)

    # Memory telemetry. When the campaign section later hits ``bad
    # allocation'' / ``not enough free memory for image buffer'' (issue
    # #92), this baseline helps diagnose whether setup itself is the
    # problem or something downstream is leaking. psutil is optional.
    _rss_mb = None
    try:
        import psutil as _psutil
        _rss_mb = _psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        pass

    if _rss_mb is not None:
        logger.info(
            "txn_setup complete: {rows:,} rows in {sec:.1f}s (process RSS: {rss:,.0f} MB)",
            rows=row_count, sec=elapsed, rss=_rss_mb,
        )
        namespace["_txn_setup_rss_mb"] = _rss_mb
    else:
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
