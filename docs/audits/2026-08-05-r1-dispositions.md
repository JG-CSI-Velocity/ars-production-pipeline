# Persona Audit Round 1 — Dispositions (2026-08-05)

Every round-1 finding with what happened to it. Sources:
`2026-08-05-r1-csm-operator.md` (Dana), `2026-08-05-r1-data-engineer.md`
(Priya), `2026-08-05-r1-exec-consumer.md` (Marcus), `2026-08-05-r1-e2e.md`.

Legend: **FIXED** (on main, tested) · **ISSUE** (filed, owner decision or
larger work) · **DEFERRED** (documented in docs/improvements-2026-08.md or
tracker, not yet scheduled) · **OPEN** (needs work-PC or JG input).

## CSM operator (Dana)

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | Schedules tab silent placebo | **FIXED** (honest notice; execution itself ships with feat/schedule-execution) |
| 2 | Launcher/server port mismatch → stale server | **FIXED** (`Start Here.bat` kills stale :8000 listener) — e4cc64d |
| 3 | Refresh/restart mid-run = spinner forever | **FIXED** (lost-contact state + /api/active_runs reattach banner) |
| 4 | Rebuild/preview config-key bug (name = client ID) | **FIXED** (`_client_meta`, tested) |
| 5 | Results dropdown race + cross-tab preview | **DEFERRED** (needs a larger Results-tab refactor; round-2 target) |
| 6 | History dead-end | **FIXED** (product/modules columns, View-log tail) |
| 7 | sections.json recovery is CLI-only | **DEFERRED** (Rebuild-module-list button; small, queued) |
| 8 | Scorecard shipped but never rendered | **FIXED** (expander) |
| 9 | Run Quality speaks auditor | **DEFERRED** (copy pass queued) |
| 10 | Diagnostic completion → GitHub instructions | **DEFERRED** (inline View/Download buttons queued) |
| 11 | Fake progress %, Format checklist regex stall | **DEFERRED** (needs formatter stage markers) |
| 12 | Months dropdown 6-period cap | **DEFERRED** (Show-older option queued) |
| 13 | Blank client = format ALL, no confirm | **FIXED** (confirm with count/CSM) |
| 14 | Schedules always current-month, unsaid | **OPEN** (fold into feat/schedule-execution spec) |
| 15 | Hardcoded james.gilmore header | **FIXED** (shows selected CSM) |
| 16 | Gallery titles from filenames | **DEFERRED** (feed viewer from run_report titles) |
| 17 | Error wording points at app.py | **FIXED** (canonical recovery string) |
| 18 | Onboarding drifts (message string, 5-package verify, manifest hint) | **DEFERRED** (small doc/bat pass queued) |

## Data engineer (Priya)

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | Combined cache mtime-only staleness | **FIXED** (input-set manifest sidecar; exact-set HIT) — cee0b39 |
| 2 | Wall-clock trailing window | **FIXED** (anchored to report month, bounded both ends) |
| 3 | abs() sign rule vs credit filters | **ISSUE #262** (changes shipped numbers; parity divergence process) |
| 4 | v3 ingest→finalize crash window | **FIXED** (marker set inside ingest txn; regression test) |
| 5 | Parity never compares slide text | **ISSUE #264** (capture-surface extension, pre-cutover) |
| 6 | Vacuous/blind parity passes | **FIXED** (zero-slide hard-fail; figless section refuses recording) |
| 7 | unknown-SHA approvals immortal | **FIXED** (unknown matches nothing; test) |
| 8 | Chart-cache purge switch a no-op | **FIXED** (purge forces misses + clears persistent sidecars) |
| 9 | rege/mailer wall-clock ages | **FIXED** (as_of_ts anchor) |
| 10 | Eligible no-op silent to deck | **FIXED (partial)** — manifest WARN flag; label/footer stamping + B4–B7 relabels remain OPEN with #250-class owner review |
| 11 | Attrition denominator env toggle | **DEFERRED** (move to clients_config; record in run report) |
| 12 | In-memory run claim, single process | **DEFERRED** (cross-process claim file; #232 lineage) |
| 13 | ODD sidecar basename key; staging quiescence | **DEFERRED** (low probability; queued) |
| 14 | PII/identity hygiene | **FIXED (partial)** — gitignore covers cross-sell CWD dir + root xlsx/csv; committed client-name comments remain (repo is private; revisit if visibility widens) |
| 15 | Value A11.1 label one layer off | **FIXED** (stamps Eligible Personal; audit map + test updated). Magic 0.80 fallback left as-is (dead code by guard; hard-fail is an owner call) |

## Exec consumer (Marcus)

| # | Finding | Disposition |
|---|---------|-------------|
| 1 | Blank-by-design exec slides | **ISSUE #263** (auto-draft Exec Summary) |
| 2 | 339-slide TXN deck vs 25/60/150 budgets | **ISSUE #263** (length law; KEEP/NIX review gates it) |
| 3 | Headlines never reach slides | **ISSUE #263** (SLIDE_LAYOUT_MAP rewiring) |
| 4 | Denominator labels vs code | **FIXED (partial)** — A11.x relabel, eligible no-op WARN; TXN rate audit + B4–B7 remain OPEN |
| 5 | Zero-shaped fallbacks | **ISSUE #263** (drop-don't-zero policy) + deck_qa zero/split checks already on main (416119a) |
| 6 | ic_rate change unexplained on slides | **DEFERRED** (assumption-change footnotes; improvements 1.6) |
| 7 | Analyst artifacts in main deck | **ISSUE #263** (KEEP/NIX review) |
| 8 | Mid-deck sag, no section synthesis leads | **DEFERRED** (DCTR-MAIN specs already define the fix) |
| 9 | Boilerplate speaker notes; action tables never slide | **DEFERRED** (improvements 1.2/1.3 family) |
| 10-11 | Polish items | **DEFERRED** |

## New issues filed this round

- **#262** TXN abs() sign rule (decision required — changes numbers)
- **#263** Deck value umbrella (exec summary, headlines, length, drop-don't-zero)
- **#264** Parity slide-text capture

## Round-2 verification targets

1. Re-run personas against main @ e4cc64d.
2. Confirm each FIXED row above holds under fresh eyes.
3. Grade the DEFERRED queue: anything a persona still rates BLOCKER/CRITICAL
   gets promoted to immediate work.
