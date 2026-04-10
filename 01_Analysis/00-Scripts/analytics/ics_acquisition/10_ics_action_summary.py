# ===========================================================================
# ICS ACTION SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled findings table + strategic action items.
# All rate metrics are per-month for time context.

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping action summary.")
else:
    findings_ics = []

    ics_only = ics_agg[ics_agg['ics_account'] != 'Non-ICS']
    _n_months = DATASET_MONTHS

    # 1. ICS penetration
    ics_acct_pct = ics_only['acct_pct'].sum()
    ics_txn_pct = ics_only['txn_pct'].sum()
    findings_ics.append({
        'Category': 'Penetration',
        'Finding': f"ICS accounts = {ics_acct_pct:.1f}% of accounts, {ics_txn_pct:.1f}% of transactions",
        'Implication': 'ICS is a ' + ('major' if ics_acct_pct > 20 else 'growing') + ' acquisition channel',
        'Priority': 'High'
    })

    # 2. Channel activity (monthly-normalized)
    ref_row = ics_agg[ics_agg['ics_account'] == 'REF']
    dm_row = ics_agg[ics_agg['ics_account'] == 'DM']
    if len(ref_row) > 0 and len(dm_row) > 0:
        ref_tpm = ref_row['txns_per_acct_mo'].values[0]
        dm_tpm = dm_row['txns_per_acct_mo'].values[0]
        ref_spm = ref_row['spend_per_acct_mo'].values[0]
        dm_spm = dm_row['spend_per_acct_mo'].values[0]
        better = 'REF' if ref_tpm > dm_tpm else 'DM'
        findings_ics.append({
            'Category': 'Channel Activity',
            'Finding': (f"REF: {ref_tpm:.1f} txns/acct/mo (${ref_spm:,.0f}/mo) vs "
                        f"DM: {dm_tpm:.1f} txns/acct/mo (${dm_spm:,.0f}/mo)"),
            'Implication': f"{better} channel produces more active accounts over {_n_months} months",
            'Priority': 'High'
        })

    # 3. Avg ticket comparison
    ics_avg = ics_df['amount'].mean() if len(ics_df) > 0 else 0
    non_avg = non_ics_df['amount'].mean() if len(non_ics_df) > 0 else 0
    if ics_avg > 0 and non_avg > 0:
        findings_ics.append({
            'Category': 'Spend Level',
            'Finding': f"ICS avg ticket ${ics_avg:.2f} vs Non-ICS ${non_avg:.2f} ({ics_avg/non_avg:.2f}x)",
            'Implication': 'ICS accounts ' + ('spend more' if ics_avg > non_avg else 'spend less') + ' per transaction',
            'Priority': 'Medium'
        })

    # 4. Total ICS revenue impact (annualized)
    ics_total_spend = ics_only['total_spend'].sum()
    total_spend_all = ics_agg['total_spend'].sum()
    spend_pct = ics_total_spend / total_spend_all * 100 if total_spend_all > 0 else 0
    annual_ics = ics_total_spend / _n_months * 12
    findings_ics.append({
        'Category': 'Revenue Impact',
        'Finding': (f"ICS accounts generate {spend_pct:.1f}% of total card spend "
                    f"(~${annual_ics:,.0f} annualized)"),
        'Implication': 'ICS acquisition directly impacts interchange revenue',
        'Priority': 'High' if spend_pct > 15 else 'Medium'
    })

    # ---------------------------------------------------------------------------
    # Styled findings table
    # ---------------------------------------------------------------------------
    findings_df_ics = pd.DataFrame(findings_ics)

    priority_colors = {
        'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
        'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
        'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
    }

    styled_findings_ics = (
        findings_df_ics.style
        .hide(axis='index')
        .applymap(lambda v: priority_colors.get(v, ''), subset=['Priority'])
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Category'], **{
            'font-weight': 'bold', 'color': GEN_COLORS['info'],
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['info']),
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
        .set_caption(f"ICS Acquisition Analysis: Key Findings  ({DATASET_LABEL}, {_n_months} months)")
    )

    display(styled_findings_ics)

    # ---------------------------------------------------------------------------
    # Action items
    # ---------------------------------------------------------------------------
    actions_ics = [
        "Compare REF vs DM cost-per-acquisition against monthly card usage value",
        "Develop channel-specific onboarding flows to maximize early card activation",
        "Create ICS-specific merchant reward partnerships based on channel preferences",
        "Track ICS account engagement tiers for 90-day post-acquisition retention signals",
        "Build ICS acquisition ROI dashboard: cost per account vs interchange revenue generated",
        "Test targeted campaigns to convert low-activity ICS accounts to active users",
    ]

    actions_df_ics = pd.DataFrame({
        'Action Item': actions_ics,
        'Status': ['Recommended'] * len(actions_ics),
    })

    styled_actions_ics = (
        actions_df_ics.style
        .hide(axis='index')
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Status'], **{
            'font-weight': 'bold', 'color': GEN_COLORS['info'],
            'text-align': 'center',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['info']),
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
        .set_caption("ICS Acquisition Strategic Action Items")
    )

    display(styled_actions_ics)
