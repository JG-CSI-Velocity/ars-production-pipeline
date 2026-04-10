# ===========================================================================
# BRACKET DONUT: Share of Transactions + Stats Panel (Conference Edition)
# ===========================================================================
# Donut left, bracket stats right. (14,7). No dollars.

fig = plt.figure(figsize=(14, 7))
gs = GridSpec(1, 2, width_ratios=[1, 1.1], wspace=0.05)

# --- LEFT: Donut ---
ax_donut = fig.add_subplot(gs[0])

wedges, texts, autotexts = ax_donut.pie(
    bracket_df['txn_count'],
    labels=None,
    autopct='%1.0f%%',
    colors=BRACKET_PALETTE,
    startangle=90,
    pctdistance=0.78,
    wedgeprops=dict(width=0.45, edgecolor='white', linewidth=3)
)

for t in autotexts:
    t.set_fontsize(14)
    t.set_fontweight('bold')
    t.set_color('white')
    t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

# Center label
ax_donut.text(0, 0, f"{bracket_df['txn_count'].sum():,.0f}\nTransactions",
              ha='center', va='center',
              fontsize=18, fontweight='bold',
              color=GEN_COLORS['dark_text'], linespacing=1.5)

ax_donut.set_title("Transaction Share\nby Bracket",
                    fontsize=22, fontweight='bold',
                    color=GEN_COLORS['dark_text'], pad=15)

# --- RIGHT: Bracket stats ---
ax_stats = fig.add_subplot(gs[1])
ax_stats.axis('off')

y_start = 0.92
y_step = 0.115

for i, (_, row) in enumerate(bracket_df.iterrows()):
    y_pos = y_start - (i * y_step)
    color = BRACKET_PALETTE[i]

    # Color dot
    ax_stats.plot(0.02, y_pos, 'o', markersize=14, color=color,
                  transform=ax_stats.transAxes, clip_on=False)

    # Bracket name
    ax_stats.text(0.08, y_pos, row['bracket'], transform=ax_stats.transAxes,
                  fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'],
                  va='center')

    # Stats line
    stats_text = (
        f"{row['txn_count']:,.0f} txn   |   "
        f"{row['account_count']:,.0f} accounts   |   "
        f"{row['txn_pct']:.1f}%"
    )
    ax_stats.text(0.08, y_pos - 0.04, stats_text,
                  transform=ax_stats.transAxes,
                  fontsize=12, color=GEN_COLORS['muted'], va='center')

fig.suptitle("Spending Bracket Breakdown",
             fontsize=28, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=1.02)

plt.tight_layout()
plt.show()
