# ===========================================================================
# COMPETITION CATEGORY PALETTE
# ===========================================================================
# Folder-specific category colors. Base theme from general/01_general_theme.

CATEGORY_PALETTE = {
    'Big Nationals':        '#E63946',
    'Top 25 Fed District':  '#C0392B',
    'Credit Unions':        '#2EC4B6',
    'Local Banks':          '#264653',
    'Digital Banks':        '#FF9F1C',
    'Custom':               '#F4A261',
    'Wallets':              '#6C757D',
    'P2p':                  '#A8DADC',
    'Bnpl':                 '#E76F51',
}

# Re-bind get_cat_color now that CATEGORY_PALETTE exists
def get_cat_color(cat_label):
    """Return palette color for a cleaned category label."""
    return CATEGORY_PALETTE.get(cat_label, GEN_COLORS['muted'])

# Derive display order from config (only categories with data)
if 'ALL_CATEGORIES' in dir():
    CATEGORY_ORDER = [
        clean_category(cat) for cat in ALL_CATEGORIES
        if cat in TRUE_COMPETITORS
    ]
else:
    CATEGORY_ORDER = ['Big Nationals', 'Top 25 Fed District', 'Credit Unions',
                      'Local Banks', 'Digital Banks']

print(f"Competition palette loaded: {len(CATEGORY_PALETTE)} category colors")
