"""html_review builder: renders AnalysisResult list -> self-contained HTML file.

Usage (library):
    from html_review.builder import build_html
    from html_review.model import ClientMeta
    build_html(results, client, out_dir, embed_images=True)

Usage (CLI):
    python -m html_review.builder <pickled_results.pkl> <client.json> <out_dir>
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable, Protocol

# Enable absolute imports under 02_Presentations/
_THIS = Path(__file__).parent
_PARENT = _THIS.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from jinja2 import Environment, FileSystemLoader, select_autoescape

from html_review.model import (
    AnalysisBlock,
    ClientMeta,
    SectionRender,
    TableRender,
)


SECTION_ORDER = [
    "overview", "dctr", "rege", "attrition", "value",
    "mailer", "transaction", "ics", "insights",
]

SECTION_TITLES = {
    "overview": "Overview",
    "dctr": "DCTR",
    "rege": "Reg E",
    "attrition": "Attrition",
    "value": "Value",
    "mailer": "ARS Mailer Campaign",
    "transaction": "Transaction",
    "ics": "ICS",
    "insights": "Insights",
}

SECTION_LEDES = {
    "overview": "Portfolio-level KPIs, segments, and the top-line story.",
    "dctr": "Debit card transaction rate and activation trajectory.",
    "rege": "Reg E opt-in trends and overdraft revenue exposure.",
    "attrition": "Churn signals, at-risk scoring, and recovery outcomes.",
    "value": "Per-account value and revenue attribution.",
    "mailer": "ARS campaign reach, response, and lift by cohort.",
    "transaction": "PIN vs signature, merchant and MCC patterns.",
    "ics": "ICS acquisition channels and performance.",
    "insights": "Executive takeaways and next-best-actions.",
}


class AnalysisResultLike(Protocol):
    """Structural type for an AnalysisResult. Builder reads attributes only."""
    slide_id: str
    title: str
    section: str
    chart_path: Path | None
    excel_data: dict[str, Any] | None
    notes: str


def _encode_png(path: Path) -> str:
    """Return a data URI for the PNG at `path`."""
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _df_to_table_render(sheet_name: str, df) -> TableRender:
    """Convert a pandas DataFrame to a TableRender."""
    columns = [str(c) for c in df.columns]
    rows = [[str(v) for v in row] for row in df.itertuples(index=False, name=None)]
    return TableRender(sheet_name=sheet_name, columns=columns, rows=rows)


def _build_block(
    result: AnalysisResultLike,
    out_dir: Path,
    embed_images: bool,
) -> AnalysisBlock:
    """Convert one AnalysisResult into an AnalysisBlock for the template."""
    chart_src: str | None = None
    if result.chart_path is not None and Path(result.chart_path).exists():
        if embed_images:
            chart_src = _encode_png(Path(result.chart_path))
        else:
            assets = out_dir / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            dest_name = f"{result.slide_id}.png"
            dest = assets / dest_name
            shutil.copy(result.chart_path, dest)
            chart_src = f"assets/{dest_name}"

    tables: list[TableRender] = []
    if result.excel_data:
        for sheet_name, df in result.excel_data.items():
            tables.append(_df_to_table_render(sheet_name, df))

    return AnalysisBlock(
        id=result.slide_id,
        title=result.title,
        chart_src=chart_src,
        tables=tables,
        notes=result.notes or "",
    )


def _group_by_section(
    results: Iterable[AnalysisResultLike],
    out_dir: Path,
    embed_images: bool,
) -> list[SectionRender]:
    """Build the section render list in canonical order."""
    by_section: dict[str, list[AnalysisBlock]] = {s: [] for s in SECTION_ORDER}
    unknown: dict[str, list[AnalysisBlock]] = {}

    for r in results:
        block = _build_block(r, out_dir, embed_images)
        key = r.section
        if key in by_section:
            by_section[key].append(block)
        else:
            unknown.setdefault(key, []).append(block)

    sections: list[SectionRender] = []
    total = len([s for s in SECTION_ORDER if by_section[s]]) + len(unknown)
    i = 0
    for key in SECTION_ORDER:
        if not by_section[key]:
            continue
        i += 1
        sections.append(SectionRender(
            id=key,
            title=SECTION_TITLES[key],
            eyebrow=f"Section {i} of {total}",
            lede=SECTION_LEDES[key],
            blocks=by_section[key],
        ))
    for key, blocks in unknown.items():
        i += 1
        sections.append(SectionRender(
            id=key, title=key.title(),
            eyebrow=f"Section {i} of {total}",
            lede="", blocks=blocks,
        ))
    return sections


def _load_text(rel_path: str) -> str:
    return (_THIS / rel_path).read_text()


def build_html(
    results: list[AnalysisResultLike],
    client: ClientMeta,
    out_dir: Path,
    embed_images: bool = True,
) -> Path:
    """Render the HTML review file. Returns path to index.html."""
    out_dir.mkdir(parents=True, exist_ok=True)

    sections = _group_by_section(results, out_dir, embed_images)

    env = Environment(
        loader=FileSystemLoader(str(_THIS / "templates")),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("index.html")

    html = template.render(
        client=client,
        sections=sections,
        styles_css=_load_text("static/styles.css"),
        print_css=_load_text("templates/print.css"),
        app_js=_load_text("static/app.js"),
        print_js=_load_text("static/print.js"),
    )

    out_path = out_dir / "index.html"
    out_path.write_text(html)
    return out_path


def _cli_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="html_review.builder",
        description="Render AnalysisResult list -> self-contained HTML review file.",
    )
    p.add_argument("results_pkl", type=Path, help="Pickled list of AnalysisResult")
    p.add_argument("client_json", type=Path, help="JSON with id/display_name/month/month_display/run_date")
    p.add_argument("out_dir", type=Path, help="Output directory")
    p.add_argument("--no-embed-images", action="store_true", help="Copy PNGs to assets/ instead of inlining")
    args = p.parse_args(argv)

    import pickle
    with args.results_pkl.open("rb") as f:
        results = pickle.load(f)
    client = ClientMeta(**json.loads(args.client_json.read_text()))
    out_path = build_html(results, client, args.out_dir, embed_images=not args.no_embed_images)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
