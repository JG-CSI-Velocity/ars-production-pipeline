# ============================================
# ics-09-debit-by-branch — Debit coverage x Branch within ICS target-Stat cohort
# ============================================
# Supersedes: ax-8-ics stat code 0 -debit branch  (filename embedded the old
# hardcoded '0'; labeled A[X].7).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-09 — Debit coverage by Branch for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)

branch_debit = (
    cohort.groupby(['Branch', 'Debit?'])
          .size()
          .unstack(fill_value=0)
)
for _col in ['Yes', 'No']:
    if _col not in branch_debit.columns:
        branch_debit[_col] = 0

branch_debit['Total']        = branch_debit[['Yes', 'No']].sum(axis=1)
branch_debit['% with Debit'] = (
    branch_debit['Yes'] / branch_debit['Total'].replace({0: pd.NA})
)

debit_by_branch = (
    branch_debit.reset_index()
                .sort_values('Total', ascending=False)
                .reset_index(drop=True)
)

total_yes = int(debit_by_branch['Yes'].sum())
total_no  = int(debit_by_branch['No'].sum())
total_all = int(debit_by_branch['Total'].sum())
total_row = pd.DataFrame({
    'Branch':        ['Total'],
    'No':            [total_no],
    'Yes':           [total_yes],
    'Total':         [total_all],
    '% with Debit':  [(total_yes / total_all) if total_all else 0],
})
debit_by_branch = pd.concat([debit_by_branch, total_row], ignore_index=True).fillna(0)

display_formatted(debit_by_branch, f"ICS {STAT_LABEL} — Debit Coverage by Branch")

print(f"\n✅ Analysis completed")
