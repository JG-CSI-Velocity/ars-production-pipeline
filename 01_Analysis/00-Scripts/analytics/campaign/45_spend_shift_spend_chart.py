# ===========================================================================
# RESPONDER SPEND SHIFT -- SPEND CHART (avg monthly spend, before vs after)
# ===========================================================================
# Grouped bars: PRE vs POST avg monthly spend per account, Responders next to
# Non-Responders (the control). Delta labels above the POST bars.

if 'ss_summary' not in dir() or len(ss_summary) == 0:
    print("    No spend-shift data available. Skipping spend chart.")
else:
    _sp = ss_summary.pivot_table(
        index='camp_status', columns='window',
        values='avg_monthly_spend_per_acct',
    ).reindex(['Responder', 'Non-Responder']).dropna(how='all')
    _sn = ss_summary.pivot_table(
        index='camp_status', columns='window', values='n_accounts',
    ).reindex(_sp.index)

    if len(_sp) == 0 or 'PRE' not in _sp.columns or 'POST' not in _sp.columns:
        print("    Spend-shift summary lacks PRE/POST rows. Skipping spend chart.")
    else:
        fig, ax = plt.subplots(figsize=(16, 8))
        x = np.arange(len(_sp))
        bar_w = 0.32

        _cohort_colors = {'Responder': GEN_COLORS['info'],
                          'Non-Responder': GEN_COLORS['warning']}
        for i, (_st, row) in enumerate(_sp.iterrows()):
            c = _cohort_colors.get(_st, GEN_COLORS['info'])
            ax.bar(i - bar_w / 2, row['PRE'], bar_w,
                   color=c, alpha=0.45,
                   label='Before (3 mo pre-mail)' if i == 0 else None)
            ax.bar(i + bar_w / 2, row['POST'], bar_w,
                   color=c,
                   label='After (3 mo post-mail)' if i == 0 else None)

            delta = row['POST'] - row['PRE']
            pct = (delta / row['PRE'] * 100) if row['PRE'] else 0
            sign = '+' if delta >= 0 else ''
            dcolor = GEN_COLORS['success'] if delta >= 0 else GEN_COLORS['accent']
            ax.text(i + bar_w / 2, row['POST'] + ax.get_ylim()[1] * 0.02,
                    f"{sign}${delta:,.0f}/mo ({sign}{pct:.0f}%)",
                    ha='center', va='bottom', fontsize=15, fontweight='bold',
                    color=dcolor)

        _labels = [
            f"{st}\n(n={int(_sn.loc[st, 'PRE']):,})" if pd.notna(_sn.loc[st, 'PRE']) else st
            for st in _sp.index
        ]
        ax.set_xticks(x)
        ax.set_xticklabels(_labels, fontsize=14, fontweight='bold')
        ax.set_ylabel("Avg Monthly Spend per Account", fontsize=16,
                      fontweight='bold', labelpad=10)

        gen_clean_axes(ax)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, p: f"${v:,.0f}"))
        ax.legend(loc='upper right', fontsize=14)

        ax.set_title("Did the Offer Change Spending? Before vs After",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02,
                f"Each account anchored to its own mail/response month; "
                f"3 full months either side  ({DATASET_LABEL})",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['dark_text'], alpha=0.75)

        plt.tight_layout()
        plt.show()
