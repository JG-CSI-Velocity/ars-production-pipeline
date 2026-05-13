# ===========================================================================
# MONTHLY PROGRESSION: 17-Month Spend by Risk Tier (Conference Edition)
# ===========================================================================
# Line chart showing when decline started for each risk group.
# Uses monthly_spend_ts built in cell 01.

if len(monthly_spend_ts) == 0:
    print("    No monthly spend time series available -- skipping chart.")
else:
    # ---------------------------------------------------------------------------
    # Aggregate monthly spend by risk tier
    # ---------------------------------------------------------------------------
    _tier_monthly = (
        monthly_spend_ts
        .groupby(['month_label', 'risk_tier'])['spend']
        .mean()
        .reset_index()
    )

    # Get ordered month labels from the data. Filter out any aggregate
    # labels (``Total'', ``YTD'', ``Avg'') that can creep in from upstream
    # rollups -- they crash pd.to_datetime(format='%b%y').
    _month_order = [
        m for m in monthly_spend_ts['month_label'].unique()
        if isinstance(m, str) and m not in ('Total', 'YTD', 'Avg', 'Average', 'All')
    ]
    # Sort chronologically by parsing MmmYY format. Skip any label that
    # doesn't parse instead of crashing the whole script.
    def _safe_parse_month(label):
        try:
            return pd.to_datetime(label, format='%b%y')
        except (ValueError, TypeError):
            return pd.Timestamp.max
    _month_sort = sorted(_month_order, key=_safe_parse_month)
    # Drop any label that didn't parse (got Timestamp.max) so the x-axis
    # doesn't show an unsortable bucket at the far right.
    _month_sort = [m for m in _month_sort if _safe_parse_month(m) != pd.Timestamp.max]
    _tier_monthly['month_label'] = pd.Categorical(
        _tier_monthly['month_label'], categories=_month_sort, ordered=True
    )
    _tier_monthly = _tier_monthly.sort_values('month_label')

    # ---------------------------------------------------------------------------
    # Line chart: one line per risk tier
    # ---------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(16, 8))

    for tier in RISK_ORDER:
        tier_data = _tier_monthly[_tier_monthly['risk_tier'] == tier]
        if len(tier_data) == 0:
            continue
        ax.plot(
            tier_data['month_label'].astype(str),
            tier_data['spend'],
            color=RISK_PALETTE[tier],
            linewidth=3,
            marker='o',
            markersize=5,
            label=tier,
            alpha=0.9,
        )

    # Rotate x-labels for readability
    ax.set_xticks(range(len(_month_sort)))
    ax.set_xticklabels([str(m) for m in _month_sort], rotation=45, ha='right', fontsize=12)

    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_xlabel("Month", fontsize=16, fontweight='bold', labelpad=10)
    ax.set_ylabel("Avg Monthly Spend per Account", fontsize=16, fontweight='bold', labelpad=10)

    ax.legend(title="Risk Tier", fontsize=12, title_fontsize=13,
              loc='upper right', frameon=True, framealpha=0.9,
              edgecolor=GEN_COLORS['grid'])

    ax.set_title("Monthly Spend Progression by Risk Tier",
                 fontsize=24, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, f"When did declining accounts start to fall? | {DATASET_LABEL}",
            transform=ax.transAxes, fontsize=14,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()

    # Callout: compare first vs last month for declining tier
    _declining_ts = _tier_monthly[_tier_monthly['risk_tier'] == 'Declining']
    if len(_declining_ts) >= 2:
        _first_val = _declining_ts.iloc[0]['spend']
        _last_val = _declining_ts.iloc[-1]['spend']
        _drop_pct = ((_last_val - _first_val) / _first_val * 100) if _first_val > 0 else 0
        print(f"\n    INSIGHT: Declining accounts dropped {abs(_drop_pct):.0f}% in avg monthly "
              f"spend over the observation period")
        print(f"    INSIGHT: Avg spend fell from {gen_fmt_dollar(_first_val, None)} "
              f"to {gen_fmt_dollar(_last_val, None)} per month")
