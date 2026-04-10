# ===========================================================================
# ACCOUNT SUMMARIES: Per-Competitor Account-Level Metrics
# ===========================================================================
# Builds all_account_summaries dict for downstream deep-dive visualizations.
# Vectorized: single groupby on full data, then split into dict.

if len(all_competitor_data) > 0:
    # Ensure competitor_match exists (created in cell 02; guard for run-order safety)
    if 'competitor_match' not in competitor_txns.columns:
        competitor_txns['competitor_match'] = competitor_txns['merchant_consolidated'].apply(normalize_competitor_name)

    # One bulk groupby instead of N individual ones
    _bulk = (
        competitor_txns.groupby(['competitor_match', 'primary_account_num'])
        .agg(
            total_amount=('amount', 'sum'),
            txn_count=('amount', 'count'),
            avg_amount=('amount', 'mean'),
            first_txn=('transaction_date', 'min'),
            last_txn=('transaction_date', 'max'),
        )
        .round(2)
    )
    _bulk['days_active'] = (_bulk['last_txn'] - _bulk['first_txn']).dt.days
    _bulk['recency_days'] = (DATASET_END - _bulk['last_txn']).dt.days

    # Split into dict (trivial -- no computation, just index slicing)
    all_account_summaries = {
        comp: grp.droplevel(0).sort_values('total_amount', ascending=False)
        for comp, grp in _bulk.groupby(level=0)
    }
    del _bulk

    print(f"    Built account summaries for {len(all_account_summaries)} competitors")
else:
    all_account_summaries = {}
    print("    No competitor data -- skipping account summaries")
