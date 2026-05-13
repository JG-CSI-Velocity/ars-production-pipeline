# ===========================================================================
# PAYROLL RETENTION: Payroll Status vs Attrition / Spend Velocity
# ===========================================================================
# If attrition_df exists: cross payroll with attrition risk.
# Otherwise: use spend velocity (last 3 months vs first 3 months) as a
# proxy for member engagement trajectory.

# ---------------------------------------------------------------------------
# Check for attrition data
# ---------------------------------------------------------------------------
has_attrition = ('attrition_df' in dir() or 'attrition_df' in globals())

if has_attrition:
    try:
        _ = attrition_df.shape
    except NameError:
        has_attrition = False

if has_attrition:
    # -----------------------------------------------------------------
    # Path A: Real attrition data available
    # -----------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Merge payroll status with attrition
    attrition_merge = attrition_df.copy()
    acct_col = None
    for col in ['primary_account_num', 'Acct Number', 'account_number']:
        if col in attrition_merge.columns:
            acct_col = col
            break

    if acct_col and acct_col != 'primary_account_num':
        attrition_merge = attrition_merge.rename(columns={acct_col: 'primary_account_num'})

    if 'primary_account_num' in attrition_merge.columns:
        payroll_attrition = payroll_df[['primary_account_num', 'has_payroll']].merge(
            attrition_merge, on='primary_account_num', how='inner'
        )

        # Look for risk/attrition column
        risk_col = None
        for col in ['attrition_risk', 'risk_score', 'churn_risk', 'declining']:
            if col in payroll_attrition.columns:
                risk_col = col
                break

        if risk_col:
            ax1 = axes[0]
            risk_by_payroll = payroll_attrition.groupby('has_payroll')[risk_col].mean()
            labels = ['Non-Payroll', 'Payroll']
            vals = [risk_by_payroll.get(False, 0), risk_by_payroll.get(True, 0)]
            colors = [GEN_COLORS['warning'], GEN_COLORS['success']]

            bars = ax1.bar(labels, vals, color=colors, edgecolor='white',
                           linewidth=2, zorder=3)
            for bar, val in zip(bars, vals):
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                         f"{val:.1f}%", ha='center', va='bottom',
                         fontsize=16, fontweight='bold', color=GEN_COLORS['dark_text'])

            gen_clean_axes(ax1)
            ax1.set_title("Avg Attrition Risk", fontsize=18, fontweight='bold',
                          color=GEN_COLORS['dark_text'], loc='left')
            ax1.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))

            # Reduction stat
            if vals[0] > 0:
                reduction = (1 - vals[1] / vals[0]) * 100
                ax1.text(0.5, 0.85,
                         f"Payroll members: {reduction:.0f}% lower risk",
                         fontsize=14, fontweight='bold', color=GEN_COLORS['success'],
                         ha='center', transform=ax1.transAxes)
        else:
            axes[0].text(0.5, 0.5, 'Risk column not found in attrition data',
                         ha='center', va='center', fontsize=14,
                         color=GEN_COLORS['muted'], transform=axes[0].transAxes)
            axes[0].axis('off')

        axes[1].text(0.5, 0.5, 'Additional attrition metrics\navailable with full data',
                     ha='center', va='center', fontsize=14,
                     color=GEN_COLORS['muted'], transform=axes[1].transAxes)
        axes[1].axis('off')
    else:
        for ax in axes:
            ax.text(0.5, 0.5, 'Cannot match accounts to attrition data',
                    ha='center', va='center', fontsize=14,
                    color=GEN_COLORS['muted'], transform=ax.transAxes)
            ax.axis('off')

    fig.suptitle("Payroll Status vs Attrition Risk",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], x=0.01, ha='left', y=GEN_TITLE_Y)
    fig.text(0.01, 0.99,
             f"Payroll as a retention anchor  --  {DATASET_LABEL}",
             fontsize=13, style='italic', color=GEN_COLORS['muted'],
             ha='left', transform=fig.transFigure)
    plt.tight_layout()
    plt.show()

else:
    # -----------------------------------------------------------------
    # Path B: No attrition data -- use spend velocity as proxy
    # -----------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Sort months and split into first half / last half
    sorted_months = sorted(combined_df['year_month'].unique())
    n_m = len(sorted_months)

    if n_m >= 4:
        first_months = sorted_months[:min(3, n_m // 2)]
        last_months = sorted_months[-min(3, n_m // 2):]
    elif n_m >= 2:
        first_months = sorted_months[:1]
        last_months = sorted_months[-1:]
    else:
        first_months = sorted_months
        last_months = sorted_months

    # Compute per-account spend in first vs last period
    first_spend = (
        combined_df[combined_df['year_month'].isin(first_months)]
        .groupby('primary_account_num')['amount']
        .agg(first_total='sum', first_count='count')
        .reset_index()
    )
    last_spend = (
        combined_df[combined_df['year_month'].isin(last_months)]
        .groupby('primary_account_num')['amount']
        .agg(last_total='sum', last_count='count')
        .reset_index()
    )

    velocity_df = first_spend.merge(last_spend, on='primary_account_num', how='outer').fillna(0)
    velocity_df = velocity_df.merge(
        payroll_df[['primary_account_num', 'has_payroll']],
        on='primary_account_num', how='left'
    )
    velocity_df['has_payroll'] = velocity_df['has_payroll'].fillna(False)

    # Spend velocity: change in monthly activity
    n_first = max(len(first_months), 1)
    n_last = max(len(last_months), 1)
    velocity_df['first_monthly'] = velocity_df['first_count'] / n_first
    velocity_df['last_monthly'] = velocity_df['last_count'] / n_last
    velocity_df['velocity'] = velocity_df['last_monthly'] - velocity_df['first_monthly']

    # Classify: growing, stable, declining
    velocity_df['trajectory'] = pd.cut(
        velocity_df['velocity'],
        bins=[-np.inf, -2, 2, np.inf],
        labels=['Declining', 'Stable', 'Growing']
    )

    # Panel 1: Avg velocity by payroll status
    ax1 = axes[0]
    vel_by_payroll = velocity_df.groupby('has_payroll')['velocity'].mean()
    labels_v = ['Non-Payroll', 'Payroll']
    vals_v = [vel_by_payroll.get(False, 0), vel_by_payroll.get(True, 0)]
    colors_v = [GEN_COLORS['warning'], GEN_COLORS['success']]

    bars = ax1.bar(labels_v, vals_v, color=colors_v, edgecolor='white',
                   linewidth=2, width=0.5, zorder=3)

    ax1.axhline(y=0, color=GEN_COLORS['muted'], linestyle='-', linewidth=1, zorder=1)

    for bar, val in zip(bars, vals_v):
        y_pos = bar.get_height() if val >= 0 else bar.get_height() - 0.3
        va = 'bottom' if val >= 0 else 'top'
        ax1.text(bar.get_x() + bar.get_width() / 2, y_pos,
                 f"{val:+.1f} txns/mo", ha='center', va=va,
                 fontsize=14, fontweight='bold', color=GEN_COLORS['dark_text'])

    gen_clean_axes(ax1)
    ax1.set_title("Avg Spend Velocity", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')
    ax1.set_ylabel("Change in Monthly Txns", fontsize=12)

    # Panel 2: Trajectory distribution (stacked bar)
    ax2 = axes[1]
    traj_data = velocity_df.groupby(['has_payroll', 'trajectory'], observed=True).size().unstack(fill_value=0)
    traj_pct = traj_data.div(traj_data.sum(axis=1), axis=0) * 100

    traj_colors = {
        'Growing': GEN_COLORS['success'],
        'Stable': GEN_COLORS['info'],
        'Declining': GEN_COLORS['accent'],
    }

    x_pos = [0, 1]
    x_labels = ['Non-Payroll', 'Payroll']
    bottom = [0, 0]

    for traj in ['Growing', 'Stable', 'Declining']:
        if traj in traj_pct.columns:
            vals = [
                traj_pct.loc[False, traj] if False in traj_pct.index else 0,
                traj_pct.loc[True, traj] if True in traj_pct.index else 0,
            ]
            bars2 = ax2.bar(x_pos, vals, bottom=bottom, width=0.5,
                           label=traj, color=traj_colors.get(traj, GEN_COLORS['muted']),
                           edgecolor='white', linewidth=1.5, zorder=3)

            for j, (val, b) in enumerate(zip(vals, bottom)):
                if val > 5:
                    ax2.text(x_pos[j], b + val / 2,
                             f"{val:.0f}%", ha='center', va='center',
                             fontsize=12, fontweight='bold', color='white')

            bottom = [b + v for b, v in zip(bottom, vals)]

    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(x_labels, fontsize=13, fontweight='bold')
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_pct))
    ax2.legend(fontsize=12, loc='upper right')

    gen_clean_axes(ax2)
    ax2.set_title("Member Trajectory Distribution", fontsize=18, fontweight='bold',
                  color=GEN_COLORS['dark_text'], loc='left')

    # Overall title
    period_label = f"{first_months[0]} to {last_months[-1]}" if first_months and last_months else ""
    fig.suptitle("Payroll as a Retention Anchor: Spend Velocity Analysis",
                 fontsize=24, fontweight='bold',
                 color=GEN_COLORS['dark_text'], x=0.01, ha='left', y=GEN_TITLE_Y)
    fig.text(0.01, 1.01,
             f"Activity change {period_label}  --  {DATASET_LABEL}",
             fontsize=13, style='italic', color=GEN_COLORS['muted'],
             ha='left', transform=fig.transFigure)

    plt.tight_layout()
    plt.show()

    # Summary
    declining_pr = 0
    declining_npr = 0
    if 'trajectory' in velocity_df.columns:
        pr_traj = velocity_df[velocity_df['has_payroll']]
        npr_traj = velocity_df[~velocity_df['has_payroll']]
        if len(pr_traj) > 0:
            declining_pr = (pr_traj['trajectory'] == 'Declining').sum() / len(pr_traj) * 100
        if len(npr_traj) > 0:
            declining_npr = (npr_traj['trajectory'] == 'Declining').sum() / len(npr_traj) * 100

    print(f"\n  Declining members: Payroll {declining_pr:.1f}% vs Non-Payroll {declining_npr:.1f}%")
    if declining_npr > 0:
        print(f"  Payroll members are {(1 - declining_pr/declining_npr)*100:.0f}% less likely to be declining")
