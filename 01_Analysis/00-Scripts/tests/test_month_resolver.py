"""Month-folder resolution for CSM source dumps (issue #220).

CSMs name their monthly OD-dump folders inconsistently ('2026.06', 'June, 2026',
...). The resolver maps the canonical YYYY.MM the pipeline speaks onto whatever
folder the CSM actually created.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MOD_PATH = (
    Path(__file__).resolve().parents[3]
    / "00_Formatting" / "00-Scripts" / "month_resolver.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("month_resolver", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mr = _load()


@pytest.mark.parametrize("name,expected", [
    ("2026.06", (2026, 6)),
    ("2026-06", (2026, 6)),
    ("2026_06", (2026, 6)),
    ("2026.6", (2026, 6)),
    ("June, 2026", (2026, 6)),
    ("June 2026", (2026, 6)),
    ("Jun 2026", (2026, 6)),
    ("06.2026", (2026, 6)),
    ("December, 2026", (2026, 12)),
    ("2026", None),          # year only -> no month
    ("ODDD archive", None),  # no date at all
    ("", None),
])
def test_parse_year_month(name, expected):
    assert mr.parse_year_month(name) == expected


def test_resolve_matches_month_name_folder(tmp_path):
    """The #220 case: canonical 2026.06 -> 'June, 2026' on disk."""
    (tmp_path / "June, 2026").mkdir()
    (tmp_path / "May, 2026").mkdir()
    assert mr.resolve_source_month_dir(tmp_path, "2026.06") == tmp_path / "June, 2026"


def test_resolve_prefers_canonical_when_present(tmp_path):
    (tmp_path / "2026.06").mkdir()
    (tmp_path / "June, 2026").mkdir()
    assert mr.resolve_source_month_dir(tmp_path, "2026.06") == tmp_path / "2026.06"


def test_resolve_handles_dashed_folder(tmp_path):
    (tmp_path / "2026-06").mkdir()
    assert mr.resolve_source_month_dir(tmp_path, "2026.06") == tmp_path / "2026-06"


def test_resolve_falls_back_when_no_match(tmp_path):
    # base exists but no matching month -> canonical path (keeps 'not found' msg honest)
    (tmp_path / "April, 2026").mkdir()
    assert mr.resolve_source_month_dir(tmp_path, "2026.06") == tmp_path / "2026.06"


def test_resolve_falls_back_when_base_missing(tmp_path):
    missing = tmp_path / "nope"
    assert mr.resolve_source_month_dir(missing, "2026.06") == missing / "2026.06"
