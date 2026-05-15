# ===========================================================================
# ACTION ROADMAP: Prioritized 3-Tier Implementation Plan
# ===========================================================================
# Quick Wins (0-30 days), Medium-Term (30-90 days), Strategic (90-365 days)
# Styled HTML table with colored tier backgrounds and upstream data references.

# ---------------------------------------------------------------------------
# Pull specific numbers from upstream data for action items
# ---------------------------------------------------------------------------

# Attrition numbers
_at_risk_ct = 0
_spend_at_risk = 0
_declining_ct = 0
_dormant_ct = 0
if 'attrition_df' in dir() and len(attrition_df) > 0:
    _declining_ct = len(attrition_df[attrition_df['risk_tier'] == 'Declining'])
    _dormant_ct = len(attrition_df[attrition_df['risk_tier'] == 'Dormant'])
    _at_risk_ct = _declining_ct + _dormant_ct
    if 'last_12mo_spend' in attrition_df.columns:
        _spend_at_risk = attrition_df[
            attrition_df['risk_tier'].isin(['Declining', 'Dormant'])
        ]['last_12mo_spend'].sum()

# Relationship numbers
_single_ct = 0
_avg_prods = 0
if 'rel_df' in dir() and len(rel_df) > 0 and 'product_count' in rel_df.columns:
    _single_ct = (rel_df['product_count'] == 1).sum()
    _avg_prods = rel_df['product_count'].mean()

# Interchange numbers
_sig_ratio = 0
_ic_opp = 0
if 'interchange_df' in dir() and len(interchange_df) > 0:
    _total_pin_d = interchange_df['total_pin_dollars'].sum() if 'total_pin_dollars' in interchange_df.columns else 0
    _total_sig_d = interchange_df['total_sig_dollars'].sum() if 'total_sig_dollars' in interchange_df.columns else 0
    _sig_ratio = (_total_sig_d / (_total_pin_d + _total_sig_d) * 100) if (_total_pin_d + _total_sig_d) > 0 else 0
    _raw_opp = interchange_df['opportunity'].sum() if 'opportunity' in interchange_df.columns else 0
    _num_months_ic = len(MONTH_LABELS) if 'MONTH_LABELS' in dir() else 12
    _ic_opp = _raw_opp * (12.0 / _num_months_ic if _num_months_ic > 0 else 1.0)

# Payroll numbers
_payroll_pct = 0
_secondary_ct = 0
if 'payroll_df' in dir() and len(payroll_df) > 0:
    _payroll_pct = (payroll_df['has_payroll'].sum() / len(payroll_df) * 100) if len(payroll_df) > 0 else 0
    if 'pfi_tier' in payroll_df.columns:
        _secondary_ct = len(payroll_df[payroll_df['pfi_tier'] == 'Secondary'])

# Reg E numbers
_optin_rate = 0
_opted_out_ct = 0
if 'rege_df' in dir() and len(rege_df) > 0:
    _opted_in_ct = len(rege_df[rege_df['current_status'] == 'Opted-In'])
    _opted_out_ct = len(rege_df[rege_df['current_status'] == 'Opted-Out'])
    _optin_rate = (_opted_in_ct / len(rege_df) * 100) if len(rege_df) > 0 else 0

# Segmentation numbers
_degraded_ct = 0
if 'seg_evo_df' in dir() and len(seg_evo_df) > 0 and 'direction' in seg_evo_df.columns:
    _degraded_ct = (seg_evo_df['direction'] == 'degraded').sum()

# ---------------------------------------------------------------------------
# Build action items for each tier
# ---------------------------------------------------------------------------
_actions = []

# --- QUICK WINS (0-30 days) ---
_actions.append({
    'tier': 'Quick Win (0-30 days)',
    'area': 'Attrition',
    'action': f"Launch outreach campaign to top 100 declining high-balance members "
              f"from the {_declining_ct:,} accounts in Declining tier",
    'expected_impact': f"Retain {gen_fmt_dollar(_spend_at_risk * 0.05, None)} in annual spend",
    'owner': 'Member Experience',
    'bg_color': '#E8F5E9',
})

_actions.append({
    'tier': 'Quick Win (0-30 days)',
    'area': 'Interchange',
    'action': f"Promote signature-preferred card usage via push notifications and "
              f"digital banking reminders (current SIG ratio: {_sig_ratio:.0f}%)",
    'expected_impact': f"Capture 5% of {gen_fmt_dollar(_ic_opp, None)} PIN-to-SIG gap",
    'owner': 'Card Services',
    'bg_color': '#E8F5E9',
})

_actions.append({
    'tier': 'Quick Win (0-30 days)',
    'area': 'Reg E',
    'action': f"Train branch staff on opt-in presentation for the "
              f"{_opted_out_ct:,} currently opted-out members",
    'expected_impact': f"Convert 2-3% of opted-out ({_opted_out_ct * 3 // 100:,} accounts)",
    'owner': 'Branch Operations',
    'bg_color': '#E8F5E9',
})

_actions.append({
    'tier': 'Quick Win (0-30 days)',
    'area': 'Relationship',
    'action': f"Generate referral lists for {_single_ct:,} single-product members "
              f"with 6+ months tenure and active transactions",
    'expected_impact': f"Identify top 500 cross-sell candidates",
    'owner': 'Sales / Branch',
    'bg_color': '#E8F5E9',
})

_actions.append({
    'tier': 'Quick Win (0-30 days)',
    'area': 'Attrition',
    'action': f"Deploy automated velocity-based early warning system for accounts "
              f"crossing 0.8x spend velocity threshold",
    'expected_impact': f"Catch declining accounts 30-60 days earlier",
    'owner': 'Analytics / IT',
    'bg_color': '#E8F5E9',
})

# --- MEDIUM TERM (30-90 days) ---
_actions.append({
    'tier': 'Medium-Term (30-90 days)',
    'area': 'Payroll',
    'action': f"Launch direct deposit switch campaign targeting {_secondary_ct:,} "
              f"Secondary PFI tier members with partial payroll activity",
    'expected_impact': f"Migrate 10% to Primary PFI (avg +$5K deposit growth)",
    'owner': 'Deposit Strategy',
    'bg_color': '#FFF3E0',
})

_actions.append({
    'tier': 'Medium-Term (30-90 days)',
    'area': 'Relationship',
    'action': f"Design product bundle offers for single-product members "
              f"(current avg: {_avg_prods:.1f} products/member)",
    'expected_impact': f"Convert 15% of {_single_ct:,} single-product to 2+ products",
    'owner': 'Product / Marketing',
    'bg_color': '#FFF3E0',
})

_actions.append({
    'tier': 'Medium-Term (30-90 days)',
    'area': 'Interchange',
    'action': f"Implement contactless card issuance program to shift "
              f"PIN-dominant transaction patterns toward signature",
    'expected_impact': f"Shift SIG ratio from {_sig_ratio:.0f}% toward {min(_sig_ratio + 5, 80):.0f}%",
    'owner': 'Card Strategy',
    'bg_color': '#FFF3E0',
})

_actions.append({
    'tier': 'Medium-Term (30-90 days)',
    'area': 'Segmentation',
    'action': f"Create targeted upgrade paths for {_degraded_ct:,} degraded-segment "
              f"members with personalized engagement campaigns",
    'expected_impact': f"Reverse 20% of segment degradation",
    'owner': 'Member Experience',
    'bg_color': '#FFF3E0',
})

_actions.append({
    'tier': 'Medium-Term (30-90 days)',
    'area': 'Attrition',
    'action': f"Build dormant reactivation program for {_dormant_ct:,} dormant accounts "
              f"with incentive-based re-engagement offers",
    'expected_impact': f"Reactivate 10% of dormant accounts",
    'owner': 'Retention Team',
    'bg_color': '#FFF3E0',
})

# --- STRATEGIC (90-365 days) ---
_actions.append({
    'tier': 'Strategic (90-365 days)',
    'area': 'Payroll',
    'action': f"Partner with employer groups and payroll processors to become "
              f"default direct deposit destination (current detection: {_payroll_pct:.0f}%)",
    'expected_impact': f"Increase payroll penetration to {min(_payroll_pct + 10, 50):.0f}%",
    'owner': 'Business Development',
    'bg_color': '#E3F2FD',
})

_actions.append({
    'tier': 'Strategic (90-365 days)',
    'area': 'Relationship',
    'action': f"Develop predictive cross-sell model using relationship depth scores "
              f"and transaction patterns across {len(rel_df) if 'rel_df' in dir() and len(rel_df) > 0 else 0:,} members",
    'expected_impact': f"Increase avg products/member from {_avg_prods:.1f} to {_avg_prods + 0.3:.1f}",
    'owner': 'Analytics / Product',
    'bg_color': '#E3F2FD',
})

_actions.append({
    'tier': 'Strategic (90-365 days)',
    'area': 'Interchange',
    'action': f"Negotiate improved interchange terms with card networks "
              f"leveraging SIG ratio improvements and volume data",
    'expected_impact': f"Increase effective interchange rate by 5-10 bps",
    'owner': 'Payments / Executive',
    'bg_color': '#E3F2FD',
})

_actions.append({
    'tier': 'Strategic (90-365 days)',
    'area': 'Attrition',
    'action': f"Implement real-time lifecycle management platform that "
              f"auto-triggers retention actions based on velocity changes",
    'expected_impact': f"Reduce at-risk accounts by 30% year-over-year",
    'owner': 'IT / Analytics',
    'bg_color': '#E3F2FD',
})

_actions.append({
    'tier': 'Strategic (90-365 days)',
    'area': 'Reg E',
    'action': f"Integrate Reg E opt-in workflow into digital onboarding and "
              f"account opening processes for new members",
    'expected_impact': f"Achieve 50%+ opt-in rate on new accounts",
    'owner': 'Digital / Compliance',
    'bg_color': '#E3F2FD',
})

# ---------------------------------------------------------------------------
# Build and style HTML table
# ---------------------------------------------------------------------------
roadmap_df = pd.DataFrame(_actions)

_display = roadmap_df[['tier', 'area', 'action', 'expected_impact', 'owner']].copy()
_display.columns = ['Tier', 'Area', 'Action', 'Expected Impact', 'Owner']

def _tier_bg(row):
    bg = roadmap_df.iloc[row.name]['bg_color'] if row.name < len(roadmap_df) else '#FFFFFF'
    return [f'background-color: {bg}'] * len(row)

styled = (
    _display.style
    .hide(axis='index')
    .set_properties(**{
        'font-size': '12px',
        'font-weight': 'bold',
        'text-align': 'left',
        'border': '1px solid #E9ECEF',
        'padding': '10px 12px',
        'vertical-align': 'top',
    })
    .set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', GEN_COLORS['primary']),
            ('color', 'white'),
            ('font-size', '14px'),
            ('font-weight', 'bold'),
            ('text-align', 'left'),
            ('padding', '10px 14px'),
        ]},
        {'selector': 'caption', 'props': [
            ('font-size', '24px'),
            ('font-weight', 'bold'),
            ('color', GEN_COLORS['dark_text']),
            ('text-align', 'left'),
            ('padding-bottom', '14px'),
        ]},
        {'selector': 'table', 'props': [
            ('width', '100%'),
        ]},
    ])
    .set_caption("Action Roadmap: Prioritized Implementation Plan")
    .apply(_tier_bg, axis=1)
)

display(styled)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
_quick_ct = sum(1 for a in _actions if 'Quick Win' in a['tier'])
_medium_ct = sum(1 for a in _actions if 'Medium-Term' in a['tier'])
_strategic_ct = sum(1 for a in _actions if 'Strategic' in a['tier'])

# Count total cells across all analysis folders
_total_folders = 8  # setup, general, attrition, balance, interchange, rege, payroll, relationship, segmentation + executive
_folder_counts = {
    'setup': 10, 'general': 28, 'attrition': 12, 'balance': 10,
    'interchange': 10, 'rege_overdraft': 10, 'payroll': 10,
    'relationship': 10, 'segment_evolution': 8, 'executive': 5,
}
# Folder/cell totals: prefer the baked-in fallback so this cell never crashes
# on a machine without the legacy /private/tmp/txn-visual-test scratch dir
# (that path was Mac-dev leftovers -- broke every Windows run as WinError 3).
# If the script's own parent directory is introspectable, use that to derive
# a current cell count; otherwise use _folder_counts as the source of truth.
_actual_total = sum(_folder_counts.values())
_folder_count = len(_folder_counts)
try:
    import os
    _script_path = globals().get("__file__")
    if _script_path:
        _analytics_root = os.path.dirname(os.path.dirname(_script_path))
        if os.path.isdir(_analytics_root):
            _live_folders = [
                d for d in os.listdir(_analytics_root)
                if os.path.isdir(os.path.join(_analytics_root, d))
                and not d.startswith(".") and not d.startswith("__")
            ]
            _live_total = 0
            for _fname in _live_folders:
                _fpath = os.path.join(_analytics_root, _fname)
                _live_total += len([
                    f for f in os.listdir(_fpath)
                    if f.endswith(".py") and not f.startswith("__")
                ])
            if _live_total > 0:
                _actual_total = _live_total
                _folder_count = len(_live_folders)
except Exception:
    pass

print(f"\n{'='*70}")
print(f"  ACTION ROADMAP SUMMARY")
print(f"{'='*70}")
print(f"  Quick Wins (0-30 days):   {_quick_ct} actions")
print(f"  Medium-Term (30-90 days): {_medium_ct} actions")
print(f"  Strategic (90-365 days):  {_strategic_ct} actions")
print(f"  Total actions:            {_quick_ct + _medium_ct + _strategic_ct}")
print(f"{'='*70}")

print(f"\n    Full analysis available across {_folder_count} folders, "
      f"{_actual_total} total cells.")

print(f"\n    INSIGHT: Quick wins focus on immediate outreach and process improvements "
      f"that require no system changes. Medium-term actions involve campaign design "
      f"and product bundling. Strategic actions build long-term analytical and "
      f"operational capabilities.")
