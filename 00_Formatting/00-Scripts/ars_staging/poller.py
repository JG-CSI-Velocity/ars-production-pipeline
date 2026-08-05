"""Scan the ready tree on the share and stage new data to local SSD.

Scope (v1, parity-safe): staging COPIES raw files byte-identically --
formatted ODD workbooks and TXN transaction files -- so the click-time
pipeline reads local disk instead of the ~1.7 MB/s share. Format conversion
(CSV -> parquet, ODD -> snapshot) happens downstream in
``ars_engine.data.txn_store`` using the parity-proven parse ports, never
here, so a staging copy can never change a number.

Ready-tree layout scanned (produced by 00_Formatting/run.py):
    <ready>/<CSM>/<month>/<client_id>/*.xlsx          formatted ODDs
    <ready>/TXN Files/<CSM>/<client_id>/[YYYY/]<file> transaction files
"""

from __future__ import annotations

import importlib.util
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ars_engine.core.config import EngineConfig, repo_root

from ars_staging.manifest import (
    load_manifest,
    needs_staging,
    save_manifest,
    staging_root,
)


def _load_txn_detection():
    """Load the canonical TXN filename matcher from its legacy home by file
    path (same pattern the legacy loaders use) -- one source of truth."""
    path = (
        repo_root()
        / "01_Analysis"
        / "00-Scripts"
        / "analytics"
        / "txn_file_detection.py"
    )
    spec = importlib.util.spec_from_file_location("txn_file_detection", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_dedupe():
    """duplicate_file_groups from legacy txn_cache.py, by file path."""
    path = repo_root() / "01_Analysis" / "00-Scripts" / "analytics" / "txn_cache.py"
    spec = importlib.util.spec_from_file_location("txn_cache_for_staging", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.duplicate_file_groups


@dataclass
class StageItem:
    kind: str  # "odd" | "txn"
    csm: str
    client_id: str
    src: Path
    month: str = ""  # ODD only


@dataclass
class PollResult:
    scanned: int = 0
    staged: int = 0
    staged_bytes: int = 0
    aliased: int = 0
    unchanged: int = 0
    errors: list[str] = field(default_factory=list)
    clients: set[str] = field(default_factory=set)


def scan_ready_tree(
    ready_dir: Path,
    csm_filter: str | None = None,
    client_filter: str | None = None,
) -> list[StageItem]:
    """Enumerate stageable files in the ready tree."""
    items: list[StageItem] = []
    if not ready_dir.exists():
        return items
    detection = _load_txn_detection()

    txn_base = ready_dir / "TXN Files"
    for csm_dir in sorted(p for p in ready_dir.iterdir() if p.is_dir()):
        if csm_dir == txn_base:
            continue
        csm = csm_dir.name
        if csm_filter and not csm.lower().startswith(csm_filter.lower()):
            continue
        for month_dir in sorted(p for p in csm_dir.iterdir() if p.is_dir()):
            for client_dir in sorted(p for p in month_dir.iterdir() if p.is_dir()):
                if client_filter and client_dir.name != client_filter:
                    continue
                for f in sorted(client_dir.glob("*.xlsx")):
                    if f.name.startswith("~$"):
                        continue
                    items.append(
                        StageItem("odd", csm, client_dir.name, f, month=month_dir.name)
                    )

    if txn_base.exists():
        for csm_dir in sorted(p for p in txn_base.iterdir() if p.is_dir()):
            csm = csm_dir.name
            if csm_filter and not csm.lower().startswith(csm_filter.lower()):
                continue
            for client_dir in sorted(p for p in csm_dir.iterdir() if p.is_dir()):
                if client_filter and client_dir.name != client_filter:
                    continue
                candidates: list[Path] = []
                for item in sorted(client_dir.iterdir()):
                    if detection.is_txn_dest_file(item):
                        candidates.append(item)
                    elif item.is_dir() and item.name.isdigit() and len(item.name) == 4:
                        candidates.extend(
                            f for f in sorted(item.iterdir())
                            if detection.is_txn_dest_file(f)
                        )
                items.extend(
                    StageItem("txn", csm, client_dir.name, f) for f in candidates
                )
    return items


def _staged_dest(item: StageItem) -> Path:
    root = staging_root(item.client_id)
    if item.kind == "odd":
        return root / "odd" / item.month / item.src.name
    return root / "txn" / item.src.name


def poll(
    config: EngineConfig | None = None,
    csm_filter: str | None = None,
    client_filter: str | None = None,
    on_client_staged: Callable[[str], None] | None = None,
    progress: Callable[[str], None] = print,
) -> PollResult:
    """One staging pass: scan, dedupe, copy what's new, update manifests.

    ``on_client_staged(client_id)`` fires after a client received new TXN
    data -- the CLI wires this to the DuckDB store refresh so pre-aggregation
    happens in the background, not at click time.
    """
    config = config or EngineConfig.load()
    ready = config.paths.ready_dir
    result = PollResult()
    items = scan_ready_tree(ready, csm_filter, client_filter)
    result.scanned = len(items)
    if not items:
        progress(f"staging: nothing found under {ready}")
        return result

    duplicate_file_groups = _load_dedupe()

    by_client: dict[str, list[StageItem]] = {}
    for it in items:
        by_client.setdefault(it.client_id, []).append(it)

    for client_id, client_items in sorted(by_client.items()):
        manifest = load_manifest(client_id)
        files = manifest["files"]
        touched = False
        new_txn = False

        # Byte-identical re-deliveries among this client's TXN files: keep the
        # first (by name), record the rest as aliases -- never staged twice.
        txn_srcs = [it.src for it in client_items if it.kind == "txn"]
        alias_of: dict[str, str] = {}
        for group in duplicate_file_groups(txn_srcs):
            keeper = group[0]
            for dupe in group[1:]:
                alias_of[dupe.name] = keeper.name

        for it in client_items:
            rec = files.get(it.src.name)
            if it.src.name in alias_of:
                keeper = alias_of[it.src.name]
                if not (rec and rec.get("status") == f"alias_of:{keeper}"):
                    try:
                        stat = it.src.stat()
                    except OSError as exc:
                        result.errors.append(f"{it.src.name}: {exc}")
                        continue
                    files[it.src.name] = {
                        "src": str(it.src),
                        "size": stat.st_size,
                        "mtime": int(stat.st_mtime),
                        "staged": None,
                        "staged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "status": f"alias_of:{keeper}",
                    }
                    touched = True
                    result.aliased += 1
                    progress(f"staging: {client_id} ALIAS {it.src.name} == {keeper}")
                else:
                    result.unchanged += 1
                continue

            if not needs_staging(it.src, rec):
                result.unchanged += 1
                continue

            dest = _staged_dest(it)
            try:
                stat = it.src.stat()
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(dest.suffix + ".part")
                shutil.copy2(it.src, tmp)
                tmp.replace(dest)
            except OSError as exc:
                result.errors.append(f"{it.src.name}: {exc}")
                progress(f"staging: {client_id} ERROR {it.src.name}: {exc}")
                continue
            files[it.src.name] = {
                "src": str(it.src),
                "size": stat.st_size,
                "mtime": int(stat.st_mtime),
                "staged": str(dest),
                "staged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "status": "staged",
            }
            touched = True
            result.staged += 1
            result.staged_bytes += stat.st_size
            result.clients.add(client_id)
            if it.kind == "txn":
                new_txn = True
            progress(
                f"staging: {client_id} <- {it.src.name} "
                f"({stat.st_size / 1_048_576:.1f} MiB)"
            )

        if touched:
            save_manifest(client_id, manifest)
        if new_txn and on_client_staged is not None:
            on_client_staged(client_id)

    progress(
        f"staging: scanned={result.scanned} staged={result.staged} "
        f"({result.staged_bytes / 1_048_576:.0f} MiB) aliased={result.aliased} "
        f"unchanged={result.unchanged} errors={len(result.errors)}"
    )
    return result


def staged_txn_files(client_id: str) -> list[Path]:
    """The client's staged (deduped) TXN files, for the DuckDB store to ingest."""
    manifest = load_manifest(client_id)
    out: list[Path] = []
    for rec in manifest["files"].values():
        if rec.get("status") == "staged" and rec.get("staged"):
            p = Path(rec["staged"])
            if "/txn/" in p.as_posix() and p.exists():
                out.append(p)
    return sorted(out)


def staged_odd_file(client_id: str, month: str) -> Path | None:
    """The client's staged ODD workbook for a month, if present."""
    root = staging_root(client_id) / "odd" / month
    if not root.exists():
        return None
    matches = sorted(root.glob("*.xlsx"))
    return matches[0] if matches else None
