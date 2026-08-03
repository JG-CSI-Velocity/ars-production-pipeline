"""The unified section registry must stay in lockstep with what's on disk --
the drift guard the stress-test asked for (app.py already omitted ICS_cohort
and invented a phantom 'ics'; cross_cohort is an unwired orphan)."""

from __future__ import annotations

import re

from ars_analysis.analytics import section_registry as sr

_NUMBERED = re.compile(r"^\d+_.*\.py$")

# Numbered-script folders intentionally NOT selectable sections. txn_setup uses
# dash-numbered scripts (shared data producer, run once) so it isn't matched by
# _NUMBERED anyway. cross_cohort (the former orphan) was deleted in Phase 3.
# If a NEW underscore-numbered folder appears unregistered, that's drift and
# this test fails so it gets a home.
_KNOWN_NON_SECTIONS: set[str] = set()


def test_every_registered_section_has_a_folder():
    for s in sr.all_sections():
        assert s.path.is_dir(), f"{s.section_id} -> missing folder analytics/{s.folder}"


def test_section_ids_are_unique_and_namespaced():
    ids = [s.section_id for s in sr.all_sections()]
    assert len(ids) == len(set(ids))
    assert all(s.section_id.startswith(("ars.", "txn.")) for s in sr.all_sections())


def test_for_product_partitions():
    ars = {s.section_id for s in sr.for_product("ars")}
    txn = {s.section_id for s in sr.for_product("txn")}
    assert ars and txn and not (ars & txn)
    assert {s.section_id for s in sr.for_product("combined")} == ars | txn


def test_no_unregistered_txn_shaped_folders():
    """Every folder of numbered TXN-style scripts is either a registered TXN
    section or a known non-section -- nothing silently unwired."""
    registered_folders = {s.folder for s in sr.txn_sections()}
    analytics_dir = sr._ANALYTICS
    orphans = []
    for folder in analytics_dir.iterdir():
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        has_numbered = any(_NUMBERED.match(p.name) for p in folder.glob("*.py"))
        if not has_numbered:
            continue
        if folder.name in registered_folders or folder.name in _KNOWN_NON_SECTIONS:
            continue
        orphans.append(folder.name)
    assert not orphans, f"Unregistered numbered-script folders (drift): {orphans}"


def test_ics_cohort_present_and_no_phantom_ics():
    ids = {s.section_id for s in sr.all_sections()}
    assert "txn.ICS_cohort" in ids            # app.py module_counts had omitted it
    assert "txn.ics" not in ids               # the phantom folder never existed
    assert not (sr._ANALYTICS / "ics").exists()
