"""Per-section parity sign-off ledger (03_Config/parity_status.json).

A section's engine_flags entry may only move to "new" once it is approved
here against >=2 distinct real clients. The status file is committed (it
contains only metadata -- client ids, timestamps, pass counts -- never data).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ars_engine.core.config import config_dir

MIN_CLIENTS_FOR_APPROVAL = 2


def _status_path(path: Path | None = None) -> Path:
    return path or config_dir() / "parity_status.json"


def load_status(path: Path | None = None) -> dict:
    p = _status_path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(status: dict, path: Path | None = None) -> None:
    p = _status_path(path)
    p.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_check(
    section_id: str,
    client_id: str,
    month: str,
    passed: bool,
    diff_count: int,
    path: Path | None = None,
) -> dict:
    """Record one parity check result for a section."""
    status = load_status(path)
    entry = status.setdefault(section_id, {"checks": {}, "approved_by": None, "approved_at": None})
    entry["checks"][client_id] = {
        "month": month,
        "passed": passed,
        "diffs": diff_count,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if not passed:
        # Any failing check voids a previous approval -- parity must be re-earned.
        entry["approved_by"] = None
        entry["approved_at"] = None
    _save(status, path)
    return entry


def passing_clients(section_id: str, path: Path | None = None) -> list[str]:
    entry = load_status(path).get(section_id, {})
    return sorted(c for c, r in entry.get("checks", {}).items() if r.get("passed"))


def approve(section_id: str, by: str, path: Path | None = None) -> dict:
    """Approve a section for cutover. Requires >=2 passing clients."""
    status = load_status(path)
    entry = status.get(section_id)
    clients = passing_clients(section_id, path)
    if entry is None or len(clients) < MIN_CLIENTS_FOR_APPROVAL:
        raise ValueError(
            f"Cannot approve {section_id}: needs passing checks on "
            f">={MIN_CLIENTS_FOR_APPROVAL} clients, has {clients or 'none'}"
        )
    entry["approved_by"] = by
    entry["approved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save(status, path)
    return entry


def is_approved(section_id: str, path: Path | None = None) -> bool:
    entry = load_status(path).get(section_id, {})
    return bool(entry.get("approved_by"))
