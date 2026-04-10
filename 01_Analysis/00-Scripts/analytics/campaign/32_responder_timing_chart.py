# ===========================================================================
# RESPONDER TIMING: When Do Responders Swipe? Early & Often?
# ===========================================================================
# Three charts exploring WHEN responders use their card:
#   1. Day-of-month distribution (early/mid/late month)
#   2. Day-of-week pattern (weekday vs weekend)
#   3. Month-part breakdown (do responders front-load activity?)
#
# Depends on: resp_dom_dist, resp_dow_dist, resp_mpart_dist (from cell 32)

if 'resp_dom_dist' not in dir() or len(resp_dom_dist) == 0:
    print("    No timing distribution data. Run cell 32 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')
    _RESP_COLOR = GEN_COLORS.get('success', '#2A9D8F')
    _NONRESP_COLOR = GEN_COLORS.get('warning', '#E9C46A')

    _status_colors = {'Responder': _RESP_COLOR, 'Non-Responder': _NONRESP_COLOR}

    # =====================================================================
    # CHART 1: Day-of-Month Distribution (line overlay)
    # =====================================================================
    fig1, ax1 = plt.subplots(figsize=(16, 6))

    for stat in ['Responder', 'Non-Responder']:
        _d = resp_dom_dist[resp_dom_dist['camp_status'] == stat].sort_values('day_of_month')
        if len(_d) == 0:
            continue
        color = _status_colors[stat]
        n_accts = resp_txn_profile[resp_txn_profile['camp_status'] == stat]['primary_account_num'].nunique()
        ax1.plot(_d['day_of_month'], _d['pct'], color=color, linewidth=2.5,
                 marker='o', markersize=4, label=f'{stat} ({n_accts:,})', zorder=3)
        # Shade area
        ax1.fill_between(_d['day_of_month'], _d['pct'], alpha=0.1, color=color)

    # Mark month thirds
    for boundary, label in [(10.5, ''), (20.5, '')]:
        ax1.axvline(boundary, color=_MUTED, linewidth=1, linestyle=':', alpha=0.5)

    ax1.text(5.5, ax1.get_ylim()[1] * 0.95, 'Early', ha='center',
             fontsize=14, color=_MUTED, fontweight='bold')
    ax1.text(15.5, ax1.get_ylim()[1] * 0.95, 'Mid', ha='center',
             fontsize=14, color=_MUTED, fontweight='bold')
    ax1.text(26, ax1.get_ylim()[1] * 0.95, 'Late', ha='center',
             fontsize=14, color=_MUTED, fontweight='bold')

    ax1.set_xlabel('Day of Month', fontsize=16, fontweight='bold', labelpad=8)
    ax1.set_ylabel('% of Transactions', fontsize=16, fontweight='bold', labelpad=8)
    ax1.set_xticks(range(1, 32))
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax1.legend(fontsize=14, framealpha=0.9)
    ax1.set_title('When in the Month Do Responders Swipe?',
                   fontsize=20, fontweight='bold', color=_DARK, pad=20, loc='left')
    ax1.text(0.0, 1.01,
             'Transaction distribution by day of month, post-mail period',
             transform=ax1.transAxes, fontsize=14, color=_MUTED, style='italic')
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax1.set_axisbelow(True)

    plt.tight_layout()
    plt.show()

    # Quantify early-month bias
    for stat in ['Responder', 'Non-Responder']:
        _d = resp_dom_dist[resp_dom_dist['camp_status'] == stat]
        _early = _d[_d['day_of_month'] <= 10]['pct'].sum()
        _mid = _d[(_d['day_of_month'] > 10) & (_d['day_of_month'] <= 20)]['pct'].sum()
        _late = _d[_d['day_of_month'] > 20]['pct'].sum()
        print(f"    {stat}: Early {_early:.1f}%  |  Mid {_mid:.1f}%  |  Late {_late:.1f}%")

    # =====================================================================
    # CHART 2: Day-of-Week Pattern (grouped bar)
    # =====================================================================
    fig2, ax2 = plt.subplots(figsize=(14, 6))

    _dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    _dow_short = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    x = np.arange(7)
    w = 0.35

    for i, stat in enumerate(['Responder', 'Non-Responder']):
        _d = resp_dow_dist[resp_dow_dist['camp_status'] == stat].sort_values('day_of_week')
        if len(_d) == 0:
            continue
        color = _status_colors[stat]
        vals = [_d[_d['day_of_week'] == dow]['pct'].values[0]
                if dow in _d['day_of_week'].values else 0
                for dow in range(7)]
        n_accts = resp_txn_profile[resp_txn_profile['camp_status'] == stat]['primary_account_num'].nunique()
        ax2.bar(x + (i - 0.5) * w, vals, width=w * 0.9,
                color=color, edgecolor='white', linewidth=0.5,
                label=f'{stat} ({n_accts:,})')

    # Weekend shading
    ax2.axvspan(4.5, 6.5, alpha=0.06, color=_DARK, zorder=0)
    ax2.text(5.5, ax2.get_ylim()[1] * 0.02, 'Weekend', ha='center',
             fontsize=14, color=_MUTED, style='italic')

    ax2.set_xticks(x)
    ax2.set_xticklabels(_dow_short, fontsize=14, fontweight='bold')
    ax2.set_ylabel('% of Transactions', fontsize=16, fontweight='bold', labelpad=8)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax2.legend(fontsize=14, framealpha=0.9)
    ax2.set_title('Day-of-Week Swipe Pattern',
                   fontsize=20, fontweight='bold', color=_DARK, pad=20, loc='left')
    ax2.text(0.0, 1.01,
             'Do responders favor certain days?  Post-mail period',
             transform=ax2.transAxes, fontsize=14, color=_MUTED, style='italic')
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax2.set_axisbelow(True)

    plt.tight_layout()
    plt.show()

    # =====================================================================
    # CHART 3: Early / Mid / Late Month Breakdown (stacked bar)
    # =====================================================================
    fig3, ax3 = plt.subplots(figsize=(10, 6))

    _parts = ['Early (1-10)', 'Mid (11-20)', 'Late (21-31)']
    _part_colors = [GEN_COLORS.get('info', '#457B9D'),
                    GEN_COLORS.get('success', '#2A9D8F'),
                    GEN_COLORS.get('warning', '#E9C46A')]

    _status_list = ['Responder', 'Non-Responder']
    _bar_data = {}
    for stat in _status_list:
        _d = resp_mpart_dist[resp_mpart_dist['camp_status'] == stat]
        _bar_data[stat] = {p: _d[_d['month_part'] == p]['pct'].values[0]
                           if p in _d['month_part'].values else 0
                           for p in _parts}

    x = np.arange(len(_status_list))
    bottom = np.zeros(len(_status_list))

    for p_idx, part in enumerate(_parts):
        vals = [_bar_data[s][part] for s in _status_list]
        bars = ax3.bar(x, vals, bottom=bottom, width=0.5,
                       color=_part_colors[p_idx], edgecolor='white', linewidth=0.5,
                       label=part)
        for j, (bar, val) in enumerate(zip(bars, vals)):
            if val > 3:
                ax3.text(bar.get_x() + bar.get_width() / 2,
                         bottom[j] + val / 2,
                         f'{val:.1f}%', ha='center', va='center',
                         fontsize=14, fontweight='bold', color='white')
        bottom += vals

    ax3.set_xticks(x)
    ax3.set_xticklabels(['Responders', 'Non-Responders'], fontsize=14, fontweight='bold')
    ax3.set_ylabel('% of Transactions', fontsize=16, fontweight='bold', labelpad=8)
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax3.legend(fontsize=14, framealpha=0.9, loc='upper right')
    ax3.set_title('Month-Part Activity: Do Responders Front-Load?',
                   fontsize=20, fontweight='bold', color=_DARK, pad=20, loc='left')
    ax3.text(0.0, 1.01,
             'Early = days 1-10, Mid = 11-20, Late = 21-31  |  Post-mail period',
             transform=ax3.transAxes, fontsize=14, color=_MUTED, style='italic')
    gen_clean_axes(ax3, keep_left=True, keep_bottom=True)

    plt.tight_layout()
    plt.show()

    # Summary insight
    if len(_bar_data) >= 2:
        _r_early = _bar_data['Responder']['Early (1-10)']
        _nr_early = _bar_data['Non-Responder']['Early (1-10)']
        if _r_early > _nr_early:
            print(f"\n    Responders front-load: {_r_early:.1f}% early-month vs "
                  f"{_nr_early:.1f}% for non-responders ({_r_early - _nr_early:+.1f} pp)")
        else:
            print(f"\n    No early-month bias detected "
                  f"(Resp: {_r_early:.1f}% vs Non-R: {_nr_early:.1f}%)")
