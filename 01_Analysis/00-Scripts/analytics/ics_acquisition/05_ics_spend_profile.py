# ===========================================================================
# ICS SPEND PROFILE: Bracket Distribution by Channel (Conference Edition)
# ===========================================================================
# Grouped bar: spend bracket distribution by ICS channel. (14,7).
# Depends on amount_bracket from general/06_bracket_data.

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping spend profile.")
else:
    try:
        ics_bracket = pd.crosstab(
            ics_merged['ics_account'],
            ics_merged['amount_bracket'],
            normalize='index'
        ) * 100

        bracket_order = ['< $1', '$1-5', '$5-10', '$10-25', '$25-50', '$50-100', '$100-500', '$500+']
        available_brackets = [b for b in bracket_order if b in ics_bracket.columns]
        ics_bracket = ics_bracket[available_brackets]

        # Order channels
        channel_order = [c for c in ['REF', 'DM', 'Non-ICS'] if c in ics_bracket.index]
        ics_bracket = ics_bracket.loc[channel_order]

        fig, ax = plt.subplots(figsize=(14, 7))

        n_channels = len(ics_bracket)
        n_brackets = len(available_brackets)
        bar_width = 0.25
        x = np.arange(n_brackets)

        channel_colors = {
            'REF': GEN_COLORS['info'],
            'DM': GEN_COLORS['primary'],
            'Non-ICS': GEN_COLORS['muted'],
        }

        for i, channel in enumerate(ics_bracket.index):
            offset = (i - n_channels / 2 + 0.5) * bar_width
            ax.bar(x + offset, ics_bracket.loc[channel], width=bar_width,
                   label=channel, color=channel_colors.get(channel, GEN_COLORS['muted']),
                   edgecolor='white', linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(available_brackets, fontsize=11, fontweight='bold', rotation=45, ha='right')
        ax.set_ylabel("% of Channel Transactions", fontsize=16, fontweight='bold', labelpad=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        ax.set_title("Spend Bracket by ICS Channel",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02,
                f"Do ICS accounts transact at different amounts than non-ICS?  ({DATASET_LABEL})",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['muted'], style='italic')

        ax.legend(
            loc='upper center', bbox_to_anchor=(0.5, -0.18),
            ncol=3, fontsize=12, frameon=False, title='Channel',
            title_fontproperties={'weight': 'bold', 'size': 13}
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.22)
        plt.show()

    except NameError:
        print("    amount_bracket not available. Run general/06_bracket_data first.")
