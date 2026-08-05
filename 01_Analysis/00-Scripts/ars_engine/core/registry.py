"""Section contract + registry for the v3 engine.

Replaces three legacy mechanisms:
- ``analytics/registry.py`` (@register + MODULE_ORDER for ARS class modules)
- ``analytics/txn_wrapper.py::TXN_SECTIONS`` (exec()-folder metadata)
- ``analytics/section_deps.py`` (AST inference of cross-script variable deps
  -- deps are now *declared* on the Section class, so static analysis of a
  shared exec namespace is no longer needed)

Section ids keep the legacy unified namespace ("ars.dctr" / "txn.merchant")
so engine_flags, the UI section picker, and parity status files use one
vocabulary across both engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ars_engine.core.context import PipelineContext
from ars_engine.core.result import SlideSpec


@dataclass(frozen=True)
class SectionMeta:
    """Registration metadata for one section."""

    section_id: str                    # canonical: "ars.dctr" / "txn.merchant"
    display_name: str
    slide_code: str = ""               # TXN slide-id prefix -> TXN-<CODE>-NN
    execution_order: int = 500         # lower runs earlier
    requires_frames: tuple[str, ...] = ()   # FrameCatalog keys this section reads
    after: tuple[str, ...] = ()        # section_ids that must run first


class Section(ABC):
    """One analytics section: consumes catalog frames, emits SlideSpecs.

    Contract rules:
    - Read data ONLY through the frames passed in (and ctx.subsets for ODD
      layers); never reach into globals or other sections' internals.
    - Cross-section values flow through ctx.results[...].insights, gated by
      the declared `after` ordering.
    - Every rate/ratio/share result must carry a denominator stamp
      (primitives.denominators.rate() does this automatically).
    """

    meta: SectionMeta

    @abstractmethod
    def build(self, ctx: PipelineContext, frames: dict) -> list[SlideSpec]:
        """Run all analyses for this section. Return ordered slide specs."""

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Check prerequisites; return error messages (empty = OK).

        Frame availability is checked centrally by the runner against
        meta.requires_frames; override for section-specific checks
        (e.g. required ODD columns).
        """
        return []


_REGISTRY: dict[str, type[Section]] = {}
_META: dict[str, SectionMeta] = {}


def register(meta: SectionMeta):
    """Class decorator: register a Section implementation under its id."""

    def deco(cls: type[Section]) -> type[Section]:
        if meta.section_id in _REGISTRY:
            raise ValueError(f"Duplicate section_id: {meta.section_id}")
        cls.meta = meta
        _REGISTRY[meta.section_id] = cls
        _META[meta.section_id] = meta
        return cls

    return deco


def get_section(section_id: str) -> type[Section]:
    _load_all()
    if section_id not in _REGISTRY:
        raise KeyError(f"Unknown section_id: {section_id!r}")
    return _REGISTRY[section_id]


def iter_sections() -> list[type[Section]]:
    """All registered sections in execution order (topologically valid:
    execution_order is the primary key; declared `after` deps are asserted)."""
    _load_all()
    ordered = sorted(_REGISTRY.values(), key=lambda c: (c.meta.execution_order, c.meta.section_id))
    seen: set[str] = set()
    for cls in ordered:
        for dep in cls.meta.after:
            if dep in _REGISTRY and dep not in seen:
                raise ValueError(
                    f"{cls.meta.section_id} declares after={dep!r} but runs first; "
                    "fix execution_order"
                )
        seen.add(cls.meta.section_id)
    return ordered


_loaded = False


def _load_all() -> None:
    """Import ars_engine.sections so @register decorators fire."""
    global _loaded
    if _loaded:
        return
    import ars_engine.sections  # noqa: F401  (import side effect: registration)

    _loaded = True
