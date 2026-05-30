# DCTR action titles (branching catalog — autonomous decks design §A)

Section: dctr
Authority: `docs/superpowers/specs/2026-05-29-autonomous-decks-design.md`
Parsed by: `01_Analysis/00-Scripts/output/template_catalog.py`

## Family: `dctr.activation_baseline`
- **section:** `dctr`
- **branch_if:** `dctr_1.rate`
- **branches:**
  - `>= 0.55` → strong
  - `0.40..0.54` → healthy
  - `0.30..0.39` → opportunity
  - `< 0.30` → urgent
- **fallback:** "Debit-card take rate snapshot across the eligible book."

### strong / variant 1 (data_first)
- **template:** "Debit-card take rate sits at {dctr_rate} of {n_eligible} eligible accounts — clearing the peer upper band."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### strong / variant 2 (context_first)
- **template:** "With {n_eligible} eligible accounts in play, {client_name}'s {dctr_rate} take rate clears the peer upper band — protect the lead."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |

### strong / variant 3 (action_first)
- **template:** "Protecting the lead is the priority — debit-card take rate sits at {dctr_rate} of {n_eligible} eligible, already above the peer upper band."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### healthy / variant 1 (data_first)
- **template:** "Debit-card take rate sits at {dctr_rate} of {n_eligible} eligible accounts, tracking the peer median; the next 5 pp is the clearest near-term lever."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### healthy / variant 2 (context_first)
- **template:** "With {n_eligible} eligible accounts active, {client_name}'s {dctr_rate} take rate tracks peer median — closing the 5 pp gap to upper quartile is the clearest near-term lever."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |

### healthy / variant 3 (action_first)
- **template:** "Closing the 5 pp gap to peer upper quartile is the clearest near-term lever; {client_name} sits at {dctr_rate} of {n_eligible} eligible, on the peer median."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### opportunity / variant 1 (data_first)
- **template:** "Debit-card take rate sits at {dctr_rate} of {n_eligible} eligible accounts — below peer median, with the bulk of the gap concentrated in the under-engaged tier."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### opportunity / variant 2 (context_first)
- **template:** "With {n_eligible} eligible accounts on the book, {client_name}'s {dctr_rate} take rate trails peer median — the under-engaged tier holds most of the recoverable gap."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |

### opportunity / variant 3 (action_first)
- **template:** "Re-engaging the under-engaged tier is the priority — {client_name}'s {dctr_rate} take rate sits below peer median across {n_eligible} eligible accounts."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### urgent / variant 1 (data_first)
- **template:** "Debit-card take rate sits at {dctr_rate} of {n_eligible} eligible — well below peer floor; activation is the single largest revenue lever in the book."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

### urgent / variant 2 (context_first)
- **template:** "With {n_eligible} eligible accounts and only {dctr_rate} activated, {client_name} sits below peer floor — activation is the single largest revenue lever available."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |

### urgent / variant 3 (action_first)
- **template:** "Activation is the single largest revenue lever available — {client_name}'s {dctr_rate} take rate sits below peer floor across {n_eligible} eligible accounts."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `n_eligible` | `dctr_1.eligible_count` | `int` |

## Family: `dctr.peer_comparison`
- **section:** `dctr`
- **branch_if:** `dctr_peer.gap_pp`
- **branches:**
  - `>= 0.05` → ahead
  - `-0.05..0.05` → at_peer
  - `< -0.05` → behind
- **fallback:** "Peer benchmark for debit-card take rate."

### ahead / variant 1 (data_first)
- **template:** "Take rate runs {gap_pp} above peer median ({dctr_rate} vs {peer_rate}) — a structural lead worth defending in next cycle's mailer."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `gap_pp` | `dctr_peer.gap_pp` | `pp_signed` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `peer_rate` | `dctr_peer.peer_median` | `pct` |

### ahead / variant 2 (context_first)
- **template:** "{client_name}'s {dctr_rate} take rate runs {gap_pp} ahead of peer median — defend the lead through next cycle's mailer cadence."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `gap_pp` | `dctr_peer.gap_pp` | `pp_signed` |

### ahead / variant 3 (action_first)
- **template:** "Defending the structural lead is the play — {client_name} runs {gap_pp} ahead of peer median on take rate."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `gap_pp` | `dctr_peer.gap_pp` | `pp_signed` |

### at_peer / variant 1 (data_first)
- **template:** "Take rate at {dctr_rate} tracks peer median ({peer_rate}) — the lever is closing the {gap_pp} gap to upper quartile, not the median."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `peer_rate` | `dctr_peer.peer_median` | `pct` |
  | `gap_pp` | `dctr_peer.gap_to_upper_pp` | `pp` |

### at_peer / variant 2 (context_first)
- **template:** "{client_name}'s {dctr_rate} take rate tracks peer median; closing the {gap_pp} gap to upper quartile is the lever."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `gap_pp` | `dctr_peer.gap_to_upper_pp` | `pp` |

### at_peer / variant 3 (action_first)
- **template:** "Closing the {gap_pp} gap to peer upper quartile is the lever — {client_name}'s take rate already tracks peer median."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `gap_pp` | `dctr_peer.gap_to_upper_pp` | `pp` |

### behind / variant 1 (data_first)
- **template:** "Take rate trails peer median by {gap_pp} ({dctr_rate} vs {peer_rate}) — closing half that gap is the explicit goal this cycle."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `gap_pp` | `dctr_peer.gap_pp` | `pp_signed` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `peer_rate` | `dctr_peer.peer_median` | `pct` |

### behind / variant 2 (context_first)
- **template:** "{client_name}'s {dctr_rate} take rate trails peer median by {gap_pp} — closing half that gap is the explicit goal this cycle."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |
  | `gap_pp` | `dctr_peer.gap_pp` | `pp_signed` |

### behind / variant 3 (action_first)
- **template:** "Closing half the {gap_pp} gap to peer median is the explicit cycle goal — {client_name} runs at {dctr_rate}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `gap_pp` | `dctr_peer.gap_pp` | `pp_signed` |
  | `dctr_rate` | `dctr_1.rate` | `pct` |

## Family: `dctr.growth_driver`
- **section:** `dctr`
- **branch_if:** `dctr_growth.yoy_pp`
- **branches:**
  - `>= 0.02` → accelerating
  - `-0.02..0.02` → flat
  - `< -0.02` → declining
- **fallback:** "Year-over-year movement in debit-card take rate."

### accelerating / variant 1 (data_first)
- **template:** "Take rate grew {yoy_pp} year-over-year — {top_driver} is the main driver, accounting for ~{driver_share} of the lift."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |
  | `top_driver` | `dctr_growth.top_driver` | `str` |
  | `driver_share` | `dctr_growth.top_driver_share` | `pct` |

### accelerating / variant 2 (context_first)
- **template:** "{client_name}'s take rate grew {yoy_pp} year-over-year on the back of {top_driver}, which accounts for ~{driver_share} of the lift."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |
  | `top_driver` | `dctr_growth.top_driver` | `str` |
  | `driver_share` | `dctr_growth.top_driver_share` | `pct` |

### accelerating / variant 3 (action_first)
- **template:** "Doubling down on {top_driver} is the obvious play — it drove ~{driver_share} of the {yoy_pp} year-over-year lift in take rate."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `top_driver` | `dctr_growth.top_driver` | `str` |
  | `driver_share` | `dctr_growth.top_driver_share` | `pct` |
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |

### flat / variant 1 (data_first)
- **template:** "Take rate moved {yoy_pp} year-over-year — within noise; the program is holding, not growing."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |

### flat / variant 2 (context_first)
- **template:** "{client_name}'s take rate moved {yoy_pp} year-over-year — within noise; the program is holding, not growing."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |

### flat / variant 3 (action_first)
- **template:** "Re-igniting growth needs a new lever — {client_name}'s take rate moved only {yoy_pp} year-over-year."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |

### declining / variant 1 (data_first)
- **template:** "Take rate fell {yoy_pp} year-over-year — {top_driver} is the main contributor; reversing it is the explicit cycle goal."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |
  | `top_driver` | `dctr_growth.top_driver` | `str` |

### declining / variant 2 (context_first)
- **template:** "{client_name}'s take rate fell {yoy_pp} year-over-year, driven mostly by {top_driver} — reversing it is the explicit cycle goal."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |
  | `top_driver` | `dctr_growth.top_driver` | `str` |

### declining / variant 3 (action_first)
- **template:** "Reversing the {yoy_pp} year-over-year decline is the explicit cycle goal — {top_driver} is the main contributor at {client_name}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `yoy_pp` | `dctr_growth.yoy_pp` | `pp_signed` |
  | `top_driver` | `dctr_growth.top_driver` | `str` |
  | `client_name` | `ctx.client.client_name` | `str` |

## Family: `dctr.momentum`
- **section:** `dctr`
- **branch_if:** `dctr_momentum.last_quarter_pp`
- **branches:**
  - `>= 0.01` → improving
  - `-0.01..0.01` → steady
  - `< -0.01` → softening
- **fallback:** "Recent-quarter movement in debit-card take rate."

### improving / variant 1 (data_first)
- **template:** "Take rate added {last_quarter_pp} in the last quarter — momentum building into next cycle."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

### improving / variant 2 (context_first)
- **template:** "{client_name} added {last_quarter_pp} to take rate in the last quarter — momentum is building into next cycle."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

### improving / variant 3 (action_first)
- **template:** "Riding the momentum into next cycle is the play — {client_name} added {last_quarter_pp} to take rate in the last quarter."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

### steady / variant 1 (data_first)
- **template:** "Take rate held flat in the last quarter ({last_quarter_pp}) — no momentum to ride; next cycle needs a deliberate push."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

### steady / variant 2 (context_first)
- **template:** "{client_name}'s take rate held flat in the last quarter — no momentum to ride; next cycle needs a deliberate push."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |

### steady / variant 3 (action_first)
- **template:** "Next cycle needs a deliberate push — {client_name}'s take rate held flat over the last quarter."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |

### softening / variant 1 (data_first)
- **template:** "Take rate lost {last_quarter_pp} in the last quarter — soften now or lose ground; the cycle goal is stabilizing before the next mailer."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

### softening / variant 2 (context_first)
- **template:** "{client_name}'s take rate gave back {last_quarter_pp} in the last quarter — stabilizing before the next mailer is the cycle goal."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

### softening / variant 3 (action_first)
- **template:** "Stabilizing before the next mailer is the cycle goal — {client_name} gave back {last_quarter_pp} on take rate last quarter."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `last_quarter_pp` | `dctr_momentum.last_quarter_pp` | `pp_signed` |

## Family: `dctr.opportunity_size`
- **section:** `dctr`
- **branch_if:** `dctr_value.usd_opportunity`
- **branches:**
  - `>= 1000000` → large
  - `100000..999999` → mid
  - `< 100000` → small
- **fallback:** "Estimated revenue opportunity in closing the take-rate gap."

### large / variant 1 (data_first)
- **template:** "Closing the take-rate gap to peer median is worth {usd_opportunity} — DCTR is the single biggest revenue lever in the book."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd_m` |

### large / variant 2 (context_first)
- **template:** "At {client_name}, closing the take-rate gap to peer median is worth {usd_opportunity} — DCTR is the single biggest revenue lever available."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd_m` |

### large / variant 3 (action_first)
- **template:** "Anchor the deck on DCTR — closing the gap is worth {usd_opportunity} for {client_name}, the single biggest revenue lever."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd_m` |
  | `client_name` | `ctx.client.client_name` | `str` |

### mid / variant 1 (data_first)
- **template:** "Closing the take-rate gap to peer median is worth {usd_opportunity} — sized to matter, but not the only lever on the table."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd` |

### mid / variant 2 (context_first)
- **template:** "At {client_name}, closing the take-rate gap to peer median is worth {usd_opportunity} — meaningful, alongside Reg E and attrition levers."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd` |

### mid / variant 3 (action_first)
- **template:** "Sequence DCTR alongside Reg E and attrition — the gap is worth {usd_opportunity} for {client_name}."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd` |
  | `client_name` | `ctx.client.client_name` | `str` |

### small / variant 1 (data_first)
- **template:** "Closing the take-rate gap to peer median is worth {usd_opportunity} — modest relative to Reg E and attrition; sequence after those."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd` |

### small / variant 2 (context_first)
- **template:** "At {client_name}, the DCTR gap is worth {usd_opportunity} — modest relative to other levers; sequence after Reg E and attrition."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd` |

### small / variant 3 (action_first)
- **template:** "Sequence DCTR after Reg E and attrition for {client_name} — the take-rate gap is worth {usd_opportunity}, modest by comparison."
- **placeholders:**
  | Slot | Path | Format |
  |---|---|---|
  | `client_name` | `ctx.client.client_name` | `str` |
  | `usd_opportunity` | `dctr_value.usd_opportunity` | `usd` |
