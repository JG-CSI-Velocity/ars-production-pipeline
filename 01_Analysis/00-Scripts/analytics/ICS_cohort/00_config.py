# ============================================
# ics-00-config  (RUN FIRST — once per client)
# ============================================
# Single place to configure every ICS cohort analysis cell.
# Change the values in the "KNOBS" block below, then run all cells.

import pandas as pd

# =========================================================
# DATA BRIDGE — wire the section to the pipeline ODD
# =========================================================
# The TXN wrapper pre-populates `odd_df` (account-level ODD) in the shared
# namespace. Legacy notebook cells assume a bare `data` frame exists, so we
# bridge it here. If no ODD is available, skip the whole section cleanly.
try:
    data = odd_df if odd_df is not None else None
except NameError:
    data = None

if data is None:
    SKIP_SECTION = True
    print("ICS_cohort SKIPPED: no ODD data available (odd_df missing/None).")

# =========================================================
# OWNER GATE — ICS_cohort only runs when ICS Account + Source exist
# =========================================================
# This section is the ICS cohort analysis. It is only meaningful when the ODD
# carries BOTH the `ICS Account` (Yes/No) and `Source` (DM/REF) columns. If
# either is missing, this client does not own this section; skip it.
if not (locals().get("SKIP_SECTION")):
    if data is None:
        SKIP_SECTION = True
        print("ICS_cohort SKIPPED: data is None.")
    elif 'ICS Account' not in data.columns:
        SKIP_SECTION = True
        print("ICS_cohort SKIPPED: 'ICS Account' column not present in ODD.")
    elif 'Source' not in data.columns:
        SKIP_SECTION = True
        print("ICS_cohort SKIPPED: 'Source' column not present in ODD.")

# Column-name bridge: the ODD loader renames 'Prod Code' -> 'Product Code', but
# the legacy product cells (06/08/12) reference 'Prod Code'. Alias whichever is
# present so those cells work regardless of which name the ODD carries.
if not (locals().get("SKIP_SECTION")) and data is not None:
    if 'Prod Code' not in data.columns and 'Product Code' in data.columns:
        data['Prod Code'] = data['Product Code']
    elif 'Product Code' not in data.columns and 'Prod Code' in data.columns:
        data['Product Code'] = data['Prod Code']

# =========================================================
# KNOBS — edit these per client / per report
# =========================================================

# (1) Which Stat Codes identify an eligible "ICS" account for this client?
#     This is NOT hardcoded — it varies by client (e.g. 1759/1746 use 'A',
#     1226 uses ['ACTIVE','INACTIVE']). It is derived from the per-client
#     ELIGIBLE_STATUS_CODES the wrapper injects into the namespace.
#     The filter is case/space-robust.
try:
    _raw_eligible = ELIGIBLE_STATUS_CODES
except NameError:
    _raw_eligible = []

ICS_STATUS_CODES = [str(s).strip().upper() for s in (_raw_eligible or []) if str(s).strip()]
if not ICS_STATUS_CODES:
    ICS_STATUS_CODES = ['O']
    print("ICS_cohort WARNING: ELIGIBLE_STATUS_CODES empty; falling back to ['O'].")

# Back-compat scalar for any reference not yet converted to the list form.
ICS_STAT_CODE = ICS_STATUS_CODES[0] if ICS_STATUS_CODES else 'O'

def is_target_status(series):
    """True where the Stat Code series matches any eligible code (case/space-robust)."""
    return series.astype(str).str.strip().str.upper().isin(ICS_STATUS_CODES)

# (2) Cohort start — the earliest Opening Month that counts as
#     a "new cohort" for cohort/activation/persona/growth cells.
#     Set EITHER a full year OR an exact YYYY-MM month.
#     Month wins if both are set.
#     Leave BOTH None to analyze all cohorts from COHORT_FLOOR onward.
COHORT_START_YEAR  = None          # e.g. 2024
COHORT_START_MONTH = None          # e.g. "2024-07"

# (3) Data floor — applied data-wide by ics-01-normalize.
#     Every row with Date Opened < COHORT_FLOOR is dropped during
#     normalization, so no downstream cell (age buckets, balance-by-age,
#     duration, etc.) can ever see pre-floor accounts.
#     Also used as the fallback for COHORT_START when neither the
#     YEAR nor the MONTH knob is set.
#     Set to None to disable the data floor entirely.
COHORT_FLOOR = "2020-01"

# (4) Activity window — the rolling period used by every "last-N-months"
#     activity / cohort / milestone cell.
#     ACTIVITY_END_MONTH = None  → auto: last FULLY COMPLETED month
#                                  (today 2026-04-xx → anchor = 2026-03)
#     ACTIVITY_END_MONTH = "2026-03" → frozen report, stays stable
ACTIVITY_WINDOW_MONTHS = 12
ACTIVITY_END_MONTH     = None

# =========================================================
# DERIVED — do not edit below
# =========================================================

STAT_LABEL = f"Stat {'/'.join(ICS_STATUS_CODES)}"

# --- Cohort start resolution ------------------------------
if COHORT_START_MONTH:
    COHORT_START = COHORT_START_MONTH
elif COHORT_START_YEAR:
    COHORT_START = f"{COHORT_START_YEAR}-01"
else:
    COHORT_START = COHORT_FLOOR

# --- Activity window resolution ---------------------------
def _resolve_activity_window(end_month_override, n_months):
    """Return a list of '%b%y' tags (e.g. 'Mar26') matching swipe/spend columns."""
    if end_month_override:
        anchor = pd.Period(end_month_override, freq='M')
    else:
        # Last FULLY COMPLETED month = the month before the current one
        anchor = pd.Timestamp.today().to_period('M') - 1
    periods = pd.period_range(end=anchor, periods=n_months, freq='M')
    tags = [p.strftime('%b%y') for p in periods]
    # End-of-month Timestamp for the last period; used anywhere that needs a
    # stable "as of" anchor. Do NOT derive this by re-parsing '%b%y' — pandas
    # treats the 2-digit year as year-of-era and overflows.
    end_date = anchor.to_timestamp(how='end')
    return tags, end_date

last_12_months, ACTIVITY_END_DATE = _resolve_activity_window(
    ACTIVITY_END_MONTH, ACTIVITY_WINDOW_MONTHS
)

# Year used by cells that split "prior years (aggregated)" from
# "latest year (individual months)" — driven by the activity window,
# NOT by today's date, so frozen reports stay stable.
ACTIVITY_ANCHOR_YEAR = ACTIVITY_END_DATE.year

# =========================================================
# ECHO — always print so you can verify before running everything else
# =========================================================

print("=" * 60)
print("ICS COHORT CONFIG")
print("=" * 60)
print(f"ICS_STATUS_CODES     : {ICS_STATUS_CODES!r}  ({STAT_LABEL})")
if COHORT_START_MONTH:
    _src = f"COHORT_START_MONTH={COHORT_START_MONTH}"
elif COHORT_START_YEAR:
    _src = f"COHORT_START_YEAR={COHORT_START_YEAR}"
else:
    _src = f"floor={COHORT_FLOOR} (no start override)"
print(f"COHORT_START         : {COHORT_START}  [{_src}]")
print(f"ACTIVITY window      : {last_12_months[0]} … {last_12_months[-1]}  ({ACTIVITY_WINDOW_MONTHS} months)")
print(f"ACTIVITY_ANCHOR_YEAR : {ACTIVITY_ANCHOR_YEAR}")
print(f"                       {last_12_months}")
print("=" * 60)

# --- Empirical Stat Code audit (only runs if `data` already loaded) ---
try:
    _sc = (
        data['Stat Code']
            .astype(str).str.upper().str.strip()
            .value_counts(dropna=False)
            .head(15)
    )
    print("\nActual Stat Code values seen in data (top 15):")
    print(_sc.to_string())
    _match = int(is_target_status(data['Stat Code']).sum())
    print(f"\nRows matching ICS_STATUS_CODES={ICS_STATUS_CODES!r}: {_match:,}")
    if _match == 0:
        print("⚠️  Zero rows match. Check the client's eligible status codes.")
except NameError:
    print("\n(Load `data` first, then re-run this cell for the Stat Code audit.)")
