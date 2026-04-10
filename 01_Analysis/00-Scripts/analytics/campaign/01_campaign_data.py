# ===========================================================================
# CAMPAIGN DATA: ARS Mail & Response Pipeline (Conference Edition)
# ===========================================================================
# Merges bimonthly Mail/Resp columns + offer/response counts from rewards_df.
# Builds: camp_summary, camp_acct, camp_resp_df, camp_nonresp_df.
# Uses DATASET_MONTHS from setup/09 for per-month normalization.
# Guard: try/except for missing columns.

try:
    # Identify available mail/resp columns
    rewards_cols = [c.strip() for c in rewards_df.columns]
    mail_cols = sorted([c for c in rewards_cols if c.endswith(' Mail')])
    resp_cols = sorted([c for c in rewards_cols if c.endswith(' Resp')])

    if len(mail_cols) == 0 and len(resp_cols) == 0:
        print("    No mail/response columns found in ODDD. Skipping campaign analysis.")
        camp_acct = pd.DataFrame()
    else:
        # Build account-level campaign summary
        camp_fields = ['Acct Number'] + mail_cols + resp_cols
        offer_resp_fields = []
        for f in ['# of Offers', '# of Responses', 'Response Grouping']:
            if f in rewards_cols:
                camp_fields.append(f)
                offer_resp_fields.append(f)

        camp_raw = rewards_df[camp_fields].copy()
        camp_raw.columns = [c.strip() for c in camp_raw.columns]
        camp_raw['Acct Number'] = camp_raw['Acct Number'].astype(str).str.strip()

        # Compute per-account: times mailed, times responded, times near-use
        camp_acct = pd.DataFrame()
        camp_acct['primary_account_num'] = camp_raw['Acct Number']

        # Count non-null mail entries (mailed = has a value)
        camp_acct['times_mailed'] = camp_raw[mail_cols].notna().sum(axis=1)

        # Classify each resp column value:
        #   TH-10/15/20/25 = hit threshold challenge (responder/success)
        #   NU 5+          = non-user activated 5+ swipes (responder/success)
        #   NU 1-4         = non-responder (missed goal, but showed activity -- tracked separately)
        #   null/blank     = non-responder (no response)
        _resp_values = camp_raw[resp_cols].copy()

        def _is_success(val):
            """TH-* or NU 5+ = success."""
            if pd.isna(val):
                return False
            v = str(val).strip().upper()
            if v.startswith('TH'):
                return True
            if v in ('NU 5+', 'NU5+', 'NU 5', 'NU 6', 'NU 7', 'NU 8', 'NU 9', 'NU 10'):
                return True
            return False

        def _is_nu_partial(val):
            """NU 1-4 = showed activity but missed goal. Non-responder, tracked separately."""
            if pd.isna(val):
                return False
            v = str(val).strip().upper()
            return v in ('NU 1-4', 'NU1-4')

        _is_true_resp = _resp_values.apply(lambda col: col.map(_is_success))
        _is_nu = _resp_values.apply(lambda col: col.map(_is_nu_partial))

        camp_acct['times_responded'] = _is_true_resp.sum(axis=1)
        camp_acct['times_near_use'] = _is_nu.sum(axis=1)

        # Also use # of Offers if available
        if '# of Offers' in camp_raw.columns:
            camp_acct['total_offers'] = pd.to_numeric(camp_raw['# of Offers'], errors='coerce').fillna(0)
        else:
            camp_acct['total_offers'] = camp_acct['times_mailed']

        # Derive total_responses from our own classification (not ODDD column which may include NU)
        camp_acct['total_responses'] = camp_acct['times_responded']
        camp_acct['total_near_use'] = camp_acct['times_near_use']

        if 'Response Grouping' in camp_raw.columns:
            camp_acct['response_grouping'] = camp_raw['Response Grouping']

        # Classify accounts: Responder (TH-* or NU 5+), Non-Responder (incl NU 1-4), Never Mailed
        # NU 1-4 accounts are Non-Responders but tracked via times_near_use for conversion analysis
        camp_acct['camp_status'] = 'Never Mailed'
        camp_acct.loc[camp_acct['times_mailed'] > 0, 'camp_status'] = 'Non-Responder'
        camp_acct.loc[camp_acct['times_responded'] > 0, 'camp_status'] = 'Responder'

        # -----------------------------------------------------------------------
        # Build period-level summary (chronological order, most recent last)
        # -----------------------------------------------------------------------
        periods = []
        for mc, rc in zip(mail_cols, resp_cols):
            period_label = mc.replace(' Mail', '')
            mailed_count = camp_raw[mc].notna().sum()
            responded_count = camp_raw[rc].map(_is_success).sum()
            near_use_count = camp_raw[rc].map(_is_nu_partial).sum()
            rate = responded_count / mailed_count * 100 if mailed_count > 0 else 0
            periods.append({
                'period': period_label,
                'mailed': mailed_count,
                'responded': responded_count,
                'near_use': near_use_count,
                'response_rate': rate,
            })

        camp_summary = pd.DataFrame(periods)

        # Sort chronologically: parse MmmYY into sortable integer
        _MONTH_ABBR = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                       'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

        def _period_sort_key(label):
            """Convert 'Apr25' -> sortable int (YYYYMM) for chronological ordering."""
            try:
                mon_abbr = label[:3]
                yr_2d = int(label[3:])
                yr_4d = 2000 + yr_2d
                return yr_4d * 100 + _MONTH_ABBR.get(mon_abbr, 0)
            except (ValueError, IndexError):
                return 999999

        camp_summary['_sort'] = camp_summary['period'].apply(_period_sort_key)
        camp_summary = camp_summary.sort_values('_sort').drop(columns='_sort').reset_index(drop=True)

        # -----------------------------------------------------------------------
        # Merge with transaction data for responder vs non-responder analysis
        # -----------------------------------------------------------------------
        camp_txn = combined_df.merge(
            camp_acct[['primary_account_num', 'camp_status', 'total_offers', 'total_responses']],
            on='primary_account_num',
            how='left'
        )
        camp_txn['camp_status'] = camp_txn['camp_status'].fillna('Unknown')

        camp_resp_df = camp_txn[camp_txn['camp_status'] == 'Responder'].copy()
        camp_nonresp_df = camp_txn[camp_txn['camp_status'] == 'Non-Responder'].copy()
        camp_never_df = camp_txn[camp_txn['camp_status'] == 'Never Mailed'].copy()

        # Status aggregation with time-normalized metrics
        _n_months = DATASET_MONTHS

        camp_status_agg = camp_txn.groupby('camp_status').agg(
            txn_count=('transaction_date', 'count'),
            unique_accounts=('primary_account_num', 'nunique'),
            total_spend=('amount', 'sum'),
            avg_spend=('amount', 'mean'),
        ).reset_index()

        total_txns_camp = len(camp_txn)
        camp_status_agg['txn_pct'] = camp_status_agg['txn_count'] / total_txns_camp * 100
        camp_status_agg['txn_per_account'] = camp_status_agg['txn_count'] / camp_status_agg['unique_accounts']
        camp_status_agg['txns_per_acct_mo'] = camp_status_agg['txn_per_account'] / _n_months
        camp_status_agg['spend_per_acct_mo'] = camp_status_agg['total_spend'] / camp_status_agg['unique_accounts'] / _n_months
        camp_status_agg = camp_status_agg.sort_values('txn_count', ascending=False)

        # -----------------------------------------------------------------------
        # Conference-styled summary table (chronological, most recent last)
        # -----------------------------------------------------------------------
        camp_display = camp_summary[['period', 'mailed', 'responded', 'near_use', 'response_rate']].copy()
        camp_display.columns = ['Period', 'Mailed', 'Responded', 'NU 1-4', 'Response Rate %']

        styled = (
            camp_display.style
            .hide(axis='index')
            .format({
                'Mailed': '{:,.0f}',
                'Responded': '{:,.0f}',
                'NU 1-4': '{:,.0f}',
                'Response Rate %': '{:.1f}%',
            })
            .set_properties(**{
                'font-size': '13px', 'font-weight': 'bold',
                'text-align': 'center', 'border': '1px solid #E9ECEF',
                'padding': '7px 10px',
            })
            .set_table_styles([
                {'selector': 'th', 'props': [
                    ('background-color', GEN_COLORS['warning']),
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
            .set_caption(f"ARS Campaign Response Summary by Period  ({DATASET_LABEL})")
            .bar(subset=['Mailed'], color=GEN_COLORS['warning'], vmin=0)
        )

        display(styled)

        n_responders = (camp_acct['camp_status'] == 'Responder').sum()
        n_nonresp = (camp_acct['camp_status'] == 'Non-Responder').sum()
        n_never = (camp_acct['camp_status'] == 'Never Mailed').sum()
        n_nu_partial = (camp_acct['times_near_use'] > 0).sum()
        n_mailed = n_responders + n_nonresp
        overall_rate = n_responders / n_mailed * 100 if n_mailed > 0 else 0
        print(f"\n    {len(mail_cols)} mailing periods, {len(resp_cols)} response periods")
        print(f"    Accounts: {n_responders:,} responders, {n_nonresp:,} non-responders, "
              f"{n_never:,} never mailed")
        print(f"    Response rate: {overall_rate:.1f}% "
              f"({n_responders:,} hit goal out of {n_mailed:,} mailed)")
        print(f"    NU 1-4 (showed activity, missed goal): {n_nu_partial:,} "
              f"({n_nu_partial / n_mailed * 100:.1f}% of mailed)" if n_mailed > 0 else "")

        # Per-period value breakdown for validation
        print(f"\n    {'Period':<10} {'Mailed':>8} {'Success':>8} {'NearUse':>8} {'NoResp':>8}  Response Values")
        print(f"    {'-'*75}")
        for mc, rc in zip(mail_cols, resp_cols):
            period_label = mc.replace(' Mail', '')
            _mailed = camp_raw[mc].notna().sum()
            _all_resp = camp_raw[rc]
            _success = _all_resp.map(_is_success).sum()
            _nu = _all_resp.map(_is_nu_partial).sum()
            _no_resp = _mailed - _success - _nu
            _vals = _all_resp.dropna().astype(str).str.strip().str.upper()
            _val_counts = _vals.value_counts().head(8).to_dict()
            _val_str = ', '.join(f"{v}={c}" for v, c in _val_counts.items())
            print(f"    {period_label:<10} {_mailed:>8,} {_success:>8,} {_nu:>8,} {_no_resp:>8,}  {_val_str}")

except (NameError, KeyError) as e:
    print(f"    Campaign data not available: {e}")
    print("    Skipping campaign analysis.")
    camp_acct = pd.DataFrame()
