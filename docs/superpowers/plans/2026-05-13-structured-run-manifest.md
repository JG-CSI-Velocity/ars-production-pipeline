# Structured Run Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unreadable rolling-tally log with a structured `run_manifest.json` written live during every pipeline run, plus a derived `run_scorecard.md` post-run summary, plus pre-formatted GitHub issue bodies for every script failure.

**Architecture:** A pure-Python `RunManifest` class owns one in-memory dict per run, mutated by the pipeline at three integration points (`runner.py`, `analytics/txn_wrapper.py`, `pipeline/steps/generate.py`) and flushed to disk after every section. A separate `error_capture` module isolates traceback frame extraction + suggested-fix heuristics + issue-body templating. A separate `scorecard` module reads the finished manifest and writes the markdown summary. No changes to any of the 220 analytics scripts.

**Tech Stack:** Python 3.13, `dataclasses`, `json`, `traceback`, `pytest` (new test directory under `01_Analysis/00-Scripts/tests/`), `loguru` (already wired). No new dependencies.

**Spec reference:** `docs/superpowers/specs/2026-05-13-structured-run-manifest-design.md`

---

## File Structure

```
01_Analysis/00-Scripts/
├── pipeline/
│   ├── manifest.py         NEW   RunManifest class, status enums, JSON I/O
│   ├── error_capture.py    NEW   Frame extraction, suggested-fix heuristic, issue-body template
│   ├── scorecard.py        NEW   Markdown generator (reads manifest, writes run_scorecard.md)
│   ├── context.py          MOD   Add `manifest: RunManifest | None = None`
│   ├── runner.py           MOD   Create manifest at run start, flush at end + on exception
│   └── steps/
│       └── generate.py     MOD   Call scorecard.write at end of generate_output
└── analytics/
    └── txn_wrapper.py      MOD   record_script() inside _execute_scripts try/except

01_Analysis/00-Scripts/tests/   NEW directory
├── __init__.py             NEW   (empty)
├── conftest.py             NEW   Add 00-Scripts to sys.path so `ars_analysis...` imports work
├── test_manifest.py        NEW   RunManifest lifecycle, persistence, atomic write
├── test_error_capture.py   NEW   Frame extraction, heuristic, issue body
└── test_scorecard.py       NEW   Markdown generation from fixture manifests

docs/
└── manifest-schema.md      NEW   Schema reference for follow-up specs (UI, anomaly engine, curation agent)
```

Each new file has one clear responsibility:
- `manifest.py` — state container + persistence
- `error_capture.py` — turn an `Exception` into structured fields
- `scorecard.py` — render markdown from a finished manifest

These can be reasoned about independently. `txn_wrapper.py` becomes the *only* place that imports `error_capture` (it's where exceptions get caught); `runner.py` is the only place that imports `manifest.py` directly; `generate.py` is the only place that imports `scorecard.py`.

---

## Task 1: Test scaffolding

**Files:**
- Create: `01_Analysis/00-Scripts/tests/__init__.py`
- Create: `01_Analysis/00-Scripts/tests/conftest.py`

- [ ] **Step 1: Create empty `__init__.py`**

```python
# empty
```

- [ ] **Step 2: Create `conftest.py`**

```python
"""Pytest scaffolding for 01_Analysis modules.

Adds the 00-Scripts directory to sys.path so tests can import
`ars_analysis.pipeline.manifest` etc. directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
```

- [ ] **Step 3: Verify pytest discovers the directory**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/ -q --collect-only`
Expected: `no tests ran` (no test files yet, but no collection errors)

- [ ] **Step 4: Commit**

```bash
git add 01_Analysis/00-Scripts/tests/__init__.py 01_Analysis/00-Scripts/tests/conftest.py
git commit -m "test: scaffold 01_Analysis tests directory"
```

---

## Task 2: Manifest types (enums + dataclasses)

**Files:**
- Create: `01_Analysis/00-Scripts/pipeline/manifest.py`
- Create: `01_Analysis/00-Scripts/tests/test_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_manifest.py
from ars_analysis.pipeline import manifest as m


def test_status_enum_values():
    assert m.RunStatus.OK.value == "ok"
    assert m.RunStatus.PARTIAL.value == "partial"
    assert m.RunStatus.FAILED.value == "failed"


def test_section_status_enum_values():
    assert m.SectionStatus.OK.value == "ok"
    assert m.SectionStatus.PARTIAL.value == "partial"
    assert m.SectionStatus.FAILED.value == "failed"
    assert m.SectionStatus.NO_CHARTS.value == "no_charts"
    assert m.SectionStatus.SKIPPED.value == "skipped"


def test_script_record_round_trips_to_dict():
    rec = m.ScriptRecord(
        name="04_build_threat_data",
        status=m.ScriptStatus.FAILED,
        elapsed_s=2.3,
        error_class="IndexError",
        error_msg="out-of-bounds",
        error_file="competition/04_build_threat_data.py",
        error_line=18,
        suggested_fix="Add a len() guard before iloc[0].",
        issue_body_md="## Failure...",
    )
    d = rec.to_dict()
    assert d["name"] == "04_build_threat_data"
    assert d["status"] == "failed"
    assert d["error_line"] == 18
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_manifest.py -v`
Expected: FAIL with `ImportError` or `AttributeError`

- [ ] **Step 3: Implement the types**

```python
# pipeline/manifest.py
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
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_manifest.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/manifest.py 01_Analysis/00-Scripts/tests/test_manifest.py
git commit -m "feat(manifest): status enums + record dataclasses"
```

---

## Task 3: RunManifest core (start, flush, atomic write)

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/manifest.py` (append)
- Modify: `01_Analysis/00-Scripts/tests/test_manifest.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_manifest.py
import json
from pathlib import Path

def test_run_manifest_starts_and_flushes(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    rm.flush()

    out_path = tmp_path / "run_manifest.json"
    assert out_path.exists()

    data = json.loads(out_path.read_text())
    assert data["schema_version"] == 1
    assert data["client_id"] == "1200"
    assert data["status"] == "running"
    assert data["sections"] == []


def test_run_manifest_end_run_sets_status_and_elapsed(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    rm.end_run(m.RunStatus.OK)

    data = json.loads((tmp_path / "run_manifest.json").read_text())
    assert data["status"] == "ok"
    assert data["ended_at"]
    assert data["elapsed_s"] >= 0


def test_flush_is_atomic_via_tempfile_rename(tmp_path: Path, monkeypatch):
    """The flush path must NOT leave a half-written file if write fails."""
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    rm.flush()  # establish baseline

    baseline = (tmp_path / "run_manifest.json").read_text()

    # Force os.replace to fail; the existing file should remain valid
    import os as _os
    real_replace = _os.replace

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(_os, "replace", boom)
    rm.flush()  # must NOT raise -- flush failures are swallowed
    assert (tmp_path / "run_manifest.json").read_text() == baseline
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_manifest.py -v`
Expected: 3 new FAILs (`RunManifest` not defined)

- [ ] **Step 3: Append the RunManifest implementation**

Append to `pipeline/manifest.py`:

```python
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
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_manifest.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/manifest.py 01_Analysis/00-Scripts/tests/test_manifest.py
git commit -m "feat(manifest): RunManifest core + atomic flush"
```

---

## Task 4: Section recording (context-manager API)

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/manifest.py` (append)
- Modify: `01_Analysis/00-Scripts/tests/test_manifest.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_manifest.py
def test_section_recorder_records_ok_path(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    with rm.start_section("Competition") as sec:
        sec.set_key_numbers({"credit_unions": 2814, "top_25_fed_district": 0})
        sec.flag(m.FlagLevel.WARN, "top_25_fed_district=0 unexpected for FL")
        sec.set_slides(38)

    rm.end_run(m.RunStatus.OK)

    data = json.loads((tmp_path / "run_manifest.json").read_text())
    section = data["sections"][0]
    assert section["name"] == "Competition"
    assert section["status"] == "ok"
    assert section["slides"] == 38
    assert section["key_numbers"]["credit_unions"] == 2814
    assert section["anomaly_flags"][0]["level"] == "warn"
    assert section["elapsed_s"] >= 0


def test_section_recorder_marks_failed_on_exception(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    try:
        with rm.start_section("Competition") as sec:
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    rm.end_run(m.RunStatus.PARTIAL)

    data = json.loads((tmp_path / "run_manifest.json").read_text())
    assert data["sections"][0]["status"] == "failed"


def test_no_charts_status_when_slides_zero_and_no_scripts(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    with rm.start_section("MCC Categories") as sec:
        pass  # nothing produced
    rm.end_run(m.RunStatus.OK)

    data = json.loads((tmp_path / "run_manifest.json").read_text())
    assert data["sections"][0]["status"] == "no_charts"
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_manifest.py::test_section_recorder_records_ok_path -v`
Expected: FAIL (`start_section` doesn't exist)

- [ ] **Step 3: Append SectionRecorder + start_section**

Append to `pipeline/manifest.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify all pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_manifest.py -v`
Expected: 9 passed (3 existing + 3 new)

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/manifest.py 01_Analysis/00-Scripts/tests/test_manifest.py
git commit -m "feat(manifest): SectionRecorder context manager"
```

---

## Task 5: error_capture — deepest project frame

**Files:**
- Create: `01_Analysis/00-Scripts/pipeline/error_capture.py`
- Create: `01_Analysis/00-Scripts/tests/test_error_capture.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_error_capture.py
from pathlib import Path
from ars_analysis.pipeline import error_capture as ec


def test_deepest_project_frame_picks_inside_analytics():
    """Frame extraction should prefer the deepest frame inside 'analytics/'."""
    try:
        # Simulate: pandas calls something, which calls something in our code, which raises
        def _user_code():
            d = {"a": 1}
            return d[0]  # raises KeyError from "our" code

        _user_code()
    except KeyError as exc:
        import sys
        tb = sys.exc_info()[2]
        frame = ec.deepest_project_frame(tb, project_marker="analytics")
        # This test file is not under analytics/, so we expect None.
        assert frame is None


def test_deepest_project_frame_finds_marker(tmp_path: Path):
    """Build a fake module under analytics/ and confirm the frame is found."""
    # Synthesize a path-like trace entry
    fake_tb = [
        ec._FrameInfo(filename="/x/y/pandas/core/something.py", lineno=999),
        ec._FrameInfo(filename="/M/ARS/01_Analysis/00-Scripts/analytics/competition/04_build_threat_data.py", lineno=18),
        ec._FrameInfo(filename="/x/y/numpy/something.py", lineno=42),
    ]
    frame = ec._pick_deepest_marker_frame(fake_tb, "analytics")
    assert frame is not None
    assert frame.lineno == 18
    assert "04_build_threat_data" in frame.filename
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_error_capture.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement error_capture frame extraction**

```python
# pipeline/error_capture.py
"""Turn an Exception into structured manifest fields."""
from __future__ import annotations

import re
import traceback
from dataclasses import dataclass
from types import TracebackType
from typing import Iterable


@dataclass
class _FrameInfo:
    filename: str
    lineno: int


def _pick_deepest_marker_frame(frames: Iterable[_FrameInfo], project_marker: str) -> _FrameInfo | None:
    """Walk frames from outermost to innermost; return the LAST frame whose
    filename contains project_marker."""
    found: _FrameInfo | None = None
    for f in frames:
        if project_marker in f.filename:
            found = f
    return found


def deepest_project_frame(tb: TracebackType | None, project_marker: str = "analytics") -> _FrameInfo | None:
    """Extract the deepest traceback frame inside the project (filtering library internals)."""
    if tb is None:
        return None
    extracted = traceback.extract_tb(tb)
    frames = [_FrameInfo(filename=f.filename, lineno=f.lineno) for f in extracted]
    return _pick_deepest_marker_frame(frames, project_marker)
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_error_capture.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/error_capture.py 01_Analysis/00-Scripts/tests/test_error_capture.py
git commit -m "feat(error_capture): deepest-project-frame extraction"
```

---

## Task 6: error_capture — suggested-fix heuristic

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/error_capture.py` (append)
- Modify: `01_Analysis/00-Scripts/tests/test_error_capture.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_error_capture.py
def test_suggest_fix_indexerror_out_of_bounds():
    s = ec.suggest_fix("IndexError", "single positional indexer is out-of-bounds")
    assert "len()" in s or "empty" in s.lower()


def test_suggest_fix_keyerror():
    s = ec.suggest_fix("KeyError", "'transaction_date'")
    assert "column" in s.lower() or "key" in s.lower()


def test_suggest_fix_memoryerror():
    s = ec.suggest_fix("MemoryError", "Unable to allocate 5.58 GiB for an array")
    assert "cross-join" in s.lower() or "cardinality" in s.lower()


def test_suggest_fix_nameerror():
    s = ec.suggest_fix("NameError", "name 'combined_df' is not defined")
    assert "upstream" in s.lower() or "earlier" in s.lower()


def test_suggest_fix_unknown_returns_empty():
    s = ec.suggest_fix("ValueError", "something weird")
    assert s == ""
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_error_capture.py -v`
Expected: 5 new FAILs

- [ ] **Step 3: Append the heuristic**

```python
# Append to pipeline/error_capture.py
_FIX_RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "IndexError",
        re.compile(r"out.of.bounds|out of bounds", re.IGNORECASE),
        "Empty group or series. Add a `len() > 0` (or `not df.empty`) guard before `iloc[0]`.",
    ),
    (
        "KeyError",
        re.compile(r".*"),
        "Column or dict key not found. Check the upstream cell that's supposed to produce this field, and verify the column rename didn't happen in standardize_merchant_name.",
    ),
    (
        "MemoryError",
        re.compile(r"unable to allocate|cannot allocate", re.IGNORECASE),
        "Likely a cross-join or unbounded groupby. Check `competitor_match` (or other groupby key) cardinality; if it's in the millions, an upstream consolidation step probably failed.",
    ),
    (
        "NameError",
        re.compile(r"is not defined", re.IGNORECASE),
        "An upstream script in this section failed and never defined this variable. Look at the earliest failure in this section's manifest scripts list.",
    ),
    (
        "FileNotFoundError",
        re.compile(r".*"),
        "Path missing. If it looks like a dev-only path (/tmp, /private/tmp), remove the hardcoded reference; if it's a real input, check that the formatting step produced it.",
    ),
    (
        "ParserError",
        re.compile(r"expected.*fields|tokenizing data", re.IGNORECASE),
        "CSV delimiter mismatch. Verify the file is comma vs tab delimited; the loader auto-retries but only if the first try raises ParserError, not on a silent 1-column parse.",
    ),
]


def suggest_fix(error_class: str, error_msg: str) -> str:
    """Map (error_class, message) to a short suggested-fix string. Empty if no match."""
    for cls, pattern, suggestion in _FIX_RULES:
        if cls == error_class and pattern.search(error_msg or ""):
            return suggestion
    return ""
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_error_capture.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/error_capture.py 01_Analysis/00-Scripts/tests/test_error_capture.py
git commit -m "feat(error_capture): suggested-fix heuristic table"
```

---

## Task 7: error_capture — issue body template + capture_exception entry point

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/error_capture.py` (append)
- Modify: `01_Analysis/00-Scripts/tests/test_error_capture.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_error_capture.py
def test_capture_exception_populates_script_record_fields():
    try:
        d = {"a": 1}
        return_value = d[0]  # noqa: F841
    except KeyError as exc:
        import sys
        tb = sys.exc_info()[2]
        fields = ec.capture_exception(
            exc, tb,
            section_name="Competition",
            script_name="04_build_threat_data",
            client_id="1200", month="2026.05",
            project_marker="tests",  # use tests/ so the test file itself is the "project frame"
        )

    assert fields["error_class"] == "KeyError"
    assert "0" in fields["error_msg"]
    assert fields["error_file"].endswith("test_error_capture.py")
    assert fields["error_line"] > 0
    assert fields["error_traceback_tail"]
    assert fields["suggested_fix"]  # KeyError always has a suggestion
    body = fields["issue_body_md"]
    assert "Competition" in body
    assert "04_build_threat_data" in body
    assert "1200" in body
    assert "2026.05" in body
    assert "KeyError" in body
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_error_capture.py::test_capture_exception_populates_script_record_fields -v`
Expected: FAIL (`capture_exception` doesn't exist)

- [ ] **Step 3: Append the entry point + issue body template**

```python
# Append to pipeline/error_capture.py
def _format_issue_body(
    *, error_class: str, error_msg: str, error_file: str, error_line: int,
    traceback_tail: str, suggested_fix: str,
    section_name: str, script_name: str,
    client_id: str, month: str,
) -> str:
    suggestion_block = f"**Suggested fix:** {suggested_fix}\n\n" if suggested_fix else ""
    return (
        f"## Failure during {client_id} / {month} run\n\n"
        f"**Section:** {section_name}\n"
        f"**Script:** {script_name}\n"
        f"**Error:** {error_class} — {error_msg}\n"
        f"**Location:** `{error_file}:{error_line}`\n\n"
        f"{suggestion_block}"
        f"<details><summary>Traceback tail</summary>\n\n"
        f"```\n{traceback_tail}\n```\n\n"
        f"</details>\n"
    )


def capture_exception(
    exc: BaseException,
    tb: TracebackType | None,
    *,
    section_name: str,
    script_name: str,
    client_id: str,
    month: str,
    project_marker: str = "analytics",
) -> dict[str, object]:
    """Turn an exception + traceback into the structured fields a ScriptRecord wants."""
    error_class = type(exc).__name__
    error_msg = str(exc)[:300]

    frame = deepest_project_frame(tb, project_marker=project_marker)
    error_file = frame.filename if frame else ""
    error_line = frame.lineno if frame else 0

    if tb is not None:
        tb_lines = traceback.format_exception(type(exc), exc, tb)
        traceback_tail = "".join(tb_lines)[-2000:]
    else:
        traceback_tail = ""

    suggested = suggest_fix(error_class, error_msg)

    body = _format_issue_body(
        error_class=error_class, error_msg=error_msg,
        error_file=error_file, error_line=error_line,
        traceback_tail=traceback_tail, suggested_fix=suggested,
        section_name=section_name, script_name=script_name,
        client_id=client_id, month=month,
    )

    return {
        "error_class": error_class,
        "error_msg": error_msg,
        "error_file": error_file,
        "error_line": error_line,
        "error_traceback_tail": traceback_tail,
        "suggested_fix": suggested,
        "issue_body_md": body,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_error_capture.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/error_capture.py 01_Analysis/00-Scripts/tests/test_error_capture.py
git commit -m "feat(error_capture): capture_exception + issue body template"
```

---

## Task 8: scorecard — markdown generator

**Files:**
- Create: `01_Analysis/00-Scripts/pipeline/scorecard.py`
- Create: `01_Analysis/00-Scripts/tests/test_scorecard.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scorecard.py
from pathlib import Path
import json
from ars_analysis.pipeline import manifest as m
from ars_analysis.pipeline import scorecard


def _build_fixture_manifest(tmp_path: Path) -> m.RunManifest:
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()
    with rm.start_section("Portfolio Overview") as sec:
        sec.set_slides(17)
        sec.set_key_numbers({"accounts": 36840, "active": 22229})
    with rm.start_section("Competition") as sec:
        sec.set_slides(38)
        sec.set_key_numbers({"credit_unions": 2814, "top_25_fed_district": 0})
        sec.flag(m.FlagLevel.WARN, "top_25_fed_district=0 unexpected for FL")
        sec.record_script(m.ScriptRecord(
            name="04_build_threat_data",
            status=m.ScriptStatus.FAILED,
            error_class="IndexError",
            error_msg="single positional indexer is out-of-bounds",
            error_file="competition/04_build_threat_data.py",
            error_line=18,
            suggested_fix="Add len() guard before iloc[0].",
            issue_body_md="## Failure during 1200 / 2026.05 run\n\n**Section:** Competition\n",
        ))
    with rm.start_section("MCC Categories") as sec:
        pass
    rm.end_run(m.RunStatus.PARTIAL)
    return rm


def test_scorecard_writes_markdown_with_verdict(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "Run scorecard" in text
    assert "1200" in text
    assert "2026.05" in text
    assert "Verdict" in text


def test_scorecard_includes_failure_with_issue_body(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "04_build_threat_data" in text
    assert "IndexError" in text
    assert "Issue body" in text
    assert "len() guard" in text


def test_scorecard_lists_section_table(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "Portfolio Overview" in text
    assert "Competition" in text
    assert "MCC Categories" in text
    assert "no_charts" in text or "No charts" in text


def test_scorecard_surfaces_anomaly_flags(tmp_path: Path):
    rm = _build_fixture_manifest(tmp_path)
    out = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = out.read_text()
    assert "top_25_fed_district=0" in text
    assert "warn" in text or "Warn" in text
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_scorecard.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement scorecard**

```python
# pipeline/scorecard.py
"""Render run_scorecard.md from a finished RunManifest."""
from __future__ import annotations

from pathlib import Path

from ars_analysis.pipeline.manifest import (
    FlagLevel,
    RunManifest,
    RunStatus,
    ScriptStatus,
    SectionStatus,
)


def _verdict(rm: RunManifest) -> str:
    totals = rm._totals()
    if rm.status == RunStatus.OK and totals["scripts_failed"] == 0:
        flagged = sum(
            1 for sec in rm.sections
            for f in sec.anomaly_flags
            if f.level in (FlagLevel.WARN, FlagLevel.ERROR)
        )
        if flagged:
            return "Ship with caution — anomaly flags present"
        return "Ship"
    if rm.status == RunStatus.FAILED:
        return "Do not ship — pipeline failed"
    return "Investigate before shipping"


def _section_row(sec) -> str:
    flags = ", ".join(f.level.value for f in sec.anomaly_flags) or "—"
    keys = ", ".join(f"{k}={v}" for k, v in list(sec.key_numbers.items())[:3]) or "—"
    status_label = {
        SectionStatus.OK: "OK",
        SectionStatus.PARTIAL: "Partial",
        SectionStatus.FAILED: "Failed",
        SectionStatus.NO_CHARTS: "No charts",
        SectionStatus.SKIPPED: "Skipped",
        SectionStatus.RUNNING: "Running",
    }.get(sec.status, str(sec.status))
    return f"| {sec.name} | {status_label} | {sec.slides} | {keys} | {flags} |"


def _failure_block(sec, script) -> str:
    body = script.issue_body_md or "(no issue body)"
    suggestion = f"\n*Suggested fix: {script.suggested_fix}*\n" if script.suggested_fix else ""
    return (
        f"### {sec.name} · {script.name} — {script.error_class}\n\n"
        f"> {script.error_msg} at `{script.error_file}:{script.error_line}`{suggestion}\n\n"
        f"<details><summary>Issue body (copy/paste)</summary>\n\n"
        f"{body}\n\n"
        f"</details>\n"
    )


def _anomaly_lines(rm: RunManifest) -> list[str]:
    lines: list[str] = []
    for sec in rm.sections:
        for flag in sec.anomaly_flags:
            lines.append(f"- **{sec.name}** ({flag.level.value}): {flag.message}")
    return lines


def write(rm: RunManifest, path: Path) -> Path:
    """Render the scorecard markdown. Returns the path written."""
    path = Path(path)
    totals = rm._totals()
    failures = [(sec, sc) for sec in rm.sections for sc in sec.scripts if sc.status == ScriptStatus.FAILED]
    anomaly_lines = _anomaly_lines(rm)

    out: list[str] = []
    out.append(f"# Run scorecard — {rm.client_id} / {rm.month} ({rm.csm})")
    out.append("")
    out.append(f"**Verdict:** {_verdict(rm)}")
    out.append("")
    out.append(f"- Slides built: **{totals['slides_built']}**")
    out.append(f"- Sections OK: {totals['sections_ok']} | failed: {totals['sections_failed']} | no charts: {totals['sections_no_charts']}")
    out.append(f"- Scripts OK: {totals['scripts_ok']} / {totals['scripts_total']} (failed: {totals['scripts_failed']})")
    out.append(f"- Elapsed: {rm.elapsed_s:.0f}s")
    out.append("")
    out.append("## Section status")
    out.append("")
    out.append("| Section | Status | Slides | Key numbers | Flags |")
    out.append("| --- | --- | --- | --- | --- |")
    for sec in rm.sections:
        out.append(_section_row(sec))
    out.append("")

    if failures:
        out.append("## Failures (ready to file)")
        out.append("")
        for sec, sc in failures:
            out.append(_failure_block(sec, sc))
            out.append("")

    if anomaly_lines:
        out.append("## Anomaly flags")
        out.append("")
        out.extend(anomaly_lines)
        out.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    return path
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_scorecard.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/scorecard.py 01_Analysis/00-Scripts/tests/test_scorecard.py
git commit -m "feat(scorecard): markdown generator from RunManifest"
```

---

## Task 9: Wire manifest into PipelineContext

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/context.py:76-100` (PipelineContext dataclass)

- [ ] **Step 1: Inspect the current PipelineContext**

```bash
sed -n '76,105p' 01_Analysis/00-Scripts/pipeline/context.py
```

- [ ] **Step 2: Add the manifest field**

Edit `01_Analysis/00-Scripts/pipeline/context.py`:

Find:
```python
    debit_column: str = ""  # Auto-detected debit column name (set by step_subsets)
    progress_callback: Callable[[str], None] | None = None
```

Replace with:
```python
    debit_column: str = ""  # Auto-detected debit column name (set by step_subsets)
    progress_callback: Callable[[str], None] | None = None
    manifest: object = None  # ars_analysis.pipeline.manifest.RunManifest | None
```

`object` instead of importing `RunManifest` avoids a circular import (manifest.py doesn't import context.py, but the loader order during cold start can be fragile). Call sites use `getattr(ctx, "manifest", None)` defensively.

- [ ] **Step 3: Verify it parses + nothing breaks**

```bash
cd 01_Analysis/00-Scripts && python -c "from ars_analysis.pipeline.context import PipelineContext; print(PipelineContext.__dataclass_fields__['manifest'])"
```
Expected: prints a Field object referencing `manifest`.

- [ ] **Step 4: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/context.py
git commit -m "feat(pipeline): add manifest field to PipelineContext"
```

---

## Task 10: Wire manifest into runner.py (start_run + end_run + flush on exception)

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/runner.py`

- [ ] **Step 1: Read the runner to find the right anchors**

```bash
grep -n "def run_pipeline\|AUDIT\|client_label" 01_Analysis/00-Scripts/pipeline/runner.py
```

Confirm line numbers for the `run_pipeline` function start and the AUDIT logger.info() calls at run start and run end. Note the line numbers in your scratch notes; you'll edit there.

- [ ] **Step 2: Inject manifest creation at run start**

In `run_pipeline()`, right after `client_label = f"..."`, before the first AUDIT logger.info, add:

```python
    # Structured run manifest -- writes run_manifest.json next to the log.
    try:
        from ars_analysis.pipeline.manifest import RunManifest, RunStatus
        _manifest = RunManifest(
            client_id=ctx.client.client_id,
            client_name=getattr(ctx.client, "client_name", "") or "",
            csm=getattr(ctx.client, "csm", "") or "",
            month=getattr(ctx.client, "month", "") or "",
            product=getattr(ctx.settings, "product", "") if ctx.settings else "",
            output_dir=ctx.paths.base_dir,
        )
        _manifest.start_run()
        ctx.manifest = _manifest
    except Exception as _exc:
        logger.warning("manifest init failed (continuing): {err}", err=_exc)
        ctx.manifest = None
```

- [ ] **Step 3: Inject end-of-run flush**

After the per-step loop, before the final `return results`, add:

```python
    # Finalize manifest with the overall run status.
    if getattr(ctx, "manifest", None) is not None:
        try:
            from ars_analysis.pipeline.manifest import RunStatus
            any_failed = any(not r.success and r.name != "archive" for r in results)
            ctx.manifest.end_run(RunStatus.PARTIAL if any_failed else RunStatus.OK)
        except Exception as _exc:
            logger.warning("manifest end_run failed: {err}", err=_exc)
```

- [ ] **Step 4: Inject exception-path flush**

Find the try/except around the per-step execution (look for `except Exception as exc:` inside `run_pipeline`). Right after the `logger.error("...")` line in the critical-failure branch, before the `break`, add:

```python
            if getattr(ctx, "manifest", None) is not None:
                try:
                    from ars_analysis.pipeline.manifest import RunStatus
                    ctx.manifest.end_run(RunStatus.FAILED)
                except Exception:
                    pass
```

- [ ] **Step 5: Verify pipeline imports still work**

```bash
cd 01_Analysis/00-Scripts && python -c "from ars_analysis.pipeline.runner import run_pipeline; print('ok')"
```
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/runner.py
git commit -m "feat(runner): create + finalize RunManifest around pipeline execution"
```

---

## Task 11: Wire manifest into txn_wrapper._execute_scripts

**Files:**
- Modify: `01_Analysis/00-Scripts/analytics/txn_wrapper.py`

- [ ] **Step 1: Find the try/except inside `_execute_scripts`**

```bash
grep -n "try:\|except Exception as exc\|ScriptFailure(" 01_Analysis/00-Scripts/analytics/txn_wrapper.py
```

You're looking for the block where each script is `exec()`'d. There's already a `ScriptFailure` dataclass and an exception handler that calls `logger.error` and `failures.append(...)`. We're adding to that handler.

- [ ] **Step 2: Add `manifest` parameter to `_execute_scripts`**

Locate the `def _execute_scripts(...)` signature. Update it to accept the active section recorder:

Find:
```python
def _execute_scripts(script_dir: Path, namespace: dict[str, Any],
                     chart_dir: Path, section_prefix: str
                     ) -> tuple[list[Path], list[ScriptFailure]]:
```

Replace with:
```python
def _execute_scripts(script_dir: Path, namespace: dict[str, Any],
                     chart_dir: Path, section_prefix: str,
                     section_recorder: object = None,
                     manifest_meta: dict[str, str] | None = None,
                     ) -> tuple[list[Path], list[ScriptFailure]]:
```

`manifest_meta` carries `client_id` and `month` for the issue body templating.

- [ ] **Step 3: Inject success + failure records inside the per-script loop**

Locate the per-script loop block:
```python
        with ChartCapture(chart_dir, prefix=f"{section_prefix}_{script_name}") as capture:
            try:
                code = script_path.read_text(encoding="utf-8")
                namespace["__file__"] = str(script_path)
                exec(compile(code, str(script_path), "exec"), namespace)
            except Exception as exc:
                logger.error("  TXN script failed: {name}: {err}", name=script_name, err=exc)
                failures.append(ScriptFailure(
                    script_name=script_name,
                    error_type=type(exc).__name__,
                    error_msg=str(exc)[:200],
                ))
```

Wrap this block in a timer and add manifest recording. Replace it with:

```python
        with ChartCapture(chart_dir, prefix=f"{section_prefix}_{script_name}") as capture:
            import sys as _sys
            import time as _time
            from ars_analysis.pipeline.manifest import ScriptRecord, ScriptStatus
            from ars_analysis.pipeline import error_capture as _ec

            _t0 = _time.monotonic()
            _failed = False
            try:
                code = script_path.read_text(encoding="utf-8")
                namespace["__file__"] = str(script_path)
                exec(compile(code, str(script_path), "exec"), namespace)
            except Exception as exc:
                _failed = True
                logger.error("  TXN script failed: {name}: {err}", name=script_name, err=exc)
                failures.append(ScriptFailure(
                    script_name=script_name,
                    error_type=type(exc).__name__,
                    error_msg=str(exc)[:200],
                ))
                if section_recorder is not None:
                    meta = manifest_meta or {}
                    fields = _ec.capture_exception(
                        exc, _sys.exc_info()[2],
                        section_name=section_prefix,
                        script_name=script_name,
                        client_id=meta.get("client_id", ""),
                        month=meta.get("month", ""),
                    )
                    section_recorder.record_script(ScriptRecord(
                        name=script_name,
                        status=ScriptStatus.FAILED,
                        elapsed_s=round(_time.monotonic() - _t0, 2),
                        **fields,
                    ))

            if not _failed and section_recorder is not None:
                section_recorder.record_script(ScriptRecord(
                    name=script_name,
                    status=ScriptStatus.OK,
                    elapsed_s=round(_time.monotonic() - _t0, 2),
                    slides=len(capture.captured) if hasattr(capture, "captured") else 0,
                ))
```

Note: `**fields` spreads the dict returned by `capture_exception` into the `ScriptRecord` constructor. Verify the keys match: `error_class`, `error_msg`, `error_file`, `error_line`, `error_traceback_tail`, `suggested_fix`, `issue_body_md` — these are all already on `ScriptRecord`.

- [ ] **Step 4: Update the call site in TXNSectionWrapper.run**

`_execute_scripts` has three call sites in `txn_wrapper.py` — one for `txn_setup` (one-shot, runs across all sections), one for the main per-section call inside `TXNSectionWrapper.run`, and a third helper call. We only wrap the **main per-section call** (around line 317 in current code, the one immediately after `chart_dir = ctx.paths.charts_dir / self.section_name`). The other two intentionally don't record into the manifest because they're shared setup/teardown, not section work.

Locate the main call (search for `charts, self.failures = _execute_scripts(`):
```python
charts, self.failures = _execute_scripts(
    self.section_dir, namespace, chart_dir, self.section_name,
)
```

Replace with:
```python
_mf = getattr(ctx, "manifest", None)
_section_cm = _mf.start_section(self.display_name) if _mf is not None else _NullCM()
_manifest_meta = {
    "client_id": getattr(ctx.client, "client_id", ""),
    "month": getattr(ctx.client, "month", ""),
} if _mf is not None else None

with _section_cm as _sec:
    _recorder = _sec if _mf is not None else None
    charts, self.failures = _execute_scripts(
        self.section_dir, namespace, chart_dir, self.section_name,
        section_recorder=_recorder, manifest_meta=_manifest_meta,
    )
    # Record slide count + flag if zero slides on a section that expected them
    if _mf is not None and _recorder is not None:
        _recorder.set_slides(len(charts))
        if len(charts) == 0 and len(self.failures) == 0:
            # Section produced nothing without errors -- worth flagging
            from ars_analysis.pipeline.manifest import FlagLevel
            _recorder.flag(FlagLevel.INFO, "section produced 0 slides without errors")
```

Add this small helper class somewhere near the top of `txn_wrapper.py` (after the existing imports):
```python
class _NullCM:
    def __enter__(self): return None
    def __exit__(self, *a): return False
```

- [ ] **Step 5: Verify imports + a quick syntax check**

```bash
cd 01_Analysis/00-Scripts && python -c "import ars_analysis.analytics.txn_wrapper; print('ok')"
```
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add 01_Analysis/00-Scripts/analytics/txn_wrapper.py
git commit -m "feat(txn_wrapper): record per-script status + capture errors into manifest"
```

---

## Task 12: Wire scorecard.write into the generate step

**Files:**
- Modify: `01_Analysis/00-Scripts/pipeline/steps/generate.py`

- [ ] **Step 1: Find the end of step_generate**

```bash
grep -n "def step_generate\|Deliverables generated" 01_Analysis/00-Scripts/pipeline/steps/generate.py
```

- [ ] **Step 2: Add scorecard call after the "Deliverables generated" log line**

Find the line that logs `Deliverables generated for {client_id}`. Right after that line (still inside the function), add:

```python
    # Post-run scorecard derived from the manifest. Optional: only runs if
    # the manifest was set up. Failures here never break the pipeline.
    _mf = getattr(ctx, "manifest", None)
    if _mf is not None:
        try:
            from ars_analysis.pipeline.scorecard import write as _scorecard_write
            _scorecard_path = ctx.paths.base_dir / "run_scorecard.md"
            _scorecard_write(_mf, _scorecard_path)
            logger.info("Run scorecard written: {p}", p=_scorecard_path)
        except Exception as _exc:
            logger.warning("scorecard write failed: {err}", err=_exc)
```

- [ ] **Step 3: Verify import works**

```bash
cd 01_Analysis/00-Scripts && python -c "from ars_analysis.pipeline.steps import generate; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add 01_Analysis/00-Scripts/pipeline/steps/generate.py
git commit -m "feat(generate): write run_scorecard.md from manifest at end of pipeline"
```

---

## Task 13: End-to-end integration smoke test

**Files:**
- Create: `01_Analysis/00-Scripts/tests/test_pipeline_integration.py`

- [ ] **Step 1: Write a fake-pipeline integration test**

This test exercises the full manifest lifecycle without running the real analytics pipeline. It proves the wiring is consistent.

```python
# tests/test_pipeline_integration.py
from pathlib import Path
import json

from ars_analysis.pipeline import manifest as m
from ars_analysis.pipeline import scorecard
from ars_analysis.pipeline import error_capture as ec


def test_full_lifecycle_writes_manifest_and_scorecard(tmp_path: Path):
    rm = m.RunManifest(
        client_id="1200", client_name="Guardians CU",
        csm="JamesG", month="2026.05", product="combined",
        output_dir=tmp_path,
    )
    rm.start_run()

    # Section 1: success path
    with rm.start_section("Portfolio Overview") as sec:
        sec.set_key_numbers({"accounts": 36840})
        sec.record_script(m.ScriptRecord(name="02_portfolio_data", status=m.ScriptStatus.OK, slides=3))
        sec.set_slides(17)

    # Section 2: a real failure captured through error_capture
    with rm.start_section("Competition") as sec:
        try:
            d = {"a": 1}
            return_val = d[0]  # noqa: F841
        except KeyError as exc:
            import sys
            fields = ec.capture_exception(
                exc, sys.exc_info()[2],
                section_name="Competition",
                script_name="04_build_threat_data",
                client_id="1200", month="2026.05",
                project_marker="tests",
            )
            sec.record_script(m.ScriptRecord(
                name="04_build_threat_data",
                status=m.ScriptStatus.FAILED,
                **fields,
            ))
            sec.flag(m.FlagLevel.WARN, "data anomaly")
        sec.set_slides(38)

    rm.end_run(m.RunStatus.PARTIAL)

    manifest_path = tmp_path / "run_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["status"] == "partial"
    assert data["totals"]["scripts_failed"] == 1
    assert data["totals"]["sections_ok"] == 1
    assert data["sections"][1]["scripts"][0]["error_class"] == "KeyError"

    scorecard_path = scorecard.write(rm, tmp_path / "run_scorecard.md")
    text = scorecard_path.read_text()
    assert "Run scorecard" in text
    assert "Portfolio Overview" in text
    assert "Competition" in text
    assert "04_build_threat_data" in text
    assert "Issue body" in text
```

- [ ] **Step 2: Run the integration test**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/test_pipeline_integration.py -v`
Expected: 1 passed

- [ ] **Step 3: Run the full test suite**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/ -v`
Expected: all tests pass (16 total: 9 manifest + 8 error_capture + 4 scorecard + 1 integration = should be 22; verify the actual count matches your expectations from earlier tasks)

- [ ] **Step 4: Commit**

```bash
git add 01_Analysis/00-Scripts/tests/test_pipeline_integration.py
git commit -m "test: end-to-end manifest + scorecard lifecycle"
```

---

## Task 14: Schema doc for follow-up specs

**Files:**
- Create: `docs/manifest-schema.md`

- [ ] **Step 1: Write the schema reference**

```markdown
# run_manifest.json schema

Source of truth: `01_Analysis/00-Scripts/pipeline/manifest.py`.

Consumers: post-run scorecard (today), future UI panel, future anomaly engine, future curation agent.

## Top-level fields

| Field            | Type   | Notes |
| ---              | ---    | --- |
| `schema_version` | int    | Always 1 in this spec. Bump for breaking changes. |
| `run_id`         | str    | `{client_id}_{month}_{YYYYMMDD_HHMMSS}` |
| `client_id`      | str    | |
| `client_name`    | str    | |
| `csm`            | str    | |
| `month`          | str    | `YYYY.MM` |
| `product`        | str    | `ars` / `txn` / `combined` |
| `started_at`     | str    | ISO 8601 UTC |
| `ended_at`       | str    | ISO 8601 UTC |
| `elapsed_s`      | float  | |
| `status`         | str    | `running` / `ok` / `partial` / `failed` |
| `totals`         | object | aggregate counters (see below) |
| `sections`       | array  | one entry per pipeline section |

## `totals`

| Field                | Type | Notes |
| ---                  | ---  | --- |
| `sections_ok`        | int  | |
| `sections_failed`    | int  | |
| `sections_no_charts` | int  | |
| `scripts_total`      | int  | |
| `scripts_ok`         | int  | |
| `scripts_failed`     | int  | |
| `slides_built`       | int  | sum across sections |

## `sections[]`

| Field            | Type   | Notes |
| ---              | ---    | --- |
| `name`           | str    | Section display name |
| `status`         | str    | `running` / `ok` / `partial` / `failed` / `no_charts` / `skipped` |
| `started_at`     | str    | ISO 8601 UTC |
| `ended_at`       | str    | ISO 8601 UTC |
| `elapsed_s`      | float  | |
| `slides`         | int    | Number of charts captured this section |
| `key_numbers`    | object | Free-form `{string: number}` — section reports its own KPIs |
| `anomaly_flags`  | array  | `[{level: info|warn|error, message: str}]` |
| `scripts`        | array  | one entry per .py script in the section |

## `sections[].scripts[]`

| Field                  | Type | Notes |
| ---                    | ---  | --- |
| `name`                 | str  | Script stem |
| `status`               | str  | `ok` / `failed` / `skipped` |
| `elapsed_s`            | float | |
| `slides`               | int  | Charts captured by this script |
| `error_class`          | str  | Exception class name (empty on success) |
| `error_msg`            | str  | First 300 chars |
| `error_file`           | str  | Deepest project frame path |
| `error_line`           | int  | Line in error_file |
| `error_traceback_tail` | str  | Last 2KB of traceback string |
| `suggested_fix`        | str  | Heuristic suggestion (may be empty) |
| `issue_body_md`        | str  | Pre-formatted GitHub issue body |

## Compatibility rules

- **Add fields freely.** Consumers must use `.get()` with defaults.
- **Never rename or remove fields** without bumping `schema_version`.
- **Status string values are stable** (UI/consumers may switch on them).
```

- [ ] **Step 2: Commit**

```bash
git add docs/manifest-schema.md
git commit -m "docs: run_manifest.json schema reference"
```

---

## Task 15: Final smoke run

**Goal:** Confirm the manifest writes correctly during a real (or near-real) pipeline run.

- [ ] **Step 1: Verify the full test suite still passes**

Run: `cd 01_Analysis/00-Scripts && python -m pytest tests/ -q`
Expected: all pass

- [ ] **Step 2: Inspect a test fixture run**

```bash
cd 01_Analysis/00-Scripts && python -c "
from pathlib import Path
import tempfile, json
from ars_analysis.pipeline import manifest as m
with tempfile.TemporaryDirectory() as d:
    rm = m.RunManifest(client_id='1200', client_name='Guardians', csm='JamesG', month='2026.05', product='combined', output_dir=Path(d))
    rm.start_run()
    with rm.start_section('Test') as sec:
        sec.set_key_numbers({'count': 100})
        sec.set_slides(5)
    rm.end_run(m.RunStatus.OK)
    print(json.dumps(json.loads((Path(d)/'run_manifest.json').read_text()), indent=2))
"
```
Expected: prints a full manifest JSON with status `ok`, one section, totals.

- [ ] **Step 3: Push the branch**

```bash
git push -u origin spec/structured-run-manifest
```

- [ ] **Step 4: Open the PR**

```bash
gh pr create --title "feat(pipeline): structured run manifest + post-run scorecard" --body "Implements docs/superpowers/specs/2026-05-13-structured-run-manifest-design.md.

- New RunManifest class (in-memory + atomic JSON flush)
- error_capture: deepest-project-frame extraction, suggested-fix heuristic, issue-body template
- scorecard: post-run Markdown summary with copy-paste failure issue bodies
- Wired into runner.py + analytics/txn_wrapper.py + steps/generate.py
- No changes to any of the 220 analytics scripts
- Tests: pipeline/tests/ (manifest, error_capture, scorecard, integration)

After merge: run_manifest.json + run_scorecard.md ship next to the deck for every run."
```

---

## Self-review (writer's checklist)

This plan was self-reviewed against the spec on 2026-05-13. Notes:

- **Spec coverage:** Every section in the spec has at least one task. Architecture diagram → Tasks 2-12. Schema → Tasks 2-4. Structured error capture → Tasks 5-7 + 11. Post-run scorecard → Task 8 + 12. Testing → Tasks 1, 2, 3, 4, 5, 6, 7, 8, 13. Out-of-scope items (UI, anomaly engine, curation agent, pre-flight validator, checkpoint/resume) are correctly absent.
- **No placeholders:** No "TBD" or "implement appropriately" — every step shows exact code or commands.
- **Type consistency:** `ScriptRecord` field names (`error_class`, `error_msg`, `error_file`, `error_line`, `error_traceback_tail`, `suggested_fix`, `issue_body_md`) match between Task 2 (definition) and Tasks 7 + 11 (consumers via `**fields` spread). `RunStatus` / `SectionStatus` / `ScriptStatus` / `FlagLevel` enums consistent across all tasks. `RunManifest.start_section()` API matches between Task 4 (defined) and Tasks 11 + 13 (used). `scorecard.write(rm, path) -> Path` signature matches between Task 8 (defined) and Task 12 (called).
- **TDD discipline:** Each new module gets a failing test first, then the minimal implementation, then a passing test, then commit.
- **Frequent commits:** 15 commits across the plan, one logical change per commit.
