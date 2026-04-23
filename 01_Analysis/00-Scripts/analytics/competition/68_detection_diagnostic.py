# ===========================================================================
# DETECTION DIAGNOSTIC -- Audit competitor tagging for this client
# ===========================================================================
# Run this when category counts look wrong (empty local_banks / credit_unions,
# surprisingly low BNPL, etc.). It audits:
#
#   1. Whether CLIENT_ID has a CLIENT_CONFIGS entry in cell 01. If not, the
#      client's credit_unions + local_banks patterns are empty, so nothing
#      ever tags into those buckets. This is the #1 cause of "no local banks
#      or CU competitors" in a report.
#   2. How many transactions are tagged per category (including zeros).
#   3. Top merchants in each category -- sanity check the matches.
#   4. Unmatched merchants containing financial keywords -- competitors
#      that exist in the data but aren't in config yet. Copy these into
#      the client's CLIENT_CONFIGS entry.
#   5. Unmatched BNPL-looking merchants (AFFIRM / KLARNA / AFTERPAY / SEZZLE
#      / PAY anywhere in the name, not just starts_with).
#
# Assumes competitor_txns, combined_df, COMPETITOR_MERCHANTS, ALL_CATEGORIES
# are in globals.
# ===========================================================================

import os
import re
import pandas as pd

print("=" * 72)
print("COMPETITOR DETECTION DIAGNOSTIC")
print("=" * 72)

# ---------------------------------------------------------------------------
# 1. CLIENT_ID + CLIENT_CONFIGS membership
# ---------------------------------------------------------------------------
client_id = os.environ.get('CLIENT_ID', '') if 'CLIENT_ID' not in dir() else CLIENT_ID
has_cfg = 'CLIENT_CONFIGS' in dir()
configured = has_cfg and client_id in CLIENT_CONFIGS
print(f"\n  CLIENT_ID               : {client_id or '(not set)'}")
print(f"  CLIENT_CONFIGS present  : {has_cfg}")
print(f"  Entry for this client   : {configured}")
if has_cfg and not configured:
    print()
    print("  >>> WARNING: this client has no CLIENT_CONFIGS entry in cell 01.")
    print("  >>> credit_unions / local_banks / custom patterns are EMPTY.")
    print("  >>> Nothing will tag into 'Credit Unions' or 'Local Banks' categories.")
    print()
    print(f"  >>> FIX: add an entry to CLIENT_CONFIGS in 01_competitor_config.py:")
    print(f"  >>>   '{client_id}': {{  ")
    print(f"  >>>       'fed_district': '<1-12>',")
    print(f"  >>>       'credit_unions': ['SOME CU', 'ANOTHER CU', ...],")
    print(f"  >>>       'local_banks':   ['SOME BANK', ...],")
    print(f"  >>>       'custom': [], 'rollups': {{}},")
    print(f"  >>>   }},")

# ---------------------------------------------------------------------------
# 2. Per-category transaction counts (observed=False so empties show up)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("PER-CATEGORY COUNTS (all configured categories, including empty)")
print("-" * 72)
_cat_counts = (competitor_txns['competitor_category']
               .value_counts(dropna=False, sort=False)
               .reindex(ALL_CATEGORIES, fill_value=0))
_cat_accts = {}
for cat in ALL_CATEGORIES:
    _sub = competitor_txns[competitor_txns['competitor_category'] == cat]
    _cat_accts[cat] = _sub['primary_account_num'].nunique() if len(_sub) else 0

for cat in ALL_CATEGORIES:
    n = int(_cat_counts.get(cat, 0))
    a = int(_cat_accts.get(cat, 0))
    patterns = COMPETITOR_MERCHANTS.get(cat, {})
    n_pats = len(patterns.get('starts_with', [])) + len(patterns.get('exact', []))
    flag = "  <-- EMPTY (no patterns configured)" if n_pats == 0 else ""
    print(f"  {cat:<25s}  {n:>10,} txns  {a:>8,} accts  ({n_pats} patterns){flag}")

# ---------------------------------------------------------------------------
# 3. Top merchants per non-empty category (quick sanity read)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("TOP 5 MERCHANTS PER POPULATED CATEGORY")
print("-" * 72)
for cat in ALL_CATEGORIES:
    sub = competitor_txns[competitor_txns['competitor_category'] == cat]
    if len(sub) == 0:
        continue
    top = (sub.groupby('competitor_match')
           .size().sort_values(ascending=False).head(5))
    print(f"\n  [{cat}]")
    for name, cnt in top.items():
        print(f"    {cnt:>8,}  {name}")

# ---------------------------------------------------------------------------
# 4. Unmatched financial-looking merchants (potential missing competitors)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("TOP 30 UNMATCHED MERCHANTS WITH FINANCIAL KEYWORDS")
print("(Candidates to add to credit_unions / local_banks / custom)")
print("-" * 72)
_untagged = combined_df[combined_df['competitor_category'].isna()]
if len(_untagged):
    _m_upper = _untagged['merchant_consolidated'].astype(str).str.upper()
    _fin_mask = _m_upper.str.contains(
        r'BANK|CREDIT UNION|\bCU\b|FEDERAL CREDIT|SAVINGS|MORTGAGE|FINANCIAL|LENDING',
        regex=True, na=False
    )
    _fin = _untagged[_fin_mask]
    if len(_fin):
        top_fin = (_fin.groupby('merchant_consolidated')
                   .size().sort_values(ascending=False).head(30))
        for name, cnt in top_fin.items():
            print(f"    {cnt:>8,}  {name}")
    else:
        print("    (none found)")
else:
    print("    (no untagged transactions in combined_df)")

# ---------------------------------------------------------------------------
# 5. BNPL-looking merchants (both matched and unmatched)
# ---------------------------------------------------------------------------
print()
print("-" * 72)
print("BNPL AUDIT -- any merchant containing AFFIRM / KLARNA / AFTERPAY / "
      "SEZZLE / ZIP / QUADPAY / SPLITIT")
print("(Matched: already tagged. Unmatched: probably a detection gap.)")
print("-" * 72)
_bnpl_regex = r'AFFIRM|KLARNA|AFTERPAY|SEZZLE|\bZIP PAY\b|QUADPAY|SPLITIT'
_all_m_upper = combined_df['merchant_consolidated'].astype(str).str.upper()
_hits = combined_df[_all_m_upper.str.contains(_bnpl_regex, regex=True, na=False)]
if len(_hits):
    _grouped = (_hits.groupby(['merchant_consolidated', 'competitor_category'],
                              dropna=False, observed=True)
                .size().reset_index(name='txns')
                .sort_values('txns', ascending=False)
                .head(30))
    for _, row in _grouped.iterrows():
        cat = row['competitor_category']
        cat_s = str(cat) if pd.notna(cat) else 'UNMATCHED'
        tag = f"[{cat_s}]"
        print(f"    {int(row['txns']):>8,}  {tag:<18s}  {row['merchant_consolidated']}")
else:
    print("    (no BNPL-like merchant names found anywhere in combined_df)")

print()
print("=" * 72)
print("END DIAGNOSTIC")
print("=" * 72)
