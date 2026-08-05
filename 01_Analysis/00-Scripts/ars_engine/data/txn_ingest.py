"""Parse one raw TXN transaction file -- ported from txn_setup/04-define-data-func.py.

The parse semantics are the parity surface: delimiter sniffing with fallback,
malformed-line recovery on the SAME delimiter (issue #251), surviving-header
detection (issue: FNB Alaska banner files), 13 named columns + source_file.
Type coercion matches txn_setup/05-combine-data.py element-wise: amount via
pd.to_numeric(errors='coerce'), transaction_date via pd.to_datetime
(format='mixed', dayfirst=False). The legacy global sign rule (abs when the
COMBINED median is negative) is NOT applied here -- it is a whole-dataset
property and lives in txn_store.finalize().
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "transaction_date",      # Date of Transaction (MM/DD/YYYY)
    "primary_account_num",   # Primary account number (hashed)
    "transaction_type",      # PIN, SIG, ACH, CHK
    "amount",                # Transaction amount
    "mcc_code",              # Merchant Category Code
    "merchant_name",         # Merchant name
    "terminal_location_1",   # Terminal location/address
    "terminal_location_2",   # Additional location info
    "terminal_id",           # Terminal ID
    "merchant_id",           # Merchant ID
    "institution",           # Institution number
    "card_present",          # Y/N indicator
    "transaction_code",      # Transaction code
]

# Dtype hints -- avoids pandas type inference on millions of rows
DTYPE_HINTS = {i: "str" for i in range(len(EXPECTED_COLUMNS))}

_SEP_LABELS = {"\t": "tab", ",": "comma", "|": "pipe", ";": "semicolon"}


def _read_with_sep(filepath, sep, on_bad_lines="error"):
    """Single attempt to read a TXN file with the given delimiter."""
    return pd.read_csv(
        filepath,
        sep=sep,
        skiprows=1,
        header=None,
        dtype=DTYPE_HINTS,
        low_memory=False,
        na_values=["", "NA", "N/A"],
        on_bad_lines=on_bad_lines,
    )


def _peek_delimiter(filepath, candidates=("\t", ",", "|", ";"), sample_lines=20):
    """Sniff the most likely delimiter from a small header sample.

    Median per-line count over up to ``sample_lines`` non-empty lines; the
    winner needs a median >= 1, else tab. Handles pipe/semicolon exports the
    old tab-or-comma logic mishandled silently (issue #137, client 1585).
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            sample = []
            for line in fh:
                if line.strip():
                    sample.append(line)
                if len(sample) >= sample_lines:
                    break
        if not sample:
            return "\t"
        counts = {sep: [line.count(sep) for line in sample] for sep in candidates}
        scored = sorted(
            counts.items(),
            key=lambda kv: sorted(kv[1])[len(kv[1]) // 2],  # median per-line count
            reverse=True,
        )
        best, best_counts = scored[0]
        if sorted(best_counts)[len(best_counts) // 2] >= 1:
            return best
        return "\t"
    except Exception:  # noqa: BLE001 - sniffing is best-effort; reader falls back
        return "\t"


# Header keywords for banner files whose real header survives skiprows=1
_HEADER_KEYWORDS = (
    "transaction date", "transaction_date", "trans date", "date",
    "account number", "account_number", "primary account", "acct",
    "transaction type", "trans type", "type code",
    "amount", "mcc", "merchant", "terminal", "institution",
)
_MAX_HEADER_ROWS_TO_CHECK = 2


def load_transaction_file(filepath: Path | str, log=print) -> pd.DataFrame:
    """Load a debit card transaction file (.txt, .csv, or no extension).

    1. Sniff the delimiter; 2. read with it; 3. on a wrong guess or
    ParserError, retry the SAME delimiter skipping bad lines (accepting only
    the expected shape), then fall through to the other candidates keeping
    whichever is closest to the expected column count.
    """
    filepath = Path(filepath)
    target_cols = len(EXPECTED_COLUMNS)
    candidates = ["\t", ",", "|", ";"]

    def _label(s):
        return _SEP_LABELS.get(s, repr(s))

    def _try(sep):
        try:
            return _read_with_sep(filepath, sep)
        except pd.errors.ParserError as exc:
            # A handful of malformed rows must not disqualify an otherwise-
            # correct delimiter (issue #251: 5.7M tab-clean rows except one).
            # Retry the SAME delimiter skipping bad lines; accept only the
            # expected shape so wrong delimiters still fall through.
            try:
                retry = _read_with_sep(filepath, sep, on_bad_lines="skip")
            except pd.errors.ParserError:
                log(f"  WARNING: {filepath.name} ParserError with {_label(sep)} delimiter: {exc}")
                return None
            if len(retry.columns) == target_cols and len(retry):
                log(
                    f"  Note: {filepath.name} has malformed line(s) ({exc}); recovered "
                    f"with {_label(sep)} delimiter by skipping them -- {len(retry):,} rows kept."
                )
                return retry
            log(f"  WARNING: {filepath.name} ParserError with {_label(sep)} delimiter: {exc}")
            return None

    primary = _peek_delimiter(filepath, tuple(candidates))
    ordered = [primary] + [s for s in candidates if s != primary]

    df = None
    best_df = None
    best_sep = None
    for sep in ordered:
        attempt = _try(sep)
        if attempt is None:
            continue
        if len(attempt.columns) == target_cols:
            df = attempt
            if sep != primary:
                log(f"  Loaded with {_label(sep)} delimiter (sniffer guessed {_label(primary)}).")
            break
        if best_df is None or abs(len(attempt.columns) - target_cols) < abs(
            len(best_df.columns) - target_cols
        ):
            best_df = attempt
            best_sep = sep

    if df is None and best_df is None:
        raise ValueError(
            f"{filepath.name}: could not parse with any delimiter (tab/comma/pipe/semicolon)"
        )
    if df is None:
        df = best_df
        log(
            f"  WARNING: no delimiter yielded {target_cols} columns for {filepath.name}; "
            f"using {_label(best_sep)} ({len(df.columns)} cols)."
        )
    if len(df.columns) != target_cols:
        log(f"  WARNING: {filepath.name} has {len(df.columns)} columns (expected {target_cols})")

    # Drop 1-2 header rows that survived skiprows=1 (banner files)
    dropped = 0
    for _ in range(_MAX_HEADER_ROWS_TO_CHECK):
        if len(df) == 0:
            break
        try:
            first_row = df.iloc[0].astype(str).str.lower()
            joined = " ".join(v for v in first_row.values if v and v != "nan")
        except Exception:  # noqa: BLE001 - malformed first row: stop checking
            break
        if not any(kw in joined for kw in _HEADER_KEYWORDS):
            break
        df = df.iloc[1:].reset_index(drop=True)
        dropped += 1
    if dropped:
        log(f"  Dropped {dropped} surviving header row(s) from {filepath.name}")

    df.columns = EXPECTED_COLUMNS[: len(df.columns)]
    df["source_file"] = filepath.name
    return df


def coerce_types(df: pd.DataFrame, log=print) -> pd.DataFrame:
    """Element-wise type coercion, matching txn_setup/05-combine-data.py.

    Applied per file here; identical to the legacy combined-frame application
    because both operations are element-wise. The global abs-if-median<0 sign
    rule is deliberately NOT here (see txn_store.finalize).
    """
    df = df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    bad = int(df["amount"].isna().sum())
    if bad > 0:
        log(f"WARNING: {bad:,} rows with non-numeric amount values (set to NaN)")
    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"], format="mixed", dayfirst=False
    )
    return df
