# ===========================================================================
# BUSINESS ACTION SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled findings table + strategic action items.

if 'biz_agg' not in dir() or len(biz_agg) == 0:
    print("    No business data available. Skipping action summary.")
else:
    findings_b = []

    # 1. Concentration
    top5_share_bf = biz_agg.head(5)['txn_pct'].sum()
    findings_b.append({
        'Category': 'Concentration',
        'Finding': f"Top 5 business merchants = {top5_share_bf:.1f}% of txns; top 10 = {top10_share_biz:.1f}%; {len(biz_agg)} total",
        'Implication': 'Business portfolio heavily concentrated -- deepen key partnerships',
        'Priority': 'High'
    })

    # 2. Dominant merchant
    top_merch_b = biz_agg.iloc[0]
    findings_b.append({
        'Category': '#1 Merchant',
        'Finding': f"{top_merch_b['merchant_consolidated'][:30]} = {top_merch_b['txn_pct']:.1f}% share, {int(top_merch_b['unique_accounts']):,} accounts",
        'Implication': 'Single-merchant dependency risk for business portfolio',
        'Priority': 'High'
    })

    # 3. Growth/decline dynamics
    if 'biz_cohort_df' in dir() and len(biz_cohort_df) > 0 and len(sorted_months_biz) >= 2:
        avg_new_bf = biz_cohort_df['new'].mean()
        avg_lost_bf = biz_cohort_df['lost'].mean()
        net_bf = avg_new_bf - avg_lost_bf
        findings_b.append({
            'Category': 'Lifecycle',
            'Finding': f"Avg {avg_new_bf:.0f} new business merchants/month, {avg_lost_bf:.0f} lost; net {'+' if net_bf > 0 else ''}{net_bf:.0f}",
            'Implication': 'Business merchant ecosystem is ' + ('growing' if net_bf > 0 else 'shrinking'),
            'Priority': 'Medium' if net_bf >= 0 else 'High'
        })

    # 4. Volatility
    if len(biz_consistency_df) > 0:
        pct_volatile_b = (biz_consistency_df['cv'] > 100).sum() / len(biz_consistency_df) * 100
        findings_b.append({
            'Category': 'Volatility',
            'Finding': f"{pct_volatile_b:.0f}% of business merchants have CV > 100% (highly volatile spend)",
            'Implication': 'B2B revenue predictability risk from volatile merchant base',
            'Priority': 'Medium'
        })

    # 5. 80% threshold
    above_80_b = biz_agg[biz_agg['cumulative_txn_pct'] >= 80]
    if len(above_80_b) > 0:
        n_to_80_b = int(above_80_b.iloc[0]['rank'])
        findings_b.append({
            'Category': '80% Coverage',
            'Finding': f"Only {n_to_80_b} business merchants needed for 80% of transactions",
            'Implication': f"Focus B2B relationship management on {n_to_80_b} core merchants",
            'Priority': 'High'
        })

    # 6. Portfolio context
    try:
        biz_pct_of_portfolio = len(business_df) / len(combined_df) * 100
        findings_b.append({
            'Category': 'Portfolio Context',
            'Finding': f"Business accounts = {biz_pct_of_portfolio:.1f}% of total portfolio transactions",
            'Implication': 'Business segment requires dedicated merchant partnership and reward strategy',
            'Priority': 'High'
        })
    except NameError:
        pass

    # -------------------------------------------------------------------
    # Styled findings table
    # -------------------------------------------------------------------
    findings_df_b = pd.DataFrame(findings_b)

    priority_colors = {
        'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
        'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
        'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
    }

    styled_findings_b = (
        findings_df_b.style
        .hide(axis='index')
        .applymap(lambda v: priority_colors.get(v, ''), subset=['Priority'])
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Category'], **{
            'font-weight': 'bold', 'color': GEN_COLORS['primary'],
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['primary']),
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
        .set_caption("Business Account Analysis: Key Findings & Recommendations")
    )

    display(styled_findings_b)

    # -------------------------------------------------------------------
    # Action items
    # -------------------------------------------------------------------
    n80_b = n_to_80_b if len(above_80_b) > 0 else 'N/A'

    actions_b = [
        f"Deepen B2B partnerships with top {n80_b} core business merchants (80% coverage)",
        f"Monitor {top_merch_b['merchant_consolidated'][:25]} dependency -- {top_merch_b['txn_pct']:.1f}% single-merchant risk",
        "Develop business card reward programs at top merchant partners",
        "Create business account acquisition strategy around top merchant categories",
        "Build B2B merchant health scorecard: volume + stability + account penetration",
        "Track new business merchant entrant ramp-up for early partnership signals",
    ]

    actions_df_b = pd.DataFrame({
        'Action Item': actions_b,
        'Status': ['Recommended'] * len(actions_b),
    })

    styled_actions_b = (
        actions_df_b.style
        .hide(axis='index')
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Status'], **{
            'font-weight': 'bold', 'color': GEN_COLORS['primary'],
            'text-align': 'center',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['primary']),
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
        .set_caption("Business Account Strategic Action Items")
    )

    display(styled_actions_b)
