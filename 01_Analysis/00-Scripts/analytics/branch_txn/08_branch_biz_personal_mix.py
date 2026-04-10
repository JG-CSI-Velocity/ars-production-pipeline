# ===========================================================================
# BRANCH BIZ/PERSONAL MIX: Account Type by Branch (Conference Edition)
# ===========================================================================
# Stacked bar: business vs personal account mix by branch. (14,7).

if 'br_agg' not in dir() or len(br_agg) == 0:
    print("    No branch data available. Skipping biz/personal mix.")
else:
    top10_br_mix = br_agg.head(10)['branch'].tolist()

    br_biz_pers = br_df[br_df['branch'].isin(top10_br_mix)]
    br_bp_ct = pd.crosstab(
        br_biz_pers['branch'],
        br_biz_pers['business_flag'],
        normalize='index'
    ) * 100

    # Sort by personal share for visual clarity
    if 'No' in br_bp_ct.columns:
        br_bp_ct = br_bp_ct.sort_values('No', ascending=True)

    fig, ax = plt.subplots(figsize=(14, 7))

    y_pos = range(len(br_bp_ct))
    names = [str(b)[:20] for b in br_bp_ct.index]
    bottom = np.zeros(len(br_bp_ct))

    bp_colors = {'No': GEN_COLORS['success'], 'Yes': GEN_COLORS['primary']}
    bp_labels = {'No': 'Personal', 'Yes': 'Business'}

    for col in ['No', 'Yes']:
        if col in br_bp_ct.columns:
            ax.barh(y_pos, br_bp_ct[col], left=bottom,
                    color=bp_colors.get(col, GEN_COLORS['muted']),
                    label=bp_labels.get(col, col),
                    edgecolor='white', linewidth=0.5, height=0.65)
            bottom += br_bp_ct[col].values

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=11, fontweight='bold')
    ax.set_xlabel("% of Branch Transactions", fontsize=13, fontweight='bold', labelpad=8)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax.set_xlim(0, 105)

    gen_clean_axes(ax, keep_left=True, keep_bottom=True)
    ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    ax.set_title("Business vs Personal Mix by Branch",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02, "Which branches skew business vs personal?",
            transform=ax.transAxes, fontsize=15,
            color=GEN_COLORS['muted'], style='italic')

    ax.legend(
        loc='upper center', bbox_to_anchor=(0.5, -0.08),
        ncol=2, fontsize=12, frameon=False, title='Account Type',
        title_fontproperties={'weight': 'bold', 'size': 13}
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    plt.show()
