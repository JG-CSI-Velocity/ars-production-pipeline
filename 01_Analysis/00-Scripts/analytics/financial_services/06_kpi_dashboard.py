# ===========================================================================
# KPI DASHBOARD: Financial Services Leakage at a Glance
# ===========================================================================

total_members = combined_df['primary_account_num'].nunique()

# Addressable leakage only -- exclude categories the FI can't realistically win
# back (Insurance, Tax & Accounting). Owner decision: the headline reflects
# capturable product leakage; insurance/tax are reported separately as context.
try:
    _non_addr = set(NON_ADDRESSABLE_CATEGORIES)
except NameError:
    _non_addr = {'Insurance', 'Tax & Accounting'}

_has_addr     = multi_product_df['categories'].apply(lambda cs: any(c not in _non_addr for c in cs))
addressable_df = multi_product_df[_has_addr]

leaking_members = len(addressable_df)
pct_leaking = (leaking_members / total_members * 100) if total_members > 0 else 0
n_addr_categories = len([c for c in financial_services_data if c not in _non_addr])
_addr_cat_count = addressable_df['categories'].apply(lambda cs: sum(1 for c in cs if c not in _non_addr))
avg_categories = _addr_cat_count.mean() if len(addressable_df) > 0 else 0
active_30d = len(addressable_df[addressable_df['recency_days'] <= 30])

# Context only (not counted as addressable leakage): insurance / tax reach
_has_ctx = multi_product_df['categories'].apply(lambda cs: any(c in _non_addr for c in cs))
context_members = int(_has_ctx.sum())
pct_context = (context_members / total_members * 100) if total_members > 0 else 0

kpis = [
    (f"{pct_leaking:.1f}%",     "of Account Holders Use\nAddressable External Products", GEN_COLORS['accent']),
    (f"{n_addr_categories}",    "Addressable Product\nCategories Detected",  GEN_COLORS['info']),
    (f"{avg_categories:.1f}",   "Avg Addressable Services\nper Account Holder",  GEN_COLORS['warning']),
    (f"{active_30d:,}",         "Active Addressable\nLeakage (30 Days)",     GEN_COLORS['success']),
]

fig, axes = plt.subplots(1, 4, figsize=(18, 5))
fig.patch.set_facecolor('#FFFFFF')

for ax, (value, label, color) in zip(axes, kpis):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    card = FancyBboxPatch(
        (0.03, 0.05), 0.94, 0.90,
        boxstyle="round,pad=0.05",
        facecolor=color, alpha=0.08,
        edgecolor=color, linewidth=2.5
    )
    ax.add_patch(card)

    ax.text(0.5, 0.62, value, transform=ax.transAxes,
            fontsize=48, fontweight='bold', color=color,
            ha='center', va='center')
    ax.text(0.5, 0.20, label, transform=ax.transAxes,
            fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'],
            ha='center', va='center', linespacing=1.4)

fig.suptitle("Financial Services Leakage at a Glance",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)

plt.tight_layout()
plt.show()

if pct_leaking > 30:
    print(f"\n    INSIGHT: {pct_leaking:.0f}% of your account holders use external financial products you could win back.")
    print(f"    That is {leaking_members:,} account holders with addressable relationships elsewhere.")
print(f"    (Context: {pct_context:.0f}% use insurance/tax services -- reported separately, not capturable leakage.)")
