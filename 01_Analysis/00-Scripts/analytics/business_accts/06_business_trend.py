# ===========================================================================
# BUSINESS TREND: Top 10 Merchant Shares Over Time (Conference Edition)
# ===========================================================================
# Multi-line: monthly share for top 10 business merchants. (14,7).

if 'biz_monthly' not in dir() or len(biz_monthly) == 0:
    print("    No business data available. Skipping trend chart.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    trend_colors_b = BRACKET_PALETTE[:8] + [GEN_COLORS['muted'], GEN_COLORS['warning']]

    for i, merchant in enumerate(top10_biz):
        m_data = biz_monthly[biz_monthly['merchant_consolidated'] == merchant].sort_values('year_month')
        if len(m_data) == 0:
            continue
        dates = m_data['year_month'].dt.to_timestamp()
        ax.plot(dates, m_data['share_pct'],
                color=trend_colors_b[i], linewidth=2.5,
                label=merchant[:25], marker='o', markersize=4, zorder=4)

        last_val = m_data['share_pct'].iloc[-1]
        ax.text(dates.iloc[-1], last_val,
                f"  {merchant[:18]}", fontsize=9, fontweight='bold',
                color=trend_colors_b[i], va='center')

    ax.set_ylabel("% of Monthly Business Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_xlabel("")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.tick_params(axis='x', rotation=45)

    ax.set_title("Top 10 Business Merchant Trends",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Are business merchant shares stable or shifting?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.15),
        ncol=3, fontsize=10, frameon=False, title='Merchant',
        title_fontproperties={'weight': 'bold', 'size': 12}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.22)
    plt.show()
