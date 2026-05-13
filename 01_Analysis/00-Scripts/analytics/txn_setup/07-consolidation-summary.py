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

# ---------------------------------------------------------------------------
# SMART UNKNOWN-MERCHANT FALLBACK
# ---------------------------------------------------------------------------
# When merchant_name is genuinely empty (ATM withdrawals, bank fees, internal
# transfers), the consolidator returns 'UNKNOWN MERCHANT'. On personal accounts
# this typically runs ~5-10%; on business it can hit 40% (lots of ACH activity
# without a recognizable merchant). Lumping them all under one bucket distorts
# the top-merchant charts and the leakage analysis.
#
# Re-label these rows based on the transaction_type column (PIN / SIG / ACH /
# CHK / ATM / FEE / etc.) so the chart shows what those transactions actually
# are -- ``ATM WITHDRAWAL'' / ``BANK FEE'' / ``ACH TRANSFER'' / etc. -- rather
# than one giant ``UNKNOWN MERCHANT'' bucket. This is purely cosmetic relabeling;
# downstream tagging (tag_competitors, financial_services) treats the new
# labels exactly the same as Unknown (they don't match any competitor pattern).
# ---------------------------------------------------------------------------
_unknown_mask = combined_df['merchant_consolidated'] == 'UNKNOWN MERCHANT'
_n_unknown_before = int(_unknown_mask.sum())
if _n_unknown_before > 0 and 'transaction_type' in combined_df.columns:
    _ttype = combined_df.loc[_unknown_mask, 'transaction_type'].astype(str).str.upper().str.strip()

    # Map common transaction_type codes to descriptive labels. Unknown values
    # fall through to the generic ``UNKNOWN MERCHANT'' label so we don't
    # silently invent buckets for codes we haven't seen.
    def _label_for_ttype(t):
        if not t or t in ('NAN', 'NONE', ''):
            return 'UNKNOWN MERCHANT'
        if 'ATM' in t:
            return 'ATM WITHDRAWAL'
        if 'FEE' in t or t in ('SC', 'NSF', 'OD'):
            return 'BANK FEE'
        if 'ACH' in t:
            return 'ACH TRANSFER (NO MERCHANT)'
        if 'CHK' in t or 'CHECK' in t or t == 'CK':
            return 'CHECK (NO MERCHANT)'
        if 'XFER' in t or 'TRANSFER' in t or t in ('TR', 'TRF'):
            return 'INTERNAL TRANSFER'
        if t in ('PIN', 'SIG', 'POS', 'DEB'):
            return 'POS TRANSACTION (NO MERCHANT)'
        if 'DEP' in t or 'DEPOSIT' in t:
            return 'DEPOSIT (NO MERCHANT)'
        if 'WD' in t or 'WTHD' in t or 'WITHDRAW' in t:
            return 'WITHDRAWAL (NO MERCHANT)'
        return 'UNKNOWN MERCHANT'

    combined_df.loc[_unknown_mask, 'merchant_consolidated'] = _ttype.apply(_label_for_ttype)

    _n_unknown_after = int((combined_df['merchant_consolidated'] == 'UNKNOWN MERCHANT').sum())
    _relabeled = _n_unknown_before - _n_unknown_after
    print(f"  Smart Unknown fallback: relabeled {_relabeled:,} rows by transaction_type")
    print(f"  ({_n_unknown_before:,} unknowns before -> {_n_unknown_after:,} truly unknown after)")
    if _relabeled > 0:
        # Show the breakdown so the user can audit
        _new_labels = (
            combined_df.loc[_unknown_mask, 'merchant_consolidated']
            .value_counts().head(10)
        )
        for _label, _count in _new_labels.items():
            print(f"     {_count:>10,}  {_label}")

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
