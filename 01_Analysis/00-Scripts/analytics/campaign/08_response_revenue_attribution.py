# ===========================================================================
# RESPONSE REVENUE ATTRIBUTION: IC Revenue Comparison (Conference Edition)
# ===========================================================================
# Compares interchange (IC) revenue per account: responders vs non-responders.
# Incremental IC = (resp_ic_per_acct - nonresp_ic_per_acct) * n_responders
#
# Depends on: camp_acct, camp_status_agg, camp_resp_df, camp_nonresp_df (cell 01)

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
    _INFO = GEN_COLORS.get('info', '#457B9D')
    _WARNING = GEN_COLORS.get('warning', '#E9C46A')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')

    # IC rate: default or from config
    IC_RATE = 0.018  # typical debit IC rate

    n_resp = (camp_acct['camp_status'] == 'Responder').sum()
    n_nonresp = (camp_acct['camp_status'] == 'Non-Responder').sum()
    n_months = DATASET_MONTHS if 'DATASET_MONTHS' in dir() else 12

    # Per-account spend
    resp_spend = 0
    nonresp_spend = 0

    if 'camp_status_agg' in dir() and len(camp_status_agg) > 0:
        _resp_row = camp_status_agg[camp_status_agg['camp_status'] == 'Responder']
        _nonresp_row = camp_status_agg[camp_status_agg['camp_status'] == 'Non-Responder']

        if len(_resp_row) > 0:
            resp_spend = _resp_row['spend_per_acct_mo'].values[0]
        if len(_nonresp_row) > 0:
            nonresp_spend = _nonresp_row['spend_per_acct_mo'].values[0]

    resp_ic_mo = resp_spend * IC_RATE
    nonresp_ic_mo = nonresp_spend * IC_RATE
    ic_delta_mo = resp_ic_mo - nonresp_ic_mo
    ic_delta_annual = ic_delta_mo * 12
    incremental_ic_annual = ic_delta_annual * n_resp

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7),
                                    gridspec_kw={'width_ratios': [1, 1]})

    # -----------------------------------------------------------
    # Left: Per-Account Monthly IC Revenue comparison
    # -----------------------------------------------------------
    categories = ['Responder', 'Non-Responder']
    ic_values = [resp_ic_mo, nonresp_ic_mo]
    colors = [_SUCCESS, _ACCENT]

    bars = ax1.bar(categories, ic_values, color=colors,
                   edgecolor='white', linewidth=1.5, width=0.45, zorder=3)

    for bar, val in zip(bars, ic_values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(ic_values) * 0.03,
                 f"${val:.2f}", ha='center', va='bottom',
                 fontsize=20, fontweight='bold', color=_DARK)

    # Delta annotation
    if ic_delta_mo > 0:
        ax1.annotate(
            f"+${ic_delta_mo:.2f}/mo\nper account",
            xy=(0.5, min(ic_values)),
            xytext=(0.5, max(ic_values) * 0.7),
            fontsize=16, fontweight='bold', color=_SUCCESS,
            ha='center', va='center',
            arrowprops=dict(arrowstyle='->', color=_SUCCESS, lw=2),
        )

    ax1.set_ylabel("Monthly IC Revenue / Account", fontsize=16, fontweight='bold')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
    ax1.tick_params(axis='x', labelsize=16)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=GEN_COLORS.get('grid', '#E0E0E0'),
                  linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Per-Account IC Revenue", fontsize=20, fontweight='bold',
                  color=_DARK, pad=14)

    # -----------------------------------------------------------
    # Right: Total Incremental IC Value (KPI style)
    # -----------------------------------------------------------
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')

    # Background card
    card = FancyBboxPatch(
        (0.5, 0.5), 9, 9,
        boxstyle="round,pad=0.4",
        facecolor=_SUCCESS, edgecolor='white', linewidth=3, alpha=0.15
    )
    ax2.add_patch(card)

    ax2.text(5, 8.5, "Incremental IC Revenue", ha='center', va='center',
             fontsize=18, fontweight='bold', color=_DARK)

    ax2.text(5, 6.5, f"${incremental_ic_annual:,.0f}", ha='center', va='center',
             fontsize=42, fontweight='bold', color=_SUCCESS)
    ax2.text(5, 5.2, "annual incremental IC", ha='center', va='center',
             fontsize=16, color=_MUTED, fontweight='bold')

    ax2.text(5, 3.5,
             f"= {n_resp:,} responders  x  ${ic_delta_annual:.2f}/yr/acct",
             ha='center', va='center', fontsize=14, color=_DARK)

    ax2.text(5, 2.2,
             f"Spend/mo: Resp ${resp_spend:,.0f}  vs  Non-Resp ${nonresp_spend:,.0f}",
             ha='center', va='center', fontsize=14, color=_MUTED, style='italic')

    ax2.text(5, 1.2,
             f"IC rate: {IC_RATE*100:.1f}%",
             ha='center', va='center', fontsize=14, color=_MUTED)

    fig.suptitle("Interchange Revenue Attribution",
                 fontsize=28, fontweight='bold', color=_DARK, y=0.98)
    fig.text(0.5, 0.93,
             f"Responder vs Non-Responder IC contribution  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    plt.show()

    print(f"\n    IC Revenue Attribution:")
    print(f"      Resp IC/mo/acct:    ${resp_ic_mo:.2f}  (spend ${resp_spend:,.0f})")
    print(f"      Non-Resp IC/mo/acct: ${nonresp_ic_mo:.2f}  (spend ${nonresp_spend:,.0f})")
    print(f"      Delta:               +${ic_delta_mo:.2f}/mo  (+${ic_delta_annual:.2f}/yr)")
    print(f"      Incremental annual:  ${incremental_ic_annual:,.0f}  ({n_resp:,} responders)")
