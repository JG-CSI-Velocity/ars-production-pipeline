# ===========================================================================
# SEGMENT BY CATEGORY: Per-Category Stacked Bars (Conference Edition)
# ===========================================================================
# One chart per competitor category showing wallet-share segments.
# Categories with fewer than 2 competitors are skipped.

if len(competitor_spend_analysis) > 0:
    # Group competitors by category
    _cat_groups = {}
    for comp_name, df in competitor_spend_analysis.items():
        cat_raw = df['competitor_category'].iloc[0]
        cat_label = clean_category(cat_raw)
        if cat_label not in _cat_groups:
            _cat_groups[cat_label] = []

        seg = df['segment'].value_counts()
        n = len(df)
        _cat_groups[cat_label].append({
            'competitor': comp_name,
            'accounts': n,
            'heavy_pct': seg.get('Competitor-Heavy', 0) / n * 100,
            'balanced_pct': seg.get('Balanced', 0) / n * 100,
            'primary_pct': seg.get('Primary', 0) / n * 100,
        })

    for cat_label, comps in _cat_groups.items():
        cdf = pd.DataFrame(comps).sort_values('accounts', ascending=True)
        if len(cdf) < 2:
            continue
        cdf = cdf.tail(15)

        fig_h = max(6, len(cdf) * 0.55 + 2)
        fig, ax = plt.subplots(figsize=(14, fig_h))

        y = range(len(cdf))

        ax.barh(y, cdf['heavy_pct'],
                color=SEGMENT_PALETTE['Competitor-Heavy'],
                label='Competitor-Heavy (>50%)', height=0.65, zorder=3)
        ax.barh(y, cdf['balanced_pct'], left=cdf['heavy_pct'],
                color=SEGMENT_PALETTE['Balanced'],
                label='Balanced (25-50%)', height=0.65, zorder=3)
        ax.barh(y, cdf['primary_pct'],
                left=cdf['heavy_pct'] + cdf['balanced_pct'],
                color=SEGMENT_PALETTE['Primary'],
                label='Primary (<25%)', height=0.65, zorder=3)

        short_names = [
            (n[:23] + '..' if len(n) > 25 else n) for n in cdf['competitor']
        ]
        ax.set_yticks(y)
        ax.set_yticklabels(short_names, fontsize=12, fontweight='bold')

        ax.set_xlabel('Share of Accounts (%)', fontsize=14, fontweight='bold', labelpad=10)
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

        gen_clean_axes(ax)
        ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)

        # Account counts
        for i, (_, row) in enumerate(cdf.iterrows()):
            ax.text(101, i, f"{row['accounts']:,.0f}",
                    va='center', fontsize=10, fontweight='bold',
                    color=GEN_COLORS['muted'])

        cat_color = CATEGORY_PALETTE.get(cat_label, GEN_COLORS['info'])
        ax.set_title(f'{cat_label} -- Account Segmentation',
                     fontsize=22, fontweight='bold',
                     color=cat_color, pad=16, loc='left')
        ax.text(0.0, 0.97,
                f"Top {len(cdf)} by account reach  |  Wallet-share segmentation",
                transform=ax.transAxes, fontsize=12,
                color=GEN_COLORS['muted'], style='italic')

        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
                  ncol=3, fontsize=12, frameon=False)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.10)
        plt.show()

        # Category summary
        total_heavy = sum(r['heavy_pct'] * r['accounts'] / 100 for r in comps)
        total_n = sum(r['accounts'] for r in comps)
        print(f"    {cat_label}: {len(comps)} competitors, "
              f"{total_n:,.0f} accounts, "
              f"{total_heavy / total_n * 100:.1f}% Competitor-Heavy overall")
