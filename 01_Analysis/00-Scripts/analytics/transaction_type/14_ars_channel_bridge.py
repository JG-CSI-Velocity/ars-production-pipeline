# ===========================================================================
# ARS CHANNEL BRIDGE: Connecting ACH/CHK to Campaign Results
# ===========================================================================
# Links multi-channel insight to ARS campaign status.
# Two panels:
#   Left:  Channel usage rates by Responder/Non-Responder/Never Mailed
#   Right: Total volume by type for Responder vs Non-Responder
#
# Depends on: acct_channels (cell 13), camp_acct (section 09)

_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_GRID = GEN_COLORS.get('grid', '#E0E0E0')

_type_colors = {
    'SIG': GEN_COLORS.get('warning', '#E9C46A'),
    'PIN': GEN_COLORS.get('success', '#2A9D8F'),
    'ACH': GEN_COLORS.get('info', '#457B9D'),
    'CHK': GEN_COLORS.get('accent', '#E63946'),
}

if 'camp_acct' not in dir() or len(camp_acct) == 0:
    print("    No campaign data (camp_acct). Run section 09 first to see ARS bridge.")
elif 'acct_channels' not in dir() or len(acct_channels) == 0:
    print("    No channel data (acct_channels). Run cell 13 first.")
else:
    # Merge channel profile with campaign status
    _status_col = 'camp_status' if 'camp_status' in camp_acct.columns else None
    if _status_col is None:
        # Try to derive from available columns
        for _c in ['status', 'response_status', 'camp_group']:
            if _c in camp_acct.columns:
                _status_col = _c
                break

    if _status_col is None:
        print("    Cannot find campaign status column in camp_acct. Skipping.")
    else:
        acct_camp_channels = acct_channels.merge(
            camp_acct[['primary_account_num', _status_col]].drop_duplicates(),
            on='primary_account_num',
            how='left'
        )
        acct_camp_channels[_status_col] = acct_camp_channels[_status_col].fillna('Never Mailed')

        # Group
        _groups = ['Responder', 'Non-Responder', 'Never Mailed']
        _available_groups = [g for g in _groups if g in acct_camp_channels[_status_col].values]

        if len(_available_groups) < 2:
            print(f"    Only {len(_available_groups)} campaign group(s) found. Need at least 2 for comparison.")
        else:
            camp_channel_rates = acct_camp_channels[
                acct_camp_channels[_status_col].isin(_available_groups)
            ].groupby(_status_col).agg(
                acct_count=('primary_account_num', 'count'),
                pct_ach=('has_ach', 'mean'),
                pct_chk=('has_chk', 'mean'),
                pct_pin=('has_pin', 'mean'),
                pct_sig=('has_sig', 'mean'),
                avg_channels=('channel_count', 'mean'),
                avg_monthly_spend=('monthly_spend', 'mean'),
            )
            camp_channel_rates[['pct_ach', 'pct_chk', 'pct_pin', 'pct_sig']] *= 100
            camp_channel_rates = camp_channel_rates.reindex(_available_groups)

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 9))
            fig.subplots_adjust(wspace=0.30, top=0.85, bottom=0.15)

            # =================================================================
            # LEFT: Channel Usage Rates by Campaign Status
            # =================================================================
            _metrics = ['pct_pin', 'pct_sig', 'pct_ach', 'pct_chk']
            _metric_labels = ['PIN', 'SIG', 'ACH', 'CHK']
            _metric_colors = [_type_colors.get(l, _MUTED) for l in _metric_labels]

            _x = np.arange(len(_available_groups))
            _bar_width = 0.18
            _offsets = np.arange(len(_metrics)) - (len(_metrics) - 1) / 2

            for i, (metric, label, color) in enumerate(zip(_metrics, _metric_labels, _metric_colors)):
                vals = camp_channel_rates[metric].values
                bars = ax1.bar(_x + _offsets[i] * _bar_width, vals, _bar_width,
                              color=color, edgecolor='white', linewidth=0.5,
                              label=label, alpha=0.85)
                for bar, val in zip(bars, vals):
                    if val > 3:
                        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                                 f'{val:.0f}%', ha='center', va='bottom',
                                 fontsize=14, fontweight='bold', color=color)

            ax1.set_xticks(_x)
            ax1.set_xticklabels(_available_groups, fontsize=16, fontweight='bold')
            ax1.set_ylabel('% of Accounts with Activity', fontsize=18, fontweight='bold', labelpad=8)
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax1.legend(fontsize=14, framealpha=0.9, ncol=4, loc='upper right')
            ax1.set_title('Channel Usage by Campaign Status',
                          fontsize=20, fontweight='bold', color=_DARK, pad=10)
            gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
            ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
            ax1.set_axisbelow(True)

            # Add avg channels annotation below bars
            for i, grp in enumerate(_available_groups):
                _avg_ch = camp_channel_rates.loc[grp, 'avg_channels']
                ax1.text(i, -0.06, f'Avg: {_avg_ch:.1f} channels',
                         ha='center', va='top', fontsize=14, fontweight='bold',
                         color=_DARK, transform=ax1.get_xaxis_transform())

            # =================================================================
            # RIGHT: Total Volume by Type per Group (stacked bar)
            # =================================================================
            # Get volume by type for each campaign group
            _camp_merged = combined_df.merge(
                camp_acct[['primary_account_num', _status_col]].drop_duplicates(),
                on='primary_account_num',
                how='left'
            )
            _camp_merged[_status_col] = _camp_merged[_status_col].fillna('Never Mailed')
            _camp_merged = _camp_merged[_camp_merged[_status_col].isin(_available_groups)]

            _vol_pivot = _camp_merged.groupby([_status_col, 'transaction_type'])['amount'].sum().unstack(fill_value=0)
            _vol_pivot = _vol_pivot.reindex(_available_groups)

            _type_order = [t for t in ['PIN', 'SIG', 'ACH', 'CHK'] if t in _vol_pivot.columns]
            _vol_pivot = _vol_pivot[_type_order]

            # Normalize per account for fair comparison
            _acct_counts = camp_channel_rates['acct_count']
            _vol_per_acct = _vol_pivot.div(_acct_counts, axis=0)

            _x2 = np.arange(len(_available_groups))
            _bottom = np.zeros(len(_available_groups))

            for t in _type_order:
                vals = _vol_per_acct[t].values
                ax2.bar(_x2, vals, width=0.5, bottom=_bottom,
                        color=_type_colors.get(t, _MUTED), edgecolor='white',
                        linewidth=1, label=t)

                # Labels inside segments if large enough
                for j, (val, bot) in enumerate(zip(vals, _bottom)):
                    _total_bar = _vol_per_acct.iloc[j].sum()
                    if val / _total_bar > 0.08:
                        _fmt = f"${val:,.0f}"
                        ax2.text(_x2[j], bot + val / 2, _fmt,
                                 ha='center', va='center', fontsize=14,
                                 fontweight='bold', color='white')

                _bottom += vals

            # Total label on top
            for j, grp in enumerate(_available_groups):
                _total = _vol_per_acct.loc[grp].sum()
                ax2.text(_x2[j], _total + _total * 0.02,
                         f'${_total:,.0f}/acct',
                         ha='center', va='bottom', fontsize=16,
                         fontweight='bold', color=_DARK)

            ax2.set_xticks(_x2)
            ax2.set_xticklabels(_available_groups, fontsize=16, fontweight='bold')
            ax2.set_ylabel('Total Volume per Account', fontsize=18, fontweight='bold', labelpad=8)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
            ax2.legend(fontsize=14, framealpha=0.9, loc='upper right')
            ax2.set_title('Total Payment Volume per Account by Type',
                          fontsize=20, fontweight='bold', color=_DARK, pad=10)
            gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
            ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
            ax2.set_axisbelow(True)

            fig.suptitle('ARS Responders: The Full Payment Relationship',
                         fontsize=28, fontweight='bold', color=_DARK, y=0.95)
            fig.text(0.5, 0.905,
                     'ARS activates debit, but responders are multi-channel payment hubs',
                     ha='center', fontsize=16, color=_MUTED, style='italic')

            plt.show()

            # Console
            print(f"\n    ARS CHANNEL BRIDGE")
            print(f"    {'='*50}")
            for grp in _available_groups:
                _row = camp_channel_rates.loc[grp]
                print(f"    {grp}: {int(_row['acct_count']):,} accounts, "
                      f"avg {_row['avg_channels']:.1f} channels, "
                      f"${_row['avg_monthly_spend']:,.0f}/mo")
                print(f"      PIN: {_row['pct_pin']:.0f}%  SIG: {_row['pct_sig']:.0f}%  "
                      f"ACH: {_row['pct_ach']:.0f}%  CHK: {_row['pct_chk']:.0f}%")
