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


def _parse_section_file(path: Path) -> dict[str, TemplateFamily]:
    """Parse one section's markdown file into family entries.

    The grammar is intentionally narrow — see this module's docstring for the
    canonical layout. Anything we can't parse is skipped with a WARNING.
    """
    # Implementation lands in Task 3 — for now return empty so the skeleton
    # imports clean and the loader's directory-missing tests pass.
    return {}


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
