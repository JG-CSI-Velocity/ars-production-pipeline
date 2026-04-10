# ===========================================================================
# RESPONSE LADDER: First vs Repeat + Movement (Conference Edition)
# ===========================================================================
# For 2nd+ waves: (1) donut of first-time vs repeat responders,
# (2) horizontal bar showing ladder movement (Up/Same/Down).
#
# Depends on: camp_acct, rewards_df, mail_cols, resp_cols (cell 01)

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
elif len(resp_cols) < 2:
    print("    Need 2+ waves for ladder analysis. Skipping.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _SUCCESS = GEN_COLORS.get('success', '#2A9D8F')
    _INFO = GEN_COLORS.get('info', '#457B9D')
    _WARNING = GEN_COLORS.get('warning', '#E9C46A')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')

    def _is_success(val):
        if pd.isna(val):
            return False
        v = str(val).strip().upper()
        return v.startswith('TH') or v in ('NU 5+', 'NU5+', 'NU 5', 'NU 6',
                                            'NU 7', 'NU 8', 'NU 9', 'NU 10')

    def _challenge_tier(val):
        if pd.isna(val):
            return 0
        v = str(val).strip().upper()
        if v.startswith('TH-'):
            try:
                return int(v.replace('TH-', ''))
            except ValueError:
                return 5
        if v in ('NU 5+', 'NU5+', 'NU 5'):
            return 1
        return 0

    # Track per-account response history across waves
    _acct_col = 'Acct Number' if 'Acct Number' in rewards_df.columns else ' Acct Number'
    acct_ids = rewards_df[_acct_col].astype(str).str.strip()

    # Build response history
    resp_history = pd.DataFrame({'acct': acct_ids})
    for i, rc in enumerate(resp_cols):
        period = rc.replace(' Resp', '')
        resp_history[f'w{i}_success'] = rewards_df[rc].map(_is_success)
        resp_history[f'w{i}_tier'] = rewards_df[rc].map(_challenge_tier)

    n_waves = len(resp_cols)
    has_ladder_data = False

    for w_idx in range(1, n_waves):
        period = resp_cols[w_idx].replace(' Resp', '')

        # Current wave responders
        curr_mask = resp_history[f'w{w_idx}_success']
        if curr_mask.sum() == 0:
            continue

        # Check if they responded in any prior wave
        prior_success = resp_history[[f'w{j}_success' for j in range(w_idx)]].any(axis=1)
        curr_responders = resp_history[curr_mask].copy()
        curr_responders['is_repeat'] = prior_success[curr_mask].values

        n_first = (~curr_responders['is_repeat']).sum()
        n_repeat = curr_responders['is_repeat'].sum()
        n_total = len(curr_responders)

        if n_total == 0:
            continue

        has_ladder_data = True

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7),
                                        gridspec_kw={'width_ratios': [1, 1.3]})

        # Left: First vs Repeat donut
        sizes = [n_first, n_repeat]
        labels = ['First-Time', 'Repeat']
        colors = [_INFO, _SUCCESS]

        wedges, _, _ = ax1.pie(
            sizes, labels=None, autopct='',
            colors=colors, startangle=90,
            wedgeprops={'width': 0.45, 'edgecolor': 'white', 'linewidth': 2.5}
        )

        ax1.text(0, 0.05, f"{n_total:,}", ha='center', va='center',
                 fontsize=32, fontweight='bold', color=_DARK)
        ax1.text(0, -0.15, 'Responded', ha='center', va='center',
                 fontsize=16, color=_MUTED, fontweight='bold')

        ax1.legend(
            [f"First-Time: {n_first:,} ({n_first/n_total*100:.0f}%)",
             f"Repeat: {n_repeat:,} ({n_repeat/n_total*100:.0f}%)"],
            loc='lower center', fontsize=14, frameon=False,
            bbox_to_anchor=(0.5, -0.12)
        )

        # Right: Ladder movement for repeat responders
        if n_repeat > 0:
            repeat_data = curr_responders[curr_responders['is_repeat']].copy()

            # Get most recent prior tier
            prior_tiers = []
            for _, row in repeat_data.iterrows():
                best_prior = 0
                for j in range(w_idx):
                    if row[f'w{j}_success']:
                        best_prior = max(best_prior, row[f'w{j}_tier'])
                prior_tiers.append(best_prior)

            repeat_data['prior_tier'] = prior_tiers
            repeat_data['curr_tier'] = repeat_data[f'w{w_idx}_tier'].values

            repeat_data['movement'] = 'Same'
            repeat_data.loc[repeat_data['curr_tier'] > repeat_data['prior_tier'], 'movement'] = 'Up'
            repeat_data.loc[repeat_data['curr_tier'] < repeat_data['prior_tier'], 'movement'] = 'Down'

            move_counts = repeat_data['movement'].value_counts()
            move_order = ['Up', 'Same', 'Down']
            move_colors = {'Up': _SUCCESS, 'Same': _WARNING, 'Down': _ACCENT}

            y_pos = range(len(move_order))
            bar_vals = [move_counts.get(m, 0) for m in move_order]
            bar_colors = [move_colors[m] for m in move_order]

            bars = ax2.barh(list(y_pos), bar_vals, color=bar_colors,
                           edgecolor='white', linewidth=1.5, height=0.5, zorder=3)

            ax2.set_yticks(list(y_pos))
            ax2.set_yticklabels(move_order, fontsize=16, fontweight='bold')

            max_val = max(bar_vals) if bar_vals else 1
            for j, (val, label) in enumerate(zip(bar_vals, move_order)):
                pct = val / n_repeat * 100 if n_repeat > 0 else 0
                ax2.text(val + max_val * 0.03, j,
                         f"{val:,} ({pct:.0f}%)",
                         va='center', fontsize=16, fontweight='bold',
                         color=move_colors[label])

            ax2.set_xlabel("Repeat Responders", fontsize=16, fontweight='bold')
            ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
            ax2.set_xlim(0, max_val * 1.4)
            gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
            ax2.xaxis.grid(True, color=GEN_COLORS.get('grid', '#E0E0E0'),
                          linewidth=0.5, alpha=0.7)
            ax2.set_axisbelow(True)
            ax2.set_title("Challenge Ladder Movement",
                         fontsize=20, fontweight='bold', color=_DARK, pad=14)
        else:
            ax2.text(0.5, 0.5, "No repeat responders\nin this wave",
                     ha='center', va='center', fontsize=18, color=_MUTED,
                     transform=ax2.transAxes)
            ax2.axis('off')

        fig.suptitle(f"First vs Repeat Responders: {period}",
                     fontsize=28, fontweight='bold', color=_DARK, y=0.98)
        fig.text(0.5, 0.93,
                 f"Are repeat responders climbing to higher challenges?  |  {DATASET_LABEL}",
                 ha='center', fontsize=16, color=_MUTED, style='italic')

        plt.tight_layout(rect=[0, 0, 1, 0.91])
        plt.show()

    if not has_ladder_data:
        print("    No ladder data available (need 2+ waves with responders).")
    else:
        # Overall summary
        all_repeat = 0
        all_first = 0
        for w_idx in range(1, n_waves):
            curr_mask = resp_history[f'w{w_idx}_success']
            prior_success = resp_history[[f'w{j}_success' for j in range(w_idx)]].any(axis=1)
            all_repeat += (curr_mask & prior_success).sum()
            all_first += (curr_mask & ~prior_success).sum()
        if all_repeat + all_first > 0:
            print(f"\n    Ladder Summary (waves 2+):")
            print(f"      First-time: {all_first:,}  |  Repeat: {all_repeat:,}")
            print(f"      Repeat rate: {all_repeat / (all_repeat + all_first) * 100:.1f}%")
