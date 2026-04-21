# ============================================
# ics-37-activation-personas — Fast / Slow / One-and-Done / Never / Too New classification
# ============================================
# Supersedes: ax-35- persona activation milestones  (34-activation personas dropped — earlier draft).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Produces `ics_cohort_personas` — attaches a Category column to each account
# so downstream cells (ics-38) can slice by persona.

print(f"\n📊 ics-37 — Activation personas for ICS {STAT_LABEL} debit cohort...")

cohort = ics_cohort_debit(data)
cohort = add_opening_month(cohort)
cohort = apply_cohort_start(cohort).copy()

def _classify(row):
    _opening_dt = pd.to_datetime(row['Opening Month'])
    _m3_tag     = (_opening_dt + pd.DateOffset(months=2)).strftime('%b%y')
    _m1_tag     = _opening_dt.strftime('%b%y')
    _m1_col     = f"{_m1_tag} Swipes"
    _m3_col     = f"{_m3_tag} Swipes"

    # If the cohort is so new that its M3 month hasn't happened yet in the data
    # window → classify as Too New. Use last_12_months as the "data available" window.
    if _m3_tag not in last_12_months:
        return 'Too New (<3 Months)'

    _m1 = float(row[_m1_col]) if _m1_col in row.index and pd.notna(row[_m1_col]) else 0.0
    _m3 = float(row[_m3_col]) if _m3_col in row.index and pd.notna(row[_m3_col]) else 0.0

    if   _m1 > 0 and _m3 > 0:   return 'Fast Activator'
    elif _m1 == 0 and _m3 > 0:  return 'Slow Burner'
    elif _m1 > 0 and _m3 == 0:  return 'One and Done'
    else:                       return 'Never Activator'

cohort['Category'] = cohort.apply(_classify, axis=1)
ics_cohort_personas = cohort   # expose for ics-38

_CATEGORY_ORDER = [
    'Fast Activator', 'Slow Burner', 'One and Done',
    'Never Activator', 'Too New (<3 Months)'
]

activation_personas = (
    cohort['Category']
          .value_counts()
          .reindex(_CATEGORY_ORDER, fill_value=0)
          .reset_index()
)
activation_personas.columns = ['Category', 'Account Count']
_total = int(activation_personas['Account Count'].sum())
activation_personas['% of Total'] = (activation_personas['Account Count'] / _total) if _total else 0

total_row = pd.DataFrame([{
    'Category':      'Total',
    'Account Count': _total,
    '% of Total':    1.0 if _total else 0.0,
}])
activation_personas = pd.concat([activation_personas, total_row], ignore_index=True)

display_formatted(
    activation_personas,
    f"ICS {STAT_LABEL} — Activation Personas"
)

print(f"\n{'=' * 72}")
print(f"📊 ICS {STAT_LABEL} — ACTIVATION PERSONA SUMMARY")
print(f"{'=' * 72}")
print(f"   Accounts Classified : {_total:,}")
for _cat in _CATEGORY_ORDER:
    _n = int(cohort['Category'].eq(_cat).sum())
    if _n:
        print(f"   {_cat:<22}: {_n:>6,}  ({_n / _total:.1%})")

print(f"\n✅ Analysis completed")
