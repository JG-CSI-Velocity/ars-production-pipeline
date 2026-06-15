EXPECTED_COLUMNS = [
    'transaction_date',      # Date of Transaction (MM/DD/YYYY)
    'primary_account_num',   # Primary account number (hashed)
    'transaction_type',      # PIN, SIG, ACH, CHK
    'amount',               # Transaction amount
    'mcc_code',             # Merchant Category Code
    'merchant_name',        # Merchant name
    'terminal_location_1',  # Terminal location/address
    'terminal_location_2',  # Additional location info
    'terminal_id',          # Terminal ID
    'merchant_id',          # Merchant ID
    'institution',          # Institution number
    'card_present',         # Y/N indicator
    'transaction_code'      # Transaction code
]

# Dtype hints -- avoids pandas type inference on millions of rows (saves ~30% read time)
DTYPE_HINTS = {
    0: 'str',    # transaction_date (parsed later)
    1: 'str',    # primary_account_num
    2: 'str',    # transaction_type (PIN, SIG, etc.)
    3: 'str',    # amount (cleaned later with pd.to_numeric)
    4: 'str',    # mcc_code
    5: 'str',    # merchant_name
    6: 'str',    # terminal_location_1
    7: 'str',    # terminal_location_2
    8: 'str',    # terminal_id
    9: 'str',    # merchant_id
    10: 'str',   # institution
    11: 'str',   # card_present
    12: 'str',   # transaction_code
}


def _read_with_sep(filepath, sep):
    """Single attempt to read a TXN file with the given delimiter."""
    return pd.read_csv(filepath, sep=sep, skiprows=1, header=None,
                       dtype=DTYPE_HINTS, low_memory=False,
                       na_values=['', 'NA', 'N/A'])


_SEP_LABELS = {'\t': 'tab', ',': 'comma', '|': 'pipe', ';': 'semicolon'}


def _peek_delimiter(filepath, candidates=('\t', ',', '|', ';'), sample_lines=20):
    """Sniff the most likely delimiter from a small header sample.

    Reads up to ``sample_lines`` non-empty lines from the top of the file and
    counts how often each candidate appears per line, returning the delimiter
    with the highest median count >= 1 (else tab). Cheap (a few KB) and handles
    pipe / semicolon exports that the old tab-or-comma logic mishandled
    silently -- producing a 1-column DataFrame of raw lines that downstream
    analytics couldn't read (issue #137, client 1585).
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
            sample = []
            for line in fh:
                if line.strip():
                    sample.append(line)
                if len(sample) >= sample_lines:
                    break
        if not sample:
            return '\t'
        counts = {sep: [line.count(sep) for line in sample] for sep in candidates}
        scored = sorted(
            counts.items(),
            key=lambda kv: sorted(kv[1])[len(kv[1]) // 2],  # median per-line count
            reverse=True,
        )
        best, best_counts = scored[0]
        if sorted(best_counts)[len(best_counts) // 2] >= 1:
            return best
        return '\t'
    except Exception:
        return '\t'


def load_transaction_file(filepath):
    """Load a debit card transaction file (.txt, .csv, or no extension).

    Strategy:
      1. Sniff the delimiter from a small header sample (tab / comma / pipe /
         semicolon supported).
      2. Read with the sniffed delimiter.
      3. If that yields a 1-column frame (wrong guess) or a ParserError, fall
         through to every other candidate and keep whichever produces the
         column count closest to EXPECTED_COLUMNS.

    The old logic only tried tab and comma, so card-processor exports using
    pipe (`|`) or semicolon (`;`) silently produced a 1-column frame of raw
    lines that downstream analytics couldn't use (issue #137, client 1585).
    """
    filepath = Path(filepath)
    target_cols = len(EXPECTED_COLUMNS)
    candidates = ['\t', ',', '|', ';']

    def _label(s):
        return _SEP_LABELS.get(s, repr(s))

    def _try(sep):
        try:
            return _read_with_sep(filepath, sep)
        except pd.errors.ParserError as exc:
            print(f"  WARNING: {filepath.name} ParserError with {_label(sep)} delimiter: {exc}")
            return None

    # Sniff first so the most likely delimiter is tried first, then the rest.
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
                print(f"  Loaded with {_label(sep)} delimiter (sniffer guessed {_label(primary)}).")
            break
        # Track the closest-to-expected result as a fallback.
        if best_df is None or abs(len(attempt.columns) - target_cols) < abs(len(best_df.columns) - target_cols):
            best_df = attempt
            best_sep = sep

    if df is None and best_df is None:
        raise ValueError(
            f"{filepath.name}: could not parse with any delimiter "
            f"(tab/comma/pipe/semicolon)"
        )

    if df is None:
        df = best_df
        print(f"  WARNING: no delimiter yielded {target_cols} columns for {filepath.name}; "
              f"using {_label(best_sep)} ({len(df.columns)} cols). Downstream analytics may fail.")

    if len(df.columns) != target_cols:
        print(f"  WARNING: {filepath.name} has {len(df.columns)} columns (expected {target_cols})")

    # ----------------------------------------------------------
    # Drop header rows that survived skiprows=1
    # ----------------------------------------------------------
    # Some clients (e.g. FNB Alaska / 1441) deliver TXN files with a
    # metadata banner BEFORE the actual header line:
    #
    #   "Report: Debit Card Transactions; Generated 2026-04-26"   <- banner
    #   "Transaction Date<TAB>Account<TAB>Type<TAB>Amount..."     <- header
    #   "2026-04-01<TAB>12345<TAB>PIN<TAB>5.00..."                <- data
    #
    # skiprows=1 strips the banner; the header row survives as ``row 0''
    # and breaks every downstream type coercion (date parse fails on the
    # literal string "Transaction Date", amount becomes NaN, etc.).
    #
    # Detect-and-drop: if the first 1-2 rows contain values matching known
    # header keywords (case-insensitive substring), drop them. Safe for
    # files that do NOT have a banner -- they parsed cleanly to begin with
    # and these rows simply don't match.
    _header_keywords = (
        'transaction date', 'transaction_date', 'trans date', 'date',
        'account number', 'account_number', 'primary account', 'acct',
        'transaction type', 'trans type', 'type code',
        'amount', 'mcc', 'merchant', 'terminal', 'institution',
    )
    _max_rows_to_check = 2
    _dropped_header_rows = 0
    for _ in range(_max_rows_to_check):
        if len(df) == 0:
            break
        # Build a single concatenated lowercase string of the first row's
        # non-null values, then check if any header-keyword appears in it.
        try:
            _first_row = df.iloc[0].astype(str).str.lower()
            _joined = ' '.join(v for v in _first_row.values if v and v != 'nan')
        except Exception:
            break
        _looks_like_header = any(kw in _joined for kw in _header_keywords)
        if not _looks_like_header:
            break
        df = df.iloc[1:].reset_index(drop=True)
        _dropped_header_rows += 1
    if _dropped_header_rows:
        print(f"  Dropped {_dropped_header_rows} surviving header row(s) from {filepath.name}")

    # Assign column names
    df.columns = EXPECTED_COLUMNS[:len(df.columns)]

    # Add metadata
    df['source_file'] = filepath.name

    return df


# ------------------------------------------------------------
# Load data -- Parquet cache or raw files
# ------------------------------------------------------------
import time as _t
_load_start = _t.time()

if USE_PARQUET_CACHE is not None:
    # Fast path: load from Parquet cache (seconds instead of minutes)
    print(f"Loading Parquet cache: {USE_PARQUET_CACHE.name}")
    combined_df = pd.read_parquet(USE_PARQUET_CACHE)
    transaction_files = []  # not needed, combined_df is ready
    SKIP_COMBINE = True
    print(f"  Loaded: {len(combined_df):,} rows x {len(combined_df.columns)} cols in {_t.time() - _load_start:.1f}s")
    print(f"  Memory: {combined_df.memory_usage(deep=True).sum() / 1024**2:.0f} MB")
else:
    # Standard path: read TXN files (now from local temp, much faster than network)
    transaction_files = []
    SKIP_COMBINE = False
    print(f"Loading {len(files_to_load)} transaction files...\n")

    for file_path in sorted(files_to_load):
        df = load_transaction_file(file_path)
        transaction_files.append(df)
        print(f"  Loaded: {file_path.name} ({len(df):,} rows)")

    print(f"\n{'='*50}")
    print(f"Total transactions loaded: {sum(len(df) for df in transaction_files):,}")
    print(f"File read time: {_t.time() - _load_start:.1f}s")
