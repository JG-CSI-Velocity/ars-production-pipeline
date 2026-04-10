# ===========================================================================
# COHORT LIFT DATA: Before/After Spend Analysis by Mail Wave (Conference Ed.)
# ===========================================================================
# Builds per-wave cohort data using monthly Spend/Swipes from ODDD.
# For each wave: identifies responders vs non-responders, computes pre/post
# spend averages, and calculates Difference-in-Differences (DID) lift.
# Outputs: WAVE_CONFIG, cohort_acct, cohort_summary, cohort_did
# Guard: try/except for missing columns.

try:
    if 'camp_acct' not in dir() or len(camp_acct) == 0:
        raise NameError("camp_acct not available")

    # -----------------------------------------------------------------
    # 1. Discover monthly Spend and Swipes columns dynamically
    # -----------------------------------------------------------------
    rewards_cols = [c.strip() for c in rewards_df.columns]

    _VALID_MON = {'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'}

    spend_month_cols = sorted(
        [c for c in rewards_cols if c.endswith(' Spend') and c[0].isupper()
         and len(c.split(' ')[0]) in (5, 6)
         and c.split(' ')[0][:3] in _VALID_MON],
        key=lambda c: pd.to_datetime(c.replace(' Spend', ''), format='%b%y')
    )
    swipe_month_cols = sorted(
        [c for c in rewards_cols if c.endswith(' Swipes') and c[0].isupper()
         and len(c.split(' ')[0]) in (5, 6)
         and c.split(' ')[0][:3] in _VALID_MON],
        key=lambda c: pd.to_datetime(c.replace(' Swipes', ''), format='%b%y')
    )

    # Build lookup: month_label -> column name
    spend_lookup = {c.replace(' Spend', ''): c for c in spend_month_cols}
    swipe_month_map = {c.replace(' Swipes', ''): c for c in swipe_month_cols}

    # All available month labels in chronological order
    all_months = list(spend_lookup.keys())
    all_month_dates = [pd.to_datetime(m, format='%b%y') for m in all_months]

    print(f"    Monthly Spend columns: {len(spend_month_cols)} ({all_months[0]} to {all_months[-1]})")
    print(f"    Monthly Swipes columns: {len(swipe_month_cols)}")

    # -----------------------------------------------------------------
    # 2. Build WAVE_CONFIG from discovered mail/resp columns
    # -----------------------------------------------------------------
    # mail_cols and resp_cols come from 01_campaign_data
    WAVE_CONFIG = {}
    for mc, rc in zip(mail_cols, resp_cols):
        wave_label = mc.replace(' Mail', '')
        mail_date = pd.to_datetime(wave_label, format='%b%y')

        # Pre-period: 3 months before the mail month
        pre_months = []
        for m, d in zip(all_months, all_month_dates):
            months_before = (mail_date.year - d.year) * 12 + (mail_date.month - d.month)
            if 1 <= months_before <= 3:
                pre_months.append(m)

        # Post-period windows: 1mo, 3mo, 6mo after mail month
        post_1mo, post_3mo, post_6mo = [], [], []
        for m, d in zip(all_months, all_month_dates):
            months_after = (d.year - mail_date.year) * 12 + (d.month - mail_date.month)
            if months_after == 1:
                post_1mo.append(m)
            if 1 <= months_after <= 3:
                post_3mo.append(m)
            if 1 <= months_after <= 6:
                post_6mo.append(m)

        # Only include waves where we have at least 1 month post-data
        if len(post_1mo) > 0 and len(pre_months) > 0:
            WAVE_CONFIG[wave_label] = {
                'mail_col': mc,
                'resp_col': rc,
                'mail_date': mail_date,
                'pre_months': pre_months,
                'post_1mo': post_1mo,
                'post_3mo': post_3mo if len(post_3mo) >= 2 else post_1mo,
                'post_6mo': post_6mo if len(post_6mo) >= 4 else None,
            }

    print(f"\n    Waves with analyzable pre/post data: {len(WAVE_CONFIG)}")
    for wl, wc in WAVE_CONFIG.items():
        post_info = f"1mo={len(wc['post_1mo'])}, 3mo={len(wc['post_3mo'])}"
        if wc['post_6mo']:
            post_info += f", 6mo={len(wc['post_6mo'])}"
        print(f"      {wl}: pre={wc['pre_months']}, post=[{post_info}]")

    # -----------------------------------------------------------------
    # 3. Build cohort_acct: one row per account-wave
    # -----------------------------------------------------------------
    cohort_rows = []
    acct_nums = rewards_df['Acct Number' if 'Acct Number' in rewards_df.columns
                           else ' Acct Number'].astype(str).str.strip()

    for wave_label, wc in WAVE_CONFIG.items():
        # Determine responder status for this wave
        resp_col = wc['resp_col'].strip()
        mail_col = wc['mail_col'].strip()

        # Check columns exist
        resp_available = resp_col in rewards_cols
        mail_available = mail_col in rewards_cols

        if not mail_available:
            continue

        was_mailed = rewards_df[mail_col].notna()
        # TH-* or NU 5+ = success; NU 1-4 = near-use
        if resp_available:
            _rv = rewards_df[resp_col]
            was_responded = _rv.map(lambda v: False if pd.isna(v) else str(v).strip().upper().startswith('TH') or str(v).strip().upper() in ('NU 5+','NU5+','NU 5','NU 6','NU 7','NU 8','NU 9','NU 10'))
            was_near_use = _rv.map(lambda v: False if pd.isna(v) else str(v).strip().upper() in ('NU 1-4','NU1-4'))
        else:
            was_responded = pd.Series(False, index=rewards_df.index)
            was_near_use = pd.Series(False, index=rewards_df.index)

        # Pre-period avg spend/swipes
        pre_spend_cols = [spend_lookup[m] for m in wc['pre_months'] if m in spend_lookup]
        pre_swipe_cols = [swipe_month_map[m] for m in wc['pre_months'] if m in swipe_month_map]

        # Post-period avg spend/swipes (use 3mo window as default)
        post_months = wc['post_3mo']
        post_spend_cols = [spend_lookup[m] for m in post_months if m in spend_lookup]
        post_swipe_cols = [swipe_month_map[m] for m in post_months if m in swipe_month_map]

        if len(pre_spend_cols) == 0 or len(post_spend_cols) == 0:
            continue

        pre_spend_vals = rewards_df[pre_spend_cols].apply(
            pd.to_numeric, errors='coerce'
        ).mean(axis=1).fillna(0)

        post_spend_vals = rewards_df[post_spend_cols].apply(
            pd.to_numeric, errors='coerce'
        ).mean(axis=1).fillna(0)

        pre_swipe_vals = rewards_df[pre_swipe_cols].apply(
            pd.to_numeric, errors='coerce'
        ).mean(axis=1).fillna(0) if len(pre_swipe_cols) > 0 else pd.Series(0, index=rewards_df.index)

        post_swipe_vals = rewards_df[post_swipe_cols].apply(
            pd.to_numeric, errors='coerce'
        ).mean(axis=1).fillna(0) if len(post_swipe_cols) > 0 else pd.Series(0, index=rewards_df.index)

        # Build rows for mailed accounts only
        # NU 1-4 = Non-Responder (tracked via nu_partial flag for conversion analysis)
        mask = was_mailed
        for idx in rewards_df.index[mask]:
            _status = 'Responder' if was_responded.loc[idx] else 'Non-Responder'
            cohort_rows.append({
                'acct_number': acct_nums.loc[idx],
                'wave': wave_label,
                'wave_date': wc['mail_date'],
                'status': _status,
                'nu_partial': bool(was_near_use.loc[idx]),
                'pre_spend': pre_spend_vals.loc[idx],
                'post_spend': post_spend_vals.loc[idx],
                'spend_delta': post_spend_vals.loc[idx] - pre_spend_vals.loc[idx],
                'pre_swipes': pre_swipe_vals.loc[idx],
                'post_swipes': post_swipe_vals.loc[idx],
                'swipe_delta': post_swipe_vals.loc[idx] - pre_swipe_vals.loc[idx],
                'post_window_months': len(post_months),
            })

    cohort_acct = pd.DataFrame(cohort_rows)
    print(f"\n    cohort_acct: {len(cohort_acct):,} account-wave rows")
    print(f"    Responders: {(cohort_acct['status'] == 'Responder').sum():,}")
    print(f"    Non-Responders: {(cohort_acct['status'] == 'Non-Responder').sum():,}")
    print(f"    of which NU 1-4: {cohort_acct['nu_partial'].sum():,} (showed activity, missed goal)")

    # -----------------------------------------------------------------
    # 4. Build cohort_summary: one row per wave with DID
    # -----------------------------------------------------------------
    summary_rows = []
    for wave_label in WAVE_CONFIG:
        wdf = cohort_acct[cohort_acct['wave'] == wave_label]
        resp = wdf[wdf['status'] == 'Responder']
        nonresp = wdf[wdf['status'] == 'Non-Responder']

        if len(resp) == 0 or len(nonresp) == 0:
            continue

        resp_pre = resp['pre_spend'].mean()
        resp_post = resp['post_spend'].mean()
        resp_delta = resp_post - resp_pre

        nonresp_pre = nonresp['pre_spend'].mean()
        nonresp_post = nonresp['post_spend'].mean()
        nonresp_delta = nonresp_post - nonresp_pre

        did_spend = resp_delta - nonresp_delta

        # Swipes DID
        resp_swipe_delta = resp['post_swipes'].mean() - resp['pre_swipes'].mean()
        nonresp_swipe_delta = nonresp['post_swipes'].mean() - nonresp['pre_swipes'].mean()
        did_swipes = resp_swipe_delta - nonresp_swipe_delta

        summary_rows.append({
            'wave': wave_label,
            'wave_date': WAVE_CONFIG[wave_label]['mail_date'],
            'mailed': len(wdf),
            'responded': len(resp),
            'response_rate': len(resp) / len(wdf) * 100,
            'resp_pre_spend': resp_pre,
            'resp_post_spend': resp_post,
            'resp_spend_delta': resp_delta,
            'nonresp_pre_spend': nonresp_pre,
            'nonresp_post_spend': nonresp_post,
            'nonresp_spend_delta': nonresp_delta,
            'did_spend_lift': did_spend,
            'did_spend_pct': did_spend / resp_pre * 100 if resp_pre > 0 else 0,
            'resp_swipe_delta': resp_swipe_delta,
            'nonresp_swipe_delta': nonresp_swipe_delta,
            'did_swipes_lift': did_swipes,
        })

    cohort_summary = pd.DataFrame(summary_rows).sort_values('wave_date').reset_index(drop=True)
    cohort_did = cohort_summary[['wave', 'wave_date', 'did_spend_lift', 'did_spend_pct',
                                  'did_swipes_lift', 'mailed', 'responded', 'response_rate']].copy()

    # -----------------------------------------------------------------
    # 5. Build persistence data (1mo, 3mo, 6mo post windows)
    # -----------------------------------------------------------------
    persist_rows = []
    for wave_label, wc in WAVE_CONFIG.items():
        for window_name, window_months in [('1mo', wc['post_1mo']),
                                            ('3mo', wc['post_3mo']),
                                            ('6mo', wc['post_6mo'])]:
            if window_months is None or len(window_months) == 0:
                continue

            post_s_cols = [spend_lookup[m] for m in window_months if m in spend_lookup]
            pre_s_cols = [spend_lookup[m] for m in wc['pre_months'] if m in spend_lookup]

            if len(post_s_cols) == 0 or len(pre_s_cols) == 0:
                continue

            mail_col = wc['mail_col'].strip()
            resp_col = wc['resp_col'].strip()
            was_mailed = rewards_df[mail_col].notna()
            if resp_col in rewards_cols:
                _rv = rewards_df[resp_col]
                was_responded = _rv.map(lambda v: False if pd.isna(v) else str(v).strip().upper().startswith('TH') or str(v).strip().upper() in ('NU 5+','NU5+','NU 5','NU 6','NU 7','NU 8','NU 9','NU 10'))
                was_near_use = _rv.map(lambda v: False if pd.isna(v) else str(v).strip().upper() in ('NU 1-4','NU1-4'))
            else:
                was_responded = pd.Series(False, index=rewards_df.index)
                was_near_use = pd.Series(False, index=rewards_df.index)

            pre_vals = rewards_df[pre_s_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1).fillna(0)
            post_vals = rewards_df[post_s_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1).fillna(0)

            for label, mask in [('Responder', was_mailed & was_responded),
                                ('Non-Responder', was_mailed & ~was_responded)]:
                if mask.sum() == 0:
                    continue
                avg_pre = pre_vals[mask].mean()
                avg_post = post_vals[mask].mean()
                persist_rows.append({
                    'wave': wave_label,
                    'window': window_name,
                    'status': label,
                    'pre_spend': avg_pre,
                    'post_spend': avg_post,
                    'delta': avg_post - avg_pre,
                    'n_accounts': mask.sum(),
                })

    cohort_persist = pd.DataFrame(persist_rows)

    # -----------------------------------------------------------------
    # 6. Display summary table
    # -----------------------------------------------------------------
    disp_cols = ['wave', 'mailed', 'responded', 'response_rate',
                 'resp_spend_delta', 'nonresp_spend_delta', 'did_spend_lift', 'did_spend_pct']
    disp_df = cohort_summary[disp_cols].copy()
    disp_df.columns = ['Wave', 'Mailed', 'Responded', 'Resp Rate %',
                        'Resp Delta', 'Non-Resp Delta', 'DID Lift ($)', 'DID Lift %']

    styled = (
        disp_df.style
        .hide(axis='index')
        .format({
            'Mailed': '{:,.0f}',
            'Responded': '{:,.0f}',
            'Resp Rate %': '{:.1f}%',
            'Resp Delta': '${:,.2f}',
            'Non-Resp Delta': '${:,.2f}',
            'DID Lift ($)': '${:,.2f}',
            'DID Lift %': '{:+.1f}%',
        })
        .set_properties(**{
            'font-size': '13px', 'font-weight': 'bold',
            'text-align': 'center', 'border': '1px solid #E9ECEF',
            'padding': '7px 10px',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['success']),
                ('color', 'white'), ('font-size', '14px'),
                ('font-weight', 'bold'), ('text-align', 'center'),
                ('padding', '8px 10px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'), ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption(f"Cohort Lift Analysis: Difference-in-Differences Summary  ({DATASET_LABEL})")
    )

    display(styled)

    avg_did = cohort_summary['did_spend_lift'].mean()
    print(f"\n    Average DID spend lift across waves: ${avg_did:,.2f}/account/month")
    print(f"    Interpretation: Responders changed spending by ${avg_did:,.2f}/mo MORE than non-responders")

except (NameError, KeyError) as e:
    print(f"    Cohort lift data not available: {e}")
    print("    Ensure campaign cells 01-10 have been run first.")
    cohort_acct = pd.DataFrame()
    cohort_summary = pd.DataFrame()
    cohort_did = pd.DataFrame()
    cohort_persist = pd.DataFrame()
