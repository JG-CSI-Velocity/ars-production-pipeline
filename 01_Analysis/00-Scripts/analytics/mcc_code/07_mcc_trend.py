# ===========================================================================
# MCC TREND: Top 10 Category Shares Over Time (Conference Edition)
# ===========================================================================
# Multi-line: monthly share of top 10 MCCs. (14,7).

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping trend chart.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    # Use BRACKET_PALETTE for 10 colors
    trend_colors = BRACKET_PALETTE[:8] + [GEN_COLORS['muted'], GEN_COLORS['grid']]

    for i, mcc_code in enumerate(top10_codes):
        mcc_data = mcc_monthly[mcc_monthly['mcc_code'] == mcc_code].sort_values('year_month')
        if len(mcc_data) == 0:
            continue

        dates = mcc_data['year_month'].dt.to_timestamp()
        ax.plot(
            dates, mcc_data['share_pct'],
            color=trend_colors[i], linewidth=2.5,
            label=str(mcc_code), marker='o', markersize=4, zorder=4
        )

        # End-of-line label
        last_val = mcc_data['share_pct'].iloc[-1]
        ax.text(dates.iloc[-1], last_val,
                f"  {mcc_code}", fontsize=10, fontweight='bold',
                color=trend_colors[i], va='center')

    ax.set_ylabel("% of Monthly Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_xlabel("")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.tick_params(axis='x', rotation=45)

    ax.set_title("Top 10 MCC Category Trends",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Are spending patterns shifting across merchant categories?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.15),
        ncol=5, fontsize=12, frameon=False, title='MCC Code',
        title_fontproperties={'weight': 'bold', 'size': 13}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.18)
    plt.show()
