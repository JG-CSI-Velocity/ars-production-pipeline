# Slide Design Principles

This document defines the design framework for every client-facing deck produced by this pipeline. It is the single source of truth — if chat feedback contradicts this file, update the file first.

The target standard is **top-tier management consulting** (McKinsey / Bain / BCG). Every slide should be defensible as a standalone artifact a partner would put in front of a CEO.

---

## 1. Philosophy

### 1.1 Pyramid principle
Every slide answers **one question**. The reader should not have to infer what they're looking at. If a slide is trying to convey two ideas, it's two slides.

### 1.2 Action titles
The title is the **insight**, not the category.

- ❌ "Account Composition"
- ✅ "89% of accounts are personal — business segment represents a $Xm underpenetrated opportunity"

- ❌ "DCTR by Branch"
- ✅ "L12M DCTR trails historical by 8pp; 3 branches drive 70% of the gap"

- ❌ "L12M Funnel"
- ✅ "Eligibility step is the largest drop-off (−38%); no improvement vs historical"

Every title must be a **complete sentence with a verb** that states the finding. If the title does not change between clients, it is the wrong title.

### 1.3 SCQA narrative arc
The deck tells one story in four acts:

| Act | Content | Slides |
|---|---|---|
| **Situation** | Who the client is, what we looked at | Cover + context |
| **Complication** | What we found | Exec summary + section headers |
| **Question** | What the client should do | Implicit in each section |
| **Answer** | Recommendations + quantified value | Value slides + call-to-action |

### 1.4 So-what first
The reader should know **what to do about it** within 5 seconds of looking at the slide. The chart supports the so-what; the so-what does not wait for the reader to decode the chart.

Every slide has:
- An action title (the so-what)
- A callout box or emphasized annotation (the key number)
- Supporting visual evidence (the chart)
- A methodology footer (the defensibility)

### 1.5 Data-ink ratio
Remove anything that does not earn its place:

- No 3D charts, ever.
- No chart junk (shadows, gradients, drop shadows on text, unnecessary borders).
- Gridlines only if they help read values. Usually no.
- Legends only if there are 2+ series. For single-series charts, the title and axis labels suffice.
- Color is information, not decoration. If two bars are the same color, they represent the same thing. If two are different colors, the difference means something.

### 1.6 Emphasis through contrast
Use color to direct the eye to the insight. The chart might show 20 branches; 3 are highlighted in teal and 17 are gray. The reader's eye goes where the insight is.

---

## 2. Deck structure

Every engagement deck follows this skeleton:

```
1. Cover                          (client name, engagement, date, confidentiality)
2. Executive summary              (1 slide, 3-5 bullets, all findings + recommendations)
3. Agenda                         (optional; skip for decks <20 slides)
4. Context                        (1-2 slides: portfolio snapshot, scope, methodology)
5. [Section divider]              (tells the reader what this section covers + why)
   └ Section content              (3-5 slides, each answering one question)
6. [Section divider]
   └ Section content
... (repeat per workstream)
7. Summary of recommendations     (what to do, sized by impact, sequenced)
8. Next steps                     (what we propose next)
9. Appendix                       (everything the main deck had to cut)
10. Methodology appendix          (data sources, assumptions, benchmark definitions)
```

**Hard rule: main deck ≤ 25 slides** (excluding appendix). More than that and the client stops reading.

---

## 3. Slide anatomy

Every content slide has four regions. They are always in the same place:

```
┌────────────────────────────────────────────────────────────┐
│  ACTION TITLE (the so-what, 1-2 lines, left-aligned)       │  <- 18-20% of slide height
├────────────────────────────────────────────────────────────┤
│                                                            │
│                                                            │
│   CHART / VISUAL EVIDENCE                                  │  <- 60-65% of slide height
│                                                            │
│        ┌──────────────────────────────────┐                │
│        │  CALLOUT BOX (key number + text) │                │  <- overlays or sits below
│        └──────────────────────────────────┘                │
│                                                            │
├────────────────────────────────────────────────────────────┤
│  SOURCE: ... | METHODOLOGY: ... | N = ...                  │  <- footnote band, 8-9pt
│  Client | Date | Page # | STRICTLY CONFIDENTIAL            │  <- footer, 8pt
└────────────────────────────────────────────────────────────┘
```

For 2-up slides, the action title spans both panels and each panel has a sub-title (descriptive, not action — the action is already in the main title).

For KPI/cover slides, the callout box becomes the central element and the chart shrinks or disappears.

---

## 4. Typography

| Element | Font | Size | Weight | Color |
|---|---|---|---|---|
| Action title | Arial | 24pt | Bold | `#1E3D59` (navy) |
| Sub-title (panel header) | Arial | 16pt | Semibold | `#1E3D59` |
| Body text | Arial | 12pt | Regular | `#333333` |
| Callout number | Arial | 32-44pt | Bold | accent color |
| Callout text | Arial | 14pt | Semibold | `#1E3D59` |
| Chart axis / tick labels | Arial | 11-12pt | Regular | `#555555` |
| Chart data labels | Arial | 11pt | Bold | series color or `#333333` |
| Footnote / source | Arial | 9pt | Italic | `#777777` |
| Footer (confidentiality) | Arial | 8pt | Regular | `#999999` |

**No more than 4 text sizes on a single slide.** More than that looks amateur.

---

## 5. Color system

| Role | Hex | Usage |
|---|---|---|
| **Primary** (navy) | `#1E3D59` | Titles, primary bars, axis lines |
| **Accent teal** | `#17A2B8` | Focus series, "our" data, L12M line |
| **Secondary teal** | `#6FB3C0` | Secondary series (when needed alongside primary teal) |
| **Positive** | `#28A745` | Favorable outcomes, opportunity |
| **Negative** | `#DC3545` | Unfavorable outcomes, drop-offs, attrition |
| **Warning** | `#FFC107` | Flags, attention-needed |
| **Muted gray** | `#B0B0B0` | Historical baseline, non-emphasized series |
| **Light gray** | `#E8E8E8` | Gridlines, volume bars (behind rate lines) |
| **Dark text** | `#333333` | Body text |
| **Light text** | `#777777` | Footnotes, axis labels |
| **Background** | `#FFFFFF` | Slide background. Never colored. |

**Rules:**
- The deck never uses more than 4 colors on a single slide (besides neutrals).
- Red is reserved for "bad" — never use it for a neutral series.
- Volume bars behind rate lines are always muted gray so the rate line is primary.
- Historical baselines are always muted gray; L12M or "current" is always accent teal.

---

## 6. Chart rules

### 6.1 General
- No 3D.
- No chart-junk fill patterns.
- Origin at zero unless there's a reason otherwise (and then, explicit annotation).
- Y-axis labels use the same units as the data (%, $, count) — no "Values".
- X-axis labels are rotated 0° if they fit, else 45° (never 90°).
- If data is time-series, the most recent period is on the right. Always.

### 6.2 Rate + volume combo (our signature chart)
- Volume = columns, muted gray (`#E8E8E8`), right Y-axis
- Rate line = accent teal (`#17A2B8`), left Y-axis, line width 3, markers on every point
- Historical rate (when present) = muted gray (`#B0B0B0`), dashed line, no markers
- Both Y-axes labeled with units
- Rate line is always drawn last so it sits on top

### 6.3 Comparison
- Always sort ascending or descending by the value being compared, unless a natural order exists (months, segments).
- Highlight the 2-3 bars that carry the insight; gray out the rest.
- Annotate the hero bars with the number inline.

### 6.4 Funnel
- 4-5 stages max.
- Drop-off between stages labeled in red inside a rounded callout.
- The largest drop-off stage gets extra visual weight (bold label, color accent).
- Total volume shown at the top; conversion % shown at each step.

### 6.5 Hero / value slide
- One number. Big. Center.
- Sub-number (supporting evidence, e.g., "of $45M potential").
- Two or three bullet points explaining the math.
- Waterfall chart for breakdowns, with "drivers" labeled.

---

## 7. Callout boxes

Every content slide has one callout. Format:

```
┌─────────────────────────────────────┐
│  +$3.2M                             │   <- Hero number (accent color, 32pt bold)
│  annual revenue                     │   <- 14pt semibold
│  from closing branch DCTR gap       │   <- 12pt regular
└─────────────────────────────────────┘
```

- Hero number is always visible from 10 feet away.
- Two-line sub-label max.
- Always anchored to a specific action the client can take.
- Not a vague observation.

❌ "Performance is below average"  
✅ "Lifting 3 branches to portfolio median = $3.2M annual uplift"

---

## 8. Footer band (every slide)

Two lines:

1. **Source/methodology**: `Source: [client] ODD file, <month> | Peer benchmark: credit unions $250M-$1B AUM (2024) | N = <count>` — 9pt italic
2. **Footer**: `<Client Name>  |  <Month YYYY>  |  Slide <page>  |  STRICTLY CONFIDENTIAL` — 8pt regular

---

## 9. Section dividers

Full-bleed navy background. Left-aligned text. Three elements:

- **Section number** (in teal): `02`
- **Section title** (white, 36pt bold): "Debit Card Take Rate"
- **Lead-in sentence** (white, 18pt regular): "Current penetration, where opportunity sits, and what closing the gap is worth."

No charts, no logos, no ornamentation.

---

## 10. Naming and numbering

- Slides are numbered in the footer. Never in the title.
- Sections are numbered (01, 02, 03) matching the divider.
- Appendix slides prefix with "A." (A1, A2, ...) in the footer, not body.
- Exhibits inside a slide use lettered sub-labels (panel a, panel b) NEVER "left" / "right" in the title.

---

## 11. Per-section application

Per-slide specs live in `docs/slide_specs/` (one markdown file per section). Each spec references:
- The source `AnalysisResult.slide_id`(s)
- The Group ID from `SLIDE_MANIFEST.xlsx`
- The action title template (with placeholders for client-specific data)
- The callout template
- Any chart enhancements required vs what the analytics module currently produces

See `docs/slide_specs/dctr.md` for the first example.

---

## 12. What this does not cover

- Specific PPTX template layout XML — that lives in `01_Analysis/00-Scripts/output/template/`
- Chart style defaults — those live in `01_Analysis/00-Scripts/charts/style.py`. Any deviation from this document is a bug in style.py.
- Dynamic text generation (action titles with real numbers) — that's a job for `deck_builder.py`, driven by the per-slide specs.

---

## 13. When to update this document

- New design decision → update here FIRST, then update code.
- Client pushes back on something → capture the rule here so it persists across engagements and sessions.
- New chart type added → document its rules in §6 before shipping.

The rule is simple: **if it's not in this file, it's not a standard.** Anything that's "just the way we do it" should be codified here within a session of noticing it.
