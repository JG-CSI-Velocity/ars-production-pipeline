# ===========================================================================
# ENGAGEMENT DATA: Classify Accounts by Activity Tier
# ===========================================================================
# Power (top 5%), Heavy (5-20%), Moderate (20-60%), Light (60-90%), Dormant (bottom 10%).
# Data only.

# Transaction count per account
acct_txn_counts = (
    combined_df.groupby('primary_account_num')['transaction_date']
    .count()
    .reset_index()
)
acct_txn_counts.columns = ['account', 'txn_count']
acct_txn_counts = acct_txn_counts.sort_values('txn_count', ascending=False).reset_index(drop=True)

# Percentile ranks (1 = most active)
acct_txn_counts['pct_rank'] = acct_txn_counts['txn_count'].rank(pct=True, ascending=False)

# Classify tiers
def classify_engagement(pct_rank):
    if pct_rank <= 0.05:
        return 'Power'
    if pct_rank <= 0.20:
        return 'Heavy'
    if pct_rank <= 0.60:
        return 'Moderate'
    if pct_rank <= 0.90:
        return 'Light'
    return 'Dormant'

acct_txn_counts['tier'] = acct_txn_counts['pct_rank'].apply(classify_engagement)

# Engagement summary
engagement_summary = []
total_accts = len(acct_txn_counts)
total_txns_eng = acct_txn_counts['txn_count'].sum()

for tier in ENGAGE_ORDER:
    tier_data = acct_txn_counts[acct_txn_counts['tier'] == tier]
    acct_count = len(tier_data)
    txn_sum = tier_data['txn_count'].sum()
    engagement_summary.append({
        'tier': tier,
        'account_count': acct_count,
        'acct_pct': (acct_count / total_accts * 100) if total_accts > 0 else 0,
        'txn_count': txn_sum,
        'txn_pct': (txn_sum / total_txns_eng * 100) if total_txns_eng > 0 else 0,
        'avg_txns': tier_data['txn_count'].mean() if acct_count > 0 else 0,
    })

engagement_df = pd.DataFrame(engagement_summary)

print("Engagement data built.")
for _, row in engagement_df.iterrows():
    print(f"  {row['tier']:>8s}: {row['account_count']:>5,} accounts ({row['acct_pct']:.0f}%), "
          f"{row['txn_count']:>8,} txns ({row['txn_pct']:.1f}%), "
          f"avg {row['avg_txns']:.1f} txns/acct")
