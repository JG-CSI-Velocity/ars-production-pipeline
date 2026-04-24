# ===========================================================================
# CU / LOCAL BANK AUDIT -- verify every configured competitor is tagged
# ===========================================================================
# Specifically addresses the ``two credit unions, two local banks'' problem
# where CoastHills (client 1776) should have surfaced 7-8 CUs and 6-7 local
# banks but the slide reported only two of each. Root cause was carrier
# prefix noise ("ACH CREDIT ...") preventing prefix-match in
# tag_competitors. After the txn_setup/06 strip-carrier-noise fix, this
# diagnostic is what confirms each client's CU/bank list is fully captured.
#
# For every configured credit_unions + local_banks pattern, prints:
#   - Whether any tagged transaction used it
#   - The tagged txn count + account count
#   - Top 5 unmatched merchants containing CREDIT UNION / BANK / FCU that
#     DIDN'T tag (candidates for new rules in client config)
#
# Assumes competitor_txns, combined_df, COMPETITOR_MERCHANTS, CLIENT_CONFIGS
# are in globals.
# ===========================================================================

import os as _os_audit
import pandas as _pd_audit

print("=" * 72)
print("CU / LOCAL BANK AUDIT  --  CLIENT:",
      globals().get("CLIENT_ID", _os_audit.environ.get("CLIENT_ID", "?")))
print("=" * 72)

_client_id = globals().get("CLIENT_ID", _os_audit.environ.get("CLIENT_ID", ""))
_cfg = CLIENT_CONFIGS.get(_client_id, {}) if "CLIENT_CONFIGS" in dir() else {}
_cu_patterns    = _cfg.get("credit_unions", [])
_bank_patterns  = _cfg.get("local_banks", [])

# ---------------------------------------------------------------------------
# Per-pattern audit
# ---------------------------------------------------------------------------
def _audit_patterns(label, patterns):
    print()
    print(f"-- {label} --  ({len(patterns)} configured)")
    if not patterns:
        print("  (none configured for this client)")
        return 0, 0
    cu_df = competitor_txns.copy() if "competitor_txns" in dir() else _pd_audit.DataFrame()
    if cu_df.empty:
        print("  (competitor_txns is empty -- run cell 02 first)")
        return 0, 0
    hit_count = 0
    total_txns = 0
    total_accts = set()
    for pat in patterns:
        pat_upper = pat.upper().strip()
        # Match merchants whose normalized name STARTS with the pattern
        m = cu_df["merchant_consolidated"].astype(str).str.upper().str.startswith(pat_upper)
        n_txn = int(m.sum())
        n_acct = cu_df.loc[m, "primary_account_num"].nunique() if n_txn else 0
        if n_txn:
            hit_count += 1
            total_txns += n_txn
            total_accts.update(cu_df.loc[m, "primary_account_num"].unique())
            mark = "OK  "
        else:
            mark = "MISS"
        print(f"    {mark}  {pat:<35s}  {n_txn:>8,} txns  {n_acct:>6,} accts")
    print(f"  Summary: {hit_count}/{len(patterns)} patterns tagged "
          f"({total_txns:,} txns, {len(total_accts):,} unique accts)")
    return hit_count, len(patterns)

_cu_hit,   _cu_total   = _audit_patterns("CREDIT UNIONS",  _cu_patterns)
_bank_hit, _bank_total = _audit_patterns("LOCAL BANKS",    _bank_patterns)

# ---------------------------------------------------------------------------
# Unmatched financial-institution merchants (candidates to add)
# ---------------------------------------------------------------------------
print()
print("-- TOP 30 UNMATCHED FI-LIKE MERCHANTS --")
print("(Candidates to add to CLIENT_CONFIGS[credit_unions/local_banks])")
if "combined_df" in dir() and "competitor_category" in combined_df.columns:
    _untagged = combined_df[combined_df["competitor_category"].isna()]
    if len(_untagged):
        _m_upper = _untagged["merchant_consolidated"].astype(str).str.upper()
        _fi_mask = _m_upper.str.contains(
            r"CREDIT UNION|\bFCU\b|\bCU\b|FEDERAL CREDIT|BANK",
            regex=True, na=False,
        )
        _fi_hits = _untagged[_fi_mask]
        if len(_fi_hits):
            _top = (_fi_hits.groupby("merchant_consolidated")
                    .agg(txns=("primary_account_num", "count"),
                         accts=("primary_account_num", "nunique"))
                    .sort_values("txns", ascending=False)
                    .head(30))
            for name, row in _top.iterrows():
                print(f"    {int(row['txns']):>8,} txns  {int(row['accts']):>5,} accts  {name}")
        else:
            print("    (no untagged FI-like merchants -- good coverage)")
    else:
        print("    (no untagged transactions)")
else:
    print("    (combined_df or competitor_category not in namespace)")

# ---------------------------------------------------------------------------
# Headline diagnosis
# ---------------------------------------------------------------------------
print()
print("-" * 72)
if _cu_total and _cu_hit < _cu_total:
    print(f"  WARNING: only {_cu_hit} of {_cu_total} configured CUs captured.")
    print(f"  Check: (a) carrier prefix stripping in txn_setup/06;")
    print(f"         (b) merchant name variants under different spellings.")
elif _cu_total:
    print(f"  CUs: {_cu_hit}/{_cu_total} fully captured.")
if _bank_total and _bank_hit < _bank_total:
    print(f"  WARNING: only {_bank_hit} of {_bank_total} configured local banks captured.")
elif _bank_total:
    print(f"  Local banks: {_bank_hit}/{_bank_total} fully captured.")
print("=" * 72)
