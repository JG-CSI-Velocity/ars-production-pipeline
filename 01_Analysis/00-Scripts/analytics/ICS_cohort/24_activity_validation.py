# ============================================
# ics-24-activity-validation — Diagnostic: swipe/spend columns & cohort sanity
# ============================================
# Supersedes: ax-22-spend-swipe-validation.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# This cell exists so you can SEE what the cohort-filter + activity-window
# produced before trusting downstream L12M cells. No display_formatted table
# — it's a printed sanity report.

import re as _re_diag

print(f"\n🔎 ics-24 — Activity validation for ICS {STAT_LABEL}...")

cohort = ics_cohort(data)
swipe_cols, spend_cols = swipe_spend_columns(cohort)

print(f"\n   Cohort size                       : {len(cohort):,}")
print(f"   Activity window                   : {last_12_months[0]} … {last_12_months[-1]} "
      f"({len(last_12_months)} months)")
print(f"   Swipe columns matched ({len(swipe_cols):>2})        : {swipe_cols}")
print(f"   Spend columns matched ({len(spend_cols):>2})        : {spend_cols}")

# Month-tag alignment check
_tag = lambda c: c.split(' ', 1)[0]
swipe_tags = sorted({_tag(c) for c in swipe_cols})
spend_tags = sorted({_tag(c) for c in spend_cols})
if swipe_tags != spend_tags:
    print("   ⚠️  Swipe / Spend month tags DO NOT match:")
    print(f"      swipe only: {sorted(set(swipe_tags) - set(spend_tags))}")
    print(f"      spend only: {sorted(set(spend_tags) - set(swipe_tags))}")
else:
    print("   ✅ Swipe and Spend month tags aligned")

# Are we missing any window months?
_missing = [m for m in last_12_months if m not in swipe_tags]
if _missing:
    print(f"   ⚠️  Window months with no matching Swipes column: {_missing}")

# Duplicate account ID check
if 'Acct ID' in cohort.columns:
    _dups = cohort.loc[cohort['Acct ID'].duplicated(keep=False), 'Acct ID']
    if not _dups.empty:
        print(f"   ⚠️  Duplicate Acct IDs in cohort: {_dups.nunique()} unique IDs duplicated")
    else:
        print("   ✅ No duplicate Acct IDs in cohort")

# Reconcile vs MonthlySwipes12 / MonthlySpend12 if present
if swipe_cols:
    _our_swipes = cohort[swipe_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum().sum()
    _our_spend  = cohort[spend_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum().sum()
    print(f"\n   Grand totals from monthly columns :")
    print(f"      Swipes : {int(_our_swipes):,}")
    print(f"      Spend  : ${float(_our_spend):,.2f}")

    if 'MonthlySwipes12' in cohort.columns:
        _provided_sw = pd.to_numeric(cohort['MonthlySwipes12'], errors='coerce').fillna(0).sum()
        print(f"      vs MonthlySwipes12 rollup        : {int(_provided_sw):,}  "
              f"(Δ = {int(_our_swipes - _provided_sw):+,})")
    if 'MonthlySpend12' in cohort.columns:
        _provided_sp = pd.to_numeric(cohort['MonthlySpend12'], errors='coerce').fillna(0).sum()
        print(f"      vs MonthlySpend12 rollup         : ${float(_provided_sp):,.2f}  "
              f"(Δ = ${float(_our_spend - _provided_sp):+,.2f})")
