"""Integration smoke test for the narrative rebuild.

Verifies:
  * Every narrative section is in the registry in the right order.
  * Absorb targets resolve to registered sections.
  * Persona module is importable and returns 15 slide IDs.
  * Every registered placeholder renders to a non-empty fake value.
  * No section key collides.
"""

from __future__ import annotations

from placeholders import PLACEHOLDERS, render
from persona_module import PERSONA_MODULES, build_persona_appendix
from sections import SECTION_REGISTRY


NARRATIVE_KEYS = [
    "open",
    "truth",
    "diagnosis_engagement",
    "diagnosis_targeting",
    "diagnosis_ecosystem",
    "persona_bridge",
    "opportunity",
    "plan",
]


def test_narrative_sections_lead_the_registry():
    keys = [s.key for s in SECTION_REGISTRY]
    assert keys[: len(NARRATIVE_KEYS)] == NARRATIVE_KEYS


def test_every_absorb_target_is_a_registered_section():
    registered = {s.key for s in SECTION_REGISTRY}
    for section in SECTION_REGISTRY:
        for donor in section.absorb_ids.values():
            assert donor in registered, (
                f"{section.key} absorbs from {donor!r} which is not registered"
            )


def test_persona_module_returns_fifteen_slides():
    assert len(build_persona_appendix()) == 15
    assert {m.key for m in PERSONA_MODULES} == {"nonuser", "climber", "decliner"}


def test_every_placeholder_has_non_empty_fake_value():
    for key, p in PLACEHOLDERS.items():
        assert p.fake_value, f"{key} has empty fake_value"


def test_render_produces_plain_strings_for_mixed_input():
    sample = (
        "{{CLIENT_NAME}} has {{NOTEBOOK_PENETRATION}} customer-level "
        "debit penetration compared to {{PIPELINE_DCTR}} account-level DCTR."
    )
    out = render(sample)
    for token in ("{{CLIENT_NAME}}", "{{NOTEBOOK_PENETRATION}}", "{{PIPELINE_DCTR}}"):
        assert token not in out


def test_no_section_key_collision():
    keys = [s.key for s in SECTION_REGISTRY]
    assert len(keys) == len(set(keys))
