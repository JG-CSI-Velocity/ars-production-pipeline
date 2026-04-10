# ===========================================================================
# PROGRAM EFFECTIVENESS: DCTR + IC Value + Benchmarks (Conference Edition)
# ===========================================================================
# (1) DCTR progression: historical vs L12M bar with pp delta arrow
# (2) Cumulative IC value area chart (incremental revenue over time)
# (3) Industry benchmark bars (CU vs PULSE benchmarks)
#
# Depends on: camp_acct, camp_summary, cohort_summary (cells 01, 10)
# Falls back to PULSE benchmarks if DCTR/RegE data unavailable

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

    # PULSE Industry Benchmarks (defaults)
    PULSE_ACTIVE_CARD_RATE = 66.3
    PULSE_REGE_AVG = 50.0
    AVG_ANNUAL_IC = 216  # $/card/yr

    # Compute CU metrics from available data
    n_total = len(rewards_df) if 'rewards_df' in dir() else len(camp_acct)
    n_with_debit_txns = combined_df['primary_account_num'].nunique() if 'combined_df' in dir() else n_total
    cu_active_rate = n_with_debit_txns / n_total * 100 if n_total > 0 else 0

    # RegE opt-in if available
    cu_rege = None
    if 'rewards_df' in dir():
        _rege_cols = [c for c in rewards_df.columns if 'Reg E' in c or 'reg_e' in c.lower()]
        if len(_rege_cols) > 0:
            _rege_vals = rewards_df[_rege_cols[0]]
            _opted = _rege_vals.astype(str).str.strip().str.upper().isin(['Y', 'YES', '1', 'TRUE', 'OPTED-IN'])
            cu_rege = _opted.sum() / len(_rege_vals) * 100

    # IC rate
    IC_RATE = 0.018

    fig = plt.figure(figsize=(20, 7))
    gs = fig.add_gridspec(1, 3, wspace=0.3)

    # -----------------------------------------------------------
    # Panel 1: Active Card Rate vs PULSE benchmark
    # -----------------------------------------------------------
    ax1 = fig.add_subplot(gs[0])

    labels = ['This CU', 'PULSE Avg']
    values = [cu_active_rate, PULSE_ACTIVE_CARD_RATE]
    colors = [_SUCCESS if cu_active_rate >= PULSE_ACTIVE_CARD_RATE else _ACCENT,
              _MUTED]

    bars = ax1.bar(labels, values, color=colors, edgecolor='white',
                   linewidth=1.5, width=0.45, zorder=3)

    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                 f"{val:.1f}%", ha='center', va='bottom',
                 fontsize=20, fontweight='bold', color=_DARK)

    delta = cu_active_rate - PULSE_ACTIVE_CARD_RATE
    ax1.text(0.5, max(values) * 0.5,
             f"{delta:+.1f}pp",
             ha='center', va='center', fontsize=18, fontweight='bold',
             color=_SUCCESS if delta >= 0 else _ACCENT,
             transform=ax1.get_xaxis_transform())

    ax1.set_ylabel("Active Card Rate (%)", fontsize=16, fontweight='bold')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax1.tick_params(axis='x', labelsize=16)
    ax1.set_ylim(0, max(values) * 1.25)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Debit Card Through Rate", fontsize=20, fontweight='bold',
                  color=_DARK, pad=14)

    # -----------------------------------------------------------
    # Panel 2: Cumulative IC Value over waves
    # -----------------------------------------------------------
    ax2 = fig.add_subplot(gs[1])

    if 'cohort_summary' in dir() and len(cohort_summary) > 0:
        cum_ic = []
        running = 0
        for _, row in cohort_summary.iterrows():
            # IC value = DID spend lift * IC rate * responders * 12 months
            ic_val = abs(row['did_spend_lift']) * IC_RATE * row['responded'] * 12
            running += ic_val
            cum_ic.append({'wave': row['wave'], 'cum_ic': running, 'wave_ic': ic_val})

        _ic_df = pd.DataFrame(cum_ic)
        x = np.arange(len(_ic_df))

        ax2.fill_between(x, _ic_df['cum_ic'], alpha=0.2, color=_SUCCESS)
        ax2.plot(x, _ic_df['cum_ic'], color=_SUCCESS, linewidth=3,
                 marker='o', markersize=8, markerfacecolor='white',
                 markeredgecolor=_SUCCESS, markeredgewidth=2.5, zorder=4)

        for i, row in _ic_df.iterrows():
            ax2.text(i, row['cum_ic'] + _ic_df['cum_ic'].max() * 0.04,
                     f"${row['cum_ic']:,.0f}",
                     ha='center', va='bottom', fontsize=14,
                     fontweight='bold', color=_SUCCESS)

        ax2.set_xticks(x)
        ax2.set_xticklabels(_ic_df['wave'], fontsize=14, fontweight='bold',
                           rotation=45, ha='right')
        ax2.set_ylabel("Cumulative IC Value", fontsize=16, fontweight='bold')
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
    else:
        ax2.text(0.5, 0.5, "Run cohort analysis\n(cell 10) first",
                 ha='center', va='center', fontsize=16, color=_MUTED,
                 transform=ax2.transAxes)

    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Cumulative IC Revenue", fontsize=20, fontweight='bold',
                  color=_DARK, pad=14)

    # -----------------------------------------------------------
    # Panel 3: Benchmark Comparison
    # -----------------------------------------------------------
    ax3 = fig.add_subplot(gs[2])

    bench_labels = ['Active Card\nRate']
    cu_vals = [cu_active_rate]
    pulse_vals = [PULSE_ACTIVE_CARD_RATE]

    if cu_rege is not None:
        bench_labels.append('Reg E\nOpt-In')
        cu_vals.append(cu_rege)
        pulse_vals.append(PULSE_REGE_AVG)

    x = np.arange(len(bench_labels))
    w = 0.3

    bars_cu = ax3.bar(x - w / 2, cu_vals, w, label='This CU',
                      color=_INFO, edgecolor='white', linewidth=1.5, zorder=3)
    bars_pulse = ax3.bar(x + w / 2, pulse_vals, w, label='PULSE Avg',
                         color=_MUTED, edgecolor='white', linewidth=1.5,
                         alpha=0.6, zorder=3)

    for bar, val in zip(bars_cu, cu_vals):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{val:.1f}%", ha='center', va='bottom',
                 fontsize=14, fontweight='bold', color=_INFO)
    for bar, val in zip(bars_pulse, pulse_vals):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{val:.1f}%", ha='center', va='bottom',
                 fontsize=14, fontweight='bold', color=_MUTED)

    ax3.set_xticks(x)
    ax3.set_xticklabels(bench_labels, fontsize=14, fontweight='bold')
    ax3.set_ylabel("Rate (%)", fontsize=16, fontweight='bold')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax3.legend(fontsize=14, framealpha=0.9)
    ax3.set_ylim(0, max(max(cu_vals), max(pulse_vals)) * 1.25)
    gen_clean_axes(ax3, keep_left=True, keep_bottom=True)
    ax3.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.7)
    ax3.set_axisbelow(True)
    ax3.set_title("Industry Benchmarks", fontsize=20, fontweight='bold',
                  color=_DARK, pad=14)

    fig.suptitle("Program Effectiveness Dashboard",
                 fontsize=28, fontweight='bold', color=_DARK, y=1.02)
    fig.text(0.5, 0.97,
             f"CU performance vs PULSE benchmarks  |  {DATASET_LABEL}",
             ha='center', fontsize=16, color=_MUTED, style='italic')

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()

    print(f"\n    Program Effectiveness:")
    print(f"      Active card rate: {cu_active_rate:.1f}% (PULSE avg: {PULSE_ACTIVE_CARD_RATE:.1f}%)")
    if cu_rege is not None:
        print(f"      Reg E opt-in:    {cu_rege:.1f}% (PULSE avg: {PULSE_REGE_AVG:.1f}%)")
