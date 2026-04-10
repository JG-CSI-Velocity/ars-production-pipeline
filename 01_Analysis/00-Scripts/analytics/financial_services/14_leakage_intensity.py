# ===========================================================================
# LEAKAGE INTENSITY: Highest-Priority Account Holders
# ===========================================================================
# Bubble chart: breadth (x) vs depth (y), size = urgency, color = tier

top_leakers = multi_product_df.head(50).copy()

# Tier labeling
top_leakers['priority_tier'] = pd.cut(
    top_leakers['leakage_score'],
    bins=[-1, 30, 60, 100],
    labels=['Monitor', 'Engage', 'Critical']
)

tier_colors = {
    'Critical': GEN_COLORS['accent'],
    'Engage':   GEN_COLORS['warning'],
    'Monitor':  GEN_COLORS['info']
}

fig, ax = plt.subplots(figsize=(14, 9))

for tier in ['Monitor', 'Engage', 'Critical']:
    subset = top_leakers[top_leakers['priority_tier'] == tier]
    if len(subset) == 0:
        continue
    # Bubble size from urgency score
    sizes = subset['urgency_score'].clip(lower=20) * 8

    ax.scatter(
        subset['category_count'],
        subset['total_txn'],
        s=sizes, c=tier_colors.get(tier, GEN_COLORS['muted']),
        alpha=0.65, edgecolor='white', linewidth=1.5,
        label=f"{tier} ({len(subset)})", zorder=3
    )

# Jitter x slightly for visibility
ax.set_xlabel("External FinServ Categories Used", fontsize=18, fontweight='bold', labelpad=12)
ax.set_ylabel("Total External Transactions", fontsize=18, fontweight='bold', labelpad=12)
ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

# Force integer x-ticks
ax.set_xticks(range(1, int(top_leakers['category_count'].max()) + 1))

gen_clean_axes(ax)
ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
ax.set_axisbelow(True)

ax.set_title("Leakage Intensity: Top 50 Accounts",
             fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97,
        "Score = 30% breadth + 30% depth + 40% recency  |  Bubble size = urgency",
        transform=ax.transAxes, fontsize=14, color=GEN_COLORS['muted'], style='italic')

legend = ax.legend(
    loc='upper center', bbox_to_anchor=(0.5, -0.08),
    ncol=3, fontsize=14, frameon=False,
    markerscale=0.6
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.12)
plt.show()

# Stats
critical_count = len(top_leakers[top_leakers['priority_tier'] == 'Critical'])
engage_count = len(top_leakers[top_leakers['priority_tier'] == 'Engage'])
print(f"\n    PRIORITY BREAKDOWN (Top 50):")
print(f"      Critical: {critical_count} accounts (immediate action)")
print(f"      Engage:   {engage_count} accounts (proactive outreach)")
print(f"      Monitor:  {len(top_leakers) - critical_count - engage_count} accounts (watch list)")
