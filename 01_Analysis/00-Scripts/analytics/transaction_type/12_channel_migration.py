# ===========================================================================
# CHANNEL MIGRATION: CHK to ACH Shift Over Time
# ===========================================================================
# Single chart showing ACH spend share rising while CHK share declines.
# The crossover (if visible) is the visual story.
#
# Depends on: tt_monthly (cell 01)

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')
_ACH_COLOR = GEN_COLORS.get('info', '#457B9D')
_CHK_COLOR = GEN_COLORS.get('accent', '#E63946')

_has_ach = 'ACH' in tt_monthly['transaction_type'].values
_has_chk = 'CHK' in tt_monthly['transaction_type'].values

if not _has_ach and not _has_chk:
    print("    No ACH or CHK data in monthly trends. Skipping.")
else:
    fig, ax = plt.subplots(figsize=(18, 8))
    fig.subplots_adjust(top=0.85, bottom=0.15)

    _types_to_plot = []
    if _has_ach:
        _types_to_plot.append(('ACH', _ACH_COLOR, '-', 'o'))
    if _has_chk:
        _types_to_plot.append(('CHK', _CHK_COLOR, '-', 's'))

    def _period_to_dates(s):
        """Convert a year_month Series (Period or string) to datetime."""
        try:
            if hasattr(s.dtype, 'freq'):
                return s.dt.to_timestamp()
        except Exception:
            pass
        try:
            return pd.PeriodIndex(s).to_timestamp()
        except Exception:
            return pd.to_datetime(s.astype(str))

    for t, color, ls, marker in _types_to_plot:
        _data = tt_monthly[tt_monthly['transaction_type'] == t].sort_values('year_month')
        dates = _period_to_dates(_data['year_month'])
        vals = _data['spend_share_pct'].values

        ax.plot(dates, vals, color=color, linewidth=3, marker=marker,
                markersize=6, markeredgecolor='white', markeredgewidth=1.5,
                zorder=4, label=t)

        # Start/end labels
        if len(vals) > 0:
            ax.text(dates.iloc[0], vals[0], f' {vals[0]:.1f}%',
                    ha='right', va='center', fontsize=15, fontweight='bold', color=color)
            ax.text(dates.iloc[-1], vals[-1], f' {vals[-1]:.1f}%',
                    ha='left', va='center', fontsize=15, fontweight='bold', color=color)

            # Direction arrow in legend
            _chg = vals[-1] - vals[0]
            _arrow = '^' if _chg > 0 else 'v' if _chg < 0 else '-'

    # Combined non-debit share
    _non_debit = tt_monthly[tt_monthly['transaction_type'].isin(['ACH', 'CHK'])].copy()
    if len(_non_debit) > 0:
        _combined = _non_debit.groupby('year_month')['spend_share_pct'].sum().sort_index()
        try:
            _combined_dates = _combined.index.to_timestamp()
        except Exception:
            _combined_dates = pd.to_datetime(_combined.index.astype(str))
        ax.plot(_combined_dates, _combined.values, color=_MUTED, linewidth=2,
                linestyle=':', alpha=0.6, zorder=3, label='ACH + CHK Combined')
        ax.text(_combined_dates[-1], _combined.values[-1],
                f' {_combined.values[-1]:.1f}%',
                ha='left', va='center', fontsize=14, fontweight='bold', color=_MUTED)

    # Debit share reference line
    _debit = tt_monthly[tt_monthly['transaction_type'].isin(['PIN', 'SIG'])].copy()
    if len(_debit) > 0:
        _debit_share = _debit.groupby('year_month')['spend_share_pct'].sum().sort_index()
        try:
            _debit_dates = _debit_share.index.to_timestamp()
        except Exception:
            _debit_dates = pd.to_datetime(_debit_share.index.astype(str))
        ax.fill_between(_debit_dates, _debit_share.values, alpha=0.05,
                        color=GEN_COLORS.get('success', '#2A9D8F'))

    ax.set_ylabel('% of Total Spend', fontsize=16, fontweight='bold', labelpad=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    ax.tick_params(axis='x', rotation=0, labelsize=14)
    ax.legend(fontsize=14, framealpha=0.9, loc='best',
              title='Payment Channel',
              title_fontproperties={'weight': 'bold', 'size': 15})
    ax.set_title('Payment Channel Share of Spend Over Time',
                 fontsize=20, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    fig.suptitle('Channel Migration: Checks vs Electronic Payments',
                 fontsize=28, fontweight='bold', color=_DARK, y=0.95)
    fig.text(0.5, 0.905,
             'Are accounts shifting from checks to electronic (ACH) payments?',
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.show()

    # Console
    print(f"\n    CHANNEL MIGRATION")
    print(f"    {'='*50}")
    for t, color, ls, marker in _types_to_plot:
        _data = tt_monthly[tt_monthly['transaction_type'] == t].sort_values('year_month')
        _first = _data['spend_share_pct'].iloc[0]
        _last = _data['spend_share_pct'].iloc[-1]
        _chg = _last - _first
        print(f"    {t}: {_first:.1f}% -> {_last:.1f}%  ({_chg:+.1f}pp)")
