"""Auto-generated speaker notes for CSM presentations.

Phase 18.5: Section-specific talking points replacing generic template.

Produces structured talking points that CSMs can read in Presenter View.
Format:
    KEY FINDING: [headline restated]
    - Supporting data point 1
    - Supporting data point 2

    TALKING POINT:
    - Section-specific client conversation starters

File: 01_Analysis/00-Scripts/output/notes.py
Action: REPLACE entire file contents with this version.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Section-specific talking points
# ---------------------------------------------------------------------------
# Each section has 2-3 targeted conversation starters that help CSMs
# drive actionable discussions instead of generic "what do you think?" prompts.

_SECTION_TALKING_POINTS: dict[str, list[str]] = {
    # --- ARS Sections ---
    "overview": [
        "Has the eligible account base grown or contracted since the last review?",
        "Are there segments (business vs personal) where penetration is notably different?",
    ],
    "dctr": [
        "Which branches have the lowest DCTR, and what does their activation process look like?",
        "Is there a new-account onboarding flow that includes debit card activation within the first 30 days?",
        "What outreach has been done to the eligible-but-no-debit segment?",
    ],
    "rege": [
        "How is Reg E opt-in being presented during account opening — is it opt-in or opt-out framing?",
        "What is the branch-level variation in opt-in rates, and are top performers doing something different?",
        "Has there been any recent compliance guidance that changed Reg E presentation?",
    ],
    "attrition": [
        "What is driving closures in the highest-attrition segments?",
        "Are there retention campaigns targeting at-risk accounts before they close?",
        "How much revenue walks out the door with each closed account?",
    ],
    "mailer": [
        "What has the mailer response rate trend looked like over the last 3-6 months?",
        "Is there a noticeable lift in engagement for accounts that received mailers vs those that did not?",
        "Are there segments that respond particularly well (or poorly) to the mailer program?",
    ],
    "value": [
        "How does the revenue-per-account difference between debit-active and non-active compare to peer institutions?",
        "What is the incremental value the ARS program has delivered this period?",
    ],
    "insights": [
        "Which of the three recommended actions is the most realistic to execute in the next quarter?",
        "What internal resources or approvals are needed to move forward on the top recommendation?",
        "How does the combined opportunity compare to the institution's annual revenue growth target?",
    ],
    "competition": [
        "Which competitors are capturing the most wallet share from your members/customers?",
        "Are there specific merchant categories where competitive leakage is highest?",
        "What differentiation strategies could recapture spend from the top 2-3 competitors?",
    ],
    "ics": [
        "Which acquisition channels are driving the highest-quality new accounts?",
        "How does the cost-per-acquisition compare across channels?",
    ],
    # --- TXN Sections ---
    "transaction": [
        "What trends do you see in overall transaction volume and average ticket size?",
        "Are there seasonal patterns that should inform campaign timing?",
    ],
    "merchant": [
        "Which top merchants represent the greatest concentration risk?",
        "Are there emerging merchant categories where spend is growing?",
    ],
    "payroll": [
        "What percentage of members/customers have direct deposit set up?",
        "How does PFI scoring correlate with product cross-sell success?",
    ],
    "engagement": [
        "What percentage of accounts are in the highest engagement tier?",
        "Has the engagement distribution shifted since the last review period?",
    ],
}

# Slide ID prefix → section key mapping
_SLIDE_SECTION_MAP: dict[str, str] = {
    "A1": "overview",
    "A3": "overview",
    "A7": "dctr",
    "DCTR": "dctr",
    "A8": "rege",
    "A9": "attrition",
    "A10": "value",
    "A11": "value",
    "A12": "mailer",
    "A13": "mailer",
    "A14": "mailer",
    "A15": "mailer",
    "A16": "mailer",
    "A17": "mailer",
    "A18": "insights",
    "A19": "insights",
    "A20": "insights",
    "S": "insights",
    "ICS": "ics",
    "TXN": "transaction",
}


def _resolve_section(slide_id: str) -> str:
    """Map a slide_id to its section key for talking-point lookup."""
    if not slide_id:
        return ""

    # Exact prefix match (longest first)
    sid_upper = slide_id.upper()
    for prefix in sorted(_SLIDE_SECTION_MAP.keys(), key=len, reverse=True):
        if sid_upper.startswith(prefix):
            return _SLIDE_SECTION_MAP[prefix]

    return ""


def generate_notes(
    slide_id: str,
    headline: str,
    insights: dict[str, Any],
    kpis: dict[str, str] | None = None,
) -> str:
    """Generate speaker notes from analysis data.

    Args:
        slide_id: The slide identifier (e.g., "DCTR-1").
        headline: The conclusion headline for this slide.
        insights: Raw insights dict from ctx.results.
        kpis: Optional KPI label->value pairs displayed on the slide.

    Returns:
        Multi-line speaker notes string.
    """
    lines: list[str] = [f"KEY FINDING: {headline}", ""]

    # Pull inner insights if nested
    inner = insights.get("insights", insights) if isinstance(insights, dict) else {}

    # Add KPI supporting data
    if kpis:
        for label, value in kpis.items():
            if label.lower() not in ("subtitle", "title"):
                lines.append(f"  - {label}: {value}")
        if len(kpis) > 0:
            lines.append("")

    # Add context from notes field if available
    notes_raw = inner.get("notes", "") if isinstance(inner, dict) else ""
    if notes_raw:
        lines.append(f"CONTEXT: {notes_raw}")
        lines.append("")

    # Section-specific talking points (Phase 18.5)
    section = _resolve_section(slide_id)
    talking_points = _SECTION_TALKING_POINTS.get(section, [])

    if talking_points:
        lines.append("TALKING POINTS:")
        for tp in talking_points:
            lines.append(f"  - {tp}")
    else:
        # Fallback for unmapped sections
        lines.append("TALKING POINT:")
        lines.append("  - What actions has the client taken on this metric since last review?")
        lines.append("  - How does this compare to their strategic goals?")

    return "\n".join(lines)
