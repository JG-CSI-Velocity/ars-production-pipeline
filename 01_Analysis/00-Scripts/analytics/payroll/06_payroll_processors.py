# ===========================================================================
# PAYROLL PROCESSORS: Top Sources of Payroll/Direct Deposit Detected
# ===========================================================================
# Horizontal bar chart showing which payroll processors and employers
# are routing deposits through this credit union.

fig, ax = plt.subplots(figsize=(14, 8))

# ---------------------------------------------------------------------------
# Aggregate by payroll source
# ---------------------------------------------------------------------------
if 'payroll_source' in combined_df.columns:
    source_agg = (
        combined_df[combined_df['payroll_detected']]
        .groupby('payroll_source')
        .agg(
            txn_count=('amount', 'count'),
            unique_accounts=('primary_account_num', 'nunique'),
            total_amount=('amount', 'sum'),
            avg_amount=('amount', 'mean'),
        )
        .reset_index()
        .sort_values('unique_accounts', ascending=True)
    )

    if len(source_agg) == 0:
        ax.text(0.5, 0.5, 'No payroll transactions detected',
                ha='center', va='center', fontsize=18,
                color=GEN_COLORS['muted'], transform=ax.transAxes)
        ax.axis('off')
        plt.show()
    else:
        # Limit to top 15 sources
        source_agg = source_agg.tail(15)

        # Color known processors differently from generic/pattern
        def color_source(name):
            known = ['ADP', 'PAYCHEX', 'GUSTO', 'CERIDIAN', 'WORKDAY',
                     'PAYLOCITY', 'PAYCOM', 'PAYCOR', 'INTUIT PAYROLL',
                     'QUICKBOOKS PAYROLL']
            if name in known:
                return GEN_COLORS['accent']
            elif name == 'Direct Deposit (Generic)':
                return GEN_COLORS['info']
            else:
                return GEN_COLORS['muted']

        bar_colors = [color_source(s) for s in source_agg['payroll_source']]

        bars = ax.barh(range(len(source_agg)), source_agg['unique_accounts'],
                       color=bar_colors, edgecolor='white', linewidth=1.5, zorder=3)

        # Value labels with account count and avg amount
        for i, (bar, row) in enumerate(zip(bars, source_agg.itertuples())):
            accts = row.unique_accounts
            avg_amt = row.avg_amount
            ax.text(bar.get_width() + max(source_agg['unique_accounts'].max() * 0.01, 1),
                    bar.get_y() + bar.get_height() / 2,
                    f"{accts:,} accts  |  avg ${avg_amt:,.0f}",
                    ha='left', va='center', fontsize=11,
                    fontweight='bold', color=GEN_COLORS['dark_text'])

        ax.set_yticks(range(len(source_agg)))
        # astype(str) before .str[] -- same defensive cast that 393cae2
        # applied to payroll/05, payroll/10, and merchant/08. payroll_source
        # is a groupby key whose dtype can be categorical (txn_wrapper memory
        # optimization), numeric (no detection ran, fallback values), or NaN,
        # any of which raise "Can only use .str accessor with string values!"
        # without the cast.
        ax.set_yticklabels(
            source_agg['payroll_source'].astype(str).str[:30],
            fontsize=12, fontweight='bold',
        )
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))

        # Legend
        from matplotlib.patches import Patch
        legend_items = [
            Patch(facecolor=GEN_COLORS['accent'], label='Known Processor'),
            Patch(facecolor=GEN_COLORS['info'], label='Generic Direct Deposit'),
            Patch(facecolor=GEN_COLORS['muted'], label='Pattern-Detected'),
        ]
        ax.legend(handles=legend_items, loc='lower right', fontsize=12)

        gen_clean_axes(ax)

        ax.set_title("Payroll Sources: Who Is Paying Your Members?",
                     fontsize=24, fontweight='bold', color=GEN_COLORS['dark_text'],
                     loc='left', pad=20)
        ax.text(0.0, 1.03,
                f"Employers and processors routing deposits here  --  {DATASET_LABEL}",
                fontsize=13, style='italic', color=GEN_COLORS['muted'],
                transform=ax.transAxes)

        plt.tight_layout()
        plt.show()

        # Summary stats
        total_pr_accts = source_agg['unique_accounts'].sum()
        known_processors = ['ADP', 'PAYCHEX', 'GUSTO', 'CERIDIAN', 'WORKDAY',
                           'PAYLOCITY', 'PAYCOM', 'PAYCOR', 'INTUIT PAYROLL',
                           'QUICKBOOKS PAYROLL']
        known_mask = source_agg['payroll_source'].isin(known_processors)
        known_accts = source_agg.loc[known_mask, 'unique_accounts'].sum()
        known_pct = known_accts / total_pr_accts * 100 if total_pr_accts > 0 else 0

        print(f"\n  {len(source_agg)} distinct payroll sources detected")
        print(f"  {known_accts:,} accounts ({known_pct:.1f}%) from known processors")
        print(f"  Top source: {source_agg.iloc[-1]['payroll_source']} "
              f"({source_agg.iloc[-1]['unique_accounts']:,} accounts)")
else:
    ax.text(0.5, 0.5, 'Payroll source data not available\n(run 01_payroll_data first)',
            ha='center', va='center', fontsize=18,
            color=GEN_COLORS['muted'], transform=ax.transAxes)
    ax.axis('off')
    plt.show()
