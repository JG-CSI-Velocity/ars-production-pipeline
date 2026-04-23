# Reg E — Main Deck Specification

**Governing doc:** `SLIDE_DESIGN.md`
**Manifest rows:** `ARS - RegE` sheet in `SLIDE_MANIFEST.xlsx` (rows marked Keep=Y)
**Section title (divider):** "Reg E Opt-In"
**Section lead-in:** "Where opt-in stands today, where concentration sits, and what expanding opt-in is worth in overdraft revenue."

Main deck = 3 content slides. Mirrors DCTR structure.

---

## Slide REGE-MAIN-1 — L12M Trajectory + Branch Gap

**Group ID:** `REGE-MAIN-1`
**Layout:** TWO_CONTENT (9)
**Components:** A8.3 (enhanced) + A8.4a (rebuilt)

### Action title (template)

`L12M Reg E opt-in of {l12m_rate}% {trails|matches|beats} historical by {|gap|}pp; {top_n} branches drive {contribution}% of the gap`

Examples:
- "L12M opt-in of 31% trails historical by 4pp; 4 branches drive 62% of the gap"
- "L12M opt-in of 42% matches historical; flat across all branches"

### Panel A (left) — Monthly combo

**Sub-title:** "L12M opt-in rate and eligible volume, by month"

Spec identical to DCTR Slide 1 Panel A, except:
- Left Y-axis: Opt-In % (0-100)
- Rate line series name: "L12M opt-in rate"
- Reference line: historical opt-in rate
- Volume columns: same muted gray
- Source chart: extend `analytics/rege/status.py` A8.3 with volume-bar overlay

### Panel B (right) — Branch combo

**Sub-title:** "Branch opt-in rate vs historical, by eligible volume"

Spec identical to DCTR Slide 1 Panel B, except:
- Data: branch-level Reg E opt-in rates (historical + L12M)
- Source chart: rebuild `analytics/rege/branches.py` A8.4a as vertical combo (currently horizontal bar)
- Focus logic: 3 branches with largest absolute contribution to the gap (or to the opportunity, if rate is up)

### Callout

**Template:** `Closing the gap at {b1}, {b2}, {b3} → ${overdraft_revenue}M annual overdraft uplift`

Hero: `$X.XM` navy.
Sub: `annual overdraft interchange + fees from incremental opt-ins`
Tertiary: `Based on closing to portfolio-median opt-in; assumes {od_per_optin} annual overdraft revenue per opted-in account`

### Footnote band

Standard; source should note the specific Reg E code column used (Reg E column detection per month varies).

---

## Slide REGE-MAIN-2 — Funnel All-Time vs TTM

**Group ID:** `REGE-MAIN-2`
**Layout:** TWO_CONTENT (9)
**Components:** A8.10 (all-time) + A8.11 (TTM)

### Action title (template)

`Largest drop-off is at the {biggest_drop_stage} stage ({drop}%); {changed|unchanged} vs all-time`

Logic identical to DCTR Slide 2 action-title logic.

### Panel A (left) — All-time funnel

**Sub-title:** "All-time opt-in conversion"

Restyled `_render_funnel` output from `analytics/rege/dimensions.py` A8.10, per `SLIDE_DESIGN.md`:
- All stages navy
- Biggest-drop stage: red border + red-filled drop-off badge
- Volume counts white inside box, 20pt bold
- Conversion % labels in white rounded boxes with navy border

### Panel B (right) — TTM funnel

**Sub-title:** "Last 12 months opt-in conversion"

Identical styling. Plus: delta-vs-all-time overlay at each stage (`+Xpp` green / `-Xpp` red).

### Callout

**Template:** `{biggest_drop_stage} drop = {drop_count:,} eligible accounts/year never opting in. At portfolio-median conversion, {recovery:,} additional opt-ins/year`

Hero: `+{recovery:,}` accent teal.
Sub: `incremental opt-ins per year at peer-median`

### Footnote band

- **Source:** Note peer benchmark + the fact that Reg E column auto-detects per month (cite the selected column for context).

---

## Slide REGE-MAIN-3 — Value of Reg E Opt-In

**Group ID:** `REGE-MAIN-3`
**Layout:** CUSTOM (8), single-panel hero
**Components:** A11.2

### Action title (template)

`A single Reg E opt-in is worth ${per_optin_value}/year; closing the opt-in gap is worth ${total_value:,}/year`

### Hero layout

Identical to DCTR Slide 3, different numbers:
- **Hero number:** per-opt-in value
- **Sub-text:** `annual value per opted-in account`
- **Tertiary:** `Based on overdraft frequency × avg overdraft fee, net of charge-offs`

### Waterfall

Stages:
1. Baseline overdraft revenue (gray)
2. + Branches 1-3 uplift (green)
3. + Remaining branches to median (lighter green)
4. + New-account opt-in flow improvement (teal)
5. = Total Reg E opportunity (navy bold)

### Callout

**Template:** `${total_value:,}/year is {mult}x the current Reg E revenue line`

### Footnote band

- **Source:** `Per-opt-in value: avg monthly OD frequency × avg OD fee × net-of-waives | Full methodology in Appendix M.4`

---

## Module-level work required

| Slide / panel | Current module | Required change |
|---|---|---|
| Slide 1 left | `analytics/rege/status.py` (A8.3) | Add volume-column series; add historical reference line |
| Slide 1 right | `analytics/rege/branches.py` (A8.4a) | Rebuild as vertical combo: branches on X, volume + 2 rate lines |
| Slide 1 callout | above | Compute gap contribution by branch; expose top 3 + revenue impact on `ctx.results` |
| Slide 2 both | `analytics/rege/dimensions.py` (A8.10, A8.11) | Add `biggest_drop_stage` + stage-delta to insights; style updates per §6.4 |
| Slide 3 | `analytics/value/analysis.py` (A11.2) | Structure waterfall stages; compute per-opt-in value separately |

All changes are Session-2 work.
