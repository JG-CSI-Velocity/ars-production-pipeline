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


def test_pattern_key_compiles_to_regex(specs_dir):
    """`A13.{month}` should match A13.Jan26 and capture 'Jan26'."""
    pattern, names = ss._compile_pattern_key("A13.{month}")
    assert names == ["month"]
    m = pattern.match("A13.Jan26")
    assert m is not None
    assert m.group("month") == "Jan26"
    # Doesn't bleed across dots
    assert pattern.match("A13.Jan26.Swipes") is None
    assert pattern.match("A14.Jan26") is None


def test_pattern_key_excludes_non_month_tokens(specs_dir):
    """Non-month A13 slides (A13.5, A13.6, A13.Agg) must NOT match A13.{month}.

    Regression: these matched the per-month template, captured month='5'/'Agg',
    failed input resolution, and leaked '{overall_rate:.1f}%' onto the slide.
    """
    pattern, _ = ss._compile_pattern_key("A13.{month}")
    assert pattern.match("A13.Apr26") is not None
    for non_month in ("A13.5", "A13.6", "A13.Agg"):
        assert pattern.match(non_month) is None, non_month


def test_render_spec_drops_unresolved_callout_tokens(specs_dir):
    """A callout whose input can't resolve renders empty, never leaking braces."""
    (specs_dir / "demo.yml").write_text(
        """
DEMO:
  action_title: "Static title"
  inputs:
    overall_rate: ctx.results.missing.insights.rate
  callout:
    hero: "{overall_rate:.1f}%"
    sub: "{total_resp:,} respondents"
"""
    )
    spec = ss.get_spec("demo", "DEMO")
    rendered = ss.render_spec(spec, {}, _Client())
    assert rendered.callout_hero == ""
    assert rendered.callout_sub == ""
    assert "{" not in rendered.callout_hero
    assert any("dropped" in w for w in rendered.render_warnings)


def test_get_spec_resolves_pattern_keyed_template(specs_dir):
    """Pattern-keyed templates render one spec per matching slide_id."""
    (specs_dir / "demo.yml").write_text(
        '''
"A13.{month}":
  layout: TWO_CONTENT
  action_title: "{month_label}: {total_mailed:,} mailed"
  inputs:
    month_label: month
    total_mailed: ctx.results.monthly_summaries.{month}.total_mailed
  denominator_label: Eligible
'''
    )
    spec = ss.get_spec("demo", "A13.Jan26")
    assert spec is not None
    assert spec.slide_id == "A13.Jan26"
    assert (
        spec.inputs["total_mailed"]
        == "ctx.results.monthly_summaries.Jan26.total_mailed"
    )
    assert spec.inputs["month"] == '"Jan26"'


def test_get_spec_pattern_renders_with_ctx_results(specs_dir):
    (specs_dir / "demo.yml").write_text(
        '''
"A13.{month}":
  action_title: "{month}: {total_mailed:,} mailed at {overall_rate:.1f}%"
  inputs:
    month_label: month
    total_mailed: ctx.results.monthly_summaries.{month}.total_mailed
    overall_rate: ctx.results.monthly_summaries.{month}.overall_rate
  denominator_label: Eligible
  callout:
    hero: "{overall_rate:.1f}%"
'''
    )
    spec = ss.get_spec("demo", "A13.Feb26")
    rendered = ss.render_spec(
        spec,
        {
            "monthly_summaries": {
                "Feb26": {"total_mailed": 12345, "overall_rate": 4.2},
                "Jan26": {"total_mailed": 999,   "overall_rate": 9.9},
            }
        },
        _Client(),
    )
    assert rendered.action_title == "Feb26: 12,345 mailed at 4.2%"
    assert rendered.callout_hero == "4.2%"
    assert "999" not in rendered.action_title


def test_get_spec_exact_match_wins_over_pattern(specs_dir):
    """An exact-match key should be preferred over a pattern-match template."""
    (specs_dir / "demo.yml").write_text(
        '''
"A13.{month}":
  action_title: "template title"
  denominator_label: Eligible
A13.Jan26:
  action_title: "exact title"
  denominator_label: Eligible
'''
    )
    spec = ss.get_spec("demo", "A13.Jan26")
    assert spec.action_title == "exact title"
    spec2 = ss.get_spec("demo", "A13.Feb26")
    assert spec2.action_title == "template title"


def test_repo_specs_load_without_error():
    """Every authored spec across all sections must parse and be 4-layer compliant."""
    ss.clear_spec_cache()
    # SLIDE_SPECS_DIR not set -> uses _DEFAULT_SPECS_DIR
    authored_sections = ("dctr", "rege", "overview", "attrition", "value", "insights", "mailer")
    by_section = {s: ss.load_specs(s) for s in authored_sections}
    for section, specs in by_section.items():
        assert len(specs) >= 1, f"{section}.yml should declare at least one slide"

    valid_labels = {"Eligible", "Eligible Personal", "Eligible Business", "Open"}
    for section, specs in by_section.items():
        for spec in specs.values():
            assert spec.denominator_label in valid_labels, (
                f"{section}/{spec.slide_id}: denominator_label "
                f"'{spec.denominator_label}' not in 4-layer law"
            )
