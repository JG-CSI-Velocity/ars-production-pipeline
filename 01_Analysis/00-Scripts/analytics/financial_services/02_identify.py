# ===========================================================================
# CELL 2: IDENTIFY FINANCIAL SERVICES TRANSACTIONS
# ===========================================================================
# Scans combined_df for finserv patterns. Builds financial_services_data dict.
# Produces: financial_services_data, finserv_summary_df

financial_services_data = {}

print("Scanning for financial services transactions...\n")

search_column = 'merchant_consolidated' if 'merchant_consolidated' in combined_df.columns else 'merchant_name'

false_positive_patterns = [
    'TOWING', 'TOW SERVICE', 'BODY SHOP', 'AUTO REPAIR',
    'AUTO PARTS', 'AUTOZONE', 'AUTO TRADER', 'TRADER JOE', "TRADER JOE'S"
]

_REGEX_BATCH_SIZE = 80  # avoid massive regex alternations

# ---------------------------------------------------------------------------
# PERFORMANCE: Match patterns against unique merchants first, then filter.
# This avoids running regex against millions of rows for every category.
# ---------------------------------------------------------------------------
_unique_merchants = combined_df[search_column].dropna().unique()
_unique_merch_series = pd.Series(_unique_merchants)

for category, patterns in FINANCIAL_SERVICES_PATTERNS.items():
    # Match patterns against unique merchant names (much smaller list)
    # Uses prefix matching (str.match with ^) to be consistent with
    # section 06's tag_competitors() which also uses starts_with logic.
    import re as _re
    _merch_mask = pd.Series(False, index=_unique_merch_series.index)
    for _i in range(0, len(patterns), _REGEX_BATCH_SIZE):
        _batch = patterns[_i:_i + _REGEX_BATCH_SIZE]
        _regex = '^(?:' + '|'.join(_re.escape(p) for p in _batch) + ')'
        _merch_mask |= _unique_merch_series.str.match(
            _regex, case=False, na=False
        )
    _matched_merchants = set(_unique_merch_series[_merch_mask].values)

    if not _matched_merchants:
        continue

    # Filter false positives from matched merchant names
    _fp_removed = set()
    for m in _matched_merchants:
        _m_upper = m.upper() if isinstance(m, str) else ''
        if any(fp in _m_upper for fp in false_positive_patterns):
            _fp_removed.add(m)
    _matched_merchants -= _fp_removed

    if not _matched_merchants:
        continue

    # Now filter combined_df using the small set of matched merchants (fast isin)
    category_trans = combined_df[combined_df[search_column].isin(_matched_merchants)].copy()

    if len(category_trans) == 0:
        continue

    # Build merchant summary
    merchant_summary = category_trans.groupby(search_column).agg({
        'amount': ['sum', 'count'],
        'primary_account_num': 'nunique'
    }).round(2)
    merchant_summary.columns = ['Total Spend', 'Transactions', 'Unique Accounts']
    merchant_summary = merchant_summary.sort_values('Transactions', ascending=False)

    financial_services_data[category] = {
        'transactions': category_trans,
        'merchant_summary': merchant_summary
    }

    pass  # data stored in financial_services_data

# Build summary DataFrame for visual cells
_total_portfolio_accts = combined_df['primary_account_num'].nunique()

finserv_summary = []
for category, data in financial_services_data.items():
    _cat_accts = data['transactions']['primary_account_num'].nunique()
    _cat_spend = data['transactions']['amount'].sum()
    finserv_summary.append({
        'category': category,
        'unique_accounts': _cat_accts,
        'total_transactions': len(data['transactions']),
        'total_spend': _cat_spend,
        'unique_merchants': len(data['merchant_summary']),
        'pct_portfolio': _cat_accts / _total_portfolio_accts * 100 if _total_portfolio_accts > 0 else 0,
    })

finserv_summary_df = pd.DataFrame(finserv_summary).sort_values('total_transactions', ascending=False)

total_txn = finserv_summary_df['total_transactions'].sum()
total_accts = finserv_summary_df['unique_accounts'].sum()
total_spend = finserv_summary_df['total_spend'].sum()

# ---------------------------------------------------------------------------
# Conference-grade styled output
# ---------------------------------------------------------------------------
_DARK = GEN_COLORS.get('dark_text', '#1B2A4A')
_MUTED = GEN_COLORS.get('muted', '#6C757D')
_ACCENT = GEN_COLORS.get('accent', '#E63946')
_INFO = GEN_COLORS.get('info', '#457B9D')
_SUCCESS = GEN_COLORS.get('success', '#2A9D8F')

# --- KPI row: scan results at a glance ---
fig_kpi, axes_kpi = plt.subplots(1, 4, figsize=(20, 4))
fig_kpi.subplots_adjust(wspace=0.15, top=0.75, bottom=0.05)

def _fmt_money(v):
    if abs(v) >= 1e6:
        return f"${v/1e6:,.1f}M"
    return f"${v/1e3:,.0f}K"

_scan_kpis = [
    (f"{len(financial_services_data)}", "Categories\nDetected", _INFO),
    (f"{total_accts:,}", "Accounts with\nExternal FinServ", _ACCENT),
    (f"{total_txn:,}", "Total External\nTransactions", _MUTED),
    (_fmt_money(total_spend), "External FinServ\nSpend Volume", _SUCCESS),
]

for ax, (value, label, color) in zip(axes_kpi, _scan_kpis):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    card = FancyBboxPatch(
        (0.03, 0.05), 0.94, 0.90,
        boxstyle="round,pad=0.05",
        facecolor=color, alpha=0.10,
        edgecolor=color, linewidth=2.5
    )
    ax.add_patch(card)

    ax.text(0.5, 0.62, value, transform=ax.transAxes,
            fontsize=36, fontweight='bold', color=color,
            ha='center', va='center')
    ax.text(0.5, 0.18, label, transform=ax.transAxes,
            fontsize=13, fontweight='bold', color=_DARK,
            ha='center', va='center', linespacing=1.4)

fig_kpi.suptitle("Financial Services Detection: Scan Results",
                 fontsize=22, fontweight='bold', color=_DARK, y=0.95)

plt.show()

# --- Conference-styled summary table ---
scan_display = finserv_summary_df[['category', 'unique_accounts', 'pct_portfolio',
                                    'total_transactions', 'total_spend', 'unique_merchants']].copy()
scan_display.columns = ['Category', 'Accounts', '% of Portfolio', 'Transactions', 'Total Spend', 'Merchants']

styled_scan = (
    scan_display.style
    .hide(axis='index')
    .format({
        'Accounts': '{:,}',
        '% of Portfolio': '{:.1f}%',
        'Transactions': '{:,}',
        'Total Spend': '${:,.0f}',
        'Merchants': '{:,}',
    })
    .set_properties(**{
        'font-size': '14px', 'text-align': 'left',
        'border': '1px solid #E9ECEF', 'padding': '10px 14px',
    })
    .set_properties(subset=['Category'], **{
        'font-weight': 'bold', 'color': _INFO,
        'font-size': '15px',
    })
    .set_properties(subset=['Accounts', '% of Portfolio', 'Transactions', 'Total Spend', 'Merchants'], **{
        'text-align': 'center',
    })
    .bar(subset=['% of Portfolio'], color=f'{_ACCENT}30', vmin=0)
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', _INFO),
            ('color', 'white'), ('font-size', '15px'),
            ('font-weight', 'bold'), ('text-align', 'center'),
            ('padding', '10px 14px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '22px'), ('font-weight', 'bold'),
            ('color', _DARK), ('text-align', 'left'),
            ('padding-bottom', '14px'),
        ]},
        {'selector': 'td', 'props': [
            ('border-bottom', f'1px solid #E9ECEF'),
        ]},
    ])
    .set_caption("External Financial Services: Category Breakdown")
)

display(styled_scan)

# Console summary
print(f"\n    FINANCIAL SERVICES SCAN COMPLETE")
print(f"    {'='*55}")
print(f"    Categories detected:   {len(financial_services_data)}")
print(f"    Total accounts:        {total_accts:,} / {_total_portfolio_accts:,} ({total_accts/_total_portfolio_accts*100:.1f}%)")
print(f"    Total transactions:    {total_txn:,}")
print(f"    Total external spend:  {_fmt_money(total_spend)}")
print(f"    Unique merchants:      {finserv_summary_df['unique_merchants'].sum():,}")
