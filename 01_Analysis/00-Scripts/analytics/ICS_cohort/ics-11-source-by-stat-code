# ============================================
# ics-11-source-by-stat-code — Stat Code × Source cross-tab within ICS
# ============================================
# Supersedes: ax-10-stat code by source  (labeled A[X].10 but frame was named
# ax9_*; bespoke Source blank-handling now in ics-01).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print("\n📊 ics-11 — Stat Code by Source within ICS...")

ics_only = data[data['ICS Account'] == 'Yes'].copy()

stat_source = (
    ics_only.groupby(['Stat Code', 'Source'])
            .size()
            .unstack(fill_value=0)
)
stat_source['Total'] = stat_source.sum(axis=1)

# Per-row share for each Source
for _col in [c for c in stat_source.columns if c != 'Total']:
    stat_source[f'{_col} %'] = (stat_source[_col] / stat_source['Total']).round(2)

source_by_stat = (
    stat_source.reset_index()
               .sort_values('Total', ascending=False)
               .reset_index(drop=True)
)

# Totals row
total_sum = int(source_by_stat['Total'].sum())
total_row_data = {'Stat Code': 'Total'}
for _col in source_by_stat.columns:
    if _col == 'Stat Code':
        continue
    if '%' in _col:
        _base = _col.replace(' %', '')
        if _base in source_by_stat.columns:
            _val = source_by_stat[_base].sum()
            total_row_data[_col] = round((_val / total_sum), 2) if total_sum else 0
        else:
            total_row_data[_col] = 0
    else:
        total_row_data[_col] = int(source_by_stat[_col].sum())
source_by_stat = pd.concat(
    [source_by_stat, pd.DataFrame([total_row_data])], ignore_index=True
).fillna(0)

display_formatted(source_by_stat, "ICS — Stat Code by Source")

print(f"\n✅ Analysis completed")
