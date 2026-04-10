# ===========================================================================
# ICS MERCHANT PREFERENCES: REF vs DM Top Merchants (Conference Edition)
# ===========================================================================
# Two-panel: Top 10 merchants for REF vs DM. (14,7).

if 'ics_agg' not in dir() or len(ics_agg) == 0:
    print("    No ICS data available. Skipping merchant preferences.")
else:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    # --- LEFT: REF top merchants ---
    if len(ics_ref_df) > 0:
        ref_top = ics_ref_df['merchant_consolidated'].value_counts().head(10)
        ref_pct = ref_top / len(ics_ref_df) * 100
        ref_names = [m[:22] for m in ref_pct.index]
        ref_pct_sorted = ref_pct.sort_values()

        ax1.barh(range(len(ref_pct_sorted)), ref_pct_sorted.values,
                 color=GEN_COLORS['info'], edgecolor='white', linewidth=0.5, height=0.65)
        ax1.set_yticks(range(len(ref_pct_sorted)))
        ax1.set_yticklabels([m[:22] for m in ref_pct_sorted.index], fontsize=10, fontweight='bold')
        for j, val in enumerate(ref_pct_sorted.values):
            ax1.text(val + 0.1, j, f"{val:.1f}%", va='center', fontsize=9,
                     fontweight='bold', color=GEN_COLORS['info'])
    else:
        ax1.text(0.5, 0.5, "No REF data", ha='center', va='center',
                 fontsize=14, color=GEN_COLORS['muted'], transform=ax1.transAxes)

    ax1.set_xlabel("% of REF Transactions", fontsize=12, fontweight='bold', labelpad=8)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)
    ax1.set_title("Referral (REF) Accounts", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['info'], pad=12)

    # --- RIGHT: DM top merchants ---
    if len(ics_dm_df) > 0:
        dm_top = ics_dm_df['merchant_consolidated'].value_counts().head(10)
        dm_pct = dm_top / len(ics_dm_df) * 100
        dm_pct_sorted = dm_pct.sort_values()

        ax2.barh(range(len(dm_pct_sorted)), dm_pct_sorted.values,
                 color=GEN_COLORS['primary'], edgecolor='white', linewidth=0.5, height=0.65)
        ax2.set_yticks(range(len(dm_pct_sorted)))
        ax2.set_yticklabels([m[:22] for m in dm_pct_sorted.index], fontsize=10, fontweight='bold')
        for j, val in enumerate(dm_pct_sorted.values):
            ax2.text(val + 0.1, j, f"{val:.1f}%", va='center', fontsize=9,
                     fontweight='bold', color=GEN_COLORS['primary'])
    else:
        ax2.text(0.5, 0.5, "No DM data", ha='center', va='center',
                 fontsize=14, color=GEN_COLORS['muted'], transform=ax2.transAxes)

    ax2.set_xlabel("% of DM Transactions", fontsize=12, fontweight='bold', labelpad=8)
    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.set_title("Direct Mail (DM) Accounts", fontsize=20, fontweight='bold',
                   color=GEN_COLORS['primary'], pad=12)

    fig.suptitle("ICS Merchant Preferences by Channel",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=1.04)
    fig.text(0.5, 0.96,
             f"Do referral and direct mail members shop at different merchants?  ({DATASET_LABEL})",
             ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)
    plt.show()
