# Phase 13: TXN Merge Batch 1 - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Copy the first 11 TXN folders (01-general through 11-transaction-type) plus 00-setup into 01_Analysis/00-Scripts/analytics/, adding .py extensions. Handle overlaps with existing ARS folders (attrition, rege, mailer). One commit, show diff, approve, push.

</domain>

<decisions>
## Implementation Decisions

### Folder Mapping
- **D-01:** Copy TXN 01-general -> analytics/general/ (29 scripts)
- **D-02:** Copy TXN 02-merchant -> analytics/merchant/ (14 scripts)
- **D-03:** Copy TXN 03-mcc-code -> analytics/mcc_code/ (15 scripts)
- **D-04:** Copy TXN 04-business-accts -> analytics/business_accts/ (14 scripts)
- **D-05:** Copy TXN 05-personal-accts -> analytics/personal_accts/ (14 scripts)
- **D-06:** Copy TXN 06-direct-competition -> analytics/competition/ (34 scripts)
- **D-07:** Copy TXN 07-financial-services -> analytics/financial_services/ (19 scripts)
- **D-08:** Copy TXN 08-ics-acquisition -> analytics/ics_acquisition/ (10 scripts)
- **D-09:** Copy TXN 09-ars-campaign -> analytics/campaign/ (43 scripts) -- SEPARATE from ARS mailer/
- **D-10:** Copy TXN 10-branch -> analytics/branch_txn/ (10 scripts)
- **D-11:** Copy TXN 11-transaction-type -> analytics/transaction_type/ (16 scripts)

### Overlap Handling
- **D-12:** ARS attrition/ stays UNTOUCHED. TXN attrition scripts (Phase 14) will go to attrition_txn/. No attrition work in this phase.
- **D-13:** ARS rege/ stays UNTOUCHED. TXN rege scripts (Phase 14) will go to rege_overdraft/. No rege work in this phase.
- **D-14:** ARS mailer/ stays UNTOUCHED. TXN campaign scripts go to campaign/ (D-09). Different data source, kept separate.

### Setup Scripts
- **D-15:** Copy TXN 00-setup -> analytics/txn_setup/ (10 scripts). TXN-specific utilities (file config, data loading, merchant consolidation). Not shared with ARS.

### File Naming
- **D-16:** Add .py extension to all scripts. Keep original filenames exactly as-is. e.g., 01_general_theme -> 01_general_theme.py

### Push Strategy
- **D-17:** All 12 folders (11 TXN + txn_setup) in ONE commit. Show full file list and diff to JG before pushing. Wait for explicit approval. JG pulls on work PC after push.

### Claude's Discretion
- Whether to add __init__.py to each new TXN folder
- Whether to add a README or index to the new folders
- Commit message wording

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs -- requirements fully captured in decisions above.

### Source Directories
- `TXN-v4-complete/00-setup/` -- 10 setup scripts to copy to txn_setup/
- `TXN-v4-complete/01-general/` -- 29 scripts
- `TXN-v4-complete/02-merchant/` -- 14 scripts
- `TXN-v4-complete/03-mcc-code/` -- 15 scripts
- `TXN-v4-complete/04-business-accts/` -- 14 scripts
- `TXN-v4-complete/05-personal-accts/` -- 14 scripts
- `TXN-v4-complete/06-direct-competition/` -- 34 scripts
- `TXN-v4-complete/07-financial-services/` -- 19 scripts
- `TXN-v4-complete/08-ics-acquisition/` -- 10 scripts
- `TXN-v4-complete/09-ars-campaign/` -- 43 scripts
- `TXN-v4-complete/10-branch/` -- 10 scripts
- `TXN-v4-complete/11-transaction-type/` -- 16 scripts

### Target Directory
- `01_Analysis/00-Scripts/analytics/` -- existing ARS analytics, new TXN folders go here alongside

</canonical_refs>

<code_context>
## Existing Code Insights

### Existing ARS Analytics Folders (DO NOT TOUCH)
- attrition/ (rates.py, dimensions.py, impact.py, _helpers.py)
- dctr/ (penetration.py, trends.py, funnel.py, overlays.py, branches.py, _helpers.py)
- insights/ (synthesis.py, effectiveness.py, conclusions.py, dormant.py, branch_scorecard.py, _data.py)
- mailer/ (reach.py, response.py, cohort.py, impact.py, insights.py, _helpers.py)
- overview/ (eligibility.py, product_codes.py, stat_codes.py)
- rege/ (status.py, dimensions.py, branches.py, _helpers.py)
- value/ (analysis.py)

### TXN Script Nature
- Converted Jupyter notebook cells, NOT modular imports
- Scripts assume shared namespace (previous cell output in scope)
- 00-setup defines globals: CLIENT_ID, CLIENT_PATH, file discovery functions, combined_df
- Currently hardcoded to client 1776/CoastHills (parameterization is Phase 15)

</code_context>

<specifics>
## Specific Ideas

- Total files: 228 (11 folders) + 10 (setup) = 238 scripts getting .py extensions
- The scripts are self-contained notebook cells -- they don't import from each other
- This is a pure file copy + rename operation. No code changes to the scripts themselves.
- Parameterization of hardcoded values is deferred to Phase 15.

</specifics>

<deferred>
## Deferred Ideas

- TXN attrition scripts -> attrition_txn/ (Phase 14)
- TXN rege scripts -> rege_overdraft/ (Phase 14)  
- Parameterize CLIENT_ID/CLIENT_PATH in setup scripts (Phase 15)
- Register TXN modules in analysis runner (v2 milestone)

</deferred>

---

*Phase: 13-txn-merge-batch-1*
*Context gathered: 2026-04-10*
