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


def _sniff_delimiter(filepath, sample_bytes=8192):
    """Detect delimiter from FILE CONTENT, not just extension.

    Reads the first few KB and counts tabs vs commas. The winner is the
    real delimiter. Falls back to extension-based guessing only if the
    sample is empty or both counts tie at zero.

    Why content-based: some clients deliver TSV data with a .csv
    extension (e.g. 1441 / FNB Alaska, 4/26 run, issue #95). Pandas read
    that file with sep=',' because of the extension; the header line had
    no commas so it was parsed as 1 column; line 278 happened to contain
    a literal comma inside a field, suddenly making it look like 2
    columns and crashing the entire pipeline with the unhelpful
    ``Expected 1 fields, saw 2''. Sniffing the actual delimiter prevents
    this whole class of failure.
    """
    try:
        with open(filepath, 'rb') as fh:
            sample = fh.read(sample_bytes).decode('utf-8', errors='replace')
        # Count delimiter occurrences only on lines after the first to
        # avoid an unusually delimiter-heavy header skewing the count.
        lines = sample.splitlines()[1:5] if len(sample.splitlines()) > 1 else sample.splitlines()
        joined = '\n'.join(lines) if lines else sample
        n_tabs = joined.count('\t')
        n_commas = joined.count(',')
        if n_tabs == 0 and n_commas == 0:
            # Couldn't sniff -- fall back to extension
            return ',' if filepath.suffix.lower() == '.csv' else '\t'
        return '\t' if n_tabs > n_commas else ','
    except Exception:
        # If we can't even read it, defer the explosion to pd.read_csv
        # which will give a clearer error
        return ',' if filepath.suffix.lower() == '.csv' else '\t'


def load_transaction_file(filepath):
    """Load a debit card transaction file (.txt or .csv).

    Delimiter is detected from file CONTENT (not just extension).
    Mismatched extension+content (e.g. .csv that's actually tab-delimited)
    used to crash with ``Error tokenizing data. Expected 1 fields,
    saw 2'' -- now handled transparently with a content-aware sniff
    plus retry-with-other-delimiter fallback in both directions.
    """
    filepath = Path(filepath)

    # Pick delimiter from content, not extension
    sep = _sniff_delimiter(filepath)
    sep_label = 'TAB' if sep == '\t' else 'COMMA'
    extension_guess = ',' if filepath.suffix.lower() == '.csv' else '\t'
    if sep != extension_guess:
        ext_label = 'TAB' if extension_guess == '\t' else 'COMMA'
        print(f"  NOTE: {filepath.name} extension suggests {ext_label} but content is {sep_label}; using {sep_label}")

    # Use dtype hints to skip type inference (big speedup on millions of rows)
    try:
        df = pd.read_csv(filepath, sep=sep, skiprows=1, header=None,
                         dtype=DTYPE_HINTS, low_memory=False, na_values=['', 'NA', 'N/A'])
    except Exception as exc:
        print(f"  WARNING: {filepath.name} failed parse with {sep_label}: {type(exc).__name__}: {exc}")
        # Try the other delimiter as a last resort
        other = ',' if sep == '\t' else '\t'
        other_label = 'TAB' if other == '\t' else 'COMMA'
        print(f"           Retrying with {other_label}...")
        df = pd.read_csv(filepath, sep=other, skiprows=1, header=None,
                         dtype=DTYPE_HINTS, low_memory=False, na_values=['', 'NA', 'N/A'])
        sep = other
        sep_label = other_label

    # Both-direction retry: if we ended up with 1 column, the sniff was
    # probably wrong (e.g. file with no delimiters in the first 4 lines
    # because every field was empty). Try the OTHER delimiter.
    if len(df.columns) == 1:
        other = ',' if sep == '\t' else '\t'
        other_label = 'TAB' if other == '\t' else 'COMMA'
        print(f"  WARNING: {filepath.name} parsed to 1 column with {sep_label}; retrying with {other_label}")
        try:
            df_retry = pd.read_csv(filepath, sep=other, skiprows=1, header=None,
                                   dtype=DTYPE_HINTS, low_memory=False, na_values=['', 'NA', 'N/A'])
            if len(df_retry.columns) > 1:
                df = df_retry
                sep = other
                sep_label = other_label
        except Exception as exc:
            print(f"           Retry also failed: {type(exc).__name__}: {exc}")

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
