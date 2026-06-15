#!/usr/bin/env python3
"""Run the ARS deck QA gate on any .pptx and print findings by severity.

Wraps `ars_analysis.output.deck_qa.audit_deck` with the import alias so you can
QA a deck without the boilerplate. deck_qa is conservative (tuned so known-good
decks pass clean), so anything it flags is worth looking at.

    python run_deck_qa.py path/to/deck.pptx
"""
from __future__ import annotations

import sys
from pathlib import Path

from _repo import install_alias

install_alias()
from ars_analysis.output.deck_qa import audit_deck  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pptx = Path(sys.argv[1])
    if not pptx.exists():
        print(f"No such file: {pptx}")
        return 2

    res = audit_deck(str(pptx))
    counts = res.get("counts", {})
    print(f"{res.get('file')}  |  slides={res.get('slides')}  |  "
          f"passed={res.get('passed')}")
    print(f"CRITICAL={counts.get('CRITICAL', 0)}  "
          f"MAJOR={counts.get('MAJOR', 0)}  MINOR={counts.get('MINOR', 0)}\n")

    order = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}
    findings = sorted(
        res.get("findings", []),
        key=lambda f: (order.get(f.get("severity"), 9), f.get("slide", 0)),
    )
    for f in findings:
        slide = f.get("slide", 0)
        loc = f"slide {slide}" if slide else "deck"
        print(f"  [{f.get('severity'):8}] {f.get('code'):14} {loc:9} :: {f.get('message')}")

    if not findings:
        print("  (no findings — clean)")
    return 0 if res.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
