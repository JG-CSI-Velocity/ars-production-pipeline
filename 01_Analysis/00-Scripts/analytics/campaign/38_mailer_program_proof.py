# ===========================================================================
# MAILER PROGRAM PROOF: Flow Diagram + ROI (Conference Edition)
# ===========================================================================
# Flow diagram: Mailer -> Activation -> Spend Lift
# True DID lift = resp_delta - non_delta (eliminates market trend)
# Two result boxes: IC revenue + retention value. Total ROI footer.
#
# Depends on: camp_acct, camp_summary, cohort_summary (cells 01, 10)

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
    _INFO = GEN_COLORS.get('info', '#457B9D')
    _WARNING = GEN_COLORS.get('warning', '#E9C46A')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')
    _PRIMARY = GEN_COLORS.get('primary', '#264653')

    IC_RATE = 0.018

    n_mailed = (camp_acct['camp_status'] != 'Never Mailed').sum()
    n_responded = (camp_acct['camp_status'] == 'Responder').sum()
    response_rate = n_responded / n_mailed * 100 if n_mailed > 0 else 0

    # DID metrics from cohort analysis
    avg_did_lift = 0
    ic_annual = 0
    if 'cohort_summary' in dir() and len(cohort_summary) > 0:
        avg_did_lift = cohort_summary['did_spend_lift'].mean()
        ic_annual = abs(avg_did_lift) * IC_RATE * n_responded * 12

    fig, ax = plt.subplots(figsize=(18, 10))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # -----------------------------------------------------------
    # Flow boxes
    # -----------------------------------------------------------
    box_props = dict(boxstyle='round,pad=0.5', linewidth=2.5)

    # Box 1: Mailer Program
    box1 = FancyBboxPatch((0.5, 6), 4, 3, boxstyle="round,pad=0.3",
                           facecolor=_INFO, edgecolor='white', linewidth=2.5,
                           alpha=0.9)
    ax.add_patch(box1)
    ax.text(2.5, 8, "MAILER\nPROGRAM", ha='center', va='center',
            fontsize=20, fontweight='bold', color='white', linespacing=1.3)
    ax.text(2.5, 6.5, f"{n_mailed:,} mailed",
            ha='center', va='center', fontsize=14, color='white', alpha=0.85)

    # Arrow 1 -> 2
    ax.annotate('', xy=(5.5, 7.5), xytext=(4.7, 7.5),
                arrowprops=dict(arrowstyle='->', color=_DARK, lw=2.5))
    ax.text(5.1, 8.2, f"{response_rate:.1f}%\nrate",
            ha='center', va='center', fontsize=14, fontweight='bold', color=_DARK)

    # Box 2: Activation
    box2 = FancyBboxPatch((5.5, 6), 4, 3, boxstyle="round,pad=0.3",
                           facecolor=_SUCCESS, edgecolor='white', linewidth=2.5,
                           alpha=0.9)
    ax.add_patch(box2)
    ax.text(7.5, 8, "ACTIVATION", ha='center', va='center',
            fontsize=20, fontweight='bold', color='white')
    ax.text(7.5, 6.5, f"{n_responded:,} responded",
            ha='center', va='center', fontsize=14, color='white', alpha=0.85)

    # Arrow 2 -> 3
    ax.annotate('', xy=(10.5, 7.5), xytext=(9.7, 7.5),
                arrowprops=dict(arrowstyle='->', color=_DARK, lw=2.5))

    # Box 3: Spend Lift
    box3 = FancyBboxPatch((10.5, 6), 4, 3, boxstyle="round,pad=0.3",
                           facecolor=_WARNING, edgecolor='white', linewidth=2.5,
                           alpha=0.9)
    ax.add_patch(box3)
    ax.text(12.5, 8, "SPEND\nLIFT", ha='center', va='center',
            fontsize=20, fontweight='bold', color='white', linespacing=1.3)
    ax.text(12.5, 6.5, f"DID: ${avg_did_lift:+,.0f}/mo",
            ha='center', va='center', fontsize=14, color='white', alpha=0.85)

    # -----------------------------------------------------------
    # DID Explanation box (center)
    # -----------------------------------------------------------
    did_box = FancyBboxPatch((5, 3.5), 8, 2, boxstyle="round,pad=0.3",
                              facecolor='white', edgecolor=_DARK, linewidth=1.5)
    ax.add_patch(did_box)
    ax.text(9, 5,
            "True DID Lift = Responder Change - Non-Responder Change",
            ha='center', va='center', fontsize=16, fontweight='bold',
            color=_DARK)
    ax.text(9, 4,
            "Eliminates market trend contamination",
            ha='center', va='center', fontsize=14, color=_MUTED, style='italic')

    # -----------------------------------------------------------
    # Result boxes (bottom row)
    # -----------------------------------------------------------
    # IC Revenue box
    ic_box = FancyBboxPatch((1, 0.5), 6, 2.2, boxstyle="round,pad=0.3",
                             facecolor=_SUCCESS, edgecolor='white', linewidth=2,
                             alpha=0.15)
    ax.add_patch(ic_box)
    ax.text(4, 2.2, "IC Revenue Impact", ha='center', va='center',
            fontsize=16, fontweight='bold', color=_SUCCESS)
    ax.text(4, 1.5, f"${ic_annual:,.0f} / year",
            ha='center', va='center', fontsize=22, fontweight='bold',
            color=_SUCCESS)
    ax.text(4, 0.9, f"= {n_responded:,} x ${abs(avg_did_lift)*IC_RATE*12:.2f}/yr",
            ha='center', va='center', fontsize=14, color=_MUTED)

    # Retention Value box
    retention_annual = abs(avg_did_lift) * n_responded * 12
    ret_box = FancyBboxPatch((9, 0.5), 6, 2.2, boxstyle="round,pad=0.3",
                              facecolor=_INFO, edgecolor='white', linewidth=2,
                              alpha=0.15)
    ax.add_patch(ret_box)
    ax.text(12, 2.2, "Retained Spend Value", ha='center', va='center',
            fontsize=16, fontweight='bold', color=_INFO)
    ax.text(12, 1.5, f"${retention_annual:,.0f} / year",
            ha='center', va='center', fontsize=22, fontweight='bold',
            color=_INFO)
    ax.text(12, 0.9, f"= {n_responded:,} x ${abs(avg_did_lift)*12:.0f}/yr",
            ha='center', va='center', fontsize=14, color=_MUTED)

    # Total ROI footer
    total_value = ic_annual + retention_annual
    ax.text(9, -0.3,
            f"Total Annual Program Value: ${total_value:,.0f}",
            ha='center', va='center', fontsize=20, fontweight='bold',
            color=_DARK,
            bbox=dict(boxstyle='round,pad=0.3', facecolor=_WARNING, alpha=0.3))

    fig.suptitle("Mailer Program: Proof of Impact",
                 fontsize=28, fontweight='bold', color=_DARK, y=0.98)
    fig.text(0.5, 0.94,
             f"DID methodology isolates true program effect  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, -0.02, 1, 0.92])
    plt.show()

    print(f"\n    Mailer Program Proof:")
    print(f"      Mailed: {n_mailed:,}  ->  Responded: {n_responded:,}  ({response_rate:.1f}%)")
    print(f"      Avg DID Lift: ${avg_did_lift:+,.0f}/mo/acct")
    print(f"      IC Revenue:     ${ic_annual:,.0f}/yr")
    print(f"      Retained Spend: ${retention_annual:,.0f}/yr")
    print(f"      Total Value:    ${total_value:,.0f}/yr")
