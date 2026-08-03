"""Naming-detection tests for TXN file discovery (GitHub issue #251).

Ascend FCU (1192) delivers extensionless files named
`1192_35687_[2026.07.05][10.03.04]_monthlydebittransactions`, which the old
rule (`.txt`/`.csv`, or exactly `_transaction`) silently rejected in both the
formatting gather and the analysis loader. These tests lock the broadened
matcher against every naming variant seen in the wild (issues #45 and #251).
"""

from __future__ import annotations

from pathlib import Path

from ars_analysis.analytics.txn_file_detection import (
    is_txn_dest_file,
    is_txn_filename,
)

# Every file from the 1192 folder in issue #251, verbatim.
ASCEND_1192_FILES = [
    "1192_30938_[2026.01.02][15.44.19]_velocity debit transactions dec 2025.txt",
    "1192_30938_[2026.02.05][14.22.13]_184202",
    "1192_35687_[2025.10.08][09.20.27]_monthlydebittransactions",
    "1192_35687_[2025.11.05][10.02.57]_monthlydebittransactions",
    "1192_35687_[2025.12.05][10.02.52]_monthlydebittransactions",
    "1192_35687_[2026.03.11][09.00_USED.35]_213981",
    "1192_35687_[2026.04.05][10.03.41]_monthlydebittransactions",
    "1192_35687_[2026.05.06][13.40.15]_velocity debit trans april 2026.txt",
    "1192_35687_[2026.06.05][10.03.12]_monthlydebittransactions",
    "1192_35687_[2026.07.05][10.03.04]_monthlydebittransactions",
]

# Variants from issue #45 that already worked and must keep working.
KNOWN_GOOD_VARIANTS = [
    "coasthills-trans-02282026.txt",
    "1441_16286_[2026.04.03][07.15.33]_debit card transaction monthly.csv",
    "1562_19776_[2026.04.01][11.48.26]_velocity.ars.transactions.2026.04.01.txt",
    "1585_30973_[2023.07.21][14.18.53]_monthly_transaction_data_mls (1).txt",
    "1761_30615_[2026.04.01][03.09.06]_velocity_debit_card_transaction_monthly_file.txt",
    "1795_31142_[2026.04.01][11.30.27]_monthlytran.csv",
    "1745_29335_[2026.04.01][03.09.06]_transaction",
]

NON_TXN_FILES = [
    "1192_ODDD.zip",
    "1192-2026-07-Ascend FCU-ODD.csv",
    "1192_combined_cache.parquet",
    "notes.xlsx",
    "formatting_log.txt",
]


class TestIsTxnFilename:
    def test_extensionless_plural_transactions_matches(self):
        assert is_txn_filename(
            "1192_35687_[2026.07.05][10.03.04]_monthlydebittransactions"
        )

    def test_known_variants_still_match(self):
        for name in KNOWN_GOOD_VARIANTS:
            assert is_txn_filename(name), name

    def test_extensionless_tran_without_transaction_suffix_matches(self):
        # Future-proofing: a monthlytran-style name that arrives extensionless
        assert is_txn_filename("1795_31142_[2026.04.01][11.30.27]_monthlytran")

    def test_zip_and_odd_and_cache_do_not_match(self):
        for name in NON_TXN_FILES:
            assert not is_txn_filename(name), name

    def test_renamed_files_without_tran_do_not_match_dump_side(self):
        # These can only be recognized in the curated destination folder.
        assert not is_txn_filename("1192_30938_[2026.02.05][14.22.13]_184202")
        assert not is_txn_filename("1192_35687_[2026.03.11][09.00_USED.35]_213981")


class TestIsTxnDestFile:
    def _touch(self, tmp_path: Path, name: str) -> Path:
        p = tmp_path / name
        p.write_bytes(b"x")
        return p

    def test_all_ascend_files_recognized_in_dest_folder(self, tmp_path):
        for name in ASCEND_1192_FILES:
            assert is_txn_dest_file(self._touch(tmp_path, name)), name

    def test_parquet_cache_not_recognized(self, tmp_path):
        assert not is_txn_dest_file(self._touch(tmp_path, "1192_combined_cache.parquet"))

    def test_directory_not_recognized(self, tmp_path):
        d = tmp_path / "2026"
        d.mkdir()
        assert not is_txn_dest_file(d)

    def test_known_variants_recognized(self, tmp_path):
        for name in KNOWN_GOOD_VARIANTS:
            assert is_txn_dest_file(self._touch(tmp_path, name)), name
