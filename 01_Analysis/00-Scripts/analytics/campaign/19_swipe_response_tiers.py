# ===========================================================================
# CAMPAIGN SWIPE DISTRIBUTION: Who Are the Responders? (Conference Edition)
# ===========================================================================
# Grouped bar: swipe tier distribution among Responders vs Non-Responders.
# Shows WHICH swipe tiers respond, not response rate (which is tautological
# for ARS campaigns where the response IS swiping).
# X-axis ordered low-to-high (Non-user → highest tier).
# Depends on swipe_lookup from general/29_swipe_category_data.

if 'swipe_lookup' not in dir() or not isinstance(swipe_lookup, pd.DataFrame) or len(swipe_lookup) == 0:
    print("    No SwipeCat data in ODDD. Skipping swipe distribution chart.")
elif 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping swipe distribution chart.")
else:
    _cat_col = None
    _order_var = None
    _palette_var = None

    if 'swipe_cat12' in swipe_lookup.columns and 'SWIPE12_ORDER' in dir():
        _cat_col = 'swipe_cat12'
        _order_var = SWIPE12_ORDER
        _palette_var = SWIPE12_PALETTE
    elif 'swipe_cat3' in swipe_lookup.columns and 'SWIPE3_ORDER' in dir():
        _cat_col = 'swipe_cat3'
        _order_var = SWIPE3_ORDER
        _palette_var = SWIPE3_PALETTE

    if _cat_col is None:
        print("    No SwipeCat tier columns found in swipe_lookup. Skipping.")
    else:
        _swipe_camp = camp_acct[['primary_account_num', 'camp_status', 'total_responses']].merge(
            swipe_lookup[['primary_account_num', _cat_col]], on='primary_account_num', how='inner'
        )

        _mailed = _swipe_camp[_swipe_camp['camp_status'] != 'Never Mailed']

        if len(_mailed) == 0:
            print("    No mailed accounts with swipe data. Skipping chart.")
        else:
            # Order tiers low-to-high (reverse the discovered order which is high-first)
            _tier_order = list(reversed([t for t in _order_var if t in _mailed[_cat_col].values]))
            if len(_tier_order) == 0:
                _tier_order = sorted(_mailed[_cat_col].unique())

            # Compute % distribution within each status group
            _status_groups = ['Responder', 'Non-Responder']
            _status_colors = {
                'Responder': GEN_COLORS['success'],
                'Non-Responder': GEN_COLORS['warning'],
            }

            _dist_data = {}
            for status in _status_groups:
                _subset = _mailed[_mailed['camp_status'] == status]
                if len(_subset) == 0:
                    continue
                _counts = _subset[_cat_col].value_counts()
                _total = len(_subset)
                _dist_data[status] = {
                    'pcts': [_counts.get(t, 0) / _total * 100 for t in _tier_order],
                    'counts': [_counts.get(t, 0) for t in _tier_order],
                    'total': _total,
                }

            if len(_dist_data) == 0:
                print("    No data for grouped bar. Skipping.")
            else:
                fig, ax = plt.subplots(figsize=(14, 7))

                n_groups = len(_tier_order)
                n_bars = len(_dist_data)
                bar_width = 0.35
                x = np.arange(n_groups)

                for b_idx, (status, data) in enumerate(_dist_data.items()):
                    offset = (b_idx - (n_bars - 1) / 2) * bar_width
                    bars = ax.bar(x + offset, data['pcts'], width=bar_width * 0.9,
                                  color=_status_colors.get(status, GEN_COLORS['muted']),
                                  edgecolor='white', linewidth=0.5,
                                  label=f"{status} ({data['total']:,})")

                    for bar, pct, cnt in zip(bars, data['pcts'], data['counts']):
                        if pct > 2:
                            ax.text(bar.get_x() + bar.get_width() / 2,
                                    bar.get_height() + 0.5,
                                    f"{pct:.1f}%",
                                    ha='center', va='bottom', fontsize=14,
                                    fontweight='bold',
                                    color=_status_colors.get(status, GEN_COLORS['muted']))

                ax.set_xticks(x)
                ax.set_xticklabels(_tier_order, fontsize=14, fontweight='bold')
                ax.set_ylabel("% of Group", fontsize=16, fontweight='bold', labelpad=10)
                ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

                gen_clean_axes(ax, keep_left=True, keep_bottom=True)
                ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
                ax.set_axisbelow(True)
                ax.legend(loc='upper right', fontsize=14, framealpha=0.9)

                _window_label = '12-month' if '12' in _cat_col else '3-month'
                ax.set_title("Swipe Tier Distribution: Responders vs Non-Responders",
                             fontsize=26, fontweight='bold',
                             color=GEN_COLORS['dark_text'], pad=30, loc='left')
                ax.text(0.0, 1.02,
                        f"Which swipe tiers are campaign responders coming from?  "
                        f"({_window_label} avg monthly swipes, {DATASET_LABEL})",
                        transform=ax.transAxes, fontsize=14,
                        color=GEN_COLORS['muted'], style='italic')

                plt.tight_layout()
                plt.show()
