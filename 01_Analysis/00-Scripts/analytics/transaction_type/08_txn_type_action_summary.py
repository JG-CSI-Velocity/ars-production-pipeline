# ===========================================================================
# TXN TYPE ACTION SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled findings table + strategic action items.

findings_tt = []

# 1. PIN vs SIG split
findings_tt.append({
    'Category': 'Type Split',
    'Finding': f"PIN = {tt_pin_pct:.1f}% of transactions, SIG = {tt_sig_pct:.1f}%",
    'Implication': 'PIN-heavy' if tt_pin_pct > tt_sig_pct else 'SIG-heavy' + ' portfolio affects interchange revenue mix',
    'Priority': 'High'
})

# 2. Average ticket difference
if tt_pin_avg_ticket > 0 and tt_sig_avg_ticket > 0:
    ticket_ratio = tt_sig_avg_ticket / tt_pin_avg_ticket if tt_pin_avg_ticket > 0 else 0
    findings_tt.append({
        'Category': 'Avg Ticket',
        'Finding': f"SIG avg ticket ${tt_sig_avg_ticket:.2f} vs PIN ${tt_pin_avg_ticket:.2f} ({ticket_ratio:.1f}x)",
        'Implication': 'Signature transactions carry higher dollar value per swipe',
        'Priority': 'Medium'
    })

# 3. Merchant routing patterns
if 'PIN' in tt_merch_pivot.columns:
    high_pin = (tt_merch_pivot['PIN'] > 80).sum()
    high_sig = (tt_merch_pivot['PIN'] < 20).sum()
    findings_tt.append({
        'Category': 'Routing',
        'Finding': f"{high_pin} merchants are >80% PIN, {high_sig} are >80% SIG (of top 50)",
        'Implication': 'Merchant routing is polarized -- most merchants have a strong type preference',
        'Priority': 'Medium'
    })

# 4. Transaction type count
n_types = len(tt_agg)
other_pct = 100 - tt_pin_pct - tt_sig_pct
if other_pct > 1:
    findings_tt.append({
        'Category': 'Other Types',
        'Finding': f"{other_pct:.1f}% of transactions are non-PIN/SIG ({n_types} types total)",
        'Implication': 'Monitor ACH/check transactions for potential fraud or atypical usage',
        'Priority': 'Low' if other_pct < 5 else 'Medium'
    })

# ---------------------------------------------------------------------------
# Styled findings table
# ---------------------------------------------------------------------------
findings_df_tt = pd.DataFrame(findings_tt)

priority_colors = {
    'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
    'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
    'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
}

styled_findings_tt = (
    findings_df_tt.style
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
    .set_caption("Transaction Type Analysis: Key Findings")
)

display(styled_findings_tt)

# ---------------------------------------------------------------------------
# Action items
# ---------------------------------------------------------------------------
actions_tt = [
    f"Review interchange revenue impact: PIN at {tt_pin_pct:.0f}% vs SIG at {tt_sig_pct:.0f}% of volume",
    "Analyze PIN routing economics -- are merchants routing to lowest-cost network?",
    "Monitor SIG-heavy merchants for potential PIN-debit incentive opportunities",
    "Track PIN vs SIG trend monthly for shifts in cardholder routing behavior",
    "Evaluate age-based routing patterns for targeted cardholder education",
    "Build PIN/SIG merchant scorecard for interchange optimization strategy",
]

actions_df_tt = pd.DataFrame({
    'Action Item': actions_tt,
    'Status': ['Recommended'] * len(actions_tt),
})

styled_actions_tt = (
    actions_df_tt.style
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
    .set_caption("Transaction Type Strategic Action Items")
)

display(styled_actions_tt)
