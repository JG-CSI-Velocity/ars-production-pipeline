"""Per-client staging manifest.

One JSON per client at ``<local-cache>/staging/<client_id>/manifest.json``.
Each record maps a SOURCE file (on the share) to its STAGED copy (local SSD):

    {
      "files": {
        "<source name>": {
          "src": str, "size": int, "mtime": int,
          "staged": str | null,     # local path, null for aliases
          "staged_at": iso8601,
          "status": "staged" | "alias_of:<keeper name>"
        }
      },
      "last_poll": iso8601
    }

Change detection is size+mtime (cheap over SMB); byte-identical re-deliveries
are detected separately via head/tail SHA-256 grouping and recorded as
aliases so a relabeled month is never staged -- or counted -- twice.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ars_engine.core.config import local_cache_root


def staging_root(client_id: str) -> Path:
    return local_cache_root() / "staging" / str(client_id)


def manifest_path(client_id: str) -> Path:
    return staging_root(client_id) / "manifest.json"


def load_manifest(client_id: str) -> dict[str, Any]:
    p = manifest_path(client_id)
    if not p.exists():
        return {"files": {}, "last_poll": None}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"files": {}, "last_poll": None}


def save_manifest(client_id: str, manifest: dict[str, Any]) -> None:
    """Atomic write (tmp + replace) so a killed poll never corrupts state."""
    p = manifest_path(client_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest["last_poll"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=1)
        os.replace(tmp, p)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def needs_staging(src: Path, record: dict[str, Any] | None) -> bool:
    """True when the source is new or changed relative to its manifest record."""
    if record is None:
        return True
    if record.get("status", "").startswith("alias_of:"):
        return False
    try:
        stat = src.stat()
    except OSError:
        return False  # source vanished; nothing to do
    if int(stat.st_mtime) != record.get("mtime") or stat.st_size != record.get("size"):
        return True
    staged = record.get("staged")
    return not (staged and Path(staged).exists())
