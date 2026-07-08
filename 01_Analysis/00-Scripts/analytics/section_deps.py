"""Static cross-section dependency analysis for the TXN analytics sections.

TXN sections are folders of numbered scripts exec'd into one shared namespace;
they read variables other sections produce, guarded only by silent
`if var in globals()` skips. This module makes that coupling explicit by AST
static analysis (it never imports or runs the scripts), so the closed-loop
runner can run a section's real upstream producers before it.

`dependency_graph()` returns the full per-section graph (used by the audit CLI
`tools/module_deps.py`); `upstream_sections()` returns the ordered TXN sections
the runner must execute before a given section.
"""

from __future__ import annotations

import ast
import builtins
from pathlib import Path

_ANALYTICS = Path(__file__).resolve().parent

# Names the shared TXN namespace injects before any section runs -- see
# txn_wrapper._build_namespace() and the txn_setup/ scripts. Consuming one of
# these is NOT a cross-section dependency.
BASE_NAMES: set[str] = {
    "pd", "np", "plt", "sns", "GridSpec", "FancyBboxPatch",
    "LinearSegmentedColormap", "OrderedDict", "mdates", "pe", "mticker",
    "re", "json", "gc", "time", "Path", "os", "sys", "warnings",
    "display", "display_formatted",
    "CLIENT_ID", "CLIENT_NAME", "MONTH", "CSM",
    "odd_df", "ELIGIBLE_STATUS_CODES",
    "combined_df", "combined_df_all", "rewards_df", "rewards_df_all",
    "business_df", "personal_df", "DATASET_MONTHS", "ELIGIBLE_ACCOUNTS",
    "SKIP_SECTION", "SKIP_SCRIPT_PATTERNS",
}

_BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__builtins__"}


def _script_files(section_dir: Path) -> list[Path]:
    return sorted(p for p in section_dir.glob("*.py") if not p.name.startswith("_"))


def _names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(produced, consumed) names for one parsed script. produced is broad
    (any binding, any scope) so function-locals never look like cross-section
    deps; consumed is Name loads."""
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


def dependency_graph() -> dict:
    """{section: {depends_on_sections, cross_section_names, unresolved_names}}."""
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
        external = {n for n in external
                    if n != "_" and not (len(n) == 1 and n.islower())}
        per_section[section_dir.name] = {"produces": produced, "external": external}

    producer: dict[str, set[str]] = {}
    for sect, info in per_section.items():
        for name in info["produces"]:
            producer.setdefault(name, set()).add(sect)

    graph: dict[str, dict] = {}
    for sect, info in per_section.items():
        satisfied: dict[str, list[str]] = {}
        unresolved: list[str] = []
        for name in sorted(info["external"]):
            producers = sorted(producer.get(name, set()) - {sect})
            if producers:
                satisfied[name] = producers
            else:
                unresolved.append(name)
        graph[sect] = {
            "depends_on_sections": sorted({p for ps in satisfied.values() for p in ps}),
            "cross_section_names": satisfied,
            "unresolved_names": unresolved,
        }
    return graph


def _txn_order() -> dict[str, int]:
    from ars_analysis.analytics.txn_wrapper import TXN_SECTIONS
    return {name: meta.get("order", 500) for name, meta in TXN_SECTIONS.items()}


def upstream_sections(folder: str) -> list[str]:
    """Ordered TXN section folders to run before ``folder`` so its cross-section
    reads resolve. Transitive over TXN sections only, using the *primary*
    producer of each needed name (``general`` -- the theme/formatter/demo hub --
    wins when it's a producer, else the earliest-order TXN section), so we don't
    drag in the many sections that merely re-assign shared theme vars
    defensively. Excludes the target itself.
    """
    from ars_analysis.analytics.txn_wrapper import TXN_SECTIONS

    txn = set(TXN_SECTIONS)
    order = _txn_order()
    graph = dependency_graph()

    def primary(producers: list[str]) -> str | None:
        cands = [p for p in producers if p in txn]
        if not cands:
            return None
        if "general" in cands:
            return "general"
        return min(cands, key=lambda f: order.get(f, 500))

    seen: set[str] = set()
    stack = [folder]
    while stack:
        cur = stack.pop()
        for _name, producers in graph.get(cur, {}).get("cross_section_names", {}).items():
            p = primary(producers)
            if p and p != folder and p not in seen:
                seen.add(p)
                stack.append(p)
    return sorted(seen, key=lambda f: order.get(f, 500))
