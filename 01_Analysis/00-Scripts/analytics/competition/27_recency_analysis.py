# ===========================================================================
# RECENCY ANALYSIS: Days Since Last Competitor Transaction (Conference)
# ===========================================================================
# Aggregate recency distribution across all competitor accounts, plus
# a 30/90/180-day breakdown. Uses all_account_summaries.

if 'all_account_summaries' not in dir():
    print("⚠️  all_account_summaries not found — run 19_account_summaries.py first.")
elif len(all_account_summaries) > 0:
    # Build category lookup from competitor_txns (robust to key mismatches)
    _cat_lookup = (
        competitor_txns.groupby('competitor_match')['competitor_category']
        .first()
        .to_dict()
    )

    # Combine recency from all competitors into one view
    _all_recency = []
    for comp_name, acct_df in all_account_summaries.items():
        cat_raw = _cat_lookup.get(comp_name, None)
        if cat_raw is None or cat_raw in PAYMENT_ECOSYSTEMS:
            continue
        _r = acct_df[['recency_days']].copy()
        _r['competitor'] = comp_name
        _r['category'] = clean_category(cat_raw)
        _all_recency.append(_r)

    recency_all = pd.concat(_all_recency, ignore_index=True)

    # --- Aggregate histogram ---
    fig, ax = plt.subplots(figsize=(14, 7))

    bins = list(range(0, min(int(recency_all['recency_days'].max()) + 30, 400), 15))
    ax.hist(recency_all['recency_days'], bins=bins,
            color=GEN_COLORS['warning'], edgecolor='white',
            linewidth=0.8, alpha=0.85, zorder=3)

    # Reference lines
    for days, label, color in [
        (30, '30 days', GEN_COLORS['success']),
        (90, '90 days', GEN_COLORS['info']),
        (180, '180 days', GEN_COLORS['accent']),
    ]:
        ax.axvline(days, color=color, linestyle='--', linewidth=2.5,
                   alpha=0.7, label=label, zorder=4)

    ax.set_xlabel('Days Since Last Competitor Transaction',
                  fontsize=16, fontweight='bold', labelpad=10)
    ax.set_ylabel('Account-Competitor Pairs',
                  fontsize=16, fontweight='bold', labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

    gen_clean_axes(ax)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    ax.set_title('Competitor Recency Distribution',
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=20, loc='left')
    ax.text(0.0, 0.97,
            "How recently are your members transacting with competitors?",
            transform=ax.transAxes, fontsize=13,
            color=GEN_COLORS['muted'], style='italic')

    # Stats annotation
    total = len(recency_all)
    r30 = (recency_all['recency_days'] <= 30).sum()
    r90 = (recency_all['recency_days'] <= 90).sum()
    r180 = (recency_all['recency_days'] <= 180).sum()

    stats = (
        f"Last 30 days: {r30:,} ({r30/total*100:.1f}%)\n"
        f"Last 90 days: {r90:,} ({r90/total*100:.1f}%)\n"
        f"Last 180 days: {r180:,} ({r180/total*100:.1f}%)"
    )
    ax.text(0.97, 0.95, stats, transform=ax.transAxes,
            va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='white',
                      alpha=0.95, edgecolor=GEN_COLORS['grid'], linewidth=2),
            fontsize=12, fontweight='bold', family='monospace')

    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
              ncol=3, fontsize=12, frameon=False)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.10)
    plt.show()

    # Insight callout
    if r30 / total > 0.5:
        print(f"    ACTIVE THREAT: {r30/total*100:.1f}% of competitor relationships "
              f"had activity in the last 30 days.")
    dormant = total - r180
    if dormant > 0:
        print(f"    OPPORTUNITY: {dormant:,} account-competitor pairs dormant for 180+ days "
              f"-- these members may be consolidating back to you.")
