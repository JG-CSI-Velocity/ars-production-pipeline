# ===========================================================================
# MCC ACTION SUMMARY: Findings & Strategic Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled summary table with key findings from MCC analysis.

if 'mcc_agg' not in dir() or len(mcc_agg) == 0:
    print("    No MCC aggregation data available. Skipping action summary.")
else:
    # ---------------------------------------------------------------------------
    # Build findings from MCC data
    # ---------------------------------------------------------------------------
    findings = []

    # 1. Concentration
    top5_share = mcc_agg.head(5)['txn_pct'].sum()
    top10_share = mcc_agg.head(10)['txn_pct'].sum()
    top20_share = mcc_agg.head(20)['txn_pct'].sum()
    total_mccs = len(mcc_agg)
    findings.append({
        'Category': 'Concentration',
        'Finding': f"Top 5 MCCs = {top5_share:.1f}% of txns; top 10 = {top10_share:.1f}%; {total_mccs} total categories",
        'Implication': 'Highly concentrated -- rewards/offers should target dominant MCCs',
        'Priority': 'High'
    })

    # 2. Top category
    top_mcc = mcc_agg.iloc[0]
    findings.append({
        'Category': 'Dominant MCC',
        'Finding': f"MCC {int(top_mcc['mcc_code'])} = {top_mcc['txn_pct']:.1f}% share, {int(top_mcc['unique_accounts']):,} accounts",
        'Implication': 'Single-category dependency risk; monitor for merchant attrition',
        'Priority': 'High'
    })

    # 3. Account diversity
    try:
        median_div = acct_diversity['distinct_mccs'].median()
        pct_single = (acct_diversity['distinct_mccs'] == 1).mean() * 100
        findings.append({
            'Category': 'Diversity',
            'Finding': f"Median {median_div:.0f} MCCs/account; {pct_single:.1f}% use only 1 category",
            'Implication': 'Single-category users at churn risk; cross-category incentives needed',
            'Priority': 'Medium'
        })
    except NameError:
        pass

    # 4. Business vs Personal
    if 'business_flag' in combined_df.columns:
        biz_txns = (combined_df['business_flag'] == 'Yes').sum()
        biz_pct = biz_txns / len(combined_df) * 100
        findings.append({
            'Category': 'Biz vs Personal',
            'Finding': f"Business = {biz_pct:.1f}% of transactions",
            'Implication': 'Different MCC mixes suggest segment-specific reward tiers',
            'Priority': 'Medium'
        })

    # 5. Spend profile
    top_mcc_median_spend = combined_df[combined_df['mcc_code'] == top_mcc['mcc_code']]['amount'].median()
    overall_median_spend = combined_df['amount'].median()
    findings.append({
        'Category': 'Spend Size',
        'Finding': f"Top MCC median ${top_mcc_median_spend:,.0f} vs portfolio median ${overall_median_spend:,.0f}",
        'Implication': 'Category-specific interchange and reward optimization opportunity',
        'Priority': 'Medium'
    })

    # 6. 80% threshold
    _n_to_80 = 'N/A'
    if 'cumulative_txn_pct' in mcc_agg.columns:
        above_80 = mcc_agg[mcc_agg['cumulative_txn_pct'] >= 80]
        if len(above_80) > 0:
            _n_to_80 = int(above_80.iloc[0]['rank'])
            findings.append({
                'Category': '80% Threshold',
                'Finding': f"Only {_n_to_80} MCCs needed to reach 80% of all transactions",
                'Implication': f"Focus merchant partnerships on {_n_to_80} categories for maximum impact",
                'Priority': 'High'
            })

    # ---------------------------------------------------------------------------
    # Styled summary table
    # ---------------------------------------------------------------------------
    findings_df = pd.DataFrame(findings)

    priority_colors = {
        'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
        'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
        'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
    }

    def style_priority(val):
        return priority_colors.get(val, '')

    styled_findings = (
        findings_df.style
        .hide(axis='index')
        .applymap(style_priority, subset=['Priority'])
        .set_properties(**{
            'font-size': '13px',
            'text-align': 'left',
            'border': '1px solid #E9ECEF',
            'padding': '8px 12px',
        })
        .set_properties(subset=['Category'], **{
            'font-weight': 'bold',
            'color': GEN_COLORS['primary'],
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['primary']),
                ('color', 'white'),
                ('font-size', '14px'),
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('padding', '8px 12px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'),
                ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']),
                ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption("MCC Analysis: Key Findings & Recommendations")
    )

    display(styled_findings)

    # ---------------------------------------------------------------------------
    # Action items
    # ---------------------------------------------------------------------------
    actions = [
        "Target top 5 MCCs for enhanced rewards -- covers {:.0f}% of transactions".format(top5_share),
        "Build merchant partnerships around {} core categories for 80% coverage".format(_n_to_80),
        "Develop cross-category incentives for single-MCC accounts (churn risk segment)",
        "Create segment-specific reward tiers for Business vs Personal MCC mixes",
        "Monitor seasonal MCC shifts for dynamic reward calendar opportunities",
        "Investigate MCC diversity gap between Power and Dormant engagement tiers",
    ]

    actions_df = pd.DataFrame({
        'Action Item': actions,
        'Status': ['Recommended'] * len(actions),
    })

    styled_actions = (
        actions_df.style
        .hide(axis='index')
        .set_properties(**{
            'font-size': '13px',
            'text-align': 'left',
            'border': '1px solid #E9ECEF',
            'padding': '8px 12px',
        })
        .set_properties(subset=['Status'], **{
            'font-weight': 'bold',
            'color': GEN_COLORS['accent'],
            'text-align': 'center',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['accent']),
                ('color', 'white'),
                ('font-size', '14px'),
                ('font-weight', 'bold'),
                ('text-align', 'center'),
                ('padding', '8px 12px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'),
                ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']),
                ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption("MCC Strategic Action Items")
    )

    display(styled_actions)
