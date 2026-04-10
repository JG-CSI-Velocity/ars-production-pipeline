# ===========================================================================
# ICS RETENTION: Recent Activity by Channel (Conference Edition)
# ===========================================================================
# Bar chart: % of accounts active in most recent month by channel. (14,7).

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping retention chart.")
else:
    # Most recent month
    most_recent = ics_merged['year_month'].max()
    recent_accts = ics_merged[ics_merged['year_month'] == most_recent]

    # Activity rate by channel
    retention_data = []
    for channel in ['REF', 'DM', 'Non-ICS']:
        total_accts = ics_merged[ics_merged['ics_account'] == channel]['primary_account_num'].nunique()
        active_accts = recent_accts[recent_accts['ics_account'] == channel]['primary_account_num'].nunique()
        rate = active_accts / total_accts * 100 if total_accts > 0 else 0
        retention_data.append({
            'channel': channel,
            'total_accounts': total_accts,
            'active_accounts': active_accts,
            'activity_rate': rate,
        })

    ret_df = pd.DataFrame(retention_data)

    fig, ax = plt.subplots(figsize=(14, 7))

    channel_colors = {
        'REF': GEN_COLORS['info'],
        'DM': GEN_COLORS['primary'],
        'Non-ICS': GEN_COLORS['muted'],
    }

    x = range(len(ret_df))
    colors = [channel_colors.get(c, GEN_COLORS['muted']) for c in ret_df['channel']]

    bars = ax.bar(x, ret_df['activity_rate'], color=colors,
                  edgecolor='white', linewidth=0.5, width=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(ret_df['channel'], fontsize=14, fontweight='bold')
    ax.set_ylabel("% of Accounts Active in Latest Month", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Value labels
    for bar, (_, row) in zip(bars, ret_df.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                f"{row['activity_rate']:.1f}%\n({int(row['active_accounts']):,} of {int(row['total_accounts']):,})",
                ha='center', va='bottom', fontsize=11, fontweight='bold',
                color=channel_colors.get(row['channel'], GEN_COLORS['muted']))

    ax.set_title("Account Activity Rate by ICS Channel",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02,
            f"What % of each channel's accounts transacted in {most_recent}?  (over {DATASET_LABEL})",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
