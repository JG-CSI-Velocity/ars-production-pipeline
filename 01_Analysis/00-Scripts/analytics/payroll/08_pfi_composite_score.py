# ===========================================================================
# PFI COMPOSITE SCORE: Primary Financial Institution Scoring Model
# ===========================================================================
# Builds a 0-20 scale PFI score per account based on payroll, balance,
# card activity, product count, tenure, and bill pay signals.

# ---------------------------------------------------------------------------
# 1. Payroll component (0 or 5)
# ---------------------------------------------------------------------------
payroll_df['pfi_payroll'] = payroll_df['has_payroll'].astype(int) * 5

# ---------------------------------------------------------------------------
# 2. Balance component (0-4)
# ---------------------------------------------------------------------------
bal_col = None
for col_name in ['avg_balance', 'curr_balance']:
    if col_name in payroll_df.columns:
        bal_col = col_name
        break

if bal_col:
    conditions = [
        payroll_df[bal_col] <= 0,
        (payroll_df[bal_col] > 0) & (payroll_df[bal_col] <= 1000),
        (payroll_df[bal_col] > 1000) & (payroll_df[bal_col] <= 5000),
        (payroll_df[bal_col] > 5000) & (payroll_df[bal_col] <= 25000),
        payroll_df[bal_col] > 25000,
    ]
    choices = [0, 1, 2, 3, 4]
    payroll_df['pfi_balance'] = np.select(conditions, choices, default=0)
else:
    payroll_df['pfi_balance'] = 0

# ---------------------------------------------------------------------------
# 3. Card activity component (0-4, percentile-based on monthly txn count)
# ---------------------------------------------------------------------------
n_months = max(DATASET_MONTHS, 1) if 'DATASET_MONTHS' in dir() or 'DATASET_MONTHS' in globals() else 1
payroll_df['monthly_txn_rate'] = payroll_df['total_txn_count'] / n_months

if payroll_df['monthly_txn_rate'].sum() > 0:
    pctiles = payroll_df['monthly_txn_rate'].rank(pct=True)
    payroll_df['pfi_activity'] = pd.cut(
        pctiles,
        bins=[-0.01, 0.20, 0.40, 0.60, 0.80, 1.01],
        labels=[0, 1, 2, 3, 4],
    ).astype(int)
else:
    payroll_df['pfi_activity'] = 0

# ---------------------------------------------------------------------------
# 4. Product count component (1 prod=1, 2=2, 3+=3)
# ---------------------------------------------------------------------------
if 'prod_code' in payroll_df.columns:
    # Count distinct products per account from rewards_df if available
    if 'rewards_df' in dir() or 'rewards_df' in globals():
        acct_key = None
        for col in ['Acct Number', 'primary_account_num']:
            if col in rewards_df.columns:
                acct_key = col
                break
        prod_key = None
        for col in ['Prod Code', 'prod_code']:
            if col in rewards_df.columns:
                prod_key = col
                break

        if acct_key and prod_key:
            prod_counts = rewards_df.groupby(acct_key)[prod_key].nunique().reset_index()
            prod_counts.columns = ['primary_account_num', 'n_products']
            payroll_df = payroll_df.drop(columns=['n_products'], errors='ignore')
            payroll_df = payroll_df.merge(prod_counts, on='primary_account_num', how='left')
            payroll_df['n_products'] = payroll_df['n_products'].fillna(1).astype(int)
        else:
            payroll_df['n_products'] = 1
    else:
        payroll_df['n_products'] = 1

    payroll_df['pfi_products'] = payroll_df['n_products'].clip(upper=3)
else:
    payroll_df['n_products'] = 1
    payroll_df['pfi_products'] = 1

# ---------------------------------------------------------------------------
# 5. Tenure component (<1yr=1, 1-3yr=2, 3+=3)
# ---------------------------------------------------------------------------
if 'account_age_days' in payroll_df.columns:
    conditions_t = [
        payroll_df['account_age_days'] < 365,
        (payroll_df['account_age_days'] >= 365) & (payroll_df['account_age_days'] < 1095),
        payroll_df['account_age_days'] >= 1095,
    ]
    choices_t = [1, 2, 3]
    payroll_df['pfi_tenure'] = np.select(conditions_t, choices_t, default=1)
else:
    payroll_df['pfi_tenure'] = 1

# ---------------------------------------------------------------------------
# 6. Bill pay signals (0-1): recurring same-merchant debits
# ---------------------------------------------------------------------------
# Scan for accounts with 3+ debits to the same merchant (utilities, insurance pattern)
debit_txns = combined_df[combined_df['amount'] < 0].copy()
if 'merchant_consolidated' in debit_txns.columns and len(debit_txns) > 0:
    recurring_debits = debit_txns.groupby(
        ['primary_account_num', 'merchant_consolidated']
    ).size().reset_index(name='debit_count')

    # Accounts with at least 2 merchants receiving 3+ debits = bill pay signal
    recurring_debits = recurring_debits[recurring_debits['debit_count'] >= 3]
    bill_pay_accts = recurring_debits.groupby('primary_account_num').size().reset_index(name='recurring_merchants')
    bill_pay_accts['pfi_billpay'] = (bill_pay_accts['recurring_merchants'] >= 2).astype(int)

    payroll_df = payroll_df.drop(columns=['pfi_billpay'], errors='ignore')
    payroll_df = payroll_df.merge(
        bill_pay_accts[['primary_account_num', 'pfi_billpay']],
        on='primary_account_num', how='left'
    )
    payroll_df['pfi_billpay'] = payroll_df['pfi_billpay'].fillna(0).astype(int)
else:
    payroll_df['pfi_billpay'] = 0

# ---------------------------------------------------------------------------
# 7. Composite PFI score (0-20)
# ---------------------------------------------------------------------------
SCORE_COMPONENTS = ['pfi_payroll', 'pfi_balance', 'pfi_activity',
                    'pfi_products', 'pfi_tenure', 'pfi_billpay']

payroll_df['pfi_score'] = payroll_df[SCORE_COMPONENTS].sum(axis=1)

# PFI Tier assignment
tier_conditions = [
    payroll_df['pfi_score'] >= 14,
    (payroll_df['pfi_score'] >= 9) & (payroll_df['pfi_score'] < 14),
    (payroll_df['pfi_score'] >= 5) & (payroll_df['pfi_score'] < 9),
    payroll_df['pfi_score'] < 5,
]
tier_labels = ['Primary', 'Secondary', 'Tertiary', 'Incidental']
payroll_df['pfi_tier'] = np.select(tier_conditions, tier_labels, default='Incidental')

PFI_TIER_ORDER = ['Primary', 'Secondary', 'Tertiary', 'Incidental']
PFI_TIER_COLORS = {
    'Primary':    GEN_COLORS['accent'],
    'Secondary':  GEN_COLORS['warning'],
    'Tertiary':   GEN_COLORS['info'],
    'Incidental': GEN_COLORS['muted'],
}

# ---------------------------------------------------------------------------
# 8. Bar chart: PFI tier distribution
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(18, 8))

tier_counts = payroll_df['pfi_tier'].value_counts()
tier_counts = tier_counts.reindex(PFI_TIER_ORDER).fillna(0).astype(int)
tier_pcts = tier_counts / tier_counts.sum() * 100

ax1 = axes[0]
bar_colors = [PFI_TIER_COLORS[t] for t in PFI_TIER_ORDER]
bars = ax1.bar(PFI_TIER_ORDER, tier_pcts, color=bar_colors,
               edgecolor='white', linewidth=2, zorder=3)

for bar, pct, cnt in zip(bars, tier_pcts, tier_counts):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
             f"{pct:.1f}%", ha='center', va='bottom',
             fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'])
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 0.5,
             f"n={cnt:,}", ha='center', va='center',
             fontsize=12, fontweight='bold', color='white')

ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
gen_clean_axes(ax1)
ax1.set_title("PFI Tier Distribution", fontsize=20, fontweight='bold',
              color=GEN_COLORS['dark_text'], loc='left')

# ---------------------------------------------------------------------------
# Score histogram
# ---------------------------------------------------------------------------
ax2 = axes[1]
score_range = range(0, 21)
score_counts = payroll_df['pfi_score'].value_counts().reindex(score_range, fill_value=0)

def score_to_color(s):
    if s >= 14:
        return PFI_TIER_COLORS['Primary']
    elif s >= 9:
        return PFI_TIER_COLORS['Secondary']
    elif s >= 5:
        return PFI_TIER_COLORS['Tertiary']
    return PFI_TIER_COLORS['Incidental']

hist_colors = [score_to_color(s) for s in score_range]

ax2.bar(score_range, score_counts.values, color=hist_colors,
        edgecolor='white', linewidth=0.5, zorder=3)

# Tier boundary lines
for boundary, label in [(5, 'Tertiary'), (9, 'Secondary'), (14, 'Primary')]:
    ax2.axvline(x=boundary - 0.5, color=GEN_COLORS['dark_text'],
                linestyle='--', linewidth=1.5, alpha=0.6, zorder=2)
    ax2.text(boundary - 0.3, ax2.get_ylim()[1] * 0.95, label,
             fontsize=10, fontweight='bold', color=GEN_COLORS['dark_text'],
             rotation=90, va='top')

ax2.set_xlabel("PFI Score", fontsize=14)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))
gen_clean_axes(ax2)
ax2.set_title("Score Distribution (0-20)", fontsize=20, fontweight='bold',
              color=GEN_COLORS['dark_text'], loc='left')

fig.suptitle("PFI Composite Score: Member Relationship Depth",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], x=0.01, ha='left', y=GEN_TITLE_Y)
fig.text(0.01, 1.01,
         f"Payroll (5) + Balance (4) + Activity (4) + Products (3) + Tenure (3) + Bill Pay (1)  --  {DATASET_LABEL}",
         fontsize=12, style='italic', color=GEN_COLORS['muted'],
         ha='left', transform=fig.transFigure)

plt.tight_layout()
plt.show()

# ---------------------------------------------------------------------------
# 9. Styled tier summary table
# ---------------------------------------------------------------------------
tier_summary_rows = []
for tier in PFI_TIER_ORDER:
    subset = payroll_df[payroll_df['pfi_tier'] == tier]
    row = {
        'PFI Tier': tier,
        'Accounts': f"{len(subset):,}",
        '% of Total': f"{len(subset) / len(payroll_df) * 100:.1f}%",
        'Avg PFI Score': f"{subset['pfi_score'].mean():.1f}",
        'Has Payroll': f"{subset['has_payroll'].mean() * 100:.0f}%",
    }
    if bal_col:
        row['Avg Balance'] = f"${subset[bal_col].mean():,.0f}"
    row['Avg Txns'] = f"{subset['total_txn_count'].mean():,.0f}"
    tier_summary_rows.append(row)

tier_table = pd.DataFrame(tier_summary_rows)

styled_tier = (
    tier_table.style
    .hide(axis='index')
    .set_properties(**{
        'font-size': '13px', 'text-align': 'center',
        'border': '1px solid #E9ECEF', 'padding': '8px 12px',
    })
    .set_properties(subset=['PFI Tier'], **{
        'font-weight': 'bold', 'text-align': 'left',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'), ('font-size', '14px'),
            ('font-weight', 'bold'), ('text-align', 'center'),
            ('padding', '8px 12px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'), ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
            ('padding-bottom', '12px'),
        ]},
    ])
    .set_caption("PFI Tier Summary")
)

display(styled_tier)

# Component averages
print("\nPFI Score Component Averages:")
for comp in SCORE_COMPONENTS:
    max_val = 5 if comp == 'pfi_payroll' else (4 if comp in ['pfi_balance', 'pfi_activity'] else (3 if comp in ['pfi_products', 'pfi_tenure'] else 1))
    avg = payroll_df[comp].mean()
    print(f"  {comp.replace('pfi_', '').title():>12}: {avg:.2f} / {max_val}")
print(f"  {'TOTAL':>12}: {payroll_df['pfi_score'].mean():.2f} / 20")
