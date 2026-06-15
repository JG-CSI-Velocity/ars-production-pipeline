# ============================================
# ics-06-product-mix — Product Code distribution within ICS target-Stat cohort
# ============================================
# Supersedes: ax-5-prod code  (hardcoded letter 'O'; inconsistent label A[X].6).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

import numpy as np

print(f"\n📊 ics-06 — Product Code distribution for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)

# Normalize missing product codes
cohort['Prod Code'] = (
    cohort['Prod Code']
          .replace(['', 'nan', 'NaN', None], np.nan)
          .fillna('Unknown')
)

prod_mix = (
    cohort.groupby('Prod Code', dropna=False)
          .size()
          .rename('Account Count')
          .reset_index()
)

total = int(prod_mix['Account Count'].sum())
prod_mix[f'% of ICS {ICS_STAT_CODE}'] = (
    prod_mix['Account Count'] / total if total else 0.0
)
prod_mix = prod_mix.sort_values('Account Count', ascending=False).reset_index(drop=True)

total_row = pd.DataFrame({
    'Prod Code':                  ['Total'],
    'Account Count':              [total],
    f'% of ICS {ICS_STAT_CODE}':  [1.0 if total else 0.0],
})
prod_mix = pd.concat([prod_mix, total_row], ignore_index=True)

display_formatted(prod_mix, f"ICS {STAT_LABEL} — Product Code Distribution")

print(f"\n✅ Analysis completed")
print(f"   Total ICS {STAT_LABEL} accounts : {total:,}")
