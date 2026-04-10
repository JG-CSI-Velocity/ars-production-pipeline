# ===========================================================================
# SEGMENT SUMMARY: Competitor Wallet-Share Table (Conference Edition)
# ===========================================================================
# Styled table showing segment breakdown per competitor, sorted by account count.
# Filters out noise (competitors with fewer than MIN_ACCOUNTS).

MIN_DISPLAY_ACCOUNTS = 10  # Suppress single-account noise from transaction variants

if len(competitor_spend_analysis) > 0:
    _rows = []
    for comp_name, df in competitor_spend_analysis.items():
        n = len(df)
        if n < MIN_DISPLAY_ACCOUNTS:
            continue
        cat_raw = df['competitor_category'].iloc[0]
        if cat_raw in PAYMENT_ECOSYSTEMS:
            continue
        seg_counts = df['segment'].value_counts()
        _rows.append({
            'competitor': comp_name,
            'category': clean_category(cat_raw),
            'accounts': n,
            'heavy': seg_counts.get('Competitor-Heavy', 0),
            'balanced': seg_counts.get('Balanced', 0),
            'primary': seg_counts.get('Primary', 0),
            'heavy_pct': seg_counts.get('Competitor-Heavy', 0) / n * 100,
            'balanced_pct': seg_counts.get('Balanced', 0) / n * 100,
            'primary_pct': seg_counts.get('Primary', 0) / n * 100,
        })

    seg_summary_df = (
        pd.DataFrame(_rows)
        .sort_values('accounts', ascending=False)
    )

    _suppressed = len(competitor_spend_analysis) - len(seg_summary_df)

    # Display formatted table
    _disp = seg_summary_df.copy()
    _disp.columns = [
        'Competitor', 'Category', 'Accounts',
        'Heavy', 'Balanced', 'Primary',
        '% Heavy', '% Balanced', '% Primary',
    ]
    _disp['Accounts'] = _disp['Accounts'].apply(lambda x: f"{x:,}")
    _disp['Heavy'] = _disp['Heavy'].apply(lambda x: f"{x:,}")
    _disp['Balanced'] = _disp['Balanced'].apply(lambda x: f"{x:,}")
    _disp['Primary'] = _disp['Primary'].apply(lambda x: f"{x:,}")
    _disp['% Heavy'] = _disp['% Heavy'].apply(lambda x: f"{x:.1f}%")
    _disp['% Balanced'] = _disp['% Balanced'].apply(lambda x: f"{x:.1f}%")
    _disp['% Primary'] = _disp['% Primary'].apply(lambda x: f"{x:.1f}%")

    display(_disp.style.hide(axis='index'))

    # Insight callout
    if len(seg_summary_df) > 0:
        worst = seg_summary_df.iloc[0]
        print(f"\n    Highest exposure: {worst['competitor']} "
              f"({worst['accounts']:,} accounts, "
              f"{worst['heavy_pct']:.1f}% Competitor-Heavy)")

    high_risk_comps = seg_summary_df[seg_summary_df['heavy_pct'] > 20]
    if len(high_risk_comps) > 0:
        print(f"    WARNING: {len(high_risk_comps)} competitors have >20% of "
              f"their accounts in the Competitor-Heavy segment.")

    if _suppressed > 0:
        print(f"    ({_suppressed} competitors with <{MIN_DISPLAY_ACCOUNTS} accounts suppressed)")
