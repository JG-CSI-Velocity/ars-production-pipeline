# ===========================================================================
# RESPONDER SPEND SHIFT -- DATA (before vs after each account's mail anchor)
# ===========================================================================
# The question this answers (#251 discussion): for people who responded to a
# mail offer -- where were they spending before, where now, how much, and did
# the PIN/SIG mix or the vendor mix change? Non-Responders are computed side
# by side as the control, anchored the same way, so a shift can be attributed
# to the offer rather than to a market-wide trend.
#
# Anchors (per account):
#   Responder     -> month of their FIRST successful response (TH*/NU 5+)
#   Non-Responder -> month they were FIRST mailed
#   Never Mailed  -> excluded
# Windows: PRE = the 3 full months strictly before the anchor month,
#          POST = the 3 full months strictly after it (the anchor month is the
#          transition and belongs to neither). Accounts whose windows extend
#          past the loaded transaction range are excluded and counted, so the
#          comparison never mixes partial windows.

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping spend-shift analysis.")
    ss_summary = pd.DataFrame()
else:
    print("=" * 100)
    print(" " * 30 + "RESPONDER SPEND SHIFT (before vs after mail anchor)")
    print("=" * 100)

    # ---- Per-account anchor month, scanning waves chronologically ---------
    _ss_pairs = sorted(
        zip(mail_cols, resp_cols),
        key=lambda mr: _period_sort_key(mr[0].replace(' Mail', '')),
    )
    _ss_n = len(camp_raw)
    _ss_resp_anchor = np.full(_ss_n, np.nan)
    _ss_mail_anchor = np.full(_ss_n, np.nan)
    for _mc, _rc in _ss_pairs:
        _key = float(_period_sort_key(_mc.replace(' Mail', '')))
        _hit = camp_raw[_rc].map(_is_success).to_numpy() & np.isnan(_ss_resp_anchor)
        _ss_resp_anchor = np.where(_hit, _key, _ss_resp_anchor)
        _mailed = camp_raw[_mc].notna().to_numpy() & np.isnan(_ss_mail_anchor)
        _ss_mail_anchor = np.where(_mailed, _key, _ss_mail_anchor)

    _ss_status = camp_acct['camp_status'].to_numpy()
    ss_anchor_df = pd.DataFrame({
        'primary_account_num': camp_raw['Acct Number'].to_numpy(),
        'camp_status': _ss_status,
        'anchor_key': np.where(_ss_status == 'Responder',
                               _ss_resp_anchor, _ss_mail_anchor),
    })
    ss_anchor_df = ss_anchor_df[
        ss_anchor_df['camp_status'].isin(['Responder', 'Non-Responder'])
    ].dropna(subset=['anchor_key'])

    # anchor_key is YYYYMM; convert to a linear month index for window math
    _ak = ss_anchor_df['anchor_key'].astype(int)
    ss_anchor_df['anchor_mi'] = (_ak // 100) * 12 + (_ak % 100 - 1)

    # ---- Coverage: both windows must sit inside the loaded txn range ------
    _ss_start_mi = DATASET_START.year * 12 + DATASET_START.month - 1
    _ss_end_mi = DATASET_END.year * 12 + DATASET_END.month - 1
    _ss_covered = (
        (ss_anchor_df['anchor_mi'] - 3 >= _ss_start_mi)
        & (ss_anchor_df['anchor_mi'] + 3 <= _ss_end_mi)
    )
    ss_excluded = {'no_full_window': int((~_ss_covered).sum())}
    ss_anchor_df = ss_anchor_df[_ss_covered]
    print(f"  Anchored accounts with full PRE+POST windows: {len(ss_anchor_df):,} "
          f"({ss_excluded['no_full_window']:,} excluded -- windows fall outside "
          f"{DATASET_LABEL})")

    if len(ss_anchor_df) == 0:
        print("    No accounts have full before/after windows inside the data "
              "range. Skipping spend-shift analysis.")
        ss_summary = pd.DataFrame()
    else:
        # ---- Window-tag each transaction of an anchored account -----------
        ss_txn = camp_txn[
            ['primary_account_num', 'amount', 'transaction_type',
             'merchant_consolidated', 'year_month']
        ].merge(
            ss_anchor_df[['primary_account_num', 'camp_status', 'anchor_mi']],
            on='primary_account_num', how='inner',
        )
        ss_txn['month_index'] = (
            ss_txn['year_month'].dt.year * 12 + (ss_txn['year_month'].dt.month - 1)
        )
        _rel = ss_txn['month_index'] - ss_txn['anchor_mi']
        ss_txn['window'] = np.where(
            (_rel >= -3) & (_rel <= -1), 'PRE',
            np.where((_rel >= 1) & (_rel <= 3), 'POST', 'OUT'),
        )
        ss_win = ss_txn[ss_txn['window'] != 'OUT'].copy()
        _tt = ss_win['transaction_type'].astype(str).str.upper().str.strip()
        ss_win['is_pin'] = _tt.eq('PIN')
        ss_win['is_sig'] = _tt.eq('SIG')

        # ---- Cohort x window summary --------------------------------------
        # Denominator: ALL anchored+covered accounts in the cohort (not just
        # the ones with activity in the window), so per-account averages are
        # comparable between PRE and POST.
        _ss_n_by_cohort = ss_anchor_df.groupby('camp_status')['primary_account_num'].nunique()
        ss_summary = ss_win.groupby(['camp_status', 'window'], observed=True).agg(
            total_spend=('amount', 'sum'),
            txns=('amount', 'count'),
            pin_txns=('is_pin', 'sum'),
            sig_txns=('is_sig', 'sum'),
            accounts_active=('primary_account_num', 'nunique'),
        ).reset_index()
        ss_summary['n_accounts'] = ss_summary['camp_status'].map(_ss_n_by_cohort)
        ss_summary['avg_monthly_spend_per_acct'] = (
            ss_summary['total_spend'] / ss_summary['n_accounts'] / 3.0
        )
        _ss_ps = (ss_summary['pin_txns'] + ss_summary['sig_txns']).replace(0, np.nan)
        ss_summary['sig_share_pct'] = ss_summary['sig_txns'] / _ss_ps * 100

        # ---- Vendor mix per cohort x window -------------------------------
        ss_vendors = (
            ss_win.groupby(['camp_status', 'window', 'merchant_consolidated'],
                           observed=True)['amount']
            .sum().reset_index(name='spend')
        )

        # Responder vendor shift: entered / exited / grew / shrank
        _rv = ss_vendors[ss_vendors['camp_status'] == 'Responder'].pivot_table(
            index='merchant_consolidated', columns='window',
            values='spend', fill_value=0.0,
        )
        for _w in ('PRE', 'POST'):
            if _w not in _rv.columns:
                _rv[_w] = 0.0
        ss_vendor_shift = _rv[['PRE', 'POST']].copy()
        ss_vendor_shift['delta'] = ss_vendor_shift['POST'] - ss_vendor_shift['PRE']
        ss_vendor_shift['shift'] = np.where(
            ss_vendor_shift['PRE'] == 0, 'NEW',
            np.where(ss_vendor_shift['POST'] == 0, 'GONE',
                     np.where(ss_vendor_shift['delta'] >= 0, 'GREW', 'SHRANK')),
        )
        ss_vendor_shift = ss_vendor_shift.sort_values('POST', ascending=False)

        # ---- Console headline ---------------------------------------------
        for _st in ('Responder', 'Non-Responder'):
            _rows = ss_summary[ss_summary['camp_status'] == _st]
            _pre = _rows[_rows['window'] == 'PRE']
            _post = _rows[_rows['window'] == 'POST']
            if len(_pre) and len(_post):
                _p, _q = _pre.iloc[0], _post.iloc[0]
                print(f"  {_st}: ${_p['avg_monthly_spend_per_acct']:,.0f} -> "
                      f"${_q['avg_monthly_spend_per_acct']:,.0f} avg monthly spend/acct | "
                      f"SIG share {_p['sig_share_pct']:.1f}% -> {_q['sig_share_pct']:.1f}% "
                      f"(n={int(_p['n_accounts']):,})")
        _new_v = ss_vendor_shift[ss_vendor_shift['shift'] == 'NEW']
        _gone_v = ss_vendor_shift[ss_vendor_shift['shift'] == 'GONE']
        print(f"  Responder vendor mix: {len(_new_v):,} merchants entered, "
              f"{len(_gone_v):,} exited between windows")
