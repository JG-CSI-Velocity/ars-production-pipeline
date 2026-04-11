"""TXN Wrapper -- executes notebook-cell scripts as AnalysisModule instances.

Each TXN section (general, merchant, competition, etc.) has a folder of
numbered Python scripts that were converted from Jupyter notebook cells.
These scripts share a global namespace -- variables from earlier scripts
are available in later ones.

This wrapper:
1. Runs txn_setup/ scripts first to establish shared state (CLIENT_ID, combined_df, etc.)
2. Runs the section's scripts in order (01_*.py, 02_*.py, ...)
3. Intercepts matplotlib figure saves to capture chart PNGs
4. Returns AnalysisResult objects for the deck builder

Usage:
    wrapper = TXNSectionWrapper("general", "01_Analysis/00-Scripts/analytics/general")
    results = wrapper.run(ctx)
"""

from __future__ import annotations

import io
import os
import sys
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
            except Exception:
                pass
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

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        """Execute all scripts in the section and capture results."""
        logger.info("TXN section: {name} ({dir})", name=self.display_name, dir=self.section_dir)

        # Build shared namespace with common imports and context
        namespace = _build_namespace(ctx)

        # Run txn_setup first if not already done
        setup_dir = self.section_dir.parent / "txn_setup"
        if setup_dir.exists() and "_txn_setup_done" not in namespace:
            logger.info("  Running txn_setup...")
            _execute_scripts(setup_dir, namespace, ctx.paths.chart_dir, "txn_setup")
            namespace["_txn_setup_done"] = True

        # Run section scripts
        chart_dir = ctx.paths.chart_dir / self.section_name
        charts = _execute_scripts(self.section_dir, namespace, chart_dir, self.section_name)

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

    ns: dict[str, Any] = {
        # Common imports available to all scripts
        "pd": pd,
        "np": np,
        "plt": plt,
        "Path": Path,
        "os": os,
        "sys": sys,
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

    # Set environment variable so 02-file-config.py can read it
    os.environ["CLIENT_ID"] = ctx.client.client_id

    return ns


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
