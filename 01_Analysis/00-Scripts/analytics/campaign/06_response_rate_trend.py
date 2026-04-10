# ===========================================================================
# RESPONSE RATE TREND: Stacked Count + Rate Lines (Conference Edition)
# ===========================================================================
# Chart 1: Stacked bar of responder count by segment per wave
# Chart 2: Multi-line response rate trend by segment across waves
#
# Depends on: camp_summary, rewards_df, mail_cols, resp_cols (cell 01)

if 'camp_summary' not in dir() or len(camp_summary) == 0:
    print("    No campaign summary. Run cell 01 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
    _INFO = GEN_COLORS.get('info', '#457B9D')
    _WARNING = GEN_COLORS.get('warning', '#E9C46A')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')
    _PRIMARY = GEN_COLORS.get('primary', '#264653')

    _seg_colors = {
        'NU': _SUCCESS, 'TH-10': _INFO, 'TH-15': _WARNING,
        'TH-20': _ACCENT, 'TH-25': _PRIMARY,
        'TH (All)': _INFO, 'Unknown': _MUTED,
    }

    def _parse_seg(val):
        if pd.isna(val):
            return None
        v = str(val).strip().upper()
        if v.startswith('TH-'):
            return v
        if v.startswith('TH') and len(v) > 2 and v[2:].strip('-').isdigit():
            return f"TH-{v[2:].strip('-')}"
        if v in ('NU 5+', 'NU5+', 'NU 5', 'NU 6', 'NU 7', 'NU 8', 'NU 9', 'NU 10'):
            return 'NU'
        if v in ('10', '15', '20', '25'):
            return f"TH-{v}"
        return None

    def _is_success(val):
        if pd.isna(val):
            return False
        v = str(val).strip().upper()
        return v.startswith('TH') or v in ('NU 5+', 'NU5+', 'NU 5', 'NU 6',
                                            'NU 7', 'NU 8', 'NU 9', 'NU 10')

    # Build wave x segment matrix
    wave_labels = []
    seg_resp_matrix = {}
    wave_mailed_counts = {}

    for mc, rc in zip(mail_cols, resp_cols):
        period = mc.replace(' Mail', '')
        was_mailed = rewards_df[mc].notna()
        n_mailed_w = was_mailed.sum()
        if n_mailed_w == 0:
            continue

        wave_labels.append(period)
        wave_mailed_counts[period] = n_mailed_w

        resp_vals = rewards_df.loc[was_mailed, rc]
        success_mask = resp_vals.map(_is_success)
        seg_series = resp_vals[success_mask].map(_parse_seg)
        seg_counts = seg_series.value_counts()

        for seg, cnt in seg_counts.items():
            if seg not in seg_resp_matrix:
                seg_resp_matrix[seg] = {}
            seg_resp_matrix[seg][period] = cnt

    if len(wave_labels) < 2:
        print("    Need 2+ waves for trend. Skipping.")
    else:
        all_segs = sorted(seg_resp_matrix.keys(),
                         key=lambda s: sum(seg_resp_matrix[s].values()), reverse=True)

        # -----------------------------------------------------------
        # Chart 1: Stacked bar of responder counts by segment
        # -----------------------------------------------------------
        fig, ax = plt.subplots(figsize=(16, 7))
        x = np.arange(len(wave_labels))
        bar_width = 0.5
        bottoms = np.zeros(len(wave_labels))

        for seg in all_segs:
            vals = [seg_resp_matrix.get(seg, {}).get(w, 0) for w in wave_labels]
            color = _seg_colors.get(seg, _MUTED)
            ax.bar(x, vals, bar_width, bottom=bottoms, label=seg,
                   color=color, edgecolor='white', linewidth=1)
            bottoms += np.array(vals)

        # Total labels on top
        for i, total in enumerate(bottoms):
            ax.text(i, total + bottoms.max() * 0.02,
                    f"{int(total):,}", ha='center', va='bottom',
                    fontsize=15, fontweight='bold', color=_DARK)

        ax.set_xticks(x)
        ax.set_xticklabels(wave_labels, fontsize=14, fontweight='bold')
        ax.set_ylabel("Responder Count", fontsize=16, fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
        ax.legend(fontsize=14, loc='upper left', framealpha=0.9)
        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.yaxis.grid(True, color=GEN_COLORS.get('grid', '#E0E0E0'),
                      linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        fig.suptitle("Responder Count by Segment per Wave",
                     fontsize=28, fontweight='bold', color=_DARK, y=0.98)
        fig.text(0.5, 0.93,
                 f"Stacked by challenge segment  |  {DATASET_LABEL}",
                 ha='center', fontsize=16, color=_MUTED, style='italic')

        plt.tight_layout(rect=[0, 0, 1, 0.91])
        plt.show()

        # -----------------------------------------------------------
        # Chart 2: Response rate trend lines by segment
        # -----------------------------------------------------------
        fig, ax = plt.subplots(figsize=(16, 7))

        markers = ['o', 's', '^', 'D', 'v', 'P']
        for idx, seg in enumerate(all_segs):
            rates = []
            for w in wave_labels:
                resp_cnt = seg_resp_matrix.get(seg, {}).get(w, 0)
                mailed_cnt = wave_mailed_counts.get(w, 1)
                rates.append(resp_cnt / mailed_cnt * 100)

            color = _seg_colors.get(seg, _MUTED)
            marker = markers[idx % len(markers)]
            ax.plot(x, rates, color=color, linewidth=3, marker=marker,
                    markersize=9, markerfacecolor='white',
                    markeredgecolor=color, markeredgewidth=2.5,
                    label=seg, zorder=4)

            # End label
            ax.text(x[-1] + 0.15, rates[-1],
                    f"{rates[-1]:.1f}%", ha='left', va='center',
                    fontsize=14, fontweight='bold', color=color)

        # Overall rate line
        overall_rates = []
        for w in wave_labels:
            total_resp_w = sum(seg_resp_matrix.get(s, {}).get(w, 0) for s in all_segs)
            overall_rates.append(total_resp_w / wave_mailed_counts.get(w, 1) * 100)

        ax.plot(x, overall_rates, color=_MUTED, linewidth=2.5,
                linestyle='--', alpha=0.7, label='Overall', zorder=3)

        ax.set_xticks(x)
        ax.set_xticklabels(wave_labels, fontsize=14, fontweight='bold')
        ax.set_ylabel("Response Rate (%)", fontsize=16, fontweight='bold')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        ax.legend(fontsize=14, loc='best', framealpha=0.9)
        gen_clean_axes(ax, keep_left=True, keep_bottom=True)
        ax.yaxis.grid(True, color=GEN_COLORS.get('grid', '#E0E0E0'),
                      linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)

        fig.suptitle("Response Rate Trend by Segment",
                     fontsize=28, fontweight='bold', color=_DARK, y=0.98)
        fig.text(0.5, 0.93,
                 f"Which segments are improving?  |  {DATASET_LABEL}",
                 ha='center', fontsize=16, color=_MUTED, style='italic')

        plt.tight_layout(rect=[0, 0, 1, 0.91])
        plt.show()
