# ===========================================================================
# AGE SPENDING PROFILE: Top MCC Categories by Age Band (Conference Edition)
# ===========================================================================
# Horizontal grouped bar: top 10 MCC categories by age band (% of txns). (14,8).

age_matched_local = demo_df[demo_df['age_band'].notna()].copy()

# Get top 10 MCC codes overall
top10_mcc = (
    age_matched_local.groupby('mcc_code').size()
    .sort_values(ascending=False).head(10).index.tolist()
)

# Build cross-tab: age band x MCC (percentage within each age band)
mcc_age_data = age_matched_local[age_matched_local['mcc_code'].isin(top10_mcc)]
crosstab = pd.crosstab(mcc_age_data['mcc_code'], mcc_age_data['age_band'], normalize='columns') * 100

# Reorder columns to age order
crosstab = crosstab[[b for b in AGE_ORDER if b in crosstab.columns]]

if len(crosstab.columns) == 0 or len(crosstab) == 0:
    print("    No age band / MCC cross-tab data available. Skipping age spending profile.")
else:
    # Sort by overall frequency
    mcc_order = (
        mcc_age_data.groupby('mcc_code').size()
        .sort_values(ascending=True).index.tolist()
    )
    mcc_order = [m for m in mcc_order if m in crosstab.index]
    crosstab = crosstab.reindex(mcc_order)

    fig, ax = plt.subplots(figsize=(16, 9))

    n_bands = len(crosstab.columns)
    n_mcc = len(crosstab)
    bar_height = 0.8 / n_bands
    y_base = np.arange(n_mcc)

    for i, band in enumerate(crosstab.columns):
        offset = (i - n_bands / 2 + 0.5) * bar_height
        bars = ax.barh(
            y_base + offset, crosstab[band],
            height=bar_height, color=AGE_PALETTE.get(band, GEN_COLORS['muted']),
            label=band, edgecolor='white', linewidth=0.5
        )

    ax.set_yticks(y_base)
    ax.set_yticklabels(crosstab.index, fontsize=15, fontweight='bold')
    ax.set_xlabel("% of Age Band's Transactions", fontsize=18, fontweight='bold', labelpad=10)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("Where Each Generation Spends",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Top 10 merchant categories by age band share",
            transform=ax.transAxes, fontsize=16,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.08),
        ncol=6, fontsize=15, frameon=False, title='Age Band',
        title_fontproperties={'weight': 'bold', 'size': 16}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.show()
