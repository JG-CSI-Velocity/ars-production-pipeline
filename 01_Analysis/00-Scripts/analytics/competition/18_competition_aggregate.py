# ===========================================================================
# COMPETITIVE LANDSCAPE -- Category Overview + Digital Banks Deep Dive
# ===========================================================================
# Two square charts for side-by-side PowerPoint layout:
#   Left:  All categories by member penetration (color-coded by category)
#   Right: Digital banks deep dive -- which fintechs are capturing your members?

competitor_txns = combined_df[combined_df['competitor_category'].notna()].copy()
total_accounts = combined_df['primary_account_num'].nunique()

# --- Category-level aggregation ---
cat_agg = (
    competitor_txns.groupby('competitor_category')
    .agg(
        transactions=('amount', 'count'),
        accounts=('primary_account_num', 'nunique'),
    )
    .reset_index()
)
cat_agg['category_label'] = cat_agg['competitor_category'].apply(clean_category)
cat_agg['penetration'] = cat_agg['accounts'] / total_accounts * 100
cat_agg = cat_agg.sort_values('accounts', ascending=True)

# --- Data-driven color logic ---
def cat_bar_color(cat_raw):
    label = clean_category(cat_raw)
    return CATEGORY_PALETTE.get(label, GEN_COLORS['info'])

bar_colors = [cat_bar_color(c) for c in cat_agg['competitor_category']]

# Configurable annotations for specific categories
_CATEGORY_ANNOTATIONS = {
    'digital_banks': ('THREAT', GEN_COLORS['accent']),
    'bnpl': ('OPPORTUNITY', GEN_COLORS['success']),
}

# =====================================================================
# CHART 1: Category Landscape (square)
# =====================================================================
fig1, ax1 = plt.subplots(figsize=(8, 7))

y_pos = range(len(cat_agg))
ax1.barh(y_pos, cat_agg['accounts'],
         color=bar_colors, edgecolor='white', linewidth=1.5, height=0.6, zorder=3)

for i, (_, row) in enumerate(cat_agg.iterrows()):
    ax1.text(row['accounts'] * 1.02, i,
             f"{row['accounts']:,} ({row['penetration']:.1f}%)",
             fontsize=11, fontweight='bold', color=GEN_COLORS['dark_text'], va='center')

    annotation = _CATEGORY_ANNOTATIONS.get(row['competitor_category'])
    if annotation and row['accounts'] > 0:
        label_text, stroke_color = annotation
        ax1.text(row['accounts'] * 0.5, i, label_text,
                 ha='center', va='center', fontsize=10, fontweight='bold', color='white',
                 path_effects=[pe.withStroke(linewidth=2.5, foreground=stroke_color)])

ax1.set_yticks(y_pos)
ax1.set_yticklabels(cat_agg['category_label'], fontsize=12, fontweight='bold')
ax1.set_xlabel('Unique Members', fontsize=13, fontweight='bold', labelpad=10)
ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
ax1.set_xlim(0, cat_agg['accounts'].max() * 1.50)

gen_clean_axes(ax1)
ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
ax1.set_axisbelow(True)

ax1.set_title('Competitive Landscape',
              fontsize=20, fontweight='bold', color=GEN_COLORS['dark_text'], pad=16, loc='left')
ax1.text(0.0, 0.97,
         f"Member penetration across {len(cat_agg)} categories",
         transform=ax1.transAxes, fontsize=11, color=GEN_COLORS['muted'], style='italic')

fig1.tight_layout()
plt.show()

# =====================================================================
# CHART 2: Digital Banks Deep Dive (square, guarded)
# =====================================================================
if 'digital_banks' in ALL_CATEGORIES:
    digital_txns = competitor_txns[competitor_txns['competitor_category'] == 'digital_banks'].copy()

    if len(digital_txns) > 0:
        merch_col = 'merchant_consolidated'
        digital_txns['norm_merchant'] = digital_txns[merch_col].apply(normalize_competitor_name)

        db_agg = (
            digital_txns.groupby('norm_merchant')
            .agg(
                transactions=('amount', 'count'),
                accounts=('primary_account_num', 'nunique'),
            )
            .reset_index()
            .sort_values('accounts', ascending=True)
            .tail(10)
        )
        db_agg['penetration'] = db_agg['accounts'] / total_accounts * 100

        fig2, ax2 = plt.subplots(figsize=(8, 7))

        y2 = range(len(db_agg))
        max_accts = db_agg['accounts'].max()
        db_colors = [
            GEN_COLORS['accent'] if a == max_accts
            else '#C0392B' if a >= max_accts * 0.5
            else '#E74C3C'
            for a in db_agg['accounts']
        ]

        ax2.barh(y2, db_agg['accounts'],
                 color=db_colors, edgecolor='white', linewidth=1.5, height=0.6, zorder=3)

        for i, (_, row) in enumerate(db_agg.iterrows()):
            ax2.text(row['accounts'] * 1.02, i,
                     f"{row['accounts']:,} ({row['penetration']:.1f}%)",
                     fontsize=11, fontweight='bold', color=GEN_COLORS['dark_text'], va='center')

        ax2.set_yticks(y2)
        ax2.set_yticklabels(db_agg['norm_merchant'], fontsize=12, fontweight='bold')
        ax2.set_xlabel('Unique Members', fontsize=13, fontweight='bold', labelpad=10)
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
        ax2.set_xlim(0, db_agg['accounts'].max() * 1.40)

        gen_clean_axes(ax2)
        ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
        ax2.set_axisbelow(True)

        total_db_accts = digital_txns['primary_account_num'].nunique()
        ax2.set_title('Digital Banks Deep Dive',
                      fontsize=20, fontweight='bold', color=GEN_COLORS['accent'], pad=16, loc='left')
        ax2.text(0.0, 0.97,
                 f"{total_db_accts:,} members ({total_db_accts / total_accounts * 100:.1f}% penetration)",
                 transform=ax2.transAxes, fontsize=11, color=GEN_COLORS['muted'], style='italic')

        fig2.tight_layout()
        plt.show()

# --- Insight callouts (guarded) ---
if 'digital_banks' in ALL_CATEGORIES:
    db_row = cat_agg[cat_agg['competitor_category'] == 'digital_banks']
    if len(db_row) > 0:
        db = db_row.iloc[0]
        print(f"\n    THREAT: Digital Banks reach {db['accounts']:,} members ({db['penetration']:.1f}% penetration).")
    if 'digital_txns' in dir() and len(digital_txns) > 0:
        top_db = db_agg.iloc[-1]
        print(f"    TOP DIGITAL THREAT: {top_db['norm_merchant']} with {top_db['accounts']:,} members.")

if 'bnpl' in ALL_CATEGORIES:
    bnpl_row = cat_agg[cat_agg['competitor_category'] == 'bnpl']
    if len(bnpl_row) > 0:
        bp = bnpl_row.iloc[0]
        print(f"    OPPORTUNITY: BNPL has {bp['accounts']:,} members -- offer your own BNPL/installment product.")
