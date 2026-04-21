# ============================================
# ics-22-balance-distribution-current — Curr Bal tier distribution for ICS target-Stat cohort
# ============================================
# Supersedes: ax-20-stat code -current bal.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Pair: ics-21-balance-distribution-avg uses Avg Bal instead.
# This cell adds % of accounts and % of balance columns that ics-21 omits.

print(f"\n📊 ics-22 — Curr Bal distribution for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)
cohort = add_balance_tier(cohort, balance_col='Curr Bal')

dist = (
    cohort.groupby('Tier')['Curr Bal']
          .agg(Account_Count='count', Total_Balance='sum')
          .reset_index()
)
dist['Tier'] = pd.Categorical(dist['Tier'], categories=BALANCE_TIER_ORDER, ordered=True)
dist = dist.sort_values('Tier').reset_index(drop=True)

total_accounts = len(cohort)
total_balance  = float(cohort['Curr Bal'].sum())

dist['Pct_Accounts'] = (dist['Account_Count'] / total_accounts) if total_accounts else 0.0
dist['Pct_Balance']  = (dist['Total_Balance'] / total_balance)  if total_balance  else 0.0

total_row = pd.DataFrame({
    'Tier':          ['Total'],
    'Account_Count': [int(dist['Account_Count'].sum())],
    'Total_Balance': [float(dist['Total_Balance'].sum())],
    'Pct_Accounts':  [1.0 if total_accounts else 0.0],
    'Pct_Balance':   [1.0 if total_balance  else 0.0],
})
balance_distribution_current = pd.concat([dist, total_row], ignore_index=True)

for c in ['Account_Count', 'Total_Balance']:
    balance_distribution_current[c] = (
        pd.to_numeric(balance_distribution_current[c], errors='coerce')
          .fillna(0).astype(int)
    )
for c in ['Pct_Accounts', 'Pct_Balance']:
    balance_distribution_current[c] = pd.to_numeric(
        balance_distribution_current[c], errors='coerce'
    )

balance_distribution_current = balance_distribution_current.rename(columns={
    'Pct_Accounts': 'Percent Accounts',
    'Pct_Balance':  'Percent Balance',
})

display_formatted(
    balance_distribution_current,
    f"ICS {STAT_LABEL} — Curr Bal Distribution"
)

_avg_bal = float(cohort['Curr Bal'].mean()) if total_accounts else 0.0
print(f"\n✅ Analysis completed")
print(f"   Total ICS {STAT_LABEL} accounts : {total_accounts:,}")
print(f"   Total Current Balance          : ${total_balance:,.2f}")
print(f"   Mean Current Balance           : ${_avg_bal:,.2f}")
