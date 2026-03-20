"""Load pipeline settings from ars_config.json.

Standalone loader -- no pydantic_settings dependency. Resolves relative
paths against ars_base so retrieve.py and format.py get absolute paths.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PathsConfig:
    ars_base: Path
    retrieve_dir: Path
    watch_root: Path
    incoming_dir: Path
    presentations_dir: Path
    archive_dir: Path
    config_dir: Path
    log_dir: Path
    template_path: Path
    tracker_path: Path


@dataclass
class CSMSources:
    sources: dict[str, Path] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    skip_pptx: bool = False
    skip_excel_archive: bool = False
    chart_dpi: int = 150
    max_workers: int = 1
    use_local_temp: bool = False


@dataclass
class Settings:
    paths: PathsConfig
    csm_sources: CSMSources
    pipeline: PipelineConfig


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load settings from JSON, resolve relative paths against ars_base."""
    if config_path is None:
        config_path = Path(__file__).parent / "ars_config.json"
    config_path = Path(config_path)

    with open(config_path, encoding="utf-8") as f:
        raw = json.load(f)

    # Resolve paths
    base = Path(raw["paths"]["ars_base"])
    paths_raw = raw["paths"]

    def resolve(key: str, default: str = "") -> Path:
        val = Path(paths_raw.get(key, default))
        return val if val.is_absolute() else base / val

    paths = PathsConfig(
        ars_base=base,
        retrieve_dir=resolve("retrieve_dir"),
        watch_root=resolve("watch_root"),
        incoming_dir=resolve("incoming_dir"),
        presentations_dir=resolve("presentations_dir"),
        archive_dir=resolve("archive_dir"),
        config_dir=resolve("config_dir"),
        log_dir=resolve("log_dir"),
        template_path=resolve("template_path"),
        tracker_path=resolve("tracker_path"),
    )

    # CSM sources
    csm_raw = raw.get("csm_sources", {}).get("sources", {})
    csm = CSMSources(sources={name: Path(p) for name, p in csm_raw.items()})

    # Pipeline
    pipe_raw = raw.get("pipeline", {})
    pipeline = PipelineConfig(
        skip_pptx=pipe_raw.get("skip_pptx", False),
        skip_excel_archive=pipe_raw.get("skip_excel_archive", False),
        chart_dpi=pipe_raw.get("chart_dpi", 150),
        max_workers=pipe_raw.get("max_workers", 1),
        use_local_temp=pipe_raw.get("use_local_temp", False),
    )

    return Settings(paths=paths, csm_sources=csm, pipeline=pipeline)
