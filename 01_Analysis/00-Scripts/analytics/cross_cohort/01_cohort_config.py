# ===========================================================================
# CROSS-COHORT CONFIG -- Account-level frame that wires ICS + ARS + Tier
# ===========================================================================
# Builds cross_df (one row per account) from rewards_df with:
#   - is_ics, ics_channel          (from 'ICS Account' + 'Source')
#   - open_date, open_cohort        (from 'Date Opened')
#   - n_mailed, n_responded, response_rate, response_group
#   - ever_mailed, ever_responded, mailed_nonresponder, never_mailed
#   - first_mail_period, first_response_period,
#     days_to_first_mail, days_to_first_response
#   - first_seg, current_seg        (first/last non-Control Segmentation)
#   - first_tier, current_tier, tier_rank_delta, tier_trajectory
#     (per-period tier bucketized from monthly Swipes with same cutoffs
#      as SwipeCat3/SwipeCat12 from shared/format_odd.py)
#
# Mail / Resp / Segmentation columns are auto-discovered by suffix so the
# frame scales as new bi-monthly mail rounds arrive.
#
# Downstream cross_cohort cells (02..50) consume cross_df and join to
# competition data via primary_account_num -> acct_number.
# ===========================================================================

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 0. Guard: need rewards_df
# ---------------------------------------------------------------------------
if 'rewards_df' not in dir():
    raise RuntimeError(
        "cross_cohort/01 needs rewards_df. Run setup/txn_setup (or the ODDD "
        "loader) first."
    )

_all_cols = rewards_df.columns.tolist()
_acct_col = 'Acct Number' if 'Acct Number' in _all_cols else ' Acct Number'

# ---------------------------------------------------------------------------
# 1. Month parsing helper (shared shape with retention/01)
# ---------------------------------------------------------------------------
_MONTH_MAP = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
              'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}


def _tag_to_period(tag):
    """'Mar26' -> Period('2026-03','M'); bad input -> NaT."""
    try:
        return pd.Period(year=2000 + int(tag[3:]), month=_MONTH_MAP[tag[:3]], freq='M')
    except (KeyError, ValueError, IndexError):
        return pd.NaT


def _sort_by_period(cols, suffix):
    return sorted(
        cols,
        key=lambda c: _tag_to_period(c.replace(suffix, '').strip()) or pd.Period('1900-01', 'M'),
    )


# ---------------------------------------------------------------------------
# 2. Discover ARS + Segmentation columns (suffix-based, scale-safe)
# ---------------------------------------------------------------------------
_mail_cols = _sort_by_period([c for c in _all_cols if c.endswith(' Mail')], ' Mail')
_resp_cols = _sort_by_period([c for c in _all_cols if c.endswith(' Resp')], ' Resp')
_seg_cols = _sort_by_period([c for c in _all_cols if c.endswith(' Segmentation')], ' Segmentation')

# Monthly Swipes columns -- used to build per-period tier
_swipe_cols = _sort_by_period(
    [c for c in _all_cols if c.endswith(' Swipes')
     and not c.startswith('Total') and not c.startswith('last') and not c.startswith('Last')],
    ' Swipes',
)

_mail_periods = [_tag_to_period(c.replace(' Mail', '').strip()) for c in _mail_cols]
_resp_periods = [_tag_to_period(c.replace(' Resp', '').strip()) for c in _resp_cols]
_seg_periods = [_tag_to_period(c.replace(' Segmentation', '').strip()) for c in _seg_cols]

# ---------------------------------------------------------------------------
# 3. Seed cross_df from rewards_df with defensive column picks
# ---------------------------------------------------------------------------
_keep = [_acct_col]
for c in ('ICS Account', 'Source', 'Date Opened', 'Date Closed',
          'Account Holder Age', 'Account Age', 'Branch', 'Prod Code', 'Prod Desc',
          'Business?', 'Stat Code', 'Stat Desc', 'Avg Bal', 'Curr Bal',
          'SwipeCat3', 'SwipeCat12',
          '# of Offers', '# of Responses', 'Response Grouping'):
    if c in _all_cols:
        _keep.append(c)

cross_df = rewards_df[_keep + _mail_cols + _resp_cols + _seg_cols + _swipe_cols].copy()
cross_df.rename(columns={_acct_col: 'acct_number'}, inplace=True)
cross_df['acct_number'] = cross_df['acct_number'].astype(str).str.strip()

# ---------------------------------------------------------------------------
# 4. ICS identification
# ---------------------------------------------------------------------------
_ICS_YES = {'YES', 'Y'}
_VALID_CHANNELS = {'DM', 'REF'}

if 'ICS Account' in cross_df.columns:
    _flag = cross_df['ICS Account'].astype(str).str.strip().str.upper()
    cross_df['is_ics'] = _flag.isin(_ICS_YES)
else:
    cross_df['is_ics'] = False

if 'Source' in cross_df.columns:
    _src = cross_df['Source'].astype(str).str.strip().str.upper()
    cross_df['ics_channel'] = np.where(
        cross_df['is_ics'] & _src.isin(_VALID_CHANNELS), _src,
        np.where(cross_df['is_ics'], 'ICS-Unknown', 'Non-ICS'),
    )
else:
    cross_df['ics_channel'] = np.where(cross_df['is_ics'], 'ICS-Unknown', 'Non-ICS')

# ---------------------------------------------------------------------------
# 5. Cohort anchors
# ---------------------------------------------------------------------------
if 'Date Opened' in cross_df.columns:
    cross_df['open_date'] = pd.to_datetime(cross_df['Date Opened'], errors='coerce')
    cross_df['open_cohort'] = cross_df['open_date'].dt.to_period('M')
else:
    cross_df['open_date'] = pd.NaT
    cross_df['open_cohort'] = pd.NA

# ---------------------------------------------------------------------------
# 6. ARS rollups (prefer upstream values, recompute defensively)
# ---------------------------------------------------------------------------
if _mail_cols:
    _mail_mask = cross_df[_mail_cols].notna()
    cross_df['n_mailed'] = _mail_mask.sum(axis=1).astype(int)
else:
    _mail_mask = None
    cross_df['n_mailed'] = cross_df.get('# of Offers', 0)

if _resp_cols:
    # format_odd step 6 treats "NU 1-4" as not-responded. Mirror that here.
    _resp_notna = cross_df[_resp_cols].replace('NU 1-4', pd.NA).notna()
    cross_df['n_responded'] = _resp_notna.sum(axis=1).astype(int)
else:
    _resp_notna = None
    cross_df['n_responded'] = cross_df.get('# of Responses', 0)

cross_df['ever_mailed'] = cross_df['n_mailed'] > 0
cross_df['ever_responded'] = cross_df['n_responded'] > 0
cross_df['never_mailed'] = ~cross_df['ever_mailed']
cross_df['mailed_nonresponder'] = cross_df['ever_mailed'] & ~cross_df['ever_responded']

cross_df['response_rate'] = np.where(
    cross_df['ever_mailed'],
    cross_df['n_responded'] / cross_df['n_mailed'].where(cross_df['n_mailed'] > 0),
    np.nan,
)

# Prefer upstream Response Grouping; recompute if absent
if 'Response Grouping' not in cross_df.columns:
    rg = pd.Series('check', index=cross_df.index)
    rg[cross_df['n_mailed'] == 0] = 'No Offer'
    rg[(cross_df['n_mailed'] > 0) & (cross_df['n_responded'] == 0)] = 'Non-Responder'
    rg[(cross_df['n_mailed'] == 1) & (cross_df['n_responded'] == 1)] = 'SO-SR'
    rg[(cross_df['n_mailed'] >= 2) & (cross_df['n_responded'] == 1)] = 'MO-SR'
    rg[cross_df['n_responded'] >= 2] = 'MR'
    cross_df['response_group'] = rg
else:
    cross_df['response_group'] = cross_df['Response Grouping']

# ---------------------------------------------------------------------------
# 7. First-mail / first-response timing (drives activation speed cells)
# ---------------------------------------------------------------------------
def _first_period(mask_df, periods):
    """Vectorized: for each row, period of the first True column."""
    if mask_df is None or mask_df.empty or len(periods) == 0:
        return pd.Series(pd.NaT, index=cross_df.index)
    arr = mask_df.values
    idx = np.where(arr.any(axis=1), arr.argmax(axis=1), -1)
    out = np.array([periods[i] if i >= 0 else pd.NaT for i in idx], dtype=object)
    return pd.Series(out, index=cross_df.index)


cross_df['first_mail_period'] = _first_period(_mail_mask, _mail_periods)
cross_df['first_response_period'] = _first_period(_resp_notna, _resp_periods)


def _period_to_month_end(p):
    return p.to_timestamp(how='end') if isinstance(p, pd.Period) else pd.NaT


_fm_ts = cross_df['first_mail_period'].map(_period_to_month_end)
_fr_ts = cross_df['first_response_period'].map(_period_to_month_end)
cross_df['days_to_first_mail'] = (_fm_ts - cross_df['open_date']).dt.days
cross_df['days_to_first_response'] = (_fr_ts - cross_df['open_date']).dt.days

# ---------------------------------------------------------------------------
# 8. Segmentation first/last (Control/Non-Responder/Responder per period)
# ---------------------------------------------------------------------------
if _seg_cols:
    _seg_block = cross_df[_seg_cols].astype(str)
    # first non-Control label per row (Control = account was NOT mailed that period)
    _not_control = _seg_block.where(_seg_block != 'Control')
    cross_df['first_seg'] = _not_control.bfill(axis=1).iloc[:, 0]
    cross_df['current_seg'] = _not_control.ffill(axis=1).iloc[:, -1]
else:
    cross_df['first_seg'] = pd.NA
    cross_df['current_seg'] = pd.NA

# ---------------------------------------------------------------------------
# 9. Per-period usage tier (same cutoffs as shared/format_odd _categorize_swipes)
#    Applied to monthly Swipes. first_tier = tier at account's FIRST active
#    month with swipes > 0; current_tier = tier in the most recent month.
# ---------------------------------------------------------------------------
_TIER_LABELS = ['Non-user', '1-5 Swipes', '6-10 Swipes', '11-15 Swipes',
                '16-20 Swipes', '21-25 Swipes', '26-40 Swipes', '41+ Swipes']
_TIER_RANK = {lbl: i for i, lbl in enumerate(_TIER_LABELS)}


def _bucket(v):
    if pd.isna(v) or v < 1:
        return 'Non-user'
    if v <= 5:
        return '1-5 Swipes'
    if v <= 10:
        return '6-10 Swipes'
    if v <= 15:
        return '11-15 Swipes'
    if v <= 20:
        return '16-20 Swipes'
    if v <= 25:
        return '21-25 Swipes'
    if v <= 40:
        return '26-40 Swipes'
    return '41+ Swipes'


if _swipe_cols:
    _sw = cross_df[_swipe_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    # first active month = first column where swipes > 0
    _active = _sw.gt(0)
    _first_idx = np.where(_active.any(axis=1), _active.values.argmax(axis=1), -1)
    _last_idx = np.where(_active.any(axis=1),
                         _sw.shape[1] - 1 - _active.values[:, ::-1].argmax(axis=1), -1)

    _first_vals = np.where(_first_idx >= 0,
                           _sw.values[np.arange(len(_sw)), np.clip(_first_idx, 0, None)], 0.0)
    _last_vals = np.where(_last_idx >= 0,
                          _sw.values[np.arange(len(_sw)), np.clip(_last_idx, 0, None)], 0.0)

    cross_df['first_tier'] = pd.Series(_first_vals, index=cross_df.index).map(_bucket)
    cross_df['current_tier'] = pd.Series(_last_vals, index=cross_df.index).map(_bucket)

    cross_df['first_tier_rank'] = cross_df['first_tier'].map(_TIER_RANK)
    cross_df['current_tier_rank'] = cross_df['current_tier'].map(_TIER_RANK)
    cross_df['tier_rank_delta'] = cross_df['current_tier_rank'] - cross_df['first_tier_rank']

    cross_df['tier_trajectory'] = np.where(
        cross_df['tier_rank_delta'] > 0, 'Up',
        np.where(cross_df['tier_rank_delta'] < 0, 'Down', 'Flat'),
    )
else:
    cross_df['first_tier'] = pd.NA
    cross_df['current_tier'] = pd.NA
    cross_df['first_tier_rank'] = np.nan
    cross_df['current_tier_rank'] = np.nan
    cross_df['tier_rank_delta'] = np.nan
    cross_df['tier_trajectory'] = pd.NA

# ---------------------------------------------------------------------------
# 10. Exports for downstream cells
# ---------------------------------------------------------------------------
CROSS_MAIL_COLS = _mail_cols
CROSS_RESP_COLS = _resp_cols
CROSS_SEG_COLS = _seg_cols
CROSS_SWIPE_COLS = _swipe_cols
CROSS_MAIL_PERIODS = _mail_periods
CROSS_RESP_PERIODS = _resp_periods
CROSS_SEG_PERIODS = _seg_periods
CROSS_TIER_LABELS = _TIER_LABELS
CROSS_TIER_RANK = _TIER_RANK

# ---------------------------------------------------------------------------
# 11. Echo
# ---------------------------------------------------------------------------
_n = len(cross_df)
_n_ics = int(cross_df['is_ics'].sum())
_n_dm = int((cross_df['ics_channel'] == 'DM').sum())
_n_ref = int((cross_df['ics_channel'] == 'REF').sum())
_n_mailed = int(cross_df['ever_mailed'].sum())
_n_responded = int(cross_df['ever_responded'].sum())
_resp_rate = _n_responded / _n_mailed if _n_mailed else 0.0

print('=' * 64)
print('CROSS-COHORT CONFIG')
print('=' * 64)
print(f'Accounts                 : {_n:,}')
print(f'  ICS                    : {_n_ics:,} ({_n_ics / _n * 100:.1f}%)' if _n else '  ICS                    : 0')
print(f'    DM                   : {_n_dm:,}')
print(f'    REF                  : {_n_ref:,}')
print(f'Mail periods discovered  : {len(_mail_cols)} ({_mail_cols[0] if _mail_cols else "-"} .. {_mail_cols[-1] if _mail_cols else "-"})')
print(f'Resp periods discovered  : {len(_resp_cols)}')
print(f'Segmentation periods     : {len(_seg_cols)}')
print(f'Swipe periods (for tier) : {len(_swipe_cols)}')
print(f'Ever mailed              : {_n_mailed:,} ({_n_mailed / _n * 100:.1f}%)' if _n else '')
print(f'Ever responded           : {_n_responded:,}  (resp-rate of mailed: {_resp_rate * 100:.1f}%)')
if cross_df['open_cohort'].notna().any():
    print(f'Open-cohort range        : {cross_df["open_cohort"].min()} .. {cross_df["open_cohort"].max()}')
print(f'Tier trajectory          : Up={int((cross_df["tier_trajectory"] == "Up").sum()):,}  '
      f'Flat={int((cross_df["tier_trajectory"] == "Flat").sum()):,}  '
      f'Down={int((cross_df["tier_trajectory"] == "Down").sum()):,}')
print('=' * 64)
