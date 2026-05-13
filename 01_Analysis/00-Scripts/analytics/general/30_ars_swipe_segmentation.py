# ===========================================================================
# ARS SWIPE SEGMENTATION: monthly swipes per account, 3-month vs 12-month
# ===========================================================================
# User spec from 4/27 deck review (issue #95):
#   ``We have segmentation by spend and swipes. Need to align on ARS:
#     <1 swipe/mo (Avg), 1-5, 6-10, 11-15, 16-20, 21-25, 25+
#     These are 3-month average counts, and I'd like to see 12-month avgs.
#     Active and declining is good, keep that.''
#
# Output:
#   * Side-by-side bars: 3-month rolling avg bucket vs 12-month avg bucket.
#     Same bucket -> stable. Lower 3m than 12m -> declining (yellow flag).
#     Higher 3m than 12m -> active / growing (green flag).
#   * Stable / Active / Declining KPI cards on the right.
#
# Inputs (from txn_setup):
#   combined_df with primary_account_num, year_month, transaction_type
# ===========================================================================

import pandas as _pd_swipe
import matplotlib.pyplot as _plt_swipe
from matplotlib.patches import FancyBboxPatch as _FB

# Defensive: only run if combined_df + helpers are present
if 'combined_df' not in dir() or 'compute_swipe_segmentation' not in dir():
    print("    Skipping ARS swipe segmentation -- combined_df or helper missing.")
else:
    _seg = compute_swipe_segmentation(combined_df)
    if len(_seg) == 0:
        print("    No swipe data available for ARS segmentation.")
    else:
        _GEN = globals().get('GEN_COLORS', {
            'accent': '#E63946', 'info': '#457B9D', 'success': '#2EC4B6',
            'warning': '#FF9F1C', 'dark_text': '#1B2A4A', 'muted': '#6C757D',
            'grid': '#E0E0E0',
        })
        _PAL = globals().get('ARS_SWIPE_PALETTE', {})
        _ORD = globals().get('ARS_SWIPE_ORDER', [])
        _M_TI = globals().get('MEMBER_NOUN_TITLE_PL', 'Members')
        _M_PL = globals().get('MEMBER_NOUN_PLURAL', 'members')

        # Counts per bucket for both windows
        _c3  = _seg['bucket_3m'].value_counts().reindex(_ORD, fill_value=0)
        _c12 = _seg['bucket_12m'].value_counts().reindex(_ORD, fill_value=0)
        _total = max(int(_c12.sum()), 1)

        # Stable / Active / Declining flags: compare each account's 3m vs 12m
        # bucket position in the ordered list. Higher index = more swipes.
        _idx = {label: i for i, label in enumerate(_ORD)}
        _seg['_3m_idx']  = _seg['bucket_3m'].map(_idx).fillna(0).astype(int)
        _seg['_12m_idx'] = _seg['bucket_12m'].map(_idx).fillna(0).astype(int)
        _stable    = int((_seg['_3m_idx'] == _seg['_12m_idx']).sum())
        _active    = int((_seg['_3m_idx'] >  _seg['_12m_idx']).sum())
        _declining = int((_seg['_3m_idx'] <  _seg['_12m_idx']).sum())

        # ---------------------------------------------------------------
        # Chart: side-by-side 3m vs 12m bars per bucket
        # ---------------------------------------------------------------
        fig, (ax1, ax2) = _plt_swipe.subplots(
            1, 2, figsize=(20, 7),
            gridspec_kw={'width_ratios': [3.5, 2]},
        )

        import numpy as _np_swipe
        x = _np_swipe.arange(len(_ORD))
        bar_w = 0.4
        _bars12 = ax1.bar(x - bar_w / 2, _c12.values, bar_w,
                          label='12-month avg',
                          color=_GEN['info'], edgecolor='white', linewidth=1.0)
        _bars3 = ax1.bar(x + bar_w / 2, _c3.values, bar_w,
                         label='3-month avg (recent)',
                         color=_GEN['accent'], edgecolor='white', linewidth=1.0)

        for bar, n in zip(_bars12, _c12.values):
            if n > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + max(_c12.max() * 0.015, 1),
                         f"{int(n):,}", ha='center', va='bottom', fontsize=10,
                         fontweight='bold', color=_GEN['info'])
        for bar, n in zip(_bars3, _c3.values):
            if n > 0:
                ax1.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + max(_c3.max() * 0.015, 1),
                         f"{int(n):,}", ha='center', va='bottom', fontsize=10,
                         fontweight='bold', color=_GEN['accent'])

        ax1.set_xticks(x)
        ax1.set_xticklabels(_ORD, fontsize=12, fontweight='bold', rotation=0)
        ax1.set_xlabel("Monthly swipes per account",
                       fontsize=13, fontweight='bold', labelpad=8)
        ax1.set_ylabel(f"{_M_TI}", fontsize=13, fontweight='bold')
        ax1.set_title(f"ARS Swipe Segmentation -- 3-month vs 12-month avg",
                      fontsize=18, fontweight='bold',
                      color=_GEN['dark_text'], loc='left', pad=10)
        ax1.legend(loc='upper right', fontsize=12, frameon=False)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.yaxis.grid(True, color=_GEN['grid'], linewidth=0.5, alpha=0.7)
        ax1.set_axisbelow(True)
        _max_count = max(_c3.max(), _c12.max(), 1)
        ax1.set_ylim(0, _max_count * 1.18)

        # --- KPI cards: Stable / Active / Declining ---
        _kpis = [
            (f"{_stable:,}",
             "Stable\n(3m bucket = 12m)",
             f"{(_stable / _total * 100):.1f}% of {_M_PL}",
             _GEN['info']),
            (f"{_active:,}",
             f"Active / Growing\n(3m higher than 12m)",
             f"{(_active / _total * 100):.1f}% of {_M_PL}",
             _GEN['success']),
            (f"{_declining:,}",
             f"Declining\n(3m lower than 12m)",
             f"{(_declining / _total * 100):.1f}% of {_M_PL}",
             _GEN['accent']),
        ]
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')
        for i, (val, label, sub, color) in enumerate(_kpis):
            y0 = 0.72 - i * 0.28
            card = _FB((0.04, y0), 0.92, 0.22,
                      boxstyle="round,pad=0.02",
                      facecolor=color, alpha=0.10,
                      edgecolor=color, linewidth=2,
                      transform=ax2.transAxes)
            ax2.add_patch(card)
            ax2.text(0.10, y0 + 0.13, val, transform=ax2.transAxes,
                     fontsize=30, fontweight='bold', color=color, va='center')
            ax2.text(0.50, y0 + 0.16, label, transform=ax2.transAxes,
                     fontsize=12, fontweight='bold',
                     color=_GEN['dark_text'], va='center', ha='left')
            ax2.text(0.50, y0 + 0.06, sub, transform=ax2.transAxes,
                     fontsize=10.5, color=_GEN['muted'], va='center', ha='left')

        _title_y = globals().get('GEN_TITLE_Y', 0.97)
        _subtitle_y = globals().get('GEN_SUBTITLE_Y', 0.92)
        _top_pad = globals().get('GEN_TOP_PAD', 0.85)
        fig.suptitle(f"How active are {_M_PL} on their cards?",
                     fontsize=22, fontweight='bold',
                     color=_GEN['dark_text'], y=_title_y)
        fig.text(0.5, _subtitle_y,
                 "Recent vs steady state -- gaps between 3-month and 12-month "
                 "averages reveal who is changing behavior",
                 ha='center', fontsize=12, color=_GEN['muted'], style='italic')
        _plt_swipe.subplots_adjust(top=_top_pad, bottom=0.13,
                                   left=0.06, right=0.97, wspace=0.18)
        _plt_swipe.show()

        # ---------------------------------------------------------------
        # Console summary
        # ---------------------------------------------------------------
        print()
        print("=" * 64)
        print(f"  ARS SWIPE SEGMENTATION  ({_total:,} {_M_PL})")
        print("=" * 64)
        print(f"  Bucket            3m count    12m count   3m %     12m %")
        print(f"  ---------------- ----------  ----------  -------  -------")
        for bucket in _ORD:
            n3 = int(_c3.get(bucket, 0))
            n12 = int(_c12.get(bucket, 0))
            p3 = (n3 / _total) * 100
            p12 = (n12 / _total) * 100
            print(f"  {bucket:<16s} {n3:>10,}  {n12:>10,}  {p3:>5.1f}%   {p12:>5.1f}%")
        print()
        print(f"  Stable     (3m == 12m bucket): {_stable:>9,}  ({_stable / _total * 100:>5.1f}%)")
        print(f"  Active     (3m  > 12m bucket): {_active:>9,}  ({_active / _total * 100:>5.1f}%)")
        print(f"  Declining  (3m  < 12m bucket): {_declining:>9,}  ({_declining / _total * 100:>5.1f}%)")
        print("=" * 64)
