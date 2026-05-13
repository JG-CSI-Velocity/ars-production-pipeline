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
