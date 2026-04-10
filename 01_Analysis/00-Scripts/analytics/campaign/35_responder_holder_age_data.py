# ===========================================================================
# ACCOUNT HOLDER AGE: Are Younger or Older Members More Likely to Respond?
# ===========================================================================
# Uses DOB or 'Account Holder Age' from ODDD to compute the account holder's
# actual age at the time of each mailing.
#
# Output: holder_age_df   (per-account-wave with holder_age, age_band, status)
#         holder_age_summary (response rate by holder age band)
# Depends on: WAVE_CONFIG (cell 11), rewards_df (setup), camp_acct (cell 01)

if 'WAVE_CONFIG' not in dir() or len(WAVE_CONFIG) == 0:
    print("    No WAVE_CONFIG. Run cell 11 first.")
elif 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data. Run cell 01 first.")
else:
    _acct_col = 'Acct Number' if 'Acct Number' in rewards_df.columns else ' Acct Number'

    # Look for DOB or Account Holder Age
    _dob_col = None
    for _candidate in ['DOB', 'dob', 'Date of Birth', 'date_of_birth', 'BIRTH_DATE']:
        if _candidate in rewards_df.columns:
            _dob_col = _candidate
            break

    _holder_age_col = None
    for _candidate in ['Account Holder Age', 'account_holder_age', 'HOLDER_AGE', 'Member Age']:
        if _candidate in rewards_df.columns:
            _holder_age_col = _candidate
            break

    if _dob_col is None and _holder_age_col is None:
        print("    No DOB or Account Holder Age column found in ODDD.")
        holder_age_df = pd.DataFrame()
        holder_age_summary = pd.DataFrame()
    else:
        # Age bands (years)
        HOLDER_BINS = [18, 25, 35, 45, 55, 65, 75, 120]
        HOLDER_LABELS = ['18-24', '25-34', '35-44', '45-54', '55-64', '65-74', '75+']

        _rows = []

        for wave_label, wc in WAVE_CONFIG.items():
            mail_date = wc['mail_date']
            mc = wc['mail_col'].strip()
            rc = wc['resp_col'].strip()

            was_mailed = rewards_df[mc].notna()
            if was_mailed.sum() == 0:
                continue

            acct_nums = rewards_df.loc[was_mailed, _acct_col].astype(str).str.strip()

            # Compute holder age at mail
            if _dob_col:
                _dob = pd.to_datetime(rewards_df.loc[was_mailed, _dob_col], errors='coerce')
                _holder_years = (mail_date - _dob).dt.days / 365.25
            else:
                _holder_years = pd.to_numeric(
                    rewards_df.loc[was_mailed, _holder_age_col], errors='coerce'
                )

            # Response status
            resp_vals = rewards_df.loc[was_mailed, rc] if rc in rewards_cols else pd.Series(None, index=rewards_df.index[was_mailed])
            _rv = resp_vals.astype(str).str.strip().str.upper()
            is_success = (_rv.str.startswith('TH') |
                          _rv.isin(['NU 5+', 'NU5+', 'NU 5', 'NU 6', 'NU 7', 'NU 8', 'NU 9', 'NU 10'])
                         ) & resp_vals.notna()

            # Segment
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
                'holder_age_years': _holder_years.values,
                'status': np.where(is_success.values, 'Responder', 'Non-Responder'),
                'segment': _seg.values,
            })

            # Filter out invalid ages (under 18 or over 120)
            _wave_df = _wave_df[_wave_df['holder_age_years'].notna() &
                                (_wave_df['holder_age_years'] >= 18) &
                                (_wave_df['holder_age_years'] <= 120)]

            # Bucket into age bands
            _wave_df['age_band'] = pd.cut(
                _wave_df['holder_age_years'],
                bins=HOLDER_BINS,
                labels=HOLDER_LABELS,
                right=False,
            )

            _rows.append(_wave_df)

        if len(_rows) == 0:
            print("    No usable holder age data.")
            holder_age_df = pd.DataFrame()
            holder_age_summary = pd.DataFrame()
        else:
            holder_age_df = pd.concat(_rows, ignore_index=True)
            holder_age_df['age_band'] = holder_age_df['age_band'].cat.remove_unused_categories()

            # ------------------------------------------------------------------
            # Summary: response rate by holder age band
            # ------------------------------------------------------------------
            _agg = holder_age_df.groupby('age_band', observed=True).agg(
                mailed=('acct_number', 'count'),
                responded=('status', lambda x: (x == 'Responder').sum()),
            ).reset_index()
            _agg['response_rate'] = _agg['responded'] / _agg['mailed'] * 100
            _agg['pct_of_responders'] = _agg['responded'] / _agg['responded'].sum() * 100
            _agg['pct_of_mailed'] = _agg['mailed'] / _agg['mailed'].sum() * 100

            holder_age_summary = _agg

            # Display styled summary
            _disp = holder_age_summary.copy()
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
                .set_caption("Response Rate by Account Holder Age  (All Mailers Pooled)")
            )
            display(_styled)

            # Console summary
            _top = holder_age_summary.loc[holder_age_summary['response_rate'].idxmax()]
            _bot = holder_age_summary.loc[holder_age_summary['response_rate'].idxmin()]
            print(f"\n    Account holder age:")
            print(f"      Highest response rate: {_top['age_band']} at {_top['response_rate']:.1f}% "
                  f"({int(_top['responded']):,}/{int(_top['mailed']):,})")
            print(f"      Lowest response rate:  {_bot['age_band']} at {_bot['response_rate']:.1f}% "
                  f"({int(_bot['responded']):,}/{int(_bot['mailed']):,})")
            print(f"      Total: {len(holder_age_df):,} account-wave observations")

            _r_med = holder_age_df[holder_age_df['status'] == 'Responder']['holder_age_years'].median()
            _nr_med = holder_age_df[holder_age_df['status'] == 'Non-Responder']['holder_age_years'].median()
            print(f"      Median holder age: Responders {_r_med:.0f} yrs vs "
                  f"Non-Responders {_nr_med:.0f} yrs")
