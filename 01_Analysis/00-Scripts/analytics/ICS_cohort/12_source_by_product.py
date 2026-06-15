# ============================================
# ics-12-source-by-product — Product Code × Source cross-tab within ICS
# ============================================
# Supersedes: ax-11-source by prod code  (labeled A[X].10 — dup label).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print("\n📊 ics-12 — Source by Product Code within ICS...")

ics_only = data[data['ICS Account'] == 'Yes'].copy()

prod_source = (
    ics_only.groupby(['Prod Code', 'Source'])
            .size()
            .unstack(fill_value=0)
)
prod_source['Total'] = prod_source.sum(axis=1)

for _col in [c for c in prod_source.columns if c != 'Total']:
    prod_source[f'{_col} %'] = (prod_source[_col] / prod_source['Total']).round(2)

source_by_product = (
    prod_source.reset_index()
               .sort_values('Total', ascending=False)
               .reset_index(drop=True)
)

total_sum = int(source_by_product['Total'].sum())
total_row_data = {'Prod Code': 'Total'}
for _col in source_by_product.columns:
    if _col == 'Prod Code':
        continue
    if '%' in _col:
        _base = _col.replace(' %', '')
        if _base in source_by_product.columns:
            _val = source_by_product[_base].sum()
            total_row_data[_col] = round((_val / total_sum), 2) if total_sum else 0
        else:
            total_row_data[_col] = 0
    else:
        total_row_data[_col] = int(source_by_product[_col].sum())
source_by_product = pd.concat(
    [source_by_product, pd.DataFrame([total_row_data])], ignore_index=True
).fillna(0)

display_formatted(source_by_product, "ICS — Source by Product Code")

print(f"\n✅ Analysis completed")
