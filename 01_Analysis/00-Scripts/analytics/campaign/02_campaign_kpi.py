# ===========================================================================
# CAMPAIGN KPI: Program Reach Dashboard (Conference Edition)
# ===========================================================================
# 6 KPI cards + nested proportional circles showing
# eligible > mailed > responded funnel.
#
# Depends on: camp_acct, camp_summary, rewards_df (cell 01)

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

    # Compute KPIs
    n_eligible = len(rewards_df) if 'rewards_df' in dir() else len(camp_acct)
    n_mailed = (camp_acct['camp_status'] != 'Never Mailed').sum()
    n_responded = (camp_acct['camp_status'] == 'Responder').sum()
    n_unique_resp = camp_acct.loc[camp_acct['camp_status'] == 'Responder',
                                  'primary_account_num'].nunique()
    overall_rate = n_responded / n_mailed * 100 if n_mailed > 0 else 0
    mail_penetration = n_mailed / n_eligible * 100 if n_eligible > 0 else 0

    # Responder share of eligible spend
    resp_spend_share = 0
    if 'camp_status_agg' in dir() and len(camp_status_agg) > 0:
        _total_spend = camp_status_agg['total_spend'].sum()
        _resp_spend = camp_status_agg.loc[
            camp_status_agg['camp_status'] == 'Responder', 'total_spend'
        ].sum()
        resp_spend_share = _resp_spend / _total_spend * 100 if _total_spend > 0 else 0

    # -----------------------------------------------------------------
    # KPI Cards (row 1)
    # -----------------------------------------------------------------
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.4], hspace=0.3)

    # Row 1: 6 KPI cards
    gs_top = gs[0].subgridspec(1, 6, wspace=0.15)

    kpi_data = [
        {'label': 'Eligible\nAccounts', 'value': f"{n_eligible:,}",
         'sub': 'total portfolio', 'color': _MUTED},
        {'label': 'Total\nMailed', 'value': f"{n_mailed:,}",
         'sub': f"{mail_penetration:.0f}% of eligible", 'color': _INFO},
        {'label': 'Total\nResponded', 'value': f"{n_responded:,}",
         'sub': f"across {len(camp_summary)} waves", 'color': _SUCCESS},
        {'label': 'Unique\nResponders', 'value': f"{n_unique_resp:,}",
         'sub': 'distinct accounts', 'color': _WARNING},
        {'label': 'Overall\nResponse Rate', 'value': f"{overall_rate:.1f}%",
         'sub': f"{n_responded:,} of {n_mailed:,}", 'color': _ACCENT},
        {'label': 'Responder\nSpend Share', 'value': f"{resp_spend_share:.1f}%",
         'sub': 'of total portfolio spend', 'color': _PRIMARY},
    ]

    for i, kpi in enumerate(kpi_data):
        ax = fig.add_subplot(gs_top[i])
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        card = FancyBboxPatch(
            (0.3, 0.3), 9.4, 9.4,
            boxstyle="round,pad=0.3",
            facecolor=kpi['color'], edgecolor='white', linewidth=3
        )
        ax.add_patch(card)

        ax.text(5, 7.2, kpi['label'],
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='white', alpha=0.85, linespacing=1.2)
        ax.text(5, 4.5, kpi['value'],
                ha='center', va='center', fontsize=36, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.3, kpi['sub'],
                ha='center', va='center', fontsize=14,
                color='white', alpha=0.8, style='italic')

    # -----------------------------------------------------------------
    # Row 2: Nested Proportional Circles (eligible > mailed > responded)
    # -----------------------------------------------------------------
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(-1.5, 1.5)
    ax2.set_ylim(-1.5, 1.5)
    ax2.set_aspect('equal')
    ax2.axis('off')

    max_r = 1.2
    r_eligible = max_r
    r_mailed = max_r * np.sqrt(n_mailed / n_eligible) if n_eligible > 0 else max_r * 0.7
    r_responded = max_r * np.sqrt(n_responded / n_eligible) if n_eligible > 0 else max_r * 0.3

    circles = [
        (r_eligible, _MUTED, 0.12, f"Eligible: {n_eligible:,}"),
        (r_mailed, _INFO, 0.18, f"Mailed: {n_mailed:,}"),
        (r_responded, _SUCCESS, 0.25, f"Responded: {n_responded:,}"),
    ]

    for r, color, alpha, label in circles:
        circle = plt.Circle((0, 0), r, facecolor=color, alpha=alpha,
                            edgecolor=color, linewidth=2.5)
        ax2.add_patch(circle)

    # Labels
    ax2.text(0, 0, f"{n_responded:,}\nResponded",
             ha='center', va='center', fontsize=20, fontweight='bold',
             color=_SUCCESS)
    ax2.text(0, r_mailed * 0.7, f"{n_mailed:,} Mailed",
             ha='center', va='bottom', fontsize=16, fontweight='bold',
             color=_INFO)
    ax2.text(0, r_eligible * 0.85, f"{n_eligible:,} Eligible",
             ha='center', va='bottom', fontsize=16, fontweight='bold',
             color=_MUTED)

    # Conversion rates between rings
    ax2.text(1.0, -0.3,
             f"Mail Penetration: {mail_penetration:.1f}%\n"
             f"Response Rate: {overall_rate:.1f}%\n"
             f"Portfolio Activation: {n_responded / n_eligible * 100:.1f}%"
             if n_eligible > 0 else "",
             ha='left', va='center', fontsize=16, fontweight='bold',
             color=_DARK, linespacing=1.6,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                       edgecolor=_MUTED, alpha=0.9))

    fig.suptitle("ARS Program Reach",
                 fontsize=28, fontweight='bold',
                 color=_DARK, y=0.98)
    fig.text(0.5, 0.94,
             f"Eligible > Mailed > Responded funnel  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    plt.show()
