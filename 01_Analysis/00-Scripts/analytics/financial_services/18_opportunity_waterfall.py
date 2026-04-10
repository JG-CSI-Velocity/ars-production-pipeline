# ===========================================================================
# OPPORTUNITY WATERFALL: How Big Is the Addressable Market?
# ===========================================================================
# For each category: total account holders -> those with external activity -> your opportunity

total_members = combined_df['primary_account_num'].nunique()

opp_data = []
for category, acct_df in all_financial_accounts.items():
    leaking = len(acct_df)
    active_leaking = len(acct_df[acct_df['Recency_Days'] <= 90])
    opp_data.append({
        'category': category,
        'total_members': total_members,
        'leaking': leaking,
        'active_leaking': active_leaking,
        'pct_leaking': leaking / total_members * 100 if total_members > 0 else 0,
    })

opp_df = pd.DataFrame(opp_data).sort_values('leaking', ascending=True)

fig, ax = plt.subplots(figsize=(14, max(9, len(opp_df) * 0.6)))

# Background: total account holders (light gray, full width)
ax.barh(range(len(opp_df)), [total_members] * len(opp_df),
        color=GEN_COLORS['grid'], alpha=0.3, height=0.65, zorder=1)

# Leaking accounts (category color)
colors = [fs_get_color(c) for c in opp_df['category']]
ax.barh(range(len(opp_df)), opp_df['leaking'],
        color=colors, edgecolor='white', linewidth=1, height=0.65, zorder=3)

# Active leaking (dark overlay on left portion)
ax.barh(range(len(opp_df)), opp_df['active_leaking'],
        color=GEN_COLORS['accent'], alpha=0.6, edgecolor='none', height=0.65, zorder=4)

# Labels
for i, (_, row) in enumerate(opp_df.iterrows()):
    ax.text(
        row['leaking'] * 1.01, i,
        f"{row['leaking']:,} account holders ({row['pct_leaking']:.1f}%)",
        fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'], va='center'
    )

ax.set_yticks(range(len(opp_df)))
ax.set_yticklabels(opp_df['category'], fontsize=13, fontweight='bold')
ax.set_xlabel("Account Holders", fontsize=18, fontweight='bold', labelpad=12)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

gen_clean_axes(ax)
ax.set_axisbelow(True)

ax.set_title("Product Opportunity by Category",
             fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97,
        "Gray = total account holders  |  Color = external users  |  Red = active (< 90d)",
        transform=ax.transAxes, fontsize=14, color=GEN_COLORS['muted'], style='italic')

# Total opportunity summary in corner
total_leaking = opp_df['leaking'].sum()
total_active = opp_df['active_leaking'].sum()
ax.text(0.97, 0.05,
        f"Total leaking: {total_leaking:,}\nActive (90d): {total_active:,}",
        transform=ax.transAxes, fontsize=14, fontweight='bold',
        color=GEN_COLORS['accent'], ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=GEN_COLORS['accent'], alpha=0.9))

plt.tight_layout()
plt.show()

print(f"\n    OPPORTUNITY: Each colored bar represents account holders you could serve with your own products.")
print(f"    Total addressable: {total_leaking:,} account holder-product relationships across {len(opp_df)} categories.")
