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
| Firing model | **In-process background thread, claim-once** | No admin rights, no OS config, fully UI-operable. Atomic per-month claim means a job runs exactly once even when several CSMs have the UI open. |
| Target month | **Current calendar month** | Matches the existing Run Now behavior; `current_report_month(today) = today's YYYY.MM`. |
| Missing input | **Skip + retry daily, log "waiting for data"** | Tolerates late data dumps without manual babysitting. |
| Task per schedule | **format / generate / both** | Directly requested. `task` field, defaults to `both` for back-compat. |
| Code location | **All in `app.py`** (one file) | Per operator preference; engine is a clearly-marked section, still split into small testable functions. |
| Visibility | **Schedules tab is the single shared dashboard** | `schedules.json` is on the shared drive, so every CSM's UI reads the same list. No per-user filtering. |

### Explicitly out of scope (YAGNI)

- Weekly/daily frequency. Monthly day-of-month only.
- One-click Windows auto-start task (would let jobs fire with **no** UI open).
  Noted as a clean future add-on, not part of this work.

## Architecture

A background thread inside `app.py` wakes on an interval, finds due schedules,
and runs them through the **same** pipeline code the manual buttons use. Because
`schedules.json` lives on the shared `M:\ARS\` drive and every CSM runs their own
`app.py`, an **atomic claim** guarantees each job runs exactly once per month no
matter how many UIs are open.

There is no central server. The "central location" is the shared `schedules.json`
plus the Schedules tab that renders it — every UI shows the same rows.

### Firing logic (`>=`, not `==`)

Due detection uses `today.day >= schedule.day` AND `last_run_month != current
month`. Using `>=` means if no UI was open *on* the exact day, the first tick
afterward (still within the month) catches up. Paired with claim-once and
skip-on-missing-data, this is robust to machines being off.

## Components — all in `app.py`

### Engine section (new, small functions; imported by tests)

- `current_report_month(today) -> "YYYY.MM"` — current calendar month.
- `due_schedules(schedules, today) -> list` — enabled, `today.day >= day`, and
  `last_run_month != current_report_month(today)`. Pure function.
- `try_claim(claims_dir, schedule_id, month) -> bool` — atomic
  `O_CREAT|O_EXCL` marker file as the cross-process mutex. Winner runs; losers
  skip. A stale claim (older than ~6h with no recorded completion) may be
  re-claimed so a crashed run does not wedge the month.
- `SchedulerEngine` thread — every ~10 minutes: for each due schedule, call
  `_input_ready()`; if ready, `try_claim()`; if won, launch via
  `_execute_pipeline` and on success stamp `last_run` / `last_run_month`; if
  input not ready, set `last_status = "waiting for data"` and leave the job
  unclaimed so a later tick retries. Tracks `last_tick_at` for the heartbeat.
- Started once on FastAPI startup.

### Pipeline driver refactor

Today the format/analysis subprocess plumbing is duplicated across `/api/format`,
`/api/run`, **and** the run-now handler — three near-identical copies. Collapse to
one:

- `_execute_pipeline(run_id, csm, month, client_id, product, task, extras, source_path="")`
  — `task` (`format` | `generate` | `both`) selects which steps run; updates the
  in-memory `runs` registry so scheduled runs stream and appear in Recent Runs
  exactly like manual runs. `/api/format`, `/api/run`, run-now, and the engine
  all call it.
- `_input_ready(task, csm, month, client_id) -> bool` — readiness depends on
  task: `format` and `both` gate on the **raw dump** being present (format
  produces the ODD that generate then consumes); `generate` gates on a
  **formatted ODD** being present. Reuses existing `find_formatted_odd` and the
  raw-dump scan.

### Endpoints

- `GET /api/scheduler/status -> {active, last_tick_at}` — drives the heartbeat.
- `POST /api/schedules/{id}/toggle` — pause/resume via the existing `enabled` field.
- Existing schedule endpoints unchanged in shape.

### Schedule record (additive, back-compat)

```jsonc
{
  "id": "sched_xxxx",
  "csm": "Dan",
  "client_id": "1759",
  "product": "ars",
  "day": 5,
  "extras": "none",
  "task": "both",            // NEW: format | generate | both (default both)
  "enabled": true,
  "created": "...",
  "last_run": "2026-07-05 08:12",
  "last_run_month": "2026.07", // NEW: idempotency key for claim-once
  "last_status": "complete",   // NEW: complete | error | waiting for data | running
  "last_checked": "..."        // NEW: last tick that evaluated this schedule
}
```

## UI changes — `index.html`

- New-Schedule form: add a **Task** dropdown (Format only / Generate only /
  Format + Generate).
- Table: add **Task** and **Target** (month) columns; richer **Status**
  (Active/Paused + last result: `✓ 2026.06`, `⏳ waiting for data`, `✗ error`,
  `⏳ running`); add **Pause/Resume** button beside Run Now / Delete; show
  **Next Run**.
- **Heartbeat line** at the top of the Schedules page, polling
  `/api/scheduler/status`:
  *"Scheduler active — last checked 2:32 PM. Keep the Velocity window open for
  schedules to run."* Makes the one real constraint visible and honest.
- Scheduled runs already flow into the existing **Recent Runs** view via the
  shared `runs` registry — no extra work.

## Data flow

1. Operator sets a schedule → `POST /api/schedules` → `schedules.json` on `M:`.
2. Every running `app.py`'s engine ticks → reads the shared file.
3. Due + input-ready + claim-won → `_execute_pipeline` → writes deck/outputs +
   stamps `last_run_month` / `last_status` back into `schedules.json`.
4. The Schedules table and heartbeat (every UI) reflect it.

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

- `due_schedules` across a range of dates (before/on/after day; already-run month).
- `current_report_month` computation.
- `try_claim` race — two concurrent claims for the same (schedule, month) → exactly
  one wins.
- Missing-data path → schedule left unclaimed and retryable; status set to
  `waiting for data`.

## Known edge cases / refinements

- **Stale claim timeout** (~6h) handles a crashed runner without wedging the month.
- **Back-compat**: existing `schedules.json` entries lack `task` / `last_run_month`
  → treated as `both` / never-run.
- **Current-month targeting** assumes data for the reporting month is available in
  that calendar month; if the convention later shifts to prior-month, add a
  `months_back` offset to the schedule record (non-breaking).
