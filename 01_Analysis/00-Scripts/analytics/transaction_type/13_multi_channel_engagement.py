# ===========================================================================
# MULTI-CHANNEL ENGAGEMENT: The Stickiness Story
# ===========================================================================
# Accounts using multiple payment types are stickier and more valuable.
# Three panels:
#   Left:   Account count by number of channel types (1, 2, 3, 4)
#   Center: Avg monthly spend per account by channel count
#   Right:  Avg active months by channel count
#
# Depends on: combined_df, total_months (from portfolio_data)
# Produces: acct_channels (used by cell 14)

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')
_SUCCESS = GEN_COLORS.get('success', '#2A9D8F')

# Build per-account channel usage profile
acct_channels = combined_df.groupby('primary_account_num').agg(
    channel_count=('transaction_type', 'nunique'),
    total_spend=('amount', 'sum'),
    txn_count=('transaction_date', 'count'),
    active_months=('year_month', 'nunique'),
).reset_index()

# Add per-type flags
for _t in ['PIN', 'SIG', 'ACH', 'CHK']:
    _accts_with = combined_df[combined_df['transaction_type'] == _t]['primary_account_num'].unique()
    acct_channels[f'has_{_t.lower()}'] = acct_channels['primary_account_num'].isin(_accts_with).astype(int)

_n_months = total_months if 'total_months' in dir() else len(combined_df['year_month'].unique())
acct_channels['monthly_spend'] = acct_channels['total_spend'] / _n_months
acct_channels['monthly_txns'] = acct_channels['txn_count'] / _n_months

# Aggregate by channel count
channel_summary = acct_channels.groupby('channel_count').agg(
    acct_count=('primary_account_num', 'count'),
    avg_monthly_spend=('monthly_spend', 'mean'),
    median_monthly_spend=('monthly_spend', 'median'),
    avg_active_months=('active_months', 'mean'),
    avg_monthly_txns=('monthly_txns', 'mean'),
    total_spend=('total_spend', 'sum'),
).reset_index()

# Color gradient: lighter for fewer channels, darker for more
_channel_colors = {
    1: '#B2DFDB',
    2: '#4DB6AC',
    3: '#00897B',
    4: '#004D40',
}

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(26, 8))
fig.subplots_adjust(wspace=0.28, top=0.85, bottom=0.15)

_x = channel_summary['channel_count'].values
_x_pos = np.arange(len(_x))
_colors = [_channel_colors.get(c, _MUTED) for c in _x]

# =================================================================
# LEFT: Account Count by Channel Count
# =================================================================
bars1 = ax1.bar(_x_pos, channel_summary['acct_count'], width=0.55,
                color=_colors, edgecolor='white', linewidth=1)

for bar, count, pct in zip(bars1, channel_summary['acct_count'],
                            channel_summary['acct_count'] / channel_summary['acct_count'].sum() * 100):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + bar.get_height() * 0.02,
             f'{count:,}\n({pct:.0f}%)', ha='center', va='bottom',
             fontsize=15, fontweight='bold', color=_DARK)

ax1.set_xticks(_x_pos)
ax1.set_xticklabels([f'{c} type{"s" if c > 1 else ""}' for c in _x],
                    fontsize=15, fontweight='bold')
ax1.set_ylabel('Number of Accounts', fontsize=16, fontweight='bold', labelpad=8)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e3:,.0f}K" if v >= 1e3 else f"{v:,.0f}"))
ax1.set_title('Accounts by Channel Diversity',
              fontsize=18, fontweight='bold', color=_DARK, pad=10)
gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax1.set_axisbelow(True)

# =================================================================
# CENTER: Avg Monthly Spend by Channel Count
# =================================================================
bars2 = ax2.bar(_x_pos, channel_summary['avg_monthly_spend'], width=0.55,
                color=_colors, edgecolor='white', linewidth=1)

for bar, val in zip(bars2, channel_summary['avg_monthly_spend']):
    _fmt = f"${val:,.0f}"
    ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + bar.get_height() * 0.02,
             _fmt, ha='center', va='bottom',
             fontsize=16, fontweight='bold', color=_DARK)

# Multiplier annotation: how much more do multi-channel users spend?
_single = channel_summary[channel_summary['channel_count'] == 1]['avg_monthly_spend'].values
if len(_single) > 0 and _single[0] > 0:
    _base = _single[0]
    for i, (bar, ch_count) in enumerate(zip(bars2, _x)):
        if ch_count > 1:
            _mult = channel_summary[channel_summary['channel_count'] == ch_count]['avg_monthly_spend'].values[0] / _base
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                     f'{_mult:.1f}x', ha='center', va='center',
                     fontsize=16, fontweight='bold', color='white')

ax2.set_xticks(_x_pos)
ax2.set_xticklabels([f'{c} type{"s" if c > 1 else ""}' for c in _x],
                    fontsize=15, fontweight='bold')
ax2.set_ylabel('Avg Monthly Spend per Account', fontsize=16, fontweight='bold', labelpad=8)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
ax2.set_title('Spend Increases with Channel Diversity',
              fontsize=18, fontweight='bold', color=_DARK, pad=10)
gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax2.set_axisbelow(True)

# =================================================================
# RIGHT: Avg Active Months by Channel Count
# =================================================================
bars3 = ax3.bar(_x_pos, channel_summary['avg_active_months'], width=0.55,
                color=_colors, edgecolor='white', linewidth=1)

for bar, val in zip(bars3, channel_summary['avg_active_months']):
    ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + bar.get_height() * 0.02,
             f'{val:.1f}', ha='center', va='bottom',
             fontsize=16, fontweight='bold', color=_DARK)

# Reference: max possible months
ax3.axhline(_n_months, color=_MUTED, linewidth=1, linestyle=':', alpha=0.5)
ax3.text(len(_x_pos) - 0.5, _n_months + 0.2, f'Max: {_n_months} months',
         fontsize=14, color=_MUTED, ha='right', fontweight='bold')

ax3.set_xticks(_x_pos)
ax3.set_xticklabels([f'{c} type{"s" if c > 1 else ""}' for c in _x],
                    fontsize=15, fontweight='bold')
ax3.set_ylabel('Avg Active Months', fontsize=16, fontweight='bold', labelpad=8)
ax3.set_title('Engagement Consistency',
              fontsize=18, fontweight='bold', color=_DARK, pad=10)
gen_clean_axes(ax3, keep_left=True, keep_bottom=True)
ax3.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax3.set_axisbelow(True)

fig.suptitle('Multi-Channel Engagement = Higher Value',
             fontsize=28, fontweight='bold', color=_DARK, y=0.95)
fig.text(0.5, 0.905,
         'Accounts using more payment channels spend more and stay engaged longer',
         ha='center', fontsize=16, color=_MUTED, style='italic')

plt.show()

# Console
print(f"\n    MULTI-CHANNEL ENGAGEMENT")
print(f"    {'='*50}")
for _, row in channel_summary.iterrows():
    _c = int(row['channel_count'])
    print(f"    {_c} type{'s' if _c > 1 else ' '}: {int(row['acct_count']):,} accounts, "
          f"${row['avg_monthly_spend']:,.0f}/mo avg, "
          f"{row['avg_active_months']:.1f} active months")
if len(_single) > 0 and _single[0] > 0:
    _max_ch = channel_summary['channel_count'].max()
    _max_spend = channel_summary[channel_summary['channel_count'] == _max_ch]['avg_monthly_spend'].values[0]
    print(f"    Multiplier: {_max_ch}-channel accounts spend {_max_spend/_single[0]:.1f}x more than single-channel")
