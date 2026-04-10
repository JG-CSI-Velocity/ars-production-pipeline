# ===========================================================================
# SPEND SCATTER: CU vs Competitor Quadrant Analysis (Conference Edition)
# ===========================================================================
# For each top-N competitor, scatter plot of CU spend (x) vs competitor
# spend (y), colored by wallet-share %. Quadrant labels identify risk zones.

if len(competitor_spend_analysis) > 0 and len(deep_dive_competitors) > 0:
    for comp_name in deep_dive_competitors:
        df = competitor_spend_analysis[comp_name]
        if len(df) < 5:
            continue

        fig, ax = plt.subplots(figsize=(14, 9))

        scatter = ax.scatter(
            df['your_spend'], df['competitor_spend'],
            s=100, alpha=0.65,
            c=df['competitor_pct'], cmap='RdYlGn_r',
            edgecolors='white', linewidth=0.8,
            vmin=0, vmax=100, zorder=3,
        )

        ax.set_xlabel('Your Spend ($)', fontsize=16, fontweight='bold', labelpad=12)
        ax.set_ylabel(f'{comp_name} Spend ($)', fontsize=16, fontweight='bold', labelpad=12)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

        gen_clean_axes(ax)
        ax.grid(alpha=0.3, color=GEN_COLORS['grid'], linewidth=0.5)
        ax.set_axisbelow(True)

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
        cbar.set_label('% at Competitor', rotation=270, labelpad=20,
                       fontsize=12, fontweight='bold')

        # 50/50 diagonal reference
        max_val = max(df['your_spend'].max(), df['competitor_spend'].max())
        ax.plot([0, max_val], [0, max_val], '--',
                color=GEN_COLORS['muted'], alpha=0.5, linewidth=2,
                label='50/50 Line', zorder=2)

        # Median crosshairs
        med_cu = df['your_spend'].median()
        med_comp = df['competitor_spend'].median()
        ax.axvline(med_cu, color=GEN_COLORS['info'], linestyle=':', alpha=0.4, linewidth=2)
        ax.axhline(med_comp, color=GEN_COLORS['accent'], linestyle=':', alpha=0.4, linewidth=2)

        # Quadrant labels
        ax.text(0.03, 0.97, 'WINNING\nHigh Ours / Low Competitor',
                transform=ax.transAxes, ha='left', va='top',
                bbox=dict(boxstyle='round', facecolor=GEN_COLORS['success'],
                          alpha=0.85, edgecolor='white', linewidth=2),
                fontsize=10, fontweight='bold', color='white')

        ax.text(0.97, 0.97, 'HIGH RISK\nHigh Competitor / Low Ours',
                transform=ax.transAxes, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor=GEN_COLORS['accent'],
                          alpha=0.85, edgecolor='white', linewidth=2),
                fontsize=10, fontweight='bold', color='white')

        ax.text(0.97, 0.03, 'BIG SPENDERS\nHigh Both',
                transform=ax.transAxes, ha='right', va='bottom',
                bbox=dict(boxstyle='round', facecolor=GEN_COLORS['info'],
                          alpha=0.7, edgecolor='white', linewidth=2),
                fontsize=9, fontweight='bold', color='white')

        ax.text(0.03, 0.03, 'LOW VALUE\nLow Both',
                transform=ax.transAxes, ha='left', va='bottom',
                bbox=dict(boxstyle='round', facecolor=GEN_COLORS['grid'],
                          alpha=0.8, edgecolor='white', linewidth=2),
                fontsize=9, color=GEN_COLORS['dark_text'])

        ax.set_title(f'Spend Distribution: {comp_name}',
                     fontsize=22, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=20, loc='left')
        ax.text(0.0, 0.97,
                f"{len(df):,} accounts  |  Color = % of spend at competitor",
                transform=ax.transAxes, fontsize=12,
                color=GEN_COLORS['muted'], style='italic')

        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
                  fontsize=11, frameon=False)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)
        plt.show()

        # Quadrant counts
        high_risk = len(df[(df['competitor_spend'] > med_comp) &
                           (df['your_spend'] < med_cu)])
        winning = len(df[(df['competitor_spend'] < med_comp) &
                         (df['your_spend'] > med_cu)])
        n = len(df)
        print(f"    {comp_name}: "
              f"Winning {winning:,} ({winning/n*100:.1f}%)  |  "
              f"High Risk {high_risk:,} ({high_risk/n*100:.1f}%)")
