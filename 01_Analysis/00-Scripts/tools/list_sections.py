"""Print the unified section registry as JSON -- the source for the UI module
picker (GET /api/modules). Kept as a subprocess so the web server doesn't import
the heavy analytics stack; the registry stays the single source of truth.
"""

from __future__ import annotations

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

from ars_analysis.analytics.section_registry import all_sections  # noqa: E402


def main() -> int:
    out = [
        {
            "section_id": s.section_id,
            "product": s.product,
            "display_name": s.display_name,
            "slide_code": s.slide_code,
            "module_count": len(s.module_ids) if s.module_ids else None,
        }
        for s in all_sections()
    ]
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
