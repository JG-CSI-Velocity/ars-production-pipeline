"""Verify SECTION_REGISTRY reflects the narrative order."""

from __future__ import annotations

from sections import SECTION_REGISTRY


def test_narrative_sections_lead_the_registry():
    keys = [s.key for s in SECTION_REGISTRY]
    expected_prefix = [
        "open",
        "truth",
        "diagnosis_engagement",
        "diagnosis_targeting",
        "diagnosis_ecosystem",
        "persona_bridge",
        "opportunity",
        "plan",
    ]
    assert keys[: len(expected_prefix)] == expected_prefix


def test_topic_sections_remain_in_registry_as_appendix_providers():
    keys = {s.key for s in SECTION_REGISTRY}
    for topic in ("overview", "dctr", "rege", "attrition", "mailer",
                  "transaction", "ics", "value", "insights"):
        assert topic in keys, f"{topic} missing -- its slides need to reach appendix"


def test_registry_has_no_duplicates():
    keys = [s.key for s in SECTION_REGISTRY]
    assert len(keys) == len(set(keys))
