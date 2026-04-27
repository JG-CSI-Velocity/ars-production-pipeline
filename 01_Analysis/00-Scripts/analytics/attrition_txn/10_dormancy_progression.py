# ===========================================================================
# DORMANCY PROGRESSION: Account Status + Months Since Last Activity
# ===========================================================================
# Distribution of account statuses. Months with zero swipes histogram.

# ---------------------------------------------------------------------------
# Panel 1: Account status distribution (if available)
# ---------------------------------------------------------------------------
_has_status = 'stat_desc' in attrition_df.columns or 'stat_code' in attrition_df.columns
_status_col = 'stat_desc' if 'stat_desc' in attrition_df.columns else (
    'stat_code' if 'stat_code' in attrition_df.columns else None
)

# ---------------------------------------------------------------------------
# Panel 2: Months since last activity (from monthly swipe columns)
# ---------------------------------------------------------------------------
_month_swipe_cols = [c for c in rewards_df.columns if c.endswith(' Swipes') and len(c) <= 13]
_month_swipe_cols = sorted(_month_swipe_cols, key=lambda c: c)

_has_swipe_ts = len(_month_swipe_cols) > 0

if _has_swipe_ts:
    # Build swipe matrix: each row = account, each col = month
    _swipe_matrix = rewards_df[['Acct Number'] + _month_swipe_cols].copy()
    _swipe_matrix.columns = ['account_number'] + [c.replace(' Swipes', '') for c in _month_swipe_cols]
    for col in _swipe_matrix.columns[1:]:
        _swipe_matrix[col] = pd.to_numeric(_swipe_matrix[col], errors='coerce').fillna(0)

    # Count consecutive zero-swipe months from the latest month backwards
    _swipe_vals = _swipe_matrix.iloc[:, 1:].values
    _months_inactive = []
    for row in _swipe_vals:
        count = 0
        for val in reversed(row):
            if val == 0:
                count += 1
            else:
                break
        _months_inactive.append(count)

    _swipe_matrix['months_inactive'] = _months_inactive

    # Merge risk tier
    _tier_map = attrition_df[['account_number', 'risk_tier']].drop_duplicates()
    _swipe_matrix = _swipe_matrix.merge(_tier_map, on='account_number', how='left')

# ---------------------------------------------------------------------------
# Build figure
# ---------------------------------------------------------------------------
_n_panels = int(_has_status) + int(_has_swipe_ts)
if _n_panels == 0:
    print("    No status or monthly swipe data available -- skipping dormancy analysis.")
else:
    fig, axes = plt.subplots(1, _n_panels, figsize=(7 * _n_panels + 2, 7))
    if _n_panels == 1:
        axes = [axes]

    _panel_idx = 0

    # Panel: Status distribution
    if _has_status and _status_col:
        _status_counts = (
            attrition_df[_status_col].value_counts()
            .head(10)
            .sort_values(ascending=True)
        )

        y_pos = range(len(_status_counts))
        _colors = [
            GEN_COLORS['accent'] if any(kw in str(s).lower() for kw in ['closed', 'revoked', 'charged'])
            else GEN_COLORS['info']
            for s in _status_counts.index
        ]

        bars = axes[_panel_idx].barh(
            y_pos, _status_counts.values,
            color=_colors, edgecolor='white', linewidth=1.5, height=0.6
        )
        axes[_panel_idx].set_yticks(y_pos)
        axes[_panel_idx].set_yticklabels(_status_counts.index, fontsize=12, fontweight='bold')

        _max_val = _status_counts.max()
        for bar, val in zip(bars, _status_counts.values):
            axes[_panel_idx].text(
                val + (_max_val * 0.02),
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va='center', fontsize=12, fontweight='bold',
                color=GEN_COLORS['dark_text']
            )

        axes[_panel_idx].xaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
        gen_clean_axes(axes[_panel_idx], keep_left=True, keep_bottom=True)
        axes[_panel_idx].set_title("Account Status Distribution",
                                   fontsize=18, fontweight='bold',
                                   color=GEN_COLORS['dark_text'], pad=15, loc='left')
        axes[_panel_idx].set_xlabel("Account Count", fontsize=14, fontweight='bold', labelpad=10)
        _panel_idx += 1

    # Panel: Months since last activity histogram
    if _has_swipe_ts:
        _inactive_data = _swipe_matrix['months_inactive']
        _max_months = int(_inactive_data.max())
        _bins = range(0, min(_max_months + 2, len(_month_swipe_cols) + 2))

        axes[_panel_idx].hist(
            _inactive_data, bins=_bins,
            color=GEN_COLORS['warning'], edgecolor='white', linewidth=1.5,
            alpha=0.85, align='left',
        )

        # Mark dormant threshold
        axes[_panel_idx].axvline(
            x=3, color=GEN_COLORS['accent'], linewidth=2, linestyle='--', alpha=0.8
        )
        axes[_panel_idx].text(
            3.2, axes[_panel_idx].get_ylim()[1] * 0.9,
            "3+ months = high risk", fontsize=12, fontweight='bold',
            color=GEN_COLORS['accent'], va='top'
        )

        axes[_panel_idx].yaxis.set_major_formatter(plt.FuncFormatter(gen_fmt_count))
        gen_clean_axes(axes[_panel_idx], keep_left=True, keep_bottom=True)
        axes[_panel_idx].set_title("Consecutive Months Without Swipes",
                                   fontsize=18, fontweight='bold',
                                   color=GEN_COLORS['dark_text'], pad=15, loc='left')
        axes[_panel_idx].set_xlabel("Months Inactive (from latest)", fontsize=14,
                                    fontweight='bold', labelpad=10)
        axes[_panel_idx].set_ylabel("Account Count", fontsize=14, fontweight='bold', labelpad=10)

    fig.suptitle("Dormancy Progression",
                 fontsize=24, fontweight='bold',
                 color=GEN_COLORS['dark_text'], y=GEN_TITLE_Y)
    fig.text(0.5, 0.99, f"How long have inactive accounts been silent? | {DATASET_LABEL}",
             fontsize=14, color=GEN_COLORS['muted'], style='italic', ha='center')

    plt.tight_layout()
    plt.show()

    # Callouts
    if _has_swipe_ts:
        _3plus = (_inactive_data >= 3).sum()
        _6plus = (_inactive_data >= 6).sum()
        _total_sw = len(_inactive_data)
        print(f"\n    INSIGHT: {_3plus:,} accounts ({_3plus/_total_sw*100:.1f}%) "
              f"have 3+ consecutive months with zero swipes")
        print(f"    INSIGHT: {_6plus:,} accounts ({_6plus/_total_sw*100:.1f}%) "
              f"have 6+ months of inactivity")
