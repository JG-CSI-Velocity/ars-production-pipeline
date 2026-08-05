"""Tests for the v3 data layer: ingest parse port, merchant rules loading,
DuckDB store refresh/finalize, and the frame-level golden verify gate."""

from pathlib import Path

import pandas as pd
import pytest

from ars_engine.data import merchant_rules, txn_store
from ars_engine.data.txn_ingest import coerce_types, load_transaction_file

HEADER = "Transaction Date\tAccount\tType\tAmount\tMCC\tMerchant\tLoc1\tLoc2\tTermID\tMerchID\tInst\tCP\tCode\n"


def _tab_file(tmp_path: Path, name: str, rows: list[list[str]]) -> Path:
    p = tmp_path / name
    p.write_text(HEADER + "\n".join("\t".join(r) for r in rows) + "\n")
    return p


def _row(date, acct, ttype, amount, merchant, mcc="5411"):
    return [date, acct, ttype, str(amount), mcc, merchant, "loc1", "loc2",
            "T1", "M1", "9999", "Y", "05"]


@pytest.fixture
def cache_root(tmp_path, monkeypatch):
    monkeypatch.setenv("ARS_LOCAL_CACHE_DIR", str(tmp_path / "cache"))
    return tmp_path


class TestIngestParse:
    def test_tab_file_parses_13_cols_plus_source(self, tmp_path):
        f = _tab_file(tmp_path, "bank-trans-06302026.txt",
                      [_row("06/15/2026", "A1", "SIG", "10.00", "NETFLIX.COM")])
        df = load_transaction_file(f, log=lambda m: None)
        assert list(df.columns)[-1] == "source_file"
        assert len(df.columns) == 14
        assert df.loc[0, "merchant_name"] == "NETFLIX.COM"

    def test_comma_and_pipe_delimiters(self, tmp_path):
        for sep, name in ((",", "a-trans.csv"), ("|", "b-trans.txt")):
            p = tmp_path / name
            row = sep.join(_row("05/01/2026", "A1", "PIN", "5.00", "SHOP"))
            p.write_text("h" + sep.join(["x"] * 12) + "\n" + row + "\n")
            df = load_transaction_file(p, log=lambda m: None)
            assert len(df.columns) == 14, name
            assert df.loc[0, "amount"] == "5.00"

    def test_surviving_banner_header_dropped(self, tmp_path):
        p = tmp_path / "banner-trans.txt"
        p.write_text(
            "Report: Debit Card Transactions; Generated 2026-04-26\n"
            + HEADER
            + "\t".join(_row("04/01/2026", "A1", "SIG", "7.00", "SHOP")) + "\n"
        )
        df = load_transaction_file(p, log=lambda m: None)
        assert len(df) == 1
        assert df.loc[0, "transaction_date"] == "04/01/2026"

    def test_coerce_types(self, tmp_path):
        f = _tab_file(tmp_path, "c-trans.txt", [
            _row("06/15/2026", "A1", "SIG", "10.50", "X"),
            _row("06/16/2026", "A2", "SIG", "garbage", "Y"),
        ])
        df = coerce_types(load_transaction_file(f, log=lambda m: None), log=lambda m: None)
        assert df["amount"].tolist()[0] == 10.50
        assert pd.isna(df["amount"].tolist()[1])
        assert df["transaction_date"].dt.year.tolist() == [2026, 2026]


class TestMerchantRules:
    def test_legacy_rules_load_and_consolidate(self):
        assert merchant_rules.standardize_merchant_name("AMZN MKTP US*123") == "AMAZON"
        assert merchant_rules.standardize_merchant_name("NETFLIX.COM CA") == "NETFLIX"
        assert (
            merchant_rules.standardize_merchant_name("WM SUPERCENTER #100")
            == "WALMART (ALL LOCATIONS)"
        )
        assert merchant_rules.standardize_merchant_name(None) == "UNKNOWN MERCHANT"

    def test_build_map_skips_nan(self):
        m = merchant_rules.build_merchant_map(["NETFLIX.COM", None, "NETFLIX INC"])
        assert set(m["merchant_consolidated"]) == {"NETFLIX"}
        assert len(m) == 2


def _make_staged(tmp_path) -> list[Path]:
    f1 = _tab_file(tmp_path, "bank-trans-06302026.txt", [
        _row("06/15/2026", "A1", "SIG", "25.00", "AMZN MKTP US*1"),
        _row("06/16/2026", "A1", "SIG", "12.00", "NETFLIX.COM"),
        _row("06/17/2026", "A2", "ATM", "40.00", ""),
        _row("06/18/2026", "A2", "PIN", "60.00", "WM SUPERCENTER #100"),
        _row("06/19/2026", "A3", "SIG", "9.00", "LOCAL SHOP"),
    ])
    f2 = _tab_file(tmp_path, "bank-trans-05312026.txt", [
        _row("05/10/2026", "A1", "SIG", "30.00", "AMZN MKTP US*2"),
        _row("05/11/2026", "A3", "ACH", "100.00", ""),
    ])
    return [f1, f2]


class TestStore:
    def test_refresh_ingests_and_finalizes(self, cache_root, tmp_path):
        files = _make_staged(tmp_path)
        r = txn_store.refresh("t1", staged_files=files, log=lambda m: None)
        assert r.ingested == 2 and r.rows_added == 7 and r.finalized
        assert not r.errors

        mm = txn_store.read_table("t1", "monthly_by_merchant")
        june_amazon = mm[
            (mm["merchant_consolidated"] == "AMAZON")
            & (mm["month"].astype(str) == "2026-06-01")
        ]
        assert june_amazon["total_amount"].iloc[0] == 25.00
        # smart-unknown fallback by transaction_type
        assert "ATM WITHDRAWAL" in set(mm["merchant_consolidated"])
        assert "ACH TRANSFER (NO MERCHANT)" in set(mm["merchant_consolidated"])

    def test_refresh_is_incremental_and_replaces_changed_files(self, cache_root, tmp_path):
        files = _make_staged(tmp_path)
        txn_store.refresh("t2", staged_files=files, log=lambda m: None)
        r2 = txn_store.refresh("t2", staged_files=files, log=lambda m: None)
        assert r2.ingested == 0 and r2.skipped == 2 and not r2.finalized

        # re-deliver file2 with different content -> rows replaced, not appended
        import os
        f2 = files[1]
        f2.write_text(HEADER + "\t".join(_row("05/10/2026", "A1", "SIG", "35.00",
                                              "AMZN MKTP US*2")) + "\n")
        os.utime(f2, (f2.stat().st_mtime + 5, f2.stat().st_mtime + 5))
        r3 = txn_store.refresh("t2", staged_files=files, log=lambda m: None)
        assert r3.ingested == 1
        con = txn_store.connect("t2")
        try:
            total = con.execute("SELECT count(*) FROM transactions").fetchone()[0]
            may = con.execute(
                "SELECT sum(amount) FROM transactions WHERE source_file = ?", [f2.name]
            ).fetchone()[0]
        finally:
            con.close()
        assert total == 6  # 5 + 1 replaced (was 7)
        assert may == 35.00

    def test_global_abs_rule_uses_dataset_median(self, cache_root, tmp_path):
        f = _tab_file(tmp_path, "neg-trans-06302026.txt", [
            _row("06/15/2026", "A1", "SIG", "-25.00", "NETFLIX.COM"),
            _row("06/16/2026", "A1", "SIG", "-12.00", "NETFLIX.COM"),
            _row("06/17/2026", "A2", "SIG", "8.00", "NETFLIX.COM"),
        ])
        txn_store.refresh("t3", staged_files=[f], log=lambda m: None)
        mm = txn_store.read_table("t3", "monthly_by_merchant")
        assert mm["total_amount"].iloc[0] == 45.00  # abs applied


def _legacy_combined(files: list[Path]) -> pd.DataFrame:
    """Emulate the legacy pipeline in pure Python (05 + 07 semantics):
    concat, coerce, abs-if-median<0, merchant map over uniques + fillna,
    smart-unknown fallback by transaction_type."""
    frames = [coerce_types(load_transaction_file(f, log=lambda m: None), log=lambda m: None)
              for f in sorted(files)]
    combined = pd.concat(frames, ignore_index=True)
    if combined["amount"].median() < 0:
        combined["amount"] = combined["amount"].abs()
    raw = combined["merchant_name"]
    uniq = pd.Index(raw.dropna().unique())
    mapping = pd.Series([merchant_rules.standardize_merchant_name(m) for m in uniq], index=uniq)
    combined["merchant_consolidated"] = raw.map(mapping).fillna("UNKNOWN MERCHANT")
    mask = combined["merchant_consolidated"] == "UNKNOWN MERCHANT"
    if mask.any():
        ttype = combined.loc[mask, "transaction_type"].astype(str).str.upper().str.strip()

        def label(t):
            if not t or t in ("NAN", "NONE", ""):
                return "UNKNOWN MERCHANT"
            if "ATM" in t:
                return "ATM WITHDRAWAL"
            if "FEE" in t or t in ("SC", "NSF", "OD"):
                return "BANK FEE"
            if "ACH" in t:
                return "ACH TRANSFER (NO MERCHANT)"
            if "CHK" in t or "CHECK" in t or t == "CK":
                return "CHECK (NO MERCHANT)"
            if "XFER" in t or "TRANSFER" in t or t in ("TR", "TRF"):
                return "INTERNAL TRANSFER"
            if t in ("PIN", "SIG", "POS", "DEB"):
                return "POS TRANSACTION (NO MERCHANT)"
            if "DEP" in t or "DEPOSIT" in t:
                return "DEPOSIT (NO MERCHANT)"
            if "WD" in t or "WTHD" in t or "WITHDRAW" in t:
                return "WITHDRAWAL (NO MERCHANT)"
            return "UNKNOWN MERCHANT"

        combined.loc[mask, "merchant_consolidated"] = ttype.apply(label)
    return combined


class TestFrameGoldenVerify:
    def test_store_matches_legacy_semantics_exactly(self, cache_root, tmp_path):
        files = _make_staged(tmp_path)
        txn_store.refresh("t4", staged_files=files, log=lambda m: None)
        legacy = _legacy_combined(files)
        parquet = tmp_path / "legacy_combined.parquet"
        legacy.to_parquet(parquet, index=False)
        assert txn_store.verify("t4", parquet, log=lambda m: None) == 0

    def test_verify_catches_injected_drift(self, cache_root, tmp_path):
        files = _make_staged(tmp_path)
        txn_store.refresh("t5", staged_files=files, log=lambda m: None)
        legacy = _legacy_combined(files)
        legacy.loc[0, "amount"] = legacy.loc[0, "amount"] + 0.01  # one cent of drift
        parquet = tmp_path / "legacy_combined.parquet"
        legacy.to_parquet(parquet, index=False)
        assert txn_store.verify("t5", parquet, log=lambda m: None) > 0


class TestOrphanReconcile:
    def test_alias_swap_does_not_double_count(self, cache_root, tmp_path):
        """Re-delivery of a byte-identical file under a name that sorts BEFORE
        the existing keeper demotes the old file to alias; its rows must leave
        the store, not double every aggregate (ultrareview bug_004)."""
        rows = [_row("06/15/2026", "A1", "SIG", "25.00", "NETFLIX.COM")]
        b = _tab_file(tmp_path, "b-report-trans-06302026.txt", rows)
        txn_store.refresh("to1", staged_files=[b], log=lambda m: None)

        # identical content, alphabetically-earlier name; staging now passes
        # only the new keeper
        a = _tab_file(tmp_path, "a-report-trans-06302026.txt", rows)
        r = txn_store.refresh("to1", staged_files=[a], log=lambda m: None)
        assert r.orphans_removed == 1
        assert r.finalized

        con = txn_store.connect("to1")
        try:
            total = con.execute("SELECT count(*) FROM transactions").fetchone()[0]
            names = [x[0] for x in con.execute(
                "SELECT DISTINCT source_file FROM transactions").fetchall()]
        finally:
            con.close()
        assert total == 1  # not 2
        assert names == ["a-report-trans-06302026.txt"]
        mm = txn_store.read_table("to1", "monthly_by_merchant")
        assert mm["total_amount"].sum() == 25.00  # not 50

    def test_empty_staged_list_never_mass_deletes(self, cache_root, tmp_path):
        f = _tab_file(tmp_path, "keep-trans-06302026.txt",
                      [_row("06/15/2026", "A1", "SIG", "10.00", "X")])
        txn_store.refresh("to2", staged_files=[f], log=lambda m: None)
        r = txn_store.refresh("to2", staged_files=[], log=lambda m: None)
        assert r.orphans_removed == 0
        con = txn_store.connect("to2")
        try:
            assert con.execute("SELECT count(*) FROM transactions").fetchone()[0] == 1
        finally:
            con.close()


class TestWideFile:
    def test_more_than_13_columns_truncates_instead_of_crashing(self, tmp_path):
        """Schema drift: 14-column file keeps its rows (ultrareview bug_006;
        legacy raised ValueError and the store would silently drop the file)."""
        row = _row("06/15/2026", "A1", "SIG", "10.00", "SHOP") + ["extra"]
        p = tmp_path / "wide-trans-06302026.txt"
        p.write_text("h\t" * 13 + "h\n" + "\t".join(row) + "\n")
        df = load_transaction_file(p, log=lambda m: None)
        assert len(df.columns) == 14  # 13 named + source_file
        assert df.loc[0, "merchant_name"] == "SHOP"


class TestNullKeyParity:
    def test_null_group_keys_match_pandas_dropna(self, cache_root, tmp_path):
        """Legacy pandas groupby drops NaN keys; the store must exclude NULL
        mcc/type/account groups the same way (real data has plenty)."""
        f = _tab_file(tmp_path, "nulls-trans-06302026.txt", [
            _row("06/15/2026", "A1", "SIG", "10.00", "NETFLIX.COM"),
            _row("06/16/2026", "A1", "", "20.00", "NETFLIX.COM"),          # null type
            _row("06/17/2026", "", "SIG", "30.00", "NETFLIX.COM"),         # null account
            _row("06/18/2026", "A2", "SIG", "40.00", "NETFLIX.COM", mcc=""),  # null mcc
        ])
        txn_store.refresh("tn", staged_files=[f], log=lambda m: None)

        # store-side sanity: null keys excluded from keyed aggregates
        by_type = txn_store.read_table("tn", "monthly_by_type")
        assert by_type["txn_count"].sum() == 3
        by_mcc = txn_store.read_table("tn", "monthly_by_mcc")
        assert by_mcc["txn_count"].sum() == 3
        first_last = txn_store.read_table("tn", "account_first_last")
        assert set(first_last["primary_account_num"]) == {"A1", "A2"}

        # full golden gate against the legacy-emulated frame
        legacy = _legacy_combined([f])
        parquet = tmp_path / "legacy_nulls.parquet"
        legacy.to_parquet(parquet, index=False)
        assert txn_store.verify("tn", parquet, log=lambda m: None) == 0


class TestFrameCatalog:
    def test_txn_frames_and_unknown_key(self, cache_root, tmp_path):
        from ars_engine.core import ClientInfo, OutputPaths, PipelineContext
        from ars_engine.data.frames import FrameCatalog

        files = _make_staged(tmp_path)
        txn_store.refresh("t6", staged_files=files, log=lambda m: None)
        ctx = PipelineContext(
            client=ClientInfo(client_id="t6", client_name="T", month="2026.06"),
            paths=OutputPaths.from_dir(tmp_path),
        )
        cat = FrameCatalog(ctx)
        df = cat.get("txn.monthly_by_merchant")
        assert not df.empty
        assert cat.get("txn.monthly_by_merchant") is df  # cached
        with pytest.raises(KeyError):
            cat.get("nope.frame")
        with pytest.raises(KeyError):
            cat.get("odd.eligible")  # not loaded yet
