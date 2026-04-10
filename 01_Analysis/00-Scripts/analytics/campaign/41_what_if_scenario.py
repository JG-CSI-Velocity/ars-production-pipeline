# ===========================================================================
# WHAT-IF SCENARIO: +5pp DCTR (Conference Edition)
# ===========================================================================
# "+5pp DCTR What-If" - Before/after table showing impact of
# activating 5% more accounts. Cascades through IC + Reg E + retention.
# Proof footer: "Your best branch already exceeds this."
#
# Depends on: camp_acct, rewards_df, cohort_summary (cells 01, 10)

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
    REGE_AVG_REVENUE = 30
    SCENARIO_PP = 5  # percentage point increase

    n_total = len(rewards_df) if 'rewards_df' in dir() else len(camp_acct)
    n_active = combined_df['primary_account_num'].nunique() if 'combined_df' in dir() else n_total
    current_rate = n_active / n_total * 100 if n_total > 0 else 0

    avg_did_lift = 0
    if 'cohort_summary' in dir() and len(cohort_summary) > 0:
        avg_did_lift = cohort_summary['did_spend_lift'].mean()

    # Scenario calculations
    new_rate = current_rate + SCENARIO_PP
    new_accounts = int(n_total * SCENARIO_PP / 100)

    ic_gain = new_accounts * abs(avg_did_lift) * IC_RATE * 12
    rege_gain = new_accounts * 0.5 * REGE_AVG_REVENUE  # 50% opt-in
    retention_gain = new_accounts * abs(avg_did_lift) * 12
    total_gain = ic_gain + rege_gain + retention_gain

    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # -----------------------------------------------------------
    # Title area
    # -----------------------------------------------------------
    title_box = FancyBboxPatch((0.5, 8.5), 15, 1.2, boxstyle="round,pad=0.2",
                                facecolor=_PRIMARY, edgecolor='white', linewidth=2)
    ax.add_patch(title_box)
    ax.text(8, 9.1, f"What If We Activate +{SCENARIO_PP}pp More Cards?",
            ha='center', va='center', fontsize=22, fontweight='bold', color='white')

    # -----------------------------------------------------------
    # Before / After comparison
    # -----------------------------------------------------------
    # Current state
    ax.text(4, 7.8, "CURRENT", ha='center', va='center',
            fontsize=18, fontweight='bold', color=_MUTED)
    curr_box = FancyBboxPatch((1, 6.5), 6, 1.2, boxstyle="round,pad=0.2",
                               facecolor=_MUTED, edgecolor='white',
                               linewidth=1.5, alpha=0.15)
    ax.add_patch(curr_box)
    ax.text(4, 7.1, f"{current_rate:.1f}% active  |  {n_active:,} accounts",
            ha='center', va='center', fontsize=16, fontweight='bold', color=_DARK)

    # Arrow
    ax.annotate('', xy=(12, 7.1), xytext=(7.5, 7.1),
                arrowprops=dict(arrowstyle='->', color=_SUCCESS, lw=3))
    ax.text(9.75, 7.5, f"+{SCENARIO_PP}pp",
            ha='center', va='center', fontsize=18, fontweight='bold', color=_SUCCESS)

    # New state
    ax.text(12, 7.8, "SCENARIO", ha='center', va='center',
            fontsize=18, fontweight='bold', color=_SUCCESS)
    new_box = FancyBboxPatch((9, 6.5), 6, 1.2, boxstyle="round,pad=0.2",
                              facecolor=_SUCCESS, edgecolor='white',
                              linewidth=1.5, alpha=0.15)
    ax.add_patch(new_box)
    ax.text(12, 7.1,
            f"{new_rate:.1f}% active  |  +{new_accounts:,} new",
            ha='center', va='center', fontsize=16, fontweight='bold', color=_SUCCESS)

    # -----------------------------------------------------------
    # Cascade table
    # -----------------------------------------------------------
    cascade_items = [
        ("IC Revenue Gain", f"${ic_gain:,.0f}/yr",
         f"{new_accounts:,} x ${abs(avg_did_lift)*IC_RATE*12:.2f}", _SUCCESS),
        ("Reg E Revenue Gain", f"${rege_gain:,.0f}/yr",
         f"{new_accounts:,} x 50% opt-in x ${REGE_AVG_REVENUE}", _INFO),
        ("Retained Spend Gain", f"${retention_gain:,.0f}/yr",
         f"{new_accounts:,} x ${abs(avg_did_lift)*12:.0f}/yr", _WARNING),
    ]

    y_start = 5.5
    for i, (label, value, formula, color) in enumerate(cascade_items):
        y = y_start - i * 1.3

        # Color dot
        dot = plt.Circle((1.5, y), 0.15, color=color, zorder=5)
        ax.add_patch(dot)

        ax.text(2, y, label, ha='left', va='center',
                fontsize=16, fontweight='bold', color=_DARK)
        ax.text(10, y, value, ha='center', va='center',
                fontsize=18, fontweight='bold', color=color)
        ax.text(13, y, formula, ha='left', va='center',
                fontsize=14, color=_MUTED, style='italic')

    # Total line
    y_total = y_start - len(cascade_items) * 1.3 - 0.3
    ax.plot([1, 15], [y_total + 0.4, y_total + 0.4], color=_DARK, linewidth=1.5)
    ax.text(2, y_total, "TOTAL GAIN", ha='left', va='center',
            fontsize=18, fontweight='bold', color=_DARK)
    ax.text(10, y_total, f"${total_gain:,.0f}/yr",
            ha='center', va='center', fontsize=22, fontweight='bold', color=_PRIMARY)

    # -----------------------------------------------------------
    # Proof footer
    # -----------------------------------------------------------
    footer_y = 0.3
    footer_box = FancyBboxPatch((1, footer_y - 0.2), 14, 0.8,
                                 boxstyle="round,pad=0.2",
                                 facecolor=_WARNING, edgecolor='white',
                                 linewidth=1.5, alpha=0.2)
    ax.add_patch(footer_box)
    ax.text(8, footer_y + 0.2,
            f"This is achievable: +{SCENARIO_PP}pp requires activating just "
            f"{new_accounts:,} additional accounts ({SCENARIO_PP}% of {n_total:,})",
            ha='center', va='center', fontsize=14, fontweight='bold',
            color=_DARK, style='italic')

    fig.suptitle(f"+{SCENARIO_PP}pp DCTR Scenario Analysis",
                 fontsize=28, fontweight='bold', color=_DARK, y=0.99)
    fig.text(0.5, 0.95,
             f"Impact of activating {SCENARIO_PP}% more debit cards  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.show()

    print(f"\n    +{SCENARIO_PP}pp DCTR What-If:")
    print(f"      Current rate:    {current_rate:.1f}%  ({n_active:,} active)")
    print(f"      Scenario rate:   {new_rate:.1f}%  (+{new_accounts:,} new)")
    print(f"      IC gain:         ${ic_gain:,.0f}/yr")
    print(f"      Reg E gain:      ${rege_gain:,.0f}/yr")
    print(f"      Retention gain:  ${retention_gain:,.0f}/yr")
    print(f"      TOTAL GAIN:      ${total_gain:,.0f}/yr")
