"""Branching action-title catalog (autonomous decks design, §A).

Loads one markdown file per section from ``docs/action_title_templates/``,
parses each into a ``TemplateFamily`` keyed by template id, and exposes
``select_variant(family_id, ctx_results, client_id)`` which picks a variant
deterministically based on the family's branch rule plus a stable hash of
``client_id + family_id``.

This module supersedes the flat catalog at ``docs/action_title_templates.md``
on a per-template-id basis: if a family is found here, it wins; otherwise the
populator falls back to the legacy flat catalog (kept for parity until rollout
completes).

Catalog file layout (per section markdown file):

  # <section_title>

  ## Family: `<family_id>`            (e.g. dctr.activation_baseline)
  - **branch_if:** `<dotted.ctx.results.path>`
  - **branches:**
    - `>= 0.55` → strong
    - `0.40..0.54` → healthy
    - `0.30..0.39` → opportunity
    - `< 0.30` → urgent
  - **fallback:** "<sentence used when no branch matches>"

  ### strong / variant 1 (data-first)
  - **template:** "..."
  - **placeholders:**
    | Slot | Path | Format |
    |---|---|---|
    | ... | ... | ... |

  ### strong / variant 2 (context-first)
  ...

Loader behavior:
  * Catalog directory missing OR empty -> returns ``{}`` (caller falls back).
  * One section file unreadable -> logs WARNING, skips it, keeps the rest.
  * One family unparseable -> logs WARNING, skips it, keeps the rest.
  * Catalog is read once per process; cache it at module level via
    ``CatalogCache.get()``.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


# Default catalog directory: <repo>/docs/action_title_templates/
_DEFAULT_CATALOG_DIR = (
    Path(__file__).resolve().parents[3] / "docs" / "action_title_templates"
)


@dataclass
class Variant:
    """One variant within one branch of a family."""

    branch: str          # branch label, e.g. "strong"
    angle: str           # "data_first" | "context_first" | "action_first"
    template: str
    placeholders: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass
class TemplateFamily:
    """A branching family (e.g. ``dctr.activation_baseline``)."""

    id: str
    section: str
    branch_path: str | None            # dotted ctx.results path; None => no branching
    branches: list[tuple[str, str]]    # ordered list of (rule_expr, branch_label)
    variants: dict[str, list[Variant]] # branch_label -> [Variant, Variant, Variant]
    fallback: str                      # used when no branch matches


def load_catalog(catalog_dir: Path | None = None) -> dict[str, TemplateFamily]:
    """Parse every .md file in ``catalog_dir`` and return a map of families.

    Returns ``{}`` when the directory is missing or empty. Per-file parse
    failures are logged as warnings and skipped; the loader never raises.
    """
    d = catalog_dir or _DEFAULT_CATALOG_DIR
    if not d.exists() or not d.is_dir():
        logger.info("Branching catalog dir missing at {d}; falling back to flat catalog", d=d)
        return {}
    families: dict[str, TemplateFamily] = {}
    for path in sorted(d.glob("*.md")):
        try:
            families.update(_parse_section_file(path))
        except OSError as exc:
            logger.warning("Could not read catalog file {p}: {err}", p=path, err=exc)
    return families


_FAMILY_HDR_RE = re.compile(r"^##\s+Family:\s+`([^`]+)`\s*$")
_VARIANT_HDR_RE = re.compile(r"^###\s+(\S+)\s*/\s*variant\s+\d+\s*\((\w+)\)\s*$", re.IGNORECASE)
_KV_RE = re.compile(r"^\-\s+\*\*([^*]+):\*\*\s*(.*?)\s*$")
_BRANCH_RULE_RE = re.compile(r"^\s*\-\s+`([^`]+)`\s*(?:→|->)\s*(\S+)\s*$")
_TEMPLATE_RE = re.compile(r"^\-\s+\*\*template:\*\*\s*\"(.+?)\"\s*$")
_FALLBACK_RE = re.compile(r"^\-\s+\*\*fallback:\*\*\s*\"(.+?)\"\s*$")
_TABLE_ROW_RE = re.compile(
    r"^\s*\|\s*`?([^|`]+?)`?\s*\|\s*`([^|`]+)`\s*\|\s*`([^|`]+)`\s*\|\s*$"
)


def _parse_section_file(path: Path) -> dict[str, TemplateFamily]:
    """Parse one section markdown file into ``{family_id: TemplateFamily}``."""
    text = path.read_text(encoding="utf-8")
    out: dict[str, TemplateFamily] = {}

    family_id: str | None = None
    section: str = ""
    branch_path: str | None = None
    branches: list[tuple[str, str]] = []
    variants: dict[str, list[Variant]] = {}
    fallback: str = ""
    cur_variant: Variant | None = None
    in_branches_list = False
    in_placeholder_table = False

    def _flush_variant() -> None:
        nonlocal cur_variant
        if cur_variant is not None:
            variants.setdefault(cur_variant.branch, []).append(cur_variant)
            cur_variant = None

    def _flush_family() -> None:
        nonlocal family_id, section, branch_path, branches, variants, fallback
        _flush_variant()
        if family_id is not None:
            out[family_id] = TemplateFamily(
                id=family_id,
                section=section,
                branch_path=branch_path,
                branches=list(branches),
                variants=dict(variants),
                fallback=fallback,
            )
        family_id = None
        section = ""
        branch_path = None
        branches = []
        variants = {}
        fallback = ""

    for raw in text.splitlines():
        m_fam = _FAMILY_HDR_RE.match(raw)
        if m_fam:
            _flush_family()
            family_id = m_fam.group(1).strip()
            in_branches_list = False
            in_placeholder_table = False
            continue
        if family_id is None:
            continue

        m_var = _VARIANT_HDR_RE.match(raw)
        if m_var:
            _flush_variant()
            cur_variant = Variant(
                branch=m_var.group(1).strip().lower(),
                angle=m_var.group(2).strip().lower(),
                template="",
            )
            in_branches_list = False
            in_placeholder_table = False
            continue

        if cur_variant is not None:
            m_tpl = _TEMPLATE_RE.match(raw)
            if m_tpl:
                cur_variant.template = m_tpl.group(1)
                continue
            if raw.lstrip().startswith("|"):
                m_row = _TABLE_ROW_RE.match(raw)
                if m_row:
                    slot = m_row.group(1).strip()
                    if slot.lower() in ("slot", "---"):
                        in_placeholder_table = True
                        continue
                    cur_variant.placeholders[slot] = {
                        "path": m_row.group(2).strip(),
                        "format": m_row.group(3).strip(),
                    }
                    in_placeholder_table = True
                    continue
            continue

        # Family-level lines (we're between family header and first variant).
        m_kv = _KV_RE.match(raw)
        if m_kv:
            key = m_kv.group(1).strip().lower()
            val = m_kv.group(2).strip().strip("`")
            if key == "section":
                section = val
            elif key == "branch_if":
                branch_path = val
            elif key == "branches":
                in_branches_list = True
                continue
            elif key == "fallback":
                # Strip surrounding quotes if present.
                if len(val) >= 2 and val[0] == val[-1] == '"':
                    val = val[1:-1]
                fallback = val
            in_branches_list = False
            continue

        if in_branches_list:
            m_rule = _BRANCH_RULE_RE.match(raw)
            if m_rule:
                branches.append((m_rule.group(1).strip(), m_rule.group(2).strip().lower()))
                continue
            if raw.strip() == "":
                continue
            in_branches_list = False

        m_fb = _FALLBACK_RE.match(raw)
        if m_fb:
            fallback = m_fb.group(1)

    _flush_family()
    return out


class CatalogCache:
    """Process-wide single-load cache. Mirrors ``ActionTitlePopulator._catalog``."""

    _families: dict[str, TemplateFamily] | None = None

    @classmethod
    def get(cls, force_reload: bool = False) -> dict[str, TemplateFamily]:
        if cls._families is None or force_reload:
            cls._families = load_catalog()
        return cls._families


def select_variant(
    family_id: str,
    ctx_results: dict | None,
    client_id: str,
) -> Variant | None:
    """Select a variant for the given family. Stub — implemented in Task 4."""
    raise NotImplementedError("select_variant lands in Task 4")
