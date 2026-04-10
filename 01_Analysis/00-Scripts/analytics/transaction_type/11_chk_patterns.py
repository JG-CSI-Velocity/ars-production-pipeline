# ===========================================================================
# CHECK PATTERNS: Check Usage Trends & Ticket Size Comparison
# ===========================================================================
# Two panels:
#   Left:  Monthly CHK volume trend with linear trendline
#   Right: Average ticket comparison across all 4 transaction types
#
# Depends on: combined_df, tt_agg, GEN_COLORS

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')
_CHK_COLOR = GEN_COLORS.get('accent', '#E63946')

_type_colors = {
    'SIG': GEN_COLORS.get('warning', '#E9C46A'),
    'PIN': GEN_COLORS.get('success', '#2A9D8F'),
    'ACH': GEN_COLORS.get('info', '#457B9D'),
    'CHK': GEN_COLORS.get('accent', '#E63946'),
}

chk_df = combined_df[combined_df['transaction_type'] == 'CHK'].copy()

if len(chk_df) < 50:
    print(f"    Insufficient CHK data ({len(chk_df)} records). Skipping.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 9))
    fig.subplots_adjust(wspace=0.28, top=0.85, bottom=0.15)

    # =================================================================
    # LEFT: Monthly CHK Volume Trend with Trendline
    # =================================================================
    chk_monthly = chk_df.groupby('year_month').agg(
        txn_count=('transaction_date', 'count'),
        total_spend=('amount', 'sum'),
        unique_accounts=('primary_account_num', 'nunique'),
    ).sort_index()

    dates = chk_monthly.index.to_timestamp()
    spend = chk_monthly['total_spend'].values
    counts = chk_monthly['txn_count'].values

    # Trend line
    x_numeric = np.arange(len(dates))
    _coeffs = np.polyfit(x_numeric, spend, 1)
    _trend = np.poly1d(_coeffs)
    _trend_vals = _trend(x_numeric)
    _monthly_slope = _coeffs[0]
    _pct_chg = (spend[-1] / spend[0] - 1) * 100 if spend[0] > 0 else 0
    _is_declining = _pct_chg < 0

    ax1.fill_between(dates, spend, alpha=0.15, color=_CHK_COLOR)
    ax1.plot(dates, spend, color=_CHK_COLOR, linewidth=2.5, marker='o',
             markersize=5, markeredgecolor='white', markeredgewidth=1.5,
             zorder=4, label='Check Volume')

    _trend_color = GEN_COLORS.get('accent', '#E63946') if _is_declining else GEN_COLORS.get('success', '#2A9D8F')
    ax1.plot(dates, _trend_vals, color=_trend_color, linewidth=2,
             linestyle='--', alpha=0.7, zorder=3,
             label=f'Trend ({_pct_chg:+.1f}%)')

    # First/last annotations
    _first_fmt = f"${spend[0]/1e6:,.2f}M" if spend[0] >= 1e6 else f"${spend[0]/1e3:,.0f}K"
    _last_fmt = f"${spend[-1]/1e6:,.2f}M" if spend[-1] >= 1e6 else f"${spend[-1]/1e3:,.0f}K"

    ax1.annotate(_first_fmt, xy=(dates[0], spend[0]),
                 xytext=(5, -20), textcoords='offset points',
                 fontsize=16, fontweight='bold', color=_CHK_COLOR, ha='left')
    ax1.annotate(f'{_last_fmt} ({_pct_chg:+.1f}%)', xy=(dates[-1], spend[-1]),
                 xytext=(-5, 15), textcoords='offset points',
                 fontsize=16, fontweight='bold', color=_trend_color, ha='right')

    ax1.set_ylabel('Monthly Check Volume', fontsize=16, fontweight='bold', labelpad=8)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda v, _: f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    ax1.tick_params(axis='x', rotation=0, labelsize=14)
    ax1.legend(fontsize=14, framealpha=0.9, loc='upper right')
    ax1.set_title('Check Volume Over Time',
                  fontsize=20, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax1.set_axisbelow(True)

    # =================================================================
    # RIGHT: Average Ticket by Transaction Type
    # =================================================================
    _types_ordered = [t for t in ['PIN', 'SIG', 'ACH', 'CHK'] if t in tt_agg['transaction_type'].values]
    _ticket_data = tt_agg[tt_agg['transaction_type'].isin(_types_ordered)].set_index('transaction_type')
    _ticket_data = _ticket_data.reindex(_types_ordered)

    _x = np.arange(len(_types_ordered))
    _colors = [_type_colors.get(t, _MUTED) for t in _types_ordered]

    bars = ax2.bar(_x, _ticket_data['avg_spend'], width=0.5,
                   color=_colors, edgecolor='white', linewidth=1, alpha=0.85)

    # Value labels
    for bar, t in zip(bars, _types_ordered):
        _val = _ticket_data.loc[t, 'avg_spend']
        _count = int(_ticket_data.loc[t, 'txn_count'])
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + bar.get_height() * 0.02,
                 f'${_val:,.2f}', ha='center', va='bottom', fontsize=16,
                 fontweight='bold', color=_type_colors.get(t, _DARK))
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                 f'{_count:,}\ntxns', ha='center', va='center', fontsize=14,
                 color='white', fontweight='bold')

    # Highlight highest ticket
    _max_type = _ticket_data['avg_spend'].idxmax()
    _max_idx = _types_ordered.index(_max_type)
    bars[_max_idx].set_edgecolor(_DARK)
    bars[_max_idx].set_linewidth(2)

    ax2.set_xticks(_x)
    ax2.set_xticklabels(_types_ordered, fontsize=16, fontweight='bold')
    ax2.set_ylabel('Average Transaction Amount', fontsize=16, fontweight='bold', labelpad=8)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax2.set_title('Average Ticket by Transaction Type',
                  fontsize=20, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax2.set_axisbelow(True)

    fig.suptitle('Check Transaction Patterns',
                 fontsize=28, fontweight='bold', color=_DARK, y=0.95)
    _direction = 'declining' if _is_declining else 'growing'
    fig.text(0.5, 0.905,
             f'{len(chk_df):,} check transactions  |  Volume {_direction} at {_pct_chg:+.1f}%',
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.show()

    # Console
    print(f"\n    CHECK PATTERNS")
    print(f"    {'='*50}")
    print(f"    Total check transactions: {len(chk_df):,}")
    print(f"    Avg check amount: ${chk_df['amount'].mean():,.2f}")
    print(f"    Median check amount: ${chk_df['amount'].median():,.2f}")
    print(f"    Volume trend: {_pct_chg:+.1f}% ({_direction})")
    print(f"    Monthly slope: ${_monthly_slope:+,.0f}/mo")
    print(f"    Unique check writers: {chk_df['primary_account_num'].nunique():,}")
