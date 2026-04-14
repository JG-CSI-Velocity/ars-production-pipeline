# Requirements: Velocity Pipeline Merge

**Defined:** 2026-04-10
**Core Value:** Data integrity above all else -- every analysis module must produce numerically identical results to validated Jupyter notebook outputs.

## v1.1 Requirements

Requirements for the TXN merge milestone. Each maps to roadmap phases.

### Repo Setup

- [x] **REPO-01**: Local repo reset to clean GitHub state (a314c50)
- [x] **REPO-02**: Working directory has no leftover v1.0 artifacts outside 00-05 structure

### Folder Structure

- [x] **FOLD-01**: 02_Presentations/ directory exists on GitHub
- [x] **FOLD-02**: 03_Config/ directory exists with ars_config.json and settings.py
- [x] **FOLD-03**: 04_Logs/ directory exists on GitHub
- [x] **FOLD-04**: 05_UI/ directory exists with FastAPI app and static files (moved from ui/)
- [x] **FOLD-05**: GitHub repo folder structure mirrors M:\ARS\ 00-05 layout exactly

### TXN Script Merge

- [x] **TXN-01**: 22 TXN folders created under 01_Analysis/00-Scripts/analytics/ (plus txn_setup/)
- [x] **TXN-02**: All 325 TXN scripts copied with .py extensions
- [x] **TXN-03**: ARS attrition/ stays separate from TXN attrition_txn/
- [x] **TXN-04**: ARS rege/ stays separate from TXN rege_overdraft/
- [x] **TXN-05**: ARS mailer/ stays separate from TXN campaign/
- [x] **TXN-06**: Setup scripts placed in txn_setup/ under analytics/

### Setup Parameterization

- [x] **PARAM-01**: TXN setup scripts accept client ID from environment (not hardcoded 1776)
- [x] **PARAM-02**: TXN file paths read from TXN Files/{CSM}/{client_id}/ with trailing 12-month window

### Verification

- [ ] **VERIF-01**: Existing ARS formatting pipeline runs without errors after merge
- [ ] **VERIF-02**: Existing ARS analysis modules run without errors after merge
- [ ] **VERIF-03**: Existing PowerPoint generation works after merge
- [ ] **VERIF-04**: Each folder commit can be pulled independently on work PC

## v1.0 Requirements (completed, then reverted)

The v1.0 milestone built framework code that was reverted from GitHub on 2026-04-10. These requirements are not active -- documented for history only. See MILESTONES.md for details.

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Integration

- **INTG-01**: TXN modules registered in analysis runner alongside ARS modules
- **INTG-02**: TXN sections available in report presets
- **INTG-03**: UI can trigger TXN analysis runs
- **INTG-04**: Combined ARS+TXN report generation in single pipeline run

## Out of Scope

| Feature | Reason |
|---------|--------|
| Velocity Python package | v1.0 lesson: no framework without implementation |
| YAML manifests / section registry | Defer abstraction until scripts are merged and working |
| New UI pages | UI restructure only (move ui/ to 05_UI/); no new features |
| Automated testing framework | Focus on file merge; testing comes after scripts are verified |
| Schedule/batch automation | Defer until pipeline integration is complete |
| Jupyter notebook migration | Notebook stays as JG's validation tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REPO-01 | Phase 11 | Complete |
| REPO-02 | Phase 11 | Complete |
| FOLD-01 | Phase 12 | Complete |
| FOLD-02 | Phase 12 | Complete |
| FOLD-03 | Phase 12 | Complete |
| FOLD-04 | Phase 12 | Complete |
| FOLD-05 | Phase 12 | Complete |
| TXN-01 | Phase 13-14 | Complete |
| TXN-02 | Phase 13-14 | Complete |
| TXN-03 | Phase 13 | Complete |
| TXN-04 | Phase 13 | Complete |
| TXN-05 | Phase 13 | Complete |
| TXN-06 | Phase 13 | Complete |
| PARAM-01 | Phase 15 | Complete |
| PARAM-02 | Phase 15 | Complete |
| VERIF-01 | Phase 16 | Pending |
| VERIF-02 | Phase 16 | Pending |
| VERIF-03 | Phase 16 | Pending |
| VERIF-04 | Phase 16 | Pending |

**Coverage:**
- v1.1 requirements: 19 total
- Complete: 15
- Pending (verification): 4

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-13 after Phase 15 completion*
