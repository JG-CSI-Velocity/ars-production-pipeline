"""Step: Filter ctx.all_slides per deck manifest before deck assembly.

Three modes:
  - full           (default) -- no filter, current behavior
  - client         -- emit only slides referenced in docs/deck/slide_manifest.json
  - supplementary  -- emit every slide NOT referenced in the manifest (inverse)

Wired into pipeline/steps/generate.step_generate as the first action so the
Excel and PowerPoint deliverables both reflect the filtered view.

V1 implementation is section-level: a manifest entry like
``competition/29_wallet_share.py`` keeps ALL slides whose slide_id matches
``TXN-competition-*``. Per-script granularity requires tracking the source
script in AnalysisResult (deferred -- see docs/deck/WORK_IN_PROGRESS.md).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loguru import logger


# Resolved at import time so a missing manifest doesn't crash the pipeline.
_MANIFEST_CACHE: dict[str, Any] | None = None


def _manifest_path() -> Path:
    """Repo-root-relative manifest path. Returns even if file missing."""
    return Path(__file__).resolve().parents[4] / "docs" / "deck" / "slide_manifest.json"


def _load_manifest() -> dict[str, Any] | None:
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    path = _manifest_path()
    if not path.exists():
        logger.warning("Deck manifest not found at {p} -- deck-mode filter is a no-op", p=path)
        return None
    try:
        _MANIFEST_CACHE = json.loads(path.read_text())
        return _MANIFEST_CACHE
    except Exception as exc:
        logger.warning("Failed to parse deck manifest: {err} -- filter no-op", err=exc)
        return None


def _allowed_section_ids(manifest: dict[str, Any]) -> set[str]:
    """Extract the set of TXN section names referenced by manifest scripts.

    e.g. "competition/29_wallet_share.py" -> "competition"
         "ICS_cohort/ics-40-exec-summary" -> "ICS_cohort"
    """
    sections: set[str] = set()
    for slide in manifest.get("slides", []):
        for script in slide.get("scripts", []):
            if ":" in script:
                # NEW:executive/foo.py or script:competition/x.py
                _, _, real = script.partition(":")
                script = real
            head, _, _ = script.partition("/")
            if head:
                sections.add(head)
    return sections


def _allowed_module_ids(manifest: dict[str, Any]) -> set[str]:
    """Extract registered module IDs referenced in manifest."""
    mods: set[str] = set()
    for slide in manifest.get("slides", []):
        for mid in slide.get("modules", []):
            mods.add(mid)
    return mods


def _slide_section(slide_id: str) -> str | None:
    """Pull section from slide_id. Examples:
        TXN-competition-01 -> competition
        ARS-dctr.penetration-01 -> dctr.penetration  (rare format)
        anything else -> None
    """
    m = re.match(r"^TXN-([^-]+)-\d+$", slide_id)
    if m:
        return m.group(1)
    return None


def step_apply_deck_manifest(ctx: Any) -> None:
    """Filter ctx.all_slides + ctx.results in place per ctx.deck_mode.

    Reads ctx.deck_mode (str) -- defaults to "full" if absent. Pulls manifest
    from docs/deck/slide_manifest.json. Logs before/after counts.
    """
    mode = getattr(ctx, "deck_mode", None)
    if not mode:
        # Try client_config (where run.py plumbs it in)
        cfg = getattr(ctx, "client_config", None) or {}
        mode = cfg.get("deck_mode", "full")

    if mode == "full":
        return

    manifest = _load_manifest()
    if manifest is None:
        return

    if not hasattr(ctx, "all_slides") or not ctx.all_slides:
        logger.info("deck_filter: ctx.all_slides empty, nothing to filter")
        return

    allowed_sections = _allowed_section_ids(manifest)
    allowed_modules = _allowed_module_ids(manifest)

    # Conditional ICS section: when client mode AND no ICS_cohort output was
    # produced, exclude slides flagged with "conditional": "ics" in manifest.
    # Predicate: any captured slide_id starting with "TXN-ICS_cohort-" or
    # "TXN-ics_acquisition-" indicates ICS data is present.
    has_ics_output = any(
        ("ICS_cohort" in r.slide_id) or ("ics_acquisition" in r.slide_id.lower())
        for r in ctx.all_slides
    )
    if not has_ics_output:
        allowed_sections.discard("ICS_cohort")
        logger.info("deck_filter: no ICS data detected -- ICS slides will be excluded")

    before = len(ctx.all_slides)

    def _is_in_manifest(result) -> bool:
        sec = _slide_section(result.slide_id)
        if sec and sec in allowed_sections:
            return True
        # Module-based slides (ARS modules) -- their slide_id starts with module-specific prefix
        # We approximate by checking if any allowed module id appears in result.title or slide_id
        for mid in allowed_modules:
            short = mid.split(".")[-1]  # e.g. "penetration" from "dctr.penetration"
            if short in result.slide_id.lower() or short in (result.title or "").lower():
                return True
        return False

    if mode == "client":
        keep = [r for r in ctx.all_slides if _is_in_manifest(r)]
    elif mode == "supplementary":
        keep = [r for r in ctx.all_slides if not _is_in_manifest(r)]
    else:
        logger.warning("deck_filter: unknown deck_mode={mode!r}, treating as 'full'", mode=mode)
        return

    ctx.all_slides = keep

    # Also prune ctx.results so Excel/run report only show retained slides
    if hasattr(ctx, "results") and isinstance(ctx.results, dict):
        kept_ids = {r.slide_id for r in keep}
        for mid, results_list in list(ctx.results.items()):
            if isinstance(results_list, list):
                ctx.results[mid] = [r for r in results_list if r.slide_id in kept_ids]

    after = len(ctx.all_slides)
    logger.info(
        "deck_filter mode={mode}: {before} -> {after} slides ({pct:.0f}% retained)",
        mode=mode, before=before, after=after,
        pct=(after / before * 100) if before > 0 else 0,
    )
