# ===========================================================================
# GENERAL PORTFOLIO THEME - 5,000 PERSON ROOM
# ===========================================================================
# Import once, use everywhere. All charts inherit this theme.
# Design: Large fonts, bold colors, zero clutter, no dollar figures.

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap

# ---------------------------------------------------------------------------
# Color palette (bold, high-contrast, projector-safe)
# ---------------------------------------------------------------------------
GEN_COLORS = {
    'primary':     '#1B2A4A',   # deep navy
    'accent':      '#E63946',   # signal red
    'success':     '#2EC4B6',   # teal
    'warning':     '#FF9F1C',   # amber
    'info':        '#457B9D',   # steel blue
    'light_bg':    '#F8F9FA',   # off-white
    'dark_text':   '#1B2A4A',
    'muted':       '#6C757D',
    'grid':        '#E9ECEF',
}

# Bracket palette (8 spending bins, ordered light-to-dark)
BRACKET_PALETTE = [
    '#A8DADC',   # < $1
    '#457B9D',   # $1-5
    '#2EC4B6',   # $5-10
    '#FF9F1C',   # $10-25
    '#F4A261',   # $25-50
    '#E76F51',   # $50-100
    '#E63946',   # $100-500
    '#1B2A4A',   # $500+
]

# Age band palette (6 bands)
AGE_PALETTE = {
    '18-25':  '#E63946',
    '26-35':  '#FF9F1C',
    '36-45':  '#2EC4B6',
    '46-55':  '#457B9D',
    '56-65':  '#264653',
    '65+':    '#1B2A4A',
}
AGE_ORDER = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']

# Engagement tier palette
ENGAGE_PALETTE = {
    'Power':    '#E63946',
    'Heavy':    '#FF9F1C',
    'Moderate': '#2EC4B6',
    'Light':    '#457B9D',
    'Dormant':  '#6C757D',
}
ENGAGE_ORDER = ['Power', 'Heavy', 'Moderate', 'Light', 'Dormant']

# Account age palette (9 bands)
ACCT_AGE_PALETTE = {
    '1-90d':    '#E63946',
    '91-180d':  '#FF9F1C',
    '181-365d': '#F4A261',
    '1-2yr':    '#2EC4B6',
    '2-3yr':    '#457B9D',
    '3-5yr':    '#264653',
    '5-10yr':   '#1B2A4A',
    '10-20yr':  '#6C757D',
    '20yr+':    '#A8DADC',
}
ACCT_AGE_ORDER = ['1-90d', '91-180d', '181-365d', '1-2yr', '2-3yr',
                   '3-5yr', '5-10yr', '10-20yr', '20yr+']

# Spend tier palette
SPEND_TIER_PALETTE = {
    'Very High': '#E63946',
    'High':      '#FF9F1C',
    'Medium':    '#457B9D',
    'Low':       '#6C757D',
}
SPEND_TIER_ORDER = ['Very High', 'High', 'Medium', 'Low']

# Swipe category palette (LEGACY 5-bucket -- kept for backward compatibility
# with cells that still reference these names; new analyses should prefer
# the ARS_SWIPE_* buckets defined immediately below).
SWIPE_PALETTE = {
    'Very High': '#E63946',
    'High':      '#FF9F1C',
    'Medium':    '#2EC4B6',
    'Low':       '#457B9D',
    'Inactive':  '#6C757D',
}
SWIPE_ORDER = ['Very High', 'High', 'Medium', 'Low', 'Inactive']

# ---------------------------------------------------------------------------
# ARS-standard swipe-volume segmentation (per user spec, 4/27 review)
# ---------------------------------------------------------------------------
# 7 buckets aligned to the ARS playbook -- monthly swipes per account.
# Used as both 3-month rolling average and 12-month average so the deck
# can show ``recent activity vs steady state'' side-by-side.
ARS_SWIPE_BUCKETS = [
    # (lower_inclusive, upper_inclusive_or_None, label)
    (0,    0,    '<1 (Inactive)'),
    (1,    5,    '1-5'),
    (6,    10,   '6-10'),
    (11,   15,   '11-15'),
    (16,   20,   '16-20'),
    (21,   25,   '21-25'),
    (26,   None, '25+'),
]
ARS_SWIPE_ORDER = [b[2] for b in ARS_SWIPE_BUCKETS]
ARS_SWIPE_PALETTE = {
    '<1 (Inactive)': '#6C757D',   # gray
    '1-5':           '#457B9D',   # steel blue
    '6-10':          '#2EC4B6',   # teal
    '11-15':         '#A8DADC',   # mint
    '16-20':         '#FF9F1C',   # amber
    '21-25':         '#F4A261',   # warm orange
    '25+':           '#E63946',   # red
}


def bucket_swipes_per_month(n):
    """Map a per-month-average swipe count to its ARS bucket label.
    Accepts int/float (rounded to nearest int for bucketing). NaN -> first
    bucket (treated as inactive). Use on a Series via .apply()."""
    try:
        if n is None:
            return ARS_SWIPE_BUCKETS[0][2]
        if isinstance(n, float) and (n != n):  # NaN check
            return ARS_SWIPE_BUCKETS[0][2]
        x = int(round(float(n)))
    except (TypeError, ValueError):
        return ARS_SWIPE_BUCKETS[0][2]
    if x <= 0:
        return ARS_SWIPE_BUCKETS[0][2]
    for lo, hi, label in ARS_SWIPE_BUCKETS:
        if hi is None:
            if x >= lo:
                return label
        elif lo <= x <= hi:
            return label
    return ARS_SWIPE_BUCKETS[-1][2]


def compute_swipe_segmentation(df, txn_type_col='transaction_type',
                               acct_col='primary_account_num',
                               month_col='year_month',
                               window_months=3):
    """Compute per-account swipe averages over a window and return a DataFrame
    with one row per account containing:
        avg_swipes_3m       (most recent ``window_months'' avg)
        avg_swipes_12m      (full 12-month avg)
        bucket_3m           ARS bucket label using avg_swipes_3m
        bucket_12m          ARS bucket label using avg_swipes_12m

    Counts only PIN / SIG transactions (debit-card swipes). Falls back to
    counting ALL rows if transaction_type is missing.

    Use this when you want the user-spec ``3-month rolling vs 12-month''
    side-by-side view in a segmentation chart.
    """
    import pandas as _pd
    if df is None or len(df) == 0:
        return _pd.DataFrame(columns=[
            acct_col, 'avg_swipes_3m', 'avg_swipes_12m',
            'bucket_3m', 'bucket_12m',
        ])

    work = df
    # Restrict to PIN/SIG transactions when txn_type_col is present.
    if txn_type_col in work.columns:
        _ttype = work[txn_type_col].astype(str).str.upper().str.strip()
        _swipe_mask = _ttype.isin(['PIN', 'SIG', 'POS', 'DEBIT'])
        if _swipe_mask.any():
            work = work[_swipe_mask]

    if month_col not in work.columns or acct_col not in work.columns:
        return _pd.DataFrame(columns=[
            acct_col, 'avg_swipes_3m', 'avg_swipes_12m',
            'bucket_3m', 'bucket_12m',
        ])

    # Per-account, per-month txn count
    monthly = (
        work.groupby([acct_col, month_col]).size()
        .reset_index(name='swipes')
    )

    # Most-recent N months for the 3m window
    months_sorted = sorted(monthly[month_col].unique())
    recent_months = months_sorted[-window_months:]

    avg_3m = (
        monthly[monthly[month_col].isin(recent_months)]
        .groupby(acct_col)['swipes'].mean()
        .reset_index().rename(columns={'swipes': 'avg_swipes_3m'})
    )
    avg_12m = (
        monthly.groupby(acct_col)['swipes'].mean()
        .reset_index().rename(columns={'swipes': 'avg_swipes_12m'})
    )

    out = avg_12m.merge(avg_3m, on=acct_col, how='left')
    out['avg_swipes_3m'] = out['avg_swipes_3m'].fillna(0)
    out['bucket_3m']  = out['avg_swipes_3m'].apply(bucket_swipes_per_month)
    out['bucket_12m'] = out['avg_swipes_12m'].apply(bucket_swipes_per_month)
    return out

# ---------------------------------------------------------------------------
# Matplotlib global theme
# ---------------------------------------------------------------------------
plt.rcParams.update({
    'figure.facecolor':    '#FFFFFF',
    'axes.facecolor':      '#FFFFFF',
    'axes.edgecolor':      GEN_COLORS['grid'],
    'axes.labelcolor':     GEN_COLORS['dark_text'],
    'axes.titleweight':    'bold',
    'axes.labelweight':    'bold',
    'axes.titlesize':      22,
    'axes.labelsize':      16,
    'xtick.labelsize':     14,
    'ytick.labelsize':     14,
    'font.family':         'sans-serif',
    'font.weight':         'bold',
    'font.size':           14,
    'legend.fontsize':     13,
    'legend.frameon':      False,
    'figure.dpi':          150,
    'savefig.dpi':         300,
    'savefig.bbox':        'tight',
})

sns.set_style("white")

# ---------------------------------------------------------------------------
# Helper: conference-safe axis formatting (no dollars)
# ---------------------------------------------------------------------------
def gen_fmt_pct(x, _):
    return f"{x:.1f}%"

def gen_fmt_count(x, _):
    if x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{x/1_000:.0f}K"
    return f"{int(x)}"

def gen_fmt_index(x, _):
    return f"{x:.0f}"

def gen_fmt_dollar(x, _):
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:,.0f}"

# ---------------------------------------------------------------------------
# Helper: consistent title + subtitle placement
# ---------------------------------------------------------------------------
# Universal rule: title sits above the figure (y=1.02), subtitle sits inside
# the figure at y=0.94 (default) — that yields >=0.08 figure-height clearance
# between them at any normal figsize. Caller can override if needed, but
# the defaults should be safe everywhere.
def chart_title(fig, title, subtitle=None, title_size=22, subtitle_size=14,
                title_y=1.02, subtitle_y=0.94, reserve_top=0.88,
                title_color=None, subtitle_color=None):
    """Place a title (and optional subtitle) with consistent spacing.

    Use this in new code instead of bare ``fig.suptitle`` + ``fig.text``
    so subtitles never end up jammed against the title.
    """
    if title_color is None:
        title_color = GEN_COLORS['dark_text']
    if subtitle_color is None:
        subtitle_color = GEN_COLORS['muted']

    fig.suptitle(title, fontsize=title_size, fontweight='bold',
                 color=title_color, y=title_y)
    if subtitle:
        fig.text(0.5, subtitle_y, subtitle, ha='center',
                 fontsize=subtitle_size, color=subtitle_color, style='italic')
        # When a subtitle is present, reserve more space at the top so
        # the axes don't crowd it.
        try:
            fig.subplots_adjust(top=reserve_top)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helper: remove chart clutter
# ---------------------------------------------------------------------------
def gen_clean_axes(ax, keep_left=True, keep_bottom=True):
    """Remove spines and ticks for a clean conference look."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if not keep_left:
        ax.spines['left'].set_visible(False)
        ax.tick_params(left=False)
    if not keep_bottom:
        ax.spines['bottom'].set_visible(False)
        ax.tick_params(bottom=False)
    ax.grid(False)

print("General portfolio theme loaded.")
print(f"  Palettes: {len(BRACKET_PALETTE)} bracket, {len(AGE_PALETTE)} age, {len(ENGAGE_PALETTE)} engagement, {len(ACCT_AGE_PALETTE)} account age, {len(SPEND_TIER_PALETTE)} spend tier, {len(SWIPE_PALETTE)} swipe")
print(f"  Font base: {plt.rcParams['font.size']}pt bold")
print(f"  DPI: {plt.rcParams['figure.dpi']}")


# ===========================================================================
# CLIENT TYPE + DYNAMIC LANGUAGE (CU = members, Bank = customers)
# ===========================================================================
# Auto-detect from CLIENT_NAME + CLIENT_TYPE override (per-client config or
# env var). Every cell that displays "members" / "customers" should reference
# these variables instead of hardcoding either word, so a single client config
# entry flips the whole deck's terminology.
#
# Manual override: set CLIENT_TYPE = 'cu' | 'bank' env var, otherwise
# heuristic on CLIENT_NAME (CU / Credit Union / FCU / Federal Credit -> 'cu').

import os as _os_lang

def _detect_client_type():
    explicit = (_os_lang.environ.get('CLIENT_TYPE', '') or '').strip().lower()
    if explicit in ('cu', 'credit_union', 'creditunion'):
        return 'cu'
    if explicit in ('bank',):
        return 'bank'
    name = (globals().get('CLIENT_NAME') or _os_lang.environ.get('CLIENT_NAME', '') or '').upper()
    if 'CREDIT UNION' in name or 'FEDERAL CREDIT' in name or ' FCU' in name + ' ' or name.endswith(' CU') or ' CU ' in f' {name} ':
        return 'cu'
    return 'bank'

CLIENT_TYPE = _detect_client_type()

# Singular + plural noun forms used in slide copy and chart annotations
if CLIENT_TYPE == 'cu':
    MEMBER_NOUN          = 'member'
    MEMBER_NOUN_PLURAL   = 'members'
    MEMBER_NOUN_TITLE    = 'Member'
    MEMBER_NOUN_TITLE_PL = 'Members'
    POSSESSIVE           = "the credit union's"
    INSTITUTION_NOUN     = 'credit union'
else:
    MEMBER_NOUN          = 'customer'
    MEMBER_NOUN_PLURAL   = 'customers'
    MEMBER_NOUN_TITLE    = 'Customer'
    MEMBER_NOUN_TITLE_PL = 'Customers'
    POSSESSIVE           = "the bank's"
    INSTITUTION_NOUN     = 'bank'


def member_word(n=None, plural=None, title=False):
    """Return ``member''/``members''/``customer''/``customers'' based on the
    active CLIENT_TYPE. Pass n for auto-pluralization, or plural=True/False
    explicitly. title=True returns the capitalized form."""
    if n is not None:
        plural = (n != 1)
    if plural is None:
        plural = True
    if title:
        return MEMBER_NOUN_TITLE_PL if plural else MEMBER_NOUN_TITLE
    return MEMBER_NOUN_PLURAL if plural else MEMBER_NOUN


# ===========================================================================
# UNIVERSAL TITLE / SUBTITLE LAYOUT CONSTANTS
# ===========================================================================
# Many cells were placing fig.suptitle at y=1.04 (above the figure box)
# with a fig.text subtitle at y=0.96 -- subtitle ended up inside the title's
# whitespace, causing visual overlap. Use these constants instead so every
# cell ends up with the same breathing room.
#
#     fig.suptitle("...", y=GEN_TITLE_Y)
#     fig.text(0.5, GEN_SUBTITLE_Y, "subtitle...", ha='center', ...)
#     plt.subplots_adjust(top=GEN_TOP_PAD)
GEN_TITLE_Y    = 0.97
GEN_SUBTITLE_Y = 0.92
GEN_TOP_PAD    = 0.85

print(f"  CLIENT_TYPE: {CLIENT_TYPE}  (terminology: {MEMBER_NOUN_PLURAL})")
