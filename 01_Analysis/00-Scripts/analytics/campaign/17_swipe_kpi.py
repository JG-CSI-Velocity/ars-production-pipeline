# ===========================================================================
# CAMPAIGN SWIPE KPI: Swipe Metrics by Campaign Status (Conference Edition)
# ===========================================================================
# 4 FancyBboxPatch cards. (18,5).
# Uses cohort_acct (from 11_cohort_lift_data) which has per-account
# pre/post swipe averages computed from MmmYY Swipes columns.

if 'cohort_acct' not in dir() or len(cohort_acct) == 0:
    print("    No cohort data available. Skipping swipe KPI dashboard.")
elif 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping swipe KPI dashboard.")
else:
    # Use most recent wave's data for each account (latest snapshot)
    _latest_wave = cohort_acct.sort_values('wave_date').drop_duplicates(
        subset='acct_number', keep='last'
    )

    _resp = _latest_wave[_latest_wave['status'] == 'Responder']
    _nonresp = _latest_wave[_latest_wave['status'] == 'Non-Responder']

    # Avg monthly swipes (post-period = current behavior)
    resp_avg_swipes = _resp['post_swipes'].mean() if len(_resp) > 0 else 0
    nonresp_avg_swipes = _nonresp['post_swipes'].mean() if len(_nonresp) > 0 else 0
    swipe_lift_pct = ((resp_avg_swipes - nonresp_avg_swipes) / nonresp_avg_swipes * 100) if nonresp_avg_swipes > 0 else 0

    # Swipe change: how much did swipes change pre->post?
    resp_swipe_change = (_resp['post_swipes'].mean() - _resp['pre_swipes'].mean()) if len(_resp) > 0 else 0
    nonresp_swipe_change = (_nonresp['post_swipes'].mean() - _nonresp['pre_swipes'].mean()) if len(_nonresp) > 0 else 0

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))

    kpi_data = [
        {
            'label': 'Responder Avg Swipes/Mo',
            'value': f"{resp_avg_swipes:.1f}",
            'sub': f"post-campaign avg, {len(_resp):,} responders",
            'color': GEN_COLORS['success'],
        },
        {
            'label': 'Non-Resp Avg Swipes/Mo',
            'value': f"{nonresp_avg_swipes:.1f}",
            'sub': f"post-campaign avg, {len(_nonresp):,} non-responders",
            'color': GEN_COLORS['warning'],
        },
        {
            'label': 'Swipe Lift',
            'value': f"{swipe_lift_pct:+.1f}%",
            'sub': "responder vs non-responder monthly swipes",
            'color': GEN_COLORS['accent'] if swipe_lift_pct > 0 else GEN_COLORS['muted'],
        },
        {
            'label': 'Resp Swipe Change',
            'value': f"{resp_swipe_change:+.1f}",
            'sub': f"pre-to-post change (non-resp: {nonresp_swipe_change:+.1f})",
            'color': GEN_COLORS['info'] if resp_swipe_change > 0 else GEN_COLORS['muted'],
        },
    ]

    for ax, kpi in zip(axes, kpi_data):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        card = FancyBboxPatch(
            (0.3, 0.3), 9.4, 9.4,
            boxstyle="round,pad=0.3",
            facecolor=kpi['color'], edgecolor='white', linewidth=3
        )
        ax.add_patch(card)

        ax.text(5, 6.8, kpi['label'],
                ha='center', va='center', fontsize=14, fontweight='bold',
                color='white', alpha=0.85)
        ax.text(5, 4.5, kpi['value'],
                ha='center', va='center', fontsize=42, fontweight='bold',
                color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground=kpi['color'])])
        ax.text(5, 2.3, kpi['sub'],
                ha='center', va='center', fontsize=14,
                color='white', alpha=0.8, style='italic')

    fig.suptitle("Campaign Swipe Behavior Overview",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.97, f"Monthly card usage metrics  |  {DATASET_LABEL}",
             ha='center', fontsize=14, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
