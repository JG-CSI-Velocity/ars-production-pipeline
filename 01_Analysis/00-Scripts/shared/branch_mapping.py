"""Shared branch ID → name mapping.

The canonical source is `03_Config/clients_config.json` under each client
entry as the `BranchMapping` field (a dict of `"branch_id": "Branch Name"`).
This module is the single place every analytics section -- ARS or TXN --
should call when it needs to turn raw branch IDs from the ODD data into
operator-friendly names for charts and tables.

Existing call sites (kept for reference):
- analytics/branch_txn/01_branch_data.py (legacy in-place mapping, works)
- analytics/dctr/branches.py, dctr/_helpers.py
- analytics/rege/branches.py
- analytics/attrition/dimensions.py

Newer call sites added when this helper was introduced:
- analytics/payroll/01_payroll_data.py
- analytics/relationship/01_relationship_data.py
- analytics/ICS_cohort/ics-01-normalize

Resolution rules:
1. Keys come in as strings. The ODD column can emit numbers as int, float,
   or string ("1" / "1.0" / 1 / 1.0); we normalize to a stripped string and
   also try the integer-cast form ("1.0" -> "1") for the lookup.
2. Unmapped IDs pass through unchanged so a missing entry in the config
   shows up as a raw number rather than crashing.
3. If the client has no `BranchMapping` entry at all, this returns an empty
   dict and `apply_branch_names` is a no-op (charts will show numeric IDs;
   the pipeline already prints a loud warning when this happens).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def _candidate_config_paths() -> list[Path]:
    """Search order for clients_config.json."""
    candidates: list[Path] = []
    env = os.environ.get("CLIENTS_CONFIG_PATH")
    if env:
        candidates.append(Path(env))
    if sys.platform == "win32":
        candidates.append(Path(r"M:\ARS\03_Config\clients_config.json"))
    else:
        candidates.append(Path("/Volumes/M/ARS/03_Config/clients_config.json"))
    # Repo-root fallback (dev / fresh clone). 00-Scripts/shared/branch_mapping.py
    # -> ../../../03_Config/clients_config.json
    here = Path(__file__).resolve()
    for n in (3, 4):
        try:
            candidates.append(here.parents[n] / "03_Config" / "clients_config.json")
        except IndexError:
            pass
    return candidates


def _resolve_config_path() -> Path | None:
    for cand in _candidate_config_paths():
        if cand.exists():
            return cand
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_branch_map(
    client_id: str | int | None,
    clients_config: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return `{branch_id: branch_name}` for the given client.

    Empty dict when the client_id is unknown or has no BranchMapping field.

    Parameters
    ----------
    client_id : str | int | None
        The client ID. Coerced to string for the lookup. None -> empty dict.
    clients_config : dict, optional
        Pre-loaded clients_config.json content. When omitted, the file is
        read fresh from disk. Pass this when you already have it in scope
        (e.g. txn_setup loads it once and stashes it as `_clients_config`).
    """
    if not client_id:
        return {}
    cid = str(client_id).strip()
    if not cid:
        return {}

    if clients_config is None:
        path = _resolve_config_path()
        if path is None:
            return {}
        try:
            clients_config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    if not isinstance(clients_config, dict):
        return {}
    entry = clients_config.get(cid, {})
    if not isinstance(entry, dict):
        return {}

    raw_map = entry.get("BranchMapping") or entry.get("branch_mapping") or {}
    if not isinstance(raw_map, dict):
        return {}
    # Normalize keys + values to strings.
    return {str(k).strip(): str(v).strip() for k, v in raw_map.items() if v}


def map_branch_id(branch_id: Any, mapping: dict[str, str]) -> str:
    """Translate a single branch ID. Falls back to the original string."""
    if branch_id is None:
        return ""
    s = str(branch_id).strip()
    if not s:
        return ""
    if s in mapping:
        return mapping[s]
    # ODD often emits floats ("1.0"); strip the trailing decimal and retry.
    if "." in s:
        clean = s.split(".")[0]
        if clean in mapping:
            return mapping[clean]
    return s  # unmapped: pass through


def apply_branch_names(
    df: pd.DataFrame,
    column: str = "branch",
    mapping: dict[str, str] | None = None,
    client_id: str | int | None = None,
    clients_config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """In-place: replace branch IDs in `df[column]` with mapped names.

    Returns the same DataFrame (mutated) so call sites can chain or assign.
    No-op when the column is missing, the mapping is empty, or the column
    is entirely null. Unmapped IDs pass through unchanged.

    Pass either `mapping` directly OR (`client_id`, optional `clients_config`)
    to have the map loaded from clients_config.json on the spot.
    """
    if column not in df.columns:
        return df

    if mapping is None:
        mapping = load_branch_map(client_id, clients_config=clients_config)
    if not mapping:
        return df

    # Skip if the column is all-null (nothing to map; avoids a costly apply).
    if df[column].notna().sum() == 0:
        return df

    df[column] = df[column].map(lambda v: map_branch_id(v, mapping) if pd.notna(v) else v)
    return df


__all__ = ["load_branch_map", "map_branch_id", "apply_branch_names"]
