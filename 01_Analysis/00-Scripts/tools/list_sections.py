"""Emit the unified section registry as JSON.

Printed to stdout by default. With ``--write`` it writes ``tools/sections.json``
-- the STATIC file the UI's ``/api/modules`` serves, so the web server never
imports the heavy analytics stack (matplotlib/pandas/...) just to list sections
(that import was slow-to-stalling on the work machine and left the module
picker stuck on "Loading modules…").

Regenerate whenever sections change:  python tools/list_sections.py --write
(A test asserts the committed sections.json matches the live registry.)
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS)]
    _pkg.__package__ = "ars_analysis"
    sys.modules["ars_analysis"] = _pkg

_SECTIONS_JSON = Path(__file__).resolve().parent / "sections.json"


def build_sections() -> list[dict]:
    """The section list, from the live registry."""
    from ars_analysis.analytics.section_registry import all_sections
    return [
        {
            "section_id": s.section_id,
            "product": s.product,
            "display_name": s.display_name,
            "slide_code": s.slide_code,
            "module_count": len(s.module_ids) if s.module_ids else None,
        }
        for s in all_sections()
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit the unified section registry as JSON.")
    ap.add_argument("--write", action="store_true",
                    help="write tools/sections.json (the static file /api/modules serves)")
    args = ap.parse_args()

    data = build_sections()
    if args.write:
        _SECTIONS_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {_SECTIONS_JSON} ({len(data)} sections)")
    else:
        print(json.dumps(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
