# ===========================================================================
# FINANCIAL SERVICES DETECTION DIAGNOSTIC
# ===========================================================================
# Audit tool for financial services tagging (section 7). Run when category
# counts look wrong (empty Crypto despite having Coinbase users, empty
# Investment/Brokerage, empty Mortgage, etc.). This is the parallel of
# competition/68_detection_diagnostic.py for the finserv scan.
#
# Reports:
#   1. Per-category transaction / account / merchant counts (including zeros).
#   2. Top 10 matched merchants per populated category (sanity check).
#   3. Top 30 unmatched merchants whose names look financial but aren't in
#      config yet -- explicitly scans for crypto/brokerage/mortgage/lending
#      brand roots the competition diagnostic misses.
#   4. Whether ecosystem patterns (BNPL / Wallet / P2P) came from competition
#      section or from the local fallback.
#
# Assumes: combined_df, FINANCIAL_SERVICES_PATTERNS, financial_services_data,
# finserv_summary_df are in globals (run 01_config.py and 02_identify.py
# before this cell).
# ===========================================================================

import re as _re
import pandas as _pd

print("=" * 72)
print("FINANCIAL SERVICES DETECTION DIAGNOSTIC")
print("=" * 72)

# ---------------------------------------------------------------------------
# 1. Pattern source (competition ecosystems vs local fallback)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("ECOSYSTEM PATTERN SOURCE")
print("-" * 72)
_using_competition_ecos = 'UNIVERSAL_ECOSYSTEMS' in dir()
print(f"  UNIVERSAL_ECOSYSTEMS in scope : {_using_competition_ecos}")
if _using_competition_ecos:
    print(f"  BNPL / Wallets / P2P patterns sourced from competition section.")
else:
    print(f"  >>> Competition section NOT loaded. Finserv is using FALLBACK ecosystem")
    print(f"  >>> patterns (see 01_config.py). For a single source of truth, run")
    print(f"  >>> competition/01_competitor_config.py before this section.")

# ---------------------------------------------------------------------------
# 2. Per-category counts (show EVERY configured category, including zeros)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("PER-CATEGORY COUNTS (all configured categories, including empty)")
print("-" * 72)

_all_cats = list(FINANCIAL_SERVICES_PATTERNS.keys())
_fs_summary = globals().get('finserv_summary_df')
_fs_data = globals().get('financial_services_data', {})

for _cat in _all_cats:
    _n_pats = len(FINANCIAL_SERVICES_PATTERNS.get(_cat, []))
    if _cat in _fs_data and len(_fs_data[_cat]['transactions']) > 0:
        _txn = len(_fs_data[_cat]['transactions'])
        _accts = _fs_data[_cat]['transactions']['primary_account_num'].nunique()
        _merchs = len(_fs_data[_cat]['merchant_summary'])
        _flag = ""
    else:
        _txn, _accts, _merchs = 0, 0, 0
        _flag = "  <-- EMPTY"
    print(f"  {_cat:<28s}  {_txn:>10,} txns  {_accts:>8,} accts  "
          f"{_merchs:>4} merchants  ({_n_pats} patterns){_flag}")

# ---------------------------------------------------------------------------
# 3. Top 10 merchants per populated category (sanity read)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("TOP 10 MATCHED MERCHANTS PER POPULATED CATEGORY")
print("-" * 72)
for _cat in _all_cats:
    if _cat not in _fs_data:
        continue
    _ms = _fs_data[_cat].get('merchant_summary')
    if _ms is None or len(_ms) == 0:
        continue
    print(f"\n  [{_cat}]")
    for _name, _row in _ms.head(10).iterrows():
        _tx = int(_row['Transactions'])
        _ac = int(_row['Unique Accounts'])
        print(f"    {_tx:>8,} txns  {_ac:>6,} accts  {_name}")

# ---------------------------------------------------------------------------
# 4. Unmatched merchants that LOOK financial
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("TOP 40 UNMATCHED MERCHANTS WITH FINANCIAL SERVICE KEYWORDS")
print("(Candidates to add to FINANCIAL_SERVICES_PATTERNS in 01_config.py)")
print("-" * 72)

# Build the set of merchants already tagged by any category
_tagged = set()
for _cat, _d in _fs_data.items():
    _tagged |= set(_d['transactions']['merchant_consolidated'].dropna().unique())

_search_column = 'merchant_consolidated' if 'merchant_consolidated' in combined_df.columns else 'merchant_name'
_all_merch = combined_df[_search_column].dropna()
_unmatched_merch_series = _all_merch[~_all_merch.isin(_tagged)]

# Keywords covering the brand roots / terms the competition diagnostic misses.
# Includes crypto, brokerage, mortgage, lending, investment, specific brand
# roots (coinbase/robinhood/fidelity/schwab/vanguard/etc.) that don't contain
# the word "bank" or "financial".
_FS_KEYWORDS = [
    # traditional finserv
    r'MORTGAGE', r'LENDING', r'LOAN',
    r'INVEST', r'BROKER', r'SECURITIES', r'WEALTH',
    r'RETIREMENT', r'IRA', r'401K', r'ROTH',
    r'INSURANCE',
    # crypto / digital assets (brand roots + generic)
    r'CRYPTO', r'COIN', r'BITCOIN', r'BTC\b', r'ETH\b', r'USDC',
    r'COINBASE', r'BINANCE', r'KRAKEN', r'GEMINI',
    r'BLOCKCHAIN', r'METAMASK', r'LEDGER', r'UPHOLD',
    # brokerage brand roots
    r'ROBINHOOD', r'FIDELITY', r'SCHWAB', r'VANGUARD',
    r'ETRADE', r'TDAMERITRADE', r'AMERITRADE',
    r'MERRILL', r'MORGAN STANLEY', r'RAYMOND JAMES',
    r'WEBULL', r'TASTYTRADE', r'INTERACTIVE BROKERS',
    r'BETTERMENT', r'WEALTHFRONT', r'ACORNS', r'STASH', r'SOFI',
    # consumer lending / tax / credit
    r'UPSTART', r'LENDING TREE', r'LENDINGCLUB', r'PROSPER',
    r'CREDIT KARMA', r'EXPERIAN', r'TRANSUNION', r'EQUIFAX',
    r'TURBOTAX', r'H&R BLOCK', r'QUICKBOOKS',
]
_fs_regex = r'\b(?:' + '|'.join(_FS_KEYWORDS) + r')'
_m_upper = _unmatched_merch_series.astype(str).str.upper()
_fin_mask = _m_upper.str.contains(_fs_regex, regex=True, na=False)
_fin_hits = _unmatched_merch_series[_fin_mask]

if len(_fin_hits):
    _top_fin = (_fin_hits.groupby(_fin_hits).size()
                .sort_values(ascending=False).head(40))
    for _name, _cnt in _top_fin.items():
        print(f"    {int(_cnt):>8,}  {_name}")
else:
    print("    (no obvious finserv-like merchants left unmatched)")

# ---------------------------------------------------------------------------
# 5. Brand-root audit: any merchant containing these names, matched or not
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("BRAND AUDIT: top 30 rows containing Coinbase / Robinhood / Fidelity /")
print("Schwab / Vanguard / Crypto / Rocket -- matched AND unmatched")
print("(Helps see if a brand is tagging to the WRONG category.)")
print("-" * 72)

_brand_regex = (r'\b(?:COINBASE|ROBINHOOD|FIDELITY|SCHWAB|VANGUARD|'
                r'CRYPTO|BITCOIN|BINANCE|KRAKEN|ROCKET|BETTERMENT|WEALTHFRONT)')
_brand_hits = combined_df[
    combined_df[_search_column].astype(str).str.upper().str.contains(
        _brand_regex, regex=True, na=False
    )
]
if len(_brand_hits):
    # Tag each merchant with whichever category (if any) claims it
    _m_to_cat = {}
    for _cat, _d in _fs_data.items():
        for _m in _d['transactions']['merchant_consolidated'].dropna().unique():
            _m_to_cat.setdefault(_m, _cat)
    _brand_grouped = (_brand_hits.groupby(_search_column)
                      .size().sort_values(ascending=False).head(30))
    for _name, _cnt in _brand_grouped.items():
        _cat = _m_to_cat.get(_name, 'UNMATCHED')
        print(f"    {int(_cnt):>8,}  [{_cat[:22]:<22s}]  {_name}")
else:
    print("    (no brand-root hits in data -- client may simply not have these merchants)")

print()
print("=" * 72)
print("END DIAGNOSTIC")
print("=" * 72)
