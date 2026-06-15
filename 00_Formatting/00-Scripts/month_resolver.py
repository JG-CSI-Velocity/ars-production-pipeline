"""Tolerant month-folder resolution for CSM source dumps (issue #220).

CSMs name their monthly OD-dump folders inconsistently -- ``2026.06``,
``2026-06``, ``June, 2026``, ``Jun 2026``, etc. The pipeline always speaks the
canonical ``YYYY.MM`` month, so when locating a CSM's source folder we parse
every candidate subfolder into a ``(year, month)`` pair and match on that
instead of a brittle string compare.

Pure stdlib so it can be imported and unit-tested without the formatting
pipeline's heavier dependencies.
"""

from __future__ import annotations

import calendar
import re
from pathlib import Path

# Month names and 3-letter abbreviations -> month number.
_MONTH_LOOKUP: dict[str, int] = {}
for _i in range(1, 13):
    _MONTH_LOOKUP[calendar.month_name[_i].lower()] = _i
    _MONTH_LOOKUP[calendar.month_abbr[_i].lower()] = _i

# Longest-first so "june" wins over the "jun" abbreviation.
_MONTH_WORD_RE = re.compile(
    r"\b(" + "|".join(sorted(_MONTH_LOOKUP, key=len, reverse=True)) + r")\b"
)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
# YYYY<sep>MM (sep required so a bare year doesn't grab an unrelated digit).
_NUM_YM_RE = re.compile(r"\b(20\d{2})[._\-/ ](\d{1,2})\b")
# MM<sep>YYYY (month-first numeric form, e.g. 06.2026).
_NUM_MY_RE = re.compile(r"\b(\d{1,2})[._\-/ ](20\d{2})\b")


def parse_year_month(name: str):
    """Parse a folder name into ``(year, month)``, or ``None`` if it encodes no
    month. Handles numeric (``2026.06``, ``2026-06``, ``06.2026``) and
    month-name (``June, 2026``, ``Jun 2026``) forms."""
    if not name:
        return None
    s = name.strip().lower()

    m = _NUM_YM_RE.search(s)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return (year, month)

    m = _NUM_MY_RE.search(s)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return (year, month)

    wm = _MONTH_WORD_RE.search(s)
    ym = _YEAR_RE.search(s)
    if wm and ym:
        return (int(ym.group(1)), _MONTH_LOOKUP[wm.group(1)])

    return None


def resolve_source_month_dir(base, month):
    """Return the month subfolder under ``base`` matching the canonical
    ``YYYY.MM`` ``month``, tolerating per-CSM folder naming.

    Falls back to ``base / month`` when ``base`` is missing, ``month`` is
    unparseable, or nothing matches -- so a caller's "source not found"
    message still points at the expected canonical path.
    """
    base = Path(base)
    target = parse_year_month(month)
    default = base / month
    if target is None or not base.exists():
        return default
    # Canonical folder present -> use it (no scan; preserves prior behavior).
    if default.is_dir():
        return default
    for child in sorted(base.iterdir()):
        try:
            if child.is_dir() and parse_year_month(child.name) == target:
                return child
        except OSError:
            continue
    return default
