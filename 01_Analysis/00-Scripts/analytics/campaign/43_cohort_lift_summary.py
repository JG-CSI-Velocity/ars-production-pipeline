# ===========================================================================
# COHORT LIFT SUMMARY: Findings & Recommendations (Conference Edition)
# ===========================================================================
# Styled HTML table summarizing per-wave results + strategic action items
# for the client presentation. Uses established action-summary pattern.

if 'cohort_summary' not in dir() or len(cohort_summary) == 0:
    print("    No cohort data available. Skipping lift summary.")
else:
    # -----------------------------------------------------------------
    # Findings table: one row per wave
    # -----------------------------------------------------------------
    findings_lift = []

    for _, row in cohort_summary.iterrows():
        did_val = row['did_spend_lift']
        did_pct = row['did_spend_pct']
        swipe_did = row['did_swipes_lift']
        sign = '+' if did_val >= 0 else ''

        findings_lift.append({
            'Wave': row['wave'],
            'Mailed': f"{row['mailed']:,}",
            'Responded': f"{row['responded']:,}",
            'Response Rate': f"{row['response_rate']:.1f}%",
            'DID Spend Lift': f"{sign}${did_val:,.2f}/acct/mo",
            'DID Swipes Lift': f"{'+' if swipe_did >= 0 else ''}{swipe_did:,.1f}/acct/mo",
            'Verdict': 'Positive Lift' if did_val > 0 else 'Neutral' if did_val == 0 else 'Negative',
        })

    # Overall summary row
    avg_did = cohort_summary['did_spend_lift'].mean()
    avg_swipe_did = cohort_summary['did_swipes_lift'].mean()
    total_resp = cohort_summary['responded'].sum()
    total_mailed = cohort_summary['mailed'].sum()
    avg_rate = total_resp / total_mailed * 100 if total_mailed > 0 else 0

    findings_lift.append({
        'Wave': 'OVERALL AVG',
        'Mailed': f"{total_mailed:,}",
        'Responded': f"{total_resp:,}",
        'Response Rate': f"{avg_rate:.1f}%",
        'DID Spend Lift': f"{'+'if avg_did >= 0 else ''}${avg_did:,.2f}/acct/mo",
        'DID Swipes Lift': f"{'+'if avg_swipe_did >= 0 else ''}{avg_swipe_did:,.1f}/acct/mo",
        'Verdict': 'PROGRAM WORKS' if avg_did > 0 else 'REVIEW NEEDED',
    })

    findings_df_lift = pd.DataFrame(findings_lift)

    verdict_colors = {
        'Positive Lift': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold',
        'Neutral': 'background-color: #FFF8E1; color: #FF9F1C; font-weight: bold',
        'Negative': 'background-color: #FDECEA; color: #E63946; font-weight: bold',
        'PROGRAM WORKS': 'background-color: #E8F5E9; color: #2EC4B6; font-weight: bold; font-size: 14px',
        'REVIEW NEEDED': 'background-color: #FDECEA; color: #E63946; font-weight: bold; font-size: 14px',
    }

    styled_findings_lift = (
        findings_df_lift.style
        .hide(axis='index')
        .applymap(lambda v: verdict_colors.get(v, ''), subset=['Verdict'])
        .set_properties(**{
            'font-size': '13px', 'text-align': 'center',
            'border': '1px solid #E9ECEF', 'padding': '8px 12px',
        })
        .set_properties(subset=['Wave'], **{
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
        .set_caption(f"ARS Cohort Lift Analysis: Wave-by-Wave Results  ({DATASET_LABEL})")
    )

    display(styled_findings_lift)

    # -----------------------------------------------------------------
    # Key narrative points for client presentation
    # -----------------------------------------------------------------
    narrative = []

    positive_waves = (cohort_summary['did_spend_lift'] > 0).sum()
    total_waves = len(cohort_summary)
    narrative.append(f"{positive_waves} of {total_waves} waves show positive DID spend lift")

    if avg_did > 0:
        annual_lift = avg_did * 12 * total_resp
        narrative.append(f"Average DID lift: ${avg_did:,.2f}/acct/month = ${avg_did * 12:,.0f}/acct/year")
        narrative.append(f"Estimated annual portfolio impact: ${annual_lift:,.0f} in protected spend")

    if avg_swipe_did > 0:
        narrative.append(f"Card usage (swipes) also shows {avg_swipe_did:+,.1f} DID lift per account/month")

    # Cumulative unique responders
    all_resp_accts = set(cohort_acct[cohort_acct['status'] == 'Responder']['acct_number'])
    all_mailed_accts = set(cohort_acct['acct_number'])
    pen = len(all_resp_accts) / len(all_mailed_accts) * 100 if len(all_mailed_accts) > 0 else 0
    narrative.append(f"Cumulative penetration: {pen:.1f}% of mailed accounts have responded at least once")

    print("\n    --- Key Narrative for Client Presentation ---")
    for point in narrative:
        print(f"    * {point}")

    # -----------------------------------------------------------------
    # Strategic action items
    # -----------------------------------------------------------------
    actions_lift = [
        "Present DID methodology to client: isolates TRUE program lift from market trends",
        "Use counterfactual chart (cell 18) as the headline visual in next board presentation",
        "Track persistence data: if lift fades after 3 months, consider booster campaigns",
        "Focus future mailings on accounts showing early response signals from prior waves",
        "Quantify interchange revenue from protected spend to demonstrate ROI in dollars",
        "Consider increasing mailing frequency for high-potential non-responders",
    ]

    actions_df_lift = pd.DataFrame({
        'Action Item': actions_lift,
        'Status': ['Recommended'] * len(actions_lift),
    })

    styled_actions_lift = (
        actions_df_lift.style
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
        .set_caption("Cohort Lift Strategic Action Items")
    )

    display(styled_actions_lift)
