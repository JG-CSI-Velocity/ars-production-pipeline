# ===========================================================================
# MOMENTUM: Fastest Growing vs Declining Banks (Conference Edition)
# ===========================================================================
# Diverging horizontal bar chart. Growing = right (red). Declining = left (green).
# No dollars. Uses transaction growth rate (last 3mo vs prev 3mo).

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES

    momentum_data = []

    for competitor, competitor_trans in all_competitor_data.items():
        category = competitor_trans['competitor_category'].iloc[0]
        if category not in bank_categories:
            continue

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

        recent_acct = competitor_trans[
            competitor_trans['year_month'].isin(recent_3)
        ]['primary_account_num'].nunique()

        txn_growth = ((recent_txn - prev_txn) / prev_txn * 100) if prev_txn > 0 else 0

        # Minimum threshold: need at least 50 recent transactions to be meaningful
        if recent_txn < 50:
            continue

        momentum_data.append({
            'bank': competitor,
            'category': category,
            'txn_growth': txn_growth,
            'recent_txn': recent_txn,
            'recent_acct': recent_acct
        })

    if len(momentum_data) > 0:
        mdf = pd.DataFrame(momentum_data)
        mdf['category_label'] = mdf['category'].str.replace('_', ' ').str.title()

        # Top 8 growers + Top 7 decliners (show both sides)
        growers = mdf[mdf['txn_growth'] > 0].sort_values('txn_growth', ascending=False).head(8)
        decliners = mdf[mdf['txn_growth'] < 0].sort_values('txn_growth', ascending=True).head(7)
        show_df = pd.concat([growers, decliners]).sort_values('txn_growth', ascending=True)

        if len(show_df) > 0:
            # Shorten names
            show_df['short_name'] = show_df['bank'].apply(
                lambda n: n[:25] + '..' if len(str(n)) > 27 else n
            )

            fig, ax = plt.subplots(figsize=(14, 9))

            # Bar colors: red for growing, green for declining (opportunity)
            bar_colors = [
                GEN_COLORS['accent'] if g > 0 else GEN_COLORS['success']
                for g in show_df['txn_growth']
            ]

            bars = ax.barh(
                range(len(show_df)),
                show_df['txn_growth'],
                color=bar_colors,
                edgecolor='white',
                linewidth=1,
                height=0.65,
                zorder=3
            )

            # Value labels
            for i, (_, row) in enumerate(show_df.iterrows()):
                offset = 1.5 if row['txn_growth'] >= 0 else -1.5
                ha = 'left' if row['txn_growth'] >= 0 else 'right'
                ax.text(
                    row['txn_growth'] + offset, i,
                    f"{row['txn_growth']:+.1f}%",
                    fontsize=13, fontweight='bold',
                    color=GEN_COLORS['dark_text'],
                    va='center', ha=ha
                )

            ax.set_yticks(range(len(show_df)))
            ax.set_yticklabels(show_df['short_name'], fontsize=13, fontweight='bold')

            # Center line
            ax.axvline(x=0, color=GEN_COLORS['dark_text'], linewidth=2, zorder=5)

            # Labels
            ax.set_xlabel("Transaction Growth (Last 3mo vs Previous 3mo)",
                         fontsize=16, fontweight='bold', labelpad=12)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.0f}%"))

            gen_clean_axes(ax)
            ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
            ax.set_axisbelow(True)

            # Title
            ax.set_title("Competitive Momentum",
                         fontsize=28, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=20, loc='left')
            ax.text(0.0, 0.97, "Who is gaining?  Who is losing?",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            # Side labels
            x_max = show_df['txn_growth'].abs().max()
            ax.text(x_max * 0.7, len(show_df) + 0.3,
                    "THREAT  -->",
                    fontsize=14, fontweight='bold', color=GEN_COLORS['accent'],
                    alpha=0.5, ha='center')
            ax.text(-x_max * 0.7, len(show_df) + 0.3,
                    "<--  OPPORTUNITY",
                    fontsize=14, fontweight='bold', color=GEN_COLORS['success'],
                    alpha=0.5, ha='center')

            plt.tight_layout()
            plt.show()

            # Opportunity callout
            if len(decliners) > 0:
                total_declining_acct = decliners['recent_acct'].sum()
                print(f"\n    OPPORTUNITY: {len(decliners)} banks losing momentum.")
                print(f"    {total_declining_acct:,} accounts showing reduced competitor activity.")
                print("    These customers may be ready to consolidate -- target with retention offers.")
    else:
        print("Insufficient data for momentum analysis (need 6+ months).")
