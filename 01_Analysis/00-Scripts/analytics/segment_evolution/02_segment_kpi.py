# ===========================================================================
# SEGMENT EVOLUTION KPI: 4-Card Migration Snapshot (Conference Edition)
# ===========================================================================
# Card 1: % Upgraded | Card 2: % Degraded | Card 3: % Stable
# Card 4: Most Common Current Segment. (18, 5) FancyBboxPatch cards.

if 'seg_evo_df' not in dir() or len(seg_evo_df) == 0:
    print("    No segment evolution data available. Skipping KPI dashboard.")
else:
    with_data = seg_evo_df[seg_evo_df['waves_present'] > 0]
    n_total = len(with_data)

    if n_total == 0:
        print("    No accounts with segmentation data. Skipping KPI dashboard.")
    else:
        upgraded_ct = (with_data['direction'] == 'upgraded').sum()
        degraded_ct = (with_data['direction'] == 'degraded').sum()
        stable_ct = (with_data['direction'] == 'stable').sum()

        pct_upgraded = upgraded_ct / n_total * 100
        pct_degraded = degraded_ct / n_total * 100
        pct_stable = stable_ct / n_total * 100

        # Most common current (last) segment
        last_seg_counts = with_data['last_segment'].dropna().value_counts()
        most_common_seg = last_seg_counts.index[0] if len(last_seg_counts) > 0 else 'N/A'
        most_common_pct = (
            last_seg_counts.iloc[0] / n_total * 100
            if len(last_seg_counts) > 0 else 0
        )

        fig, axes = plt.subplots(1, 4, figsize=(18, 5))

        kpi_data = [
            {
                'label': 'Upgraded',
                'value': f"{pct_upgraded:.1f}%",
                'sub': f"{upgraded_ct:,} accounts moved to a higher segment",
                'color': GEN_COLORS['success'],
            },
            {
                'label': 'Degraded',
                'value': f"{pct_degraded:.1f}%",
                'sub': f"{degraded_ct:,} accounts moved to a lower segment",
                'color': GEN_COLORS['accent'],
            },
            {
                'label': 'Stable',
                'value': f"{pct_stable:.1f}%",
                'sub': f"{stable_ct:,} accounts remained in same segment",
                'color': GEN_COLORS['info'],
            },
            {
                'label': 'Top Current Segment',
                'value': most_common_seg,
                'sub': f"{most_common_pct:.1f}% of accounts ({last_seg_counts.iloc[0]:,})"
                       if len(last_seg_counts) > 0 else "no data",
                'color': GEN_COLORS['warning'],
            },
        ]

        for ax, kpi in zip(axes, kpi_data):
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 10)
            ax.axis('off')

            card = FancyBboxPatch(
                (0.3, 0.3), 9.4, 9.4,
                boxstyle="round,pad=0.3",
                facecolor=kpi['color'], edgecolor='white', linewidth=3
            )
            ax.add_patch(card)

            ax.text(5, 6.8, kpi['label'],
                    ha='center', va='center', fontsize=14, fontweight='bold',
                    color='white', alpha=0.85)

            # Adjust font size for text values that may be long
            val_fontsize = 42 if len(kpi['value']) <= 6 else 28
            ax.text(5, 4.5, kpi['value'],
                    ha='center', va='center', fontsize=val_fontsize,
                    fontweight='bold', color='white',
                    path_effects=[pe.withStroke(linewidth=2,
                                                foreground=kpi['color'])])
            ax.text(5, 2.3, kpi['sub'],
                    ha='center', va='center', fontsize=11,
                    color='white', alpha=0.8, style='italic')

        fig.suptitle("Segment Migration Overview",
                     fontsize=28, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
        fig.text(0.5, GEN_SUBTITLE_Y,
                 f"First vs. last segmentation wave  ({DATASET_LABEL})",
                 ha='center', fontsize=13,
                 color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.show()
