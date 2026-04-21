# ============================================
# ics-33-cohort-milestones-extended — Milestones with prior years aggregated + current-year monthly
# ============================================
# Supersedes: ax-30-cohort-milestones.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Produces `cohort_milestones_extended` — a long-horizon cohort view that
# keeps the row count manageable by aggregating all complete prior years
# into single rows (e.g. "2023", "2024") and breaking out the current
# anchor year month-by-month (e.g. "2025-01", "2025-02" …).
#
# Milestones: M1, M3, M6, M9, M12. Metrics per milestone: Active count,
# % Active, Avg Swipes, Avg Spend.

print(f"\n📊 ics-33 — Extended cohort milestones for ICS {STAT_LABEL} debit cohort...")

cohort = ics_cohort_debit(data)
cohort = add_opening_month(cohort)
cohort = apply_cohort_start(cohort)

# Derive the ordered list of "opening periods": prior complete years
# rolled up into one row each, then the anchor year broken into months.
_all_months     = sorted(cohort['Opening Month'].dropna().unique().tolist())
_anchor_year    = ACTIVITY_ANCHOR_YEAR
_prior_years    = sorted({m[:4] for m in _all_months if int(m[:4]) < _anchor_year})
_current_months = sorted([m for m in _all_months if int(m[:4]) == _anchor_year])
_opening_periods = _prior_years + _current_months

_MILESTONES = [1, 3, 6, 9, 12]

rows = []
for _period in _opening_periods:
    if len(_period) == 4:                                     # full year
        _sub        = cohort[cohort['Opening Month'].str.startswith(_period)].copy()
        _opening_dt = pd.to_datetime(f"{_period}-01")         # anchor to Jan of that year
    else:                                                     # YYYY-MM
        _sub        = cohort[cohort['Opening Month'] == _period].copy()
        _opening_dt = pd.to_datetime(_period)
    if _sub.empty:
        continue

    _row = {
        'Opening Period':      _period,
        'Cohort Size':         int(len(_sub)),
        'Avg Current Balance': float(_sub['Curr Bal'].mean()),
    }

    for _m in _MILESTONES:
        _tag   = (_opening_dt + pd.DateOffset(months=_m - 1)).strftime('%b%y')
        _s_col = f"{_tag} Swipes"
        _d_col = f"{_tag} Spend"
        if (_s_col in _sub.columns) and (_d_col in _sub.columns):
            _sw     = pd.to_numeric(_sub[_s_col], errors='coerce').fillna(0)
            _sp     = pd.to_numeric(_sub[_d_col], errors='coerce').fillna(0)
            _active = int((_sw > 0).sum())
            _row[f'M{_m} Active']     = _active
            _row[f'M{_m} % Active']   = (_active / len(_sub)) if len(_sub) else 0
            _row[f'M{_m} Avg Swipes'] = float(_sw.mean())
            _row[f'M{_m} Avg Spend']  = float(_sp.mean())
        else:
            _row[f'M{_m} Active']     = pd.NA
            _row[f'M{_m} % Active']   = pd.NA
            _row[f'M{_m} Avg Swipes'] = pd.NA
            _row[f'M{_m} Avg Spend']  = pd.NA

    rows.append(_row)

cohort_milestones_extended = pd.DataFrame(rows)

display_formatted(
    cohort_milestones_extended,
    f"ICS {STAT_LABEL} — Cohort Milestones (Prior Years Aggregated + {_anchor_year} Monthly)"
)

print(f"\n✅ Analysis completed")
print(f"   Prior years aggregated : {_prior_years}")
print(f"   Current-year months    : {len(_current_months)} ({_anchor_year})")
print(f"   Total opening periods  : {len(cohort_milestones_extended)}")
