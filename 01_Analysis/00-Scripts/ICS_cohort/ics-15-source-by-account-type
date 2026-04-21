# ============================================
# ics-15-source-by-account-type — Account Type × Source cross-tab within ICS
# ============================================
# Supersedes: ax-14-p vs b.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Same as before, but appends two columns at the right edge so you can
# see the at-target-Stat cohort alongside the All-ICS totals — without
# exploding every Source column into a (All, Stat O) pair.

print(f"\n📊 ics-15 — Source by Account Type: All ICS + at {STAT_LABEL} totals...")

ics_only = data[data['ICS Account'] == 'Yes'].copy()
ics_only['Account Type'] = ics_only['Business?'].map(
    {'Yes': 'Business', 'No': 'Personal'}
)

# All-ICS pivot (Account Type rows × Source cols, plus Total + per-Source %)
type_source = (
    ics_only.groupby(['Account Type', 'Source'])
            .size()
            .unstack(fill_value=0)
)
type_source['Total'] = type_source.sum(axis=1)
for _col in [c for c in type_source.columns if c != 'Total']:
    type_source[f'{_col} %'] = (type_source[_col] / type_source['Total']).round(2)
source_by_account_type = type_source.reset_index()

# At-target-Stat cohort: just per-Account-Type totals (don't explode Sources)
target_counts = (
    ics_cohort(data)
        .assign(_AT=lambda d: d['Business?'].map({'Yes': 'Business', 'No': 'Personal'}))
        ['_AT']
        .value_counts()
        .reindex(['Personal', 'Business'], fill_value=0)
)
_target_total = int(target_counts.sum())

source_by_account_type[f'At {STAT_LABEL}']   = source_by_account_type['Account Type'].map(
    target_counts.to_dict()
).fillna(0).astype(int)
source_by_account_type[f'At {STAT_LABEL} %'] = (
    source_by_account_type[f'At {STAT_LABEL}'] / _target_total if _target_total else 0
)

# Totals row.
total_sum = int(source_by_account_type['Total'].sum())
total_row_data = {'Account Type': 'Total'}
for _col in source_by_account_type.columns:
    if _col == 'Account Type':
        continue
    if _col == f'At {STAT_LABEL}':
        total_row_data[_col] = _target_total
    elif _col == f'At {STAT_LABEL} %':
        total_row_data[_col] = 1.0 if _target_total else 0
    elif '%' in _col:
        _base = _col.replace(' %', '')
        if _base in source_by_account_type.columns:
            _val = source_by_account_type[_base].sum()
            total_row_data[_col] = round((_val / total_sum), 2) if total_sum else 0
        else:
            total_row_data[_col] = 0
    else:
        total_row_data[_col] = int(source_by_account_type[_col].sum())

source_by_account_type = pd.concat(
    [source_by_account_type, pd.DataFrame([total_row_data])], ignore_index=True
).fillna(0)

display_formatted(
    source_by_account_type,
    f"ICS — Source by Account Type (with At {STAT_LABEL} totals)"
)

print(f"\n✅ Analysis completed")
print(f"   All ICS         : {total_sum:,}")
print(f"   At {STAT_LABEL} : {_target_total:,}")
