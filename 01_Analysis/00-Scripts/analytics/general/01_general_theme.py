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

# Swipe category palette (default labels -- data cell auto-discovers actual values)
SWIPE_PALETTE = {
    'Very High': '#E63946',
    'High':      '#FF9F1C',
    'Medium':    '#2EC4B6',
    'Low':       '#457B9D',
    'Inactive':  '#6C757D',
}
SWIPE_ORDER = ['Very High', 'High', 'Medium', 'Low', 'Inactive']

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
