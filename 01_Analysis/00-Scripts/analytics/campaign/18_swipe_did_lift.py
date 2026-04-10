# ===========================================================================
# COHORT SWIPES LIFT: DID Analysis for Card Usage (Conference Edition)
# ===========================================================================
# Same DID methodology as cell 14, but for swipes (card usage frequency).
# Important: some clients care about activation/usage more than spend. (14,7).

if 'cohort_did' not in dir() or len(cohort_did) == 0:
    print("    No cohort DID data available. Skipping swipes lift chart.")
else:
    fig, ax = plt.subplots(figsize=(14, 7))

    n_waves = len(cohort_did)
    x = np.arange(n_waves)

    # Color bars: green if positive, red if negative
    colors = [GEN_COLORS['success'] if v >= 0 else GEN_COLORS['accent']
              for v in cohort_did['did_swipes_lift']]

    bars = ax.bar(x, cohort_did['did_swipes_lift'],
                  color=colors, edgecolor='white', linewidth=1, width=0.55)

    # Zero line
    ax.axhline(y=0, color=GEN_COLORS['dark_text'], linewidth=1.5, linestyle='-', alpha=0.4)

    ax.set_xticks(x)
    ax.set_xticklabels(cohort_did['wave'], fontsize=14, fontweight='bold')
    ax.set_ylabel("DID Swipes Lift (txns/acct/month)", fontsize=16, fontweight='bold', labelpad=10)

    gen_clean_axes(ax)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Annotate each bar
    for i, (bar, (_, row)) in enumerate(zip(bars, cohort_did.iterrows())):
        val = row['did_swipes_lift']
        sign = '+' if val >= 0 else ''
        y_pos = val + (abs(ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02) * (1 if val >= 0 else -1)
        va = 'bottom' if val >= 0 else 'top'

        ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                f"{sign}{val:,.1f}",
                ha='center', va=va, fontsize=14, fontweight='bold',
                color=colors[i])

    # Avg line
    avg_swipe_lift = cohort_did['did_swipes_lift'].mean()
    ax.axhline(y=avg_swipe_lift, color=GEN_COLORS['info'], linewidth=2,
               linestyle='--', alpha=0.8, label=f"Avg DID: {avg_swipe_lift:+,.1f} swipes")
    ax.legend(loc='upper right', fontsize=14)

    ax.set_title("Card Activation Proof: DID Swipes Lift by Wave",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02,
            f"Are responders using their cards MORE than non-responders?  ({DATASET_LABEL})",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
