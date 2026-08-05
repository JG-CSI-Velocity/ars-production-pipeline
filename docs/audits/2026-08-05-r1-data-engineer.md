# Data-Engineering Audit — Round 1

**Persona:** "Priya" — senior data engineer, external review
**Date:** 2026-08-05
**Scope:** Denominator/rate correctness (sampled: dctr, rege, attrition, competition, payroll, value, mailer, insights), cache invalidation (parquet ODD cache, chart cache, v3 DuckDB staging), crash/concurrency safety, reproducibility, the ars_parity harness, and data hygiene. All findings verified against source unless marked SUSPECTED. Prioritized: things that produce wrong numbers silently.

---

## 1. Legacy TXN combined-parquet cache freshness is mtime-only — stale numbers on file deletion or mtime-preserving re-delivery

**Severity:** CRITICAL-wrong-numbers
**Where:** `01_Analysis/00-Scripts/analytics/txn_setup/02-file-config.py:262-284`; key layout in `01_Analysis/00-Scripts/analytics/txn_cache.py:63-74`
**Defect:** The combined cache (`{client_id}_combined_cache.parquet`) is validated only by "cache mtime > newest surviving file's mtime". Two silent-stale paths:
1. **File removed** (e.g. the operator deletes the duplicate month from issue #251, or a mis-delivered file): the cache, which baked that file's rows in, is still "newer than all files" → `HIT`, and the double-counted month keeps shipping.
2. **Corrected re-delivery with preserved mtime**: `shutil.copy2`/robocopy/SMB copies preserve the source mtime. A corrected file whose mtime predates the cache write reads as `HIT` → old numbers served for a new file.
Additionally, when `files_to_load` is empty the cache is trusted unconditionally (`Status: HIT (no raw TXN files found; using cache)`).
**Evidence:**
```python
_newest_file_mtime = max(f.stat().st_mtime for f in files_to_load)
if _cache_mtime > _newest_file_mtime:
    USE_PARQUET_CACHE = _ACTIVE_CACHE
    ...
    print(f"  Status: HIT (skipping file read, saving ~25 min)")
```
Contrast: the v3 store fixed exactly this class with the orphan reconcile in `ars_engine/data/txn_store.py:249-281` ("a re-delivery under an alphabetically-earlier name silently DOUBLES every dollar/volume aggregate"). The legacy engine — the one in production — remains exposed.
**Suggested fix:** Key the cache on the file SET, not just newest mtime: store `{name: (size, mtime)}` of the inputs in a sidecar (or the parquet metadata) at save time and require exact-set equality for a HIT, mirroring the v3 `ingested_files` design. `file_cache_path()` in txn_cache.py already embeds `mtime+size` in the name for per-file caches — the combined cache should get the same treatment.

## 2. TXN trailing-12-month window is anchored to the wall clock, not the report month

**Severity:** CRITICAL-wrong-numbers (reproducibility)
**Where:** `01_Analysis/00-Scripts/analytics/txn_setup/02-file-config.py:194-196, 211`
**Defect:** File selection uses "today":
```python
now = datetime.now()
first_of_current_month = datetime(now.year, now.month, 1)
window_start = first_of_current_month - relativedelta(months=TRAILING_MONTHS)
...
recent_files = [f for f, d in dated_files if d >= window_start]
```
The same client/month deck run in June vs. re-run in August selects a different file set (newly delivered July/August files enter; the oldest months fall out) → every L12M TXN aggregate changes. Same inputs do NOT give the same deck; the "2026.06 deck" depends on when the button was clicked. This also compounds Finding 1: a late re-run can push ALL dated files outside the window → `files_to_load` empty → unconditional cache HIT with data from the old window.
**Suggested fix:** Anchor the window to the report month (`ctx.end_date` / the selected `month` folder), which the ARS side already does via `filter_l12m(df, ctx.start_date, ctx.end_date)` and `as_of_ts()`.

## 3. Global abs() sign rule destroys the credit/debit distinction payroll (and any credit-filtered section) depends on

**Severity:** CRITICAL-wrong-numbers
**Where:** `01_Analysis/00-Scripts/analytics/txn_setup/05-combine-data.py:20-21` interacting with `01_Analysis/00-Scripts/analytics/payroll/01_payroll_data.py:39, 232-241`
**Defect:** Combine applies an unconditional whole-book normalization:
```python
if combined_df['amount'].median() < 0:
    combined_df['amount'] = combined_df['amount'].abs()
```
For any client whose feed records debits as negative (median < 0 — the very condition that triggers the rule), every amount becomes positive. Downstream, payroll detection filters "credits":
```python
credit_mask = combined_df['amount'] > 0          # matches EVERY txn post-abs
...
_debit_amt = combined_df['amount'].clip(upper=0) # identically 0 post-abs
_credit_amt = combined_df['amount'].clip(lower=0) # == amount
```
Consequences, all silent: keyword/pattern payroll detection runs over debits too (a recurring $14.99 subscription debit qualifies as a "recurring credit pattern"), inflating "X% of accounts have detected payroll"; `total_debit` is 0 for every account and `total_credit == total_spend` on the account activity merge feeding payroll value/demographic slides. The v3 store reproduces the same rule (`txn_store.py:317-323`) for parity, so the defect will carry forward unless addressed as a documented divergence.
**Suggested fix:** Preserve the sign in a separate column (`amount_signed`) before normalizing, and point credit/debit masks at it; where the raw feed is truly unsigned, derive direction from `transaction_code`/`transaction_type` and stamp the deck when direction is unknowable. Flag as an owner decision under the parity process (`divergence_reason`).

## 4. v3 txn_store: crash between ingest commits and finalize() silently serves stale aggregates

**Severity:** MAJOR (v3 not yet production, but this defeats its own crash-safety design)
**Where:** `01_Analysis/00-Scripts/ars_engine/data/txn_store.py:210-247 (ingest loop), 294-298 (finalize trigger), 315 (marker set)`
**Defect:** `finalize_pending` is set only INSIDE `finalize()`. Each file ingest is its own committed transaction that also updates `ingested_files`. Kill the process (Windows sleep/reboot — the exact scenario the marker was built for) after one or more file commits but before `finalize()` starts, and the next `refresh()` sees: files already known → `skipped`; `rules_stale` false; aggregate tables present; `finalize_pending != "1"` → **no rebuild**. The aggregates (`monthly_by_merchant` etc.) then permanently exclude the newly ingested rows while `transactions` contains them — sections read stale, internally inconsistent tables with no error.
**Evidence:**
```python
if changed or rules_stale or aggregates_missing or finalize_interrupted:
    ...
    finalize(con, log=log)          # marker set inside finalize(), too late
```
**Suggested fix:** Set a dirty marker inside each file's ingest transaction (e.g. `_meta_set(con, "finalize_pending", "1")` between the `DELETE`/`INSERT` and `COMMIT`), so any committed ingest guarantees a finalize on the next refresh. One line, closes the window exactly.

## 5. Parity harness never compares slide text: titles, notes, KPIs, bullets, and headline scalars are invisible

**Severity:** MAJOR (a numeric regression on the deck surface passes parity)
**Where:** `01_Analysis/00-Scripts/ars_parity/capture.py:64-73`; `01_Analysis/00-Scripts/ars_parity/compare.py:131-141`
**Defect:** Slide-level parity compares exactly three booleans:
```python
for key in ("success", "has_chart", "has_excel"):
    if ginfo.get(key) != cinfo.get(key): ...
```
`title` and `module_id` are captured but never compared; `notes`, `kpis`, `bullets`, and the `ctx.results`-driven headline callouts (the numbers CSMs actually read on the slide — e.g. `value_1.pot_l12m`, `reg_e_1.opt_in_rate` on REGE-MAIN-1) are not captured at all. A v3 port that emits a correct Excel table and figure but a wrong headline number ("$1.2M potential" vs "$120K") is a clean PARITY PASS. Chart-only TXN slides are covered only when figdata exists (see Finding 6).
**Suggested fix:** Extend `run_report.json` capture to include `notes`/`kpis`/`bullets` per slide and compare them (numeric substrings under rtol, text exact). The plumbing already exists — `AnalysisResult` carries all three fields.

## 6. Parity harness accepts vacuous and partially-blind passes

**Severity:** MAJOR
**Where:** `01_Analysis/00-Scripts/ars_parity/capture.py:49-86`; `01_Analysis/00-Scripts/ars_parity/__main__.py:41-57, 60-90`
**Defect:** Two holes:
1. **Empty-snapshot pass.** `capture_run` never fails when `run_report.json` / `*_analysis.xlsx` are absent (wrong `--month` string, wrong `--product` suffix, wrong run dir): it saves a 0-slide/0-sheet/0-figure snapshot. `cmd_check` only requires `meta.json` to exist. Empty golden vs empty candidate → "PARITY PASS — no differences", and `record_check(..., passed=True)` counts toward the 2-client approval gate.
2. **Figure blindness is silent at check time.** figdata only exists when the legacy run was made with `ARS_PARITY_CAPTURE=1` (`figure_data.py:9-10`); `cmd_capture` prints a NOTE, but `cmd_check` happily passes a golden with zero figures — for the many legacy TXN scripts that are chart-only (`has_excel: false`), NOTHING numeric is compared for those sections.
**Suggested fix:** `cmd_check` should hard-fail (exit 2, not a recorded pass) when either snapshot has zero slides, and refuse `--section` recording for a section whose in-scope slides contribute zero sheets AND zero figures.

## 7. Sign-off SHA gate is bypassable when git is unavailable — which is the known state of the work machine

**Severity:** MAJOR
**Where:** `01_Analysis/00-Scripts/ars_parity/signoff.py:20-29, 94-103`
**Defect:** Approval requires passing checks "AT THE CURRENT ENGINE SHA", but:
```python
if _check_ok(r) and (r.get("sha") in (sha, "unknown"))
```
A check recorded with `sha == "unknown"` (git absent/failed — the M:\ARS work machine has a documented history of broken git) matches EVERY future SHA forever. Checks recorded on such a machine keep sections "passing" across arbitrary engine changes, quietly defeating the cutover gate. Also, per-run `--tolerances` overrides (`__main__.py:70-71`) are not recorded in the signoff entry, so a check passed under loosened tolerances is indistinguishable from a strict one.
**Suggested fix:** Treat `"unknown"` SHA as matching nothing (or only other `"unknown"`s recorded the same day, with a warning); persist the tolerance override file's hash in the check record.

## 8. Chart cache can ship stale PNGs after a code fix, and the advertised purge switch is a no-op

**Severity:** MAJOR
**Where:** `01_Analysis/00-Scripts/charts/cache.py:49-88 (keying), 30-31 vs 196-203 (purge)`
**Defect:** The fingerprint covers only the caller-chosen columns + extras; there is no mandatory code-version component. Fix a bug in a `draw_fn` (wrong bar computed from `ctx.results` scalars not in the fingerprint, wrong color mapping, wrong label math) and the cached PNG with the OLD numbers is served — the module docstring itself names this poisoning scenario. Worse, the documented recovery lever does nothing:
```python
# module docstring: "ARS_CHART_CACHE_PURGE=1   clear all .cachekey sidecars on import"
if os.environ.get("ARS_CHART_CACHE_PURGE") == "1":
    ...
    # We can't know the run dir at import; this is a defensive no-op.
```
An operator (or a UI button) that sets the switch believes the cache is purged; it is not, and the stale chart ships. `persistent_chart_dir` caches survive across runs and months, widening the exposure for mailer combo slides.
**Suggested fix:** Fold a per-callsite code-version token into every key by default (e.g. hash of the draw function's source via `inspect.getsource`, or a bumped literal enforced by review), and either implement the purge env var (walk `persistent_chart_dir` root + run charts dir) or delete its documentation. Per the UI-first rule, expose "Clear chart cache" as a UI action.

## 9. Wall-clock ages in rege and mailer bypass the canonical as_of_ts — past-month re-runs shift age buckets

**Severity:** MAJOR (silently different rates for the same reporting period)
**Where:** `01_Analysis/00-Scripts/analytics/rege/dimensions.py:197`; `01_Analysis/00-Scripts/analytics/mailer/_helpers.py:461`; canonical helper `01_Analysis/00-Scripts/analytics/base.py:25-34`
**Defect:** `base.as_of_ts(ctx)` exists precisely so ages anchor to the report end date ("replaces scattered pd.Timestamp.now()"), yet:
- rege A8.6 fallback: `d["Holder Age"] = (pd.Timestamp.now() - d["Birth Date"]).dt.days / 365.25` — for clients whose ODD carries `Birth Date` but not `Account Holder Age`, every holder-age opt-in bucket drifts with the run date; a re-run 2 months later moves boundary members between buckets and changes the printed A8.6 rates.
- mailer `_helpers.py:461`: `member_ages = (pd.Timestamp.now() - dob[valid_dob])...` — ten lines after the SAME function correctly uses `as_of_ts(ctx)` for account age (line 451). The "of Responders aged X" headline metric is wall-clock dependent.
(`insights/dormant.py:207` also uses `Timestamp.now()`, but only for scatter marker sizes — cosmetic, MINOR.)
**Suggested fix:** Replace both with `as_of_ts(ctx)`; add a repo-level test greping analytics for `Timestamp.now()`/`datetime.now()` outside an allowlist.

## 10. TXN eligible-filter no-op path leaves "Eligible"-labeled rates on the Open (or wider) layer; Appendix-B mislabels still open

**Severity:** MAJOR (denominator LAW violation, silent to the deck reader)
**Where:** `01_Analysis/00-Scripts/analytics/txn_wrapper.py:765-790`; `docs/EQUATION_DICTIONARY.md` Appendix B (B4-B7)
**Defect:** `_inject_eligible_filter` enforces the 4-layer framework, but when `ctx.subsets.eligible_data` is unavailable or no account column is recognized it no-ops with only a log warning: every TXN section then computes over the unfiltered universe while slide specs/labels continue to claim "Eligible". A misconfigured `EligibleStatusCodes` for a new client produces a full deck of mislabeled denominators with zero on-deck indication. This is the live-code twin of the already-documented-but-open B4 (competition), B5 (financial_services), B6 (rege_overdraft), B7 (attrition label) discrepancies in EQUATION_DICTIONARY Appendix B.
**Suggested fix:** When the filter no-ops, stamp the run manifest with a WARN-level flag (the `manifest.flag(FlagLevel.WARN, ...)` mechanism attrition already uses) AND force `denominator_label="Open"` on affected results so the audit step and deck QA see the truth; resolve B4-B7 with owner sign-off.

## 11. Attrition denominator is selected by an environment variable

**Severity:** MINOR (defaults are consistent; the risk is cross-machine divergence)
**Where:** `01_Analysis/00-Scripts/analytics/attrition/_helpers.py:255-264`
**Defect:** `ARS_ATTRITION_ELIGIBLE_ONLY=1` switches the entire attrition population from full book to the eligible-comparable book. The stamped label (`L12M Exposure`) does not change with the env var, so two machines (or a scheduled run with different env) print different attrition rates under the same label for the same month. The standardized `l12m_attrition` base itself is sound (closures ⊆ base; documented after the A9.x history).
**Suggested fix:** Move the toggle to `clients_config.json` (per-client, versioned, visible in the run manifest) and record its value in `run_report.json`.

## 12. In-memory run-collision guard only protects a single server process

**Severity:** MINOR (crash/concurrency)
**Where:** `05_UI/app.py:198-236`
**Defect:** `_reject_if_run_active` scans the in-process `runs` dict. Two server instances (double-launched `Start Here.bat`, or a dev CLI run beside the UI) share no claim file, so the #232 collision class (same output folder, `run_manifest.json` `os.replace` WinError 5, garbled logs) is still reachable cross-process. Also `product` is part of the identity tuple, so an `ars` run and a `combined` run for the same client/month are both admitted; SUSPECTED that both write the same completed-analysis folder (not fully traced).
**Suggested fix:** A claim file (`<run_dir>/.run.lock` with PID + started-at, stale after STALE_RUN_SECONDS) created via `O_EXCL` in the output folder; treat `combined` as colliding with its `ars`/`txn` constituents.

## 13. ODD sidecar cache is keyed by basename only, in a directory shared across clients; staging copies un-quiesced files

**Severity:** MINOR (low probability; silent wrong-client data if hit)
**Where:** `01_Analysis/00-Scripts/pipeline/steps/load.py:438-452`; `00_Formatting/00-Scripts/ars_staging/poller.py:234-240`
**Defect:**
1. Sidecar path is `<cache>/odd/{src.name}.{mtime}.{size}.pkl` — no client component (unlike `file_cache_path`, which nests under `<kind>/<client_id>/`). Two clients whose ODD exports share a generic basename (e.g. `ODD.xlsx`) AND coincide on int-mtime+size (batch-exported same second, same row template) would silently read each other's parsed frame.
2. Staging `copy2`s share files with no quiescence check; a TXN export still being written lands truncated in staging, gets ingested into the DuckDB store, and stays until the next poll notices the source stat changed. Transiently wrong aggregates, self-healing but unflagged.
**Suggested fix:** Add the client id (or full source path hash) to the sidecar name; in staging, require size stable across two stats ~seconds apart (or compare stat before/after copy) before recording the manifest entry.

## 14. Data hygiene: client identities in committed source; account-list output dir not gitignored

**Severity:** MINOR (hygiene; no account-level PII currently tracked — verified)
**Where:** `.gitignore`; `01_Analysis/00-Scripts/analytics/competition/01_competitor_config.py:756,785`; `01_Analysis/00-Scripts/analytics/txn_file_detection.py:8`; multiple tests; `03_Config/clients_config.json`
**Defect:**
1. Real institution identities are committed: `'1776': { # CoastHills (Central Coast, CA)` and `'1615': { # Cape & Coast Bank (Cape Cod, MA)`; tests hardcode `client_name="CoastHills CU"`; `clients_config.json` BranchMapping ties client IDs to branch towns (Lompoc, Santa Maria, ...). The "config has no names" assumption doesn't hold in practice.
2. `01_Analysis/00-Scripts/Actionable Lists for Clients/` (currently `1776_CoastHills CU/cross_sell_lists/`, empty) is NOT ignored — `git check-ignore` returns non-match; the `.gitignore` pattern covers `01_Analysis/Actionable Lists for Clients/` only. The moment an account-level cross-sell CSV is generated there on a dev machine, `git add -A` commits real member PII.
3. Root ignore covers `/*.pptx` and `/*.mp4` but not root `*.xlsx`/`*.csv` beyond `SLIDE_MANIFEST.xlsx` — a deck's companion analysis workbook parked at the root would be tracked. (Client deck files currently at the repo root, e.g. `1615-2026-02-Cape & Coast Bank-ARS Results.pptx`, are ignored — verified untracked.)
**Suggested fix:** Add `01_Analysis/00-Scripts/Actionable Lists for Clients/` and root `/*.xlsx` (with a `!SLIDE_MANIFEST.template.xlsx` exception) to `.gitignore`; move client-identifying comments/fixtures to an untracked local config or neutral fixtures if the repo's visibility ever widens.

## 15. Value A11.1 denominator label is one layer off

**Severity:** MINOR (label, not math)
**Where:** `01_Analysis/00-Scripts/analytics/value/analysis.py:277, 300-313, 448-449`
**Defect:** The base is `ctx.subsets.eligible_personal` further filtered to L12M-active (open, or closed on/after `start_date`), but the result stamps `denominator_label="Eligible"`. Under the 4-layer LAW this is **Eligible Personal** (with an activity overlay that isn't one of the four layers at all). Also line 372 falls back to a magic `0.80` DCTR when the eligible-personal base is empty — unreachable today (guarded at 278) but a numeric landmine for refactors.
**Suggested fix:** Stamp `"Eligible Personal"` and note the L12M-active overlay in the slide's methodology text; replace `0.80` with a hard failure.

---

## Top 5 by risk to shipped numbers

1. **Finding 1 — combined-cache mtime-only invalidation (legacy, in production today):** a deleted or mtime-preserving re-delivered TXN file silently serves last delivery's numbers across every TXN section of the deck.
2. **Finding 3 — abs() sign rule vs. credit-filtered analytics:** for debit-negative feeds, payroll penetration/value and every credit/debit split are computed on a universe where "credit" means "everything"; wrong headline percentages with no warning, and v3 will faithfully reproduce it.
3. **Finding 2 — wall-clock trailing window:** the same month's deck changes numbers depending on the run date; combined with Finding 1 it can pin an entire run to an outdated cache.
4. **Findings 5+6+7 — parity harness blind spots (headline text uncompared, vacuous passes recordable, "unknown"-SHA approvals immortal):** the v3 cutover gate can go green while the deck surface regresses — this is the mechanism meant to prevent every other wrong number, so holes here multiply all v3 risk.
5. **Finding 4 — v3 ingest/finalize crash window:** a mid-run kill at the wrong moment leaves DuckDB aggregates permanently missing ingested rows, silently, on the engine intended to replace the legacy path.
