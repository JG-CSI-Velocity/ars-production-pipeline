# ===========================================================================
# TXN TYPE BY BRACKET: PIN vs SIG by Spend Amount (Conference Edition)
# ===========================================================================
# Stacked bar: PIN vs SIG mix by spend bracket. (14,7).
# Depends on amount_bracket from general/06_bracket_data.

try:
    tt_bracket = pd.crosstab(
        combined_df['amount_bracket'],
        combined_df['transaction_type'],
        normalize='index'
    ) * 100

    # Ensure bracket order
    bracket_order = ['< $1', '$1-5', '$5-10', '$10-25', '$25-50', '$50-100', '$100-500', '$500+']
    available_brackets = [b for b in bracket_order if b in tt_bracket.index]
    tt_bracket = tt_bracket.loc[available_brackets]

    fig, ax = plt.subplots(figsize=(14, 7))

    x = range(len(tt_bracket))
    bar_width = 0.6
    bottom = np.zeros(len(tt_bracket))

    type_colors = {
        'PIN': GEN_COLORS['success'],
        'SIG': GEN_COLORS['warning'],
    }
    other_idx = 0
    other_colors = [GEN_COLORS['info'], GEN_COLORS['muted'], GEN_COLORS['accent']]

    for col in tt_bracket.columns:
        if col in type_colors:
            color = type_colors[col]
        else:
            color = other_colors[other_idx % len(other_colors)]
            other_idx += 1
        ax.bar(x, tt_bracket[col], bottom=bottom, width=bar_width,
               label=col, color=color, edgecolor='white', linewidth=0.5)
        bottom += tt_bracket[col].values

    ax.set_xticks(x)
    ax.set_xticklabels(available_brackets, fontsize=12, fontweight='bold', rotation=45, ha='right')
    ax.set_ylabel("% of Bracket Transactions", fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax.set_ylim(0, 105)

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("PIN vs Signature by Spend Amount",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Do larger transactions route differently than small ones?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.18),
        ncol=5, fontsize=12, frameon=False, title='Transaction Type',
        title_fontproperties={'weight': 'bold', 'size': 13}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.22)
    plt.show()

except NameError:
    print("    amount_bracket not available. Run general/06_bracket_data first.")
