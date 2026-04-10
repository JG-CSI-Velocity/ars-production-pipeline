# ===========================================================================
# SWIPE CATEGORY DATA: Read Pre-Computed Swipe Tiers from ODDD
# ===========================================================================
# SwipeCat3:  3-month avg monthly swipe category (text label from ODDD)
# SwipeCat12: 12-month avg monthly swipe category (text label from ODDD)
# Both are account-level fields on rewards_df. Labels auto-discovered.
# Builds: swipe_lookup, SWIPE3/12_ORDER, SWIPE3/12_PALETTE, swipe_summary_3/12.

try:
    _swipe_cat_fields = ['SwipeCat3', 'SwipeCat12']
    _swipe_cat_present = [f for f in _swipe_cat_fields if f in rewards_df.columns]

    if len(_swipe_cat_present) == 0:
        print("    No SwipeCat columns found in ODDD. Skipping swipe category data.")
        swipe_lookup = pd.DataFrame()
    else:
        # Select only needed columns (memory-safe, no full rewards_df copy)
        _swipe_cols = ['Acct Number'] + _swipe_cat_present
        for _opt in ['MonthlySwipes3', 'MonthlySwipes12',
                      'last 3-mon swipes', 'last 12-mon swipes', 'Total Swipes']:
            if _opt in rewards_df.columns:
                _swipe_cols.append(_opt)

        swipe_lookup = rewards_df[_swipe_cols].copy()
        swipe_lookup.rename(columns={'Acct Number': 'primary_account_num'}, inplace=True)
        swipe_lookup['primary_account_num'] = (
            swipe_lookup['primary_account_num'].astype(str).str.strip()
        )

        # Standardize column names
        _rename_map = {}
        if 'SwipeCat3' in swipe_lookup.columns:
            _rename_map['SwipeCat3'] = 'swipe_cat3'
        if 'SwipeCat12' in swipe_lookup.columns:
            _rename_map['SwipeCat12'] = 'swipe_cat12'
        if 'MonthlySwipes3' in swipe_lookup.columns:
            _rename_map['MonthlySwipes3'] = 'monthly_swipes3'
        if 'MonthlySwipes12' in swipe_lookup.columns:
            _rename_map['MonthlySwipes12'] = 'monthly_swipes12'
        swipe_lookup.rename(columns=_rename_map, inplace=True)

        # Convert numeric columns
        for _nc in ['monthly_swipes3', 'monthly_swipes12',
                     'last 3-mon swipes', 'last 12-mon swipes', 'Total Swipes']:
            if _nc in swipe_lookup.columns:
                swipe_lookup[_nc] = pd.to_numeric(swipe_lookup[_nc], errors='coerce')

        # Drop rows where both SwipeCat columns are null
        _cat_cols = [c for c in ['swipe_cat3', 'swipe_cat12'] if c in swipe_lookup.columns]
        swipe_lookup = swipe_lookup.dropna(subset=_cat_cols, how='all')

        # Clean category strings
        for _cc in _cat_cols:
            swipe_lookup[_cc] = swipe_lookup[_cc].astype(str).str.strip()

        # -----------------------------------------------------------------
        # Auto-discover label ordering by median monthly swipes
        # -----------------------------------------------------------------
        _base_colors = ['#E63946', '#FF9F1C', '#2EC4B6', '#457B9D', '#A8DADC',
                        '#6C757D', '#264653', '#F4A261', '#E76F51', '#1B2A4A']

        for _cat_col, _num_col, _label in [
            ('swipe_cat3', 'monthly_swipes3', '3-month'),
            ('swipe_cat12', 'monthly_swipes12', '12-month'),
        ]:
            if _cat_col not in swipe_lookup.columns:
                continue

            # Sort categories by median numeric swipes (highest first)
            if _num_col in swipe_lookup.columns:
                _medians = (
                    swipe_lookup.groupby(_cat_col)[_num_col]
                    .median()
                    .sort_values(ascending=False)
                )
                _discovered_order = _medians.index.tolist()
            else:
                # Fallback: alphabetical
                _discovered_order = sorted(swipe_lookup[_cat_col].dropna().unique())

            # Map discovered labels to palette colors (cycle if > 10 categories)
            _colors = (_base_colors * ((len(_discovered_order) // len(_base_colors)) + 1))
            _palette = {lbl: _colors[i] for i, lbl in enumerate(_discovered_order)}

            if _cat_col == 'swipe_cat3':
                SWIPE3_ORDER = _discovered_order
                SWIPE3_PALETTE = _palette
            else:
                SWIPE12_ORDER = _discovered_order
                SWIPE12_PALETTE = _palette

        # -----------------------------------------------------------------
        # Summary tables (one per window)
        # -----------------------------------------------------------------
        swipe_summary_3 = pd.DataFrame()
        swipe_summary_12 = pd.DataFrame()

        for _cat_col, _order_name, _summary_name in [
            ('swipe_cat3', 'SWIPE3_ORDER', '3-month'),
            ('swipe_cat12', 'SWIPE12_ORDER', '12-month'),
        ]:
            if _cat_col not in swipe_lookup.columns:
                continue
            _order = globals().get(_order_name, [])
            _total = len(swipe_lookup[swipe_lookup[_cat_col].notna()])
            _rows = []
            for _tier in _order:
                _tier_data = swipe_lookup[swipe_lookup[_cat_col] == _tier]
                _count = len(_tier_data)
                _avg_swipes = 0.0
                _num_col = 'monthly_swipes3' if '3' in _cat_col else 'monthly_swipes12'
                if _num_col in _tier_data.columns:
                    _avg_swipes = _tier_data[_num_col].mean()
                _rows.append({
                    'tier': _tier,
                    'account_count': _count,
                    'acct_pct': (_count / _total * 100) if _total > 0 else 0,
                    'avg_monthly_swipes': _avg_swipes,
                })
            _df = pd.DataFrame(_rows)
            if _summary_name == '3-month':
                swipe_summary_3 = _df
            else:
                swipe_summary_12 = _df

        # -----------------------------------------------------------------
        # Summary print
        # -----------------------------------------------------------------
        print("Swipe category data built.")
        print(f"  Accounts with swipe data: {len(swipe_lookup):,}")

        for _name, _df in [('3-month', swipe_summary_3), ('12-month', swipe_summary_12)]:
            if _df is not None and len(_df) > 0:
                print(f"\n  {_name} SwipeCat distribution:")
                for _, _row in _df.iterrows():
                    _swipe_str = f"  avg {_row['avg_monthly_swipes']:.1f}/mo" if _row['avg_monthly_swipes'] > 0 else ""
                    print(f"    {_row['tier']:>15s}: {_row['account_count']:>6,} "
                          f"({_row['acct_pct']:.1f}%){_swipe_str}")

except (NameError, KeyError) as e:
    print(f"    Swipe category data not available: {e}")
    swipe_lookup = pd.DataFrame()
