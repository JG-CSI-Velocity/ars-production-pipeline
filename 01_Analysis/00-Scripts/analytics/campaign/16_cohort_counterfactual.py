# ===========================================================================
# COHORT COUNTERFACTUAL: Actual vs "Without ARS" Portfolio Spend (Conf. Ed.)
# ===========================================================================
# Dual line chart: actual portfolio spend vs what it would be if responders
# had followed the non-responder decline trend. The gap = program value. (16,8).

if 'cohort_summary' not in dir() or len(cohort_summary) == 0:
    print("    No cohort data available. Skipping counterfactual chart.")
else:
    import time as _time
    _t0 = _time.time()

    # -----------------------------------------------------------------
    # 1. Pre-compute responder info per wave (vectorized, done once)
    # -----------------------------------------------------------------
    acct_col = 'Acct Number' if 'Acct Number' in rewards_df.columns else ' Acct Number'
    _n_rows = len(rewards_df)
    print(f"    Counterfactual: {_n_rows:,} rows, {len(all_months)} months, {len(WAVE_CONFIG)} waves")

    wave_cf_data = {}
    for wave_label, wc in WAVE_CONFIG.items():
        mail_col = wc['mail_col'].strip()
        resp_col = wc['resp_col'].strip()
        was_mailed = rewards_df[mail_col].notna()

        if resp_col in [c.strip() for c in rewards_df.columns]:
            _rv = rewards_df[resp_col]
            was_responded = _rv.map(lambda v: False if pd.isna(v) else
                                    str(v).strip().upper().startswith('TH') or
                                    str(v).strip().upper() in ('NU 5+','NU5+'))
        else:
            was_responded = pd.Series(False, index=rewards_df.index)

        resp_mask = was_mailed & was_responded
        if resp_mask.sum() == 0:
            continue

        pre_cols = [spend_lookup[pm] for pm in wc['pre_months'] if pm in spend_lookup]
        if len(pre_cols) == 0:
            continue

        pre_avg = rewards_df[pre_cols].apply(pd.to_numeric, errors='coerce').mean(axis=1)

        wave_row = cohort_summary[cohort_summary['wave'] == wave_label]
        if len(wave_row) == 0:
            continue
        nr_pre = wave_row['nonresp_pre_spend'].values[0]
        nr_post = wave_row['nonresp_post_spend'].values[0]
        change_ratio = nr_post / nr_pre if nr_pre > 0 else 1.0

        cf_resp_spend = pre_avg * change_ratio

        wave_cf_data[wave_label] = {
            'resp_mask': resp_mask,
            'cf_resp_spend': cf_resp_spend,
            'mail_date': wc['mail_date'],
        }

    print(f"    Pre-compute done: {len(wave_cf_data)} waves with responders ({_time.time()-_t0:.1f}s)")

    # -----------------------------------------------------------------
    # 2. Build actual vs counterfactual monthly totals
    # -----------------------------------------------------------------
    # Pre-convert ALL monthly spend columns at once (avoid repeated pd.to_numeric)
    _spend_cols_ordered = [spend_lookup[m] for m in all_months if m in spend_lookup]
    _spend_months_ordered = [m for m in all_months if m in spend_lookup]
    _all_spend_matrix = rewards_df[_spend_cols_ordered].apply(pd.to_numeric, errors='coerce').fillna(0)

    print(f"    Spend matrix built: {_all_spend_matrix.shape} ({_time.time()-_t0:.1f}s)")

    actual_monthly = []
    counterfactual_monthly = []

    for i, m in enumerate(_spend_months_ordered):
        month_date = pd.to_datetime(m, format='%b%y')
        col = _spend_cols_ordered[i]

        all_spend = _all_spend_matrix[col]
        actual_monthly.append({'month': m, 'month_date': month_date, 'spend': all_spend.sum()})

        # Counterfactual: start with actual, replace responders in post-period
        cf_spend = all_spend.copy()
        for wave_label, wd in wave_cf_data.items():
            months_after = (month_date.year - wd['mail_date'].year) * 12 + \
                           (month_date.month - wd['mail_date'].month)
            if months_after >= 1:
                mask = wd['resp_mask']
                cf_vals = wd['cf_resp_spend']
                valid = mask & cf_vals.notna() & (cf_vals > 0)
                cf_spend.loc[valid] = cf_vals.loc[valid]

        counterfactual_monthly.append({'month': m, 'month_date': month_date, 'spend': cf_spend.sum()})

    actual_df = pd.DataFrame(actual_monthly)
    cf_df = pd.DataFrame(counterfactual_monthly)

    print(f"    Monthly totals done: {len(actual_df)} months ({_time.time()-_t0:.1f}s)")

    # -----------------------------------------------------------------
    # 3. Chart
    # -----------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(16, 8))

    ax.plot(range(len(actual_df)), actual_df['spend'],
            color=GEN_COLORS['success'], linewidth=3, marker='o',
            markersize=7, markeredgecolor='white', markeredgewidth=1.5,
            label='Actual Portfolio Spend', zorder=5)

    ax.plot(range(len(cf_df)), cf_df['spend'],
            color=GEN_COLORS['accent'], linewidth=3, linestyle='--',
            marker='s', markersize=6, markeredgecolor='white', markeredgewidth=1.5,
            label='Without ARS Program', zorder=4)

    ax.fill_between(range(len(actual_df)),
                    cf_df['spend'], actual_df['spend'],
                    where=actual_df['spend'].values >= cf_df['spend'].values,
                    color=GEN_COLORS['success'], alpha=0.15,
                    label='ARS Program Value')

    ax.set_xticks(range(len(actual_df)))
    ax.set_xticklabels(actual_df['month'], fontsize=14, fontweight='bold',
                       rotation=45, ha='right')
    ax.set_ylabel("Total Portfolio Spend", fontsize=16, fontweight='bold', labelpad=10)

    gen_clean_axes(ax)
    ax.yaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(gen_fmt_count))

    ax.legend(loc='upper right', fontsize=14)

    if len(actual_df) > 0:
        last_actual = actual_df['spend'].iloc[-1]
        last_cf = cf_df['spend'].iloc[-1]
        gap = last_actual - last_cf
        if gap > 0:
            mid_y = (last_actual + last_cf) / 2
            ax.annotate(f"${gap:,.0f}\nprotected",
                        xy=(len(actual_df) - 1, mid_y),
                        xytext=(len(actual_df) - 3, mid_y + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.1),
                        fontsize=14, fontweight='bold', color=GEN_COLORS['success'],
                        arrowprops=dict(arrowstyle='->', color=GEN_COLORS['success'], lw=2))

    ax.set_title("Counterfactual: What If We Didn't Have the ARS Program?",
                 fontsize=26, fontweight='bold',
                 color=GEN_COLORS['dark_text'], pad=35, loc='left')
    ax.text(0.0, 1.02,
            f"Green gap = spend protected by campaign responder activation  ({DATASET_LABEL})",
            transform=ax.transAxes, fontsize=14,
            color=GEN_COLORS['muted'], style='italic')

    plt.tight_layout()
    plt.show()

    print(f"    Counterfactual complete ({_time.time()-_t0:.1f}s total)")
