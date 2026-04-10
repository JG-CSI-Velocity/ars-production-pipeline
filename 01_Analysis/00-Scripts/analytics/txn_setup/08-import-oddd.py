# Load ODDD
odd_file = Path(r"M:\ARS\Incoming\ODDD Files\JamesG\2026.02\1776\1776-2026-02-CoastHills CU-ODD.xlsx")

print("Loading rewards file...")
rewards_df = pd.read_excel(odd_file)
print(f"Loaded: {len(rewards_df):,} rows, {len(rewards_df.columns)} columns")

# ODD Columns
print("\nColumns:")
for col in rewards_df.columns:
    print(f"  {col}")
