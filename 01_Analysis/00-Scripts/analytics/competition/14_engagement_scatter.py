# ===========================================================================
# SCATTER: Activity per Account vs Growth (Conference Edition)
# ===========================================================================
# Replaces comp-spend. No dollars. Uses transactions-per-account index.
# Strategic quadrant with median crosshairs.

def plot_activity_vs_growth(
    threat_df,
    title="Engagement Depth vs Growth",
    subtitle="Which competitors are deepening and accelerating?",
    top_n=10
):
    if threat_df is None or threat_df.empty:
        print("No threat data available.")
        return

    plot_df = (
        threat_df.copy()
        .sort_values('threat_score', ascending=False)
        .head(top_n)
    )

    # Transactions per account (engagement depth, no dollars)
    if 'total_transactions' in plot_df.columns:
        plot_df['txn_per_account'] = plot_df.apply(
            lambda r: r['total_transactions'] / r['unique_accounts']
            if r['unique_accounts'] > 0 else 0, axis=1
        )
    else:
        # Fallback: use total_spend as proxy for transaction volume
        plot_df['txn_per_account'] = plot_df.apply(
            lambda r: r['total_spend'] / r['unique_accounts']
            if r['unique_accounts'] > 0 else 0, axis=1
        )
        # Normalize to index
        max_val = plot_df['txn_per_account'].max()
        plot_df['txn_per_account'] = (plot_df['txn_per_account'] / max_val * 100) if max_val > 0 else 0

    plot_df['category_label'] = (
        plot_df['category'].astype(str).str.replace('_', ' ').str.title()
    )

    # ----- Build chart -----
    fig, ax = plt.subplots(figsize=(12, 7))

    # Quadrant lines at medians
    med_x = plot_df['txn_per_account'].median()
    med_y = plot_df['growth_rate'].median()
    ax.axhline(y=med_y, color=GEN_COLORS['muted'], linewidth=1.5,
               linestyle='--', alpha=0.4, zorder=1)
    ax.axvline(x=med_x, color=GEN_COLORS['muted'], linewidth=1.5,
               linestyle='--', alpha=0.4, zorder=1)

    # Plot points
    for _, row in plot_df.iterrows():
        color = CATEGORY_PALETTE.get(row['category_label'], GEN_COLORS['muted'])
        edge = GEN_COLORS['accent'] if row['growth_rate'] > 10 else 'white'
        ax.scatter(
            row['txn_per_account'], row['growth_rate'],
            s=300, color=color, alpha=0.8,
            edgecolor=edge, linewidth=2, zorder=4
        )

    # Labels
    name_col = 'competitor' if 'competitor' in plot_df.columns else 'bank'
    for _, row in plot_df.iterrows():
        name = str(row[name_col])
        if len(name) > 20:
            name = name[:18] + '..'
        ax.annotate(
            name,
            xy=(row['txn_per_account'], row['growth_rate']),
            xytext=(8, 10), textcoords='offset points',
            fontsize=12, fontweight='bold',
            color=GEN_COLORS['dark_text'],
            path_effects=[pe.withStroke(linewidth=3, foreground='white')],
            zorder=5
        )

    # Axes
    ax.set_xlabel("Engagement Depth (activity per account)", fontsize=16,
                  fontweight='bold', labelpad=12)
    ax.set_ylabel("Growth Rate (%)", fontsize=16, fontweight='bold', labelpad=12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:+.0f}%"))

    gen_clean_axes(ax)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    # Title
    ax.set_title(title, fontsize=24, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=20, loc='left')
    ax.text(0.0, 0.97, subtitle, transform=ax.transAxes,
            fontsize=14, color=GEN_COLORS['muted'], style='italic')

    # Legend
    legend_cats = plot_df['category_label'].unique()
    legend_handles = [
        plt.scatter([], [], s=120, color=CATEGORY_PALETTE.get(c, GEN_COLORS['muted']),
                    edgecolor='white', linewidth=1.5, label=c)
        for c in legend_cats
    ]
    ax.legend(
        handles=legend_handles,
        loc='upper center', bbox_to_anchor=(0.5, -0.10),
        ncol=len(legend_cats), fontsize=13, frameon=False
    )

    ax.margins(0.1)
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.14)
    plt.show()


# ---- Run ----
if 'threat_df' in dir() and threat_df is not None and len(threat_df) > 0:
    plot_activity_vs_growth(
        threat_df,
        title="Engagement Depth vs Growth",
        subtitle="Upper right = deep engagement + fast growth = highest threat",
        top_n=10
    )
