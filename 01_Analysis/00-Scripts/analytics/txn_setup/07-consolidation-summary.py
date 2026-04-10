# ===========================================================================
# DATA PREPARATION - MERCHANT NAME CONSOLIDATION
# ===========================================================================
"""
## Data Preparation - Merchant Consolidation
Standardizes merchant names to consolidate variations and improve analysis quality.
Examples:
  - "WALMART.COM", "WAL-MART #3893", "WM SUPERCENTER" → "WALMART (ALL LOCATIONS)"
  - "APPLE.COM/BILL", "APPLE COM BILL" → "APPLE.COM/BILL"
  - "NETFLIX.COM", "NETFLIX COM", "Netflix.com" → "NETFLIX"
"""
print("="*100)
print(" " * 30 + "MERCHANT NAME CONSOLIDATION")
print("="*100)

# Apply universal consolidation function
print("\nApplying merchant name standardization...")
combined_df['merchant_consolidated'] = combined_df['merchant_name'].apply(standardize_merchant_name)

# Calculate consolidation impact
original_count = combined_df['merchant_name'].nunique()
consolidated_count = combined_df['merchant_consolidated'].nunique()
reduction = original_count - consolidated_count
reduction_pct = (reduction / original_count) * 100

print(f"\nConsolidation complete.")
print(f"  Original unique merchants: {original_count:,}")
print(f"  After consolidation: {consolidated_count:,}")
print(f"  Merchants consolidated: {reduction:,} ({reduction_pct:.1f}% reduction)")

# Show top consolidations (merchants with most variations)
print(f"\n" + "-"*100)
print("TOP 10 CONSOLIDATIONS (Merchants with Most Variations)")
print("-"*100)

consolidation_summary = combined_df.groupby('merchant_consolidated').agg({
    'merchant_name': 'nunique',
    'primary_account_num': 'nunique',
    'amount': 'sum',
    'transaction_date': 'count'
}).round(2)

consolidation_summary.columns = ['variations', 'unique_accounts', 'total_spend', 'transaction_count']
consolidation_summary = consolidation_summary[consolidation_summary['variations'] > 1]
consolidation_summary = consolidation_summary.sort_values('variations', ascending=False)

# Display top 10
top_10_consolidated = consolidation_summary.head(10)
display_df = pd.DataFrame({
    'Consolidated Merchant': top_10_consolidated.index,
    'Variations': top_10_consolidated['variations'].astype(int),
    'Accounts': top_10_consolidated['unique_accounts'].astype(int),
    'Transactions': top_10_consolidated['transaction_count'].astype(int)
})

display(display_df.style.hide(axis='index'))

# Show examples of what got consolidated for top 3
print(f"\n" + "-"*100)
print("EXAMPLES - Original Variations (Top 3 Consolidated Merchants)")
print("-"*100)

for merchant in consolidation_summary.head(3).index:
    variations = combined_df[combined_df['merchant_consolidated'] == merchant]['merchant_name'].unique()
    variation_count = len(variations)
    
    print(f"\n  {merchant}")
    print(f"   Consolidated {variation_count} variations:")
    
    for i, var in enumerate(sorted(variations)[:5], 1):
        print(f"   {i}. {var}")
    
    if variation_count > 5:
        print(f"   ... and {variation_count - 5} more variations")

print(f"\n" + "="*100)
print("Data preparation complete - Ready for analysis")
print("="*100)
