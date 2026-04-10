# ===========================================================================
# COMPETITOR CONFIGURATION -- Multi-Client Layered Structure
# ===========================================================================
# How it works:
#   1. Set CLIENT_ID in setup/02-file-config
#   2. This cell looks up the client in CLIENT_CONFIGS (Section C)
#   3. Universal patterns (A) + Fed District (B) + Client patterns (C) merge
#   4. Derived variables (D) and functions (E) are computed automatically
#
# To add a new client: add an entry to CLIENT_CONFIGS in Section C.
# Everything else is automatic.
# ===========================================================================

import pandas as pd

# ===========================================================================
# SECTION A: UNIVERSAL COMPETITORS (do not edit)
# ===========================================================================

UNIVERSAL_COMPETITORS = {

    'big_nationals': {
        'starts_with': [
            'BANK OF AMERICA', 'B OF A',
            'WELLS FARGO', 'WELLS FARGO BANK',
            'CHASE BANK', 'CHASE CARD', 'CHASE CREDIT',
            'CHASE PAY', 'CHASE AUTO', 'CHASE MORTGAGE',
            'CHASE TRANSFER', 'CHASE HOME', 'CHASE LOAN',
            'JPMORGAN CHASE',
            'US BANK', 'U.S. BANK',
            'CITIBANK', 'CITI CARD',
            'CAPITAL ONE BANK', 'CAPITAL ONE',
            'USAA',
            'PNC BANK', 'PNC FINANCIAL',
            'TRUIST', 'TRUIST BANK',
            'TD BANK',
        ],
        'exact': [],
    },

    'digital_banks': {
        'starts_with': [
            'CHIME', 'CHIME BANK',
            'SOFI', 'SOFI BANK', 'SOFI MONEY',
            'VARO BANK', 'VARO MONEY',
            'CURRENT MOBILE', 'CURRENT BANK',
            'ALLY BANK', 'ALLY FINANCIAL',
            'DISCOVER BANK', 'DISCOVER SAVINGS',
            'MARCUS BY GOLDMAN', 'MARCUS BANK',
            'REVOLUT',
            'MONZO',
            'N26',
            'GREENLIGHT FINANCIAL',
            'GO2BANK',
            'ONE FINANCE',
            'ASPIRATION',
            'AXOS BANK',
            'SYNCHRONY BANK',
        ],
        'exact': [],
    },
}

UNIVERSAL_ECOSYSTEMS = {

    'wallets': {
        'starts_with': [
            'APPLE PAY', 'APPLE CASH',
            'VENMO',
            'PAYPAL',
            'CASH APP', 'SQUARE CASH',
            'GOOGLE PAY', 'GOOGLE WALLET',
            'SAMSUNG PAY',
        ],
        'exact': [],
    },

    'p2p': {
        'starts_with': [
            'ZELLE',
        ],
        'exact': [],
    },

    'bnpl': {
        'starts_with': [
            'AFFIRM', 'AFFIRM PAYMENT',
            'KLARNA',
            'AFTERPAY',
            'SEZZLE',
            'ZIP PAY', 'QUADPAY',
            'SPLITIT',
        ],
        'exact': [],
    },
}

# ===========================================================================
# SECTION B: FED DISTRICT TOP 25 REGIONALS (do not edit)
# ===========================================================================
# Key = Fed District number (string).
# These are the largest regional/super-regional banks in each district,
# excluding big nationals already covered in Section A.

FED_DISTRICT_TOP_25 = {

    # District 1 -- Boston (CT, MA, ME, NH, RI, VT)
    '1': {
        'starts_with': [
            'CITIZENS BANK', 'CITIZENS FINANCIAL',
            'EASTERN BANK',
            'WEBSTER BANK',
            'ROCKLAND TRUST',
            'BERKSHIRE BANK', 'BERKSHIRE HILLS',
            'BROOKLINE BANK',
            'SANTANDER BANK', 'SANTANDER',
            'LIBERTY BANK',
            'CAMDEN NATIONAL',
            'BANGOR SAVINGS',
            'PEOPLE\'S UNITED', 'PEOPLES UNITED',
            'BAR HARBOR BANK',
            'MASCOMA SAVINGS',
            'NAVIGANT CREDIT UNION',
            'INDEPENDENT BANK',
        ],
        'exact': [],
    },

    # District 2 -- New York (NY, NJ, part of CT)
    '2': {
        'starts_with': [
            'M&T BANK', 'M AND T BANK',
            'VALLEY NATIONAL',
            'FLAGSTAR BANK',
            'NEW YORK COMMUNITY BANK', 'NYCB',
            'COLUMBIA BANK',
            'PROVIDENT BANK',
            'INVESTORS BANK',
            'POPULAR BANK',
            'FLUSHING BANK',
            'DIME COMMUNITY',
            'AMALGAMATED BANK',
            'SIGNATURE BANK',
            'STERLING NATIONAL',
            'CROSS RIVER BANK',
            'OCEANFIRST BANK',
        ],
        'exact': [],
    },

    # District 3 -- Philadelphia (DE, PA, southern NJ)
    '3': {
        'starts_with': [
            'FULTON BANK', 'FULTON FINANCIAL',
            'WSFS BANK', 'WSFS FINANCIAL',
            'CUSTOMERS BANK',
            'UNIVEST BANK',
            'S&T BANK',
            'NORTHWEST BANK', 'NORTHWEST SAVINGS',
            'FIRST KEYSTONE',
            'BRYN MAWR TRUST',
            'REPUBLIC FIRST',
            'OCEANFIRST',
            'NATIONAL PENN',
            'ESL FEDERAL',
            'PARKVALE SAVINGS',
            'FIRST NATIONAL COMMUNITY',
            'RIVERVIEW FINANCIAL',
        ],
        'exact': [],
    },

    # District 4 -- Cleveland (OH, western PA, WV, eastern KY)
    '4': {
        'starts_with': [
            'KEYBANK', 'KEY BANK',
            'HUNTINGTON BANK', 'HUNTINGTON NATIONAL',
            'FIFTH THIRD', 'FIFTH THIRD BANK',
            'FIRST FINANCIAL BANK',
            'WESBANCO',
            'PARK NATIONAL',
            'S&T BANK',
            'OHIO VALLEY BANK',
            'CIVISTA BANK',
            'FIRST FEDERAL SAVINGS',
            'CITY NATIONAL BANK',
            'FARMERS & MERCHANTS',
            'FIRST DEFIANCE',
            'WESTFIELD BANK',
            'FIRST MERIT',
        ],
        'exact': [],
    },

    # District 5 -- Richmond (MD, VA, NC, SC, DC)
    '5': {
        'starts_with': [
            'FIRST CITIZENS BANK',
            'ATLANTIC UNION BANK',
            'LIVE OAK BANK',
            'SOUTH STATE BANK',
            'UNITED BANKSHARES', 'UNITED BANK',
            'SANDY SPRING BANK',
            'PINNACLE FINANCIAL',
            'OLD NATIONAL BANK',
            'FNB CORP', 'FNB BANK',
            'SERVISFIRST',
            'HOWARD BANK',
            'TOWNEBANK',
            'FIRST BANCSHARES',
            'BURKE & HERBERT',
            'NATIONAL BANK OF BLACKSBURG',
        ],
        'exact': [],
    },

    # District 6 -- Atlanta (GA, FL, AL, TN, MS, LA)
    '6': {
        'starts_with': [
            'REGIONS BANK', 'REGIONS FINANCIAL',
            'SYNOVUS', 'SYNOVUS BANK',
            'RENASANT BANK',
            'AMERIS BANK', 'AMERIS BANCORP',
            'HANCOCK WHITNEY',
            'TRUSTMARK BANK', 'TRUSTMARK NATIONAL',
            'SEACOAST BANK', 'SEACOAST BANKING',
            'ORIGIN BANK',
            'PINNACLE FINANCIAL',
            'FIRSTBANK',
            'CENTENNIAL BANK',
            'CADENCE BANK',
            'SOUTHERN FIRST BANK',
            'CENTERSTATE BANK',
            'IBERIA BANK',
        ],
        'exact': [],
    },

    # District 7 -- Chicago (IL, IN, IA, MI, WI)
    '7': {
        'starts_with': [
            'BMO HARRIS', 'BMO BANK',
            'NORTHERN TRUST',
            'WINTRUST', 'WINTRUST BANK',
            'OLD NATIONAL',
            'ASSOCIATED BANK',
            'FIRST BUSEY',
            'HEARTLAND FINANCIAL',
            'QCR HOLDINGS',
            'INDEPENDENT BANK',
            'HILLS BANK',
            'MERCANTILE NATIONAL',
            'FIRST MIDWEST',
            'BYLINE BANK',
            'INLAND BANK',
            'GLACIER BANK',
        ],
        'exact': [],
    },

    # District 8 -- St. Louis (MO, AR, parts of IL/IN/KY/MS/TN)
    '8': {
        'starts_with': [
            'COMMERCE BANK', 'COMMERCE BANCSHARES',
            'SIMMONS BANK', 'SIMMONS FINANCIAL',
            'ARVEST BANK',
            'BOK FINANCIAL',
            'CENTENNIAL BANK',
            'RELYANCE BANK',
            'FIRST SECURITY BANK',
            'BANK OF SPRINGFIELD',
            'REPUBLIC BANK',
            'STOCK YARDS BANK',
            'CENTRAL BANK',
            'SOUTHERN BANCSHARES',
            'HOME FEDERAL SAVINGS',
            'FIRST FEDERAL BANK',
            'GREAT SOUTHERN BANK',
        ],
        'exact': [],
    },

    # District 9 -- Minneapolis (MN, MT, ND, SD, WI)
    '9': {
        'starts_with': [
            'BREMER BANK', 'BREMER FINANCIAL',
            'ALERUS FINANCIAL', 'ALERUS BANK',
            'BELL BANK',
            'GATE CITY BANK',
            'FIRST INTERSTATE BANK',
            'GLACIER BANK', 'GLACIER BANCGROUP',
            'BRIDGEWATER BANK',
            'DACOTAH BANK',
            'GREAT WESTERN BANK',
            'MINNWEST BANK',
            'CHOICE FINANCIAL',
            'WESTERN STATE BANK',
            'STARION FINANCIAL', 'STARION BANK',
            'HEARTLAND FINANCIAL',
            'BORDER BANK',
        ],
        'exact': [],
    },

    # District 10 -- Kansas City (KS, MO, NE, OK, CO, WY, NM)
    '10': {
        'starts_with': [
            'BOK FINANCIAL', 'BANK OF OKLAHOMA',
            'UMB BANK', 'UMB FINANCIAL',
            'MIDFIRST BANK',
            'ARVEST BANK',
            'PINNACLE BANK',
            'FIRST NATIONAL BANK OF OMAHA',
            'FIRSTBANK',
            'ALPINE BANK',
            'VECTRA BANK',
            'GREAT WESTERN BANK',
            'CROSSFIRST BANK',
            'SPIRIT OF TEXAS',
            'ENTERPRISE BANK',
            'CENTRAL BANCOMPANY',
            'INTRUST BANK',
        ],
        'exact': [],
    },

    # District 11 -- Dallas (TX, LA, NM)
    '11': {
        'starts_with': [
            'FROST BANK',
            'PROSPERITY BANK', 'PROSPERITY BANCSHARES',
            'TEXAS CAPITAL BANK',
            'INDEPENDENT FINANCIAL',
            'HILLTOP HOLDINGS', 'HILLTOP BANK',
            'ORIGIN BANK',
            'FIRST HORIZON',
            'GUARANTY BANK',
            'SOUTHSIDE BANK',
            'CROSSFIRST BANK',
            'LONE STAR NATIONAL',
            'VERITEX BANK', 'VERITEX COMMUNITY',
            'INTERNATIONAL BANK OF COMMERCE',
            'GLACIER BANK',
            'HAPPY STATE BANK',
        ],
        'exact': [],
    },

    # District 12 -- San Francisco (CA, OR, WA, NV, AZ, UT, HI, AK, ID)
    '12': {
        'starts_with': [
            'WESTERN ALLIANCE BANK',
            'BANNER BANK',
            'COLUMBIA BANK', 'COLUMBIA BANKING',
            'WASHINGTON FEDERAL',
            'UMPQUA BANK',
            'ZIONS BANK', 'ZIONS BANCORP',
            'EAST WEST BANK',
            'CATHAY BANK',
            'PACIFIC PREMIER BANK',
            'BANC OF CALIFORNIA',
            'HOMESTREET BANK',
            'HERITAGE FINANCIAL',
            'FIRST HAWAIIAN BANK',
            'BANK OF HAWAII',
            'WASHINGTON TRUST BANK',
            'GLACIER BANK',
            'NEVADA STATE BANK',
        ],
        'exact': [],
    },
}

# ===========================================================================
# SECTION C: CLIENT CONFIGS (add new clients here)
# ===========================================================================
# Each key is a CLIENT_ID. The config cell looks up CLIENT_ID and uses:
#   - fed_district: which Fed District top-25 to load
#   - credit_unions: local competing credit unions
#   - local_banks: community/local banks in the market
#   - custom: optional catch-all (defaults to empty)
#
# To onboard a new client: copy an existing entry, change the ID/patterns.

CLIENT_CONFIGS = {

    '1776': {  # CoastHills (Central Coast, CA)
        'fed_district': '12',
        'credit_unions': [
            'SESLOC CREDIT UNION', 'SESLOC CU',
            'SLO CREDIT UNION', 'SLO CU',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
            'GOLDEN 1 CREDIT UNION', 'GOLDEN 1 CU',
            'SCHOOLSFIRST FEDERAL',
            'STAR ONE CREDIT UNION',
            'PATELCO CREDIT UNION',
            'FIRST TECH FEDERAL',
        ],
        'local_banks': [
            'MECHANICS BANK',
            'AMERICAN RIVIERA BANK',
            'COMMUNITY BANK OF SANTA MARIA',
            'BANK OF THE SIERRA',
            'WEST COAST COMMUNITY BANK',
            'SANTA CRUZ COUNTY BANK',
            'BAY COMMERCIAL FINANCE',
        ],
        'custom': [],
        'rollups': {
            'SESLOC CU':        'SESLOC CREDIT UNION',
            'SLO CU':           'SLO CREDIT UNION',
            'NAVY FEDERAL CU':  'NAVY FEDERAL CREDIT UNION',
            'GOLDEN 1 CU':      'GOLDEN 1 CREDIT UNION',
        },
    },
    '1615': {  # Cape & Coast Bank (Cape Cod, MA)
        'fed_district': '1',
        'credit_unions': [
            'FIRST CITIZENS FEDERAL CREDIT UNION', "FIRST CITIZENS' FEDERAL CREDIT UNION",
            'BRIGHTBRIDGE CREDIT UNION', 'MERRIMACK VALLEY CREDIT UNION',
            'ROCKLAND FEDERAL CREDIT UNION',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            'CAPE COD FIVE', 'CAPE COD 5', 'CAPE COD FIVE CENTS',
            'EASTERN BANK',
            'ROCKLAND TRUST',
            'BLUESTONE BANK',
            "SEAMEN'S BANK", 'SEAMENS BANK',
            "MARTHA'S VINEYARD SAVINGS BANK", 'MARTHAS VINEYARD SAVINGS',
            'MV BANK',
        ],
        'custom': [],
        'rollups': {
            'CAPE COD FIVE':            'Cape Cod Five Cents Savings Bank',
            'CAPE COD 5':               'Cape Cod Five Cents Savings Bank',
            'CAPE COD FIVE CENTS':      'Cape Cod Five Cents Savings Bank',
            'SEAMENS BANK':             "SEAMEN'S BANK",
            'MARTHAS VINEYARD SAVINGS': "MARTHA'S VINEYARD SAVINGS BANK",
            'MV BANK':                  "MARTHA'S VINEYARD SAVINGS BANK",
            "FIRST CITIZENS' FEDERAL CREDIT UNION": 'FIRST CITIZENS FEDERAL CREDIT UNION',
            'NAVY FEDERAL CU':          'NAVY FEDERAL CREDIT UNION',
        },
    },

    # Template for new clients -- copy and fill in:
    # 'XXXX': {  # Client Name (Location)
    #     'fed_district': '?',
    #     'credit_unions': [],
    #     'local_banks': [],
    #     'custom': [],
    #     'rollups': {
    #         # Map variant patterns to canonical name:
    #         # 'SOME CU': 'SOME CREDIT UNION',
    #     },
    # },
}

# ===========================================================================
# SECTION D: DERIVED VARIABLES (computed -- do not edit below this line)
# ===========================================================================

# Look up client config (fall back to empty if CLIENT_ID not found)
_client_cfg = CLIENT_CONFIGS.get(CLIENT_ID if 'CLIENT_ID' in dir() else '', {})

CLIENT_FED_DISTRICT = _client_cfg.get('fed_district', '12')

_district_config = FED_DISTRICT_TOP_25.get(
    CLIENT_FED_DISTRICT,
    {'starts_with': [], 'exact': []}
)

# Build client-specific competitor dicts from the config lists
CLIENT_SPECIFIC_COMPETITORS = {
    'credit_unions': {
        'starts_with': _client_cfg.get('credit_unions', []),
        'exact': [],
    },
    'local_banks': {
        'starts_with': _client_cfg.get('local_banks', []),
        'exact': [],
    },
    'custom': {
        'starts_with': _client_cfg.get('custom', []),
        'exact': [],
    },
}

# Merge all sections into COMPETITOR_MERCHANTS for tag_competitors()
COMPETITOR_MERCHANTS = {}
COMPETITOR_MERCHANTS.update(UNIVERSAL_COMPETITORS)
COMPETITOR_MERCHANTS['top_25_fed_district'] = _district_config
COMPETITOR_MERCHANTS.update(UNIVERSAL_ECOSYSTEMS)
COMPETITOR_MERCHANTS.update(CLIENT_SPECIFIC_COMPETITORS)

# Remove empty categories
COMPETITOR_MERCHANTS = {
    k: v for k, v in COMPETITOR_MERCHANTS.items()
    if len(v.get('starts_with', [])) > 0 or len(v.get('exact', [])) > 0
}

# Semantic groupings for downstream cells
TRUE_COMPETITORS = [k for k in COMPETITOR_MERCHANTS if k not in ('wallets', 'p2p', 'bnpl')]
PAYMENT_ECOSYSTEMS = [k for k in COMPETITOR_MERCHANTS if k in ('wallets', 'p2p', 'bnpl')]
BANK_CATEGORIES = list(TRUE_COMPETITORS)
ALL_CATEGORIES = list(COMPETITOR_MERCHANTS.keys())

# ===========================================================================
# SECTION E: DETECTION FUNCTIONS
# ===========================================================================

def tag_competitors(df, merchant_col='merchant_consolidated'):
    """Tag transactions with competitor_category column.

    Memory-optimized for large DataFrames (13M+ rows):
      - Drops old columns + gc.collect() before allocating new ones
      - pd.Categorical for category (~13 MiB vs ~102 MiB object array)
      - numpy arrays in the loop to reduce pandas overhead
      - competitor_match is NOT stored here (saves 102 MiB); derive it
        downstream on the filtered competitor subset instead
    """
    import re, gc
    import numpy as np

    # Free memory from any previous run
    for col in ('competitor_category', 'competitor_match'):
        if col in df.columns:
            df.drop(columns=col, inplace=True)
    gc.collect()

    n = len(df)
    merchant_upper = df[merchant_col].astype(str).str.upper().str.strip()

    tagged = np.zeros(n, dtype=bool)
    cat_names = list(COMPETITOR_MERCHANTS.keys())
    cat_codes = np.full(n, -1, dtype=np.int8)  # -1 -> NaN in Categorical

    for cat_idx, (category, patterns) in enumerate(COMPETITOR_MERCHANTS.items()):
        sw = [p.upper().strip() for p in patterns.get('starts_with', []) if p.strip()]
        ex = [p.upper().strip() for p in patterns.get('exact', []) if p.strip()]

        cat_mask = np.zeros(n, dtype=bool)

        if sw:
            regex = '^(?:' + '|'.join(re.escape(p) for p in sw) + ')'
            cat_mask |= merchant_upper.str.match(regex, na=False).values

        if ex:
            cat_mask |= merchant_upper.isin(ex).values

        new_hits = cat_mask & ~tagged
        if new_hits.any():
            cat_codes[new_hits] = cat_idx
            tagged |= new_hits

    # Free the large uppercase Series (~250 MiB) before allocating results
    del merchant_upper, tagged
    gc.collect()

    # Categorical column: ~13 MiB (int8 codes) vs ~102 MiB (object array)
    # from_codes treats -1 as NaN automatically
    df['competitor_category'] = pd.Categorical.from_codes(
        cat_codes, categories=cat_names
    )
    del cat_codes
    gc.collect()

    return df


_FINANCIAL_KEYWORDS = [
    'BANK', 'BANKING', 'CREDIT UNION', 'CU ', 'FEDERAL CREDIT',
    'FINANCIAL', 'SAVINGS', 'LENDING', 'MORTGAGE', 'LOAN',
    'BROKERAGE', 'INVESTMENT', 'TRUST COMPANY',
]

def discover_unmatched_financial(df, merchant_col='merchant_consolidated', top_n=20):
    """Find potential competitors not yet in config."""
    untagged = df[df['competitor_category'].isna()] if 'competitor_category' in df.columns else df

    if len(untagged) == 0:
        return pd.DataFrame()

    merchant_upper = untagged[merchant_col].astype(str).str.upper()
    mask = pd.Series(False, index=untagged.index)
    for kw in _FINANCIAL_KEYWORDS:
        mask = mask | merchant_upper.str.contains(kw, na=False)

    financial_unmatched = untagged[mask]
    if len(financial_unmatched) == 0:
        return pd.DataFrame()

    result = (
        financial_unmatched
        .groupby(merchant_col)
        .agg(
            transactions=('amount', 'count'),
            accounts=('primary_account_num', 'nunique'),
            total_spend=('amount', 'sum'),
        )
        .sort_values('transactions', ascending=False)
        .head(top_n)
        .reset_index()
    )
    return result


# ---------------------------------------------------------------------------
# Name normalization (roll up merchant variants to canonical names)
# ---------------------------------------------------------------------------

# Manual overrides: multiple patterns that should collapse to one name.
# These take priority over auto-matching from COMPETITOR_MERCHANTS.
_MANUAL_ROLLUPS = {
    # Big Nationals
    'JPMORGAN':         'CHASE',
    'BOFA':             'BANK OF AMERICA',
    'B OF A':           'BANK OF AMERICA',
    'U.S. BANK':        'US BANK',
    'CITI CARD':        'CITIBANK',
    'PNC FINANCIAL':    'PNC BANK',
    # Digital Banks
    'ALLY FINANCIAL':   'ALLY BANK',
    'DISCOVER BANK':    'DISCOVER',
    'DISCOVER SAVINGS': 'DISCOVER',
    'DISCOVER CARD':    'DISCOVER',
    'CURRENT MOBILE':   'CURRENT',
    'CURRENT BANK':     'CURRENT',
    'MARCUS BY':        'MARCUS (GOLDMAN SACHS)',
    'MARCUS BANK':      'MARCUS (GOLDMAN SACHS)',
    # Ecosystems
    'SQUARE CASH':      'CASH APP',
    'GOOGLE WALLET':    'GOOGLE PAY',
    # CU abbreviations
    'GOLDEN 1 CU':      'GOLDEN 1 CREDIT UNION',
    'GOLDEN 1':         'GOLDEN 1 CREDIT UNION',
    # Fed District variant patterns (same institution, different name form)
    'CITIZENS FINANCIAL':       'CITIZENS BANK',
    'PEOPLES UNITED':           "PEOPLE'S UNITED",
    'M AND T BANK':             'M&T BANK',
    'NYCB':                     'NEW YORK COMMUNITY BANK',
    'FULTON FINANCIAL':         'FULTON BANK',
    'WSFS FINANCIAL':           'WSFS BANK',
    'NORTHWEST SAVINGS':        'NORTHWEST BANK',
    'KEY BANK':                 'KEYBANK',
    'HUNTINGTON NATIONAL':      'HUNTINGTON BANK',
    'FIFTH THIRD':              'FIFTH THIRD BANK',
    'UNITED BANKSHARES':        'UNITED BANK',
    'FNB CORP':                 'FNB BANK',
    'REGIONS FINANCIAL':        'REGIONS BANK',
    'SYNOVUS BANK':             'SYNOVUS',
    'AMERIS BANCORP':           'AMERIS BANK',
    'TRUSTMARK NATIONAL':       'TRUSTMARK BANK',
    'SEACOAST BANKING':         'SEACOAST BANK',
    'BMO HARRIS':               'BMO BANK',
    'WINTRUST BANK':            'WINTRUST',
    'COMMERCE BANCSHARES':      'COMMERCE BANK',
    'SIMMONS FINANCIAL':        'SIMMONS BANK',
    'BREMER FINANCIAL':         'BREMER BANK',
    'ALERUS BANK':              'ALERUS FINANCIAL',
    'GLACIER BANCGROUP':        'GLACIER BANK',
    'STARION BANK':             'STARION FINANCIAL',
    'BANK OF OKLAHOMA':         'BOK FINANCIAL',
    'UMB FINANCIAL':            'UMB BANK',
    'PROSPERITY BANCSHARES':    'PROSPERITY BANK',
    'VERITEX COMMUNITY':        'VERITEX BANK',
    'COLUMBIA BANKING':         'COLUMBIA BANK',
    'ZIONS BANCORP':            'ZIONS BANK',
}

# Merge client-specific rollups (abbreviation variants like "CAPE COD 5" -> "CAPE COD FIVE")
for _pattern, _canonical in _client_cfg.get('rollups', {}).items():
    _MANUAL_ROLLUPS[_pattern.upper().strip()] = _canonical

# Build auto-match lookup from COMPETITOR_MERCHANTS config.
# Every starts_with pattern becomes a rollup entry mapping to itself.
# Sorted longest-first so "CHASE BANK" matches before "CHASE".
_AUTO_ROLLUPS = []
for _cat, _pats in COMPETITOR_MERCHANTS.items():
    for _p in _pats.get('starts_with', []):
        _p_upper = _p.upper().strip()
        if _p_upper:
            _AUTO_ROLLUPS.append((_p_upper, _p.strip()))
_AUTO_ROLLUPS.sort(key=lambda x: len(x[0]), reverse=True)

# Prefix-based dedup: if one canonical name starts with another, collapse
# to the shorter one. E.g., "SANTANDER BANK" -> "SANTANDER" because both
# are patterns and "SANTANDER BANK" starts with "SANTANDER".
_auto_canonicals = sorted(set(name for _, name in _AUTO_ROLLUPS), key=len)
_prefix_collapse = {}
for _i, _short in enumerate(_auto_canonicals):
    _short_u = _short.upper()
    for _long in _auto_canonicals[_i + 1:]:
        if _long.upper().startswith(_short_u) and _long not in _prefix_collapse:
            _prefix_collapse[_long] = _short
_AUTO_ROLLUPS = [
    (prefix, _prefix_collapse.get(name, name)) for prefix, name in _AUTO_ROLLUPS
]


def normalize_competitor_name(bank_name: str) -> str:
    """Roll up variant merchant names to a single canonical name.

    Two-layer matching:
      1. Manual overrides (ALLY FINANCIAL -> ALLY BANK, etc.)
      2. Auto-match from COMPETITOR_MERCHANTS config patterns
         (CITIZENS BANK ONLINE -> CITIZENS BANK, etc.)

    This ensures every tagged merchant resolves to the config pattern
    that matched it, not the raw merchant string with random suffixes.
    """
    if not isinstance(bank_name, str):
        return bank_name
    name_u = bank_name.upper().strip()

    # Layer 1: manual overrides (highest priority)
    for prefix, canonical in _MANUAL_ROLLUPS.items():
        if name_u.startswith(prefix):
            return canonical

    # Layer 2: auto-match against all config patterns (longest match wins)
    for prefix, canonical in _AUTO_ROLLUPS:
        if name_u.startswith(prefix):
            return canonical

    return bank_name.strip()


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------
def clean_category(cat_str):
    """'big_nationals' -> 'Big Nationals', 'top_25_fed_district' -> 'Top 25 Fed District'"""
    if not isinstance(cat_str, str):
        return str(cat_str)
    return cat_str.replace('_', ' ').title()

def get_cat_color(cat_label):
    """Return palette color for a cleaned category label.
    CATEGORY_PALETTE must be defined in 06_conference_theme before use."""
    return CATEGORY_PALETTE.get(cat_label, GEN_COLORS['muted']) if 'CATEGORY_PALETTE' in dir() else GEN_COLORS['muted']

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
_client_name = CLIENT_NAME if 'CLIENT_NAME' in dir() else 'Unknown'
total_patterns = sum(
    len(v.get('starts_with', [])) + len(v.get('exact', []))
    for v in COMPETITOR_MERCHANTS.values()
)

print(f"Competitor config loaded for {_client_name} (Fed District {CLIENT_FED_DISTRICT}):")
print(f"  Categories: {len(COMPETITOR_MERCHANTS)}  |  Patterns: {total_patterns}")
print(f"  True competitors: {len(TRUE_COMPETITORS)}  |  Payment ecosystems: {len(PAYMENT_ECOSYSTEMS)}")
for cat in ALL_CATEGORIES:
    n = len(COMPETITOR_MERCHANTS[cat].get('starts_with', [])) + len(COMPETITOR_MERCHANTS[cat].get('exact', []))
    label = cat.replace('_', ' ').title()
    print(f"    {label:25s} {n:>3} patterns")
