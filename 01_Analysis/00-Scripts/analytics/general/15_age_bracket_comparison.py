# ===========================================================================
# AGE BRACKET COMPARISON: Spending Bracket Distribution by Age Band
# ===========================================================================
# Stacked bar per age band showing bracket distribution. (14,7).
# Do younger members make more small txns? Do older skew larger?

age_matched_local = demo_df[demo_df['age_band'].notna()].copy()

# Ensure amount_bracket exists on demo_df
if 'amount_bracket' not in age_matched_local.columns:
    age_matched_local['amount_bracket'] = pd.cut(
        age_matched_local['amount'], bins=BRACKET_BINS, labels=BRACKET_LABELS, right=False
    )

# Cross-tab: age band x bracket, normalized per age band
age_bracket_ct = pd.crosstab(
    age_matched_local['age_band'],
    age_matched_local['amount_bracket'],
    normalize='index'
) * 100

# Ensure column order matches BRACKET_LABELS
age_bracket_ct = age_bracket_ct[[b for b in BRACKET_LABELS if b in age_bracket_ct.columns]]
# Ensure row order matches AGE_ORDER
age_bracket_ct = age_bracket_ct.reindex([b for b in AGE_ORDER if b in age_bracket_ct.index])

fig, ax = plt.subplots(figsize=(16, 8))

x = np.arange(len(age_bracket_ct))
bar_width = 0.65
bottom = np.zeros(len(age_bracket_ct))

for i, bracket in enumerate(age_bracket_ct.columns):
    vals = age_bracket_ct[bracket].values
    ax.bar(
        x, vals, bar_width,
        bottom=bottom, color=BRACKET_PALETTE[BRACKET_LABELS.index(bracket)],
        label=bracket, edgecolor='white', linewidth=0.5
    )
    # Label segments > 8%
    for j, v in enumerate(vals):
        if v > 8:
            ax.text(x[j], bottom[j] + v / 2, f"{v:.0f}%",
                    ha='center', va='center', fontsize=14,
                    fontweight='bold', color='white',
                    path_effects=[pe.withStroke(linewidth=2, foreground='#333333')])
    bottom += vals

ax.set_xticks(x)
ax.set_xticklabels(age_bracket_ct.index, fontsize=16, fontweight='bold')
ax.set_ylabel("% of Transactions", fontsize=18, fontweight='bold', labelpad=10)
ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))

gen_clean_axes(ax, keep_left=True, keep_bottom=True)

ax.set_title("Spending Bracket Mix by Age Group",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Do younger account holders skew smaller? Do older account holders skew larger?",
        transform=ax.transAxes, fontsize=16,
        color=GEN_COLORS['muted'], style='italic')

ax.legend(
    loc='upper center', bbox_to_anchor=(0.5, -0.08),
    ncol=4, fontsize=15, frameon=False, title='Spending Bracket',
    title_fontproperties={'weight': 'bold', 'size': 16}
)

plt.tight_layout()
plt.subplots_adjust(bottom=0.15)
plt.show()
