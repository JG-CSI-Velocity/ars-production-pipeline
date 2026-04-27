# ===========================================================================
# MCC BY BUSINESS/PERSONAL: Category Differences (Conference Edition)
# ===========================================================================
# Side-by-side horizontal bars: top 10 MCCs for Business vs Personal. (14,7).

if 'mcc_code' not in combined_df.columns or combined_df['mcc_code'].notna().sum() == 0:
    print("    No MCC code data available. Skipping business/personal MCC split.")
elif 'business_flag' not in combined_df.columns:
    print("    No business_flag column found. Skipping business/personal MCC split.")
else:
    biz_mcc = combined_df[combined_df['business_flag'] == 'Yes']
    per_mcc = combined_df[combined_df['business_flag'] == 'No']

    if len(biz_mcc) == 0 or len(per_mcc) == 0:
        print("    Need both business and personal transactions for comparison. Skipping.")
    else:
        # Top 10 MCCs for each segment (by txn count)
        biz_top = biz_mcc.groupby('mcc_code').size().reset_index(name='txn_count')
        biz_total = len(biz_mcc)
        biz_top['pct'] = biz_top['txn_count'] / biz_total * 100
        biz_top = biz_top.sort_values('pct', ascending=False).head(10)

        per_top = per_mcc.groupby('mcc_code').size().reset_index(name='txn_count')
        per_total = len(per_mcc)
        per_top['pct'] = per_top['txn_count'] / per_total * 100
        per_top = per_top.sort_values('pct', ascending=False).head(10)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

        # --- LEFT: Business ---
        biz_plot = biz_top.sort_values('pct', ascending=True)
        ax1.barh(
            range(len(biz_plot)), biz_plot['pct'],
            color=GEN_COLORS['primary'], edgecolor='white', linewidth=0.5, height=0.7
        )
        ax1.set_yticks(range(len(biz_plot)))
        ax1.set_yticklabels(biz_plot['mcc_code'].astype(str), fontsize=13, fontweight='bold')
        ax1.set_xlabel("% of Business Transactions", fontsize=14, fontweight='bold', labelpad=8)
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
        ax1.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax1.set_axisbelow(True)
        ax1.set_title("Business Accounts", fontsize=20, fontweight='bold',
                       color=GEN_COLORS['primary'], pad=12)

        # Value labels
        for j, (_, row) in enumerate(biz_plot.iterrows()):
            ax1.text(row['pct'] + 0.3, j, f"{row['pct']:.1f}%",
                     va='center', fontsize=11, fontweight='bold', color=GEN_COLORS['primary'])

        # --- RIGHT: Personal ---
        per_plot = per_top.sort_values('pct', ascending=True)
        ax2.barh(
            range(len(per_plot)), per_plot['pct'],
            color=GEN_COLORS['success'], edgecolor='white', linewidth=0.5, height=0.7
        )
        ax2.set_yticks(range(len(per_plot)))
        ax2.set_yticklabels(per_plot['mcc_code'].astype(str), fontsize=13, fontweight='bold')
        ax2.set_xlabel("% of Personal Transactions", fontsize=14, fontweight='bold', labelpad=8)
        ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
        gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
        ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
        ax2.set_axisbelow(True)
        ax2.set_title("Personal Accounts", fontsize=20, fontweight='bold',
                       color=GEN_COLORS['success'], pad=12)

        for j, (_, row) in enumerate(per_plot.iterrows()):
            ax2.text(row['pct'] + 0.3, j, f"{row['pct']:.1f}%",
                     va='center', fontsize=11, fontweight='bold', color=GEN_COLORS['success'])

        fig.suptitle("Top MCC Categories: Business vs Personal",
                     fontsize=26, fontweight='bold',
                     color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
        fig.text(0.5, GEN_SUBTITLE_Y, "Do business and personal accounts use different merchant categories?",
                 ha='center', fontsize=15, color=GEN_COLORS['muted'], style='italic')

        plt.tight_layout()
        plt.subplots_adjust(top=0.88)
        plt.show()

        # Overlap callout
        biz_set = set(biz_top['mcc_code'].tolist())
        per_set = set(per_top['mcc_code'].tolist())
        overlap = biz_set & per_set
        only_biz = biz_set - per_set
        only_per = per_set - biz_set
        print(f"\n    Overlap: {len(overlap)} MCCs appear in both top 10")
        if only_biz:
            print(f"    Business-only: {', '.join(str(c) for c in sorted(only_biz))}")
        if only_per:
            print(f"    Personal-only: {', '.join(str(c) for c in sorted(only_per))}")
