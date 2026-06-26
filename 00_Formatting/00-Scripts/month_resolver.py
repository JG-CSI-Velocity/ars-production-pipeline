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


def _parse_compact_digits(s: str):
    """Parse a separator-less numeric folder name into ``(year, month)``.

    Handles the date-style dumps some CSMs use, e.g. Dan's ``060126``
    (MMDDYY -> June 2026), as well as ``202606`` (YYYYMM), ``20260601``
    (YYYYMMDD) and ``06012026`` (MMDDYYYY). Returns ``None`` when the digits
    don't encode a valid month. A bare 4-digit year is intentionally not a
    month and yields ``None``.
    """
    def valid_month(m):
        return 1 <= m <= 12

    def valid_day(d):
        return 1 <= d <= 31

    def valid_year(y):
        return 2000 <= y <= 2099

    if len(s) == 6:
        # YYYYMM (e.g. 202606); years start with "20" so MM can't be 20+.
        year, month = int(s[:4]), int(s[4:6])
        if valid_year(year) and valid_month(month):
            return (year, month)
        # MMDDYY (e.g. 060126 -> June 2026).
        month, day, yy = int(s[:2]), int(s[2:4]), int(s[4:6])
        if valid_month(month) and valid_day(day):
            return (2000 + yy, month)
    elif len(s) == 8:
        # YYYYMMDD (e.g. 20260601).
        year, month, day = int(s[:4]), int(s[4:6]), int(s[6:8])
        if valid_year(year) and valid_month(month) and valid_day(day):
            return (year, month)
        # MMDDYYYY (e.g. 06012026).
        month, day, year = int(s[:2]), int(s[2:4]), int(s[4:8])
        if valid_month(month) and valid_day(day) and valid_year(year):
            return (year, month)
    return None


def parse_year_month(name: str):
    """Parse a folder name into ``(year, month)``, or ``None`` if it encodes no
    month. Handles numeric (``2026.06``, ``2026-06``, ``06.2026``), compact
    date (``060126``, ``202606``) and month-name (``June, 2026``, ``Jun
    2026``) forms."""
    if not name:
        return None
    s = name.strip().lower()

    # Separator-less numeric dumps (e.g. Dan's MMDDYY folders); the regexes
    # below all require a separator, so handle these first.
    if s.isdigit():
        compact = _parse_compact_digits(s)
        if compact:
            return compact

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
