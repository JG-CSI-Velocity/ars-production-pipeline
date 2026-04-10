# ===========================================================================
# SEASONAL INDEX: Calendar Month Activity Index (Conference Edition)
# ===========================================================================
# Bar: index where 100 = average. Green above, red below. (8,7) square.

# Build calendar month index
cal_monthly = monthly_summary.copy()
cal_monthly['cal_month'] = cal_monthly.index.month
cal_monthly['cal_month_name'] = cal_monthly.index.strftime('%b')

# Average txns per calendar month across years
cal_avg = cal_monthly.groupby('cal_month')['txn_count'].mean()
overall_avg = cal_avg.mean()

# Index: 100 = overall average
seasonal_index = (cal_avg / overall_avg * 100).reset_index()
seasonal_index.columns = ['cal_month', 'index']

# Month names
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
seasonal_index['month_name'] = seasonal_index['cal_month'].apply(
    lambda m: month_names[m - 1] if 1 <= m <= 12 else str(m)
)

fig, ax = plt.subplots(figsize=(8, 7))

colors = [
    GEN_COLORS['success'] if v >= 100 else GEN_COLORS['accent']
    for v in seasonal_index['index']
]

bars = ax.bar(
    seasonal_index['month_name'], seasonal_index['index'],
    color=colors, edgecolor='white', linewidth=1.5, width=0.7
)

# Baseline at 100
ax.axhline(y=100, color=GEN_COLORS['muted'], linewidth=2, linestyle='--', zorder=1)
ax.text(len(seasonal_index) - 0.5, 101, "Average = 100",
        fontsize=12, color=GEN_COLORS['muted'], ha='right', va='bottom')

# Value labels
for bar, val in zip(bars, seasonal_index['index']):
    y_offset = 1 if val >= 100 else -4
    ax.text(bar.get_x() + bar.get_width() / 2, val + y_offset,
            f"{val:.0f}", ha='center', va='bottom' if val >= 100 else 'top',
            fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'])

gen_clean_axes(ax, keep_left=True, keep_bottom=True)
ax.set_ylabel("Index (100 = Avg)", fontsize=16, fontweight='bold', labelpad=10)

ax.set_title("Seasonal Activity Index",
             fontsize=22, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Which months run hot or cold?",
        transform=ax.transAxes, fontsize=14,
        color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()
