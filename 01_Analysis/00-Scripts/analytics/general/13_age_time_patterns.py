# ===========================================================================
# AGE TIME PATTERNS: Hour-of-Day Activity by Age Band (Conference Edition)
# ===========================================================================
# Overlaid curves showing when each age band transacts. (14,7).

fig, ax = plt.subplots(figsize=(16, 8))

age_matched_local = demo_df[demo_df['age_band'].notna()].copy()

for band in AGE_ORDER:
    band_data = age_matched_local[age_matched_local['age_band'] == band]
    if len(band_data) == 0:
        continue

    hourly = band_data.groupby('txn_hour').size()
    # Normalize to percentage of band's total
    hourly_pct = (hourly / hourly.sum() * 100).reindex(range(24), fill_value=0)

    ax.plot(
        hourly_pct.index, hourly_pct.values,
        color=AGE_PALETTE[band], linewidth=3, label=band,
        marker='o', markersize=4, zorder=4
    )

ax.set_xlabel("Hour of Day", fontsize=18, fontweight='bold', labelpad=10)
ax.set_ylabel("% of Age Band's Transactions", fontsize=18, fontweight='bold', labelpad=10)
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f"{h}:00" for h in range(0, 24, 2)], fontsize=15)
ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

gen_clean_axes(ax, keep_left=True, keep_bottom=True)
ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

ax.set_title("Transaction Timing by Age Group",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Younger account holders transact later; older account holders transact earlier",
        transform=ax.transAxes, fontsize=16,
        color=GEN_COLORS['muted'], style='italic')

ax.legend(
    loc='upper center', bbox_to_anchor=(0.5, -0.12),
    ncol=6, fontsize=15, frameon=False, title='Age Band',
    title_fontproperties={'weight': 'bold', 'size': 16}
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.15)
plt.show()
