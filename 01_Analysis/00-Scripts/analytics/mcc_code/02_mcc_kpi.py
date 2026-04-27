# ===========================================================================
# MCC KPI DASHBOARD: Category Concentration (Conference Edition)
# ===========================================================================
# 4 bold cards. (18,5).

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC data available. Skipping KPI dashboard.")
else:
    top5_share = mcc_agg.head(5)['txn_pct'].sum()
    top10_share = mcc_agg.head(10)['txn_pct'].sum()
    top20_share = mcc_agg.head(20)['txn_pct'].sum()

    kpis = [
        (f"{len(mcc_agg)}", "MCC Categories\nDetected", GEN_COLORS['primary']),
        (f"{top5_share:.0f}%", "of Txns in\nTop 5 MCCs", GEN_COLORS['accent']),
        (f"{top10_share:.0f}%", "of Txns in\nTop 10 MCCs", GEN_COLORS['info']),
        (f"{mcc_agg['txn_per_account'].median():.1f}", "Median Txns\nper Account per MCC", GEN_COLORS['success']),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    fig.patch.set_facecolor('#FFFFFF')

    for ax, (value, label, color) in zip(axes, kpis):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        card = FancyBboxPatch(
            (0.03, 0.05), 0.94, 0.90,
            boxstyle="round,pad=0.05",
            facecolor=color, alpha=0.08,
            edgecolor=color, linewidth=2.5
        )
        ax.add_patch(card)

        ax.text(0.5, 0.62, value, transform=ax.transAxes,
                fontsize=48, fontweight='bold', color=color,
                ha='center', va='center')

        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'],
                ha='center', va='center', linespacing=1.4)

    fig.suptitle("Merchant Category Concentration",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)

    plt.tight_layout()
    plt.show()
