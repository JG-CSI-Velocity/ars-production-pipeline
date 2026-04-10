# ===========================================================================
# EXPORT: Account-Level CSV Files
# ===========================================================================
# Exports three CSVs per competitor in deep_dive_competitors:
#   1. Full wallet-share comparison
#   2. At-risk accounts (Competitor-Heavy segment)
#   3. Opportunity accounts (Primary segment)
# Uses canonical competitor_spend_analysis from cell 20.

from pathlib import Path

output_dir = Path(f"output/{CLIENT_ID}_{CLIENT_NAME}/competition")
output_dir.mkdir(parents=True, exist_ok=True)

if len(competitor_spend_analysis) > 0:
    exported = 0

    for comp_name, df in competitor_spend_analysis.items():
        safe_name = comp_name.replace(' ', '_').replace('/', '_')

        export_df = df[['primary_account_num', 'total_spend', 'total_txns',
                        'competitor_spend', 'competitor_txns',
                        'your_spend', 'your_txns',
                        'competitor_pct', 'segment',
                        'competitor_name', 'competitor_category']].copy()
        export_df = export_df.sort_values('total_spend', ascending=False)

        # Full comparison
        path_full = output_dir / f"{safe_name}_wallet_share.csv"
        export_df.to_csv(path_full, index=False)

        # At-risk (Competitor-Heavy)
        at_risk = export_df[export_df['segment'] == 'Competitor-Heavy']
        path_risk = output_dir / f"{safe_name}_at_risk.csv"
        at_risk.to_csv(path_risk, index=False)

        # Opportunity (Primary)
        opportunity = export_df[export_df['segment'] == 'Primary']
        path_opp = output_dir / f"{safe_name}_opportunity.csv"
        opportunity.to_csv(path_opp, index=False)

        exported += 1
        if comp_name in deep_dive_competitors:
            print(f"    {comp_name}:")
            print(f"      Full:        {path_full.name} ({len(export_df):,} accounts)")
            print(f"      At-Risk:     {path_risk.name} ({len(at_risk):,} accounts)")
            print(f"      Opportunity: {path_opp.name} ({len(opportunity):,} accounts)")

    print(f"\n    Exported {exported} competitors to {output_dir}/")
    print(f"    3 files each: wallet_share, at_risk, opportunity")
else:
    print("    No competitor data to export")
