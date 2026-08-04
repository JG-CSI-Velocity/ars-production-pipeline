# ===========================================================================
# RESPONDER SPEND SHIFT -- VENDOR MIX (where responders spend, before vs after)
# ===========================================================================
# Two panels of horizontal bars: top-10 merchants by responder spend in the
# PRE window vs the POST window. Merchants that were absent from the PRE
# window are flagged NEW in the POST panel.

if 'ss_vendor_shift' not in dir() or len(ss_vendor_shift) == 0:
    print("    No spend-shift vendor data available. Skipping vendor chart.")
else:
    _pre_top = ss_vendor_shift.sort_values('PRE', ascending=False).head(10)
    _post_top = ss_vendor_shift.sort_values('POST', ascending=False).head(10)
    _pre_top = _pre_top[_pre_top['PRE'] > 0]
    _post_top = _post_top[_post_top['POST'] > 0]

    if len(_pre_top) == 0 and len(_post_top) == 0:
        print("    No responder vendor spend in either window. Skipping vendor chart.")
    else:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

        def _panel(ax, frame, col, title, base_color):
            frame = frame.iloc[::-1]  # largest at top
            labels = [str(m)[:32] for m in frame.index]
            colors = [
                GEN_COLORS['success'] if (col == 'POST' and s == 'NEW') else base_color
                for s in frame['shift']
            ]
            bars = ax.barh(labels, frame[col], color=colors)
            for bar, (_, row) in zip(bars, frame.iterrows()):
                suffix = "  NEW" if (col == 'POST' and row['shift'] == 'NEW') else ""
                ax.text(bar.get_width() * 1.01, bar.get_y() + bar.get_height() / 2,
                        f"${row[col]:,.0f}{suffix}", va='center',
                        fontsize=12, fontweight='bold',
                        color=GEN_COLORS['dark_text'])
            ax.set_title(title, fontsize=18, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=12, loc='left')
            gen_clean_axes(ax)
            ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)
            ax.tick_params(axis='y', labelsize=12)
            ax.xaxis.set_major_formatter(
                mticker.FuncFormatter(lambda v, p: f"${v/1000:,.0f}K" if v >= 1000 else f"${v:,.0f}"))

        _panel(ax1, _pre_top, 'PRE',
               "BEFORE the offer (3 mo pre-mail)", GEN_COLORS['info'])
        _panel(ax2, _post_top, 'POST',
               "AFTER the offer (3 mo post-mail)", GEN_COLORS['info'])

        fig.suptitle("Where Responders Spend: Before vs After the Offer",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], x=0.02, ha='left')

        plt.tight_layout(rect=[0, 0, 1, 0.93])
        plt.show()
