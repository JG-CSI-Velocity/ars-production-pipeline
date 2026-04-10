# ===========================================================================
# SWIPE BEHAVIOR SHIFT: Short-Term vs Long-Term (Conference Edition)
# ===========================================================================
# Two-panel heatmap: SwipeCat3 (recent) vs SwipeCat12 (long-term).
# Left = Responders, Right = Non-Responders. (16,8).
# Both axes ordered low-to-high (Non-user at bottom-left).
# Diagonal = stable behavior. Upper-right of diagonal = improving.

if 'swipe_lookup' not in dir() or not isinstance(swipe_lookup, pd.DataFrame) or len(swipe_lookup) == 0:
    print("    No swipe category data available. Skipping migration matrix.")
elif 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping migration matrix.")
else:
    try:
        _has_both = ('swipe_cat3' in swipe_lookup.columns and
                     'swipe_cat12' in swipe_lookup.columns)

        if not _has_both:
            print("    Need both SwipeCat3 and SwipeCat12 for migration matrix. Skipping.")
        else:
            # Order: low-to-high (reverse the discovered orders which are high-first)
            _order3_raw = SWIPE3_ORDER if 'SWIPE3_ORDER' in dir() else SWIPE_ORDER
            _order12_raw = SWIPE12_ORDER if 'SWIPE12_ORDER' in dir() else SWIPE_ORDER
            _order3 = list(reversed(_order3_raw))
            _order12 = list(reversed(_order12_raw))

            _swipe_camp = swipe_lookup[['primary_account_num', 'swipe_cat3', 'swipe_cat12']].merge(
                camp_acct[['primary_account_num', 'camp_status']],
                on='primary_account_num', how='inner'
            )

            # Filter to mailed accounts only
            _swipe_camp = _swipe_camp[_swipe_camp['camp_status'] != 'Never Mailed']

            if len(_swipe_camp) == 0:
                print("    No mailed accounts with both SwipeCat fields. Skipping.")
            else:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

                # Filter orders to values that exist in data
                _row_order = [t for t in _order12 if t in _swipe_camp['swipe_cat12'].values]
                _col_order = [t for t in _order3 if t in _swipe_camp['swipe_cat3'].values]

                if len(_row_order) == 0 or len(_col_order) == 0:
                    print("    Empty tier intersection. Skipping migration matrix.")
                else:
                    _improve_stats = {}

                    for ax, _status, _title in [
                        (ax1, 'Responder', 'Responders'),
                        (ax2, 'Non-Responder', 'Non-Responders'),
                    ]:
                        _subset = _swipe_camp[_swipe_camp['camp_status'] == _status]

                        if len(_subset) == 0:
                            ax.text(0.5, 0.5, f"No {_title} data",
                                    ha='center', va='center', transform=ax.transAxes,
                                    fontsize=14, color=GEN_COLORS['muted'])
                            ax.set_title(_title, fontsize=20, fontweight='bold')
                            continue

                        _xtab = pd.crosstab(
                            _subset['swipe_cat12'],
                            _subset['swipe_cat3'],
                        )
                        # Reindex to low-to-high order, fill missing with 0
                        _xtab = _xtab.reindex(
                            index=_row_order, columns=_col_order, fill_value=0
                        )

                        # Compute % improved vs declined
                        # With low-to-high ordering on both axes:
                        #   Above diagonal (col_idx > row_idx) = 3mo tier HIGHER than 12mo = improving
                        #   Below diagonal (col_idx < row_idx) = 3mo tier LOWER than 12mo = declining
                        _total_accts = _xtab.values.sum()
                        _improved = 0
                        _declined = 0
                        for _ri, _r in enumerate(_row_order):
                            for _ci, _c in enumerate(_col_order):
                                _val = _xtab.loc[_r, _c] if (_r in _xtab.index and _c in _xtab.columns) else 0
                                if _ci > _ri:
                                    _improved += _val
                                elif _ci < _ri:
                                    _declined += _val

                        _improve_pct = (_improved / _total_accts * 100) if _total_accts > 0 else 0
                        _decline_pct = (_declined / _total_accts * 100) if _total_accts > 0 else 0
                        _stable_pct = 100 - _improve_pct - _decline_pct
                        _improve_stats[_status] = _improve_pct

                        cmap = LinearSegmentedColormap.from_list(
                            f'swipe_{_status}',
                            ['#FFFFFF', GEN_COLORS['success'] if _status == 'Responder' else GEN_COLORS['warning']]
                        )

                        sns.heatmap(
                            _xtab, annot=True, fmt=',d', cmap=cmap,
                            linewidths=2, linecolor='white',
                            cbar_kws={'shrink': 0.5, 'label': 'Accounts'},
                            annot_kws={'fontsize': 10, 'fontweight': 'bold'},
                            ax=ax
                        )

                        ax.set_xlabel('Recent Behavior (3-Month Swipe Tier)',
                                      fontsize=14, fontweight='bold', labelpad=10)
                        ax.set_ylabel('Baseline (12-Month Swipe Tier)',
                                      fontsize=14, fontweight='bold', labelpad=10)
                        ax.set_xticklabels(ax.get_xticklabels(), fontsize=14,
                                           fontweight='bold', rotation=45, ha='right')
                        ax.set_yticklabels(ax.get_yticklabels(), fontsize=14,
                                           fontweight='bold', rotation=0)

                        ax.set_title(f"{_title}  ({len(_subset):,} accounts)",
                                     fontsize=18, fontweight='bold',
                                     color=GEN_COLORS['dark_text'], pad=12)

                        # Stats below chart with clear spacing
                        _stats_color = GEN_COLORS['success'] if _improve_pct > _decline_pct else GEN_COLORS['accent']
                        ax.text(0.5, -0.22,
                                f"Improving: {_improve_pct:.1f}%  |  "
                                f"Stable: {_stable_pct:.1f}%  |  "
                                f"Declining: {_decline_pct:.1f}%",
                                transform=ax.transAxes, ha='center', fontsize=14,
                                fontweight='bold', color=_stats_color)

                    # Reading guide (placed between panels, not overlapping)
                    fig.text(0.5, 0.02,
                             "Read: find an account's 12-month tier on Y-axis, "
                             "then 3-month tier on X-axis.  Right of diagonal = usage increasing.",
                             ha='center', fontsize=14,
                             color=GEN_COLORS['muted'], style='italic')

                    fig.suptitle("Swipe Behavior Shift: Are Responders Accelerating?",
                                 fontsize=24, fontweight='bold',
                                 color=GEN_COLORS['dark_text'], y=1.01)

                    # Summary comparison
                    if len(_improve_stats) >= 2:
                        _resp_imp = _improve_stats.get('Responder', 0)
                        _nonr_imp = _improve_stats.get('Non-Responder', 0)
                        print(f"    Responders improving: {_resp_imp:.1f}%  vs  "
                              f"Non-Responders improving: {_nonr_imp:.1f}%")
                        if _resp_imp > _nonr_imp:
                            print(f"    Campaign drives {_resp_imp - _nonr_imp:.1f} pp more behavioral improvement")

                    plt.tight_layout()
                    plt.subplots_adjust(top=0.90, bottom=0.12)
                    plt.show()

    except NameError as e:
        print(f"    Missing dependency for swipe migration matrix: {e}")
