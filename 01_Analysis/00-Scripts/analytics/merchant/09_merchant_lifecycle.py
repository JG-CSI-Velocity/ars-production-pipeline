# ===========================================================================
# MERCHANT LIFECYCLE: New / Continuing / Lost by Month (Conference Edition)
# ===========================================================================
# Stacked bar: merchant cohort composition over time. (14,7).

fig, ax = plt.subplots(figsize=(14, 7))

plot_cohort = cohort_df.copy()
plot_cohort['month_label'] = plot_cohort['year_month'].dt.to_timestamp().dt.strftime('%b %Y')
x_pos = np.arange(len(plot_cohort))

# Stacked bars: continuing (base), returning, new
ax.bar(x_pos, plot_cohort['continuing'], color=GEN_COLORS['info'],
       label='Continuing', edgecolor='white', linewidth=0.5, width=0.7)
ax.bar(x_pos, plot_cohort['returning'], bottom=plot_cohort['continuing'],
       color=GEN_COLORS['success'], label='Returning',
       edgecolor='white', linewidth=0.5, width=0.7)
ax.bar(x_pos, plot_cohort['new'], bottom=plot_cohort['continuing'] + plot_cohort['returning'],
       color=GEN_COLORS['warning'], label='New',
       edgecolor='white', linewidth=0.5, width=0.7)

# Lost merchants as negative bars
ax.bar(x_pos, -plot_cohort['lost'], color=GEN_COLORS['accent'],
       label='Lost', edgecolor='white', linewidth=0.5, width=0.7, alpha=0.7)

ax.axhline(y=0, color=GEN_COLORS['dark_text'], linewidth=1, zorder=3)

ax.set_xticks(x_pos)
ax.set_xticklabels(plot_cohort['month_label'], fontsize=11, fontweight='bold',
                    rotation=45, ha='right')
ax.set_ylabel("Merchant Count", fontsize=16, fontweight='bold', labelpad=10)
ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

gen_clean_axes(ax, keep_left=True, keep_bottom=True)
ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

ax.set_title("Merchant Lifecycle by Month",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "New entrants, continuing partners, and merchant attrition",
        transform=ax.transAxes, fontsize=15,
        color=GEN_COLORS['muted'], style='italic')

ax.legend(
    loc='upper center', bbox_to_anchor=(0.5, -0.18),
    ncol=4, fontsize=12, frameon=False, title='Merchant Status',
    title_fontproperties={'weight': 'bold', 'size': 13}
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.22)
plt.show()

# Callout
avg_new = cohort_df['new'].mean()
avg_lost = cohort_df['lost'].mean()
net = avg_new - avg_lost
print(f"\n    Avg new merchants/month: {avg_new:.0f}")
print(f"    Avg lost merchants/month: {avg_lost:.0f}")
print(f"    Net monthly change: {'+' if net > 0 else ''}{net:.0f}")
