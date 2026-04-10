# ===========================================================================
# REVENUE CASCADE: Per-Activation Waterfall (Conference Edition)
# ===========================================================================
# "The Debit Card Cascade" - Stacked waterfall: 3 revenue streams
# per activation (IC + Reg E weighted by opt-in + retention value).
# Per-card ROI = stream_1 + stream_2 + stream_3.
#
# Depends on: camp_acct, cohort_summary (cells 01, 10)
# Falls back to PULSE defaults for missing data

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
    REGE_OPT_IN = 0.50  # default 50%
    REGE_AVG_REVENUE = 30  # $/acct/yr for opted-in

    n_responded = (camp_acct['camp_status'] == 'Responder').sum()

    # DID lift
    avg_did_lift = 0
    if 'cohort_summary' in dir() and len(cohort_summary) > 0:
        avg_did_lift = cohort_summary['did_spend_lift'].mean()

    # Per-activation annual values
    ic_per_acct = abs(avg_did_lift) * IC_RATE * 12
    rege_per_acct = REGE_AVG_REVENUE * REGE_OPT_IN
    retention_per_acct = abs(avg_did_lift) * 12  # retained spend

    total_per_acct = ic_per_acct + rege_per_acct + retention_per_acct

    # Check for RegE data
    if 'rewards_df' in dir():
        _rege_cols = [c for c in rewards_df.columns if 'Reg E' in c or 'reg_e' in c.lower()]
        if len(_rege_cols) > 0:
            _rege_vals = rewards_df[_rege_cols[0]]
            _opted = _rege_vals.astype(str).str.strip().str.upper().isin(
                ['Y', 'YES', '1', 'TRUE', 'OPTED-IN'])
            REGE_OPT_IN = _opted.sum() / len(_rege_vals)
            rege_per_acct = REGE_AVG_REVENUE * REGE_OPT_IN
            total_per_acct = ic_per_acct + rege_per_acct + retention_per_acct

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8),
                                    gridspec_kw={'width_ratios': [1.2, 1]})

    # -----------------------------------------------------------
    # Left: Waterfall chart
    # -----------------------------------------------------------
    categories = ['IC Revenue', 'Reg E\n(weighted)', 'Retained\nSpend', 'TOTAL']
    values = [ic_per_acct, rege_per_acct, retention_per_acct, total_per_acct]
    colors = [_SUCCESS, _INFO, _WARNING, _PRIMARY]
    bottoms = [0, ic_per_acct, ic_per_acct + rege_per_acct, 0]

    for i, (cat, val, color, bottom) in enumerate(zip(categories, values, colors, bottoms)):
        if i == 3:  # Total bar
            ax1.bar(i, val, color=color, edgecolor='white', linewidth=2,
                   width=0.5, zorder=3, alpha=0.85)
        else:
            ax1.bar(i, val, bottom=bottom, color=color, edgecolor='white',
                   linewidth=2, width=0.5, zorder=3)

        # Value label
        label_y = bottom + val / 2 if i < 3 else val / 2
        ax1.text(i, bottom + val + total_per_acct * 0.03,
                 f"${val:.2f}", ha='center', va='bottom',
                 fontsize=18, fontweight='bold', color=color)

    # Connector lines between stacked segments
    for i in range(2):
        top = bottoms[i] + values[i]
        ax1.plot([i + 0.25, i + 0.75], [top, top],
                 color=_MUTED, linewidth=1, linestyle='--', alpha=0.5)

    ax1.set_xticks(range(4))
    ax1.set_xticklabels(categories, fontsize=14, fontweight='bold')
    ax1.set_ylabel("Annual Value per Activation ($/acct/yr)",
                   fontsize=16, fontweight='bold')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=GEN_COLORS.get('grid', '#E0E0E0'),
                  linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Per-Activation Revenue Cascade",
                  fontsize=20, fontweight='bold', color=_DARK, pad=14)

    # -----------------------------------------------------------
    # Right: Portfolio impact summary
    # -----------------------------------------------------------
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')

    # Summary card
    card = FancyBboxPatch((0.3, 0.3), 9.4, 9.4,
                           boxstyle="round,pad=0.3",
                           facecolor='white', edgecolor=_DARK, linewidth=1.5)
    ax2.add_patch(card)

    ax2.text(5, 9, "Portfolio Impact", ha='center', va='center',
             fontsize=20, fontweight='bold', color=_DARK)

    y_pos = 7.5
    stream_data = [
        (f"IC Revenue", f"${ic_per_acct:.2f}/acct/yr", f"${ic_per_acct * n_responded:,.0f} total", _SUCCESS),
        (f"Reg E (weighted)", f"${rege_per_acct:.2f}/acct/yr", f"${rege_per_acct * n_responded:,.0f} total", _INFO),
        (f"Retained Spend", f"${retention_per_acct:.0f}/acct/yr", f"${retention_per_acct * n_responded:,.0f} total", _WARNING),
    ]

    for label, per_acct, total, color in stream_data:
        ax2.plot([1.5, 2], [y_pos, y_pos], color=color, linewidth=4, solid_capstyle='round')
        ax2.text(2.3, y_pos, label, ha='left', va='center',
                 fontsize=14, fontweight='bold', color=_DARK)
        ax2.text(7, y_pos + 0.15, per_acct, ha='center', va='center',
                 fontsize=14, fontweight='bold', color=color)
        ax2.text(7, y_pos - 0.3, total, ha='center', va='center',
                 fontsize=14, color=_MUTED)
        y_pos -= 1.5

    # Total
    ax2.plot([1, 9], [3.2, 3.2], color=_DARK, linewidth=1)
    ax2.text(5, 2.5, f"${total_per_acct:.2f} / activation / year",
             ha='center', va='center', fontsize=18, fontweight='bold', color=_DARK)
    ax2.text(5, 1.5, f"x {n_responded:,} activations =",
             ha='center', va='center', fontsize=14, color=_MUTED)
    ax2.text(5, 0.7, f"${total_per_acct * n_responded:,.0f} annual value",
             ha='center', va='center', fontsize=20, fontweight='bold', color=_SUCCESS)

    fig.suptitle("The Debit Card Revenue Cascade",
                 fontsize=28, fontweight='bold', color=_DARK, y=1.0)
    fig.text(0.5, 0.96,
             f"Three revenue streams per activation  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    plt.show()

    print(f"\n    Revenue Cascade (per activation, annual):")
    print(f"      IC Revenue:     ${ic_per_acct:.2f}  (DID lift ${abs(avg_did_lift):.0f}/mo x {IC_RATE*100:.1f}%)")
    print(f"      Reg E:          ${rege_per_acct:.2f}  ({REGE_OPT_IN*100:.0f}% opt-in x ${REGE_AVG_REVENUE}/yr)")
    print(f"      Retained Spend: ${retention_per_acct:.0f}")
    print(f"      TOTAL:          ${total_per_acct:.2f}/acct/yr")
    print(f"      Portfolio:      ${total_per_acct * n_responded:,.0f}/yr ({n_responded:,} activations)")
