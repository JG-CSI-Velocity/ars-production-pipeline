# ============================================
# ics-25-activity-summary — Last-N-months activity KPI card for ICS target-Stat cohort
# ============================================
# Supersedes: ax-23-L12-spend-swipe.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-25 — Activity summary for ICS {STAT_LABEL} "
      f"({last_12_months[0]} … {last_12_months[-1]})...")

cohort = add_l12m_totals(ics_cohort(data))

cohort['Avg Spend per Swipe'] = (
    cohort['Total L12M Spend']
    / cohort['Total L12M Swipes'].replace({0: np.nan})
).fillna(0)

# Headline numbers
total_accts    = len(cohort)
active_accts   = int(cohort['Active in L12M'].sum())
inactive_accts = total_accts - active_accts

total_swipes = int(cohort['Total L12M Swipes'].sum())
total_spend  = float(cohort['Total L12M Spend'].sum())

avg_swipes_all    = float(cohort['Total L12M Swipes'].mean()) if total_accts else 0
avg_spend_all     = float(cohort['Total L12M Spend'].mean())  if total_accts else 0
avg_swipes_active = float(cohort.loc[cohort['Active in L12M'], 'Total L12M Swipes'].mean()) if active_accts else 0
avg_spend_active  = float(cohort.loc[cohort['Active in L12M'], 'Total L12M Spend'].mean())  if active_accts else 0
avg_spend_per_sw  = (total_spend / total_swipes) if total_swipes else 0

avg_bal_all    = float(cohort['Curr Bal'].mean()) if total_accts else 0
avg_bal_active = float(cohort.loc[cohort['Active in L12M'], 'Curr Bal'].mean()) if active_accts else 0

activity_summary = pd.DataFrame({
    'Metric': [
        'Total Accounts',
        'Accounts with Swipes',
        'Accounts with No Swipes',
        '% Active',
        'Avg Current Balance (All Accts)',
        'Avg Current Balance (Active Accts)',
        'Total Swipes (All Accts)',
        'Total Spend (All Accts)',
        'Avg Swipes per Acct',
        'Avg Spend per Acct',
        'Avg Swipes per Active Acct',
        'Avg Spend per Active Acct',
        'Avg Spend per Swipe',
    ],
    'Value': [
        f"{total_accts:,}",
        f"{active_accts:,}",
        f"{inactive_accts:,}",
        f"{(active_accts / total_accts):.1%}" if total_accts else "0.0%",
        f"${avg_bal_all:,.2f}",
        f"${avg_bal_active:,.2f}",
        f"{total_swipes:,}",
        f"${total_spend:,.2f}",
        f"{avg_swipes_all:.0f}",
        f"${avg_spend_all:,.2f}",
        f"{avg_swipes_active:.0f}",
        f"${avg_spend_active:,.2f}",
        f"${avg_spend_per_sw:,.2f}",
    ],
})

display_formatted(
    activity_summary,
    f"ICS {STAT_LABEL} — Activity Summary ({last_12_months[0]} … {last_12_months[-1]})"
)

print(f"\n✅ Analysis completed")
print(f"   Total Accounts : {total_accts:,}")
print(f"   Active Rate    : {(active_accts / total_accts) if total_accts else 0:.1%}")
print(f"   Total Swipes   : {total_swipes:,}")
print(f"   Total Spend    : ${total_spend:,.2f}")
