# Session final state — 14 PRs across the Velocity pipeline

**Session window:** 2026-06-03 → 2026-06-06
**Entry point for reviewers:** [`W_PHASES_REVIEW.md`](W_PHASES_REVIEW.md) (PR #165)
**Scope:** Implements the reconciled 4-wave plan ([`plans/2026-06-06-velocity-pipeline-reconciled.md`](plans/2026-06-06-velocity-pipeline-reconciled.md)) plus every named follow-up.

---

## PR inventory

### Wave PRs (4) — original plan

| # | Title | Touches | Tests |
|---|---|---|---|
| [#161](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/161) | W1 — Denominator-law enforcement | `audit.py`, `shared/debit.py`, `branch_scorecard.py`, `_safe` wrappers | +10 |
| [#162](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/162) | W2 — Single brand authority | `shared/brand.py`, ~15 analytics files, Excel, deck builder, UI CSS, docs | +8 |
| [#163](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/163) | W3 — YAML slide spec system | `output/slide_spec.py`, 9 YAML specs, `deck_builder._build_action_slide` | +8 |
| [#164](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/164) | W4 — CSM experience | Run Quality panel, Deck Shape editor, Format checklist, ODD cache, rebuild deck, TestClient harness | +7 (UI), +7 (backend) |

### Documentation PRs (2)

| # | Title | Surface |
|---|---|---|
| [#165](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/165) | Consolidated review checklist | `docs/W_PHASES_REVIEW.md` — single entry point for verifying all wave PRs |
| [#168](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/168) | TXN-results adapter design | `docs/txn-results-adapter-design.md` — architecture for unblocking TXN specs |

### Infrastructure PRs (3)

| # | Title | Touches | Tests |
|---|---|---|---|
| [#166](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/166) | Chart-PNG content-hash cache | `charts/cache.py`, `docs/chart-cache-adoption.md` | +10 |
| [#167](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/167) | HTML preview surface | `02_Presentations/html_review/from_run_report.py`, `/api/preview_html`, Results-tab iframe | +5 |
| [#169](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/169) | TXN-results adapter implementation | `analytics/txn_exports.py`, `txn_wrapper.expose_to_ctx_results`, `competition.yml`, `txn_exec.yml` | +10 |

### Stacked PRs (5) — build on earlier PRs

| # | Title | Base | Touches |
|---|---|---|---|
| [#170](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/170) | W1 audit registry + module stamps | #161 | Prefix-length bug fix; registry covers every slide_id; DCTR-1/2/3, A8.1, A9.1, A11.1 stamped |
| [#171](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/171) | First cache adoption — DCTR A7.2 | #166 | Proves end-to-end pattern; +4 tests |
| [#172](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/172) | Per-month mailer pattern-keyed template | #163 | `A13.{month}` syntax; one template renders every monthly slide; +4 tests |
| [#173](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/173) | Cache adoption — A8.1 Reg E + A9.1 attrition | #166 | Two more module adoptions |
| [#174](https://github.com/JG-CSI-Velocity/ars-production-pipeline/pull/174) | Cache adoption — S1 Revenue Gap | #166 | Insights synthesis adoption |

---

## Total impact

- **Files touched:** 80+
- **Tests added:** 67 (10 audit + 8 brand + 8 slide_spec + 7 manifest editor + 7 UI endpoint + 5 HTML preview + 10 cache infra + 4 cache adoption + 10 TXN adapter + 4 W1 stamps + 4 pattern keys)
- **Test count at end of session:** **102 across the worktree** (backend + UI + HTML preview)
- **All passing:** yes

---

## Recommended merge order

The wave PRs first, in numerical wave order, then the stacked refinements, then the cross-cutting infrastructure.

```
1. #161 W1 Law      (foundation)
2. #170 W1 stamps   (stacks on #161; drives violations to zero)
3. #162 W2 Brand    (independent off main)
4. #163 W3 Slides   (independent off main)
5. #172 mailer template (stacks on #163)
6. #164 W4 UX       (independent off main)
7. #169 TXN adapter (independent off main; references competition.yml/txn_exec.yml created here)
8. #166 Cache infra (independent off main)
9. #171 / #173 / #174 cache adoptions (stack on #166)
10. #167 HTML preview (independent off main)
11. #165 review checklist (anytime)
12. #168 TXN design doc (reference; merge anytime or close)
```

**File overlap to watch at merge time:**

- `docs/slide_specs/competition.yml` + `docs/slide_specs/txn_exec.yml` — written as stubs in #163, replaced with full specs in #169. Resolution: take #169's version.
- `docs/slide_specs/mailer.yml` — extended in #163 (aggregate + reach), then again in #172 (per-month template). #172 stacks on #163 so the merge is clean if order is followed.

---

## What's still left

### Genuinely operator-side (cannot ship without input)

1. **Read [`W_PHASES_REVIEW.md`](W_PHASES_REVIEW.md)** on the work PC, work through the per-PR checklist as each merges.
2. **Decide `OPEN_ALLOWLIST` additions** for W1 (audit.py) before merging. Currently only `dctr_2` is whitelisted to use `Open` as primary denominator; any other deck slide that legitimately frames Open needs to be added or the scorecard will flag false positives.
3. **Settle the four open design questions** in PR #168 (TXN adapter design doc) — three of them are already settled by #169's actual implementation, but the doc should be updated to reflect the chosen answers if it's going to merge as canonical.

### Mechanical work (ships when convenient, no design decisions)

4. **More cache adoptions** per `docs/chart-cache-adoption.md`. 4 of ~100 chart sites cached so far. Each additional adoption is a small commit per the pattern in #171/#173/#174. Recommended adoption order: continue through DCTR (trends, branches, overlays, funnel), then Reg E historical (A8.2/A8.3), then mailer monthly summaries.
5. **Stamp `denominator_label` on more ARS modules** to drive W1's `framework_compliant=False` count toward zero. Each `AnalysisResult` constructor that returns a rate-bearing slide should add `denominator_label="Eligible"` (or appropriate layer) + `denominator_n=<count>`. The registry in audit.py already covers everything by default, so stamping is refinement, not unblocking.
6. **Per-section export registrations** in `analytics/txn_exports.py` (PR #169) for the remaining TXN sections beyond competition + executive. Same pattern; one tuple per script.

### Genuinely deferred (separate scope)

7. **CI pipeline** — `rates_audit.csv` diff would be the natural foundation. Not in this session's scope.
8. **Plotly-aware chart cache shim** for TXN section sections that use Plotly instead of matplotlib. Noted in `docs/chart-cache-adoption.md`.
9. **Renaming operator-facing product names** (`ars`/`txn`/`dep`). Explicit non-goal.

---

## Why the session stopped here

The technical surface area covered by the original plan plus every named follow-up plus several discovered follow-ups (audit registry refinement, pattern-keyed templates, cache adoptions) is now in flight. Additional cache adoptions are mechanical repetition without architectural change. Adding more PRs increases reviewer load without adding new shape.

The `/goal comlwrw rhia` text set early in the session was unparseable as a stopping condition. The stop hook itself reported it could not evaluate satisfaction. After the work reached its natural stopping point (every named item shipped), the most useful remaining action was this consolidation doc.

Next decisions belong to whoever opens the PR queue. Most likely first move: pull `feat/w1-denominator-law-enforcement` (or download the ZIP per the SETUP.md workflow), run it against one client on the work PC, and walk the W1 section of `W_PHASES_REVIEW.md`.
