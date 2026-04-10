# ===========================================================================
# BRANCH SPEND PROFILE: Bracket Distribution by Branch (Conference Edition)
# ===========================================================================
# Grouped bar: spend bracket distribution for top 5 branches vs portfolio. (14,7).
# Depends on amount_bracket from general/06_bracket_data.

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping spend profile.")
else:
    try:
        top5_br_spend = br_agg.head(5)['branch'].tolist()

        br_bracket = pd.crosstab(
            br_df[br_df['branch'].isin(top5_br_spend)]['branch'],
            br_df[br_df['branch'].isin(top5_br_spend)]['amount_bracket'],
            normalize='index'
        ) * 100

        # Ensure bracket order
        bracket_order = ['< $1', '$1-5', '$5-10', '$10-25', '$25-50', '$50-100', '$100-500', '$500+']
        available_brackets = [b for b in bracket_order if b in br_bracket.columns]
        br_bracket = br_bracket[available_brackets]

        fig, ax = plt.subplots(figsize=(14, 7))

        n_branches = len(br_bracket)
        n_brackets = len(available_brackets)
        bar_width = 0.15
        x = np.arange(n_brackets)

        branch_colors = [GEN_COLORS['accent'], GEN_COLORS['primary'], GEN_COLORS['info'],
                          GEN_COLORS['success'], GEN_COLORS['warning']]

        for i, branch in enumerate(br_bracket.index):
            offset = (i - n_branches / 2 + 0.5) * bar_width
            ax.bar(x + offset, br_bracket.loc[branch], width=bar_width,
                   label=str(branch)[:15], color=branch_colors[i % len(branch_colors)],
                   edgecolor='white', linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(available_brackets, fontsize=11, fontweight='bold', rotation=45, ha='right')
        ax.set_ylabel("% of Branch Transactions", fontsize=16, fontweight='bold', labelpad=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        ax.set_title("Spend Bracket Distribution by Branch",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02, "Do branches differ in transaction size patterns?",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['muted'], style='italic')

        ax.legend(
            loc='upper center', bbox_to_anchor=(0.5, -0.18),
            ncol=5, fontsize=10, frameon=False, title='Branch',
            title_fontproperties={'weight': 'bold', 'size': 12}
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.22)
        plt.show()

    except NameError:
        print("    amount_bracket not available. Run general/06_bracket_data first.")
