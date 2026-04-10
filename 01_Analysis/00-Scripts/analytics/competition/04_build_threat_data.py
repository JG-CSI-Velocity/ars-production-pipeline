# ===========================================================================
# BUILD THREAT & PENETRATION DATA
# ===========================================================================
# Single pass over all_competitor_data to build both:
#   - threat_df:  top 15 bank competitors by threat score (used by cells 13, 14)
#   - pen_df:     all bank competitors with penetration metrics (used by cell 12)
#
# Includes name normalization (Golden 1 variants, Revolut variants, etc.)

# normalize_competitor_name is defined in 01_competitor_config

if len(all_competitor_data) > 0:
    bank_categories = BANK_CATEGORIES
    total_accounts = combined_df['primary_account_num'].nunique()
    raw_rows = []

    for competitor, comp_txns in all_competitor_data.items():
        category = comp_txns['competitor_category'].iloc[0]
        if category not in bank_categories:
            continue

        unique_accounts = comp_txns['primary_account_num'].nunique()
        total_spend = comp_txns['amount'].sum()
        transaction_count = len(comp_txns)
        penetration_pct = (unique_accounts / total_accounts * 100) if total_accounts > 0 else 0
        avg_per_account = total_spend / unique_accounts if unique_accounts > 0 else 0

        # Growth: last 3 months vs previous 3 months
        if 'year_month' not in comp_txns.columns:
            comp_txns = comp_txns.copy()
            comp_txns['year_month'] = pd.to_datetime(comp_txns['transaction_date']).dt.to_period('M')

        sorted_months = sorted(comp_txns['year_month'].unique())
        if len(sorted_months) >= 6:
            recent = comp_txns[comp_txns['year_month'].isin(sorted_months[-3:])]['amount'].sum()
            previous = comp_txns[comp_txns['year_month'].isin(sorted_months[-6:-3])]['amount'].sum()
            growth_rate = (recent - previous) / previous * 100 if previous > 0 else 0
        else:
            growth_rate = 0

        raw_rows.append({
            'competitor': competitor,
            'category': category,
            'total_spend': total_spend,
            'unique_accounts': unique_accounts,
            'penetration_pct': penetration_pct,
            'transaction_count': transaction_count,
            'avg_per_account': avg_per_account,
            'growth_rate': growth_rate,
        })

    if len(raw_rows) > 0:
        raw_df = pd.DataFrame(raw_rows)

        # --- pen_df: all bank competitors (no rollup needed for bubble chart) ---
        pen_df = raw_df.rename(columns={'competitor': 'bank'}).sort_values(
            'unique_accounts', ascending=False
        ).copy()

        # --- threat_df: normalized/rolled-up, top 15 by threat score ---
        raw_df['normalized_bank'] = raw_df['competitor'].apply(normalize_competitor_name)
        raw_df['growth_weighted'] = raw_df['growth_rate'] * raw_df['total_spend']

        rolled = (
            raw_df.groupby(['normalized_bank', 'category'], as_index=False)
            .agg(
                total_spend=('total_spend', 'sum'),
                unique_accounts=('unique_accounts', 'sum'),
                transaction_count=('transaction_count', 'sum'),
                growth_weighted=('growth_weighted', 'sum'),
            )
        )
        rolled['growth_rate'] = rolled.apply(
            lambda r: r['growth_weighted'] / r['total_spend'] if r['total_spend'] > 0 else 0, axis=1
        )
        rolled['penetration_pct'] = rolled['unique_accounts'] / total_accounts * 100 if total_accounts > 0 else 0
        rolled['avg_per_account'] = rolled.apply(
            lambda r: r['total_spend'] / r['unique_accounts'] if r['unique_accounts'] > 0 else 0, axis=1
        )
        # Threat score: 40% penetration, 30% spend, 30% growth
        rolled['threat_score'] = (
            (rolled['penetration_pct'] * 4) +
            (rolled['total_spend'] / 100_000) * 3 +
            (rolled['growth_rate'].clip(lower=0) / 10) * 3
        )
        threat_df = (
            rolled.rename(columns={'normalized_bank': 'competitor'})
            .sort_values('threat_score', ascending=False)
            .head(15)
        )

        print(f"    Competitor data built: {len(pen_df)} bank competitors, top {len(threat_df)} threats scored")
    else:
        pen_df = pd.DataFrame()
        threat_df = pd.DataFrame()
        print("    No bank competitors found in dataset")
else:
    pen_df = pd.DataFrame()
    threat_df = pd.DataFrame()
    print("    No competitor data available")
