"""Walk every analysis cell in 01_Analysis/00-Scripts/analytics/ and
generate one AnalysisResultLike per cell using real titles from header
comments. Placeholder data for charts. Purpose: demo the full-scale
deck (~400 exhibits) without real client data.
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from html_review.tests.fixtures.tiny_deck import AnalysisResultLike


# fixtures/full_analytics.py -> fixtures/ -> tests/ -> html_review/ ->
# 02_Presentations/ -> RPE-Workflow/ (that's 4 parents).
ANALYTICS_ROOT = (
    Path(__file__).resolve().parents[4]
    / "01_Analysis"
    / "00-Scripts"
    / "analytics"
)

SKIP_FILES = {"__init__.py", "base.py", "registry.py", "txn_wrapper.py"}
SKIP_DIRS = {"__pycache__"}

# Map the various analytics folder names to the 9 canonical sections.
# Anything not mapped falls back to the folder name as its section id.
SECTION_MAP = {
    "overview": "overview",
    "general": "overview",
    "executive": "overview",

    "dctr": "dctr",

    "rege": "rege",
    "rege_overdraft": "rege",

    "attrition": "attrition",
    "attrition_txn": "attrition",
    "retention": "attrition",

    "value": "value",

    "campaign": "mailer",
    "mailer": "mailer",
    "ars_campaign": "mailer",
    "engagement": "mailer",
    "segment_evolution": "mailer",

    "transaction": "transaction",
    "transaction_type": "transaction",
    "merchant": "transaction",
    "mcc_code": "transaction",
    "business_accts": "transaction",
    "personal_accts": "transaction",
    "branch_txn": "transaction",
    "txn_setup": "transaction",
    "product": "transaction",
    "balance": "transaction",
    "interchange": "transaction",

    "competition": "ics",
    "financial_services": "ics",
    "ics_acquisition": "ics",
    "payroll": "ics",
    "relationship": "ics",

    "insights": "insights",
}


def _extract_title(py_path: Path) -> str:
    """Pull a human title from a cell.

    Tries in order:
    1. Class attribute display_name on an AnalysisModule subclass
    2. Module docstring first line
    3. First ALL-CAPS header comment line like "# SECTION: Title"
    4. Cleaned-up filename
    """
    try:
        text = py_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return py_path.stem.replace("_", " ").title()

    # 1. display_name class attr
    m = re.search(r'display_name\s*[:=]\s*["\']([^"\']+)["\']', text)
    if m:
        return m.group(1)

    # 2. Module docstring -- first non-empty line
    doc_match = re.match(r'\s*"""([^"\n]+)', text)
    if doc_match:
        first_doc = doc_match.group(1).strip()
        # Trim trailing punctuation and trailing descriptors after " -- "
        if " -- " in first_doc:
            first_doc = first_doc.split(" -- ", 1)[0].strip()
        if first_doc.endswith("."):
            first_doc = first_doc[:-1]
        if len(first_doc) > 3:
            return first_doc

    # 3. First meaningful comment line of the form "# LABEL: Title"
    lines = text.splitlines()
    for line in lines[:40]:
        ls = line.strip()
        if ls.startswith("# ") and ":" in ls and not ls.startswith("# ==="):
            after_colon = ls.split(":", 1)[1].strip()
            if len(after_colon) > 6 and not after_colon.startswith("-"):
                return after_colon

    # 4. Clean filename
    stem = py_path.stem
    # Strip leading digits/underscores like "02_"
    stem = re.sub(r"^\d+[_\-]?", "", stem)
    return stem.replace("_", " ").strip().title() or py_path.stem


def _placeholder_png(out_path: Path) -> Path:
    """Create a single shared navy PNG at out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1800, 900), (27, 54, 93)).save(out_path)
    return out_path


def full_analytics(tmp_path: Path) -> list[AnalysisResultLike]:
    """Walk every .py cell in analytics/ and produce AnalysisResultLike entries."""
    if not ANALYTICS_ROOT.exists():
        raise FileNotFoundError(
            f"Analytics root not found: {ANALYTICS_ROOT}. "
            f"Run from a repo clone that has the analytics/ folder."
        )

    shared_png = _placeholder_png(tmp_path / "placeholder.png")
    results: list[AnalysisResultLike] = []

    for folder in sorted(ANALYTICS_ROOT.iterdir()):
        if not folder.is_dir() or folder.name in SKIP_DIRS:
            continue

        section = SECTION_MAP.get(folder.name, folder.name)

        for py_file in sorted(folder.glob("*.py")):
            if py_file.name in SKIP_FILES:
                continue
            # Skip private helpers like _helpers.py, _data.py
            if py_file.name.startswith("_"):
                continue

            slide_id = f"{folder.name}__{py_file.stem}"
            title = _extract_title(py_file)
            results.append(AnalysisResultLike(
                slide_id=slide_id,
                title=title,
                section=section,
                chart_path=shared_png,
                notes=(
                    f"Cell: analytics/{folder.name}/{py_file.name}. "
                    f"Real data pending pipeline run -- placeholder rendering."
                ),
            ))

    return results
