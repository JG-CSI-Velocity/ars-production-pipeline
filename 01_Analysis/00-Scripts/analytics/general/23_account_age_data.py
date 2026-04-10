# ===========================================================================
# ACCOUNT AGE DATA: Lifecycle Metrics from ODDD (Conference Edition)
# ===========================================================================
# Merge Account Age, Date Opened, spend cols from rewards_df.
# Compute first-txn date, days-to-first-txn (TTM only), spend tiers.

# DATASET_START, DATASET_END, DATASET_MONTHS, DATASET_LABEL
# are defined in setup/09-oddd-account-type (available to all folders).

# ---------------------------------------------------------------------------
# Merge account lifecycle fields from ODDD
# ---------------------------------------------------------------------------
acct_subset = rewards_df[['Acct Number', 'Account Age', 'Date Opened',
                           'Total Spend', 'last 12-mon spend',
                           'last 3-mon spend']].copy()
acct_subset.columns = ['account_number', 'acct_age', 'date_opened',
                        'oddd_total_spend', 'oddd_12mo_spend', 'oddd_3mo_spend']

acct_subset['acct_age'] = pd.to_numeric(acct_subset['acct_age'], errors='coerce')
acct_subset['date_opened'] = pd.to_datetime(acct_subset['date_opened'], errors='coerce')
acct_subset['oddd_total_spend'] = pd.to_numeric(acct_subset['oddd_total_spend'], errors='coerce')
acct_subset['oddd_12mo_spend'] = pd.to_numeric(acct_subset['oddd_12mo_spend'], errors='coerce')
acct_subset['oddd_3mo_spend'] = pd.to_numeric(acct_subset['oddd_3mo_spend'], errors='coerce')

# ---------------------------------------------------------------------------
# Build per-account metrics from combined_df
# ---------------------------------------------------------------------------
acct_txn_stats = combined_df.groupby('primary_account_num').agg(
    txn_count=('transaction_date', 'count'),
    first_txn_date=('transaction_date', 'min'),
    last_txn_date=('transaction_date', 'max'),
    txn_total_amount=('amount', 'sum'),
    txn_avg_amount=('amount', 'mean'),
).reset_index()
acct_txn_stats.columns = ['account_number', 'txn_count', 'first_txn_date',
                           'last_txn_date', 'txn_total_amount', 'txn_avg_amount']

# ---------------------------------------------------------------------------
# Merge ODDD + transaction stats
# ---------------------------------------------------------------------------
lifecycle_df = acct_subset.merge(
    acct_txn_stats,
    on='account_number',
    how='inner'
)

# ---------------------------------------------------------------------------
# Account age bands (9 bands, days-based from Date Opened)
# ---------------------------------------------------------------------------
# Use dataset end date (not today) so account age is relative to the data
_acct_age_ref = DATASET_END.normalize()
lifecycle_df['days_since_opened'] = (_acct_age_ref - lifecycle_df['date_opened']).dt.days

ACCT_AGE_BINS = [0, 91, 181, 366, 731, 1096, 1826, 3651, 7301, 999999]
ACCT_AGE_LABELS = ['1-90d', '91-180d', '181-365d', '1-2yr', '2-3yr',
                    '3-5yr', '5-10yr', '10-20yr', '20yr+']

lifecycle_df['acct_age_band'] = pd.cut(
    lifecycle_df['days_since_opened'],
    bins=ACCT_AGE_BINS, labels=ACCT_AGE_LABELS, right=False
)

# ---------------------------------------------------------------------------
# TTM flag: accounts opened within trailing twelve months
# Only these get days_to_first_txn (older accounts lack historical txn data)
# ---------------------------------------------------------------------------
lifecycle_df['is_ttm'] = lifecycle_df['days_since_opened'] <= 365

# Days to first transaction -- TTM accounts only
lifecycle_df['days_to_first_txn'] = np.nan
ttm_mask = lifecycle_df['is_ttm']
lifecycle_df.loc[ttm_mask, 'days_to_first_txn'] = (
    lifecycle_df.loc[ttm_mask, 'first_txn_date'] - lifecycle_df.loc[ttm_mask, 'date_opened']
).dt.days

# ---------------------------------------------------------------------------
# Spend tiers (quartiles of ODDD Total Spend among matched accounts)
# ---------------------------------------------------------------------------
spend_valid = lifecycle_df['oddd_total_spend'].dropna()
if len(spend_valid) > 0:
    q25, q50, q75 = spend_valid.quantile([0.25, 0.50, 0.75])
    def _classify_spend(val):
        if pd.isna(val):
            return None
        if val >= q75:
            return 'Very High'
        if val >= q50:
            return 'High'
        if val >= q25:
            return 'Medium'
        return 'Low'
    lifecycle_df['spend_tier'] = lifecycle_df['oddd_total_spend'].apply(_classify_spend)
else:
    lifecycle_df['spend_tier'] = None
    q25, q50, q75 = 0, 0, 0

SPEND_THRESHOLDS = {'Low': f'< ${q25:,.0f}', 'Medium': f'${q25:,.0f}-${q50:,.0f}',
                    'High': f'${q50:,.0f}-${q75:,.0f}', 'Very High': f'> ${q75:,.0f}'}

# ---------------------------------------------------------------------------
# Monthly txns per account (annualized for fair comparison across age bands)
# ---------------------------------------------------------------------------
lifecycle_df['months_in_dataset'] = np.clip(
    ((lifecycle_df['last_txn_date'] - lifecycle_df['first_txn_date']).dt.days / 30.44) + 1,
    1, None
)
lifecycle_df['txns_per_month'] = lifecycle_df['txn_count'] / lifecycle_df['months_in_dataset']

# ---------------------------------------------------------------------------
# Summary per account age band
# ---------------------------------------------------------------------------
lifecycle_matched = lifecycle_df[lifecycle_df['acct_age_band'].notna()]

lifecycle_summary = lifecycle_matched.groupby('acct_age_band', observed=True).agg(
    account_count=('account_number', 'nunique'),
    avg_txns_per_month=('txns_per_month', 'mean'),
    total_txns=('txn_count', 'sum'),
    avg_oddd_12mo=('oddd_12mo_spend', 'mean'),
    avg_txn_amount=('txn_avg_amount', 'mean'),
    pct_very_high=('spend_tier', lambda x: (x == 'Very High').sum() / len(x) * 100 if len(x) > 0 else 0),
).reset_index()

# TTM-only stats for days-to-first-txn (only for bands within TTM)
ttm_activation = lifecycle_matched[lifecycle_matched['is_ttm']].groupby(
    'acct_age_band', observed=True
).agg(
    median_days_to_first=('days_to_first_txn', 'median'),
    pct_activated_30d=('days_to_first_txn', lambda x: (x <= 30).sum() / len(x) * 100 if len(x) > 0 else 0),
).reset_index()

lifecycle_summary = lifecycle_summary.merge(ttm_activation, on='acct_age_band', how='left')

# ---------------------------------------------------------------------------
# Conference-styled summary
# ---------------------------------------------------------------------------
lc_display = lifecycle_summary.copy()
lc_display.columns = ['Age Band', 'Accounts', 'Avg Txns/Mo', 'Total Txns',
                       'Avg 12mo Spend', 'Avg Txn Size', '% Very High',
                       'Med Days to 1st Txn (TTM)', '% Activated <30d (TTM)']

styled = (
    lc_display.style
    .hide(axis='index')
    .format({
        'Accounts': '{:,.0f}',
        'Avg Txns/Mo': '{:.1f}',
        'Total Txns': '{:,.0f}',
        'Avg 12mo Spend': '${:,.0f}',
        'Avg Txn Size': '${:,.0f}',
        '% Very High': '{:.1f}%',
        'Med Days to 1st Txn (TTM)': '{:.0f}',
        '% Activated <30d (TTM)': '{:.0f}%',
    }, na_rep='--')
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
            ('padding', '10px 12px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '24px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Account Lifecycle Summary")
    .bar(subset=['Accounts'], color=GEN_COLORS['info'], vmin=0)
)

display(styled)

print(f"\n    Dataset period: {DATASET_LABEL} ({DATASET_MONTHS} months)")
print(f"    Matched accounts: {len(lifecycle_matched):,}")
print(f"    TTM accounts (opened <12mo): {lifecycle_matched['is_ttm'].sum():,}")
ttm_median = lifecycle_matched.loc[lifecycle_matched['is_ttm'], 'days_to_first_txn'].median()
if pd.notna(ttm_median):
    print(f"    TTM median days to first txn: {ttm_median:.0f}")
print(f"    Spend tiers: Low {SPEND_THRESHOLDS['Low']} | "
      f"Medium {SPEND_THRESHOLDS['Medium']} | "
      f"High {SPEND_THRESHOLDS['High']} | "
      f"Very High {SPEND_THRESHOLDS['Very High']}")
