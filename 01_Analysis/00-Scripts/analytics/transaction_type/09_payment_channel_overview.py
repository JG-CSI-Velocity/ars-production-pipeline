# ===========================================================================
# PAYMENT CHANNEL OVERVIEW: Beyond Debit — The Full Payment Picture
# ===========================================================================
# ARS measures debit (PIN/SIG) impact. But debit is only part of the story.
# This chart sizes the full portfolio: PIN + SIG + ACH + CHK.
#
# Row 1: 4 KPI cards (Debit Share, ACH Volume, CHK Volume, Non-Debit Total)
# Row 2: Horizontal 100% stacked bar showing volume by type
#
# Depends on: tt_agg (cell 01)

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')

_type_colors = {
    'SIG': GEN_COLORS.get('warning', '#E9C46A'),
    'PIN': GEN_COLORS.get('success', '#2A9D8F'),
    'ACH': GEN_COLORS.get('info', '#457B9D'),
    'CHK': GEN_COLORS.get('accent', '#E63946'),
}

# Check for non-debit types
_non_debit = tt_agg[~tt_agg['transaction_type'].isin(['PIN', 'SIG'])]

if len(_non_debit) == 0:
    print("    No ACH/CHK transaction types found. Portfolio is debit-only.")
else:
    _total_spend = tt_agg['total_spend'].sum()
    _total_txns = tt_agg['txn_count'].sum()

    _debit_spend = tt_agg[tt_agg['transaction_type'].isin(['PIN', 'SIG'])]['total_spend'].sum()
    _ach_spend = tt_agg[tt_agg['transaction_type'] == 'ACH']['total_spend'].sum()
    _chk_spend = tt_agg[tt_agg['transaction_type'] == 'CHK']['total_spend'].sum()
    _non_debit_spend = _total_spend - _debit_spend

    _debit_pct = _debit_spend / _total_spend * 100 if _total_spend > 0 else 0
    _ach_pct = _ach_spend / _total_spend * 100 if _total_spend > 0 else 0
    _chk_pct = _chk_spend / _total_spend * 100 if _total_spend > 0 else 0

    # Build figure
    fig = plt.figure(figsize=(26, 14))
    gs = fig.add_gridspec(2, 1, height_ratios=[0.7, 1.2], hspace=0.25,
                          top=0.86, bottom=0.06, left=0.04, right=0.96)

    # =================================================================
    # ROW 1: KPI Cards
    # =================================================================
    gs_cards = gs[0].subgridspec(1, 4, wspace=0.15)

    def _fmt_vol(v):
        if v >= 1e6:
            return f"${v/1e6:,.1f}M"
        return f"${v/1e3:,.0f}K"

    kpi_data = [
        {
            'label': 'Debit Card Share',
            'value': f"{_debit_pct:.1f}%",
            'sub': f'{_fmt_vol(_debit_spend)} in PIN + SIG',
            'color': GEN_COLORS.get('success', '#2A9D8F'),
        },
        {
            'label': 'ACH Volume',
            'value': _fmt_vol(_ach_spend),
            'sub': f'{_ach_pct:.1f}% of total payments',
            'color': GEN_COLORS.get('info', '#457B9D'),
        },
        {
            'label': 'Check Volume',
            'value': _fmt_vol(_chk_spend),
            'sub': f'{_chk_pct:.1f}% of total payments',
            'color': GEN_COLORS.get('accent', '#E63946'),
        },
        {
            'label': 'Beyond ARS Scope',
            'value': _fmt_vol(_non_debit_spend),
            'sub': 'ACH + CHK combined',
            'color': _DARK,
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
            facecolor=kpi['color'], edgecolor='white', linewidth=3
        )
        ax.add_patch(card)

        ax.text(5, 7.5, kpi['label'],
                ha='center', va='center', fontsize=20, fontweight='bold',
                color='white', alpha=0.85)
        ax.text(5, 5.0, kpi['value'],
                ha='center', va='center', fontsize=52, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.5, kpi['sub'],
                ha='center', va='center', fontsize=16,
                color='white', alpha=0.8, style='italic')
        ax.text(5, 1.2, DATASET_LABEL,
                ha='center', va='center', fontsize=14,
                color='white', alpha=0.6)

    # =================================================================
    # ROW 2: Horizontal Stacked Bar (100% of spend)
    # =================================================================
    ax_bar = fig.add_subplot(gs[1])

    # Order: PIN, SIG, ACH, CHK (debit first, then non-debit)
    _order = [t for t in ['PIN', 'SIG', 'ACH', 'CHK'] if t in tt_agg['transaction_type'].values]
    _extra = [t for t in tt_agg['transaction_type'].values if t not in _order]
    _order = _order + sorted(_extra)

    _left = 0
    for t in _order:
        _row = tt_agg[tt_agg['transaction_type'] == t]
        _spend = _row['total_spend'].values[0]
        _pct = _spend / _total_spend * 100
        _color = _type_colors.get(t, _MUTED)

        ax_bar.barh(0, _pct, left=_left, height=0.5,
                    color=_color, edgecolor='white', linewidth=2,
                    label=f'{t} ({_pct:.1f}%)')

        # Label inside bar if wide enough
        if _pct > 5:
            ax_bar.text(_left + _pct / 2, 0,
                        f'{t}\n{_fmt_vol(_spend)}\n({_pct:.1f}%)',
                        ha='center', va='center', fontsize=24,
                        fontweight='bold', color='white')
        elif _pct > 2:
            ax_bar.text(_left + _pct / 2, 0,
                        f'{t}\n{_pct:.1f}%',
                        ha='center', va='center', fontsize=18,
                        fontweight='bold', color='white')

        _left += _pct

    # Divider line between debit and non-debit
    ax_bar.axvline(_debit_pct, color=_DARK, linewidth=2, linestyle='--', alpha=0.6, zorder=5)
    ax_bar.text(_debit_pct, 0.35, '  ARS scope', fontsize=18, fontweight='bold',
                color=_DARK, va='bottom', ha='left')
    ax_bar.text(_debit_pct, -0.35, '  Beyond ARS  ', fontsize=18, fontweight='bold',
                color=_MUTED, va='top', ha='left')

    ax_bar.set_xlim(0, 100)
    ax_bar.set_ylim(-0.6, 0.6)
    ax_bar.set_yticks([])
    ax_bar.set_xlabel('% of Total Payment Volume', fontsize=20, fontweight='bold', labelpad=8)
    ax_bar.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax_bar.tick_params(axis='x', labelsize=16)
    ax_bar.set_title('Payment Volume by Transaction Type',
                     fontsize=24, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax_bar, keep_bottom=True)

    ax_bar.legend(fontsize=16, framealpha=0.9, loc='upper right',
                  title='Transaction Type',
                  title_fontproperties={'weight': 'bold', 'size': 18})

    fig.suptitle('Beyond Debit: The Full Payment Picture',
                 fontsize=32, fontweight='bold', color=_DARK, y=0.96)
    fig.text(0.5, 0.91,
             'ARS activates debit card usage, but debit is only part of total payment volume',
             ha='center', fontsize=18, color=_MUTED, style='italic')

    plt.show()

    # Console summary
    print(f"\n    PAYMENT CHANNEL OVERVIEW")
    print(f"    {'='*50}")
    print(f"    Total payment volume: {_fmt_vol(_total_spend)}")
    print(f"    Debit (PIN+SIG):      {_fmt_vol(_debit_spend)} ({_debit_pct:.1f}%)")
    print(f"    ACH:                  {_fmt_vol(_ach_spend)} ({_ach_pct:.1f}%)")
    print(f"    CHK:                  {_fmt_vol(_chk_spend)} ({_chk_pct:.1f}%)")
    print(f"    Non-debit total:      {_fmt_vol(_non_debit_spend)} ({100-_debit_pct:.1f}%)")
