# ============================================
# ics-16-age-by-ics-status — Account Age Range × ICS vs Non-ICS
# ============================================
# Supersedes: ax-15-account age range.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# This is one of the few cells that already compares ICS vs Non-ICS.
# We preserve that lens since it's exactly the direction we want more of.

print("\n📊 ics-16 — Account Age Range, ICS vs Non-ICS...")

# Reference date anchors on the activity window end (not today) so frozen
# reports don't drift month-to-month.
scoped = add_account_age(data)

age_distribution = (
    scoped.groupby(['Age Range', 'ICS Account'])
          .size()
          .unstack(fill_value=0)
)
for _col in ['Yes', 'No']:
    if _col not in age_distribution.columns:
        age_distribution[_col] = 0

age_distribution['Total']      = age_distribution[['Yes', 'No']].sum(axis=1)
age_distribution['ICS %']      = (age_distribution['Yes'] / age_distribution['Total']).round(2)
age_distribution['Non-ICS %']  = (age_distribution['No']  / age_distribution['Total']).round(2)

age_by_ics = (
    age_distribution.reset_index()
                    .rename(columns={'Yes': 'ICS Accounts', 'No': 'Non-ICS Accounts'})
)
age_by_ics['Age Range'] = pd.Categorical(
    age_by_ics['Age Range'], categories=AGE_RANGE_ORDER, ordered=True
)
age_by_ics = age_by_ics.sort_values('Age Range').reset_index(drop=True)

total_ics     = int(age_by_ics['ICS Accounts'].sum())
total_non_ics = int(age_by_ics['Non-ICS Accounts'].sum())
grand_total   = int(age_by_ics['Total'].sum())
total_row = pd.DataFrame({
    'Age Range':        ['Total'],
    'ICS Accounts':     [total_ics],
    'Non-ICS Accounts': [total_non_ics],
    'Total':            [grand_total],
    'ICS %':            [round(total_ics / grand_total, 2)   if grand_total else 0],
    'Non-ICS %':        [round(total_non_ics / grand_total, 2) if grand_total else 0],
})
age_by_ics = pd.concat([age_by_ics, total_row], ignore_index=True)

display_formatted(age_by_ics, "Account Age Range — ICS vs Non-ICS")

print(f"\n✅ Analysis completed")
print(f"   Anchor date (end of window): {last_12_months[-1]}")
