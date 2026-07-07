"""Tests for the analysis-side TXN auto-staging step.

Exercises the staging orchestrator and the ensure_txn_staged gate with a
synthetic source dump + destination, so no M:\\ARS layout is needed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from ars_analysis.pipeline.steps import txn_stage
from ars_analysis.pipeline.steps.txn_stage import _has_txn_file, _is_txn_file, _match_csm_source

# Load the standalone formatting staging module the same way the step does.
_FMT_SCRIPTS = Path(__file__).resolve().parents[3] / "00_Formatting" / "00-Scripts"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load("month_resolver", _FMT_SCRIPTS / "month_resolver.py")
txn_staging = _load("txn_staging", _FMT_SCRIPTS / "txn_staging.py")


def test_stage_txn_files_copies_loose_file(tmp_path):
    source = tmp_path / "OD Data Dumps" / "2026.06"
    source.mkdir(parents=True)
    (source / "1234_29335_velocity.ars.transactions.2026.06.01.txt").write_text("row\n")
    txn_base = tmp_path / "TXN Files"

    staged, errors = txn_staging.stage_txn_files(
        "JamesG", "1234", "2026.06", str(tmp_path / "OD Data Dumps"), str(txn_base),
    )
    assert errors == 0 and staged == 1
    dest = txn_base / "JamesG" / "1234"
    assert _has_txn_file(dest)


def test_stage_is_idempotent(tmp_path):
    source = tmp_path / "OD Data Dumps" / "2026.06"
    source.mkdir(parents=True)
    (source / "1234_transaction").write_text("row\n")  # extensionless variant
    txn_base = tmp_path / "TXN Files"

    first, _ = txn_staging.stage_txn_files(
        "JamesG", "1234", "2026.06", str(tmp_path / "OD Data Dumps"), str(txn_base))
    second, _ = txn_staging.stage_txn_files(
        "JamesG", "1234", "2026.06", str(tmp_path / "OD Data Dumps"), str(txn_base))
    assert first == 1        # copied on the first pass
    assert second == 0       # skipped (same name+size) on the second


def test_is_txn_file_excludes_odd_and_strays(tmp_path):
    # Real transaction files -> accepted.
    for good in (
        "1776_30825_[2026.06.01][11.00.31]_monthlytran.txt",
        "coasthills-trans-02282026.txt",
        "1441_debit card transaction monthly.csv",
        "1745_29335_[2026.06.01][07.15.33]_transaction",  # extensionless
    ):
        (tmp_path / good).write_text("x\n")
        assert _is_txn_file(tmp_path / good), good

    # An ODD export dropped in the TXN folder -> rejected (issue #247).
    odd = tmp_path / "1776-2026-07-CoastHills CU-ODD (Jul23 forward) (070226_101912)_V2_1_1.csv"
    odd.write_text("x\n")
    assert not _is_txn_file(odd)

    # A stray non-transaction csv (no 'tran') -> rejected.
    stray = tmp_path / "1776_summary.csv"
    stray.write_text("x\n")
    assert not _is_txn_file(stray)


def test_match_csm_source_fuzzy():
    sources = {"JamesG": Path("/x/JamesG"), "Aaron": Path("/x/Aaron")}
    assert _match_csm_source("JamesG", sources) == Path("/x/JamesG")   # exact
    assert _match_csm_source("James", sources) == Path("/x/JamesG")    # startswith
    assert _match_csm_source("Nobody", sources) is None


def _ctx(csm, client_id, month):
    from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
    return PipelineContext(
        client=ClientInfo(client_id=client_id, client_name=client_id, month=month, assigned_csm=csm),
        paths=OutputPaths(),
    )


def test_ensure_txn_staged_fast_path_when_present(tmp_path, monkeypatch):
    # Point the ARS base at tmp_path and pre-stage a file.
    monkeypatch.setattr(txn_stage, "_ars_base", lambda: tmp_path)
    client_dir = tmp_path / "00_Formatting" / "02-Data-Ready for Analysis" / "TXN Files" / "JamesG" / "1234"
    client_dir.mkdir(parents=True)
    (client_dir / "1234_trans.txt").write_text("row\n")

    # Should return without needing any config/source (fast path).
    txn_stage.ensure_txn_staged(_ctx("JamesG", "1234", "2026.06"))


def test_ensure_txn_staged_errors_clearly_when_unresolvable(tmp_path, monkeypatch):
    # ARS base with no config -> cannot resolve source -> actionable error.
    monkeypatch.setattr(txn_stage, "_ars_base", lambda: tmp_path)
    with pytest.raises(FileNotFoundError) as exc:
        txn_stage.ensure_txn_staged(_ctx("JamesG", "9999", "2026.06"))
    msg = str(exc.value)
    assert "9999" in msg and "--with-trans" in msg
