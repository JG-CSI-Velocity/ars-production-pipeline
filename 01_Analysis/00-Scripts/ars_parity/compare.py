"""Compare two run snapshots (golden vs candidate) under a tolerance policy.

Policy:
- Strings, ints, booleans, row counts, sheet/slide inventories: EXACT.
- Floats: relative tolerance, default 1e-9 (summation-order noise only).
- Sections whose aggregation moved to DuckDB may declare per-column
  relaxations -- every relaxation is explicit, named, and reviewable.

Every mismatch is reported at (surface / sheet-or-figure / row-key / column)
granularity so a diff is actionable, not just a red X.
"""

from __future__ import annotations

import fnmatch
import math
from dataclasses import dataclass, field
from typing import Any

from ars_parity.capture import RunSnapshot

DEFAULT_RTOL = 1e-9


@dataclass
class ComparePolicy:
    rtol: float = DEFAULT_RTOL
    atol: float = 0.0
    # {"sheet-glob": {"column-name": rtol}} -- declared per-section relaxations
    column_overrides: dict[str, dict[str, float]] = field(default_factory=dict)
    # Slide-id prefixes to include (empty = everything). Used for per-section
    # checks, e.g. ("TXN-MERCH-",) or ("A7.", "DCTR-").
    slide_prefixes: tuple[str, ...] = ()

    def rtol_for(self, sheet: str, column: str) -> float:
        for pattern, cols in self.column_overrides.items():
            if fnmatch.fnmatch(sheet, pattern) and column in cols:
                return cols[column]
        return self.rtol


@dataclass
class Diff:
    surface: str  # "slides" | "sheet" | "figure"
    where: str    # sheet name / figure stem / slide_id
    key: str      # row key / path within figure
    column: str
    golden: Any
    candidate: Any

    def __str__(self) -> str:
        return (
            f"[{self.surface}] {self.where} :: {self.key} :: {self.column}: "
            f"golden={self.golden!r} candidate={self.candidate!r}"
        )


def _floats_match(a: float, b: float, rtol: float, atol: float) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    return math.isclose(a, b, rel_tol=rtol, abs_tol=atol)


def _values_match(a: Any, b: Any, rtol: float, atol: float) -> bool:
    if a is None and b is None:
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, int) and isinstance(b, int):
            return a == b
        return _floats_match(float(a), float(b), rtol, atol)
    return a == b


def _included(slide_or_sheet: str, policy: ComparePolicy) -> bool:
    if not policy.slide_prefixes:
        return True
    return any(slide_or_sheet.startswith(p) for p in policy.slide_prefixes)


def _compare_tables(
    name: str,
    golden: dict[str, Any],
    candidate: dict[str, Any],
    policy: ComparePolicy,
    diffs: list[Diff],
) -> None:
    g_cols, c_cols = golden["columns"], candidate["columns"]
    if g_cols != c_cols:
        diffs.append(Diff("sheet", name, "<columns>", "", g_cols, c_cols))
        return
    g_rows, c_rows = golden["rows"], candidate["rows"]
    if len(g_rows) != len(c_rows):
        diffs.append(Diff("sheet", name, "<row-count>", "", len(g_rows), len(c_rows)))
    for i, (gr, cr) in enumerate(zip(g_rows, c_rows)):
        for col_idx, col in enumerate(g_cols):
            gv, cv = gr[col_idx], cr[col_idx]
            if not _values_match(gv, cv, policy.rtol_for(name, col), policy.atol):
                # Row key: first column value (tables are pre-sorted, so the
                # leading cells identify the row for a human reader)
                diffs.append(Diff("sheet", name, f"row[{i}]={gr[0]!r}", col, gv, cv))


def _walk(prefix: str, g: Any, c: Any, policy: ComparePolicy, diffs: list[Diff], where: str) -> None:
    """Structural compare for figure-data dicts/lists."""
    if isinstance(g, dict) and isinstance(c, dict):
        for k in g.keys() | c.keys():
            if k not in g or k not in c:
                diffs.append(Diff("figure", where, prefix, str(k), k in g, k in c))
                continue
            _walk(f"{prefix}.{k}" if prefix else str(k), g[k], c[k], policy, diffs, where)
        return
    if isinstance(g, list) and isinstance(c, list):
        if len(g) != len(c):
            diffs.append(Diff("figure", where, prefix, "<len>", len(g), len(c)))
            return
        for i, (gv, cv) in enumerate(zip(g, c)):
            _walk(f"{prefix}[{i}]", gv, cv, policy, diffs, where)
        return
    if not _values_match(g, c, policy.rtol, policy.atol):
        diffs.append(Diff("figure", where, prefix, "", g, c))


def compare_snapshots(
    golden: RunSnapshot, candidate: RunSnapshot, policy: ComparePolicy | None = None
) -> list[Diff]:
    policy = policy or ComparePolicy()
    diffs: list[Diff] = []

    # 1. Slide inventory: every golden slide (in scope) must exist and succeed.
    for sid, ginfo in golden.slides.items():
        if not _included(sid, policy):
            continue
        cinfo = candidate.slides.get(sid)
        if cinfo is None:
            diffs.append(Diff("slides", sid, "<presence>", "", "present", "MISSING"))
            continue
        for key in ("success", "has_chart", "has_excel"):
            if ginfo.get(key) != cinfo.get(key):
                diffs.append(Diff("slides", sid, key, "", ginfo.get(key), cinfo.get(key)))

    # 2. Excel sheets (named "{slide_id}_{sheet}").
    for name, gtable in golden.sheets.items():
        if not _included(name, policy):
            continue
        ctable = candidate.sheets.get(name)
        if ctable is None:
            diffs.append(Diff("sheet", name, "<presence>", "", "present", "MISSING"))
            continue
        _compare_tables(name, gtable, ctable, policy, diffs)

    # 3. Figure numeric payloads.
    for stem, gfig in golden.figures.items():
        if not _included(stem, policy):
            continue
        cfig = candidate.figures.get(stem)
        if cfig is None:
            diffs.append(Diff("figure", stem, "<presence>", "", "present", "MISSING"))
            continue
        _walk("", gfig, cfig, policy, diffs, stem)

    # 4. Symmetry: candidate-only surfaces are diffs too. Without this, a new
    #    engine emitting extra/renamed slides -- or a golden whose capture
    #    quietly lost figures -- would still read as a clean pass.
    for surface, gkeys, ckeys in (
        ("slides", golden.slides, candidate.slides),
        ("sheet", golden.sheets, candidate.sheets),
        ("figure", golden.figures, candidate.figures),
    ):
        for key in ckeys:
            if key not in gkeys and _included(key, policy):
                diffs.append(Diff(surface, key, "<presence>", "", "ABSENT", "extra-in-candidate"))

    return diffs


def summarize(diffs: list[Diff], limit: int = 50) -> str:
    if not diffs:
        return "PARITY PASS -- no differences"
    lines = [f"PARITY FAIL -- {len(diffs)} difference(s)"]
    lines += [f"  {d}" for d in diffs[:limit]]
    if len(diffs) > limit:
        lines.append(f"  ... and {len(diffs) - limit} more")
    return "\n".join(lines)
