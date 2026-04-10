# ===========================================================================
# SEGMENT COHORT CHART: Per-Mailer × Per-Segment SPEND Comparison
# ===========================================================================
# One horizontal figure per mailer wave, with panels (one per segment).
# Each panel: pre vs post avg monthly spend for Responders vs Non-Responders.
# Segments ordered: NU, TH-10, TH-15, TH-20, TH-25.
# Mailer details (mailed, responded, rate) displayed in suptitle.
#
# Depends on: segment_cohort_raw (from cell 25), camp_summary (from cell 01)

if 'segment_cohort_raw' not in dir() or len(segment_cohort_raw) == 0:
    print("    No segment cohort data. Run cell 25 first.")
else:
    # Canonical segment order (low to high challenge)
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

    # Use 3mo pre and 3mo post columns for the before/after comparison
    _pre_cols = [c for c in segment_cohort_raw.columns
                 if c.startswith('m-') and int(c.split('-')[1]) <= 3]
    _post_cols = [c for c in segment_cohort_raw.columns
                  if c.startswith('m+') and int(c.split('+')[1]) <= 3]

    if len(_pre_cols) == 0 or len(_post_cols) == 0:
        print("    Not enough pre/post month columns for comparison.")
    else:
        # Compute pre avg (mean of m-3 to m-1) and post avg (mean of m+1 to m+3)
        segment_cohort_raw['_pre_avg'] = segment_cohort_raw[_pre_cols].mean(axis=1)
        segment_cohort_raw['_post_avg'] = segment_cohort_raw[_post_cols].mean(axis=1)

        # Get waves in chronological order
        _waves = (
            segment_cohort_raw[['wave', 'wave_date']]
            .drop_duplicates()
            .sort_values('wave_date')['wave']
            .tolist()
        )

        # Filter to segments that exist in the data
        _available_segs = [s for s in _SEG_ORDER if s in segment_cohort_raw['segment'].values]
        _extra_segs = [s for s in segment_cohort_raw['segment'].unique()
                       if s not in _SEG_ORDER and s != 'Unknown']
        _all_segs = _available_segs + sorted(_extra_segs)

        if len(_all_segs) == 0:
            print("    No valid segments found.")
        else:
            from matplotlib.patches import Patch

            n_panels = len(_all_segs)

            # Build camp_summary lookup for mailer details
            _camp_lookup = {}
            if 'camp_summary' in dir() and len(camp_summary) > 0:
                for _, _row in camp_summary.iterrows():
                    _camp_lookup[_row['period']] = _row

            for wave in _waves:
                _wdata = segment_cohort_raw[segment_cohort_raw['wave'] == wave]
                if len(_wdata) == 0:
                    continue

                fig, axes = plt.subplots(1, n_panels, figsize=(3.5 * n_panels, 5.5),
                                          squeeze=False)
                axes = axes[0]

                _wave_date = _wdata['wave_date'].iloc[0]
                _wave_label = _wave_date.strftime('%b %Y')

                # Build suptitle with mailer details
                _suptitle = f"Mailer: {_wave_label}"
                if wave in _camp_lookup:
                    _ci = _camp_lookup[wave]
                    _suptitle += (f"   |   {int(_ci['mailed']):,} Mailed"
                                  f"   |   {int(_ci['responded']):,} Responded"
                                  f"   |   {_ci['response_rate']:.1f}% Response Rate")

                for s_idx, seg in enumerate(_all_segs):
                    ax = axes[s_idx]
                    _sdata = _wdata[_wdata['segment'] == seg]

                    _resp = _sdata[_sdata['status'] == 'Responder']
                    _nonresp = _sdata[_sdata['status'] == 'Non-Responder']

                    n_r = len(_resp)
                    n_nr = len(_nonresp)

                    if n_r == 0 and n_nr == 0:
                        ax.text(0.5, 0.5, 'No Data', ha='center', va='center',
                                transform=ax.transAxes, fontsize=14,
                                color=_MUTED, style='italic')
                        ax.set_title(seg, fontsize=20, fontweight='bold',
                                     color=_SEG_COLORS.get(seg, _DARK), pad=8)
                        ax.axis('off')
                        continue

                    # Compute group means
                    bar_labels = []
                    pre_vals = []
                    post_vals = []

                    if n_r > 0:
                        bar_labels.append(f'Resp\n({n_r:,})')
                        pre_vals.append(_resp['_pre_avg'].mean())
                        post_vals.append(_resp['_post_avg'].mean())

                    if n_nr > 0:
                        bar_labels.append(f'Non-R\n({n_nr:,})')
                        pre_vals.append(_nonresp['_pre_avg'].mean())
                        post_vals.append(_nonresp['_post_avg'].mean())

                    x = np.arange(len(bar_labels))
                    w = 0.35

                    # Pre bars (lighter)
                    for i in range(len(x)):
                        ax.bar(x[i] - w/2, pre_vals[i], width=w,
                               color=_RESP_COLOR if i == 0 else _NONRESP_COLOR,
                               alpha=0.35, edgecolor='white', linewidth=0.5)
                    # Post bars (solid)
                    for i in range(len(x)):
                        ax.bar(x[i] + w/2, post_vals[i], width=w,
                               color=_RESP_COLOR if i == 0 else _NONRESP_COLOR,
                               edgecolor='white', linewidth=0.5)

                    ax.set_xticks(x)
                    ax.set_xticklabels(bar_labels, fontsize=14, fontweight='bold')

                    # Value labels on post bars
                    for i in range(len(x)):
                        delta = post_vals[i] - pre_vals[i]
                        delta_color = _RESP_COLOR if delta >= 0 else GEN_COLORS.get('accent', '#E63946')
                        ax.text(x[i] + w/2, post_vals[i] + 1,
                                f"${post_vals[i]:,.0f}\n({delta:+,.0f})",
                                ha='center', va='bottom', fontsize=14,
                                fontweight='bold', color=delta_color)

                    ax.set_title(seg, fontsize=20, fontweight='bold',
                                 color=_SEG_COLORS.get(seg, _DARK), pad=8)

                    ax.yaxis.set_major_formatter(plt.FuncFormatter(
                        lambda v, _: f"${v:,.0f}"
                    ))

                    gen_clean_axes(ax, keep_left=(s_idx == 0), keep_bottom=True)
                    ax.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
                    ax.set_axisbelow(True)

                    if s_idx == 0:
                        ax.set_ylabel("Avg Monthly Spend ($)", fontsize=16,
                                      fontweight='bold', color=_DARK, labelpad=6)

                # Legend below figure with proper spacing
                _legend_elements = [
                    Patch(facecolor=_MUTED, alpha=0.35, label='Pre (3mo avg before mail)'),
                    Patch(facecolor=_MUTED, alpha=1.0, label='Post (3mo avg after mail)'),
                ]
                fig.legend(handles=_legend_elements, loc='lower center',
                           ncol=2, fontsize=14, frameon=False,
                           bbox_to_anchor=(0.5, -0.06))

                fig.suptitle(_suptitle,
                             fontsize=18, fontweight='bold', color=_DARK, y=1.03)

                plt.tight_layout()
                plt.subplots_adjust(bottom=0.12)
                plt.show()

            # ------------------------------------------------------------------
            # Summary: DID across all waves by segment
            # ------------------------------------------------------------------
            print(f"\n    DID Summary (3mo pre vs 3mo post, all mailers pooled):")
            for seg in _all_segs:
                _sd = segment_cohort_raw[segment_cohort_raw['segment'] == seg]
                _r = _sd[_sd['status'] == 'Responder']
                _nr = _sd[_sd['status'] == 'Non-Responder']
                if len(_r) >= 10 and len(_nr) >= 10:
                    r_delta = _r['_post_avg'].mean() - _r['_pre_avg'].mean()
                    nr_delta = _nr['_post_avg'].mean() - _nr['_pre_avg'].mean()
                    did = r_delta - nr_delta
                    print(f"      {seg:>8s}: DID = ${did:+,.2f}/mo  "
                          f"(Resp {len(_r):,}: ${r_delta:+,.2f}, "
                          f"Non-Resp {len(_nr):,}: ${nr_delta:+,.2f})")

        # Clean up temp columns
        segment_cohort_raw.drop(columns=['_pre_avg', '_post_avg'], inplace=True, errors='ignore')
