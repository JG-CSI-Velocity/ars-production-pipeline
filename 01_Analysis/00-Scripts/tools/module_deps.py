"""Cross-section dependency-DAG audit for the TXN analytics sections.

The TXN sections are folders of numbered scripts `exec()`'d into one shared
namespace (see `analytics/txn_wrapper.py`). Scripts freely read variables that
*other* sections produce, guarded only by `if var in globals()` silent skips.
That coupling is invisible until a section is run in isolation and quietly
emits an incomplete deck.

This tool makes the graph explicit. For every section folder it statically
(AST) computes:
  - names the section PRODUCES (assigned anywhere in its scripts), and
  - names it CONSUMES but never produces and that the shared setup doesn't
    provide -> its external dependencies.
It then maps each external dependency to the section(s) that produce it, giving
the real dependency DAG plus a list of "true leaf" sections (no cross-section
deps) that are safe to run standalone.

Usage:
    python tools/module_deps.py            # human-readable report
    python tools/module_deps.py --json     # machine-readable graph

This is read-only static analysis; it never imports or runs the scripts.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import json
import sys
from pathlib import Path

_ANALYTICS = Path(__file__).resolve().parents[1] / "analytics"

# Names the shared TXN namespace injects before any section runs -- see
# txn_wrapper._build_namespace() and the txn_setup/ scripts. A consume of one
# of these is NOT a cross-section dependency.
BASE_NAMES: set[str] = {
    # _build_namespace imports + shims
    "pd", "np", "plt", "sns", "GridSpec", "FancyBboxPatch",
    "LinearSegmentedColormap", "OrderedDict", "mdates", "pe", "mticker",
    "re", "json", "gc", "time", "Path", "os", "sys", "warnings",
    "display", "display_formatted",
    # client scalars + ODD
    "CLIENT_ID", "CLIENT_NAME", "MONTH", "CSM",
    "odd_df", "ELIGIBLE_STATUS_CODES",
    # txn_setup shared products (built once, available to every section)
    "combined_df", "combined_df_all", "rewards_df", "rewards_df_all",
    "business_df", "personal_df", "DATASET_MONTHS", "ELIGIBLE_ACCOUNTS",
    "SKIP_SECTION", "SKIP_SCRIPT_PATTERNS",
}

_BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__builtins__"}


def _script_files(section_dir: Path) -> list[Path]:
    return sorted(p for p in section_dir.glob("*.py") if not p.name.startswith("_"))


def _names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Return (produced, consumed) names for one parsed script.

    produced = anything bound in any scope (Store targets, args, func/class
    names, import aliases) -- deliberately broad so function-local vars don't
    show up as cross-section deps. consumed = Name loads.
    """
    produced: set[str] = set()
    consumed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                produced.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                consumed.add(node.id)
        elif isinstance(node, ast.arg):
            produced.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            produced.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                produced.add((alias.asname or alias.name).split(".")[0])
    return produced, consumed


def analyze() -> dict:
    """Return {section: {produces, consumes_external, satisfied_by}} plus the
    reverse producer map."""
    if not _ANALYTICS.exists():
        raise SystemExit(f"analytics dir not found: {_ANALYTICS}")

    per_section: dict[str, dict[str, set[str]]] = {}
    for section_dir in sorted(_ANALYTICS.iterdir()):
        if not section_dir.is_dir() or section_dir.name.startswith((".", "_")):
            continue
        scripts = _script_files(section_dir)
        if not scripts:
            continue
        produced: set[str] = set()
        consumed: set[str] = set()
        for sp in scripts:
            try:
                tree = ast.parse(sp.read_text(encoding="utf-8"), str(sp))
            except SyntaxError:
                continue
            p, c = _names(tree)
            produced |= p
            consumed |= c
        external = consumed - produced - BASE_NAMES - _BUILTINS
        # Drop obvious leaked locals (single-letter loop/except vars like the
        # `e` in `except ... as e`) that the shared-namespace exec model surfaces
        # as cross-section but which are never a real data dependency.
        external = {n for n in external
                    if n != "_" and not (len(n) == 1 and n.islower())}
        per_section[section_dir.name] = {"produces": produced, "external": external}

    # Reverse map: name -> sections that produce it.
    producer: dict[str, set[str]] = {}
    for sect, info in per_section.items():
        for name in info["produces"]:
            producer.setdefault(name, set()).add(sect)

    graph: dict[str, dict] = {}
    for sect, info in per_section.items():
        satisfied_by: dict[str, list[str]] = {}
        unresolved: list[str] = []
        for name in sorted(info["external"]):
            producers = sorted(producer.get(name, set()) - {sect})
            if producers:
                satisfied_by[name] = producers
            else:
                unresolved.append(name)
        graph[sect] = {
            "depends_on_sections": sorted(
                {p for ps in satisfied_by.values() for p in ps}
            ),
            "cross_section_names": satisfied_by,
            "unresolved_names": unresolved,
        }
    return graph


def main() -> int:
    ap = argparse.ArgumentParser(description="TXN cross-section dependency audit.")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    graph = analyze()

    if args.json:
        print(json.dumps(graph, indent=2, sort_keys=True))
        return 0

    leaves = [s for s, g in graph.items() if not g["depends_on_sections"]]
    coupled = {s: g for s, g in graph.items() if g["depends_on_sections"]}

    print("=" * 72)
    print("  TXN CROSS-SECTION DEPENDENCY DAG")
    print("=" * 72)
    print(f"\n  Leaf sections (no cross-section deps -> safe to run standalone): "
          f"{len(leaves)}")
    for s in sorted(leaves):
        print(f"    - {s}")
    print(f"\n  Coupled sections (need upstream producers): {len(coupled)}")
    for s in sorted(coupled):
        g = coupled[s]
        print(f"\n    {s}  ->  depends on: {', '.join(g['depends_on_sections'])}")
        for name, producers in sorted(g["cross_section_names"].items()):
            print(f"        {name:<24s} from {', '.join(producers)}")
        if g["unresolved_names"]:
            print(f"        (unresolved / external-lib globals: "
                  f"{', '.join(g['unresolved_names'][:12])}"
                  f"{' …' if len(g['unresolved_names']) > 12 else ''})")
    print("\n" + "=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
