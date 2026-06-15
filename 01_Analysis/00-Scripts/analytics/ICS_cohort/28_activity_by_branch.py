# ============================================
# ics-28-activity-by-branch — Last-N-months activity by Branch
# ============================================
# Supersedes: ax-26-activity by branch.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-28 — Activity by Branch for ICS {STAT_LABEL}...")

cohort = add_l12m_totals(ics_cohort(data))

grp = (
    cohort.groupby('Branch')
          .agg(
              Account_Count    = ('Total L12M Swipes', 'count'),
              Total_Swipes     = ('Total L12M Swipes', 'sum'),
              Avg_Swipes       = ('Total L12M Swipes', 'mean'),
              Median_Swipes    = ('Total L12M Swipes', 'median'),
              Total_Spend      = ('Total L12M Spend',  'sum'),
              Avg_Spend        = ('Total L12M Spend',  'mean'),
              Median_Spend     = ('Total L12M Spend',  'median'),
              Active_Accounts  = ('Active in L12M',    'sum'),
          )
          .reset_index()
)

grp['Pct_Active']      = (grp['Active_Accounts'] / grp['Account_Count']).fillna(0)
grp['Spend_per_Swipe'] = (
    grp['Total_Spend'] / grp['Total_Swipes']
).replace([np.inf, -np.inf], 0).fillna(0)

for _c in ['Account_Count', 'Total_Swipes', 'Active_Accounts']:
    grp[_c] = grp[_c].astype('int64')

activity_by_branch = (
    grp.sort_values('Account_Count', ascending=False)
       .reset_index(drop=True)
)

# Grand total row
tot_accts  = int(activity_by_branch['Account_Count'].sum())
tot_swipes = int(activity_by_branch['Total_Swipes'].sum())
tot_spend  = float(activity_by_branch['Total_Spend'].sum())
tot_active = int(activity_by_branch['Active_Accounts'].sum())
total_row = pd.DataFrame([{
    'Branch':          'Total',
    'Account_Count':   tot_accts,
    'Total_Swipes':    tot_swipes,
    'Avg_Swipes':      (tot_swipes / tot_accts) if tot_accts else 0,
    'Median_Swipes':   float(cohort['Total L12M Swipes'].median()) if len(cohort) else 0,
    'Total_Spend':     tot_spend,
    'Avg_Spend':       (tot_spend / tot_accts) if tot_accts else 0,
    'Median_Spend':    float(cohort['Total L12M Spend'].median()) if len(cohort) else 0,
    'Active_Accounts': tot_active,
    'Pct_Active':      (tot_active / tot_accts) if tot_accts else 0,
    'Spend_per_Swipe': (tot_spend / tot_swipes) if tot_swipes else 0,
}])
activity_by_branch = pd.concat([activity_by_branch, total_row], ignore_index=True)

activity_by_branch = activity_by_branch.rename(columns={
    'Account_Count':   'Account Count',
    'Total_Swipes':    'Total Swipes',
    'Avg_Swipes':      'Avg Swipes per Account',
    'Median_Swipes':   'Median Swipes per Account',
    'Total_Spend':     'Total Spend',
    'Avg_Spend':       'Avg Spend per Account',
    'Median_Spend':    'Median Spend per Account',
    'Active_Accounts': 'Active Accounts',
    'Pct_Active':      '% Active',
    'Spend_per_Swipe': 'Avg Spend per Swipe',
})

display_formatted(activity_by_branch, f"ICS {STAT_LABEL} — Activity by Branch")

print(f"\n✅ Analysis completed")
