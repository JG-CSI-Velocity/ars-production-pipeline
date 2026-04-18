"""Tests for html_review.model -- jinja2 context dataclasses."""

from pathlib import Path

from html_review.model import (
    ClientMeta,
    AnalysisBlock,
    SectionRender,
    TableRender,
)


def test_client_meta_fields():
    c = ClientMeta(
        id="1615",
        display_name="Cape & Coast Bank",
        month="2026-04",
        month_display="April 2026",
        run_date="2026-04-17",
    )
    assert c.id == "1615"
    assert c.month_display == "April 2026"


def test_table_render_holds_rows_and_columns():
    t = TableRender(
        sheet_name="Cohort",
        columns=["segment", "flagged_pct"],
        rows=[["New", "22.0"], ["Tenured", "38.5"]],
    )
    assert t.columns == ["segment", "flagged_pct"]
    assert len(t.rows) == 2


def test_analysis_block_minimal():
    b = AnalysisBlock(
        id="attrition_01",
        title="Headline.",
        chart_src="assets/chart.png",
        tables=[],
        notes="",
    )
    assert b.id == "attrition_01"
    assert b.tables == []


def test_section_render_holds_blocks():
    s = SectionRender(
        id="attrition",
        title="Attrition",
        eyebrow="Section 2 of 9",
        lede="Churn signals and recovery.",
        blocks=[],
    )
    assert s.id == "attrition"
    assert s.blocks == []
