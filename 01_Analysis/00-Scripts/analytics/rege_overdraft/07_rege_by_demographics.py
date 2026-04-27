# ===========================================================================
# REG E BY DEMOGRAPHICS: Opt-In Rate Across Segments
# ===========================================================================
# 3-panel view: opt-in rate by (1) age band, (2) balance band,
# (3) engagement tier. Identifies which segments are opting out most.

# ---------------------------------------------------------------------------
# Helper: compute opt-in rate for a grouping column
# ---------------------------------------------------------------------------
def _optin_by_group(df, group_col, order=None, palette=None):
    """Compute opt-in rate and count by a categorical grouping."""
    _grouped = df.groupby(group_col).agg(
        total=('account_number', 'nunique'),
        opted_in=('current_status', lambda x: (x == 'Opted-In').sum()),
    ).reset_index()
    _grouped['optin_pct'] = (_grouped['opted_in'] / _grouped['total'] * 100).fillna(0)

    if order:
        _cat_type = pd.CategoricalDtype(categories=order, ordered=True)
        _grouped[group_col] = _grouped[group_col].astype(_cat_type)
        _grouped = _grouped.sort_values(group_col).dropna(subset=[group_col])

    return _grouped

# ---------------------------------------------------------------------------
# Compute breakdowns
# ---------------------------------------------------------------------------
_has_age = 'age_band' in rege_df.columns
_has_bal = 'balance_band' in rege_df.columns
_has_engage = 'engage_tier' in rege_df.columns

_panels = []

if _has_age:
    _age_data = _optin_by_group(rege_df, 'age_band', order=AGE_ORDER, palette=AGE_PALETTE)
    _panels.append(('age_band', _age_data, AGE_PALETTE, AGE_ORDER, 'By Age Band'))

if _has_bal:
    _bal_order = ['Negative', '$0-500', '$500-2K', '$2K-5K', '$5K-10K', '$10K+']
    _bal_palette = {
        'Negative': GEN_COLORS['accent'],
        '$0-500': '#A8DADC',
        '$500-2K': '#457B9D',
        '$2K-5K': '#2EC4B6',
        '$5K-10K': '#FF9F1C',
        '$10K+': GEN_COLORS['primary'],
    }
    _bal_data = _optin_by_group(rege_df, 'balance_band', order=_bal_order, palette=_bal_palette)
    _panels.append(('balance_band', _bal_data, _bal_palette, _bal_order, 'By Balance Band'))

if _has_engage:
    _engage_data = _optin_by_group(rege_df, 'engage_tier', order=ENGAGE_ORDER, palette=ENGAGE_PALETTE)
    _panels.append(('engage_tier', _engage_data, ENGAGE_PALETTE, ENGAGE_ORDER, 'By Engagement Tier'))

# Fallback: if fewer than 3 panels, fill with product if available
if len(_panels) < 3 and 'Prod Desc' in rege_df.columns:
    _top_prods = rege_df['Prod Desc'].value_counts().head(8).index.tolist()
    _prod_df = rege_df[rege_df['Prod Desc'].isin(_top_prods)].copy()
    _prod_data = _optin_by_group(_prod_df, 'Prod Desc')
    _prod_data = _prod_data.sort_values('optin_pct', ascending=False)
    _prod_palette = {p: BRACKET_PALETTE[i % len(BRACKET_PALETTE)] for i, p in enumerate(_top_prods)}
    _panels.append(('Prod Desc', _prod_data, _prod_palette, _top_prods, 'By Product'))

_n_panels = min(len(_panels), 3)
if _n_panels == 0:
    print("    NOTE: No demographic columns available for breakdown")
else:
    # ---------------------------------------------------------------------------
    # Plot 3-panel (or fewer)
    # ---------------------------------------------------------------------------
    fig, axes = plt.subplots(1, _n_panels, figsize=(7 * _n_panels, 7))
    if _n_panels == 1:
        axes = [axes]

    for ax, (group_col, data, palette, order, title) in zip(axes, _panels[:3]):
        _x_pos = np.arange(len(data))
        _colors = [palette.get(str(v), GEN_COLORS['info']) for v in data[group_col]]

        bars = ax.bar(
            _x_pos, data['optin_pct'],
            color=_colors, edgecolor='white', linewidth=1.5
        )

        # Overall average line
        _overall_pct = (
            rege_df['current_status'] == 'Opted-In'
        ).sum() / len(rege_df) * 100 if len(rege_df) > 0 else 0
        ax.axhline(_overall_pct, color=GEN_COLORS['accent'], linewidth=2,
                   linestyle='--', alpha=0.7, label=f'Overall: {_overall_pct:.1f}%')

        # Data labels
        for bar, (_, row) in zip(bars, data.iterrows()):
            _height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2, _height + 1.5,
                f"{_height:.1f}%\n({int(row['total']):,})",
                ha='center', va='bottom', fontsize=11, fontweight='bold',
                color=GEN_COLORS['dark_text']
            )

        ax.set_xticks(_x_pos)
        ax.set_xticklabels(
            [str(v) for v in data[group_col]],
            rotation=30, ha='right', fontsize=12
        )
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
        ax.set_ylim(0, min(data['optin_pct'].max() + 20, 105))
        gen_clean_axes(ax)
        ax.set_title(title, fontsize=18, fontweight='bold', loc='left',
                     color=GEN_COLORS['dark_text'])
        ax.legend(loc='upper right', fontsize=10)

    fig.suptitle("Reg E Opt-In Rate by Demographics",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, 0.99,
             f"Which segments are opting out most? | {DATASET_LABEL}",
             fontsize=14, color=GEN_COLORS['muted'], style='italic',
             ha='center')

    plt.tight_layout()
    plt.show()

    # Insights
    for group_col, data, palette, order, title in _panels[:3]:
        if len(data) > 0:
            _lowest = data.loc[data['optin_pct'].idxmin()]
            _highest = data.loc[data['optin_pct'].idxmax()]
            print(f"\n    {title}:")
            print(f"      Highest opt-in: {_highest[group_col]} at "
                  f"{_highest['optin_pct']:.1f}% ({int(_highest['total']):,} accounts)")
            print(f"      Lowest opt-in:  {_lowest[group_col]} at "
                  f"{_lowest['optin_pct']:.1f}% ({int(_lowest['total']):,} accounts)")
