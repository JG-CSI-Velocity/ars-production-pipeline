"""Headless scheduled-run entrypoint.

Invoked by Windows Task Scheduler (see the "Automatic runs" card on the
Schedules tab, or `POST /api/schedules/autorun`) so due schedules fire even when
the UI server is closed. It reuses the *exact* run logic the UI uses --
`_run_due_schedules` in ``app.py`` -- so there is one code path, not two.

Behaviour:
- Runs every enabled schedule whose day-window includes today.
- Fans `csm` / `all` scope schedules out to every ready client.
- Skips clients already completed this month (idempotent across the 5th-8th
  window) and clients with a run already in progress.
- Runs sequentially, waiting for each analysis to finish, so a "run all" pass
  doesn't spawn dozens of concurrent subprocesses.

Usage:
    python schedule_runner.py            # run due schedules now
    python schedule_runner.py --dry-run  # print what WOULD run, launch nothing
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Import the app module so we share its run logic, path constants, and helpers.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import app  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Fire due Velocity schedules.")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would run without launching anything.")
    args = parser.parse_args()

    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M")
    mode = "DRY-RUN" if args.dry_run else "RUN"
    print(f"[{stamp}] schedule_runner {mode} -- ARS base: {app.ARS_BASE}")

    results = app._run_due_schedules(now, dry_run=args.dry_run, wait=not args.dry_run)

    if not results:
        print("  No schedules due today.")
        return 0

    by_status: dict[str, int] = {}
    for r in results:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        line = f"  {r['status']:<16} {r.get('csm', '?')} / {r.get('client_id', '?')}"
        if r.get("detail"):
            line += f"  ({r['detail']})"
        print(line)

    summary = ", ".join(f"{k}={v}" for k, v in sorted(by_status.items()))
    print(f"  Summary: {summary}")
    # Non-zero exit if any client errored, so Task Scheduler surfaces failures.
    return 1 if by_status.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
