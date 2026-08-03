"""CLI for the cross-section dependency-DAG audit.

The analysis logic lives in the importable library
`ars_analysis.analytics.section_deps` (so the closed-loop runner can reuse it);
this is a thin human/JSON front-end.

Usage:
    python tools/module_deps.py            # human-readable report
    python tools/module_deps.py --json     # machine-readable graph
    python tools/module_deps.py --upstream txn.merchant   # run-before list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
# Expose 00-Scripts/<pkg> as ars_analysis.<pkg>, same alias run.py uses.
import types  # noqa: E402

if "ars_analysis" not in sys.modules:
    _pkg = types.ModuleType("ars_analysis")
    _pkg.__path__ = [str(_SCRIPTS)]
    _pkg.__package__ = "ars_analysis"
    sys.modules["ars_analysis"] = _pkg

from ars_analysis.analytics import section_deps  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="TXN cross-section dependency audit.")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--upstream", metavar="FOLDER",
                    help="print the ordered upstream sections for a section folder")
    args = ap.parse_args()

    if args.upstream:
        folder = args.upstream.split(".", 1)[-1]  # accept txn.merchant or merchant
        print(" -> ".join(section_deps.upstream_sections(folder)) or "(none — leaf)")
        return 0

    graph = section_deps.dependency_graph()
    if args.json:
        print(json.dumps(graph, indent=2, sort_keys=True))
        return 0

    leaves = [s for s, g in graph.items() if not g["depends_on_sections"]]
    coupled = {s: g for s, g in graph.items() if g["depends_on_sections"]}

    print("=" * 72)
    print("  TXN CROSS-SECTION DEPENDENCY DAG")
    print("=" * 72)
    print(f"\n  Leaf sections (no cross-section deps): {len(leaves)}")
    for s in sorted(leaves):
        print(f"    - {s}")
    print(f"\n  Coupled sections: {len(coupled)}")
    for s in sorted(coupled):
        g = coupled[s]
        print(f"\n    {s}  ->  depends on: {', '.join(g['depends_on_sections'])}")
        for name, producers in sorted(g["cross_section_names"].items()):
            print(f"        {name:<24s} from {', '.join(producers)}")
    print("\n" + "=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
