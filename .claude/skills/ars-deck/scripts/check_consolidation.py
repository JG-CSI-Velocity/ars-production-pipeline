#!/usr/bin/env python3
"""Show what CURRENT code does to slides — the stale-deck test.

When a produced deck looks wrong (too many slides, un-merged 2x1s, leaked
{tokens}), the first question is NOT "what do I fix" but "does this bug still
exist in current code, or is the .pptx just old?". The consolidation and spec
functions are pure, so exercise them directly against realistic slide_ids.

If this prints a tight, correct result, the bad deck is STALE -> rebuild, don't
edit. If it reproduces the problem, you have a failing case to turn into a test.

    python check_consolidation.py
"""
from __future__ import annotations

from types import SimpleNamespace

from _repo import install_alias

install_alias()
from ars_analysis.output.deck_builder import (  # noqa: E402
    ATTRITION_APPENDIX_IDS,
    ATTRITION_MERGES,
    MAIN_MAILER_MONTHS,
    _consolidate,
    _consolidate_mailer,
)
from ars_analysis.output.slide_spec import get_spec  # noqa: E402


def R(sid: str) -> SimpleNamespace:
    """A minimal AnalysisResult stand-in with the fields consolidation reads."""
    return SimpleNamespace(
        slide_id=sid, title=sid, success=True, slide_type="chart",
        chart_path=None, extra_charts=None, bullets=[], kpis={},
        excel_data=None, notes="",
    )


def check_mailer() -> None:
    months = ["Jun23", "Aug23", "Oct23", "Dec23", "Feb24", "Apr24", "Jun24",
              "Aug24", "Oct24", "Dec24", "Feb25", "Apr25", "Jun25", "Aug25",
              "Oct25", "Dec25", "Feb26", "Apr26"]
    results = []
    for m in months:
        results += [R(f"A13.{m}"), R(f"A16.7.{m}"), R(f"A12.{m}.Swipes"),
                    R(f"A12.{m}.Spend"), R(f"A15.{m}")]
    results += [R("A13.Agg"), R("A13.5"), R("A13.6"), R("A14.1")]

    main, anc = _consolidate_mailer(results)
    print(f"MAILER ({len(months)} waves, {len(results)} raw results)")
    print(f"  main deck     = {len(main):>3} slides   (expect ~{MAIN_MAILER_MONTHS*2 + 3})")
    print(f"  ancillary     = {len(anc):>3} slides   (older waves -> Mailer_Performance.pptx)")
    print(f"  main slide_ids: {[r.slide_id for r in main]}")
    if len(main) > MAIN_MAILER_MONTHS * 2 + 6:
        print("  !! main deck looks UN-consolidated -- bug may be real in current code")
    print()


def check_attrition() -> None:
    ids = ["A9.0", "A9.0b", "A9.1", "A9.12", "A9.4b", "A9.4c", "A9.3", "A9.6", "A9.9"]
    main, app = _consolidate([R(i) for i in ids], ATTRITION_MERGES, ATTRITION_APPENDIX_IDS)
    merged = [getattr(r, "title", "") for r in main
              if "Closures: Annual" in str(getattr(r, "title", ""))]
    print(f"ATTRITION ({len(ids)} raw -> main={len(main)}, appendix={len(app)})")
    print(f"  A9.1+A9.12 merged to 2x1: {bool(merged)}")
    print(f"  appendix ids: {[getattr(r, 'slide_id', '?') for r in app]}")
    print()


def check_spec_tokens() -> None:
    print("SLIDE SPEC (mailer per-month template must NOT match non-month ids)")
    for sid in ["A13.5", "A13.Agg", "A13.6", "A13.Jun26", "A13.Apr26"]:
        s = get_spec("mailer", sid)
        verdict = "MATCH" if s else "None (no token leak)"
        flag = "  !! over-match -> tokens will leak" if (s and not sid[4:5].isalpha()) else ""
        print(f"  get_spec(mailer, {sid:9}) -> {verdict}{flag}")
    print()


if __name__ == "__main__":
    check_mailer()
    check_attrition()
    check_spec_tokens()
