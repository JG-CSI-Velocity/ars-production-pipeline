"""Unified section registry -- one canonical enumeration of the analytics
"sections" an operator can select and run.

Today the section list lives in three drifting places: the ARS class registry
(`registry.MODULE_ORDER` prefixes), the TXN folder registry
(`txn_wrapper.TXN_SECTIONS`), and hardcoded lists in `05_UI/app.py`
(`module_counts`, which already omits `ICS_cohort` and invents a phantom
`ics`). This module is the single source of truth the closed-loop module runner
builds on -- ARS sections and TXN sections behind one canonical `section_id`
namespace (`ars.<section>` / `txn.<folder>`).

Thin by design: it enumerates and locates sections; the per-section execution
contract (requires_frames / analyze / scoped deck) lands on top of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_ANALYTICS = Path(__file__).resolve().parent


@dataclass(frozen=True)
class SectionInfo:
    """One selectable analytics section."""

    section_id: str                    # canonical: "ars.dctr" / "txn.merchant"
    product: str                       # "ars" | "txn"
    display_name: str
    folder: str                        # analytics/<folder>
    slide_code: str = ""               # TXN slide-id prefix -> TXN-<code>-NN
    module_ids: tuple[str, ...] = ()   # ARS: constituent registry module ids

    @property
    def path(self) -> Path:
        return _ANALYTICS / self.folder


def ars_sections() -> list[SectionInfo]:
    """The 7 ARS sections, derived from the registry's module ordering."""
    from ars_analysis.analytics.registry import MODULE_ORDER

    order: list[str] = []
    groups: dict[str, list[str]] = {}
    for mid in MODULE_ORDER:
        sect = mid.split(".", 1)[0]
        if sect not in groups:
            groups[sect] = []
            order.append(sect)
        groups[sect].append(mid)
    return [
        SectionInfo(
            section_id=f"ars.{s}",
            product="ars",
            display_name=s.replace("_", " ").title(),
            folder=s,
            module_ids=tuple(groups[s]),
        )
        for s in order
    ]


def txn_sections() -> list[SectionInfo]:
    """The TXN sections, from TXN_SECTIONS, in execution order."""
    from ars_analysis.analytics.txn_wrapper import TXN_SECTIONS

    return [
        SectionInfo(
            section_id=f"txn.{name}",
            product="txn",
            display_name=meta.get("display", name.replace("_", " ").title()),
            folder=name,
            slide_code=meta.get("code", ""),
        )
        for name, meta in sorted(
            TXN_SECTIONS.items(), key=lambda kv: kv[1].get("order", 500)
        )
    ]


def all_sections() -> list[SectionInfo]:
    return ars_sections() + txn_sections()


def get_section(section_id: str) -> SectionInfo:
    for s in all_sections():
        if s.section_id == section_id:
            return s
    raise KeyError(f"Unknown section_id: {section_id!r}")


def for_product(product: str) -> list[SectionInfo]:
    if product == "combined":
        return all_sections()
    return [s for s in all_sections() if s.product == product]
