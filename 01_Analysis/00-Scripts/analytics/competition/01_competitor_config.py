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

import os
import pandas as pd

# ---------------------------------------------------------------------------
# SLIDE_MODE: controls deck size for competition section.
#   'standard' (default) -- core 7/8/9/11/13/15/16/31/32/33 story  (~25 slides)
#   'deep'               -- full section including all segment/wallet/banks-only
#                            parallel views (~89 slides)
#   'minimal'            -- just top-10 + category donut + momentum (~10 slides)
#
# Configured via SLIDE_MODE env var so the UI can expose it per-client.
# Ignored when the section doesn't have a curated prune list defined here.
# ---------------------------------------------------------------------------
SLIDE_MODE = os.environ.get('SLIDE_MODE', 'standard').lower()

# Competition-section prune lists. Prefix match on script stem. The 60-series
# is two PARALLEL recuts of cells 07/08/09/65 (banks-only + core-competition
# minus ecosystems). 66/67 are ecosystem deep-dives. 70 is a head-to-head
# comparison chart. All valuable but duplicative for a client exec review.
# 18, 20-24 are segment slices -- kept in 'deep' only.
#
# The per-competitor deep-dive cells (25 at-risk, 26 spend scatter,
# 28 spend-vs-frequency, 29 wallet share -- one slide per DEEP_DIVE_TOP_N
# competitor, ~32-45 slides) were DELETED outright (owner decision
# 2026-06-11). The category-level segmentation (21-24) and the per-
# competitor cross-sell CSV exports (41) are the surviving surfaces for
# that analysis.
_PRUNE_BY_MODE = {
    'standard': [
        '18_', '20_', '21_', '22_', '23_', '24_',
        '60_', '61_', '62_', '65_', '66_', '67_', '70_',
    ],
    'minimal': [
        '10_', '11_', '12_', '13_', '14_', '17_', '18_', '19_',
        '20_', '21_', '22_', '23_', '24_', '27_', '30_', '40_', '41_',
        '60_', '61_', '62_', '65_', '66_', '67_', '68_', '70_',
    ],
    'deep': [],
}
SKIP_SCRIPT_PATTERNS = _PRUNE_BY_MODE.get(SLIDE_MODE, [])
if SKIP_SCRIPT_PATTERNS:
    print(f"    SLIDE_MODE={SLIDE_MODE}: pruning {len(SKIP_SCRIPT_PATTERNS)} "
          f"competition cell patterns to control deck size")
elif SLIDE_MODE == 'deep':
    print(f"    SLIDE_MODE=deep: running ALL competition cells (~89 slides)")

# ===========================================================================
# SECTION A: UNIVERSAL COMPETITORS (do not edit)
# ===========================================================================

UNIVERSAL_COMPETITORS = {

    'big_nationals': {
        'starts_with': [
            # Bank of America — full + short forms
            'BANK OF AMERICA', 'B OF A', 'BOFA', 'BAC HOME LOANS',
            # Wells Fargo — full + collapsed (consolidation drops BANK token)
            'WELLS FARGO', 'WELLS FARGO BANK', 'WELLS FARGO HM', 'WFB',
            # Chase / JPMorgan — full + collapsed forms.
            # standardize_merchant_name collapses 'CHASE BANK …' -> 'CHASE'
            # so we MUST have 'CHASE' alone here (safe with \b — won't match PURCHASE).
            'CHASE', 'CHASE BANK', 'CHASE CARD', 'CHASE CREDIT',
            'CHASE PAY', 'CHASE AUTO', 'CHASE MORTGAGE',
            'CHASE TRANSFER', 'CHASE HOME', 'CHASE LOAN',
            'CHASE CC',
            'JPMORGAN', 'JPMORGAN CHASE', 'JPM CHASE', 'JP MORGAN',
            # US Bank
            'US BANK', 'U.S. BANK', 'USB CARDMEMBER',
            # Citi
            'CITIBANK', 'CITI CARD', 'CITICARDS', 'CITI', 'CITIGROUP',
            # Capital One
            'CAPITAL ONE BANK', 'CAPITAL ONE', 'CAPITALONE',
            'CAP ONE', 'CAPONE',
            # USAA
            'USAA', 'USAA FSB', 'USAA SVNGS', 'USAA SAVINGS', 'USAA FED SAV',
            # PNC — full + collapsed
            'PNC', 'PNC BANK', 'PNC FINANCIAL',
            # Truist (BB&T + SunTrust merger)
            'TRUIST', 'TRUIST BANK', 'BB&T', 'BBT', 'SUNTRUST',
            # TD Bank
            'TD BANK', 'TD BANK NA',
        ],
        'exact': [],
    },

    'digital_banks': {
        'starts_with': [
            'CHIME', 'CHIME BANK', 'CHIME MEMBER',
            'SOFI', 'SOFI BANK', 'SOFI MONEY', 'SOFI FINANCE', 'SOFI LENDING',
            'VARO', 'VARO BANK', 'VARO MONEY',
            'CURRENT MOBILE', 'CURRENT BANK', 'CURRENT FINANCIAL',
            'ALLY', 'ALLY BANK', 'ALLY FINANCIAL',
            'DISCOVER BANK', 'DISCOVER SAVINGS', 'DISCOVER CARD', 'DISCOVER',
            # NOTE: do NOT add 'MARCUS' bare — it false-positives on NEIMAN MARCUS.
            'MARCUS BY GOLDMAN', 'MARCUS BANK', 'MARCUS PMT', 'MARCUS GOLDMAN',
            'REVOLUT',
            'MONZO',
            'N26',
            'GREENLIGHT FINANCIAL', 'GREENLIGHT CARD',
            'GO2BANK', 'GO 2 BANK',
            'ONE FINANCE',
            'ASPIRATION', 'ASPIRATION BANK',
            'AXOS BANK', 'AXOS FINANCIAL',
            'SYNCHRONY BANK', 'SYNCHRONY',
            'DAVE INC', 'DAVE BANKING',
            'OXYGEN BANK',
            'STEP MOBILE',
            'COPPER BANK',
            'EQ BANK',
        ],
        'exact': [],
    },
}

UNIVERSAL_ECOSYSTEMS = {

    'wallets': {
        'starts_with': [
            'APPLE PAY', 'APPLE CASH', 'APPLE COM BILL',
            'VENMO', 'VENMO PAYMENT', 'VENMO CASHOUT',
            'PAYPAL', 'PAYPAL INST XFER', 'PAYPAL TRANSFER',
            'CASH APP', 'CASHAPP', 'SQUARE CASH', 'SQUARE INC',
            'GOOGLE PAY', 'GOOGLE WALLET', 'GOOGLE PAYMENT',
            'SAMSUNG PAY',
            'WISE COM', 'WISE US',
            'PAYONEER',
            'SKRILL',
        ],
        'exact': [],
    },

    'p2p': {
        'starts_with': [
            'ZELLE', 'ZELLE TRANSFER', 'ZELLE PAYMENT',
            'POPMONEY',
        ],
        'exact': [],
    },

    'bnpl': {
        'starts_with': [
            'AFFIRM', 'AFFIRM PAYMENT', 'AFFIRM INC',
            'KLARNA', 'KLARNA PAYMENT', 'KLARNA INC',
            'AFTERPAY', 'AFTERPAY US',
            'SEZZLE', 'SEZZLE INC',
            'ZIP PAY', 'ZIP US', 'QUADPAY',
            'SPLITIT',
            'PAYBRIGHT',
            'PERPAY',
            'BREAD FINANCIAL', 'BREAD PAYMENTS',
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
            'REGIONS BANK', 'REGIONS FINANCIAL', 'REGIONS BK',
            'SYNOVUS', 'SYNOVUS BANK', 'SYNOVUS BK',
            'RENASANT BANK', 'RENASANT BK',
            'AMERIS BANK', 'AMERIS BANCORP', 'AMERIS BK',
            'HANCOCK WHITNEY', 'HANCOCK WHITNEY BANK',
            'TRUSTMARK BANK', 'TRUSTMARK NATIONAL', 'TRUSTMARK NB',
            'SEACOAST BANK', 'SEACOAST BANKING', 'SEACOAST NATL',
            'ORIGIN BANK',
            'PINNACLE FINANCIAL', 'PINNACLE BANK',
            'FIRSTBANK', 'FIRST BK',
            'CENTENNIAL BANK',
            'CADENCE BANK', 'CADENCE BK',
            'SOUTHERN FIRST BANK',
            'CENTERSTATE BANK',
            'IBERIA BANK', 'IBERIABANK',
            'PROSPERITY BANCSHARES',
            'SOUTHSIDE BANK', 'SOUTH SIDE BK',
            'FIRST HORIZON BANK', 'FIRST HORIZON',
            'TRUIST BANK', 'TRUIST',          # Truist HQ Charlotte but covers SE
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
'1441': {  # First National Bank Alaska (Anchorage, AK)
        'fed_district': '12',
        'credit_unions': [
            # Alaska USA FCU rebranded to Global Credit Union; largest CU in AK
            'GLOBAL CREDIT UNION', 'GLOBAL FEDERAL CREDIT UNION', 'GLOBAL FCU', 'GLOBAL CU',
            'ALASKA USA FEDERAL CREDIT UNION', 'ALASKA USA FCU', 'ALASKA USA',
            # Credit Union 1 absorbed MAC FCU in 2025-2026 merger
            'CREDIT UNION 1', 'CU1',
            'MAC FEDERAL CREDIT UNION', 'MAC FCU',
            # Southeast AK -- True North dominant in Juneau; Tongass dominant in Ketchikan
            'TRUE NORTH FEDERAL CREDIT UNION', 'TRUE NORTH FCU', 'TRUE NORTH CU',
            'TONGASS FEDERAL CREDIT UNION', 'TONGASS FCU',
            # Interior AK -- Fairbanks
            'SPIRIT OF ALASKA FEDERAL CREDIT UNION', 'SPIRIT OF ALASKA FCU', 'SPIRIT OF ALASKA',
            # Anchorage / Mat-Su locals
            'NORTHERN SKIES FEDERAL CREDIT UNION', 'NORTHERN SKIES FCU',
            'MATANUSKA VALLEY FEDERAL CREDIT UNION', 'MATANUSKA VALLEY FCU', 'MVFCU',
            # Multi-state CU with AK branches
            'NUVISION FEDERAL CREDIT UNION', 'NUVISION CREDIT UNION', 'NUVISION FCU',
            # Heavy military presence (JBER, Eielson AFB, Fort Wainwright)
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            # KeyBank lives in District 4, not District 12 -- add explicitly for AK
            'KEYBANK', 'KEY BANK',
            # AK community banks not in Section B District 12 list
            'NORTHRIM BANK',                       # Anchorage HQ; ~17 branches statewide
            'MT. MCKINLEY BANK', 'MT MCKINLEY BANK', 'MOUNT MCKINLEY BANK',  # Fairbanks
            'DENALI STATE BANK',                   # Acquired by Global CU 2025; may persist in tx data
            'FIRST BANK',                          # Ketchikan HQ; Southeast AK -- watch for FP w/ FIRST BANK [other state]
        ],
        'custom': [],
        'rollups': {
            # --- Alaska USA -> Global Credit Union (rebrand) ---
            'GLOBAL FEDERAL CREDIT UNION':           'GLOBAL CREDIT UNION',
            'GLOBAL FCU':                            'GLOBAL CREDIT UNION',
            'GLOBAL CU':                             'GLOBAL CREDIT UNION',
            'ALASKA USA FEDERAL CREDIT UNION':       'GLOBAL CREDIT UNION',
            'ALASKA USA FCU':                        'GLOBAL CREDIT UNION',
            'ALASKA USA':                            'GLOBAL CREDIT UNION',
            # --- MAC FCU -> Credit Union 1 (2025-2026 merger) ---
            'MAC FEDERAL CREDIT UNION':              'CREDIT UNION 1',
            'MAC FCU':                               'CREDIT UNION 1',
            'CU1':                                   'CREDIT UNION 1',
            # --- CU abbreviation variants ---
            'TRUE NORTH FEDERAL CREDIT UNION':       'TRUE NORTH FCU',
            'TRUE NORTH CU':                         'TRUE NORTH FCU',
            'TONGASS FEDERAL CREDIT UNION':          'TONGASS FCU',
            'SPIRIT OF ALASKA FEDERAL CREDIT UNION': 'SPIRIT OF ALASKA FCU',
            'SPIRIT OF ALASKA':                      'SPIRIT OF ALASKA FCU',
            'NORTHERN SKIES FEDERAL CREDIT UNION':   'NORTHERN SKIES FCU',
            'MATANUSKA VALLEY FEDERAL CREDIT UNION': 'MATANUSKA VALLEY FCU',
            'MVFCU':                                 'MATANUSKA VALLEY FCU',
            'NUVISION FEDERAL CREDIT UNION':         'NUVISION CREDIT UNION',
            'NUVISION FCU':                          'NUVISION CREDIT UNION',
            'NAVY FEDERAL CU':                       'NAVY FEDERAL CREDIT UNION',
            # --- Local bank variants ---
            'KEY BANK':                              'KEYBANK',
            'MT MCKINLEY BANK':                      'MT. MCKINLEY BANK',
            'MOUNT MCKINLEY BANK':                   'MT. MCKINLEY BANK',
        },
    },
    '1759': {  # First Central Credit Union (Waco, TX)
        'fed_district': '11',  # Dallas -- TX/LA/NM (was silently defaulting to '12' SF)
        'credit_unions': [
            # --- Waco / Central Texas locals ---
            'GENCO FEDERAL CREDIT UNION', 'GENCO FCU', 'GENCO',          # Waco HQ -- top local CU
            'MEMBERS CHOICE OF CENTRAL TEXAS',
            'MEMBERS CHOICE OF CENTRAL TEXAS FEDERAL CREDIT UNION',
            'TEXELL CREDIT UNION', 'TEXELL CU', 'TEXELL',                # Woodway / Temple
            'EDUCATORS CREDIT UNION', 'EDUCATORS CU',                    # Waco
            '1ST UNIVERSITY CREDIT UNION', 'FIRST UNIVERSITY CREDIT UNION', '1ST UNIVERSITY CU',
            'GREATER CENTRAL TEXAS FEDERAL CREDIT UNION', 'GREATER CENTRAL TEXAS FCU',  # Killeen
            # --- Large statewide CUs commonly seen in Central TX member data ---
            'RANDOLPH-BROOKS FEDERAL CREDIT UNION', 'RANDOLPH BROOKS', 'RBFCU',
            'UNIVERSITY FEDERAL CREDIT UNION', 'UFCU',
            'TEXAS DOW EMPLOYEES CREDIT UNION', 'TDECU',
            'SECURITY SERVICE FEDERAL CREDIT UNION', 'SECURITY SERVICE FCU', 'SSFCU',
            # Heavy military presence nearby (Fort Cavazos / Killeen)
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            # Waco-area community banks NOT already in the District 11 top-25
            'CENTRAL NATIONAL BANK',                                     # Waco's leading independent bank
            'EXTRACO BANKS', 'EXTRACO BANK', 'EXTRACO',                  # Temple / Waco
            'TFNB', 'TFNB YOUR BANK FOR LIFE',
            'FIRST NATIONAL BANK OF MCGREGOR', 'THE FIRST NATIONAL BANK OF MCGREGOR',
            'ALLIANCE BANK CENTRAL TEXAS',                              # Woodway
            'COMMUNITY BANK & TRUST', 'COMMUNITY BANK AND TRUST',        # Waco
            'FIRST NATIONAL BANK OF CENTRAL TEXAS', 'FNBCT',
            'FIRST NATIONAL BANK TEXAS', 'FIRST CONVENIENCE BANK',       # Killeen HQ; heavy HEB retail footprint
            'AMERICAN BANK',                                             # Waco -- generic name, watch for out-of-market FPs
        ],
        'custom': [],
        'rollups': {
            # --- CU abbreviation / variant rollups ---
            'GENCO FCU':                                            'GENCO FEDERAL CREDIT UNION',
            'GENCO':                                                'GENCO FEDERAL CREDIT UNION',
            'MEMBERS CHOICE OF CENTRAL TEXAS FEDERAL CREDIT UNION': 'MEMBERS CHOICE OF CENTRAL TEXAS',
            'TEXELL CU':                                            'TEXELL CREDIT UNION',
            'TEXELL':                                               'TEXELL CREDIT UNION',
            'EDUCATORS CU':                                         'EDUCATORS CREDIT UNION',
            'FIRST UNIVERSITY CREDIT UNION':                        '1ST UNIVERSITY CREDIT UNION',
            '1ST UNIVERSITY CU':                                    '1ST UNIVERSITY CREDIT UNION',
            'GREATER CENTRAL TEXAS FCU':                            'GREATER CENTRAL TEXAS FEDERAL CREDIT UNION',
            'RANDOLPH BROOKS':                                      'RANDOLPH-BROOKS FEDERAL CREDIT UNION',
            'RBFCU':                                                'RANDOLPH-BROOKS FEDERAL CREDIT UNION',
            'UFCU':                                                 'UNIVERSITY FEDERAL CREDIT UNION',
            'TDECU':                                                'TEXAS DOW EMPLOYEES CREDIT UNION',
            'SECURITY SERVICE FCU':                                 'SECURITY SERVICE FEDERAL CREDIT UNION',
            'SSFCU':                                                'SECURITY SERVICE FEDERAL CREDIT UNION',
            'NAVY FEDERAL CU':                                      'NAVY FEDERAL CREDIT UNION',
            # --- Local bank variant rollups ---
            'EXTRACO BANK':                                         'EXTRACO BANKS',
            'EXTRACO':                                              'EXTRACO BANKS',
            'TFNB YOUR BANK FOR LIFE':                              'TFNB',
            'FIRST NATIONAL BANK OF MCGREGOR':                      'TFNB',
            'THE FIRST NATIONAL BANK OF MCGREGOR':                  'TFNB',
            'COMMUNITY BANK AND TRUST':                             'COMMUNITY BANK & TRUST',
            'FNBCT':                                                'FIRST NATIONAL BANK OF CENTRAL TEXAS',
            'FIRST CONVENIENCE BANK':                               'FIRST NATIONAL BANK TEXAS',
        },
    },
    '1226': {  # Ellafi Federal Credit Union (formerly Seasons FCU) -- Middletown, CT
        'fed_district': '1',  # Boston -- central CT (Middlesex County)
        'credit_unions': [
            'AMERICAN EAGLE FINANCIAL CREDIT UNION', 'AMERICAN EAGLE CREDIT UNION',
            'AMERICAN EAGLE FCU', 'AEFCU',                       # CT's largest community CU; serves Middlesex
            'CONNEX CREDIT UNION', 'CONNEX CU',                  # North Haven; serves Middlesex
            'NUTMEG STATE FINANCIAL CREDIT UNION', 'NUTMEG STATE CREDIT UNION', 'NUTMEG STATE CU',
            'DUTCH POINT CREDIT UNION', 'DUTCH POINT CU',        # Wethersfield; absorbed MidConn of Middletown
            'CHARTER OAK FEDERAL CREDIT UNION', 'CHARTER OAK FCU',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            'LIBERTY BANK',                                      # Middletown HQ -- 3rd largest CT bank
            'WEBSTER BANK',
            'ION BANK',
            'THOMASTON SAVINGS BANK',
            'CHELSEA GROTON BANK',
        ],
        'custom': [],
        'rollups': {
            'AMERICAN EAGLE CREDIT UNION':       'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'AMERICAN EAGLE FCU':                'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'AEFCU':                             'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'CONNEX CU':                         'CONNEX CREDIT UNION',
            'NUTMEG STATE CREDIT UNION':         'NUTMEG STATE FINANCIAL CREDIT UNION',
            'NUTMEG STATE CU':                   'NUTMEG STATE FINANCIAL CREDIT UNION',
            'DUTCH POINT CU':                    'DUTCH POINT CREDIT UNION',
            'CHARTER OAK FCU':                   'CHARTER OAK FEDERAL CREDIT UNION',
            'NAVY FEDERAL CU':                   'NAVY FEDERAL CREDIT UNION',
        },
    },
    '1746': {  # PrimeTrust Federal Credit Union -- Muncie, IN
        'fed_district': '7',  # Chicago -- covers Indiana
        'credit_unions': [
            'BALL STATE FEDERAL CREDIT UNION', 'BALL STATE FCU',  # Muncie / Ball State
            'INDIANA MEMBERS CREDIT UNION', 'IMCU',               # Muncie branch
            'PROFED CREDIT UNION', 'PROFED FEDERAL CREDIT UNION', 'PROFED FCU',
            'FORUM CREDIT UNION', 'FORUM CU',
            'CENTRA CREDIT UNION', 'CENTRA CU',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            'FIRST MERCHANTS BANK', 'FIRST MERCHANTS',            # Muncie HQ -- dominant Central IN bank
            'MUTUALBANK', 'MUTUAL BANK',                          # Muncie HQ legacy (acq. Northwest 2020)
            'NORTHWEST BANK',
            'OLD NATIONAL BANK',
            'STAR FINANCIAL BANK', 'STAR BANK',
        ],
        'custom': [],
        'rollups': {
            'BALL STATE FCU':            'BALL STATE FEDERAL CREDIT UNION',
            'IMCU':                      'INDIANA MEMBERS CREDIT UNION',
            'PROFED FEDERAL CREDIT UNION': 'PROFED CREDIT UNION',
            'PROFED FCU':                'PROFED CREDIT UNION',
            'FORUM CU':                  'FORUM CREDIT UNION',
            'CENTRA CU':                 'CENTRA CREDIT UNION',
            'NAVY FEDERAL CU':           'NAVY FEDERAL CREDIT UNION',
            'FIRST MERCHANTS':           'FIRST MERCHANTS BANK',
            'MUTUAL BANK':               'MUTUALBANK',
            'STAR BANK':                 'STAR FINANCIAL BANK',
        },
    },
    '1217': {  # Pioneer Federal Credit Union -- Mountain Home, ID
        'fed_district': '12',  # San Francisco -- covers Idaho
        'credit_unions': [
            'IDAHO CENTRAL CREDIT UNION', 'ICCU',                 # dominant ID CU; Mountain Home branch
            'CAPED CREDIT UNION', 'CAP ED CREDIT UNION', 'CAPED CU',
            'ICON CREDIT UNION', 'ICON CU',
            'WESTMARK CREDIT UNION', 'WESTMARK CU',
            'MOUNTAIN AMERICA CREDIT UNION', 'MOUNTAIN AMERICA CU', 'MACU',
            'NORTHWEST CHRISTIAN CREDIT UNION',                   # Mountain Home
            'CLARITY CREDIT UNION',                               # Meridian
        ],
        'local_banks': [
            # Treasure Valley locals NOT already in the District 12 top-25
            'D.L. EVANS BANK', 'DL EVANS BANK', 'D L EVANS BANK',
            'BANK OF IDAHO',
            'IDAHO FIRST BANK',
            'IDAHO INDEPENDENT BANK',                             # legacy (merged into First Interstate)
            'FIRST INTERSTATE BANK',
        ],
        'custom': [],
        'rollups': {
            'ICCU':                      'IDAHO CENTRAL CREDIT UNION',
            'CAP ED CREDIT UNION':       'CAPED CREDIT UNION',
            'CAPED CU':                  'CAPED CREDIT UNION',
            'ICON CU':                   'ICON CREDIT UNION',
            'WESTMARK CU':               'WESTMARK CREDIT UNION',
            'MOUNTAIN AMERICA CU':       'MOUNTAIN AMERICA CREDIT UNION',
            'MACU':                      'MOUNTAIN AMERICA CREDIT UNION',
            'DL EVANS BANK':             'D.L. EVANS BANK',
            'D L EVANS BANK':            'D.L. EVANS BANK',
        },
    },
    '1780': {  # USF Federal Credit Union (now USF CU) -- Tampa, FL
        'fed_district': '6',  # Atlanta -- covers Florida
        'credit_unions': [
            'SUNCOAST CREDIT UNION', 'SUNCOAST CU', 'SUNCOAST SCHOOLS FEDERAL CREDIT UNION',  # Tampa HQ; FL's largest
            'GTE FINANCIAL', 'GTE FEDERAL CREDIT UNION', 'GTE FCU',  # Tampa HQ
            'GROW FINANCIAL FEDERAL CREDIT UNION', 'GROW FINANCIAL', 'GROW FINANCIAL FCU',  # Tampa HQ
            'ACHIEVA CREDIT UNION', 'ACHIEVA CU',
            'MIDFLORIDA CREDIT UNION', 'MIDFLORIDA CU', 'MID FLORIDA CREDIT UNION',
            'VYSTAR CREDIT UNION', 'VYSTAR CU',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',      # MacDill AFB
        ],
        'local_banks': [
            'THE BANK OF TAMPA', 'BANK OF TAMPA',                # Tampa HQ community bank
            'AMERANT BANK', 'AMERANT',
            'SEACOAST BANK', 'SEACOAST NATIONAL BANK',
            'SOUTHSTATE BANK', 'SOUTH STATE BANK',
            'RAYMOND JAMES BANK',                               # St. Petersburg
        ],
        'custom': ['USAA'],                                     # MacDill AFB military presence
        'rollups': {
            'SUNCOAST CU':                          'SUNCOAST CREDIT UNION',
            'SUNCOAST SCHOOLS FEDERAL CREDIT UNION': 'SUNCOAST CREDIT UNION',
            'GTE FEDERAL CREDIT UNION':             'GTE FINANCIAL',
            'GTE FCU':                              'GTE FINANCIAL',
            'GROW FINANCIAL FCU':                   'GROW FINANCIAL FEDERAL CREDIT UNION',
            'GROW FINANCIAL':                       'GROW FINANCIAL FEDERAL CREDIT UNION',
            'ACHIEVA CU':                           'ACHIEVA CREDIT UNION',
            'MIDFLORIDA CU':                        'MIDFLORIDA CREDIT UNION',
            'MID FLORIDA CREDIT UNION':             'MIDFLORIDA CREDIT UNION',
            'VYSTAR CU':                            'VYSTAR CREDIT UNION',
            'NAVY FEDERAL CU':                      'NAVY FEDERAL CREDIT UNION',
            'BANK OF TAMPA':                        'THE BANK OF TAMPA',
            'AMERANT':                              'AMERANT BANK',
            'SEACOAST NATIONAL BANK':               'SEACOAST BANK',
            'SOUTH STATE BANK':                     'SOUTHSTATE BANK',
        },
    },
    '1766': {  # Fort Sill Federal Credit Union -- Lawton, OK (Army post)
        'fed_district': '10',  # Kansas City -- covers Oklahoma
        'credit_unions': [
            'COMANCHE COUNTY FEDERAL CREDIT UNION', 'COMANCHE COUNTY FCU',  # Lawton
            'SOUTHWEST OKLAHOMA FEDERAL CREDIT UNION', 'SOUTHWEST OKLAHOMA FCU',  # Lawton
            'TINKER FEDERAL CREDIT UNION', 'TINKER FCU', 'TFCU',  # OK's largest CU
            'COMMUNICATION FEDERAL CREDIT UNION', 'COMMUNICATION FCU',
            'WEOKIE CREDIT UNION', 'WEOKIE FEDERAL CREDIT UNION', 'WEOKIE',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            # NOTE: FSNB / Fort Sill National Bank is a SEPARATE institution from the
            # client (Fort Sill FEDERAL CREDIT UNION). Full-string patterns only -- never
            # a bare 'FORT SILL' that would match the client against itself.
            'FSNB', 'FORT SILL NATIONAL BANK',                  # Lawton HQ
            'CITY NATIONAL BANK & TRUST', 'CITY NATIONAL BANK AND TRUST',  # Lawton
            'LIBERTY NATIONAL BANK',                            # Lawton
            'FIRST NATIONAL BANK & TRUST', 'FIRST NATIONAL BANK AND TRUST',  # Lawton
            'ARVEST BANK',
            'BANCFIRST',
            'BANK OF OKLAHOMA', 'BOK FINANCIAL', 'BOKF',
            'IBC BANK', 'INTERNATIONAL BANK OF COMMERCE',
        ],
        'custom': ['USAA'],                                     # Fort Sill Army post military presence
        'rollups': {
            'COMANCHE COUNTY FCU':       'COMANCHE COUNTY FEDERAL CREDIT UNION',
            'SOUTHWEST OKLAHOMA FCU':    'SOUTHWEST OKLAHOMA FEDERAL CREDIT UNION',
            'TINKER FCU':                'TINKER FEDERAL CREDIT UNION',
            'TFCU':                      'TINKER FEDERAL CREDIT UNION',
            'COMMUNICATION FCU':         'COMMUNICATION FEDERAL CREDIT UNION',
            'WEOKIE FEDERAL CREDIT UNION': 'WEOKIE CREDIT UNION',
            'WEOKIE':                    'WEOKIE CREDIT UNION',
            'NAVY FEDERAL CU':           'NAVY FEDERAL CREDIT UNION',
            'FORT SILL NATIONAL BANK':   'FSNB',
            'CITY NATIONAL BANK AND TRUST': 'CITY NATIONAL BANK & TRUST',
            'FIRST NATIONAL BANK AND TRUST': 'FIRST NATIONAL BANK & TRUST',
            'BOK FINANCIAL':             'BANK OF OKLAHOMA',
            'BOKF':                      'BANK OF OKLAHOMA',
            'INTERNATIONAL BANK OF COMMERCE': 'IBC BANK',
        },
    },
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
    '1200': {  # Guardians Credit Union (South Florida)
        'fed_district': '6',
        'credit_unions': [
            # Tropical Financial CU (full + heavy truncations)
            'TROPICAL FINANCIAL CREDIT UNION', 'TROPICAL FINANCIAL', 'TROPICAL FCU',
            'TROPICAL FIN', 'TROPICAL FIN CU', 'TROP FIN', 'TROP FCU',
            # iTHINK Financial
            'ITHINK FINANCIAL CREDIT UNION', 'ITHINK FINANCIAL', 'ITHINK FCU',
            'ITHINK FIN', 'ITHINK FIN CR', 'ITHINK CU',
            # BrightStar CU
            'BRIGHTSTAR CREDIT UNION', 'BRIGHTSTAR CU', 'BRIGHTSTAR',
            'BRIGHT STAR CU',
            # WE Florida Financial
            'WE FLORIDA FINANCIAL', 'WE FLORIDA', 'WE FLORIDA FIN',
            # Power Financial CU
            'POWER FINANCIAL CREDIT UNION', 'POWER FINANCIAL', 'POWER FCU',
            'POWER FIN', 'POWER FIN CU',
            # Space Coast CU (large FL CU)
            'SPACE COAST CREDIT UNION', 'SPACE COAST CU', 'SPACE COAST',
            'SPACE CST', 'SCCU',
            # Gold Coast FCU
            'GOLD COAST FEDERAL CREDIT UNION', 'GOLD COAST FCU',
            'GOLD COAST',
            # First Choice CU
            'FIRST CHOICE CREDIT UNION', 'FIRST CHOICE CU',
            # Sun CU
            'SUN CREDIT UNION', 'SUN CU',
            # Florida Connect CU
            'FLORIDA CONNECT CREDIT UNION', 'FLORIDA CONNECT CU',
            'FLORIDA CONNECT', 'FL CONNECT CU',
            # Velocity Community CU
            'VELOCITY COMMUNITY CREDIT UNION', 'VELOCITY CU',
            'VELOCITY COMMUNITY',
            # Wellby Financial
            'WELLBY FINANCIAL', 'WELLBY FIN', 'WELLBY',
            # Navy Federal — full + heavy truncations
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
            'NAVY FEDERAL', 'NAVY FED', 'NAVY FCU', 'NFCU',
            # Major FL CUs commonly seen as cross-shopping competition
            'SUNCOAST CREDIT UNION', 'SUNCOAST CU', 'SUNCOAST',
            'GTE FINANCIAL', 'GTE FCU', 'GTE CU',
            'VYSTAR CREDIT UNION', 'VYSTAR CU', 'VYSTAR',
            'GROW FINANCIAL', 'GROW FIN', 'GROW FCU',
            'DADE COUNTY FCU', 'DADE COUNTY FED',
            'MIDFLORIDA CREDIT UNION', 'MIDFLORIDA CU', 'MIDFLORIDA',
            'COMMUNITY FIRST CREDIT UNION', 'COMMUNITY FIRST CU',
            'ADDITION FINANCIAL', 'ADDITION FIN',
            'FAIRWINDS CREDIT UNION', 'FAIRWINDS CU',
            'PARTNERSHIP FINANCIAL CU',
        ],
        'local_banks': [
            # Seacoast — full + truncations
            'SEACOAST BANK', 'SEACOAST BANKING', 'SEACOAST NATIONAL',
            'SEACOAST NATL', 'SEACOAST NATL B', 'SEACOAST NB',
            # Ocean Bank
            'OCEAN BANK', 'OCEAN BK', 'OCEAN BNK',
            # City National Bank of Florida
            'CITY NATIONAL BANK OF FLORIDA', 'CITY NATIONAL BANK',
            'CITY NATL BANK', 'CITY NATL', 'CITY NATL FL', 'CNB FL',
            # Amerant
            'AMERANT BANK', 'AMERANT', 'AMERANT BK',
            # BankUnited
            'BANKUNITED', 'BANK UNITED', 'BANKUNITED NA',
            'BANK UNITED NA', 'BANKUNITED N A',
            # United Community Bank
            'UNITED COMMUNITY BANK', 'UCBI', 'UNITED COMMUNITY',
            # First Horizon
            'FIRST HORIZON', 'FIRST HORIZON BANK', 'FIRST HORIZON NA',
            # Synovus
            'SYNOVUS', 'SYNOVUS BANK', 'SYNOVUS BK', 'SYNOVUS NA',
            # Other FL community banks frequently seen
            'FLORIDA COMMUNITY BANK', 'FCB FL',
            'FIRST FLORIDA INTEGRITY BANK', 'FFIB',
            'CENTERSTATE BANK',
            'PROFESSIONAL BANK',
            'PROSPERA BANK',
            'TIAA BANK', 'EVERBANK',
            'STONEGATE BANK',
            'GIBRALTAR PRIVATE BANK',
            'PAYROLL BANK',
            'TOTAL BANK',
            'INTERCREDIT BANK',
        ],
        'custom': [],
        'rollups': {
            # Credit Unions
            'TROPICAL FINANCIAL':       'TROPICAL FINANCIAL CREDIT UNION',
            'TROPICAL FCU':             'TROPICAL FINANCIAL CREDIT UNION',
            'ITHINK FINANCIAL':         'ITHINK FINANCIAL CREDIT UNION',
            'ITHINK FCU':               'ITHINK FINANCIAL CREDIT UNION',
            'BRIGHTSTAR CU':            'BRIGHTSTAR CREDIT UNION',
            'WE FLORIDA':               'WE FLORIDA FINANCIAL',
            'POWER FINANCIAL':          'POWER FINANCIAL CREDIT UNION',
            'POWER FCU':                'POWER FINANCIAL CREDIT UNION',
            'SPACE COAST CU':           'SPACE COAST CREDIT UNION',
            'GOLD COAST FCU':           'GOLD COAST FEDERAL CREDIT UNION',
            'FIRST CHOICE CU':          'FIRST CHOICE CREDIT UNION',
            'SUN CU':                   'SUN CREDIT UNION',
            'FLORIDA CONNECT CU':       'FLORIDA CONNECT CREDIT UNION',
            'VELOCITY CU':              'VELOCITY COMMUNITY CREDIT UNION',
            'NAVY FEDERAL CU':          'NAVY FEDERAL CREDIT UNION',
            # Local Banks
            'SEACOAST BANKING':         'SEACOAST BANK',
            'SEACOAST NATIONAL':        'SEACOAST BANK',
            'CITY NATIONAL BANK':       'CITY NATIONAL BANK OF FLORIDA',
            'CITY NATL':                'CITY NATIONAL BANK OF FLORIDA',
            'AMERANT':                  'AMERANT BANK',
            'BANK UNITED':              'BANKUNITED',
            'SYNOVUS BANK':             'SYNOVUS',
        },
    },

    '1585': {  # First Community Bank of the Heartland (Western KY / Northwest TN)
        'fed_district': '8',
        'credit_unions': [
            'LEADERS CREDIT UNION', 'LEADERS CU',
            'PEOPLES CHOICE CREDIT UNION', "PEOPLE'S CHOICE CREDIT UNION",
            'PADUCAH FEDERAL CREDIT UNION', 'PADUCAH FEDERAL CU',
            'CAPE REGIONAL CREDIT UNION', 'CAPE REGIONAL CU',
            'SIKESTON COMMUNITY CREDIT UNION',
            'SIKESTON PUBLIC SCHOOL CREDIT UNION',
            'NAVY FEDERAL CREDIT UNION', 'NAVY FEDERAL CU',
        ],
        'local_banks': [
            'FOCUS BANK',
            'FOUNDATION BANK',
            'REELFOOT BANK',
            'FIRST STATE BANK',
            'CFSB', 'COMMUNITY FINANCIAL SERVICES BANK',
            'CITIZENS BANK',
            'CITIZENS BANK OF FULTON',
            'CLINTON BANK',
            'REGIONS BANK',
            'TRUIST',
            'RIVER VALLEY AGCREDIT',
        ],
        'custom': [],
        'rollups': {
            # --- Credit Unions ---
            'LEADERS CU':                          'LEADERS CREDIT UNION',
            "PEOPLE'S CHOICE CREDIT UNION":        'PEOPLES CHOICE CREDIT UNION',
            'PADUCAH FEDERAL CU':                  'PADUCAH FEDERAL CREDIT UNION',
            'CAPE REGIONAL CU':                    'CAPE REGIONAL CREDIT UNION',
            'NAVY FEDERAL CU':                     'NAVY FEDERAL CREDIT UNION',
            # --- Local Banks ---
            'COMMUNITY FINANCIAL SERVICES BANK':   'CFSB',
            'CITIZENS BANK OF FULTON':             'CITIZENS BANK',
        },
    },

    '1453': {  # Connex Credit Union (North Haven, CT -- New Haven/Hartford/Middlesex/Fairfield)
        'fed_district': '1',
        'credit_unions': [
            # American Eagle Financial CU (East Hartford) -- largest CT CU.
            # Bare 'AMERICAN EAGLE' intentionally omitted: collides with
            # American Eagle Outfitters (apparel). Qualified forms only.
            'AMERICAN EAGLE FINANCIAL CREDIT UNION', 'AMERICAN EAGLE FINANCIAL',
            'AMERICAN EAGLE FCU', 'AMERICAN EAGLE CU', 'AEFCU',
            # Sikorsky Financial CU (Stratford). Bare 'SIKORSKY' omitted:
            # collides with Sikorsky Aircraft payroll/employer descriptors.
            'SIKORSKY FINANCIAL CREDIT UNION', 'SIKORSKY CREDIT UNION',
            'SIKORSKY FINANCIAL', 'SIKORSKY FCU', 'SIKORSKY CU',
            # Nutmeg State Financial CU (Rocky Hill)
            'NUTMEG STATE FINANCIAL CREDIT UNION', 'NUTMEG STATE FINANCIAL',
            'NUTMEG STATE FCU', 'NUTMEG STATE CU', 'NUTMEG STATE',
            # Mutual Security CU (Shelton)
            'MUTUAL SECURITY CREDIT UNION', 'MUTUAL SECURITY CU', 'MUTUAL SECURITY',
            # Seasons FCU (Middletown) -- rebranded to Ellafi FCU; data may carry either
            'SEASONS FEDERAL CREDIT UNION', 'SEASONS FCU',
            'ELLAFI FEDERAL CREDIT UNION', 'ELLAFI FCU',
        ],
        'local_banks': [
            # Guilford Savings Bank -- rebranded to Ascend Bank (Branford/Guilford/Madison)
            'GUILFORD SAVINGS BANK', 'GUILFORD SAVINGS', 'ASCEND BANK',
            # Ion Bank (Naugatuck; formerly Naugatuck Savings Bank)
            'ION BANK', 'NAUGATUCK SAVINGS BANK',
            # The Milford Bank (Milford / Stratford)
            'THE MILFORD BANK', 'MILFORD BANK',
            # New Haven Bank
            'NEW HAVEN BANK',
            # Essex Savings Bank (Middlesex). Bare 'ESSEX' omitted: too generic.
            'ESSEX SAVINGS BANK', 'ESSEX SAVINGS',
            # M&T Bank -- successor to People's United (former dominant CT bank).
            # People's United is on the District-1 top-25 list; M&T is the live brand.
            'M&T BANK', 'M AND T BANK', 'M&T',
            # KeyBank -- major CT regional, not on the District-1 top-25 list
            'KEYBANK', 'KEY BANK',
        ],
        'custom': [],
        'rollups': {
            # --- Credit Unions ---
            'AMERICAN EAGLE FINANCIAL':            'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'AMERICAN EAGLE FCU':                  'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'AMERICAN EAGLE CU':                   'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'AEFCU':                               'AMERICAN EAGLE FINANCIAL CREDIT UNION',
            'SIKORSKY CREDIT UNION':               'SIKORSKY FINANCIAL CREDIT UNION',
            'SIKORSKY FINANCIAL':                  'SIKORSKY FINANCIAL CREDIT UNION',
            'SIKORSKY FCU':                        'SIKORSKY FINANCIAL CREDIT UNION',
            'SIKORSKY CU':                         'SIKORSKY FINANCIAL CREDIT UNION',
            'NUTMEG STATE FINANCIAL':              'NUTMEG STATE FINANCIAL CREDIT UNION',
            'NUTMEG STATE FCU':                    'NUTMEG STATE FINANCIAL CREDIT UNION',
            'NUTMEG STATE CU':                     'NUTMEG STATE FINANCIAL CREDIT UNION',
            'NUTMEG STATE':                        'NUTMEG STATE FINANCIAL CREDIT UNION',
            'MUTUAL SECURITY CU':                  'MUTUAL SECURITY CREDIT UNION',
            'MUTUAL SECURITY':                     'MUTUAL SECURITY CREDIT UNION',
            'SEASONS FCU':                         'SEASONS FEDERAL CREDIT UNION',
            'ELLAFI FEDERAL CREDIT UNION':         'SEASONS FEDERAL CREDIT UNION',
            'ELLAFI FCU':                          'SEASONS FEDERAL CREDIT UNION',
            # --- Local Banks ---
            'GUILFORD SAVINGS':                    'GUILFORD SAVINGS BANK',
            'ASCEND BANK':                         'GUILFORD SAVINGS BANK',
            'NAUGATUCK SAVINGS BANK':              'ION BANK',
            'MILFORD BANK':                        'THE MILFORD BANK',
            'ESSEX SAVINGS':                       'ESSEX SAVINGS BANK',
            'M AND T BANK':                        'M&T BANK',
            'M&T':                                 'M&T BANK',
            'KEY BANK':                            'KEYBANK',
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

# Look up client config (fall back to empty if CLIENT_ID not found).
# Normalize the id -- runs have delivered it as int, padded, or float-string.
_cid = str(CLIENT_ID).strip() if 'CLIENT_ID' in dir() and CLIENT_ID is not None else ''
_client_cfg = CLIENT_CONFIGS.get(_cid, {})

# Loud warning if this client has no entry -- otherwise local_banks /
# credit_unions silently become empty lists, fed_district silently
# defaults to '12' (San Francisco), and downstream reports show zero
# matches for those categories. Run cell 68 for a full audit.
if _cid and not _client_cfg:
    print(f"  WARNING: CLIENT_ID '{_cid}' has no entry in CLIENT_CONFIGS.")
    print(f"           credit_unions / local_banks / custom patterns will be EMPTY")
    print(f"           and fed_district DEFAULTS TO '12' (San Francisco) -- the")
    print(f"           top_25_fed_district category will show ~ZERO matches for")
    print(f"           clients outside the West. Add an entry to CLIENT_CONFIGS, or")
    print(f"           run competition/68_detection_diagnostic.py for help.")

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

# ---------------------------------------------------------------------------
# Normalization for matching
# ---------------------------------------------------------------------------
# Card-network merchant descriptors are typically truncated to ~22-25 chars
# with prefixes (POS DEBIT, SQ *, etc.) and trailing location/phone garbage.
# The patterns above use full legal names. We normalize BOTH sides before
# matching so e.g. 'TROPICAL FINANCIAL CREDIT UNION' (pattern) and
# 'POS DEBIT TROPICAL FIN CU FT LAUDER FL' (data) collapse to a common form.

import re as _re

_CARD_PREFIX_RE = _re.compile(
    r'^(?:'
    r'POS\s+(?:DEBIT|PURCH(?:ASE)?|WITHDRAWAL|CREDIT)|'
    r'DEBIT\s+(?:CARD\s+(?:PURCHASE|PAYMENT)?|PURCHASE|PMT)|'
    r'CHECKCARD(?:\s+\d+)?|'
    r'PURCHASE\s+AUTHORIZED(?:\s+ON\s+\d+/\d+)?|'
    r'RECURRING\s+(?:DEBIT\s+)?PMT|'
    r'WEB\s+AUTH(?:ORIZED)?\s+PMT|'
    r'EXTERNAL\s+WITHDRAWAL|'
    r'ACH\s+(?:DEBIT|WITHDRAWAL|DEPOSIT|TRANSFER|PMT)|'
    r'SQ\s*\*|TST\s*\*|PP\s*\*|SP\s*\*|PY\s*\*|EZP\s*\*'
    r')\s*',
    _re.IGNORECASE,
)

# Order matters: longest phrases first so 'FEDERAL CREDIT UNION' is collapsed
# before 'FEDERAL' alone. Replacements are regex with \b word boundaries so
# 'FEDERATED' isn't touched by 'FEDERAL'.
_BANK_ABBREV_RULES = [
    (r'\bFEDERAL\s+CREDIT\s+UNION\b', 'FED CU'),
    (r'\bCREDIT\s+UNION\b',           'CU'),
    (r'\bFCU\b',                      'FED CU'),
    (r'\bFEDERAL\b',                  'FED'),
    (r'\bFINANCIAL\b',                'FIN'),
    (r'\bNATIONAL\s+BANK\b',          'NATL BANK'),
    (r'\bNATIONAL\b',                 'NATL'),
    (r'\bN\.A\.\b',                   'NATL'),
    (r'\bSAVINGS\s+BANK\b',           'SAVINGS BANK'),
    (r'[^\w\s]',                      ' '),   # drop punctuation
    (r'\s+',                          ' '),   # collapse whitespace
]
_BANK_ABBREV_COMPILED = [(_re.compile(p), r) for p, r in _BANK_ABBREV_RULES]


def normalize_for_match(s):
    """Collapse a merchant or pattern string into a canonical matching form."""
    s = str(s).upper().strip()
    s = _CARD_PREFIX_RE.sub('', s)
    for pat, repl in _BANK_ABBREV_COMPILED:
        s = pat.sub(repl, s)
    return s.strip()


def tag_competitors(df, merchant_col='merchant_consolidated'):
    """Tag transactions with competitor_category column.

    Matching strategy:
      - Both patterns and merchant strings are normalized via
        normalize_for_match() (strips card-descriptor prefixes, collapses
        FEDERAL CREDIT UNION / FCU / FINANCIAL / etc. to canonical short forms).
      - Word-boundary regex contains-match (was anchored ^ start-match,
        which never matched truncated card descriptors like
        'POS DEBIT TROPICAL FIN CU FT LAUDER FL').

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
    # Vectorized normalization: apply each rule once across the whole Series
    merchant_norm = df[merchant_col].astype(str).str.upper().str.strip()
    merchant_norm = merchant_norm.str.replace(_CARD_PREFIX_RE.pattern, '',
                                              regex=True, flags=_re.IGNORECASE)
    for pat, repl in _BANK_ABBREV_RULES:
        merchant_norm = merchant_norm.str.replace(pat, repl, regex=True)
    merchant_norm = merchant_norm.str.strip()

    # False-positive exclusions: a merchant name (already normalized) that
    # matches any of these substrings will NOT be tagged as a competitor,
    # even if it matched one of the patterns. Targets short generic phrases
    # that get reused outside finance (FIRST CHOICE / GOLD COAST etc.).
    _COMP_FP_HINTS = [
        # Retail / pharmacy / clinics
        'PHARMACY', 'PHARM', 'DRUGS', 'MEDICAL', 'CLINIC', 'HOSPITAL',
        'DENTAL', 'DENTIST', 'VETERINARY', 'VET CLINIC',
        # Food / grocery / restaurants
        'RESTAURANT', 'CAFE', 'PIZZA', 'BURGER', 'GRILL', 'DINER',
        'GROCERY', 'MARKET', 'DELI', 'BAKERY',
        # Auto / repair (avoid AUTO LOAN false-positives leaking)
        'AUTOMOTIVE', 'AUTO REPAIR', 'AUTO BODY', 'AUTOZONE', 'AUTO PARTS',
        'TIRES', 'OIL CHANGE', 'BODY SHOP',
        # Home / property
        'REALTY', 'REAL ESTATE', 'PROPERTIES', 'CONSTRUCTION',
        'PLUMBING', 'ROOFING', 'LANDSCAPING',
        # Services / misc
        'SALON', 'BARBER', 'SPA', 'NAILS',
        'CLEANERS', 'LAUNDRY',
        'CHURCH', 'MINISTRY',
        'SCHOOL', 'ACADEMY', 'UNIVERSITY',
        'TRADER JOE',
        # Brand-name collisions with universal patterns
        'NEIMAN MARCUS', 'NEIMAN',          # vs digital_banks MARCUS (Goldman)
        'MARCUS THEATRES', 'MARCUS THEATR', # cinema chain
        'DISCOVERY',                        # vs digital_banks DISCOVER
        'CITRUS',                           # vs big_nationals CITI
        'CHASE FIELD', 'CHASE STADIUM',     # baseball venue, not CHASE bank
    ]
    # Use word boundaries so 'SPA' doesn't match 'SPACE', 'CAFE' doesn't
    # match anything inside another word, etc.
    _comp_fp_regex = r'\b(?:' + '|'.join(re.escape(h) for h in _COMP_FP_HINTS) + r')\b'
    _fp_mask = merchant_norm.str.contains(_comp_fp_regex, na=False, regex=True).values

    tagged = np.zeros(n, dtype=bool)
    cat_names = list(COMPETITOR_MERCHANTS.keys())
    cat_codes = np.full(n, -1, dtype=np.int8)  # -1 -> NaN in Categorical

    for cat_idx, (category, patterns) in enumerate(COMPETITOR_MERCHANTS.items()):
        # Normalize patterns the same way data is normalized.
        sw = [normalize_for_match(p) for p in patterns.get('starts_with', []) if p.strip()]
        sw = [p for p in sw if p]  # drop any that normalized to empty
        ex = [normalize_for_match(p) for p in patterns.get('exact', []) if p.strip()]
        ex = [p for p in ex if p]

        # Deduplicate -- normalization collapses many variants together
        sw = sorted(set(sw), key=len, reverse=True)
        ex = sorted(set(ex))

        cat_mask = np.zeros(n, dtype=bool)

        if sw:
            # Word-boundary contains: matches anywhere in the merchant string
            # but only at word boundaries (so 'CHASE' won't match inside 'PURCHASE').
            regex = r'\b(?:' + '|'.join(re.escape(p) for p in sw) + r')\b'
            cat_mask |= merchant_norm.str.contains(regex, na=False, regex=True).values

        if ex:
            cat_mask |= merchant_norm.isin(ex).values

        # Apply false-positive guard: skip clearly non-financial merchants
        # even if their name contains a competitor brand substring.
        cat_mask &= ~_fp_mask

        new_hits = cat_mask & ~tagged
        if new_hits.any():
            cat_codes[new_hits] = cat_idx
            tagged |= new_hits

    # Free the large normalized Series (~250 MiB) before allocating results
    del merchant_norm, tagged
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
    # Traditional banking
    'BANK', 'BANKING', 'CREDIT UNION', 'CU ', 'FEDERAL CREDIT',
    'FINANCIAL', 'SAVINGS', 'LENDING', 'MORTGAGE', 'LOAN',
    'BROKERAGE', 'INVESTMENT', 'TRUST COMPANY',
    # Fintech / crypto / investing -- these brands carry NO 'bank/financial'
    # token, so the old keyword set silently hid them (e.g. COINBASE), which is
    # why missed competitors never surfaced in the discovery output. Broadened
    # so any untagged fintech/crypto/investing leakage shows up for review.
    'CRYPTO', 'BITCOIN', 'BLOCKCHAIN', 'EXCHANGE', 'WALLET',
    'SECURITIES', 'BROKER', 'WEALTH', 'ADVISOR', 'CAPITAL MANAGEMENT',
    'NEOBANK', 'FINTECH', 'PAYMENTS', 'MONEY', 'FUNDING', 'VENTURES',
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
