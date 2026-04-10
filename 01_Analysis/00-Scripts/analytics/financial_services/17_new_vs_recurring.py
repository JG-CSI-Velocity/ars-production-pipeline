# ===========================================================================
# NEW vs RECURRING LEAKAGE: Are You Losing Account Holders Now?
# ===========================================================================
# "New leakage" = first external finserv transaction within 90 days.
# This is the urgency signal: are account holders JUST starting to leave?

new_leakers = multi_product_df[multi_product_df['is_new_leakage']].copy()
recurring = multi_product_df[~multi_product_df['is_new_leakage']].copy()

# Per-category breakdown of new vs recurring
new_by_cat = {}
recurring_by_cat = {}

for category, acct_df in all_financial_accounts.items():
    new_count = 0
    rec_count = 0
    for account in acct_df.index:
        first_txn = acct_df.loc[account, 'First Transaction']
        days_since = (DATASET_END - first_txn).days
        if days_since <= 90:
            new_count += 1
        else:
            rec_count += 1
    new_by_cat[category] = new_count
    recurring_by_cat[category] = rec_count

cat_order = sorted(new_by_cat.keys(), key=lambda c: new_by_cat[c] + recurring_by_cat[c])

fig, ax = plt.subplots(figsize=(14, max(8, len(cat_order) * 0.55)))

y_pos = range(len(cat_order))

# Recurring (left, muted)
rec_vals = [recurring_by_cat[c] for c in cat_order]
ax.barh(y_pos, rec_vals, color=GEN_COLORS['info'], alpha=0.5,
        edgecolor='white', linewidth=1, height=0.65, label='Recurring (90d+ ago)', zorder=3)

# New (stacked on top, bold red)
new_vals = [new_by_cat[c] for c in cat_order]
ax.barh(y_pos, new_vals, left=rec_vals, color=GEN_COLORS['accent'],
        edgecolor='white', linewidth=1, height=0.65, label='New Leakage (< 90 days)', zorder=3)

# Labels
for i, cat in enumerate(cat_order):
    total = new_by_cat[cat] + recurring_by_cat[cat]
    new_pct = (new_by_cat[cat] / total * 100) if total > 0 else 0
    ax.text(total * 1.01, i,
            f"{total:,}  ({new_by_cat[cat]:,} new, {new_pct:.0f}%)",
            fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'], va='center')

ax.set_yticks(y_pos)
ax.set_yticklabels(cat_order, fontsize=13, fontweight='bold')
ax.set_xlabel("Number of Accounts", fontsize=18, fontweight='bold', labelpad=12)
ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

gen_clean_axes(ax)
ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
ax.set_axisbelow(True)

max_total = max(new_by_cat[c] + recurring_by_cat[c] for c in cat_order)
ax.set_xlim(0, max_total * 1.40)

ax.set_title("New vs Recurring Leakage by Category",
             fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
ax.text(0.0, 0.97, "Red = account holders who JUST started paying external providers (< 90 days)",
        transform=ax.transAxes, fontsize=14, color=GEN_COLORS['muted'], style='italic')

ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
          ncol=2, fontsize=14, frameon=False)

plt.tight_layout()
plt.subplots_adjust(bottom=0.12)
plt.show()

total_new = sum(new_by_cat.values())
total_all = sum(new_by_cat.values()) + sum(recurring_by_cat.values())
if total_new > 0:
    top_new_cat = max(new_by_cat, key=new_by_cat.get)
    print(f"\n    WARNING: {total_new:,} account holders started using external FinServ in the last 90 days.")
    print(f"    Fastest growing category: {top_new_cat} ({new_by_cat[top_new_cat]:,} new accounts)")
    print(f"    RECOMMENDED: Launch targeted retention campaigns for these account holders immediately.")
