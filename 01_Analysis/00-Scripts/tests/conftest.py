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

# Make the tests dir importable so smoke tests can share tests/_fixtures.py.
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

# Same alias run.py uses, via the one canonical bootstrap.
import ars_bootstrap  # noqa: E402

ars_bootstrap.ensure_ars_analysis()
