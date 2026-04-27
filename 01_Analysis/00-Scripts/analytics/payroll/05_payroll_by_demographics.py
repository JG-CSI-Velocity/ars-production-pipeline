# ===========================================================================
# PAYROLL BY DEMOGRAPHICS: Penetration by Age, Account Age, Branch
# ===========================================================================
# 3-panel chart showing where payroll detection is strong vs weak.

fig, axes = plt.subplots(1, 3, figsize=(22, 8))

# ---------------------------------------------------------------------------
# Panel 1: Payroll penetration by age band
# ---------------------------------------------------------------------------
ax1 = axes[0]

if 'age_band' in payroll_df.columns and payroll_df['age_band'].notna().sum() > 0:
    age_penet = payroll_df.groupby('age_band', observed=True).agg(
        total=('has_payroll', 'count'),
        payroll=('has_payroll', 'sum'),
    ).reset_index()
    age_penet['pct'] = age_penet['payroll'] / age_penet['total'] * 100

    # Reorder to AGE_ORDER
    age_penet['age_band'] = pd.Categorical(
        age_penet['age_band'], categories=AGE_ORDER, ordered=True
    )
    age_penet = age_penet.sort_values('age_band').dropna(subset=['age_band'])

    bar_colors = [AGE_PALETTE.get(str(ab), GEN_COLORS['info']) for ab in age_penet['age_band']]

    bars = ax1.bar(range(len(age_penet)), age_penet['pct'],
                   color=bar_colors, edgecolor='white', linewidth=1.5, zorder=3)

    for bar, pct, total in zip(bars, age_penet['pct'], age_penet['total']):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{pct:.1f}%", ha='center', va='bottom',
                 fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'])
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 0.5,
                 f"n={total:,}", ha='center', va='center',
                 fontsize=10, color='white', fontweight='bold')

    ax1.set_xticks(range(len(age_penet)))
    ax1.set_xticklabels(age_penet['age_band'], fontsize=12, fontweight='bold')
    ax1.set_title("By Age Band", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')
else:
    ax1.text(0.5, 0.5, 'Age data not available',
             ha='center', va='center', fontsize=16,
             color=GEN_COLORS['muted'], transform=ax1.transAxes)
    ax1.set_title("By Age Band", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')

ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
gen_clean_axes(ax1)

# ---------------------------------------------------------------------------
# Panel 2: Payroll penetration by account age
# ---------------------------------------------------------------------------
ax2 = axes[1]

if 'acct_age_band' in payroll_df.columns and payroll_df['acct_age_band'].notna().sum() > 0:
    acct_penet = payroll_df.groupby('acct_age_band', observed=True).agg(
        total=('has_payroll', 'count'),
        payroll=('has_payroll', 'sum'),
    ).reset_index()
    acct_penet['pct'] = acct_penet['payroll'] / acct_penet['total'] * 100

    acct_penet['acct_age_band'] = pd.Categorical(
        acct_penet['acct_age_band'], categories=ACCT_AGE_ORDER, ordered=True
    )
    acct_penet = acct_penet.sort_values('acct_age_band').dropna(subset=['acct_age_band'])

    bar_colors_2 = [ACCT_AGE_PALETTE.get(str(ab), GEN_COLORS['info'])
                    for ab in acct_penet['acct_age_band']]

    bars2 = ax2.bar(range(len(acct_penet)), acct_penet['pct'],
                    color=bar_colors_2, edgecolor='white', linewidth=1.5, zorder=3)

    for bar, pct in zip(bars2, acct_penet['pct']):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{pct:.1f}%", ha='center', va='bottom',
                 fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'])

    ax2.set_xticks(range(len(acct_penet)))
    ax2.set_xticklabels(acct_penet['acct_age_band'], fontsize=10,
                        fontweight='bold', rotation=45, ha='right')
    ax2.set_title("By Account Age", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')
else:
    ax2.text(0.5, 0.5, 'Account age data not available',
             ha='center', va='center', fontsize=16,
             color=GEN_COLORS['muted'], transform=ax2.transAxes)
    ax2.set_title("By Account Age", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')

ax2.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
gen_clean_axes(ax2)

# ---------------------------------------------------------------------------
# Panel 3: Payroll penetration by branch
# ---------------------------------------------------------------------------
ax3 = axes[2]

if 'branch' in payroll_df.columns and payroll_df['branch'].notna().sum() > 0:
    branch_penet = payroll_df.groupby('branch', observed=True).agg(
        total=('has_payroll', 'count'),
        payroll=('has_payroll', 'sum'),
    ).reset_index()
    branch_penet['pct'] = branch_penet['payroll'] / branch_penet['total'] * 100

    # Filter to branches with meaningful sample size
    branch_penet = branch_penet[branch_penet['total'] >= 10].copy()
    branch_penet = branch_penet.sort_values('pct', ascending=True).tail(15)

    # Color: below overall avg = warning, above = success
    overall_pct = payroll_df['has_payroll'].mean() * 100
    bar_colors_3 = [GEN_COLORS['success'] if p >= overall_pct else GEN_COLORS['warning']
                    for p in branch_penet['pct']]

    bars3 = ax3.barh(range(len(branch_penet)), branch_penet['pct'],
                     color=bar_colors_3, edgecolor='white', linewidth=1.5, zorder=3)

    # Reference line at overall average
    ax3.axvline(x=overall_pct, color=GEN_COLORS['accent'], linestyle='--',
                linewidth=2, alpha=0.8, zorder=2)
    ax3.text(overall_pct + 0.3, len(branch_penet) - 0.5,
             f"Avg: {overall_pct:.1f}%",
             fontsize=10, fontweight='bold', color=GEN_COLORS['accent'])

    for bar, pct in zip(bars3, branch_penet['pct']):
        ax3.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                 f"{pct:.1f}%", ha='left', va='center',
                 fontsize=11, fontweight='bold', color=GEN_COLORS['dark_text'])

    ax3.set_yticks(range(len(branch_penet)))
    # Cast branch to string before slicing: when branch_config.json is
    # missing, branch column contains numeric IDs and .str[] blows up with
    # ``Can only use .str accessor with string values!''. astype(str) is
    # safe for both numeric and string branch columns.
    ax3.set_yticklabels(
        branch_penet['branch'].astype(str).str[:20],
        fontsize=11, fontweight='bold',
    )
    ax3.set_title("By Branch (Top 15)", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')
else:
    ax3.text(0.5, 0.5, 'Branch data not available',
             ha='center', va='center', fontsize=16,
             color=GEN_COLORS['muted'], transform=ax3.transAxes)
    ax3.set_title("By Branch", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')

ax3.xaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
gen_clean_axes(ax3)

# ---------------------------------------------------------------------------
# Overall title
# ---------------------------------------------------------------------------
fig.suptitle("Payroll Penetration by Demographics",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], x=0.01, ha='left', y=GEN_TITLE_Y)
fig.text(0.01, 1.01,
         f"Where is payroll detection strongest and weakest?  --  {DATASET_LABEL}",
         fontsize=13, style='italic', color=GEN_COLORS['muted'],
         ha='left', transform=fig.transFigure)

plt.tight_layout()
plt.show()
