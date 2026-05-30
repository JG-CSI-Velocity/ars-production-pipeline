# Action Title Templates

**Issue:** #150 (T2.1)
**Consumed by:** `01_Analysis/00-Scripts/output/action_title_populator.py` (T2.2 / #151)
**Authority:** SLIDE_DESIGN.md §1.2 (action titles state the so-what, not the metric category)

## How this file is used

`ActionTitlePopulator._load_templates()` parses every template block below and indexes them by `id`. At slide-composition time the populator looks up the template for a slide via its mapping in `docs/slide_specs/<section>.md` (T2.5), resolves the placeholders against `ctx.results`, and substitutes the formatted values into the template.

Each template block has:
- **`id`** — unique key the populator looks up
- **`section`** — one of the §5.1 section keys
- **`template`** — the action-title sentence with `{placeholder}` slots
- **`placeholders`** — table mapping each `{placeholder}` to a dotted `ctx.results` path + format hint
- **`example`** — fully populated example so the catalog is reviewable without running the pipeline
- **`fallback`** — sentence used when any required placeholder resolves to `None` (the populator never crashes; it falls back gracefully)

Formats supported (from `_format_value`):
| Format | Input | Output |
|---|---|---|
| `pct` | `0.342` | `34%` |
| `pct1` | `0.342` | `34.2%` |
| `pp` | `0.034` | `+3.4 pp` |
| `pp_signed` | `-0.034` | `−3.4 pp` |
| `int` | `12400` | `12,400` |
| `usd` | `142000` | `$142K` |
| `usd_m` | `2400000` | `$2.4M` |
| `usd_signed` | `-12400` | `−$12K` |
| `str` | passthrough | passthrough |

Date formats (`mo_yyyy`, `iso_date`) and ordinal (`ord`, e.g. `2nd quartile`) reserved for T2.5 expansion.

---

## Overview (4)

### `overview.portfolio_snapshot`
- **section:** `overview`
- **template:** "{client_name} has {n_eligible} eligible accounts driving {pct_eligible} of the portfolio — the foundation for every metric in this deck."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |
  | `pct_eligible` | `dctr_1.eligible_pct` | `pct` |
- **example:** "Guardians Credit Union has 12,400 eligible accounts driving 78% of the portfolio — the foundation for every metric in this deck."
- **fallback:** "{client_name} portfolio composition by eligibility."

### `overview.performance_summary`
- **section:** `overview`
- **template:** "Three metrics tell the story: DCTR at {dctr_rate}, Reg E opt-in at {rege_rate}, attrition at {attr_rate} — {direction} relative to last review."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `rege_rate` | `reg_e_1.rate` | `pct` |
  | `attr_rate` | `attrition_1.overall_rate` | `pct` |
  | `direction` | `overview_summary.direction_word` | `str` |
- **example:** "Three metrics tell the story: DCTR at 34%, Reg E opt-in at 22%, attrition at 7.1% — improving relative to last review."
- **fallback:** "DCTR, Reg E, and attrition snapshot."

### `overview.segment_highlight`
- **section:** `overview`
- **template:** "{top_segment} accounts make up {pct_top_segment} of the eligible book but generate {pct_top_segment_revenue} of revenue — concentrate retention here first."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `top_segment` | `overview_segments.top_segment` | `str` |
  | `pct_top_segment` | `overview_segments.top_segment_share` | `pct` |
  | `pct_top_segment_revenue` | `overview_segments.top_segment_revenue_share` | `pct` |
- **example:** "Tenured personal accounts make up 28% of the eligible book but generate 47% of revenue — concentrate retention here first."
- **fallback:** "Top segment by share of eligible accounts."

### `overview.trend`
- **section:** `overview`
- **template:** "Eligible accounts {direction} {pct_change} year-over-year ({n_eligible_now} this period vs {n_eligible_prior} last year)."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `direction` | `overview_yoy.direction_word` | `str` |
  | `pct_change` | `overview_yoy.yoy_change` | `pct1` |
  | `n_eligible_now` | `overview_yoy.eligible_now` | `int` |
  | `n_eligible_prior` | `overview_yoy.eligible_prior` | `int` |
- **example:** "Eligible accounts grew 4.2% year-over-year (12,400 this period vs 11,900 last year)."
- **fallback:** "Eligible account year-over-year trend."

---

## DCTR (4)

### `dctr.activation_baseline`
- **section:** `dctr`
- **template:** "{client_name} debit-card take rate sits at {dctr_rate} of {n_eligible} eligible accounts — {gap_pp} below peer median."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |
  | `gap_pp` | `dctr_1.peer_gap_pp` | `pp` |
- **example:** "Guardians Credit Union debit-card take rate sits at 34% of 12,400 eligible accounts — 7 pp below peer median."
- **fallback:** "Debit card take rate — current period."

### `dctr.peer_comparison`
- **section:** `dctr`
- **template:** "DCTR of {dctr_rate} ranks {rank_ord} of {n_peers} peer credit unions — closing to median would add {opportunity_usd_m} in annual revenue."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_peer.rate` | `pct` |
  | `rank_ord` | `dctr_peer.rank_ord` | `str` |
  | `n_peers` | `dctr_peer.n_peers` | `int` |
  | `opportunity_usd_m` | `value_1.dctr_gap_value` | `usd_m` |
- **example:** "DCTR of 34% ranks 14th of 22 peer credit unions — closing to median would add $2.4M in annual revenue."
- **fallback:** "DCTR peer comparison."

### `dctr.growth_driver`
- **section:** `dctr`
- **template:** "{top_branch} leads at {top_branch_rate} DCTR; the bottom {n_underperformers} branches sit below {threshold_rate} — replicate the {top_branch} onboarding playbook there."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `top_branch` | `dctr_9.best_branch` | `str` |
  | `top_branch_rate` | `dctr_9.best_dctr` | `pct` |
  | `n_underperformers` | `dctr_9.below_threshold_count` | `int` |
  | `threshold_rate` | `dctr_9.threshold` | `pct` |
- **example:** "Westgate leads at 58% DCTR; the bottom 6 branches sit below 25% — replicate the Westgate onboarding playbook there."
- **fallback:** "DCTR variance across branches."

### `dctr.momentum`
- **section:** `dctr`
- **template:** "DCTR {direction} {trend_pp} over the past 12 months ({dctr_rate_l12m} vs {dctr_rate_prior}) — {trajectory_qual}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `direction` | `dctr_trends.direction_word` | `str` |
  | `trend_pp` | `dctr_trends.trend_pp` | `pp` |
  | `dctr_rate_l12m` | `dctr_trends.l12m_rate` | `pct` |
  | `dctr_rate_prior` | `dctr_trends.prior_rate` | `pct` |
  | `trajectory_qual` | `dctr_trends.trajectory_qual` | `str` |
- **example:** "DCTR climbed 3.4 pp over the past 12 months (34% vs 30%) — on pace to hit peer median by Q3."
- **fallback:** "DCTR trend, last 12 months."

---

## Reg E (4)

### `rege.penetration`
- **section:** `rege`
- **template:** "Reg E opt-in stands at {rege_rate} of {n_eligible_personal} eligible personal accounts — {gap_pp} below peer benchmark."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `rege_rate` | `reg_e_1.rate` | `pct` |
  | `n_eligible_personal` | `reg_e_1.eligible_count` | `int` |
  | `gap_pp` | `reg_e_1.peer_gap_pp` | `pp` |
- **example:** "Reg E opt-in stands at 22% of 9,800 eligible personal accounts — 11 pp below peer benchmark."
- **fallback:** "Reg E opt-in rate — eligible personal accounts."

### `rege.revenue_impact`
- **section:** `rege`
- **template:** "Reg E opt-ins drive {revenue_usd_m} annually; closing the {gap_pp} gap to peer would add {opportunity_usd_m}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `revenue_usd_m` | `value_2.current_revenue` | `usd_m` |
  | `gap_pp` | `value_2.gap_pp` | `pp` |
  | `opportunity_usd_m` | `value_2.opportunity` | `usd_m` |
- **example:** "Reg E opt-ins drive $1.8M annually; closing the 11 pp gap to peer would add $920K."
- **fallback:** "Reg E revenue impact."

### `rege.growth_trajectory`
- **section:** `rege`
- **template:** "Reg E opt-in {direction} {trend_pp} year-over-year ({rate_l12m} vs {rate_prior}) — {trajectory_qual}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `direction` | `reg_e_trends.direction_word` | `str` |
  | `trend_pp` | `reg_e_trends.trend_pp` | `pp` |
  | `rate_l12m` | `reg_e_trends.l12m_rate` | `pct` |
  | `rate_prior` | `reg_e_trends.prior_rate` | `pct` |
  | `trajectory_qual` | `reg_e_trends.trajectory_qual` | `str` |
- **example:** "Reg E opt-in fell 1.8 pp year-over-year (22% vs 24%) — reverses three consecutive quarters of growth."
- **fallback:** "Reg E opt-in trend."

### `rege.at_risk`
- **section:** `rege`
- **template:** "{n_at_risk} accounts ({pct_at_risk} of opt-ins) haven't transacted in 90+ days — at risk of involuntary opt-out."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `n_at_risk` | `reg_e_at_risk.count` | `int` |
  | `pct_at_risk` | `reg_e_at_risk.share_of_optins` | `pct` |
- **example:** "412 accounts (19% of opt-ins) haven't transacted in 90+ days — at risk of involuntary opt-out."
- **fallback:** "Reg E opt-in retention risk."

---

## Attrition (4)

### `attrition.closure_rate`
- **section:** `attrition`
- **template:** "Attrition ran {attr_rate} this period — {n_closed} closures across {n_eligible} eligible accounts."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `attr_rate` | `attrition_1.overall_rate` | `pct` |
  | `n_closed` | `attrition_1.n_closed` | `int` |
  | `n_eligible` | `attrition_1.eligible_count` | `int` |
- **example:** "Attrition ran 7.1% this period — 880 closures across 12,400 eligible accounts."
- **fallback:** "Account attrition — current period."

### `attrition.driver_analysis`
- **section:** `attrition`
- **template:** "{top_driver} accounts for {top_driver_share} of closures; {top_driver_segment} accounts close at {top_driver_segment_rate} — {3x_baseline} the portfolio rate."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `top_driver` | `attrition_drivers.top_driver` | `str` |
  | `top_driver_share` | `attrition_drivers.top_driver_share` | `pct` |
  | `top_driver_segment` | `attrition_drivers.top_driver_segment` | `str` |
  | `top_driver_segment_rate` | `attrition_drivers.top_driver_segment_rate` | `pct` |
  | `3x_baseline` | `attrition_drivers.multiple_of_baseline_word` | `str` |
- **example:** "Inactivity accounts for 38% of closures; under-2-year tenure accounts close at 21% — 3x the portfolio rate."
- **fallback:** "Attrition drivers — segment view."

### `attrition.prevention_opportunity`
- **section:** `attrition`
- **template:** "Each closure costs {cost_per_closure} in lifetime value; preventing {target_pct} of at-risk accounts would save {savings_usd_m} annually."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `cost_per_closure` | `value_attrition.cost_per_closure` | `usd` |
  | `target_pct` | `value_attrition.target_save_pct` | `pct` |
  | `savings_usd_m` | `value_attrition.annual_savings` | `usd_m` |
- **example:** "Each closure costs $563 in lifetime value; preventing 20% of at-risk accounts would save $1.1M annually."
- **fallback:** "Attrition prevention opportunity."

### `attrition.peer_comparison`
- **section:** `attrition`
- **template:** "Attrition of {attr_rate} ranks {rank_ord} of {n_peers} peers — {comparison_word} than the {peer_median} peer median."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `attr_rate` | `attrition_peer.rate` | `pct` |
  | `rank_ord` | `attrition_peer.rank_ord` | `str` |
  | `n_peers` | `attrition_peer.n_peers` | `int` |
  | `comparison_word` | `attrition_peer.comparison_word` | `str` |
  | `peer_median` | `attrition_peer.peer_median` | `pct` |
- **example:** "Attrition of 7.1% ranks 9th of 22 peers — better than the 8.4% peer median."
- **fallback:** "Attrition vs peer median."

---

## Mailer (4)

### `mailer.campaign_performance`
- **section:** `mailer`
- **template:** "{n_campaigns} campaigns reached {n_recipients} accounts; response rate of {response_rate} drove {n_conversions} new debit activations."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `n_campaigns` | `mailer_summary.n_campaigns` | `int` |
  | `n_recipients` | `mailer_summary.n_recipients` | `int` |
  | `response_rate` | `mailer_summary.response_rate` | `pct1` |
  | `n_conversions` | `mailer_summary.n_conversions` | `int` |
- **example:** "4 campaigns reached 6,200 accounts; response rate of 3.8% drove 236 new debit activations."
- **fallback:** "Mailer campaign performance."

### `mailer.response_rate`
- **section:** `mailer`
- **template:** "Best-performing campaign — {top_campaign} — delivered {top_response_rate} response, {top_lift_pp} above the program average."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `top_campaign` | `mailer_top.campaign_name` | `str` |
  | `top_response_rate` | `mailer_top.response_rate` | `pct1` |
  | `top_lift_pp` | `mailer_top.lift_pp` | `pp` |
- **example:** "Best-performing campaign — Q2 Eligible Re-engagement — delivered 5.2% response, 1.4 pp above the program average."
- **fallback:** "Top-performing mailer campaign."

### `mailer.revenue_impact`
- **section:** `mailer`
- **template:** "Mailer-attributed revenue: {revenue_usd_m} ({roi}x ROI on {spend_usd_k} spend) over the {window_months}-month window."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `revenue_usd_m` | `mailer_roi.revenue` | `usd_m` |
  | `roi` | `mailer_roi.roi_multiple` | `int` |
  | `spend_usd_k` | `mailer_roi.spend` | `usd` |
  | `window_months` | `mailer_roi.window_months` | `int` |
- **example:** "Mailer-attributed revenue: $1.4M (12x ROI on $115K spend) over the 12-month window."
- **fallback:** "Mailer revenue impact."

### `mailer.segment_performance`
- **section:** `mailer`
- **template:** "{top_segment} responded at {top_segment_rate}, {top_segment_lift_pp} above average — concentrate next campaign here."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `top_segment` | `mailer_segments.top_segment` | `str` |
  | `top_segment_rate` | `mailer_segments.top_segment_rate` | `pct1` |
  | `top_segment_lift_pp` | `mailer_segments.top_segment_lift_pp` | `pp` |
- **example:** "Tenured personal opted-out accounts responded at 6.8%, 3.0 pp above average — concentrate next campaign here."
- **fallback:** "Mailer response by segment."

---

## Value (4)

### `value.total_opportunity`
- **section:** `value`
- **template:** "Total annual opportunity: {total_opportunity_usd_m} — {dctr_share} from DCTR gap, {rege_share} from Reg E gap, {attr_share} from attrition prevention."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `total_opportunity_usd_m` | `value_summary.total` | `usd_m` |
  | `dctr_share` | `value_summary.dctr_share` | `pct` |
  | `rege_share` | `value_summary.rege_share` | `pct` |
  | `attr_share` | `value_summary.attr_share` | `pct` |
- **example:** "Total annual opportunity: $4.3M — 56% from DCTR gap, 22% from Reg E gap, 22% from attrition prevention."
- **fallback:** "Total revenue opportunity by lever."

### `value.gap`
- **section:** `value`
- **template:** "Closing DCTR to peer median ({peer_dctr}) would add {dctr_gap_usd_m} — equivalent to {gap_in_accounts} additional active debit accounts."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `peer_dctr` | `value_1.peer_dctr` | `pct` |
  | `dctr_gap_usd_m` | `value_1.dctr_gap_value` | `usd_m` |
  | `gap_in_accounts` | `value_1.dctr_gap_accounts` | `int` |
- **example:** "Closing DCTR to peer median (41%) would add $2.4M — equivalent to 870 additional active debit accounts."
- **fallback:** "DCTR gap to peer — revenue translation."

### `value.benchmark`
- **section:** `value`
- **template:** "Revenue per eligible account: {rpea} — {pct_vs_peer} vs the {peer_rpea} peer average."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `rpea` | `value_benchmark.rpea` | `usd` |
  | `pct_vs_peer` | `value_benchmark.delta_word` | `str` |
  | `peer_rpea` | `value_benchmark.peer_rpea` | `usd` |
- **example:** "Revenue per eligible account: $216 — 12% below the $245 peer average."
- **fallback:** "Revenue per eligible account vs peer."

### `value.per_account_impact`
- **section:** `value`
- **template:** "Activating a previously-inactive debit card is worth {value_per_activation_usd} per account; converting {target_count} accounts would add {target_value_usd_m}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `value_per_activation_usd` | `value_per_activation.value_per_unit` | `usd` |
  | `target_count` | `value_per_activation.target_count` | `int` |
  | `target_value_usd_m` | `value_per_activation.target_value` | `usd_m` |
- **example:** "Activating a previously-inactive debit card is worth $216 per account; converting 1,500 accounts would add $324K."
- **fallback:** "Per-account value of debit activation."

---

## Insights (4)

### `insights.top_insight`
- **section:** `insights`
- **template:** "The biggest lever: {lever} at {lever_value_usd_m} — {realistic_close_qual} of that is achievable in the next two quarters."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `lever` | `s1.lever_label` | `str` |
  | `lever_value_usd_m` | `s1.lever_value` | `usd_m` |
  | `realistic_close_qual` | `s1.realistic_close_qual` | `str` |
- **example:** "The biggest lever: closing the DCTR gap at $2.4M — most of that is achievable in the next two quarters."
- **fallback:** "Top revenue lever."

### `insights.growth_driver`
- **section:** `insights`
- **template:** "{best_segment} is the highest-leverage segment ({segment_rate} {segment_metric}, {segment_share_word} of opportunity) — design the next mailer for them."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `best_segment` | `s2.best_segment` | `str` |
  | `segment_rate` | `s2.segment_rate` | `pct` |
  | `segment_metric` | `s2.segment_metric` | `str` |
  | `segment_share_word` | `s2.segment_share_word` | `str` |
- **example:** "Tenured-personal-no-debit is the highest-leverage segment (12% conversion rate, 60% of opportunity) — design the next mailer for them."
- **fallback:** "Highest-leverage segment to target."

### `insights.risk_indicator`
- **section:** `insights`
- **template:** "Watch {risk_signal}: {risk_metric_value} this period vs {risk_metric_prior} prior — {risk_qual}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `risk_signal` | `s3.signal_label` | `str` |
  | `risk_metric_value` | `s3.metric_value` | `str` |
  | `risk_metric_prior` | `s3.metric_prior` | `str` |
  | `risk_qual` | `s3.risk_qual` | `str` |
- **example:** "Watch Reg E opt-out velocity: 412 this period vs 230 prior — first time it crossed our 350 trigger."
- **fallback:** "Emerging risk indicator."

### `insights.recommendation_headline`
- **section:** `insights`
- **template:** "Do three things next: {action_1}, {action_2}, {action_3} — together worth {combined_value_usd_m}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `action_1` | `s8.action_1` | `str` |
  | `action_2` | `s8.action_2` | `str` |
  | `action_3` | `s8.action_3` | `str` |
  | `combined_value_usd_m` | `s8.combined_value` | `usd_m` |
- **example:** "Do three things next: replicate Westgate onboarding, re-mail tenured opt-outs, re-engage 90-day-inactive Reg E — together worth $3.6M."
- **fallback:** "Top three recommended actions."
