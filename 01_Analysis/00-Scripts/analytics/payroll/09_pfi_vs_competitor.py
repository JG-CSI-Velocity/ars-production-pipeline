# ===========================================================================
# PFI VS COMPETITOR: Relationship Depth vs Competitor Activity
# ===========================================================================
# If competitor_category exists in combined_df: PFI tier vs competitor spend.
# Shows that weaker-PFI members leak more spend to competitors.

has_competitor = 'competitor_category' in combined_df.columns

if has_competitor:
    # -----------------------------------------------------------------
    # Build competitor spend per account
    # -----------------------------------------------------------------
    comp_txns = combined_df[combined_df['competitor_category'].notna()].copy()

    if len(comp_txns) > 0:
        acct_comp = comp_txns.groupby('primary_account_num').agg(
            competitor_txns=('amount', 'count'),
            competitor_spend=('amount', 'sum'),
            competitor_categories=('competitor_category', 'nunique'),
        ).reset_index()

        # Merge PFI tier
        pfi_comp = payroll_df[['primary_account_num', 'pfi_tier', 'pfi_score']].merge(
            acct_comp, on='primary_account_num', how='left'
        )
        pfi_comp['competitor_txns'] = pfi_comp['competitor_txns'].fillna(0)
        pfi_comp['competitor_spend'] = pfi_comp['competitor_spend'].fillna(0)
        pfi_comp['competitor_categories'] = pfi_comp['competitor_categories'].fillna(0)
        pfi_comp['has_competitor'] = pfi_comp['competitor_txns'] > 0

        # -----------------------------------------------------------------
        # Chart 1: Grouped bar -- competitor metrics by PFI tier
        # -----------------------------------------------------------------
        fig, axes = plt.subplots(1, 3, figsize=(22, 8))

        PFI_TIER_ORDER = ['Primary', 'Secondary', 'Tertiary', 'Incidental']
        PFI_TIER_COLORS = {
            'Primary':    GEN_COLORS['accent'],
            'Secondary':  GEN_COLORS['warning'],
            'Tertiary':   GEN_COLORS['info'],
            'Incidental': GEN_COLORS['muted'],
        }

        # Panel 1: % with any competitor activity
        ax1 = axes[0]
        comp_pct_by_tier = pfi_comp.groupby('pfi_tier')['has_competitor'].mean() * 100
        comp_pct_by_tier = comp_pct_by_tier.reindex(PFI_TIER_ORDER).fillna(0)

        bar_colors = [PFI_TIER_COLORS[t] for t in PFI_TIER_ORDER]
        bars1 = ax1.bar(PFI_TIER_ORDER, comp_pct_by_tier, color=bar_colors,
                        edgecolor='white', linewidth=2, zorder=3)

        for bar, pct in zip(bars1, comp_pct_by_tier):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f"{pct:.1f}%", ha='center', va='bottom',
                     fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])

        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax1)
        ax1.set_title("% with Competitor Activity", fontsize=16, fontweight='bold',
                      color=GEN_COLORS['dark_text'], loc='left')

        # Panel 2: Avg competitor txns
        ax2 = axes[1]
        comp_txn_by_tier = pfi_comp.groupby('pfi_tier')['competitor_txns'].mean()
        comp_txn_by_tier = comp_txn_by_tier.reindex(PFI_TIER_ORDER).fillna(0)

        bars2 = ax2.bar(PFI_TIER_ORDER, comp_txn_by_tier, color=bar_colors,
                        edgecolor='white', linewidth=2, zorder=3)

        for bar, val in zip(bars2, comp_txn_by_tier):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                     f"{val:.1f}", ha='center', va='bottom',
                     fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])

        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))
        gen_clean_axes(ax2)
        ax2.set_title("Avg Competitor Txns", fontsize=16, fontweight='bold',
                      color=GEN_COLORS['dark_text'], loc='left')

        # Panel 3: Avg competitor categories (breadth of leakage)
        ax3 = axes[2]
        comp_cat_by_tier = pfi_comp[pfi_comp['has_competitor']].groupby(
            'pfi_tier'
        )['competitor_categories'].mean()
        comp_cat_by_tier = comp_cat_by_tier.reindex(PFI_TIER_ORDER).fillna(0)

        bars3 = ax3.bar(PFI_TIER_ORDER, comp_cat_by_tier, color=bar_colors,
                        edgecolor='white', linewidth=2, zorder=3)

        for bar, val in zip(bars3, comp_cat_by_tier):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     f"{val:.1f}", ha='center', va='bottom',
                     fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])

        gen_clean_axes(ax3)
        ax3.set_title("Avg Competitor Categories", fontsize=16, fontweight='bold',
                      color=GEN_COLORS['dark_text'], loc='left')

        fig.suptitle("PFI Tier vs Competitor Leakage",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], x=0.01, ha='left', y=GEN_TITLE_Y)
        fig.text(0.01, 1.01,
                 f"Weaker PFI relationships correlate with more competitor activity  --  {DATASET_LABEL}",
                 fontsize=13, style='italic', color=GEN_COLORS['muted'],
                 ha='left', transform=fig.transFigure)

        plt.tight_layout()
        plt.show()

        # Comparison stat
        primary_comp = comp_pct_by_tier.get('Primary', 0)
        incidental_comp = comp_pct_by_tier.get('Incidental', 0)
        if primary_comp > 0:
            ratio = incidental_comp / primary_comp
            print(f"\n  Incidental-tier members have {ratio:.1f}x more competitor activity than Primary-tier")
        secondary_comp = comp_pct_by_tier.get('Secondary', 0)
        tertiary_comp = comp_pct_by_tier.get('Tertiary', 0)
        print(f"  Secondary/Tertiary competitor rate: {(secondary_comp + tertiary_comp) / 2:.1f}%")
    else:
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.text(0.5, 0.5, 'competitor_category column exists but no tagged transactions found',
                ha='center', va='center', fontsize=16,
                color=GEN_COLORS['muted'], transform=ax.transAxes)
        ax.axis('off')
        ax.set_title("PFI Tier vs Competitor Leakage",
                     fontsize=24, fontweight='bold', color=GEN_COLORS['dark_text'],
                     loc='left')
        plt.tight_layout()
        plt.show()

else:
    # -----------------------------------------------------------------
    # Fallback: PFI tier vs general spending patterns
    # -----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(14, 7))

    PFI_TIER_ORDER = ['Primary', 'Secondary', 'Tertiary', 'Incidental']
    PFI_TIER_COLORS = {
        'Primary':    GEN_COLORS['accent'],
        'Secondary':  GEN_COLORS['warning'],
        'Tertiary':   GEN_COLORS['info'],
        'Incidental': GEN_COLORS['muted'],
    }

    # Show avg monthly txns by PFI tier as a proxy for engagement
    n_months = max(DATASET_MONTHS, 1) if 'DATASET_MONTHS' in dir() or 'DATASET_MONTHS' in globals() else 1
    tier_activity = payroll_df.groupby('pfi_tier')['total_txn_count'].mean() / n_months
    tier_activity = tier_activity.reindex(PFI_TIER_ORDER).fillna(0)

    bar_colors = [PFI_TIER_COLORS[t] for t in PFI_TIER_ORDER]
    bars = ax.bar(PFI_TIER_ORDER, tier_activity, color=bar_colors,
                  edgecolor='white', linewidth=2, zorder=3)

    for bar, val in zip(bars, tier_activity):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                f"{val:.1f}", ha='center', va='bottom',
                fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'])

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))
    gen_clean_axes(ax)

    ax.set_title("PFI Tier: Monthly Transaction Activity",
                 fontsize=24, fontweight='bold', color=GEN_COLORS['dark_text'],
                 loc='left', pad=20)
    ax.text(0.0, 1.03,
            f"competitor_category not available; showing engagement by PFI tier  --  {DATASET_LABEL}",
            fontsize=13, style='italic', color=GEN_COLORS['muted'],
            transform=ax.transAxes)

    plt.tight_layout()
    plt.show()

    print("\n  Note: competitor_category column not found in combined_df.")
    print("  Run competitor detection first to enable PFI-vs-competitor analysis.")
