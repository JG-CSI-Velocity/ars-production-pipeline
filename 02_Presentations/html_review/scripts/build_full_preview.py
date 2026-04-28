"""Generate the full-analytics preview HTML.

    python 02_Presentations/html_review/scripts/build_full_preview.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add 02_Presentations/ to sys.path so html_review imports resolve
_THIS = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS.parents[1]))

from html_review.builder import build_html
from html_review.model import ClientMeta
from html_review.tests.fixtures.full_analytics import full_analytics


def main() -> int:
    out = Path("/tmp/html_review_full_preview")
    out.mkdir(exist_ok=True)
    results = full_analytics(out)
    print(
        f"Generated {len(results)} AnalysisResultLike entries across "
        f"the analytics tree"
    )

    client = ClientMeta(
        id="1615",
        display_name="Cape & Coast Bank",
        month="2026-04",
        month_display="April 2026",
        run_date="2026-04-17",
    )
    # --no-embed-images keeps the HTML small since all charts share one PNG
    path = build_html(results, client, out, embed_images=False)
    print(f"Wrote {path}")
    print(f"Size: {path.stat().st_size:,} bytes")
    print(
        f"Open: http://localhost:8765/ "
        f"(if the HTTP server from earlier is still up)"
    )
    print(f"   or file://{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
