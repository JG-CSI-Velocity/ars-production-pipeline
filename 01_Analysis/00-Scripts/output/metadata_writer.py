"""Run metadata writer (Phase T3.3 / issue #158).

Emits ``[client]_[month]_meta.json`` per run. Audit trail capturing
timestamps, slide counts, sections, drops, quality-gate result, and the
list of files generated.

Coexists with the existing ``pipeline/manifest.py`` JSON. The two have
different audiences:
  * ``pipeline/manifest.py`` records *step-level* execution status
    (which pipeline step ran, how long, whether it errored).
  * This module records *deliverable-level* output (what was produced
    for this client/month, was it any good).

Both ship in the run output directory; the operator can read either
one without needing the other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MetadataResult:
    path: Path
    payload: dict


class MetadataWriter:

    SCHEMA_VERSION = "1.0"

    @classmethod
    def write(
        cls,
        ctx,
        out_path: Path,
        *,
        quality_report=None,
        files_generated: list[Path] | None = None,
        elapsed_sec: float | None = None,
    ) -> MetadataResult | None:
        """Build and persist the metadata JSON. Returns None on failure.

        Pipeline integration: invoked by ``pipeline/steps/generate.py``
        after the deck + Excel + quality report are saved, so all five
        artifacts can be listed.
        """
        try:
            payload = cls._build(ctx, quality_report, files_generated, elapsed_sec)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return MetadataResult(path=out_path, payload=payload)
        except (OSError, ValueError, TypeError) as exc:
            from loguru import logger
            logger.warning("MetadataWriter failed: {err}", err=exc)
            print(f"  MetadataWriter failed: {exc}")
            return None

    # -----------------------------------------------------------------
    # Payload assembly
    # -----------------------------------------------------------------

    @classmethod
    def _build(cls, ctx, quality_report, files_generated, elapsed_sec) -> dict:
        client = getattr(ctx, "client", None)
        slides = list(getattr(ctx, "all_slides", []) or [])
        dropped = list(getattr(ctx, "dropped_slides", None) or [])

        return {
            "schema_version": cls.SCHEMA_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "elapsed_sec": elapsed_sec,
            "client": {
                "client_id": getattr(client, "client_id", "") or "",
                "client_name": getattr(client, "client_name", "") or "",
                "csm": getattr(client, "csm", "") or getattr(ctx, "csm", "") or "",
            },
            "run": {
                "month": getattr(client, "month", "") or "",
                "product_mode": (getattr(ctx, "product", "") or "ars").lower(),
                "section_filter_prefixes": list(getattr(ctx, "section_filter_prefixes", []) or []),
            },
            "modules": _module_summary(ctx),
            "slides": _slide_summary(slides, dropped),
            "sections": _section_summary(slides),
            "drops": [
                {
                    "slide_id": d.get("slide_id", ""),
                    "reason": d.get("reason", ""),
                    "detail": d.get("detail", "")[:240],
                }
                for d in dropped
            ],
            "quality": quality_report.summary() if quality_report else None,
            "files_generated": [str(p) for p in (files_generated or [])],
        }


# ---------------------------------------------------------------------------
# Summarizers
# ---------------------------------------------------------------------------


def _module_summary(ctx) -> dict:
    results = getattr(ctx, "results", {}) or {}
    return {
        "modules_included": sorted(k for k in results.keys() if not k.startswith("_")),
        "module_count": sum(1 for k in results.keys() if not k.startswith("_")),
    }


def _slide_summary(slides, dropped) -> dict:
    by_type: dict[str, int] = {}
    for s in slides:
        by_type[getattr(s, "slide_type", "unknown")] = by_type.get(getattr(s, "slide_type", "unknown"), 0) + 1
    return {
        "main_count": sum(1 for s in slides if getattr(s, "slide_type", "") != "section"),
        "section_dividers": sum(1 for s in slides if getattr(s, "slide_type", "") == "section"),
        "dropped_count": len(dropped),
        "total_count": len(slides),
        "by_type": dict(sorted(by_type.items())),
    }


def _section_summary(slides) -> dict:
    counts: dict[str, int] = {}
    for s in slides:
        key = getattr(s, "section_key", None) or ""
        counts[key] = counts.get(key, 0) + 1
    return {
        "sections_present": sorted(k for k in counts.keys() if k),
        "per_section_count": dict(sorted(counts.items())),
    }
