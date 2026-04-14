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


def load_transaction_file(filepath):
    """Load a debit card transaction file (.txt or .csv).

    Detects delimiter automatically: tab for .txt, comma for .csv.
    Some clients use .csv with commas, others use .txt with tabs.
    The format never changes within one client across months.
    """
    filepath = Path(filepath)

    # Detect delimiter by file extension
    if filepath.suffix.lower() == '.csv':
        sep = ','
    else:
        sep = '\t'

    df = pd.read_csv(filepath, sep=sep, skiprows=1, header=None, low_memory=False)

    # Warn if column count is unexpected
    if len(df.columns) == 1 and sep == '\t':
        # Might be a comma-separated file with .txt extension -- retry
        print(f"  WARNING: {filepath.name} has 1 column with tab delimiter, retrying with comma...")
        df = pd.read_csv(filepath, sep=',', skiprows=1, header=None, low_memory=False)

    if len(df.columns) != len(EXPECTED_COLUMNS):
        print(f"  WARNING: {filepath.name} has {len(df.columns)} columns (expected {len(EXPECTED_COLUMNS)})")

    # Assign column names
    df.columns = EXPECTED_COLUMNS[:len(df.columns)]

    # Add metadata
    df['source_file'] = filepath.name

    return df

# Load TXN files from the trailing 12-month window (set by 02-file-config.py)
# files_to_load = recent dated files + unparsed files (can't exclude what we can't date)
transaction_files = []
print(f"Loading {len(files_to_load)} transaction files...\n")

for file_path in sorted(files_to_load):
    df = load_transaction_file(file_path)
    transaction_files.append(df)
    print(f"  Loaded: {file_path.name} ({len(df):,} rows)")

print(f"\n{'='*50}")
print(f"Total transactions loaded: {sum(len(df) for df in transaction_files):,}")
