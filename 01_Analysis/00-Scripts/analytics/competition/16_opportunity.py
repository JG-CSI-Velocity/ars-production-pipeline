# ===========================================================================
# OPPORTUNITY ANALYSIS: Declining Competitors + Winback Targets
# ===========================================================================
# NEW CELL - Surfaces competitors losing ground = your opportunity.
# No dollars. Focus on accounts and transaction trends.

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES
    total_accounts = combined_df['primary_account_num'].nunique()

    opp_data = []

    for competitor, competitor_trans in all_competitor_data.items():
        category = competitor_trans['competitor_category'].iloc[0]
        if category not in bank_categories:
            continue

        unique_accounts = competitor_trans['primary_account_num'].nunique()
        txn_count = len(competitor_trans)
        penetration_pct = (unique_accounts / total_accounts * 100) if total_accounts > 0 else 0

        if 'year_month' not in competitor_trans.columns:
            competitor_trans['year_month'] = pd.to_datetime(
                competitor_trans['transaction_date']
            ).dt.to_period('M')

        sorted_months = sorted(competitor_trans['year_month'].unique())
        if len(sorted_months) < 6:
            continue

        recent_3 = sorted_months[-3:]
        previous_3 = sorted_months[-6:-3]

        recent_txn = len(competitor_trans[competitor_trans['year_month'].isin(recent_3)])
        prev_txn = len(competitor_trans[competitor_trans['year_month'].isin(previous_3)])
        txn_growth = ((recent_txn - prev_txn) / prev_txn * 100) if prev_txn > 0 else 0

        recent_acct = competitor_trans[
            competitor_trans['year_month'].isin(recent_3)
        ]['primary_account_num'].nunique()
        prev_acct = competitor_trans[
            competitor_trans['year_month'].isin(previous_3)
        ]['primary_account_num'].nunique()
        acct_growth = ((recent_acct - prev_acct) / prev_acct * 100) if prev_acct > 0 else 0

        opp_data.append({
            'bank': competitor,
            'category': category,
            'unique_accounts': unique_accounts,
            'penetration_pct': penetration_pct,
            'txn_growth': txn_growth,
            'acct_growth': acct_growth,
            'recent_acct': recent_acct,
        })

    if len(opp_data) > 0:
        odf = pd.DataFrame(opp_data)
        odf['category_label'] = odf['category'].str.replace('_', ' ').str.title()

        # Filter to declining competitors with meaningful account base
        declining = odf[
            (odf['txn_growth'] < 0) &
            (odf['unique_accounts'] >= 25)
        ].sort_values('txn_growth').copy()

        # Opportunity score: bigger bank + faster decline = bigger opportunity
        if len(declining) > 0:
            max_pen = declining['penetration_pct'].max()
            declining['opp_score'] = (
                (declining['penetration_pct'] / max_pen * 50 if max_pen > 0 else 0) +
                (declining['txn_growth'].abs() / declining['txn_growth'].abs().max() * 50)
            )
            declining = declining.sort_values('opp_score', ascending=False).head(12)

            # ----- Build chart -----
            fig, ax = plt.subplots(figsize=(14, 8))

            plot_df = declining.iloc[::-1]  # Reverse for top-down display

            # Bubble scatter: x = decline rate, y = position, size = accounts
            max_acct = plot_df['unique_accounts'].max()
            bubble_sizes = (plot_df['unique_accounts'] / max_acct * 800) + 200

            colors = [CATEGORY_PALETTE.get(c, GEN_COLORS['muted']) for c in plot_df['category_label']]

            ax.scatter(
                plot_df['txn_growth'].abs(),
                range(len(plot_df)),
                s=bubble_sizes,
                c=colors,
                alpha=0.75,
                edgecolor='white',
                linewidth=2,
                zorder=3
            )

            # Labels
            for i, (_, row) in enumerate(plot_df.iterrows()):
                name = row['bank']
                if len(name) > 25:
                    name = name[:23] + '..'

                ax.text(
                    row['txn_growth'] * -1 + 1, i,
                    f"  {name}  ({row['txn_growth']:+.1f}%)",
                    fontsize=13, fontweight='bold',
                    color=GEN_COLORS['dark_text'],
                    va='center',
                    path_effects=[pe.withStroke(linewidth=2, foreground='white')]
                )

            ax.set_yticks([])
            ax.set_xlabel("Rate of Decline (%)", fontsize=18, fontweight='bold', labelpad=12)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

            gen_clean_axes(ax, keep_left=False)
            ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
            ax.set_axisbelow(True)

            # Title
            ax.set_title("Winback Opportunities",
                         fontsize=28, fontweight='bold',
                         color=GEN_COLORS['success'], pad=20, loc='left')
            ax.text(0.0, 0.97,
                    "Competitors losing ground = your chance to win customers back",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            # Size legend note
            ax.text(0.99, 0.01, "Bubble size = number of accounts",
                    transform=ax.transAxes, fontsize=11,
                    color=GEN_COLORS['muted'], ha='right', va='bottom', style='italic')

            # Category legend
            legend_cats = plot_df['category_label'].unique()
            legend_handles = [
                plt.scatter([], [], s=150, color=CATEGORY_PALETTE.get(c, GEN_COLORS['muted']),
                            edgecolor='white', linewidth=1.5, label=c)
                for c in legend_cats
            ]
            ax.legend(
                handles=legend_handles,
                loc='upper center', bbox_to_anchor=(0.5, -0.08),
                ncol=len(legend_cats), fontsize=14, frameon=False
            )

            plt.tight_layout()
            plt.subplots_adjust(bottom=0.12)
            plt.show()

            # Summary
            total_opp_accounts = declining['unique_accounts'].sum()
            avg_decline = declining['txn_growth'].mean()
            print(f"\n    OPPORTUNITY SUMMARY:")
            print(f"    {len(declining)} competitors declining  |  {total_opp_accounts:,} accounts in play")
            print(f"    Average decline rate: {avg_decline:.1f}%")
            print(f"    RECOMMENDED ACTION: Target these {total_opp_accounts:,} accounts with")
            print(f"    personalized retention/acquisition campaigns.")

        else:
            print("\n    No declining competitors detected in this period.")
            print("    All competitors are stable or growing -- focus on defensive retention.")
