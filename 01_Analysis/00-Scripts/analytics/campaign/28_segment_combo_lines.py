# ===========================================================================
# SEGMENT COMBO LINES: Spend + Swipe Trajectories Combined (Per-Mailer)
# ===========================================================================
# One figure per mailer wave: 2 rows × N segment columns.
# Row 1: Avg Monthly Spend trajectory.  Row 2: Avg Monthly Swipe trajectory.
# Two lines per panel: Responder vs Non-Responder.
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

    # Spend + swipe columns
    _spend_cols = sorted(
        [c for c in segment_cohort_raw.columns if c.startswith('m') and ('+' in c or '-' in c)],
        key=lambda c: int(c[1:])
    )
    _swipe_cols = sorted(
        [c for c in segment_cohort_raw.columns if c.startswith('sw')],
        key=lambda c: int(c[2:])
    )

    _has_spend = len(_spend_cols) >= 3
    _has_swipes = len(_swipe_cols) >= 3

    if not _has_spend and not _has_swipes:
        print("    Not enough data for combo line chart.")
    else:
        # Row configs: (col_list, offset_parser, ylabel, y_fmt)
        _row_configs = []
        if _has_spend:
            _row_configs.append((_spend_cols, lambda c: int(c[1:]),
                                 'Avg Monthly Spend ($)', lambda v, _: f"${v:,.0f}"))
        if _has_swipes:
            _row_configs.append((_swipe_cols, lambda c: int(c[2:]),
                                 'Avg Monthly Swipes', lambda v, _: f"{v:,.0f}"))

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
            n_rows = len(_row_configs)

            _camp_lookup = {}
            if 'camp_summary' in dir() and len(camp_summary) > 0:
                for _, _row in camp_summary.iterrows():
                    _camp_lookup[_row['period']] = _row

            for wave in _waves:
                _wdata = segment_cohort_raw[segment_cohort_raw['wave'] == wave]
                if len(_wdata) == 0:
                    continue

                fig, axes = plt.subplots(n_rows, n_panels,
                                          figsize=(4 * n_panels, 4.5 * n_rows),
                                          squeeze=False)

                _wave_date = _wdata['wave_date'].iloc[0]
                _wave_label = _wave_date.strftime('%b %Y')

                _suptitle = f"Spend + Swipe Trajectory: {_wave_label}"
                if wave in _camp_lookup:
                    _ci = _camp_lookup[wave]
                    _suptitle += (f"   |   {int(_ci['mailed']):,} Mailed"
                                  f"   |   {int(_ci['responded']):,} Responded"
                                  f"   |   {_ci['response_rate']:.1f}% Rate")

                for r_idx, (cols, offset_fn, ylabel, y_fmt) in enumerate(_row_configs):
                    # Filter to columns with data for this wave
                    _wave_cols = [c for c in cols if c in _wdata.columns and _wdata[c].notna().any()]
                    _wave_offsets = [offset_fn(c) for c in _wave_cols]

                    # Share y-axis within each row
                    _row_ymin = float('inf')
                    _row_ymax = float('-inf')

                    for s_idx, seg in enumerate(_all_segs):
                        ax = axes[r_idx][s_idx]
                        _sdata = _wdata[_wdata['segment'] == seg]

                        _plotted = False
                        for status, color, lw, marker in [
                            ('Responder', _RESP_COLOR, 2.5, 'o'),
                            ('Non-Responder', _NONRESP_COLOR, 2, 's'),
                        ]:
                            _grp = _sdata[_sdata['status'] == status]
                            n = len(_grp)
                            if n < 5 or len(_wave_cols) < 3:
                                continue
                            means = [_grp[c].mean() for c in _wave_cols]
                            ax.plot(_wave_offsets, means, color=color, linewidth=lw,
                                    marker=marker, markersize=4, markevery=3,
                                    label=f'{status} ({n:,})', zorder=3)
                            _plotted = True
                            _row_ymin = min(_row_ymin, min(means) * 0.9)
                            _row_ymax = max(_row_ymax, max(means) * 1.1)

                        if not _plotted:
                            ax.text(0.5, 0.5, 'No Data', ha='center', va='center',
                                    transform=ax.transAxes, fontsize=14,
                                    color=_MUTED, style='italic')

                        # Mail date line
                        ax.axvline(x=0, color=_DARK, linewidth=1.2, linestyle='--',
                                   alpha=0.5, zorder=2)

                        # Segment title only on top row
                        if r_idx == 0:
                            ax.set_title(seg, fontsize=20, fontweight='bold',
                                         color=_SEG_COLORS.get(seg, _DARK), pad=8)

                        # X-axis label only on bottom row
                        if r_idx == n_rows - 1:
                            ax.set_xlabel('Months from Mail', fontsize=16,
                                          fontweight='bold', labelpad=4)

                        if s_idx == 0:
                            ax.set_ylabel(ylabel, fontsize=16,
                                          fontweight='bold', color=_DARK, labelpad=6)
                            ax.yaxis.set_major_formatter(plt.FuncFormatter(y_fmt))

                        if s_idx == 0 and r_idx == 0:
                            ax.legend(fontsize=14, loc='upper left', framealpha=0.8)

                        gen_clean_axes(ax, keep_left=(s_idx == 0), keep_bottom=True)
                        ax.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
                        ax.set_axisbelow(True)

                    # Sync y-axis across row
                    if _row_ymin < float('inf'):
                        for s_idx in range(n_panels):
                            axes[r_idx][s_idx].set_ylim(_row_ymin, _row_ymax)

                fig.suptitle(_suptitle,
                             fontsize=18, fontweight='bold', color=_DARK, y=1.02)
                plt.tight_layout()
                plt.subplots_adjust(hspace=0.3)
                plt.show()
