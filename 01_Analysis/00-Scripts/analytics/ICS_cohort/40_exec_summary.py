# ============================================
# ics-40-exec-summary — Executive summary (rendered as tables)
# ============================================
# Supersedes: ax-40-exec summary.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Section-by-section executive brief. Every table uses NUMERIC columns
# with ONE type per column — never a Value column that mixes counts /
# percents / dollars. That lets display_formatted format each column
# cleanly from its own type/name; mixing types blew up #73.
#
# _safe_display wraps every call so one bad render can't kill the rest.

print("\n" + "=" * 80)
print(f"📊 ICS ACCOUNT ANALYSIS — EXECUTIVE SUMMARY  (ICS {STAT_LABEL})")
print(f"   Activity window: {last_12_months[0]} … {last_12_months[-1]}")
print("=" * 80)

def _safe_display(frame, title):
    try:
        display_formatted(frame, title)
    except Exception as _e:
        print(f"\n   ⚠️  display_formatted failed for '{title}': {type(_e).__name__}: {_e}")
        print(f"   --- fallback plain-text render ---")
        try:
            print(frame.to_string(index=False))
        except Exception as _e2:
            print(f"   (plain-text render also failed: {_e2})")
        print(f"   ---------------------------------")

# ---- Cohort frames -------------------------------------------------------
_all_ics   = data[data['ICS Account'] == 'Yes']
_target    = add_l12m_totals(ics_cohort(data))
_target_db = add_l12m_totals(ics_cohort_debit(data))
_non_ics_l = add_l12m_totals(non_ics_cohort(data))

_total_ics_ct = len(_all_ics)
_target_ct    = len(_target)
_active_l12m  = int(_target['Active in L12M'].sum()) if _target_ct else 0
_act_rate     = (_active_l12m / _target_ct) if _target_ct else 0.0

# =========================================================================
# SECTION 1 — PORTFOLIO OVERVIEW   (Count int, % of Parent float)
# =========================================================================
print("\n📈 SECTION 1 — PORTFOLIO OVERVIEW")
print("-" * 80)

exec_portfolio = pd.DataFrame({
    'Metric': [
        'Total Accounts (all)',
        'Total ICS Accounts',
        f'ICS {STAT_LABEL}',
        f'ICS {STAT_LABEL} + Debit',
        f'Active in last {len(last_12_months)} months',
        f'Inactive in last {len(last_12_months)} months',
    ],
    'Account Count': [
        int(len(data)),
        int(_total_ics_ct),
        int(_target_ct),
        int(len(_target_db)),
        int(_active_l12m),
        int(_target_ct - _active_l12m),
    ],
    '% of Parent': [
        1.0,
        (_total_ics_ct / len(data)) if len(data) else 0.0,
        (_target_ct / _total_ics_ct) if _total_ics_ct else 0.0,
        (len(_target_db) / _target_ct) if _target_ct else 0.0,
        _act_rate,
        1.0 - _act_rate,
    ],
    'Parent': [
        'All accounts',
        'All accounts',
        'ICS accounts',
        f'ICS {STAT_LABEL}',
        f'ICS {STAT_LABEL}',
        f'ICS {STAT_LABEL}',
    ],
})
_safe_display(exec_portfolio, "Section 1 — Portfolio Overview")

# =========================================================================
# SECTION 2 — ACTIVITY METRICS   (Swipes int, Spend float)
# =========================================================================
print(f"\n💳 SECTION 2 — ACTIVITY METRICS (LAST {len(last_12_months)} MONTHS)")
print("-" * 80)

_tot_sw       = float(_target['Total L12M Swipes'].sum()) if _target_ct else 0.0
_tot_sp       = float(_target['Total L12M Spend'].sum())  if _target_ct else 0.0
_active_frame = _target[_target['Active in L12M']] if _target_ct else _target
_n_active     = len(_active_frame)

_avg_sw_all    = float(_target['Total L12M Swipes'].mean())  if _target_ct else 0.0
_avg_sp_all    = float(_target['Total L12M Spend'].mean())   if _target_ct else 0.0
_avg_sw_active = float(_active_frame['Total L12M Swipes'].mean()) if _n_active else 0.0
_avg_sp_active = float(_active_frame['Total L12M Spend'].mean())  if _n_active else 0.0
_sp_per_sw     = (_tot_sp / _tot_sw) if _tot_sw else 0.0

# Three-column shape: Metric / Total Swipes / Total Spend. Each data column
# has a single type → display_formatted can format each one correctly.
exec_activity = pd.DataFrame({
    'Metric': [
        'Total (all accounts)',
        'Average per Account (all)',
        'Average per Active Account',
        'Average per Swipe',
    ],
    'Swipes': [
        int(round(_tot_sw)),
        float(round(_avg_sw_all, 1)),
        float(round(_avg_sw_active, 1)),
        float('nan'),
    ],
    'Spend': [
        float(round(_tot_sp, 2)),
        float(round(_avg_sp_all, 2)),
        float(round(_avg_sp_active, 2)),
        float(round(_sp_per_sw, 2)),
    ],
})
_safe_display(exec_activity, f"Section 2 — ICS {STAT_LABEL} Activity (Volume × Per-Account)")

# =========================================================================
# SECTION 3 — SOURCE PERFORMANCE   (typed columns)
# =========================================================================
print("\n🎯 SECTION 3 — SOURCE PERFORMANCE")
print("-" * 80)

_rows_source = []
for _src_name in sorted(_target['Source'].dropna().unique()):
    _src        = _target[_target['Source'] == _src_name]
    _src_active = _src[_src['Active in L12M']]
    _src_ct     = len(_src)
    _src_a_ct   = len(_src_active)
    _rows_source.append({
        'Source':              _src_name,
        'Accounts':            int(_src_ct),
        'Active':              int(_src_a_ct),
        '% Active':            (_src_a_ct / _src_ct) if _src_ct else 0.0,
        'Avg Swipes (Active)': float(_src_active['Total L12M Swipes'].mean()) if _src_a_ct else 0.0,
        'Avg Spend (Active)':  float(_src_active['Total L12M Spend'].mean())  if _src_a_ct else 0.0,
    })

if _rows_source:
    exec_source = pd.DataFrame(_rows_source)
    _safe_display(exec_source, f"Section 3 — Source Performance (ICS {STAT_LABEL})")
else:
    print("   (No Source values populated in the cohort.)")

# =========================================================================
# SECTION 4 — COHORT BEHAVIOR (personas)   (typed columns)
# =========================================================================
print(f"\n🔥 SECTION 4 — COHORT BEHAVIOR (cohorts from {COHORT_START} onward)")
print("-" * 80)

try:
    _personas = ics_cohort_personas
    _CATS = ['Fast Activator', 'Slow Burner', 'One and Done',
             'Never Activator', 'Too New (<3 Months)']
    _total_classified = len(_personas)
    _rows_p = []
    for _cat in _CATS:
        _n = int((_personas['Category'] == _cat).sum())
        _rows_p.append({
            'Category':       _cat,
            'Account Count':  int(_n),
            '% of Cohort':    (_n / _total_classified) if _total_classified else 0.0,
        })
    _rows_p.append({
        'Category':       'Total Classified',
        'Account Count':  int(_total_classified),
        '% of Cohort':    1.0 if _total_classified else 0.0,
    })
    _safe_display(pd.DataFrame(_rows_p), "Section 4 — Activation Personas")
except NameError:
    print("   (Run ics-37-activation-personas first to populate this section.)")

# =========================================================================
# SECTION 5 — ICS vs NON-ICS   (split into 3 typed tables)
# =========================================================================
print(f"\n⚖️  SECTION 5 — ICS vs NON-ICS — LAST {len(last_12_months)} MONTHS")
print("-" * 80)

def _cohort_stats(frame):
    _ct  = len(frame)
    _act = int(frame['Active in L12M'].sum()) if _ct else 0
    _sw  = float(frame['Total L12M Swipes'].sum()) if _ct else 0.0
    _sp  = float(frame['Total L12M Spend'].sum())  if _ct else 0.0
    return {
        'count':      _ct,
        'active':     _act,
        'act_rate':   (_act / _ct) if _ct else 0.0,
        'avg_sw':     (_sw / _ct) if _ct else 0.0,
        'avg_sp':     (_sp / _ct) if _ct else 0.0,
        'avg_sw_act': float(frame.loc[frame['Active in L12M'], 'Total L12M Swipes'].mean()) if _act else 0.0,
        'avg_sp_act': float(frame.loc[frame['Active in L12M'], 'Total L12M Spend'].mean())  if _act else 0.0,
        'bal':        float(frame['Curr Bal'].mean()) if _ct else 0.0,
    }

_ics_s = _cohort_stats(_target)
_non_s = _cohort_stats(_non_ics_l)

# Column names carry the format hint (display_formatted dispatches by name).
# 5a) Account counts — names include "Count"
exec_vs_counts = pd.DataFrame([
    {'Metric': 'Cohort Size',
     'ICS Count':     int(_ics_s['count']),
     'Non-ICS Count': int(_non_s['count']),
     'Δ Count':       int(_ics_s['count']  - _non_s['count'])},
    {'Metric': 'Active Accounts',
     'ICS Count':     int(_ics_s['active']),
     'Non-ICS Count': int(_non_s['active']),
     'Δ Count':       int(_ics_s['active'] - _non_s['active'])},
])
_safe_display(exec_vs_counts, "Section 5a — Cohort Size (ICS vs Non-ICS)")

# 5b) Rates (float 0-1) — names include "%"
exec_vs_rates = pd.DataFrame([
    {'Metric': 'Active in L12M',
     'ICS %':     float(_ics_s['act_rate']),
     'Non-ICS %': float(_non_s['act_rate']),
     'Δ %':       float(_ics_s['act_rate'] - _non_s['act_rate'])},
])
_safe_display(exec_vs_rates, "Section 5b — Activity Rate (ICS vs Non-ICS)")

# 5c) Swipes per account — names include "Swipes"
exec_vs_swipes = pd.DataFrame([
    {'Metric': 'Avg per Account',
     'ICS Swipes':     float(_ics_s['avg_sw']),
     'Non-ICS Swipes': float(_non_s['avg_sw']),
     'Δ Swipes':       float(_ics_s['avg_sw']     - _non_s['avg_sw'])},
    {'Metric': 'Avg per Active Account',
     'ICS Swipes':     float(_ics_s['avg_sw_act']),
     'Non-ICS Swipes': float(_non_s['avg_sw_act']),
     'Δ Swipes':       float(_ics_s['avg_sw_act'] - _non_s['avg_sw_act'])},
])
_safe_display(exec_vs_swipes, "Section 5c — Swipes per Account (ICS vs Non-ICS)")

# 5d) Dollar metrics — names include "Spend" / "Balance"
exec_vs_money = pd.DataFrame([
    {'Metric': 'Avg Spend per Account',
     'ICS Spend':     float(_ics_s['avg_sp']),
     'Non-ICS Spend': float(_non_s['avg_sp']),
     'Δ Spend':       float(_ics_s['avg_sp']     - _non_s['avg_sp'])},
    {'Metric': 'Avg Spend per Active Account',
     'ICS Spend':     float(_ics_s['avg_sp_act']),
     'Non-ICS Spend': float(_non_s['avg_sp_act']),
     'Δ Spend':       float(_ics_s['avg_sp_act'] - _non_s['avg_sp_act'])},
    {'Metric': 'Avg Current Balance',
     'ICS Spend':     float(_ics_s['bal']),
     'Non-ICS Spend': float(_non_s['bal']),
     'Δ Spend':       float(_ics_s['bal']        - _non_s['bal'])},
])
_safe_display(exec_vs_money, "Section 5d — Dollar Metrics (ICS vs Non-ICS)")

print("\n" + "=" * 80)
print(f"✅ Executive summary complete")
print("=" * 80)
