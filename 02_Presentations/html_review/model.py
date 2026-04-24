"""Jinja2 context dataclasses for html_review.

Pure data shapes -- no I/O, no logic. builder.py constructs these from
AnalysisResult objects; templates render them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ClientMeta:
    id: str
    display_name: str
    month: str               # "2026-04"
    month_display: str       # "April 2026"
    run_date: str            # "2026-04-17"


@dataclass(frozen=True)
class TableRender:
    sheet_name: str
    columns: list[str]
    rows: list[list[str]]    # already stringified for HTML safety


@dataclass
class AnalysisBlock:
    id: str
    title: str
    chart_src: str | None                    # relative path or data: URI
    tables: list[TableRender] = field(default_factory=list)
    notes: str = ""


@dataclass
class SectionRender:
    id: str                                   # canonical: overview, attrition, etc.
    title: str                                # Display: "Attrition"
    eyebrow: str                              # "Section 2 of 9"
    lede: str                                 # one-paragraph section intro
    blocks: list[AnalysisBlock] = field(default_factory=list)
