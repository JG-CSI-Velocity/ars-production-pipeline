# ===========================================================================
# ICS ENGAGEMENT: Tier Distribution by Channel (Conference Edition)
# ===========================================================================
# Stacked bar: engagement tier distribution by ICS channel. (14,7).
# Depends on acct_txn_counts from general/17_engagement_data.

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping engagement chart.")
else:
    try:
        engage_lookup_ics = acct_txn_counts[['account', 'tier']].copy()
        engage_lookup_ics.columns = ['primary_account_num', 'engage_tier']

        engage_ics = ics_merged.merge(engage_lookup_ics, on='primary_account_num', how='inner')

        ics_engage_ct = pd.crosstab(
            engage_ics['ics_account'],
            engage_ics['engage_tier'],
            normalize='index'
        ) * 100

        ics_engage_ct = ics_engage_ct[[t for t in ENGAGE_ORDER if t in ics_engage_ct.columns]]

        # Order channels
        channel_order = [c for c in ['REF', 'DM', 'Non-ICS'] if c in ics_engage_ct.index]
        ics_engage_ct = ics_engage_ct.loc[channel_order]

        fig, ax = plt.subplots(figsize=(14, 7))

        x = np.arange(len(ics_engage_ct))
        bottom = np.zeros(len(ics_engage_ct))

        for tier in ics_engage_ct.columns:
            color = ENGAGE_PALETTE.get(tier, GEN_COLORS['muted'])
            ax.bar(x, ics_engage_ct[tier], bottom=bottom,
                   label=tier, color=color, edgecolor='white', linewidth=0.5, width=0.5)
            # Label if > 5%
            for i, val in enumerate(ics_engage_ct[tier]):
                if val > 5:
                    ax.text(i, bottom[i] + val / 2, f"{val:.0f}%",
                            ha='center', va='center', fontsize=10,
                            fontweight='bold', color='white')
            bottom += ics_engage_ct[tier].values

        ax.set_xticks(x)
        ax.set_xticklabels(ics_engage_ct.index, fontsize=14, fontweight='bold')
        ax.set_ylabel("% of Channel Transactions", fontsize=16, fontweight='bold', labelpad=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        ax.set_ylim(0, 105)

        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        ax.set_title("Engagement Distribution by ICS Channel",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02,
                f"Are ICS-sourced accounts more or less engaged than non-ICS?  ({DATASET_LABEL})",
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
