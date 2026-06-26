"""Tests for tolerant month-folder resolution.

Issue #232 follow-up: Dan's monthly data-dump folders are named in a
compact, separator-less ``MMDDYY`` form (``060126`` = June 1, 2026) rather
than the ``2026.06`` / ``June 2026`` forms James and Jordan use. The
resolver must recognise that format so the normal formatting flow can find
the source folder.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "00-Scripts"))

from month_resolver import parse_year_month, resolve_source_month_dir  # noqa: E402


# --- Dan's compact MMDDYY folders ---------------------------------------

def test_parses_mmddyy():
    assert parse_year_month("010126") == (2026, 1)
    assert parse_year_month("060126") == (2026, 6)
    assert parse_year_month("120126") == (2026, 12)


def test_parses_yyyymm_compact():
    assert parse_year_month("202606") == (2026, 6)


def test_parses_eight_digit_dates():
    assert parse_year_month("20260601") == (2026, 6)  # YYYYMMDD
    assert parse_year_month("06012026") == (2026, 6)  # MMDDYYYY


# --- must not over-match -------------------------------------------------

def test_year_only_folders_return_none():
    assert parse_year_month("2024") is None
    assert parse_year_month("2025") is None


def test_invalid_compact_digits_return_none():
    assert parse_year_month("130126") is None  # month 13
    assert parse_year_month("999999") is None


# --- existing James/Jordan formats still work ----------------------------

def test_existing_formats_unaffected():
    assert parse_year_month("2026.06") == (2026, 6)
    assert parse_year_month("2026-06") == (2026, 6)
    assert parse_year_month("06.2026") == (2026, 6)
    assert parse_year_month("June 2026") == (2026, 6)
    assert parse_year_month("Jun 2026") == (2026, 6)


# --- end-to-end folder resolution ----------------------------------------

def test_resolve_picks_mmddyy_folder(tmp_path):
    for name in ("2024", "2025", "010126", "050126", "060126"):
        (tmp_path / name).mkdir()

    resolved = resolve_source_month_dir(tmp_path, "2026.06")

    assert resolved == tmp_path / "060126"
