# ===========================================================================
# REG E REVENUE EXPOSURE: OD Fee Revenue Modeling & Erosion Scenarios
# ===========================================================================
# Estimate current OD fee revenue potential from opted-in accounts.
# Model impact of opt-in erosion at 5%, 10%, 20% drops.

# ---------------------------------------------------------------------------
# Revenue model parameters
# ---------------------------------------------------------------------------
# Industry-standard OD fee assumptions (configurable)
AVG_OD_FEE = 30.00           # Average OD fee per occurrence
EST_OD_EVENTS_PER_YEAR = 4   # Estimated OD events per opted-in account per year

# Sensitivity range
OD_FEE_LOW = 25.00
OD_FEE_HIGH = 35.00

# ---------------------------------------------------------------------------
# Current state
# ---------------------------------------------------------------------------
_opted_in_count = len(rege_df[rege_df['current_status'] == 'Opted-In'])
_total_count = len(rege_df)
_current_optin_rate = (_opted_in_count / _total_count * 100) if _total_count > 0 else 0

# Base revenue estimate
_base_revenue = _opted_in_count * EST_OD_EVENTS_PER_YEAR * AVG_OD_FEE
_base_revenue_low = _opted_in_count * EST_OD_EVENTS_PER_YEAR * OD_FEE_LOW
_base_revenue_high = _opted_in_count * EST_OD_EVENTS_PER_YEAR * OD_FEE_HIGH

print(f"    Revenue model assumptions:")
print(f"      Avg OD fee: ${AVG_OD_FEE:.2f} (range: ${OD_FEE_LOW}-${OD_FEE_HIGH})")
print(f"      Est. OD events/year/account: {EST_OD_EVENTS_PER_YEAR}")
print(f"      Current opted-in accounts: {_opted_in_count:,}")

# ---------------------------------------------------------------------------
# Erosion scenarios
# ---------------------------------------------------------------------------
_scenarios = [
    ('Current', 0),
    ('-5% Opt-In', 5),
    ('-10% Opt-In', 10),
    ('-20% Opt-In', 20),
]

_scenario_data = []
for label, drop_pct in _scenarios:
    _adjusted_count = max(0, int(_opted_in_count * (1 - drop_pct / 100)))
    _revenue = _adjusted_count * EST_OD_EVENTS_PER_YEAR * AVG_OD_FEE
    _lost = _base_revenue - _revenue
    _scenario_data.append({
        'scenario': label,
        'opted_in': _adjusted_count,
        'revenue': _revenue,
        'lost_revenue': _lost,
        'drop_pct': drop_pct,
    })

_scenario_df = pd.DataFrame(_scenario_data)

# ---------------------------------------------------------------------------
# Plot: Scenario comparison bar chart
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw={'width_ratios': [1.2, 1]})

# Panel 1: Revenue by scenario
_x_pos = np.arange(len(_scenario_df))
_bar_colors = [
    GEN_COLORS['success'],      # Current
    GEN_COLORS['warning'],      # -5%
    '#E76F51',                   # -10%
    GEN_COLORS['accent'],       # -20%
]

bars = ax1.bar(
    _x_pos, _scenario_df['revenue'],
    color=_bar_colors, edgecolor='white', linewidth=1.5, width=0.6
)

# Revenue labels on bars
for bar, (_, row) in zip(bars, _scenario_df.iterrows()):
    _height = bar.get_height()
    ax1.text(
        bar.get_x() + bar.get_width() / 2, _height + (_scenario_df['revenue'].max() * 0.02),
        gen_fmt_dollar(_height, None),
        ha='center', va='bottom', fontsize=14, fontweight='bold',
        color=GEN_COLORS['dark_text']
    )

# Lost revenue annotation for non-current scenarios
for i, (_, row) in enumerate(_scenario_df.iterrows()):
    if row['lost_revenue'] > 0:
        ax1.text(
            _x_pos[i], bars[i].get_height() * 0.5,
            f"-{gen_fmt_dollar(row['lost_revenue'], None)}",
            ha='center', va='center', fontsize=11, fontweight='bold',
            color='white'
        )

ax1.set_xticks(_x_pos)
ax1.set_xticklabels(_scenario_df['scenario'], fontsize=13, fontweight='bold')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
gen_clean_axes(ax1)
ax1.set_title("Estimated Annual OD Fee Revenue", fontsize=18,
              fontweight='bold', loc='left', color=GEN_COLORS['dark_text'])
ax1.set_ylabel("Revenue Potential", fontsize=14, fontweight='bold')

# Panel 2: Revenue sensitivity (fee amount x opt-in rate)
_fee_range = np.arange(OD_FEE_LOW, OD_FEE_HIGH + 1, 2.5)
_optin_drops = [0, 5, 10, 20]
_sensitivity_colors = [GEN_COLORS['success'], GEN_COLORS['warning'],
                       '#E76F51', GEN_COLORS['accent']]

for drop, color in zip(_optin_drops, _sensitivity_colors):
    _adjusted = max(0, int(_opted_in_count * (1 - drop / 100)))
    _revenues = [_adjusted * EST_OD_EVENTS_PER_YEAR * fee for fee in _fee_range]
    _label = f"Current" if drop == 0 else f"-{drop}% opt-in"
    ax2.plot(_fee_range, _revenues, color=color, linewidth=2.5,
             marker='o', markersize=5, label=_label)

ax2.set_xlabel("Average OD Fee ($)", fontsize=14, fontweight='bold')
ax2.set_ylabel("Annual Revenue", fontsize=14, fontweight='bold')
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
gen_clean_axes(ax2)
ax2.legend(loc='upper left', fontsize=11)
ax2.set_title("Revenue Sensitivity", fontsize=18,
              fontweight='bold', loc='left', color=GEN_COLORS['dark_text'])

fig.suptitle("Reg E Revenue Exposure Analysis",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.5, 0.99,
         f"OD fee revenue potential and erosion scenarios | {DATASET_LABEL}",
         fontsize=14, color=GEN_COLORS['muted'], style='italic',
         ha='center')

plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
_summary_styled = (
    _scenario_df[['scenario', 'opted_in', 'revenue', 'lost_revenue']]
    .style
    .hide(axis='index')
    .format({
        'opted_in': '{:,.0f}',
        'revenue': '${:,.0f}',
        'lost_revenue': '${:,.0f}',
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
    ])
    .set_caption("Revenue Scenario Comparison")
)
display(_summary_styled)

print(f"\n    INSIGHT: Base annual OD fee revenue potential: "
      f"{gen_fmt_dollar(_base_revenue, None)}")
print(f"    INSIGHT: Range: {gen_fmt_dollar(_base_revenue_low, None)} to "
      f"{gen_fmt_dollar(_base_revenue_high, None)}")
print(f"    INSIGHT: 10% opt-in erosion would cost "
      f"{gen_fmt_dollar(_scenario_df.iloc[2]['lost_revenue'], None)}/year")
print(f"    INSIGHT: 20% opt-in erosion would cost "
      f"{gen_fmt_dollar(_scenario_df.iloc[3]['lost_revenue'], None)}/year")
