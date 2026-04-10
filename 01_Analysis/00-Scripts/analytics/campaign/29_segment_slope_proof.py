# ===========================================================================
# SEGMENT SLOPE PROOF: Pre vs Post Direction Reversal (Conference Edition)
# ===========================================================================
# Grouped bar: pre-slope vs post-slope per segment.
# Shows direction reversal: declining before response, rising after.
# Silver "before" bars, green/red "after" bars.
#
# Depends on: segment_cohort_raw (cell 22)

if 'segment_cohort_raw' not in dir() or len(segment_cohort_raw) == 0:
    print("    No segment cohort data. Run cell 22 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')

    # Identify spend columns
    _spend_cols = sorted(
        [c for c in segment_cohort_raw.columns if c.startswith('m') and ('+' in c or '-' in c)],
        key=lambda c: int(c[1:])
    )

    _pre_cols = [c for c in _spend_cols if int(c[1:]) < 0]
    _post_cols = [c for c in _spend_cols if int(c[1:]) > 0]

    if len(_pre_cols) < 2 or len(_post_cols) < 2:
        print("    Need 2+ pre and 2+ post months for slope. Skipping.")
    else:
        # Compute slope for each segment x status group
        def _compute_slope(df, cols):
            """Linear slope of monthly spend values."""
            x = np.arange(len(cols))
            means = df[cols].mean()
            if means.std() == 0:
                return 0.0
            z = np.polyfit(x, means.values, 1)
            return z[0]

        segments = sorted(segment_cohort_raw['segment'].unique())
        segments = [s for s in segments if s != 'Unknown']

        slope_data = []
        for seg in segments:
            for status in ['Responder', 'Non-Responder']:
                _sub = segment_cohort_raw[
                    (segment_cohort_raw['segment'] == seg) &
                    (segment_cohort_raw['status'] == status)
                ]
                if len(_sub) < 5:
                    continue

                pre_slope = _compute_slope(_sub, _pre_cols)
                post_slope = _compute_slope(_sub, _post_cols[:len(_pre_cols)])

                slope_data.append({
                    'segment': seg,
                    'status': status,
                    'pre_slope': pre_slope,
                    'post_slope': post_slope,
                    'reversal': post_slope - pre_slope,
                })

        if len(slope_data) == 0:
            print("    Insufficient data per segment for slope analysis.")
        else:
            _slope_df = pd.DataFrame(slope_data)

            # Focus on Responders (the key story)
            _resp_slopes = _slope_df[_slope_df['status'] == 'Responder'].copy()
            _resp_slopes = _resp_slopes.sort_values('reversal', ascending=True)

            if len(_resp_slopes) == 0:
                print("    No responder slope data.")
            else:
                fig, ax = plt.subplots(figsize=(16, max(7, len(_resp_slopes) * 1.2 + 2)))

                n = len(_resp_slopes)
                y_pos = np.arange(n)
                bar_height = 0.35

                # Pre-slope bars (silver)
                pre_bars = ax.barh(y_pos + bar_height / 2,
                                   _resp_slopes['pre_slope'].values,
                                   bar_height, label='Pre-Response Slope',
                                   color='#B0B0B0', edgecolor='white',
                                   linewidth=1.5, zorder=3)

                # Post-slope bars (green if positive, red if negative)
                post_vals = _resp_slopes['post_slope'].values
                post_colors = [_SUCCESS if v >= 0 else _ACCENT for v in post_vals]
                post_bars = ax.barh(y_pos - bar_height / 2,
                                    post_vals, bar_height,
                                    label='Post-Response Slope',
                                    color=post_colors, edgecolor='white',
                                    linewidth=1.5, zorder=3)

                ax.set_yticks(y_pos)
                ax.set_yticklabels(_resp_slopes['segment'].values,
                                  fontsize=16, fontweight='bold')

                # Value labels
                max_abs = max(abs(_resp_slopes[['pre_slope', 'post_slope']].values).max(), 1)
                for j, (_, row) in enumerate(_resp_slopes.iterrows()):
                    # Pre label
                    ax.text(row['pre_slope'] + (max_abs * 0.03 if row['pre_slope'] >= 0
                            else -max_abs * 0.03),
                            j + bar_height / 2,
                            f"${row['pre_slope']:+.0f}",
                            va='center',
                            ha='left' if row['pre_slope'] >= 0 else 'right',
                            fontsize=14, fontweight='bold', color='#808080')
                    # Post label
                    ax.text(row['post_slope'] + (max_abs * 0.03 if row['post_slope'] >= 0
                            else -max_abs * 0.03),
                            j - bar_height / 2,
                            f"${row['post_slope']:+.0f}",
                            va='center',
                            ha='left' if row['post_slope'] >= 0 else 'right',
                            fontsize=14, fontweight='bold',
                            color=_SUCCESS if row['post_slope'] >= 0 else _ACCENT)

                ax.axvline(0, color=_DARK, linewidth=1, alpha=0.4)
                ax.set_xlabel("Monthly Spend Slope ($/mo change)",
                             fontsize=16, fontweight='bold')
                ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_dollar))
                ax.legend(fontsize=14, loc='lower right', framealpha=0.9)
                gen_clean_axes(ax, keep_left=True, keep_bottom=True)
                ax.xaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.7)
                ax.set_axisbelow(True)

                ax.set_title("Spend Trajectory Reversal: Responders",
                             fontsize=20, fontweight='bold', color=_DARK, pad=35,
                             loc='left')
                ax.text(0.0, 1.02,
                        f"Silver = pre-response slope  |  Color = post-response slope  |  {DATASET_LABEL}",
                        transform=ax.transAxes, fontsize=16,
                        color=_MUTED, style='italic')

                fig.suptitle("Direction Reversal Proof",
                             fontsize=28, fontweight='bold', color=_DARK, y=0.98)

                plt.tight_layout(rect=[0, 0, 1, 0.93])
                plt.show()

                # Summary
                n_reversed = (_resp_slopes['reversal'] > 0).sum()
                print(f"\n    Slope Reversal Summary (Responders):")
                print(f"      {n_reversed} of {n} segments show positive reversal")
                for _, row in _resp_slopes.iterrows():
                    arrow = '^' if row['reversal'] > 0 else 'v'
                    print(f"      {row['segment']}: "
                          f"${row['pre_slope']:+.0f} -> ${row['post_slope']:+.0f}  "
                          f"({arrow} ${row['reversal']:+.0f})")
