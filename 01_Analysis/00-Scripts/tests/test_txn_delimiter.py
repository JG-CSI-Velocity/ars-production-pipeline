"""Delimiter auto-detection for TXN files (issue #137).

Client 1585's transaction files are pipe-delimited; main's loader only tried
tab and comma, so they silently parsed as a single column of raw lines and
every downstream section failed. These tests pin that the sniffer + fallback
handle tab / comma / pipe / semicolon and always recover the 13-column shape.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

_MODULE = (
    Path(__file__).resolve().parents[1]
    / "analytics" / "txn_setup" / "04-define-data-func.py"
)


def _load_module() -> dict:
    # The tail of this script is notebook-style top-level code that runs the
    # actual file load against shared-namespace globals (USE_PARQUET_CACHE,
    # files_to_load, ...). Exec only the definitions prefix to get the helpers.
    src = _MODULE.read_text(encoding="utf-8")
    head = src.split("# Load data -- Parquet cache or raw files")[0]
    ns: dict = {"pd": pd, "Path": Path}
    exec(compile(head, str(_MODULE), "exec"), ns)  # noqa: S102
    return ns


_DELIMS = {"tab": "\t", "comma": ",", "pipe": "|", "semicolon": ";"}


@pytest.mark.parametrize("name,sep", list(_DELIMS.items()))
def test_peek_delimiter_detects_each(name, sep, tmp_path):
    ns = _load_module()
    rows = [sep.join(f"c{i}" for i in range(13)) for _ in range(10)]
    f = tmp_path / f"{name}.txt"
    f.write_text("HEADER LINE TO SKIP\n" + "\n".join(rows), encoding="utf-8")
    assert ns["_peek_delimiter"](str(f)) == sep, name


def _data_cols(df):
    # load_transaction_file appends a 'source_file' metadata column; the 13
    # parsed fields are the integer-named columns.
    return [c for c in df.columns if c != "source_file"]


@pytest.mark.parametrize("name,sep", list(_DELIMS.items()))
def test_load_recovers_13_columns_any_delimiter(name, sep, tmp_path):
    ns = _load_module()
    # skiprows=1 drops the banner line; 5 data rows of 13 fields each.
    data = [sep.join(f"v{r}_{c}" for c in range(13)) for r in range(5)]
    f = tmp_path / f"{name}.txt"
    f.write_text("BANNER ROW\n" + "\n".join(data), encoding="utf-8")
    df = ns["load_transaction_file"](str(f))
    assert len(_data_cols(df)) == 13, (name, df.shape)
    assert len(df) == 5, (name, len(df))


def test_pipe_no_longer_collapses_to_one_column(tmp_path):
    """Regression for #137: a pipe file must not load as a single column."""
    ns = _load_module()
    data = ["|".join(f"f{c}" for c in range(13)) for _ in range(6)]
    f = tmp_path / "1585_pipe.txt"
    f.write_text("META BANNER\n" + "\n".join(data), encoding="utf-8")
    df = ns["load_transaction_file"](str(f))
    assert len(_data_cols(df)) == 13  # was 1 before the fix


def test_single_bad_line_does_not_disqualify_correct_delimiter(tmp_path):
    # 1192 (issue #251 follow-up): files are tab-clean for millions of rows
    # except ONE line with an embedded tab (14 fields instead of 13). The old
    # logic rejected tab entirely, fell through comma/semicolon, and settled
    # for a 1-column pipe parse of garbage. The correct delimiter must win by
    # skipping the malformed line(s).
    ns = _load_module()
    good = ["\t".join(f"v{r}_{c}" for c in range(13)) for r in range(50)]
    bad = "\t".join(f"bad_{c}" for c in range(14))  # one extra field
    rows = good[:25] + [bad] + good[25:]
    f = tmp_path / "one_bad_line.txt"
    f.write_text("BANNER ROW\n" + "\n".join(rows), encoding="utf-8")

    df = ns["load_transaction_file"](str(f))

    assert len(_data_cols(df)) == 13
    assert len(df) == 50  # bad line skipped, all clean rows kept


def test_hopeless_file_still_falls_back_like_before(tmp_path):
    # A file that no delimiter can shape into 13 columns keeps the old
    # closest-match fallback behavior (with its loud warning).
    ns = _load_module()
    f = tmp_path / "hopeless.txt"
    f.write_text("BANNER\n" + "\n".join("just one field" for _ in range(10)),
                 encoding="utf-8")
    df = ns["load_transaction_file"](str(f))
    assert len(_data_cols(df)) == 1
