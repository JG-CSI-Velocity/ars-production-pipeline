# Load ODDD — discover ODD file from the same client folder as TXN files
# CLIENT_PATH, CLIENT_ID set by 02-file-config.py (runs before this script)
odd_candidates = list(CLIENT_PATH.glob(f"*{CLIENT_ID}*ODD*.xlsx"))
if not odd_candidates:
    # Fallback: check parent month folder
    odd_candidates = list(CLIENT_PATH.parent.glob(f"*{CLIENT_ID}*ODD*.xlsx"))

if not odd_candidates:
    raise FileNotFoundError(
        f"No ODD file found for client {CLIENT_ID} in {CLIENT_PATH} or parent. "
        f"Expected pattern: *{CLIENT_ID}*ODD*.xlsx"
    )

odd_file = odd_candidates[0]
if len(odd_candidates) > 1:
    print(f"WARNING: Multiple ODD files found, using: {odd_file.name}")

print(f"Loading ODD file: {odd_file.name}")
rewards_df = pd.read_excel(odd_file)
print(f"Loaded: {len(rewards_df):,} rows, {len(rewards_df.columns)} columns")

# ODD Columns
print("\nColumns:")
for col in rewards_df.columns:
    print(f"  {col}")
