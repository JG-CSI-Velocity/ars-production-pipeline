# ===========================================================================
# BUSINESS vs PERSONAL: Who Is Leaking?
# ===========================================================================

all_finserv_trans = pd.concat(
    [d['transactions'] for d in financial_services_data.values()],
    ignore_index=True
)

if 'business_flag' in all_finserv_trans.columns:
    biz_split = all_finserv_trans.groupby('business_flag').agg({
        'amount': 'count',
        'primary_account_num': 'nunique'
    })
    biz_split.columns = ['transactions', 'accounts']
    biz_split.index = biz_split.index.map({'Yes': 'Business', 'No': 'Personal'})

    biz_colors = {'Business': GEN_COLORS['primary'], 'Personal': GEN_COLORS['success']}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    for ax, metric, title in [(ax1, 'transactions', 'Transaction Split'),
                               (ax2, 'accounts', 'Account Split')]:
        wedges, _, autotexts = ax.pie(
            biz_split[metric], labels=None, autopct='%1.0f%%',
            colors=[biz_colors.get(c, GEN_COLORS['muted']) for c in biz_split.index],
            startangle=90, pctdistance=0.78,
            wedgeprops=dict(width=0.42, edgecolor='white', linewidth=3)
        )
        for t in autotexts:
            t.set_fontsize(22)
            t.set_fontweight('bold')
            t.set_color('white')
            t.set_path_effects([pe.withStroke(linewidth=2, foreground='#333333')])

        total = biz_split[metric].sum()
        ax.text(0, 0, f"{total:,.0f}\n{metric.title()}",
                ha='center', va='center', fontsize=16, fontweight='bold',
                color=GEN_COLORS['dark_text'], linespacing=1.5)
        ax.set_title(title, fontsize=22, fontweight='bold',
                      color=GEN_COLORS['dark_text'], pad=15)

    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, fc=biz_colors[lbl], edgecolor='white',
                       linewidth=1.5, label=lbl)
        for lbl in biz_split.index
    ]
    fig.legend(handles=legend_handles, loc='upper center', bbox_to_anchor=(0.5, 0.02),
               ncol=2, fontsize=16, frameon=False, columnspacing=3.0)

    fig.suptitle("Business vs Personal Leakage",
                 fontsize=28, fontweight='bold', color=GEN_COLORS['dark_text'], y=1.02)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)
    plt.show()

    biz_pct = biz_split.loc['Business', 'accounts'] / biz_split['accounts'].sum() * 100
    if biz_pct > 20:
        print(f"\n    OPPORTUNITY: Business accounts represent {biz_pct:.0f}% of external FinServ leakage.")
        print("    These are high-value relationships -- prioritize commercial product offers.")
else:
    print("No business_flag column available. Skipping Business vs Personal analysis.")
