# ===========================================================================
# TOP MERCHANTS: Who Is Draining Your Account Holders?
# ===========================================================================
# Specific merchant names, not categories. The "name and shame" chart.

all_merchant_data = []
search_col = 'merchant_consolidated' if 'merchant_consolidated' in combined_df.columns else 'merchant_name'

for category, data in financial_services_data.items():
    ms = data['merchant_summary'].reset_index()
    ms.columns = ['merchant', 'total_spend', 'transactions', 'unique_accounts']
    ms['category'] = category
    all_merchant_data.append(ms)

if len(all_merchant_data) > 0:
    merchants_df = pd.concat(all_merchant_data, ignore_index=True)
    top_merchants = merchants_df.sort_values('unique_accounts', ascending=False).head(15)

    fig, ax = plt.subplots(figsize=(14, 9))

    plot_data = top_merchants.iloc[::-1]
    colors = [fs_get_color(c) for c in plot_data['category']]

    bars = ax.barh(
        range(len(plot_data)), plot_data['unique_accounts'],
        color=colors, edgecolor='white', linewidth=1, height=0.7, zorder=3
    )

    for i, (_, row) in enumerate(plot_data.iterrows()):
        name = row['merchant']
        if len(str(name)) > 30:
            name = str(name)[:28] + '..'
        ax.text(
            row['unique_accounts'] * 1.01, i,
            f"{row['unique_accounts']:,.0f} accounts  ({row['transactions']:,.0f} txn)",
            fontsize=12, fontweight='bold', color=GEN_COLORS['dark_text'], va='center'
        )

    ax.set_yticks(range(len(plot_data)))
    labels = [str(m)[:30] + '..' if len(str(m)) > 32 else str(m) for m in plot_data['merchant']]
    ax.set_yticklabels(labels, fontsize=12, fontweight='bold')
    ax.set_xlabel("Unique Accounts", fontsize=18, fontweight='bold', labelpad=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

    gen_clean_axes(ax)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    ax.set_xlim(0, plot_data['unique_accounts'].max() * 1.40)

    ax.set_title("Top 15 External Merchants by Account Holder Reach",
                 fontsize=26, fontweight='bold', color=GEN_COLORS['dark_text'], pad=20, loc='left')
    ax.text(0.0, 0.97, "These specific companies have the most relationships with your account holders",
            transform=ax.transAxes, fontsize=15, color=GEN_COLORS['muted'], style='italic')

    # Category legend
    legend_cats = top_merchants['category'].unique()
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, fc=fs_get_color(c), edgecolor='white',
                       linewidth=1, label=c) for c in legend_cats
    ]
    ax.legend(handles=legend_handles, loc='lower right', fontsize=12, frameon=False)

    plt.tight_layout()
    plt.show()

    # Opportunity callout
    top1 = top_merchants.iloc[0]
    print(f"\n    INSIGHT: {top1['merchant']} alone has {int(top1['unique_accounts']):,} of your account holders.")
    print(f"    The top 5 merchants account for {top_merchants.head(5)['unique_accounts'].sum():,} account holder relationships.")
