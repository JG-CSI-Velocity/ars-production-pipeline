"""Quick layout preview -- generates test PPTX files per section in seconds.

No data loading, no analysis. Uses dummy content to test template
layouts, fonts, and placeholder positions.

Usage:
    python preview.py                    # all sections, one PPTX each
    python preview.py --section preamble # just the preamble
    python preview.py --section mailer   # just the mailer section
    python preview.py --list             # show available sections
"""

import argparse
import glob
import os
import sys
from pathlib import Path

# Add 00-Scripts to path
sys.path.insert(0, str(Path(__file__).parent / "00-Scripts"))

# Create ars_analysis package alias
import types
_ars_pkg = types.ModuleType("ars_analysis")
_ars_pkg.__path__ = [str(Path(__file__).parent / "00-Scripts")]
sys.modules["ars_analysis"] = _ars_pkg

from output.deck_builder import (
    DeckBuilder,
    SlideContent,
    LAYOUT_TITLE_RPE,
    LAYOUT_SECTION_ALT,
    LAYOUT_CUSTOM,
    LAYOUT_CONTENT,
    LAYOUT_TITLE_DARK,
    LAYOUT_MAIL_SUMMARY,
    LAYOUT_TWO_CONTENT,
)


def _dummy_chart(output_dir: Path, name: str = "dummy_chart.png") -> str:
    """Create a simple placeholder chart image."""
    path = output_dir / name
    if path.exists():
        return str(path)
    try:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(13, 7))
        ax.bar(["Category A", "Category B", "Category C", "Category D"],
               [42, 28, 35, 19], color=["#1B365D", "#0D9488", "#F39C12", "#95A5A6"])
        ax.set_ylabel("Value")
        fig.savefig(path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        return str(path)
    except ImportError:
        return ""


# ---------------------------------------------------------------------------
# Section definitions -- dummy slides for each section
# ---------------------------------------------------------------------------

CLIENT = "FIRST COMMUNITY BANK"
MONTH = "March 2026"
SUB = f"{CLIENT} | {MONTH}"


def _preamble(chart):
    return [
        SlideContent(slide_type="title",
                     title=f"{CLIENT}\nAccount Revenue Solution | {MONTH}",
                     layout_index=LAYOUT_TITLE_RPE),
        SlideContent(slide_type="blank", title="Agenda",
                     layout_index=LAYOUT_CONTENT),
        SlideContent(slide_type="title",
                     title=f"{CLIENT}\nProgram Performance | {MONTH}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="blank", title="Executive Summary",
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="blank",
                     title="Monthly Revenue \u2013 Last 12 Months",
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="blank", title="ARS Lift Matrix",
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="title",
                     title=f"{CLIENT}\nARS Mailer Revisit | {MONTH}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="screenshot",
                     title="ARS Mailer Revisit \u2013 Swipes",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="ARS Mailer Revisit \u2013 Spend",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="title",
                     title=f"Mailer Summaries\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="blank",
                     title=f"All Program Results\n{SUB}",
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="Program Responses to Date",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="blank",
                     title="Data Check Overview\nOur goal is turning non-users and light-users into heavy users",
                     layout_index=LAYOUT_CUSTOM),
    ]


def _mailer(chart):
    return [
        SlideContent(slide_type="section",
                     title=f"Mailer Campaign Performance\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="mailer_summary",
                     title="January 2026 Mailer Summary",
                     images=[chart] if chart else None,
                     kpis={"Mailed": "5,661", "Responded": "383", "Rate": "6.8%"},
                     bullets=[
                         "The January 2026 mailer reached 5,661 accounts with a 6.8% response rate (383 responders). TH-25 led with the highest response rate at 16.2%, while TH-10 contributed the most responders (109). This is a 1.2pp improvement over the prior mailer.",
                         "36%|of Responders were accounts opened fewer than 2 years ago",
                         "27%|of Responders aged 30-45",
                         "32%|of Responders opted into Reg E",
                         "41%|First-time responders",
                     ],
                     layout_index=LAYOUT_MAIL_SUMMARY),
        SlideContent(slide_type="mailer_summary",
                     title="November 2025 Mailer Summary",
                     images=[chart] if chart else None,
                     kpis={"Mailed": "5,430", "Responded": "614", "Rate": "11.3%"},
                     bullets=[
                         "The November 2025 mailer reached 5,430 accounts with an 11.3% response rate (614 responders). TH-15 drove the strongest response at 14.1%. 58% of responders were first-time program participants.",
                         "29%|of Responders were accounts opened fewer than 2 years ago",
                         "31%|of Responders aged 30-45",
                         "28%|of Responders opted into Reg E",
                         "58%|First-time responders",
                     ],
                     layout_index=LAYOUT_MAIL_SUMMARY),
        SlideContent(slide_type="screenshot",
                     title="Jan26 Responder Swipes",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="Jan26 Responder Spend",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
    ]


def _dctr(chart):
    return [
        SlideContent(slide_type="section",
                     title=f"How Active Are Debit Cards?\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="screenshot",
                     title="Debit Card Penetration: 34.2% of eligible accounts actively use their debit card",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="Card usage increased 2.3% over the past 12 months",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="multi_screenshot",
                     title="DCTR Trajectory: Recent Trend & Segments",
                     images=[chart, chart] if chart else None,
                     layout_index=LAYOUT_TWO_CONTENT),
    ]


def _rege(chart):
    return [
        SlideContent(slide_type="section",
                     title=f"Are Members Opting In to Overdraft Protection?\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="screenshot",
                     title="72.4% of accounts are opted in to Reg E",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="Reg E opt-in varies from 58% to 84% across branches",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
    ]


def _attrition(chart):
    return [
        SlideContent(slide_type="section",
                     title=f"Are We Losing Accounts?\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="screenshot_kpi",
                     title="1,245 accounts closed this period -- 3.8% annualized attrition",
                     images=[chart] if chart else None,
                     kpis={"Closed": "1,245", "Rate": "3.8%", "Revenue Lost": "$142K"},
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="Accounts under 2 years old close at 2.1x the rate of established accounts",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
    ]


def _value(chart):
    return [
        SlideContent(slide_type="section",
                     title=f"What Is the Revenue Impact?\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="screenshot",
                     title="ARS program generated an estimated $284K in incremental interchange revenue",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
    ]


def _insights(chart):
    return [
        SlideContent(slide_type="section",
                     title=f"What Should We Do Next?\n{SUB}",
                     layout_index=LAYOUT_SECTION_ALT),
        SlideContent(slide_type="screenshot",
                     title="3 recommended actions to improve program performance",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
        SlideContent(slide_type="screenshot",
                     title="Main Street Branch is the top-performing branch across 5 of 7 metrics",
                     images=[chart] if chart else None,
                     layout_index=LAYOUT_CUSTOM),
    ]


SECTIONS = {
    "preamble": _preamble,
    "mailer": _mailer,
    "dctr": _dctr,
    "rege": _rege,
    "attrition": _attrition,
    "value": _value,
    "insights": _insights,
}


def build_section(section_name, template_path, output_dir, chart):
    """Build a single section preview PPTX."""
    if section_name not in SECTIONS:
        print(f"  Unknown section: {section_name}")
        return
    slides = SECTIONS[section_name](chart)
    output_path = output_dir / f"preview_{section_name}.pptx"
    builder = DeckBuilder(template_path)
    builder.build(slides, str(output_path))
    print(f"  {section_name}: {output_path.name} ({len(slides)} slides)")


def main():
    parser = argparse.ArgumentParser(description="Quick layout preview per section")
    parser.add_argument("--section", type=str, default=None,
                        help="Section to preview (or 'all')")
    parser.add_argument("--list", action="store_true",
                        help="List available sections")
    parser.add_argument("--template", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    if args.list:
        print("Available sections:")
        for name in SECTIONS:
            print(f"  {name}")
        return

    # Find template
    template = args.template
    if not template:
        if os.name == "nt":
            candidates = glob.glob(r"M:\ARS\02_Presentations\*Template*.pptx")
        else:
            candidates = glob.glob("/Volumes/M/ARS/02_Presentations/*Template*.pptx")
        if candidates:
            template = candidates[0]
        else:
            fallback = Path(__file__).parent / "00-Scripts" / "output" / "template" / "2025-CSI-PPT-Template.pptx"
            if fallback.exists():
                template = str(fallback)

    if not template or not Path(template).exists():
        print(f"ERROR: Template not found. Use --template to specify.")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Template: {template}")
    print()

    # Create dummy chart once
    chart = _dummy_chart(output_dir)

    if args.section and args.section != "all":
        build_section(args.section, template, output_dir, chart)
    else:
        for name in SECTIONS:
            build_section(name, template, output_dir, chart)

    print()
    print("Done. Open the PPTX files to check layouts.")


if __name__ == "__main__":
    main()
