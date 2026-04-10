# ===========================================================================
# DEMOGRAPHIC DATA: Age Bands + Time Patterns from ODDD (Conference Edition)
# ===========================================================================
# Merge Account Holder Age from rewards_df. Create age bands.
# Extract hour and day_of_week from timestamps.

# ---------------------------------------------------------------------------
# Merge age data from ODDD
# ---------------------------------------------------------------------------
age_subset = rewards_df[['Acct Number', 'Account Holder Age']].copy()
age_subset.columns = ['account_number', 'holder_age']
age_subset['holder_age'] = pd.to_numeric(age_subset['holder_age'], errors='coerce')

demo_df = combined_df.merge(
    age_subset,
    left_on='primary_account_num',
    right_on='account_number',
    how='left'
).drop(columns='account_number')

# ---------------------------------------------------------------------------
# Age bands
# ---------------------------------------------------------------------------
AGE_BINS = [18, 26, 36, 46, 56, 66, 200]
AGE_BAND_LABELS = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']

demo_df['age_band'] = pd.cut(
    demo_df['holder_age'], bins=AGE_BINS, labels=AGE_BAND_LABELS, right=False
)

# ---------------------------------------------------------------------------
# Time features from transaction_date
# ---------------------------------------------------------------------------
demo_df['txn_hour'] = demo_df['transaction_date'].dt.hour
demo_df['txn_dow'] = demo_df['transaction_date'].dt.dayofweek  # 0=Mon, 6=Sun
demo_df['txn_dow_name'] = demo_df['transaction_date'].dt.day_name()

# ---------------------------------------------------------------------------
# Summary per age band
# ---------------------------------------------------------------------------
age_matched = demo_df[demo_df['age_band'].notna()]
age_unmatched = demo_df[demo_df['age_band'].isna()]

demo_summary = age_matched.groupby('age_band', observed=True).agg(
    txn_count=('transaction_date', 'count'),
    account_count=('primary_account_num', 'nunique'),
    merchant_count=('merchant_consolidated', 'nunique'),
).reset_index()

demo_summary['txn_per_account'] = (
    demo_summary['txn_count'] / demo_summary['account_count']
)
demo_summary['txn_pct'] = (
    demo_summary['txn_count'] / demo_summary['txn_count'].sum() * 100
)

# Top MCC per age band
top_mcc_by_age = {}
for band in AGE_BAND_LABELS:
    band_data = age_matched[age_matched['age_band'] == band]
    if len(band_data) > 0:
        top_mcc_by_age[band] = (
            band_data.groupby('mcc_code').size()
            .sort_values(ascending=False).head(10)
        )

# ---------------------------------------------------------------------------
# Conference-styled demographic summary
# ---------------------------------------------------------------------------
match_pct = len(age_matched) / len(demo_df) * 100 if len(demo_df) > 0 else 0

demo_display = demo_summary[['age_band', 'account_count', 'txn_count',
                              'txn_pct', 'merchant_count', 'txn_per_account']].copy()
demo_display.columns = ['Age Band', 'Accounts', 'Transactions', 'Txn %',
                         'Merchants', 'Txns/Account']

styled = (
    demo_display.style
    .hide(axis='index')
    .format({
        'Accounts': '{:,.0f}',
        'Transactions': '{:,.0f}',
        'Txn %': '{:.1f}%',
        'Merchants': '{:,.0f}',
        'Txns/Account': '{:.1f}',
    })
    .set_properties(**{
        'font-size': '16px',
        'font-weight': 'bold',
        'text-align': 'center',
        'border': '1px solid #E9ECEF',
        'padding': '10px 14px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '17px'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '10px 14px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '24px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Demographic Summary by Age Band")
    .bar(subset=['Transactions'], color=GEN_COLORS['info'], vmin=0)
)

display(styled)

print(f"\n    Age-matched: {len(age_matched):,} transactions ({match_pct:.1f}%)")
print(f"    Unmatched (no ODDD age data): {len(age_unmatched):,}")
