"""The uniform Module contract.

Every selectable analytics unit -- ARS section or TXN section, leaf or
aggregator -- is presented through one `Module` interface so the runner, the
UI, and tests treat them identically. This is the uniform layer of the module
rewrite: the individual sections keep their internals, but their *contract*
(identity, declared dependencies, leaf-ness, how to run, how to validate) is now
uniform and machine-checkable.

Dependencies are sourced from the static dependency graph
(analytics.section_deps) rather than hand-declared, so they can't drift from the
code. Aggregators (executive, insights) naturally surface a non-empty
`requires_modules`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ars_analysis.analytics.section_deps import required_names, upstream_sections
from ars_analysis.analytics.section_registry import (
    SectionInfo,
    all_sections,
    get_section,
)


@dataclass(frozen=True)
class Module:
    """Uniform contract over one analytics section."""

    section: SectionInfo

    # --- identity ---
    @property
    def id(self) -> str:
        return self.section.section_id

    @property
    def product(self) -> str:
        return self.section.product

    @property
    def display_name(self) -> str:
        return self.section.display_name

    @property
    def slide_code(self) -> str:
        return self.section.slide_code

    # --- declared dependencies (from the static graph, TXN only) ---
    def requires_modules(self) -> list[str]:
        """Upstream module ids that must run first so this module's cross-section
        reads resolve. Empty for leaves and for ARS sections (which depend on
        overview via the runner, not on the namespace)."""
        if self.product != "txn":
            return []
        return [f"txn.{f}" for f in upstream_sections(self.section.folder)]

    def requires_frames(self) -> list[str]:
        """Cross-section names this module reads (its data contract)."""
        if self.product != "txn":
            return []
        return required_names(self.section.folder)

    @property
    def is_leaf(self) -> bool:
        return not self.requires_modules()

    @property
    def is_aggregator(self) -> bool:
        """A module that consumes several other modules' outputs (executive,
        insights) rather than raw data -- the hardest migrations."""
        return len(self.requires_modules()) >= 4

    # --- behaviour ---
    def run(self, ctx):
        """Run this module end-to-end (format-if-needed handled upstream) and
        build its scoped deck. Delegates to the single closed-loop runner."""
        from ars_analysis.runner import run_module
        return run_module(ctx, self.id)

    def validate_contract(self) -> list[str]:
        """Static contract checks (no data needed). Empty list == well-formed."""
        errors: list[str] = []
        if not self.section.path.is_dir():
            errors.append(f"missing folder analytics/{self.section.folder}")
        if self.product == "txn" and not self.slide_code:
            errors.append("TXN section has no slide_code")
        known = {s.section_id for s in all_sections()}
        for up in self.requires_modules():
            if up not in known:
                errors.append(f"declares unknown upstream {up!r}")
        if self.id in self.requires_modules():
            errors.append("depends on itself")
        return errors


def all_modules() -> list[Module]:
    return [Module(s) for s in all_sections()]


def get_module_spec(section_id: str) -> Module:
    return Module(get_section(section_id))


def for_product(product: str) -> list[Module]:
    from ars_analysis.analytics.section_registry import for_product as _fp
    return [Module(s) for s in _fp(product)]
