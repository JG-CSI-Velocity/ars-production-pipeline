# ===========================================================================
# PERSONAL BY ENGAGEMENT: Power vs Dormant Preferences (Conference Edition)
# ===========================================================================
# Grouped bar: top 8 personal merchants, share by engagement tier. (14,7).
# Uses acct_txn_counts from general/17_engagement_data.

try:
    engage_lookup_p = acct_txn_counts[['account', 'tier']].copy()
    engage_lookup_p.columns = ['primary_account_num', 'engage_tier']

    engage_pers = personal_df.merge(engage_lookup_p, on='primary_account_num', how='inner')

    top8_pers_e = pers_agg.head(8)['merchant_consolidated'].tolist()
    engage_p_filtered = engage_pers[engage_pers['merchant_consolidated'].isin(top8_pers_e)]

    merch_engage_ct_p = pd.crosstab(
        engage_p_filtered['merchant_consolidated'],
        engage_p_filtered['engage_tier'],
        normalize='columns'
    ) * 100

    merch_engage_ct_p = merch_engage_ct_p[[t for t in ENGAGE_ORDER if t in merch_engage_ct_p.columns]]

    # Sort by Power tier share
    if 'Power' in merch_engage_ct_p.columns:
        merch_engage_ct_p = merch_engage_ct_p.sort_values('Power', ascending=True)

    # Truncate names
    merch_engage_ct_p.index = [n[:25] for n in merch_engage_ct_p.index]

    fig, ax = plt.subplots(figsize=(14, 7))

    n_tiers = len(merch_engage_ct_p.columns)
    n_merch = len(merch_engage_ct_p)
    bar_height = 0.8 / n_tiers
    y_base = np.arange(n_merch)

    for i, tier in enumerate(merch_engage_ct_p.columns):
        offset = (i - n_tiers / 2 + 0.5) * bar_height
        color = ENGAGE_PALETTE.get(tier, GEN_COLORS['muted'])
        ax.barh(y_base + offset, merch_engage_ct_p[tier],
                height=bar_height, color=color,
                label=tier, edgecolor='white', linewidth=0.5)

    ax.set_yticks(y_base)
    ax.set_yticklabels(merch_engage_ct_p.index, fontsize=11, fontweight='bold')
    ax.set_xlabel("% of Tier's Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("Personal Merchant Preferences by Engagement Tier",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Do Power personal users shop at different merchants than Dormant?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.08),
        ncol=5, fontsize=12, frameon=False, title='Engagement Tier',
        title_fontproperties={'weight': 'bold', 'size': 13}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.show()

except NameError:
    print("    acct_txn_counts not available. Run general/17_engagement_data first.")
