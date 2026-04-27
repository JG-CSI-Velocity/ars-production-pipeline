# ===========================================================================
# BUSINESS VOLATILITY: Consistent vs Volatile Spenders (Conference Edition)
# ===========================================================================
# Dual panel: top 10 most consistent + top 10 most volatile (by CV). (14,7).

if 'biz_consistency_df' not in dir() or len(biz_consistency_df) == 0:
    print("    No business consistency data available. Skipping volatility chart.")
else:
    most_consistent_b = biz_consistency_df.nsmallest(10, 'cv').copy()
    most_volatile_b = biz_consistency_df.nlargest(10, 'cv').copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # --- LEFT: Most consistent (low CV) ---
    con_plot_b = most_consistent_b.sort_values('cv', ascending=False)
    ax1.barh(range(len(con_plot_b)), con_plot_b['cv'],
             color=GEN_COLORS['info'], edgecolor='white', linewidth=0.5, height=0.6)
    ax1.set_yticks(range(len(con_plot_b)))
    ax1.set_yticklabels(con_plot_b['merchant_consolidated'].str[:25], fontsize=11, fontweight='bold')
    ax1.set_xlabel("CV %  (lower = more stable)", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Most Consistent", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['info'], pad=12)

    for j, (_, row) in enumerate(con_plot_b.iterrows()):
        ax1.text(row['cv'] + 1, j, f"{row['cv']:.0f}%",
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['info'])

    # --- RIGHT: Most volatile (high CV) ---
    vol_plot_b = most_volatile_b.sort_values('cv', ascending=True).copy()
    vol_plot_b['cv_display'] = vol_plot_b['cv'].clip(upper=300)

    ax2.barh(range(len(vol_plot_b)), vol_plot_b['cv_display'],
             color=GEN_COLORS['warning'], edgecolor='white', linewidth=0.5, height=0.6)
    ax2.set_yticks(range(len(vol_plot_b)))
    ax2.set_yticklabels(vol_plot_b['merchant_consolidated'].str[:25], fontsize=11, fontweight='bold')
    ax2.set_xlabel("CV %  (higher = more volatile)", fontsize=13, fontweight='bold', labelpad=8)
    ax2.set_xlim(0, 350)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Most Volatile", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['warning'], pad=12)

    for j, (_, row) in enumerate(vol_plot_b.iterrows()):
        label = f"{row['cv']:.0f}%"
        x_pos = min(row['cv_display'], 300) + 5
        ax2.text(x_pos, j, label,
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['warning'])

    fig.suptitle("Business Merchant Spend Consistency",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, GEN_SUBTITLE_Y, "Stable vs spiky business merchants ($10K+ spend, 3+ months, CV capped at 500%)",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()

    median_cv_b = biz_consistency_df['cv'].median()
    pct_stable_b = (biz_consistency_df['cv'] < 50).sum() / len(biz_consistency_df) * 100
    print(f"\n    Median CV: {median_cv_b:.0f}%")
    print(f"    Stable business merchants (CV < 50%): {pct_stable_b:.0f}%")
