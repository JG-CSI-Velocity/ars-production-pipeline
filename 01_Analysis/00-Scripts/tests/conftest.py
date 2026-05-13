"""Pytest scaffolding for 01_Analysis modules.

Adds the 00-Scripts directory to sys.path so tests can import
`ars_analysis.pipeline.manifest` etc. directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
