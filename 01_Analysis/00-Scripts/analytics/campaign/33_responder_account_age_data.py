# ===========================================================================
# RESPONDER ACCOUNT AGE: Are Newer Accounts More Likely to Respond?
# ===========================================================================
# Computes each mailed account's age AT THE TIME OF MAIL (not current age).
# Accounts under 90 days are excluded from mailing per business rules.
#
# For each wave × account: age_at_mail = mail_date - date_opened
# Then buckets into age bands and computes response rate by band.
#
# Output: resp_age_df (per-account-wave with age_at_mail, age_band, status)
#         resp_age_summary (response rate by age band)
# Depends on: WAVE_CONFIG (cell 11), rewards_df (setup), camp_acct (cell 01)

if 'WAVE_CONFIG' not in dir() or len(WAVE_CONFIG) == 0:
    print("    No WAVE_CONFIG. Run cell 11 first.")
elif 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
else:
    _acct_col = 'Acct Number' if 'Acct Number' in rewards_df.columns else ' Acct Number'

    # Check for Date Opened column
    _date_col = None
    for _candidate in ['Date Opened', 'date_opened', 'DateOpened', 'OPEN_DATE']:
        if _candidate in rewards_df.columns:
            _date_col = _candidate
            break

    if _date_col is None:
        print("    No 'Date Opened' column found in ODDD. Checking Account Age...")
        # Fall back to Account Age (numeric days)
        _age_col = None
        for _candidate in ['Account Age', 'account_age', 'ACCT_AGE']:
            if _candidate in rewards_df.columns:
                _age_col = _candidate
                break

    if _date_col is None and _age_col is None:
        print("    No account age or open date data available in ODDD.")
    else:
        # Age bands starting at 91 (under 90 not mailed)
        AGE_BINS = [91, 181, 366, 731, 1096, 1826, 3651, 7301, 999999]
        AGE_LABELS = ['91-180d', '181d-1yr', '1-2yr', '2-3yr',
                      '3-5yr', '5-10yr', '10-20yr', '20yr+']

        _rows = []

        for wave_label, wc in WAVE_CONFIG.items():
            mail_date = wc['mail_date']
            mc = wc['mail_col'].strip()
            rc = wc['resp_col'].strip()

            was_mailed = rewards_df[mc].notna()
            if was_mailed.sum() == 0:
                continue

            acct_nums = rewards_df.loc[was_mailed, _acct_col].astype(str).str.strip()

            # Compute age at mail
            if _date_col:
                _opened = pd.to_datetime(rewards_df.loc[was_mailed, _date_col], errors='coerce')
                _age_days = (mail_date - _opened).dt.days
            else:
                # Account Age is days as of ODDD export; adjust for time between export and mail
                _age_days = pd.to_numeric(rewards_df.loc[was_mailed, _age_col], errors='coerce')

            # Response status
            resp_vals = rewards_df.loc[was_mailed, rc] if rc in rewards_cols else pd.Series(None, index=rewards_df.index[was_mailed])
            _rv = resp_vals.astype(str).str.strip().str.upper()
            is_success = (_rv.str.startswith('TH') |
                          _rv.isin(['NU 5+', 'NU5+', 'NU 5', 'NU 6', 'NU 7', 'NU 8', 'NU 9', 'NU 10'])
                         ) & resp_vals.notna()

            # Segment (reuse parser from cell 25 if available)
            _seg = pd.Series('Unknown', index=resp_vals.index)
            if '_parse_segment' in dir():
                resp_seg = resp_vals.map(_parse_segment)
                mail_seg = rewards_df.loc[was_mailed, mc].map(_parse_segment)
                _seg[mail_seg.notna()] = mail_seg[mail_seg.notna()]
                _is_nu_partial = _rv.isin(['NU 1-4', 'NU1-4']) & resp_vals.notna()
                _seg[_is_nu_partial] = 'NU'
                _seg[resp_seg.notna() & is_success] = resp_seg[resp_seg.notna() & is_success]

            _wave_df = pd.DataFrame({
                'acct_number': acct_nums.values,
                'wave': wave_label,
                'wave_date': mail_date,
                'age_at_mail_days': _age_days.values,
                'status': np.where(is_success.values, 'Responder', 'Non-Responder'),
                'segment': _seg.values,
            })

            # Filter out invalid ages
            _wave_df = _wave_df[_wave_df['age_at_mail_days'].notna() &
                                (_wave_df['age_at_mail_days'] > 0)]

            # Bucket into age bands
            _wave_df['age_band'] = pd.cut(
                _wave_df['age_at_mail_days'],
                bins=[0] + AGE_BINS,
                labels=['<91d'] + AGE_LABELS,
                right=True,
            )

            _rows.append(_wave_df)

        if len(_rows) == 0:
            print("    No usable account age data.")
            resp_age_df = pd.DataFrame()
            resp_age_summary = pd.DataFrame()
        else:
            resp_age_df = pd.concat(_rows, ignore_index=True)

            # Remove <91d (shouldn't be mailed, but flag if present)
            _under_90 = (resp_age_df['age_band'] == '<91d').sum()
            if _under_90 > 0:
                print(f"    NOTE: {_under_90:,} account-waves with age < 91 days found "
                      f"(should not be mailed per business rules). Excluding.")
                resp_age_df = resp_age_df[resp_age_df['age_band'] != '<91d']

            # Drop unused category
            resp_age_df['age_band'] = resp_age_df['age_band'].cat.remove_unused_categories()

            # ------------------------------------------------------------------
            # Summary: response rate by age band
            # ------------------------------------------------------------------
            _agg = resp_age_df.groupby('age_band', observed=True).agg(
                mailed=('acct_number', 'count'),
                responded=('status', lambda x: (x == 'Responder').sum()),
            ).reset_index()
            _agg['response_rate'] = _agg['responded'] / _agg['mailed'] * 100
            _agg['pct_of_responders'] = _agg['responded'] / _agg['responded'].sum() * 100
            _agg['pct_of_mailed'] = _agg['mailed'] / _agg['mailed'].sum() * 100

            resp_age_summary = _agg

            # Display styled summary
            _disp = resp_age_summary.copy()
            _disp.columns = ['Age Band', 'Mailed', 'Responded', 'Response Rate',
                             '% of Responders', '% of Mailed']

            _styled = (
                _disp.style
                .hide(axis='index')
                .format({
                    'Mailed': '{:,}',
                    'Responded': '{:,}',
                    'Response Rate': '{:.1f}%',
                    '% of Responders': '{:.1f}%',
                    '% of Mailed': '{:.1f}%',
                })
                .bar(subset=['Response Rate'], color=GEN_COLORS.get('success', '#2A9D8F'),
                     vmin=0)
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
                .set_caption("Response Rate by Account Age at Time of Mail  (All Mailers Pooled)")
            )
            display(_styled)

            # By-segment breakdown (if segments available)
            _has_segs = resp_age_df['segment'].nunique() > 1 and 'Unknown' not in resp_age_df['segment'].unique()
            if _has_segs:
                _seg_age = resp_age_df.groupby(['segment', 'age_band'], observed=True).agg(
                    mailed=('acct_number', 'count'),
                    responded=('status', lambda x: (x == 'Responder').sum()),
                ).reset_index()
                _seg_age['response_rate'] = _seg_age['responded'] / _seg_age['mailed'] * 100

                _styled_seg = (
                    _seg_age.style
                    .hide(axis='index')
                    .format({'mailed': '{:,}', 'responded': '{:,}', 'response_rate': '{:.1f}%'})
                    .bar(subset=['response_rate'], color=GEN_COLORS.get('success', '#2A9D8F'), vmin=0)
                    .set_properties(**{
                        'font-size': '13px', 'font-weight': 'bold',
                        'text-align': 'center', 'border': '1px solid #E9ECEF',
                        'padding': '6px 10px',
                    })
                    .set_table_styles([
                        {'selector': 'th', 'props': [
                            ('background-color', GEN_COLORS.get('success', '#2A9D8F')),
                            ('color', 'white'), ('font-size', '13px'),
                            ('font-weight', 'bold'), ('text-align', 'center'),
                        ]},
                        {'selector': 'caption', 'props': [
                            ('font-size', '18px'), ('font-weight', 'bold'),
                            ('color', GEN_COLORS.get('dark_text', '#1B2A4A')),
                            ('text-align', 'left'), ('padding-bottom', '8px'),
                        ]},
                    ])
                    .set_caption("Response Rate by Account Age x Segment")
                )
                display(_styled_seg)

            # Console summary
            _top = resp_age_summary.loc[resp_age_summary['response_rate'].idxmax()]
            _bot = resp_age_summary.loc[resp_age_summary['response_rate'].idxmin()]
            print(f"\n    Account age at mail:")
            print(f"      Highest response rate: {_top['age_band']} at {_top['response_rate']:.1f}% "
                  f"({int(_top['responded']):,}/{int(_top['mailed']):,})")
            print(f"      Lowest response rate:  {_bot['age_band']} at {_bot['response_rate']:.1f}% "
                  f"({int(_bot['responded']):,}/{int(_bot['mailed']):,})")
            print(f"      Total: {len(resp_age_df):,} account-wave observations")

            # Median age comparison
            _r_med = resp_age_df[resp_age_df['status'] == 'Responder']['age_at_mail_days'].median()
            _nr_med = resp_age_df[resp_age_df['status'] == 'Non-Responder']['age_at_mail_days'].median()
            print(f"      Median age at mail: Responders {_r_med:,.0f} days vs "
                  f"Non-Responders {_nr_med:,.0f} days")
