# ===========================================================================
# SEGMENT HEATMAP: Per-Category Risk Heatmap (Conference Edition)
# ===========================================================================
# Color-coded grid: red scale for Competitor-Heavy (bad), green scale for
# Primary (good). One heatmap per category with 3+ competitors.

if len(competitor_spend_analysis) > 0:
    import matplotlib.patches as mpatches

    # Risk-aware color scales
    def _heatmap_color(col_idx, value):
        if col_idx == 0:  # Competitor-Heavy -- high = bad
            if value >= 20:
                return GEN_COLORS['accent']       # Dark red
            elif value >= 10:
                return '#CD5C5C'                   # Light red
            elif value >= 5:
                return '#F5C6CB'                   # Pink
            else:
                return GEN_COLORS['grid']          # Neutral gray
        elif col_idx == 1:  # Balanced -- neutral
            if value >= 30:
                return GEN_COLORS['warning']       # Dark orange
            elif value >= 15:
                return '#FFD39B'                   # Light orange
            else:
                return GEN_COLORS['grid']
        else:  # Primary -- high = good
            if value >= 90:
                return '#006400'                   # Dark green
            elif value >= 80:
                return GEN_COLORS['success']       # Teal
            elif value >= 70:
                return '#A8E6CF'                   # Light green
            else:
                return GEN_COLORS['grid']

    def _text_color(bg):
        dark_backgrounds = {GEN_COLORS['accent'], '#006400', GEN_COLORS['success']}
        return 'white' if bg in dark_backgrounds else GEN_COLORS['dark_text']

    # Group by category
    _cat_groups = {}
    for comp_name, df in competitor_spend_analysis.items():
        cat_label = clean_category(df['competitor_category'].iloc[0])
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
        cdf = (
            pd.DataFrame(comps)
            .sort_values('accounts', ascending=False)
        )
        if len(cdf) < 3:
            continue
        cdf = cdf.head(20)

        names = cdf['competitor'].values
        matrix = cdf[['heavy_pct', 'balanced_pct', 'primary_pct']].values

        fig_h = max(8, len(names) * 0.55 + 3)
        fig, ax = plt.subplots(figsize=(14, fig_h))

        cell_w, cell_h = 1.8, 0.9
        for i in range(len(names)):
            for j in range(3):
                bg = _heatmap_color(j, matrix[i, j])
                rect = mpatches.Rectangle(
                    (j * 2 - 0.9, i - 0.45), cell_w, cell_h,
                    facecolor=bg, edgecolor='white', linewidth=3,
                )
                ax.add_patch(rect)
                ax.text(
                    j * 2, i, f'{matrix[i, j]:.0f}%',
                    ha='center', va='center',
                    color=_text_color(bg),
                    fontweight='bold', fontsize=16,
                )

        ax.set_xlim(-1, 5.5)
        ax.set_ylim(-0.5, len(names) - 0.5)

        import numpy as np
        ax.set_xticks([0, 2, 4])
        ax.set_yticks(np.arange(len(names)))
        ax.set_xticklabels(
            ['Competitor-Heavy\n(>50%)', 'Balanced\n(25-50%)', 'Primary\n(<25%)'],
            fontsize=14, fontweight='bold',
        )
        short_names = [
            (n[:25] + '..' if len(n) > 27 else n) for n in names
        ]
        ax.set_yticklabels(short_names, fontsize=13, fontweight='bold')

        # Account counts on right
        for i, (_, row) in enumerate(cdf.iterrows()):
            ax.text(5.3, i, f"n={int(row['accounts']):,}",
                    va='center', fontsize=12, fontweight='bold',
                    color=GEN_COLORS['muted'])

        ax.invert_yaxis()

        cat_color = CATEGORY_PALETTE.get(cat_label, GEN_COLORS['info'])
        ax.set_title(f'{cat_label} -- Wallet-Share Heatmap',
                     fontsize=22, fontweight='bold',
                     color=cat_color, pad=20, loc='left')
        ax.text(0.0, 1.02,
                f"Top {len(cdf)} by account reach  |  Color intensity = risk level",
                transform=ax.transAxes, fontsize=12,
                color=GEN_COLORS['muted'], style='italic')

        # Remove all spines for clean heatmap
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)

        plt.tight_layout()
        plt.show()

        # Color guide
        print(f"    {cat_label} heatmap:")
        print(f"      Competitor-Heavy: dark red (>=20%) = high risk")
        print(f"      Primary: dark green (>=90%) = very loyal")
