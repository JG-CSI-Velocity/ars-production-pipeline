# ============================================
# ics-13-source-by-branch — Branch × Source cross-tab within ICS
# ============================================
# Supersedes: ax-12-source by branch.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print("\n📊 ics-13 — Source by Branch within ICS...")

ics_only = data[data['ICS Account'] == 'Yes'].copy()

branch_source = (
    ics_only.groupby(['Branch', 'Source'])
            .size()
            .unstack(fill_value=0)
)
branch_source['Total'] = branch_source.sum(axis=1)

# Per-row Source shares
for _col in [c for c in branch_source.columns if c != 'Total']:
    branch_source[f'{_col} %'] = (branch_source[_col] / branch_source['Total']).round(2)

# Branch share of overall ICS
total_ics = len(ics_only)
branch_source['Total %'] = (branch_source['Total'] / total_ics).round(2) if total_ics else 0

source_by_branch = (
    branch_source.reset_index()
                 .sort_values('Total', ascending=False)
                 .reset_index(drop=True)
)

total_sum = int(source_by_branch['Total'].sum())
total_row_data = {'Branch': 'Total'}
for _col in source_by_branch.columns:
    if _col == 'Branch':
        continue
    if _col == 'Total %':
        total_row_data[_col] = 1.0
    elif '%' in _col:
        _base = _col.replace(' %', '')
        if _base in source_by_branch.columns:
            _val = source_by_branch[_base].sum()
            total_row_data[_col] = round((_val / total_sum), 2) if total_sum else 0
        else:
            total_row_data[_col] = 0
    else:
        total_row_data[_col] = int(source_by_branch[_col].sum())
source_by_branch = pd.concat(
    [source_by_branch, pd.DataFrame([total_row_data])], ignore_index=True
).fillna(0)

display_formatted(source_by_branch, "ICS — Source by Branch")

print(f"\n✅ Analysis completed")
