# ===========================================================================
# CELL 4: BUILD CROSS-CATEGORY + LEAKAGE SCORING DATA
# ===========================================================================
# Produces: multi_product_df, leakage_scores_df

# --- Multi-product mapping ---
all_accounts = set()
for category, accounts in all_financial_accounts.items():
    all_accounts.update(accounts.index)

account_category_map = {}
for account in all_accounts:
    cats = []
    total_txn = 0
    most_recent = pd.Timestamp.min
    first_seen = pd.Timestamp.max
    for category, account_summary in all_financial_accounts.items():
        if account in account_summary.index:
            row = account_summary.loc[account]
            cats.append(category)
            total_txn += row['Transaction Count']
            if row['Last Transaction'] > most_recent:
                most_recent = row['Last Transaction']
            if row['First Transaction'] < first_seen:
                first_seen = row['First Transaction']
    account_category_map[account] = {
        'categories': cats,
        'category_count': len(cats),
        'category_list': ', '.join(cats),
        'total_txn': total_txn,
        'most_recent': most_recent,
        'first_seen': first_seen
    }

multi_product_df = pd.DataFrame.from_dict(account_category_map, orient='index')
multi_product_df.index.name = 'account'
multi_product_df = multi_product_df.sort_values('category_count', ascending=False)

# Recency in days (anchored to dataset end date, not today)
multi_product_df['recency_days'] = (DATASET_END - multi_product_df['most_recent']).dt.days
multi_product_df['tenure_days'] = (DATASET_END - multi_product_df['first_seen']).dt.days

# --- Leakage intensity score (0-100) ---
# Breadth: category count normalized
max_cats = multi_product_df['category_count'].max()
multi_product_df['breadth_score'] = (multi_product_df['category_count'] / max_cats * 100) if max_cats > 0 else 0

# Depth: transaction count normalized
max_txn = multi_product_df['total_txn'].max()
multi_product_df['depth_score'] = (multi_product_df['total_txn'] / max_txn * 100) if max_txn > 0 else 0

# Urgency: recency (lower days = higher urgency)
multi_product_df['urgency_score'] = (
    100 - multi_product_df['recency_days'].clip(upper=365) / 365 * 100
)

# Composite leakage score
multi_product_df['leakage_score'] = (
    multi_product_df['breadth_score'] * 0.30 +
    multi_product_df['depth_score'] * 0.30 +
    multi_product_df['urgency_score'] * 0.40
)

multi_product_df = multi_product_df.sort_values('leakage_score', ascending=False)

# New leakage flag (first seen within 90 days)
multi_product_df['is_new_leakage'] = multi_product_df['tenure_days'] <= 90

multi_count = len(multi_product_df[multi_product_df['category_count'] >= 2])
high_leakage = len(multi_product_df[multi_product_df['leakage_score'] > 60])
new_leakage = len(multi_product_df[multi_product_df['is_new_leakage']])

print(f"Cross-category leakage scoring: {len(multi_product_df):,} unique accounts\n")

cross_cat_rows = [
    {'Metric': 'Total unique accounts', 'Count': f"{len(multi_product_df):,}"},
    {'Metric': 'Multi-product (2+ categories)', 'Count': f"{multi_count:,}"},
    {'Metric': 'High leakage score (>60)', 'Count': f"{high_leakage:,}"},
    {'Metric': 'New leakage (< 90 days)', 'Count': f"{new_leakage:,}"},
]
cross_cat_display = pd.DataFrame(cross_cat_rows)
display(cross_cat_display.style.hide(axis='index').set_properties(**{
    'text-align': 'left',
    'font-weight': 'bold'
}, subset=['Metric']).set_properties(**{
    'text-align': 'center'
}, subset=['Count']))
