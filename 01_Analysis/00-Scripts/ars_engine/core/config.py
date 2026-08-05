"""The ONE engine configuration.

Unifies the two legacy configs:
- ``00-Scripts/config.py::ARSSettings`` (pydantic-settings over
  03_Config/ars_config.json + ARS_* env vars) -- kept as the base shape.
- ``shared/config.py::PlatformConfig`` (YAML layering) -- retired; nothing
  in the live path loaded YAML configs.

Adds the v3 pieces: repo-root/local-cache resolution, client-config lookup
(ported from the legacy runner's ``_load_client_config`` /
``_resolve_config_fallback``), and the per-section engine cutover flags.
"""

from __future__ import annotations

import json
import logging
import os
import platform as _platform
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def repo_root() -> Path:
    """Repo root: core/ -> ars_engine -> 00-Scripts -> 01_Analysis -> root."""
    return Path(__file__).resolve().parents[4]


def config_dir() -> Path:
    return repo_root() / "03_Config"


def local_cache_root() -> Path:
    """Machine-local fast storage for staged data, caches, and goldens.

    Ported from legacy ``analytics/txn_cache.py::local_cache_root``:
    %LOCALAPPDATA%\\ARS-cache on Windows, ~/.ars-cache elsewhere;
    ARS_LOCAL_CACHE_DIR overrides.
    """
    override = os.environ.get("ARS_LOCAL_CACHE_DIR")
    if override:
        root = Path(override)
    elif _platform.system() == "Windows" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "ARS-cache"
    else:
        root = Path.home() / ".ars-cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


class PathsConfig(BaseModel):
    """Filesystem layout for one deployment (the M:\\ARS production layout)."""

    ars_base: Path = Field(default_factory=repo_root)
    ready_dir: Path | None = None       # 00_Formatting/02-Data-Ready for Analysis
    analysis_dir: Path | None = None    # 01_Analysis/01_Completed_Analysis
    presentations_dir: Path | None = None  # 02_Presentations
    logs_dir: Path | None = None        # 04_Logs
    template_path: Path | None = None   # PPTX template override

    def resolved(self) -> "PathsConfig":
        base = self.ars_base
        return PathsConfig(
            ars_base=base,
            ready_dir=self.ready_dir or base / "00_Formatting" / "02-Data-Ready for Analysis",
            analysis_dir=self.analysis_dir or base / "01_Analysis" / "01_Completed_Analysis",
            presentations_dir=self.presentations_dir or base / "02_Presentations",
            logs_dir=self.logs_dir or base / "04_Logs",
            template_path=self.template_path,
        )


class RunConfig(BaseModel):
    """Run behavior settings."""

    chart_dpi: int = Field(default=150, ge=72, le=600)
    section_workers: int = Field(default=4, ge=1, le=16)
    duckdb_memory_limit: str = "4GB"
    slide_budget_main: int = 25


class EngineConfig(BaseModel):
    """Root engine configuration."""

    paths: PathsConfig = Field(default_factory=PathsConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    csm_sources: dict[str, Path] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> "EngineConfig":
        """Load from 03_Config/ars_config.json (subset of keys), with defaults.

        The legacy ars_config.json remains the operator-owned file; this reads
        the keys the v3 engine needs (paths.ars_base, csm_sources.sources) and
        ignores the rest, so one config file serves both engines during
        migration.
        """
        path = path or config_dir() / "ars_config.json"
        raw: dict = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not read %s (%s); using defaults", path, exc)
        paths_raw = raw.get("paths", {})
        sources = (raw.get("csm_sources") or {}).get("sources", {})
        cfg = cls(
            paths=PathsConfig(
                ars_base=Path(paths_raw["ars_base"]) if paths_raw.get("ars_base") else repo_root(),
                template_path=(
                    Path(paths_raw["template_path"]) if paths_raw.get("template_path") else None
                ),
            ),
            csm_sources={k: Path(v) for k, v in sources.items()},
        )
        cfg.paths = cfg.paths.resolved()
        return cfg


# ---------------------------------------------------------------------------
# Client config lookup (ported from legacy runner._load_client_config)
# ---------------------------------------------------------------------------


def _clients_config_candidates() -> list[Path]:
    candidates = (
        [
            Path(r"M:\ARS\03_Config\clients_config.json"),
            Path(r"M:\ARS\Config\clients_config.json"),
        ]
        if _platform.system() == "Windows"
        else [
            Path("/Volumes/M/ARS/03_Config/clients_config.json"),
            Path("/Volumes/M/ARS/Config/clients_config.json"),
        ]
    )
    candidates.append(config_dir() / "clients_config.json")
    return candidates


def load_client_config(client_id: str, config_path: Path | None = None) -> dict:
    """Return the clients_config.json entry for one client (empty dict if absent)."""
    path = config_path
    if path is None:
        path = next((p for p in _clients_config_candidates() if p.exists()), None)
    if path is None or not path.exists():
        logger.warning("clients_config.json not found -- empty client config")
        return {}
    all_clients = json.loads(path.read_text(encoding="utf-8"))
    if client_id in all_clients:
        return all_clients[client_id]
    if len(all_clients) == 1:
        return next(iter(all_clients.values()))
    logger.warning(
        "Client %s not found in %s (%d clients available)", client_id, path, len(all_clients)
    )
    return {}


# ---------------------------------------------------------------------------
# Engine cutover flags -- per-section old/new routing during the migration
# ---------------------------------------------------------------------------

EngineChoice = Literal["old", "new"]


def load_engine_flags(path: Path | None = None) -> dict[str, EngineChoice]:
    """Read 03_Config/engine_flags.json: {section_id: "old"|"new"}.

    Missing file or missing section id means "old" -- the legacy engine remains
    the default until a section passes parity sign-off (see ars_parity).
    """
    path = path or config_dir() / "engine_flags.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read %s (%s); all sections -> old engine", path, exc)
        return {}
    return {k: ("new" if v == "new" else "old") for k, v in raw.items()}


def engine_for_section(section_id: str, flags: dict[str, EngineChoice] | None = None) -> EngineChoice:
    flags = load_engine_flags() if flags is None else flags
    return flags.get(section_id, "old")
