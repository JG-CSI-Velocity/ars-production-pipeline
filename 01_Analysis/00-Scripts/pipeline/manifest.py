"""Structured run manifest -- live state of a pipeline run."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RunStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


class SectionStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"
    NO_CHARTS = "no_charts"
    SKIPPED = "skipped"


class ScriptStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


class FlagLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class AnomalyFlag:
    level: FlagLevel = FlagLevel.INFO
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level.value, "message": self.message}


@dataclass
class ScriptRecord:
    name: str = ""
    status: ScriptStatus = ScriptStatus.OK
    elapsed_s: float = 0.0
    slides: int = 0
    error_class: str = ""
    error_msg: str = ""
    error_file: str = ""
    error_line: int = 0
    error_traceback_tail: str = ""
    suggested_fix: str = ""
    issue_body_md: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class SectionRecord:
    name: str = ""
    status: SectionStatus = SectionStatus.RUNNING
    started_at: str = ""
    ended_at: str = ""
    elapsed_s: float = 0.0
    slides: int = 0
    key_numbers: dict[str, Any] = field(default_factory=dict)
    anomaly_flags: list[AnomalyFlag] = field(default_factory=list)
    scripts: list[ScriptRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "elapsed_s": self.elapsed_s,
            "slides": self.slides,
            "key_numbers": dict(self.key_numbers),
            "anomaly_flags": [f.to_dict() for f in self.anomaly_flags],
            "scripts": [s.to_dict() for s in self.scripts],
        }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


import json
import os
import tempfile
import time
from pathlib import Path

from loguru import logger


@dataclass
class RunManifest:
    """Owns the live state of a pipeline run. Flushes to JSON on every update."""

    client_id: str
    client_name: str
    csm: str
    month: str
    product: str
    output_dir: Path
    schema_version: int = 1
    run_id: str = ""
    started_at: str = ""
    ended_at: str = ""
    elapsed_s: float = 0.0
    status: RunStatus = RunStatus.RUNNING
    sections: list[SectionRecord] = field(default_factory=list)

    def __post_init__(self):
        self._start_monotonic: float = 0.0
        self.output_dir = Path(self.output_dir)

    @property
    def path(self) -> Path:
        return self.output_dir / "run_manifest.json"

    def start_run(self) -> None:
        self.started_at = _utcnow_iso()
        self._start_monotonic = time.monotonic()
        self.run_id = f"{self.client_id}_{self.month}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.status = RunStatus.RUNNING
        self.flush()

    def end_run(self, status: RunStatus) -> None:
        self.status = status
        self.ended_at = _utcnow_iso()
        if self._start_monotonic:
            self.elapsed_s = round(time.monotonic() - self._start_monotonic, 1)
        self.flush()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "csm": self.csm,
            "month": self.month,
            "product": self.product,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "elapsed_s": self.elapsed_s,
            "status": self.status.value,
            "totals": self._totals(),
            "sections": [s.to_dict() for s in self.sections],
        }

    def _totals(self) -> dict[str, int]:
        scripts = [sc for sec in self.sections for sc in sec.scripts]
        return {
            "sections_ok": sum(1 for s in self.sections if s.status == SectionStatus.OK),
            "sections_failed": sum(1 for s in self.sections if s.status == SectionStatus.FAILED),
            "sections_no_charts": sum(1 for s in self.sections if s.status == SectionStatus.NO_CHARTS),
            "scripts_total": len(scripts),
            "scripts_ok": sum(1 for s in scripts if s.status == ScriptStatus.OK),
            "scripts_failed": sum(1 for s in scripts if s.status == ScriptStatus.FAILED),
            "slides_built": sum(s.slides for s in self.sections),
        }

    def flush(self) -> None:
        """Atomic write. Never raises -- flush failures only log."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self.to_dict(), indent=2, default=str)
            fd, tmp_path = tempfile.mkstemp(
                prefix=".run_manifest_", suffix=".json.tmp",
                dir=str(self.output_dir),
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(payload)
                os.replace(tmp_path, self.path)
            except Exception:
                # On failure, clean up the temp file but leave the existing manifest alone
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as exc:
            logger.warning("manifest flush failed: {err}", err=exc)


class SectionRecorder:
    """Context manager that records one section. Yielded from RunManifest.start_section."""

    def __init__(self, manifest: "RunManifest", record: SectionRecord):
        self._mf = manifest
        self._record = record
        self._t0: float = 0.0

    def __enter__(self) -> "SectionRecorder":
        self._record.started_at = _utcnow_iso()
        self._record.status = SectionStatus.RUNNING
        self._t0 = time.monotonic()
        self._mf.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._record.ended_at = _utcnow_iso()
        self._record.elapsed_s = round(time.monotonic() - self._t0, 1)
        if exc is not None:
            self._record.status = SectionStatus.FAILED
        else:
            self._record.status = self._infer_status()
        self._mf.flush()
        return False  # do not suppress

    def _infer_status(self) -> SectionStatus:
        has_failed = any(s.status == ScriptStatus.FAILED for s in self._record.scripts)
        has_ok = any(s.status == ScriptStatus.OK for s in self._record.scripts)
        if has_failed and has_ok:
            return SectionStatus.PARTIAL
        if has_failed:
            return SectionStatus.FAILED
        if self._record.slides == 0 and not has_ok:
            return SectionStatus.NO_CHARTS
        return SectionStatus.OK

    # Mutation API used by call sites
    def set_slides(self, n: int) -> None:
        self._record.slides = int(n)

    def set_key_numbers(self, numbers: dict[str, Any]) -> None:
        self._record.key_numbers.update(numbers)

    def flag(self, level: FlagLevel, message: str) -> None:
        self._record.anomaly_flags.append(AnomalyFlag(level=level, message=message))

    def record_script(self, script: ScriptRecord) -> None:
        self._record.scripts.append(script)
        self._mf.flush()


# Add as a method on RunManifest -- insert near end_run
def _start_section_method(self, name: str) -> SectionRecorder:
    record = SectionRecord(name=name)
    self.sections.append(record)
    return SectionRecorder(self, record)


RunManifest.start_section = _start_section_method  # type: ignore[attr-defined]
