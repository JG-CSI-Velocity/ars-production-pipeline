# ===========================================================================
# MULTI-PRODUCT: How Many External Services per Account Holder?
# ===========================================================================

multi_dist = multi_product_df['category_count'].value_counts().sort_index()

fig, ax = plt.subplots(figsize=(10, max(8, len(multi_dist) * 1.5)))

bar_colors = [GEN_COLORS['info'] if x == 1 else
              GEN_COLORS['warning'] if x == 2 else
              GEN_COLORS['accent'] for x in multi_dist.index]

y_pos = range(len(multi_dist))
bars = ax.barh(y_pos, multi_dist.values,
               color=bar_colors, edgecolor='white', linewidth=2, alpha=0.85,
               height=0.6, zorder=3)

for i, (cat_count, acc_count) in enumerate(zip(multi_dist.index, multi_dist.values)):
    pct = acc_count / len(multi_product_df) * 100
    ax.text(acc_count * 1.01, i,
            f'{acc_count:,}  ({pct:.0f}%)',
            ha='left', va='center', fontsize=15, fontweight='bold',
            color=GEN_COLORS['dark_text'])

ax.set_yticks(y_pos)
ax.set_yticklabels([f"{c} {'category' if c == 1 else 'categories'}" for c in multi_dist.index],
                   fontsize=16, fontweight='bold')
ax.set_xlabel("Number of Accounts", fontsize=18, fontweight='bold', labelpad=12)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
ax.set_xlim(0, multi_dist.values.max() * 1.35)

gen_clean_axes(ax, keep_left=True)
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

ax.set_title("External Product Depth per Account Holder",
             fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97, "More categories = deeper external relationships = higher priority",
        transform=ax.transAxes, fontsize=16, color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()

# Callout below chart
multi_2plus = multi_dist[multi_dist.index >= 2].sum()
multi_3plus = multi_dist[multi_dist.index >= 3].sum()
print(f"\n    2+ categories: {multi_2plus:,} accounts  |  3+ categories: {multi_3plus:,} accounts (highest priority)")
