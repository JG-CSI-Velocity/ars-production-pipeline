# Insights — Section Spec

**Section key:** `insights`
**Accent:** `#555555` (charcoal, per SLIDE_DESIGN.md §5.1 — subdued so numbers stand out)
**Issue:** #154 (T2.5)

## Slides in this section

### S1 — Top revenue lever
- **Template:** `insights.top_insight`
- **Callout:** metric `Lever`, value `s1.lever_value` formatted usd_m, comparison `s1.realistic_close_qual`
- **Required ctx.results:** `s1.{lever_label,lever_value,realistic_close_qual}`
- **Chart:** none (text-heavy slide; uses kpi_hero layout)
- **Drops if:** total opportunity computed but no single lever > 30% share → reason `threshold_not_met`

### S2 — Highest-leverage segment
- **Template:** `insights.growth_driver`
- **Callout:** metric `Target segment`, value `s2.best_segment`, comparison "{segment_rate} {segment_metric}"
- **Required ctx.results:** `s2.{best_segment,segment_rate,segment_metric,segment_share_word}`
- **Chart:** scatter — segment population (x) vs opportunity per account (y), best segment highlighted

### S3 — Emerging risk indicator
- **Template:** `insights.risk_indicator`
- **Callout:** metric `Risk signal`, value `s3.signal_label`, comparison "{metric_value} vs {metric_prior}"
- **Required ctx.results:** `s3.{signal_label,metric_value,metric_prior,risk_qual}`
- **Chart:** time-series — risk metric over 12 months with threshold band

### S6 — Opportunity map (kept from S-series)
- **Callout:** metric `Top 3 levers`, value list of three short labels
- **Required ctx.results:** `s6.opportunities` (list of dicts with name, value, qual)
- **Chart:** quadrant — opportunity ($M) vs realism (qualitative)

### S7 — What-if simulator (DCTR)
- **Callout:** metric `If DCTR = peer median`, value modeled revenue lift
- **Required ctx.results:** `s7.{baseline_revenue,peer_modeled_revenue,delta}`
- **Chart:** dual bars — baseline vs scenario

### S8 — Top 3 recommendations
- **Template:** `insights.recommendation_headline`
- **Callout:** metric `Combined value`, value `s8.combined_value` formatted usd_m, comparison "3 actions"
- **Required ctx.results:** `s8.{action_1,action_2,action_3,combined_value}`
- **Chart:** three callout cards stacked, accent navy
