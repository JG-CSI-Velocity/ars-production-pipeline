# ===========================================================================
# BRANCH MONTHLY TREND: Top 5 Branch Activity Over Time (Conference Edition)
# ===========================================================================
# Multi-line: monthly txn share for top 5 branches. (14,7).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping monthly trend.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    trend_colors_br = [GEN_COLORS['accent'], GEN_COLORS['primary'], GEN_COLORS['info'],
                        GEN_COLORS['success'], GEN_COLORS['warning']]
    top5_branches = br_agg.head(5)['branch'].tolist()

    for i, branch in enumerate(top5_branches):
        b_data = br_monthly[br_monthly['branch'] == branch].sort_values('year_month')
        if len(b_data) == 0:
            continue
        dates = b_data['year_month'].dt.to_timestamp()
        ax.plot(dates, b_data['share_pct'],
                color=trend_colors_br[i], linewidth=2.5,
                label=str(branch)[:20], marker='o', markersize=4, zorder=4)

        # End-of-line label
        last_val = b_data['share_pct'].iloc[-1]
        ax.text(dates.iloc[-1], last_val,
                f"  {str(branch)[:15]}", fontsize=9, fontweight='bold',
                color=trend_colors_br[i], va='center')

    ax.set_ylabel("% of Monthly Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_xlabel("")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.tick_params(axis='x', rotation=45)

    ax.set_title("Top 5 Branch Activity Trends",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Are branch transaction shares stable or shifting?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.15),
        ncol=5, fontsize=11, frameon=False, title='Branch',
        title_fontproperties={'weight': 'bold', 'size': 12}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.22)
    plt.show()
