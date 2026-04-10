# ===========================================================================
# MERCHANT ACTION SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled findings table + strategic action items.

findings = []

# 1. Concentration
top5_share_mf = merch_agg.head(5)['txn_pct'].sum()
findings.append({
    'Category': 'Concentration',
    'Finding': f"Top 5 merchants = {top5_share_mf:.1f}% of txns; top 10 = {top10_share_m:.1f}%; {len(merch_agg)} total",
    'Implication': 'Heavy reliance on few merchants -- partner deeply but diversify',
    'Priority': 'High'
})

# 2. Dominant merchant
top_merch = merch_agg.iloc[0]
findings.append({
    'Category': '#1 Merchant',
    'Finding': f"{top_merch['merchant_consolidated'][:30]} = {top_merch['txn_pct']:.1f}% share, {int(top_merch['unique_accounts']):,} accounts",
    'Implication': 'Single-merchant dependency risk; loss would materially impact portfolio',
    'Priority': 'High'
})

# 3. Growth/decline dynamics
if len(sorted_months_m) >= 2:
    avg_new_m = cohort_df['new'].mean()
    avg_lost_m = cohort_df['lost'].mean()
    net_m = avg_new_m - avg_lost_m
    findings.append({
        'Category': 'Lifecycle',
        'Finding': f"Avg {avg_new_m:.0f} new merchants/month, {avg_lost_m:.0f} lost; net {'+' if net_m > 0 else ''}{net_m:.0f}",
        'Implication': 'Merchant ecosystem is ' + ('growing' if net_m > 0 else 'shrinking'),
        'Priority': 'Medium' if net_m >= 0 else 'High'
    })

# 4. Volatility
if len(consistency_df) > 0:
    pct_volatile = (consistency_df['cv'] > 100).sum() / len(consistency_df) * 100
    findings.append({
        'Category': 'Volatility',
        'Finding': f"{pct_volatile:.0f}% of merchants have CV > 100% (highly volatile spend)",
        'Implication': 'Revenue predictability risk from volatile merchant base',
        'Priority': 'Medium'
    })

# 5. 80% threshold
above_80_m = merch_agg[merch_agg['cumulative_txn_pct'] >= 80]
if len(above_80_m) > 0:
    n_to_80_m = int(above_80_m.iloc[0]['rank'])
    findings.append({
        'Category': '80% Coverage',
        'Finding': f"Only {n_to_80_m} merchants needed for 80% of transactions",
        'Implication': f"Focus relationship management on {n_to_80_m} core merchants",
        'Priority': 'High'
    })

# 6. Business vs personal
if 'business_flag' in combined_df.columns:
    biz_pct_m = (combined_df['business_flag'] == 'Yes').sum() / len(combined_df) * 100
    findings.append({
        'Category': 'Segment Split',
        'Finding': f"Business accounts = {biz_pct_m:.1f}% of transactions; different top merchants",
        'Implication': 'Segment-specific merchant partnerships and reward programs needed',
        'Priority': 'Medium'
    })

# ---------------------------------------------------------------------------
# Styled findings table
# ---------------------------------------------------------------------------
findings_df = pd.DataFrame(findings)

priority_colors = {
    'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
    'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
    'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
}

styled_findings = (
    findings_df.style
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
    .set_caption("Merchant Analysis: Key Findings & Recommendations")
)

display(styled_findings)

# ---------------------------------------------------------------------------
# Action items
# ---------------------------------------------------------------------------
n80 = n_to_80_m if len(above_80_m) > 0 else 'N/A'

actions = [
    f"Deepen partnerships with top {n80} core merchants (80% coverage)",
    f"Monitor {top_merch['merchant_consolidated'][:25]} dependency -- {top_merch['txn_pct']:.1f}% single-merchant risk",
    "Develop retention playbook for volatile merchants (CV > 100%)",
    "Create segment-specific merchant reward tiers (Business vs Personal)",
    "Track new merchant entrant ramp-up for early success signals",
    "Build merchant health scorecard: volume + stability + account penetration",
]

actions_df = pd.DataFrame({
    'Action Item': actions,
    'Status': ['Recommended'] * len(actions),
})

styled_actions = (
    actions_df.style
    .hide(axis='index')
    .set_properties(**{
        'font-size': '13px', 'text-align': 'left',
        'border': '1px solid #E9ECEF', 'padding': '8px 12px',
    })
    .set_properties(subset=['Status'], **{
        'font-weight': 'bold', 'color': GEN_COLORS['accent'],
        'text-align': 'center',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['accent']),
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
    .set_caption("Merchant Strategic Action Items")
)

display(styled_actions)
