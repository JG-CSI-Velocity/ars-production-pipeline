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
    # Detect rewards_df columns -- exports vary (Acct Number vs Account Number,
    # ICS Account vs ICS Acct, Source vs Source Channel). Hard-coded names
    # previously skipped the ENTIRE section via the except below when one differed.
    def _pick(cols, *cands):
        return next((c for c in cands if c in cols), None)
    _acct_col = _pick(rewards_df.columns, 'Acct Number', ' Acct Number', 'Account Number', 'AcctNumber')
    _ics_col  = _pick(rewards_df.columns, 'ICS Account', 'ICS Acct', 'ICS', 'ICS?')
    _src_col  = _pick(rewards_df.columns, 'Source', 'Source Channel', 'Channel', 'Acquisition Source')
    if not all((_acct_col, _ics_col, _src_col)):
        raise KeyError(
            f"ICS columns missing in rewards_df (acct={_acct_col}, ics={_ics_col}, src={_src_col})"
        )

    ics_subset = rewards_df[[_acct_col, _ics_col, _src_col]].copy()
    ics_subset.columns = ['account_number', 'ics_flag', 'source_channel']
    ics_subset['account_number'] = ics_subset['account_number'].astype(str).str.strip()
    ics_subset['ics_flag'] = ics_subset['ics_flag'].astype(str).str.strip().str.upper()
    ics_subset['source_channel'] = ics_subset['source_channel'].astype(str).str.strip().str.upper()

    # Diagnostic: show detected columns + raw values BEFORE classification
    _flag_vals = ics_subset['ics_flag'].value_counts()
    _src_vals = ics_subset['source_channel'].value_counts()
    print(f"    ICS columns: acct={_acct_col!r}  ics={_ics_col!r}  source={_src_col!r}")
    print("    Raw ICS Account flag values:")
    for val, cnt in _flag_vals.items():
        marker = " <-- ICS" if val in _ICS_YES else ""
        print(f"      {val!r:12s} {cnt:>8,} accounts{marker}")
    print("    Raw Source channel values:")
    for val, cnt in _src_vals.items():
        marker = " <-- channel" if val in ICS_CHANNELS else ""
        print(f"      {val!r:12s} {cnt:>8,} accounts{marker}")

    # Build ics_account: Source channel for ICS accounts, 'Non-ICS' for the rest
    is_ics = ics_subset['ics_flag'].isin(_ICS_YES)
    ics_subset['ics_account'] = 'Non-ICS'
    ics_subset.loc[is_ics, 'ics_account'] = ics_subset.loc[is_ics, 'source_channel']

    # ICS-flagged but no valid Source channel -> ICS-Unknown (still counts as ICS)
    valid_channels = set(ICS_CHANNELS)
    bad_source = is_ics & ~ics_subset['source_channel'].isin(valid_channels)
    if bad_source.sum() > 0:
        ics_subset.loc[bad_source, 'ics_account'] = 'ICS-Unknown'
        print(f"    Note: {bad_source.sum():,} ICS accounts have no valid Source channel")

    # One row per account. Prefer an ICS-flagged row over a Non-ICS duplicate so a
    # fan-out in rewards_df can't bury the ICS label.
    ics_subset = ics_subset[['account_number', 'ics_account']].copy()
    ics_subset['_is_ics'] = ics_subset['ics_account'] != 'Non-ICS'
    ics_subset = (ics_subset.sort_values('_is_ics', ascending=False)
                            .drop_duplicates(subset='account_number', keep='first')
                            .drop(columns='_is_ics'))

    # Assign by mapping on a NORMALIZED key. Avoids the prior left-merge that
    # (a) joined primary_account_num un-normalized -- any format drift made every
    # account fall to Non-ICS -- and (b) could fan out + misalign on positional
    # reassignment. map+fillna aligns on combined_df's own index, length-safe.
    _ics_map = ics_subset.set_index('account_number')['ics_account']
    _key = combined_df['primary_account_num'].astype(str).str.strip()
    combined_df['ics_account'] = _key.map(_ics_map).fillna('Non-ICS')
    ics_merged = combined_df

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
