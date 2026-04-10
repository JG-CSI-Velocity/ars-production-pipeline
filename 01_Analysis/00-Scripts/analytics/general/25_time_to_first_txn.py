# ===========================================================================
# TIME TO FIRST TRANSACTION: Activation Speed (Conference Edition)
# ===========================================================================
# Box plot of days-to-first-txn -- TTM accounts only (opened <12mo). (14,7).
# Older accounts excluded: we lack their historical transaction data.

# Filter to TTM accounts with valid days_to_first_txn
ttf_data = lifecycle_matched[
    lifecycle_matched['is_ttm'] &
    lifecycle_matched['days_to_first_txn'].notna()
].copy()

TTM_BANDS = ['1-90d', '91-180d', '181-365d']
ttf_data = ttf_data[ttf_data['acct_age_band'].isin(TTM_BANDS)]
ttf_data['acct_age_band'] = pd.Categorical(
    ttf_data['acct_age_band'], categories=TTM_BANDS, ordered=True
)

fig, ax = plt.subplots(figsize=(16, 8))

bands_present = [b for b in TTM_BANDS if b in ttf_data['acct_age_band'].values]
box_data = [ttf_data[ttf_data['acct_age_band'] == b]['days_to_first_txn'].dropna().values
            for b in bands_present]
box_colors = [ACCT_AGE_PALETTE.get(b, GEN_COLORS['muted']) for b in bands_present]

if len(box_data) > 0 and any(len(d) > 0 for d in box_data):
    bp = ax.boxplot(
        box_data, vert=True, patch_artist=True, widths=0.6,
        medianprops=dict(color='white', linewidth=2.5),
        whiskerprops=dict(color=GEN_COLORS['muted'], linewidth=1.5),
        capprops=dict(color=GEN_COLORS['muted'], linewidth=1.5),
        flierprops=dict(marker='o', markerfacecolor=GEN_COLORS['muted'],
                        markersize=3, alpha=0.3),
    )

    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('white')
        patch.set_linewidth(1.5)
        patch.set_alpha(0.85)

    ax.set_xticklabels(bands_present, fontsize=16, fontweight='bold')
    ax.set_ylabel("Days to First Transaction", fontsize=18, fontweight='bold', labelpad=10)
    ax.set_xlabel("Account Age Band (TTM Only)", fontsize=18, fontweight='bold', labelpad=10)

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Per-band stats -- positioned above each box with white background
    for i, band in enumerate(bands_present):
        band_data = ttf_data[ttf_data['acct_age_band'] == band]['days_to_first_txn']
        if len(band_data) > 0:
            med = band_data.median()
            n = len(band_data)
            pct_30 = (band_data <= 30).sum() / len(band_data) * 100
            # Place label above the upper whisker
            upper_whisker = bp['whiskers'][i * 2 + 1].get_ydata().max()
            ax.text(i + 1, upper_whisker + (ax.get_ylim()[1] * 0.03),
                    f"Median: {med:.0f}d\n{pct_30:.0f}% < 30d\nn = {n:,}",
                    fontsize=14, fontweight='bold',
                    color=GEN_COLORS['dark_text'],
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor=ACCT_AGE_PALETTE.get(band, GEN_COLORS['muted']),
                              linewidth=1.5, alpha=0.95))

    # Overall TTM callout
    overall_median = ttf_data['days_to_first_txn'].median()
    pct_within_30 = (ttf_data['days_to_first_txn'] <= 30).sum() / len(ttf_data) * 100

    ax.text(
        0.99, 0.95,
        f"All TTM: Median {overall_median:.0f} days | {pct_within_30:.0f}% within 30 days",
        transform=ax.transAxes,
        fontsize=16, fontweight='bold', color=GEN_COLORS['info'],
        ha='right', va='top',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor=GEN_COLORS['info'], alpha=0.9)
    )

    # Legend for box colors
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1,
                       fc=ACCT_AGE_PALETTE.get(b, GEN_COLORS['muted']),
                       edgecolor='white', linewidth=1.5, alpha=0.85,
                       label=f"{b} ({len(ttf_data[ttf_data['acct_age_band'] == b]):,} accounts)")
        for b in bands_present
    ]
    ax.legend(
        handles=legend_handles,
        loc='upper center', bbox_to_anchor=(0.5, -0.10),
        ncol=3, fontsize=15, frameon=False,
        title='Account Age Band', title_fontproperties={'weight': 'bold', 'size': 16}
    )

ax.set_title("How Quickly Do New Accounts Activate?",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], pad=35, loc='left')
ax.text(0.0, 1.02, "Trailing 12 months only -- older accounts lack historical transaction data",
        transform=ax.transAxes, fontsize=16,
        color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.subplots_adjust(bottom=0.14)
plt.show()
