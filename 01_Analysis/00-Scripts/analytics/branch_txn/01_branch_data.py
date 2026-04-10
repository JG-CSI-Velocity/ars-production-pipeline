# ===========================================================================
# BRANCH DATA: Master Aggregation Pipeline (Conference Edition)
# ===========================================================================
# Merges Branch from rewards_df onto combined_df. Builds: br_agg, br_monthly, br_top15.
# Guard: try/except for missing Branch column in ODDD.

try:
    import json, os

    # ------------------------------------------------------------------
    # Load branch name mapping from JSON config (branch number -> name)
    # Expected format: {"1": "Main Office", "2": "West Branch", ...}
    # Place file as branch_config.json in repo root or 10-branch/ folder.
    # ------------------------------------------------------------------
    BRANCH_NAME_MAP = {}
    _br_config_paths = [
        os.path.join(os.path.dirname(os.getcwd()), 'branch_config.json'),
        os.path.join(os.getcwd(), 'branch_config.json'),
        'branch_config.json',
        os.path.join('10-branch', 'branch_config.json'),
    ]
    # Also check the notebook's directory if running from Jupyter
    try:
        _nb_dir = os.path.dirname(os.path.abspath(''))
        _br_config_paths.append(os.path.join(_nb_dir, 'branch_config.json'))
    except Exception:
        pass

    for _cfg_path in _br_config_paths:
        if os.path.exists(_cfg_path):
            with open(_cfg_path, 'r') as _f:
                BRANCH_NAME_MAP = json.load(_f)
            print(f"    Branch config loaded: {_cfg_path} ({len(BRANCH_NAME_MAP)} branches)")
            break

    if not BRANCH_NAME_MAP:
        print("    WARNING: branch_config.json not found. Branch names will show as numbers.")
        print("    Place branch_config.json in repo root with format: {\"1\": \"Main Office\", ...}")

    # Merge Branch onto combined_df
    br_subset = rewards_df[['Acct Number', 'Branch']].copy()
    br_subset.columns = ['account_number', 'branch']
    br_subset['account_number'] = br_subset['account_number'].astype(str).str.strip()

    # Drop stale merge columns if re-running
    for col in ['branch', 'account_number_br']:
        if col in combined_df.columns:
            combined_df.drop(columns=col, inplace=True)

    br_merged = combined_df.merge(
        br_subset,
        left_on='primary_account_num',
        right_on='account_number',
        how='left'
    ).drop(columns='account_number')

    # Store branch column on combined_df for other folders
    combined_df['branch'] = br_merged['branch']

    # Filter to records with branch data
    br_df = br_merged[br_merged['branch'].notna()].copy()
    br_df['branch'] = br_df['branch'].astype(str).str.strip()

    # Apply branch name mapping if config was loaded
    if BRANCH_NAME_MAP:
        # Try mapping with raw value, then stripped of decimals (e.g. "1.0" -> "1")
        def _map_branch(val):
            if val in BRANCH_NAME_MAP:
                return BRANCH_NAME_MAP[val]
            clean = val.split('.')[0]  # "1.0" -> "1"
            if clean in BRANCH_NAME_MAP:
                return BRANCH_NAME_MAP[clean]
            return val  # Fallback: keep original number

        br_df['branch'] = br_df['branch'].apply(_map_branch)
        combined_df['branch'] = combined_df['branch'].astype(str).str.strip().apply(_map_branch)
        n_mapped = (br_df['branch'] != br_df['branch'].str.replace(r'\D', '', regex=True)).sum()
        print(f"    Branch names mapped: {br_df['branch'].nunique()} unique branches")

    if len(br_df) == 0:
        print("    All branch values are null. Skipping branch analysis.")
        br_agg = pd.DataFrame()
    else:
        # -----------------------------------------------------------------------
        # Core branch aggregation
        # -----------------------------------------------------------------------
        br_agg = br_df.groupby('branch').agg(
            txn_count=('transaction_date', 'count'),
            unique_accounts=('primary_account_num', 'nunique'),
            total_spend=('amount', 'sum'),
            avg_spend=('amount', 'mean'),
            median_spend=('amount', 'median'),
        ).reset_index()

        total_txns_br = len(br_df)
        total_accts_br = br_df['primary_account_num'].nunique()

        br_agg['txn_pct'] = br_agg['txn_count'] / total_txns_br * 100
        br_agg['acct_pct'] = br_agg['unique_accounts'] / total_accts_br * 100
        br_agg['txn_per_account'] = br_agg['txn_count'] / br_agg['unique_accounts']
        br_agg = br_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)
        br_agg['cumulative_txn_pct'] = br_agg['txn_pct'].cumsum()
        br_agg['rank'] = range(1, len(br_agg) + 1)

        br_top15 = br_agg.head(15).copy()

        # -----------------------------------------------------------------------
        # Monthly trend (top 5 branches)
        # -----------------------------------------------------------------------
        top5_branches = br_agg.head(5)['branch'].tolist()
        br_monthly = br_df[br_df['branch'].isin(top5_branches)].groupby(
            ['year_month', 'branch']
        ).agg(txn_count=('transaction_date', 'count')).reset_index()

        br_month_totals = br_df.groupby('year_month').size().reset_index(name='month_total')
        br_monthly = br_monthly.merge(br_month_totals, on='year_month')
        br_monthly['share_pct'] = br_monthly['txn_count'] / br_monthly['month_total'] * 100

        # -----------------------------------------------------------------------
        # Conference-styled top branches table
        # -----------------------------------------------------------------------
        br_display = br_top15[['rank', 'branch', 'txn_count', 'txn_pct',
                                'unique_accounts', 'total_spend', 'txn_per_account']].copy()
        br_display.columns = ['Rank', 'Branch', 'Transactions', 'Txn %',
                               'Accounts', 'Total Spend', 'Txns/Acct']

        styled = (
            br_display.style
            .hide(axis='index')
            .format({
                'Rank': '{:.0f}',
                'Transactions': '{:,.0f}',
                'Txn %': '{:.1f}%',
                'Accounts': '{:,.0f}',
                'Total Spend': '${:,.0f}',
                'Txns/Acct': '{:.1f}',
            })
            .set_properties(**{
                'font-size': '13px', 'font-weight': 'bold',
                'text-align': 'center', 'border': '1px solid #E9ECEF',
                'padding': '7px 10px',
            })
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', GEN_COLORS['accent']),
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
            .set_caption("Top 15 Branches by Transaction Volume")
            .bar(subset=['Transactions'], color=GEN_COLORS['accent'], vmin=0)
        )

        display(styled)

        print(f"\n    {len(br_agg)} branches with transaction data")
        print(f"    Top branch: {br_agg.iloc[0]['branch']} ({br_agg.iloc[0]['txn_pct']:.1f}% of txns)")
        print(f"    Top 5 = {br_agg.head(5)['txn_pct'].sum():.1f}% of transactions")
        print(f"    {total_accts_br:,} accounts matched to branches")

except (NameError, KeyError) as e:
    print(f"    Branch data not available: {e}")
    print("    Skipping branch analysis.")
    br_agg = pd.DataFrame()
