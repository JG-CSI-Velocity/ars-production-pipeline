# ===========================================================================
# BUSINESS BY ENGAGEMENT: Power vs Dormant Preferences (Conference Edition)
# ===========================================================================
# Grouped bar: top 8 business merchants, share by engagement tier. (14,7).
# Uses acct_txn_counts from general/17_engagement_data.

if 'biz_agg' not in dir() or len(biz_agg) == 0:
    print("    No business data available. Skipping engagement chart.")
else:
    try:
        engage_lookup_b = acct_txn_counts[['account', 'tier']].copy()
        engage_lookup_b.columns = ['primary_account_num', 'engage_tier']

        engage_biz = business_df.merge(engage_lookup_b, on='primary_account_num', how='inner')

        top8_biz_e = biz_agg.head(8)['merchant_consolidated'].tolist()
        engage_b_filtered = engage_biz[engage_biz['merchant_consolidated'].isin(top8_biz_e)]

        merch_engage_ct_b = pd.crosstab(
            engage_b_filtered['merchant_consolidated'],
            engage_b_filtered['engage_tier'],
            normalize='columns'
        ) * 100

        merch_engage_ct_b = merch_engage_ct_b[[t for t in ENGAGE_ORDER if t in merch_engage_ct_b.columns]]

        if 'Power' in merch_engage_ct_b.columns:
            merch_engage_ct_b = merch_engage_ct_b.sort_values('Power', ascending=True)

        merch_engage_ct_b.index = [n[:25] for n in merch_engage_ct_b.index]

        fig, ax = plt.subplots(figsize=(14, 7))

        n_tiers = len(merch_engage_ct_b.columns)
        n_merch = len(merch_engage_ct_b)
        bar_height = 0.8 / n_tiers
        y_base = np.arange(n_merch)

        for i, tier in enumerate(merch_engage_ct_b.columns):
            offset = (i - n_tiers / 2 + 0.5) * bar_height
            color = ENGAGE_PALETTE.get(tier, GEN_COLORS['muted'])
            ax.barh(y_base + offset, merch_engage_ct_b[tier],
                    height=bar_height, color=color,
                    label=tier, edgecolor='white', linewidth=0.5)

        ax.set_yticks(y_base)
        ax.set_yticklabels(merch_engage_ct_b.index, fontsize=11, fontweight='bold')
        ax.set_xlabel("% of Tier's Transactions", fontsize=16, fontweight='bold', labelpad=10)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        ax.set_title("Business Merchant Preferences by Engagement Tier",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02, "Do Power business users shop at different merchants than Dormant?",
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
