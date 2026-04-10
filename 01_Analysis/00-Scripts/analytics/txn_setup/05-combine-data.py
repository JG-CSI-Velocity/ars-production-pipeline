# Combine all dataframes
combined_df = pd.concat(transaction_files, ignore_index=True)

# Convert data types
combined_df['amount'] = combined_df['amount'].astype(float)
if combined_df['amount'].median() < 0:
    combined_df['amount'] = combined_df['amount'].abs()

# Parse transaction_date to datetime (format: MM/DD/YYYY)
combined_df['transaction_date'] = pd.to_datetime(
    combined_df['transaction_date'], format='mixed', dayfirst=False
)

# Dataset overview
print(f"Combined Dataset Overview:")
print(f"{'='*50}")
print(f"Total Shape: {combined_df.shape}")
print(f"Total Transactions: {len(combined_df):,}")
print(f"Total Columns: {combined_df.shape[1]}")
print(f"Memory Usage: {combined_df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
_dt_min = combined_df['transaction_date'].min()
_dt_max = combined_df['transaction_date'].max()
print(f"\nDate Range: {_dt_min.strftime('%b %d, %Y')} to {_dt_max.strftime('%b %d, %Y')}")
print(f"Unique Accounts: {combined_df['primary_account_num'].nunique():,}")
print(f"Unique Merchants: {combined_df['merchant_name'].nunique():,}")
print(f"Total Transactions Value: {combined_df['amount'].sum():,.0f}")
