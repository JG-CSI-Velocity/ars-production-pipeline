# ===========================================================================
# PERSONAL ACTION SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled findings table + strategic action items.

findings_p = []

# 1. Concentration
top5_share_pf = pers_agg.head(5)['txn_pct'].sum()
findings_p.append({
    'Category': 'Concentration',
    'Finding': f"Top 5 personal merchants = {top5_share_pf:.1f}% of txns; top 10 = {top10_share_pers:.1f}%; {len(pers_agg)} total",
    'Implication': 'Heavy reliance on few merchants -- partner deeply but diversify',
    'Priority': 'High'
})

# 2. Dominant merchant
top_merch_p = pers_agg.iloc[0]
findings_p.append({
    'Category': '#1 Merchant',
    'Finding': f"{top_merch_p['merchant_consolidated'][:30]} = {top_merch_p['txn_pct']:.1f}% share, {int(top_merch_p['unique_accounts']):,} accounts",
    'Implication': 'Single-merchant dependency risk for personal portfolio',
    'Priority': 'High'
})

# 3. Growth/decline dynamics
if len(sorted_months_pers) >= 2:
    avg_new_pf = pers_cohort_df['new'].mean()
    avg_lost_pf = pers_cohort_df['lost'].mean()
    net_pf = avg_new_pf - avg_lost_pf
    findings_p.append({
        'Category': 'Lifecycle',
        'Finding': f"Avg {avg_new_pf:.0f} new personal merchants/month, {avg_lost_pf:.0f} lost; net {'+' if net_pf > 0 else ''}{net_pf:.0f}",
        'Implication': 'Personal merchant ecosystem is ' + ('growing' if net_pf > 0 else 'shrinking'),
        'Priority': 'Medium' if net_pf >= 0 else 'High'
    })

# 4. Volatility
if len(pers_consistency_df) > 0:
    pct_volatile_p = (pers_consistency_df['cv'] > 100).sum() / len(pers_consistency_df) * 100
    findings_p.append({
        'Category': 'Volatility',
        'Finding': f"{pct_volatile_p:.0f}% of personal merchants have CV > 100% (highly volatile spend)",
        'Implication': 'Revenue predictability risk from volatile personal merchant base',
        'Priority': 'Medium'
    })

# 5. 80% threshold
above_80_p = pers_agg[pers_agg['cumulative_txn_pct'] >= 80]
if len(above_80_p) > 0:
    n_to_80_p = int(above_80_p.iloc[0]['rank'])
    findings_p.append({
        'Category': '80% Coverage',
        'Finding': f"Only {n_to_80_p} personal merchants needed for 80% of transactions",
        'Implication': f"Focus personal rewards and relationship management on {n_to_80_p} core merchants",
        'Priority': 'High'
    })

# 6. Portfolio context
try:
    pers_pct_of_portfolio = len(personal_df) / len(combined_df) * 100
    findings_p.append({
        'Category': 'Portfolio Context',
        'Finding': f"Personal accounts = {pers_pct_of_portfolio:.1f}% of total portfolio transactions",
        'Implication': 'Personal segment merchant strategy impacts the majority of card volume',
        'Priority': 'High' if pers_pct_of_portfolio > 60 else 'Medium'
    })
except NameError:
    pass

# ---------------------------------------------------------------------------
# Styled findings table
# ---------------------------------------------------------------------------
findings_df_p = pd.DataFrame(findings_p)

priority_colors = {
    'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
    'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
    'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
}

styled_findings_p = (
    findings_df_p.style
    .hide(axis='index')
    .applymap(lambda v: priority_colors.get(v, ''), subset=['Priority'])
    .set_properties(**{
        'font-size': '13px', 'text-align': 'left',
        'border': '1px solid #E9ECEF', 'padding': '8px 12px',
    })
    .set_properties(subset=['Category'], **{
        'font-weight': 'bold', 'color': GEN_COLORS['success'],
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['success']),
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
    .set_caption("Personal Account Analysis: Key Findings & Recommendations")
)

display(styled_findings_p)

# ---------------------------------------------------------------------------
# Action items
# ---------------------------------------------------------------------------
n80_p = n_to_80_p if len(above_80_p) > 0 else 'N/A'

actions_p = [
    f"Deepen personal reward partnerships with top {n80_p} core merchants (80% coverage)",
    f"Monitor {top_merch_p['merchant_consolidated'][:25]} dependency -- {top_merch_p['txn_pct']:.1f}% single-merchant risk",
    "Develop retention strategies for volatile personal merchants (CV > 100%)",
    "Create personal account merchant reward tiers based on usage patterns",
    "Track new personal merchant entrant ramp-up for early success signals",
    "Build personal merchant health scorecard: volume + stability + account penetration",
]

actions_df_p = pd.DataFrame({
    'Action Item': actions_p,
    'Status': ['Recommended'] * len(actions_p),
})

styled_actions_p = (
    actions_df_p.style
    .hide(axis='index')
    .set_properties(**{
        'font-size': '13px', 'text-align': 'left',
        'border': '1px solid #E9ECEF', 'padding': '8px 12px',
    })
    .set_properties(subset=['Status'], **{
        'font-weight': 'bold', 'color': GEN_COLORS['success'],
        'text-align': 'center',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['success']),
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
    .set_caption("Personal Account Strategic Action Items")
)

display(styled_actions_p)
