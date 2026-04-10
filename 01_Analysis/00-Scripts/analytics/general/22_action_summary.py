# ===========================================================================
# ACTION SUMMARY: Findings + Recommendations (Conference Edition)
# ===========================================================================
# Styled summary table + printed action items. Lists last.

# ---------------------------------------------------------------------------
# Build findings from upstream data
# ---------------------------------------------------------------------------
findings = []

# Portfolio overview
findings.append({
    'Area': 'Portfolio',
    'Finding': f"{portfolio_kpis['total_accounts']:,} accounts, "
               f"{portfolio_kpis['avg_monthly_txns']:,.0f} avg monthly transactions",
    'Signal': 'Baseline',
})

# Growth direction
growth_val = portfolio_kpis['latest_txn_growth']
findings.append({
    'Area': 'Growth',
    'Finding': f"Transaction volume {'growing' if growth_val >= 0 else 'declining'} "
               f"at {growth_val:+.1f}% MoM",
    'Signal': 'Positive' if growth_val >= 0 else 'Needs Attention',
})

# Bracket concentration
top_bracket = bracket_df.loc[bracket_df['txn_pct'].idxmax()]
findings.append({
    'Area': 'Brackets',
    'Finding': f"Most common bracket: {top_bracket['bracket']} "
               f"({top_bracket['txn_pct']:.1f}% of transactions)",
    'Signal': 'Insight',
})

# Bracket volatility
most_volatile_row = volatility_df.loc[volatility_df['Std Dev'].idxmax()]
findings.append({
    'Area': 'Volatility',
    'Finding': f"Most volatile bracket: {most_volatile_row['Bracket']} "
               f"(std dev {most_volatile_row['Std Dev']:.2f}%)",
    'Signal': 'Monitor' if most_volatile_row['Std Dev'] > 2.0 else 'Stable',
})

# Demographics (if available)
if len(demo_summary) > 0:
    largest_band = demo_summary.loc[demo_summary['txn_count'].idxmax()]
    findings.append({
        'Area': 'Demographics',
        'Finding': f"Largest age group: {largest_band['age_band']} "
                   f"({largest_band['txn_pct']:.1f}% of matched transactions)",
        'Signal': 'Insight',
    })

# Engagement
power_row = engagement_df[engagement_df['tier'] == 'Power'].iloc[0]
findings.append({
    'Area': 'Engagement',
    'Finding': f"Power users ({power_row['acct_pct']:.0f}% of accounts) "
               f"drive {power_row['txn_pct']:.1f}% of transactions",
    'Signal': 'Key Leverage',
})

# Merchant concentration
top10_cum = top15['cumulative_pct'].iloc[9] if len(top15) >= 10 else top15['cumulative_pct'].iloc[-1]
findings.append({
    'Area': 'Merchants',
    'Finding': f"Top 10 merchants account for {top10_cum:.1f}% of all transactions",
    'Signal': 'Concentrated' if top10_cum > 50 else 'Diversified',
})

findings_df = pd.DataFrame(findings)

# ---------------------------------------------------------------------------
# Styled findings table
# ---------------------------------------------------------------------------
def _signal_color(val):
    color_map = {
        'Positive': GEN_COLORS['success'],
        'Needs Attention': GEN_COLORS['accent'],
        'Monitor': GEN_COLORS['warning'],
        'Key Leverage': GEN_COLORS['info'],
        'Concentrated': GEN_COLORS['warning'],
    }
    c = color_map.get(val, GEN_COLORS['dark_text'])
    return f"color: {c}; font-weight: bold"

styled = (
    findings_df.style
    .hide(axis='index')
    .set_properties(**{
        'font-size': '14px',
        'font-weight': 'bold',
        'text-align': 'left',
        'border': '1px solid #E9ECEF',
        'padding': '10px 14px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '15px'),
            ('font-weight', 'bold'),
            ('text-align', 'left'),
            ('padding', '10px 14px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '24px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '14px'),
        ]},
    ])
    .set_caption("Portfolio Analysis Summary")
    .applymap(_signal_color, subset=['Signal'])
)

display(styled)

# ---------------------------------------------------------------------------
# Action items
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("  ACTION ITEMS")
print("=" * 80)

actions = [
    "Review Power user segment for retention and upsell opportunities",
    "Monitor volatile spending brackets for seasonal or behavioral shifts",
    f"Investigate merchant concentration (top 10 = {top10_cum:.1f}% of volume)",
]

if growth_val < 0:
    actions.insert(0, f"Transaction volume declining ({growth_val:+.1f}%) -- investigate root cause")

if len(demo_summary) > 0:
    youngest = demo_summary[demo_summary['age_band'] == '18-25']
    if len(youngest) > 0 and youngest.iloc[0]['txn_per_account'] < avg_txn_per_account * 0.7:
        actions.append("Young members (18-25) underperforming on txns/account -- engagement campaign opportunity")

for i, action in enumerate(actions, 1):
    print(f"  {i}. {action}")

print("=" * 80)
