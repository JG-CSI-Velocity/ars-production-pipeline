# ===========================================================================
# RESPONDER SPEND SHIFT -- PIN vs SIG MIX (before vs after)
# ===========================================================================
# Grouped bars: SIG share of PIN+SIG transactions, PRE vs POST, Responders
# next to Non-Responders (control). Percentage-point change above POST bars.

if 'ss_summary' not in dir() or len(ss_summary) == 0:
    print("    No spend-shift data available. Skipping PIN/SIG chart.")
else:
    _ps = ss_summary.pivot_table(
        index='camp_status', columns='window', values='sig_share_pct',
    ).reindex(['Responder', 'Non-Responder']).dropna(how='all')

    if len(_ps) == 0 or 'PRE' not in _ps.columns or 'POST' not in _ps.columns:
        print("    Spend-shift summary lacks PRE/POST rows. Skipping PIN/SIG chart.")
    else:
        fig, ax = plt.subplots(figsize=(16, 8))
        x = np.arange(len(_ps))
        bar_w = 0.32

        _cohort_colors = {'Responder': GEN_COLORS['info'],
                          'Non-Responder': GEN_COLORS['warning']}
        for i, (_st, row) in enumerate(_ps.iterrows()):
            c = _cohort_colors.get(_st, GEN_COLORS['info'])
            ax.bar(i - bar_w / 2, row['PRE'], bar_w, color=c, alpha=0.45,
                   label='Before (3 mo pre-mail)' if i == 0 else None)
            ax.bar(i + bar_w / 2, row['POST'], bar_w, color=c,
                   label='After (3 mo post-mail)' if i == 0 else None)

            delta = row['POST'] - row['PRE']
            sign = '+' if delta >= 0 else ''
            dcolor = GEN_COLORS['success'] if delta >= 0 else GEN_COLORS['accent']
            ax.text(i + bar_w / 2, row['POST'] + 1.5,
                    f"{sign}{delta:.1f} pp", ha='center', va='bottom',
                    fontsize=16, fontweight='bold', color=dcolor)

        ax.set_xticks(x)
        ax.set_xticklabels(_ps.index, fontsize=14, fontweight='bold')
        ax.set_ylabel("SIG share of PIN+SIG transactions",
                      fontsize=16, fontweight='bold', labelpad=10)
        ax.set_ylim(0, min(100, _ps.to_numpy().max() * 1.35 + 10))

        gen_clean_axes(ax)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, p: f"{v:.0f}%"))
        ax.legend(loc='upper right', fontsize=14)

        ax.set_title("PIN vs SIG Mix: Before vs After the Offer",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02,
                f"Higher SIG share = more interchange revenue per swipe  "
                f"({DATASET_LABEL})",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['dark_text'], alpha=0.75)

        plt.tight_layout()
        plt.show()
