# ===========================================================================
# THREAT QUADRANT: Penetration vs Activity Index (Conference Edition)
# ===========================================================================
# Strategic 2x2 quadrant chart. No dollars. Color = category, size = growth.
# Quadrants: Watch | Defend | Monitor | Act Now

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES
    total_accounts = combined_df['primary_account_num'].nunique()

    quad_data = []

    for competitor, competitor_trans in all_competitor_data.items():
        category = competitor_trans['competitor_category'].iloc[0]
        if category not in bank_categories:
            continue

        unique_accounts = competitor_trans['primary_account_num'].nunique()
        txn_count = len(competitor_trans)
        penetration_pct = (unique_accounts / total_accounts * 100) if total_accounts > 0 else 0

        # Growth calculation
        if 'year_month' not in competitor_trans.columns:
            competitor_trans['year_month'] = pd.to_datetime(
                competitor_trans['transaction_date']
            ).dt.to_period('M')

        sorted_months = sorted(competitor_trans['year_month'].unique())
        if len(sorted_months) >= 6:
            recent_3 = sorted_months[-3:]
            previous_3 = sorted_months[-6:-3]
            recent_txn = len(competitor_trans[competitor_trans['year_month'].isin(recent_3)])
            prev_txn = len(competitor_trans[competitor_trans['year_month'].isin(previous_3)])
            growth_rate = ((recent_txn - prev_txn) / prev_txn * 100) if prev_txn > 0 else 0
        else:
            growth_rate = 0

        quad_data.append({
            'competitor': competitor,
            'category': category,
            'penetration_pct': penetration_pct,
            'txn_count': txn_count,
            'unique_accounts': unique_accounts,
            'growth_rate': growth_rate
        })

    if len(quad_data) > 0:
        qdf = pd.DataFrame(quad_data)
        qdf['category_label'] = qdf['category'].str.replace('_', ' ').str.title()

        # Normalize transaction count to 0-100 index
        max_txn = qdf['txn_count'].max()
        qdf['activity_index'] = (qdf['txn_count'] / max_txn * 100) if max_txn > 0 else 0

        # Top 15 by combined rank
        qdf['rank_score'] = qdf['penetration_pct'] + qdf['activity_index']
        qdf = qdf.sort_values('rank_score', ascending=False).head(15)

        # Bubble size from growth (clamp negatives to small, positives scale up)
        qdf['bubble_size'] = qdf['growth_rate'].clip(lower=-20).apply(
            lambda g: max(150, min(1500, 300 + g * 15))
        )

        # Medians for quadrant lines
        med_pen = qdf['penetration_pct'].median()
        med_act = qdf['activity_index'].median()

        # ----- Build chart -----
        fig, ax = plt.subplots(figsize=(14, 10))

        # Quadrant background shading
        x_min, x_max = 0, qdf['penetration_pct'].max() * 1.2
        y_min, y_max = 0, 105

        # Top-right = danger zone (light red)
        ax.axhspan(med_act, y_max, xmin=med_pen / x_max, xmax=1,
                    color=GEN_COLORS['accent'], alpha=0.04, zorder=0)
        # Bottom-left = safe zone (light green)
        ax.axhspan(y_min, med_act, xmin=0, xmax=med_pen / x_max,
                    color=GEN_COLORS['success'], alpha=0.04, zorder=0)

        # Quadrant divider lines
        ax.axhline(y=med_act, color=GEN_COLORS['muted'], linewidth=1.5,
                    linestyle='--', alpha=0.5, zorder=1)
        ax.axvline(x=med_pen, color=GEN_COLORS['muted'], linewidth=1.5,
                    linestyle='--', alpha=0.5, zorder=1)

        # Quadrant labels
        label_props = dict(fontsize=14, fontweight='bold', alpha=0.3, ha='center', va='center')
        ax.text(med_pen * 0.5, med_act + (y_max - med_act) * 0.5, "WATCH",
                color=GEN_COLORS['warning'], **label_props, transform=ax.transData)
        ax.text(med_pen + (x_max - med_pen) * 0.5, med_act + (y_max - med_act) * 0.5, "DEFEND",
                color=GEN_COLORS['accent'], **label_props, transform=ax.transData)
        ax.text(med_pen * 0.5, med_act * 0.5, "MONITOR",
                color=GEN_COLORS['success'], **label_props, transform=ax.transData)
        ax.text(med_pen + (x_max - med_pen) * 0.5, med_act * 0.5, "ACT NOW",
                color=GEN_COLORS['info'], **label_props, transform=ax.transData)

        # Plot bubbles
        for _, row in qdf.iterrows():
            color = CATEGORY_PALETTE.get(row['category_label'], GEN_COLORS['muted'])
            edge = GEN_COLORS['accent'] if row['growth_rate'] > 10 else 'white'
            ax.scatter(
                row['penetration_pct'], row['activity_index'],
                s=row['bubble_size'], color=color, alpha=0.75,
                edgecolor=edge, linewidth=2, zorder=4
            )

        # Labels with white stroke for readability
        for _, row in qdf.iterrows():
            name = row['competitor']
            if len(name) > 20:
                name = name[:18] + '..'
            ax.annotate(
                name,
                xy=(row['penetration_pct'], row['activity_index']),
                xytext=(6, 8), textcoords='offset points',
                fontsize=11, fontweight='bold',
                color=GEN_COLORS['dark_text'],
                path_effects=[pe.withStroke(linewidth=3, foreground='white')],
                zorder=5
            )

        # Axes
        ax.set_xlabel("Account Penetration (%)", fontsize=18, fontweight='bold', labelpad=12)
        ax.set_ylabel("Transaction Activity Index", fontsize=18, fontweight='bold', labelpad=12)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        ax.set_xlim(0, x_max)
        ax.set_ylim(y_min, y_max)

        gen_clean_axes(ax)
        ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
        ax.set_axisbelow(True)

        # Title
        ax.set_title("Threat Quadrant",
                     fontsize=28, fontweight='bold',
                     color=GEN_COLORS['dark_text'], pad=20, loc='left')
        ax.text(0.0, 0.97, "Bubble size = growth momentum  |  Red border = fast growers (>10%)",
                transform=ax.transAxes, fontsize=13,
                color=GEN_COLORS['muted'], style='italic')

        # Category legend
        legend_cats = qdf['category_label'].unique()
        legend_handles = [
            plt.scatter([], [], s=150, color=CATEGORY_PALETTE.get(c, GEN_COLORS['muted']),
                        edgecolor='white', linewidth=1.5, label=c)
            for c in legend_cats
        ]
        ax.legend(
            handles=legend_handles,
            loc='upper center', bbox_to_anchor=(0.5, -0.06),
            ncol=len(legend_cats), fontsize=14, frameon=False
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.10)
        plt.show()

        # ----- OPPORTUNITY: Declining competitors -----
        declining = qdf[qdf['growth_rate'] < -5].sort_values('growth_rate')
        if len(declining) > 0:
            print(f"\n    OPPORTUNITY: {len(declining)} competitor(s) declining >5%:")
            for _, row in declining.iterrows():
                print(f"      {row['competitor']:30s}  {row['growth_rate']:+.1f}%  ({row['category_label']})")
            print("    Declining competitors = customers potentially ready to consolidate back to you.")
