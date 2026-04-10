# ===========================================================================
# MCC BY ENGAGEMENT TIER: Power vs Dormant Categories (Conference Edition)
# ===========================================================================
# Grouped bar: top 8 MCCs, share by engagement tier. (14,7).
# Uses acct_txn_counts from general/17_engagement_data.

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping MCC by engagement tier.")
elif 'acct_txn_counts' not in dir() or len(acct_txn_counts) == 0:
    print("    No engagement data available. Skipping MCC by engagement tier.")
else:
    # Merge engagement tier onto transactions
    engage_lookup = acct_txn_counts[['account', 'tier']].copy()
    engage_lookup.columns = ['primary_account_num', 'engage_tier']

    engage_txns = combined_df.merge(engage_lookup, on='primary_account_num', how='inner')

    # Top 8 MCCs
    top8_codes = mcc_agg.head(8)['mcc_code'].tolist()
    engage_mcc = engage_txns[engage_txns['mcc_code'].isin(top8_codes)]

    if len(engage_mcc) == 0:
        print("    No engagement-matched MCC data available. Skipping chart.")
    else:
        # Cross-tab: MCC x engagement tier, normalized per tier
        mcc_engage_ct = pd.crosstab(
            engage_mcc['mcc_code'],
            engage_mcc['engage_tier'],
            normalize='columns'
        ) * 100

        # Ensure tier order (match case-insensitively)
        _ct_col_map = {c.strip().title(): c for c in mcc_engage_ct.columns}
        _ordered_cols = [_ct_col_map[t] for t in ENGAGE_ORDER if t in _ct_col_map]
        if len(_ordered_cols) == 0:
            # Fallback: use whatever columns exist
            _ordered_cols = list(mcc_engage_ct.columns)
        mcc_engage_ct = mcc_engage_ct[_ordered_cols]

        # Sort by first tier share descending
        if 'Power' in mcc_engage_ct.columns:
            mcc_engage_ct = mcc_engage_ct.sort_values('Power', ascending=True)
        elif len(mcc_engage_ct.columns) > 0:
            mcc_engage_ct = mcc_engage_ct.sort_values(mcc_engage_ct.columns[0], ascending=True)

        n_tiers = len(mcc_engage_ct.columns)
        n_mcc = len(mcc_engage_ct)

        if n_tiers == 0 or n_mcc == 0:
            print("    Empty MCC x engagement cross-tab. Skipping chart.")
        else:
            fig, ax = plt.subplots(figsize=(14, 7))

            bar_height = 0.8 / n_tiers
            y_base = np.arange(n_mcc)

            for i, tier in enumerate(mcc_engage_ct.columns):
                offset = (i - n_tiers / 2 + 0.5) * bar_height
                color = ENGAGE_PALETTE.get(tier, GEN_COLORS['muted'])
                ax.barh(
                    y_base + offset, mcc_engage_ct[tier],
                    height=bar_height, color=color,
                    label=tier, edgecolor='white', linewidth=0.5
                )

            ax.set_yticks(y_base)
            ax.set_yticklabels(mcc_engage_ct.index, fontsize=13, fontweight='bold')
            ax.set_xlabel("% of Tier's Transactions", fontsize=16, fontweight='bold', labelpad=10)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

            gen_clean_axes(ax, keep_left=True, keep_bottom=True)
            ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)

            ax.set_title("MCC Preferences by Engagement Tier",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02, "Do Power users spend at different merchants than Dormant accounts?",
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
