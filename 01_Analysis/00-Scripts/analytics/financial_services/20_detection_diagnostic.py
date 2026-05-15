# ===========================================================================
# FINANCIAL SERVICES DETECTION DIAGNOSTIC -- audit tagging coverage
# ===========================================================================
# Run after cell 02 (which builds financial_services_data). This cell prints:
#
#   1. Per-category transaction + account counts and pattern counts
#      (so empty categories or categories with too-few patterns stand out).
#   2. Top tagged merchant strings per category (sanity-check the match —
#      catch a pattern hitting something it shouldn't).
#   3. Unmatched merchants whose names contain financial-services keywords
#      (BANK / LOAN / INSURANCE / INVEST / BROKER / CRYPTO / MORTGAGE / TAX
#       / ADVISOR / FUNDING / LENDING / WEALTH / RETIREMENT). These are
#      candidate merchants you can add to FINANCIAL_SERVICES_PATTERNS in
#      cell 01_config.py to close coverage gaps.
#   4. A by-category opportunity table: spend volume, unique accounts, and
#      transaction count in the unmatched pool that look like they belong
#      to a category but didn't tag.
#
# Mirrors the design of competition/68_detection_diagnostic.py.
# ===========================================================================

import pandas as _pd
import re as _re

print("=" * 72)
print("FINANCIAL SERVICES DETECTION DIAGNOSTIC")
print("=" * 72)

# ---------------------------------------------------------------------------
# 1. Per-category counts (incl. empties)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("PER-CATEGORY COUNTS (all configured categories, including empty)")
print("-" * 72)

_all_cats = list(FINANCIAL_SERVICES_PATTERNS.keys())
for _cat in _all_cats:
    _n_pats = len(FINANCIAL_SERVICES_PATTERNS[_cat])
    _data = financial_services_data.get(_cat)
    if _data is None:
        print(f"  {_cat:<25s}  {0:>10,} txns  {0:>8,} accts  ({_n_pats} patterns)  <-- NO MATCHES")
        continue
    _txns = len(_data['transactions'])
    _accts = _data['transactions']['primary_account_num'].nunique()
    _flag = ""
    if _txns < 10 and _n_pats > 5:
        _flag = "  <-- LOW MATCH RATE -- check truncated forms"
    elif _n_pats < 5:
        _flag = "  <-- few patterns; consider expanding"
    print(f"  {_cat:<25s}  {_txns:>10,} txns  {_accts:>8,} accts  ({_n_pats} patterns){_flag}")

# ---------------------------------------------------------------------------
# 2. Top merchants per non-empty category
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("TOP 5 MERCHANT STRINGS PER CATEGORY (sanity-check the matches)")
print("-" * 72)
for _cat, _data in financial_services_data.items():
    _merch_summary = _data['merchant_summary'].head(5)
    if _merch_summary.empty:
        continue
    print(f"\n  [{_cat}]")
    for _name, _row in _merch_summary.iterrows():
        _txns = int(_row['Transactions'])
        _accts = int(_row['Unique Accounts'])
        print(f"     {_name[:50]:<50s}  {_txns:>8,} txns  {_accts:>6,} accts")

# ---------------------------------------------------------------------------
# 3. Unmatched financial merchants (the discovery list)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("UNMATCHED MERCHANTS CONTAINING FINANCIAL KEYWORDS")
print("(candidates to add to FINANCIAL_SERVICES_PATTERNS in 01_config.py)")
print("-" * 72)

_FIN_KEYWORDS = [
    'BANK', 'BANKING',
    'LOAN', 'LENDING', 'LENDER',
    'MORTGAGE', 'MTG',
    'INSURANCE', 'INSURANC',
    'INVEST', 'INVST',
    'BROKER', 'BRKRGE',
    'CRYPTO', 'BITCOIN', 'BTC',
    'TAX', 'TAX SVC',
    'ADVISOR', 'ADVISORY',
    'WEALTH',
    'FUNDING',
    'CREDIT UNION', 'CREDIT CARD',
    'SAVINGS',
    'FINANCIAL', 'FINANC',
    'RETIREMENT', '401K', 'IRA',
    'HSA', 'FSA',
]
_kw_regex = _re.compile('|'.join(_re.escape(k) for k in _FIN_KEYWORDS), _re.IGNORECASE)

# Build set of already-tagged merchant strings
_tagged_merchants = set()
for _data in financial_services_data.values():
    _tagged_merchants |= set(_data['merchant_summary'].index)

_search_col = 'merchant_consolidated' if 'merchant_consolidated' in combined_df.columns else 'merchant_name'
_untagged = combined_df[~combined_df[_search_col].isin(_tagged_merchants)].copy()
_untagged = _untagged.dropna(subset=[_search_col])

# Filter to financial-looking only
_untagged_str = _untagged[_search_col].astype(str)
_fin_mask = _untagged_str.str.contains(_kw_regex, na=False)
_fin_unmatched = _untagged[_fin_mask]

if len(_fin_unmatched) == 0:
    print("  (none — all financial merchants in the data are tagged)")
else:
    _agg = (_fin_unmatched.groupby(_search_col)
            .agg(transactions=('amount', 'count'),
                 accounts=('primary_account_num', 'nunique'),
                 total_spend=('amount', 'sum'))
            .sort_values('transactions', ascending=False)
            .head(50))
    print(f"\n  {'merchant':<48s}  {'txns':>8s}  {'accts':>7s}  {'spend':>12s}")
    print(f"  {'-'*48}  {'-'*8}  {'-'*7}  {'-'*12}")
    for _name, _row in _agg.iterrows():
        _disp_name = str(_name)[:48]
        print(f"  {_disp_name:<48s}  {int(_row['transactions']):>8,}  "
              f"{int(_row['accounts']):>7,}  ${_row['total_spend']:>11,.0f}")

# ---------------------------------------------------------------------------
# 4. Categorical hint: which keywords are losing the most $ to unmatched
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("UNMATCHED SPEND BY KEYWORD (where the gaps cost the most)")
print("-" * 72)
_hint_rows = []
for _kw in _FIN_KEYWORDS:
    _km = _untagged_str.str.contains(_re.escape(_kw), case=False, na=False)
    if _km.any():
        _sub = _untagged[_km]
        _hint_rows.append({
            'keyword': _kw,
            'merchants': _sub[_search_col].nunique(),
            'transactions': len(_sub),
            'accounts': _sub['primary_account_num'].nunique(),
            'total_spend': _sub['amount'].sum(),
        })
_hints = _pd.DataFrame(_hint_rows).sort_values('total_spend', ascending=False)
if not _hints.empty:
    print(f"\n  {'keyword':<18s}  {'merch':>7s}  {'txns':>8s}  {'accts':>7s}  {'spend':>12s}")
    print(f"  {'-'*18}  {'-'*7}  {'-'*8}  {'-'*7}  {'-'*12}")
    for _, _r in _hints.iterrows():
        print(f"  {_r['keyword']:<18s}  {int(_r['merchants']):>7,}  "
              f"{int(_r['transactions']):>8,}  {int(_r['accounts']):>7,}  "
              f"${_r['total_spend']:>11,.0f}")

print()
print("=" * 72)
print("END DIAGNOSTIC -- copy unmatched merchants above into 01_config.py")
print("=" * 72)
