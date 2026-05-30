# Attrition — Section Spec

**Section key:** `attrition`
**Accent:** `#DC3545` (red, per SLIDE_DESIGN.md §5.1)
**Issue:** #154 (T2.5)

## Slides in this section

### A9.1 — Closure rate (current period)
- **Template:** `attrition.closure_rate`
- **Callout:** metric `Attrition`, value from `attrition_1.overall_rate` (pct), denominator "of {eligible_count} eligible", comparison "{n_closed} closures"
- **Required ctx.results:** `attrition_1.{overall_rate,n_closed,eligible_count}`
- **Chart:** rate-over-volume combo — closure count bars (gray), attrition rate line (red accent)
- **Drops if:** `attrition_1` missing → `data_missing`

### A9.2 — Peer comparison
- **Template:** `attrition.peer_comparison`
- **Callout:** metric `Rank`, value `attrition_peer.rank_ord`, comparison "vs {peer_median} median"
- **Required ctx.results:** `attrition_peer.{rate,rank_ord,n_peers,comparison_word,peer_median}`
- **Chart:** horizontal bar of client + 22 peers, client highlighted in section accent
- **Drops if:** `attrition_peer.n_peers < 5` → `threshold_not_met`

### A9.4 — Attrition by branch (consumed by branch_scorecard)
- **Callout:** metric `Worst branch`, value highest-attrition branch name, comparison "{attrition_rate} rate"
- **Required ctx.results:** `attrition_4.branch_df` (per-branch frame from upstream — issue #142 item 2.5)
- **Chart:** horizontal bar of branches by attrition rate, threshold line at portfolio rate
- **Drops if:** `attrition_4.branch_df` empty → `data_missing`

### A9.5 — Driver analysis
- **Template:** `attrition.driver_analysis`
- **Callout:** metric `Top driver`, value `attrition_drivers.top_driver`, comparison "{share} of closures"
- **Required ctx.results:** `attrition_drivers.{top_driver,top_driver_share,top_driver_segment,top_driver_segment_rate,multiple_of_baseline_word}`
- **Chart:** pareto bar of drivers + cumulative %

### A9.10 — Prevention opportunity
- **Template:** `attrition.prevention_opportunity`
- **Callout:** metric `Annual savings`, value `value_attrition.annual_savings` formatted usd_m, comparison "preventing {target_pct}"
- **Required ctx.results:** `value_attrition.{cost_per_closure,target_save_pct,annual_savings}`
- **Chart:** waterfall — current cost → preventable → residual
