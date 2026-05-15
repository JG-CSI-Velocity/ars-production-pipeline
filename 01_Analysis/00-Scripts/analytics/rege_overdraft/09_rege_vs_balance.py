# ===========================================================================
# REG E vs BALANCE: Opt-In Status Across Balance Bands
# ===========================================================================
# Grouped bar + risk matrix: Low-balance + opted-out = no safety net AND no
# fee revenue. High-balance + opted-in = rarely triggers OD anyway.

# ---------------------------------------------------------------------------
# Prepare balance band x Reg E status cross-tabulation
# ---------------------------------------------------------------------------
_bal_col = 'balance_band' if 'balance_band' in rege_df.columns else None
_bal_order = ['Negative', '$0-500', '$500-2K', '$2K-5K', '$5K-10K', '$10K+']

if _bal_col is None and 'Avg Bal' in rege_df.columns:
    rege_df['balance_band'] = pd.cut(
        pd.to_numeric(rege_df['Avg Bal'], errors='coerce'),
        bins=[-999999, 0, 500, 2000, 5000, 10000, 999999999],
        labels=_bal_order,
        right=True
    ).astype(str).replace('nan', 'Unknown')
    _bal_col = 'balance_band'

if _bal_col and _bal_col in rege_df.columns:
    # Cross-tabulation
    _cross = pd.crosstab(
        rege_df[_bal_col],
        rege_df['current_status'],
        margins=False
    )

    # Reindex to consistent order
    _active_statuses = [s for s in REGE_STATUS_ORDER if s in _cross.columns]
    _active_bands = [b for b in _bal_order if b in _cross.index]
    _cross = _cross.reindex(index=_active_bands, columns=_active_statuses, fill_value=0)

    # Percentage within each balance band
    _cross_pct = _cross.div(_cross.sum(axis=1), axis=0) * 100

    # ---------------------------------------------------------------------------
    # Plot 1: Grouped bar chart - opt-in rate by balance band
    # ---------------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw={'width_ratios': [1.2, 1]})

    _x_pos = np.arange(len(_active_bands))
    _n_statuses = len(_active_statuses)
    _bar_width = 0.8 / _n_statuses

    for i, status in enumerate(_active_statuses):
        _offset = (i - _n_statuses / 2 + 0.5) * _bar_width
        _vals = _cross_pct[status].values
        _color = REGE_STATUS_PALETTE.get(status, GEN_COLORS['muted'])
        bars = ax1.bar(
            _x_pos + _offset, _vals,
            width=_bar_width, color=_color, edgecolor='white',
            linewidth=1, label=status, alpha=0.85
        )

        # Labels on opted-in bars only (to reduce clutter)
        if status == 'Opted-In':
            for bar, val in zip(bars, _vals):
                if val > 0:
                    ax1.text(
                        bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f"{val:.0f}%",
                        ha='center', va='bottom', fontsize=10, fontweight='bold',
                        color=GEN_COLORS['dark_text']
                    )

    ax1.set_xticks(_x_pos)
    ax1.set_xticklabels(_active_bands, rotation=30, ha='right', fontsize=12)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
    ax1.set_ylim(0, 105)
    gen_clean_axes(ax1)
    ax1.legend(loc='upper right', fontsize=11)
    ax1.set_title("Reg E Status Mix by Balance Band", fontsize=18,
                  fontweight='bold', loc='left', color=GEN_COLORS['dark_text'])
    ax1.set_ylabel("Share of Accounts (%)", fontsize=14, fontweight='bold')

    # ---------------------------------------------------------------------------
    # Plot 2: Risk-Opportunity Matrix (heatmap)
    # ---------------------------------------------------------------------------
    # Build a 2x2-ish matrix: Balance (Low/High) x Status (In/Out)
    _risk_data = rege_df.copy()
    _risk_data['bal_group'] = 'Higher Balance'
    if 'Avg Bal' in _risk_data.columns:
        _median_bal = pd.to_numeric(_risk_data['Avg Bal'], errors='coerce').median()
        _risk_data.loc[
            pd.to_numeric(_risk_data['Avg Bal'], errors='coerce') < _median_bal,
            'bal_group'
        ] = 'Lower Balance'

    _risk_data['status_group'] = _risk_data['current_status'].apply(
        lambda x: 'Opted-In' if x == 'Opted-In' else 'Not Opted-In'
    )

    _risk_matrix = pd.crosstab(
        _risk_data['bal_group'],
        _risk_data['status_group']
    ).reindex(
        index=['Lower Balance', 'Higher Balance'],
        columns=['Opted-In', 'Not Opted-In'],
        fill_value=0
    )

    # Annotations describing the risk/opportunity
    _cell_labels = {
        ('Lower Balance', 'Opted-In'): 'Revenue Driver\n(OD likely, fees apply)',
        ('Lower Balance', 'Not Opted-In'): 'Risk Zone\n(No safety net, no revenue)',
        ('Higher Balance', 'Opted-In'): 'Low Impact\n(OD unlikely)',
        ('Higher Balance', 'Not Opted-In'): 'Low Priority\n(OD unlikely anyway)',
    }

    _risk_cmap = LinearSegmentedColormap.from_list(
        'risk', ['#FFFFFF', GEN_COLORS['warning'], GEN_COLORS['accent']]
    )

    sns.heatmap(
        _risk_matrix, annot=False, cmap=_risk_cmap,
        linewidths=3, linecolor='white', square=True,
        cbar_kws={'label': 'Account Count', 'shrink': 0.8},
        ax=ax2
    )

    for i, bal in enumerate(['Lower Balance', 'Higher Balance']):
        for j, status in enumerate(['Opted-In', 'Not Opted-In']):
            count = _risk_matrix.iloc[i, j]
            label = _cell_labels.get((bal, status), '')
            _text_color = 'white' if count > (_risk_matrix.values.max() * 0.5) else GEN_COLORS['dark_text']
            ax2.text(
                j + 0.5, i + 0.5,
                f"{count:,}\n\n{label}",
                ha='center', va='center',
                fontsize=11, fontweight='bold',
                color=_text_color, linespacing=1.3
            )

    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=0, fontsize=13)
    ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0, fontsize=13)
    ax2.set_title("Balance x Opt-In Risk Matrix", fontsize=18,
                  fontweight='bold', loc='left', color=GEN_COLORS['dark_text'])

    fig.suptitle("Reg E Opt-In vs Account Balance",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, 0.99,
             f"Where does opt-in status matter most? | {DATASET_LABEL}",
             fontsize=14, color=GEN_COLORS['muted'], style='italic',
             ha='center')

    plt.tight_layout()
    plt.show()

    # Insights
    _low_out = _risk_matrix.loc['Lower Balance', 'Not Opted-In'] if 'Not Opted-In' in _risk_matrix.columns else 0
    _low_in = _risk_matrix.loc['Lower Balance', 'Opted-In'] if 'Opted-In' in _risk_matrix.columns else 0
    _high_in = _risk_matrix.loc['Higher Balance', 'Opted-In'] if 'Opted-In' in _risk_matrix.columns else 0

    print(f"\n    INSIGHT: {_low_out:,} lower-balance accounts are NOT opted in "
          f"(no safety net, no fee revenue)")
    print(f"    INSIGHT: {_low_in:,} lower-balance accounts ARE opted in "
          f"(primary revenue driver for OD fees)")
    print(f"    INSIGHT: {_high_in:,} higher-balance accounts are opted in "
          f"(OD unlikely to trigger)")
else:
    print("    NOTE: No balance data available for Reg E vs balance analysis")
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.text(0.5, 0.5, "Balance data not available for this analysis",
            transform=ax.transAxes, fontsize=18, ha='center', va='center',
            color=GEN_COLORS['muted'])
    ax.axis('off')
    ax.set_title("Reg E Opt-In vs Account Balance",
                 fontsize=26, fontweight='bold', loc='left',
                 color=GEN_COLORS['dark_text'])
    plt.show()
