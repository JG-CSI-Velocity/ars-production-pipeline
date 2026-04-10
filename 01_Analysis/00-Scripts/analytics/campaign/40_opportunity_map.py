# ===========================================================================
# OPPORTUNITY MAP: Addressable vs Realistic (Conference Edition)
# ===========================================================================
# Two-row stacked horizontal bar:
#   "Addressable (Max)" and "Realistic (Near-Term)"
#   across debit gap + Reg E gap + retention + mailer program.
# Dollar totals annotated.
#
# Depends on: camp_acct, cohort_summary, combined_df, rewards_df

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
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')

    IC_RATE = 0.018
    PULSE_ACTIVE_RATE = 66.3
    AVG_ANNUAL_IC = 216
    REGE_AVG_REVENUE = 30
    REGE_BENCHMARK = 50.0

    n_total = len(rewards_df) if 'rewards_df' in dir() else len(camp_acct)
    n_active = combined_df['primary_account_num'].nunique() if 'combined_df' in dir() else n_total
    cu_active_rate = n_active / n_total * 100 if n_total > 0 else 0

    n_responded = (camp_acct['camp_status'] == 'Responder').sum()
    n_mailed = (camp_acct['camp_status'] != 'Never Mailed').sum()
    n_never_mailed = (camp_acct['camp_status'] == 'Never Mailed').sum()

    avg_did_lift = 0
    if 'cohort_summary' in dir() and len(cohort_summary) > 0:
        avg_did_lift = cohort_summary['did_spend_lift'].mean()

    # -----------------------------------------------------------
    # Calculate opportunity components
    # -----------------------------------------------------------

    # 1. Debit gap: inactive accounts that could be activated
    debit_gap_accts = max(0, int(n_total * PULSE_ACTIVE_RATE / 100) - n_active)
    debit_gap_value = debit_gap_accts * AVG_ANNUAL_IC  # max

    # 2. Reg E gap
    cu_rege_rate = 0
    if 'rewards_df' in dir():
        _rege_cols = [c for c in rewards_df.columns if 'Reg E' in c or 'reg_e' in c.lower()]
        if len(_rege_cols) > 0:
            _rege_vals = rewards_df[_rege_cols[0]]
            _opted = _rege_vals.astype(str).str.strip().str.upper().isin(
                ['Y', 'YES', '1', 'TRUE', 'OPTED-IN'])
            cu_rege_rate = _opted.sum() / len(_rege_vals) * 100

    rege_gap_accts = max(0, int(n_total * REGE_BENCHMARK / 100 - n_total * cu_rege_rate / 100))
    rege_gap_value = rege_gap_accts * REGE_AVG_REVENUE

    # 3. Mailer expansion: never-mailed accounts
    mailer_expansion_accts = n_never_mailed
    response_rate = n_responded / n_mailed * 100 if n_mailed > 0 else 5
    mailer_new_resp = int(mailer_expansion_accts * response_rate / 100)
    mailer_value = mailer_new_resp * abs(avg_did_lift) * IC_RATE * 12

    # 4. Retained spend from existing program
    retained_value = abs(avg_did_lift) * n_responded * 12

    # Addressable (max) vs Realistic (50% capture)
    CAPTURE_RATE = 0.50

    components = [
        ('Debit Card\nGap', debit_gap_value, _SUCCESS),
        ('Reg E\nGap', rege_gap_value, _INFO),
        ('Mailer\nExpansion', mailer_value, _WARNING),
        ('Current\nRetained', retained_value, _PRIMARY),
    ]

    fig, ax = plt.subplots(figsize=(18, 8))

    y_positions = [1.5, 0.5]
    y_labels = ['Addressable\n(Maximum)', 'Realistic\n(Near-Term)']
    bar_height = 0.6

    for y_idx, (y_pos, y_label) in enumerate(zip(y_positions, y_labels)):
        left = 0
        for label, max_val, color in components:
            val = max_val if y_idx == 0 else max_val * CAPTURE_RATE
            ax.barh(y_pos, val, left=left, height=bar_height,
                   color=color, edgecolor='white', linewidth=2, zorder=3,
                   alpha=1.0 if y_idx == 0 else 0.7)

            # Segment label inside bar
            if val > 0:
                mid = left + val / 2
                ax.text(mid, y_pos,
                        f"${val:,.0f}",
                        ha='center', va='center',
                        fontsize=14, fontweight='bold', color='white')
            left += val

        # Total annotation
        total = sum(v if y_idx == 0 else v * CAPTURE_RATE for _, v, _ in components)
        ax.text(left + max(left * 0.02, 5000), y_pos,
                f"${total:,.0f}",
                ha='left', va='center',
                fontsize=18, fontweight='bold', color=_DARK)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=16, fontweight='bold')
    ax.set_xlabel("Annual Dollar Opportunity", fontsize=16, fontweight='bold')
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, edgecolor='white', label=l.replace('\n', ' '))
                       for l, _, c in components]
    ax.legend(handles=legend_elements, fontsize=14, loc='upper right',
              framealpha=0.9, ncol=2)

    fig.suptitle("Revenue Opportunity Map",
                 fontsize=28, fontweight='bold', color=_DARK, y=0.98)
    fig.text(0.5, 0.93,
             f"Addressable vs near-term capture at {CAPTURE_RATE*100:.0f}%  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    plt.show()

    total_addressable = sum(v for _, v, _ in components)
    total_realistic = total_addressable * CAPTURE_RATE
    print(f"\n    Opportunity Map:")
    print(f"      Debit gap:       ${debit_gap_value:>12,.0f}  ({debit_gap_accts:,} accounts)")
    print(f"      Reg E gap:       ${rege_gap_value:>12,.0f}  ({rege_gap_accts:,} accounts)")
    print(f"      Mailer expansion: ${mailer_value:>12,.0f}  ({mailer_new_resp:,} projected resp)")
    print(f"      Current retained: ${retained_value:>12,.0f}  ({n_responded:,} responders)")
    print(f"      ---")
    print(f"      Addressable:     ${total_addressable:>12,.0f}")
    print(f"      Realistic ({CAPTURE_RATE*100:.0f}%): ${total_realistic:>12,.0f}")
