# ===========================================================================
# ACCOUNT AGE DASHBOARD: How Long Has the Account Been Open?
# ===========================================================================
# Single figure, 3 panels (1 row):
#   Left:   Response rate by account-age band (hero)
#   Center: Distribution histogram (resp vs non-resp overlaid)
#   Right:  Segment x age heatmap (or key stats if no segments)
#
# Depends on: resp_age_df, resp_age_summary (from cell 35)

if 'resp_age_summary' not in dir() or len(resp_age_summary) == 0:
    print("    No account age data. Run cell 35 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')
    _RESP_COLOR = GEN_COLORS.get('success', '#2A9D8F')
    _NONRESP_COLOR = GEN_COLORS.get('warning', '#E9C46A')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')
    _INFO = GEN_COLORS.get('info', '#457B9D')

    _bands = resp_age_summary['age_band'].tolist()
    x = np.arange(len(_bands))

    _has_segments = ('resp_age_df' in dir() and len(resp_age_df) > 0
                     and resp_age_df['segment'].nunique() > 1
                     and 'Unknown' not in resp_age_df['segment'].unique())

    # Build 3-panel figure
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 8))
    fig.subplots_adjust(wspace=0.30, top=0.85, bottom=0.15)

    # =================================================================
    # LEFT: Response Rate by Account Age (hero)
    # =================================================================
    # Wider bars (0.78 instead of 0.6) so the in-bar count text doesn't
    # overflow the column edges -- reported visual bug from 4/27 deck review.
    bars = ax1.bar(x, resp_age_summary['response_rate'], width=0.78,
                   color=_RESP_COLOR, edgecolor='white', linewidth=0.5, alpha=0.85)

    _max_idx = resp_age_summary['response_rate'].idxmax()
    _max_pos = list(resp_age_summary.index).index(_max_idx)
    for i, bar in enumerate(bars):
        if i == _max_pos:
            bar.set_color(_ACCENT)
            bar.set_alpha(1.0)

    # Combine rate% and count into ONE label above the bar so we don't have
    # to fit white "n=X mailed" text inside narrow columns. The mailed count
    # is essential context but doesn't need to live inside the bar.
    for i, (bar, rate, mailed) in enumerate(zip(bars,
                                                  resp_age_summary['response_rate'],
                                                  resp_age_summary['mailed'])):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f'{rate:.1f}%', ha='center', va='bottom', fontsize=14,
                 fontweight='bold',
                 color=_ACCENT if i == _max_pos else _RESP_COLOR)
        # Count label: white inside the bar IF the bar is tall enough, else
        # gray below the bar baseline so it never bleeds off-edge. Switch
        # threshold at 1.5% absolute response rate (most decks have rates
        # in the 0.5-5% range).
        if bar.get_height() >= 1.5:
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() / 2,
                     f'{int(mailed):,}', ha='center', va='center', fontsize=11,
                     color='white', fontweight='bold')
        else:
            ax1.text(bar.get_x() + bar.get_width() / 2, -0.18,
                     f'n={int(mailed):,}', ha='center', va='top', fontsize=10,
                     color=_MUTED, fontweight='bold')

    _overall_rate = resp_age_summary['responded'].sum() / resp_age_summary['mailed'].sum() * 100
    ax1.axhline(_overall_rate, color=_MUTED, linewidth=1.5, linestyle='--', zorder=2)
    ax1.text(len(x) - 0.5, _overall_rate + 0.2, f'Avg: {_overall_rate:.1f}%',
             fontsize=14, fontweight='bold', color=_MUTED, ha='right')

    ax1.set_xticks(x)
    ax1.set_xticklabels(_bands, fontsize=14, fontweight='bold', rotation=35, ha='right')
    ax1.set_ylabel('Response Rate', fontsize=16, fontweight='bold', labelpad=6)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax1.set_title('Response Rate by Account Age',
                   fontsize=15, fontweight='bold', color=_DARK, pad=8)

    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax1.set_axisbelow(True)

    # =================================================================
    # CENTER: Account Age Distribution (histogram)
    # =================================================================
    if 'resp_age_df' in dir() and len(resp_age_df) > 0:
        _cap = resp_age_df['age_at_mail_days'].quantile(0.99)
        _bins = np.linspace(91, min(_cap, 10000), 50)

        for stat, color, alpha in [('Non-Responder', _NONRESP_COLOR, 0.4),
                                    ('Responder', _RESP_COLOR, 0.6)]:
            _d = resp_age_df[resp_age_df['status'] == stat]['age_at_mail_days']
            _d = _d[(_d >= 91) & (_d <= _cap)]
            n = len(_d)
            ax2.hist(_d, bins=_bins, alpha=alpha, color=color, edgecolor='white',
                     linewidth=0.3, label=f'{stat} ({n:,})', density=True)

        for stat, color, ls in [('Responder', _RESP_COLOR, '-'),
                                 ('Non-Responder', _NONRESP_COLOR, '--')]:
            _med = resp_age_df[resp_age_df['status'] == stat]['age_at_mail_days'].median()
            ax2.axvline(_med, color=color, linewidth=2, linestyle=ls, zorder=5)
            _yrs = _med / 365.25
            _offset = 80 if stat == 'Responder' else -80
            _ha = 'left' if stat == 'Responder' else 'right'
            ax2.text(_med + _offset, ax2.get_ylim()[1] * 0.88,
                     f'{_yrs:.1f}yr', color=color, fontsize=14,
                     fontweight='bold', va='top', ha=_ha)

        ax2.set_xlabel('Account Age at Mail (days)', fontsize=16, fontweight='bold', labelpad=6)
        ax2.set_ylabel('Density', fontsize=16, fontweight='bold', labelpad=6)
        ax2.legend(fontsize=14, framealpha=0.9)
        ax2.set_title('Distribution: Resp vs Non-Resp',
                       fontsize=15, fontweight='bold', color=_DARK, pad=8)

        gen_clean_axes(ax2, keep_left=True, keep_bottom=True)
        ax2.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
        ax2.set_axisbelow(True)

    # =================================================================
    # RIGHT: Segment x Age Heatmap (or key stats)
    # =================================================================
    if _has_segments:
        _SEG_ORDER = ['NU', 'TH-10', 'TH-15', 'TH-20', 'TH-25']
        _plot_segs = [s for s in _SEG_ORDER if s in resp_age_df['segment'].values]
        _extra = [s for s in resp_age_df['segment'].unique()
                  if s not in _SEG_ORDER and s != 'Unknown']
        _plot_segs = _plot_segs + sorted(_extra)
        _plot_segs = list(reversed(_plot_segs))  # high to low (NU on bottom)

        _pivot = resp_age_df.groupby(['segment', 'age_band'], observed=True).apply(
            lambda g: (g['status'] == 'Responder').sum() / len(g) * 100
            if len(g) >= 20 else np.nan
        ).unstack(level='age_band')

        _pivot = _pivot.reindex(index=_plot_segs)
        _pivot = _pivot[[c for c in _bands if c in _pivot.columns]]

        if _pivot.notna().any().any():
            sns.heatmap(
                _pivot, annot=True, fmt='.1f', cmap='YlGn',
                linewidths=2, linecolor='white',
                cbar_kws={'shrink': 0.6, 'label': 'Rate %'},
                annot_kws={'fontsize': 8, 'fontweight': 'bold'},
                ax=ax3, vmin=0,
            )
            ax3.set_xlabel('Account Age', fontsize=16, fontweight='bold', labelpad=6)
            ax3.set_ylabel('Segment', fontsize=16, fontweight='bold', labelpad=6)
            ax3.set_xticklabels(ax3.get_xticklabels(), fontsize=14,
                                fontweight='bold', rotation=35, ha='right')
            ax3.set_yticklabels(ax3.get_yticklabels(), fontsize=14,
                                fontweight='bold', rotation=0)
            ax3.set_title('Segment x Account Age',
                           fontsize=15, fontweight='bold', color=_DARK, pad=8)
        else:
            ax3.axis('off')
    else:
        # No segment data: key stats text panel
        ax3.axis('off')

        _r_med = resp_age_df[resp_age_df['status'] == 'Responder']['age_at_mail_days'].median()
        _nr_med = resp_age_df[resp_age_df['status'] == 'Non-Responder']['age_at_mail_days'].median()
        _top = resp_age_summary.loc[resp_age_summary['response_rate'].idxmax()]
        _bot = resp_age_summary.loc[resp_age_summary['response_rate'].idxmin()]
        _total_mailed = resp_age_summary['mailed'].sum()
        _total_resp = resp_age_summary['responded'].sum()

        _stats = [
            ('Total Mailed', f'{_total_mailed:,}'),
            ('Total Responded', f'{_total_resp:,}'),
            ('Overall Rate', f'{_total_resp / _total_mailed * 100:.1f}%'),
            ('', ''),
            ('Median Acct Age (Resp)', f'{_r_med / 365.25:.1f} years'),
            ('Median Acct Age (Non-R)', f'{_nr_med / 365.25:.1f} years'),
            ('', ''),
            ('Best Band', f'{_top["age_band"]} ({_top["response_rate"]:.1f}%)'),
            ('Worst Band', f'{_bot["age_band"]} ({_bot["response_rate"]:.1f}%)'),
        ]

        _y = 0.92
        ax3.set_title('Key Metrics', fontsize=20, fontweight='bold',
                       color=_DARK, pad=8)
        for label, val in _stats:
            if label == '':
                _y -= 0.04
                continue
            ax3.text(0.1, _y, label, fontsize=14, fontweight='bold',
                     color=_MUTED, transform=ax3.transAxes, va='top')
            ax3.text(0.9, _y, val, fontsize=14, fontweight='bold',
                     color=_DARK, transform=ax3.transAxes, va='top', ha='right')
            _y -= 0.10

    # Main title
    fig.suptitle('Account Age & Campaign Response',
                 fontsize=22, fontweight='bold', color=_DARK, y=0.96)
    fig.text(0.5, 0.915,
             'How long has the account been open?  |  Accounts < 90 days excluded  |  All mailers pooled',
             ha='center', fontsize=14, color=_MUTED, style='italic')

    plt.show()
