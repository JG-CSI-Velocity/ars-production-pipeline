# ===========================================================================
# PAYROLL & PFI ACTION SUMMARY: Findings & Strategic Recommendations
# ===========================================================================
# Conference-styled findings table + strategic action items.

INDUSTRY_PFI_RATE = 60.0  # Industry benchmark: ~60% PFI rate

# ---------------------------------------------------------------------------
# 1. Build findings
# ---------------------------------------------------------------------------
findings = []

# Finding 1: Payroll capture rate vs industry
n_total = len(payroll_df)
n_payroll = int(payroll_df['has_payroll'].sum())
pct_payroll = n_payroll / n_total * 100 if n_total > 0 else 0
gap_vs_industry = INDUSTRY_PFI_RATE - pct_payroll

findings.append({
    'Category': 'Payroll Capture',
    'Finding': (f"{pct_payroll:.1f}% of accounts have detected payroll "
                f"({n_payroll:,} of {n_total:,})"),
    'Implication': (f"Industry PFI benchmark is ~{INDUSTRY_PFI_RATE:.0f}%; "
                    f"gap of {gap_vs_industry:+.1f} pp represents "
                    f"~{abs(int(gap_vs_industry / 100 * n_total)):,} accounts"),
    'Priority': 'High' if gap_vs_industry > 10 else ('Medium' if gap_vs_industry > 0 else 'Low'),
})

# Finding 2: Payroll value multiplier
bal_col = None
for col_name in ['avg_balance', 'curr_balance']:
    if col_name in payroll_df.columns:
        bal_col = col_name
        break

if bal_col:
    pr_bal = payroll_df.loc[payroll_df['has_payroll'], bal_col].mean()
    npr_bal = payroll_df.loc[~payroll_df['has_payroll'], bal_col].mean()
    bal_mult = pr_bal / npr_bal if npr_bal > 0 else 0
    findings.append({
        'Category': 'Value Multiplier',
        'Finding': f"Payroll members carry {bal_mult:.1f}x higher balances (${pr_bal:,.0f} vs ${npr_bal:,.0f})",
        'Implication': 'Each payroll capture directly increases deposits and fee income',
        'Priority': 'High',
    })

pr_txns = payroll_df.loc[payroll_df['has_payroll'], 'total_txn_count'].mean()
npr_txns = payroll_df.loc[~payroll_df['has_payroll'], 'total_txn_count'].mean()
txn_mult = pr_txns / npr_txns if npr_txns > 0 else 0
findings.append({
    'Category': 'Engagement Lift',
    'Finding': f"Payroll members generate {txn_mult:.1f}x more transactions ({pr_txns:,.0f} vs {npr_txns:,.0f})",
    'Implication': 'Higher interchange and cross-sell opportunity',
    'Priority': 'High' if txn_mult >= 2.0 else 'Medium',
})

# Finding 3: PFI tier distribution
PFI_TIER_ORDER = ['Primary', 'Secondary', 'Tertiary', 'Incidental']
if 'pfi_tier' in payroll_df.columns:
    tier_pcts = payroll_df['pfi_tier'].value_counts(normalize=True) * 100
    primary_pct = tier_pcts.get('Primary', 0)
    secondary_pct = tier_pcts.get('Secondary', 0)
    incidental_pct = tier_pcts.get('Incidental', 0)
    findings.append({
        'Category': 'PFI Distribution',
        'Finding': (f"Primary: {primary_pct:.1f}%, Secondary: {secondary_pct:.1f}%, "
                    f"Incidental: {incidental_pct:.1f}%"),
        'Implication': f"Secondary tier ({secondary_pct:.0f}%) is the prime upgrade target -- already engaged but missing payroll",
        'Priority': 'High',
    })

# Finding 4: Weakest branches/segments
if 'branch' in payroll_df.columns and payroll_df['branch'].notna().sum() > 0:
    branch_penet = payroll_df.groupby('branch').agg(
        total=('has_payroll', 'count'),
        payroll=('has_payroll', 'sum'),
    ).reset_index()
    branch_penet['pct'] = branch_penet['payroll'] / branch_penet['total'] * 100
    branch_penet = branch_penet[branch_penet['total'] >= 10]

    if len(branch_penet) > 0:
        lowest_branches = branch_penet.nsmallest(3, 'pct')
        # astype(str) first: when branch_config.json is missing, branch
        # column is numeric and .str[] raises ``Can only use .str accessor
        # with string values!''. Harmless when branch is already string.
        branch_names = ', '.join(
            lowest_branches['branch'].astype(str).str[:15].tolist()
        )
        avg_low = lowest_branches['pct'].mean()
        findings.append({
            'Category': 'Branch Gaps',
            'Finding': f"Lowest payroll branches: {branch_names} (avg {avg_low:.1f}%)",
            'Implication': 'Targeted direct deposit campaigns at these branches could close the gap',
            'Priority': 'Medium',
        })

# Finding 5: Age segment opportunity
if 'age_band' in payroll_df.columns and payroll_df['age_band'].notna().sum() > 0:
    age_penet = payroll_df.groupby('age_band', observed=True).agg(
        total=('has_payroll', 'count'),
        payroll=('has_payroll', 'sum'),
    ).reset_index()
    age_penet['pct'] = age_penet['payroll'] / age_penet['total'] * 100

    if len(age_penet) > 0:
        lowest_age = age_penet.nsmallest(1, 'pct').iloc[0]
        highest_age = age_penet.nlargest(1, 'pct').iloc[0]
        findings.append({
            'Category': 'Age Segments',
            'Finding': (f"Strongest: {highest_age['age_band']} ({highest_age['pct']:.1f}%), "
                        f"Weakest: {lowest_age['age_band']} ({lowest_age['pct']:.1f}%)"),
            'Implication': f"Younger segments may prefer digital-first direct deposit switching tools",
            'Priority': 'Medium',
        })

# Finding 6: Processor concentration
if 'payroll_source' in combined_df.columns:
    source_counts = combined_df[combined_df['payroll_detected']].groupby(
        'payroll_source'
    )['primary_account_num'].nunique()
    if len(source_counts) > 0:
        top_source = source_counts.idxmax()
        top_source_pct = source_counts.max() / source_counts.sum() * 100
        findings.append({
            'Category': 'Processor Mix',
            'Finding': f"Top processor: {top_source} ({top_source_pct:.1f}% of payroll accounts)",
            'Implication': 'Explore employer partnership with top processor for bulk enrollment',
            'Priority': 'Low',
        })

# ---------------------------------------------------------------------------
# 2. Styled findings table
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
    .set_caption("Payroll & PFI Analysis: Key Findings")
)

display(styled_findings)

# ---------------------------------------------------------------------------
# 3. Strategic action items
# ---------------------------------------------------------------------------
actions = [
    {
        'Action': 'Launch "Switch Your Direct Deposit" campaign targeting Secondary-tier PFI members',
        'Target': f"~{int(payroll_df[payroll_df['pfi_tier'] == 'Secondary'].shape[0] if 'pfi_tier' in payroll_df.columns else 0):,} accounts",
        'Expected Impact': 'Highest conversion probability -- already engaged, just missing payroll',
        'Priority': 'High',
    },
    {
        'Action': 'Implement first-payroll bonus ($50-$100) for new direct deposit enrollment',
        'Target': f"All {n_total - n_payroll:,} non-payroll accounts",
        'Expected Impact': f"Each conversion adds ~${pr_bal - npr_bal:,.0f} in avg balance" if bal_col else "Increased deposits per conversion",
        'Priority': 'High',
    },
]

if 'branch' in payroll_df.columns and payroll_df['branch'].notna().sum() > 0:
    if len(branch_penet) > 0:
        lowest_br = branch_penet.nsmallest(3, 'pct')
        actions.append({
            'Action': f"Branch-specific payroll drives at {', '.join(lowest_br['branch'].astype(str).str[:12].tolist())}",
            'Target': f"~{lowest_br['total'].sum():,} accounts at low-penetration branches",
            'Expected Impact': f"Close {abs(pct_payroll - lowest_br['pct'].mean()):.0f}pp gap vs CU average",
            'Priority': 'Medium',
        })

actions.extend([
    {
        'Action': 'Build digital direct deposit switch tool (pre-filled employer forms)',
        'Target': 'All members via mobile/online banking',
        'Expected Impact': 'Reduce friction -- industry data shows 40% higher conversion with digital tools',
        'Priority': 'Medium',
    },
    {
        'Action': 'Automate PFI score tracking and trigger campaigns at tier thresholds',
        'Target': f"Tertiary tier ({payroll_df[payroll_df['pfi_tier'] == 'Tertiary'].shape[0] if 'pfi_tier' in payroll_df.columns else 0:,} accounts approaching Secondary)",
        'Expected Impact': 'Proactive engagement before members disengage',
        'Priority': 'Medium',
    },
    {
        'Action': 'Partner with top payroll processors for employer-level enrollment programs',
        'Target': 'HR departments at local employers',
        'Expected Impact': 'Bulk direct deposit capture at point of hire',
        'Priority': 'Low',
    },
])

actions_df = pd.DataFrame(actions)

styled_actions = (
    actions_df.style
    .hide(axis='index')
    .applymap(lambda v: priority_colors.get(v, ''), subset=['Priority'])
    .set_properties(**{
        'font-size': '13px', 'text-align': 'left',
        'border': '1px solid #E9ECEF', 'padding': '8px 12px',
    })
    .set_properties(subset=['Action'], **{
        'font-weight': 'bold',
    })
    .set_properties(subset=['Priority'], **{
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
    .set_caption("Payroll & PFI Strategic Action Items")
)

display(styled_actions)

# ---------------------------------------------------------------------------
# 4. Executive summary print
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("  PAYROLL & PFI EXECUTIVE SUMMARY")
print("=" * 70)
print(f"  Payroll capture rate:     {pct_payroll:.1f}% ({n_payroll:,} accounts)")
print(f"  Industry benchmark:       ~{INDUSTRY_PFI_RATE:.0f}%")
print(f"  Gap:                      {gap_vs_industry:+.1f} percentage points")
if bal_col:
    print(f"  Balance multiplier:       {bal_mult:.1f}x (${pr_bal:,.0f} vs ${npr_bal:,.0f})")
print(f"  Transaction multiplier:   {txn_mult:.1f}x ({pr_txns:,.0f} vs {npr_txns:,.0f})")
if 'pfi_tier' in payroll_df.columns:
    print(f"  Primary PFI members:      {primary_pct:.1f}%")
    print(f"  Upgrade target (Secondary): {secondary_pct:.1f}% ({int(secondary_pct/100*n_total):,} accounts)")
print("=" * 70)
