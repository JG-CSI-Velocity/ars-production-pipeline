# ===========================================================================
# TXN TYPE SPLIT: PIN vs SIG Donut (Conference Edition)
# ===========================================================================
# Two side-by-side donuts: by txn count and by spend. (14,7).

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

# Color map for transaction types
TT_COLORS = {
    'PIN': GEN_COLORS['success'],
    'SIG': GEN_COLORS['warning'],
}
default_tt_colors = [GEN_COLORS['info'], GEN_COLORS['muted'], GEN_COLORS['accent']]

def get_tt_color(ttype, idx):
    return TT_COLORS.get(ttype, default_tt_colors[idx % len(default_tt_colors)])

# --- LEFT: By transaction count ---
types_count = tt_agg.sort_values('txn_count', ascending=False)
colors_count = [get_tt_color(t, i) for i, t in enumerate(types_count['transaction_type'])]

wedges1, texts1, autotexts1 = ax1.pie(
    types_count['txn_count'],
    labels=types_count['transaction_type'],
    colors=colors_count,
    autopct='%1.1f%%',
    startangle=90,
    pctdistance=0.75,
    wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
    textprops={'fontsize': 13, 'fontweight': 'bold'},
)
for t in autotexts1:
    t.set_fontsize(12)
    t.set_fontweight('bold')
    t.set_color('white')

centre1 = plt.Circle((0, 0), 0.55, fc='white')
ax1.add_artist(centre1)
ax1.text(0, 0.05, f"{total_txns_tt:,}", ha='center', va='center',
         fontsize=20, fontweight='bold', color=GEN_COLORS['dark_text'])
ax1.text(0, -0.12, "transactions", ha='center', va='center',
         fontsize=11, color=GEN_COLORS['muted'])
ax1.set_title("By Transaction Count", fontsize=18, fontweight='bold',
              color=GEN_COLORS['dark_text'], pad=15)

# --- RIGHT: By spend ---
types_spend = tt_agg.sort_values('total_spend', ascending=False)
colors_spend = [get_tt_color(t, i) for i, t in enumerate(types_spend['transaction_type'])]

wedges2, texts2, autotexts2 = ax2.pie(
    types_spend['total_spend'],
    labels=types_spend['transaction_type'],
    colors=colors_spend,
    autopct='%1.1f%%',
    startangle=90,
    pctdistance=0.75,
    wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
    textprops={'fontsize': 13, 'fontweight': 'bold'},
)
for t in autotexts2:
    t.set_fontsize(12)
    t.set_fontweight('bold')
    t.set_color('white')

centre2 = plt.Circle((0, 0), 0.55, fc='white')
ax2.add_artist(centre2)
total_spend_tt = tt_agg['total_spend'].sum()
ax2.text(0, 0.05, f"${total_spend_tt/1e6:.1f}M", ha='center', va='center',
         fontsize=20, fontweight='bold', color=GEN_COLORS['dark_text'])
ax2.text(0, -0.12, "total spend", ha='center', va='center',
         fontsize=11, color=GEN_COLORS['muted'])
ax2.set_title("By Spend Volume", fontsize=18, fontweight='bold',
              color=GEN_COLORS['dark_text'], pad=15)

fig.suptitle("Transaction Type Distribution",
             fontsize=26, fontweight='bold',
             color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
fig.text(0.5, GEN_SUBTITLE_Y, "How does card volume split between PIN and signature?",
         ha='center', fontsize=13, color=GEN_COLORS['muted'], style='italic')

plt.tight_layout()
plt.subplots_adjust(top=0.88)
plt.show()
