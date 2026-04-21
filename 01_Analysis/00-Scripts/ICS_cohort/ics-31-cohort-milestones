# ============================================
# ics-31-cohort-milestones — Cohort activation at M1/M3/M6/M9/M12/M18/M24 by opening month
# ============================================
# Supersedes: ax-29-cohort activation  (activation-focused version).
# Also supersedes: ax-28-cohort          (older, near-duplicate — archived).
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Produces `cohort_milestones_activation` — one row per opening month, columns for
# Cohort Size, Avg Current Balance, and Active / Activation % / Avg Swipes
# / Avg Spend at each milestone.
#
# Milestones compute wherever the data columns exist — NOT restricted to
# last_12_months. That means a 2023-05 cohort's M1 (May23) computes as long
# as "May23 Swipes" / "May23 Spend" exist in the data.
#
# ics-30-cohort-retention-heatmap and ics-32-cohort-activation-curves both
# consume this frame.

print(f"\n📊 ics-31 — Cohort milestones for ICS {STAT_LABEL} debit cohort...")

# All milestone-building logic lives in ics-02-helpers now so ics-30 and
# ics-32 can rebuild this frame independently if the user skips ics-31.
cohort_milestones_activation = build_cohort_milestones(data)

opening_months = (
    cohort_milestones_activation['Opening Month'].tolist()
    if not cohort_milestones_activation.empty else []
)

# Display version: blank out NaN activation %s so the styler doesn't misformat.
_display = cohort_milestones_activation.copy()
for _c in _display.columns:
    if _c.endswith("Activation %"):
        _display[_c] = _display[_c].apply(lambda v: v if pd.notna(v) else '')

display_formatted(_display, f"ICS {STAT_LABEL} — Cohort Milestones (M1/M3/M6/M12)")

# Summary
print(f"\n✅ Analysis completed")
if opening_months:
    print(f"   Cohorts analyzed : {len(cohort_milestones_activation)}")
    print(f"   Range            : {opening_months[0]} → {opening_months[-1]}")
    print(f"   Cohort start     : {COHORT_START}")
print("\n   Average Activation Rates (across all eligible cohorts):")
for _m in COHORT_MILESTONES_DEFAULT.keys():
    _col = f"{_m} Activation %"
    if _col in cohort_milestones_activation.columns:
        _avg = cohort_milestones_activation[_col].mean(skipna=True)
        _n   = int(cohort_milestones_activation[_col].notna().sum())
        if pd.notna(_avg):
            print(f"   {_m:>3}: {_avg:.1%}  (n={_n} cohorts)")
