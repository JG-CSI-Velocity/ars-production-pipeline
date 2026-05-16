# ===========================================================================
# PAYROLL DATA: Detection Pipeline & Account-Level Summary
# ===========================================================================
# Detects payroll/direct deposit transactions from merchant names and
# recurring credit patterns. Builds payroll_df for all downstream analysis.

import re
import time as _time
import warnings
warnings.filterwarnings('ignore')

_t0 = _time.time()

# ---------------------------------------------------------------------------
# 1. Keyword-based payroll detection
# ---------------------------------------------------------------------------
PAYROLL_KEYWORDS = [
    'PAYROLL', 'DIRECT DEP', 'DIRECT DEPOSIT', 'DDEP',
    'SALARY', 'WAGES', 'PAY FROM', 'PAYCHECK',
]

PAYROLL_PROCESSORS = [
    'ADP', 'PAYCHEX', 'GUSTO', 'CERIDIAN', 'WORKDAY',
    'PAYLOCITY', 'PAYCOM', 'PAYCOR', 'INTUIT PAYROLL',
    'QUICKBOOKS PAYROLL',
]

ALL_PAYROLL_PATTERNS = PAYROLL_KEYWORDS + PAYROLL_PROCESSORS
payroll_regex = '|'.join([re.escape(p) for p in ALL_PAYROLL_PATTERNS])

has_merchant = 'merchant_consolidated' in combined_df.columns
if has_merchant:
    keyword_mask = combined_df['merchant_consolidated'].str.contains(
        payroll_regex, case=False, na=False, regex=True
    )
else:
    keyword_mask = pd.Series(False, index=combined_df.index)

credit_mask = combined_df['amount'] > 0
keyword_payroll = keyword_mask & credit_mask

print(f"  Step 1 keyword match: {keyword_payroll.sum():,} hits "
      f"({_time.time() - _t0:.1f}s)")

# ---------------------------------------------------------------------------
# 2. Pattern-based detection: recurring credits of similar amounts
# ---------------------------------------------------------------------------
# Vectorized: bucket by amount band, check for regular date gaps.

pattern_payroll = pd.Series(False, index=combined_df.index)

_n_credits = credit_mask.sum()
_n_non_kw = (~keyword_payroll & credit_mask).sum()
print(f"  Step 2 credits: {_n_credits:,} total, {_n_non_kw:,} non-keyword")

if _n_non_kw > 0 and 'transaction_date' in combined_df.columns:
    _non_kw_idx = combined_df.index[~keyword_payroll & credit_mask]

    # Only accounts with 3+ non-keyword credits
    _acct_ids = combined_df.loc[_non_kw_idx, 'primary_account_num']
    _acct_counts = _acct_ids.value_counts()
    _eligible = _acct_counts[_acct_counts >= 3].index

    _elig_mask = _acct_ids.isin(_eligible)
    _elig_idx = _non_kw_idx[_elig_mask]

    print(f"  Step 2 eligible: {len(_elig_idx):,} txns across "
          f"{len(_eligible):,} accounts ({_time.time() - _t0:.1f}s)")

    if len(_elig_idx) > 0:
        _amt = combined_df.loc[_elig_idx, 'amount'].values
        _acct = combined_df.loc[_elig_idx, 'primary_account_num'].values
        _dates = pd.to_datetime(combined_df.loc[_elig_idx, 'transaction_date']).values

        # Build temp frame for vectorized ops
        _tmp = pd.DataFrame({
            'acct': _acct,
            'bucket': (np.log1p(_amt) * 20).round(),
            'dt': _dates,
        }, index=_elig_idx)
        _tmp = _tmp.sort_values(['acct', 'bucket', 'dt'])

        # Day gaps within each (account, bucket) group
        _grp = _tmp.groupby(['acct', 'bucket'])['dt']
        _tmp['gap'] = _grp.diff().dt.days

        # Regular = biweekly (10-18d) or monthly (25-35d)
        _regular = _tmp['gap'].between(10, 18) | _tmp['gap'].between(25, 35)

        # Need 2+ regular gaps per bucket to qualify
        _tmp['reg_count'] = _regular.groupby([_tmp['acct'], _tmp['bucket']]).transform('sum')
        _pattern_hit = _tmp['reg_count'] >= 2
        pattern_payroll.loc[_pattern_hit[_pattern_hit].index] = True

        del _tmp
        print(f"  Step 2 pattern: {pattern_payroll.sum():,} hits "
              f"({_time.time() - _t0:.1f}s)")

# Combine both detection methods
combined_df['payroll_detected'] = keyword_payroll | pattern_payroll

_total_detected = combined_df['payroll_detected'].sum()
print(f"  Step 2 total detected: {_total_detected:,} txns "
      f"({_time.time() - _t0:.1f}s)")

# ---------------------------------------------------------------------------
# 3. Identify the payroll source/processor
# ---------------------------------------------------------------------------
if _total_detected > 0 and has_merchant:
    _det_merchants = combined_df.loc[combined_df['payroll_detected'], 'merchant_consolidated']
    _upper = _det_merchants.str.upper().fillna('')

    # Vectorized processor matching
    combined_df['payroll_source'] = np.nan
    for proc in PAYROLL_PROCESSORS:
        _match = _upper.str.contains(proc, na=False)
        combined_df.loc[_match[_match].index, 'payroll_source'] = proc

    # Fill remaining keyword matches as generic
    _still_empty = combined_df['payroll_detected'] & combined_df['payroll_source'].isna()
    _kw_match = _still_empty & keyword_payroll
    combined_df.loc[_kw_match, 'payroll_source'] = 'Direct Deposit (Generic)'

    # Fill remaining pattern matches
    _pattern_only = _still_empty & ~keyword_payroll
    combined_df.loc[_pattern_only, 'payroll_source'] = 'Recurring Credit Pattern'
elif _total_detected > 0:
    combined_df.loc[combined_df['payroll_detected'], 'payroll_source'] = 'Unknown'

print(f"  Step 3 source tagging done ({_time.time() - _t0:.1f}s)")

# ---------------------------------------------------------------------------
# 4. Account-level payroll summary
# ---------------------------------------------------------------------------
payroll_txns = combined_df[combined_df['payroll_detected']].copy()
all_accounts = combined_df['primary_account_num'].unique()

if len(payroll_txns) > 0:
    acct_payroll = payroll_txns.groupby('primary_account_num').agg(
        payroll_count=('amount', 'count'),
        payroll_total=('amount', 'sum'),
        avg_payroll_amount=('amount', 'mean'),
        first_payroll=('transaction_date', 'min'),
        last_payroll=('transaction_date', 'max'),
    ).reset_index()

    # Estimate frequency: vectorized median gap approach
    _pay_dates = pd.to_datetime(payroll_txns['transaction_date'])
    _pay_sorted = payroll_txns.assign(_dt=_pay_dates).sort_values(
        ['primary_account_num', '_dt']
    )
    _pay_sorted['_gap'] = _pay_sorted.groupby('primary_account_num')['_dt'].diff().dt.days
    _median_gaps = _pay_sorted.groupby('primary_account_num')['_gap'].median()

    _freq = pd.Series('irregular', index=_median_gaps.index)
    _freq[_median_gaps <= 9] = 'weekly'
    _freq[_median_gaps.between(10, 18)] = 'biweekly'
    _freq[_median_gaps.between(19, 35)] = 'monthly'
    _freq[_median_gaps.isna()] = 'irregular'

    acct_payroll = acct_payroll.merge(
        _freq.rename('payroll_frequency').reset_index(),
        on='primary_account_num', how='left',
    )
    acct_payroll['has_payroll'] = True
else:
    acct_payroll = pd.DataFrame({
        'primary_account_num': [],
        'payroll_count': [], 'payroll_total': [],
        'avg_payroll_amount': [], 'first_payroll': [],
        'last_payroll': [], 'payroll_frequency': [],
        'has_payroll': [],
    })

print(f"  Step 4 account rollup done ({_time.time() - _t0:.1f}s)")

# Build full account-level dataframe (including non-payroll accounts)
payroll_df = pd.DataFrame({'primary_account_num': all_accounts})
payroll_df = payroll_df.merge(acct_payroll, on='primary_account_num', how='left')
payroll_df['has_payroll'] = payroll_df['has_payroll'].fillna(False)
payroll_df['payroll_count'] = payroll_df['payroll_count'].fillna(0).astype(int)
payroll_df['payroll_total'] = payroll_df['payroll_total'].fillna(0)
payroll_df['avg_payroll_amount'] = payroll_df['avg_payroll_amount'].fillna(0)
payroll_df['payroll_frequency'] = payroll_df['payroll_frequency'].fillna('none')

# ---------------------------------------------------------------------------
# 5. Merge rewards_df demographics
# ---------------------------------------------------------------------------
if 'rewards_df' in dir() or 'rewards_df' in globals():
    _acct_col = 'Acct Number' if 'Acct Number' in rewards_df.columns else ' Acct Number'
    col_map = {
        _acct_col: 'primary_account_num',
        'Account Holder Age': 'member_age',
        'Account Age': 'account_age_days',
        'Avg Bal': 'avg_balance',
        'Curr Bal': 'curr_balance',
        'Prod Code': 'prod_code',
        'Prod Desc': 'prod_desc',
        'Business?': 'is_business',
        'Branch': 'branch',
    }
    avail_cols = [c for c in col_map.keys() if c in rewards_df.columns]
    if avail_cols:
        demo_df = rewards_df[avail_cols].copy()
        demo_df = demo_df.rename(columns=col_map)
        if 'primary_account_num' in demo_df.columns:
            demo_df['primary_account_num'] = demo_df['primary_account_num'].astype(str).str.strip()
            payroll_df['primary_account_num'] = payroll_df['primary_account_num'].astype(str).str.strip()
            payroll_df = payroll_df.merge(demo_df, on='primary_account_num', how='left')

# Apply BranchMapping from clients_config.json so groupby('branch') in
# downstream payroll scripts surfaces branch NAMES instead of raw numeric IDs.
# Single source of truth lives in shared/branch_mapping.py.
if 'branch' in payroll_df.columns:
    try:
        from ars_analysis.shared.branch_mapping import apply_branch_names
        _clients_cfg = globals().get('_clients_config')
        _cid = globals().get('CLIENT_ID', '')
        apply_branch_names(payroll_df, column='branch',
                           client_id=_cid, clients_config=_clients_cfg)
    except Exception as _be:
        print(f"    WARNING: could not apply branch names to payroll_df ({_be}) -- using raw IDs")

print(f"  Step 5 demographics merged ({_time.time() - _t0:.1f}s)")

# ---------------------------------------------------------------------------
# 6. Merge combined_df activity totals
# ---------------------------------------------------------------------------
_debit_amt = combined_df['amount'].clip(upper=0)
_credit_amt = combined_df['amount'].clip(lower=0)
combined_df['_debit_amt'] = _debit_amt
combined_df['_credit_amt'] = _credit_amt

_agg_dict = {
    'total_txn_count': ('amount', 'count'),
    'total_spend': ('amount', 'sum'),
    'total_debit': ('_debit_amt', 'sum'),
    'total_credit': ('_credit_amt', 'sum'),
}
if has_merchant:
    _agg_dict['distinct_merchants'] = ('merchant_consolidated', 'nunique')

acct_activity = combined_df.groupby('primary_account_num').agg(**_agg_dict).reset_index()
combined_df.drop(columns=['_debit_amt', '_credit_amt'], inplace=True)

payroll_df = payroll_df.merge(acct_activity, on='primary_account_num', how='left')
payroll_df['total_txn_count'] = payroll_df['total_txn_count'].fillna(0).astype(int)

print(f"  Step 6 activity totals merged ({_time.time() - _t0:.1f}s)")

# ---------------------------------------------------------------------------
# 7. Age bands for demographic analysis
# ---------------------------------------------------------------------------
if 'member_age' in payroll_df.columns:
    payroll_df['member_age'] = pd.to_numeric(payroll_df['member_age'], errors='coerce')
    bins = [0, 25, 35, 45, 55, 65, 200]
    labels = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
    payroll_df['age_band'] = pd.cut(
        payroll_df['member_age'], bins=bins, labels=labels, right=True
    )

if 'account_age_days' in payroll_df.columns:
    payroll_df['account_age_days'] = pd.to_numeric(payroll_df['account_age_days'], errors='coerce')
    acct_bins = [0, 90, 180, 365, 730, 1095, 1825, 3650, 7300, 999999]
    acct_labels = ['1-90d', '91-180d', '181-365d', '1-2yr', '2-3yr',
                   '3-5yr', '5-10yr', '10-20yr', '20yr+']
    payroll_df['acct_age_band'] = pd.cut(
        payroll_df['account_age_days'], bins=acct_bins, labels=acct_labels, right=True
    )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
n_total = len(payroll_df)
n_payroll = payroll_df['has_payroll'].sum()
pct_payroll = n_payroll / n_total * 100 if n_total > 0 else 0
avg_payroll_amt = payroll_df.loc[payroll_df['has_payroll'], 'avg_payroll_amount'].mean()
n_payroll_txns = len(payroll_txns) if len(payroll_txns) > 0 else 0

print(f"\nPayroll detection complete ({_time.time() - _t0:.1f}s total).")
print(f"  {n_payroll:,} of {n_total:,} accounts ({pct_payroll:.1f}%) have detected payroll")
print(f"  {n_payroll_txns:,} payroll transactions identified")
print(f"  Avg payroll deposit: ${avg_payroll_amt:,.0f}" if avg_payroll_amt > 0 else "  Avg payroll deposit: N/A")
print(f"  Detection methods: keyword match + recurring credit pattern")
print(f"  payroll_df shape: {payroll_df.shape}")
