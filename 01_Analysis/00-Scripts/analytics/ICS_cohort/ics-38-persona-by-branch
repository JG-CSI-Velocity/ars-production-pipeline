# ============================================
# ics-38-persona-by-branch — Branch performance by activation persona (percentages)
# ============================================
# Supersedes: ax-36-activation branch performance.
# Depends on: ics-37-activation-personas  (consumes `ics_cohort_personas` for the Category column).

print(f"\n📊 ics-38 — Branch performance by activation persona for ICS {STAT_LABEL}...")

try:
    _src = ics_cohort_personas
except NameError as e:
    raise RuntimeError(
        "`ics_cohort_personas` not found — run ics-37-activation-personas first."
    ) from e

_ALL_CATS = [
    'Fast Activator', 'Slow Burner', 'One and Done',
    'Never Activator', 'Too New (<3 Months)'
]

branch_persona = (
    _src.groupby(['Branch', 'Category'])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=_ALL_CATS, fill_value=0)
)
branch_persona['Total'] = branch_persona[_ALL_CATS].sum(axis=1)

for _c in _ALL_CATS:
    branch_persona[f'{_c} %'] = (branch_persona[_c] / branch_persona['Total']).round(2)

# "Success Rate %" = Fast Activator / categorized (excludes Too New)
_categorized_cats = [c for c in _ALL_CATS if c != 'Too New (<3 Months)']
_categorized_total = branch_persona[_categorized_cats].sum(axis=1)
branch_persona['Success Rate %'] = (
    (branch_persona['Fast Activator'] / _categorized_total)
    .where(_categorized_total > 0, 0)
    .round(2)
)

persona_by_branch = (
    branch_persona.reset_index()[
        ['Branch', 'Total']
        + [f'{c} %' for c in _ALL_CATS]
        + ['Success Rate %']
    ]
    .fillna(0)
    .sort_values('Total', ascending=False)
    .reset_index(drop=True)
)

# Overall totals row
_overall = {c: int(branch_persona[c].sum()) for c in _ALL_CATS}
_overall_total = sum(_overall.values())
_overall_categorized = sum(_overall[c] for c in _categorized_cats)
_overall_success = (
    round(_overall['Fast Activator'] / _overall_categorized, 2)
    if _overall_categorized else 0
)

_total_row = {'Branch': 'Total', 'Total': _overall_total}
for _c in _ALL_CATS:
    _total_row[f'{_c} %'] = (
        round(_overall[_c] / _overall_total, 2) if _overall_total else 0
    )
_total_row['Success Rate %'] = _overall_success
persona_by_branch = pd.concat(
    [persona_by_branch, pd.DataFrame([_total_row])], ignore_index=True
).fillna(0)

display_formatted(
    persona_by_branch,
    f"ICS {STAT_LABEL} — Branch Performance by Persona (Percentages)"
)

print(f"\n✅ Analysis completed")
print(f"   Branches analyzed   : {len(persona_by_branch) - 1}")
if len(persona_by_branch) > 1:
    print(f"   Largest branch      : {persona_by_branch.iloc[0]['Branch']} "
          f"({int(persona_by_branch.iloc[0]['Total'])} accounts)")
