"""The two `format_odd.py` copies must stay identical.

The formatting stage (`00_Formatting`) and the analysis stage (`01_Analysis`)
each ship their own `shared/format_odd.py` because the numbered stage folders are
deliberately self-contained (they mirror `M:\\ARS\\` and must run independently,
so neither imports across the other's path). That independence is worth keeping —
but the two copies had silently diverged in implementation style, which is exactly
how a bug fixed in one would live on in the other.

They are now byte-identical. This test fails the moment they drift again, forcing
any real change to `format_odd` to be applied to BOTH copies.
"""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_FORMATTING = _REPO / "00_Formatting" / "00-Scripts" / "shared" / "format_odd.py"
_ANALYSIS = _REPO / "01_Analysis" / "00-Scripts" / "shared" / "format_odd.py"


def test_format_odd_copies_are_identical():
    assert _FORMATTING.exists() and _ANALYSIS.exists()
    fmt = _FORMATTING.read_text(encoding="utf-8")
    ana = _ANALYSIS.read_text(encoding="utf-8")
    assert fmt == ana, (
        "00_Formatting and 01_Analysis copies of shared/format_odd.py have diverged. "
        "They must stay identical — apply your change to BOTH files (the stages are "
        "self-contained and cannot import across each other)."
    )
