# ===========================================================================
# BALANCE BY DEMOGRAPHICS: Age, Account Age, Engagement (Conference Edition)
# ===========================================================================
# 3-panel layout: median balance by (1) age band, (2) account age, (3) engagement tier.

fig, axes = plt.subplots(1, 3, figsize=(20, 7))

# ---------------------------------------------------------------------------
# Panel 1: Balance by Age Band
# ---------------------------------------------------------------------------
has_age = 'Account Holder Age' in balance_df.columns

if has_age:
    age_df = balance_df.copy()
    age_df['Account Holder Age'] = pd.to_numeric(
        age_df['Account Holder Age'], errors='coerce'
    )

    age_bins = [0, 25, 35, 45, 55, 65, 150]
    age_labels = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
    age_df['age_band'] = pd.cut(
        age_df['Account Holder Age'], bins=age_bins, labels=age_labels, right=True
    )
    age_df = age_df.dropna(subset=['age_band'])

    age_med = age_df.groupby('age_band', observed=False)['Curr Bal'].median().reindex(AGE_ORDER)
    age_colors = [AGE_PALETTE.get(a, GEN_COLORS['muted']) for a in age_med.index]

    bars_age = axes[0].bar(age_med.index, age_med.values,
                           color=age_colors, edgecolor='white', linewidth=1.5)

    for bar, val in zip(bars_age, age_med.values):
        if pd.notna(val) and val > 0:
            axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + age_med.max() * 0.02,
                         gen_fmt_dollar(val, None),
                         ha='center', va='bottom', fontsize=11, fontweight='bold',
                         color=GEN_COLORS['dark_text'])

    axes[0].set_title("By Age Band", fontsize=18, fontweight='bold', loc='left',
                       color=GEN_COLORS['dark_text'])
    axes[0].set_ylabel("Median Balance", fontsize=13)
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
else:
    axes[0].text(0.5, 0.5, "Age data not available",
                 transform=axes[0].transAxes, ha='center', va='center',
                 fontsize=14, color=GEN_COLORS['muted'], style='italic')
    axes[0].set_title("By Age Band", fontsize=18, fontweight='bold', loc='left',
                       color=GEN_COLORS['dark_text'])

gen_clean_axes(axes[0])
axes[0].tick_params(axis='x', rotation=30)

# ---------------------------------------------------------------------------
# Panel 2: Balance by Account Age
# ---------------------------------------------------------------------------
has_acct_age = 'Account Age' in balance_df.columns

if has_acct_age:
    acct_age_df = balance_df.copy()
    acct_age_df['Account Age'] = pd.to_numeric(
        acct_age_df['Account Age'], errors='coerce'
    )

    acct_age_bins = [0, 90, 180, 365, 730, 1095, 1825, 3650, 7300, 999999]
    acct_age_labels = ['1-90d', '91-180d', '181-365d', '1-2yr', '2-3yr',
                       '3-5yr', '5-10yr', '10-20yr', '20yr+']
    acct_age_df['acct_age_band'] = pd.cut(
        acct_age_df['Account Age'], bins=acct_age_bins, labels=acct_age_labels, right=True
    )
    acct_age_df = acct_age_df.dropna(subset=['acct_age_band'])

    acct_med = acct_age_df.groupby('acct_age_band', observed=False)['Curr Bal'].median()
    acct_med = acct_med.reindex(ACCT_AGE_ORDER)
    acct_colors = [ACCT_AGE_PALETTE.get(a, GEN_COLORS['muted']) for a in acct_med.index]

    bars_acct = axes[1].bar(acct_med.index, acct_med.values,
                            color=acct_colors, edgecolor='white', linewidth=1.5)

    for bar, val in zip(bars_acct, acct_med.values):
        if pd.notna(val) and val > 0:
            axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + acct_med.max() * 0.02,
                         gen_fmt_dollar(val, None),
                         ha='center', va='bottom', fontsize=9, fontweight='bold',
                         color=GEN_COLORS['dark_text'])

    axes[1].set_title("By Account Age", fontsize=18, fontweight='bold', loc='left',
                       color=GEN_COLORS['dark_text'])
    axes[1].set_ylabel("Median Balance", fontsize=13)
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
else:
    axes[1].text(0.5, 0.5, "Account Age data not available",
                 transform=axes[1].transAxes, ha='center', va='center',
                 fontsize=14, color=GEN_COLORS['muted'], style='italic')
    axes[1].set_title("By Account Age", fontsize=18, fontweight='bold', loc='left',
                       color=GEN_COLORS['dark_text'])

gen_clean_axes(axes[1])
axes[1].tick_params(axis='x', rotation=45)

# ---------------------------------------------------------------------------
# Panel 3: Balance by Engagement Tier
# ---------------------------------------------------------------------------
has_engagement = 'acct_txn_counts' in dir() and 'engagement_tier' in locals()

# Try to build engagement tiers from txn_count if not pre-computed
if 'txn_count' in balance_df.columns:
    engage_df = balance_df.copy()
    monthly_txns = engage_df['txn_count'] / max(DATASET_MONTHS, 1)

    engage_df['engagement_tier'] = pd.cut(
        monthly_txns,
        bins=[-1, 0, 5, 15, 30, float('inf')],
        labels=['Dormant', 'Light', 'Moderate', 'Heavy', 'Power']
    )
    engage_df = engage_df.dropna(subset=['engagement_tier'])

    eng_med = engage_df.groupby('engagement_tier', observed=False)['Curr Bal'].median()
    eng_med = eng_med.reindex(ENGAGE_ORDER)
    eng_colors = [ENGAGE_PALETTE.get(e, GEN_COLORS['muted']) for e in eng_med.index]

    bars_eng = axes[2].bar(eng_med.index, eng_med.values,
                           color=eng_colors, edgecolor='white', linewidth=1.5)

    for bar, val in zip(bars_eng, eng_med.values):
        if pd.notna(val) and val > 0:
            axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + eng_med.max() * 0.02,
                         gen_fmt_dollar(val, None),
                         ha='center', va='bottom', fontsize=11, fontweight='bold',
                         color=GEN_COLORS['dark_text'])

    axes[2].set_title("By Engagement Tier", fontsize=18, fontweight='bold', loc='left',
                       color=GEN_COLORS['dark_text'])
    axes[2].set_ylabel("Median Balance", fontsize=13)
    axes[2].yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
else:
    axes[2].text(0.5, 0.5, "Engagement data not available",
                 transform=axes[2].transAxes, ha='center', va='center',
                 fontsize=14, color=GEN_COLORS['muted'], style='italic')
    axes[2].set_title("By Engagement Tier", fontsize=18, fontweight='bold', loc='left',
                       color=GEN_COLORS['dark_text'])

gen_clean_axes(axes[2])
axes[2].tick_params(axis='x', rotation=30)

# ---------------------------------------------------------------------------
# Suptitle
# ---------------------------------------------------------------------------
fig.suptitle("Balance Profile by Demographics",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.01, 1.00,
         f"Median balance across key segmentation dimensions | {DATASET_LABEL}",
         fontsize=12, style='italic', color=GEN_COLORS['muted'])

plt.tight_layout()
plt.show()

if has_age:
    highest_age = age_med.idxmax()
    print(f"\n    INSIGHT: {highest_age} age band has highest median balance "
          f"({gen_fmt_dollar(age_med.max(), None)}).")
if has_acct_age:
    highest_acct = acct_med.idxmax()
    print(f"    INSIGHT: {highest_acct} account age band has highest median balance "
          f"({gen_fmt_dollar(acct_med.max(), None)}).")
