# Mailer — Section Spec

**Section key:** `mailer`
**Accent:** `#3F88C5` (mid-blue, per SLIDE_DESIGN.md §5.1)
**Issue:** #154 (T2.5)

## Slides in this section

### A12.1 — Campaign performance summary
- **Template:** `mailer.campaign_performance`
- **Callout:** metric `Response rate`, value `mailer_summary.response_rate` formatted pct1, comparison "{n_recipients} sent → {n_conversions}"
- **Required ctx.results:** `mailer_summary.{n_campaigns,n_recipients,response_rate,n_conversions}`
- **Chart:** stacked bar by campaign — sent, opened, responded, converted
- **Drops if:** `mailer_summary.n_campaigns == 0` → `data_missing` (entire section drops; see SLIDE_DESIGN.md §12)

### A13.1 — Response rate ranking
- **Template:** `mailer.response_rate`
- **Callout:** metric `Top campaign`, value `mailer_top.response_rate` formatted pct1, comparison "{lift_pp} above avg"
- **Required ctx.results:** `mailer_top.{campaign_name,response_rate,lift_pp}`
- **Chart:** horizontal bar of campaigns sorted by response rate, top in section accent

### A15.1 — Segment performance
- **Template:** `mailer.segment_performance`
- **Callout:** metric `Top segment`, value `mailer_segments.top_segment_rate` formatted pct1, comparison "{lift_pp} above avg"
- **Required ctx.results:** `mailer_segments.{top_segment,top_segment_rate,top_segment_lift_pp}`
- **Chart:** small multiples — response rate by segment, ordered by lift

### A16.1 — ROI summary
- **Template:** `mailer.revenue_impact`
- **Callout:** metric `ROI`, value `mailer_roi.roi_multiple` formatted "Nx", comparison "${revenue}/{spend}"
- **Required ctx.results:** `mailer_roi.{revenue,roi_multiple,spend,window_months}`
- **Chart:** time-series — monthly mailer spend (gray) vs attributed revenue (accent)
