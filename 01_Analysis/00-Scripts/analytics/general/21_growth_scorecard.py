# ===========================================================================
# GROWTH SCORECARD: Diverging Bar of Growth Metrics (Conference Edition)
# ===========================================================================
# Green = growing, red = declining. (8,7) square.

# Compute growth metrics comparing latest vs earliest available
if len(monthly_summary) >= 2:
    first_month = monthly_summary.iloc[0]
    last_month = monthly_summary.iloc[-1]

    def _growth_pct(latest, earliest):
        if earliest == 0:
            return 0
        return ((latest - earliest) / earliest) * 100

    growth_metrics = pd.DataFrame([
        {'Metric': 'Transactions',
         'Growth %': _growth_pct(last_month['txn_count'], first_month['txn_count'])},
        {'Metric': 'Accounts',
         'Growth %': _growth_pct(last_month['unique_accounts'], first_month['unique_accounts'])},
        {'Metric': 'Merchants',
         'Growth %': _growth_pct(last_month['unique_merchants'], first_month['unique_merchants'])},
        {'Metric': 'Txns/Account',
         'Growth %': _growth_pct(last_month['txn_per_account'], first_month['txn_per_account'])},
    ])

    fig, ax = plt.subplots(figsize=(8, 7))

    y_pos = range(len(growth_metrics))
    colors = [
        GEN_COLORS['success'] if v >= 0 else GEN_COLORS['accent']
        for v in growth_metrics['Growth %']
    ]

    bars = ax.barh(
        y_pos, growth_metrics['Growth %'],
        color=colors, edgecolor='white', linewidth=1.5, height=0.6
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(growth_metrics['Metric'], fontsize=14, fontweight='bold')
    ax.invert_yaxis()

    # Zero line
    ax.axvline(x=0, color=GEN_COLORS['muted'], linewidth=2, linestyle='-', zorder=1)

    # Value labels
    for bar, val in zip(bars, growth_metrics['Growth %']):
        x_offset = 0.5 if val >= 0 else -0.5
        ax.text(val + x_offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%",
                va='center', ha='left' if val >= 0 else 'right',
                fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.set_xlabel("Growth %", fontsize=16, fontweight='bold', labelpad=10)

    period_label = f"{monthly_summary.index[0]} to {monthly_summary.index[-1]}"
    ax.set_title("Growth Scorecard",
                 fontsize=22, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, f"First vs last month: {period_label}",
            transform=ax.transAxes, fontsize=14,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
else:
    print("Need at least 2 months of data for growth scorecard.")
