# ============================================
# ics-29-monthly-activity-trend — Month-by-month activity trend for ICS target-Stat debit-card cohort
# ============================================
# Supersedes: ax-27-monhtly activity (typo fixed).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.

print(f"\n📊 ics-29 — Monthly activity trend for ICS {STAT_LABEL} debit-card cohort...")

cohort = ics_cohort_debit(data)
cohort_size = len(cohort)

rows = []
for m in last_12_months:
    _swipe_col = f"{m} Swipes"
    _spend_col = f"{m} Spend"
    if _swipe_col not in cohort.columns or _spend_col not in cohort.columns:
        continue

    _swipes = pd.to_numeric(cohort[_swipe_col], errors='coerce').fillna(0)
    _spend  = pd.to_numeric(cohort[_spend_col], errors='coerce').fillna(0)
    _active = int((_swipes > 0).sum())
    _total_swipes = float(_swipes.sum())
    _total_spend  = float(_spend.sum())
    _active_mask  = _swipes > 0

    rows.append({
        'Month':                       m,
        'Active Accounts':             _active,
        '% Active':                    (_active / cohort_size) if cohort_size else 0,
        'Total Swipes':                _total_swipes,
        'Total Spend':                 _total_spend,
        'Avg Swipes per Account':      float(_swipes.mean()) if cohort_size else 0,
        'Avg Spend per Account':       float(_spend.mean())  if cohort_size else 0,
        'Avg Swipes (Active Only)':    float(_swipes[_active_mask].mean()) if _active else 0,
        'Avg Spend (Active Only)':     float(_spend[_active_mask].mean())  if _active else 0,
        'Avg Spend per Swipe':         (_total_spend / _total_swipes) if _total_swipes else 0,
        'Avg Current Balance (Active)':float(cohort.loc[_active_mask, 'Curr Bal'].mean()) if _active else 0,
    })

monthly_activity_trend = pd.DataFrame(rows).fillna(0)

# Numeric hardening + rounding for display hygiene.
_num_cols = [c for c in monthly_activity_trend.columns if c != 'Month']
for _c in _num_cols:
    monthly_activity_trend[_c] = pd.to_numeric(
        monthly_activity_trend[_c], errors='coerce'
    ).round(2)

display_formatted(
    monthly_activity_trend,
    f"ICS {STAT_LABEL} — Monthly Activity Trend (Debit Card Holders)"
)

print(f"\n✅ Analysis completed")
print(f"   Cohort size (ICS {STAT_LABEL} w/ Debit) : {cohort_size:,}")
print(f"   Avg Current Balance (all)              : ${float(cohort['Curr Bal'].mean()):,.2f}"
      if cohort_size else "")
print(f"   Avg % Active across window             : "
      f"{float(monthly_activity_trend['% Active'].mean()):.2%}")
