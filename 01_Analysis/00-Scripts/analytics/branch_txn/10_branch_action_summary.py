# ===========================================================================
# BRANCH ACTION SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Conference-styled findings table + strategic action items.

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping action summary.")
else:
    findings_br = []

    # 1. Concentration
    top5_share_br = br_agg.head(5)['txn_pct'].sum()
    findings_br.append({
        'Category': 'Concentration',
        'Finding': f"Top 5 branches = {top5_share_br:.1f}% of transactions; {len(br_agg)} total branches",
        'Implication': 'Branch activity is ' + ('highly concentrated' if top5_share_br > 60 else 'moderately spread'),
        'Priority': 'High' if top5_share_br > 70 else 'Medium'
    })

    # 2. Dominant branch
    top_br = br_agg.iloc[0]
    findings_br.append({
        'Category': '#1 Branch',
        'Finding': f"Branch {str(top_br['branch'])[:20]} = {top_br['txn_pct']:.1f}% share, {int(top_br['unique_accounts']):,} accounts",
        'Implication': 'Largest branch drives disproportionate card activity',
        'Priority': 'High'
    })

    # 3. Activity variation
    cv_txn = br_agg['txn_count'].std() / br_agg['txn_count'].mean() * 100 if br_agg['txn_count'].mean() > 0 else 0
    findings_br.append({
        'Category': 'Variation',
        'Finding': f"Branch activity CV = {cv_txn:.0f}% (std/mean of txn counts across branches)",
        'Implication': 'Wide variation means some branches are significantly underperforming',
        'Priority': 'Medium' if cv_txn < 100 else 'High'
    })

    # 4. Ticket size range
    min_ticket = br_agg['avg_spend'].min()
    max_ticket = br_agg['avg_spend'].max()
    findings_br.append({
        'Category': 'Ticket Range',
        'Finding': f"Avg ticket ranges from ${min_ticket:.2f} to ${max_ticket:.2f} across branches",
        'Implication': 'Branches with higher tickets may have different merchant mix or demographics',
        'Priority': 'Medium'
    })

    # ---------------------------------------------------------------------------
    # Styled findings table
    # ---------------------------------------------------------------------------
    findings_df_br = pd.DataFrame(findings_br)

    priority_colors = {
        'High': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
        'Medium': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
        'Low': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
    }

    styled_findings_br = (
        findings_df_br.style
        .hide(axis='index')
        .applymap(lambda v: priority_colors.get(v, ''), subset=['Priority'])
        .set_properties(**{
            'font-size': '13px', 'text-align': 'left',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Category'], **{
            'font-weight': 'bold', 'color': GEN_COLORS['accent'],
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
        .set_caption("Branch Analysis: Key Findings")
    )

    display(styled_findings_br)

    # ---------------------------------------------------------------------------
    # Action items
    # ---------------------------------------------------------------------------
    actions_br = [
        f"Develop branch-specific merchant partnership strategies for top {min(5, len(br_agg))} branches",
        f"Investigate underperforming branches for card activation and usage campaigns",
        "Compare branch merchant preferences to identify geographic opportunity gaps",
        "Build branch-level reward programs tailored to local merchant ecosystems",
        "Track branch activity trends monthly for early detection of growth or decline",
        "Align branch staffing and marketing spend with card activity concentration",
    ]

    actions_df_br = pd.DataFrame({
        'Action Item': actions_br,
        'Status': ['Recommended'] * len(actions_br),
    })

    styled_actions_br = (
        actions_df_br.style
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
        .set_caption("Branch Strategic Action Items")
    )

    display(styled_actions_br)
