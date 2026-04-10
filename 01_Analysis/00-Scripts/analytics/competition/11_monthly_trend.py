# ===========================================================================
# MONTHLY TREND: Competitor Activity Over Time (Conference Edition)
# ===========================================================================
# Dual-axis: Transaction count trend + Unique accounts trend
# No dollar figures. Rolling average for smoothing.

if len(all_competitor_data) > 0:
    all_competitor_trans = pd.concat(all_competitor_data.values(), ignore_index=True)

    if 'year_month' not in all_competitor_trans.columns:
        all_competitor_trans['year_month'] = pd.to_datetime(
            all_competitor_trans['transaction_date']
        ).dt.to_period('M')

    monthly = all_competitor_trans.groupby('year_month').agg({
        'amount': 'count',
        'primary_account_num': 'nunique'
    }).rename(columns={'amount': 'transactions', 'primary_account_num': 'accounts'})
    monthly = monthly.sort_index()

    # Convert Period index to timestamps for plotting
    monthly.index = monthly.index.to_timestamp()

    # 3-month rolling average for smooth conference line
    monthly['txn_rolling'] = monthly['transactions'].rolling(3, min_periods=1).mean()
    monthly['acct_rolling'] = monthly['accounts'].rolling(3, min_periods=1).mean()

    # Month-over-month growth
    monthly['txn_growth'] = monthly['transactions'].pct_change() * 100

    # ----- Build chart -----
    fig, ax1 = plt.subplots(figsize=(14, 7))

    # Transactions bar (light, background)
    ax1.bar(
        monthly.index,
        monthly['transactions'],
        width=25,
        color=GEN_COLORS['info'],
        alpha=0.25,
        label='Monthly Transactions',
        zorder=2
    )

    # Transaction rolling line (bold, foreground)
    ax1.plot(
        monthly.index,
        monthly['txn_rolling'],
        color=GEN_COLORS['info'],
        linewidth=3.5,
        label='Transaction Trend (3mo avg)',
        zorder=4
    )

    ax1.set_ylabel("Transaction Count", fontsize=18, fontweight='bold',
                    color=GEN_COLORS['info'], labelpad=12)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    ax1.tick_params(axis='y', colors=GEN_COLORS['info'])

    # Second axis: Unique accounts
    ax2 = ax1.twinx()
    ax2.plot(
        monthly.index,
        monthly['acct_rolling'],
        color=GEN_COLORS['accent'],
        linewidth=3.5,
        linestyle='--',
        label='Unique Accounts (3mo avg)',
        zorder=4
    )
    ax2.set_ylabel("Unique Accounts", fontsize=18, fontweight='bold',
                    color=GEN_COLORS['accent'], labelpad=12)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    ax2.tick_params(axis='y', colors=GEN_COLORS['accent'])

    # Axes cleanup
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.grid(False)

    # Light horizontal grid on primary axis
    ax1.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)

    # X-axis formatting
    ax1.set_xlabel("")
    import matplotlib.dates as mdates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax1.tick_params(axis='x', rotation=45)

    # ----- Title -----
    ax1.set_title(
        "Competitor Activity Trend",
        fontsize=26, fontweight='bold',
        color=GEN_COLORS['dark_text'], pad=20, loc='left'
    )
    ax1.text(0.0, 0.97, "Are competitors gaining momentum with your customers?",
             transform=ax1.transAxes, fontsize=15,
             color=GEN_COLORS['muted'], style='italic')

    # ----- Callout: latest growth rate -----
    latest_growth = monthly['txn_growth'].iloc[-1] if len(monthly) > 1 else 0
    growth_color = GEN_COLORS['accent'] if latest_growth > 0 else GEN_COLORS['success']
    growth_label = "GROWING" if latest_growth > 0 else "DECLINING"
    ax1.text(
        0.99, 0.95,
        f"Latest month: {latest_growth:+.1f}% ({growth_label})",
        transform=ax1.transAxes,
        fontsize=16, fontweight='bold',
        color=growth_color,
        ha='right', va='top',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=growth_color, alpha=0.9)
    )

    # ----- Combined legend -----
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        lines1 + lines2, labels1 + labels2,
        loc='upper center', bbox_to_anchor=(0.5, -0.15),
        ncol=3, fontsize=14, frameon=False
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.18)
    plt.show()

    # ----- OPPORTUNITY CALLOUT -----
    if latest_growth < 0:
        print(f"\n    OPPORTUNITY: Competitor transaction activity declined {latest_growth:.1f}% last month.")
        print("    Your customers may be pulling back from competitors -- time to re-engage.")
