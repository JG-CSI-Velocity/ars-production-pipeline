# Value — Section Spec

**Section key:** `value` (note: slides physically distribute into `dctr` and `rege` sections per the denominator framework; see `03_Config/section_registry.json` `routed_elsewhere`)
**Accent:** `#28A745` (green, per SLIDE_DESIGN.md §5.1)
**Issue:** #154 (T2.5)

## Slides in this section

### A11 — Total annual opportunity
- **Template:** `value.total_opportunity`
- **Callout:** metric `Total upside`, value `value_summary.total` formatted usd_m, comparison "{dctr_share} DCTR + {rege_share} Reg E + {attr_share} attrition"
- **Required ctx.results:** `value_summary.{total,dctr_share,rege_share,attr_share}`
- **Chart:** waterfall — current revenue → DCTR opp → Reg E opp → attrition saves → total
- **Routes to:** `insights` section in narrative arc

### A11.1 — DCTR gap value
- **Template:** `value.gap`
- **Callout:** metric `DCTR opportunity`, value `value_1.dctr_gap_value` formatted usd_m, comparison "to {peer_dctr} peer median"
- **Required ctx.results:** `value_1.{peer_dctr,dctr_gap_value,dctr_gap_accounts}`
- **Chart:** dual y-axis — DCTR % bars vs annual revenue line
- **Routes to:** `dctr` section (distributed per framework)

### A11.2 — Reg E revenue impact
- **Template:** `rege.revenue_impact` (shared with rege section)
- **Callout:** metric `Reg E upside`, value `value_2.opportunity` formatted usd_m, comparison "from {gap_pp} gap"
- **Required ctx.results:** `value_2.{current_revenue,gap_pp,opportunity}`
- **Chart:** stacked bar — current revenue + opportunity = target
- **Routes to:** `rege` section (distributed per framework)

### A10 — Per-account impact
- **Template:** `value.per_account_impact`
- **Callout:** metric `Per activation`, value `value_per_activation.value_per_unit` formatted usd, comparison "{target_count} accounts = {target_value}"
- **Required ctx.results:** `value_per_activation.{value_per_unit,target_count,target_value}`
- **Chart:** scatter of accounts by activity tier with size = balance
