# ===========================================================================
# ICS MONTHLY TREND: Channel Activity Over Time (Conference Edition)
# ===========================================================================
# Line chart: monthly txn volume by ICS channel. (14,7).

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping monthly trend.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    channel_colors = {
        'REF': GEN_COLORS['info'],
        'DM': GEN_COLORS['primary'],
        'Non-ICS': GEN_COLORS['muted'],
    }

    for channel in ['REF', 'DM', 'Non-ICS']:
        c_data = ics_monthly[ics_monthly['ics_account'] == channel].sort_values('year_month')
        if len(c_data) == 0:
            continue
        dates = c_data['year_month'].dt.to_timestamp()
        ax.plot(dates, c_data['share_pct'],
                color=channel_colors.get(channel, GEN_COLORS['muted']),
                linewidth=2.5, label=channel, marker='o', markersize=4, zorder=4)

        # End-of-line label
        last_val = c_data['share_pct'].iloc[-1]
        ax.text(dates.iloc[-1], last_val,
                f"  {channel}", fontsize=11, fontweight='bold',
                color=channel_colors.get(channel, GEN_COLORS['muted']), va='center')

    ax.set_ylabel("% of Monthly Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_xlabel("")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.tick_params(axis='x', rotation=45)

    ax.set_title("ICS Channel Transaction Trends",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02,
            f"Are ICS account transaction shares growing or declining?  ({DATASET_LABEL})",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.15),
        ncol=3, fontsize=12, frameon=False, title='ICS Channel',
        title_fontproperties={'weight': 'bold', 'size': 13}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.20)
    plt.show()
