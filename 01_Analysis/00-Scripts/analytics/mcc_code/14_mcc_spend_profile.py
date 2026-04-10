# ===========================================================================
# MCC SPEND PROFILE: Transaction Size by Category (Conference Edition)
# ===========================================================================
# Box plot: avg transaction size for top 12 MCCs. (14,7).
# Reveals which categories have high-value vs micro-transactions.

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping spend profile.")
elif 'mcc_code' not in combined_df.columns:
    print("    No mcc_code column available. Skipping spend profile.")
else:
    top12_spend_codes = mcc_agg.head(12)['mcc_code'].tolist()
    spend_data = combined_df[combined_df['mcc_code'].isin(top12_spend_codes)]

    if len(spend_data) == 0:
        print("    No spend data for top MCC codes. Skipping spend profile.")
    else:
        # Order by median transaction amount
        mcc_medians = spend_data.groupby('mcc_code')['amount'].median().sort_values(ascending=True)
        ordered_codes = mcc_medians.index.tolist()

        fig, ax = plt.subplots(figsize=(14, 7))

        box_data = [
            spend_data[spend_data['mcc_code'] == code]['amount'].dropna().values
            for code in ordered_codes
        ]

        bp = ax.boxplot(
            box_data, vert=False, patch_artist=True,
            widths=0.6, showfliers=False,
            medianprops=dict(color=GEN_COLORS['accent'], linewidth=2.5),
            whiskerprops=dict(color=GEN_COLORS['muted'], linewidth=1.5),
            capprops=dict(color=GEN_COLORS['muted'], linewidth=1.5),
        )

        # Color boxes by median value (gradient)
        for i, patch in enumerate(bp['boxes']):
            frac = i / max(len(bp['boxes']) - 1, 1)
            r = int(69 + frac * (230 - 69))
            g = int(123 + frac * (57 - 123))
            b = int(157 + frac * (70 - 157))
            patch.set_facecolor(f'#{r:02x}{g:02x}{b:02x}')
            patch.set_edgecolor('white')
            patch.set_linewidth(1.5)
            patch.set_alpha(0.85)

        ax.set_yticks(range(1, len(ordered_codes) + 1))
        ax.set_yticklabels([str(c) for c in ordered_codes], fontsize=13, fontweight='bold')
        ax.set_xlabel("Transaction Amount ($)", fontsize=16, fontweight='bold', labelpad=10)

        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        # Add median value labels
        for i, code in enumerate(ordered_codes):
            med_val = mcc_medians[code]
            ax.text(med_val, i + 1.3, f"${med_val:,.0f}",
                    fontsize=10, fontweight='bold', color=GEN_COLORS['accent'],
                    ha='center')

        ax.set_title("Transaction Size by MCC Category",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02, "Which categories have large vs micro-transactions?",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()
