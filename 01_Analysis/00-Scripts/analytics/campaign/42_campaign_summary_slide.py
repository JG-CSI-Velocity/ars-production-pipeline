# ===========================================================================
# ARS CAMPAIGN SUMMARY: One-Slide Takeaway
# ===========================================================================
# Single figure combining all key campaign metrics:
#   Row 1: 5 KPI cards (total mailed, total responses, unique responders,
#           overall rate, avg DID spend lift)
#   Row 2: DID by segment bar chart + key insight callouts
#
# Depends on: camp_summary, camp_acct (cell 01), segment_cohort_raw (cell 25),
#             segment_cohort_summary (cell 25b)

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
elif 'segment_cohort_raw' not in dir() or len(segment_cohort_raw) == 0:
    print("    No segment cohort data. Run cell 25 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')
    _SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
    _WARNING = GEN_COLORS.get('warning', '#E9C46A')
    _INFO = GEN_COLORS.get('info', '#457B9D')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')

    # ------------------------------------------------------------------
    # Compute all KPIs
    # ------------------------------------------------------------------
    _total_mailings = camp_summary['mailed'].sum()
    _total_responses = camp_summary['responded'].sum()
    _total_near_use = camp_summary['near_use'].sum() if 'near_use' in camp_summary.columns else 0

    _unique_mailed = camp_acct[camp_acct['camp_status'] != 'Never Mailed']['primary_account_num'].nunique()
    _unique_resp = camp_acct[camp_acct['camp_status'] == 'Responder']['primary_account_num'].nunique()
    _overall_rate = _unique_resp / _unique_mailed * 100 if _unique_mailed > 0 else 0
    _num_mailers = len(camp_summary)

    # DID by segment (3mo pre vs 3mo post spend)
    _SEG_ORDER = ['NU', 'TH-10', 'TH-15', 'TH-20', 'TH-25']
    _did_by_seg = {}

    _valid_segs = [s for s in _SEG_ORDER if s in segment_cohort_raw['segment'].values]
    _extra_segs = [s for s in segment_cohort_raw['segment'].unique()
                   if s not in _SEG_ORDER and s != 'Unknown']
    _all_segs = _valid_segs + sorted(_extra_segs)

    # Use 3mo pre/post spend columns (m-1, m-2, m-3 vs m+1, m+2, m+3)
    _pre_cols = [c for c in segment_cohort_raw.columns if c.startswith('m-') and c[2:].lstrip('-').isdigit()
                 and 1 <= int(c[2:]) <= 3]
    _post_cols = [c for c in segment_cohort_raw.columns if c.startswith('m+') and c[2:].isdigit()
                  and 1 <= int(c[2:]) <= 3]

    for seg in _all_segs:
        _sd = segment_cohort_raw[segment_cohort_raw['segment'] == seg]
        _r = _sd[_sd['status'] == 'Responder']
        _nr = _sd[_sd['status'] == 'Non-Responder']
        if len(_r) < 5 or len(_nr) < 5:
            continue
        if len(_pre_cols) > 0 and len(_post_cols) > 0:
            r_pre = _r[_pre_cols].mean(axis=1).mean()
            r_post = _r[_post_cols].mean(axis=1).mean()
            nr_pre = _nr[_pre_cols].mean(axis=1).mean()
            nr_post = _nr[_post_cols].mean(axis=1).mean()
            _did_by_seg[seg] = (r_post - r_pre) - (nr_post - nr_pre)

    _avg_did = np.mean(list(_did_by_seg.values())) if _did_by_seg else 0

    # DID by segment for swipes
    _sw_pre_cols = [c for c in segment_cohort_raw.columns if c.startswith('sw-') and c[3:].isdigit()
                    and 1 <= int(c[3:]) <= 3]
    _sw_post_cols = [c for c in segment_cohort_raw.columns if c.startswith('sw+') and c[3:].isdigit()
                     and 1 <= int(c[3:]) <= 3]
    _did_swipes_by_seg = {}

    for seg in _all_segs:
        _sd = segment_cohort_raw[segment_cohort_raw['segment'] == seg]
        _r = _sd[_sd['status'] == 'Responder']
        _nr = _sd[_sd['status'] == 'Non-Responder']
        if len(_r) < 5 or len(_nr) < 5:
            continue
        if len(_sw_pre_cols) > 0 and len(_sw_post_cols) > 0:
            r_pre = _r[_sw_pre_cols].mean(axis=1).mean()
            r_post = _r[_sw_post_cols].mean(axis=1).mean()
            nr_pre = _nr[_sw_pre_cols].mean(axis=1).mean()
            nr_post = _nr[_sw_post_cols].mean(axis=1).mean()
            _did_swipes_by_seg[seg] = (r_post - r_pre) - (nr_post - nr_pre)

    # ------------------------------------------------------------------
    # Build figure
    # ------------------------------------------------------------------
    fig = plt.figure(figsize=(24, 14))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.6], hspace=0.25,
                          top=0.88, bottom=0.06, left=0.04, right=0.96)

    # =====================================================================
    # ROW 1: KPI Cards
    # =====================================================================
    gs_top = gs[0].subgridspec(1, 5, wspace=0.12)

    _kpis = [
        {
            'label': 'Total Mailings',
            'value': f'{_total_mailings:,}',
            'sub': f'{_num_mailers} mailers sent',
            'color': _WARNING,
        },
        {
            'label': 'Total Responses',
            'value': f'{_total_responses:,}',
            'sub': f'+ {_total_near_use:,} near-use (NU 1-4)',
            'color': _SUCCESS,
        },
        {
            'label': 'Unique Responders',
            'value': f'{_unique_resp:,}',
            'sub': f'of {_unique_mailed:,} unique accounts mailed',
            'color': _INFO,
        },
        {
            'label': 'Penetration Rate',
            'value': f'{_overall_rate:.1f}%',
            'sub': 'unique responders / unique mailed',
            'color': _ACCENT,
        },
        {
            'label': 'Avg DID Spend Lift',
            'value': f'${_avg_did:+,.0f}/mo' if _avg_did != 0 else 'N/A',
            'sub': 'per account vs non-responders',
            'color': _SUCCESS if _avg_did > 0 else _MUTED,
        },
    ]

    for i, kpi in enumerate(_kpis):
        ax = fig.add_subplot(gs_top[0, i])
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        card = FancyBboxPatch(
            (0.2, 0.2), 9.6, 9.6,
            boxstyle="round,pad=0.3",
            facecolor=kpi['color'], edgecolor='white', linewidth=3
        )
        ax.add_patch(card)

        ax.text(5, 7.0, kpi['label'],
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='white', alpha=0.9)
        ax.text(5, 4.5, kpi['value'],
                ha='center', va='center', fontsize=36, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.2, kpi['sub'],
                ha='center', va='center', fontsize=14,
                color='white', alpha=0.8, style='italic')

    # =====================================================================
    # ROW 2: DID by Segment (spend + swipes side by side)
    # =====================================================================
    gs_bot = gs[1].subgridspec(1, 2, wspace=0.25)

    # --- Left: DID Spend by Segment ---
    ax_spend = fig.add_subplot(gs_bot[0, 0])

    if _did_by_seg:
        _seg_labels = list(_did_by_seg.keys())
        _seg_vals = list(_did_by_seg.values())
        _seg_x = np.arange(len(_seg_labels))
        _seg_colors = [_SUCCESS if v > 0 else _ACCENT for v in _seg_vals]

        bars = ax_spend.bar(_seg_x, _seg_vals, width=0.6,
                            color=_seg_colors, edgecolor='white', linewidth=0.5)
        ax_spend.axhline(0, color=_MUTED, linewidth=1, zorder=1)

        # Avg line
        ax_spend.axhline(_avg_did, color=_DARK, linewidth=1.5, linestyle='--', zorder=2)
        ax_spend.text(len(_seg_x) - 0.5, _avg_did, f'  Avg: ${_avg_did:+,.0f}',
                      fontsize=14, fontweight='bold', color=_DARK, va='bottom', ha='right')

        for bar, val in zip(bars, _seg_vals):
            _va = 'bottom' if val >= 0 else 'top'
            _offset = max(abs(val) * 0.05, 1) if val >= 0 else -max(abs(val) * 0.05, 1)
            ax_spend.text(bar.get_x() + bar.get_width() / 2, val + _offset,
                          f'${val:+,.0f}', ha='center', va=_va, fontsize=14,
                          fontweight='bold', color=_DARK)

        ax_spend.set_xticks(_seg_x)
        ax_spend.set_xticklabels(_seg_labels, fontsize=14, fontweight='bold')
        ax_spend.set_ylabel('DID Spend Lift ($/mo per acct)', fontsize=16,
                            fontweight='bold', labelpad=8)
        ax_spend.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:+,.0f}"))
    else:
        ax_spend.text(0.5, 0.5, 'No DID spend data available',
                      ha='center', va='center', transform=ax_spend.transAxes,
                      fontsize=14, color=_MUTED)

    ax_spend.set_title('Spend Lift by Challenge Segment (DID)',
                        fontsize=16, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax_spend, keep_left=True, keep_bottom=True)
    ax_spend.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax_spend.set_axisbelow(True)

    # --- Right: DID Swipes by Segment ---
    ax_swipe = fig.add_subplot(gs_bot[0, 1])

    if _did_swipes_by_seg:
        _sw_labels = list(_did_swipes_by_seg.keys())
        _sw_vals = list(_did_swipes_by_seg.values())
        _sw_x = np.arange(len(_sw_labels))
        _sw_colors = [_SUCCESS if v > 0 else _ACCENT for v in _sw_vals]
        _avg_sw_did = np.mean(_sw_vals)

        bars = ax_swipe.bar(_sw_x, _sw_vals, width=0.6,
                            color=_sw_colors, edgecolor='white', linewidth=0.5)
        ax_swipe.axhline(0, color=_MUTED, linewidth=1, zorder=1)

        ax_swipe.axhline(_avg_sw_did, color=_DARK, linewidth=1.5, linestyle='--', zorder=2)
        ax_swipe.text(len(_sw_x) - 0.5, _avg_sw_did, f'  Avg: {_avg_sw_did:+,.1f}',
                      fontsize=14, fontweight='bold', color=_DARK, va='bottom', ha='right')

        for bar, val in zip(bars, _sw_vals):
            _va = 'bottom' if val >= 0 else 'top'
            _offset = max(abs(val) * 0.05, 0.2) if val >= 0 else -max(abs(val) * 0.05, 0.2)
            ax_swipe.text(bar.get_x() + bar.get_width() / 2, val + _offset,
                          f'{val:+,.1f}', ha='center', va=_va, fontsize=14,
                          fontweight='bold', color=_DARK)

        ax_swipe.set_xticks(_sw_x)
        ax_swipe.set_xticklabels(_sw_labels, fontsize=14, fontweight='bold')
        ax_swipe.set_ylabel('DID Swipe Lift (swipes/mo per acct)', fontsize=16,
                            fontweight='bold', labelpad=8)
        ax_swipe.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+,.1f}"))
    else:
        ax_swipe.text(0.5, 0.5, 'No DID swipe data available',
                      ha='center', va='center', transform=ax_swipe.transAxes,
                      fontsize=14, color=_MUTED)

    ax_swipe.set_title('Swipe Lift by Challenge Segment (DID)',
                        fontsize=16, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax_swipe, keep_left=True, keep_bottom=True)
    ax_swipe.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax_swipe.set_axisbelow(True)

    # Main title
    fig.suptitle('ARS Campaign: Full Program Summary',
                 fontsize=26, fontweight='bold', color=_DARK, y=0.96)
    fig.text(0.5, 0.925,
             f'{_num_mailers} mailers  |  3-month pre/post DID  |  All mailers pooled',
             ha='center', fontsize=14, color=_MUTED, style='italic')

    plt.show()

    # Console recap
    print(f"\n    ARS Program Summary:")
    print(f"      Mailers sent:       {_num_mailers}")
    print(f"      Total mailings:     {_total_mailings:,}")
    print(f"      Total responses:    {_total_responses:,}")
    print(f"      Near-use (NU 1-4):  {_total_near_use:,}")
    print(f"      Unique mailed:      {_unique_mailed:,}")
    print(f"      Unique responders:  {_unique_resp:,}")
    print(f"      Penetration rate:   {_overall_rate:.1f}%")
    if _did_by_seg:
        print(f"      Avg DID spend lift: ${_avg_did:+,.2f}/mo per account")
        for seg, val in _did_by_seg.items():
            print(f"        {seg}: ${val:+,.2f}/mo")
