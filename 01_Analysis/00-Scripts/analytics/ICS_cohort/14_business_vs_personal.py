# ============================================
# ics-14-business-vs-personal — Business vs Personal split within ICS
# ============================================
# Supersedes: ax-13 Biz vs Pers.
# Depends on: ics-00-config, ics-01-normalize, ics-02-helpers.
#
# Shows two cohorts side by side:
#   - All ICS accounts                              (current behavior)
#   - ICS accounts at the configured Stat Code      (= "open" for clients
#                                                     where ICS_STAT_CODE
#                                                     identifies open status)

print(f"\n📊 ics-14 — Business vs Personal: All ICS vs ICS at {STAT_LABEL}...")

all_ics = data[data['ICS Account'] == 'Yes']
target  = ics_cohort(data)

def _bp_counts(frame):
    counts = (
        frame['Business?']
             .value_counts()
             .reindex(['No', 'Yes'], fill_value=0)
    )
    return int(counts['No']), int(counts['Yes'])

all_p, all_b           = _bp_counts(all_ics)
target_p, target_b     = _bp_counts(target)
all_total              = all_p + all_b
target_total           = target_p + target_b

business_mix = pd.DataFrame({
    'Account Type':       ['Personal', 'Business', 'Total'],
    'All ICS':            [all_p, all_b, all_total],
    'All ICS %':          [
        (all_p / all_total) if all_total else 0,
        (all_b / all_total) if all_total else 0,
        1.0 if all_total else 0,
    ],
    f'At {STAT_LABEL}':   [target_p, target_b, target_total],
    f'At {STAT_LABEL} %': [
        (target_p / target_total) if target_total else 0,
        (target_b / target_total) if target_total else 0,
        1.0 if target_total else 0,
    ],
})

display_formatted(
    business_mix,
    f"ICS — Business vs Personal (All vs At {STAT_LABEL})"
)

print(f"\n✅ Analysis completed")
print(f"   All ICS         : {all_total:,}  (Personal={all_p:,}  Business={all_b:,})")
print(f"   At {STAT_LABEL} : {target_total:,}  (Personal={target_p:,}  Business={target_b:,})")
