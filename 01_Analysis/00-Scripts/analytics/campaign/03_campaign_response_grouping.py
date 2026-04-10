# ===========================================================================
# CAMPAIGN RESPONSE GROUPING: Challenge Outcomes & NU Conversion (Conf. Ed.)
# ===========================================================================
# Three separate charts:
#   1. Challenge outcome distribution (horizontal bar)
#   2. NU conversion pipeline by wave (stacked bar + conversion line)
#   3. Cumulative NU conversion funnel
# Shows which challenges drive success and whether NU 1-4 accounts convert
# to NU 5+ in subsequent waves.

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping response grouping.")
else:
    # -----------------------------------------------------------------
    # 1. Build response value distribution across all periods
    # -----------------------------------------------------------------
    _resp_values_all = []
    for mc, rc in zip(mail_cols, resp_cols):
        period_label = mc.replace(' Mail', '')
        _mailed_mask = camp_raw[mc].notna()
        _resp_vals = camp_raw.loc[_mailed_mask, rc].copy()

        for val in _resp_vals:
            if pd.isna(val):
                _resp_values_all.append({'period': period_label, 'outcome': 'No Response'})
            else:
                v = str(val).strip().upper()
                _resp_values_all.append({'period': period_label, 'outcome': v})

    _rv_df = pd.DataFrame(_resp_values_all)

    # Group outcomes into display categories
    def _outcome_category(v):
        if v == 'NO RESPONSE':
            return 'No Response'
        if v.startswith('TH'):
            return v  # keep TH-10, TH-15, etc.
        if v in ('NU 5+', 'NU5+'):
            return 'NU 5+ (Success)'
        if v in ('NU 1-4', 'NU1-4'):
            return 'NU 1-4 (Partial)'
        return v

    _rv_df['category'] = _rv_df['outcome'].apply(_outcome_category)

    # Overall distribution (exclude No Response for the chart)
    _cat_counts = _rv_df[_rv_df['category'] != 'No Response']['category'].value_counts()

    # Color mapping
    _cat_colors = {}
    for cat in _cat_counts.index:
        if cat.startswith('TH'):
            _cat_colors[cat] = GEN_COLORS['success']
        elif 'Success' in cat or '5+' in cat:
            _cat_colors[cat] = GEN_COLORS['info']
        elif 'Partial' in cat or '1-4' in cat:
            _cat_colors[cat] = GEN_COLORS['warning']
        else:
            _cat_colors[cat] = GEN_COLORS['muted']

    # -----------------------------------------------------------------
    # 2. NU conversion tracking: do NU 1-4 accounts become NU 5+ later?
    # -----------------------------------------------------------------
    _acct_col_name = 'Acct Number' if 'Acct Number' in camp_raw.columns else ' Acct Number'
    _nu_tracking = []
    _nu_partial_ever = set()
    _nu_success_ever = set()

    _sorted_periods = camp_summary['period'].tolist()
    _mc_map = {mc.replace(' Mail', ''): mc for mc in mail_cols}
    _rc_map = {rc.replace(' Resp', ''): rc for rc in resp_cols}

    for period in _sorted_periods:
        mc = _mc_map.get(period)
        rc = _rc_map.get(period)
        if mc is None or rc is None:
            continue

        _mailed = camp_raw[mc].notna()
        _resp = camp_raw[rc]
        _accts = camp_raw[_acct_col_name].astype(str).str.strip()

        _rv = _resp.astype(str).str.strip().str.upper()
        _nu14_mask = _rv.isin(['NU 1-4', 'NU1-4']) & _resp.notna()
        _nu5_mask = _rv.isin(['NU 5+', 'NU5+']) & _resp.notna()

        _nu14_accts = set(_accts[_nu14_mask])
        _nu5_accts = set(_accts[_nu5_mask])

        converted = _nu_partial_ever & _nu5_accts
        still_partial = _nu_partial_ever & _nu14_accts

        _nu_tracking.append({
            'period': period,
            'nu_14_this_wave': len(_nu14_accts),
            'nu_5plus_this_wave': len(_nu5_accts),
            'prior_nu14_converted': len(converted),
            'prior_nu14_still_partial': len(still_partial),
            'cum_nu14_pool': len(_nu_partial_ever),
        })

        _nu_partial_ever |= _nu14_accts
        _nu_success_ever |= _nu5_accts

    _nu_df = pd.DataFrame(_nu_tracking)

    # =================================================================
    # CHART 1: Challenge Outcome Distribution
    # =================================================================
    if len(_cat_counts) > 0:
        fig1, ax1 = plt.subplots(figsize=(14, 7))

        _sorted_cats = _cat_counts.sort_values()
        _names = [str(n)[:25] for n in _sorted_cats.index]
        _y_pos = range(len(_sorted_cats))
        _colors = [_cat_colors.get(c, GEN_COLORS['muted']) for c in _sorted_cats.index]

        ax1.barh(_y_pos, _sorted_cats.values, color=_colors,
                 edgecolor='white', linewidth=0.5, height=0.65)
        ax1.set_yticks(_y_pos)
        ax1.set_yticklabels(_names, fontsize=14, fontweight='bold')
        ax1.set_xlabel("Count (account-periods)", fontsize=16, fontweight='bold', labelpad=8)

        for j, (cat_name, count) in enumerate(_sorted_cats.items()):
            _total_responses = _cat_counts.sum()
            _pct = count / _total_responses * 100
            ax1.text(count + _total_responses * 0.01, j,
                     f"{count:,} ({_pct:.1f}%)",
                     va='center', fontsize=14, fontweight='bold',
                     color=GEN_COLORS['dark_text'])

        gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
        ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax1.set_axisbelow(True)

        ax1.set_title("Challenge Outcome Distribution",
                       fontsize=26, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax1.text(0.0, 1.02,
                 f"Which challenge types drive the most responses?  ({DATASET_LABEL})",
                 transform=ax1.transAxes, fontsize=14,
                 color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()

    # =================================================================
    # CHART 2: NU Conversion Pipeline by Wave
    # =================================================================
    if len(_nu_df) > 0 and _nu_df['nu_14_this_wave'].sum() > 0:
        fig2, ax2 = plt.subplots(figsize=(14, 7))

        x = range(len(_nu_df))

        ax2.bar(x, _nu_df['nu_14_this_wave'], color=GEN_COLORS['warning'],
                edgecolor='white', linewidth=0.5, width=0.6, label='NU 1-4 (Partial)')
        ax2.bar(x, _nu_df['nu_5plus_this_wave'], bottom=_nu_df['nu_14_this_wave'],
                color=GEN_COLORS['success'], edgecolor='white', linewidth=0.5,
                width=0.6, label='NU 5+ (Success)')

        # Overlay: conversions from prior NU 1-4 pool
        if _nu_df['prior_nu14_converted'].sum() > 0:
            ax2b = ax2.twinx()
            ax2b.plot(list(x), _nu_df['prior_nu14_converted'],
                      color=GEN_COLORS['accent'], linewidth=2.5, marker='D',
                      markersize=7, markeredgecolor='white', markeredgewidth=1.5,
                      label='Prior NU 1-4 Converted', zorder=5)
            ax2b.set_ylabel("Prior NU 1-4 Converted to NU 5+", fontsize=16,
                            fontweight='bold', color=GEN_COLORS['accent'], labelpad=10)
            ax2b.spines['top'].set_visible(False)
            ax2b.spines['left'].set_visible(False)
            ax2b.grid(False)
            ax2b.legend(loc='upper right', fontsize=14)

        ax2.set_xticks(list(x))
        ax2.set_xticklabels(_nu_df['period'], fontsize=14, fontweight='bold',
                            rotation=45, ha='right')
        ax2.set_ylabel("Accounts per Wave", fontsize=16, fontweight='bold', labelpad=10)

        gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
        ax2.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax2.set_axisbelow(True)
        ax2.legend(loc='upper left', fontsize=14)

        ax2.set_title("Non-User Conversion Pipeline by Wave",
                       fontsize=26, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax2.text(0.0, 1.02,
                 f"NU 1-4 vs NU 5+ each wave, with prior-wave conversions  ({DATASET_LABEL})",
                 transform=ax2.transAxes, fontsize=14,
                 color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()

    # =================================================================
    # CHART 3: Cumulative NU Conversion Funnel
    # =================================================================
    _total_nu14_ever = len(_nu_partial_ever)
    _total_nu5_ever = len(_nu_success_ever)
    _converted_ever = len(_nu_partial_ever & _nu_success_ever)
    _conversion_rate = _converted_ever / _total_nu14_ever * 100 if _total_nu14_ever > 0 else 0

    if _total_nu14_ever > 0:
        fig3, ax3 = plt.subplots(figsize=(14, 7))

        _never_converted = _total_nu14_ever - _converted_ever
        funnel_labels = ['Total NU 1-4\n(Ever)', 'Converted to\nNU 5+', 'Never\nConverted']
        funnel_values = [_total_nu14_ever, _converted_ever, _never_converted]
        funnel_colors = [GEN_COLORS['warning'], GEN_COLORS['success'], GEN_COLORS['muted']]

        bars = ax3.bar(range(len(funnel_labels)), funnel_values,
                       color=funnel_colors, edgecolor='white', linewidth=0.5, width=0.5)

        ax3.set_xticks(range(len(funnel_labels)))
        ax3.set_xticklabels(funnel_labels, fontsize=14, fontweight='bold')
        ax3.set_ylabel("Unique Accounts", fontsize=16, fontweight='bold', labelpad=10)

        for bar, val in zip(bars, funnel_values):
            pct = val / _total_nu14_ever * 100
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                     f"{val:,}\n({pct:.1f}%)",
                     ha='center', va='bottom', fontsize=14, fontweight='bold',
                     color=GEN_COLORS['dark_text'])

        gen_clean_axes(ax3, keep_left=True, keep_bottom=True)
        ax3.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax3.set_axisbelow(True)

        ax3.set_title("Non-User Conversion Funnel (Cumulative)",
                       fontsize=26, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=35, loc='left')
        ax3.text(0.0, 1.02,
                 f"Do NU 1-4 accounts eventually convert to NU 5+ in later waves?  ({DATASET_LABEL})",
                 transform=ax3.transAxes, fontsize=14,
                 color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()

    # -----------------------------------------------------------------
    # Summary stats
    # -----------------------------------------------------------------
    print(f"\n    Challenge outcome distribution (across all periods):")
    for cat, count in _cat_counts.items():
        print(f"      {cat:<25s}: {count:>6,}")

    print(f"\n    Non-User conversion tracking:")
    print(f"      Total unique NU 1-4 accounts (ever): {_total_nu14_ever:,}")
    print(f"      Total unique NU 5+ accounts (ever):  {_total_nu5_ever:,}")
    print(f"      NU 1-4 who later hit NU 5+:          {_converted_ever:,} ({_conversion_rate:.1f}% conversion)")
    if _total_nu14_ever > 0:
        _never_converted = _total_nu14_ever - _converted_ever
        print(f"      NU 1-4 never converted:              {_never_converted:,} ({_never_converted/_total_nu14_ever*100:.1f}%)")
