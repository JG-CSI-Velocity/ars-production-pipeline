# ===========================================================================
# CAMPAIGN SWIPE TREND: Monthly Trajectory by Status (Conference Edition)
# ===========================================================================
# Multi-line chart: monthly avg swipes for Responder / Non-Responder / Never Mailed.
# Vertical dashed lines at campaign wave months. (14,7).
# Uses per-month swipe columns (MmmYY Swipes) from rewards_df -- NOT combined_df.

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping swipe trend chart.")
else:
    try:
        # Dynamically discover monthly swipe columns
        _all_cols = [c.strip() for c in rewards_df.columns]
        _swipe_month_cols = [c for c in _all_cols
                             if c.endswith(' Swipes') and c not in ('Total Swipes',)]

        if len(_swipe_month_cols) == 0:
            print("    No monthly Swipes columns found in ODDD. Skipping trend chart.")
        else:
            # Parse month labels and sort chronologically
            _MONTH_ABBR_T = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                             'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

            def _swipe_sort_key(col_name):
                label = col_name.replace(' Swipes', '')
                try:
                    mon_abbr = label[:3]
                    yr_2d = int(label[3:])
                    return (2000 + yr_2d) * 100 + _MONTH_ABBR_T.get(mon_abbr, 0)
                except (ValueError, IndexError):
                    return 999999

            _swipe_month_cols = sorted(_swipe_month_cols, key=_swipe_sort_key)
            _month_labels = [c.replace(' Swipes', '') for c in _swipe_month_cols]

            # Build account x month table from rewards_df (small: ~50K x 17)
            _acct_camp_status = camp_acct[['primary_account_num', 'camp_status']]
            _swipe_ts = rewards_df[['Acct Number'] + _swipe_month_cols].copy()
            _swipe_ts.rename(columns={'Acct Number': 'primary_account_num'}, inplace=True)
            _swipe_ts['primary_account_num'] = _swipe_ts['primary_account_num'].astype(str).str.strip()
            _swipe_ts = _swipe_ts.merge(_acct_camp_status, on='primary_account_num', how='inner')

            # Convert swipe columns to numeric
            for _sc in _swipe_month_cols:
                _swipe_ts[_sc] = pd.to_numeric(_swipe_ts[_sc], errors='coerce').fillna(0)

            # Compute mean swipes per month per camp_status
            _status_colors = {
                'Responder':     GEN_COLORS['success'],
                'Non-Responder': GEN_COLORS['warning'],
                'Never Mailed':  GEN_COLORS['muted'],
            }

            fig, ax = plt.subplots(figsize=(14, 7))

            for _status in ['Responder', 'Non-Responder', 'Never Mailed']:
                _subset = _swipe_ts[_swipe_ts['camp_status'] == _status]
                if len(_subset) == 0:
                    continue
                _means = [_subset[c].mean() for c in _swipe_month_cols]
                _lw = 3 if _status == 'Responder' else 2
                _alpha = 1.0 if _status != 'Never Mailed' else 0.6
                ax.plot(range(len(_month_labels)), _means,
                        color=_status_colors.get(_status, GEN_COLORS['muted']),
                        linewidth=_lw, alpha=_alpha, label=_status,
                        marker='o', markersize=5)

            # Campaign wave markers (vertical dashed lines)
            if 'mail_cols' in dir() and len(mail_cols) > 0:
                _wave_labels = sorted(
                    [c.replace(' Mail', '') for c in mail_cols],
                    key=lambda lbl: _swipe_sort_key(lbl + ' Swipes')
                )
                for _wl in _wave_labels:
                    if _wl in _month_labels:
                        _idx = _month_labels.index(_wl)
                        ax.axvline(_idx, color=GEN_COLORS['accent'], linestyle='--',
                                   linewidth=1.5, alpha=0.6)
                        ax.text(_idx, ax.get_ylim()[1] * 0.97, f"Mail\n{_wl}",
                                ha='center', va='top', fontsize=14, fontweight='bold',
                                color=GEN_COLORS['accent'], alpha=0.8)

            ax.set_xticks(range(len(_month_labels)))
            ax.set_xticklabels(_month_labels, fontsize=14, fontweight='bold', rotation=45, ha='right')
            ax.set_ylabel("Avg Monthly Swipes", fontsize=16, fontweight='bold', labelpad=10)

            gen_clean_axes(ax, keep_left=True, keep_bottom=True)
            ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)

            ax.legend(loc='upper left', fontsize=14, frameon=False)

            ax.set_title("Monthly Swipe Trajectory by Campaign Status",
                         fontsize=26, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=35, loc='left')
            ax.text(0.0, 1.02,
                    f"Do campaign responders increase card usage after mailing waves?  ({DATASET_LABEL})",
                    transform=ax.transAxes, fontsize=14,
                    color=GEN_COLORS['muted'], style='italic')

            plt.tight_layout()
            plt.show()

    except NameError as e:
        print(f"    Missing dependency for swipe trend chart: {e}")
