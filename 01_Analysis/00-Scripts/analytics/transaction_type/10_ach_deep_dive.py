# ===========================================================================
# ACH DEEP DIVE: Where Does ACH Money Flow?
# ===========================================================================
# Two panels:
#   Left:  Top 15 ACH merchants/payees by total volume
#   Right: Monthly ACH trend (volume + unique accounts)
#
# Depends on: combined_df, GEN_COLORS

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')
_ACH_COLOR = GEN_COLORS.get('info', '#457B9D')

ach_df = combined_df[combined_df['transaction_type'] == 'ACH'].copy()

if len(ach_df) < 50:
    print(f"    Insufficient ACH data ({len(ach_df)} records). Skipping.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 9),
                                    gridspec_kw={'width_ratios': [1.2, 1]})
    fig.subplots_adjust(wspace=0.30, top=0.85, bottom=0.12)

    # =================================================================
    # LEFT: Top 15 ACH Merchants by Volume
    # =================================================================
    ach_merch = ach_df.groupby('merchant_consolidated').agg(
        txn_count=('transaction_date', 'count'),
        total_spend=('amount', 'sum'),
        unique_accounts=('primary_account_num', 'nunique'),
        avg_amount=('amount', 'mean'),
    ).reset_index().sort_values('total_spend', ascending=False)

    _top = ach_merch.head(15).sort_values('total_spend', ascending=True)
    _names = _top['merchant_consolidated'].apply(lambda x: x[:25] + '...' if len(str(x)) > 25 else x)
    _y = np.arange(len(_top))

    bars = ax1.barh(_y, _top['total_spend'], height=0.6,
                    color=_ACH_COLOR, edgecolor='white', linewidth=0.5, alpha=0.85)

    for i, (bar, spend, accts) in enumerate(zip(bars, _top['total_spend'], _top['unique_accounts'])):
        _fmt = f"${spend/1e6:,.1f}M" if spend >= 1e6 else f"${spend/1e3:,.0f}K"
        ax1.text(bar.get_width() + bar.get_width() * 0.02, bar.get_y() + bar.get_height() / 2,
                 f'{_fmt}  ({int(accts):,} accts)',
                 va='center', fontsize=15, fontweight='bold', color=_ACH_COLOR)

    ax1.set_yticks(_y)
    ax1.set_yticklabels(_names, fontsize=14, fontweight='bold')
    ax1.set_xlabel('Total ACH Volume', fontsize=16, fontweight='bold', labelpad=8)
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"))
    ax1.set_title('Top 15 ACH Payees by Volume',
                  fontsize=20, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax1.set_axisbelow(True)

    # =================================================================
    # RIGHT: Monthly ACH Trend
    # =================================================================
    ach_monthly = ach_df.groupby('year_month').agg(
        txn_count=('transaction_date', 'count'),
        total_spend=('amount', 'sum'),
        unique_accounts=('primary_account_num', 'nunique'),
        avg_amount=('amount', 'mean'),
    ).sort_index()

    dates = ach_monthly.index.to_timestamp()
    spend = ach_monthly['total_spend'].values

    ax2.fill_between(dates, spend, alpha=0.15, color=_ACH_COLOR)
    ax2.plot(dates, spend, color=_ACH_COLOR, linewidth=2.5, marker='o',
             markersize=5, markeredgecolor='white', markeredgewidth=1.5,
             zorder=4, label='ACH Volume')

    ax2.set_ylabel('Monthly ACH Volume', fontsize=16, fontweight='bold', labelpad=8)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"))

    # Unique accounts on secondary y-axis
    ax2b = ax2.twinx()
    ax2b.plot(dates, ach_monthly['unique_accounts'], color=_MUTED, linewidth=2,
              linestyle='--', marker='s', markersize=4, alpha=0.7, label='Unique Accounts')
    ax2b.set_ylabel('Unique ACH Accounts', fontsize=15, fontweight='bold',
                    labelpad=8, color=_MUTED)
    ax2b.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax2b.tick_params(axis='y', colors=_MUTED)

    # First/last labels
    _first_fmt = f"${spend[0]/1e6:,.2f}M" if spend[0] >= 1e6 else f"${spend[0]/1e3:,.0f}K"
    _last_fmt = f"${spend[-1]/1e6:,.2f}M" if spend[-1] >= 1e6 else f"${spend[-1]/1e3:,.0f}K"
    _pct_chg = (spend[-1] / spend[0] - 1) * 100 if spend[0] > 0 else 0

    ax2.annotate(f'{_first_fmt}', xy=(dates[0], spend[0]),
                 xytext=(5, -20), textcoords='offset points',
                 fontsize=16, fontweight='bold', color=_ACH_COLOR, ha='left')
    ax2.annotate(f'{_last_fmt} ({_pct_chg:+.1f}%)', xy=(dates[-1], spend[-1]),
                 xytext=(-5, 15), textcoords='offset points',
                 fontsize=16, fontweight='bold',
                 color=GEN_COLORS.get('success', '#2A9D8F') if _pct_chg >= 0 else GEN_COLORS.get('accent', '#E63946'),
                 ha='right')

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    ax2.tick_params(axis='x', rotation=0, labelsize=14)
    ax2.set_title('Monthly ACH Volume Trend',
                  fontsize=20, fontweight='bold', color=_DARK, pad=10)

    # Combined legend
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=14, framealpha=0.9, loc='upper left')

    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax2.set_axisbelow(True)

    fig.suptitle('ACH Payment Patterns',
                 fontsize=28, fontweight='bold', color=_DARK, y=0.95)
    fig.text(0.5, 0.905,
             f'{len(ach_df):,} ACH transactions  |  {ach_df["primary_account_num"].nunique():,} accounts',
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.show()

    # Console
    print(f"\n    ACH DEEP DIVE")
    print(f"    {'='*50}")
    print(f"    Total ACH transactions: {len(ach_df):,}")
    print(f"    Total ACH volume: {_first_fmt} to {_last_fmt} ({_pct_chg:+.1f}%)")
    print(f"    Unique ACH accounts: {ach_df['primary_account_num'].nunique():,}")
    print(f"    Avg ACH amount: ${ach_df['amount'].mean():,.2f}")
    print(f"    Top ACH payee: {ach_merch.iloc[0]['merchant_consolidated']}")
