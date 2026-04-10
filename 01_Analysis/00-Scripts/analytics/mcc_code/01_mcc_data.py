# ===========================================================================
# MCC DATA: Master Category Pipeline (Conference Edition)
# ===========================================================================
# Single aggregation, multiple views. Merges ODDD demographics.
# Replaces 3 duplicated top-50 cells with one clean data layer.

if 'mcc_code' not in combined_df.columns or combined_df['mcc_code'].notna().sum() == 0:
    print("    No MCC code data available in this dataset. Skipping MCC analysis.")
    mcc_agg = pd.DataFrame()
    mcc_top20 = pd.DataFrame()
    mcc_top50 = pd.DataFrame()
    top10_codes = []
    mcc_monthly = pd.DataFrame()
else:
    # ---------------------------------------------------------------------------
    # Core MCC aggregation from combined_df
    # ---------------------------------------------------------------------------
    mcc_agg = combined_df.groupby('mcc_code').agg(
        txn_count=('transaction_date', 'count'),
        unique_accounts=('primary_account_num', 'nunique'),
        unique_merchants=('merchant_consolidated', 'nunique'),
        total_spend=('amount', 'sum'),
        avg_spend=('amount', 'mean'),
        median_spend=('amount', 'median'),
    ).reset_index()

    total_txns_all = len(combined_df)
    total_accts_all = combined_df['primary_account_num'].nunique()

    mcc_agg['txn_pct'] = mcc_agg['txn_count'] / total_txns_all * 100
    mcc_agg['acct_pct'] = mcc_agg['unique_accounts'] / total_accts_all * 100
    mcc_agg['txn_per_account'] = mcc_agg['txn_count'] / mcc_agg['unique_accounts']
    mcc_agg = mcc_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)

    # Cumulative share
    mcc_agg['cumulative_txn_pct'] = mcc_agg['txn_pct'].cumsum()

    # Rank
    mcc_agg['rank'] = range(1, len(mcc_agg) + 1)

    # ---------------------------------------------------------------------------
    # Top slices for downstream cells
    # ---------------------------------------------------------------------------
    mcc_top20 = mcc_agg.head(20).copy()
    mcc_top50 = mcc_agg.head(50).copy()

    # ---------------------------------------------------------------------------
    # Monthly MCC trend (top 10 by txn count, share over time)
    # ---------------------------------------------------------------------------
    top10_codes = mcc_agg.head(10)['mcc_code'].tolist()
    mcc_monthly = combined_df[combined_df['mcc_code'].isin(top10_codes)].groupby(
        ['year_month', 'mcc_code']
    ).size().reset_index(name='txn_count')

    monthly_totals = combined_df.groupby('year_month').size().reset_index(name='month_total')
    mcc_monthly = mcc_monthly.merge(monthly_totals, on='year_month')
    mcc_monthly['share_pct'] = mcc_monthly['txn_count'] / mcc_monthly['month_total'] * 100

    # ---------------------------------------------------------------------------
    # Conference-styled top 20 summary
    # ---------------------------------------------------------------------------
    mcc_display = mcc_top20[['rank', 'mcc_code', 'txn_count', 'txn_pct',
                              'unique_accounts', 'acct_pct', 'unique_merchants',
                              'total_spend', 'txn_per_account']].copy()
    mcc_display.columns = ['Rank', 'MCC', 'Transactions', 'Txn %', 'Accounts',
                            'Acct %', 'Merchants', 'Total Spend', 'Txns/Acct']

    styled = (
        mcc_display.style
        .hide(axis='index')
        .format({
            'Rank': '{:.0f}',
            'Transactions': '{:,.0f}',
            'Txn %': '{:.1f}%',
            'Accounts': '{:,.0f}',
            'Acct %': '{:.1f}%',
            'Merchants': '{:,.0f}',
            'Total Spend': '${:,.0f}',
            'Txns/Acct': '{:.1f}',
        })
        .set_properties(**{
            'font-size': '13px',
            'font-weight': 'bold',
            'text-align': 'center',
            'border': '1px solid #E9ECEF',
            'padding': '7px 10px',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['primary']),
                ('color', 'white'),
                ('font-size', '14px'),
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('padding', '8px 10px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'),
                ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']),
                ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption("Top 20 MCC Categories by Transaction Volume")
        .bar(subset=['Transactions'], color=GEN_COLORS['info'], vmin=0)
    )

    display(styled)

    top20_txn_share = mcc_top20['txn_pct'].sum()
    print(f"\n    {len(mcc_agg)} total MCC codes")
    print(f"    Top 20 = {top20_txn_share:.1f}% of all transactions")
    print(f"    Top 50 = {mcc_top50['txn_pct'].sum():.1f}% of all transactions")
