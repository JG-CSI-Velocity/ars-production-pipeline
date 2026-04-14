# Roadmap: Velocity Pipeline Merge

## Milestones

- (completed) **v1.0 Framework** - Phases 1-10 (shipped 2026-04-10, then reverted)
- (active) **v1.1 TXN Merge** - Phases 11-16 (15/19 requirements complete, verification pending)
- (planned) **v2.0 Production Polish** - Phases 17-18 (E2E orchestration + slide layout refinement)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (11.1, 11.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 11: Repo Reset and Cleanup** - Reset local repo to clean GitHub state (a314c50), remove all v1.0 artifacts ✓ 2026-04-10
- [x] **Phase 12: Folder Structure** - Create 02-05 directories, move config and UI files, mirror M:\ARS\ layout ✓ 2026-04-10
- [x] **Phase 13: TXN Merge Batch 1** - Merge first 11 TXN folders (general through transaction_type) with overlap handling ✓ 2026-04-11
- [x] **Phase 14: TXN Merge Batch 2** - Merge remaining 11 TXN folders (product through executive), completing all 22 folders ✓ 2026-04-11
- [x] **Phase 15: Setup Parameterization** - TXN setup scripts parameterized (CLIENT_ID from env), TXN files separated to TXN Files/{CSM}/{client_id}/, trailing 12-month window ✓ 2026-04-13
- [ ] **Phase 16: Verification** - Confirm existing ARS pipeline works after merge, validate folder-by-folder pull on work PC

## Phase Details

### Phase 11: Repo Reset and Cleanup
**Goal**: Local repo matches GitHub exactly at commit a314c50 with zero leftover v1.0 artifacts
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: REPO-01, REPO-02
**Success Criteria** (what must be TRUE):
  1. Running `git status` in the local repo shows a clean working tree with no untracked files outside the a314c50 structure
  2. Running `git log -1` shows commit a314c50 (or a descendant with only the reset commit)
  3. No velocity/ package directory, no manifest YAML files, no v1.0 UI pages exist in the working tree
**Plans**: 1/1 plans complete
Plans:
- [x] 11-01-PLAN.md -- Hard reset to a314c50, clean v1.0 artifacts, user verification

### Phase 12: Folder Structure
**Goal**: GitHub repo has the 00-05 numbered directory layout that mirrors M:\ARS\ exactly, with config and UI files in their correct locations
**Depends on**: Phase 11
**Requirements**: FOLD-01, FOLD-02, FOLD-03, FOLD-04, FOLD-05
**Success Criteria** (what must be TRUE):
  1. Directories 02_Presentations/, 03_Config/, 04_Logs/, and 05_UI/ exist on GitHub after push
  2. ars_config.json and settings.py are in 03_Config/ (not nested under 00_Formatting/00-Scripts/configs/)
  3. FastAPI app.py and all static UI files are under 05_UI/ (ui/ directory no longer exists)
  4. Running `ls` at repo root shows 00_Formatting, 01_Analysis, 02_Powerpoint, 02_Presentations, 03_Config, 04_Logs, 05_UI as the primary structure
  5. Work PC can `git pull` this commit and see the same folder layout as M:\ARS\
**Plans:** 2/2 plans complete
Plans:
- [x] 12-01-PLAN.md -- Create 03_Config/, move config files, update import paths
- [x] 12-02-PLAN.md -- Create remaining dirs, copy 02_Powerpoint, move UI, delete mockups, push gate

### Phase 13: TXN Merge Batch 1
**Goal**: First 11 TXN section folders (general through transaction_type) are merged into 01_Analysis/00-Scripts/analytics/ with overlap modules kept separate
**Depends on**: Phase 12
**Requirements**: TXN-03, TXN-04, TXN-05, TXN-06
**Success Criteria** (what must be TRUE):
  1. Folders general/, merchant/, mcc_code/, business_accts/, personal_accts/, competition/, financial_services/, ics_acquisition/, campaign/, branch_txn/, transaction_type/ exist under 01_Analysis/00-Scripts/analytics/
  2. ARS attrition/ is untouched and TXN attrition scripts go to attrition_txn/ (both directories exist side by side)
  3. ARS rege/ is untouched and TXN rege scripts go to rege_overdraft/ (both directories exist side by side)
  4. ARS mailer/ is untouched and TXN campaign scripts go to campaign/ (both directories exist side by side)
  5. 00-setup scripts are placed in shared/ or 03_Config/ as utility files with .py extensions
**Plans:** 1 plan
Plans:
- [ ] 13-01-PLAN.md -- Copy 12 TXN folders (238 scripts) with .py extensions, push gate

### Phase 14: TXN Merge Batch 2
**Goal**: Remaining 11 TXN section folders (product through executive) are merged, completing the full 22-folder TXN integration
**Depends on**: Phase 13
**Requirements**: TXN-01, TXN-02
**Success Criteria** (what must be TRUE):
  1. Folders product/, attrition_txn/, balance/, interchange/, rege_overdraft/, payroll/, relationship/, segment_evolution/, retention/, engagement/, executive/ exist under 01_Analysis/00-Scripts/analytics/
  2. All 22 TXN folders are present under 01_Analysis/00-Scripts/analytics/ (verified by count)
  3. All 332 TXN scripts have .py extensions (no extensionless files remain)
  4. Work PC can `git pull` this commit and see the complete TXN folder structure
**Plans**: TBD

### Phase 15: Setup Parameterization
**Goal**: TXN setup scripts accept any client ID and read transaction files from the standard monthly client folder (not hardcoded paths)
**Depends on**: Phase 13
**Requirements**: PARAM-01, PARAM-02
**Success Criteria** (what must be TRUE):
  1. No TXN setup script contains a hardcoded reference to client 1776 or "CoastHills"
  2. TXN file paths resolve from the same folder structure as ODD files (00_Formatting/02-Data-Ready for Analysis/{CSM}/{YYYY.MM}/{client_id}/)
  3. Running a TXN setup script with a different client ID (e.g., 1200) produces correct path resolution without errors
**Plans**: TBD

### Phase 16: Verification
**Goal**: The merged repo works correctly -- existing ARS pipeline runs without errors and each folder commit pulls cleanly on the work PC
**Depends on**: Phase 14, Phase 15
**Requirements**: VERIF-01, VERIF-02, VERIF-03, VERIF-04
**Success Criteria** (what must be TRUE):
  1. Running the ARS formatting pipeline (00_Formatting/run.py) produces the same output as before the merge
  2. Running the ARS analysis modules (01_Analysis/run.py) produces the same output as before the merge
  3. Running PowerPoint generation (02_Powerpoint/) produces a valid PPTX from analysis results
  4. Each phase (11-15) was committed and pushed separately, and the work PC successfully pulled each one
**Plans**: TBD

## Progress

**Execution Order:**
v1.1: 11 -> 12 -> 13 -> 14 -> 15 -> 16
v1.1 → v2.0: 17 -> 18 (slide refinement is iterative, section by section)

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 11. Repo Reset | v1.1 | Complete | 2026-04-10 |
| 12. Folder Structure | v1.1 | Complete | 2026-04-10 |
| 13. TXN Merge Batch 1 | v1.1 | Complete | 2026-04-11 |
| 14. TXN Merge Batch 2 | v1.1 | Complete | 2026-04-11 |
| 15. Setup Parameterization | v1.1 | Complete | 2026-04-13 |
| 16. Verification | v1.1 | Pending -- needs work PC test | - |
| 17. E2E Orchestration | v2.0 | Not started | - |
| 18. Slide Layout Refinement | v2.0 | Not started | - |

---

### Phase 17: End-to-End Orchestration & Scheduling
**Goal:** Single-command or single-button pipeline that chains formatting -> analysis (ARS + TXN) -> PowerPoint generation for one client/month. Include scheduling support so CSMs can set up recurring runs (e.g., monthly auto-generate for their clients).
**Depends on:** Phase 16
**Requirements:** TBD
**Plans:** TBD

### Phase 18: Slide Layout Refinement (All Sections)
**Goal:** Go section by section through SLIDE_MANIFEST.xlsx and refine chart sizing, positioning, text, and styling for all slides -- both ARS and TXN. Iterative process with JG review per section.
**Depends on:** Phase 16
**Requirements:** TBD
**Plans:** TBD
