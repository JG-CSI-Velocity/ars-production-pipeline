# ===========================================================================
# ACTION LISTS: Exportable Account Lists for Campaigns
# ===========================================================================
# These are the "turn insights into action" lists.
# Each list is a targeted campaign segment ready for export.

print("=" * 100)
print("ACTIONABLE CAMPAIGN LISTS")
print("=" * 100)

# --- LIST 1: High-Priority Multi-Product (3+ categories) ---
list_1 = multi_product_df[multi_product_df['category_count'] >= 3].copy()
list_1_display = list_1[['category_count', 'total_txn', 'recency_days', 'leakage_score', 'category_list']].head(25)
list_1_display.columns = ['Categories', 'Total Txn', 'Days Since Last', 'Leakage Score', 'External Services']

print(f"\n--- LIST 1: MULTI-PRODUCT HIGH PRIORITY (3+ external categories) ---")
print(f"Total accounts: {len(list_1):,}")
print(f"Recommended action: Full relationship review + bundled product offer\n")
if len(list_1) > 0:
    display(list_1_display.style.hide(axis='index') if hasattr(list_1_display, 'style') else list_1_display.head(25))

# --- LIST 2: Active Leakage (last 30 days) ---
list_2 = multi_product_df[multi_product_df['recency_days'] <= 30].copy()
list_2 = list_2.sort_values('leakage_score', ascending=False)
list_2_display = list_2[['category_count', 'total_txn', 'recency_days', 'leakage_score', 'category_list']].head(25)
list_2_display.columns = ['Categories', 'Total Txn', 'Days Since Last', 'Leakage Score', 'External Services']

print(f"\n--- LIST 2: ACTIVE LEAKAGE (transaction in last 30 days) ---")
print(f"Total accounts: {len(list_2):,}")
print(f"Recommended action: Immediate outreach -- these account holders are actively paying competitors\n")
if len(list_2) > 0:
    display(list_2_display.style.hide(axis='index') if hasattr(list_2_display, 'style') else list_2_display.head(25))

# --- LIST 3: Auto Loan Refinance Targets ---
if 'Auto Loans' in all_financial_accounts:
    auto_accts = all_financial_accounts['Auto Loans'].copy()
    list_3 = auto_accts[auto_accts['Recency_Days'] <= 180].sort_values('Transaction Count', ascending=False)
    list_3_display = list_3[['Transaction Count', 'Last Transaction', 'Recency_Days', 'Merchants']].head(25)
    list_3_display.columns = ['Transactions', 'Last Payment', 'Days Ago', 'Lender']

    print(f"\n--- LIST 3: AUTO LOAN REFINANCE TARGETS (active in 180 days) ---")
    print(f"Total accounts: {len(list_3):,}")
    print(f"Recommended action: Auto loan refinance campaign\n")
    if len(list_3) > 0:
        display(list_3_display.style.hide(axis='index') if hasattr(list_3_display, 'style') else list_3_display.head(25))

# --- LIST 4: Mortgage/HELOC Targets ---
if 'Mortgage/HELOC' in all_financial_accounts:
    mort_accts = all_financial_accounts['Mortgage/HELOC'].copy()
    list_4 = mort_accts[mort_accts['Recency_Days'] <= 180].sort_values('Transaction Count', ascending=False)
    list_4_display = list_4[['Transaction Count', 'Last Transaction', 'Recency_Days', 'Merchants']].head(25)
    list_4_display.columns = ['Transactions', 'Last Payment', 'Days Ago', 'Lender']

    print(f"\n--- LIST 4: MORTGAGE/HELOC TARGETS (active in 180 days) ---")
    print(f"Total accounts: {len(list_4):,}")
    print(f"Recommended action: HELOC or refinance offer\n")
    if len(list_4) > 0:
        display(list_4_display.style.hide(axis='index') if hasattr(list_4_display, 'style') else list_4_display.head(25))

# --- LIST 5: Investment/Wealth Management Prospects ---
if 'Investment/Brokerage' in all_financial_accounts:
    invest_accts = all_financial_accounts['Investment/Brokerage'].copy()
    list_5 = invest_accts[invest_accts['Recency_Days'] <= 180].sort_values('Transaction Count', ascending=False)
    list_5_display = list_5[['Transaction Count', 'Last Transaction', 'Recency_Days', 'Merchants']].head(25)
    list_5_display.columns = ['Transactions', 'Last Activity', 'Days Ago', 'Brokerage']

    print(f"\n--- LIST 5: INVESTMENT/WEALTH MANAGEMENT PROSPECTS (active in 180 days) ---")
    print(f"Total accounts: {len(list_5):,}")
    print(f"Recommended action: Wealth management consultation offer\n")
    if len(list_5) > 0:
        display(list_5_display.style.hide(axis='index') if hasattr(list_5_display, 'style') else list_5_display.head(25))

# --- LIST 6: New Leakage -- Just Started (< 90 days) ---
list_6 = multi_product_df[multi_product_df['is_new_leakage']].copy()
list_6 = list_6.sort_values('category_count', ascending=False)
list_6_display = list_6[['category_count', 'total_txn', 'tenure_days', 'leakage_score', 'category_list']].head(25)
list_6_display.columns = ['Categories', 'Total Txn', 'Days Since First', 'Leakage Score', 'External Services']

print(f"\n--- LIST 6: NEW LEAKAGE (first external finserv < 90 days ago) ---")
print(f"Total accounts: {len(list_6):,}")
print(f"Recommended action: Immediate re-engagement -- you just lost these account holders\n")
if len(list_6) > 0:
    display(list_6_display.style.hide(axis='index') if hasattr(list_6_display, 'style') else list_6_display.head(25))

# --- LIST 7: Credit Card Balance Transfer Targets ---
if 'Credit Cards' in all_financial_accounts:
    cc_accts = all_financial_accounts['Credit Cards'].copy()
    list_7 = cc_accts[cc_accts['Recency_Days'] <= 90].sort_values('Transaction Count', ascending=False)
    list_7_display = list_7[['Transaction Count', 'Last Transaction', 'Recency_Days', 'Merchants']].head(25)
    list_7_display.columns = ['Transactions', 'Last Payment', 'Days Ago', 'Card Issuer']

    print(f"\n--- LIST 7: CREDIT CARD BALANCE TRANSFER TARGETS (active in 90 days) ---")
    print(f"Total accounts: {len(list_7):,}")
    print(f"Recommended action: Balance transfer or new card offer\n")
    if len(list_7) > 0:
        display(list_7_display.style.hide(axis='index') if hasattr(list_7_display, 'style') else list_7_display.head(25))

# --- SUMMARY ---
print(f"\n{'=' * 100}")
print("LIST SUMMARY")
print(f"{'=' * 100}")
print(f"  List 1: Multi-product (3+ categories)      {len(list_1):>6,} accounts")
print(f"  List 2: Active leakage (last 30 days)       {len(list_2):>6,} accounts")
if 'Auto Loans' in all_financial_accounts:
    print(f"  List 3: Auto loan refinance targets         {len(list_3):>6,} accounts")
if 'Mortgage/HELOC' in all_financial_accounts:
    print(f"  List 4: Mortgage/HELOC targets              {len(list_4):>6,} accounts")
if 'Investment/Brokerage' in all_financial_accounts:
    print(f"  List 5: Investment prospects                {len(list_5):>6,} accounts")
print(f"  List 6: New leakage (< 90 days)             {len(list_6):>6,} accounts")
if 'Credit Cards' in all_financial_accounts:
    print(f"  List 7: Credit card balance transfer        {len(list_7):>6,} accounts")
print(f"\nAll lists are stored as DataFrames and ready for export.")
