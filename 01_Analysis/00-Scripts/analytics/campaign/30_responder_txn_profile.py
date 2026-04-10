# ===========================================================================
# RESPONDER TRANSACTION PROFILE: Ticket Size, Frequency & Timing
# ===========================================================================
# Merges transaction-level data with campaign status to compare HOW
# responders use their card vs non-responders.
#
# Key metrics per account:
#   - Avg ticket size (SIG and PIN separately)
#   - Transactions per month
#   - Unique active days per month
#   - Day-of-month distribution (early/mid/late)
#   - Day-of-week pattern
#
# Output: resp_txn_profile (per-account summary), resp_txn_detail (txn-level)
# Depends on: combined_df (setup), camp_acct (cell 01), WAVE_CONFIG (cell 11)

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
elif 'combined_df' not in dir() or len(combined_df) == 0:
    print("    No transaction data. Run setup cells first.")
else:
    # ------------------------------------------------------------------
    # 1. Merge transactions with campaign status
    # ------------------------------------------------------------------
    _merge_cols = ['primary_account_num', 'camp_status']
    if 'segment_cohort_raw' in dir() and len(segment_cohort_raw) > 0:
        # Get latest segment assignment per account (from most recent wave)
        _seg_latest = (
            segment_cohort_raw
            .sort_values('wave_date')
            .drop_duplicates(subset='acct_number', keep='last')
            [['acct_number', 'segment']]
            .rename(columns={'acct_number': 'primary_account_num'})
        )

    resp_txn_detail = combined_df.merge(
        camp_acct[_merge_cols], on='primary_account_num', how='inner'
    )

    # Only mailed accounts
    resp_txn_detail = resp_txn_detail[resp_txn_detail['camp_status'] != 'Never Mailed'].copy()

    # Attach segment if available
    if '_seg_latest' in dir():
        resp_txn_detail = resp_txn_detail.merge(
            _seg_latest, on='primary_account_num', how='left'
        )
        resp_txn_detail['segment'] = resp_txn_detail['segment'].fillna('Unknown')

    if len(resp_txn_detail) == 0:
        print("    No mailed account transactions found.")
    else:
        # Add time features
        resp_txn_detail['day_of_month'] = resp_txn_detail['transaction_date'].dt.day
        resp_txn_detail['day_of_week'] = resp_txn_detail['transaction_date'].dt.dayofweek  # 0=Mon
        resp_txn_detail['day_name'] = resp_txn_detail['transaction_date'].dt.day_name()
        resp_txn_detail['year_month_str'] = resp_txn_detail['transaction_date'].dt.to_period('M').astype(str)
        resp_txn_detail['is_sig'] = resp_txn_detail['transaction_type'].str.upper().str.strip() == 'SIG'
        resp_txn_detail['is_pin'] = resp_txn_detail['transaction_type'].str.upper().str.strip() == 'PIN'

        # Month part: early (1-10), mid (11-20), late (21-31)
        resp_txn_detail['month_part'] = pd.cut(
            resp_txn_detail['day_of_month'],
            bins=[0, 10, 20, 31],
            labels=['Early (1-10)', 'Mid (11-20)', 'Late (21-31)']
        )

        # ------------------------------------------------------------------
        # 2. Post-mail transactions only (after earliest mail date)
        # ------------------------------------------------------------------
        if 'WAVE_CONFIG' in dir() and len(WAVE_CONFIG) > 0:
            _earliest_mail = min(wc['mail_date'] for wc in WAVE_CONFIG.values())
            resp_txn_post = resp_txn_detail[
                resp_txn_detail['transaction_date'] >= _earliest_mail
            ].copy()
        else:
            resp_txn_post = resp_txn_detail.copy()

        # ------------------------------------------------------------------
        # 3. Per-account profile (post-mail period)
        # ------------------------------------------------------------------
        _acct_groups = resp_txn_post.groupby(['primary_account_num', 'camp_status'])

        resp_txn_profile = _acct_groups.agg(
            total_txns=('amount', 'count'),
            total_spend=('amount', 'sum'),
            avg_ticket=('amount', 'mean'),
            median_ticket=('amount', 'median'),
            sig_txns=('is_sig', 'sum'),
            pin_txns=('is_pin', 'sum'),
            unique_days=('transaction_date', 'nunique'),
            unique_months=('year_month_str', 'nunique'),
        ).reset_index()

        # Derived metrics
        resp_txn_profile['txns_per_month'] = (
            resp_txn_profile['total_txns'] / resp_txn_profile['unique_months'].clip(lower=1)
        )
        resp_txn_profile['active_days_per_month'] = (
            resp_txn_profile['unique_days'] / resp_txn_profile['unique_months'].clip(lower=1)
        )
        resp_txn_profile['sig_pct'] = (
            resp_txn_profile['sig_txns'] / resp_txn_profile['total_txns'].clip(lower=1) * 100
        )

        # SIG-only avg ticket
        _sig_tickets = (
            resp_txn_post[resp_txn_post['is_sig']]
            .groupby(['primary_account_num', 'camp_status'])['amount']
            .mean()
            .reset_index()
            .rename(columns={'amount': 'avg_sig_ticket'})
        )
        resp_txn_profile = resp_txn_profile.merge(
            _sig_tickets, on=['primary_account_num', 'camp_status'], how='left'
        )

        # PIN-only avg ticket
        _pin_tickets = (
            resp_txn_post[resp_txn_post['is_pin']]
            .groupby(['primary_account_num', 'camp_status'])['amount']
            .mean()
            .reset_index()
            .rename(columns={'amount': 'avg_pin_ticket'})
        )
        resp_txn_profile = resp_txn_profile.merge(
            _pin_tickets, on=['primary_account_num', 'camp_status'], how='left'
        )

        # Attach segment
        if '_seg_latest' in dir():
            resp_txn_profile = resp_txn_profile.merge(
                _seg_latest, on='primary_account_num', how='left'
            )
            resp_txn_profile['segment'] = resp_txn_profile['segment'].fillna('Unknown')

        # ------------------------------------------------------------------
        # 4. Day-of-month distribution by status (for timing analysis)
        # ------------------------------------------------------------------
        resp_dom_dist = (
            resp_txn_post
            .groupby(['camp_status', 'day_of_month'])
            .size()
            .reset_index(name='txn_count')
        )
        # Normalize to % within each status
        _status_totals = resp_dom_dist.groupby('camp_status')['txn_count'].transform('sum')
        resp_dom_dist['pct'] = resp_dom_dist['txn_count'] / _status_totals * 100

        # Day-of-week distribution
        resp_dow_dist = (
            resp_txn_post
            .groupby(['camp_status', 'day_of_week', 'day_name'])
            .size()
            .reset_index(name='txn_count')
        )
        _dow_totals = resp_dow_dist.groupby('camp_status')['txn_count'].transform('sum')
        resp_dow_dist['pct'] = resp_dow_dist['txn_count'] / _dow_totals * 100

        # Month-part distribution
        resp_mpart_dist = (
            resp_txn_post
            .groupby(['camp_status', 'month_part'])
            .size()
            .reset_index(name='txn_count')
        )
        _mp_totals = resp_mpart_dist.groupby('camp_status')['txn_count'].transform('sum')
        resp_mpart_dist['pct'] = resp_mpart_dist['txn_count'] / _mp_totals * 100

        # ------------------------------------------------------------------
        # 5. Summary comparison table
        # ------------------------------------------------------------------
        _summary = resp_txn_profile.groupby('camp_status').agg(
            accounts=('primary_account_num', 'nunique'),
            avg_ticket=('avg_ticket', 'mean'),
            median_ticket=('median_ticket', 'median'),
            avg_sig_ticket=('avg_sig_ticket', 'mean'),
            avg_pin_ticket=('avg_pin_ticket', 'mean'),
            txns_per_month=('txns_per_month', 'mean'),
            active_days_mo=('active_days_per_month', 'mean'),
            sig_pct=('sig_pct', 'mean'),
        ).reset_index()

        _summary.columns = [
            'Status', 'Accounts', 'Avg Ticket', 'Median Ticket',
            'Avg SIG Ticket', 'Avg PIN Ticket',
            'Txns/Month', 'Active Days/Month', 'SIG %',
        ]

        _styled = (
            _summary.style
            .hide(axis='index')
            .format({
                'Accounts': '{:,}',
                'Avg Ticket': '${:,.2f}',
                'Median Ticket': '${:,.2f}',
                'Avg SIG Ticket': '${:,.2f}',
                'Avg PIN Ticket': '${:,.2f}',
                'Txns/Month': '{:,.1f}',
                'Active Days/Month': '{:,.1f}',
                'SIG %': '{:.1f}%',
            })
            .set_properties(**{
                'font-size': '14px', 'font-weight': 'bold',
                'text-align': 'center', 'border': '1px solid #E9ECEF',
                'padding': '8px 12px',
            })
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', GEN_COLORS.get('info', '#457B9D')),
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
            .set_caption("Responder vs Non-Responder Transaction Profile  (Post-Mail Transactions)")
        )
        display(_styled)

        # Quick deltas
        if len(_summary) >= 2:
            _r = _summary[_summary['Status'] == 'Responder'].iloc[0]
            _nr = _summary[_summary['Status'] == 'Non-Responder'].iloc[0]
            print(f"\n    Key Differences (Responder vs Non-Responder):")
            print(f"      Avg ticket:        ${_r['Avg Ticket']:,.2f} vs ${_nr['Avg Ticket']:,.2f}  "
                  f"({(_r['Avg Ticket'] / _nr['Avg Ticket'] - 1) * 100:+.1f}%)")
            print(f"      Avg SIG ticket:    ${_r['Avg SIG Ticket']:,.2f} vs ${_nr['Avg SIG Ticket']:,.2f}  "
                  f"({(_r['Avg SIG Ticket'] / _nr['Avg SIG Ticket'] - 1) * 100:+.1f}%)")
            print(f"      Txns/month:        {_r['Txns/Month']:,.1f} vs {_nr['Txns/Month']:,.1f}  "
                  f"({(_r['Txns/Month'] / _nr['Txns/Month'] - 1) * 100:+.1f}%)")
            print(f"      Active days/month: {_r['Active Days/Month']:,.1f} vs {_nr['Active Days/Month']:,.1f}  "
                  f"({(_r['Active Days/Month'] / _nr['Active Days/Month'] - 1) * 100:+.1f}%)")

        print(f"\n    resp_txn_detail: {len(resp_txn_detail):,} transactions")
        print(f"    resp_txn_post: {len(resp_txn_post):,} post-mail transactions")
        print(f"    resp_txn_profile: {len(resp_txn_profile):,} account profiles")
