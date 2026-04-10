# ===========================================================================
# CATEGORY COMBINATIONS: Which Services Travel Together?
# ===========================================================================
# Co-occurrence matrix: if an account holder uses Auto Loans externally,
# what else are they using? Reveals cross-sell chains.

from itertools import combinations

categories_list = list(all_financial_accounts.keys())

# Build co-occurrence matrix
cooccurrence = pd.DataFrame(0, index=categories_list, columns=categories_list)

for _, row in multi_product_df.iterrows():
    cats = row['categories']
    if len(cats) >= 2:
        for c1, c2 in combinations(cats, 2):
            cooccurrence.loc[c1, c2] += 1
            cooccurrence.loc[c2, c1] += 1

# Diagonal = total accounts in each category
for cat in categories_list:
    if cat in all_financial_accounts:
        cooccurrence.loc[cat, cat] = len(all_financial_accounts[cat])

# Mask diagonal for heatmap (show only co-occurrences)
mask = np.eye(len(categories_list), dtype=bool)
display_matrix = cooccurrence.copy().astype(float)
for i in range(len(categories_list)):
    display_matrix.iloc[i, i] = np.nan

_n_cats = len(categories_list)
fig, ax = plt.subplots(figsize=(max(16, _n_cats * 1.1), max(11, _n_cats * 0.8)))
fig.subplots_adjust(top=0.88, bottom=0.18, left=0.18, right=0.95)

from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list('combo', ['#F8F9FA', '#457B9D', '#E63946'])

sns.heatmap(
    display_matrix, annot=True, fmt=',.0f', cmap=cmap,
    linewidths=2, linecolor='white',
    cbar_kws={'label': 'Shared Accounts', 'shrink': 0.6},
    annot_kws={'fontsize': 16, 'fontweight': 'bold'},
    mask=mask, ax=ax,
    xticklabels=categories_list,
    yticklabels=categories_list
)

ax.set_xticklabels(ax.get_xticklabels(), fontsize=15, fontweight='bold', rotation=45, ha='right')
ax.set_yticklabels(ax.get_yticklabels(), fontsize=15, fontweight='bold', rotation=0)

fig.suptitle("Product Co-Occurrence Matrix",
             fontsize=28, fontweight='bold', color=GEN_COLORS['dark_text'], y=0.96)
fig.text(0.5, 0.91, "Hot cells = account holders using both external services. These reveal cross-sell chains.",
         ha='center', fontsize=16, color=GEN_COLORS['muted'], style='italic')

plt.show()

# Top combinations callout
combo_pairs = []
for c1, c2 in combinations(categories_list, 2):
    count = cooccurrence.loc[c1, c2]
    if count > 0:
        combo_pairs.append((c1, c2, count))

combo_pairs.sort(key=lambda x: x[2], reverse=True)
if len(combo_pairs) > 0:
    print(f"\n    TOP PRODUCT COMBINATIONS (account holders using both externally):")
    for c1, c2, count in combo_pairs[:5]:
        print(f"      {c1} + {c2}: {int(count):,} account holders")
    top_combo = combo_pairs[0]
    print(f"\n    INSIGHT: {int(top_combo[2]):,} account holders have BOTH {top_combo[0]} and {top_combo[1]} externally.")
    print(f"    Bundle these products in a single retention offer for maximum impact.")
