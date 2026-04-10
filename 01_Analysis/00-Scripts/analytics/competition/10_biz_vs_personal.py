# ===========================================================================
# BUSINESS vs PERSONAL: Side-by-Side Donut (Conference Edition)
# ===========================================================================
# No dollars. Shows transaction split + account split.

if len(all_competitor_data) > 0:
    all_competitor_trans = pd.concat(all_competitor_data.values(), ignore_index=True)

    if 'business_flag' in all_competitor_trans.columns:
        biz_split = all_competitor_trans.groupby('business_flag').agg({
            'amount': 'count',
            'primary_account_num': 'nunique'
        })
        biz_split.columns = ['transactions', 'accounts']
        biz_split.index = biz_split.index.map({
            'Yes': 'Business', 'No': 'Personal'
        })

        biz_colors = {
            'Business': GEN_COLORS['primary'],
            'Personal': GEN_COLORS['success']
        }

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        # --- LEFT: Transaction split ---
        wedges1, _, autotexts1 = ax1.pie(
            biz_split['transactions'],
            labels=None,
            autopct='%1.0f%%',
            colors=[biz_colors.get(c, GEN_COLORS['muted']) for c in biz_split.index],
            startangle=90,
            pctdistance=0.78,
            wedgeprops=dict(width=0.42, edgecolor='white', linewidth=3)
        )
        for t in autotexts1:
            t.set_fontsize(22)
            t.set_fontweight('bold')
            t.set_color('white')
            t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

        ax1.text(0, 0, f"{biz_split['transactions'].sum():,.0f}\nTransactions",
                 ha='center', va='center',
                 fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'],
                 linespacing=1.5)
        ax1.set_title("Transaction Split", fontsize=22, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=15)

        # --- RIGHT: Account split ---
        wedges2, _, autotexts2 = ax2.pie(
            biz_split['accounts'],
            labels=None,
            autopct='%1.0f%%',
            colors=[biz_colors.get(c, GEN_COLORS['muted']) for c in biz_split.index],
            startangle=90,
            pctdistance=0.78,
            wedgeprops=dict(width=0.42, edgecolor='white', linewidth=3)
        )
        for t in autotexts2:
            t.set_fontsize(22)
            t.set_fontweight('bold')
            t.set_color('white')
            t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

        ax2.text(0, 0, f"{biz_split['accounts'].sum():,.0f}\nAccounts",
                 ha='center', va='center',
                 fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'],
                 linespacing=1.5)
        ax2.set_title("Account Split", fontsize=22, fontweight='bold',
                       color=GEN_COLORS['dark_text'], pad=15)

        # Shared legend
        legend_handles = [
            plt.Rectangle((0, 0), 1, 1, fc=biz_colors[lbl], edgecolor='white',
                           linewidth=1.5, label=lbl)
            for lbl in biz_split.index
        ]
        fig.legend(
            handles=legend_handles,
            loc='upper center',
            bbox_to_anchor=(0.5, 0.02),
            ncol=2,
            fontsize=16,
            frameon=False,
            handletextpad=0.5,
            columnspacing=3.0
        )

        fig.suptitle("Business vs Personal Competitor Activity",
                     fontsize=28, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=1.02)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.08)
        plt.show()

        # Opportunity callout
        biz_pct = biz_split.loc['Business', 'transactions'] / biz_split['transactions'].sum() * 100
        if biz_pct > 30:
            print(f"\n    OPPORTUNITY: Business accounts represent {biz_pct:.0f}% of competitor transactions.")
            print("    High-value business relationships at risk -- prioritize commercial retention.")
    else:
        print("No business_flag column found in competitor data.")
