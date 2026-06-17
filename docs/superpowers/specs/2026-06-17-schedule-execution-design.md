# Automatic Schedule Execution — Design

**Date:** 2026-06-17
**Branch:** `feat/schedule-execution`
**Status:** Design approved; pending spec review → implementation plan

## Problem

The UI already has a **Schedules** tab: a form to create a schedule (CSM, client,
product, day-of-month, extras), a table listing schedules, and **Run Now** /
**Delete** buttons, backed by `GET/POST/DELETE /api/schedules` persisting to
`M:\ARS\03_Config\schedules.json` plus `POST /api/schedules/{id}/run`.

Nothing makes it automatic. There is no tick loop, no cron, no scheduler — a
schedule only runs when a human clicks **Run Now**. The tab's own copy claims
"Schedules run automatically on the specified day," which is currently false.

Goal: make schedules fire on their own, let each schedule choose the **format**
process, the **generate** process, or both, keep setup dead simple, and give
everyone **one shared place** to see what is scheduled and what has run.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Firing model | **In-process background thread, claim-once** | No admin rights, no OS config, fully UI-operable. Best-effort per-month claim + idempotent runs: a job runs once when several CSMs have the UI open; a rare double-run just overwrites the same deck (wasted compute, not corruption). |
| Target month | **Current calendar month** | Confirmed. Matches the existing Run Now behavior; `current_report_month(today) = today's YYYY.MM`. |
| Schedule scope | **Per schedule: one client OR all of a CSM's clients** | Confirmed. `scope` field (`client` \| `csm`). Covers a one-off client and the real monthly "run all of Jordan's decks on the 5th." |
| Missing input | **Skip + retry daily, log "waiting for data"** | Tolerates late data dumps without manual babysitting. |
| Task per schedule | **format / generate / both** | Directly requested. `task` field, defaults to `both` for back-compat. |
| Status storage | **Claim file doubles as the per-schedule status (single writer); `schedules.json` is definition-only** | Eliminates concurrent read-modify-write on the one shared list. The claim winner is the only writer of that month's status. |
| Run history | **Per-run JSON record in a shared `04_Logs/runs/` ledger; Recent Runs reads that** | One writer per file (no contention), cross-machine, and replaces the flaky log-scraping that makes today's Recent Runs / gallery inaccurate. |
| Claim atomicity | **Best-effort exclusive-create + idempotent runs** | `O_CREAT\|O_EXCL` is not reliably atomic on SMB; rather than pretend exactly-once, accept that a rare duplicate harmlessly overwrites the same deck. |
| Code location | **All in `app.py`** (one file) | Per operator preference; engine is a clearly-marked section, still split into small testable functions. |
| Visibility | **Schedules tab is the single shared dashboard** | `schedules.json` (definitions) + per-schedule claim/status files, both on the shared drive, so every CSM's UI shows the same rows. No per-user filtering. |

### Explicitly out of scope (YAGNI)

- Weekly/daily frequency. Monthly day-of-month only.
- One-click Windows auto-start task (would let jobs fire with **no** UI open).
  Noted as a clean future add-on, not part of this work.

## Architecture

A background thread inside `app.py` wakes on an interval, finds due schedules,
and runs them through the **same** pipeline code the manual buttons use. Every
CSM runs their own `app.py`; coordination is via files on the shared `M:\ARS\`
drive, with each volatile file having a **single writer** so there is no
read-modify-write race.

### Three files, by who writes them

- **`03_Config/schedules.json` — definition only.** Holds the schedule list
  (csm, client/scope, product, day, task, enabled). Written *only* on user CRUD
  (create/delete/toggle), via write-temp-then-`os.replace` (atomic, no torn
  reads). The engine **never** writes here, so concurrent ticks can't clobber it.
- **`03_Config/schedule_claims/{id}.{month}.json` — per-month status.** Created
  by whichever engine *claims* a due schedule for the month; that machine is the
  sole writer. Holds `claimed_by`, `claimed_at`, `status`
  (`running`/`complete`/`error`/`waiting for data`), and per-client detail for
  csm-scope. The UI merges definitions + the current month's claim file to render
  each row's live status. Replaces the old plan of stamping status back into the
  shared list.
- **`04_Logs/runs/{run_id}.json` — the run-history ledger.** One structured
  record per run (manual *or* scheduled): csm, client, month, product, task,
  status, started/finished, deck path, error. Written once by the running
  machine. Recent Runs and the gallery read this directory instead of scraping
  text logs — which is the root cause of today's inaccurate history.

There is no central server; the "central location" is these shared files plus the
Schedules tab that renders them — every UI shows the same rows.

### Claim = best-effort, runs = idempotent

A claim is an exclusive-create (`open(path, "x")`) of the per-month claim file.
On SMB this is best-effort, not a hard mutex, so the guarantee is softened
honestly: in the rare case two machines both "win," each rebuilds the **same**
deck to the **same** path — one overwrites the other. Wasted minutes, never
corruption. A stale claim (older than ~6h with no completion) may be re-claimed
so a crashed run doesn't wedge the month.

### Firing logic (`>=`, not `==`)

Due detection uses `today.day >= schedule.day` AND no completed claim file exists
for `(schedule, current_report_month)`. Using `>=` means if no UI was open *on*
the exact day, the first tick afterward (still within the month) catches up.
Paired with claim-once and skip-on-missing-data, this is robust to machines being
off.

## Components — all in `app.py`

### Engine section (new, small functions; imported by tests)

- `current_report_month(today) -> "YYYY.MM"` — current calendar month.
- `claim_status(schedule_id, month) -> dict|None` — read the per-month claim
  file (status sidecar), or None if unclaimed. Pure read.
- `due_schedules(schedules, today, claim_lookup) -> list` — enabled,
  `today.day >= day`, and no **completed** claim for the current month
  (a `waiting for data` / stale claim is still due). Pure function; takes a
  `claim_lookup(id, month)` callable so tests inject claim state.
- `try_claim(claims_dir, schedule_id, month) -> bool` — best-effort exclusive
  create (`open(..., "x")`) of the claim file. Winner runs and owns the file as
  the sole status writer; losers skip. A stale claim (older than ~6h with no
  recorded completion) may be re-claimed so a crashed run does not wedge the month.
- `update_claim(schedule_id, month, **fields)` — single-writer status update on
  the claim file (the claim winner only): `status`, `clients` detail, timestamps.
- `clients_for_scope(schedule, month) -> list[client_id]` — for `scope=client`,
  just `[client_id]`; for `scope=csm`, enumerate the CSM's clients for the month
  (reuse the `/api/clients` raw-dump + formatted-folder union).
- `SchedulerEngine` thread — tick on startup, then every ~10 minutes. For each
  due schedule: resolve `clients_for_scope`; if none ready (`_input_ready`), set
  the claim status to `waiting for data` and retry next tick; else `try_claim()`;
  if won, run each ready client through `_execute_pipeline`, writing a ledger
  record per client and updating the claim file's per-client status; mark the
  claim `complete`/`error` when done. Tracks `last_tick_at` for the heartbeat.
- Started once on FastAPI startup.

### Pipeline driver refactor

Today the format/analysis subprocess plumbing is duplicated across `/api/format`,
`/api/run`, **and** the run-now handler — three near-identical copies. Collapse to
one:

- `_execute_pipeline(run_id, csm, month, client_id, product, task, extras, source_path="")`
  — `task` (`format` | `generate` | `both`) selects which steps run; updates the
  in-memory `runs` registry (live streaming) **and** writes a `04_Logs/runs/`
  ledger record at the end. `/api/format`, `/api/run`, run-now, and the engine
  all call it — one driver, one place. Carries the generate-side fix already
  shipped on `feat/generate-from-path`: when generate locates the formatted ODD,
  it passes that exact path to the analysis step (no second discovery).
- `_input_ready(task, csm, month, client_id) -> bool` — readiness depends on
  task: `format` and `both` gate on the **raw dump** being present (format
  produces the ODD that generate then consumes); `generate` gates on a
  **formatted ODD** being present. Reuses existing `find_formatted_odd` and the
  raw-dump scan. Readiness is evaluated on the *running* machine, so a job
  naturally migrates to whichever CSM can actually see its source data.
- `write_run_record(run_id, ...)` / `read_run_history(limit)` — append a per-run
  JSON file to `04_Logs/runs/` and read the ledger back (newest first). Recent
  Runs and the gallery switch to these instead of parsing `.log` files.

### Endpoints

- `GET /api/scheduler/status -> {active, last_tick_at}` — drives the heartbeat.
- `POST /api/schedules/{id}/toggle` — pause/resume via the existing `enabled` field.
- Existing schedule endpoints unchanged in shape.

### Schedule record — `schedules.json` (definition only, additive, back-compat)

```jsonc
{
  "id": "sched_xxxx",
  "csm": "Dan",
  "scope": "client",         // NEW: "client" | "csm" (default "client")
  "client_id": "1759",       // ignored when scope == "csm"
  "product": "ars",
  "day": 5,
  "task": "both",            // NEW: format | generate | both (default both)
  "extras": "none",
  "enabled": true,
  "created": "..."
}
```

Volatile run state is **not** stored here (no engine writes to the shared list).
Back-compat: existing entries lack `scope`/`task` → treated as `client` / `both`.

### Claim / status file — `schedule_claims/{id}.{YYYY.MM}.json` (single writer)

```jsonc
{
  "schedule_id": "sched_xxxx",
  "month": "2026.07",
  "claimed_by": "VPADMIS-DAN",      // machine that won the claim
  "claimed_at": "2026-07-05T08:12:03",
  "status": "running",              // running | complete | error | waiting for data
  "updated_at": "2026-07-05T08:14:51",
  "clients": {                      // per-client for scope=csm; one entry for scope=client
    "1759": {"status": "complete", "run_id": "1759_..._ab12", "deck": ".../1759_..._ars_deck.pptx"},
    "1801": {"status": "waiting for data"}
  }
}
```

## UI changes — `index.html`

- New-Schedule form: add a **Scope** toggle (This client / All of this CSM's
  clients — hides the Client field when "All") and a **Task** dropdown (Format
  only / Generate only / Format + Generate).
- Table: add **Scope**, **Task**, **Target** (month) columns; richer **Status**
  (Active/Paused + last result: `✓ 2026.07`, `⏳ waiting for data`, `✗ error`,
  `⏳ running`; for csm-scope a roll-up like `✓ 5/6 · ⏳ 1`); **Pause/Resume**
  beside Run Now / Delete; show **Next Run**. Status comes from the current
  month's claim file, merged onto each definition row.
- **Heartbeat line** at the top of the Schedules page, polling
  `/api/scheduler/status`:
  *"Scheduler active — last checked 2:32 PM. Keep the Velocity window open for
  schedules to run."* Makes the one real constraint visible and honest.
- **Recent Runs + Results gallery rework** (the second half of this work): both
  read the new `04_Logs/runs/` ledger instead of scraping `.log` files, so they
  reflect what actually ran (manual or scheduled), across machines, accurately.
  This is the fix for "history is worthless / not updating," and it's the same
  ledger the scheduler writes — one source of truth.

## Data flow

1. Operator sets a schedule → `POST /api/schedules` → `schedules.json` (definition
   only) on `M:`.
2. Every running `app.py`'s engine ticks → reads the definitions + this month's
   claim files.
3. Due + input-ready + claim-won → `_execute_pipeline` per client → writes
   deck/outputs, a `04_Logs/runs/` ledger record per client, and status into the
   **claim file** (sole writer). `schedules.json` is never touched by the engine.
4. The Schedules table (definitions ⨝ claim files), the heartbeat, and Recent
   Runs (ledger) — on every UI — reflect it.

## User experience (walkthrough)

1. **Setup** — Schedules → **+ New Schedule** → pick CSM, Client, Product, Task,
   Day → **Save**. ~15 seconds, no cron syntax, no paths, no Python.
2. **Shared dashboard** — the tab shows every schedule for every CSM, each with
   task, day, target month, last run + result, next run, and live status, under
   a scheduler heartbeat line.
3. **Due day, data ready** — the first CSM with the UI open fires the job; the
   row goes `running…` → `✓ <month>`; it also appears in Recent Runs with the
   usual streaming log. If others have the UI open, claim-once prevents duplicates.
4. **Due day, data not landed** — row shows `⏳ waiting for data`; the engine
   re-checks daily and runs it the moment the dump appears.
5. **Failure** — row shows `✗ error`; operator opens Recent Runs for the full
   log, fixes input, clicks **Run Now** to retry immediately.
6. **Manual control** — Run Now (fire now), Pause/Resume, Delete.
7. **The one constraint** — schedules fire only while someone, somewhere has the
   Velocity window open; the heartbeat makes that visible, and catch-up logic
   runs missed jobs the next time any UI opens within the month.

## Error handling

- Missing input → skip + `waiting for data` + daily retry within the month.
- Subprocess failure → `last_status = "error"`, full log still streamable via the
  existing run viewer.
- Claim contention → loser silently skips.
- Crashed mid-run → stale-claim timeout lets the next tick recover the month.

## Testing

`05_UI/tests/test_scheduler.py` (pure logic, no subprocesses; functions imported
from `app.py`):

- `due_schedules` across a range of dates (before/on/after day) and claim states
  (no claim / completed claim / `waiting for data` claim / stale claim).
- `current_report_month` computation.
- `try_claim` — local race (threads) → one winner; a completed claim blocks
  re-claim; a stale claim is re-claimable. (On SMB it's best-effort; the duplicate
  path is covered by idempotent output, not the test.)
- `clients_for_scope` — `client` returns the one id; `csm` enumerates the month's
  clients from a fixture folder tree.
- Missing-data path → claim status `waiting for data`, retryable next tick.
- Ledger round-trip — `write_run_record` then `read_run_history` returns it
  newest-first; Recent Runs/gallery read it without touching `.log` files.

## Known edge cases / refinements

- **Stale claim timeout** (~6h) handles a crashed runner without wedging the month.
- **Back-compat**: existing `schedules.json` entries lack `scope` / `task` →
  treated as `client` / `both`; with no claim files they read as never-run.
- **Duplicate runs** (rare, from best-effort SMB claim) are harmless: same client,
  same deck path, overwrite. No exactly-once promise on a network share.
- **csm-scope readiness**: a csm schedule runs whichever clients are ready that
  tick and leaves the rest `waiting for data`; the claim completes when all
  ready-able clients are done, and late clients get picked up on a later tick.
- **Current-month targeting** assumes data for the reporting month is available in
  that calendar month; if the convention later shifts to prior-month, add a
  `months_back` offset to the schedule record (non-breaking).
