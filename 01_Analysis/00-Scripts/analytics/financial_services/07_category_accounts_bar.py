# ===========================================================================
# ACCOUNTS BY CATEGORY: Where Are Account Holders Going?
# ===========================================================================

cat_data = finserv_summary_df.copy().sort_values('unique_accounts', ascending=True)

fig, ax = plt.subplots(figsize=(14, max(9, len(cat_data) * 0.6)))

colors = [fs_get_color(c) for c in cat_data['category']]

bars = ax.barh(
    range(len(cat_data)),
    cat_data['unique_accounts'],
    color=colors, edgecolor='white', linewidth=1, height=0.7, zorder=3
)

for i, (_, row) in enumerate(cat_data.iterrows()):
    ax.text(
        row['unique_accounts'] * 1.01, i,
        f"{row['unique_accounts']:,}  ({row['total_transactions']:,} txn)",
        fontsize=13, fontweight='bold', color=GEN_COLORS['dark_text'], va='center'
    )

ax.set_yticks(range(len(cat_data)))
ax.set_yticklabels(cat_data['category'], fontsize=14, fontweight='bold')
ax.set_xlabel("Unique Accounts", fontsize=18, fontweight='bold', labelpad=12)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

gen_clean_axes(ax)
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)
ax.set_xlim(0, cat_data['unique_accounts'].max() * 1.35)

ax.set_title("Account Holder Leakage by Product Category",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97, "How many account holders are paying external financial service providers?",
        transform=ax.transAxes, fontsize=15, color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.show()
