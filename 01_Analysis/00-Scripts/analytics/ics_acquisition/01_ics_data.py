# ===========================================================================
# ICS ACQUISITION DATA: Master Aggregation Pipeline (Conference Edition)
# ===========================================================================
# Merges ICS Account + Source from rewards_df onto combined_df.
# ICS Account field = Yes/No (or Y/N) -- flags whether account is ICS.
# Source field = REF (referral) or DM (direct mail) -- the acquisition channel.
# Builds: ics_agg, ics_acct_map, ics_df, non_ics_df.
# Uses DATASET_MONTHS from setup/09 for per-month normalization.

# Values in 'ICS Account' that mean YES (case-insensitive)
_ICS_YES = {'YES', 'Y'}

# Expected Source channel codes (case-insensitive)
ICS_CHANNELS = ['REF', 'DM']

try:
    # Pull both ICS Account (Y/N flag) and Source (channel code)
    ics_subset = rewards_df[['Acct Number', 'ICS Account', 'Source']].copy()
    ics_subset.columns = ['account_number', 'ics_flag', 'source_channel']
    ics_subset['account_number'] = ics_subset['account_number'].astype(str).str.strip()

    # Clean both fields
    ics_subset['ics_flag'] = ics_subset['ics_flag'].astype(str).str.strip().str.upper()
    ics_subset['source_channel'] = ics_subset['source_channel'].astype(str).str.strip().str.upper()

    # Diagnostic: show raw values BEFORE classification
    _flag_vals = ics_subset['ics_flag'].value_counts()
    _src_vals = ics_subset['source_channel'].value_counts()
    print("    Raw ICS Account flag values:")
    for val, cnt in _flag_vals.items():
        marker = " <-- ICS" if val in _ICS_YES else ""
        print(f"      {val!r:12s} {cnt:>8,} accounts{marker}")
    print("    Raw Source channel values:")
    for val, cnt in _src_vals.items():
        marker = " <-- channel" if val in ICS_CHANNELS else ""
        print(f"      {val!r:12s} {cnt:>8,} accounts{marker}")

    # Build ics_account: use Source channel for ICS accounts, 'Non-ICS' for rest
    is_ics = ics_subset['ics_flag'].isin(_ICS_YES)
    ics_subset['ics_account'] = 'Non-ICS'
    ics_subset.loc[is_ics, 'ics_account'] = ics_subset.loc[is_ics, 'source_channel']

    # If Source is missing/invalid for an ICS-flagged account, label as 'ICS-Unknown'
    valid_channels = set(ICS_CHANNELS)
    bad_source = is_ics & ~ics_subset['source_channel'].isin(valid_channels)
    if bad_source.sum() > 0:
        ics_subset.loc[bad_source, 'ics_account'] = 'ICS-Unknown'
        print(f"    Note: {bad_source.sum():,} ICS accounts have no valid Source channel")

    # Keep only the columns needed for merge
    ics_subset = ics_subset[['account_number', 'ics_account']]

    # Drop stale merge columns if re-running
    if 'ics_account' in combined_df.columns:
        combined_df.drop(columns='ics_account', inplace=True)

    ics_merged = combined_df.merge(
        ics_subset,
        left_on='primary_account_num',
        right_on='account_number',
        how='left',
    ).drop(columns='account_number')

    ics_merged['ics_account'] = ics_merged['ics_account'].fillna('Non-ICS')

    # Store on combined_df
    combined_df['ics_account'] = ics_merged['ics_account']

    # Account-level map for other folders
    ics_acct_map = ics_subset.rename(columns={'account_number': 'primary_account_num'})

    # Split
    ics_df = ics_merged[ics_merged['ics_account'].isin(ICS_CHANNELS)].copy()
    ics_ref_df = ics_merged[ics_merged['ics_account'] == 'REF'].copy()
    ics_dm_df = ics_merged[ics_merged['ics_account'] == 'DM'].copy()
    non_ics_df = ics_merged[ics_merged['ics_account'] == 'Non-ICS'].copy()

    # Check if we have meaningful ICS data
    ics_values = ics_merged['ics_account'].value_counts()

    if len(ics_df) == 0:
        print("    No ICS accounts found in dataset. Skipping ICS analysis.")
        ics_agg = pd.DataFrame()
    else:
        # -----------------------------------------------------------------------
        # Core ICS aggregation by channel (with time-normalized metrics)
        # -----------------------------------------------------------------------
        _n_months = DATASET_MONTHS  # from setup/09

        ics_agg = ics_merged.groupby('ics_account').agg(
            txn_count=('transaction_date', 'count'),
            unique_accounts=('primary_account_num', 'nunique'),
            total_spend=('amount', 'sum'),
            avg_spend=('amount', 'mean'),
            median_spend=('amount', 'median'),
        ).reset_index()

        total_txns_ics = len(ics_merged)
        total_accts_ics = ics_merged['primary_account_num'].nunique()

        ics_agg['txn_pct'] = ics_agg['txn_count'] / total_txns_ics * 100
        ics_agg['acct_pct'] = ics_agg['unique_accounts'] / total_accts_ics * 100
        ics_agg['txn_per_account'] = ics_agg['txn_count'] / ics_agg['unique_accounts']

        # Time-normalized: per account per month
        ics_agg['txns_per_acct_mo'] = ics_agg['txn_per_account'] / _n_months
        ics_agg['spend_per_acct_mo'] = ics_agg['total_spend'] / ics_agg['unique_accounts'] / _n_months

        ics_agg = ics_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)

        # -----------------------------------------------------------------------
        # Monthly trend by ICS channel
        # -----------------------------------------------------------------------
        ics_monthly = ics_merged.groupby(
            ['year_month', 'ics_account']
        ).agg(txn_count=('transaction_date', 'count')).reset_index()

        ics_month_totals = ics_merged.groupby('year_month').size().reset_index(name='month_total')
        ics_monthly = ics_monthly.merge(ics_month_totals, on='year_month')
        ics_monthly['share_pct'] = ics_monthly['txn_count'] / ics_monthly['month_total'] * 100

        # -----------------------------------------------------------------------
        # Conference-styled summary table
        # -----------------------------------------------------------------------
        ics_display = ics_agg[['ics_account', 'txn_count', 'txn_pct', 'unique_accounts',
                                'acct_pct', 'total_spend', 'avg_spend',
                                'txns_per_acct_mo', 'spend_per_acct_mo']].copy()
        ics_display.columns = ['Channel', 'Transactions', 'Txn %', 'Accounts',
                                'Acct %', 'Total Spend', 'Avg Ticket',
                                'Txns/Acct/Mo', 'Spend/Acct/Mo']

        styled = (
            ics_display.style
            .hide(axis='index')
            .format({
                'Transactions': '{:,.0f}',
                'Txn %': '{:.1f}%',
                'Accounts': '{:,.0f}',
                'Acct %': '{:.1f}%',
                'Total Spend': '${:,.0f}',
                'Avg Ticket': '${:.2f}',
                'Txns/Acct/Mo': '{:.1f}',
                'Spend/Acct/Mo': '${:,.0f}',
            })
            .set_properties(**{
                'font-size': '13px', 'font-weight': 'bold',
                'text-align': 'center', 'border': '1px solid #E9ECEF',
                'padding': '7px 10px',
            })
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', GEN_COLORS['info']),
                    ('color', 'white'), ('font-size', '14px'),
                    ('font-weight', 'bold'), ('text-align', 'center'),
                    ('padding', '8px 10px'),
                ]},
                {'selector': 'caption', 'props': [
                    ('font-size', '22px'), ('font-weight', 'bold'),
                    ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                    ('padding-bottom', '12px'),
                ]},
            ])
            .set_caption(f"ICS Acquisition Channel Summary  ({DATASET_LABEL}, {_n_months} months)")
            .bar(subset=['Transactions'], color=GEN_COLORS['info'], vmin=0)
        )

        display(styled)

        ics_total_accts = ics_agg[ics_agg['ics_account'] != 'Non-ICS']['unique_accounts'].sum()
        ics_total_pct = ics_agg[ics_agg['ics_account'] != 'Non-ICS']['acct_pct'].sum()
        print(f"\n    Period: {DATASET_LABEL} ({_n_months} months)")
        print(f"    ICS accounts: {ics_total_accts:,} ({ics_total_pct:.1f}% of all accounts)")
        print(f"    Channel breakdown: {dict(ics_values)}")
        print(f"    ICS avg ticket: ${ics_df['amount'].mean():.2f} vs Non-ICS: ${non_ics_df['amount'].mean():.2f}")

except (NameError, KeyError) as e:
    print(f"    ICS Account data not available: {e}")
    print("    Skipping ICS acquisition analysis.")
    ics_agg = pd.DataFrame()
