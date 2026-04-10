# ===========================================================================
# TOP COMPETITORS BY SEGMENT: Stacked Bar (Conference Edition)
# ===========================================================================
# Horizontal stacked bar showing segment % for the top 15 competitors.
# Sorted by total account count, largest at top.

if len(competitor_spend_analysis) > 0:
    _rows = []
    for comp_name, df in competitor_spend_analysis.items():
        # Skip payment ecosystems (wallets, p2p, bnpl)
        cat_raw = df['competitor_category'].iloc[0] if len(df) > 0 else ''
        if cat_raw in PAYMENT_ECOSYSTEMS:
            continue
        seg = df['segment'].value_counts()
        n = len(df)
        _rows.append({
            'competitor': comp_name,
            'accounts': n,
            'heavy_pct': seg.get('Competitor-Heavy', 0) / n * 100,
            'balanced_pct': seg.get('Balanced', 0) / n * 100,
            'primary_pct': seg.get('Primary', 0) / n * 100,
        })

    _sdf = (
        pd.DataFrame(_rows)
        .sort_values('accounts', ascending=False)
        .head(15)
        .iloc[::-1]  # Flip for top-down display in barh
    )

    fig, ax = plt.subplots(figsize=(14, 9))

    y = range(len(_sdf))

    ax.barh(y, _sdf['heavy_pct'],
            color=SEGMENT_PALETTE['Competitor-Heavy'],
            label='Competitor-Heavy (>50%)', height=0.65, zorder=3)
    ax.barh(y, _sdf['balanced_pct'], left=_sdf['heavy_pct'],
            color=SEGMENT_PALETTE['Balanced'],
            label='Balanced (25-50%)', height=0.65, zorder=3)
    ax.barh(y, _sdf['primary_pct'],
            left=_sdf['heavy_pct'] + _sdf['balanced_pct'],
            color=SEGMENT_PALETTE['Primary'],
            label='Primary (<25%)', height=0.65, zorder=3)

    # Competitor labels
    short_names = [
        (n[:23] + '..' if len(n) > 25 else n) for n in _sdf['competitor']
    ]
    ax.set_yticks(y)
    ax.set_yticklabels(short_names, fontsize=13, fontweight='bold')

    ax.set_xlabel('Share of Accounts (%)', fontsize=16, fontweight='bold', labelpad=10)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

    gen_clean_axes(ax)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    # Account count annotations on right edge
    for i, (_, row) in enumerate(_sdf.iterrows()):
        ax.text(101, i, f"{row['accounts']:,.0f}",
                va='center', fontsize=11, fontweight='bold',
                color=GEN_COLORS['muted'])
    ax.text(101, len(_sdf) - 0.2, 'Accounts', fontsize=10, fontweight='bold',
            color=GEN_COLORS['muted'], style='italic', va='bottom')

    # Title
    ax.set_title('Account Segmentation by Competitor',
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=20, loc='left')
    ax.text(0.0, 0.97,
            f"Top 15 competitors by account reach  |  Wallet-share segmentation",
            transform=ax.transAxes, fontsize=13,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
              ncol=3, fontsize=13, frameon=False)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.10)
    plt.show()
