# ===========================================================================
# BRACKET DATA: Spending Bins + Monthly Crosstab (Conference Edition)
# ===========================================================================
# 8 bins, counts/pcts/accounts per bracket. Styled summary output.

# Define spending brackets
BRACKET_BINS = [0, 1, 5, 10, 25, 50, 100, 500, float('inf')]
BRACKET_LABELS = ['< $1', '$1-5', '$5-10', '$10-25', '$25-50', '$50-100', '$100-500', '$500+']

# Create bracket column
combined_df['amount_bracket'] = pd.cut(
    combined_df['amount'], bins=BRACKET_BINS, labels=BRACKET_LABELS, right=False
)

# ---------------------------------------------------------------------------
# Bracket summary: counts, percentages, accounts
# ---------------------------------------------------------------------------
bracket_summary = []
total_txns_all = len(combined_df)

for bracket in BRACKET_LABELS:
    mask = combined_df['amount_bracket'] == bracket
    count = mask.sum()
    accounts = combined_df.loc[mask, 'primary_account_num'].nunique()
    bracket_summary.append({
        'bracket': bracket,
        'txn_count': count,
        'txn_pct': (count / total_txns_all * 100) if total_txns_all > 0 else 0,
        'account_count': accounts,
        'acct_pct': (accounts / portfolio_kpis['total_accounts'] * 100)
                    if portfolio_kpis['total_accounts'] > 0 else 0,
    })

bracket_df = pd.DataFrame(bracket_summary)

# ---------------------------------------------------------------------------
# Monthly crosstab: bracket shares over time (raw percentages)
# ---------------------------------------------------------------------------
monthly_bracket_counts = pd.crosstab(
    combined_df['year_month'], combined_df['amount_bracket']
)
monthly_bracket_pct = pd.crosstab(
    combined_df['year_month'], combined_df['amount_bracket'], normalize='index'
) * 100

# ---------------------------------------------------------------------------
# Conference-styled bracket summary
# ---------------------------------------------------------------------------
bracket_display = bracket_df.copy()
bracket_display.columns = ['Bracket', 'Transactions', 'Trans %', 'Accounts', 'Acct %']

styled = (
    bracket_display.style
    .hide(axis='index')
    .format({
        'Transactions': '{:,.0f}',
        'Trans %': '{:.1f}%',
        'Accounts': '{:,.0f}',
        'Acct %': '{:.1f}%',
    })
    .set_properties(**{
        'font-size': '15px',
        'font-weight': 'bold',
        'text-align': 'center',
        'border': '1px solid #E9ECEF',
        'padding': '10px 14px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '16px'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '10px 14px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Spending Bracket Summary")
    .bar(subset=['Transactions'], color=GEN_COLORS['info'], vmin=0)
)

display(styled)

print(f"\n    {len(BRACKET_LABELS)} brackets | {bracket_df['txn_count'].sum():,} total transactions bucketed")
