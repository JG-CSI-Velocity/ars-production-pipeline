# ===========================================================================
# MOMENTUM: Fastest Growing vs Declining Banks (Conference Edition)
# ===========================================================================
# Diverging horizontal bar chart. Growing = right (red). Declining = left (green).
# Uses a UNIFIED 3-month window (last 3 months of the dataset) so every
# competitor is compared on the same dates. Underneath the chart we print
# a detail table with absolute volumes so that "Capital One is declining"
# can be read alongside "...but still the Nth largest competitor".

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES

    # -----------------------------------------------------------------------
    # 1) Unified date windows — same recent_3 and previous_3 for every bank.
    # -----------------------------------------------------------------------
    if 'year_month' not in combined_df.columns:
        combined_df = combined_df.assign(
            year_month=pd.to_datetime(combined_df['transaction_date']).dt.to_period('M')
        )
    _all_months = sorted(combined_df['year_month'].dropna().unique())

    if len(_all_months) < 6:
        print("Insufficient data for momentum analysis (need 6+ months of transactions).")
    else:
        RECENT_3   = _all_months[-3:]
        PREVIOUS_3 = _all_months[-6:-3]

        def _period_label(periods):
            """'Jan26 - Mar26' style label from a list of pd.Period months."""
            _starts = [p.strftime('%b%y') for p in periods]
            return f"{_starts[0]} - {_starts[-1]}"

        RECENT_LABEL   = _period_label(RECENT_3)
        PREVIOUS_LABEL = _period_label(PREVIOUS_3)

        print(f"    Momentum window : RECENT ({RECENT_LABEL}) vs PREVIOUS ({PREVIOUS_LABEL})")

        # -------------------------------------------------------------------
        # 2) Per-competitor momentum — using the SAME window for every bank.
        # -------------------------------------------------------------------
        momentum_data = []
        for competitor, competitor_trans in all_competitor_data.items():
            category = competitor_trans['competitor_category'].iloc[0]
            if category not in bank_categories:
                continue

            if 'year_month' not in competitor_trans.columns:
                competitor_trans['year_month'] = pd.to_datetime(
                    competitor_trans['transaction_date']
                ).dt.to_period('M')

            _recent = competitor_trans[competitor_trans['year_month'].isin(RECENT_3)]
            _prev   = competitor_trans[competitor_trans['year_month'].isin(PREVIOUS_3)]

            recent_txn  = len(_recent)
            prev_txn    = len(_prev)
            recent_acct = _recent['primary_account_num'].nunique()
            prev_acct   = _prev['primary_account_num'].nunique()
            recent_spend = float(_recent['amount'].sum())
            prev_spend   = float(_prev['amount'].sum())

            txn_growth    = ((recent_txn  - prev_txn)  / prev_txn  * 100) if prev_txn  > 0 else 0
            acct_growth   = ((recent_acct - prev_acct) / prev_acct * 100) if prev_acct > 0 else 0
            spend_growth  = ((recent_spend - prev_spend) / prev_spend * 100) if prev_spend > 0 else 0

            # Require at least 50 recent txns so single-digit flutters don't
            # show up as "+400% growth" from 5 → 25 transactions.
            if recent_txn < 50:
                continue

            momentum_data.append({
                'bank':          competitor,
                'category':      category,
                'recent_txn':    recent_txn,
                'prev_txn':      prev_txn,
                'txn_growth':    txn_growth,
                'recent_acct':   recent_acct,
                'prev_acct':     prev_acct,
                'acct_growth':   acct_growth,
                'recent_spend':  recent_spend,
                'prev_spend':    prev_spend,
                'spend_growth':  spend_growth,
            })

        if len(momentum_data) == 0:
            mdf = pd.DataFrame()
        else:
            mdf = pd.DataFrame(momentum_data)
            mdf['category_label'] = mdf['category'].str.replace('_', ' ').str.title()

        # Top 8 growers + Top 7 decliners (show both sides)
        growers = mdf[mdf['txn_growth'] > 0].sort_values('txn_growth', ascending=False).head(8) if len(mdf) else pd.DataFrame()
        decliners = mdf[mdf['txn_growth'] < 0].sort_values('txn_growth', ascending=True).head(7) if len(mdf) else pd.DataFrame()
        show_df = pd.concat([growers, decliners]).sort_values('txn_growth', ascending=True) if len(mdf) else pd.DataFrame()

        if len(show_df) > 0:
            # Shorten names
            show_df['short_name'] = show_df['bank'].apply(
                lambda n: n[:25] + '..' if len(str(n)) > 27 else n
            )

            fig, ax = plt.subplots(figsize=(14, 9))

            # Bar colors: two sequential colormaps keyed to recent account
            # count. Threats (growers) use Reds; opportunities (decliners)
            # use Blues. Darker = more accounts using that competitor.
            # Direction is still conveyed by left/right position AND hue.
            import matplotlib as _mpl
            _cmap_threat = _mpl.colormaps.get_cmap('Reds')
            _cmap_opp    = _mpl.colormaps.get_cmap('Blues')
            _acct_vals = show_df['recent_acct'].astype(float).values
            _acct_max  = float(_acct_vals.max()) if len(_acct_vals) and _acct_vals.max() > 0 else 1.0
            # Squeeze into [0.30, 0.90] so the smallest bar isn't invisible-white
            # and the largest isn't black.
            _intensity = 0.30 + (_acct_vals / _acct_max) * 0.60
            _growths   = show_df['txn_growth'].values
            bar_colors = [
                (_cmap_threat(v) if g > 0 else _cmap_opp(v))
                for g, v in zip(_growths, _intensity)
            ]

            bars = ax.barh(
                range(len(show_df)),
                show_df['txn_growth'],
                color=bar_colors,
                edgecolor='white',
                linewidth=1,
                height=0.65,
                zorder=3
            )

            # Value labels — always anchored to the zero line on the opposite
            # side of the bar, so negative-growth labels can't bleed into the
            # competitor-name yticklabels on the far left.
            _x_max = float(show_df['txn_growth'].abs().max())
            _label_offset = max(0.8, _x_max * 0.02)
            for i, (_, row) in enumerate(show_df.iterrows()):
                if row['txn_growth'] >= 0:
                    # Growing bar extends right → label to the right of the bar tip
                    _x = row['txn_growth'] + _label_offset
                    _ha = 'left'
                else:
                    # Declining bar extends left → put the label on the RIGHT
                    # of the zero line (the center of the chart), never near
                    # the bank-name yticks.
                    _x = _label_offset
                    _ha = 'left'
                ax.text(
                    _x, i, f"{row['txn_growth']:+.1f}%",
                    fontsize=12, fontweight='bold',
                    color=GEN_COLORS['dark_text'],
                    va='center', ha=_ha,
                )

            ax.set_yticks(range(len(show_df)))
            ax.set_yticklabels(show_df['short_name'], fontsize=13, fontweight='bold')

            # Center line
            ax.axvline(x=0, color=GEN_COLORS['dark_text'], linewidth=2, zorder=5)

            # Labels — surface the actual dates so the reader isn't guessing.
            ax.set_xlabel(
                f"Transaction Growth:  {RECENT_LABEL}  vs  {PREVIOUS_LABEL}",
                fontsize=16, fontweight='bold', labelpad=12,
            )
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.0f}%"))

            gen_clean_axes(ax)
            ax.xaxis.grid(True, color=GEN_COLORS['grid'], linewidth=0.5, alpha=0.5)
            ax.set_axisbelow(True)

            # Title — pushed up, with generous pad so the subtitle and the
            # THREAT/OPPORTUNITY side labels don't crowd into it.
            ax.set_title("Competitive Momentum",
                         fontsize=28, fontweight='bold',
                         color=GEN_COLORS['dark_text'], pad=44, loc='left')
            # Subtitle lives ABOVE the axes (y=1.06) so it can't overlap bars.
            ax.text(0.0, 1.06, "Who is gaining?  Who is losing?",
                    transform=ax.transAxes, fontsize=15,
                    color=GEN_COLORS['muted'], style='italic')

            # THREAT / OPPORTUNITY direction labels — placed in the figure
            # margin (below the x-axis label) via fig.text so they can't
            # collide with the bars, value labels, or competitor names.
            fig.text(0.75, 0.03, "THREAT  →",
                     fontsize=13, fontweight='bold', color='#C62828',
                     alpha=0.75, ha='center')
            fig.text(0.25, 0.03, "←  OPPORTUNITY",
                     fontsize=13, fontweight='bold', color='#1565C0',
                     alpha=0.75, ha='center')

            # Bubble-size-equivalent legend text for the heatmap
            ax.text(0.99, 1.06,
                    "Darker bars = more accounts using that competitor",
                    transform=ax.transAxes, fontsize=11,
                    color=GEN_COLORS['muted'], style='italic', ha='right')

            plt.tight_layout()
            plt.subplots_adjust(top=0.86, bottom=0.18)   # extra bottom room for THREAT/OPPORTUNITY labels
            plt.show()

            # Opportunity callout
            if len(decliners) > 0:
                # Distinct-count across ALL declining banks so one account active
                # at multiple declining banks isn't counted multiple times.
                _dec_names = set(decliners['bank'])
                _dec_txns  = competitor_txns[competitor_txns['competitor_match'].isin(_dec_names)]
                total_declining_acct = int(_dec_txns['primary_account_num'].nunique())
                print(f"\n    OPPORTUNITY: {len(decliners)} banks losing momentum.")
                print(f"    {total_declining_acct:,} accounts showing reduced competitor activity.")
                print("    These customers may be ready to consolidate -- target with retention offers.")

        # ---------------------------------------------------------------
        # 3) Detail table — absolute volumes alongside growth %s so a
        #    "declining" bank with 50,000 recent transactions doesn't get
        #    confused with a "declining" bank that has 60. Capital One
        #    should show as declining-but-still-huge here, answering the
        #    "why does this look odd?" question directly.
        # ---------------------------------------------------------------
        if len(mdf) > 0:
            _detail = mdf.sort_values('recent_txn', ascending=False).copy()
            _detail['_trend'] = _detail['txn_growth'].apply(
                lambda g: '↑ GROW' if g > 0 else ('↓ DEC' if g < 0 else '=')
            )
            _display = pd.DataFrame({
                'Bank':                      _detail['bank'],
                'Category':                  _detail['category_label'],
                'Trend':                     _detail['_trend'],
                f'Txns ({RECENT_LABEL})':    _detail['recent_txn'].map('{:,}'.format),
                f'Txns ({PREVIOUS_LABEL})':  _detail['prev_txn'].map('{:,}'.format),
                'Txn Growth %':              _detail['txn_growth'].map('{:+.1f}%'.format),
                f'Accts ({RECENT_LABEL})':   _detail['recent_acct'].map('{:,}'.format),
                'Acct Growth %':             _detail['acct_growth'].map('{:+.1f}%'.format),
                f'Spend ({RECENT_LABEL})':   _detail['recent_spend'].map('${:,.0f}'.format),
                'Spend Growth %':            _detail['spend_growth'].map('{:+.1f}%'.format),
            })
            try:
                display_formatted(_display, f"Momentum Detail — {RECENT_LABEL} vs {PREVIOUS_LABEL}")
            except (NameError, Exception):
                print("\n--- Momentum Detail ---")
                print(_display.to_string(index=False))

