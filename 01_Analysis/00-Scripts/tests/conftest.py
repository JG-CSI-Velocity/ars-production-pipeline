"""Pytest scaffolding for 01_Analysis modules.

Mirrors the runtime alias from 01_Analysis/run.py so tests can use
`from ars_analysis.pipeline.manifest import ...` against modules
that physically live under 00-Scripts/.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Same alias trick run.py uses to expose 00-Scripts/<pkg>/ as ars_analysis.<pkg>
if "ars_analysis" not in sys.modules:
    _ars_pkg = types.ModuleType("ars_analysis")
    _ars_pkg.__path__ = [str(_SCRIPTS_DIR)]
    _ars_pkg.__package__ = "ars_analysis"
    sys.modules["ars_analysis"] = _ars_pkg
