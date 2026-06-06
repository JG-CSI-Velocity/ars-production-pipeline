"""Build the Velocity Analysis -- Methodology & Data Integrity report (PDF).

A branded, modern, data-storytelling document that explains how every
client-facing rate is calculated, section by section, and tells the story
of the canonical-denominator work (the DCTR Open-vs-Eligible fix).

Pure matplotlib so it runs anywhere the pipeline runs (no extra deps).
Colors and type come from shared.brand so the report stays in lockstep
with the rest of the product. Montserrat / Space Mono are the production
brand fonts; this build falls back to the nearest installed grotesque +
mono when they are unavailable, with no change to layout or color.

Run:  python docs/methodology/build_methodology_pdf.py
Out:  docs/methodology/Velocity-Analysis-Methodology.pdf
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle

# --- Brand authority (single source of truth) -------------------------------
_SCRIPTS = Path(__file__).resolve().parents[2] / "01_Analysis" / "00-Scripts"
sys.path.insert(0, str(_SCRIPTS))
try:
    from shared.brand import BRAND  # type: ignore
except Exception:  # pragma: no cover -- fallback if path shifts
    BRAND = {
        "navy": "#00274C", "navy_soft": "#1A3A66", "accent": "#F15D22",
        "accent_light": "#FEF0E8", "positive": "#2A8B3E", "negative": "#C73E1D",
        "warning": "#F39C12", "neutral": "#8B95A2", "muted": "#B0B0B0",
        "light_gray": "#E8E8E8", "text": "#222222", "text_muted": "#777777",
        "bg": "#FFFFFF",
    }

NAVY = BRAND["navy"]
ACCENT = BRAND["accent"]
ACCENT_LT = BRAND["accent_light"]
POS = BRAND["positive"]
NEG = BRAND["negative"]
MUTED = BRAND["muted"]
LGRAY = BRAND["light_gray"]
TEXT = BRAND["text"]
TMUTED = BRAND["text_muted"]

# --- Fonts: prefer brand, fall back gracefully ------------------------------
_installed = {f.name for f in fm.fontManager.ttflist}
SANS = next((f for f in ("Montserrat", "Liberation Sans", "Arial", "DejaVu Sans") if f in _installed), "DejaVu Sans")
MONO = next((f for f in ("Space Mono", "DejaVu Sans Mono", "Liberation Mono") if f in _installed), "DejaVu Sans Mono")
plt.rcParams["font.family"] = SANS
plt.rcParams["pdf.fonttype"] = 42  # embed TrueType so text stays selectable

PAGE_W, PAGE_H = 11.0, 8.5  # letter landscape -- modern deck-report hybrid
MARGIN = 0.85
TODAY = date.today().strftime("%B %Y")


# ===========================================================================
# Low-level page helpers
# ===========================================================================

def _new_page(pdf, bg=BRAND["bg"]):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H), dpi=200)
    fig.patch.set_facecolor(bg)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, PAGE_W)
    ax.set_ylim(0, PAGE_H)
    ax.axis("off")
    return fig, ax


def _text(ax, x, y, s, size, color=TEXT, weight="normal", font=None,
          ha="left", va="baseline", alpha=1.0, style="normal", spacing=None):
    t = ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                ha=ha, va=va, alpha=alpha, fontstyle=style,
                fontfamily=font or SANS, zorder=5)
    if spacing is not None:
        t.set_linespacing(spacing)
    return t


def _rule(ax, x, y, w, color=ACCENT, lw=2.4):
    ax.plot([x, x + w], [y, y], color=color, lw=lw, solid_capstyle="butt", zorder=4)


def _footer(ax, page_no, label="Velocity Analysis  ·  Methodology & Data Integrity"):
    _rule(ax, MARGIN, 0.52, PAGE_W - 2 * MARGIN, color=LGRAY, lw=0.8)
    _text(ax, MARGIN, 0.34, label, 7.5, color=TMUTED)
    _text(ax, PAGE_W - MARGIN, 0.34, f"{page_no:02d}", 7.5, color=TMUTED,
          ha="right", font=MONO)
    _text(ax, PAGE_W / 2, 0.34, "STRICTLY CONFIDENTIAL", 7.5, color=TMUTED, ha="center")


def _section_header(ax, kicker, title, subtitle=None):
    """Standard content-page header: small accent kicker, big navy title."""
    _text(ax, MARGIN, PAGE_H - 1.02, kicker.upper(), 10, color=ACCENT,
          weight="bold", font=MONO)
    _text(ax, MARGIN, PAGE_H - 1.52, title, 25, color=NAVY, weight="bold")
    _rule(ax, MARGIN, PAGE_H - 1.74, 1.5, color=ACCENT, lw=3)
    if subtitle:
        _text(ax, MARGIN, PAGE_H - 2.12, subtitle, 12.5, color=TMUTED, spacing=1.35)


def _pill(ax, x, y, w, h, label, fill, text_color="#FFFFFF", size=8.5, weight="bold"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                facecolor=fill, edgecolor="none", zorder=4))
    _text(ax, x + w / 2, y + h / 2, label, size, color=text_color, weight=weight,
          ha="center", va="center", font=MONO)


# ===========================================================================
# Page 1 -- Cover
# ===========================================================================

def page_cover(pdf):
    fig, ax = _new_page(pdf, bg=NAVY)
    # accent corner block
    ax.add_patch(Rectangle((0, 0), PAGE_W, 0.32, color=ACCENT, zorder=2))
    ax.add_patch(Rectangle((0, PAGE_H - 0.12), 3.4, 0.12, color=ACCENT, zorder=2))

    _text(ax, MARGIN, PAGE_H - 1.7, "VELOCITY", 13, color="#FFFFFF", weight="bold",
          font=MONO, alpha=0.85)
    _text(ax, MARGIN, PAGE_H - 2.0, "ARS + Transaction Analytics", 11, color=ACCENT,
          weight="bold")

    _text(ax, MARGIN, 5.0, "How We Measure", 46, color="#FFFFFF", weight="bold")
    _text(ax, MARGIN, 4.18, "Methodology & Data Integrity", 22, color="#FFFFFF",
          alpha=0.92)
    _rule(ax, MARGIN, 3.85, 2.2, color=ACCENT, lw=3)

    _text(ax, MARGIN, 3.25,
          "Every client-facing rate, the population it is measured over,\n"
          "and the story of how we made the headline numbers defensible.",
          13.5, color="#FFFFFF", alpha=0.8, spacing=1.4)

    _text(ax, MARGIN, 1.15, TODAY.upper(), 10, color="#FFFFFF", weight="bold",
          font=MONO, alpha=0.7)
    _text(ax, PAGE_W - MARGIN, 1.15, "STRICTLY CONFIDENTIAL", 9, color="#FFFFFF",
          alpha=0.55, ha="right", font=MONO)
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# Page 2 -- The story (executive narrative)
# ===========================================================================

def page_story(pdf, page_no):
    fig, ax = _new_page(pdf)
    _section_header(ax, "The story", "A headline rate that didn't reconcile")

    body = [
        ("The symptom.", TEXT,
         "Our take rate led the deck at ~30%. The\n"
         "validated notebook put the same portfolio\n"
         "near 80%. A 50-point gap on the first number\n"
         "a client sees is a credibility problem."),
        ("The cause.", TEXT,
         "Take rate divided by the eligible book —\n"
         "open accounts narrowed by status and product\n"
         "code — instead of by all open accounts. The\n"
         "denominator, not the math, was the bug."),
        ("The fix.", TEXT,
         "We codified one canonical base per metric.\n"
         "The portfolio rate divides by all open\n"
         "accounts; the eligible cut is kept as a\n"
         "labeled companion, shown side by side."),
        ("The safeguard.", TEXT,
         "Every published rate writes to a per-run\n"
         "audit file with its denominator and count.\n"
         "Two runs diff in one command; any rate that\n"
         "moves more than a point flags itself."),
    ]
    y = PAGE_H - 2.7
    for lead, _c, txt in body:
        _text(ax, MARGIN, y, lead, 13.5, color=ACCENT, weight="bold")
        _text(ax, MARGIN + 1.7, y, txt, 12, color=TEXT, spacing=1.45, va="top")
        y -= 1.34

    # right-margin hero stat
    hx = PAGE_W - MARGIN - 2.7
    ax.add_patch(FancyBboxPatch((hx, 5.0), 2.7, 1.9,
                 boxstyle="round,pad=0.03,rounding_size=0.08",
                 facecolor=ACCENT_LT, edgecolor="none", zorder=3))
    _text(ax, hx + 1.35, 6.45, "~30% → ~80%", 21, color=NAVY, weight="bold",
          ha="center", va="center")
    _text(ax, hx + 1.35, 5.55, "portfolio DCTR, once measured\nover the right population",
          9.5, color=TMUTED, ha="center", va="center", spacing=1.3)

    _footer(ax, page_no)
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# Page 3 -- The denominator framework (nested populations + tier map)
# ===========================================================================

def page_framework(pdf, page_no):
    fig, ax = _new_page(pdf)
    _section_header(ax, "The framework", "One canonical base per metric",
                    "Rates differ only by the population beneath them. We name that\n"
                    "population once, so every number reconciles to a known base.")

    # Nested-population diagram (left): All accounts > Open > Eligible
    ox, oy = MARGIN, 2.4
    layers = [
        ("All accounts on file", 4.7, 3.6, LGRAY, TEXT),
        ("Open accounts  —  the take-rate base", 3.8, 2.9, BRAND["navy_soft"], "#FFFFFF"),
        ("Eligible book  —  stat + product filtered", 2.7, 2.0, NAVY, "#FFFFFF"),
    ]
    for label, w, h, fill, tc in layers:
        ax.add_patch(FancyBboxPatch((ox, oy), w, h,
                     boxstyle="round,pad=0.02,rounding_size=0.06",
                     facecolor=fill, edgecolor="none", zorder=3))
        _text(ax, ox + 0.18, oy + h - 0.28, label, 10.5, color=tc, weight="bold", va="top")
        oy += 0.0  # keep nested from same origin
    # annotate the two key rates
    _text(ax, ox + 0.2, 2.95, "DCTR-1  =  Open w/ debit  ÷  Total open",
          10.5, color="#FFFFFF", font=MONO, weight="bold")
    _text(ax, ox + 0.2, 2.66, "DCTR-1 companion  =  Elig w/ debit ÷ Total elig",
          9, color="#FFFFFF", font=MONO, alpha=0.8)

    # Tier map (right)
    tx = MARGIN + 5.4
    _text(ax, tx, PAGE_H - 2.55, "WHICH BASE EACH SLIDE USES", 9.5, color=ACCENT,
          weight="bold", font=MONO)
    rows = [
        ("Portfolio headline", "All open accounts", "DCTR-1, DCTR-3", POS),
        ("Methodology comp", "Open + Eligible, shown side by side", "DCTR-2, companions", ACCENT),
        ("Eligible detail", "Eligible book only", "DCTR-4/5, 9, A7.x, overlays", NAVY),
    ]
    ry = PAGE_H - 3.0
    for tier, base, slides, c in rows:
        ax.add_patch(Rectangle((tx, ry - 0.86), 0.07, 0.86, color=c, zorder=4))
        _text(ax, tx + 0.22, ry - 0.1, tier, 12, color=NAVY, weight="bold", va="top")
        _text(ax, tx + 0.22, ry - 0.42, base, 10, color=TEXT, va="top")
        _text(ax, tx + 0.22, ry - 0.68, slides, 8.5, color=TMUTED, va="top", font=MONO)
        ry -= 1.12

    _text(ax, tx, ry + 0.05,
          "Detail breakdowns stay on the eligible book on purpose: a\n"
          "branch- or balance-tier take rate answers “adoption within the\n"
          "program,” not “across the whole portfolio.”",
          9, color=TMUTED, va="top", spacing=1.35, style="italic")

    _footer(ax, page_no)
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# Page 4 -- DCTR calculations + open-vs-eligible illustration
# ===========================================================================

def page_dctr(pdf, page_no):
    fig, ax = _new_page(pdf)
    _section_header(ax, "Section · DCTR", "Debit Card Take Rate",
                    "The numerator is identical everywhere — debit_mask counts the cards.\n"
                    "Only the population beneath it changes.")

    # left: formula table
    rows = [
        ("DCTR-1", "overall", "open w/ debit ÷ total open", "Open"),
        ("DCTR-1", "companion", "elig w/ debit ÷ total elig", "Eligible"),
        ("DCTR-2", "comparison", "the two rates, side by side", "Both"),
        ("DCTR-3", "L12M open", "open w/ debit ÷ total open  (TTM)", "Open"),
        ("DCTR-3", "L12M elig", "elig w/ debit ÷ total elig  (TTM)", "Eligible"),
        ("DCTR-4/5", "pers / biz", "debit ÷ total", "Eligible"),
        ("DCTR-9 · A7.x", "branch / age", "debit ÷ total", "Eligible"),
    ]
    base_color = {"Open": POS, "Eligible": NAVY, "Both": ACCENT}
    y = PAGE_H - 2.95
    _text(ax, MARGIN, y + 0.28, "SLIDE", 8, color=TMUTED, weight="bold", font=MONO)
    _text(ax, MARGIN + 1.5, y + 0.28, "FORMULA", 8, color=TMUTED, weight="bold", font=MONO)
    for sid, _m, formula, base in rows:
        _text(ax, MARGIN, y, sid, 10, color=NAVY, weight="bold", font=MONO, va="center")
        _text(ax, MARGIN + 1.5, y, formula, 9.5, color=TEXT, font=MONO, va="center")
        _pill(ax, PAGE_W - MARGIN - 4.55, y - 0.13, 0.95, 0.26, base,
              base_color[base], size=7.5)
        _rule(ax, MARGIN, y - 0.24, 5.3, color=LGRAY, lw=0.6)
        y -= 0.49

    # right: illustration chart -- open vs eligible on a worked example
    cax = fig.add_axes([0.62, 0.34, 0.30, 0.32])
    cax.set_facecolor("none")
    labels = ["All open", "Eligible"]
    rates = [80, 100]
    bars = cax.bar(labels, rates, color=[POS, NAVY], width=0.62, zorder=3)
    counts = ["10 accts", "4 accts"]
    for b, r, n in zip(bars, rates, counts):
        cax.text(b.get_x() + b.get_width() / 2, r + 2.5, f"{r}%", ha="center",
                 va="bottom", fontsize=13, fontweight="bold", color=NAVY)
        cax.text(b.get_x() + b.get_width() / 2, 4, n, ha="center", va="bottom",
                 fontsize=8.5, color="#FFFFFF", fontweight="bold")
    cax.set_ylim(0, 118)
    cax.set_yticks([])
    for s in ("top", "right", "left"):
        cax.spines[s].set_visible(False)
    cax.spines["bottom"].set_color(MUTED)
    cax.tick_params(labelsize=10, colors=TEXT, length=0)
    cax.set_title("Worked example: same 8 cards, two bases",
                  fontsize=10, color=NAVY, fontweight="bold", pad=10, loc="left")
    _text(ax, PAGE_W - MARGIN - 3.1, 2.18,
          "Narrowing to eligible products raises the rate —\n"
          "which is why the portfolio headline uses the open base.",
          8.5, color=TMUTED, va="top", spacing=1.3, style="italic")

    _footer(ax, page_no)
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# Page 5 -- Per-section calculation reference (cards)
# ===========================================================================

def page_reference(pdf, page_no):
    fig, ax = _new_page(pdf)
    _section_header(ax, "Reference", "Calculations by section",
                    "Every shipped rate, its formula, and the population it divides by.")

    cards = [
        ("Overview", POS, [
            ("eligibility_rate", "eligible ÷ all accounts"),
            ("drop-off %", "(prev − curr) ÷ prev stage"),
            ("personal / business", "segment ÷ eligible"),
        ]),
        ("Reg E", NAVY, [
            ("opt-in rate", "opted-in ÷ eligible personal"),
            ("(base)", "eligible personal, not debit-narrowed"),
            ("NaN handling", "missing → not opted in"),
        ]),
        ("Attrition", ACCENT, [
            ("overall_rate", "closed ÷ all rows"),
            ("l12m_rate", "l12m closed ÷ open at start"),
            ("revenue lost", "last_spend × ic_rate × 12"),
        ]),
        ("Value", NAVY, [
            ("delta", "rev/acct with − without debit"),
            ("pot_hist", "awo × delta × DCTR-1 rate"),
            ("note", "tracks the portfolio base"),
        ]),
        ("Mailer", POS, [
            ("resp_rate", "responders ÷ mailed"),
            ("penetration", "responders ÷ eligible w/ card"),
        ]),
        ("Insights", ACCENT, [
            ("S1 gap", "accts_without × delta"),
            ("realistic", "total_gap × 0.25"),
            ("S4–S8", "inherit upstream bases"),
        ]),
    ]
    cw, ch = 2.95, 1.78
    gx, gy = 0.28, 0.42
    x0 = MARGIN
    y0 = PAGE_H - 2.95
    for i, (name, color, items) in enumerate(cards):
        col = i % 3
        rowi = i // 3
        x = x0 + col * (cw + gx)
        y = y0 - rowi * (ch + gy)
        ax.add_patch(FancyBboxPatch((x, y - ch), cw, ch,
                     boxstyle="round,pad=0.02,rounding_size=0.07",
                     facecolor="#FFFFFF", edgecolor=LGRAY, linewidth=1.0, zorder=3))
        ax.add_patch(Rectangle((x, y - 0.34), cw, 0.34, color=color, zorder=4))
        _text(ax, x + 0.16, y - 0.17, name, 11.5, color="#FFFFFF", weight="bold", va="center")
        iy = y - 0.62
        for metric, formula in items:
            _text(ax, x + 0.16, iy, metric, 9, color=NAVY, weight="bold", font=MONO)
            _text(ax, x + 0.16, iy - 0.2, formula, 8.3, color=TEXT, va="top")
            iy -= 0.46

    _footer(ax, page_no)
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
# Page 6 -- The safeguard (rates audit) + closing
# ===========================================================================

def page_safeguard(pdf, page_no):
    fig, ax = _new_page(pdf)
    _section_header(ax, "The safeguard", "Numbers that defend themselves",
                    "Each run writes rates_audit.csv — one row per published rate,\n"
                    "with the exact denominator label and count.")

    # mock audit rows
    head = ["slide_id", "metric", "value", "denominator_n", "denominator_label"]
    data = [
        ["DCTR-1", "overall_dctr", "0.8100", "12,000", "open accounts"],
        ["DCTR-1", "eligible_dctr", "0.3200", "4,800", "eligible accounts"],
        ["DCTR-2", "open_dctr", "0.8000", "12,000", "open accounts"],
        ["DCTR-3", "l12m_dctr", "0.7400", "1,950", "open accounts (L12M)"],
        ["A9.1", "overall_rate", "0.0600", "12,000", "all rows"],
        ["A11.1", "pot_l12m", "412,500", "—", "active personal w/o debit"],
    ]
    colx = [MARGIN, MARGIN + 1.5, MARGIN + 3.0, MARGIN + 4.1, MARGIN + 5.4]
    ax.add_patch(Rectangle((MARGIN - 0.12, PAGE_H - 3.18), 8.7, 0.34, color=NAVY, zorder=3))
    for cx, h in zip(colx, head):
        _text(ax, cx, PAGE_H - 3.01, h, 8, color="#FFFFFF", weight="bold", font=MONO, va="center")
    ry = PAGE_H - 3.5
    for r in data:
        for cx, val in zip(colx, r):
            c = ACCENT if val in ("open accounts", "open accounts (L12M)") else TEXT
            w = "bold" if c == ACCENT else "normal"
            _text(ax, cx, ry, val, 8.5, color=c, font=MONO, weight=w, va="center")
        _rule(ax, MARGIN - 0.12, ry - 0.16, 8.7, color=LGRAY, lw=0.5)
        ry -= 0.38

    _text(ax, MARGIN, ry - 0.2,
          "Diff two runs and every line is a rate that moved. Intended change, or\n"
          "regression — you know before the deck reaches the client.",
          11, color=TEXT, va="top", spacing=1.4)

    # closing band
    ax.add_patch(Rectangle((0, 0.85), PAGE_W, 0.9, color=NAVY, zorder=2))
    _text(ax, MARGIN, 1.3, "Accurate first. Then beautiful.", 15, color="#FFFFFF",
          weight="bold", va="center")
    _text(ax, PAGE_W - MARGIN, 1.3, "shared/brand.py  ·  rates_audit.csv", 9,
          color=ACCENT, va="center", ha="right", font=MONO)

    _footer(ax, page_no)
    pdf.savefig(fig); plt.close(fig)


# ===========================================================================
def build(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_path) as pdf:
        page_cover(pdf)
        page_story(pdf, 2)
        page_framework(pdf, 3)
        page_dctr(pdf, 4)
        page_reference(pdf, 5)
        page_safeguard(pdf, 6)
        d = pdf.infodict()
        d["Title"] = "Velocity Analysis -- Methodology & Data Integrity"
        d["Author"] = "Velocity Pipeline"
        d["Subject"] = "How every client-facing rate is calculated"
    return out_path


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "Velocity-Analysis-Methodology.pdf"
    p = build(out)
    print(f"Wrote {p}  ({p.stat().st_size/1024:.0f} KB, fonts: {SANS} / {MONO})")
