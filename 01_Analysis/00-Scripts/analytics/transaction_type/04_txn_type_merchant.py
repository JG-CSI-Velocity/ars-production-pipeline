# ===========================================================================
# TXN TYPE MERCHANT: PIN Preference by Merchant (Conference Edition)
# ===========================================================================
# Diverging bar: top 15 merchants by PIN preference (% PIN - 50% baseline). (14,7).

if 'PIN' in tt_merch_pivot.columns:
    # Compute PIN preference score: % PIN minus 50% baseline
    tt_merch_pref = tt_merch_pivot.copy()
    tt_merch_pref['pin_preference'] = tt_merch_pref['PIN'] - 50

    # Get top 15 merchants by txn volume that have meaningful split
    top_vol = combined_df['merchant_consolidated'].value_counts().head(50).index
    tt_merch_pref = tt_merch_pref[tt_merch_pref.index.isin(top_vol)]

    # Take top 8 PIN-heavy and top 7 SIG-heavy for balanced diverging bar
    pin_heavy = tt_merch_pref.nlargest(8, 'pin_preference')
    sig_heavy = tt_merch_pref.nsmallest(7, 'pin_preference')
    tt_diverging = pd.concat([pin_heavy, sig_heavy]).sort_values('pin_preference')

    fig, ax = plt.subplots(figsize=(14, 7))

    names = [n[:25] for n in tt_diverging.index]
    values = tt_diverging['pin_preference'].values
    colors = [GEN_COLORS['success'] if v >= 0 else GEN_COLORS['warning'] for v in values]

    y_pos = range(len(tt_diverging))
    ax.barh(y_pos, values, color=colors, edgecolor='white', linewidth=0.5, height=0.7)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=10, fontweight='bold')
    ax.axvline(x=0, color=GEN_COLORS['dark_text'], linewidth=1.5, zorder=5)

    ax.set_xlabel("PIN Preference (% PIN - 50% baseline)", fontsize=13, fontweight='bold', labelpad=8)
    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Value labels
    for j, (val, name) in enumerate(zip(values, names)):
        pin_actual = tt_diverging['PIN'].iloc[j]
        offset = 1 if val >= 0 else -1
        ha = 'left' if val >= 0 else 'right'
        ax.text(val + offset, j, f"{pin_actual:.0f}% PIN",
                va='center', fontsize=9, fontweight='bold',
                color=GEN_COLORS['success'] if val >= 0 else GEN_COLORS['warning'],
                ha=ha)

    # Legend annotation
    ax.text(0.98, 0.05,
            "PIN-heavy merchants (teal) vs SIG-heavy (amber)",
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=11, fontweight='bold', color=GEN_COLORS['muted'],
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      edgecolor=GEN_COLORS['grid'], alpha=0.9))

    ax.set_title("Merchant PIN vs Signature Preference",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Which merchants skew PIN-debit vs signature?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
else:
    print("    PIN column not found in transaction type data. Skipping merchant preference chart.")
