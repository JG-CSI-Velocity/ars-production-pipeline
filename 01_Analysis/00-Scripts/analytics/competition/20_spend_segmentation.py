# ===========================================================================
# SPEND SEGMENTATION: Competitor Wallet-Share Analysis
# ===========================================================================
# Single canonical build of competitor_spend_analysis.
# 3-tier segments: Primary (<25%), Balanced (25-50%), Competitor-Heavy (>50%)
# Vectorized: one bulk groupby + one merge, then split into dict.

# How many competitors get individual deep-dive charts (cells 25-29)
DEEP_DIVE_TOP_N = 8

SEGMENT_LABELS = ['Primary', 'Balanced', 'Competitor-Heavy']
SEGMENT_BINS   = [0, 25, 50, 100]

SEGMENT_PALETTE = {
    'Competitor-Heavy': GEN_COLORS['accent'],
    'Balanced':         GEN_COLORS['warning'],
    'Primary':       GEN_COLORS['success'],
}

if len(all_competitor_data) > 0:
    # Ensure competitor_match exists (created in cell 02; guard for run-order safety)
    if 'competitor_match' not in competitor_txns.columns:
        competitor_txns['competitor_match'] = competitor_txns['merchant_consolidated'].apply(normalize_competitor_name)

    # Total spend per account across ALL transactions (computed once)
    _account_totals = (
        combined_df.groupby('primary_account_num')
        .agg(total_spend=('amount', 'sum'), total_txns=('amount', 'count'))
        .reset_index()
    )

    # One bulk groupby instead of N individual ones
    _acct_comp = (
        competitor_txns.groupby(['competitor_match', 'primary_account_num'])
        .agg(competitor_spend=('amount', 'sum'), competitor_txns=('amount', 'count'))
        .reset_index()
    )

    # One merge instead of N individual merges
    _merged = _acct_comp.merge(_account_totals, on='primary_account_num', how='left')
    del _acct_comp, _account_totals

    _merged['your_spend'] = _merged['total_spend'] - _merged['competitor_spend']
    _merged['your_txns'] = _merged['total_txns'] - _merged['competitor_txns']
    _merged['competitor_pct'] = (
        _merged['competitor_spend'] / _merged['total_spend'] * 100
    ).clip(0, 100)
    _merged['segment'] = pd.cut(
        _merged['competitor_pct'],
        bins=SEGMENT_BINS,
        labels=SEGMENT_LABELS,
        include_lowest=True,
    )

    # Add category from competitor_txns (one lookup, not N)
    _cat_map = competitor_txns.groupby('competitor_match')['competitor_category'].first()
    _merged['competitor_category'] = _merged['competitor_match'].map(_cat_map)
    _merged['competitor_name'] = _merged['competitor_match']

    # Split into dict (trivial index slicing)
    competitor_spend_analysis = {
        name: grp.reset_index(drop=True)
        for name, grp in _merged.groupby('competitor_match')
    }
    del _merged

    # Rank TRUE competitors by account count for deep-dive selection
    # (exclude payment ecosystems: wallets, p2p, bnpl)
    _comp_sizes = {
        name: len(df) for name, df in competitor_spend_analysis.items()
        if df['competitor_category'].iloc[0] not in PAYMENT_ECOSYSTEMS
    }
    deep_dive_competitors = sorted(
        _comp_sizes, key=_comp_sizes.get, reverse=True
    )[:DEEP_DIVE_TOP_N]

    # Summary
    total_heavy = sum(
        (df['segment'] == 'Competitor-Heavy').sum()
        for df in competitor_spend_analysis.values()
    )
    total_balanced = sum(
        (df['segment'] == 'Balanced').sum()
        for df in competitor_spend_analysis.values()
    )
    total_cu = sum(
        (df['segment'] == 'Primary').sum()
        for df in competitor_spend_analysis.values()
    )

    print(f"    Built spend segmentation for {len(competitor_spend_analysis)} competitors")
    print(f"    Deep-dive charts will cover top {DEEP_DIVE_TOP_N}: {', '.join(deep_dive_competitors[:3])}...")
    print(f"\n    Segment Totals (account-competitor pairs):")
    print(f"      Competitor-Heavy (>50%):  {total_heavy:,}")
    print(f"      Balanced (25-50%):        {total_balanced:,}")
    print(f"      Primary (<25%):        {total_cu:,}")

else:
    competitor_spend_analysis = {}
    deep_dive_competitors = []
    print("    No competitor data -- skipping spend segmentation")
