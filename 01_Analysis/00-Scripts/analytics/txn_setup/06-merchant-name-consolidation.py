"""
UNIVERSAL MERCHANT CONSOLIDATION FUNCTION
==========================================
Works across all clients to consolidate common merchant name variations.
Add this to your notebook and use it in your merchant analysis sections.
"""

import re as _re_clean

# Carrier prefixes that banks/processors prepend to the REAL merchant string.
# Stripped BEFORE brand matching so "ACH CREDIT SESLOC CREDIT UNION 805-555"
# becomes "SESLOC CREDIT UNION 805-555" and prefix-match in tag_competitors
# correctly tags it as a credit_union.
#
# This is the root cause of the 1776 undercount: wallets/BNPL brands
# (VENMO, ZELLE, PAYPAL, AFFIRM, KLARNA, AFTERPAY) have EXPLICIT rules in
# this file that reduce them to clean names, so tag_competitors' prefix
# match works. Credit unions and local banks have NO explicit rules -- so
# "ACH CREDIT SESLOC CREDIT UNION" stays messy and prefix-match FAILS,
# dropping the transaction entirely from competitor_txns.
_CARRIER_PREFIX_RE = _re_clean.compile(
    r'^(?:'
    r'DEBIT\s+PURCHASE|DEBIT\s+CARD\s+PURCHASE|DEBIT\s+POS|DEBIT|'
    r'CREDIT\s+PURCHASE|CREDIT\s+CARD|CREDIT|'
    r'POS\s+PURCHASE|POS\s+DEBIT|POS|'
    r'ACH\s+DEBIT|ACH\s+CREDIT|ACH\s+PAYMENT|ACH\s+WEB|ACH|'
    r'PURCHASE\s+AUTHORIZED|PURCHASE|'
    r'PAYMENT\s+TO|PAYMENT|'
    r'EXTERNAL\s+TRANSFER|EXT\s+TRANSFER|EXT\s+XFER|EXT|'
    r'ONLINE\s+TRANSFER|WEB\s+TRANSFER|TRANSFER|XFER|'
    r'DIRECT\s+DEP|DIRECT\s+DEBIT|'
    r'RECURRING\s+PAYMENT|RECURRING|'
    r'CKCD|DEB|CRD'
    r')\s+',
    _re_clean.IGNORECASE,
)

# Trailing per-transaction noise that prevents clean grouping later:
# phone numbers, account digits, two-letter state codes.
_TRAILING_STATE_RE  = _re_clean.compile(r'\s+[A-Z]{2}$')
_TRAILING_DIGITS_RE = _re_clean.compile(r'\s+[\d\-]{3,}$')
_TRAILING_PHONE_RE  = _re_clean.compile(r'\s+(?:\d{3}[-\s]?\d{3}[-\s]?\d{4})$')


def _strip_carrier_noise(merchant_upper):
    """Remove carrier prefix + per-txn tail so the real merchant name is at
    position 0. Safe for every merchant type including wallets/BNPL (their
    rules below still work because brand rules use `in merchant_upper`
    substring checks, not prefix checks)."""
    # Strip leading carrier prefix up to 3 times to handle doubled prefixes
    # like "POS DEBIT PURCHASE"
    for _ in range(3):
        new = _CARRIER_PREFIX_RE.sub('', merchant_upper, count=1)
        if new == merchant_upper:
            break
        merchant_upper = new
    # Strip trailing noise in a loop until stable so
    # "RANDOM SHOP 123456 CA" collapses to "RANDOM SHOP" in one call.
    for _ in range(4):
        prev = merchant_upper
        merchant_upper = _TRAILING_PHONE_RE.sub('', merchant_upper)
        merchant_upper = _TRAILING_DIGITS_RE.sub('', merchant_upper)
        merchant_upper = _TRAILING_STATE_RE.sub('', merchant_upper)
        if merchant_upper == prev:
            break
    return merchant_upper.strip()


def standardize_merchant_name(merchant_name):
    """
    Consolidate duplicate merchant variations across all clients.
    Returns standardized merchant name for cleaner analysis.
    """
    # Handle NaN / empty merchant names
    if pd.isna(merchant_name) or str(merchant_name).strip() in ('', 'NAN', 'NONE'):
        return 'UNKNOWN MERCHANT'

    # Normalize: strip whitespace, convert to uppercase
    merchant_upper = str(merchant_name).strip().upper()

    # Remove extra spaces (multiple spaces → single space)
    merchant_upper = ' '.join(merchant_upper.split())

    # Strip carrier prefix ("DEBIT POS", "ACH CREDIT", etc.) + per-txn
    # tail (phone, digits, state) so brand rules below and downstream
    # prefix-match in tag_competitors see the REAL merchant name. Wallet
    # and BNPL rules below use substring checks so this does not change
    # their behavior; CUs / local banks / misc competitors gain correct
    # tagging that was silently missing.
    merchant_upper = _strip_carrier_noise(merchant_upper)

    # ============================================================================
    # TECH & DIGITAL SERVICES
    # ============================================================================
    
    # Apple
    if 'APPLE.COM' in merchant_upper or 'APPLE COM' in merchant_upper:
        return 'APPLE.COM/BILL'
    
    if 'APPLE CASH' in merchant_upper:
        if 'SENT MONEY' in merchant_upper:
            return 'APPLE CASH - SENT MONEY'
        elif 'INST XFER' in merchant_upper or 'TRANSFER' in merchant_upper:
            return 'APPLE CASH - TRANSFERS'
        elif 'BALANCE ADD' in merchant_upper:
            return 'APPLE CASH - BALANCE ADD'
        return 'APPLE CASH'
    
    if 'APPLE' in merchant_upper and 'STORE' in merchant_upper:
        return 'APPLE STORE'
    
    # Google
    if 'GOOGLE' in merchant_upper:
        if 'PLAY' in merchant_upper:
            return 'GOOGLE PLAY'
        if 'STORAGE' in merchant_upper or 'DRIVE' in merchant_upper:
            return 'GOOGLE STORAGE'
        if 'YOUTUBE' in merchant_upper:
            return 'YOUTUBE'
        return 'GOOGLE'
    
    # Amazon
    if 'AMAZON' in merchant_upper:
        if 'PRIME' in merchant_upper:
            return 'AMAZON PRIME'
        if 'AMZN' in merchant_upper:
            return 'AMAZON'
        return 'AMAZON'
    
    if 'AMZN' in merchant_upper:
        return 'AMAZON'
    
    # Prime Video
    if 'PRIME VIDEO' in merchant_upper:
        return 'PRIME VIDEO'
    
    # Netflix
    if 'NETFLIX' in merchant_upper:
        return 'NETFLIX'
    
    # Streaming services
    if 'SPOTIFY' in merchant_upper:
        return 'SPOTIFY'
    
    if 'HULU' in merchant_upper:
        return 'HULU'
    
    if 'DISNEY' in merchant_upper and 'PLUS' in merchant_upper:
        return 'DISNEY+'
    
    if 'HBO' in merchant_upper and 'MAX' in merchant_upper:
        return 'HBO MAX'
    
    # PayPal
    if 'PAYPAL' in merchant_upper:
        if 'INST XFER' in merchant_upper or 'TRANSFER' in merchant_upper:
            return 'PAYPAL TRANSFERS'
        return 'PAYPAL'
    
    # Venmo
    if 'VENMO' in merchant_upper:
        return 'VENMO'
    
    # Zelle
    if 'ZELLE' in merchant_upper:
        return 'ZELLE'
    
    # Cash App
    if 'CASH APP' in merchant_upper or 'CASHAPP' in merchant_upper:
        return 'CASH APP'
    
    # ============================================================================
    # RETAIL - BIG BOX
    # ============================================================================
    
    # Walmart
    if 'WMT PLUS' in merchant_upper or 'WALMART PLUS' in merchant_upper:
        return 'WALMART PLUS'
    
    if 'WALMART' in merchant_upper or 'WAL-MART' in merchant_upper or 'WM SUPERCENTER' in merchant_upper:
        if 'WALMART.COM' in merchant_upper or 'WALMART COM' in merchant_upper:
            return 'WALMART.COM'
        return 'WALMART (ALL LOCATIONS)'
    
    # Target
    if 'TARGET' in merchant_upper and ('T-' in merchant_upper or 'STORE' in merchant_upper):
        return 'TARGET (ALL LOCATIONS)'
    
    # Costco
    if 'COSTCO' in merchant_upper:
        return 'COSTCO'
    
    # Sam's Club
    if 'SAMS CLUB' in merchant_upper or "SAM'S CLUB" in merchant_upper:
        return 'SAMS CLUB'
    
    # BJ's Wholesale
    if "BJ'S" in merchant_upper or 'BJS' in merchant_upper:
        return "BJ'S WHOLESALE"
    
    # ============================================================================
    # RETAIL - DOLLAR STORES
    # ============================================================================
    
    if 'DOLLAR TREE' in merchant_upper or merchant_upper == 'DOLLARTREE':
        return 'DOLLAR TREE'
    
    if 'DOLLAR GENERAL' in merchant_upper or merchant_upper == 'DOLLARGENERAL':
        return 'DOLLAR GENERAL'
    
    if 'FAMILY DOLLAR' in merchant_upper:
        return 'FAMILY DOLLAR'
    
    if 'FIVE BELOW' in merchant_upper or '5 BELOW' in merchant_upper:
        return 'FIVE BELOW'
    
    # ============================================================================
    # RETAIL - DEPARTMENT STORES
    # ============================================================================
    
    if 'BURLINGTON' in merchant_upper:
        return 'BURLINGTON'
    
    if 'KOHLS' in merchant_upper or "KOHL'S" in merchant_upper:
        return "KOHL'S"
    
    if 'MARSHALLS' in merchant_upper:
        return 'MARSHALLS'
    
    if 'TJ MAXX' in merchant_upper or 'TJMAXX' in merchant_upper:
        return 'TJ MAXX'
    
    if 'ROSS' in merchant_upper and 'DRESS' in merchant_upper:
        return 'ROSS DRESS FOR LESS'
    
    if 'NORDSTROM' in merchant_upper:
        return 'NORDSTROM'
    
    if "MACY'S" in merchant_upper or 'MACYS' in merchant_upper:
        return "MACY'S"
    
    # ============================================================================
    # RETAIL - SPECIALTY
    # ============================================================================
    
    if 'HOBBY LOBBY' in merchant_upper or 'HOBBYLOBBY' in merchant_upper:
        return 'HOBBY LOBBY'
    
    if 'MICHAELS' in merchant_upper and 'STORES' in merchant_upper:
        return 'MICHAELS'
    
    if 'HOME DEPOT' in merchant_upper or 'HOMEDEPOT' in merchant_upper:
        return 'HOME DEPOT'
    
    if "LOWE'S" in merchant_upper or 'LOWES' in merchant_upper:
        return "LOWE'S"
    
    if 'MENARDS' in merchant_upper:
        return 'MENARDS'
    
    if 'ACE HDWE' in merchant_upper or 'ACE HARDWARE' in merchant_upper:
        return 'ACE HARDWARE'
    
    if 'TRUE VALUE' in merchant_upper or 'TRUEVALUE' in merchant_upper:
        return 'TRUE VALUE'
    
    if 'BED BATH' in merchant_upper:
        return 'BED BATH & BEYOND'
    
    if 'BEST BUY' in merchant_upper or 'BESTBUY' in merchant_upper:
        return 'BEST BUY'
    
    if 'DICKS SPORTING' in merchant_upper or "DICK'S SPORTING" in merchant_upper:
        return 'DICKS SPORTING GOODS'
    
    if 'PETCO' in merchant_upper:
        return 'PETCO'
    
    if 'PETSMART' in merchant_upper:
        return 'PETSMART'
    
    # ============================================================================
    # ONLINE RETAIL
    # ============================================================================
    
    if 'TIKTOK' in merchant_upper and 'SHOP' in merchant_upper:
        return 'TIKTOK SHOP'
    
    if 'SHEIN' in merchant_upper:
        return 'SHEIN'
    
    if 'TEMU' in merchant_upper:
        return 'TEMU'
    
    if 'ETSY' in merchant_upper:
        return 'ETSY'
    
    if 'EBAY' in merchant_upper:
        return 'EBAY'
    
    if 'AFTERPAY' in merchant_upper:
        return 'AFTERPAY'
    
    if 'KLARNA' in merchant_upper:
        return 'KLARNA'
    
    if 'AFFIRM' in merchant_upper:
        return 'AFFIRM'
    
    # ============================================================================
    # GROCERS - REGIONAL
    # ============================================================================
    
    # Midwest
    if 'JEWEL' in merchant_upper and 'OSCO' in merchant_upper:
        return 'JEWEL-OSCO (ALL LOCATIONS)'
    
    if 'WOODMANS' in merchant_upper or 'WOODMAN' in merchant_upper:
        return 'WOODMANS FOOD MARKET (ALL LOCATIONS)'
    
    if 'MEIJER' in merchant_upper:
        return 'MEIJER (ALL LOCATIONS)'
    
    if 'HY-VEE' in merchant_upper or 'HYVEE' in merchant_upper:
        return 'HY-VEE'
    
    if 'SCHNUCKS' in merchant_upper:
        return 'SCHNUCKS'
    
    # Northeast
    if 'STOP & SHOP' in merchant_upper or 'STOP AND SHOP' in merchant_upper:
        return 'STOP & SHOP'
    
    if 'MARKET BASKET' in merchant_upper:
        return 'MARKET BASKET'
    
    if 'SHAWS' in merchant_upper or "SHAW'S" in merchant_upper:
        return "SHAW'S"
    
    if 'HANNAFORD' in merchant_upper:
        return 'HANNAFORD'
    
    if 'WEGMANS' in merchant_upper:
        return 'WEGMANS'
    
    if 'GIANT FOOD' in merchant_upper or 'GIANT EAGLE' in merchant_upper:
        return 'GIANT'
    
    # Southeast
    if 'PUBLIX' in merchant_upper:
        return 'PUBLIX'
    
    if 'KROGER' in merchant_upper:
        return 'KROGER'
    
    if 'HARRIS TEETER' in merchant_upper:
        return 'HARRIS TEETER'
    
    if 'FOOD LION' in merchant_upper:
        return 'FOOD LION'
    
    # West
    if 'ALBERTSONS' in merchant_upper:
        return 'ALBERTSONS'
    
    if 'SAFEWAY' in merchant_upper:
        return 'SAFEWAY'
    
    if 'VONS' in merchant_upper:
        return 'VONS'
    
    if 'RALPHS' in merchant_upper:
        return 'RALPHS'
    
    if 'FRED MEYER' in merchant_upper:
        return 'FRED MEYER'
    
    # National
    if 'WHOLE FOODS' in merchant_upper:
        return 'WHOLE FOODS'
    
    if 'TRADER JOE' in merchant_upper:
        return "TRADER JOE'S"
    
    if 'ALDI' in merchant_upper:
        return 'ALDI'
    
    if 'LIDL' in merchant_upper:
        return 'LIDL'
    
    if 'FRESH MARKET' in merchant_upper:
        return 'FRESH MARKET'
    
    # ============================================================================
    # GAS STATIONS / CONVENIENCE
    # ============================================================================
    
    if 'SPEEDWAY' in merchant_upper:
        return 'SPEEDWAY'
    
    if 'SHELL' in merchant_upper and ('SERVICE' in merchant_upper or 'OIL' in merchant_upper or merchant_upper.startswith('SHELL')):
        return 'SHELL'
    
    if 'MARATHON' in merchant_upper:
        return 'MARATHON'
    
    if 'BP' == merchant_upper or merchant_upper.startswith('BP '):
        return 'BP'
    
    if 'MOBIL' in merchant_upper or 'EXXON' in merchant_upper:
        return 'EXXON/MOBIL'
    
    if 'CHEVRON' in merchant_upper:
        return 'CHEVRON'
    
    if 'CITGO' in merchant_upper:
        return 'CITGO'
    
    if 'SUNOCO' in merchant_upper:
        return 'SUNOCO'
    
    if 'VALERO' in merchant_upper:
        return 'VALERO'
    
    if 'CIRCLE K' in merchant_upper or 'CIRCLEK' in merchant_upper:
        return 'CIRCLE K'
    
    if '7-ELEVEN' in merchant_upper or '7ELEVEN' in merchant_upper or '7 ELEVEN' in merchant_upper:
        return '7-ELEVEN'
    
    if 'WAWA' in merchant_upper:
        return 'WAWA'
    
    if 'SHEETZ' in merchant_upper:
        return 'SHEETZ'
    
    if 'QUICKTRIP' in merchant_upper or 'QT' in merchant_upper:
        return 'QUICKTRIP'
    
    if 'CUMBERLAND' in merchant_upper or 'SMARTREWARDS' in merchant_upper:
        return 'CUMBERLAND FARMS'
    
    if 'PILOT' in merchant_upper and ('FLYING' in merchant_upper or 'TRAVEL' in merchant_upper):
        return 'PILOT FLYING J'
    
    if "LOVE'S" in merchant_upper or 'LOVES' in merchant_upper:
        return "LOVE'S TRAVEL STOPS"
    
    # ============================================================================
    # RESTAURANTS - FAST FOOD
    # ============================================================================
    
    if 'MCDONALDS' in merchant_upper or "MCDONALD'S" in merchant_upper:
        return "MCDONALD'S"
    
    if 'BURGER KING' in merchant_upper:
        return 'BURGER KING'
    
    if "WENDY'S" in merchant_upper or 'WENDYS' in merchant_upper:
        return "WENDY'S"
    
    if 'TACO BELL' in merchant_upper:
        return 'TACO BELL'
    
    if 'CHIPOTLE' in merchant_upper:
        return 'CHIPOTLE'
    
    if 'SUBWAY' in merchant_upper:
        return 'SUBWAY'
    
    if 'CHICK-FIL-A' in merchant_upper or 'CHICKFILA' in merchant_upper:
        return 'CHICK-FIL-A'
    
    if 'POPEYES' in merchant_upper:
        return 'POPEYES'
    
    if 'KFC' in merchant_upper:
        return 'KFC'
    
    if 'PANERA' in merchant_upper:
        return 'PANERA BREAD'
    
    if 'JIMMY JOHN' in merchant_upper:
        return "JIMMY JOHN'S"
    
    if 'ARBY' in merchant_upper:
        return "ARBY'S"
    
    if 'SONIC' in merchant_upper and 'DRIVE' in merchant_upper:
        return 'SONIC DRIVE-IN'
    
    if 'FIVE GUYS' in merchant_upper:
        return 'FIVE GUYS'
    
    if 'CULVERS' in merchant_upper or "CULVER'S" in merchant_upper:
        return "CULVER'S"
    
    if 'PORTILLOS' in merchant_upper or "PORTILLO'S" in merchant_upper:
        return "PORTILLO'S"
    
    # ============================================================================
    # RESTAURANTS - CASUAL/DELIVERY
    # ============================================================================
    
    if 'STARBUCKS' in merchant_upper:
        return 'STARBUCKS'
    
    if 'DUNKIN' in merchant_upper:
        return 'DUNKIN'
    
    if 'TROPICAL SMOOTHIE' in merchant_upper:
        return 'TROPICAL SMOOTHIE CAFE'
    
    if 'SMOOTHIE KING' in merchant_upper:
        return 'SMOOTHIE KING'
    
    if 'JAMBA' in merchant_upper:
        return 'JAMBA JUICE'
    
    if 'DOORDASH' in merchant_upper:
        return 'DOORDASH'
    
    if 'UBER' in merchant_upper:
        if 'EATS' in merchant_upper:
            return 'UBER EATS'
        return 'UBER'
    
    if 'GRUBHUB' in merchant_upper:
        return 'GRUBHUB'
    
    if 'INSTACART' in merchant_upper:
        return 'INSTACART'
    
    # ============================================================================
    # UTILITIES
    # ============================================================================
    
    # Electric
    if 'COMED' in merchant_upper or 'COM ED' in merchant_upper:
        return 'COMED'
    
    if 'DUKE ENERGY' in merchant_upper:
        return 'DUKE ENERGY'
    
    if 'DOMINION' in merchant_upper and 'ENERGY' in merchant_upper:
        return 'DOMINION ENERGY'
    
    if 'NATIONAL GRID' in merchant_upper:
        return 'NATIONAL GRID'
    
    if 'EVERSOURCE' in merchant_upper:
        return 'EVERSOURCE'
    
    if 'AMEREN' in merchant_upper:
        return 'AMEREN'
    
    # Gas
    if 'NICOR' in merchant_upper:
        return 'NICOR GAS'
    
    if 'PEOPLES GAS' in merchant_upper:
        return 'PEOPLES GAS'
    
    if 'NATIONAL FUEL' in merchant_upper:
        return 'NATIONAL FUEL'
    
    # Water
    if 'WATER' in merchant_upper and ('DEPT' in merchant_upper or 'DEPARTMENT' in merchant_upper):
        return 'WATER UTILITY'
    
    if 'NARRAGANSETT' in merchant_upper:
        return 'NARRAGANSETT BAY (UTILITIES)'
    
    # ============================================================================
    # TELECOM
    # ============================================================================
    
    # Cable/Internet
    if 'COMCAST' in merchant_upper or 'XFINITY' in merchant_upper:
        return 'COMCAST/XFINITY'
    
    if 'SPECTRUM' in merchant_upper:
        return 'SPECTRUM'
    
    if 'COX' in merchant_upper and ('CABLE' in merchant_upper or 'COMM' in merchant_upper):
        return 'COX COMMUNICATIONS'
    
    if 'VERIZON FIOS' in merchant_upper:
        return 'VERIZON FIOS'
    
    # Wireless
    if 'ATT*' in merchant_upper or 'AT&T' in merchant_upper or 'AT T' in merchant_upper:
        if 'BILL' in merchant_upper or 'PAYMENT' in merchant_upper or 'AUTOPAY' in merchant_upper:
            return 'AT&T'
        return 'AT&T'
    
    if 'TMOBILE' in merchant_upper or 'T-MOBILE' in merchant_upper or 'T MOBILE' in merchant_upper:
        return 'T-MOBILE'
    
    if 'VERIZON' in merchant_upper and 'WIRELESS' in merchant_upper:
        return 'VERIZON WIRELESS'
    
    if 'SPRINT' in merchant_upper:
        return 'SPRINT'
    
    if 'CRICKET' in merchant_upper and 'WIRELESS' in merchant_upper:
        return 'CRICKET WIRELESS'
    
    if 'BOOST MOBILE' in merchant_upper:
        return 'BOOST MOBILE'
    
    if 'METRO' in merchant_upper and ('PCS' in merchant_upper or 'MOBILE' in merchant_upper):
        return 'METRO BY T-MOBILE'
    
    # ============================================================================
    # INSURANCE
    # ============================================================================
    
    if 'STATE FARM' in merchant_upper:
        return 'STATE FARM'
    
    if 'GEICO' in merchant_upper:
        return 'GEICO'
    
    if 'PROGRESSIVE' in merchant_upper:
        return 'PROGRESSIVE'
    
    if 'ALLSTATE' in merchant_upper:
        return 'ALLSTATE'
    
    if 'FARMERS' in merchant_upper and 'INSURANCE' in merchant_upper:
        return 'FARMERS INSURANCE'
    
    if 'LIBERTY MUTUAL' in merchant_upper:
        return 'LIBERTY MUTUAL'
    
    if 'NATIONWIDE' in merchant_upper:
        return 'NATIONWIDE'
    
    if 'USAA' in merchant_upper:
        return 'USAA'
    
    if 'AMERICAN FAMILY' in merchant_upper:
        return 'AMERICAN FAMILY INSURANCE'
    
    # ============================================================================
    # TOLLS
    # ============================================================================
    
    if 'E-ZPASS' in merchant_upper or 'EZPASS' in merchant_upper or 'EZ PASS' in merchant_upper:
        return 'E-ZPASS'
    
    if 'IL TOLLWAY' in merchant_upper or 'ILLINOIS TOLLWAY' in merchant_upper or 'I-PASS' in merchant_upper:
        return 'ILLINOIS TOLLWAY'
    
    if 'SUNPASS' in merchant_upper:
        return 'SUNPASS'
    
    if 'FASTRAK' in merchant_upper:
        return 'FASTRAK'
    
    if 'TOLL' in merchant_upper and ('ROAD' in merchant_upper or 'AUTHORITY' in merchant_upper):
        return 'TOLL AUTHORITY'
    
    # ============================================================================
    # FINANCIAL SERVICES
    # ============================================================================
    
    # Alt Finance
    if 'DAVE' in merchant_upper and ('INC' in merchant_upper or 'APP' in merchant_upper):
        return 'DAVE'
    
    if 'CHIME' in merchant_upper:
        return 'CHIME'
    
    if 'VARO' in merchant_upper:
        return 'VARO'
    
    if 'CURRENT' in merchant_upper and 'CARD' in merchant_upper:
        return 'CURRENT'
    
    if 'FLEX FINANCE' in merchant_upper or 'FLEXFINANCE' in merchant_upper:
        return 'FLEX FINANCE'
    
    if 'EARNIN' in merchant_upper:
        return 'EARNIN'
    
    if 'BRIGIT' in merchant_upper:
        return 'BRIGIT'
    
    if 'POSSIBLE FINANCE' in merchant_upper:
        return 'POSSIBLE FINANCE'
    
    # Traditional Banks
    if 'CHASE' in merchant_upper and ('BANK' in merchant_upper or 'CARD' in merchant_upper or 'PAYMENT' in merchant_upper):
        return 'CHASE'
    
    if 'BANK OF AMERICA' in merchant_upper or 'BOFA' in merchant_upper:
        return 'BANK OF AMERICA'
    
    if 'WELLS FARGO' in merchant_upper:
        return 'WELLS FARGO'
    
    if 'CITIBANK' in merchant_upper or 'CITI CARD' in merchant_upper:
        return 'CITIBANK'
    
    if 'US BANK' in merchant_upper or 'U.S. BANK' in merchant_upper:
        return 'US BANK'
    
    if 'PNC BANK' in merchant_upper:
        return 'PNC'
    
    if 'TD BANK' in merchant_upper:
        return 'TD BANK'
    
    if 'CAPITAL ONE' in merchant_upper:
        return 'CAPITAL ONE'
    
    if 'DISCOVER' in merchant_upper and ('CARD' in merchant_upper or 'PAYMENT' in merchant_upper):
        return 'DISCOVER'
    
    if 'AMEX' in merchant_upper or 'AMERICAN EXPRESS' in merchant_upper:
        return 'AMERICAN EXPRESS'
    
    if 'SYNCHRONY' in merchant_upper:
        return 'SYNCHRONY'
    
    # Lending
    if 'ONEMAIN' in merchant_upper or 'ONE MAIN' in merchant_upper:
        return 'ONEMAIN FINANCIAL'
    
    if 'LENDING CLUB' in merchant_upper:
        return 'LENDING CLUB'
    
    if 'SOFI' in merchant_upper:
        return 'SOFI'
    
    if 'UPSTART' in merchant_upper:
        return 'UPSTART'
    
    if 'ROCKET' in merchant_upper and ('MORTGAGE' in merchant_upper or 'LOANS' in merchant_upper):
        return 'ROCKET MORTGAGE'
    
    # Student Loans
    if 'DEPT EDUCATION' in merchant_upper or 'DEPARTMENT OF EDUCATION' in merchant_upper or 'ED FINANCIAL' in merchant_upper:
        return 'DEPT OF EDUCATION (STUDENT LOANS)'
    
    if 'NAVIENT' in merchant_upper:
        return 'NAVIENT'
    
    if 'NELNET' in merchant_upper:
        return 'NELNET'
    
    if 'GREAT LAKES' in merchant_upper and 'LOAN' in merchant_upper:
        return 'GREAT LAKES (STUDENT LOANS)'
    
    if 'MOHELA' in merchant_upper:
        return 'MOHELA'
    
    # ============================================================================
    # GAMING / BETTING
    # ============================================================================
    
    if 'FANDUEL' in merchant_upper:
        return 'FANDUEL'
    
    if 'DRAFTKINGS' in merchant_upper:
        return 'DRAFTKINGS'
    
    if 'BETMGM' in merchant_upper:
        return 'BETMGM'
    
    if 'CAESARS' in merchant_upper and ('SPORTSBOOK' in merchant_upper or 'CASINO' in merchant_upper):
        return 'CAESARS SPORTSBOOK'
    
    if 'POINTSBET' in merchant_upper:
        return 'POINTSBET'
    
    if 'BETRIVERS' in merchant_upper:
        return 'BETRIVERS'
    
    if 'BARSTOOL' in merchant_upper and 'SPORTSBOOK' in merchant_upper:
        return 'BARSTOOL SPORTSBOOK'
    
    if 'BETFAIR' in merchant_upper:
        return 'BETFAIR'
    
    if 'ILLINOIS STATE LOTTERY' in merchant_upper or 'IL LOTTERY' in merchant_upper:
        return 'ILLINOIS STATE LOTTERY'
    
    # ============================================================================
    # GOVERNMENT / MUNICIPAL
    # ============================================================================
    
    if merchant_upper.startswith('TOWN OF'):
        return 'MUNICIPAL PAYMENTS (TOWNS)'
    
    if merchant_upper.startswith('CITY OF'):
        return 'MUNICIPAL PAYMENTS (CITIES)'
    
    if 'COMMONWEALTH' in merchant_upper and 'SEC OF MA' in merchant_upper:
        return 'COMMONWEALTH OF MA'
    
    if 'IRS' in merchant_upper and ('TAX' in merchant_upper or 'PAYMENT' in merchant_upper):
        return 'IRS (TAX PAYMENTS)'
    
    if 'DMV' in merchant_upper or ('MOTOR VEHICLE' in merchant_upper and 'DEPT' in merchant_upper):
        return 'DMV'
    
    # ============================================================================
    # HEALTHCARE
    # ============================================================================
    
    if 'BLUE CROSS' in merchant_upper or 'BCBS' in merchant_upper:
        return 'BLUE CROSS BLUE SHIELD'
    
    if 'UNITED HEALTHCARE' in merchant_upper or 'UNITEDHEALTHCARE' in merchant_upper:
        return 'UNITED HEALTHCARE'
    
    if 'AETNA' in merchant_upper:
        return 'AETNA'
    
    if 'CIGNA' in merchant_upper:
        return 'CIGNA'
    
    if 'HUMANA' in merchant_upper:
        return 'HUMANA'
    
    if 'KAISER' in merchant_upper:
        return 'KAISER PERMANENTE'
    
    if 'CVS' in merchant_upper and 'PHARMACY' in merchant_upper:
        return 'CVS PHARMACY'
    
    if 'WALGREENS' in merchant_upper:
        return 'WALGREENS'
    
    if 'RITE AID' in merchant_upper:
        return 'RITE AID'

     
    # ============================================================================
    # Auto Loan Companies
    # ============================================================================
    
    if 'GM FINANCIAL' in merchant_upper:
        return 'GM FINANCIAL'
    
    if 'SANTANDER CONSUMER' in merchant_upper:
        return 'SANTANDER CONSUMER'
    
    if 'NISSAN MOTOR ACCEPTANCE' in merchant_upper:
        return 'NISSAN MOTOR ACCEPTANCE'
    
    if 'MAZDA FINANCIAL' in merchant_upper:
        return 'MAZDA FINANCIAL'
    
    if 'TOYOTA FINANCIAL' in merchant_upper:
        return 'TOYOTA FINANCIAL'
    
    if 'FORD MOTOR CREDIT' in merchant_upper:
        return 'FORD MOTOR CREDIT'
    
    if 'HONDA FINANCE' in merchant_upper:
        return 'HONDA FINANCE'
        
    # ============================================================================
    # If no explicit brand rule fired, return the NOISE-STRIPPED + UPPERCASED
    # version instead of the raw input. This is what lets CUs, local banks,
    # and other competitors get tagged correctly downstream: tag_competitors
    # prefix-matches on this value, so "SESLOC CREDIT UNION" (clean) works
    # but "ACH CREDIT SESLOC CREDIT UNION 805-555" (raw) does not.
    # ============================================================================
    return merchant_upper if merchant_upper else merchant_name
