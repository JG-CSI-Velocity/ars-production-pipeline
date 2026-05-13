# ===========================================================================
# PFI SCORING: Primary Financial Institution Score (Conference Edition)
# ===========================================================================
# Composite score: balance + activity + tenure + product breadth.
# Tiers: Primary (10+), Secondary (6-9), Tertiary (3-5), Incidental (0-2).

pfi_df = balance_df.copy()

# ---------------------------------------------------------------------------
# Component 1: Balance score (0-5)
# ---------------------------------------------------------------------------
BALANCE_SCORE_MAP = {
    '$0': 0,
    '$1-1K': 1,
    '$1K-5K': 2,
    '$5K-25K': 3,
    '$25K-100K': 4,
    '$100K+': 5,
}

if 'balance_band' in pfi_df.columns:
    pfi_df['bal_score'] = pfi_df['balance_band'].map(BALANCE_SCORE_MAP).fillna(0).astype(int)
else:
    pfi_df['bal_score'] = 0

# ---------------------------------------------------------------------------
# Component 2: Activity score based on monthly txn count percentile (0-5)
# ---------------------------------------------------------------------------
if 'txn_count' in pfi_df.columns:
    monthly_txns = pfi_df['txn_count'] / max(DATASET_MONTHS, 1)
    pfi_df['activity_score'] = pd.cut(
        monthly_txns.rank(pct=True, method='min') * 100,
        bins=[-1, 10, 30, 50, 70, 90, 101],
        labels=[0, 1, 2, 3, 4, 5]
    ).astype(float).fillna(0).astype(int)
else:
    pfi_df['activity_score'] = 0

# ---------------------------------------------------------------------------
# Component 3: Tenure score based on account age (0-3)
# ---------------------------------------------------------------------------
if 'Account Age' in pfi_df.columns:
    acct_age_numeric = pd.to_numeric(pfi_df['Account Age'], errors='coerce').fillna(0)
    pfi_df['tenure_score'] = pd.cut(
        acct_age_numeric,
        bins=[-1, 365, 1095, 2555, 999999],
        labels=[0, 1, 2, 3]
    ).astype(float).fillna(0).astype(int)
else:
    pfi_df['tenure_score'] = 0

# ---------------------------------------------------------------------------
# Component 4: Product breadth score (0-3)
# ---------------------------------------------------------------------------
if 'Prod Code' in pfi_df.columns and 'Acct Number' in pfi_df.columns:
    # Count unique product codes per account holder
    # Use rewards_df to get all products per account if multiple rows exist
    prod_counts = rewards_df.groupby('Acct Number')['Prod Code'].nunique().reset_index()
    prod_counts.columns = ['Acct Number', 'prod_count']

    pfi_df = pfi_df.merge(prod_counts, on='Acct Number', how='left')
    pfi_df['prod_count'] = pfi_df['prod_count'].fillna(1).astype(int)

    pfi_df['product_score'] = pd.cut(
        pfi_df['prod_count'],
        bins=[0, 1, 2, 3, 999],
        labels=[0, 1, 2, 3],
        right=True
    ).astype(float).fillna(0).astype(int)
else:
    pfi_df['product_score'] = 0

# ---------------------------------------------------------------------------
# Total PFI Score + Tiers
# ---------------------------------------------------------------------------
pfi_df['pfi_score'] = (pfi_df['bal_score'] + pfi_df['activity_score'] +
                       pfi_df['tenure_score'] + pfi_df['product_score'])

PFI_TIER_MAP = {
    'Primary': (10, 999),
    'Secondary': (6, 9),
    'Tertiary': (3, 5),
    'Incidental': (0, 2),
}

PFI_TIER_ORDER = ['Primary', 'Secondary', 'Tertiary', 'Incidental']

PFI_TIER_PALETTE = {
    'Primary':    GEN_COLORS['success'],
    'Secondary':  GEN_COLORS['info'],
    'Tertiary':   GEN_COLORS['warning'],
    'Incidental': GEN_COLORS['muted'],
}

def assign_pfi_tier(score):
    for tier, (low, high) in PFI_TIER_MAP.items():
        if low <= score <= high:
            return tier
    return 'Incidental'

pfi_df['pfi_tier'] = pfi_df['pfi_score'].apply(assign_pfi_tier)
pfi_df['pfi_tier'] = pd.Categorical(
    pfi_df['pfi_tier'], categories=PFI_TIER_ORDER, ordered=True
)

# ---------------------------------------------------------------------------
# Bar chart: PFI tier distribution
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(16, 7),
                          gridspec_kw={'width_ratios': [1, 1]})

tier_counts = pfi_df['pfi_tier'].value_counts().reindex(PFI_TIER_ORDER).fillna(0)
tier_pcts = tier_counts / tier_counts.sum() * 100
tier_colors = [PFI_TIER_PALETTE.get(t, GEN_COLORS['muted']) for t in tier_counts.index]

bars = axes[0].bar(tier_counts.index, tier_counts.values,
                   color=tier_colors, edgecolor='white', linewidth=2)

for bar, count, pct in zip(bars, tier_counts.values, tier_pcts.values):
    axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + tier_counts.max() * 0.02,
                 f"{int(count):,}\n({pct:.1f}%)",
                 ha='center', va='bottom', fontsize=12, fontweight='bold',
                 color=GEN_COLORS['dark_text'])

axes[0].set_title("PFI Tier Distribution", fontsize=20, fontweight='bold',
                   loc='left', color=GEN_COLORS['dark_text'])
axes[0].set_ylabel("Number of Accounts", fontsize=13)
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))
axes[0].set_ylim(0, tier_counts.max() * 1.25)
gen_clean_axes(axes[0])

# ---------------------------------------------------------------------------
# Right panel: avg balance and avg spend per PFI tier
# ---------------------------------------------------------------------------
tier_stats = pfi_df.groupby('pfi_tier', observed=False).agg(
    avg_bal=('Curr Bal', 'mean'),
    avg_spend=('total_spend', 'mean') if 'total_spend' in pfi_df.columns else ('Curr Bal', 'mean'),
    total_deposits=('Curr Bal', 'sum'),
    count=('Acct Number', 'count')
).reindex(PFI_TIER_ORDER)

x_pos = np.arange(len(PFI_TIER_ORDER))
width = 0.35

bars_bal = axes[1].bar(x_pos - width / 2, tier_stats['avg_bal'],
                       width, color=GEN_COLORS['primary'], label='Avg Balance',
                       edgecolor='white', linewidth=1.5)

if 'total_spend' in pfi_df.columns:
    bars_spend = axes[1].bar(x_pos + width / 2, tier_stats['avg_spend'],
                             width, color=GEN_COLORS['accent'], label='Avg Spend',
                             edgecolor='white', linewidth=1.5)

axes[1].set_xticks(x_pos)
axes[1].set_xticklabels(PFI_TIER_ORDER)
axes[1].set_title("Avg Balance & Spend by PFI Tier", fontsize=20, fontweight='bold',
                   loc='left', color=GEN_COLORS['dark_text'])
axes[1].set_ylabel("Amount", fontsize=13)
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
axes[1].legend(fontsize=12)
gen_clean_axes(axes[1])

fig.suptitle("Primary Financial Institution (PFI) Score Analysis",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.01, 1.00,
         f"Score = Balance(0-5) + Activity(0-5) + Tenure(0-3) + Products(0-3) | {DATASET_LABEL}",
         fontsize=12, style='italic', color=GEN_COLORS['muted'])

plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
print(f"\n    PFI Tier Summary:")
for tier in PFI_TIER_ORDER:
    row = tier_stats.loc[tier]
    print(f"      {tier:>12s}: {int(row['count']):>6,} accounts | "
          f"Avg Bal: {gen_fmt_dollar(row['avg_bal'], None):>8s} | "
          f"Total Deposits: {gen_fmt_dollar(row['total_deposits'], None):>8s}")

primary_pct = tier_pcts.get('Primary', 0)
primary_deposit_pct = (tier_stats.loc['Primary', 'total_deposits'] /
                       tier_stats['total_deposits'].sum() * 100
                       if tier_stats['total_deposits'].sum() > 0 else 0)
print(f"\n    INSIGHT: {primary_pct:.1f}% of members are Primary FI -- "
      f"holding {primary_deposit_pct:.1f}% of total deposits.")
print(f"    INSIGHT: Incidental members ({tier_pcts.get('Incidental', 0):.1f}%) "
      f"represent upgrade opportunity via targeted engagement.")
