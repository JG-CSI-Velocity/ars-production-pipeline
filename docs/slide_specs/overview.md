# Overview — Section Spec

**Section key:** `overview`
**Accent:** `#1E3D59` (navy, per SLIDE_DESIGN.md §5.1)
**Issue:** #154 (T2.5)

## Slides in this section

### A1 — Portfolio composition
- **Template:** `overview.portfolio_snapshot`
- **Callout:** metric `Eligible accounts`, value from `dctr_1.eligible_count`, denominator "of {open_count} open accounts", comparison "{pct_eligible} of book"
- **Required ctx.results:** `dctr_1.eligible_count`, `dctr_1.eligible_pct`, `dctr_1.open_count`
- **Chart:** stacked bar (eligible vs ineligible by segment); accent navy for eligible, neutral gray for ineligible
- **Drops if:** `dctr_1` not populated → drop_reason=`data_missing`

### A1.1 — Three-metric summary
- **Template:** `overview.performance_summary`
- **Callout:** metric `Trend`, value from `overview_summary.headline_pct`, comparison `overview_summary.direction_word`
- **Required ctx.results:** `dctr_1.rate`, `reg_e_1.rate`, `attrition_1.overall_rate`, `overview_summary.direction_word`
- **Chart:** three KPI tiles (DCTR, Reg E, Attrition) with directional arrows

### A3 — Top segment highlight
- **Template:** `overview.segment_highlight`
- **Callout:** metric `Top segment`, value `overview_segments.top_segment`, comparison `{share_word}`
- **Required ctx.results:** `overview_segments.{top_segment,top_segment_share,top_segment_revenue_share}`
- **Chart:** horizontal bar of segment revenue share vs population share
- **Drops if:** fewer than 3 segments → `threshold_not_met`

### A3.1 — Eligible YoY trend
- **Template:** `overview.trend`
- **Callout:** metric `Eligible YoY`, value `overview_yoy.yoy_change` formatted pct1, comparison "{direction} from {eligible_prior}"
- **Required ctx.results:** `overview_yoy.{direction_word,yoy_change,eligible_now,eligible_prior}`
- **Chart:** time-series line, 24 months, accent teal for current
