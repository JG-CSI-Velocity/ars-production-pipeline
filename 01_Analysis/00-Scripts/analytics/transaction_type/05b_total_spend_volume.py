# ===========================================================================
# TOTAL SPEND VOLUME: Is Portfolio Spend Actually Down?
# ===========================================================================
# Presentation-ready single slide answering the client's claim.
#
# Row 1: 4 KPI cards (First Month, Last Month, Change %, Monthly Trend)
# Row 2: Full-width line chart with trend + per-type mini bars
#
# Depends on: tt_monthly (cell 01)

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')
_SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
_ACCENT = GEN_COLORS.get('accent', '#E63946')
_INFO = GEN_COLORS.get('info', '#457B9D')
_WARNING = GEN_COLORS.get('warning', '#E9C46A')

_type_colors = {
    'SIG': _WARNING,
    'PIN': _SUCCESS,
    'ACH': _INFO,
    'CHK': _ACCENT,
}

def _fmt_spend(v):
    if abs(v) >= 1e6:
        return f"${v/1e6:,.2f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:,.0f}K"
    return f"${v:,.0f}"

# ---------------------------------------------------------------------------
# Aggregate total spend per month (all types combined)
# ---------------------------------------------------------------------------
_monthly_total = tt_monthly.groupby('year_month').agg(
    total_spend=('total_spend', 'sum'),
    txn_count=('txn_count', 'sum'),
).sort_index()

dates = _monthly_total.index.to_timestamp()
spend = _monthly_total['total_spend'].values
_n_months = len(spend)

# Trend line (linear regression)
x_numeric = np.arange(_n_months)
_coeffs = np.polyfit(x_numeric, spend, 1)
_trend_vals = np.poly1d(_coeffs)(x_numeric)
_monthly_slope = _coeffs[0]

# Direction and change
_is_up = spend[-1] > spend[0]
_pct_change = (spend[-1] / spend[0] - 1) * 100
_hero_color = _SUCCESS if _is_up else _ACCENT
_direction = "up" if _is_up else "down"
_trend_up = _monthly_slope > 0
_trend_color = _SUCCESS if _trend_up else _ACCENT
_avg_spend = spend.mean()

# Per-type first vs last
_type_changes = []
for t in tt_monthly['transaction_type'].unique():
    _td = tt_monthly[tt_monthly['transaction_type'] == t].sort_values('year_month')
    if len(_td) >= 2:
        _tf = _td.iloc[0]['total_spend']
        _tl = _td.iloc[-1]['total_spend']
        if _tf > 0:
            _type_changes.append((t, _tf, _tl, (_tl / _tf - 1) * 100))
_type_changes.sort(key=lambda x: abs(x[1] + x[2]), reverse=True)

# ---------------------------------------------------------------------------
# Build figure: KPI row + chart row + type breakdown row
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(26, 14))
gs = fig.add_gridspec(3, 1, height_ratios=[0.7, 1.8, 0.8],
                      hspace=0.25, top=0.88, bottom=0.05, left=0.05, right=0.95)

# =================================================================
# ROW 1: KPI Cards
# =================================================================
gs_cards = gs[0].subgridspec(1, 4, wspace=0.12)

_first_mo = _monthly_total.index[0]
_last_mo = _monthly_total.index[-1]

kpi_data = [
    {
        'label': f'First Month ({_first_mo})',
        'value': _fmt_spend(spend[0]),
        'sub': 'starting point',
        'color': _MUTED,
    },
    {
        'label': f'Last Month ({_last_mo})',
        'value': _fmt_spend(spend[-1]),
        'sub': 'most recent',
        'color': _hero_color,
    },
    {
        'label': 'YoY Change',
        'value': f'{_pct_change:+.1f}%',
        'sub': f'first vs last month',
        'color': _hero_color,
    },
    {
        'label': 'Total $ Change',
        'value': _fmt_spend(spend[-1] - spend[0]),
        'sub': f'{_direction} over {_n_months} months',
        'color': _hero_color,
    },
]

for idx, kpi in enumerate(kpi_data):
    ax = fig.add_subplot(gs_cards[idx])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    card = FancyBboxPatch(
        (0.3, 0.3), 9.4, 9.4,
        boxstyle="round,pad=0.3",
        facecolor=kpi['color'], alpha=0.10,
        edgecolor=kpi['color'], linewidth=3
    )
    ax.add_patch(card)

    ax.text(5, 7.2, kpi['label'],
            ha='center', va='center', fontsize=18, fontweight='bold',
            color=_DARK)
    ax.text(5, 4.5, kpi['value'],
            ha='center', va='center', fontsize=44, fontweight='bold',
            color=kpi['color'])
    ax.text(5, 2.0, kpi['sub'],
            ha='center', va='center', fontsize=16,
            color=_MUTED, style='italic')

# =================================================================
# ROW 2: Full-Width Line Chart
# =================================================================
ax_chart = fig.add_subplot(gs[1])

# Shaded area
ax_chart.fill_between(dates, spend, alpha=0.12, color=_INFO)

# Main line
ax_chart.plot(dates, spend, color=_INFO, linewidth=3.5, marker='o',
              markersize=7, markeredgecolor='white', markeredgewidth=2,
              zorder=4, label='Monthly Spend')

# Trend line
ax_chart.plot(dates, _trend_vals, color=_hero_color, linewidth=2.5,
              linestyle='--', alpha=0.8, zorder=3,
              label=f'Trend ({_pct_change:+.1f}%)')

# Start diamond
ax_chart.plot(dates[0], spend[0], marker='D', markersize=14, color=_MUTED,
              markeredgecolor='white', markeredgewidth=2.5, zorder=6)
ax_chart.annotate(_fmt_spend(spend[0]),
                  xy=(dates[0], spend[0]),
                  xytext=(15, -30), textcoords='offset points',
                  fontsize=20, fontweight='bold', color=_MUTED, ha='left',
                  arrowprops=dict(arrowstyle='->', color=_MUTED, lw=2))

# End diamond
ax_chart.plot(dates[-1], spend[-1], marker='D', markersize=14, color=_hero_color,
              markeredgecolor='white', markeredgewidth=2.5, zorder=6)
ax_chart.annotate(f'{_fmt_spend(spend[-1])}  ({_pct_change:+.1f}%)',
                  xy=(dates[-1], spend[-1]),
                  xytext=(-15, 25), textcoords='offset points',
                  fontsize=20, fontweight='bold', color=_hero_color, ha='right',
                  arrowprops=dict(arrowstyle='->', color=_hero_color, lw=2))

# Min/Max callouts
_min_idx = np.argmin(spend)
_max_idx = np.argmax(spend)
if _min_idx not in [0, len(spend) - 1]:
    ax_chart.plot(dates[_min_idx], spend[_min_idx], marker='v', markersize=10,
                  color=_ACCENT, markeredgecolor='white', markeredgewidth=1.5, zorder=5)
    ax_chart.annotate(f'Low: {_fmt_spend(spend[_min_idx])}',
                      xy=(dates[_min_idx], spend[_min_idx]),
                      xytext=(0, -22), textcoords='offset points',
                      fontsize=16, fontweight='bold', color=_ACCENT, ha='center')

if _max_idx not in [0, len(spend) - 1]:
    ax_chart.plot(dates[_max_idx], spend[_max_idx], marker='^', markersize=10,
                  color=_SUCCESS, markeredgecolor='white', markeredgewidth=1.5, zorder=5)
    ax_chart.annotate(f'High: {_fmt_spend(spend[_max_idx])}',
                      xy=(dates[_max_idx], spend[_max_idx]),
                      xytext=(0, 18), textcoords='offset points',
                      fontsize=16, fontweight='bold', color=_SUCCESS, ha='center')

# Average line
ax_chart.axhline(_avg_spend, color=_MUTED, linewidth=1.2, linestyle=':', alpha=0.5)
ax_chart.text(dates[_n_months // 2], _avg_spend,
              f'  Avg: {_fmt_spend(_avg_spend)}',
              fontsize=16, color=_MUTED, va='bottom', fontweight='bold')

ax_chart.set_ylabel('Total Monthly Spend', fontsize=20, fontweight='bold', labelpad=8)
ax_chart.yaxis.set_major_formatter(plt.FuncFormatter(
    lambda v, _: f"${v/1e6:,.1f}M" if v >= 1e6 else f"${v/1e3:,.0f}K"))
ax_chart.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
ax_chart.tick_params(axis='x', rotation=0, labelsize=16)
ax_chart.tick_params(axis='y', labelsize=16)
ax_chart.legend(fontsize=16, framealpha=0.9, loc='upper left')
gen_clean_axes(ax_chart, keep_left=True, keep_bottom=True)
ax_chart.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
ax_chart.set_axisbelow(True)

# =================================================================
# ROW 3: Per-Type Change Bars (horizontal, first vs last month)
# =================================================================
if len(_type_changes) > 0:
    gs_bottom = gs[2].subgridspec(1, 2, wspace=0.25, width_ratios=[1.5, 1])
    ax_types = fig.add_subplot(gs_bottom[0])
    ax_verdict = fig.add_subplot(gs_bottom[1])

    _tc_types = [tc[0] for tc in _type_changes]
    _tc_pcts = [tc[3] for tc in _type_changes]
    _tc_colors = [_SUCCESS if p >= 0 else _ACCENT for p in _tc_pcts]
    _y_pos = np.arange(len(_tc_types))

    bars = ax_types.barh(_y_pos, _tc_pcts, height=0.5,
                         color=_tc_colors, edgecolor='white', linewidth=1, alpha=0.85)

    for i, (bar, tc) in enumerate(zip(bars, _type_changes)):
        t, _tf, _tl, _tp = tc
        _sign = '+' if _tp >= 0 else ''
        ax_types.text(bar.get_width() + (1 if _tp >= 0 else -1),
                      bar.get_y() + bar.get_height() / 2,
                      f'{_sign}{_tp:.1f}%  ({_fmt_spend(_tf)} > {_fmt_spend(_tl)})',
                      va='center', ha='left' if _tp >= 0 else 'right',
                      fontsize=18, fontweight='bold',
                      color=_tc_colors[i])

    ax_types.axvline(0, color=_DARK, linewidth=1, alpha=0.3)
    ax_types.set_yticks(_y_pos)
    ax_types.set_yticklabels(_tc_types, fontsize=18, fontweight='bold')
    ax_types.set_xlabel('% Change (First to Last Month)', fontsize=16, fontweight='bold')
    ax_types.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax_types.tick_params(axis='x', labelsize=15)
    # No panel title -- avoids overlap with data labels
    gen_clean_axes(ax_types, keep_left=True, keep_bottom=True)
    ax_types.xaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax_types.set_axisbelow(True)
    # Expand x-axis so data labels don't clip
    _xlim = ax_types.get_xlim()
    ax_types.set_xlim(_xlim[0] * 1.1 if _xlim[0] < 0 else _xlim[0],
                      _xlim[1] * 1.4 if _xlim[1] > 0 else _xlim[1])

    # Summary card (red outline, white fill)
    ax_verdict.axis('off')

    _verdict_card = FancyBboxPatch(
        (0.02, 0.05), 0.96, 0.90,
        boxstyle="round,pad=0.04",
        facecolor='white', edgecolor=_ACCENT, linewidth=3,
        transform=ax_verdict.transAxes
    )
    ax_verdict.add_patch(_verdict_card)

    ax_verdict.text(0.50, 0.62,
                    f'Spend is {_direction}',
                    fontsize=36, fontweight='bold', color=_hero_color,
                    transform=ax_verdict.transAxes, ha='center', va='center')

    ax_verdict.text(0.50, 0.38,
                    f'{_fmt_spend(spend[0])} > {_fmt_spend(spend[-1])}',
                    fontsize=22, fontweight='bold', color=_DARK,
                    transform=ax_verdict.transAxes, ha='center', va='center')

    ax_verdict.text(0.50, 0.18,
                    f'{_pct_change:+.1f}% over {_n_months} months',
                    fontsize=18, fontweight='bold', color=_MUTED,
                    transform=ax_verdict.transAxes, ha='center', va='center')

fig.suptitle('Total Spend Volume: Is Spend Actually Down?',
             fontsize=32, fontweight='bold', color=_DARK, y=0.96)
fig.text(0.5, 0.92, DATASET_LABEL,
         ha='center', fontsize=18, color=_MUTED, style='italic')

plt.show()

# Console summary
print(f"\n    Total Spend Volume Analysis")
print(f"    {'='*50}")
print(f"    Period: {_first_mo} to {_last_mo} ({_n_months} months)")
print(f"    First month:  {_fmt_spend(spend[0])}")
print(f"    Last month:   {_fmt_spend(spend[-1])}")
print(f"    YoY change:   {_pct_change:+.1f}% ({_direction})")
print(f"    Total $ change: {_fmt_spend(spend[-1] - spend[0])}")
print(f"    Avg monthly:  {_fmt_spend(_avg_spend)}")
for t, _tf, _tl, _tp in _type_changes:
    print(f"      {t}: {_fmt_spend(_tf)} > {_fmt_spend(_tl)}  ({_tp:+.1f}%)")
