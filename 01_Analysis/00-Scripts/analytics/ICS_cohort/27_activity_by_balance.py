# ============================================
# ics-27-activity-by-balance — Last-N-months activity by Curr Bal tier
# ============================================
# Supersedes: ax-25-activity by balance.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-27 — Activity by Curr Bal tier for ICS {STAT_LABEL}...")

cohort = add_l12m_totals(ics_cohort(data))
cohort = add_balance_tier(cohort, balance_col='Curr Bal')

grp = (
    cohort.groupby('Tier', dropna=False)
          .agg(
              Account_Count   = ('Total L12M Swipes', 'count'),
              Total_Swipes    = ('Total L12M Swipes', 'sum'),
              Avg_Swipes_raw  = ('Total L12M Swipes', 'mean'),
              Median_Swipes   = ('Total L12M Swipes', 'median'),
              Total_Spend     = ('Total L12M Spend',  'sum'),
              Avg_Spend       = ('Total L12M Spend',  'mean'),
              Median_Spend    = ('Total L12M Spend',  'median'),
              Active_Accounts = ('Active in L12M',    'sum'),
          )
          .reset_index()
)

grp['Tier'] = pd.Categorical(grp['Tier'], categories=BALANCE_TIER_ORDER, ordered=True)
grp = grp.sort_values('Tier').reset_index(drop=True)

# Derived metrics
grp['Pct_Active']      = (grp['Active_Accounts'] / grp['Account_Count']).fillna(0)
grp['Spend_per_Swipe'] = (
    grp['Total_Spend'] / grp['Total_Swipes']
).replace([np.inf, -np.inf], 0).fillna(0)

# Whole-number Avg/Median Swipes per user preference
grp['Avg_Swipes']    = grp['Avg_Swipes_raw'].round(0).astype('int64')
grp['Median_Swipes'] = pd.to_numeric(grp['Median_Swipes'], errors='coerce').round(0).fillna(0).astype('int64')
grp['Account_Count']   = grp['Account_Count'].astype('int64')
grp['Total_Swipes']    = grp['Total_Swipes'].astype('int64')
grp['Active_Accounts'] = grp['Active_Accounts'].astype('int64')

# Grand total row
tot_accts  = int(grp['Account_Count'].sum())
tot_swipes = int(grp['Total_Swipes'].sum())
tot_spend  = float(grp['Total_Spend'].sum())

total_row = pd.DataFrame([{
    'Tier':            'Total',
    'Account_Count':   tot_accts,
    'Total_Swipes':    tot_swipes,
    'Avg_Swipes_raw':  (tot_swipes / tot_accts) if tot_accts else 0,
    'Median_Swipes':   int(cohort['Total L12M Swipes'].median()) if len(cohort) else 0,
    'Total_Spend':     tot_spend,
    'Avg_Spend':       (tot_spend / tot_accts) if tot_accts else 0,
    'Median_Spend':    float(cohort['Total L12M Spend'].median()) if len(cohort) else 0,
    'Active_Accounts': int(grp['Active_Accounts'].sum()),
    'Pct_Active':      (grp['Active_Accounts'].sum() / tot_accts) if tot_accts else 0,
    'Spend_per_Swipe': (tot_spend / tot_swipes) if tot_swipes else 0,
}])
grp = pd.concat([grp, total_row], ignore_index=True)
grp.loc[grp['Tier'] == 'Total', 'Avg_Swipes'] = (
    grp.loc[grp['Tier'] == 'Total', 'Avg_Swipes_raw'].round(0).astype('int64')
)

activity_by_balance = (
    grp[['Tier',
         'Account_Count', 'Total_Swipes', 'Avg_Swipes', 'Median_Swipes',
         'Total_Spend',  'Avg_Spend',    'Median_Spend',
         'Active_Accounts', 'Pct_Active', 'Spend_per_Swipe']]
      .rename(columns={
          'Account_Count':    'Account Count',
          'Total_Swipes':     'Total Swipes',
          'Avg_Swipes':       'Avg Swipes per Acct',
          'Median_Swipes':    'Median Swipes per Acct',
          'Total_Spend':      'Total Spend',
          'Avg_Spend':        'Avg Spend per Acct',
          'Median_Spend':     'Median Spend per Acct',
          'Active_Accounts':  'Active Accounts',
          'Pct_Active':       '% Active',
          'Spend_per_Swipe':  'Avg Spend per Swipe',
      })
)

display_formatted(
    activity_by_balance,
    f"ICS {STAT_LABEL} — Activity by Balance Tier (Curr Bal)"
)

print(f"\n✅ Analysis completed")
