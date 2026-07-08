"""The UI serves a STATIC ``tools/sections.json`` for ``/api/modules`` (no live
import of the analytics stack -- that subprocess stalled the module picker on
the work machine). This test guarantees the committed file never drifts from the
live registry: if a section is added/renamed/removed, regenerate it with

    python 01_Analysis/00-Scripts/tools/list_sections.py --write
"""
from __future__ import annotations

import json
from pathlib import Path

from tools import list_sections

_SECTIONS_JSON = Path(__file__).resolve().parents[1] / "tools" / "sections.json"


def test_committed_sections_json_matches_registry():
    committed = json.loads(_SECTIONS_JSON.read_text(encoding="utf-8"))
    live = list_sections.build_sections()
    assert committed == live, (
        "tools/sections.json is stale -- regenerate with: "
        "python 01_Analysis/00-Scripts/tools/list_sections.py --write"
    )
