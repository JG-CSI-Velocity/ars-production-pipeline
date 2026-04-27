# ===========================================================================
# COMPETITOR COUNT DISTRIBUTION: how many competitors does each account use?
# ===========================================================================
# Mirrors financial_services/13_category_combinations style of analysis but
# at the COMPETITOR-COUNT level instead of category co-occurrence:
#
#   How many accounts use 1 competitor? 2-3? 4-5? 6-7? More?
#
# Same intent as the user's existing financial-services-categories analysis
# applied to the competition section. Excludes wallets/BNPL/P2P by default
# since those are payment ecosystems, not banking competitors -- the
# question is "how many ALTERNATIVE BANKS are members shopping at?".
#
# Toggle COMPETITOR_COUNT_INCLUDE_ECOSYSTEMS = True if you want a parallel
# all-competitors view that includes ecosystems.
#
# Inputs (from competition/02_competitor_detection):
#   competitor_txns          DataFrame with primary_account_num, competitor_match,
#                            competitor_category
#   BANK_CATEGORIES          list of category keys excluding wallets/p2p/bnpl
#   GEN_COLORS, member_word, MEMBER_NOUN_PLURAL  from general theme
# ===========================================================================

import pandas as _pd_cc
import numpy as _np_cc
import matplotlib.pyplot as _plt_cc
from matplotlib.patches import FancyBboxPatch as _FancyBox

# Optional toggle (defaults to bank-only count)
COMPETITOR_COUNT_INCLUDE_ECOSYSTEMS = bool(globals().get(
    "COMPETITOR_COUNT_INCLUDE_ECOSYSTEMS", False))

# Defensive bootstrap -- same pattern as the 60-series cells.
_BOOT_OK = True
try:
    competitor_txns
except NameError:
    print("    Skipping cell 35 -- competitor_txns missing. Run cell 02 first.")
    _BOOT_OK = False

try:
    BANK_CATEGORIES
except NameError:
    try:
        BANK_CATEGORIES = [k for k in COMPETITOR_MERCHANTS
                           if k not in ('wallets', 'p2p', 'bnpl')]
    except NameError:
        BANK_CATEGORIES = []

# Colors / language fallback
_GEN = globals().get('GEN_COLORS', {
    'accent': '#E63946', 'info': '#457B9D', 'success': '#2EC4B6',
    'warning': '#FF9F1C', 'dark_text': '#1B2A4A', 'muted': '#6C757D',
    'grid': '#E0E0E0',
})
_M_WORD_PL = globals().get('MEMBER_NOUN_PLURAL', 'members')
_M_WORD_TI = globals().get('MEMBER_NOUN_TITLE_PL', 'Members')

if _BOOT_OK:
    # ---------------------------------------------------------------
    # Filter the txn set: bank-categories only (or all, per toggle)
    # ---------------------------------------------------------------
    if COMPETITOR_COUNT_INCLUDE_ECOSYSTEMS:
        _ctx = competitor_txns.copy()
        _scope_label = "All competitors (banks + payment ecosystems)"
    else:
        _ctx = competitor_txns[
            competitor_txns['competitor_category'].isin(BANK_CATEGORIES)
        ].copy()
        _scope_label = "Banking competitors only (wallets/BNPL/P2P excluded)"

    if len(_ctx) == 0:
        print("    No competitor txns in scope -- skipping cell 35.")
    else:
        # ---------------------------------------------------------------
        # Per-account distinct competitor count
        # ---------------------------------------------------------------
        _per_acct = (
            _ctx.groupby('primary_account_num')['competitor_match']
            .nunique()
            .reset_index(name='n_competitors')
        )

        # Bucket per the user spec: 1, 2-3, 4-5, 6-7, 8+
        def _bucket(n):
            if n == 1:
                return '1'
            if 2 <= n <= 3:
                return '2-3'
            if 4 <= n <= 5:
                return '4-5'
            if 6 <= n <= 7:
                return '6-7'
            return '8+'
        _per_acct['bucket'] = _per_acct['n_competitors'].apply(_bucket)

        _bucket_order = ['1', '2-3', '4-5', '6-7', '8+']
        _by_bucket = (
            _per_acct.groupby('bucket').size().reindex(_bucket_order, fill_value=0)
        )
        _total_competitor_accts = int(_by_bucket.sum())
        _by_bucket_pct = (_by_bucket / max(_total_competitor_accts, 1)) * 100

        # Total portfolio for the no-competitor pct
        try:
            _total_portfolio = combined_df['primary_account_num'].nunique()
        except Exception:
            _total_portfolio = _total_competitor_accts
        _no_competitor = max(_total_portfolio - _total_competitor_accts, 0)
        _no_competitor_pct = _no_competitor / max(_total_portfolio, 1) * 100

        # ---------------------------------------------------------------
        # Visual: 2-panel
        #   Left: bar chart of bucketed distribution
        #   Right: KPI cards summarizing single-vs-multi competitor mix
        # ---------------------------------------------------------------
        fig, (ax1, ax2) = _plt_cc.subplots(
            1, 2, figsize=(20, 7), gridspec_kw={'width_ratios': [3, 2]},
        )

        # --- LEFT: Bucket bar ---
        _bar_colors = [
            _GEN['info'], _GEN['info'], _GEN['warning'], _GEN['accent'], _GEN['accent']
        ]
        _bars = ax1.bar(
            range(len(_bucket_order)), _by_bucket.values,
            color=_bar_colors, edgecolor='white', linewidth=1.2, width=0.78,
        )
        for i, (bar, n, pct) in enumerate(zip(_bars, _by_bucket.values, _by_bucket_pct.values)):
            ax1.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + max(_by_bucket.max() * 0.02, 1),
                     f"{int(n):,}\n({pct:.1f}%)",
                     ha='center', va='bottom', fontsize=13,
                     fontweight='bold', color=_GEN['dark_text'])

        ax1.set_xticks(range(len(_bucket_order)))
        ax1.set_xticklabels(_bucket_order, fontsize=14, fontweight='bold')
        ax1.set_xlabel(f"Number of distinct competitors used per {globals().get('MEMBER_NOUN', 'member')}",
                       fontsize=13, fontweight='bold', labelpad=10)
        ax1.set_ylabel(f"{_M_WORD_TI} ({_M_WORD_PL})", fontsize=13, fontweight='bold')
        ax1.set_title("Competitor-Count Distribution",
                      fontsize=20, fontweight='bold',
                      color=_GEN['dark_text'], loc='left', pad=10)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.yaxis.grid(True, color=_GEN['grid'], linewidth=0.5, alpha=0.7)
        ax1.set_axisbelow(True)
        ax1.set_ylim(0, _by_bucket.max() * 1.20 if _by_bucket.max() > 0 else 1)

        # --- RIGHT: KPI cards ---
        _single = int(_by_bucket.get('1', 0))
        _multi = _total_competitor_accts - _single
        _heavy = int(_by_bucket.get('6-7', 0)) + int(_by_bucket.get('8+', 0))
        _kpis = [
            (f"{_no_competitor:,}",
             f"{_M_WORD_TI} with NO\ncompetitor activity",
             f"{_no_competitor_pct:.1f}% of portfolio",
             _GEN['success']),
            (f"{_single:,}",
             f"Use exactly 1\ncompetitor",
             f"{(_single / max(_total_portfolio, 1) * 100):.1f}% of portfolio",
             _GEN['info']),
            (f"{_multi:,}",
             f"Use 2+ competitors\n(actively shopping)",
             f"{(_multi / max(_total_portfolio, 1) * 100):.1f}% of portfolio",
             _GEN['warning']),
            (f"{_heavy:,}",
             f"Use 6+ competitors\n(deeply diversified)",
             f"{(_heavy / max(_total_portfolio, 1) * 100):.1f}% of portfolio",
             _GEN['accent']),
        ]
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')
        for i, (val, label, sub, color) in enumerate(_kpis):
            y0 = 0.78 - i * 0.22
            card = _FancyBox((0.04, y0), 0.92, 0.18,
                             boxstyle="round,pad=0.02",
                             facecolor=color, alpha=0.10,
                             edgecolor=color, linewidth=2,
                             transform=ax2.transAxes)
            ax2.add_patch(card)
            ax2.text(0.10, y0 + 0.10, val, transform=ax2.transAxes,
                     fontsize=28, fontweight='bold', color=color, va='center')
            ax2.text(0.50, y0 + 0.13, label, transform=ax2.transAxes,
                     fontsize=12, fontweight='bold',
                     color=_GEN['dark_text'], va='center', ha='left')
            ax2.text(0.50, y0 + 0.04, sub, transform=ax2.transAxes,
                     fontsize=10.5, color=_GEN['muted'], va='center', ha='left')

        # Title (use universal layout constants)
        _title_y = globals().get('GEN_TITLE_Y', 0.97)
        _subtitle_y = globals().get('GEN_SUBTITLE_Y', 0.92)
        _top_pad = globals().get('GEN_TOP_PAD', 0.85)
        fig.suptitle(f"How Many Competitors Do {_M_WORD_TI} Use?",
                     fontsize=24, fontweight='bold',
                     color=_GEN['dark_text'], y=_title_y)
        fig.text(0.5, _subtitle_y, _scope_label,
                 ha='center', fontsize=12, color=_GEN['muted'], style='italic')
        _plt_cc.subplots_adjust(top=_top_pad, bottom=0.13, left=0.07, right=0.97, wspace=0.25)
        _plt_cc.show()

        # ---------------------------------------------------------------
        # Console summary
        # ---------------------------------------------------------------
        print()
        print("=" * 60)
        print(f"  COMPETITOR-COUNT DISTRIBUTION  ({_scope_label})")
        print("=" * 60)
        print(f"  Total {_M_WORD_PL} in portfolio:        {_total_portfolio:>9,}")
        print(f"  {_M_WORD_TI} with NO competitor activity: {_no_competitor:>9,}  ({_no_competitor_pct:.1f}%)")
        print(f"  {_M_WORD_TI} with competitor activity:    {_total_competitor_accts:>9,}  "
              f"({(100 - _no_competitor_pct):.1f}%)")
        print()
        print(f"  Of those with competitor activity:")
        for bucket in _bucket_order:
            n = int(_by_bucket.get(bucket, 0))
            pct = _by_bucket_pct.get(bucket, 0)
            print(f"    {bucket:<5s} competitors:  {n:>8,}  ({pct:.1f}%)")
        print("=" * 60)
