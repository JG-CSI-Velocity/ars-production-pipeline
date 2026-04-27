# ===========================================================================
# COMPETITOR DETECTION & SUMMARY (Conference Edition)
# ===========================================================================
# Tags all competitor transactions, builds downstream variables,
# and renders a conference-quality detection summary panel.

# -------------------------------------------------------------------------
# Defensive: theme / palette fallbacks
# -------------------------------------------------------------------------
# The Panel 2 rendering block below references CATEGORY_PALETTE, GEN_COLORS,
# gen_fmt_count, and gen_clean_axes. Those normally come from
# (analytics/general/*) + (competition/06_conference_theme.py). If the user
# runs this cell before those — which is natural since 06 > 02 — we hit
# NameError (#76). Provide sensible defaults so this cell runs standalone.

try:
    CATEGORY_PALETTE
except NameError:
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

try:
    GEN_COLORS
except NameError:
    GEN_COLORS = {
        'dark_text': '#1f2d3a',
        'muted':     '#6C757D',
        'grid':      '#DDDDDD',
    }

try:
    gen_fmt_count
except NameError:
    def gen_fmt_count(x, _pos=None):
        return f"{int(x):,}"

try:
    gen_clean_axes
except NameError:
    def gen_clean_axes(ax, keep_left=False, keep_bottom=False):
        for _spine in ('top', 'right'):
            ax.spines[_spine].set_visible(False)
        if not keep_left:
            ax.spines['left'].set_visible(False)
        if not keep_bottom:
            ax.spines['bottom'].set_visible(False)

# Tag competitors using the matching function from 01_competitor_config
combined_df = tag_competitors(combined_df, merchant_col='merchant_consolidated')

# Build summary from tagged results
competitor_txns = combined_df[combined_df['competitor_category'].notna()].copy()
competitor_txns['competitor_match'] = competitor_txns['merchant_consolidated'].apply(normalize_competitor_name)

summary_data = competitor_txns.groupby(['competitor_category', 'competitor_match']).agg(
    total_transactions=('amount', 'count'),
    unique_accounts=('primary_account_num', 'nunique'),
    total_amount=('amount', 'sum')
).reset_index().rename(columns={
    'competitor_category': 'category',
    'competitor_match': 'competitor'
}).sort_values('total_amount', ascending=False)

# Build per-competitor dict keyed by normalized name (merges variant groups)
all_competitor_data = {
    name: group for name, group in competitor_txns.groupby('competitor_match')
}

# Also tag business and personal if they exist
if 'business_df' in dir() and len(business_df) > 0:
    business_df = tag_competitors(business_df, merchant_col='merchant_consolidated')
if 'personal_df' in dir() and len(personal_df) > 0:
    personal_df = tag_competitors(personal_df, merchant_col='merchant_consolidated')

# ---------------------------------------------------------------------------
# Conference summary panel
# ---------------------------------------------------------------------------
total_accounts = combined_df['primary_account_num'].nunique()
comp_accounts = competitor_txns['primary_account_num'].nunique()

if len(competitor_txns) == 0:
    print("\nNo competitor transactions found.")
else:
    pct_comp_txns = len(competitor_txns) / len(combined_df) * 100
    pct_comp_accounts = comp_accounts / total_accounts * 100
    unique_competitors = competitor_txns['competitor_match'].nunique()
    n_categories = competitor_txns['competitor_category'].nunique()
    true_txns = len(competitor_txns[competitor_txns['competitor_category'].isin(TRUE_COMPETITORS)])
    eco_txns = len(competitor_txns[competitor_txns['competitor_category'].isin(PAYMENT_ECOSYSTEMS)])

    # --- Panel 1: Detection KPIs ---
    kpis = [
        (f"{len(combined_df):,}",     "Transactions\nSearched",         GEN_COLORS['info']),
        (f"{len(competitor_txns):,}",  "Competitor\nTransactions",       GEN_COLORS['accent']),
        (f"{pct_comp_accounts:.1f}%",  "Accounts with\nCompetitor Activity", GEN_COLORS['accent']),
        (f"{unique_competitors}",      "Unique\nCompetitors",            GEN_COLORS['warning']),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(20, 4.5))
    fig.patch.set_facecolor('#FFFFFF')
    fig.suptitle("Competitor Detection Results",
                 fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)

    for ax, (value, label, color) in zip(axes, kpis):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        card = FancyBboxPatch(
            (0.03, 0.05), 0.94, 0.90,
            boxstyle="round,pad=0.05",
            facecolor=color, alpha=0.08,
            edgecolor=color, linewidth=2.5,
        )
        ax.add_patch(card)
        ax.text(0.5, 0.62, value, transform=ax.transAxes,
                fontsize=40, fontweight='bold', color=color, ha='center', va='center')
        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'],
                ha='center', va='center', linespacing=1.4)

    plt.tight_layout()
    plt.show()

    # --- Panel 2: Category breakdown (horizontal bar) + true vs ecosystem (donut) ---
    cat_summary = competitor_txns.groupby('competitor_category').agg(
        transactions=('amount', 'count'),
        accounts=('primary_account_num', 'nunique')
    ).sort_values('transactions', ascending=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 6), gridspec_kw={'width_ratios': [3, 2]})
    fig.patch.set_facecolor('#FFFFFF')

    # Left: category bar
    cat_labels = [c.replace('_', ' ').title() for c in cat_summary.index]
    cat_colors = [CATEGORY_PALETTE.get(c, GEN_COLORS['muted']) for c in cat_labels]
    plot_labels = cat_labels[::-1]
    plot_vals = cat_summary['transactions'].values[::-1]
    plot_colors = cat_colors[::-1]
    plot_accounts = cat_summary['accounts'].values[::-1]

    bars = ax1.barh(range(len(plot_labels)), plot_vals,
                    color=plot_colors, edgecolor='white', linewidth=1, height=0.65, zorder=3)

    for i, (val, accts) in enumerate(zip(plot_vals, plot_accounts)):
        ax1.text(val * 1.01, i, f"{val:,}  ({accts:,} accts)",
                 fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'], va='center')

    ax1.set_yticks(range(len(plot_labels)))
    ax1.set_yticklabels(plot_labels, fontsize=13, fontweight='bold')
    ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    max_val = plot_vals.max()
    ax1.set_xlim(0, max_val * 1.4)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Transactions by Category", fontsize=20, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=15, loc='left')

    # Right: true competitors vs ecosystem donut
    donut_vals = [true_txns, eco_txns]
    donut_labels = ['True Competitors', 'Payment Ecosystems']
    donut_colors = [GEN_COLORS['accent'], GEN_COLORS['info']]
    wedges, texts, autotexts = ax2.pie(
        donut_vals, labels=donut_labels, colors=donut_colors,
        autopct=lambda p: f'{p:.1f}%', startangle=90, pctdistance=0.75,
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
        textprops=dict(fontsize=13, fontweight='bold', color=GEN_COLORS['dark_text']),
    )
    for at in autotexts:
        at.set_fontsize(14)
        at.set_fontweight('bold')
    ax2.set_title("True vs Ecosystem", fontsize=20, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=15)
    total_str = f"{true_txns + eco_txns:,}"
    ax2.text(0, 0, total_str, ha='center', va='center',
             fontsize=22, fontweight='bold', color=GEN_COLORS['dark_text'])
    ax2.text(0, -0.12, "total txns", ha='center', va='center',
             fontsize=11, color=GEN_COLORS['muted'])

    plt.tight_layout()
    plt.show()

    # --- Panel 3: Top 10 competitors table (by normalized name) ---
    top10 = (
        competitor_txns.groupby('competitor_match')
        .agg(
            txns=('amount', 'count'),
            accounts=('primary_account_num', 'nunique'),
            category=('competitor_category', 'first'),
        )
        .sort_values('txns', ascending=False)
        .head(10)
    )

    fig, ax = plt.subplots(figsize=(20, 5))
    fig.patch.set_facecolor('#FFFFFF')
    ax.axis('off')
    ax.set_xlim(0, 20)
    ax.set_ylim(-0.5, len(top10) + 1.5)
    ax.invert_yaxis()

    ax.text(0.2, 0, "Top 10 Competitors by Transaction Volume",
            fontsize=22, fontweight='bold', color=GEN_COLORS['dark_text'])

    # Header row
    headers = ['Rank', 'Competitor', 'Transactions', 'Accounts', 'Category']
    h_x = [0.2, 1.5, 9.5, 12.5, 15.0]
    for hx, h in zip(h_x, headers):
        ax.text(hx, 1, h, fontsize=12, fontweight='bold', color=GEN_COLORS['muted'])
    ax.plot([0.2, 19.5], [1.3, 1.3], color=GEN_COLORS['grid'], linewidth=1.5)

    for i, (merchant, row) in enumerate(top10.iterrows()):
        y = i + 1.8
        cat_label = row['category'].replace('_', ' ').title()
        cat_color = CATEGORY_PALETTE.get(cat_label, GEN_COLORS['muted'])
        name = merchant[:35] + '..' if len(str(merchant)) > 37 else merchant

        ax.text(h_x[0] + 0.3, y, f"{i+1}", fontsize=14, fontweight='bold',
                color=GEN_COLORS['dark_text'], ha='center')
        ax.text(h_x[1], y, name, fontsize=13, fontweight='bold', color=GEN_COLORS['dark_text'])
        ax.text(h_x[2], y, f"{row['txns']:,}", fontsize=13, fontweight='bold',
                color=GEN_COLORS['accent'])
        ax.text(h_x[3], y, f"{row['accounts']:,}", fontsize=13, color=GEN_COLORS['dark_text'])

        # Category badge
        badge = FancyBboxPatch((h_x[4] - 0.1, y - 0.25), len(cat_label) * 0.18 + 0.4, 0.5,
                               boxstyle="round,pad=0.08", facecolor=cat_color,
                               alpha=0.12, edgecolor=cat_color, linewidth=1)
        ax.add_patch(badge)
        ax.text(h_x[4] + 0.1, y, cat_label, fontsize=11, fontweight='bold', color=cat_color)

        if i < len(top10) - 1:
            ax.plot([0.2, 19.5], [y + 0.4, y + 0.4], color=GEN_COLORS['grid'],
                    linewidth=0.5, alpha=0.5)

    plt.tight_layout()
    plt.show()

    # --- Unmatched financial discovery ---
    unmatched = discover_unmatched_financial(competitor_txns)
    if len(unmatched) > 0:
        print(f"\n    DISCOVERY: {len(unmatched)} potential competitors NOT in config")
        display(unmatched.head(20))
    else:
        print(f"\n    All financial merchants matched to known competitors.")

    print(f"    Competitor detection complete: {n_categories} categories, {unique_competitors} competitors")
