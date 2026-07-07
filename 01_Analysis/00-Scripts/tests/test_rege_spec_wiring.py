"""Regression test for the REGE-MAIN-1 slide-spec wiring.

`rege/status.py` stores `ctx.results["reg_e_1"]` as a FLAT dict
(`opt_in_rate`, `l12m_rate`, `total_base`, ...). The spec previously pointed at
`reg_e_1.insights.opt_in_rate` / `reg_e_2.insights.l12m_opt_in`, an `.insights.`
sub-object and a `reg_e_2` key that the modules never write -- so every input
silently resolved to None and the Reg E hero callout rendered blank on real
client decks. This test loads the REAL `docs/slide_specs/rege.yml` and asserts
REGE-MAIN-1 resolves against the actual flat `reg_e_1` shape.

See docs/EQUATION_DICTIONARY.md Appendix B (B1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from ars_analysis.output import slide_spec as ss


@dataclass
class _Client:
    client_id: str = "1615"
    client_name: str = "AcmeCU"
    month: str = "2026.04"
    csm: str = "James"


# Exactly the shape rege/status.py writes (flat keys, NO `insights` layer).
REG_E_1 = {
    "opt_in_rate": 0.35,
    "l12m_rate": 0.42,
    "total_base": 1200,
    "opted_in": 420,
    "opted_out": 780,
}

# Repo docs/slide_specs from tests/ -> 00-Scripts -> 01_Analysis -> repo root.
REAL_SPECS_DIR = Path(__file__).resolve().parents[3] / "docs" / "slide_specs"


@pytest.fixture
def rege_main_1(monkeypatch):
    monkeypatch.setenv("SLIDE_SPECS_DIR", str(REAL_SPECS_DIR))
    ss.clear_spec_cache()
    spec = ss.get_spec("rege", "REGE-MAIN-1")
    assert spec is not None, "REGE-MAIN-1 missing from docs/slide_specs/rege.yml"
    return spec


def test_rege_main_1_renders_real_opt_in_rate(rege_main_1):
    rendered = ss.render_spec(rege_main_1, {"reg_e_1": REG_E_1}, _Client())
    # opt_in_rate 0.35 -> "35%" (was blank when the spec pointed at .insights.)
    assert rendered.callout_hero == "35%"
    assert "35%" in rendered.action_title
    # overall_total comes from reg_e_1.total_base (1,200), not a phantom key.
    assert "1,200" in rendered.callout_tertiary


def test_rege_main_1_all_callout_fields_render(rege_main_1):
    # render_spec only warns for None inputs referenced in the action_title, so
    # assert the rendered callout text directly: a callout-only input (e.g.
    # overall_total) regressing to a phantom key drops the field (the renderer
    # clears unresolved tokens), which this catches where a warning check would not.
    rendered = ss.render_spec(rege_main_1, {"reg_e_1": REG_E_1}, _Client())
    assert rendered.callout_hero == "35%"
    assert rendered.callout_tertiary, "tertiary callout was dropped (unresolved input)"
    assert "1,200" in rendered.callout_tertiary  # overall_total -> reg_e_1.total_base


def test_rege_main_1_trend_is_l12m_minus_all_time(rege_main_1):
    rendered = ss.render_spec(rege_main_1, {"reg_e_1": REG_E_1}, _Client())
    # trend_pp = (l12m_rate 0.42 - opt_in_rate 0.35) * 100 = +7pp -> "accelerating"
    assert "+7pp" in rendered.action_title
    assert "accelerating" in rendered.action_title


def test_rege_main_1_zero_l12m_opt_in_is_real_not_suppressed(rege_main_1):
    # A genuine 0% L12M opt-in is data, not "missing": trend must read the true
    # collapse, not be masked as flat by a falsy-zero guard.
    results = {"reg_e_1": {**REG_E_1, "l12m_rate": 0.0}}  # 35% all-time -> 0% L12M
    rendered = ss.render_spec(rege_main_1, results, _Client())
    assert "-35pp" in rendered.action_title
    assert "softening" in rendered.action_title
    assert "flat +0pp" not in rendered.action_title


def test_rege_main_1_sub_1pp_move_reads_flat_not_accelerating(rege_main_1):
    # +0.3pp rounds to +0pp; the word must agree with the number (no
    # "accelerating +0pp"). Symmetric dead-band with the softening side.
    results = {"reg_e_1": {**REG_E_1, "opt_in_rate": 0.350, "l12m_rate": 0.353}}
    rendered = ss.render_spec(rege_main_1, results, _Client())
    assert "flat +0pp" in rendered.action_title
    assert "accelerating" not in rendered.action_title
