# ============================================
# ics-23-age-distribution-target — Account Age distribution for ICS target-Stat cohort
# ============================================
# Supersedes: ax-21-stat code age distro.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Sibling of ics-16 (which compares ICS vs Non-ICS on the same buckets).
# This one is the single-cohort target-Stat view.

print(f"\n📊 ics-23 — Age distribution for ICS {STAT_LABEL}...")

cohort = add_account_age(ics_cohort(data))

age_dist = (
    cohort['Age Range']
          .value_counts()
          .reindex(AGE_RANGE_ORDER, fill_value=0)
          .reset_index()
)
age_dist.columns = ['Age Range', 'Account Count']

den = int(age_dist['Account Count'].sum())
age_dist['% of Total'] = (age_dist['Account Count'] / den) if den else 0.0

total_row = pd.DataFrame({
    'Age Range':     ['Total'],
    'Account Count': [den],
    '% of Total':    [1.0 if den else 0.0],
})
age_distribution_target = pd.concat([age_dist, total_row], ignore_index=True)

display_formatted(
    age_distribution_target,
    f"ICS {STAT_LABEL} — Account Age Distribution"
)

print(f"\n✅ Analysis completed")
print(f"   Total ICS {STAT_LABEL} accounts : {den:,}")
print(f"   Anchor date (end of window)   : {ACTIVITY_END_DATE.date()}")
