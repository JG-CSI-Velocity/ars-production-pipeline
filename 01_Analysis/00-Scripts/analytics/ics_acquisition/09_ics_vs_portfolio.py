# ===========================================================================
# ICS VS PORTFOLIO: ICS Top Merchants vs Full Portfolio (Conference Edition)
# ===========================================================================
# Two-panel: ICS top 10 merchants vs same merchants in full portfolio. (14,7).
# Depends on merch_agg from merchant/01_merchant_data.

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping portfolio comparison.")
else:
    try:
        # Top 10 ICS merchants
        ics_merch = ics_df.groupby('merchant_consolidated').agg(
            txn_count=('transaction_date', 'count')
        ).reset_index()
        ics_merch['ics_pct'] = ics_merch['txn_count'] / len(ics_df) * 100
        ics_merch = ics_merch.sort_values('txn_count', ascending=False).head(10)
        ics_merch = ics_merch.sort_values('ics_pct', ascending=True)

        # Look up same merchants in portfolio
        portfolio_share = merch_agg.set_index('merchant_consolidated')['txn_pct']
        ics_merch['portfolio_pct'] = ics_merch['merchant_consolidated'].map(portfolio_share).fillna(0)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        names = [m[:22] for m in ics_merch['merchant_consolidated']]
        y_pos = range(len(ics_merch))

        # --- LEFT: ICS share ---
        ax1.barh(y_pos, ics_merch['ics_pct'],
                 color=GEN_COLORS['info'], edgecolor='white', linewidth=0.5, height=0.65)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(names, fontsize=10, fontweight='bold')
        ax1.set_xlabel("% of ICS Txns", fontsize=13, fontweight='bold', labelpad=8)
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
        ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax1.set_axisbelow(True)
        ax1.set_title("ICS Account Share", fontsize=20, fontweight='bold',
                       color=GEN_COLORS['info'], pad=12)

        for j, (_, row) in enumerate(ics_merch.iterrows()):
            ax1.text(row['ics_pct'] + 0.2, j, f"{row['ics_pct']:.1f}%",
                     va='center', fontsize=9, fontweight='bold', color=GEN_COLORS['info'])

        # --- RIGHT: Portfolio share ---
        ax2.barh(y_pos, ics_merch['portfolio_pct'],
                 color=GEN_COLORS['muted'], edgecolor='white', linewidth=0.5, height=0.65)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(names, fontsize=10, fontweight='bold')
        ax2.set_xlabel("% of All Portfolio Txns", fontsize=13, fontweight='bold', labelpad=8)
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
        ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax2.set_axisbelow(True)
        ax2.set_title("Full Portfolio Share", fontsize=20, fontweight='bold',
                       color=GEN_COLORS['muted'], pad=12)

        for j, (_, row) in enumerate(ics_merch.iterrows()):
            ax2.text(row['portfolio_pct'] + 0.2, j, f"{row['portfolio_pct']:.1f}%",
                     va='center', fontsize=9, fontweight='bold', color=GEN_COLORS['muted'])

        fig.suptitle("ICS vs Full Portfolio",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
        fig.text(0.5, GEN_SUBTITLE_Y,
                 f"How do ICS top merchants compare to the overall member base?  ({DATASET_LABEL})",
                 ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.subplots_adjust(top=0.88)
        plt.show()

    except NameError:
        print("    merch_agg not available. Run merchant/01_merchant_data first for portfolio comparison.")
