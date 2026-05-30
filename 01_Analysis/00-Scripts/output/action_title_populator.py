"""Action-title populator (Phase T2.2 / issue #151).

Loads the catalog from ``docs/action_title_templates.md`` and renders a
populated action title for a slide given the slide's template id and the
shared ``ctx.results`` dict.

Why a separate module
=====================
``output/headlines.py`` was the right thing while the per-section
generators were being written (b0ff9d6 / fd7119b) but a function-per-
slide model doesn't scale to the 28-template catalog without
duplication. The populator collapses every action title into a single
parsing + formatting pipeline driven by the markdown catalog.

Contract
========
``populate(template_id, slide_id, ctx, ctx_results, fallback_title)``
returns a finished title string. The flow is:

  1. Look up the template block by ``template_id``.
  2. For each ``{placeholder}`` in the template, walk the dot-notation
     path against ``ctx_results`` (with an extension for ``ctx.client.*``
     which reads from the ``PipelineContext.client`` dataclass).
  3. Apply the format hint from the placeholder table.
  4. Substitute. If any placeholder resolves to ``None`` or NaN, fall
     back to the block's ``fallback`` sentence; if even that fails,
     return ``fallback_title`` (typically the analytics module's
     default slide title).

Nothing raises. The populator's invariant is: a slide always gets a
title, even if it's the boring fallback.

Wiring
======
``deck_builder._result_to_slide`` looks up the slide's template id via
``docs/slide_specs/<section>.md`` (T2.5). When the spec file or mapping
is missing, ``populate`` is skipped and the legacy ``headlines.py``
generators handle the slide -- so this rollout is non-breaking.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger


# Default catalog location: <repo>/docs/action_title_templates.md
_CATALOG_PATH = Path(__file__).resolve().parents[3] / "docs" / "action_title_templates.md"

# Public alias so callers don't import the private path constant.
DEFAULT_CATALOG_PATH = _CATALOG_PATH


# ---------------------------------------------------------------------------
# Catalog parsing
# ---------------------------------------------------------------------------


@dataclass
class TemplateBlock:
    """One template parsed from the markdown catalog."""

    id: str
    section: str
    template: str
    placeholders: dict[str, dict[str, str]]   # name -> {"path": ..., "format": ...}
    fallback: str


_HEADER_RE = re.compile(r"^###\s+`([^`]+)`\s*$")
_KV_RE = re.compile(r"^\-\s+\*\*([^*]+)\*\*:\s*(.+?)\s*$")
_TEMPLATE_RE = re.compile(r"^\-\s+\*\*template:\*\*\s*\"(.+?)\"\s*$")
_FALLBACK_RE = re.compile(r"^\-\s+\*\*fallback:\*\*\s*\"(.+?)\"\s*$")
_TABLE_ROW_RE = re.compile(r"^\s*\|\s*`?([^|`]+?)`?\s*\|\s*`([^|`]+)`\s*\|\s*`([^|`]+)`\s*\|\s*$")


def load_catalog(path: Path | None = None) -> dict[str, TemplateBlock]:
    """Parse the markdown catalog and return a {template_id: TemplateBlock} map.

    Returns an empty dict if the file is missing or unreadable -- the
    populator is non-fatal by design.
    """
    p = path or _CATALOG_PATH
    if not p.exists():
        logger.warning("action_title_templates.md missing at {p}; populator disabled", p=p)
        return {}
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not read {p}: {err}", p=p, err=exc)
        return {}

    blocks: dict[str, TemplateBlock] = {}
    current_id: str | None = None
    current: dict[str, Any] | None = None
    in_placeholder_table = False

    def _flush() -> None:
        nonlocal current_id, current
        if current_id is None or current is None:
            return
        tpl = current.get("template")
        if not tpl:
            current_id = None
            current = None
            return
        blocks[current_id] = TemplateBlock(
            id=current_id,
            section=current.get("section", ""),
            template=tpl,
            placeholders=current.get("placeholders", {}),
            fallback=current.get("fallback", ""),
        )
        current_id = None
        current = None

    for raw in text.splitlines():
        m_hdr = _HEADER_RE.match(raw)
        if m_hdr:
            _flush()
            current_id = m_hdr.group(1).strip()
            current = {"placeholders": {}}
            in_placeholder_table = False
            continue
        if current is None:
            continue

        m_tpl = _TEMPLATE_RE.match(raw)
        if m_tpl:
            current["template"] = m_tpl.group(1)
            continue
        m_fb = _FALLBACK_RE.match(raw)
        if m_fb:
            current["fallback"] = m_fb.group(1)
            continue
        m_kv = _KV_RE.match(raw)
        if m_kv:
            key = m_kv.group(1).strip().lower()
            val = m_kv.group(2).strip().strip("`")
            if key in ("section",):
                current[key] = val
            in_placeholder_table = False
            continue

        # Placeholder table rows look like: | name | path | format |
        # (may be indented under the `- **placeholders:**` bullet).
        if raw.lstrip().startswith("|"):
            m_row = _TABLE_ROW_RE.match(raw)
            if m_row:
                # Skip the markdown table header row "| Slot | Path | Format |"
                slot = m_row.group(1).strip()
                if slot.lower() in ("slot", "---"):
                    in_placeholder_table = True
                    continue
                current.setdefault("placeholders", {})[slot] = {
                    "path": m_row.group(2).strip(),
                    "format": m_row.group(3).strip(),
                }
                in_placeholder_table = True
                continue
            # Table separator (|---|---|---|) hits here too; just stay in mode.
            if in_placeholder_table:
                continue

    _flush()
    return blocks


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------


def extract_value(path: str, ctx_results: dict, ctx: Any | None = None) -> Any:
    """Walk a dotted ``path`` against ``ctx_results`` (or ``ctx`` for
    ``ctx.client.*`` and ``ctx.subsets.*`` paths). Returns the raw value
    or ``None`` if any segment is missing.
    """
    if not path:
        return None
    parts = path.split(".")
    # Special-case ctx.client.* and ctx.subsets.* etc.
    if parts[0] == "ctx" and ctx is not None:
        obj: Any = ctx
        for seg in parts[1:]:
            obj = getattr(obj, seg, None) if not isinstance(obj, dict) else obj.get(seg)
            if obj is None:
                return None
        return obj
    # ctx.results-rooted (with or without explicit prefix)
    if parts[0] == "ctx_results":
        parts = parts[1:]
    obj = ctx_results
    for seg in parts:
        if isinstance(obj, dict):
            obj = obj.get(seg)
        else:
            obj = getattr(obj, seg, None)
        if obj is None:
            return None
    return obj


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _is_real_number(v: Any) -> bool:
    if not isinstance(v, (int, float)):
        return False
    try:
        return not (math.isnan(v) or math.isinf(v))
    except (TypeError, ValueError):
        return False


def _format_usd(value: float) -> str:
    av = abs(value)
    sign = "−" if value < 0 else ""
    if av >= 1_000_000:
        return f"{sign}${av / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{sign}${av / 1_000:.0f}K"
    return f"{sign}${av:.0f}"


def format_value(value: Any, fmt: str) -> str | None:
    """Apply a format hint. Returns None if ``value`` can't be formatted
    that way -- which signals the caller to use the fallback sentence.
    """
    if value is None:
        return None
    fmt = (fmt or "str").lower()

    if fmt == "str":
        return str(value)

    if fmt in ("pct", "pct1"):
        if not _is_real_number(value):
            return None
        precision = 0 if fmt == "pct" else 1
        return f"{float(value) * 100:.{precision}f}%"

    if fmt == "pp":
        if not _is_real_number(value):
            return None
        return f"{float(value) * 100:.1f} pp"

    if fmt == "pp_signed":
        if not _is_real_number(value):
            return None
        v = float(value) * 100
        sign = "−" if v < 0 else "+"
        return f"{sign}{abs(v):.1f} pp"

    if fmt == "int":
        if not _is_real_number(value):
            return None
        return f"{int(value):,}"

    if fmt == "usd":
        if not _is_real_number(value):
            return None
        return _format_usd(float(value))

    if fmt == "usd_m":
        if not _is_real_number(value):
            return None
        v = float(value)
        sign = "−" if v < 0 else ""
        return f"{sign}${abs(v) / 1_000_000:.1f}M"

    if fmt == "usd_signed":
        if not _is_real_number(value):
            return None
        v = float(value)
        sign = "−" if v < 0 else "+"
        return f"{sign}{_format_usd(abs(v))}"

    # Unknown format: defensively passthrough as string so a typo in the
    # catalog doesn't crash the deck.
    logger.warning("Unknown action-title format hint: {fmt}", fmt=fmt)
    return str(value)


# ---------------------------------------------------------------------------
# Populator
# ---------------------------------------------------------------------------


class ActionTitlePopulator:
    """Singleton-ish populator. Caches the parsed catalog once per process."""

    _catalog: dict[str, TemplateBlock] | None = None

    @classmethod
    def catalog(cls, force_reload: bool = False) -> dict[str, TemplateBlock]:
        if cls._catalog is None or force_reload:
            cls._catalog = load_catalog()
        return cls._catalog

    @classmethod
    def populate(
        cls,
        template_id: str,
        ctx_results: dict | None,
        ctx: Any | None = None,
        fallback_title: str = "",
    ) -> str:
        """Render an action title.

        Order of attempts:
          1. Branching catalog (``output/template_catalog.py``) — chosen by
             variant rules + stable hash of client id.
          2. Flat catalog (``docs/action_title_templates.md``) — legacy.
          3. ``fallback_title``.
        """
        # 1. Branching catalog
        try:
            from ars_analysis.output import template_catalog
            client_id = ""
            if ctx is not None:
                client = getattr(ctx, "client", None)
                client_id = str(getattr(client, "client_id", "") or getattr(client, "client_name", ""))
            variant = template_catalog.select_variant(
                template_id, ctx_results or {}, client_id or "default"
            )
            if variant is not None:
                rendered = cls._render_variant(variant, ctx_results or {}, ctx)
                if rendered is not None:
                    return rendered
                family = template_catalog.CatalogCache.get().get(template_id)
                if family is not None and family.fallback:
                    return family.fallback
        except Exception as exc:
            logger.warning(
                "Branching catalog lookup failed for {tid}: {err}; falling back to flat catalog",
                tid=template_id, err=exc,
            )

        # 2. Flat catalog (legacy path; unchanged from prior behavior)
        catalog = cls.catalog()
        block = catalog.get(template_id)
        if block is None:
            return fallback_title or template_id

        resolved: dict[str, str] = {}
        ok = True
        for name, meta in block.placeholders.items():
            raw = extract_value(meta.get("path", ""), ctx_results or {}, ctx)
            formatted = format_value(raw, meta.get("format", "str"))
            if formatted is None:
                ok = False
                logger.info(
                    "Action title {tid}: missing/invalid value for {{{name}}} (path={path})",
                    tid=template_id, name=name, path=meta.get("path", "?"),
                )
                break
            resolved[name] = formatted

        if ok:
            try:
                return block.template.format(**resolved)
            except (KeyError, IndexError) as exc:
                logger.warning(
                    "Action title {tid}: substitution failed ({err}); using fallback",
                    tid=template_id, err=exc,
                )

        # Fallback sentence -- doesn't need substitutions to be valid.
        if block.fallback:
            try:
                return block.fallback.format(**resolved) if "{" in block.fallback else block.fallback
            except (KeyError, IndexError):
                return block.fallback

        return fallback_title or template_id

    @classmethod
    def _render_variant(cls, variant, ctx_results: dict, ctx: Any | None) -> str | None:
        """Substitute a Variant's placeholders. Returns None if any required slot
        can't be resolved (so the caller can use the family-level fallback)."""
        resolved: dict[str, str] = {}
        for name, meta in variant.placeholders.items():
            raw = extract_value(meta.get("path", ""), ctx_results, ctx)
            formatted = format_value(raw, meta.get("format", "str"))
            if formatted is None:
                return None
            resolved[name] = formatted
        try:
            return variant.template.format(**resolved)
        except (KeyError, IndexError):
            return None

    @classmethod
    def known_template_ids(cls) -> list[str]:
        return sorted(cls.catalog().keys())
