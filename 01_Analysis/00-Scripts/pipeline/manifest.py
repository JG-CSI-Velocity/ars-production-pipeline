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
