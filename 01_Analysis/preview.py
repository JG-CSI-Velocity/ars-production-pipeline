"""Quick layout preview -- generates test PPTX per section with ALL slides.

Shows every slide the real pipeline would produce, with dummy charts.
Each slide is labeled with its slide ID so you can map it to the
analytics module that generates it.

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
        ax.set_title("Sample Chart (Placeholder)", fontsize=16)
        fig.savefig(path, dpi=100, bbox_inches="tight")
        plt.close(fig)
        return str(path)
    except ImportError:
        return ""


def _s(slide_id, title, slide_type="screenshot", layout=LAYOUT_CUSTOM, kpis=None, bullets=None):
    """Shorthand to create a SlideContent with slide ID in the title."""
    return {
        "id": slide_id,
        "title": f"[{slide_id}] {title}",
        "clean_title": title,
        "slide_type": slide_type,
        "layout": layout,
        "kpis": kpis,
        "bullets": bullets,
    }


def _build_slides(defs, chart):
    """Convert shorthand defs to SlideContent list."""
    slides = []
    for d in defs:
        sc = SlideContent(
            slide_type=d["slide_type"],
            title=d["title"],
            images=[chart] if chart and d["slide_type"] not in ("title", "section", "blank") else None,
            kpis=d.get("kpis"),
            bullets=d.get("bullets"),
            layout_index=d["layout"],
        )
        slides.append(sc)
    return slides


# ---------------------------------------------------------------------------
CLIENT = "FIRST COMMUNITY BANK"
MONTH = "March 2026"
SUB = f"{CLIENT} | {MONTH}"
# ---------------------------------------------------------------------------


def _preamble():
    return [
        _s("P01", f"{CLIENT}\nAccount Revenue Solution | {MONTH}", "title", LAYOUT_TITLE_RPE),
        _s("P02", "Agenda", "blank", LAYOUT_CONTENT),
        _s("P03", f"{CLIENT}\nProgram Performance | {MONTH}", "title", LAYOUT_SECTION_ALT),
        _s("P04", "Executive Summary", "blank", LAYOUT_CUSTOM),
        _s("P05", "Monthly Revenue \u2013 Last 12 Months", "blank", LAYOUT_CUSTOM),
        _s("P06", "ARS Lift Matrix", "blank", LAYOUT_CUSTOM),
        _s("P07", f"{CLIENT}\nARS Mailer Revisit | {MONTH}", "title", LAYOUT_SECTION_ALT),
        _s("P08", "ARS Mailer Revisit \u2013 Swipes", "screenshot", LAYOUT_CUSTOM),
        _s("P09", "ARS Mailer Revisit \u2013 Spend", "screenshot", LAYOUT_CUSTOM),
        _s("P10", f"Mailer Summaries\n{SUB}", "title", LAYOUT_SECTION_ALT),
        _s("P11", f"All Program Results\n{SUB}", "blank", LAYOUT_CUSTOM),
        _s("P12", "Program Responses to Date", "screenshot", LAYOUT_CUSTOM),
        _s("P13", "Data Check Overview\nOur goal is turning non-users and light-users into heavy users", "blank", LAYOUT_CUSTOM),
    ]


def _dctr():
    """DCTR: 16 penetration slides + 12 A7.x analysis slides.
    MAIN: DCTR-2..16 (skip DCTR-1), A7.4, A7.6a, A7.7, A7.8, A7.10a, A7.11, A7.12
    MERGED: A7.6a+A7.4, A7.7+A7.8, A7.11+A7.12
    APPENDIX: A7.5, A7.6b, A7.9, A7.10b, A7.10c, A7.13, A7.14, A7.15
    """
    return [
        _s("DIV", f"How Active Are Debit Cards?\n{SUB}", "section", LAYOUT_SECTION_ALT),
        # Penetration slides (DCTR-1 skipped)
        _s("DCTR-2", "DCTR: Historical Debit Card Take Rate"),
        _s("DCTR-3", "DCTR: L12M Snapshot"),
        _s("DCTR-4", "DCTR: Open vs Eligible Comparison"),
        _s("DCTR-5", "DCTR: Personal vs Business Split"),
        _s("DCTR-6", "DCTR: Monthly Trend"),
        _s("DCTR-7", "DCTR: Branch Comparison"),
        _s("DCTR-8", "DCTR: Age Distribution"),
        _s("DCTR-9", "DCTR: Product Code Analysis"),
        _s("DCTR-10", "DCTR: Cohort Analysis"),
        _s("DCTR-11", "DCTR: New Account Activation"),
        _s("DCTR-12", "DCTR: Dormant Reactivation"),
        _s("DCTR-13", "DCTR: PIN vs Signature Split"),
        _s("DCTR-14", "DCTR: Spend per Active Card"),
        _s("DCTR-15", "DCTR: Swipes per Active Card"),
        _s("DCTR-16", "DCTR: Revenue per Card"),
        # A7.x analysis (merged pairs shown as multi_screenshot)
        _s("A7.6a+A7.4", "DCTR Trajectory: Recent Trend & Segments", "multi_screenshot", LAYOUT_TWO_CONTENT),
        _s("A7.7+A7.8", "DCTR Funnel: Historical vs TTM", "multi_screenshot", LAYOUT_TWO_CONTENT),
        _s("A7.10a", "DCTR: Eligible vs Non-Eligible Overlay"),
        _s("A7.11+A7.12", "DCTR Opportunity: Age Analysis", "multi_screenshot", LAYOUT_TWO_CONTENT),
        # Value slide absorbed into DCTR
        _s("A11.1", "Value of a Debit Card"),
        # APPENDIX
        _s("APP", "Appendix \u2013 DCTR", "section", LAYOUT_SECTION_ALT),
        _s("A7.5", "[Appendix] DCTR: Eligible Trend"),
        _s("A7.6b", "[Appendix] DCTR: Segment Detail"),
        _s("A7.9", "[Appendix] DCTR: Eligible vs Non-Eligible"),
        _s("A7.10b", "[Appendix] DCTR: Overlay Detail"),
        _s("A7.10c", "[Appendix] DCTR: Overlay KPI", "screenshot_kpi", LAYOUT_CUSTOM,
           kpis={"Active": "12,345", "Rate": "34.2%"}),
        _s("A7.13", "[Appendix] DCTR: Product Breakdown"),
        _s("A7.14", "[Appendix] DCTR: Tenure Analysis"),
        _s("A7.15", "[Appendix] DCTR: Branch Detail"),
    ]


def _rege():
    """Reg E: 13 slides.
    MAIN: A8.3, A8.4a, A8.4b, A8.10+A8.11 (merged), A8.5+A8.6 (merged), A8.13
    APPENDIX: A8.1, A8.2, A8.4c, A8.7, A8.12
    """
    return [
        _s("DIV", f"Are Members Opting In to Overdraft Protection?\n{SUB}", "section", LAYOUT_SECTION_ALT),
        # Main
        _s("A8.3", "Reg E: L12M Monthly Opt-In Trend"),
        _s("A8.4a", "Reg E: Branch Comparison (Horizontal)"),
        _s("A8.4b", "Reg E: Branch Comparison (Combo)"),
        _s("A8.10+A8.11", "Reg E Funnel: All-Time vs TTM", "multi_screenshot", LAYOUT_TWO_CONTENT),
        _s("A8.5+A8.6", "Reg E Opportunity: Age Analysis", "multi_screenshot", LAYOUT_TWO_CONTENT),
        _s("A8.13", "Reg E: Branch x Month Pivot"),
        # Value slide absorbed into Reg E
        _s("A11.2", "Value of Reg E Opt-In"),
        # APPENDIX
        _s("APP", "Appendix \u2013 Reg E", "section", LAYOUT_SECTION_ALT),
        _s("A8.1", "[Appendix] Reg E: Overall Status"),
        _s("A8.2", "[Appendix] Reg E: Historical Year/Decade"),
        _s("A8.4c", "[Appendix] Reg E: Branch Scatter"),
        _s("A8.7", "[Appendix] Reg E: Product Code Breakdown"),
        _s("A8.12", "[Appendix] Reg E: 24-Month Trend"),
    ]


def _attrition():
    """Attrition: 13 slides.
    MAIN: A9.1, A9.3+A9.6 (merged), A9.9, A9.10, A9.11, A9.12
    APPENDIX: A9.2, A9.4, A9.5, A9.7, A9.8, A9.13
    """
    return [
        _s("DIV", f"Are We Losing Accounts?\n{SUB}", "section", LAYOUT_SECTION_ALT),
        # Main
        _s("A9.1", "Attrition: Overview", "screenshot_kpi", LAYOUT_CUSTOM,
           kpis={"Closed": "1,245", "Rate": "3.8%"}),
        _s("A9.3+A9.6", "Attrition: Open vs Closed & Personal vs Business", "multi_screenshot", LAYOUT_TWO_CONTENT),
        _s("A9.9", "Attrition: Account Age Profile", "screenshot_kpi", LAYOUT_CUSTOM,
           kpis={"< 2yr": "42%", "2-5yr": "31%"}),
        _s("A9.10", "Attrition: Holder Age Profile", "screenshot_kpi", LAYOUT_CUSTOM,
           kpis={"18-35": "28%", "35-55": "45%"}),
        _s("A9.11", "Attrition: Product Breakdown", "screenshot_kpi", LAYOUT_CUSTOM,
           kpis={"Checking": "68%", "Savings": "22%"}),
        _s("A9.12", "Attrition: Branch Impact", "screenshot_kpi", LAYOUT_CUSTOM,
           kpis={"Top": "Main St", "Rate": "5.2%"}),
        # APPENDIX
        _s("APP", "Appendix \u2013 Attrition", "section", LAYOUT_SECTION_ALT),
        _s("A9.2", "[Appendix] Attrition: Monthly Trend"),
        _s("A9.4", "[Appendix] Attrition: Closure Reasons"),
        _s("A9.5", "[Appendix] Attrition: Tenure at Closure"),
        _s("A9.7", "[Appendix] Attrition: Revenue Impact Detail"),
        _s("A9.8", "[Appendix] Attrition: Segment Comparison"),
        _s("A9.13", "[Appendix] Attrition: Branch Detail"),
    ]


def _mailer():
    """Mailer: ~75 slides in full run. Preview shows structure for 2 months.
    Per month: A13.{month} summary + A12.{month}.Swipes + A12.{month}.Spend
    Plus: A13.Agg, A13.5, A13.6, A14.2, A15.1-A15.4, A16.1-A16.6, A17.1-A17.3
    """
    return [
        _s("DIV", f"Mailer Campaign Performance\n{SUB}", "section", LAYOUT_SECTION_ALT),
        # Most recent month
        _s("A13.Jan26", "January 2026 Mailer Summary", "mailer_summary", LAYOUT_MAIL_SUMMARY,
           kpis={"Mailed": "5,661", "Responded": "383", "Rate": "6.8%"},
           bullets=[
               "The January 2026 mailer reached 5,661 accounts with a 6.8% response rate.",
               "36%|of Responders opened < 2 years ago",
               "27%|of Responders aged 30-45",
               "32%|opted into Reg E",
               "41%|First-time responders",
           ]),
        _s("A12.Jan26.Swipes", "Jan26 Responder Swipes", "screenshot", LAYOUT_CUSTOM),
        _s("A12.Jan26.Spend", "Jan26 Responder Spend", "screenshot", LAYOUT_CUSTOM),
        # Second most recent month
        _s("A13.Nov25", "November 2025 Mailer Summary", "mailer_summary", LAYOUT_MAIL_SUMMARY,
           kpis={"Mailed": "5,430", "Responded": "614", "Rate": "11.3%"},
           bullets=[
               "The November 2025 mailer reached 5,430 accounts with an 11.3% response rate.",
               "29%|opened < 2 years ago",
               "31%|aged 30-45",
               "28%|opted into Reg E",
               "58%|First-time responders",
           ]),
        _s("A12.Nov25.Swipes", "Nov25 Responder Swipes", "screenshot", LAYOUT_CUSTOM),
        _s("A12.Nov25.Spend", "Nov25 Responder Spend", "screenshot", LAYOUT_CUSTOM),
        # Mailer revisit
        _s("A14.2", "Responder Account Age Distribution"),
        # Aggregate summaries
        _s("A13.Agg", "All-Time Mailer Summary", "mailer_summary", LAYOUT_MAIL_SUMMARY,
           kpis={"Mailed": "84,915", "Responded": "8,412", "Rate": "9.9%"},
           bullets=[
               "Across all 15 mailers, 84,915 accounts were mailed with a 9.9% cumulative response rate.",
               "34%|opened < 2 years ago",
               "29%|aged 30-45",
               "30%|opted into Reg E",
               "52%|First-time responders",
           ]),
        _s("A13.5", "Responder Count Trend (Stacked Bar)"),
        _s("A13.6", "Response Rate Trend (Line Chart)"),
        # Impact slides
        _s("A15.1", "Market Reach: Program Penetration"),
        _s("A15.2", "Spend Share: Responder vs Non-Responder"),
        _s("A15.3", "Revenue Attribution"),
        _s("A15.4", "Pre/Post Spend Delta"),
        # Cohort trajectories
        _s("A16.1", "Cohort Trajectory: Swipes (Recent)"),
        _s("A16.2", "Cohort Trajectory: Swipes (All)"),
        _s("A16.3", "Cohort Trajectory: Spend (Recent)"),
        _s("A16.4", "Cohort Trajectory: Spend (All)"),
        _s("A16.5", "Cohort Trajectory: Items (Recent)"),
        _s("A16.6", "Cohort Trajectory: Items (All)"),
        # Cumulative reach
        _s("A17.1", "Cumulative Reach: Accounts"),
        _s("A17.2", "Cumulative Reach: By Segment"),
        _s("A17.3", "Cumulative Reach: Response Rate Over Time"),
        # APPENDIX (older months would go here)
        _s("APP", "Appendix \u2013 Mailer (Older Months)", "section", LAYOUT_SECTION_ALT),
        _s("A13.Sep25", "[Appendix] September 2025 Mailer Summary", "mailer_summary", LAYOUT_MAIL_SUMMARY,
           kpis={"Mailed": "5,100", "Responded": "520", "Rate": "10.2%"},
           bullets=[
               "The September 2025 mailer reached 5,100 accounts with a 10.2% response rate.",
               "31%|opened < 2 years ago",
               "28%|aged 30-45",
               "33%|opted into Reg E",
               "47%|First-time responders",
           ]),
    ]


def _value():
    """Value: 2 slides (A11.1 absorbed by DCTR, A11.2 absorbed by Reg E).
    In practice these appear inside other sections, not standalone.
    """
    return [
        _s("DIV", f"What Is the Revenue Impact?\n{SUB}", "section", LAYOUT_SECTION_ALT),
        _s("A11.1", "Value of a Debit Card (absorbed into DCTR section)"),
        _s("A11.2", "Value of Reg E Opt-In (absorbed into Reg E section)"),
    ]


def _insights():
    """Insights: S1-S8 synthesis + A18 effectiveness + A19 branch scorecard + A20 dormant."""
    return [
        _s("DIV", f"What Should We Do Next?\n{SUB}", "section", LAYOUT_SECTION_ALT),
        # Synthesis
        _s("S1", "Key Finding: Portfolio Health Summary"),
        _s("S2", "Key Finding: Card Usage Momentum"),
        _s("S3", "Key Finding: Risk & Retention"),
        _s("S4", "Key Finding: Campaign Effectiveness"),
        _s("S5", "Key Finding: Revenue Opportunity"),
        _s("S6", "Recommended Action 1"),
        _s("S7", "Recommended Action 2"),
        _s("S8", "Recommended Action 3"),
        # Effectiveness proof
        _s("A18.1", "Program ROI: Revenue per Dollar Invested"),
        _s("A18.2", "Effectiveness: Responder Lift vs Control"),
        _s("A18.3", "Effectiveness: Incremental Revenue Proof"),
        # Branch scorecard
        _s("A19.1", "Branch Scorecard: Rankings"),
        _s("A19.2", "Branch Scorecard: Detail"),
        # Dormant opportunity
        _s("A20.1", "Dormant Opportunity: Segment Profile"),
        _s("A20.2", "Dormant Opportunity: Revenue Recovery"),
        _s("A20.3", "Dormant Opportunity: Reactivation Targets"),
    ]


def _overview():
    """Overview: A1, A1b, A3 (all skipped in production deck)."""
    return [
        _s("DIV", f"How Big Is This Program?\n{SUB}", "section", LAYOUT_SECTION_ALT),
        _s("A1", "Account Composition (skipped in production)"),
        _s("A1b", "Product Code Distribution (skipped in production)"),
        _s("A3", "Eligibility Funnel (skipped in production)"),
    ]


SECTIONS = {
    "preamble": _preamble,
    "overview": _overview,
    "dctr": _dctr,
    "rege": _rege,
    "attrition": _attrition,
    "mailer": _mailer,
    "value": _value,
    "insights": _insights,
}


def build_section(section_name, template_path, output_dir, chart):
    """Build a single section preview PPTX."""
    if section_name not in SECTIONS:
        print(f"  Unknown section: {section_name}")
        return
    defs = SECTIONS[section_name]()
    slides = _build_slides(defs, chart)
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
        for name, fn in SECTIONS.items():
            slides = fn()
            print(f"  {name} ({len(slides)} slides)")
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
