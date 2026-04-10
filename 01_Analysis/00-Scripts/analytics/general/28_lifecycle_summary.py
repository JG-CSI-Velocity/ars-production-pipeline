# ===========================================================================
# LIFECYCLE SUMMARY: Full Account Age Breakdown (Conference Edition)
# ===========================================================================
# Styled table + findings + callouts.
# All metrics labeled with time periods. TTM-only for activation metrics.

lc_full = lifecycle_summary.copy()
lc_full['acct_age_band'] = pd.Categorical(
    lc_full['acct_age_band'], categories=ACCT_AGE_ORDER, ordered=True
)
lc_full = lc_full.sort_values('acct_age_band')

# Build display table
lc_table = lc_full[['acct_age_band', 'account_count', 'avg_txns_per_month',
                     'avg_oddd_12mo', 'avg_txn_amount',
                     'median_days_to_first', 'pct_activated_30d',
                     'pct_very_high']].copy()

lc_table.columns = [
    'Account Age',
    'Accounts',
    'Txns / Month',
    '12mo Spend / Acct',
    'Avg $ per Txn',
    'Days to 1st Txn (TTM)',
    '% Active <30d (TTM)',
    '% Top Spenders',
]

styled = (
    lc_table.style
    .hide(axis='index')
    .format({
        'Accounts': '{:,.0f}',
        'Txns / Month': '{:.1f}',
        '12mo Spend / Acct': '${:,.0f}',
        'Avg $ per Txn': '${:,.0f}',
        'Days to 1st Txn (TTM)': '{:.0f}',
        '% Active <30d (TTM)': '{:.0f}%',
        '% Top Spenders': '{:.1f}%',
    }, na_rep='--')
    .set_properties(**{
        'font-size': '15px',
        'font-weight': 'bold',
        'text-align': 'center',
        'border': '1px solid #E9ECEF',
        'padding': '10px 14px',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '16px'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('padding', '10px 12px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '26px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '6px'),
            ('line-height', '1.4'),
        ]},
    ])
    .set_caption("Account Lifecycle Scorecard")
    .bar(subset=['Accounts'], color=GEN_COLORS['info'], vmin=0)
    .bar(subset=['% Top Spenders'], color=GEN_COLORS['accent'], vmin=0, vmax=100)
)

display(styled)

# Definitions line below table
print(f"\n    Column definitions:")
print(f"      Txns / Month = avg monthly transaction rate per account ({DATASET_LABEL})")
print(f"      12mo Spend / Acct = ODDD trailing 12-month total spend, averaged per account")
print(f"      Avg $ per Txn = mean transaction amount per account ({DATASET_LABEL})")
print(f"      Days to 1st Txn = median days from open to first card swipe (TTM accounts only)")
print(f"      % Top Spenders = ODDD Total Spend > ${q75:,.0f} (top 25% of all matched accounts)")

# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("  LIFECYCLE FINDINGS")
print("=" * 80)

# Newest cohort activation (TTM only)
newest = lc_full[lc_full['acct_age_band'] == '1-90d']
if len(newest) > 0:
    n = newest.iloc[0]
    med_days = n.get('median_days_to_first', None)
    if pd.notna(med_days):
        print(f"  1. Newest accounts (1-90d): {n['account_count']:,.0f} accounts, "
              f"median {med_days:.0f} days to first transaction")
    else:
        print(f"  1. Newest accounts (1-90d): {n['account_count']:,.0f} accounts")

# Most active band (by monthly txn rate)
most_active = lc_full.loc[lc_full['avg_txns_per_month'].idxmax()]
print(f"  2. Most active band: {most_active['acct_age_band']} "
      f"({most_active['avg_txns_per_month']:.1f} txns/month per account)")

# Highest spend band (ODDD 12mo)
highest_spend = lc_full.loc[lc_full['avg_oddd_12mo'].idxmax()]
print(f"  3. Highest 12mo spend: {highest_spend['acct_age_band']} "
      f"(${highest_spend['avg_oddd_12mo']:,.0f} avg per account, trailing 12 months)")

# New account risk
new_bands = lifecycle_matched[lifecycle_matched['acct_age_band'].isin(['1-90d', '91-180d', '181-365d'])]
if len(new_bands) > 0:
    new_low = (new_bands['spend_tier'] == 'Low').sum()
    new_total = len(new_bands)
    pct_low = new_low / new_total * 100
    print(f"  4. New accounts (< 1yr) in Low spend tier (< ${q25:,.0f} total): "
          f"{pct_low:.0f}% -- onboarding engagement opportunity")

# TTM activation speed
ttm_data = lifecycle_matched[lifecycle_matched['is_ttm'] & lifecycle_matched['days_to_first_txn'].notna()]
if len(ttm_data) > 0:
    ttm_median = ttm_data['days_to_first_txn'].median()
    pct_30d = (ttm_data['days_to_first_txn'] <= 30).sum() / len(ttm_data) * 100
    print(f"  5. TTM activation: median {ttm_median:.0f} days, "
          f"{pct_30d:.0f}% within 30 days ({len(ttm_data):,} TTM accounts)")

print(f"\n  Spend tier thresholds (ODDD Total Spend quartiles):")
print(f"    Low:       < ${q25:,.0f}")
print(f"    Medium:    ${q25:,.0f} - ${q50:,.0f}")
print(f"    High:      ${q50:,.0f} - ${q75:,.0f}")
print(f"    Very High: > ${q75:,.0f}  (= '% Top Spenders' in table)")
print("=" * 80)
