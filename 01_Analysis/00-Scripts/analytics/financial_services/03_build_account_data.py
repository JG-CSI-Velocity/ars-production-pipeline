# ===========================================================================
# CELL 3: BUILD ACCOUNT-LEVEL DATA
# ===========================================================================
# Produces: all_financial_accounts (dict: category -> account_summary DataFrame)

all_financial_accounts = {}

search_column = 'merchant_consolidated' if 'merchant_consolidated' in combined_df.columns else 'merchant_name'

for category, data in financial_services_data.items():
    category_trans = data['transactions']

    account_summary = category_trans.groupby('primary_account_num').agg({
        'amount': ['sum', 'count', 'mean'],
        'transaction_date': ['min', 'max'],
        search_column: lambda x: ' | '.join(x.unique()[:3])
    }).round(2)

    account_summary.columns = [
        'Total Spend', 'Transaction Count', 'Avg Transaction',
        'First Transaction', 'Last Transaction', 'Merchants'
    ]
    account_summary = account_summary.sort_values('Transaction Count', ascending=False)

    # Recency (anchored to dataset end date, not today)
    account_summary['Recency_Days'] = (
        DATASET_END - account_summary['Last Transaction']
    ).dt.days

    # Recency tier
    account_summary['Recency_Tier'] = pd.cut(
        account_summary['Recency_Days'],
        bins=[-1, 30, 90, 365, 99999],
        labels=['Active (0-30d)', 'Cooling (30-90d)', 'Dormant (90-365d)', 'Lapsed (365d+)']
    )

    all_financial_accounts[category] = account_summary

acct_rows = []
for cat, df in all_financial_accounts.items():
    active = len(df[df['Recency_Days'] <= 30])
    acct_rows.append({
        'Category': cat,
        'Accounts': len(df),
        'Active (30d)': active,
    })

acct_build_df = pd.DataFrame(acct_rows).sort_values('Accounts', ascending=False)

print(f"Account data built: {len(all_financial_accounts)} categories, {acct_build_df['Accounts'].sum():,} total accounts\n")
display(acct_build_df.style.hide(axis='index').set_properties(**{
    'text-align': 'left',
    'font-weight': 'bold'
}, subset=['Category']).set_properties(**{
    'text-align': 'center'
}, subset=['Accounts', 'Active (30d)']).format({
    'Accounts': '{:,}',
    'Active (30d)': '{:,}'
}))
