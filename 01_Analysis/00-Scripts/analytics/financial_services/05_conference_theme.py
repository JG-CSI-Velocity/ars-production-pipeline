# ===========================================================================
# FINSERV CATEGORY PALETTE
# ===========================================================================
# Folder-specific category colors. Base theme from general/01_general_theme.

FS_CAT_PALETTE = {
    # Original bank-centric categories
    'Auto Loans':            '#E76F51',
    'Investment/Brokerage':  '#264653',
    'Treasury/Bonds':        '#2A9D8F',
    'Mortgage/HELOC':        '#E63946',
    'Personal Loans':        '#457B9D',
    'Credit Cards':          '#F4A261',
    'Student Loans':         '#6C757D',
    'Business Loans':        '#2EC4B6',
    # Non-bank financial competitors
    'Insurance':             '#9B2226',
    'BNPL/Pay Later':        '#BB3E03',
    'Crypto/Digital Assets': '#5A189A',
    'Tax & Accounting':      '#0077B6',
    'Financial Advisory':    '#606C38',
    'Debt Services':         '#D62828',
    'Credit Monitoring':     '#4A4E69',
    'Digital Wallets/P2P':   '#00B4D8',
}

def fs_get_color(cat):
    return FS_CAT_PALETTE.get(cat, GEN_COLORS['muted'])

print(f"FinServ palette loaded: {len(FS_CAT_PALETTE)} category colors")
print(f"  Bank-centric: 9  |  Non-bank: {len(FS_CAT_PALETTE) - 9}")
