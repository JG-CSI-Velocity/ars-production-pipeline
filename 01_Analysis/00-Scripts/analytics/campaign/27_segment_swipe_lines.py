# ===========================================================================
# SEGMENT SWIPE LINES: Monthly Swipe Trajectory by Segment (Per-Mailer)
# ===========================================================================
# One figure per mailer wave. Each panel = one segment.
# Two lines per panel: Responder vs Non-Responder avg monthly swipes.
# X-axis: month offset relative to mail date. Vertical line at mail month.
#
# Depends on: segment_cohort_raw (cell 25), camp_summary (cell 01)

if 'segment_cohort_raw' not in dir() or len(segment_cohort_raw) == 0:
    print("    No segment cohort data. Run cell 25 first.")
else:
    _SEG_ORDER = ['NU', 'TH-10', 'TH-15', 'TH-20', 'TH-25']
    _SEG_COLORS = {
        'NU':    '#457B9D',
        'TH-10': '#2A9D8F',
        'TH-15': '#E9C46A',
        'TH-20': '#F4A261',
        'TH-25': '#E76F51',
    }

    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')
    _RESP_COLOR = GEN_COLORS.get('success', '#2A9D8F')
    _NONRESP_COLOR = GEN_COLORS.get('warning', '#E9C46A')

    # Identify swipe offset columns
    _swipe_cols = sorted(
        [c for c in segment_cohort_raw.columns if c.startswith('sw')],
        key=lambda c: int(c[2:])
    )
    _offsets = [int(c[2:]) for c in _swipe_cols]

    if len(_swipe_cols) < 3:
        print("    Not enough swipe months for line chart.")
        print(f"    Available sw columns: {[c for c in segment_cohort_raw.columns if c.startswith('sw')]}")
    else:
        _waves = (
            segment_cohort_raw[['wave', 'wave_date']]
            .drop_duplicates()
            .sort_values('wave_date')['wave']
            .tolist()
        )

        _available_segs = [s for s in _SEG_ORDER if s in segment_cohort_raw['segment'].values]
        _extra_segs = [s for s in segment_cohort_raw['segment'].unique()
                       if s not in _SEG_ORDER and s != 'Unknown']
        _all_segs = _available_segs + sorted(_extra_segs)

        if len(_all_segs) == 0:
            print("    No valid segments found.")
        else:
            n_panels = len(_all_segs)

            _camp_lookup = {}
            if 'camp_summary' in dir() and len(camp_summary) > 0:
                for _, _row in camp_summary.iterrows():
                    _camp_lookup[_row['period']] = _row

            for wave in _waves:
                _wdata = segment_cohort_raw[segment_cohort_raw['wave'] == wave]
                if len(_wdata) == 0:
                    continue

                _wave_sw_cols = [c for c in _swipe_cols if c in _wdata.columns and _wdata[c].notna().any()]
                _wave_offsets = [int(c[2:]) for c in _wave_sw_cols]
                if len(_wave_offsets) < 3:
                    continue

                fig, axes = plt.subplots(1, n_panels, figsize=(4 * n_panels, 5.5),
                                          squeeze=False, sharey=True)
                axes = axes[0]

                _wave_date = _wdata['wave_date'].iloc[0]
                _wave_label = _wave_date.strftime('%b %Y')

                _suptitle = f"Swipe Trajectory: {_wave_label}"
                if wave in _camp_lookup:
                    _ci = _camp_lookup[wave]
                    _suptitle += (f"   |   {int(_ci['mailed']):,} Mailed"
                                  f"   |   {int(_ci['responded']):,} Responded"
                                  f"   |   {_ci['response_rate']:.1f}% Rate")

                for s_idx, seg in enumerate(_all_segs):
                    ax = axes[s_idx]
                    _sdata = _wdata[_wdata['segment'] == seg]

                    for status, color, lw, marker in [
                        ('Responder', _RESP_COLOR, 2.5, 'o'),
                        ('Non-Responder', _NONRESP_COLOR, 2, 's'),
                    ]:
                        _grp = _sdata[_sdata['status'] == status]
                        n = len(_grp)
                        if n < 5:
                            continue
                        means = [_grp[c].mean() for c in _wave_sw_cols]
                        ax.plot(_wave_offsets, means, color=color, linewidth=lw,
                                marker=marker, markersize=4, markevery=3,
                                label=f'{status} ({n:,})', zorder=3)

                    ax.axvline(x=0, color=_DARK, linewidth=1.2, linestyle='--', alpha=0.5, zorder=2)
                    ax.text(0.3, 0.98, 'Mail', transform=ax.get_xaxis_transform(),
                            fontsize=14, color=_MUTED, va='top')

                    ax.set_title(seg, fontsize=20, fontweight='bold',
                                 color=_SEG_COLORS.get(seg, _DARK), pad=8)
                    ax.set_xlabel('Months from Mail', fontsize=16, fontweight='bold', labelpad=4)

                    if s_idx == 0:
                        ax.set_ylabel('Avg Monthly Swipes', fontsize=16,
                                      fontweight='bold', color=_DARK, labelpad=6)
                        ax.yaxis.set_major_formatter(plt.FuncFormatter(
                            lambda v, _: f"{v:,.0f}"
                        ))
                    ax.legend(fontsize=14, loc='upper left', framealpha=0.8)

                    gen_clean_axes(ax, keep_left=(s_idx == 0), keep_bottom=True)
                    ax.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
                    ax.set_axisbelow(True)

                fig.suptitle(_suptitle,
                             fontsize=18, fontweight='bold', color=_DARK, y=1.03)
                plt.tight_layout()
                plt.show()
