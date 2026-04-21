# ============================================
# ics-26-activity-by-source-debit — Last-N-months activity by Source × Debit status
# ============================================
# Supersedes: ax-24-stat-code-debit-activity.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Output: Source rows with "Debit Yes" / "Debit No" sub-rows nested under each,
# plus a Grand Total row at the bottom.

print(f"\n📊 ics-26 — Activity by Source & Debit for ICS {STAT_LABEL}...")

cohort = add_l12m_totals(ics_cohort(data))

def _bucket_metrics(label, frame):
    count = len(frame)
    swipes = int(frame['Total L12M Swipes'].sum())
    spend  = float(frame['Total L12M Spend'].sum())
    active = int(frame['Active in L12M'].sum())
    return {
        'Source / Debit':         label,
        'Account Count':          count,
        'Total Swipes':           swipes,
        'Total Spend':            spend,
        'Active Accounts':        active,
        '% Active':               (active / count) if count else 0,
        'Avg Swipes per Account': float(frame['Total L12M Swipes'].mean()) if count else 0,
        'Avg Spend per Account':  float(frame['Total L12M Spend'].mean())  if count else 0,
        'Avg Spend per Swipe':    (spend / swipes) if swipes else 0,
    }

rows = []
for source in sorted(cohort['Source'].unique()):
    source_frame = cohort[cohort['Source'] == source]
    rows.append(_bucket_metrics(source, source_frame))

    yes_frame = source_frame[source_frame['Debit?'] == 'Yes']
    if len(yes_frame):
        rows.append(_bucket_metrics('  --- Debit Yes', yes_frame))

    no_frame = source_frame[source_frame['Debit?'] == 'No']
    if len(no_frame):
        rows.append(_bucket_metrics('  --- Debit No', no_frame))

rows.append(_bucket_metrics('Grand Total', cohort))

activity_by_source_debit = pd.DataFrame(rows).fillna(0)

# Round non-label numeric columns for display hygiene (keeps types numeric).
for _c in activity_by_source_debit.columns:
    if _c != 'Source / Debit':
        activity_by_source_debit[_c] = pd.to_numeric(
            activity_by_source_debit[_c], errors='coerce'
        ).round(2)

display_formatted(
    activity_by_source_debit,
    f"ICS {STAT_LABEL} — Activity by Source & Debit Status"
)

print(f"\n✅ Analysis completed")
