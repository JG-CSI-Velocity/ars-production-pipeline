# ===========================================================================
# SEGMENT COHORT DATA: Build Per-Account Spend + Swipe Time Series
# ===========================================================================
# For each mailer wave, classifies EVERY mailed account into a challenge
# segment and response status, then attaches monthly spend and swipe values
# at offsets relative to the mail date (-6 to +36 months).
#
# Segment assignment priority:
#   1. Responders (TH-* or NU 5+) → segment from resp column
#   2. NU 1-4 (tried, missed) → segment = NU, status = Non-Responder
#   3. Null response → segment from mail column if available, else Unknown
#
# Output:  segment_cohort_raw  (one row per account × wave)
#   Columns: acct_number, wave, wave_date, segment, status,
#            m-6..m+36 (spend), sw-6..sw+36 (swipes)
#
# Depends on: WAVE_CONFIG, spend_lookup, swipe_month_map, rewards_df (cell 11)

try:
    if 'WAVE_CONFIG' not in dir() or len(WAVE_CONFIG) == 0:
        raise NameError("WAVE_CONFIG not available -- run cell 11 first")

    _acct_col = 'Acct Number' if 'Acct Number' in rewards_df.columns else ' Acct Number'

    # ------------------------------------------------------------------
    # Segment parser
    # ------------------------------------------------------------------
    def _parse_segment(val):
        """Map a mail or resp value to a canonical segment label."""
        if pd.isna(val):
            return None
        v = str(val).strip().upper()
        if v.startswith('TH-'):
            return v
        if v.startswith('TH') and len(v) > 2 and v[2:].strip('-').isdigit():
            return f"TH-{v[2:].strip('-')}"
        if v in ('NU 5+', 'NU5+', 'NU 5', 'NU 6', 'NU 7', 'NU 8', 'NU 9', 'NU 10',
                 'NU 1-4', 'NU1-4', 'NU', 'NON-USER', 'NONUSER', 'NON USER'):
            return 'NU'
        if v in ('10', '15', '20', '25'):
            return f"TH-{v}"
        if v in ('5', '5+'):
            return 'NU'
        return None

    # ------------------------------------------------------------------
    # Build raw data: one row per mailed account per wave
    # ------------------------------------------------------------------
    MAX_POST_MONTHS = 36
    MONTH_OFFSETS = list(range(-6, MAX_POST_MONTHS + 1))

    _wave_rows = []
    _overview = []

    for wave_label, wc in WAVE_CONFIG.items():
        mail_date = wc['mail_date']
        mc = wc['mail_col'].strip()
        rc = wc['resp_col'].strip()

        was_mailed = rewards_df[mc].notna()
        n_mailed = was_mailed.sum()
        if n_mailed == 0:
            continue

        # Classify segment and status
        resp_vals = rewards_df.loc[was_mailed, rc] if rc in rewards_cols else pd.Series(None, index=rewards_df.index[was_mailed])
        mail_vals = rewards_df.loc[was_mailed, mc]
        acct_nums = rewards_df.loc[was_mailed, _acct_col].astype(str).str.strip()

        resp_seg = resp_vals.map(_parse_segment)
        mail_seg = mail_vals.map(_parse_segment)

        _rv = resp_vals.astype(str).str.strip().str.upper()
        is_success = (_rv.str.startswith('TH') |
                      _rv.isin(['NU 5+', 'NU5+', 'NU 5', 'NU 6', 'NU 7', 'NU 8', 'NU 9', 'NU 10'])
                     ) & resp_vals.notna()

        # Segment: resp_segment > NU (for NU 1-4) > mail_segment > Unknown
        segment = pd.Series('Unknown', index=resp_vals.index)
        segment[mail_seg.notna()] = mail_seg[mail_seg.notna()]
        _is_nu_partial = _rv.isin(['NU 1-4', 'NU1-4']) & resp_vals.notna()
        segment[_is_nu_partial] = 'NU'
        segment[resp_seg.notna() & is_success] = resp_seg[resp_seg.notna() & is_success]

        status = pd.Series('Non-Responder', index=resp_vals.index)
        status[is_success] = 'Responder'

        # Collect spend + swipe values at each month offset
        spend_data = {}
        swipe_data = {}
        for offset in MONTH_OFFSETS:
            target = (mail_date + pd.DateOffset(months=offset)).strftime('%b%y')
            if target in spend_lookup:
                spend_data[offset] = pd.to_numeric(
                    rewards_df.loc[was_mailed, spend_lookup[target]], errors='coerce'
                ).fillna(0)
            if 'swipe_month_map' in dir() and target in swipe_month_map:
                swipe_data[offset] = pd.to_numeric(
                    rewards_df.loc[was_mailed, swipe_month_map[target]], errors='coerce'
                ).fillna(0)

        if len(spend_data) == 0:
            continue

        # Assemble wave DataFrame
        wdf = pd.DataFrame({
            'acct_number': acct_nums.values,
            'wave': wave_label,
            'wave_date': mail_date,
            'segment': segment.values,
            'status': status.values,
        })
        for o, vals in spend_data.items():
            wdf[f'm{o:+d}'] = vals.values
        for o, vals in swipe_data.items():
            wdf[f'sw{o:+d}'] = vals.values

        _wave_rows.append(wdf)

        # Overview stats
        seg_counts = pd.Series(segment.values).value_counts().to_dict()
        _overview.append({
            'Wave': wave_label,
            'Date': mail_date.strftime('%b %Y'),
            'Mailed': n_mailed,
            'Responders': int(is_success.sum()),
            'Spend Months': f"{min(spend_data):+d} to {max(spend_data):+d}",
            'Swipe Months': f"{min(swipe_data):+d} to {max(swipe_data):+d}" if swipe_data else '--',
            'Segments': ', '.join(f"{s}: {c:,}" for s, c in sorted(seg_counts.items()) if s != 'Unknown'),
        })

    if len(_wave_rows) == 0:
        raise ValueError("No waves with usable data")

    segment_cohort_raw = pd.concat(_wave_rows, ignore_index=True)

    # Fallback: if no segment has enough data in both groups, broaden TH-* → TH (All)
    MIN_SEGMENT_N = 10
    _xtab = segment_cohort_raw.groupby(['segment', 'status']).size().unstack(fill_value=0)
    _has_valid = any(
        _xtab.loc[s].get('Responder', 0) >= MIN_SEGMENT_N and
        _xtab.loc[s].get('Non-Responder', 0) >= MIN_SEGMENT_N
        for s in _xtab.index
    )
    if not _has_valid:
        segment_cohort_raw['segment'] = segment_cohort_raw['segment'].apply(
            lambda s: 'TH (All)' if s.startswith('TH') else s
        )
        print("    NOTE: Segments broadened to TH (All) / NU due to small group sizes.")

    # ------------------------------------------------------------------
    # Output: wave overview table
    # ------------------------------------------------------------------
    _ov_df = pd.DataFrame(_overview)
    _styled_ov = (
        _ov_df.style
        .hide(axis='index')
        .format({'Mailed': '{:,}', 'Responders': '{:,}'})
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
        .set_caption("Segment Cohort Data: Wave Overview")
    )
    display(_styled_ov)

    # Segment × Status cross-tab
    _xtab_final = segment_cohort_raw.groupby(['segment', 'status']).size().unstack(fill_value=0)
    _xtab_final['Total'] = _xtab_final.sum(axis=1)
    _styled_xtab = (
        _xtab_final.style
        .format('{:,}')
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
        .set_caption("Segment x Status: Account Counts (All Mailers Pooled)")
    )
    display(_styled_xtab)

    _spend_cols = [c for c in segment_cohort_raw.columns if c.startswith('m') and ('+' in c or '-' in c)]
    _swipe_cols = [c for c in segment_cohort_raw.columns if c.startswith('sw')]
    print(f"\n    segment_cohort_raw: {len(segment_cohort_raw):,} rows  |  "
          f"{len(_spend_cols)} spend months  |  {len(_swipe_cols)} swipe months")

except (NameError, KeyError, ValueError) as e:
    print(f"    Segment cohort data not available: {e}")
    print("    Ensure cells 01 and 11 have been run first.")
    segment_cohort_raw = pd.DataFrame()
