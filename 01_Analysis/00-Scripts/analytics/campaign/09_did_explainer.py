# ===========================================================================
# DID EXPLAINER: What Is Difference-in-Differences?
# ===========================================================================
# Visual one-pager that explains the DID methodology using actual data.
# Show this BEFORE showing DID results so the audience understands the math.
#
# Depends on: segment_cohort_raw (cell 25)

if 'segment_cohort_raw' not in dir() or len(segment_cohort_raw) == 0:
    print("    No segment cohort data. Run cell 25 first.")
else:
    _DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
    _MUTED = GEN_COLORS.get('muted', '#6C757D')
    _GRID = GEN_COLORS.get('grid', '#E0E0E0')
    _RESP_COLOR = GEN_COLORS.get('success', '#2A9D8F')
    _NONRESP_COLOR = GEN_COLORS.get('warning', '#E9C46A')
    _ACCENT = GEN_COLORS.get('accent', '#E63946')
    _INFO = GEN_COLORS.get('info', '#457B9D')

    # Compute real numbers for the explainer
    _pre_cols = sorted([c for c in segment_cohort_raw.columns
                        if c.startswith('m-') and c[2:].lstrip('-').isdigit()
                        and 1 <= int(c[2:]) <= 3])
    _post_cols = sorted([c for c in segment_cohort_raw.columns
                         if c.startswith('m+') and c[2:].isdigit()
                         and 1 <= int(c[2:]) <= 3])

    _r = segment_cohort_raw[segment_cohort_raw['status'] == 'Responder']
    _nr = segment_cohort_raw[segment_cohort_raw['status'] == 'Non-Responder']

    r_pre = _r[_pre_cols].mean(axis=1).mean() if len(_pre_cols) > 0 else 0
    r_post = _r[_post_cols].mean(axis=1).mean() if len(_post_cols) > 0 else 0
    nr_pre = _nr[_pre_cols].mean(axis=1).mean() if len(_pre_cols) > 0 else 0
    nr_post = _nr[_post_cols].mean(axis=1).mean() if len(_post_cols) > 0 else 0

    r_change = r_post - r_pre
    nr_change = nr_post - nr_pre
    did = r_change - nr_change

    # ------------------------------------------------------------------
    # Build explainer figure
    # ------------------------------------------------------------------
    fig = plt.figure(figsize=(22, 13))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.30,
                          top=0.85, bottom=0.06, left=0.06, right=0.94)

    # =====================================================================
    # TOP-LEFT: The concept (slope chart)
    # =====================================================================
    ax1 = fig.add_subplot(gs[0, 0])

    # Plot the two lines: before → after
    ax1.plot([0, 1], [r_pre, r_post], color=_RESP_COLOR, linewidth=4,
             marker='o', markersize=14, markeredgecolor='white', markeredgewidth=2,
             zorder=5, label='Responders')
    ax1.plot([0, 1], [nr_pre, nr_post], color=_NONRESP_COLOR, linewidth=4,
             marker='s', markersize=14, markeredgecolor='white', markeredgewidth=2,
             zorder=5, label='Non-Responders')

    # Dotted counterfactual: where responders WOULD have been without the program
    _counterfactual = r_pre + nr_change
    ax1.plot([0, 1], [r_pre, _counterfactual], color=_RESP_COLOR, linewidth=2,
             linestyle=':', alpha=0.5, zorder=3)
    ax1.plot(1, _counterfactual, marker='o', markersize=10, color=_RESP_COLOR,
             alpha=0.4, zorder=3)

    # DID bracket on the right
    _bracket_x = 1.08
    ax1.annotate('', xy=(_bracket_x, _counterfactual), xytext=(_bracket_x, r_post),
                 arrowprops=dict(arrowstyle='<->', color=_ACCENT, lw=2.5))
    ax1.text(_bracket_x + 0.05, (_counterfactual + r_post) / 2,
             f'DID\n${did:+,.0f}/mo',
             fontsize=14, fontweight='bold', color=_ACCENT, va='center')

    # Labels on the dots
    ax1.text(-0.05, r_pre, f'${r_pre:,.0f}', ha='right', va='center',
             fontsize=14, fontweight='bold', color=_RESP_COLOR)
    ax1.text(-0.05, nr_pre, f'${nr_pre:,.0f}', ha='right', va='center',
             fontsize=14, fontweight='bold', color=_NONRESP_COLOR)
    ax1.text(0.55, r_post + (r_post - nr_post) * 0.08, f'${r_post:,.0f}',
             ha='center', va='bottom', fontsize=14, fontweight='bold', color=_RESP_COLOR)
    ax1.text(0.55, nr_post - (r_post - nr_post) * 0.08, f'${nr_post:,.0f}',
             ha='center', va='top', fontsize=14, fontweight='bold', color=_NONRESP_COLOR)

    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(['Before Mail', 'After Mail'], fontsize=14, fontweight='bold')
    ax1.set_ylabel('Avg Monthly Spend', fontsize=16, fontweight='bold', labelpad=8)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax1.set_xlim(-0.2, 1.35)
    ax1.legend(fontsize=14, framealpha=0.9, loc='upper left')
    ax1.set_title('The DID Concept',
                   fontsize=16, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax1, keep_left=True, keep_bottom=True)
    ax1.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax1.set_axisbelow(True)

    # =====================================================================
    # TOP-RIGHT: The math (text panel)
    # =====================================================================
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis('off')

    _lines = [
        ('The Question:', _DARK, 16, 'bold', 0.95),
        ('"Did the mailer actually change behavior,', _MUTED, 13, 'normal', 0.88),
        ('  or would spending have changed anyway?"', _MUTED, 13, 'normal', 0.82),
        ('', '', 0, '', 0.78),
        ('The Math:', _DARK, 16, 'bold', 0.72),
        ('', '', 0, '', 0.68),
        (f'  Responders:      ${r_pre:,.0f} → ${r_post:,.0f}  ({r_change:+,.0f}/mo)', _RESP_COLOR, 13, 'bold', 0.63),
        (f'  Non-Responders:  ${nr_pre:,.0f} → ${nr_post:,.0f}  ({nr_change:+,.0f}/mo)', _NONRESP_COLOR, 13, 'bold', 0.56),
        ('', '', 0, '', 0.52),
        (f'  Natural trend (everyone changed):  {nr_change:+,.0f}/mo', _MUTED, 13, 'normal', 0.47),
        (f'  Responder extra lift:              {r_change:+,.0f} - ({nr_change:+,.0f})', _MUTED, 13, 'normal', 0.40),
        ('', '', 0, '', 0.36),
        (f'  DID = ${did:+,.0f}/mo per account', _ACCENT, 18, 'bold', 0.28),
        ('', '', 0, '', 0.22),
        ('This is the spend change we can attribute', _DARK, 12, 'normal', 0.16),
        ('to the ARS program, not seasonal trends.', _DARK, 12, 'normal', 0.10),
    ]

    for text, color, size, weight, y_pos in _lines:
        if text == '':
            continue
        ax2.text(0.05, y_pos, text, fontsize=size, fontweight=weight,
                 color=color, transform=ax2.transAxes, va='top',
                 family='monospace' if '$' in text and '→' in text else 'sans-serif')

    ax2.set_title('How DID Works',
                   fontsize=16, fontweight='bold', color=_DARK, pad=10)

    # =====================================================================
    # BOTTOM-LEFT: Why it matters (waterfall-style)
    # =====================================================================
    ax3 = fig.add_subplot(gs[1, 0])

    _waterfall_labels = ['Resp\nBefore', 'Natural\nTrend', 'Program\nLift', 'Resp\nAfter']
    _waterfall_bottoms = [0, r_pre, r_pre + nr_change, 0]
    _waterfall_heights = [r_pre, nr_change, did, r_post]
    _waterfall_colors = [_MUTED, _NONRESP_COLOR, _ACCENT if did > 0 else _MUTED, _RESP_COLOR]

    _wx = np.arange(len(_waterfall_labels))
    bars = ax3.bar(_wx, _waterfall_heights, bottom=_waterfall_bottoms, width=0.55,
                   color=_waterfall_colors, edgecolor='white', linewidth=1)

    # Connector lines
    for i in range(len(_wx) - 1):
        _top = _waterfall_bottoms[i] + _waterfall_heights[i]
        ax3.plot([_wx[i] + 0.275, _wx[i+1] - 0.275], [_top, _top],
                 color=_MUTED, linewidth=1, linestyle='--', alpha=0.5)

    # Value labels
    for i, (bar, val, bot) in enumerate(zip(bars, _waterfall_heights, _waterfall_bottoms)):
        _y = bot + val / 2 if i in [0, 3] else bot + val
        _va = 'center' if i in [0, 3] else ('bottom' if val >= 0 else 'top')
        _offset = 0 if i in [0, 3] else (3 if val >= 0 else -3)
        _fmt = f'${val:,.0f}' if i in [0, 3] else f'${val:+,.0f}/mo'
        ax3.text(bar.get_x() + bar.get_width() / 2, _y + _offset,
                 _fmt, ha='center', va=_va, fontsize=14,
                 fontweight='bold', color='white' if i in [0, 3] else _waterfall_colors[i])

    ax3.set_xticks(_wx)
    ax3.set_xticklabels(_waterfall_labels, fontsize=14, fontweight='bold')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax3.set_ylabel('Avg Monthly Spend', fontsize=16, fontweight='bold', labelpad=8)
    ax3.set_title('Breaking Down the Change',
                   fontsize=16, fontweight='bold', color=_DARK, pad=10)
    gen_clean_axes(ax3, keep_left=True, keep_bottom=True)
    ax3.yaxis.grid(True, color=_GRID, linewidth=0.5, alpha=0.5)
    ax3.set_axisbelow(True)

    # =====================================================================
    # BOTTOM-RIGHT: Plain-English summary
    # =====================================================================
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')

    _summary = [
        ('In Plain English:', _DARK, 18, 'bold', 0.92),
        ('', '', 0, '', 0.86),
        ('Both responders and non-responders', _DARK, 14, 'normal', 0.80),
        ('saw spending changes after the mailer.', _DARK, 14, 'normal', 0.74),
        ('', '', 0, '', 0.68),
        ('Non-responders show the natural trend', _NONRESP_COLOR, 14, 'bold', 0.62),
        ('(what would have happened anyway).', _MUTED, 13, 'normal', 0.56),
        ('', '', 0, '', 0.50),
        ('Responders changed MORE than that.', _RESP_COLOR, 14, 'bold', 0.44),
        ('', '', 0, '', 0.38),
        ('The difference is what the', _DARK, 14, 'normal', 0.32),
        ('ARS program actually drove.', _DARK, 14, 'bold', 0.26),
        ('', '', 0, '', 0.18),
    ]

    # Add the punchline with a box
    for text, color, size, weight, y_pos in _summary:
        if text == '':
            continue
        ax4.text(0.08, y_pos, text, fontsize=size, fontweight=weight,
                 color=color, transform=ax4.transAxes, va='top')

    # Punchline card
    _punch = FancyBboxPatch(
        (0.03, 0.02), 0.94, 0.12,
        boxstyle="round,pad=0.02",
        facecolor=_ACCENT if did > 0 else _MUTED,
        edgecolor='white', linewidth=2, alpha=0.15,
        transform=ax4.transAxes
    )
    ax4.add_patch(_punch)
    ax4.text(0.50, 0.08,
             f'DID = ${did:+,.0f}/mo per account attributable to ARS',
             fontsize=15, fontweight='bold', color=_ACCENT if did > 0 else _MUTED,
             transform=ax4.transAxes, ha='center', va='center')

    ax4.set_title('The Takeaway',
                   fontsize=16, fontweight='bold', color=_DARK, pad=10)

    # Main title
    fig.suptitle('Understanding Difference-in-Differences (DID)',
                 fontsize=24, fontweight='bold', color=_DARK, y=0.95)
    fig.text(0.5, 0.905,
             'Isolating the true program impact from natural spending trends',
             ha='center', fontsize=14, color=_MUTED, style='italic')

    plt.show()
