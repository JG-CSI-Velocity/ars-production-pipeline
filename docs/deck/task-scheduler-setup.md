# Windows Task Scheduler — one-time setup on the work PC

Phases 17.3 (scheduled runs) and 19 (overnight formatting sweep) both rely on Windows Task Scheduler hitting `localhost:8000`. The FastAPI server can't reliably schedule itself — `Start Here.bat` closes when the terminal closes, taking any in-process scheduler with it.

This doc is the one-time configuration the operator does in the Task Scheduler UI. Each task is a few clicks.

---

## Prerequisite

`Start Here.bat` must be running at the scheduled hour. Two options:

- **Manual:** the CSM leaves the Velocity Pipeline terminal open during the scheduled window. Fine for daily 06:00 runs.
- **Auto-launch:** add a second Task Scheduler entry that launches `Start Here.bat` at boot. See "Auto-launch on boot" below.

Long-term, `app.py` should run as a Windows Service (via `nssm` or `pywin32`) so it survives reboots and runs headless. That's a follow-up phase.

---

## Task 1 — Scheduled runs (Phase 17.3)

**Goal:** every morning at 06:00, fire any schedules whose `day_of_month` matches today.

1. Open **Task Scheduler** (Win + R → `taskschd.msc`).
2. Right pane → **Create Basic Task**.
3. **Name:** `Velocity Pipeline — Run Due Schedules`
4. **Trigger:** Daily, 06:00.
5. **Action:** Start a program.
   - Program/script: `powershell`
   - Arguments: `-Command "Invoke-RestMethod -Method POST -Uri http://localhost:8000/api/schedules/run-due"`
6. **Finish.**

**Verify:** in the task list, right-click the task → **Run**. Then open the UI → History tab. A new entry should appear (or the run-due endpoint should report "no schedules due today" — both are pass conditions).

---

## Task 2 — Overnight formatting sweep (Phase 19)

**Goal:** on the 7th, 9th, and 11th of every month at 02:00, scan opt-in CSM folders for unformatted ZIPs and format them.

Create three triggers on a single task (or three separate tasks — Task Scheduler allows either).

1. **Create Basic Task** → name: `Velocity Pipeline — Overnight Format Sweep`
2. **Trigger:** Monthly, days 7, 9, 11, 02:00.
3. **Action:** Start a program.
   - Program/script: `powershell`
   - Arguments: `-Command "Invoke-RestMethod -Method POST -Uri http://localhost:8000/api/format-sweep"`
4. **Finish.**

**Verify:** right-click the task → **Run**. Then UI → Sweep tab. A new entry should appear with file counts.

---

## Auto-launch on boot (optional but recommended)

If the operator wants `Start Here.bat` to launch automatically at login:

1. **Create Basic Task** → name: `Velocity Pipeline — Launch at Login`
2. **Trigger:** At log on (current user).
3. **Action:** Start a program.
   - Program/script: `cmd`
   - Arguments: `/c "M:\ARS\Start Here.bat"`
   - Start in: `M:\ARS\`
4. **Finish.**

The terminal window will pop up shortly after login. Closing it still stops the server — but at least restart-then-forget works.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Task Scheduler shows "Last Run Result: 0x1" | `powershell` couldn't reach `localhost:8000` | Confirm `Start Here.bat` is running. Open `http://localhost:8000` in the browser — if it doesn't load, relaunch the bat. |
| Task fires but UI shows no new run | Endpoint returned 200 with "no due schedules" | Open UI → Schedules tab → confirm at least one schedule has today's `day_of_month`. |
| Task Scheduler says "the operator is not logged on" | Default Task Scheduler config | Right-click task → Properties → General → "Run whether user is logged on or not" + provide password. |
| 404 from `/api/schedules/run-due` or `/api/format-sweep` | Endpoints not yet shipped | Phase 17.3 / Stream 4 still in progress. Wait for the merge. |

---

## Why not a Python `schedule` library or APScheduler?

Both libraries run inside the FastAPI process. When the operator closes the terminal, `app.py` dies and the scheduler stops. Task Scheduler is OS-level and fires independent of whether `app.py` is running — and when `app.py` isn't running, the HTTP call simply fails (and Task Scheduler logs it), which is the desired observable behavior.

Once `app.py` runs as a Windows Service this trade-off shifts. Until then, OS-level scheduling is the right call.
