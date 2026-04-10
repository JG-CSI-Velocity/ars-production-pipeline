def load_transaction_file(filepath):
    """
    Load a debit card transaction file
    """
    filepath = Path(filepath)
    
    # Skip the metadata header line, read tab-delimited data
    df = pd.read_csv(filepath, sep='\t', skiprows=1, header=None, low_memory=False)
    
    # Assign column names based on the file definition document
    df.columns = [
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
    ][:len(df.columns)]  # Only use as many names as there are columns
    
    # Add metadata
    df['source_file'] = filepath.name
    
    return df

# Load all transaction files
transaction_files = []
files_to_load = sorted(CLIENT_PATH.glob(f'**/*.{FILE_EXTENSION}'))
print(f"Loading {len(files_to_load)} transaction files...\n")

for file_path in files_to_load:
    df = load_transaction_file(file_path)
    transaction_files.append(df)
    print(f"  Loaded: {file_path.name} ({len(df):,} rows)")

print(f"\n{'='*50}")
print(f"Total transactions loaded: {sum(len(df) for df in transaction_files):,}")
