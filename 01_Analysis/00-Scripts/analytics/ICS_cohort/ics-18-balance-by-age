# ============================================
# ics-18-balance-by-age — Balance tier × Account Age for ICS target-Stat cohort
# ============================================
# Supersedes: ax-17-balance by age range.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Uses Avg Bal (matches the original). For Current-balance tiers by age,
# copy this cell and pass balance_col='Curr Bal' to add_balance_tier().

print(f"\n📊 ics-18 — Balance tier × Account Age for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)
cohort = add_account_age(cohort)
cohort = add_balance_tier(cohort, balance_col='Avg Bal')

# Build Tier × Age Range pivot with all tiers/ages present in canonical order.
pivot = (
    pd.DataFrame({'Tier': BALANCE_TIER_ORDER})
      .merge(
          cohort.groupby(['Tier', 'Age Range']).size().unstack(fill_value=0),
          on='Tier', how='left'
      )
      .fillna(0)
)

# Keep only age columns that appear in this dataset, in canonical order.
age_cols = [c for c in AGE_RANGE_ORDER if c in pivot.columns]
pivot = pivot[['Tier'] + age_cols]
pivot['Total'] = pivot[age_cols].sum(axis=1)

# Grand-total row.
grand = {'Tier': 'Total'}
for c in age_cols + ['Total']:
    grand[c] = int(pivot[c].sum())
balance_by_age = pd.concat([pivot, pd.DataFrame([grand])], ignore_index=True)

# Force integers for display (no ".00" artifacts).
for c in balance_by_age.columns:
    if c != 'Tier':
        balance_by_age[c] = (
            pd.to_numeric(balance_by_age[c], errors='coerce')
              .fillna(0).astype('int64')
        )

# Rename age columns to " Count" so the styler formats them as integers.
balance_by_age = balance_by_age.rename(
    columns={c: f"{c} Count" for c in age_cols}
)

display_formatted(
    balance_by_age,
    f"ICS {STAT_LABEL} — Balance Tier (Avg Bal) by Account Age"
)

print(f"\n✅ Analysis completed")
print(f"   Total ICS {STAT_LABEL} accounts : {len(cohort):,}")
print(f"   Anchor date (end of window)   : {last_12_months[-1]}")
