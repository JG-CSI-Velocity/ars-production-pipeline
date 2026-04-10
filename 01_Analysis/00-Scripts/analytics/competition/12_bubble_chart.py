# ===========================================================================
# BUBBLE CHART: COMPETITIVE LANDSCAPE (Conference Edition)
# ===========================================================================
# Penetration % (x) vs Transaction Volume Index (y) vs Account Reach (size)
# No dollar figures. Color = category. Labels with smart offset.

def plot_competitive_landscape_bubble(
    penetration_df,
    title="Competitive Landscape",
    subtitle="Account Penetration vs Transaction Activity",
    top_n=12
):
    if penetration_df is None or penetration_df.empty:
        print("No penetration data available.")
        return

    chart_df = (
        penetration_df.copy()
        .sort_values('unique_accounts', ascending=False)
        .head(top_n)
    )

    chart_df['category_label'] = chart_df['category'].str.replace('_', ' ').str.title()

    # Transaction volume index (normalized 0-100, no dollars)
    max_txn = chart_df['transaction_count'].max()
    chart_df['txn_index'] = (chart_df['transaction_count'] / max_txn * 100) if max_txn > 0 else 0

    # Bubble size: scale accounts to visual range
    max_acct = chart_df['unique_accounts'].max()
    min_bubble, max_bubble = 200, 2500
    chart_df['bubble_size'] = (
        chart_df['unique_accounts'] / max_acct * (max_bubble - min_bubble) + min_bubble
    )

    # Colors per row
    chart_df['color'] = chart_df['category_label'].map(
        lambda c: CATEGORY_PALETTE.get(c, GEN_COLORS['muted'])
    )

    # ----- Build chart -----
    fig, ax = plt.subplots(figsize=(14, 9))

    # Draw bubbles
    for _, row in chart_df.iterrows():
        ax.scatter(
            row['penetration_pct'],
            row['txn_index'],
            s=row['bubble_size'],
            color=row['color'],
            alpha=0.75,
            edgecolor='white',
            linewidth=2,
            zorder=3
        )

    # ----- Smart labels (offset to avoid overlap) -----
    positions = []
    for _, row in chart_df.iterrows():
        x, y = row['penetration_pct'], row['txn_index']
        # Offset direction: alternate above/below, nudge right
        offset_y = 3.5 if len(positions) % 2 == 0 else -4.5
        # Check for nearby labels and adjust
        for px, py in positions:
            if abs(x - px) < 0.3 and abs(y + offset_y - py) < 5:
                offset_y += 5
        positions.append((x, y + offset_y))

        bank_name = row['bank'] if 'bank' in chart_df.columns else row.get('competitor', '')
        # Shorten long names for readability at distance
        if len(bank_name) > 22:
            bank_name = bank_name[:20] + '..'

        ax.annotate(
            bank_name,
            xy=(x, y),
            xytext=(8, offset_y),
            textcoords='offset points',
            fontsize=12,
            fontweight='bold',
            color=GEN_COLORS['dark_text'],
            path_effects=[pe.withStroke(linewidth=3, foreground='white')],
            zorder=5
        )

    # ----- Axes -----
    ax.set_xlabel("Account Penetration (%)", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], labelpad=12)
    ax.set_ylabel("Transaction Volume Index", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], labelpad=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_index))

    gen_clean_axes(ax)

    # Light reference grid (horizontal only)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # ----- Title block -----
    ax.set_title(title, fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=20, loc='left')
    ax.text(0.0, 0.97, subtitle, transform=ax.transAxes,
            fontsize=15, color=GEN_COLORS['muted'], style='italic')

    # ----- Legend (category colors) -----
    legend_cats = chart_df['category_label'].unique()
    legend_handles = [
        plt.scatter([], [], s=150, color=CATEGORY_PALETTE.get(c, GEN_COLORS['muted']),
                    edgecolor='white', linewidth=1.5, label=c)
        for c in legend_cats
    ]
    legend = ax.legend(
        handles=legend_handles,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.08),
        ncol=len(legend_cats),
        fontsize=14,
        frameon=False,
        handletextpad=0.5,
        columnspacing=2.0
    )

    # Size reference note
    ax.text(0.99, 0.01, "Bubble size = Account reach",
            transform=ax.transAxes, fontsize=11, color=GEN_COLORS['muted'],
            ha='right', va='bottom', style='italic')

    # Margins so bubbles don't clip
    ax.margins(0.08)

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.show()


# ---- Run ----
if len(penetration_data) > 0:
    plot_competitive_landscape_bubble(
        pen_df,
        title="Competitive Landscape",
        subtitle="Who is capturing your customers?  (Bubble size = account reach)",
        top_n=12
    )
