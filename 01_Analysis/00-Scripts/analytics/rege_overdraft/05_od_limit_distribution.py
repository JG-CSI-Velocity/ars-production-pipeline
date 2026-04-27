# ===========================================================================
# OD LIMIT DISTRIBUTION: Current Overdraft Limit Amounts
# ===========================================================================
# Histogram + bar chart showing the distribution of OD limits across
# opted-in accounts. Helps identify limit concentration bands.

# ---------------------------------------------------------------------------
# Prepare data: current OD limits for all accounts
# ---------------------------------------------------------------------------
_od_data = rege_df[['account_number', 'current_od_limit', 'current_status']].copy()
_od_data['current_od_limit'] = pd.to_numeric(_od_data['current_od_limit'], errors='coerce')

# Classify into OD limit bands
def _classify_od_band(limit):
    """Assign an OD limit to a named band."""
    if pd.isna(limit) or limit <= 0:
        return '$0'
    elif limit <= 100:
        return '$1-100'
    elif limit <= 500:
        return '$100-500'
    elif limit <= 1000:
        return '$500-1K'
    else:
        return '$1K+'

_od_data['od_band'] = _od_data['current_od_limit'].apply(_classify_od_band)

# Count by band
_band_counts = (
    _od_data
    .groupby('od_band')['account_number']
    .nunique()
    .reindex(OD_LIMIT_BANDS, fill_value=0)
    .reset_index()
)
_band_counts.columns = ['od_band', 'accounts']
_band_counts['pct'] = (_band_counts['accounts'] / _band_counts['accounts'].sum() * 100)

# ---------------------------------------------------------------------------
# Plot: 2-panel (histogram + band bar chart)
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7), gridspec_kw={'width_ratios': [1.2, 1]})

# Panel 1: Histogram of raw OD limit values (exclude zeros for readability)
_nonzero = _od_data['current_od_limit'].dropna()
_nonzero_positive = _nonzero[_nonzero > 0]

if len(_nonzero_positive) > 0:
    _max_limit = _nonzero_positive.quantile(0.98)
    _bins = np.linspace(0, _max_limit, 30)

    ax1.hist(
        _nonzero_positive.clip(upper=_max_limit),
        bins=_bins, color=GEN_COLORS['info'], edgecolor='white',
        linewidth=1.5, alpha=0.85
    )

    # Mark mean and median
    _mean_val = _nonzero_positive.mean()
    _median_val = _nonzero_positive.median()
    ax1.axvline(_mean_val, color=GEN_COLORS['accent'], linewidth=2.5,
                linestyle='--', label=f'Mean: {gen_fmt_dollar(_mean_val, None)}')
    ax1.axvline(_median_val, color=GEN_COLORS['success'], linewidth=2.5,
                linestyle='-.', label=f'Median: {gen_fmt_dollar(_median_val, None)}')
    ax1.legend(loc='upper right', fontsize=12)
else:
    ax1.text(0.5, 0.5, "No non-zero OD limits found",
             transform=ax1.transAxes, fontsize=16, ha='center', va='center',
             color=GEN_COLORS['muted'])

ax1.set_xlabel("OD Limit Amount", fontsize=14, fontweight='bold')
ax1.set_ylabel("Number of Accounts", fontsize=14, fontweight='bold')
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_dollar))
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))
gen_clean_axes(ax1)
ax1.set_title("OD Limit Distribution (Non-Zero)", fontsize=18,
              fontweight='bold', loc='left', color=GEN_COLORS['dark_text'])

# Panel 2: Bar chart by OD limit band
_colors = [OD_LIMIT_PALETTE[i] for i in range(len(OD_LIMIT_BANDS))]
_bars = ax2.bar(
    _band_counts['od_band'], _band_counts['accounts'],
    color=_colors, edgecolor='white', linewidth=1.5
)

# Data labels
for bar, pct in zip(_bars, _band_counts['pct']):
    _height = bar.get_height()
    if _height > 0:
        ax2.text(
            bar.get_x() + bar.get_width() / 2, _height + (_band_counts['accounts'].max() * 0.02),
            f"{int(_height):,}\n({pct:.1f}%)",
            ha='center', va='bottom', fontsize=12, fontweight='bold',
            color=GEN_COLORS['dark_text']
        )

ax2.set_xlabel("OD Limit Band", fontsize=14, fontweight='bold')
ax2.set_ylabel("Number of Accounts", fontsize=14, fontweight='bold')
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))
gen_clean_axes(ax2)
ax2.set_title("Accounts by OD Limit Band", fontsize=18,
              fontweight='bold', loc='left', color=GEN_COLORS['dark_text'])

fig.suptitle("Overdraft Limit Distribution",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.5, 0.99,
         f"Current OD limit amounts across all accounts | {DATASET_LABEL}",
         fontsize=14, color=GEN_COLORS['muted'], style='italic',
         ha='center')

plt.tight_layout()
plt.show()

# Summary
_zero_od = len(_od_data[_od_data['current_od_limit'].fillna(0) <= 0])
print(f"\n    INSIGHT: {_zero_od:,} accounts have $0 or no OD limit")
for _, row in _band_counts.iterrows():
    print(f"      {row['od_band']:>10s}: {row['accounts']:>6,} accounts ({row['pct']:.1f}%)")
