# ===========================================================================
# BRACKET VOLATILITY: Monthly Stability Analysis (Conference Edition)
# ===========================================================================
# BUG FIX: compute from raw floats in monthly_bracket_pct, NOT string parsing.
# Styled table output.

volatility_rows = []
for bracket in BRACKET_LABELS:
    col_data = monthly_bracket_pct[bracket]
    mean_val = col_data.mean()
    std_val = col_data.std()
    min_val = col_data.min()
    max_val = col_data.max()
    range_val = max_val - min_val

    if std_val < 1.0:
        stability = 'Stable'
    elif std_val < 2.0:
        stability = 'Moderate'
    else:
        stability = 'Volatile'

    volatility_rows.append({
        'Bracket': bracket,
        'Avg %': mean_val,
        'Std Dev': std_val,
        'Min %': min_val,
        'Max %': max_val,
        'Range': range_val,
        'Stability': stability,
    })

volatility_df = pd.DataFrame(volatility_rows)

# Styled display
def _stability_color(val):
    if val == 'Stable':
        return f"color: {GEN_COLORS['success']}; font-weight: bold"
    if val == 'Moderate':
        return f"color: {GEN_COLORS['warning']}; font-weight: bold"
    return f"color: {GEN_COLORS['accent']}; font-weight: bold"

styled = (
    volatility_df.style
    .hide(axis='index')
    .format({
        'Avg %': '{:.1f}%',
        'Std Dev': '{:.2f}%',
        'Min %': '{:.1f}%',
        'Max %': '{:.1f}%',
        'Range': '{:.1f}%',
    })
    .set_properties(**{
        'font-size': '14px',
        'font-weight': 'bold',
        'text-align': 'center',
        'border': '1px solid #E9ECEF',
        'padding': '8px 12px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '15px'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '10px 12px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("Bracket Volatility Analysis")
    .applymap(_stability_color, subset=['Stability'])
)

display(styled)

# Callout
most_volatile = volatility_df.loc[volatility_df['Std Dev'].idxmax(), 'Bracket']
most_stable = volatility_df.loc[volatility_df['Std Dev'].idxmin(), 'Bracket']
print(f"\n    Most stable bracket: {most_stable}")
print(f"    Most volatile bracket: {most_volatile}")
