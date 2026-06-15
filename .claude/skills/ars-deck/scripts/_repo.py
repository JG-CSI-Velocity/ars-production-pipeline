"""Locate the repo's analysis package and install the `ars_analysis` alias.

The ARS modules import as `from ars_analysis.X import Y`, but they physically
live under `01_Analysis/00-Scripts/`. `01_Analysis/run.py` wires this alias at
runtime; these review scripts need the same trick to import deck_builder /
deck_qa / slide_spec outside the pipeline.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path


def find_scripts_dir(start: Path | None = None) -> Path:
    """Find 01_Analysis/00-Scripts by walking up from cwd, then from this file.

    Trying cwd first lets the scripts work against whatever repo checkout you're
    in; falling back to this file's own location means they still work when run
    by absolute path from an unrelated directory (the scripts live inside the
    repo at .claude/skills/ars-deck/scripts/).
    """
    starts = [start] if start else [Path.cwd(), Path(__file__).resolve().parent]
    for s in starts:
        base = s.resolve()
        for candidate_base in [base, *base.parents]:
            candidate = candidate_base / "01_Analysis" / "00-Scripts"
            if candidate.is_dir():
                return candidate
    raise SystemExit(
        "Could not find 01_Analysis/00-Scripts. Run from inside the "
        "RPE-Workflow / ars-production-pipeline repo, or pass the repo path."
    )


def install_alias(scripts_dir: Path | None = None) -> Path:
    """Put 00-Scripts on sys.path and alias it as the `ars_analysis` package."""
    scripts_dir = scripts_dir or find_scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    if "ars_analysis" not in sys.modules:
        pkg = types.ModuleType("ars_analysis")
        pkg.__path__ = [str(scripts_dir)]
        pkg.__package__ = "ars_analysis"
        sys.modules["ars_analysis"] = pkg
    return scripts_dir
