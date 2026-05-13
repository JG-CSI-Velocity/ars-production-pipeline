# ===========================================================================
# CROSS-SELL EXPORT: Account-Level CSV Files (CSM hand-off)
# ===========================================================================
# The CSV files this cell produces are what the CSM hands to the client.
# Three files per competitor:
#   1. <competitor>_wallet_share.csv    -- every account that has spent at
#                                          that competitor, with totals + %
#   2. <competitor>_at_risk.csv         -- subset where competitor share > 50%
#                                          (leakage hotspots)
#   3. <competitor>_opportunity.csv     -- subset where competitor share < 25%
#                                          (cross-sell targets)
#
# This cell is DEFENSIVE -- it does its own groupby off competitor_txns +
# combined_df instead of depending on the heavy cell 20 output. If cell 20
# blew up on memory or any of cells 19/25-29 failed, these CSVs still ship.
# That matters: the CSV hand-off is the CSM's actual deliverable to the
# client. The slides are nice; the lists are operational.
#
# Output folder: <client output root>/cross_sell_lists/
# Anchored on ctx.paths if available (matches the rest of the pipeline)
# with a working-dir fallback so notebook runs still work.

from pathlib import Path
import os as _os

# ---------------------------------------------------------------------------
# Resolve output folder
# ---------------------------------------------------------------------------
_out_root = None
try:
    # ctx is injected by the pipeline runner for module-mode runs.
    _out_root = Path(ctx.paths.client_dir) / "cross_sell_lists"     # type: ignore[name-defined]
except Exception:
    _out_root = None

if _out_root is None:
    # Notebook / standalone fallback. Use CWD-relative path so this cell
    # never silently writes to a surprising location.
    _client_id = globals().get('CLIENT_ID', 'unknown')
    _client_name = globals().get('CLIENT_NAME', 'client')
    _out_root = Path(f"output/{_client_id}_{_client_name}/cross_sell_lists")

_out_root.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Build per-account totals directly (independent of cell 20)
# ---------------------------------------------------------------------------
_have_comp = (
    'competitor_txns' in dir() and len(competitor_txns) > 0
    and 'combined_df' in dir() and len(combined_df) > 0
)

if not _have_comp:
    print(f"    No competitor data -- skipping cross-sell export ({_out_root})")
else:
    # Ensure competitor_match exists (in case cell 02 didn't set it)
    if 'competitor_match' not in competitor_txns.columns:
        competitor_txns['competitor_match'] = (
            competitor_txns['merchant_consolidated']
            .apply(normalize_competitor_name)
        )

    # Total spend per account across ALL transactions
    _acct_total = (
        combined_df.groupby('primary_account_num')
        .agg(total_spend=('amount', 'sum'),
             total_txns=('amount', 'count'))
        .reset_index()
    )

    # Per (competitor, account) spend
    _acct_comp = (
        competitor_txns.groupby(['competitor_match', 'primary_account_num'])
        .agg(competitor_spend=('amount', 'sum'),
             competitor_txns=('amount', 'count'),
             competitor_category=('competitor_category', 'first'))
        .reset_index()
    )
    _acct_comp = _acct_comp.merge(_acct_total, on='primary_account_num', how='left')

    _acct_comp['your_spend'] = (
        _acct_comp['total_spend'] - _acct_comp['competitor_spend']
    )
    _acct_comp['your_txns'] = (
        _acct_comp['total_txns'] - _acct_comp['competitor_txns']
    )
    _acct_comp['competitor_pct'] = (
        _acct_comp['competitor_spend']
        / _acct_comp['total_spend'].replace(0, pd.NA)
        * 100
    ).fillna(0).clip(0, 100).round(1)
    _acct_comp['segment'] = pd.cut(
        _acct_comp['competitor_pct'],
        bins=[-0.01, 25, 50, 100.01],
        labels=['Primary', 'Balanced', 'Competitor-Heavy'],
    )

    # Export columns in CSM-friendly order
    _export_cols = [
        'primary_account_num',
        'total_spend', 'total_txns',
        'competitor_spend', 'competitor_txns',
        'your_spend', 'your_txns',
        'competitor_pct', 'segment',
        'competitor_match', 'competitor_category',
    ]

    _exported = 0
    _index_rows = []
    for comp_name, df in _acct_comp.groupby('competitor_match'):
        safe_name = (
            str(comp_name).replace(' ', '_').replace('/', '_')
                          .replace('*', '_').replace('?', '_')
                          .replace(',', '').replace("'", '')
        )

        export_df = df[_export_cols].copy().sort_values(
            'total_spend', ascending=False,
        )

        path_full = _out_root / f"{safe_name}_wallet_share.csv"
        export_df.to_csv(path_full, index=False)

        at_risk = export_df[export_df['segment'] == 'Competitor-Heavy']
        path_risk = _out_root / f"{safe_name}_at_risk.csv"
        at_risk.to_csv(path_risk, index=False)

        opportunity = export_df[export_df['segment'] == 'Primary']
        path_opp = _out_root / f"{safe_name}_opportunity.csv"
        opportunity.to_csv(path_opp, index=False)

        _exported += 1
        _index_rows.append({
            'competitor': comp_name,
            'category': (
                df['competitor_category'].iloc[0]
                if 'competitor_category' in df.columns and len(df) > 0
                else 'unknown'
            ),
            'total_accounts': len(export_df),
            'at_risk_accounts': len(at_risk),
            'opportunity_accounts': len(opportunity),
            'total_competitor_spend': float(export_df['competitor_spend'].sum()),
        })

        # Verbose-print only for deep-dive competitors (keeps log readable)
        if 'deep_dive_competitors' in dir() and comp_name in deep_dive_competitors:
            print(f"    {comp_name}:")
            print(f"      Full:        {path_full.name} ({len(export_df):,} accounts)")
            print(f"      At-Risk:     {path_risk.name} ({len(at_risk):,} accounts)")
            print(f"      Opportunity: {path_opp.name} ({len(opportunity):,} accounts)")

    # Index CSV so CSMs can see all available competitors at a glance
    if _index_rows:
        import pandas as _pd_local
        _idx_df = (
            _pd_local.DataFrame(_index_rows)
            .sort_values('total_competitor_spend', ascending=False)
        )
        _idx_df.to_csv(_out_root / '_INDEX.csv', index=False)

    print(f"\n    Cross-sell lists: exported {_exported} competitors")
    print(f"    Folder: {_out_root}")
    print(f"    3 files per competitor: wallet_share.csv, at_risk.csv, opportunity.csv")
    print(f"    Plus _INDEX.csv summarizing account counts and spend per competitor")
