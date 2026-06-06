"""Tests for the YAML slide-spec loader and renderer."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from ars_analysis.output import slide_spec as ss


@dataclass
class _Client:
    client_id: str = "1615"
    client_name: str = "AcmeCU"
    month: str = "2026.04"
    csm: str = "James"


@pytest.fixture
def specs_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SLIDE_SPECS_DIR", str(tmp_path))
    ss.clear_spec_cache()
    return tmp_path


def test_load_specs_missing_section_returns_empty(specs_dir):
    assert ss.load_specs("nope") == {}


def test_load_specs_parses_basic_yml(specs_dir):
    (specs_dir / "demo.yml").write_text(
        """
DEMO-1:
  layout: TWO_CONTENT
  components: [A1]
  action_title: "Hello {client_name}"
  denominator_label: Eligible
  inputs:
    rate: ctx.results.demo.insights.rate
  callout:
    hero: "{rate:.0%}"
    sub: "demo rate"
  footer:
    source: "Source: {client_name} ODD"
"""
    )
    specs = ss.load_specs("demo")
    assert "DEMO-1" in specs
    spec = specs["DEMO-1"]
    assert spec.layout == "TWO_CONTENT"
    assert spec.components == ["A1"]
    assert spec.action_title == "Hello {client_name}"
    assert spec.denominator_label == "Eligible"
    assert spec.callout.hero == "{rate:.0%}"
    assert spec.footer.source.startswith("Source:")


def test_get_spec_caches(specs_dir):
    (specs_dir / "x.yml").write_text("X1:\n  action_title: hi\n")
    a = ss.get_spec("x", "X1")
    b = ss.get_spec("x", "X1")
    assert a is b  # cached -- same object


def test_resolve_dotted_walks_nested_dicts():
    results = {"dctr_1": {"insights": {"dctr": 0.31}}}
    assert ss._resolve_dotted("ctx.results.dctr_1.insights.dctr", results) == 0.31
    assert ss._resolve_dotted("dctr_1.insights.dctr", results) == 0.31
    assert ss._resolve_dotted("dctr_1.insights.missing", results) is None


def test_render_spec_fills_action_title_with_ctx_values(specs_dir):
    (specs_dir / "demo.yml").write_text(
        """
DEMO:
  action_title: "DCTR {rate:.0%} for {client_name}"
  inputs:
    rate: ctx.results.dctr_1.insights.dctr
"""
    )
    spec = ss.get_spec("demo", "DEMO")
    rendered = ss.render_spec(
        spec,
        {"dctr_1": {"insights": {"dctr": 0.31}}},
        _Client(),
    )
    assert rendered.action_title == "DCTR 31% for AcmeCU"
    assert rendered.render_warnings == []


def test_render_spec_lenient_on_missing_inputs(specs_dir):
    (specs_dir / "demo.yml").write_text(
        """
DEMO:
  action_title: "Rate is {rate:.0%}"
  inputs:
    rate: ctx.results.missing.insights.rate
"""
    )
    spec = ss.get_spec("demo", "DEMO")
    rendered = ss.render_spec(spec, {}, _Client())
    # Should keep the literal placeholder and surface a warning, NOT raise
    assert "{rate" in rendered.action_title or "{rate:.0%}" in rendered.action_title
    assert any("missing input" in w or "format failed" in w or "resolved to None" in w
               for w in rendered.render_warnings)


def test_render_spec_passes_callout_and_footer_through(specs_dir):
    (specs_dir / "demo.yml").write_text(
        """
DEMO:
  action_title: "Static title"
  denominator_label: Eligible Personal
  callout:
    hero: "$5.2M"
    sub: "uplift"
  footer:
    source: "Source: {client_name} ODD, {month}"
"""
    )
    spec = ss.get_spec("demo", "DEMO")
    rendered = ss.render_spec(spec, {}, _Client())
    assert rendered.callout_hero == "$5.2M"
    assert rendered.callout_sub == "uplift"
    assert "AcmeCU" in rendered.footer_source
    assert "2026.04" in rendered.footer_source
    assert rendered.denominator_label == "Eligible Personal"


def test_repo_specs_load_without_error():
    """The dctr.yml and rege.yml shipped with the repo must parse."""
    ss.clear_spec_cache()
    # SLIDE_SPECS_DIR not set -> uses _DEFAULT_SPECS_DIR
    dctr = ss.load_specs("dctr")
    rege = ss.load_specs("rege")
    assert len(dctr) >= 1, "dctr.yml should declare at least one slide"
    assert len(rege) >= 1, "rege.yml should declare at least one slide"
    # Every spec must declare a 4-layer-compliant denominator_label
    valid_labels = {"Eligible", "Eligible Personal", "Eligible Business", "Open"}
    for spec in list(dctr.values()) + list(rege.values()):
        assert spec.denominator_label in valid_labels, (
            f"{spec.slide_id}: denominator_label '{spec.denominator_label}' "
            f"not in 4-layer law"
        )
