# ===========================================================================
# BUSINESS ACCOUNT DATA: Master Aggregation Pipeline (Conference Edition)
# ===========================================================================
# Single aggregation for business account merchants.
# Builds: biz_agg, biz_top20, biz_monthly, biz_consistency_df, biz_cohort_df.
# Guard: skips gracefully if no business data exists.

if 'business_df' not in dir() or business_df is None or len(business_df) == 0:
    print("    No business account data in this dataset. Skipping.")
else:
    try:
        # Safety: fill any remaining NaN merchant names
        _biz_nan = business_df['merchant_consolidated'].isna().sum()
        if _biz_nan > 0:
            business_df['merchant_consolidated'] = business_df['merchant_consolidated'].fillna('UNKNOWN MERCHANT')
            print(f"    Filled {_biz_nan:,} NaN merchant names with 'UNKNOWN MERCHANT'")

        # -------------------------------------------------------------------
        # Core merchant aggregation (business accounts only)
        # -------------------------------------------------------------------
        biz_agg = business_df.groupby('merchant_consolidated').agg(
            txn_count=('transaction_date', 'count'),
            unique_accounts=('primary_account_num', 'nunique'),
            total_spend=('amount', 'sum'),
            avg_spend=('amount', 'mean'),
            median_spend=('amount', 'median'),
        ).reset_index()

        total_txns_biz = len(business_df)
        total_accts_biz = business_df['primary_account_num'].nunique()

        biz_agg['txn_pct'] = biz_agg['txn_count'] / total_txns_biz * 100
        biz_agg['acct_pct'] = biz_agg['unique_accounts'] / total_accts_biz * 100
        biz_agg['txn_per_account'] = biz_agg['txn_count'] / biz_agg['unique_accounts']
        biz_agg = biz_agg.sort_values('txn_count', ascending=False).reset_index(drop=True)
        biz_agg['cumulative_txn_pct'] = biz_agg['txn_pct'].cumsum()
        biz_agg['rank'] = range(1, len(biz_agg) + 1)

        # Top slices
        biz_top20 = biz_agg.head(20).copy()
        biz_top50 = biz_agg.head(50).copy()

        # Concentration metrics (computed early so downstream cells can use them)
        top5_share_biz = biz_agg.head(5)['txn_pct'].sum()
        top10_share_biz = biz_agg.head(10)['txn_pct'].sum()

        # -------------------------------------------------------------------
        # Monthly merchant trend (top 10 business merchants)
        # -------------------------------------------------------------------
        top10_biz = biz_agg.head(10)['merchant_consolidated'].tolist()
        biz_monthly = business_df[business_df['merchant_consolidated'].isin(top10_biz)].groupby(
            ['year_month', 'merchant_consolidated']
        ).agg(txn_count=('transaction_date', 'count')).reset_index()

        monthly_totals_biz = business_df.groupby('year_month').size().reset_index(name='month_total')
        biz_monthly = biz_monthly.merge(monthly_totals_biz, on='year_month')
        biz_monthly['share_pct'] = biz_monthly['txn_count'] / biz_monthly['month_total'] * 100

        # -------------------------------------------------------------------
        # Spend consistency (CV per merchant, business transactions only)
        # -------------------------------------------------------------------
        b_monthly_spend = business_df.groupby(
            ['merchant_consolidated', 'year_month']
        )['amount'].sum().reset_index()

        b_pivot = b_monthly_spend.pivot(
            index='merchant_consolidated', columns='year_month', values='amount'
        ).fillna(0)

        biz_consist_rows = []
        for merchant in b_pivot.index:
            vals = b_pivot.loc[merchant].values
            nonzero = vals[vals > 0]
            if len(nonzero) >= 3 and nonzero.mean() > 0:
                cv = nonzero.std() / nonzero.mean() * 100
                biz_consist_rows.append({
                    'merchant_consolidated': merchant,
                    'total_spend': nonzero.sum(),
                    'mean_monthly': nonzero.mean(),
                    'cv': cv,
                    'months_active': len(nonzero),
                })

        biz_consistency_df = pd.DataFrame(biz_consist_rows)
        biz_consistency_df = biz_consistency_df[biz_consistency_df['total_spend'] >= 10000].copy()

        # Cap CV at 500% to prevent renderer overflow
        if len(biz_consistency_df) > 0:
            biz_consistency_df['cv'] = biz_consistency_df['cv'].clip(upper=500)

        # -------------------------------------------------------------------
        # Merchant cohort (new / returning / lost per month)
        # -------------------------------------------------------------------
        sorted_months_biz = sorted(business_df['year_month'].unique())
        _biz_valid = business_df[business_df['merchant_consolidated'].notna()]
        first_month_map_biz = _biz_valid.groupby('merchant_consolidated')['year_month'].min()
        monthly_sets_biz = {m: set(_biz_valid[_biz_valid['year_month'] == m]['merchant_consolidated'].unique())
                            for m in sorted_months_biz}

        biz_cohort_rows = []
        for i, month in enumerate(sorted_months_biz):
            current = monthly_sets_biz[month]
            new_m = {m for m in current if first_month_map_biz[m] == month}
            if i > 0:
                prev = monthly_sets_biz[sorted_months_biz[i - 1]]
                returning = {m for m in current if m not in prev and first_month_map_biz[m] != month}
                lost = prev - current
            else:
                returning = set()
                lost = set()
            continuing = current - new_m - returning

            biz_cohort_rows.append({
                'year_month': month,
                'total': len(current), 'new': len(new_m),
                'returning': len(returning), 'continuing': len(continuing),
                'lost': len(lost),
            })

        biz_cohort_df = pd.DataFrame(biz_cohort_rows)

        # -------------------------------------------------------------------
        # Conference-styled top 20 table
        # -------------------------------------------------------------------
        b_display = biz_top20[['rank', 'merchant_consolidated', 'txn_count', 'txn_pct',
                                'unique_accounts', 'total_spend', 'txn_per_account']].copy()
        b_display.columns = ['Rank', 'Merchant', 'Transactions', 'Txn %',
                              'Accounts', 'Total Spend', 'Txns/Acct']
        b_display['Merchant'] = b_display['Merchant'].str[:35]

        styled = (
            b_display.style
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
                    ('background-color', GEN_COLORS['primary']), ('color', 'white'),
                    ('font-size', '14px'), ('font-weight', 'bold'),
                    ('text-align', 'center'), ('padding', '8px 10px'),
                ]},
                {'selector': 'caption', 'props': [
                    ('font-size', '22px'), ('font-weight', 'bold'),
                    ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                    ('padding-bottom', '12px'),
                ]},
            ])
            .set_caption("Top 20 Business Account Merchants by Transaction Volume")
            .bar(subset=['Transactions'], color=GEN_COLORS['primary'], vmin=0)
        )

        display(styled)

        print(f"\n    {len(biz_agg)} business merchants")
        print(f"    Top 5 = {top5_share_biz:.1f}% of business transactions")
        print(f"    Top 10 = {top10_share_biz:.1f}% of business transactions")
        print(f"    Top 20 = {biz_top20['txn_pct'].sum():.1f}% of business transactions")
        print(f"    Consistency metrics: {len(biz_consistency_df)} merchants with $10K+ business spend")

    except Exception as e:
        import traceback
        print(f"    Business data pipeline error: {e}")
        traceback.print_exc()
