# ===========================================================================
# TXN TYPE TREND: Monthly Volume by Transaction Type
# ===========================================================================
# Three panels showing actual volumes over time, not just mix %:
#   Left:   Total spend by type (stacked area)
#   Center: Transaction count by type (stacked area)
#   Right:  PIN vs SIG share % (line chart)
#
# Depends on: tt_monthly (cell 01)

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(26, 8))
fig.subplots_adjust(wspace=0.28, top=0.85, bottom=0.18)

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')

# Type colors
_type_colors = {
    'SIG': GEN_COLORS.get('warning', '#E9C46A'),
    'PIN': GEN_COLORS.get('success', '#2A9D8F'),
    'ACH': GEN_COLORS.get('info', '#457B9D'),
    'CHK': GEN_COLORS.get('accent', '#E63946'),
}

# Prepare pivots
_spend_pivot = tt_monthly.pivot(
    index='year_month', columns='transaction_type', values='total_spend'
).fillna(0).sort_index()

_count_pivot = tt_monthly.pivot(
    index='year_month', columns='transaction_type', values='txn_count'
).fillna(0).sort_index()

_share_pivot = tt_monthly.pivot(
    index='year_month', columns='transaction_type', values='share_pct'
).fillna(0).sort_index()

dates = _spend_pivot.index.to_timestamp()

# Order: SIG first (usually larger), then PIN, then others
_main_types = [c for c in ['SIG', 'PIN'] if c in _spend_pivot.columns]
_other_types = [c for c in _spend_pivot.columns if c not in _main_types]
_all_types = _main_types + sorted(_other_types)

_colors = [_type_colors.get(t, BRACKET_PALETTE[i % len(BRACKET_PALETTE)])
           for i, t in enumerate(_all_types)]

# =================================================================
# LEFT: Total Spend by Type (stacked area)
# =================================================================
ax1.stackplot(dates, *[_spend_pivot[t] for t in _all_types],
              labels=_all_types, colors=_colors, alpha=0.75,
              edgecolor='white', linewidth=0.5)

ax1.set_ylabel('Total Monthly Spend', fontsize=16, fontweight='bold', labelpad=8)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"))
ax1.set_title('Spend Volume by Type', fontsize=18, fontweight='bold', color=_DARK, pad=8)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax1.tick_params(axis='x', rotation=0, labelsize=14)
gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax1.set_axisbelow(True)

# =================================================================
# CENTER: Transaction Count by Type (stacked area)
# =================================================================
ax2.stackplot(dates, *[_count_pivot[t] for t in _all_types],
              labels=_all_types, colors=_colors, alpha=0.75,
              edgecolor='white', linewidth=0.5)

ax2.set_ylabel('Monthly Transactions', fontsize=16, fontweight='bold', labelpad=8)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e3:,.0f}K" if v >= 1e3 else f"{v:,.0f}"))
ax2.set_title('Transaction Count by Type', fontsize=18, fontweight='bold', color=_DARK, pad=8)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax2.tick_params(axis='x', rotation=0, labelsize=14)
gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax2.set_axisbelow(True)

# =================================================================
# RIGHT: PIN vs SIG Share % (line chart)
# =================================================================
for t in _main_types:
    _vals = _share_pivot[t] if t in _share_pivot.columns else None
    if _vals is not None:
        ax3.plot(dates, _vals, color=_type_colors.get(t, _MUTED), linewidth=2.5,
                 marker='o', markersize=4, label=t, zorder=3)
        # Start and end labels
        ax3.text(dates[0], _vals.iloc[0], f' {_vals.iloc[0]:.0f}%',
                 ha='right', va='center', fontsize=15, fontweight='bold',
                 color=_type_colors.get(t, _MUTED))
        ax3.text(dates[-1], _vals.iloc[-1], f' {_vals.iloc[-1]:.0f}%',
                 ha='left', va='center', fontsize=15, fontweight='bold',
                 color=_type_colors.get(t, _MUTED))

ax3.set_ylabel('% of Transactions', fontsize=16, fontweight='bold', labelpad=8)
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax3.set_title('PIN vs SIG Share', fontsize=18, fontweight='bold', color=_DARK, pad=8)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax3.tick_params(axis='x', rotation=0, labelsize=14)
ax3.legend(fontsize=14, framealpha=0.9)
gen_clean_axes(ax3, keep_left=True, keep_bottom=True)
ax3.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax3.set_axisbelow(True)

# Shared legend for stacked charts
handles, labels = ax1.get_legend_handles_labels()
fig.legend(handles, labels, loc='lower center', ncol=len(_all_types),
           fontsize=14, frameon=False, bbox_to_anchor=(0.35, 0.01),
           title='Transaction Type',
           title_fontproperties={'weight': 'bold', 'size': 15})

fig.suptitle('Transaction Volume Trends by Type',
             fontsize=28, fontweight='bold', color=_DARK, y=0.95)
fig.text(0.5, 0.905, DATASET_LABEL,
         ha='center', fontsize=16, color=_MUTED, style='italic')

plt.show()

# Console: first vs last month totals
_first_mo = _spend_pivot.index[0]
_last_mo = _spend_pivot.index[-1]
_first_spend = _spend_pivot.loc[_first_mo].sum()
_last_spend = _spend_pivot.loc[_last_mo].sum()
_spend_change = (_last_spend / _first_spend - 1) * 100
_first_count = _count_pivot.loc[_first_mo].sum()
_last_count = _count_pivot.loc[_last_mo].sum()
_count_change = (_last_count / _first_count - 1) * 100

print(f"\n    {_first_mo} → {_last_mo}:")
print(f"      Spend: ${_first_spend:,.0f} → ${_last_spend:,.0f}  ({_spend_change:+.1f}%)")
print(f"      Txns:  {_first_count:,.0f} → {_last_count:,.0f}  ({_count_change:+.1f}%)")
for t in _all_types:
    _t_first = _spend_pivot[t].iloc[0]
    _t_last = _spend_pivot[t].iloc[-1]
    _t_chg = (_t_last / _t_first - 1) * 100 if _t_first > 0 else 0
    print(f"      {t}: ${_t_first:,.0f} → ${_t_last:,.0f}  ({_t_chg:+.1f}%)")
