# ===========================================================================
# CELL 1: CONFIGURATION - Financial Services Patterns
# ===========================================================================

FINANCIAL_SERVICES_PATTERNS = {
    'Auto Loans': [
        # OEM captive finance — full + heavy truncations
        'TOYOTA MOTOR CREDIT', 'TOYOTA FINANCIAL', 'TOYOTA FIN', 'TOYOTA MTR CR', 'TMCC',
        'VW CREDIT', 'VOLKSWAGEN CREDIT', 'VW CR',
        'FORD MOTOR CREDIT', 'FORD CREDIT', 'FORD MTR CR', 'FMCC',
        'GM FINANCIAL', 'GM FIN', 'GMAC',
        'HONDA FINANCE', 'HONDA FINANCIAL', 'HONDA FIN', 'AMERICAN HONDA FIN',
        'NISSAN MOTOR ACCEPTANCE', 'NISSAN FINANCIAL', 'NISSAN MTR ACCEPT', 'NMAC',
        'ALLY AUTO', 'ALLY FINANCIAL AUTO',
        'CAPITAL ONE AUTO', 'CAP ONE AUTO',
        'CHASE AUTO FINANCE', 'CHASE AUTO', 'CHASE AUTO FIN',
        'SANTANDER CONSUMER', 'SANTANDER CONS USA', 'CHRYSLER CAP', 'CCAP',
        'HYUNDAI MOTOR FINANCE', 'HYUNDAI MTR FIN', 'HYUNDAI CAPITAL',
        'KIA MOTORS FINANCE', 'KIA MTR FIN', 'KIA FINANCE',
        'SUBARU MOTOR FINANCE', 'SUBARU FIN',
        'MAZDA FINANCIAL', 'MAZDA FIN', 'MAZDA CAPITAL', 'TFS MAZDA',
        'BMW FINANCIAL', 'BMW FIN', 'BMW FINANCIAL SVCS',
        'MERCEDES-BENZ FINANCIAL', 'MERCEDES BENZ FIN', 'MB FINANCIAL SVCS', 'MBFS',
        'TESLA FINANCE', 'TESLA FIN', 'TESLA AUTO',
        'LEXUS FINANCIAL', 'LEXUS FIN',
        'ACURA FINANCIAL', 'ACURA FIN',
        'INFINITI FINANCIAL', 'INFINITI FIN',
        'AUDI FINANCIAL', 'AUDI FIN',
        'PORSCHE FINANCIAL', 'PORSCHE FIN',
        # Non-captive auto lenders
        'CARMAX AUTO FINANCE', 'CARMAX FIN', 'CAF AUTO',
        'WESTLAKE FINANCIAL', 'WESTLAKE FIN',
        'CREDIT ACCEPTANCE',
        'EXETER FINANCE',
        'GLOBAL LENDING',
        'BRIDGECREST',
        'AMERICAN CREDIT ACCEPTANCE',
        'WORLD OMNI FINANCIAL',
    ],

    'Investment/Brokerage': [
        # Wirehouses
        'MORGAN STANLEY CLIENT', 'MORGAN STANLEY BROKERAGE', 'MORGAN STANLEY',
        'RAYMOND JAMES ASSOC', 'RAYMOND JAMES & ASSOC', 'RAYMOND JAMES',
        'MERRILL LYNCH', 'MERRILL EDGE', 'MERRILL',
        'WELLS FARGO ADVISORS', 'WELLS FARGO CLEARING',
        # Brokerages (full + collapsed)
        'CHARLES SCHWAB', 'SCHWAB BROKERAGE', 'SCHWAB & CO', 'SCHWAB CLIENT', 'SCHWAB',
        'FIDELITY INVESTMENTS', 'FIDELITY BROKERAGE', 'FIDELITY NETBENEFITS', 'FIDELITY',
        'VANGUARD BROKERAGE', 'VANGUARD GROUP', 'VANGUARD',
        'E*TRADE', 'ETRADE', 'E TRADE', 'ETRADE SECURITIES',
        'TD AMERITRADE', 'AMERITRADE',
        'RBC CAPITAL MARKETS', 'RBC WEALTH',
        'LPL FINANCIAL', 'LPL FIN',
        'EDWARD JONES INVESTMENTS',
        # Robo-advisors
        'BETTERMENT LLC', 'BETTERMENT', 'BETTERMENT HOLDINGS',
        'WEALTHFRONT BROKERAGE', 'WEALTHFRONT',
        'ACORNS SECURITIES', 'ACORNS INVESTMENT', 'ACORNS',
        'STASH INVEST', 'STASH FINANCIAL',
        'M1 FINANCE', 'M1 HOLDINGS',
        # Retail brokers
        'ROBINHOOD SECURITIES', 'ROBINHOOD MARKETS',
        'WEBULL CORPORATION', 'WEBULL FINANCIAL', 'WEBULL',
        'INTERACTIVE BROKERS', 'IBKR',
        'TASTYTRADE', 'TASTYWORKS',
        'PUBLIC HOLDINGS', 'PUBLIC INVEST',
        # Mutual fund / advisor families
        'T ROWE PRICE', 'T. ROWE PRICE', 'TROWE PRICE',
        'AMERICAN FUNDS',
        'FRANKLIN TEMPLETON',
        'BLACKROCK', 'ISHARES',
        'DODGE & COX',
    ],

    'Treasury/Bonds': [
        'TREASURY DIRECT', 'TREASURYDIRECT', 'TREAS DIR',
        'US TREASURY', 'U S TREASURY',
        'I BOND', 'EE BOND',
        'FED RESERVE', 'FEDERAL RESERVE',
    ],

    'Mortgage/HELOC': [
        'ROCKET MORTGAGE', 'ROCKET MTG', 'QUICKEN LOANS', 'QUICKEN MTG',
        'PENNYMAC LOAN', 'PENNYMAC CORP', 'PENNYMAC',
        'FREEDOM MORTGAGE', 'FREEDOM MTG',
        'MR COOPER MORTGAGE', 'MR COOPER', 'MR COOPER MTG',
        'CALIBER HOME LOANS', 'CALIBER HOMES',
        'OCWEN LOAN', 'OCWEN FINANCIAL',
        'NEWREZ LLC', 'NEWREZ MTG', 'NEWREZ',
        'FLAGSTAR BANK MORTGAGE', 'FLAGSTAR MTG',
        'LAKEVIEW LOAN', 'LAKEVIEW MTG',
        'CARRINGTON MORTGAGE', 'CARRINGTON MTG',
        'GUILD MORTGAGE', 'GUILD MTG',
        'UNITED WHOLESALE MORTGAGE', 'UWM',
        'LOAN DEPOT', 'LOANDEPOT', 'LDEPOT',
        'BETTER COM', 'BETTER.COM', 'BETTER MORTGAGE',
        'WELLS FARGO HOME MTG', 'WELLS FARGO HOME LOANS',
        'CHASE HOME LENDING', 'CHASE HOME MTG',
        'CITIMORTGAGE', 'CITI HOME LOANS',
        'BANK OF AMERICA HOME LOANS',
        'AMERIHOME MORTGAGE',
        'NATIONSTAR MORTGAGE', 'NATIONSTAR',
        'BAYVIEW LOAN',
        'PHH MORTGAGE',
    ],

    'Personal Loans': [
        'SOFI LENDING', 'SOFI LOAN', 'SOFI PERSONAL', 'SOFI BANK',
        'LENDING CLUB CORP', 'LENDING CLUB', 'LC PERSONAL',
        'PROSPER FUNDING', 'PROSPER MARKETPLACE',
        'UPSTART NETWORK', 'UPSTART HOLDINGS', 'UPSTART',
        'MARCUS BY GOLDMAN', 'MARCUS PERSONAL', 'MARCUS GOLDMAN', 'MARCUS LOAN',
        'DISCOVER PERSONAL LOANS', 'DISCOVER PERS LOANS',
        'LIGHTSTREAM', 'TRUIST LIGHTSTREAM',
        'PAYOFF INC', 'HAPPY MONEY',
        'BEST EGG', 'BEST EGG LOAN', 'MARLETTE FUNDING',
        'AVANT', 'AVANT INC',
        'ONEMAIN FINANCIAL', 'ONE MAIN', 'ONEMAIN',
        'OPORTUN',
        'LENDINGPOINT',
        'UPGRADE INC', 'UPGRADE LENDING',
    ],

    'Credit Cards': [
        # Amex
        'AMEX EPAYMENT', 'AMEX EPMT', 'AMERICAN EXPRESS PAYMENT',
        'AMERICAN EXPRESS AUTOPAY', 'AMERICAN EXPRESS', 'AMEX',
        # Discover
        'DISCOVER CARD PAYMENT', 'DISCOVER E-PAYMENT', 'DISCOVER PMT',
        # Capital One
        'CAPITAL ONE CREDIT CARD', 'CAPITAL ONE CC PAYMENT', 'CAPITAL ONE CC',
        'CAP ONE CC',
        # Citi
        'CITI CARD PAYMENT', 'CITICARDS PAYMENT', 'CITICARDS CBNA',
        # Barclays
        'BARCLAYS CREDIT CARD', 'BARCLAYCARD PAYMENT', 'BARCLAYCARD',
        'BARCLAYS',
        # Synchrony
        'SYNCHRONY BANK PAYMENT', 'SYNCHRONY CREDIT', 'SYNCB',
        # Chase cards
        'CHASE CARD SERVICES', 'CHASE CREDIT CARD PAYMENT', 'CHASE CC PMT',
        # Other issuers
        'COMENITY BANK', 'COMENITY CAPITAL',
        'BREAD FINANCIAL',
    ],

    'Student Loans': [
        'DEPT OF EDUCATION', 'DEPARTMENT OF EDUCATION', 'US DEPT OF ED',
        'ED FINANCIAL SERVICES', 'EDFINANCIAL', 'EDFIN',
        'NAVIENT CORPORATION', 'NAVIENT PAYMENT', 'NAVIENT',
        'NELNET PAYMENT', 'NELNET LOAN', 'NELNET',
        'GREAT LAKES BORROWER', 'GREAT LAKES HIGHER ED', 'GREAT LAKES',
        'MOHELA LOAN', 'MOHELA',
        'AIDVANTAGE',
        'EARNEST OPERATIONS', 'EARNEST INC',
        'COMMONBOND LENDING', 'COMMONBOND',
        'FEDLOAN SERVICING', 'FEDLOAN', 'FEDERAL LOAN SVCS',
        'SALLIE MAE', 'SALLIE MAE BANK',
        'COLLEGE AVE', 'COLLEGE AVE STUDENT',
        'ASCENT FUNDING',
    ],

    'Business Loans': [
        'SBA LOAN PAYMENT', 'SMALL BUSINESS ADMIN', 'SBA',
        'KABBAGE INC', 'KABBAGE',
        'BLUEVINE CAPITAL', 'BLUEVINE',
        'FUNDBOX INC', 'FUNDBOX',
        'LENDIO FUNDING', 'LENDIO',
        'AMERICAN EXPRESS BUSINESS LOAN', 'AMEX BUSINESS FINANCING', 'AMEX BUS LOAN',
        'PAYPAL WORKING CAPITAL', 'PAYPAL BUSINESS LOAN',
        'SQUARE CAPITAL', 'SQUARE FINANCIAL',
        'ONDECK CAPITAL', 'ONDECK',
        'CREDIBLY', 'NATIONAL FUNDING',
        'BUSINESS LOAN BUILDER',
    ],

    'Insurance': [
        'STATE FARM', 'STATEFARM', 'STATE FARM INS', 'STATE FARM PMT',
        'GEICO', 'GEICO INSURANCE', 'GEICO INS', 'GEICO PMT',
        'PROGRESSIVE INSURANCE', 'PROGRESSIVE CASUALTY', 'PROGRESSIVE INS',
        'PROGRESSIVE', 'PROGRESSIVE POL',
        'ALLSTATE INSURANCE', 'ALLSTATE PAYMENT', 'ALLSTATE INS', 'ALLSTATE',
        'USAA INSURANCE', 'USAA PROPERTY', 'USAA INS', 'USAA P&C',
        'FARMERS INSURANCE', 'FARMERS GROUP', 'FARMERS INS',
        'LIBERTY MUTUAL', 'LIBERTY INSURANCE', 'LIBERTY MUT', 'LIBERTY MUT INS',
        'NATIONWIDE INSURANCE', 'NATIONWIDE MUTUAL', 'NATIONWIDE INS', 'NATIONWIDE',
        'TRAVELERS INSURANCE', 'TRAVELERS INDEMNITY', 'TRAVELERS INS', 'TRAVELERS',
        'AMERICAN FAMILY INSURANCE', 'AMFAM', 'AMFAM INS', 'AMERICAN FAMILY INS',
        'ERIE INSURANCE', 'ERIE INDEMNITY', 'ERIE INS',
        'METLIFE INSURANCE', 'METLIFE PAYMENT', 'METLIFE INS', 'METLIFE',
        'PRUDENTIAL INSURANCE', 'PRUDENTIAL FINANCIAL', 'PRUDENTIAL INS',
        'NEW YORK LIFE', 'NEW YORK LIFE INSURANCE', 'NYL INS', 'NYL',
        'NORTHWESTERN MUTUAL', 'NORTHWESTERN MUTUAL LIFE', 'NW MUTUAL',
        'LINCOLN FINANCIAL', 'LINCOLN NATIONAL', 'LINCOLN BENEFIT',
        'GUARDIAN LIFE', 'GUARDIAN INSURANCE', 'GUARDIAN INS',
        'PRINCIPAL FINANCIAL', 'PRINCIPAL LIFE', 'PRINCIPAL INS',
        'AFLAC', 'AFLAC INSURANCE', 'AFLAC INS',
        'LEMONADE INSURANCE', 'LEMONADE INC', 'LEMONADE',
        'ROOT INSURANCE', 'ROOT INS',
        'HIPPO INSURANCE', 'HIPPO INS',
        'THE HARTFORD', 'HARTFORD FIN', 'HARTFORD INS',
        'THE GENERAL INS', 'THE GENERAL AUTO',
        'MERCURY INSURANCE', 'MERCURY INS',
        'KEMPER INSURANCE', 'KEMPER INS',
        'INFINITY INSURANCE', 'INFINITY INS',
        '21ST CENTURY INS', '21ST CENTURY',
        'ESURANCE',
        'AAA INSURANCE', 'AAA INS',
        'AARP INSURANCE',
        'CIGNA HEALTH', 'CIGNA INS',
        'AETNA HEALTH', 'AETNA INS',
        'BLUE CROSS', 'BLUECROSS', 'BCBS',
        'ANTHEM',
        'UNITED HEALTHCARE', 'UHC',
        'HUMANA', 'HUMANA INS',
        'GENWORTH',
        'MUTUAL OF OMAHA',
    ],

    # 'BNPL/Pay Later' is built dynamically below from UNIVERSAL_ECOSYSTEMS

    'Crypto/Digital Assets': [
        'COINBASE', 'COINBASE INC', 'COINBASE PRO', 'COINBASE.COM', 'COINBASE EXCHANGE',
        'CRYPTO.COM', 'CRYPTO COM',
        'BINANCE', 'BINANCE US', 'BINANCE.US',
        'KRAKEN', 'KRAKEN.COM', 'PAYWARD INC', 'PAYWARD',
        'GEMINI EXCHANGE', 'GEMINI TRUST', 'GEMINI.COM', 'GEMINI',
        'BITPAY', 'BLOCKCHAIN COM', 'BLOCKCHAIN.COM',
        'CASHAPP BITCOIN', 'CASH APP BTC', 'CASHAPP BTC',
        'ROBINHOOD CRYPTO',
        'BLOCKFI', 'BLOCKFI LENDING',
        'CELSIUS NETWORK',
        'NEXO',
        'BITSTAMP',
        'BITTREX',
        'METAMASK',
        'PHANTOM WALLET',
    ],

    'Tax & Accounting': [
        'TURBOTAX', 'INTUIT TURBOTAX', 'INTUIT TAX', 'INTUIT*TURBOTAX',
        'H&R BLOCK', 'H R BLOCK', 'HRB TAX', 'HRBLOCK', 'H AND R BLOCK',
        'JACKSON HEWITT', 'JACKSON HEWITT TAX',
        'LIBERTY TAX', 'LIBERTY TAX SVC',
        'TAX ACT', 'TAXACT',
        'TAXSLAYER', 'FREETAXUSA', 'FREE TAX USA',
        'QUICKBOOKS', 'INTUIT QUICKBOOKS', 'INTUIT QB', 'QB ONLINE',
        'INTUIT PROCONNECT',
        'FRESHBOOKS',
        'XERO ACCOUNTING', 'XERO',
        'WAVE ACCOUNTING',
        'PWC', 'DELOITTE', 'KPMG', 'ERNST YOUNG',
        # Note: short names like 'PWC' kept here; FP guard handles edge cases.
    ],

    'Financial Advisory': [
        'EDWARD JONES', 'EDWARD D JONES', 'EDWARDS JONES',
        'PRIMERICA', 'PRIMERICA FINANCIAL', 'PRIMERICA INC',
        'AMERIPRISE', 'AMERIPRISE FINANCIAL', 'AMERIPRISE FIN',
        'TRANSAMERICA', 'TRANSAMERICA LIFE', 'TRANSAMERICA FIN',
        'MASS MUTUAL', 'MASSMUTUAL', 'MASSMUTUAL FIN',
        'TIAA', 'TIAA-CREF', 'TIAA CREF',
        'JOHN HANCOCK', 'JOHN HANCOCK LIFE', 'JOHN HANCOCK FIN',
        'EMPOWER RETIREMENT', 'EMPOWER', 'EMPOWER FINANCIAL',
        'GREAT-WEST LIFE', 'GREAT WEST LIFE',
        'VOYA', 'VOYA FINANCIAL', 'VOYA FIN',
        'NATIONWIDE FINANCIAL', 'NATIONWIDE INV',
        'AXA EQUITABLE', 'EQUITABLE',
        'WADDELL REED',
        'FISHER INVESTMENTS',
        'STIFEL NICOLAUS',
        'ALLIANZ LIFE',
        'PACIFIC LIFE',
    ],

    'Debt Services': [
        'NATIONAL DEBT RELIEF', 'NATL DEBT RELIEF',
        'FREEDOM DEBT RELIEF', 'FREEDOM DEBT',
        'CREDIT COUNSELING',
        'GREENPATH FINANCIAL', 'GREENPATH',
        'MONEY MANAGEMENT INTL', 'MMI',
        'NFCC',
        'DEBT.COM', 'DEBT COM',
        'CONSOLIDATED CREDIT',
        'ACCREDITED DEBT RELIEF',
        'NEW ERA DEBT',
        'CURADEBT',
        'PACIFIC DEBT',
    ],

    'Credit Monitoring': [
        'EXPERIAN', 'EXPERIAN CREDIT', 'EXPERIAN*',
        'TRANSUNION', 'TRANSUNION CREDIT', 'TRANSUNION INTERAC',
        'EQUIFAX', 'EQUIFAX CREDIT', 'EQUIFAX*',
        'CREDIT KARMA', 'CREDITKARMA',
        'IDENTITY GUARD',
        'LIFELOCK', 'LIFELOCK NORTON', 'NORTON LIFELOCK',
        'MYFICO', 'FICO SCORE',
        'IDENTITYFORCE',
        'PRIVACYGUARD',
        'ZANDER ID THEFT',
    ],

    'Retirement / 401k': [
        'EMPOWER RETIREMENT', 'EMPOWER',
        'FIDELITY 401K', 'FIDELITY NETBENEFITS',
        'VANGUARD 401K', 'VANGUARD RETIREMENT',
        'TROWE PRICE RETIREMENT',
        'ALIGHT SOLUTIONS',
        'TRANSAMERICA RETIREMENT',
        'PRINCIPAL RETIREMENT',
        'VOYA RETIREMENT',
        'ASCENSUS', 'ASCENSUS RETIREMENT',
    ],

    'HSA / FSA': [
        'HSA BANK', 'HSABANK',
        'HEALTH EQUITY', 'HEALTHEQUITY',
        'FIDELITY HSA',
        'OPTUM BANK', 'OPTUM HSA',
        'WAGEWORKS', 'HEALTH SAVINGS',
        'PAYFLEX',
        'WEX HEALTH',
    ],

    # 'Digital Wallets/P2P' is built dynamically below from UNIVERSAL_ECOSYSTEMS

    # NOTE: "Other Banks" removed. Competitor bank detection is handled
    # by section 06 (tag_competitors). This section focuses on financial
    # products/services, not institutions.
}

# ---------------------------------------------------------------------------
# Addressable vs context categories (owner decision 2026-06-14)
# ---------------------------------------------------------------------------
# The "leakage" headline should reflect products the FI can realistically win
# back. Insurance and Tax & Accounting are near-universal and NOT capturable by
# a credit union, so they are reported as context, not headline leakage.
NON_ADDRESSABLE_CATEGORIES = ['Insurance', 'Tax & Accounting']
ADDRESSABLE_CATEGORIES = [c for c in FINANCIAL_SERVICES_PATTERNS
                          if c not in NON_ADDRESSABLE_CATEGORIES]

# ---------------------------------------------------------------------------
# Auto-build BNPL and Wallets/P2P from UNIVERSAL_ECOSYSTEMS (section 06)
# Single source of truth — both sections use the same patterns.
# ---------------------------------------------------------------------------
if 'UNIVERSAL_ECOSYSTEMS' in dir():
    if 'bnpl' in UNIVERSAL_ECOSYSTEMS:
        FINANCIAL_SERVICES_PATTERNS['BNPL/Pay Later'] = \
            UNIVERSAL_ECOSYSTEMS['bnpl'].get('starts_with', [])
    _wallet_p2p = []
    for _eco_key in ('wallets', 'p2p'):
        if _eco_key in UNIVERSAL_ECOSYSTEMS:
            _wallet_p2p.extend(UNIVERSAL_ECOSYSTEMS[_eco_key].get('starts_with', []))
    if _wallet_p2p:
        FINANCIAL_SERVICES_PATTERNS['Digital Wallets/P2P'] = _wallet_p2p

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

config_rows = []
for category, patterns in FINANCIAL_SERVICES_PATTERNS.items():
    config_rows.append({
        'Category': category,
        'Patterns': len(patterns),
    })

config_df = pd.DataFrame(config_rows).sort_values('Patterns', ascending=True)
total_patterns = config_df['Patterns'].sum()

# --- Conference-grade visual ---
fig, ax = plt.subplots(figsize=(14, max(7, len(config_df) * 0.55)))

_DARK = '#1B2A4A'
_ACCENT = '#E63946'
_MUTED = '#6C757D'
_BG = '#F8F9FA'

bar_colors = [_ACCENT if v == config_df['Patterns'].max() else '#3A7CA5' for v in config_df['Patterns']]

bars = ax.barh(range(len(config_df)), config_df['Patterns'],
               color=bar_colors, edgecolor='white', linewidth=1.5, height=0.65, zorder=3)

for i, (_, row) in enumerate(config_df.iterrows()):
    ax.text(row['Patterns'] + 0.5, i, f"{row['Patterns']}",
            fontsize=16, fontweight='bold', color=_DARK, va='center')

ax.set_yticks(range(len(config_df)))
ax.set_yticklabels(config_df['Category'], fontsize=15, fontweight='bold', color=_DARK)
ax.set_xlabel('Merchant Patterns Tracked', fontsize=16, fontweight='bold', color=_DARK, labelpad=12)

ax.set_xlim(0, config_df['Patterns'].max() * 1.25)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color(_MUTED)
ax.tick_params(left=False, bottom=True, colors=_MUTED)
ax.xaxis.grid(True, color='#E0E0E0', linewidth=0.5, alpha=0.5)
ax.set_axisbelow(True)

ax.set_title('Financial Services Detection Engine',
             fontsize=26, fontweight='bold', color=_DARK, pad=20, loc='left')
ax.text(0.0, 0.97,
        f"{len(config_df)} categories  |  {total_patterns} total merchant patterns",
        transform=ax.transAxes, fontsize=14, color=_MUTED, style='italic')

plt.tight_layout()
plt.show()
