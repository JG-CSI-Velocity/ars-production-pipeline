# ============================================
# ics-08-debit-by-product — Debit coverage x Product Code within ICS target-Stat cohort
# ============================================
# Supersedes: ax-7-debit-prod code  (filter hardcoded to digit '0'; labeled A[X].6).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-08 — Debit coverage by Product Code for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)

# Count matrix: Prod Code rows x Debit? columns (Yes/No), plus Total + %
prod_debit = (
    cohort.groupby(['Prod Code', 'Debit?'])
          .size()
          .unstack(fill_value=0)
)
for _col in ['Yes', 'No']:
    if _col not in prod_debit.columns:
        prod_debit[_col] = 0

prod_debit['Total']        = prod_debit[['Yes', 'No']].sum(axis=1)
prod_debit['% with Debit'] = (
    prod_debit['Yes'] / prod_debit['Total'].replace({0: pd.NA})
)

debit_by_product = (
    prod_debit.reset_index()
              .sort_values('% with Debit', ascending=False, na_position='last')
              .reset_index(drop=True)
)

total_yes   = int(debit_by_product['Yes'].sum())
total_no    = int(debit_by_product['No'].sum())
total_all   = int(debit_by_product['Total'].sum())
total_row = pd.DataFrame({
    'Prod Code':     ['Total'],
    'No':            [total_no],
    'Yes':           [total_yes],
    'Total':         [total_all],
    '% with Debit':  [(total_yes / total_all) if total_all else 0],
})
debit_by_product = pd.concat([debit_by_product, total_row], ignore_index=True).fillna(0)

display_formatted(debit_by_product, f"ICS {STAT_LABEL} — Debit Coverage by Product Code")

print(f"\n✅ Analysis completed")
