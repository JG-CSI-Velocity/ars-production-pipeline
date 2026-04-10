# ===========================================================================
# SEGMENT COHORT SUMMARY: Window Averages + Difference-in-Differences
# ===========================================================================
# Aggregates segment_cohort_raw into summary windows (3mo, 6mo, 12mo, etc.)
# and computes DID (treatment effect) for each segment.
#
# Output:  segment_cohort_summary  (one row per segment × status)
#   Columns: segment, status, n_accounts, {window}_spend, {window}_swipes
#
# Depends on: segment_cohort_raw (from cell 25)

if 'segment_cohort_raw' not in dir() or len(segment_cohort_raw) == 0:
    print("    No segment cohort data. Run cell 25 first.")
else:
    # Identify available offset columns
    _spend_cols = sorted(
        [c for c in segment_cohort_raw.columns if c.startswith('m') and ('+' in c or '-' in c)],
        key=lambda c: int(c[1:])
    )
    _swipe_cols = sorted(
        [c for c in segment_cohort_raw.columns if c.startswith('sw')],
        key=lambda c: int(c[2:])
    )
    _spend_offsets = [int(c[1:]) for c in _spend_cols]
    _swipe_offsets = [int(c[2:]) for c in _swipe_cols]

    # Valid segments: >= MIN_N in both Responder and Non-Responder
    MIN_N = 10
    _xtab = segment_cohort_raw.groupby(['segment', 'status']).size().unstack(fill_value=0)
    _valid_segs = [
        s for s in _xtab.index
        if _xtab.loc[s].get('Responder', 0) >= MIN_N
        and _xtab.loc[s].get('Non-Responder', 0) >= MIN_N
    ]

    if len(_valid_segs) == 0:
        print("    No segments with enough data in both groups.")
        segment_cohort_summary = pd.DataFrame()
    else:
        _filtered = segment_cohort_raw[segment_cohort_raw['segment'].isin(_valid_segs)]

        # Define time windows
        WINDOWS = {
            '3mo Pre':  {'offsets': [o for o in _spend_offsets if -3 <= o < 0]},
            '6mo Pre':  {'offsets': [o for o in _spend_offsets if -6 <= o < 0]},
            '3mo Post': {'offsets': [o for o in _spend_offsets if 1 <= o <= 3]},
            '6mo Post': {'offsets': [o for o in _spend_offsets if 1 <= o <= 6]},
            '12mo Post': {'offsets': [o for o in _spend_offsets if 1 <= o <= 12]},
            '24mo Post': {'offsets': [o for o in _spend_offsets if 1 <= o <= 24]},
            '36mo Post': {'offsets': [o for o in _spend_offsets if 1 <= o <= 36]},
        }

        # Build summary rows
        _rows = []
        for seg in _valid_segs:
            for stat in ['Responder', 'Non-Responder']:
                _data = _filtered[(_filtered['segment'] == seg) & (_filtered['status'] == stat)]
                if len(_data) == 0:
                    continue
                row = {'Segment': seg, 'Status': stat, 'Accounts': len(_data)}

                for win_name, cfg in WINDOWS.items():
                    # Spend
                    s_cols = [f'm{o:+d}' for o in cfg['offsets'] if f'm{o:+d}' in _data.columns]
                    row[f'{win_name} Spend'] = _data[s_cols].mean(axis=1).mean() if s_cols else None
                    # Swipes
                    sw_cols = [f'sw{o:+d}' for o in cfg['offsets'] if f'sw{o:+d}' in _data.columns]
                    row[f'{win_name} Swipes'] = _data[sw_cols].mean(axis=1).mean() if sw_cols else None

                _rows.append(row)

        segment_cohort_summary = pd.DataFrame(_rows)

        # ------------------------------------------------------------------
        # Display: Spend summary table
        # ------------------------------------------------------------------
        _spend_display_cols = ['Segment', 'Status', 'Accounts']
        _spend_fmt = {'Accounts': '{:,}'}
        for w in WINDOWS:
            col = f'{w} Spend'
            if col in segment_cohort_summary.columns and segment_cohort_summary[col].notna().any():
                _spend_display_cols.append(col)
                _spend_fmt[col] = '${:,.0f}'

        _spend_tbl = segment_cohort_summary[_spend_display_cols].copy()
        _styled_spend = (
            _spend_tbl.style
            .hide(axis='index')
            .format(_spend_fmt)
            .set_properties(**{
                'font-size': '13px', 'font-weight': 'bold',
                'text-align': 'center', 'border': '1px solid #E9ECEF',
                'padding': '7px 10px',
            })
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', GEN_COLORS.get('info', '#457B9D')),
                    ('color', 'white'), ('font-size', '13px'),
                    ('font-weight', 'bold'), ('text-align', 'center'),
                    ('padding', '8px 10px'),
                ]},
                {'selector': 'caption', 'props': [
                    ('font-size', '20px'), ('font-weight', 'bold'),
                    ('color', GEN_COLORS.get('dark_text', '#1B2A4A')),
                    ('text-align', 'left'), ('padding-bottom', '10px'),
                ]},
            ])
            .set_caption("Avg Monthly Spend by Segment x Status  (All Mailers Pooled)")
        )
        display(_styled_spend)

        # Display: Swipe summary table (if swipe data exists)
        _swipe_display_cols = ['Segment', 'Status', 'Accounts']
        _swipe_fmt = {'Accounts': '{:,}'}
        _has_swipe_data = False
        for w in WINDOWS:
            col = f'{w} Swipes'
            if col in segment_cohort_summary.columns and segment_cohort_summary[col].notna().any():
                _swipe_display_cols.append(col)
                _swipe_fmt[col] = '{:,.1f}'
                _has_swipe_data = True

        if _has_swipe_data:
            _swipe_tbl = segment_cohort_summary[_swipe_display_cols].copy()
            _styled_swipe = (
                _swipe_tbl.style
                .hide(axis='index')
                .format(_swipe_fmt)
                .set_properties(**{
                    'font-size': '13px', 'font-weight': 'bold',
                    'text-align': 'center', 'border': '1px solid #E9ECEF',
                    'padding': '7px 10px',
                })
                .set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', GEN_COLORS.get('success', '#2A9D8F')),
                        ('color', 'white'), ('font-size', '13px'),
                        ('font-weight', 'bold'), ('text-align', 'center'),
                        ('padding', '8px 10px'),
                    ]},
                    {'selector': 'caption', 'props': [
                        ('font-size', '20px'), ('font-weight', 'bold'),
                        ('color', GEN_COLORS.get('dark_text', '#1B2A4A')),
                        ('text-align', 'left'), ('padding-bottom', '10px'),
                    ]},
                ])
                .set_caption("Avg Monthly Swipes by Segment x Status  (All Mailers Pooled)")
            )
            display(_styled_swipe)

        # ------------------------------------------------------------------
        # DID table (styled, not print statements)
        # ------------------------------------------------------------------
        _did_rows = []
        _did_windows = ['3mo Post', '6mo Post', '12mo Post']
        _pre_window = '3mo Pre'

        for seg in _valid_segs:
            _r = segment_cohort_summary[
                (segment_cohort_summary['Segment'] == seg) &
                (segment_cohort_summary['Status'] == 'Responder')
            ]
            _nr = segment_cohort_summary[
                (segment_cohort_summary['Segment'] == seg) &
                (segment_cohort_summary['Status'] == 'Non-Responder')
            ]
            if len(_r) == 0 or len(_nr) == 0:
                continue

            did_row = {
                'Segment': seg,
                'Resp N': int(_r['Accounts'].iloc[0]),
                'Non-R N': int(_nr['Accounts'].iloc[0]),
            }

            for dw in _did_windows:
                spend_col = f'{dw} Spend'
                pre_col = f'{_pre_window} Spend'
                if spend_col in _r.columns and pre_col in _r.columns:
                    r_pre = _r[pre_col].iloc[0]
                    r_post = _r[spend_col].iloc[0]
                    nr_pre = _nr[pre_col].iloc[0]
                    nr_post = _nr[spend_col].iloc[0]
                    if all(v is not None for v in [r_pre, r_post, nr_pre, nr_post]):
                        did_row[f'DID {dw}'] = (r_post - r_pre) - (nr_post - nr_pre)

            _did_rows.append(did_row)

        if _did_rows:
            _did_df = pd.DataFrame(_did_rows)
            _did_fmt = {'Resp N': '{:,}', 'Non-R N': '{:,}'}
            for c in _did_df.columns:
                if c.startswith('DID'):
                    _did_fmt[c] = '${:+,.2f}/mo'

            _styled_did = (
                _did_df.style
                .hide(axis='index')
                .format(_did_fmt)
                .applymap(
                    lambda v: f'color: {GEN_COLORS.get("success", "#2A9D8F")}' if isinstance(v, (int, float)) and v > 0
                    else f'color: {GEN_COLORS.get("accent", "#E63946")}' if isinstance(v, (int, float)) and v < 0
                    else '',
                    subset=[c for c in _did_df.columns if c.startswith('DID')]
                )
                .set_properties(**{
                    'font-size': '14px', 'font-weight': 'bold',
                    'text-align': 'center', 'border': '1px solid #E9ECEF',
                    'padding': '8px 12px',
                })
                .set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', GEN_COLORS.get('warning', '#E9C46A')),
                        ('color', 'white'), ('font-size', '14px'),
                        ('font-weight', 'bold'), ('text-align', 'center'),
                        ('padding', '8px 12px'),
                    ]},
                    {'selector': 'caption', 'props': [
                        ('font-size', '20px'), ('font-weight', 'bold'),
                        ('color', GEN_COLORS.get('dark_text', '#1B2A4A')),
                        ('text-align', 'left'), ('padding-bottom', '10px'),
                    ]},
                ])
                .set_caption("Difference-in-Differences: Spend Lift by Segment  (All Mailers Pooled)")
            )
            display(_styled_did)
