"""Snapshot the numeric outputs of one completed pipeline run.

A snapshot is engine-agnostic: it reads only the run's artifacts
(``run_report.json``, ``*_analysis.xlsx``, ``charts/**/*.figdata.json``), so
the same code captures a legacy-engine golden and a v3-engine candidate.
Comparison happens between two snapshots (see compare.py) -- the harness
never needs to import either engine.

Snapshots live under ``<local-cache>/golden/<client>/<month>/<product>/<label>/``
on the machine that ran the pipeline. Real-client snapshots are NEVER
committed to git.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ars_engine.core.config import local_cache_root

from ars_parity.normalize import normalize_workbook


@dataclass
class RunSnapshot:
    client_id: str
    month: str
    product: str
    label: str  # "golden" | "candidate"
    # slide_id -> {module_id, title, success, has_chart, has_excel}
    slides: dict[str, dict[str, Any]] = field(default_factory=dict)
    # sheet name -> normalized table
    sheets: dict[str, dict[str, Any]] = field(default_factory=dict)
    # chart stem (e.g. "TXN-MERCH-03_merchant_01") -> figure data dict
    figures: dict[str, dict[str, Any]] = field(default_factory=dict)


def snapshot_root(client_id: str, month: str, product: str, label: str) -> Path:
    return local_cache_root() / "golden" / client_id / month / product / label


def _find_one(run_dir: Path, pattern: str) -> Path | None:
    matches = sorted(run_dir.glob(pattern))
    return matches[0] if matches else None


def capture_run(
    run_dir: Path | str,
    client_id: str,
    month: str,
    product: str = "ars",
    label: str = "golden",
) -> RunSnapshot:
    """Read one run's artifacts into a RunSnapshot."""
    run_dir = Path(run_dir)
    suffix = "_txn" if product == "txn" else ""
    snap = RunSnapshot(client_id=client_id, month=month, product=product, label=label)

    report_path = _find_one(run_dir, f"{client_id}_{month}{suffix}_run_report.json")
    if report_path:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        for s in payload.get("slides", []):
            sid = s.get("slide_id", "")
            if sid:
                snap.slides[sid] = {
                    "module_id": s.get("module_id", ""),
                    "title": s.get("title", ""),
                    "success": bool(s.get("success")),
                    "has_chart": bool(s.get("has_chart")),
                    "has_excel": bool(s.get("has_excel")),
                }

    xlsx_path = _find_one(run_dir, f"{client_id}_{month}{suffix}_analysis.xlsx")
    if xlsx_path:
        snap.sheets = normalize_workbook(xlsx_path)

    for fd in sorted(run_dir.glob("charts/**/*.figdata.json")):
        stem = fd.name[: -len(".figdata.json")]
        try:
            snap.figures[stem] = json.loads(fd.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

    return snap


def save_snapshot(snap: RunSnapshot, dest: Path | None = None) -> Path:
    """Persist a snapshot; returns its directory."""
    dest = dest or snapshot_root(snap.client_id, snap.month, snap.product, snap.label)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "slides.json").write_text(json.dumps(snap.slides, indent=1), encoding="utf-8")
    (dest / "sheets.json").write_text(json.dumps(snap.sheets), encoding="utf-8")
    (dest / "figures.json").write_text(json.dumps(snap.figures), encoding="utf-8")
    (dest / "meta.json").write_text(
        json.dumps(
            {
                "client_id": snap.client_id,
                "month": snap.month,
                "product": snap.product,
                "label": snap.label,
                "slides": len(snap.slides),
                "sheets": len(snap.sheets),
                "figures": len(snap.figures),
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    return dest


def load_snapshot(src: Path) -> RunSnapshot:
    src = Path(src)
    meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    snap = RunSnapshot(
        client_id=meta["client_id"],
        month=meta["month"],
        product=meta["product"],
        label=meta["label"],
    )
    snap.slides = json.loads((src / "slides.json").read_text(encoding="utf-8"))
    snap.sheets = json.loads((src / "sheets.json").read_text(encoding="utf-8"))
    snap.figures = json.loads((src / "figures.json").read_text(encoding="utf-8"))
    return snap
