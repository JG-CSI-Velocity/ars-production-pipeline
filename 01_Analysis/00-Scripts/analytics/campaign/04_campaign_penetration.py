# ===========================================================================
# CAMPAIGN PENETRATION: New vs Repeat Responders & Cumulative Reach
# ===========================================================================
# Tracks cumulative unique mailed/responded accounts across periods.
# For each period: identifies first-time vs repeat responders.
# Responder = TH-* or NU 5+ (not NU 1-4).
# Outputs: penetration_df, repeat_summary.
# Guard: camp_acct must exist.

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data available. Skipping penetration analysis.")
else:
    # -----------------------------------------------------------------
    # 1. Build per-period penetration using set operations
    # -----------------------------------------------------------------
    _acct_col = rewards_df['Acct Number' if 'Acct Number' in rewards_df.columns
                           else ' Acct Number'].astype(str).str.strip()

    # Total population = eligible accounts in rewards_df (filtered upstream
    # by txn_wrapper._inject_eligible_filter; falls back to full ODDD if
    # ELIGIBLE_FILTER_APPLIED is False).
    total_population = len(_acct_col.unique())

    cum_mailed_set = set()
    cum_responded_set = set()
    period_rows = []

    for mc, rc in zip(mail_cols, resp_cols):
        period_label = mc.replace(' Mail', '')

        # Accounts mailed this period
        mailed_accts = set(_acct_col[rewards_df[mc].notna()])

        # Responders: TH-* or NU 5+ only (not NU 1-4)
        _rv = rewards_df[rc]
        _is_resp = _rv.map(lambda v: False if pd.isna(v) else
                           str(v).strip().upper().startswith('TH') or
                           str(v).strip().upper() in ('NU 5+', 'NU5+'))
        resp_accts = set(_acct_col[_is_resp])

        # New vs repeat (computed BEFORE updating cumulative sets)
        new_responders = resp_accts - cum_responded_set
        repeat_responders = resp_accts & cum_responded_set

        # Grow cumulative sets
        cum_mailed_set |= mailed_accts
        cum_responded_set |= resp_accts

        # Penetration = % of TOTAL portfolio, not just mailed subset
        mail_penetration = len(cum_mailed_set) / total_population * 100 if total_population > 0 else 0
        resp_penetration = len(cum_responded_set) / total_population * 100 if total_population > 0 else 0
        # Response rate = % of mailed that responded (different from penetration)
        cum_response_rate = len(cum_responded_set) / len(cum_mailed_set) * 100 if len(cum_mailed_set) > 0 else 0

        period_rows.append({
            'period': period_label,
            'mailed': len(mailed_accts),
            'responded': len(resp_accts),
            'new_responders': len(new_responders),
            'repeat_responders': len(repeat_responders),
            'cum_unique_mailed': len(cum_mailed_set),
            'cum_unique_responded': len(cum_responded_set),
            'cum_mail_penetration_pct': mail_penetration,
            'cum_resp_penetration_pct': resp_penetration,
            'cum_response_rate_pct': cum_response_rate,
        })

    penetration_df = pd.DataFrame(period_rows)

    # Sort chronologically
    _MONTH_ABBR = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,
                   'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

    def _pen_sort_key(label):
        try:
            return (2000 + int(label[3:])) * 100 + _MONTH_ABBR.get(label[:3], 0)
        except (ValueError, IndexError):
            return 999999

    penetration_df['_sort'] = penetration_df['period'].apply(_pen_sort_key)
    penetration_df = penetration_df.sort_values('_sort').drop(columns='_sort').reset_index(drop=True)

    # -----------------------------------------------------------------
    # 2. Repeat responder summary
    # -----------------------------------------------------------------
    # Count how many periods each account was a TRUE responder (TH/NU 5+)
    _resp_success_counts = rewards_df[resp_cols].apply(
        lambda col: col.map(lambda v: False if pd.isna(v) else
                            str(v).strip().upper().startswith('TH') or
                            str(v).strip().upper() in ('NU 5+', 'NU5+'))
    ).sum(axis=1)
    _resp_mask = _resp_success_counts > 0

    total_unique_mailed = len(cum_mailed_set)
    total_unique_responded = len(cum_responded_set)
    single_responders = int((_resp_success_counts[_resp_mask] == 1).sum())
    multi_responders = int((_resp_success_counts[_resp_mask] > 1).sum())

    repeat_summary = {
        'total_population': total_population,
        'total_unique_mailed': total_unique_mailed,
        'total_unique_responded': total_unique_responded,
        'single_responders': single_responders,
        'multi_responders': multi_responders,
        'mail_penetration_pct': total_unique_mailed / total_population * 100 if total_population > 0 else 0,
        'resp_penetration_pct': total_unique_responded / total_population * 100 if total_population > 0 else 0,
        'response_rate_pct': total_unique_responded / total_unique_mailed * 100 if total_unique_mailed > 0 else 0,
        'multi_resp_pct': multi_responders / total_unique_responded * 100 if total_unique_responded > 0 else 0,
        'avg_periods_responded': float(_resp_success_counts[_resp_mask].mean()),
    }

    # =================================================================
    # CHART 1: New vs Repeat Responders by Period
    # =================================================================
    fig1, ax1 = plt.subplots(figsize=(14, 7))

    x = np.arange(len(penetration_df))
    bar_width = 0.55

    ax1.bar(x, penetration_df['new_responders'], width=bar_width,
            label='New Responder', color=GEN_COLORS['success'],
            edgecolor='white', linewidth=0.5)
    ax1.bar(x, penetration_df['repeat_responders'], width=bar_width,
            bottom=penetration_df['new_responders'],
            label='Repeat Responder', color=GEN_COLORS['warning'],
            edgecolor='white', linewidth=0.5)

    # Value labels on segments
    for i, row in penetration_df.iterrows():
        if row['new_responders'] > 0:
            ax1.text(i, row['new_responders'] / 2,
                     f"{int(row['new_responders']):,}",
                     ha='center', va='center', fontsize=14, fontweight='bold',
                     color='white')
        if row['repeat_responders'] > 0:
            ax1.text(i, row['new_responders'] + row['repeat_responders'] / 2,
                     f"{int(row['repeat_responders']):,}",
                     ha='center', va='center', fontsize=14, fontweight='bold',
                     color='white')

    ax1.set_xticks(x)
    ax1.set_xticklabels(penetration_df['period'], fontsize=14,
                         fontweight='bold', rotation=45, ha='right')
    ax1.set_ylabel("Responders", fontsize=16, fontweight='bold', labelpad=10)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))

    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax1.set_axisbelow(True)

    # Cumulative penetration lines on secondary axis (vs TOTAL population)
    ax1_twin = ax1.twinx()
    ax1_twin.plot(x, penetration_df['cum_mail_penetration_pct'],
                  color=GEN_COLORS['info'], linewidth=2.5,
                  marker='s', markersize=6, zorder=5, linestyle='--',
                  label='Mail Penetration (% of portfolio)')
    ax1_twin.plot(x, penetration_df['cum_resp_penetration_pct'],
                  color=GEN_COLORS['accent'], linewidth=3,
                  marker='D', markersize=8, zorder=5,
                  label='Response Penetration (% of portfolio)')
    _pen_base_label = "Eligible Portfolio" if globals().get('ELIGIBLE_FILTER_APPLIED') else "Total Portfolio"
    ax1_twin.set_ylabel(f"% of {_pen_base_label} ({total_population:,} accounts)", fontsize=16,
                         fontweight='bold', color=GEN_COLORS['accent'], labelpad=10)
    ax1_twin.yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_pct))
    ax1_twin.spines['top'].set_visible(False)
    ax1_twin.spines['left'].set_visible(False)

    for i, pct in enumerate(penetration_df['cum_resp_penetration_pct']):
        ax1_twin.text(i, pct + 0.3, f"{pct:.1f}%", ha='center', fontsize=14,
                      fontweight='bold', color=GEN_COLORS['accent'])

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc='upper center', bbox_to_anchor=(0.5, -0.22),
               ncol=3, fontsize=14, frameon=False)

    ax1.set_title("New vs Repeat Responders by Period",
                  fontsize=26, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax1.text(0.0, 1.02,
             f"Cumulative penetration of mailed population  ({DATASET_LABEL})",
             transform=ax1.transAxes, fontsize=14,
             color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.22)
    plt.show()

    # =================================================================
    # CHART 2: Responder Funnel
    # =================================================================
    fig2, ax2 = plt.subplots(figsize=(14, 7))

    funnel_labels = [
        'Total\nPortfolio',
        'Ever\nMailed',
        'Ever\nResponded',
        'Single\nResponse',
        'Multi\nResponse',
    ]
    funnel_values = [
        total_population,
        total_unique_mailed,
        total_unique_responded,
        single_responders,
        multi_responders,
    ]
    funnel_colors = [
        GEN_COLORS['muted'],
        GEN_COLORS['info'],
        GEN_COLORS['success'],
        GEN_COLORS['warning'],
        GEN_COLORS['accent'],
    ]

    y_pos = range(len(funnel_labels))
    ax2.barh(y_pos, funnel_values, color=funnel_colors,
             edgecolor='white', linewidth=1, height=0.6)

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(funnel_labels, fontsize=14, fontweight='bold')
    ax2.xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
    ax2.invert_yaxis()

    gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
    ax2.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax2.set_axisbelow(True)

    # Value labels with percentages (all vs total portfolio)
    for j, val in enumerate(funnel_values):
        pct = val / total_population * 100 if total_population > 0 else 0
        _pen_pct_base = "eligible" if globals().get('ELIGIBLE_FILTER_APPLIED') else "portfolio"
        if j == 0:
            pct_label = f"  {val:,}"
        else:
            pct_label = f"  {val:,}  ({pct:.1f}% of {_pen_pct_base})"
        ax2.text(val, j, pct_label, va='center', fontsize=14,
                 fontweight='bold', color=funnel_colors[j])

    ax2.set_title("Responder Funnel",
                  fontsize=26, fontweight='bold',
                  color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax2.text(0.0, 1.02,
             f"How deeply has the campaign reached the mailed population?  ({DATASET_LABEL})",
             transform=ax2.transAxes, fontsize=14,
             color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()

    # -----------------------------------------------------------------
    # 3. Styled summary table
    # -----------------------------------------------------------------
    pen_display = penetration_df.copy()
    pen_display.columns = [
        'Period', 'Mailed', 'Responded', 'New Resp', 'Repeat Resp',
        'Cum Mailed', 'Cum Resp',
        'Mail Pen %', 'Resp Pen %', 'Response Rate %',
    ]

    styled_pen = (
        pen_display.style
        .hide(axis='index')
        .format({
            'Mailed': '{:,.0f}',
            'Responded': '{:,.0f}',
            'New Resp': '{:,.0f}',
            'Repeat Resp': '{:,.0f}',
            'Cum Mailed': '{:,.0f}',
            'Cum Resp': '{:,.0f}',
            'Mail Pen %': '{:.1f}%',
            'Resp Pen %': '{:.1f}%',
            'Response Rate %': '{:.1f}%',
        })
        .set_properties(**{
            'font-size': '13px', 'font-weight': 'bold',
            'text-align': 'center', 'border': '1px solid #E9ECEF',
            'padding': '7px 10px',
        })
        .set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', GEN_COLORS['warning']),
                ('color', 'white'), ('font-size', '14px'),
                ('font-weight', 'bold'), ('text-align', 'center'),
                ('padding', '8px 10px'),
            ]},
            {'selector': 'caption', 'props': [
                ('font-size', '22px'), ('font-weight', 'bold'),
                ('color', GEN_COLORS['dark_text']), ('text-align', 'left'),
                ('padding-bottom', '12px'),
            ]},
        ])
        .set_caption(f"Campaign Penetration by Period  ({'Eligible' if globals().get('ELIGIBLE_FILTER_APPLIED') else 'Total'} portfolio: {total_population:,} accounts  |  {DATASET_LABEL})")
        .bar(subset=['Resp Pen %'], color=GEN_COLORS['success'], vmin=0)
    )

    display(styled_pen)

    # -----------------------------------------------------------------
    # 4. Console summary
    # -----------------------------------------------------------------
    _pen_console_base = "eligible portfolio" if globals().get('ELIGIBLE_FILTER_APPLIED') else "total portfolio"
    print(f"\n    Penetration Analysis (vs {_pen_console_base} of {total_population:,} accounts):")
    print(f"    Total unique mailed: {total_unique_mailed:,} "
          f"({repeat_summary['mail_penetration_pct']:.1f}% of {_pen_console_base})")
    print(f"    Total unique responded (ever): {total_unique_responded:,} "
          f"({repeat_summary['resp_penetration_pct']:.1f}% of {_pen_console_base})")
    print(f"    Cumulative response rate (of mailed): {repeat_summary['response_rate_pct']:.1f}%")
    if total_unique_responded > 0:
        print(f"    Single-response accounts: {single_responders:,} "
              f"({single_responders / total_unique_responded * 100:.1f}% of responders)")
    print(f"    Multi-response accounts: {multi_responders:,} "
          f"({repeat_summary['multi_resp_pct']:.1f}% of responders)")
    print(f"    Avg periods responded (among responders): "
          f"{repeat_summary['avg_periods_responded']:.1f}")
