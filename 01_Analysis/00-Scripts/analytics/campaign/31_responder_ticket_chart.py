# ===========================================================================
# RESPONDER TICKET SIZE: Do Responders Have Higher-Value Transactions?
# ===========================================================================
# Four-panel figure:
#   1. Avg ticket by status (all types)
#   2. Avg SIG ticket by status
#   3. Avg ticket by status × segment
#   4. Ticket distribution (histogram overlay)
#
# Depends on: resp_txn_profile, resp_txn_post (from cell 32)

if 'resp_txn_profile' not in dir() or len(resp_txn_profile) == 0:
    print("    No transaction profile data. Run cell 32 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')
    _RESP_COLOR = GEN_COLORS.get('success', '#2A9D8F')
    _NONRESP_COLOR = GEN_COLORS.get('warning', '#E9C46A')

    _has_segment = 'segment' in resp_txn_profile.columns
    _SEG_ORDER = ['NU', 'TH-10', 'TH-15', 'TH-20', 'TH-25']

    # =====================================================================
    # CHART 1: Avg Ticket + Txns/Month + Active Days (3-panel KPI)
    # =====================================================================
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 6))

    _status_order = ['Responder', 'Non-Responder']
    _colors = [_RESP_COLOR, _NONRESP_COLOR]

    # --- Panel 1: Avg ticket (all + SIG + PIN) ---
    _metrics = []
    for stat in _status_order:
        _d = resp_txn_profile[resp_txn_profile['camp_status'] == stat]
        _metrics.append({
            'All': _d['avg_ticket'].mean(),
            'SIG': _d['avg_sig_ticket'].mean(),
            'PIN': _d['avg_pin_ticket'].mean(),
        })

    _ticket_labels = ['All', 'SIG', 'PIN']
    x = np.arange(len(_ticket_labels))
    w = 0.35

    for i, (stat, color) in enumerate(zip(_status_order, _colors)):
        vals = [_metrics[i][t] for t in _ticket_labels]
        bars = ax1.bar(x + (i - 0.5) * w, vals, width=w * 0.9,
                       color=color, edgecolor='white', linewidth=0.5,
                       label=stat)
        for bar, val in zip(bars, vals):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                     f'${val:,.2f}', ha='center', va='bottom', fontsize=14,
                     fontweight='bold', color=color)

    ax1.set_xticks(x)
    ax1.set_xticklabels(_ticket_labels, fontsize=14, fontweight='bold')
    ax1.set_ylabel('Avg Ticket ($)', fontsize=16, fontweight='bold', labelpad=8)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax1.legend(fontsize=14, framealpha=0.9)
    ax1.set_title('Average Transaction Size', fontsize=20, fontweight='bold',
                   color=_DARK, pad=12)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax1.set_axisbelow(True)

    # --- Panel 2: Txns per month ---
    for i, (stat, color) in enumerate(zip(_status_order, _colors)):
        _d = resp_txn_profile[resp_txn_profile['camp_status'] == stat]
        val = _d['txns_per_month'].mean()
        bar = ax2.bar(i, val, color=color, edgecolor='white', linewidth=0.5, width=0.6)
        ax2.text(i, val + 0.3, f'{val:,.1f}', ha='center', va='bottom',
                 fontsize=14, fontweight='bold', color=color)

    ax2.set_xticks(range(len(_status_order)))
    ax2.set_xticklabels(['Resp', 'Non-R'], fontsize=14, fontweight='bold')
    ax2.set_ylabel('Transactions / Month', fontsize=16, fontweight='bold', labelpad=8)
    ax2.set_title('Monthly Transaction Frequency', fontsize=20, fontweight='bold',
                   color=_DARK, pad=12)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax2.set_axisbelow(True)

    # --- Panel 3: Active days per month ---
    for i, (stat, color) in enumerate(zip(_status_order, _colors)):
        _d = resp_txn_profile[resp_txn_profile['camp_status'] == stat]
        val = _d['active_days_per_month'].mean()
        bar = ax3.bar(i, val, color=color, edgecolor='white', linewidth=0.5, width=0.6)
        ax3.text(i, val + 0.15, f'{val:,.1f}', ha='center', va='bottom',
                 fontsize=14, fontweight='bold', color=color)

    ax3.set_xticks(range(len(_status_order)))
    ax3.set_xticklabels(['Resp', 'Non-R'], fontsize=14, fontweight='bold')
    ax3.set_ylabel('Unique Active Days / Month', fontsize=16, fontweight='bold', labelpad=8)
    ax3.set_title('Card Usage Spread', fontsize=20, fontweight='bold',
                   color=_DARK, pad=12)
    gen_clean_axes(ax3, keep_left=True, keep_bottom=True)
    ax3.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax3.set_axisbelow(True)

    fig.suptitle('Responders Use Their Card More Often, With Higher-Value Transactions',
                 fontsize=22, fontweight='bold', color=_DARK, y=1.03)
    plt.tight_layout()
    plt.show()

    # =====================================================================
    # CHART 2: Ticket Distribution (histogram overlay)
    # =====================================================================
    fig2, ax4 = plt.subplots(figsize=(14, 6))

    # Cap at 99th percentile for cleaner histogram
    _cap = resp_txn_profile['avg_ticket'].quantile(0.99)
    _bins = np.linspace(0, _cap, 50)

    for stat, color, alpha in [('Non-Responder', _NONRESP_COLOR, 0.5),
                                ('Responder', _RESP_COLOR, 0.7)]:
        _d = resp_txn_profile[resp_txn_profile['camp_status'] == stat]['avg_ticket']
        _d = _d[_d <= _cap]
        ax4.hist(_d, bins=_bins, alpha=alpha, color=color, edgecolor='white',
                 linewidth=0.3, label=f'{stat} ({len(_d):,})', density=True)

    # Median lines
    for stat, color, ls in [('Responder', _RESP_COLOR, '-'),
                             ('Non-Responder', _NONRESP_COLOR, '--')]:
        _med = resp_txn_profile[resp_txn_profile['camp_status'] == stat]['avg_ticket'].median()
        ax4.axvline(_med, color=color, linewidth=2.5, linestyle=ls, zorder=5)
        ax4.text(_med, ax4.get_ylim()[1] * 0.9, f'  Median: ${_med:,.0f}',
                 color=color, fontsize=14, fontweight='bold', va='top')

    ax4.set_xlabel('Average Ticket Size ($)', fontsize=16, fontweight='bold', labelpad=8)
    ax4.set_ylabel('Density', fontsize=16, fontweight='bold', labelpad=8)
    ax4.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax4.legend(fontsize=14, framealpha=0.9)
    ax4.set_title('Ticket Size Distribution: Responders Skew Higher',
                   fontsize=20, fontweight='bold', color=_DARK, pad=20, loc='left')
    ax4.text(0.0, 1.01, 'Per-account avg ticket, post-mail period',
             transform=ax4.transAxes, fontsize=14, color=_MUTED, style='italic')
    gen_clean_axes(ax4, keep_left=True, keep_bottom=True)
    ax4.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax4.set_axisbelow(True)

    plt.tight_layout()
    plt.show()

    # =====================================================================
    # CHART 3: Avg ticket by segment (if available)
    # =====================================================================
    if _has_segment:
        _segs = [s for s in _SEG_ORDER if s in resp_txn_profile['segment'].values]
        _extra = [s for s in resp_txn_profile['segment'].unique()
                  if s not in _SEG_ORDER and s != 'Unknown']
        _plot_segs = _segs + sorted(_extra)

        if len(_plot_segs) >= 2:
            fig3, ax5 = plt.subplots(figsize=(14, 6))

            x = np.arange(len(_plot_segs))
            w = 0.35

            for i, (stat, color) in enumerate(zip(_status_order, _colors)):
                vals = []
                for seg in _plot_segs:
                    _d = resp_txn_profile[
                        (resp_txn_profile['camp_status'] == stat) &
                        (resp_txn_profile['segment'] == seg)
                    ]
                    vals.append(_d['avg_ticket'].mean() if len(_d) > 0 else 0)

                bars = ax5.bar(x + (i - 0.5) * w, vals, width=w * 0.9,
                               color=color, edgecolor='white', linewidth=0.5,
                               label=stat)
                for bar, val in zip(bars, vals):
                    if val > 0:
                        ax5.text(bar.get_x() + bar.get_width() / 2,
                                 bar.get_height() + 0.5,
                                 f'${val:,.0f}', ha='center', va='bottom',
                                 fontsize=14, fontweight='bold', color=color)

            ax5.set_xticks(x)
            ax5.set_xticklabels(_plot_segs, fontsize=14, fontweight='bold')
            ax5.set_ylabel('Avg Ticket ($)', fontsize=16, fontweight='bold', labelpad=8)
            ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
            ax5.legend(fontsize=14, framealpha=0.9)
            ax5.set_title('Average Ticket Size by Challenge Segment',
                           fontsize=20, fontweight='bold', color=_DARK, pad=20, loc='left')
            ax5.text(0.0, 1.01,
                     'Do higher-challenge responders also spend more per swipe?',
                     transform=ax5.transAxes, fontsize=14, color=_MUTED, style='italic')
            gen_clean_axes(ax5, keep_left=True, keep_bottom=True)
            ax5.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
            ax5.set_axisbelow(True)

            plt.tight_layout()
            plt.show()
