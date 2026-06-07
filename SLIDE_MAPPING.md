# Master Slide Mapping Document

## CSI Template Spec

**Template:** `2025-CSI-PPT-Template.pptx`
**Dimensions:** 13.33" x 7.5" (widescreen 16:9)
**Font Family:** Montserrat
- Headings: Montserrat ExtraBold
- Body: Montserrat Regular

### Available Layouts

| Index | Name | Placeholders | Use For |
|-------|------|-------------|---------|
| 0 | Title Slide | Title + Subtitle | Generic title slide |
| 1 | Title Slide_Reverse | Title + Subtitle | Alt title (dark bg) |
| 2 | Title and Content | Title + Content | Standard chart/data slide |
| 3 | Title and Content_Reverse | Title + Content | Alt color chart slide |
| 4 | 2_Section Header | Title + Text | Section divider (teal) |
| 5 | 5_Section Header | Title + Text | Section divider (alt) |
| 6 | 3_Section Header_Gray Bkgrnd | Title + Text | Section divider (gray) |
| 7 | 2_Title Slide | Title + Subtitle | Secondary title |
| 8 | Custom Layout | Title only | Chart-only slide (full bleed) |
| 9 | Two Content | Title + 2 Content | Side-by-side comparison |
| 10 | Comparison | Title + 2 Headers + 2 Content | Labeled comparison |
| 11 | Blank | (none) | Full custom / image only |
| 13 | Picture with Content | Title + Picture + Text | Chart + commentary |
| 16 | 1_Title and Content | Title only (wide) | Wide chart slide |
| 17 | 1_Title Slide_RPE | Title + Subtitle | RPE product title |
| 18 | 4_Title Slide_ARS | Title + Subtitle | ARS product title |
| 19 | 5_Title Slide_ICS | Title + Subtitle | ICS product title |

### Font Sizing Standards

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Slide title (conclusion headline) | Montserrat | 20pt | ExtraBold |
| Subtitle / annotation | Montserrat | 14pt | Regular |
| Chart title (on image) | Montserrat | 18pt | Bold |
| Chart subtitle | Montserrat | 12pt | Regular |
| Data labels | Montserrat | 11pt | Regular |
| Axis labels | Montserrat | 10pt | Regular |
| Footnotes | Montserrat | 9pt | Regular |
| KPI hero number | Montserrat | 36pt | ExtraBold |
| KPI label | Montserrat | 11pt | Regular |

### Color System

| Name | Hex | Usage |
|------|-----|-------|
| Navy | #1A1A1A | Primary, emphasis, section dividers |
| Teal | #0D9488 | Positive, growth, success |
| Coral | #E74C3C | Negative, decline, warning |
| Amber | #F39C12 | Caution, transitional |
| Gray | #95A5A6 | Neutral, inactive, de-emphasized |
| Slate | #6B7280 | Body text, secondary |
| White | #FFFFFF | Backgrounds, contrast text |

**Rule:** One focal color per chart. Everything else muted to alpha=0.3.

---

## Slide Construction Rules

### Every Slide Has Three Layers

```
TOP:     Conclusion headline (complete sentence stating the finding)
MIDDLE:  Data visual (chart rendered as PNG at 150 DPI)
BOTTOM:  Business implication (speaker note or annotation)
```

### Headline Rules

- Complete sentence with metric, magnitude, and direction
- BAD: "Debit Card Penetration by Branch"
- GOOD: "Three branches account for 62% of debit growth, led by Main Office at 23%"
- Template: `[Metric] [changed] by [X%] due to [driver], resulting in [impact]`

### Chart Rendering

- Figure size: `figsize=(13, 7)` to match slide dimensions
- DPI: 150
- Font in charts: Montserrat (set via matplotlib rcParams)
- Direct labels on data points (no legends when possible)
- Highlight focal series at full opacity, mute others to alpha=0.3
- Remove gridlines, borders, decorative elements

---

## ARS Module -> Slide Mapping (22 modules)

### Section 1: Overview

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `overview.stat_codes` | "{X}% of accounts are open and eligible for the ARS program" | Horizontal bar (status breakdown) | 2 |
| `overview.product_codes` | "{Product} accounts represent {X}% of the eligible portfolio" | Horizontal bar (product mix) | 2 |
| `overview.eligibility` | "{N:,} accounts are eligible -- {X}% of total portfolio" | KPI cards + donut | 2 |

### Section 2: Debit Card Throughput (DCTR)

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `dctr.penetration` | "{X}% of eligible accounts actively use their debit card" | Stacked bar (active vs inactive) | 2 |
| `dctr.trends` | "Card usage {increased/decreased} {X}% over the past 12 months" | Line chart (monthly trend) | 2 |
| `dctr.branches` | "{Branch} leads with {X}% penetration -- {Branch} trails at {Y}%" | Horizontal bar (ranked by branch) | 2 |
| `dctr.funnel` | "Of {N:,} eligible accounts, {X}% have activated their card" | Funnel chart (eligible > enrolled > active) | 2 |
| `dctr.overlays` | "PIN transactions account for {X}% of volume, but only {Y}% of spend" | Grouped bar (PIN vs SIG by volume and spend) | 9 |

### Section 3: Reg E / Overdraft

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `rege.status` | "{X}% of accounts are opted in to Reg E, generating ${Y:,} in OD fees" | Stacked bar + KPI | 2 |
| `rege.branches` | "Reg E opt-in varies from {low}% to {high}% across branches" | Horizontal bar (by branch) | 2 |
| `rege.dimensions` | "Accounts opened in the last 2 years have {X}% higher opt-in rates" | Grouped bar (by age, product, tenure) | 2 |

### Section 4: Attrition

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `attrition.rates` | "{N:,} accounts closed this period -- {X}% annualized attrition rate" | Line chart (monthly closures) + KPI | 2 |
| `attrition.dimensions` | "Accounts under 2 years old close at {X}x the rate of established accounts" | Grouped bar (by age, product) | 2 |
| `attrition.impact` | "Closed accounts represented ${Y:,} in annual interchange revenue" | Waterfall chart | 2 |

### Section 5: Mailer Campaign

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `mailer.insights` | "ARS program mailed {N:,} accounts across {W} waves with {X}% overall response" | KPI cards (mailed, responded, rate) | 2 |
| `mailer.response` | "{Segment} achieved the highest response rate at {X}%" | Grouped bar (rate by segment per wave) | 2 |
| `mailer.impact` | "Responders increased monthly spend by ${X:,.0f} -- a {Y}% lift over non-responders" | Before/after grouped bar | 9 |
| `mailer.cohort` | "Each mail wave added {N:,} activated accounts to the portfolio" | Stacked area (cumulative by cohort) | 2 |
| `mailer.reach` | "Program has reached {X}% of the eligible portfolio through {W} waves" | Line chart (cumulative penetration) | 2 |

### Section 6: Value

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `value.analysis` | "ARS program generated an estimated ${X:,} in incremental interchange revenue" | Waterfall or cascade chart | 2 |

### Section 7: Insights

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| `insights.synthesis` | "Key Finding: [top insight from all modules]" | Bullet summary | 12 |
| `insights.conclusions` | "[N] recommended actions to improve program performance" | Numbered list | 12 |
| `insights.effectiveness` | "Program ROI: ${X} revenue per $1 invested in mailer costs" | KPI card | 2 |
| `insights.branch_scorecard` | "{Branch} is the top-performing branch across {N} of {M} metrics" | Heatmap or scorecard table | 8 |
| `insights.dormant` | "{N:,} dormant accounts represent ${X:,} in recoverable interchange" | Bar chart (dormant segmented by potential) | 2 |

---

## TXN Module -> Slide Mapping (35 modules across 22 sections)

### Section 01: Portfolio Overview

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Portfolio KPIs | "{N:,} active accounts generated ${X:,} in total spend" | KPI hero cards (6) | 2 |
| Engagement Tiers | "{X}% of accounts are in the top two engagement tiers" | Stacked bar (tier distribution) | 2 |
| Demographics | "Members aged {range} account for {X}% of total spend" | Horizontal bar (age bands) | 2 |
| Seasonal Patterns | "Spend peaks in {month} and troughs in {month}" | Line chart (12-month trend) | 2 |

### Section 02-05: Merchant Analysis

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Top Merchants | "{Merchant} captures {X}% of all debit transactions" | Horizontal bar (top 15) | 2 |
| Merchant Concentration | "Top 10 merchants account for {X}% of total spend" | Pareto (cumulative %) | 2 |
| MCC Categories | "{Category} is the largest spend category at ${X:,}" | Treemap or horizontal bar | 2 |
| Business vs Personal | "Business accounts average ${X:,}/mo vs ${Y:,} for personal" | Grouped bar | 9 |

### Section 06: Competition

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Competitor Detection | "{N:,} accounts transact at {N} competitor institutions" | KPI + list | 2 |
| Wallet Share | "Competitors capture ${X:,} annually from your members" | Horizontal bar (by competitor) | 2 |
| Threat Quadrant | "{Competitor} is high-frequency, high-spend -- the biggest threat" | Scatter (frequency vs spend) | 8 |

### Section 07: Financial Services

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| FI Transactions | "${X:,} flows to other financial institutions monthly" | Horizontal bar | 2 |
| Leakage Analysis | "Member funds leaving to {FI} total ${X:,} annually" | Waterfall | 2 |

### Section 09: ARS Campaign (same as ARS modules above)

### Section 10: Branch Performance

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Branch Rankings | "{Branch} leads in {metric} -- {Branch} needs attention" | Horizontal bar (ranked) | 2 |
| Branch Spend Profile | "Average monthly spend ranges from ${low} to ${high} across branches" | Box plot or bar | 2 |

### Section 11: Transaction Type

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| PIN vs SIG Split | "PIN transactions are {X}% of volume but {Y}% of spend" | Stacked bar (by type) | 2 |
| Payment Channels | "{Channel} usage grew {X}% year-over-year" | Grouped bar or line | 2 |

### Section 13: Attrition (same as ARS attrition)

### Section 14: Balance

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Balance Bands | "{X}% of accounts have balances under ${threshold}" | Histogram or bar | 2 |
| PFI Scoring | "{N:,} accounts show primary financial institution behavior" | KPI + distribution | 2 |

### Section 15: Interchange

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Interchange Revenue | "Total interchange: ${X:,} -- PIN: ${P:,}, SIG: ${S:,}" | Stacked bar (PIN vs SIG) | 2 |
| Opportunity Gap | "Shifting {X}% of PIN to signature would add ${Y:,} in revenue" | Waterfall | 2 |

### Section 22: Executive Scorecard

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Scorecard | "Overall program health: {rating} -- {N} of {M} metrics trending positive" | RAG heatmap table | 8 |
| Strategic Priorities | "Top 3 priorities for the next quarter" | Numbered list | 12 |

---

## ICS Module -> Slide Mapping

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| ICS Overview | "{N:,} accounts have ICS -- {X}% of eligible portfolio" | KPI + donut | 2 |
| Source Analysis | "Direct mail drives {X}% of ICS enrollments vs {Y}% referral" | Stacked bar | 2 |
| Channel Performance | "{Channel} converts at {X}% -- {N:,} enrollments this period" | Horizontal bar | 2 |
| Branch ICS | "{Branch} has the highest ICS penetration at {X}%" | Horizontal bar (ranked) | 2 |
| Product Mix | "ICS accounts are {X}% {Product} -- skewing toward {type}" | Stacked bar | 2 |
| Tenure Analysis | "ICS accounts average {X} years older than non-ICS" | Grouped bar (age comparison) | 2 |
| Revenue Impact | "ICS accounts generate ${X} more in annual interchange" | Bar + delta annotation | 2 |
| Referral Intelligence | "{N:,} referral opportunities identified across {B} branches" | Horizontal bar + KPI | 2 |

---

## Deposits Module -> Slide Mapping

| Module | Slide Title Pattern | Chart Type | Layout |
|--------|-------------------|------------|--------|
| Portfolio Baseline | "Median monthly deposits: ${X:,} across {N:,} accounts" | KPI cards | 2 |
| Tier Analysis | "{Tier} accounts deposit ${X:,}/mo -- {Y}x the portfolio median" | Horizontal bar (by tier) | 2 |
| Campaign Response | "{X}% response rate across {W} waves -- {Segment} highest at {Y}%" | Grouped bar (by segment per wave) | 2 |
| Cohort DID | "Responders increased deposits by ${X:,}/mo vs ${Y:,} for non-responders" | Before/after grouped bar | 9 |
| Deposit Lift by Offer | "Deposits increased after {N} of {M} offers" | Grouped bar (pre vs post per offer) | 2 |
| Deposit Lift by Segment | "{Segment} shows the strongest deposit lift at +{X}%" | Grouped bar (by segment) | 2 |
| Distribution (Box Plot) | "Deposit distribution shifted upward for {Segment}" | Box plot (pre vs post) | 8 |
| Responder Trajectory | "First-time responders show sustained deposit growth at +6 months" | Line chart (trajectory) | 2 |

---

## Deck Assembly Order

### ARS Deck

1. Title slide (Layout 18: ARS title)
2. Section: Program Overview (Layout 4: section divider)
3. Eligibility, Stat Codes, Product Codes
4. Section: Card Usage (Layout 4)
5. DCTR slides (5)
6. Section: Risk & Compliance (Layout 4)
7. Reg E slides (3), Attrition slides (3)
8. Section: Campaign Performance (Layout 4)
9. Mailer slides (5)
10. Section: Value & Recommendations (Layout 4)
11. Value slide, Insights slides (5)

### TXN Deck

1. Title slide (Layout 17: RPE title)
2. Section: Portfolio Overview (Layout 4)
3. Portfolio slides (4)
4. Section: Merchant Intelligence (Layout 4)
5. Merchant slides (4)
6. Section: Competitive Landscape (Layout 4)
7. Competition slides (3)
8. Section: Operations (Layout 4)
9. Branch, Transaction Type, Product, Interchange slides
10. Section: Risk & Retention (Layout 4)
11. Attrition, Balance slides
12. Section: Executive Summary (Layout 4)
13. Scorecard, Priorities

### ICS Deck

1. Title slide (Layout 19: ICS title)
2. All ICS slides in order

### Deposits Deck

1. Title slide (Layout 18: ARS title -- deposits is ARS-adjacent)
2. Section: Deposit Baseline
3. Baseline + Tier slides
4. Section: Campaign Impact on Deposits
5. Campaign, DID, Lift slides
6. Section: Evidence
7. Distribution, Trajectory slides

---

## Adding a New Module

1. Create analysis function that returns `AnalysisResult` with chart + data
2. Register with `@register` decorator in `analytics/`
3. Add to `MODULE_ORDER` in `registry.py`
4. Add a row to the appropriate section in this mapping doc
5. Define: headline pattern, chart type, layout index
6. The deck builder picks it up automatically

### Headline Template by Category

| Category | Template |
|----------|----------|
| Program Overview | "{N:,} [accounts/members] are [status] -- {X}% of [total]" |
| Growth | "[Metric] [grew/increased] by {X}% [timeframe], driven by [driver]" |
| Engagement | "{X}% of [group] are [actively/not] [doing thing]" |
| Attrition | "{N:,} [accounts] [closed/left] -- equivalent to [operational comparison]" |
| Performance | "[Entity] leads at {X}% -- [Entity] trails at {Y}%" |
| Revenue | "[Program] generated ${X:,} in [revenue type] -- a {Y}% [increase]" |
| Recommendations | "[N] [actions/opportunities] identified to [improve/recover] [metric]" |
