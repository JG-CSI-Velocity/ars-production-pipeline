"""Step: auto-stage TXN files when the destination folder is empty.

TXN files are staged into ``…/02-Data-Ready for Analysis/TXN Files/{CSM}/{client}/``
by the *formatting* run (``00_Formatting/run.py --with-trans``). When an analysis
run skips formatting (the ODD was already formatted), that staging never happens
and ``txn_setup`` finds nothing -- the run then stalls on an empty namespace.

This step closes that gap: before txn_setup reads, if the destination is empty it
stages the client's TXN files itself, reusing formatting's copy/unzip logic
(``00_Formatting/00-Scripts/txn_staging.py``) and the CSM source mapping in
``03_Config/ars_config.json``. If it still can't find them, it fails fast with an
actionable message instead of the silent stall.

Collision-safe reuse: the formatting and analysis trees each have their own
``shared``/``pipeline`` packages, so the standalone helper modules are loaded by
file path (never added to ``sys.path`` as packages).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from loguru import logger

from ars_analysis.pipeline.context import PipelineContext

# Same ARS base resolution txn_setup/02-file-config.py uses, so we stage into the
# exact folder discovery will read from.
_ARS_BASE_CANDIDATES = [
    Path(r"M:\ARS"),
    Path("/Volumes/M/ARS"),
    Path(__file__).resolve().parents[4],
]


def _ars_base() -> Path:
    return next((p for p in _ARS_BASE_CANDIDATES if p.exists()), _ARS_BASE_CANDIDATES[-1])


def _is_txn_file(p: Path) -> bool:
    """A TXN file is .txt/.csv, or extensionless ending in `_transaction`.

    Matches txn_setup/02-file-config.py::_is_txn_file exactly.
    """
    if not p.is_file():
        return False
    if p.suffix.lower() in (".txt", ".csv"):
        return True
    return p.name.lower().endswith("_transaction")


def _has_txn_file(client_dir: Path) -> bool:
    """True if the client dir holds a TXN file (top level or a 4-digit year folder)."""
    if not client_dir.exists():
        return False
    for item in client_dir.iterdir():
        if _is_txn_file(item):
            return True
        if item.is_dir() and item.name.isdigit() and len(item.name) == 4:
            for f in item.iterdir():
                if _is_txn_file(f):
                    return True
    return False


def _load_by_path(module_name: str, path: Path):
    """Import a standalone module by file path, registering it under module_name.

    Registration lets a dependent module's ``from <module_name> import ...``
    resolve (txn_staging imports month_resolver) without touching sys.path.
    """
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _match_csm_source(csm: str, sources: dict) -> Path | None:
    """Resolve a CSM's source dump root from csm_sources, fuzzy like formatting."""
    if not csm:
        return None
    if csm in sources:
        return Path(sources[csm])
    low = csm.lower()
    for name, path in sources.items():
        nl = name.lower()
        if nl == low or nl.startswith(low) or low.startswith(nl):
            return Path(path)
    return None


def ensure_txn_staged(ctx: PipelineContext) -> None:
    """Stage the client's TXN files if the destination folder is empty.

    No-op (fast path) when files are already staged -- normal runs pay only a
    directory scan. Raises FileNotFoundError with remediation if it can't stage.
    """
    csm = (getattr(ctx.client, "assigned_csm", "") or "").strip()
    client_id = ctx.client.client_id
    month = (ctx.client.month or "").strip()

    ars_base = _ars_base()
    txn_base = ars_base / "00_Formatting" / "02-Data-Ready for Analysis" / "TXN Files"
    client_dir = (txn_base / csm / client_id) if csm else None

    # -- Fast path: already staged --
    if client_dir is not None and _has_txn_file(client_dir):
        return
    if not csm:
        # Mirror txn_setup's CSM-less fallback: any CSM subfolder holding the client.
        if txn_base.exists():
            for d in txn_base.iterdir():
                if d.is_dir() and _has_txn_file(d / client_id):
                    return
        raise FileNotFoundError(
            f"No TXN files staged for client {client_id} under {txn_base} and no CSM "
            f"given, so the source dump can't be resolved to auto-stage. Re-run "
            f"formatting with --with-trans, or drop the TXN file into "
            f"{txn_base}/<CSM>/{client_id}."
        )

    # -- Need to stage: load formatting's standalone helpers by file path --
    config_dir = ars_base / "03_Config"
    fmt_scripts = ars_base / "00_Formatting" / "00-Scripts"
    if not (config_dir / "ars_config.json").exists() or not (fmt_scripts / "txn_staging.py").exists():
        raise FileNotFoundError(
            f"No TXN files staged for client {client_id} at {client_dir}, and the "
            f"formatting config/staging modules were not found under {ars_base}. "
            f"Re-run formatting with --with-trans, or drop the TXN file into {client_dir}."
        )

    _load_by_path("month_resolver", fmt_scripts / "month_resolver.py")
    txn_staging = _load_by_path("txn_staging", fmt_scripts / "txn_staging.py")
    settings_mod = _load_by_path("ars_fmt_settings", config_dir / "settings.py")

    settings = settings_mod.load_settings(config_dir / "ars_config.json")
    sources = dict(settings.csm_sources.sources)
    source_root = _match_csm_source(csm, sources)
    if source_root is None:
        raise FileNotFoundError(
            f"No TXN files staged for client {client_id} at {client_dir}, and no CSM "
            f"source mapping for '{csm}' in ars_config.json csm_sources "
            f"(have: {list(sources)[:8]}). Re-run formatting with --with-trans, or "
            f"drop the TXN file into {client_dir}."
        )

    clients_config = {}
    ccp = config_dir / "clients_config.json"
    if ccp.exists():
        try:
            clients_config = json.loads(ccp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            clients_config = {}

    logger.info(
        "TXN Files empty for {csm}/{cid} -- auto-staging from {src}",
        csm=csm, cid=client_id, src=source_root,
    )
    # Stage into the SAME {csm} folder txn_setup will read (ctx CSM, not the
    # config key), so discovery finds the files regardless of a fuzzy match.
    staged, errors = txn_staging.stage_txn_files(
        csm, client_id, month, str(source_root), str(txn_base),
        clients_config=clients_config, log=lambda m: logger.info(m.strip()),
    )
    logger.info("TXN auto-stage: {n} file(s) copied, {e} error(s)", n=staged, e=errors)

    if not _has_txn_file(client_dir):
        raise FileNotFoundError(
            f"Auto-staging found no transaction files for client {client_id}. "
            f"Searched source: {source_root} (month {month}). "
            f"Expected destination: {client_dir}. Re-run formatting with "
            f"--with-trans, or drop the TXN file into {client_dir}."
        )
