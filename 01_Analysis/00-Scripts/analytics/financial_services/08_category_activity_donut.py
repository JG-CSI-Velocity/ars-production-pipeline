# ===========================================================================
# ACTIVITY SHARE: Donut + Stats
# ===========================================================================
# Groups smallest categories into "Other" if more than 10 categories detected,
# keeping the donut readable at any category count.

cat_data = finserv_summary_df.sort_values('total_transactions', ascending=False).copy()

# Group small categories into "Other" for donut readability
_MAX_DONUT_SLICES = 10
if len(cat_data) > _MAX_DONUT_SLICES:
    _top = cat_data.head(_MAX_DONUT_SLICES - 1)
    _rest = cat_data.iloc[_MAX_DONUT_SLICES - 1:]
    _other_row = pd.DataFrame([{
        'category': f'Other ({len(_rest)} categories)',
        'unique_accounts': _rest['unique_accounts'].sum(),
        'total_transactions': _rest['total_transactions'].sum(),
        'unique_merchants': _rest['unique_merchants'].sum(),
    }])
    donut_data = pd.concat([_top, _other_row], ignore_index=True)
else:
    donut_data = cat_data

fig = plt.figure(figsize=(18, max(9, len(cat_data) * 0.55)))
gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

# --- LEFT: Donut ---
ax_donut = fig.add_subplot(gs[0])
colors = [fs_get_color(c) if not c.startswith('Other (') else GEN_COLORS['muted']
          for c in donut_data['category']]

wedges, texts, autotexts = ax_donut.pie(
    donut_data['total_transactions'],
    labels=None, autopct=lambda p: f'{p:.0f}%' if p >= 3 else '',
    colors=colors,
    startangle=90, pctdistance=0.78,
    wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3)
)
for t in autotexts:
    t.set_fontsize(14)
    t.set_fontweight('bold')
    t.set_color('white')
    t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

total_txn = cat_data['total_transactions'].sum()
ax_donut.text(0, 0, f"{total_txn:,.0f}\nTransactions",
              ha='center', va='center', fontsize=17, fontweight='bold',
              color=GEN_COLORS['dark_text'], linespacing=1.5)
ax_donut.set_title("Transaction Share\nby Category", fontsize=22,
                    fontweight='bold', color=GEN_COLORS['dark_text'], pad=15)

# --- RIGHT: Full category stats (all categories, scaled font) ---
ax_stats = fig.add_subplot(gs[1])
ax_stats.axis('off')

_n_cats = len(cat_data)
_font_main = max(11, min(16, 22 - _n_cats // 2))
_font_sub = max(9, _font_main - 3)
_marker_size = max(8, min(14, 18 - _n_cats // 2))

y_start = 0.95
y_step = 0.90 / max(_n_cats, 1)

for i, (_, row) in enumerate(cat_data.iterrows()):
    y_pos = y_start - (i * y_step)
    color = fs_get_color(row['category'])

    ax_stats.plot(0.02, y_pos, 'o', markersize=_marker_size, color=color,
                  transform=ax_stats.transAxes, clip_on=False)
    ax_stats.text(0.07, y_pos, row['category'], transform=ax_stats.transAxes,
                  fontsize=_font_main, fontweight='bold', color=GEN_COLORS['dark_text'], va='center')
    stats_text = f"{row['total_transactions']:,.0f} txn  |  {row['unique_accounts']:,.0f} accounts"
    ax_stats.text(0.07, y_pos - 0.025, stats_text, transform=ax_stats.transAxes,
                  fontsize=_font_sub, color=GEN_COLORS['muted'], va='center')

fig.suptitle("External FinServ Activity Breakdown",
             fontsize=28, fontweight='bold', color=GEN_COLORS['dark_text'], y=0.98)

plt.tight_layout()
plt.show()
