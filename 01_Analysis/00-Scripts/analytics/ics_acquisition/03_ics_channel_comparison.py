# ===========================================================================
# ICS CHANNEL COMPARISON: REF vs DM vs Non-ICS (Conference Edition)
# ===========================================================================
# Grouped horizontal bar: key metrics by acquisition channel. (14,7).
# All rate metrics normalized to per-month for time context.

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping channel comparison.")
else:
    fig, axes = plt.subplots(1, 3, figsize=(14, 7))

    channels = ics_agg.sort_values('txn_count', ascending=True)
    names = channels['ics_account'].tolist()
    y_pos = range(len(channels))

    channel_colors = {
        'REF': GEN_COLORS['info'],
        'DM': GEN_COLORS['primary'],
        'Non-ICS': GEN_COLORS['muted'],
    }
    colors = [channel_colors.get(n, GEN_COLORS['muted']) for n in names]

    metrics = [
        ('avg_spend', 'Avg Ticket ($)', '${:.2f}'),
        ('txns_per_acct_mo', 'Txns/Acct/Month', '{:.1f}'),
        ('spend_per_acct_mo', 'Spend/Acct/Month ($)', '${:,.0f}'),
    ]

    for ax, (col, label, fmt) in zip(axes, metrics):
        ax.barh(y_pos, channels[col], color=colors,
                edgecolor='white', linewidth=0.5, height=0.55)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=11, fontweight='bold')
        ax.set_xlabel(label, fontsize=12, fontweight='bold', labelpad=8)
        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        for j, (_, row) in enumerate(channels.iterrows()):
            ax.text(row[col] * 1.02, j, fmt.format(row[col]),
                    va='center', fontsize=9, fontweight='bold',
                    color=channel_colors.get(row['ics_account'], GEN_COLORS['muted']))

    fig.suptitle("ICS Acquisition Channel Comparison",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.96,
             f"How do referral and direct mail accounts compare?  ({DATASET_LABEL}, {DATASET_MONTHS} mo)",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()
