# ============================================
# ics-21-balance-distribution-avg — Avg Bal tier distribution for ICS target-Stat cohort
# ============================================
# Supersedes: ax-19-stat code x balance.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Pair: ics-22-balance-distribution-current uses Curr Bal instead.

print(f"\n📊 ics-21 — Avg Bal distribution for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)
cohort = add_balance_tier(cohort, balance_col='Avg Bal')

# Build tier base with every tier present, in canonical order.
base = (
    pd.DataFrame({'Tier': BALANCE_TIER_ORDER})
      .merge(
          cohort.groupby('Tier')['Avg Bal']
                .agg(Account_Count='count', Total_Balance='sum'),
          on='Tier', how='left'
      )
)
base['Account_Count'] = base['Account_Count'].fillna(0).astype(int)
base['Total_Balance'] = base['Total_Balance'].fillna(0.0)

balance_distribution_avg = base[['Tier', 'Account_Count', 'Total_Balance']].copy()

total_row = pd.DataFrame([{
    'Tier':          'Total',
    'Account_Count': int(balance_distribution_avg['Account_Count'].sum()),
    'Total_Balance': float(balance_distribution_avg['Total_Balance'].sum()),
}])
balance_distribution_avg = pd.concat(
    [balance_distribution_avg, total_row], ignore_index=True
)

for c in ['Account_Count', 'Total_Balance']:
    balance_distribution_avg[c] = pd.to_numeric(
        balance_distribution_avg[c], errors='coerce'
    )

display_formatted(
    balance_distribution_avg,
    f"ICS {STAT_LABEL} — Avg Bal Distribution"
)

_total_bal = float(cohort['Avg Bal'].sum())
_avg_bal   = float(cohort['Avg Bal'].mean()) if len(cohort) else 0.0
print(f"\n✅ Analysis completed")
print(f"   Total ICS {STAT_LABEL} accounts : {len(cohort):,}")
print(f"   Total Avg Balance              : ${_total_bal:,.2f}")
print(f"   Mean Avg Balance               : ${_avg_bal:,.2f}")
