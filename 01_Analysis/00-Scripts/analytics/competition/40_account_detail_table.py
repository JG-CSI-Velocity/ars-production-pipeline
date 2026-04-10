# ===========================================================================
# ACCOUNT DETAIL TABLES: Per-Competitor Account Summaries
# ===========================================================================
# Display-only cell. Data already built in cell 19 (all_account_summaries).
# Shows formatted top-25 tables per competitor. This cell can be slow for
# many competitors -- placed at end so visualizations render first.

if len(all_account_summaries) > 0:
    # Build category lookup from competitor_txns (robust to key mismatches)
    _cat_lookup_40 = (
        competitor_txns.groupby('competitor_match')['competitor_category']
        .first()
        .to_dict()
    )

    for comp_name in deep_dive_competitors:
        if comp_name not in all_account_summaries:
            continue

        acct = all_account_summaries[comp_name]
        cat = _cat_lookup_40.get(comp_name, 'unknown')
        cat_label = clean_category(cat)

        print(f"\n    {comp_name} [{cat_label}] -- Top 25 Accounts by Spend")
        print(f"    {'_' * 80}")

        _disp = acct.head(25).copy()
        _disp['total_amount'] = _disp['total_amount'].apply(lambda x: f"${x:,.2f}")
        _disp['avg_amount'] = _disp['avg_amount'].apply(lambda x: f"${x:,.2f}")
        _disp['first_txn'] = _disp['first_txn'].dt.strftime('%Y-%m-%d')
        _disp['last_txn'] = _disp['last_txn'].dt.strftime('%Y-%m-%d')

        _disp.columns = [
            'Total Spend', 'Txn Count', 'Avg Txn',
            'First Txn', 'Last Txn',
            'Days Active', 'Recency (Days)',
        ]

        display(_disp)

        # Quick segmentation stats
        high_val = (acct['total_amount'] > 1000).sum()
        frequent = (acct['txn_count'] >= 5).sum()
        recent_30 = (acct['recency_days'] <= 30).sum()
        recent_90 = (acct['recency_days'] <= 90).sum()
        n = len(acct)

        print(f"    High Value (>$1K):     {high_val:,} ({high_val/n*100:.1f}%)")
        print(f"    Frequent (5+ txns):    {frequent:,} ({frequent/n*100:.1f}%)")
        print(f"    Active last 30 days:   {recent_30:,} ({recent_30/n*100:.1f}%)")
        print(f"    Active last 90 days:   {recent_90:,} ({recent_90/n*100:.1f}%)")

    print(f"\n    Showing detail for top {len(deep_dive_competitors)} competitors")
    print(f"    Full data available in all_account_summaries dict "
          f"({len(all_account_summaries)} competitors)")
