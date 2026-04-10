# ===========================================================================
# COHORT BEFORE/AFTER: Responder vs Non-Responder Spend Change (Conf. Ed.)
# ===========================================================================
# Grouped bar chart: for each wave, pre vs post avg monthly spend
# for Responders and Non-Responders side by side. (16,8).

if 'cohort_summary' not in dir() or len(cohort_summary) == 0:
    print("    No cohort data available. Skipping before/after chart.")
else:
    n_waves = len(cohort_summary)
    fig, ax = plt.subplots(figsize=(16, 8))

    x = np.arange(n_waves)
    bar_w = 0.18

    # Responder pre/post
    bars_r_pre = ax.bar(x - 1.5 * bar_w, cohort_summary['resp_pre_spend'],
                        bar_w, label='Responder PRE', color=GEN_COLORS['info'], alpha=0.5)
    bars_r_post = ax.bar(x - 0.5 * bar_w, cohort_summary['resp_post_spend'],
                         bar_w, label='Responder POST', color=GEN_COLORS['info'])

    # Non-responder pre/post
    bars_n_pre = ax.bar(x + 0.5 * bar_w, cohort_summary['nonresp_pre_spend'],
                        bar_w, label='Non-Resp PRE', color=GEN_COLORS['warning'], alpha=0.5)
    bars_n_post = ax.bar(x + 1.5 * bar_w, cohort_summary['nonresp_post_spend'],
                         bar_w, label='Non-Resp POST', color=GEN_COLORS['warning'])

    ax.set_xticks(x)
    ax.set_xticklabels(cohort_summary['wave'], fontsize=14, fontweight='bold')
    ax.set_ylabel("Avg Monthly Spend per Account", fontsize=16, fontweight='bold', labelpad=10)

    gen_clean_axes(ax)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))

    # Annotate deltas above responder post bars
    for i, (_, row) in enumerate(cohort_summary.iterrows()):
        delta = row['resp_spend_delta']
        sign = '+' if delta >= 0 else ''
        color = GEN_COLORS['success'] if delta >= 0 else GEN_COLORS['accent']
        ax.text(i - 0.5 * bar_w, row['resp_post_spend'] + ax.get_ylim()[1] * 0.015,
                f"{sign}${delta:,.0f}", ha='center', va='bottom',
                fontsize=14, fontweight='bold', color=color)

        # Non-resp delta
        nd = row['nonresp_spend_delta']
        nsign = '+' if nd >= 0 else ''
        ncolor = GEN_COLORS['success'] if nd >= 0 else GEN_COLORS['accent']
        ax.text(i + 1.5 * bar_w, row['nonresp_post_spend'] + ax.get_ylim()[1] * 0.015,
                f"{nsign}${nd:,.0f}", ha='center', va='bottom',
                fontsize=14, fontweight='bold', color=ncolor)

    ax.legend(loc='upper right', fontsize=14, ncol=2)

    ax.set_title("Before vs After: Spend Change by Mail Wave",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02,
            f"Responders show different trajectory than non-responders  ({DATASET_LABEL})",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
