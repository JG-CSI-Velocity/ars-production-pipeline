# ===========================================================================
# RELATIONSHIP BY DEMOGRAPHICS: 3-Panel Depth Analysis (Conference Edition)
# ===========================================================================
# Panel 1: Product count by age band
# Panel 2: Product count by account age / tenure
# Panel 3: Product count by branch
# Which segments have the shallowest relationships?

if 'rel_df' not in dir() or len(rel_df) == 0:
    print("    No relationship data available. Skipping demographics analysis.")
else:
    # ------------------------------------------------------------------
    # Determine which panels we can build
    # ------------------------------------------------------------------
    panels = []

    # Panel 1: Age band
    if 'age_band' in rel_df.columns and rel_df['age_band'].notna().sum() > 0:
        age_depth = (
            rel_df.groupby('age_band')
            .agg(
                avg_products=('product_count', 'mean'),
                member_count=('account_number', 'count'),
                pct_single=('product_count', lambda x: (x == 1).mean() * 100),
            )
            .reset_index()
        )
        age_depth = age_depth[age_depth['member_count'] >= 10]
        if len(age_depth) > 0:
            # Sort by AGE_ORDER
            age_depth['age_band'] = pd.Categorical(
                age_depth['age_band'], categories=AGE_ORDER, ordered=True
            )
            age_depth = age_depth.sort_values('age_band').dropna(subset=['age_band'])
            panels.append({
                'data': age_depth,
                'x_col': 'age_band',
                'title': 'By Age Band',
                'palette': AGE_PALETTE,
            })

    # Panel 2: Tenure band
    if 'tenure_band' in rel_df.columns and rel_df['tenure_band'].notna().sum() > 0:
        tenure_depth = (
            rel_df.groupby('tenure_band')
            .agg(
                avg_products=('product_count', 'mean'),
                member_count=('account_number', 'count'),
                pct_single=('product_count', lambda x: (x == 1).mean() * 100),
            )
            .reset_index()
        )
        tenure_depth = tenure_depth[tenure_depth['member_count'] >= 10]
        if len(tenure_depth) > 0:
            tenure_depth['tenure_band'] = pd.Categorical(
                tenure_depth['tenure_band'], categories=ACCT_AGE_ORDER, ordered=True
            )
            tenure_depth = tenure_depth.sort_values('tenure_band').dropna(subset=['tenure_band'])
            panels.append({
                'data': tenure_depth,
                'x_col': 'tenure_band',
                'title': 'By Account Tenure',
                'palette': ACCT_AGE_PALETTE,
            })

    # Panel 3: Branch
    if 'branch' in rel_df.columns and rel_df['branch'].notna().sum() > 0:
        branch_depth = (
            rel_df.groupby('branch')
            .agg(
                avg_products=('product_count', 'mean'),
                member_count=('account_number', 'count'),
                pct_single=('product_count', lambda x: (x == 1).mean() * 100),
            )
            .reset_index()
        )
        # Filter to branches with meaningful member counts
        min_branch_members = max(20, len(rel_df) * 0.005)
        branch_depth = branch_depth[branch_depth['member_count'] >= min_branch_members]
        branch_depth = branch_depth.sort_values('avg_products', ascending=True)
        if len(branch_depth) > 15:
            branch_depth = branch_depth.tail(15)
        if len(branch_depth) > 0:
            panels.append({
                'data': branch_depth,
                'x_col': 'branch',
                'title': 'By Branch',
                'palette': None,
            })

    if len(panels) == 0:
        print("    No demographic dimensions available (age, tenure, branch).")
        print("    Skipping demographics panel.")
    else:
        n_panels = len(panels)
        fig, axes = plt.subplots(1, n_panels, figsize=(max(14, 6 * n_panels), 7))
        if n_panels == 1:
            axes = [axes]

        for ax, panel in zip(axes, panels):
            data = panel['data']
            x_col = panel['x_col']
            x_labels = [str(v)[:15] for v in data[x_col]]
            x_pos = range(len(data))
            values = data['avg_products'].values

            # Color bars
            if panel['palette']:
                bar_colors = [
                    panel['palette'].get(str(v), GEN_COLORS['info'])
                    for v in data[x_col]
                ]
            else:
                n = len(data)
                bar_colors = [plt.cm.ScalarMappable(
                    cmap=LinearSegmentedColormap.from_list(
                        'branch', [GEN_COLORS['info'], GEN_COLORS['primary']]
                    ),
                    norm=plt.Normalize(0, max(n - 1, 1))
                ).to_rgba(i) for i in range(n)]

            bars = ax.bar(
                x_pos, values, color=bar_colors,
                edgecolor='white', linewidth=1.5, width=0.65, zorder=3
            )

            ax.set_xticks(x_pos)
            rotation = 45 if len(x_labels) > 6 else 0
            ha = 'right' if rotation > 0 else 'center'
            ax.set_xticklabels(x_labels, fontsize=14, fontweight='bold',
                               rotation=rotation, ha=ha)

            max_v = max(values) if len(values) > 0 else 1
            for i, v in enumerate(values):
                pct_single = data.iloc[i]['pct_single']
                ax.text(i, v + max_v * 0.02,
                        f"{v:.1f}\n({pct_single:.0f}% single)",
                        ha='center', va='bottom', fontsize=14, fontweight='bold',
                        color=GEN_COLORS['dark_text'])

            ax.set_ylabel("Avg Products/Member", fontsize=16, fontweight='bold', labelpad=8)
            ax.set_ylim(0, max_v * 1.35)

            gen_clean_axes(ax)
            ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
            ax.set_axisbelow(True)

            ax.set_title(panel['title'], fontsize=18, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=12)

            # Highlight shallowest segment
            min_idx = data['avg_products'].idxmin()
            min_segment = data.loc[min_idx, x_col]
            min_val = data.loc[min_idx, 'avg_products']
            pos_in_chart = list(data.index).index(min_idx)
            ax.annotate(
                'shallowest',
                xy=(pos_in_chart, min_val),
                xytext=(pos_in_chart, min_val + max_v * 0.15),
                fontsize=14, fontweight='bold', color=GEN_COLORS['accent'],
                ha='center',
                arrowprops=dict(arrowstyle='->', color=GEN_COLORS['accent'], lw=1.5)
            )

        fig.suptitle("Relationship Depth by Demographic Segment",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
        fig.text(0.01, 1.01,
                 f"Which segments have the shallowest relationships?  |  {DATASET_LABEL}",
                 transform=fig.transFigure, fontsize=14,
                 color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()
