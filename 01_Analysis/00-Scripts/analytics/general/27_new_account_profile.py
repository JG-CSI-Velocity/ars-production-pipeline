# ===========================================================================
# NEW ACCOUNT PROFILE: Spend Tiers for Newest Accounts (Conference Edition)
# ===========================================================================
# Stacked bar: spend tier distribution for 1-90d, 91-180d, 181-365d. (8,7).
# Low on bottom, Very High on top. Shows actual dollar thresholds.

NEW_BANDS = ['1-90d', '91-180d', '181-365d']

new_accts = lifecycle_matched[
    lifecycle_matched['acct_age_band'].isin(NEW_BANDS) &
    lifecycle_matched['spend_tier'].notna()
].copy()

if len(new_accts) > 0:
    # Cross-tab: age band x spend tier, normalized per band
    tier_ct = pd.crosstab(
        new_accts['acct_age_band'],
        new_accts['spend_tier'],
        normalize='index'
    ) * 100

    # Stack order: Low on bottom, Very High on top
    STACK_ORDER = ['Low', 'Medium', 'High', 'Very High']
    tier_ct = tier_ct.reindex(
        index=[b for b in NEW_BANDS if b in tier_ct.index],
        columns=[t for t in STACK_ORDER if t in tier_ct.columns]
    ).fillna(0)

    fig, ax = plt.subplots(figsize=(10, 8))

    x = np.arange(len(tier_ct))
    bar_width = 0.55
    bottom = np.zeros(len(tier_ct))

    for tier in tier_ct.columns:
        vals = tier_ct[tier].values
        color = SPEND_TIER_PALETTE.get(tier, GEN_COLORS['muted'])
        ax.bar(
            x, vals, bar_width,
            bottom=bottom, color=color,
            label=f"{tier} ({SPEND_THRESHOLDS[tier]})",
            edgecolor='white', linewidth=1
        )
        # Label segments > 10%
        for j, v in enumerate(vals):
            if v > 10:
                ax.text(x[j], bottom[j] + v / 2, f"{v:.0f}%",
                        ha='center', va='center', fontsize=15,
                        fontweight='bold', color='white',
                        path_effects=[pe.withStroke(linewidth=2, foreground='#333333')])
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(tier_ct.index, fontsize=16, fontweight='bold')
    ax.set_ylabel("% of Accounts", fontsize=18, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)

    ax.set_title("New Account Spend Profile",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "How many new accounts reach healthy spend levels?",
            transform=ax.transAxes, fontsize=16,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.08),
        ncol=2, fontsize=14, frameon=False, title='Spend Tier (ODDD Total Spend)',
        title_fontproperties={'weight': 'bold', 'size': 15}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.18)
    plt.show()

    # Callout with thresholds
    print(f"\n    Spend tier thresholds (ODDD Total Spend quartiles):")
    for tier in STACK_ORDER:
        print(f"      {tier}: {SPEND_THRESHOLDS[tier]}")
    print()
    for band in NEW_BANDS:
        if band in tier_ct.index:
            low_pct = tier_ct.loc[band, 'Low'] if 'Low' in tier_ct.columns else 0
            vh_pct = tier_ct.loc[band, 'Very High'] if 'Very High' in tier_ct.columns else 0
            print(f"    {band}: {low_pct:.0f}% Low spend, {vh_pct:.0f}% Very High spend")
else:
    print("No new accounts with spend tier data available.")
