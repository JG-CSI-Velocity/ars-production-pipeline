"""One place that wires the ``ars_analysis`` package alias.

The analysis code imports ``from ars_analysis.X import Y`` while the modules
physically live in this folder (01_Analysis/00-Scripts). Until the repo is a
real installed package, every entry point needs the same two steps: put this
folder on sys.path and register the ``ars_analysis`` alias. This module is
that logic, exactly once. Entry points do::

    sys.path.insert(0, str(<path to 00-Scripts>))
    import ars_bootstrap
    ars_bootstrap.ensure_ars_analysis()

Hand-copied variants of this shim used to live in eight files and drifted;
one carried a ``__path__`` pointing at a folder that does not exist.
"""
import sys
import types
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def ensure_ars_analysis() -> None:
    """Idempotently register 00-Scripts as the ``ars_analysis`` package."""
    scripts = str(SCRIPTS_DIR)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    if "ars_analysis" not in sys.modules:
        pkg = types.ModuleType("ars_analysis")
        pkg.__path__ = [scripts]
        pkg.__package__ = "ars_analysis"
        sys.modules["ars_analysis"] = pkg
