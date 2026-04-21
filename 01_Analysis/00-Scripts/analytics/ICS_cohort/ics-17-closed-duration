# ============================================
# ics-17-closed-duration — How long closed ICS accounts stayed open
# ============================================
# Supersedes: ax-16-closed accounts.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Closed-only view. For open-vs-closed comparison see ics-18 (coming next).

print("\n📊 ics-17 — Closed ICS account duration analysis...")

ics_accounts = data[data['ICS Account'] == 'Yes'].copy()
ics_open     = ics_accounts[ics_accounts['Date Closed'].isna()]
ics_closed   = ics_accounts[ics_accounts['Date Closed'].notna()].copy()

ics_closed['Days Open']       = (ics_closed['Date Closed'] - ics_closed['Date Opened']).dt.days
ics_closed['Duration Range']  = ics_closed['Days Open'].map(_age_bucket)

# Present all buckets even if empty, in canonical order.
closed_duration = (
    pd.DataFrame({'Duration Range': AGE_RANGE_ORDER})
      .merge(
          ics_closed['Duration Range'].value_counts().rename('Closed Count'),
          on='Duration Range', how='left'
      )
)
closed_duration['Closed Count'] = closed_duration['Closed Count'].fillna(0).astype(int)

den = len(ics_closed)
closed_duration['% of Closed ICS'] = (
    closed_duration['Closed Count'] / den if den else 0.0
)

# Rename duration label to a neutral header (keeps display formatter happy).
closed_duration = closed_duration.rename(columns={'Duration Range': 'Label'})

# Totals block: Total Closed / Total Open / Grand Total
total_block = pd.DataFrame({
    'Label':            ['Total Closed', 'Total Open', 'Grand Total'],
    'Closed Count':     [len(ics_closed), len(ics_open), len(ics_accounts)],
    '% of Closed ICS':  [1.0, pd.NA, pd.NA],
})
closed_duration = pd.concat([closed_duration, total_block], ignore_index=True)

closed_duration['Closed Count']    = pd.to_numeric(closed_duration['Closed Count'],    errors='coerce')
closed_duration['% of Closed ICS'] = pd.to_numeric(closed_duration['% of Closed ICS'], errors='coerce')

display_formatted(closed_duration, "ICS Accounts — Closed Duration")

total = len(ics_accounts)
print(f"\n✅ Analysis completed")
print(f"   Total ICS       : {total:,}")
print(f"   Currently Open  : {len(ics_open):,} ({(len(ics_open)/total if total else 0):.2%})")
print(f"   Closed          : {len(ics_closed):,} ({(len(ics_closed)/total if total else 0):.2%})")
