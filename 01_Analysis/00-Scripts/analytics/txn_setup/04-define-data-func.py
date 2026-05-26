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
    """Single attempt to read a TXN file with the given delimiter.

    on_bad_lines='skip' drops rows whose field count doesn't match the
    header. Real TXN dumps occasionally contain a single malformed row
    (an unescaped comma in a merchant_name, a truncated line, etc.) and
    we'd rather lose that one row than fail the whole file -- and by
    extension the whole client's TXN run.
    """
    return pd.read_csv(filepath, sep=sep, skiprows=1, header=None,
                       dtype=DTYPE_HINTS, low_memory=False,
                       na_values=['', 'NA', 'N/A'],
                       on_bad_lines='skip')


def load_transaction_file(filepath):
    """Load a debit card transaction file (.txt, .csv, or no extension).

    Picks an initial delimiter from the file extension (.csv -> comma,
    else tab), then auto-retries with the other delimiter if the first
    attempt either raises a ParserError or yields a single-column
    DataFrame (which means the file is delimited by the OTHER character).

    This makes the loader robust to:
      - .csv files that are actually tab-delimited (common from card
        processors that mislabel TSV exports)
      - .txt files that are actually comma-delimited
      - extensionless files
    """
    filepath = Path(filepath)

    # First guess from extension; everything not-.csv defaults to tab.
    first_sep = ',' if filepath.suffix.lower() == '.csv' else '\t'
    other_sep = '\t' if first_sep == ',' else ','

    def _label(s):
        return 'comma' if s == ',' else 'tab'

    df = None
    try:
        df = _read_with_sep(filepath, first_sep)
    except pd.errors.ParserError as e:
        # Most common: .csv extension but tab-delimited body. Some rows happen
        # to contain a stray comma which makes pandas error out instead of
        # falling through to the 1-column check below.
        print(f"  WARNING: {filepath.name} failed to parse as {_label(first_sep)}-delimited ({e.__class__.__name__}); "
              f"retrying as {_label(other_sep)}-delimited...")
        df = _read_with_sep(filepath, other_sep)

    # 1-column result means we picked the wrong delimiter. Retry the other way.
    if len(df.columns) == 1 and other_sep is not None:
        print(f"  WARNING: {filepath.name} parsed as 1 column with {_label(first_sep)} delimiter; "
              f"retrying with {_label(other_sep)}...")
        df = _read_with_sep(filepath, other_sep)

    if len(df.columns) != len(EXPECTED_COLUMNS):
        print(f"  WARNING: {filepath.name} has {len(df.columns)} columns (expected {len(EXPECTED_COLUMNS)})")

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

    _skipped_files = []
    for file_path in sorted(files_to_load):
        try:
            df = load_transaction_file(file_path)
            transaction_files.append(df)
            print(f"  Loaded: {file_path.name} ({len(df):,} rows)")
        except Exception as _exc:
            print(f"  SKIPPED: {file_path.name} -- {_exc.__class__.__name__}: {_exc}")
            _skipped_files.append((file_path.name, str(_exc)))
            continue
    if _skipped_files:
        print(f"\n  WARNING: {len(_skipped_files)} file(s) skipped due to read errors; "
              f"continuing with the {len(transaction_files)} that loaded successfully.")

    print(f"\n{'='*50}")
    print(f"Total transactions loaded: {sum(len(df) for df in transaction_files):,}")
    print(f"File read time: {_t.time() - _load_start:.1f}s")
