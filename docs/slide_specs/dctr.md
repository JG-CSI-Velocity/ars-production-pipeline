# DCTR — Main Deck Specification

**Governing doc:** `SLIDE_DESIGN.md`
**Manifest rows:** `ARS - DCTR` sheet in `SLIDE_MANIFEST.xlsx` (rows marked Keep=Y)
**Section title (divider):** "Debit Card Take Rate"
**Section lead-in:** "Where the portfolio sits today, where the gap concentrates, and what closing it is worth."

Main deck = 3 content slides. Everything else lives in the Support Deck.

---

## Slide DCTR-MAIN-1 — L12M Trajectory + Branch Gap

**Group ID:** `DCTR-MAIN-1`
**Layout:** TWO_CONTENT (9)
**Components:** A7.6a (enhanced) + DCTR-7 (rebuilt)

### Action title (template)

`L12M DCTR of {l12m_rate}% {trails|matches|beats} historical by {|gap|}pp; {top_n} branches drive {contribution}% of the gap`

Examples when populated:
- "L12M DCTR of 52% trails historical by 6pp; 3 branches drive 71% of the gap"
- "L12M DCTR of 68% beats historical by 4pp; upside concentrated in top 3 branches"

**Logic for the title:**
- Compare L12M overall DCTR vs historical overall DCTR → signed `|gap|`
- If `|gap| < 1`, use "matches"
- If DCTR is down, identify the 3 branches with largest absolute contribution to the gap (volume × rate delta), report their combined share
- If DCTR is up, identify the 3 branches with the highest L12M rate and report their combined contribution to the gain

### Panel A (left) — Monthly combo

**Sub-title:** "L12M take rate and eligible volume, by month"

- **X-axis:** months (12 ticks, most recent on right)
- **Left Y-axis:** DCTR % (0-100 scale, tight to data range +10pp headroom)
- **Right Y-axis:** Eligible accounts opened (muted)
- **Columns** (right axis): monthly eligible account opens
  - Color: `#E8E8E8` (light gray)
  - Width: 0.65
  - No edge, no pattern
- **Line** (left axis): monthly DCTR %
  - Color: `#17A2B8` (accent teal)
  - Line width: 3
  - Markers: circle, size 8, filled same color
  - Data labels: on every point, 11pt bold, teal, offset +1.5pp above
- **Reference line:** horizontal dashed line at historical DCTR %, muted gray `#B0B0B0`, 1.5pt dashed, labeled `Historical avg: {hist}%` at right edge
- **No gridlines.** No legend (2 series, self-evident from label + reference line annotation).

**Annotation:** If L12M shows a clear trend (3+ consecutive months up/down), add a small teal arrow + "+/- Xpp L12M" label near the most recent point.

### Panel B (right) — Branch combo

**Sub-title:** "Branch take rate vs historical, by eligible volume"

- **X-axis:** branches, sorted descending by L12M eligible volume (left = largest branch)
- **Branch filter:** exclude any branch where L12M eligible volume = 0. No zero-volume bars; rate lines don't extend through inactive branches. Exclusion count ("{n} inactive branches hidden") shown in the footnote band if any.
- **Left Y-axis:** DCTR % (0-100)
- **Right Y-axis:** Eligible accounts opened (muted)
- **Columns** (right axis): eligible account volume per branch
  - Color: `#E8E8E8` light gray for non-focus branches, `#CCCCCC` slightly darker for the 3 focus branches
  - The focus branches are the 3 identified in the action title logic
- **Line 1** (left axis): Historical take rate per branch
  - Color: `#B0B0B0` (muted gray)
  - Line width: 2, dashed
  - Markers: small gray squares
- **Line 2** (left axis): L12M take rate per branch
  - Color: `#17A2B8` (accent teal)
  - Line width: 3, solid
  - Markers: teal circles, size 8
- **Branch labels:** rotated 45° if >6 branches, else horizontal
- **Focus highlighting:** the 3 driver branches get their X-axis label in **bold navy**; all others in regular gray
- **Legend:** top-right, "Historical / L12M" — horizontal, 2 items only (volume not in legend; it's self-evident)

**Annotation:** For each of the 3 focus branches, a small red delta marker showing the pp gap between historical and L12M, e.g. "−11pp".

### Callout (positioned bottom-center, spanning both panels)

**Template:** `Closing the gap at {b1}, {b2}, {b3} → ${delta_revenue}M annual uplift`

Hero number format: `$X.XM` (one decimal, millions). Accent color navy `#1E3D59`.
Sub-text 14pt: `annual debit interchange uplift`
Tertiary 12pt: `Based on closing to portfolio-median DCTR; assumes 0.8% of spend at average ticket`

### Footnote band

- **Source:** `Source: [client] ODD, {month} | Peer benchmark: credit unions $250M-$1B AUM (2024) | N = {eligible_count:,}`
- **Footer:** `{client_name}  |  {month}  |  Slide {n}  |  STRICTLY CONFIDENTIAL`

---

## Slide DCTR-MAIN-2 — Funnel Historical vs L12M

**Group ID:** `DCTR-MAIN-2`
**Layout:** TWO_CONTENT (9)
**Components:** A7.7 (historical funnel) + A7.8 (L12M funnel)

### Action title (template)

`Largest drop-off is at the {biggest_drop_stage} stage ({drop}%); {changed|unchanged} vs historical`

Examples:
- "Largest drop-off is at the Eligibility stage (−38%); unchanged vs historical"
- "Largest drop-off is at the Debit Activation stage (−24%); L12M is 7pp worse than historical"

**Logic:**
- Identify the stage-to-stage drop with the largest absolute % loss (same for historical and L12M)
- If same stage in both → "unchanged"
- If different stages → call out both
- If L12M drop is materially worse (>5pp) → flag "L12M is Xpp worse"

### Panel A (left) — Historical funnel

**Sub-title:** "Historical (all-time) conversion"

Existing `_render_funnel` output from `analytics/dctr/funnel.py`, restyled per `SLIDE_DESIGN.md`:

- All stages same navy `#1E3D59` fill
- Biggest-drop stage gets red border (2pt, `#DC3545`) AND the drop-off callout badge gets a red fill instead of white
- All conversion % labels in rounded white boxes with navy border
- Volume counts shown inside each box, 20pt bold white
- Stage labels left of boxes, 18pt semibold navy

### Panel B (right) — L12M funnel

**Sub-title:** "L12M conversion"

Identical style to Panel A.

**Trend overlay:** To the right of each L12M stage, a small delta vs historical in subtext: `+2% vs hist` (green) or `−7% vs hist` (red).

### Callout (below both funnels, spanning full width)

**Template:** `{biggest_drop_stage} drop = {drop_count:,} accounts / year not reaching debit activation. Lifting to peer median ({peer_rate}%) = +{recovery} accounts/yr`

Hero: `+{recovery:,}` accounts, accent teal.
Sub: `incremental active debit holders per year at peer-median conversion`

### Footnote band

- **Source:** `Source: [client] ODD, {month} | Peer benchmark median: {peer_rate}% at the {biggest_drop_stage} step`
- Standard footer.

---

## Slide DCTR-MAIN-3 — Value of a Debit Card

**Group ID:** `DCTR-MAIN-3`
**Layout:** CUSTOM (8), single-panel hero
**Components:** A11.1

### Action title (template)

`A single debit-card activation is worth ${per_card_value}/year; closing the DCTR gap is worth ${total_value:,}/year`

Example: "A single debit-card activation is worth $142/year; closing the DCTR gap is worth $3.2M/year"

### Hero layout

Left third of slide: one massive number + subtext.
- **Hero number:** `$142` — 64pt bold teal
- **Sub-text:** `annual value per activated debit card`
- **Tertiary:** `Based on avg interchange per card + avg deposit lift`

Right two-thirds: waterfall chart.

### Waterfall

Stages (left to right):
1. Baseline DCTR revenue (gray)
2. + Branches 1-3 uplift (green)
3. + Remaining branches to median (lighter green)
4. + New-account activation improvement (teal)
5. = Total opportunity (navy, bold bar)

Each bar labeled with $ delta and cumulative.

### Callout (bottom-right, below waterfall)

**Template:** `${total_value:,}/year is {mult}x the current debit program revenue`

Anchor: comparison to current state (makes the opportunity tangible).

### Footnote band

- **Source:** `Per-card value: avg interchange {ic}% of spend × avg swipe volume | Deposit lift: {lift}% median on debit-active vs non-debit accounts | Full methodology in Appendix M.3`
- Standard footer.

---

## Module-level work required

For this spec to be implementable, the following code changes are needed:

| Slide / panel | Current module | Required change |
|---|---|---|
| Slide 1 left | `analytics/dctr/trends.py` (A7.6a) | Add volume-column series behind the rate line; add historical reference line |
| Slide 1 right | `analytics/dctr/branches.py` (DCTR-7) | Rebuild as vertical combo: branches on X, volume columns + 2 rate lines (historical + L12M) |
| Slide 1 callout | all above | Compute gap contribution by branch (volume × rate delta), return top 3 as structured data on `ctx.results["dctr_7"]["gap_contributors"]` |
| Slide 2 both | `analytics/dctr/funnel.py` (A7.7, A7.8) | Add `biggest_drop_stage` + `drop_pct` to insights dict; compute historical-vs-L12M stage delta |
| Slide 3 | `analytics/value/analysis.py` (A11.1) | Structure waterfall stages as discrete items in `ctx.results["value_1"]["waterfall_stages"]`; compute per-card value separately from total |
| All | `output/deck_builder.py` | Read action-title templates from slide specs; populate with values from `ctx.results[...]`; render callout boxes and footnote bands per `SLIDE_DESIGN.md` |
| All | `charts/style.py` | Update color/typography defaults to match `SLIDE_DESIGN.md` §4-5 |

These changes are Session-2 work once the manifest + design doc are approved.
