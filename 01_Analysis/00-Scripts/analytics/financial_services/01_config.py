# ===========================================================================
# CELL 1: CONFIGURATION - Financial Services Patterns
# ===========================================================================

FINANCIAL_SERVICES_PATTERNS = {
    'Auto Loans': [
        'TOYOTA MOTOR CREDIT', 'TOYOTA FINANCIAL',
        'VW CREDIT', 'VOLKSWAGEN CREDIT',
        'FORD MOTOR CREDIT', 'FORD CREDIT',
        'GM FINANCIAL', 'HONDA FINANCE', 'HONDA FINANCIAL',
        'NISSAN MOTOR ACCEPTANCE', 'NISSAN FINANCIAL',
        'ALLY AUTO', 'CAPITAL ONE AUTO', 'CHASE AUTO FINANCE',
        'SANTANDER CONSUMER', 'HYUNDAI MOTOR FINANCE',
        'KIA MOTORS FINANCE', 'SUBARU MOTOR FINANCE',
        'MAZDA FINANCIAL', 'BMW FINANCIAL',
        'MERCEDES-BENZ FINANCIAL', 'TESLA FINANCE'
    ],

    'Investment/Brokerage': [
        'MORGAN STANLEY CLIENT', 'MORGAN STANLEY BROKERAGE',
        'RAYMOND JAMES ASSOC', 'RAYMOND JAMES & ASSOC',
        'CHARLES SCHWAB', 'SCHWAB BROKERAGE',
        'FIDELITY INVESTMENTS', 'FIDELITY BROKERAGE',
        'VANGUARD BROKERAGE', 'VANGUARD GROUP',
        'E\\*TRADE', 'ETRADE', 'TD AMERITRADE',
        'MERRILL LYNCH', 'MERRILL EDGE',
        'RBC CAPITAL MARKETS', 'LPL FINANCIAL',
        'BETTERMENT LLC', 'WEALTHFRONT BROKERAGE',
        'ROBINHOOD SECURITIES', 'WEBULL CORPORATION',
        'INTERACTIVE BROKERS', 'TASTYTRADE'
    ],

    'Treasury/Bonds': [
        'TREASURY DIRECT', 'TREASURYDIRECT', 'US TREASURY'
    ],

    'Mortgage/HELOC': [
        'ROCKET MORTGAGE', 'QUICKEN LOANS',
        'PENNYMAC LOAN', 'PENNYMAC CORP',
        'FREEDOM MORTGAGE', 'MR COOPER MORTGAGE',
        'CALIBER HOME LOANS', 'OCWEN LOAN',
        'NEWREZ LLC', 'FLAGSTAR BANK MORTGAGE',
        'LAKEVIEW LOAN', 'CARRINGTON MORTGAGE',
        'GUILD MORTGAGE', 'UNITED WHOLESALE MORTGAGE'
    ],

    'Personal Loans': [
        'SOFI LENDING', 'SOFI LOAN',
        'LENDING CLUB CORP', 'PROSPER FUNDING',
        'UPSTART NETWORK', 'MARCUS BY GOLDMAN',
        'MARCUS PERSONAL', 'DISCOVER PERSONAL LOANS',
        'LIGHTSTREAM', 'PAYOFF INC', 'BEST EGG'
    ],

    'Credit Cards': [
        'AMEX EPAYMENT', 'AMERICAN EXPRESS PAYMENT',
        'AMERICAN EXPRESS AUTOPAY',
        'DISCOVER CARD PAYMENT', 'DISCOVER E-PAYMENT',
        'CAPITAL ONE CREDIT CARD', 'CAPITAL ONE CC PAYMENT',
        'CITI CARD PAYMENT', 'CITICARDS PAYMENT',
        'BARCLAYS CREDIT CARD', 'BARCLAYCARD PAYMENT',
        'SYNCHRONY BANK PAYMENT', 'SYNCHRONY CREDIT',
        'CHASE CARD SERVICES', 'CHASE CREDIT CARD PAYMENT'
    ],

    'Student Loans': [
        'DEPT OF EDUCATION', 'DEPARTMENT OF EDUCATION',
        'ED FINANCIAL SERVICES',
        'NAVIENT CORPORATION', 'NAVIENT PAYMENT',
        'NELNET PAYMENT', 'NELNET LOAN',
        'GREAT LAKES BORROWER', 'GREAT LAKES HIGHER ED',
        'MOHELA LOAN', 'AIDVANTAGE',
        'EARNEST OPERATIONS', 'COMMONBOND LENDING'
    ],

    'Business Loans': [
        'SBA LOAN PAYMENT', 'SMALL BUSINESS ADMIN',
        'KABBAGE INC', 'BLUEVINE CAPITAL',
        'FUNDBOX INC', 'LENDIO FUNDING',
        'AMERICAN EXPRESS BUSINESS LOAN',
        'AMEX BUSINESS FINANCING',
        'PAYPAL WORKING CAPITAL', 'SQUARE CAPITAL',
        'ONDECK CAPITAL'
    ],

    'Insurance': [
        'STATE FARM', 'STATEFARM',
        'GEICO', 'GEICO INSURANCE',
        'PROGRESSIVE INSURANCE', 'PROGRESSIVE CASUALTY',
        'ALLSTATE INSURANCE', 'ALLSTATE PAYMENT',
        'USAA INSURANCE', 'USAA PROPERTY',
        'FARMERS INSURANCE', 'FARMERS GROUP',
        'LIBERTY MUTUAL', 'LIBERTY INSURANCE',
        'NATIONWIDE INSURANCE', 'NATIONWIDE MUTUAL',
        'TRAVELERS INSURANCE', 'TRAVELERS INDEMNITY',
        'AMERICAN FAMILY INSURANCE', 'AMFAM',
        'ERIE INSURANCE', 'ERIE INDEMNITY',
        'METLIFE INSURANCE', 'METLIFE PAYMENT',
        'PRUDENTIAL INSURANCE', 'PRUDENTIAL FINANCIAL',
        'NEW YORK LIFE', 'NEW YORK LIFE INSURANCE',
        'NORTHWESTERN MUTUAL', 'NORTHWESTERN MUTUAL LIFE',
        'LINCOLN FINANCIAL', 'LINCOLN NATIONAL',
        'GUARDIAN LIFE', 'GUARDIAN INSURANCE',
        'PRINCIPAL FINANCIAL', 'PRINCIPAL LIFE',
        'AFLAC', 'AFLAC INSURANCE',
        'LEMONADE INSURANCE', 'LEMONADE INC',
        'ROOT INSURANCE', 'HIPPO INSURANCE',
    ],

    # 'BNPL/Pay Later' is built dynamically below from UNIVERSAL_ECOSYSTEMS

    'Crypto/Digital Assets': [
        'COINBASE', 'COINBASE INC', 'COINBASE PRO',
        'CRYPTO.COM', 'CRYPTO COM',
        'BINANCE', 'BINANCE US',
        'KRAKEN', 'PAYWARD INC',
        'GEMINI EXCHANGE', 'GEMINI TRUST',
        'BITPAY', 'BLOCKCHAIN COM',
        'CASHAPP BITCOIN', 'CASH APP BTC',
        'ROBINHOOD CRYPTO',
    ],

    'Tax & Accounting': [
        'TURBOTAX', 'INTUIT TURBOTAX', 'INTUIT TAX',
        'H&R BLOCK', 'H R BLOCK', 'HRB TAX',
        'JACKSON HEWITT', 'JACKSON HEWITT TAX',
        'LIBERTY TAX', 'TAX ACT', 'TAXACT',
        'TAXSLAYER', 'FREETAXUSA',
        'QUICKBOOKS', 'INTUIT QUICKBOOKS',
    ],

    'Financial Advisory': [
        'EDWARD JONES', 'EDWARD D JONES',
        'PRIMERICA', 'PRIMERICA FINANCIAL',
        'AMERIPRISE', 'AMERIPRISE FINANCIAL',
        'TRANSAMERICA', 'TRANSAMERICA LIFE',
        'MASS MUTUAL', 'MASSMUTUAL',
        'TIAA', 'TIAA-CREF', 'TIAA CREF',
        'JOHN HANCOCK', 'JOHN HANCOCK LIFE',
        'EMPOWER RETIREMENT', 'GREAT-WEST LIFE',
    ],

    'Debt Services': [
        'NATIONAL DEBT RELIEF', 'FREEDOM DEBT RELIEF',
        'CREDIT COUNSELING', 'GREENPATH FINANCIAL',
        'MONEY MANAGEMENT INTL', 'NFCC',
        'DEBT.COM', 'CONSOLIDATED CREDIT',
        'ACCREDITED DEBT RELIEF', 'NEW ERA DEBT',
    ],

    'Credit Monitoring': [
        'EXPERIAN', 'EXPERIAN CREDIT',
        'TRANSUNION', 'TRANSUNION CREDIT',
        'EQUIFAX', 'EQUIFAX CREDIT',
        'CREDIT KARMA', 'CREDITKARMA',
        'IDENTITY GUARD', 'LIFELOCK',
        'MYFICO', 'FICO SCORE',
    ],

    # 'Digital Wallets/P2P' is built dynamically below from UNIVERSAL_ECOSYSTEMS

    # NOTE: "Other Banks" removed. Competitor bank detection is handled
    # by section 06 (tag_competitors). This section focuses on financial
    # products/services, not institutions.
}

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
