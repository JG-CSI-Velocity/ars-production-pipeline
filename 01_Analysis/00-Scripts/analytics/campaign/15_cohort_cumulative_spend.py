# ===========================================================================
# COHORT CUMULATIVE SPEND: Stacked Area of Protected Spend (Conference Ed.)
# ===========================================================================
# THE HERO VISUAL. X-axis = months. Each cohort is a colored band showing
# the additional spend from responders above the non-responder baseline.
# Bands stack to show cumulative growth of program impact. (16,8).

if 'cohort_summary' not in dir() or len(cohort_summary) == 0:
    print("    No cohort data available. Skipping cumulative spend chart.")
else:
    # Build monthly time series of "protected spend" per cohort
    # For each wave's responders: protected_spend_in_month_M =
    #   (responder avg spend in M) - (responder pre avg + non-resp change in M)
    #   = DID lift * responder_count (simplified: use avg DID across post window)

    cohort_colors = [GEN_COLORS['success'], GEN_COLORS['info'], GEN_COLORS['warning'],
                     GEN_COLORS['accent'], GEN_COLORS['primary'], GEN_COLORS['muted']]

    # Create monthly index
    month_labels = all_months
    month_dates = all_month_dates

    # For each cohort, determine which months are "post" months
    cohort_monthly = {}
    for i, (_, row) in enumerate(cohort_summary.iterrows()):
        wave = row['wave']
        wc = WAVE_CONFIG[wave]
        mail_date = wc['mail_date']
        did_lift = row['did_spend_lift']
        n_resp = row['responded']

        # Protected spend per month = DID lift * number of responders
        monthly_vals = {}
        for m, d in zip(month_labels, month_dates):
            months_after = (d.year - mail_date.year) * 12 + (d.month - mail_date.month)
            if 1 <= months_after <= 6:  # Up to 6 months post
                # Check if we have data for this month
                if m in spend_lookup:
                    monthly_vals[m] = max(0, did_lift * n_resp)
            else:
                monthly_vals[m] = 0

        cohort_monthly[wave] = monthly_vals

    # Build DataFrame for stacking
    stack_df = pd.DataFrame(cohort_monthly, index=month_labels).fillna(0)
    # Only keep months where at least one cohort has protected spend
    has_data = stack_df.sum(axis=1) > 0
    # Include a couple months before first activity for context
    first_active = has_data.idxmax() if has_data.any() else month_labels[0]
    first_idx = max(0, month_labels.index(first_active) - 2)
    stack_df = stack_df.iloc[first_idx:]

    fig, ax = plt.subplots(figsize=(16, 8))

    waves_in_order = list(cohort_summary['wave'])
    bottom = np.zeros(len(stack_df))
    legend_handles = []

    for i, wave in enumerate(waves_in_order):
        if wave not in stack_df.columns:
            continue
        vals = stack_df[wave].values.astype(float)
        color = cohort_colors[i % len(cohort_colors)]
        ax.fill_between(range(len(stack_df)), bottom, bottom + vals,
                        color=color, alpha=0.75, linewidth=0)
        ax.plot(range(len(stack_df)), bottom + vals,
                color=color, linewidth=1.5, alpha=0.9)
        legend_handles.append(plt.Rectangle((0, 0), 1, 1, fc=color, alpha=0.75, label=f"{wave} Cohort"))
        bottom = bottom + vals

    ax.set_xticks(range(len(stack_df)))
    ax.set_xticklabels(stack_df.index, fontsize=14, fontweight='bold', rotation=45, ha='right')
    ax.set_ylabel("Cumulative Protected Spend ($)", fontsize=16, fontweight='bold', labelpad=10)

    gen_clean_axes(ax)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))

    ax.legend(handles=legend_handles, loc='upper left', fontsize=14)

    # Annotate total at the peak
    peak_val = bottom.max()
    peak_idx = np.argmax(bottom)
    if peak_val > 0:
        ax.annotate(f"${peak_val:,.0f}\ntotal protected",
                    xy=(peak_idx, peak_val),
                    xytext=(peak_idx + 1, peak_val * 1.05),
                    fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'],
                    ha='center',
                    arrowprops=dict(arrowstyle='->', color=GEN_COLORS['dark_text'], lw=1.5))

    ax.set_title("Cumulative Protected Spend: Each Cohort Stacks",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02,
            f"Each mail wave adds new activated spenders who protect against portfolio decline  ({DATASET_LABEL})",
            transform=ax.transAxes, fontsize=14,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()
