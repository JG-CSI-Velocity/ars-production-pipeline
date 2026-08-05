# Data-Engineering Audit — Round 2 (Adversarial Verification)

**Persona:** "Priya" — senior data engineer, fresh eyes
**Date:** 2026-08-05
**Scope:** Refute-or-verify every data-engineer row marked FIXED in
`docs/audits/2026-08-05-r1-dispositions.md` (fix commit `cee0b39` and
neighbors, on main), re-grade DEFERRED rows 11–13, plus new findings.
Every REFUTED verdict below carries a concrete failing input or a runtime
reproduction, not just a reading of the code.

**Test evidence:** targeted files
(`test_txn_cache_inputs.py`, `test_v3_txn_store.py`, `test_v3_parity.py`,
`test_audit.py`) — **58 passed**. Full suite — **565 passed in 38s**.
Both refutations below live on paths the suite does not execute.

**Verdict counts: 7 VERIFIED · 1 REFUTED · 2 PARTIALLY REFUTED · 3 DEFERRED unchanged (no promotions).**

---

## Per-fix verdicts

### 1. Combined-cache input-set manifest — VERIFIED (two residual gaps, below)

- Manifest write is on the **single** save path: the only `to_parquet` for the
  combined cache is `09-oddd-account-type.py:167`, and
  `save_input_manifest(PARQUET_CACHE, files_to_load)` at
  `09-oddd-account-type.py:184` runs inside the same `_save_cache()` used by
  all three dirty triggers (rebuild, consolidation recompute, ODD re-merge —
  `_cache_dirty` at `09:146-150`). Pure HITs skip the save, correctly.
- Crash ordering is safe: parquet `replace` lands before the manifest write,
  so a kill in between leaves a new cache with the OLD manifest → set
  mismatch → MISS → clean rebuild. Fail-toward-rebuild, correct direction.
- Legacy-migration read path (`_ACTIVE_CACHE != PARQUET_CACHE`,
  `02-file-config.py:184-187`): `input_set_matches` is called against
  `_ACTIVE_CACHE` (`02:294`); the share-side legacy cache has no sidecar →
  returns `None` → documented mtime fallback with an explicit
  "pre-manifest cache" status line (`02:312-313`). Acceptable and honest.
- Refutation attempts that FAILED (fix holds): deleted input
  (`test_deleted_input_invalidates`), mtime-preserving re-delivery
  (`test_mtime_preserving_redelivery_invalidates`), added input, corrupt
  manifest — all covered and passing.

**Residual gap A (accepted r1 risk, still open):** the empty
`files_to_load` branch at `02-file-config.py:279-285` is checked BEFORE the
manifest and is still an unconditional HIT. Failing scenario: operator
deletes ALL raw TXN files (or every file falls outside the report window) →
`Status: HIT (no raw TXN files found; using cache)` serves the old data with
zero manifest consultation, even though the manifest (non-empty recorded set
vs. empty current set) would flag exactly this. One-line fix: consult
`input_set_matches(_ACTIVE_CACHE, [])` in that branch and warn on mismatch.

**Residual gap B (new, MINOR):** `input_set_matches` keys entries by
`Path(f).name` only (`txn_cache.py:98,132`). `files_to_load` can contain a
flat file and a year-subfolder file with the same basename
(`gather_all_txn_files`, `02:152-159`); dict-key collision means last-stat
wins and a same-name/same-stat move between layouts is invisible. Contrast
v3's `_source_key` (`txn_store.py:171-184`), which was built to avoid
exactly this. Low probability; key by relative path to close.

### 2. Report-month window anchor — **REFUTED: ships a NameError on every TXN run**

The window logic itself is correct — I tried and failed to break it:

- `MONTH="2026.06"` → window `[2025-07-01, 2026-07-01)` (`02:201-211`);
  a 2026-06-30 file is in, a 2026-07-01 file is excluded by the new upper
  bound (`02:228`), a 2025-07-01 file is in, 2025-06-30 out. Half-open
  interval is right at both edges.
- Malformed/absent `MONTH` falls back to wall clock with a printed NOTE
  (`02:205-210`) — degraded but honest.
- Unparsed-date files still always included (`02:232`) — unchanged r1
  behavior, deliberate.

But the refactor renamed `first_of_current_month` → `window_end` and missed
the summary print:

```
02-file-config.py:352
print(f"Trailing window:     {window_start:%Y-%m-%d} to {first_of_current_month:%Y-%m-%d} ...")
```

`first_of_current_month` is defined **nowhere** in the file or the exec
namespace (repo-wide grep: zero definitions). **Runtime-reproduced** in a
scratch mirror of the repo layout: the script executes the entire cache
decision, then dies at line 352 with
`NameError: name 'first_of_current_month' is not defined`.

Blast radius: `txn_wrapper._execute_scripts` catches the exception per
script (`txn_wrapper.py:304-310`), so every TXN run now logs
`txn_setup FAILURES (1): 02-file-config.py -- downstream sections likely broken`
(`txn_wrapper.py:958-967`) and records a failed setup script in the run
manifest / Run Quality panel. Because the failure is at the summary print,
all state downstream sections need (window, `files_to_load`,
`USE_PARQUET_CACHE`) is already set — numbers are RIGHT, but every run is
branded as having a critical setup failure, the `unparsed dates` and
`No TXN files` warnings at `02:356-362` never print, and a real
02-file-config failure is now indistinguishable from this permanent one.
Cry-wolf state on the exact panel fix #10 routes its warnings to.

Why the suite missed it: `test_txn_cache_inputs.py` tests the `txn_cache`
helpers only; nothing execs `02-file-config.py`. The scratch-mirror exec
used for this reproduction would make a cheap regression test.

**Fix:** use `window_end` at line 352 (one word); add an exec-smoke test.

### 4. v3 finalize_pending — PARTIALLY REFUTED

The r1 kill-window is genuinely closed:

- Marker set INSIDE each ingest transaction (`txn_store.py:233-239`,
  between `BEGIN` and `COMMIT`), and before orphan removal
  (`txn_store.py:279`). A kill after any committed ingest and before
  `finalize()` leaves `finalize_pending=1` → next refresh rebuilds
  (`txn_store.py:303-307`). Covered by passing tests in
  `test_v3_txn_store.py`.

But the fix's empty-store early-return opens a NEW silent-stale hole —
**runtime-confirmed** against the real module:

```
finalize(), txn_store.py:321-327
if n == 0:
    _meta_set(con, "finalize_pending", "0")   # marker cleared...
    return                                     # ...aggregate tables NOT dropped
```

Failing sequence (reproduced with duckdb in the venv):
1. Ingest file A, finalize → `monthly_by_merchant` has A's rows.
2. Next poll: A leaves the staged set (de-staged/alias), replacement B fails
   to parse (`refresh` records the error and continues, `txn_store.py:221-226`).
3. Orphan reconcile deletes A's rows → `transactions` is EMPTY →
   `finalize()` early-returns, **clears the marker**, and leaves the
   aggregate tables fully populated with A's data.
4. Every subsequent refresh: no change, rules fresh, aggregates present,
   no pending marker → **stale aggregates served indefinitely** while
   `transactions` holds zero rows. Observed state after step 3:
   `transactions=0, monthly_by_merchant=1, finalize_pending='0'`.

This is precisely the "internally inconsistent tables with no error" failure
the marker was built to kill. **Fix:** in the `n == 0` branch, `DROP`/empty
the `AGGREGATE_TABLES` before clearing the marker (an empty store should
serve empty aggregates, not last month's).

Secondary (MINOR, new): the orphan-removal block is NOT wrapped in an
explicit transaction (`txn_store.py:279-285`) — DuckDB autocommits each
statement. A kill between `DELETE FROM transactions` (line 281) and
`DELETE FROM ingested_files` (line 284) leaves an `ingested_files` row for
data that is gone; if that file later re-enters the staged set with
identical size/mtime, `known.get(key) == (size, mtime)` skips it
(`txn_store.py:218-219`) and its rows are silently absent forever. Wrap the
three statements in `BEGIN`/`COMMIT` like the ingest loop.

### 6. Vacuous/blind parity passes — VERIFIED (one scoping gap)

- Zero-slide hard-fail: `__main__.py:73-79` exits 2 for EITHER empty
  snapshot before any diff or recording. Refutation attempt (record via a
  passing empty-vs-empty check) is dead: `record_check` is unreachable past
  the guard, and `check` without `--section` records nothing.
- Figless recording refused: `__main__.py:92-102` exits 2 when
  `--section` is given and golden has zero sheets AND zero figures.
- Candidate-side blindness is covered by compare symmetry: a candidate
  missing sheets/figures the golden has produces `<presence>` diffs
  (`compare.py:147-149,157-159`), and candidate-only surfaces diff too
  (`compare.py:166-173`). Passed=False then voids prior approval
  (`signoff.py:82-85`).

**Gap (residual, matches r1's exact suggested wording, not implemented):**
the guard is snapshot-global, not prefix-scoped. Failing scenario: a mixed
`txn` golden where some sections have Excel but `TXN-MERCH-*` is chart-only
and was captured without `ARS_PARITY_CAPTURE=1`. Then
`check --prefix TXN-MERCH- --section txn.merchant` passes the guard
(`golden.sheets` non-empty), the prefix filter excludes every sheet/figure
in scope (`compare.py:76-79,145,155`), and the recorded "pass" verified
only three slide booleans. Fix: apply `_included(...)` to the guard's
sheet/figure counts.

### 7. unknown-SHA approvals — VERIFIED (SHA half); tolerance provenance still missing

- `signoff.py:104-108`: `r.get("sha") == sha and sha != "unknown"` —
  a check recorded with `sha == "unknown"` matches nothing, and a machine
  whose CURRENT sha is unknown gets an empty passing list, so
  `approve` raises (`signoff.py:116-120`). Refutation attempts (record on
  broken-git machine then approve anywhere; approve from the broken-git
  machine) both blocked. Tested in the passing parity test file.
- **Residual from r1 #7 (not addressed, not claimed):** `--tolerances`
  overrides (`__main__.py:81-83`) still leave no trace in the recorded
  check (`signoff.py:70-81` has no tolerance field) — a check passed under
  loosened per-column rtol is indistinguishable from a strict one.

### 8. Chart-cache purge — VERIFIED (two footnotes)

- `CACHE_PURGE` forces every `cached_chart` lookup to miss
  (`cache.py:124`) and re-stamps fresh sidecars (`cache.py:135-139`);
  import-time purge clears persistent sidecars (`cache.py:202-211`) via a
  real `purge_cache` walk (`cache.py:182-199`). The documented lever now
  does what it says.
- Refutation attempt on the `chart_is_cached` bypass: `chart_is_cached`
  does NOT consult `CACHE_PURGE` (`cache.py:156-167`), but both callers
  (`mailer/cohort.py:532`, `mailer/response.py:235`) key off
  `persistent_chart_dir(...)` whose sidecars the import-time purge already
  deleted in the same process, so the lookup misses anyway. Holds today —
  but only by this coincidence of call sites; `chart_is_cached` should
  check `CACHE_PURGE` explicitly before someone points it at a per-run path.
- `CACHE_PURGE` + `CACHE_DISABLED` together: disabled wins in
  `cached_chart` (draws every time, writes no sidecars) and the import-time
  sidecar deletion still runs — no interaction bug.
- Footnotes: (a) the r1 root cause — no code-version token in the
  fingerprint — remains; the purge is the recovery lever, not prevention
  (per-callsite `_COMBO_CACHE_V`-style versions exist only where authors
  remembered). (b) The lever is env-var-only; per the repo's UI-first rule
  there is still no "Clear chart cache" action in `05_UI` (no
  `ARS_CHART_CACHE_PURGE` reference in `app.py`).

### 9. as_of_ts anchors in rege/mailer — VERIFIED

- `rege/dimensions.py:199`: inside `by_holder_age`, a closure defined in
  `_holder_age(self, ctx, ...)` — `ctx` is captured from the enclosing
  scope; import at `dimensions.py:13`. In scope, correct.
- `mailer/_helpers.py:463`: same function whose line 451 already used
  `as_of_ts(ctx)`; `ctx` is a parameter (used at 443). In scope, correct.
- Fallback: `as_of_ts` returns `pd.Timestamp.now()` only when
  `ctx.end_date` is None (`base.py:33-34`) — wall clock can only re-enter
  on a pipeline run with no end date, which is the documented intent.
- Remaining `Timestamp.now()` in analytics: `insights/dormant.py:207`
  (scatter marker sizes, cosmetic — r1 already graded MINOR) and the
  `base.py` fallback itself. The r1-suggested grep-allowlist test was not
  added; without it the next contributor can reintroduce a wall-clock age
  silently.

### 10. Eligible no-op WARN flag — VERIFIED as the partial it claims to be

- Fires on BOTH no-op branches: eligible_data unavailable
  (`txn_wrapper.py:790-791`) and no recognized account column
  (`txn_wrapper.py:813`). `_flag_eligible_noop` uses the same
  `manifest.flag(FlagLevel.WARN, ...)` machinery attrition uses
  (`txn_wrapper.py:745-765`; `pipeline/manifest.py:177,298`), and app.py
  surfaces manifest flags in the quality panel.
- `manifest is None` paths: `PipelineContext.manifest` defaults to None
  (`pipeline/context.py:111`) and is populated by `runner.start_run()` —
  so any invocation outside the runner (standalone/legacy driving of
  `txn_wrapper`) silently drops the flag (`txn_wrapper.py:751-753`) and
  reverts to log-only. On the normal UI run path the manifest exists.
- Cosmetic asymmetry: the no-acct-column branch skips
  `_log_total_vs_eligible` (the unavailable branch calls it with None).
- As the disposition itself states: deck labels/footers still claim
  "Eligible" when the filter no-ops, and B4–B7 remain open. The flag is a
  trace, not a correction — grading only what was claimed. VERIFIED.

### 14. Hygiene gitignore — VERIFIED (partial as documented)

`git check-ignore -v` confirms all three: the CWD-relative cross-sell dir
(`.gitignore:44-45`), root `/*.xlsx` + `/*.csv` with the
`!/SLIDE_MANIFEST.template.xlsx` exception (`.gitignore:58-60`).
Committed client-name comments/fixtures remain, as the disposition
acknowledges (private repo, revisit on visibility change).

### 15. A11.x denominator label — PARTIALLY REFUTED (deck surface still says "Eligible")

What holds:
- `value/analysis.py:451` stamps `denominator_label="Eligible Personal"`
  on A11.1 with the L12M-active overlay noted in comments; the audit
  registry maps `A11` → "Eligible Personal" with length-sorted prefix
  matching so A11 beats A1 (`pipeline/steps/audit.py:73-77,107,121`);
  tests updated and passing. The 0.80 fallback at
  `value/analysis.py:372` is unchanged — still dead code behind the
  emptiness guard, per the disposition's owner-call note.

What refutes completeness — two consumers still expect/emit "Eligible"
for value slides (the exact question r1's finding was about):

1. **`docs/slide_specs/value.yml:21`** — `VALUE-MAIN-1` declares
   `denominator_label: Eligible` (and the file header comment says
   "Anchors to Eligible"). That spec label flows onto the rendered slide:
   `output/slide_spec.py:124` reads it, `:402` copies it to the rendered
   slide, and `output/deck_builder.py:2022,2047` carries it into the deck.
   So the deck the CSM ships still labels the value slide **Eligible**
   while the AnalysisResult and the denominator audit now say
   **Eligible Personal** — the run report and the slide disagree about the
   same number. "Eligible" is in the audit's `LAW_LABELS`, so no test or
   QA check trips on the inconsistency.
2. **`docs/EQUATION_DICTIONARY.md:283`** — still documents
   "A11.1 stamps `denominator_label=\"Eligible\"` ... `value.yml` labels
   Eligible". The dictionary is the reference operators are told to trust;
   it now describes pre-fix behavior.

Also within scope of "A11.x": **A11.2's** actual base is
`eligible_personal ∩ _is_debit_yes` (`value/analysis.py:488`) — the
**Eligible Personal w/Debit** layer — but A11.2 stamps nothing, so the
registry labels it "Eligible Personal" (`audit.py:77`). The r1 defect
("label one layer off") is fixed for A11.1 and reproduced verbatim for
A11.2. Fix: stamp `"Eligible Personal w/Debit"` on A11.2, update
`value.yml:21` to `Eligible Personal`, refresh EQUATION_DICTIONARY §283.

---

## DEFERRED re-grades (rows 11–13)

| # | Row | Current state | Grade |
|---|-----|---------------|-------|
| 11 | Attrition env toggle | Unchanged: `ARS_ATTRITION_ELIGIBLE_ONLY` still read at `analytics/attrition/_helpers.py:259-261`, label still doesn't change with it | **Keep DEFERRED (MINOR)** — defaults still consistent; becomes MAJOR if scheduled runs ever execute with a different env than click-time runs, so land it with (or before) feat/schedule-execution |
| 12 | In-process run guard | Unchanged: `_reject_if_run_active` at `05_UI/app.py:219` scans the in-process dict; no claim file, no `O_EXCL` anywhere in app.py | **Keep DEFERRED (MINOR)** — e4cc64d (launcher kills stale :8000 listener) actually reduces the double-server path; feat/schedule-execution spec is in-process-thread, so no new cross-process writer is imminent |
| 13 | ODD sidecar key / staging quiescence | Unchanged: sidecar still `{name}.{mtime}.{size}.pkl` with no client component (`pipeline/steps/load.py:450`); poller still `copy2`s with no size-stability check (`ars_staging/poller.py:236-244`) — though stat-before-copy at `:241` means a mid-copy change is caught next poll (self-healing, as r1 said) | **Keep DEFERRED (MINOR)** — probability unchanged; both fixes remain small |

No promotions: none of the three got worse, and nothing merged since r1
increased their exposure.

---

## New findings (round 1 missed)

1. **NameError at `02-file-config.py:352`** — detailed under fix #2 above.
   Severity: MAJOR (every TXN run reports a failed setup script; warnings
   after line 352 never print; permanent cry-wolf in Run Quality).
2. **v3 empty-store finalize hole** (`txn_store.py:321-327`) — detailed
   under fix #4. Severity: MAJOR-for-v3 (silent stale aggregates,
   runtime-confirmed).
3. **v3 orphan removal not transactional** (`txn_store.py:279-285`) —
   detailed under fix #4. Severity: MINOR (narrow window, silent row loss
   only on re-stage with identical stat).
4. **Manifest basename keying** (`txn_cache.py:98,132`) — under fix #1
   residual B. MINOR.
5. **Empty-`files_to_load` HIT skips the manifest** (`02:279-285`) —
   under fix #1 residual A. MINOR (probability dropped now the window no
   longer drifts with the wall clock, but the operator-deletes-everything
   case remains).
6. **Prefix-scoped vacuous parity pass** (`__main__.py:92`) — under fix
   #6. MINOR until TXN chart-only sections start their parity runs, then
   it sits directly on the cutover gate.
7. **Spec-vs-result denominator label divergence has no QA check** — the
   deck can stamp a different LAW label than the AnalysisResult for the
   same slide (see fix #15) and nothing compares them. Suggest: audit step
   cross-checks `rendered.denominator_label` against the result's stamp.

---

## Test results

| Command | Result |
|---|---|
| `pytest test_txn_cache_inputs.py test_v3_txn_store.py test_v3_parity.py test_audit.py -q` | 58 passed |
| `pytest -q` (full suite) | 565 passed in 38.16s |
| Scratch-mirror exec of `02-file-config.py` (MONTH=2026.06) | **NameError line 352** (refutation evidence, #2) |
| duckdb repro: ingest→finalize→orphan-all→refresh | **transactions=0, monthly_by_merchant=1, finalize_pending='0'** (refutation evidence, #4) |

Both refuted defects are invisible to the suite: nothing execs
`02-file-config.py`, and no txn_store test drives the
orphan-empties-the-store sequence. Add both as regression tests with the
fixes.
