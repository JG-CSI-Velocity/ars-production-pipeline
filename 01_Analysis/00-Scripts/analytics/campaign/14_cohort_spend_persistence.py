# ===========================================================================
# COHORT SPEND PERSISTENCE: Lift Durability at 1/3/6 Months (Conf. Edition)
# ===========================================================================
# Grouped bars: for each wave, responder DID lift at 1mo, 3mo, 6mo post.
# Shows whether the lift lasts or is a one-time bump. (14,7).

if 'cohort_persist' not in dir() or len(cohort_persist) == 0:
    print("    No persistence data available. Skipping persistence chart.")
else:
    # Compute DID per wave per window
    persist_did_rows = []
    for wave in cohort_persist['wave'].unique():
        wdf = cohort_persist[cohort_persist['wave'] == wave]
        for window in ['1mo', '3mo', '6mo']:
            resp_row = wdf[(wdf['window'] == window) & (wdf['status'] == 'Responder')]
            nonresp_row = wdf[(wdf['window'] == window) & (wdf['status'] == 'Non-Responder')]
            if len(resp_row) > 0 and len(nonresp_row) > 0:
                did = resp_row['delta'].values[0] - nonresp_row['delta'].values[0]
                persist_did_rows.append({
                    'wave': wave,
                    'window': window,
                    'did_lift': did,
                })

    persist_did = pd.DataFrame(persist_did_rows)

    if len(persist_did) == 0:
        print("    Insufficient data for persistence analysis.")
    else:
        # Pivot for grouped bars
        waves = persist_did['wave'].unique()
        windows = ['1mo', '3mo', '6mo']
        window_labels = {'1mo': '1 Month', '3mo': '3 Months', '6mo': '6 Months'}
        window_colors = {
            '1mo': GEN_COLORS['info'],
            '3mo': GEN_COLORS['success'],
            '6mo': GEN_COLORS['warning'],
        }

        fig, ax = plt.subplots(figsize=(14, 7))

        n_waves = len(waves)
        bar_w = 0.22
        x = np.arange(n_waves)

        for j, window in enumerate(windows):
            vals = []
            for wave in waves:
                match = persist_did[(persist_did['wave'] == wave) & (persist_did['window'] == window)]
                vals.append(match['did_lift'].values[0] if len(match) > 0 else np.nan)

            positions = x + (j - 1) * bar_w
            valid_mask = ~np.isnan(vals)
            valid_vals = [v for v in vals if not np.isnan(v)]
            valid_pos = positions[valid_mask]

            if len(valid_vals) > 0:
                bars = ax.bar(valid_pos, valid_vals, bar_w,
                              label=window_labels[window],
                              color=window_colors[window], edgecolor='white', linewidth=1)

                for bar, val in zip(bars, valid_vals):
                    sign = '+' if val >= 0 else ''
                    va = 'bottom' if val >= 0 else 'top'
                    y_off = abs(ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02 * (1 if val >= 0 else -1)
                    ax.text(bar.get_x() + bar.get_width() / 2, val + y_off,
                            f"{sign}${val:,.0f}", ha='center', va=va,
                            fontsize=14, fontweight='bold', color=window_colors[window])

        # Zero line
        ax.axhline(y=0, color=GEN_COLORS['dark_text'], linewidth=1.5, linestyle='-', alpha=0.4)

        ax.set_xticks(x)
        ax.set_xticklabels(waves, fontsize=14, fontweight='bold')
        ax.set_ylabel("DID Spend Lift ($/acct/month)", fontsize=16, fontweight='bold', labelpad=10)

        gen_clean_axes(ax)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
        ax.legend(loc='upper right', fontsize=14)

        ax.set_title("Lift Persistence: Does the Spend Increase Last?",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax.text(0.0, 1.02,
                f"DID lift measured at 1, 3, and 6 months post-campaign  ({DATASET_LABEL})",
                transform=ax.transAxes, fontsize=15,
                color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()
