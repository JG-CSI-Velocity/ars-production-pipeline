# ============================================
# ics-10-source-distribution — Source mix across all ICS accounts
# ============================================
# Supersedes: ax-9-ics source.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Covers ALL ICS (not filtered to ICS_STAT_CODE) — Source attribution is a
# portfolio question, not a target-stat question.

print("\n📊 ics-10 — Source distribution across ICS accounts...")

ics_only = data[data['ICS Account'] == 'Yes']

source_dist = (
    ics_only['Source']
            .value_counts(dropna=False)
            .reset_index()
)
source_dist.columns = ['Source', 'Count']

den = len(ics_only)
source_dist['% of ICS Accounts'] = (source_dist['Count'] / den) if den else 0
source_dist = source_dist.sort_values('Count', ascending=False).reset_index(drop=True)

total_row = pd.DataFrame({
    'Source':              ['Total'],
    'Count':               [int(source_dist['Count'].sum())],
    '% of ICS Accounts':   [1.0 if den else 0.0],
})
source_dist = pd.concat([source_dist, total_row], ignore_index=True).fillna(0)

display_formatted(source_dist, "ICS — Source Distribution")

print(f"\n✅ Analysis completed")
print(f"   Total ICS accounts : {den:,}")
print(f"   Unique sources     : {ics_only['Source'].nunique()}")
