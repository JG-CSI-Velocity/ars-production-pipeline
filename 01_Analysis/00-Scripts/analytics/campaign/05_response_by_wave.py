# ===========================================================================
# RESPONSE BY WAVE: Per-Wave Composite (Conference Edition)
# ===========================================================================
# For each wave + all-time aggregate:
#   Left: donut chart (response share by segment)
#   Right: horizontal bar (response rate by segment)
#
# Depends on: camp_summary, camp_acct, rewards_df, mail_cols, resp_cols (cell 01)

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
elif 'camp_summary' not in dir() or len(camp_summary) == 0:
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

    # Parse response values per wave to get segment breakdown
    _MONTH_ABBR = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                   'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

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

    rewards_cols_clean = [c.strip() for c in rewards_df.columns]

    # Build per-wave segment data
    wave_seg_data = []

    for mc, rc in zip(mail_cols, resp_cols):
        period_label = mc.replace(' Mail', '')
        was_mailed = rewards_df[mc].notna()
        n_mailed_w = was_mailed.sum()
        if n_mailed_w == 0:
            continue

        resp_vals = rewards_df.loc[was_mailed, rc]
        seg_series = resp_vals.map(_parse_seg)
        success_mask = resp_vals.map(_is_success)

        # Segment counts (responders only)
        seg_counts = seg_series[success_mask].value_counts()

        # Segment response rates (mailed by segment based on mail column)
        mail_seg = rewards_df.loc[was_mailed, mc].map(_parse_seg)
        for seg in seg_counts.index:
            n_mailed_seg = (mail_seg == seg).sum() + (
                (mail_seg.isna()) & (seg_series == seg) & success_mask
            ).sum()
            if n_mailed_seg == 0:
                n_mailed_seg = n_mailed_w

            wave_seg_data.append({
                'wave': period_label,
                'segment': seg,
                'responded': int(seg_counts.get(seg, 0)),
                'mailed': int(n_mailed_seg),
                'rate': seg_counts.get(seg, 0) / n_mailed_w * 100,
            })

    if len(wave_seg_data) == 0:
        print("    No segment-level response data found.")
    else:
        _wsd = pd.DataFrame(wave_seg_data)
        waves = _wsd['wave'].unique()

        for wave in waves:
            _wd = _wsd[_wsd['wave'] == wave].copy()
            if len(_wd) == 0:
                continue

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7),
                                            gridspec_kw={'width_ratios': [1, 1.3]})

            # Left: Donut chart
            sizes = _wd['responded'].values
            labels = _wd['segment'].values
            colors = [_seg_colors.get(s, _MUTED) for s in labels]
            total_resp = sizes.sum()

            wedges, texts, autotexts = ax1.pie(
                sizes, labels=None, autopct='',
                colors=colors, startangle=90, pctdistance=0.78,
                wedgeprops={'width': 0.45, 'edgecolor': 'white', 'linewidth': 2}
            )

            # Center text
            ax1.text(0, 0.05, f"{total_resp:,}", ha='center', va='center',
                     fontsize=32, fontweight='bold', color=_DARK)
            ax1.text(0, -0.15, 'Responded', ha='center', va='center',
                     fontsize=16, color=_MUTED, fontweight='bold')

            # Legend
            ax1.legend(
                [f"{l}: {s:,} ({s/total_resp*100:.0f}%)" for l, s in zip(labels, sizes)],
                loc='lower center', fontsize=14, frameon=False,
                bbox_to_anchor=(0.5, -0.15), ncol=2
            )

            # Right: Horizontal bar (response share by segment)
            _wd_sorted = _wd.sort_values('responded', ascending=True)
            y_pos = range(len(_wd_sorted))
            bar_colors = [_seg_colors.get(s, _MUTED) for s in _wd_sorted['segment']]

            bars = ax2.barh(list(y_pos), _wd_sorted['responded'],
                           color=bar_colors, edgecolor='white',
                           linewidth=1.5, height=0.6, zorder=3)

            ax2.set_yticks(list(y_pos))
            ax2.set_yticklabels(_wd_sorted['segment'], fontsize=14, fontweight='bold')

            max_val = _wd_sorted['responded'].max()
            for j, (val, seg) in enumerate(zip(_wd_sorted['responded'],
                                               _wd_sorted['segment'])):
                pct = val / total_resp * 100 if total_resp > 0 else 0
                ax2.text(val + max_val * 0.02, j,
                         f"{val:,} ({pct:.0f}%)",
                         va='center', fontsize=14, fontweight='bold',
                         color=_seg_colors.get(seg, _MUTED))

            ax2.set_xlabel("Responder Count", fontsize=16, fontweight='bold')
            ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
            ax2.set_xlim(0, max_val * 1.35)
            gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
            ax2.xaxis.grid(True, color=GEN_COLORS.get('grid', '#E0E0E0'),
                          linewidth=0.5, alpha=0.7)
            ax2.set_axisbelow(True)

            fig.suptitle(f"Response Breakdown: {wave}",
                         fontsize=28, fontweight='bold', color=_DARK, y=0.98)
            fig.text(0.5, 0.93,
                     f"Segment distribution of responders  |  {DATASET_LABEL}",
                     ha='center', fontsize=16, color=_MUTED, style='italic')

            plt.tight_layout(rect=[0, 0, 1, 0.91])
            plt.show()

        # Print summary
        _totals = _wsd.groupby('segment')['responded'].sum().sort_values(ascending=False)
        print(f"\n    All-wave response by segment:")
        for seg, cnt in _totals.items():
            print(f"      {seg}: {cnt:,}")
