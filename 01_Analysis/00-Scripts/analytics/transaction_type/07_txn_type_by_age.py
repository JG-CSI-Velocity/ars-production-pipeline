# ===========================================================================
# TXN TYPE BY AGE: PIN vs SIG Preference by Age Band (Conference Edition)
# ===========================================================================
# Grouped bar: PIN vs SIG share by age band. (14,7).
# Depends on demo_df from general/11_demographic_data.

try:
    tt_age = pd.crosstab(
        demo_df['age_band'],
        demo_df['transaction_type'],
        normalize='index'
    ) * 100

    # Ensure age band order
    available_ages = [a for a in AGE_ORDER if a in tt_age.index]
    tt_age = tt_age.loc[available_ages]

    fig, ax = plt.subplots(figsize=(14, 7))

    n_types = min(len(tt_age.columns), 4)
    bar_width = 0.7 / n_types
    x = np.arange(len(tt_age))

    type_colors = {
        'PIN': GEN_COLORS['success'],
        'SIG': GEN_COLORS['warning'],
    }
    other_idx = 0
    other_colors = [GEN_COLORS['info'], GEN_COLORS['muted']]

    plot_cols = ['PIN', 'SIG'] if 'PIN' in tt_age.columns and 'SIG' in tt_age.columns else tt_age.columns[:4]

    for i, col in enumerate(plot_cols):
        if col not in tt_age.columns:
            continue
        offset = (i - len(plot_cols) / 2 + 0.5) * bar_width
        if col in type_colors:
            color = type_colors[col]
        else:
            color = other_colors[other_idx % len(other_colors)]
            other_idx += 1
        bars = ax.bar(x + offset, tt_age[col], width=bar_width,
                      label=col, color=color, edgecolor='white', linewidth=0.5)

        # Value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 3:
                ax.text(bar.get_x() + bar.get_width() / 2, height + 0.8,
                        f"{height:.0f}%", ha='center', va='bottom',
                        fontsize=9, fontweight='bold', color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(available_ages, fontsize=13, fontweight='bold')
    ax.set_ylabel("% of Age Band Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("PIN vs Signature by Age Band",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Do younger members prefer PIN while older members use signature?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.08),
        ncol=5, fontsize=12, frameon=False, title='Transaction Type',
        title_fontproperties={'weight': 'bold', 'size': 13}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.show()

except NameError:
    print("    demo_df not available. Run general/11_demographic_data first.")
