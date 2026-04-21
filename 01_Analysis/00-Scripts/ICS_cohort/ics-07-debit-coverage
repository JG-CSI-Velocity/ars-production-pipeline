# ============================================
# ics-07-debit-coverage — Debit card coverage within ICS target-Stat cohort
# ============================================
# Supersedes: ax-6-ics-debit flat  (filter hardcoded to digit '0'; comment
# said "LETTER 'O'" — classic O-vs-0 bug).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-07 — Debit coverage for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)

debit_coverage = (
    cohort['Debit?']
          .value_counts()
          .reindex(['Yes', 'No'], fill_value=0)
          .reset_index()
)
debit_coverage.columns = ['Debit Card', 'Count']

den = len(cohort)
debit_coverage[f'% of ICS {ICS_STAT_CODE}'] = (
    debit_coverage['Count'] / den if den else 0
)

total_row = pd.DataFrame({
    'Debit Card':                 ['Total'],
    'Count':                      [int(debit_coverage['Count'].sum())],
    f'% of ICS {ICS_STAT_CODE}':  [1.0 if den else 0.0],
})
debit_coverage = pd.concat([debit_coverage, total_row], ignore_index=True).fillna(0)

display_formatted(debit_coverage, f"ICS {STAT_LABEL} — Debit Card Coverage")

print(f"\n✅ Analysis completed")
print(f"   ICS {STAT_LABEL} accounts : {den:,}")
print(f"   With Debit              : {int((cohort['Debit?'] == 'Yes').sum()):,}")
print(f"   Without Debit           : {int((cohort['Debit?'] == 'No').sum()):,}")
