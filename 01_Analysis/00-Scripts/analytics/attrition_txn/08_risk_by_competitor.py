# ===========================================================================
# RISK BY COMPETITOR: Are Declining Members Going to Competitors?
# ===========================================================================
# Cross-reference declining accounts with competitor transaction activity.
# Only runs if competitor_category column exists in combined_df.

if 'competitor_category' not in combined_df.columns:
    print("    No competitor_category column in combined_df -- skipping competitor analysis.")
    print("    To enable this chart, add competitor classification to transaction data.")
else:
    # ---------------------------------------------------------------------------
    # Identify declining/dormant accounts with competitor activity
    # ---------------------------------------------------------------------------
    _at_risk_accts = set(
        attrition_df[attrition_df['risk_tier'].isin(['Declining', 'Dormant'])]['account_number']
    )

    # Find accounts with competitor transactions
    _comp_txns = combined_df[combined_df['competitor_category'].notna()].copy()
    _accts_with_comp = set(_comp_txns['primary_account_num'].unique())

    # Cross-reference
    _at_risk_with_comp = _at_risk_accts & _accts_with_comp
    _at_risk_no_comp = _at_risk_accts - _accts_with_comp

    _comp_data = pd.DataFrame([
        {'Category': 'With Competitor Activity',
         'Count': len(_at_risk_with_comp),
         'Pct': len(_at_risk_with_comp) / len(_at_risk_accts) * 100 if _at_risk_accts else 0},
        {'Category': 'No Competitor Activity',
         'Count': len(_at_risk_no_comp),
         'Pct': len(_at_risk_no_comp) / len(_at_risk_accts) * 100 if _at_risk_accts else 0},
    ])

    # ---------------------------------------------------------------------------
    # Bar chart: competitor presence among at-risk accounts
    # ---------------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7),
                                    gridspec_kw={'width_ratios': [1, 1.3]})

    # Left panel: With vs Without competitor activity
    _bar_colors = [GEN_COLORS['accent'], GEN_COLORS['muted']]
    bars = ax1.barh(
        _comp_data['Category'], _comp_data['Count'],
        color=_bar_colors, edgecolor='white', linewidth=1.5, height=0.5
    )
    ax1.invert_yaxis()

    for bar, row in zip(bars, _comp_data.itertuples()):
        width = bar.get_width()
        ax1.text(width + (_comp_data['Count'].max() * 0.02),
                 bar.get_y() + bar.get_height() / 2,
                 f"{width:,.0f} ({row.Pct:.1f}%)",
                 va='center', fontsize=13, fontweight='bold',
                 color=GEN_COLORS['dark_text'])

    ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.set_title("At-Risk Accounts", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=15, loc='left')

    # Right panel: Top competitor categories among at-risk accounts
    _comp_at_risk_txns = _comp_txns[
        _comp_txns['primary_account_num'].isin(_at_risk_with_comp)
    ]
    if len(_comp_at_risk_txns) > 0:
        _top_comp = (
            _comp_at_risk_txns.groupby('competitor_category')
            .agg(
                txn_count=('transaction_date', 'count'),
                unique_accts=('primary_account_num', 'nunique'),
            )
            .sort_values('txn_count', ascending=False)
            .head(10)
            .reset_index()
        )

        y_pos = range(len(_top_comp))
        bars2 = ax2.barh(
            y_pos, _top_comp['txn_count'],
            color=GEN_COLORS['accent'], alpha=0.7,
            edgecolor='white', linewidth=1.5, height=0.6
        )
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(_top_comp['competitor_category'], fontsize=12, fontweight='bold')
        ax2.invert_yaxis()

        for bar, row in zip(bars2, _top_comp.itertuples()):
            width = bar.get_width()
            ax2.text(width + (_top_comp['txn_count'].max() * 0.02),
                     bar.get_y() + bar.get_height() / 2,
                     f"{width:,.0f} txns ({row.unique_accts:,} accts)",
                     va='center', fontsize=11, fontweight='bold',
                     color=GEN_COLORS['dark_text'])

        ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
        gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
        ax2.set_title("Top Competitor Categories (At-Risk Only)",
                      fontsize=18, fontweight='bold',
                      color=GEN_COLORS['dark_text'], pad=15, loc='left')
    else:
        ax2.text(0.5, 0.5, "No competitor transactions found",
                 transform=ax2.transAxes, ha='center', va='center',
                 fontsize=14, color=GEN_COLORS['muted'])
        gen_clean_axes(ax2)

    fig.suptitle("Competitor Activity Among Declining Members",
                 fontsize=24, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, 0.99,
             f"Are at-risk members switching or just spending less? | {DATASET_LABEL}",
             fontsize=14, color=GEN_COLORS['muted'], style='italic', ha='center')

    plt.tight_layout()
    plt.show()

    # Callout
    _comp_pct = len(_at_risk_with_comp) / len(_at_risk_accts) * 100 if _at_risk_accts else 0
    print(f"\n    INSIGHT: {_comp_pct:.1f}% of at-risk accounts show competitor activity")
    print(f"    INSIGHT: {len(_at_risk_no_comp):,} accounts are declining WITHOUT "
          f"competitor usage (disengagement, not switching)")
