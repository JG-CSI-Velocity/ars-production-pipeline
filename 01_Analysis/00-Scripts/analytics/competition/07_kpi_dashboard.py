# ===========================================================================
# KPI DASHBOARD: High-Level Competitor Metrics (Conference Edition)
# ===========================================================================
# Big bold numbers for a stage screen. No tables, no dollars.
# Shows: % of accounts using competitors, % of transactions, competitor count

if len(all_competitor_data) > 0:
    summary_df = pd.DataFrame(summary_data).sort_values('total_amount', ascending=False)

    # BUG FIX: summary_df has ONE row per competitor, so summing
    # unique_accounts double-counts any account that uses >1 competitor
    # (drove pct_accounts above 100%). Count distinct accounts once
    # across the whole competitor_txns frame instead.
    # Isolate payment ecosystems (wallets/p2p/bnpl) from TRUE competitors
    # (banks/CUs/crypto-investing). Venmo/PayPal/Zelle/Cash App/BNPL are
    # near-universal payment apps, not displacement threats -- lumping them in
    # inflated "% using competitors". Headline = true competitors only; payment
    # app adoption is reported as its own, clearly-labeled number.
    try:
        _true_cats, _eco_cats = list(TRUE_COMPETITORS), list(PAYMENT_ECOSYSTEMS)
    except NameError:
        _eco_cats = ['wallets', 'p2p', 'bnpl']
        _true_cats = [c for c in competitor_txns['competitor_category'].dropna().unique()
                      if c not in _eco_cats]

    _true_txns = competitor_txns[competitor_txns['competitor_category'].isin(_true_cats)]
    _eco_txns  = competitor_txns[competitor_txns['competitor_category'].isin(_eco_cats)]

    total_competitor_trans    = len(_true_txns)
    total_competitor_accounts = _true_txns['primary_account_num'].nunique()
    total_competitors_found   = _true_txns['competitor_match'].nunique()

    total_all_trans    = len(combined_df)
    total_all_accounts = combined_df['primary_account_num'].nunique()

    pct_trans    = (total_competitor_trans / total_all_trans * 100) if total_all_trans > 0 else 0
    pct_accounts = (total_competitor_accounts / total_all_accounts * 100) if total_all_accounts > 0 else 0

    eco_accounts     = _eco_txns['primary_account_num'].nunique()
    pct_eco_accounts = (eco_accounts / total_all_accounts * 100) if total_all_accounts > 0 else 0

    _muted = GEN_COLORS.get('muted', '#6C757D') if hasattr(GEN_COLORS, 'get') else '#6C757D'

    # ----- KPI card layout (headline = true competitors; payment apps separate) -----
    kpis = [
        (f"{pct_accounts:.1f}%",       "of Accounts Using\nCompetitor Banks/CUs",  GEN_COLORS['accent']),
        (f"{pct_trans:.1f}%",          "of Transactions\nto Competitors",          GEN_COLORS['info']),
        (f"{total_competitors_found}", "Competitors\nDetected",                    GEN_COLORS['warning']),
        (f"{pct_eco_accounts:.1f}%",   "Use Payment Apps\n(not competitors)",      _muted),
    ]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    fig.patch.set_facecolor('#FFFFFF')

    for ax, (value, label, color) in zip(axes, kpis):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Card background
        card = FancyBboxPatch(
            (0.03, 0.05), 0.94, 0.90,
            boxstyle="round,pad=0.05",
            facecolor=color,
            alpha=0.08,
            edgecolor=color,
            linewidth=2.5
        )
        ax.add_patch(card)

        # Big number
        ax.text(0.5, 0.62, value, transform=ax.transAxes,
                fontsize=48, fontweight='bold', color=color,
                ha='center', va='center')

        # Label
        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=15, fontweight='bold', color=GEN_COLORS['dark_text'],
                ha='center', va='center', linespacing=1.4)

    # Supertitle
    fig.suptitle("Competitive Exposure at a Glance",
                 fontsize=28, fontweight='bold',
                 color=GEN_COLORS['dark_text'],
                 y=GEN_TITLE_Y)

    plt.tight_layout()
    plt.show()

    # Opportunity callout -- based on TRUE competitor reach (banks/CUs/crypto),
    # not payment-app usage.
    if pct_accounts < 20:
        print(f"\n    OPPORTUNITY: Only {pct_accounts:.1f}% of accounts use a competitor bank/CU.")
        print("    Competitor footprint is limited -- defend these relationships now before it grows.")
    elif pct_accounts > 40:
        print(f"\n    WARNING: {pct_accounts:.1f}% of accounts use a competitor bank/CU.")
        print("    Significant competitive overlap -- targeted retention strategy needed.")
    print(f"    (Payment apps -- Venmo/PayPal/Zelle/Cash App/BNPL -- reach "
          f"{pct_eco_accounts:.1f}% of accounts; reported separately, not as competitors.)")
