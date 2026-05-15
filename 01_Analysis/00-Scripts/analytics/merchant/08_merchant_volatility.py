# ===========================================================================
# MERCHANT VOLATILITY: Consistent vs Volatile Spenders (Conference Edition)
# ===========================================================================
# Dual panel: top 10 most consistent + top 10 most volatile (by CV). (14,7).

if len(consistency_df) > 0:
    most_consistent = consistency_df.nsmallest(10, 'cv').copy()
    most_volatile = consistency_df.nlargest(10, 'cv').copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # --- LEFT: Most consistent (low CV) ---
    con_plot = most_consistent.sort_values('cv', ascending=False)
    ax1.barh(range(len(con_plot)), con_plot['cv'],
             color=GEN_COLORS['info'], edgecolor='white', linewidth=0.5, height=0.6)
    ax1.set_yticks(range(len(con_plot)))
    # astype(str) guards against categorical dtype (txn_wrapper optimizes
    # merchant_consolidated to category for memory), NaN values, and the
    # long-string edge case that blew up with a bogus figsize width in
    # matplotlib's text metrics. Same defensive cast used in payroll/05.
    ax1.set_yticklabels(
        con_plot['merchant_consolidated'].astype(str).str[:25],
        fontsize=11, fontweight='bold',
    )
    ax1.set_xlabel("CV %  (lower = more stable)", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Most Consistent", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['info'], pad=12)

    for j, (_, row) in enumerate(con_plot.iterrows()):
        ax1.text(row['cv'] + 1, j, f"{row['cv']:.0f}%",
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['info'])

    # --- RIGHT: Most volatile (high CV) ---
    # CV already capped at 500% in 01_merchant_data; display cap at 300% for readability
    vol_plot = most_volatile.sort_values('cv', ascending=True).copy()
    vol_plot['cv_display'] = vol_plot['cv'].clip(upper=300)

    ax2.barh(range(len(vol_plot)), vol_plot['cv_display'],
             color=GEN_COLORS['warning'], edgecolor='white', linewidth=0.5, height=0.6)
    ax2.set_yticks(range(len(vol_plot)))
    ax2.set_yticklabels(
        vol_plot['merchant_consolidated'].astype(str).str[:25],
        fontsize=11, fontweight='bold',
    )
    ax2.set_xlabel("CV %  (higher = more volatile)", fontsize=13, fontweight='bold', labelpad=8)
    ax2.set_xlim(0, 350)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Most Volatile", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['warning'], pad=12)

    for j, (_, row) in enumerate(vol_plot.iterrows()):
        label = f"{row['cv']:.0f}%"
        x_pos = min(row['cv_display'], 300) + 5
        ax2.text(x_pos, j, label,
                 va='center', fontsize=10, fontweight='bold', color=GEN_COLORS['warning'])

    # Place suptitle INSIDE the figure (y=0.99) rather than above the frame
    # (y=1.04). Combined with tight_layout() + subplots_adjust(top=0.88),
    # the old above-frame placement created a negative inner height that
    # matplotlib's text-metric pipeline occasionally translated into a
    # wildly overflowed width (the ``width=16345162437324666'' crash we
    # saw in merchant_08 during a 1776 run). Keeping all layout directives
    # within the [0, 1] figure coord space prevents the overflow.
    fig.suptitle("Merchant Spend Consistency",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=0.99)
    fig.text(0.5, 0.93, "Coefficient of variation: stable vs spiky merchants ($10K+ spend, 3+ months, CV capped at 500%)",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    # Reserve headroom for the title via subplots_adjust ONLY -- don't
    # also call tight_layout, which can undo the reservation and produce
    # the conflicting-layout crash above.
    plt.subplots_adjust(top=0.86, bottom=0.08, left=0.15, right=0.97, wspace=0.45)
    plt.show()

    # Summary
    median_cv = consistency_df['cv'].median()
    pct_stable = (consistency_df['cv'] < 50).sum() / len(consistency_df) * 100
    print(f"\n    Median CV: {median_cv:.0f}%")
    print(f"    Stable merchants (CV < 50%): {pct_stable:.0f}%")
else:
    print("No consistency data available.")
