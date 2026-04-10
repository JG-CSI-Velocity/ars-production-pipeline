# ===========================================================================
# ACH/CHK ACTION SUMMARY: Findings & Strategic Recommendations
# ===========================================================================
# Conference-styled findings table + action items for non-debit channels.
# Follows exact pattern from 08_txn_type_action_summary.
#
# Depends on: tt_agg, tt_monthly, acct_channels (cell 13)

findings_ac = []

# 1. ACH/CHK share of total volume
_total_spend = tt_agg['total_spend'].sum()
_debit_spend = tt_agg[tt_agg['transaction_type'].isin(['PIN', 'SIG'])]['total_spend'].sum()
_non_debit_pct = (_total_spend - _debit_spend) / _total_spend * 100 if _total_spend > 0 else 0
_ach_spend = tt_agg[tt_agg['transaction_type'] == 'ACH']['total_spend'].sum()
_chk_spend = tt_agg[tt_agg['transaction_type'] == 'CHK']['total_spend'].sum()

if _non_debit_pct > 0:
    findings_ac.append({
        'Category': 'Volume Share',
        'Finding': f"Non-debit payments = {_non_debit_pct:.1f}% of total volume (ACH + CHK)",
        'Implication': 'ARS debit activation captures only part of total payment relationship',
        'Priority': 'High' if _non_debit_pct > 30 else 'Medium'
    })

# 2. ACH trend
_ach_monthly = tt_monthly[tt_monthly['transaction_type'] == 'ACH'].sort_values('year_month')
if len(_ach_monthly) >= 2:
    _ach_first = _ach_monthly.iloc[0]['total_spend']
    _ach_last = _ach_monthly.iloc[-1]['total_spend']
    _ach_chg = (_ach_last / _ach_first - 1) * 100 if _ach_first > 0 else 0
    _direction = 'growing' if _ach_chg > 0 else 'declining'
    findings_ac.append({
        'Category': 'ACH Trend',
        'Finding': f"ACH volume is {_direction} ({_ach_chg:+.1f}% over period)",
        'Implication': f"Electronic payment adoption is {'accelerating' if _ach_chg > 5 else 'stable' if abs(_ach_chg) < 5 else 'slowing'}",
        'Priority': 'Medium'
    })

# 3. CHK trend
_chk_monthly = tt_monthly[tt_monthly['transaction_type'] == 'CHK'].sort_values('year_month')
if len(_chk_monthly) >= 2:
    _chk_first = _chk_monthly.iloc[0]['total_spend']
    _chk_last = _chk_monthly.iloc[-1]['total_spend']
    _chk_chg = (_chk_last / _chk_first - 1) * 100 if _chk_first > 0 else 0
    findings_ac.append({
        'Category': 'CHK Trend',
        'Finding': f"Check volume changed {_chk_chg:+.1f}% over the period",
        'Implication': 'Check-to-ACH migration opportunity' if _chk_chg < 0 else 'Check usage remains significant',
        'Priority': 'Medium' if abs(_chk_chg) > 10 else 'Low'
    })

# 4. Multi-channel engagement
if 'acct_channels' in dir() and len(acct_channels) > 0:
    _single = acct_channels[acct_channels['channel_count'] == 1]['monthly_spend'].mean()
    _multi = acct_channels[acct_channels['channel_count'] >= 3]['monthly_spend'].mean()
    if _single > 0 and _multi > 0:
        _mult = _multi / _single
        findings_ac.append({
            'Category': 'Multi-Channel',
            'Finding': f"3+ channel accounts spend {_mult:.1f}x more per month than single-channel",
            'Implication': 'Channel diversity is a strong predictor of account value',
            'Priority': 'High'
        })

    _pct_multi = (acct_channels['channel_count'] >= 2).sum() / len(acct_channels) * 100
    findings_ac.append({
        'Category': 'Adoption',
        'Finding': f"{_pct_multi:.0f}% of accounts use 2+ payment channels",
        'Implication': 'Opportunity to increase channel diversity for single-channel accounts',
        'Priority': 'Medium'
    })

# 5. ACH avg ticket vs debit
if _ach_spend > 0:
    _ach_avg = tt_agg[tt_agg['transaction_type'] == 'ACH']['avg_spend'].values
    _debit_avg = tt_agg[tt_agg['transaction_type'].isin(['PIN', 'SIG'])]['avg_spend'].mean()
    if len(_ach_avg) > 0 and _debit_avg > 0:
        _ratio = _ach_avg[0] / _debit_avg
        findings_ac.append({
            'Category': 'Ticket Size',
            'Finding': f"ACH avg ticket ${_ach_avg[0]:,.2f} is {_ratio:.1f}x the debit avg (${_debit_avg:,.2f})",
            'Implication': 'ACH transactions carry higher per-payment dollar value',
            'Priority': 'Low'
        })

# Display findings
if len(findings_ac) == 0:
    print("    No ACH/CHK findings to report (insufficient data).")
else:
    findings_df_ac = pd.DataFrame(findings_ac)

    priority_colors = {
        'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
        'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
        'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
    }

    styled_findings_ac = (
        findings_df_ac.style
        .hide(axis='index')
        .applymap(lambda v: priority_colors.get(v, ''), subset=['Priority'])
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Category'], **{
            'font-weight': 'bold', 'color': GEN_COLORS.get('info', '#457B9D'),
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS.get('info', '#457B9D')),
                ('color', 'white'), ('font-size', '14px'),
                ('font-weight', 'bold'), ('text-align', 'center'),
                ('padding', '8px 12px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'), ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption("ACH & Check Analysis: Key Findings")
    )

    display(styled_findings_ac)

    # Action items
    actions_ac = [
        "Size the full payment relationship: ARS debit lift + existing ACH/CHK = total account value",
        "Identify high-ACH, low-debit accounts as ARS campaign targets (untapped debit potential)",
        "Target CHK-to-ACH migration for high-check-volume accounts (reduce processing cost)",
        "Use multi-channel engagement score as a predictor of ARS response likelihood",
        "Track ACH/CHK trends alongside debit metrics for complete portfolio health monitoring",
        "Position ARS results in context: debit activation deepens already-valuable multi-channel relationships",
    ]

    actions_df_ac = pd.DataFrame({
        'Action Item': actions_ac,
        'Status': ['Recommended'] * len(actions_ac),
    })

    styled_actions_ac = (
        actions_df_ac.style
        .hide(axis='index')
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Status'], **{
            'font-weight': 'bold', 'color': GEN_COLORS.get('info', '#457B9D'),
            'text-align': 'center',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS.get('info', '#457B9D')),
                ('color', 'white'), ('font-size', '14px'),
                ('font-weight', 'bold'), ('text-align', 'center'),
                ('padding', '8px 12px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'), ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption("ACH & Check Strategic Action Items")
    )

    display(styled_actions_ac)

    # Console
    print(f"\n    ACH/CHK ACTION SUMMARY")
    print(f"    {'='*50}")
    print(f"    {len(findings_ac)} findings generated")
    print(f"    {len(actions_ac)} action items recommended")
