# ===========================================================================
# RELATIONSHIP DATA: Build Member Relationship Depth Profile
# ===========================================================================
# Aggregates product holdings per member from rewards_df, merges transaction
# activity from combined_df, and computes relationship depth scores.
# Produces: rel_df, product_combos_df

import pandas as pd
import numpy as np

try:
    # ------------------------------------------------------------------
    # 1. Product count per account from rewards_df
    # ------------------------------------------------------------------
    rewards_clean = rewards_df.copy()
    rewards_clean.columns = rewards_clean.columns.str.strip()

    acct_col = 'Acct Number'
    prod_col = 'Prod Code'
    prod_desc_col = 'Prod Desc'

    # Validate required columns exist
    required_cols = [acct_col, prod_col]
    missing = [c for c in required_cols if c not in rewards_clean.columns]
    if missing:
        raise KeyError(f"Missing columns in rewards_df: {missing}")

    rewards_clean[acct_col] = rewards_clean[acct_col].astype(str).str.strip()

    # Build product list per account
    acct_products = rewards_clean.groupby(acct_col).agg(
        product_count=(prod_col, 'nunique'),
        product_codes=(prod_col, lambda x: sorted(x.dropna().unique().tolist())),
        product_descriptions=(
            prod_desc_col if prod_desc_col in rewards_clean.columns else prod_col,
            lambda x: sorted(x.dropna().unique().tolist())
        ),
    ).reset_index()

    acct_products.rename(columns={acct_col: 'account_number'}, inplace=True)

    # Create product combination string for co-occurrence analysis
    acct_products['product_combination'] = acct_products['product_codes'].apply(
        lambda x: ' + '.join([str(p) for p in x])
    )

    # ------------------------------------------------------------------
    # 2. Merge balance and demographic data from rewards_df
    # ------------------------------------------------------------------
    demo_cols = {
        'Avg Bal': 'avg_bal',
        'Curr Bal': 'curr_bal',
        'Account Holder Age': 'member_age',
        'Account Age': 'account_age',
        'Business?': 'is_business',
        'Branch': 'branch',
    }

    available_demo = {k: v for k, v in demo_cols.items() if k in rewards_clean.columns}

    if available_demo:
        demo_agg = {}
        for orig, alias in available_demo.items():
            if orig in ('Avg Bal', 'Curr Bal'):
                demo_agg[alias] = (orig, 'mean')
            elif orig in ('Account Holder Age', 'Account Age'):
                demo_agg[alias] = (orig, 'first')
            else:
                demo_agg[alias] = (orig, 'first')

        demo_df = rewards_clean.groupby(acct_col).agg(**demo_agg).reset_index()
        demo_df.rename(columns={acct_col: 'account_number'}, inplace=True)
        demo_df['account_number'] = demo_df['account_number'].astype(str).str.strip()

        acct_products = acct_products.merge(demo_df, on='account_number', how='left')

    # ------------------------------------------------------------------
    # 3. Merge transaction activity from combined_df
    # ------------------------------------------------------------------
    txn_summary = combined_df.groupby('primary_account_num').agg(
        txn_count=('amount', 'count'),
        total_spend=('amount', 'sum'),
        avg_txn=('amount', 'mean'),
        last_txn_date=('transaction_date', 'max'),
        first_txn_date=('transaction_date', 'min'),
        active_months=('year_month', 'nunique'),
    ).reset_index()
    txn_summary.rename(columns={'primary_account_num': 'account_number'}, inplace=True)
    txn_summary['account_number'] = txn_summary['account_number'].astype(str).str.strip()

    rel_df = acct_products.merge(txn_summary, on='account_number', how='left')

    # Apply BranchMapping so 'branch' shows names not numeric IDs in downstream
    # groupby. Source of truth: 03_Config/clients_config.json -> BranchMapping.
    if 'branch' in rel_df.columns:
        try:
            from ars_analysis.shared.branch_mapping import apply_branch_names
            _clients_cfg = globals().get('_clients_config')
            _cid = globals().get('CLIENT_ID', '')
            apply_branch_names(rel_df, column='branch',
                               client_id=_cid, clients_config=_clients_cfg)
        except Exception as _be:
            print(f"    WARNING: could not apply branch names to rel_df ({_be}) -- using raw IDs")

    # Fill missing transaction data (members with products but no transactions)
    rel_df['txn_count'] = rel_df['txn_count'].fillna(0).astype(int)
    rel_df['total_spend'] = rel_df['total_spend'].fillna(0)
    rel_df['active_months'] = rel_df['active_months'].fillna(0).astype(int)

    # ------------------------------------------------------------------
    # 4. Compute relationship depth score
    # ------------------------------------------------------------------
    # Determine if active in last 3 months
    if 'last_txn_date' in rel_df.columns:
        cutoff_3mo = DATASET_END - pd.DateOffset(months=3)
        rel_df['active_last_3mo'] = (
            pd.to_datetime(rel_df['last_txn_date'], errors='coerce') >= cutoff_3mo
        ).fillna(False).astype(int)
    else:
        rel_df['active_last_3mo'] = 0

    has_balance = 0
    if 'avg_bal' in rel_df.columns:
        has_balance_series = (rel_df['avg_bal'].fillna(0) > 0).astype(int)
    elif 'curr_bal' in rel_df.columns:
        has_balance_series = (rel_df['curr_bal'].fillna(0) > 0).astype(int)
    else:
        has_balance_series = pd.Series(0, index=rel_df.index)

    rel_df['relationship_depth_score'] = (
        rel_df['product_count'] * 2
        + has_balance_series
        + rel_df['active_last_3mo']
    )

    # ------------------------------------------------------------------
    # 5. Product count tier for charting
    # ------------------------------------------------------------------
    rel_df['product_tier'] = rel_df['product_count'].apply(
        lambda x: '5+' if x >= 5 else str(int(x))
    )
    PRODUCT_TIER_ORDER = ['1', '2', '3', '4', '5+']

    # ------------------------------------------------------------------
    # 6. Age bands (if age data available)
    # ------------------------------------------------------------------
    if 'member_age' in rel_df.columns:
        rel_df['age_band'] = pd.cut(
            pd.to_numeric(rel_df['member_age'], errors='coerce'),
            bins=[0, 25, 35, 45, 55, 65, 200],
            labels=['18-25', '26-35', '36-45', '46-55', '56-65', '65+'],
            right=True
        )

    # ------------------------------------------------------------------
    # 7. Account age / tenure bands (if available)
    # ------------------------------------------------------------------
    if 'account_age' in rel_df.columns:
        acct_age_numeric = pd.to_numeric(rel_df['account_age'], errors='coerce')
        if acct_age_numeric.notna().sum() > 0:
            max_val = acct_age_numeric.max()
            if max_val > 365:
                # Days
                rel_df['tenure_band'] = pd.cut(
                    acct_age_numeric,
                    bins=[-1, 90, 180, 365, 730, 1095, 1825, 3650, 7300, 999999],
                    labels=['1-90d', '91-180d', '181-365d', '1-2yr', '2-3yr',
                            '3-5yr', '5-10yr', '10-20yr', '20yr+']
                )
            else:
                # Years
                rel_df['tenure_band'] = pd.cut(
                    acct_age_numeric,
                    bins=[-1, 0.25, 0.5, 1, 2, 3, 5, 10, 20, 999],
                    labels=['1-90d', '91-180d', '181-365d', '1-2yr', '2-3yr',
                            '3-5yr', '5-10yr', '10-20yr', '20yr+']
                )

    # ------------------------------------------------------------------
    # 8. Check for finserv data (external financial services leakage)
    # ------------------------------------------------------------------
    HAS_FINSERV = False
    try:
        if 'finserv_summary_df' in dir() and len(finserv_summary_df) > 0:
            HAS_FINSERV = True
            print(f"  Financial services leakage data available: {len(finserv_summary_df)} categories")
        elif 'financial_services_data' in dir() and len(financial_services_data) > 0:
            HAS_FINSERV = True
            print(f"  Financial services data available: {len(financial_services_data)} categories")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 9. Product combination summary for co-occurrence
    # ------------------------------------------------------------------
    product_combos_df = (
        rel_df.groupby('product_combination')
        .agg(
            member_count=('account_number', 'count'),
            avg_products=('product_count', 'mean'),
            avg_spend=('total_spend', 'mean'),
        )
        .reset_index()
        .sort_values('member_count', ascending=False)
        .reset_index(drop=True)
    )

    # ------------------------------------------------------------------
    # Summary output
    # ------------------------------------------------------------------
    total_members = len(rel_df)
    avg_products = rel_df['product_count'].mean()
    single_product_pct = (rel_df['product_count'] == 1).mean() * 100
    three_plus_pct = (rel_df['product_count'] >= 3).mean() * 100
    max_products = rel_df['product_count'].max()

    print(f"Relationship data built: {total_members:,} members")
    print(f"  Avg products per member: {avg_products:.2f}")
    print(f"  Single-product members (flight risk): {single_product_pct:.1f}%")
    print(f"  Members with 3+ products (sticky): {three_plus_pct:.1f}%")
    print(f"  Max products held: {max_products}")
    print(f"\n  Product count distribution:")
    dist = rel_df['product_tier'].value_counts()
    for tier in PRODUCT_TIER_ORDER:
        if tier in dist.index:
            count = dist[tier]
            pct = count / total_members * 100
            print(f"    {tier} product(s): {count:,} members ({pct:.1f}%)")

    print(f"\n  Top 5 product combinations:")
    for _, row in product_combos_df.head(5).iterrows():
        print(f"    {row['product_combination']}: {int(row['member_count']):,} members")

except (NameError, KeyError, AttributeError) as e:
    print(f"  Relationship data not available: {e}")
    print("  Ensure rewards_df and combined_df are loaded.")
    rel_df = pd.DataFrame()
    product_combos_df = pd.DataFrame()
    HAS_FINSERV = False
    PRODUCT_TIER_ORDER = ['1', '2', '3', '4', '5+']
