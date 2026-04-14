# ===========================================================================
# SECTION 3B: MERGE ODD DATA & CREATE BUSINESS/PERSONAL SPLITS
# ===========================================================================

# Clean up column names (remove leading/trailing spaces)
rewards_df.columns = rewards_df.columns.str.strip()

# Check business flag distribution
print(f"Business account distribution:")
print(rewards_df['Business?'].value_counts())

# Create a clean subset for merging
odd_subset = rewards_df[['Acct Number', 'Business?']].copy()
odd_subset.columns = ['account_number', 'business_flag']

# Normalize account numbers to string (Excel loads as int/float, TSV as string)
odd_subset['account_number'] = odd_subset['account_number'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
combined_df['primary_account_num'] = combined_df['primary_account_num'].astype(str).str.strip()

# Drop stale merge columns so cell is safe to re-run
for col in ['business_flag', 'account_number', 'business_flag_x', 'business_flag_y']:
    if col in combined_df.columns:
        combined_df.drop(columns=col, inplace=True)

# Merge with transaction data
combined_df = combined_df.merge(
    odd_subset,
    left_on='primary_account_num',
    right_on='account_number',
    how='left'
)

# Drop the redundant account_number column
combined_df.drop('account_number', axis=1, inplace=True)

# Check merge results
print(f"\nMerge results:")
print(f"  Total transactions: {len(combined_df):,}")
print(f"  Matched to ODD: {combined_df['business_flag'].notna().sum():,}")
print(f"  Unmatched: {combined_df['business_flag'].isna().sum():,}")

# Debug: show sample account numbers from each side if match rate is low
_match_rate = combined_df['business_flag'].notna().mean()
if _match_rate < 0.5:
    print(f"\n  WARNING: Low match rate ({_match_rate:.1%})")
    print(f"  Sample txn acct nums: {combined_df['primary_account_num'].head(3).tolist()}")
    print(f"  Sample ODDD acct nums: {odd_subset['account_number'].head(3).tolist()}")

# Check what the actual values are
print("\nBusiness flag unique values in merged data:")
print(combined_df['business_flag'].value_counts())

# Normalize business_flag values (handle Y/Yes/YES/True variants)
_bf = combined_df['business_flag'].astype(str).str.strip().str.lower()
combined_df['business_flag'] = _bf.map(
    lambda v: 'Yes' if v in ('yes', 'y', 'true', '1') else ('No' if v in ('no', 'n', 'false', '0') else None)
)

# Split into business and personal
business_df = combined_df[combined_df['business_flag'] == 'Yes'].copy()
personal_df = combined_df[combined_df['business_flag'] == 'No'].copy()

print(f"\nTransaction split:")
print(f"  Business transactions: {len(business_df):,}")
print(f"  Personal transactions: {len(personal_df):,}")
print(f"  Unmatched transactions: {combined_df['business_flag'].isna().sum():,}")

# ===========================================================================
# CREATE YEAR_MONTH COLUMN FOR TIME-BASED ANALYSIS
# ===========================================================================

combined_df['transaction_date'] = pd.to_datetime(combined_df['transaction_date'])
business_df['transaction_date'] = pd.to_datetime(business_df['transaction_date'])
personal_df['transaction_date'] = pd.to_datetime(personal_df['transaction_date'])

# ---------------------------------------------------------------------------
# Dataset date range constants (available to ALL downstream folders)
# ---------------------------------------------------------------------------
DATASET_START  = combined_df['transaction_date'].min()
DATASET_END    = combined_df['transaction_date'].max()
DATASET_MONTHS = max(1, round((DATASET_END - DATASET_START).days / 30.44))
DATASET_LABEL  = f"{DATASET_START.strftime('%b %Y')}-{DATASET_END.strftime('%b %Y')}"
print(f"\nDataset period: {DATASET_LABEL} ({DATASET_MONTHS} months)")

# Create year_month column in all dataframes
if 'year_month' not in combined_df.columns:
    combined_df['year_month'] = combined_df['transaction_date'].dt.to_period('M')
    business_df['year_month'] = business_df['transaction_date'].dt.to_period('M')
    personal_df['year_month'] = personal_df['transaction_date'].dt.to_period('M')
    print(f"Created year_month column for time-based analysis")

# ===========================================================================
# FINAL VERIFICATION
# ===========================================================================

print(f"\nVerification:")
print(f"  combined_df has 'merchant_consolidated': {'merchant_consolidated' in combined_df.columns}")
print(f"  business_df has 'merchant_consolidated': {'merchant_consolidated' in business_df.columns}")
print(f"  personal_df has 'merchant_consolidated': {'merchant_consolidated' in personal_df.columns}")
print(f"  combined_df has 'year_month': {'year_month' in combined_df.columns}")
print(f"  business_df has 'year_month': {'year_month' in business_df.columns}")
print(f"  personal_df has 'year_month': {'year_month' in personal_df.columns}")

if 'merchant_consolidated' not in business_df.columns:
    print("\nWARNING: merchant_consolidated column missing!")
    print("   Make sure Section 2 (Data Prep) ran before Section 3!")
elif 'year_month' not in business_df.columns:
    print("\nWARNING: year_month column missing!")
    print("   This should not happen - check the code above!")
else:
    print(f"\nReady for analysis.")
    print(f"  Business unique merchants (consolidated): {business_df['merchant_consolidated'].nunique():,}")
    print(f"  Personal unique merchants (consolidated): {personal_df['merchant_consolidated'].nunique():,}")
    print(f"  Total months in dataset: {combined_df['year_month'].nunique()}")

# ===========================================================================
# SAVE PARQUET CACHE (speeds up subsequent runs from ~25 min to ~10 sec)
# ===========================================================================
if not SKIP_COMBINE:
    try:
        print(f"\nSaving Parquet cache for next run...")
        combined_df.to_parquet(PARQUET_CACHE, index=False, engine='pyarrow')
        _cache_mb = PARQUET_CACHE.stat().st_size / 1024 / 1024
        print(f"  Saved: {PARQUET_CACHE.name} ({_cache_mb:.0f} MB)")
        print(f"  Next run will load from cache instead of reading {len(files_to_load)} files")
    except Exception as _e:
        print(f"  WARNING: Could not save Parquet cache: {_e}")
        print(f"  (Not fatal -- next run will rebuild from source files)")

