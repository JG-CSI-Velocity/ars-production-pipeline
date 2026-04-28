# ARS Executive Narrative Rebuild — Design Spec

**Date:** 2026-04-17
**Repo:** `/Users/jgmbp/Desktop/RPE-Workflow/` (ars-production-pipeline under `Step 3 - Powerpoint/`)
**Branch:** TBD — proposed `feature/exec-narrative-rebuild`
**Status:** Draft — pending user review
**Companion artifact:** [`2026-04-17-deck-blueprint.md`](./2026-04-17-deck-blueprint.md) — slide-by-slide mapping, produced by Phase B subagent. Treat the blueprint as the authoritative slide inventory for this spec.

---

## 1. Problem

The existing ARS client executive deck is organized around **data topics** (DCTR, Reg E, Attrition, Mailer, Transaction, ICS) inside an SCR arc. The story it tells is "here is what the data says about your program." Clients hear: "the program underperformed."

That framing loses the room. The program hasn't underperformed — customers are spending, they're just not spending with the bank. The deck needs to lead with behavior, not metrics, and end with a plan, not a scorecard.

## 2. Goal

Rebuild the deck around a narrative arc — **Truth → Diagnosis → Opportunity → Plan** — so the client leaves aligned on *what to do* instead of graded on *what happened*. Reuse the ~95 slides the pipeline already produces wherever they serve the new story; add only the slides the narrative genuinely needs; cut or appendix everything else.

This is a **template rebuild**, not a client-specific deck. Every slide uses real analytics field names + chart types but placeholder numbers. Real numbers land per-client at pipeline run time.

## 3. Non-goals

- Re-rendering charts or changing analytics logic. This spec does not touch `01_Analysis/00-Scripts/analytics/*`.
- Building new analytics folders (Transaction and ICS stay empty — TXN v2.0 is tracked separately).
- Fixing the pipeline DCTR denominator bug. The spec treats the notebook-truth number as a placeholder; any slide whose claim depends on it carries a footnote until the notebook handoff is spec'd separately.
- Building the persona deep-dive module implementation. The module is scoped in section 7 but its implementation is a follow-on spec.
- Client data. No real numbers, no real names in the repo.

## 4. Locked decisions (Phase A)

| Decision | Lock | Source |
|---|---|---|
| Narrative arc | Open → Truth → Diagnosis → Opportunity → Plan → Close | User draft + Q1 |
| Diagnosis has three gaps | Engagement, Targeting, Ecosystem | User draft |
| Persona count | 3 — Non-User, Climber, Decliner | Q1 response |
| Personas in main deck | One bridge slide between Diagnosis and Plan | Q2 response |
| Denominator source for Truth slides | Jupyter notebook customer-level penetration (~80%), NOT pipeline DCTR (~30%) | Memory: project_data_trust_issue |
| Audience | Bank executives / ARS program owners | Default |
| Numbers in template | **All placeholder / fake.** Real numbers land per-client via pipeline at run time. | User guidance, 2026-04-17 |

## 5. Defaults (Phase B — confirmed absent objection)

| # | Blueprint question | Default |
|---|---|---|
| Q1-bp | Decliner placement | **Ecosystem Gap** inside Diagnosis (keeps 3 gaps clean; Opportunity stays forward-looking) |
| Q2-bp | Notebook truth number source | **Placeholder** per user guidance — every Truth/Opportunity claim uses a fake number and a `{{NOTEBOOK_PENETRATION}}` template variable. A follow-on spec handles the notebook handoff. |
| Q3-bp | S5 "Debit Card Cascade" | **Appendix** — available as optional insert for cascade-focused clients |
| Q4-bp | Mailer months in main deck | **1 month** (most recent) in main; prior months appendix-only |
| Q5-bp | Transaction and ICS sections | **Out of scope** for this rebuild. Sections stay registered-but-empty. |
| Q6-bp | Benchmark slide (A18.3) | **Include in Plan** with explicit denominator footnote until the source is audited |
| Q7-bp | Agenda slide | **Replace P02** with a new 4-beat agenda (Truth / Diagnosis / Opportunity / Plan) |

## 6. Deck structure

Six main-deck sections, in order. Slide IDs and sources reference the [blueprint](./2026-04-17-deck-blueprint.md) — see blueprint §2 for the full mapping table.

### 6.1 Open
| Slide | Role | Source |
|---|---|---|
| P01 (reused) | Title / Client name | existing preamble |
| P02-new | 4-beat Agenda | new text slide, replaces P02 placeholder |

### 6.2 Truth
| Slide | Role | Source |
|---|---|---|
| Truth-1 (new) | Executive Reframe — "Your customers are spending. Just not with you." | new text+KPI slide; placeholder 80% |
| Truth-2 (new) | True Debit Penetration | new chart slide; placeholder customer-level % alongside account-level DCTR for contrast |
| DCTR-3 (reused) | TTM DCTR narrative | existing `dctr/penetration.py` output, carries denominator footnote |

### 6.3 Diagnosis

Three sub-sections, one per gap. Each opens with a divider slide.

**6.3.1 Engagement Gap (Non-User)**
| Slide | Source |
|---|---|
| A7.11 | `dctr/trends.py (age)` — DCTR by account age |
| A7.12 | `dctr/trends.py (age)` — DCTR by holder age |
| A20.1 | `insights/dormant.py` — dormant population size |

**6.3.2 Targeting Gap (Climber)**
| Slide | Source |
|---|---|
| A14.2 | `mailer/response.py` — responder profile |
| A15.1 or A15.3 | `mailer/attribution.py` — lift vs baseline (pick one; keep A15.3) |
| A16.1 | `mailer/cohort.py` — responder spend trajectory |

**6.3.3 Ecosystem Gap (Decliner + leakage)**
| Slide | Source |
|---|---|
| A9.1 | `attrition/rates.py` — overall attrition rate |
| A9.3 | `attrition/rates.py` — open vs closed |
| A9.9 | `attrition/impact.py` — debit retention effect |
| A7.10a | `dctr/branches.py` — branch ranking (leakage signal) |

### 6.4 Persona Bridge

Single slide between Diagnosis and Plan.

| Slide | Role | Source |
|---|---|---|
| Bridge-1 (new) | Meet the 3 customer types | 3-card composite layout. Data for each card pulled from: Non-User (complement of DCTR-3), Climber (A14.2 + A7.11), Decliner (A9.1 + A20.2). Placeholder sizing numbers. |

### 6.5 Opportunity
| Slide | Role | Source |
|---|---|---|
| Opp-1 (new) | Total Addressable Spend | new slide; value calc based on A11.1 logic but with notebook-truth placeholder denominator |
| A11.2 (reused) | Reg E value | existing `value/analysis.py` |
| S3 (reused) | Opportunity synthesis | existing `insights/synthesis.py` |

### 6.6 Plan
| Slide | Role | Source |
|---|---|---|
| Plan-1 (new) | 3–5 Strategic Pillars | new text slide mapped to the three gaps |
| A17.1 | `mailer/reach.py` — reach (evidence for targeting pillar) |
| A18.3 | `insights/effectiveness.py` — industry benchmark (with denominator footnote) |
| A12.{most_recent_month} | `mailer` — most recent month mailer (only 1 month in main) |
| Close-1 (new) | Final takeaway / CTA | new text slide |

## 7. Persona deep-dive module (optional, toggled)

Separate appendix pack of 15 slides (5 per persona). Not in core deck. Spec'd only enough here that the Phase B assembler can wire a `--persona-module` flag; implementation details are deferred.

See blueprint §6 for the full slide list per persona. All slides come from existing analytics folders (no new analytics required).

## 8. Appendix

Every slide currently in a section's `_APPENDIX_IDS` stays in appendix. Blueprint §4 lists the additional main-deck-to-appendix demotions (approximately 45 slides total). Appendix order within each section preserves current ordering.

## 9. Template placeholders

Every new slide created under this spec uses placeholder values where a client-specific number would go. Pipeline fills them at run time. Convention:

- `{{CLIENT_NAME}}` — bank / CU name
- `{{NOTEBOOK_PENETRATION}}` — customer-level debit penetration (e.g., 80%)
- `{{PIPELINE_DCTR}}` — account-level DCTR (e.g., 30%)
- `{{ADDRESSABLE_SPEND_USD}}` — Opportunity-1 headline number
- `{{NONUSER_COUNT}}`, `{{CLIMBER_COUNT}}`, `{{DECLINER_COUNT}}` — Persona Bridge sizing
- `{{MOST_RECENT_MAILER_MONTH}}` — Plan section mailer slide selector

Placeholders are tracked in a single `02_Powerpoint/placeholders.py` module so the template has one source of truth.

## 10. Branch strategy

- Branch from `main`: `feature/exec-narrative-rebuild`
- Build the new section modules additively in `02_Powerpoint/sections/` — do not delete old modules until the new assembler is proven
- One commit per new section module (open, truth, diagnosis_engagement, diagnosis_targeting, diagnosis_ecosystem, persona_bridge, opportunity, plan) — Close-1 lives inside plan.py
- One commit for the registry reorder in `sections/__init__.py`
- One commit for the placeholders module
- Blueprint and this spec both already live in `docs/superpowers/specs/` — no additional doc commits in this branch

## 11. File changes expected

New / modified under `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/`:

```
02_Powerpoint/
├── deck_assembler.py              # lightly modified: optional --persona-module flag
├── placeholders.py                # new: template variable registry
├── sections/
│   ├── __init__.py                # modified: reorder SECTION_REGISTRY to narrative
│   ├── _base.py                   # unchanged
│   ├── open.py                    # new: Title + Agenda
│   ├── truth.py                   # new: Truth-1, Truth-2, DCTR-3 passthrough
│   ├── diagnosis_engagement.py    # new: A7.11/12, A20.1
│   ├── diagnosis_targeting.py     # new: A14.2, A15.3, A16.1
│   ├── diagnosis_ecosystem.py     # new: A9.1/3/9, A7.10a
│   ├── persona_bridge.py          # new: single 3-card slide
│   ├── opportunity.py             # new: Opp-1, A11.2, S3
│   ├── plan.py                    # new: pillars, A17.1, A18.3, 1 mailer month, Close
│   ├── overview.py                # unchanged (still appendix-only)
│   ├── dctr.py                    # modified: most slides → appendix
│   ├── rege.py                    # modified: most slides → appendix
│   ├── attrition.py               # modified: most slides → appendix
│   ├── mailer.py                  # modified: 1 month in main, rest appendix
│   ├── transaction.py             # unchanged (still empty)
│   ├── ics.py                     # unchanged (still empty)
│   ├── value.py                   # modified: most slides → appendix (S1 absorbed into Opp-1)
│   └── insights.py                # modified: S3 in main, rest appendix
└── persona_module/                # new package (optional deep-dive)
    ├── __init__.py
    ├── nonuser.py
    ├── climber.py
    └── decliner.py
```

**Not touched:** `01_Analysis/`, `00_Formatting/`, `03_Config/`, `04_Logs/`, `05_UI/`, `SLIDE_MAPPING.md`, `polish.py`.

## 12. Testing

- Add fixture deck test that runs the new assembler with `--persona-module=off` against a canned analytics output and verifies section order + slide count matches this spec.
- Add a second test with `--persona-module=on` and verify the 15 persona slides append correctly.
- Reuse existing test infrastructure under `02_Powerpoint/tests/` (pattern already established by deck-polish spec).
- No real client data in fixtures.

## 13. Acceptance criteria

- [ ] All 9 new section modules exist and register into `SECTION_REGISTRY` in narrative order.
- [ ] `placeholders.py` registers every `{{...}}` variable used in new slides.
- [ ] Existing section modules demote slides to appendix per blueprint §4; no existing slide is deleted, only moved.
- [ ] Running the assembler produces a deck with ~24 main-deck content slides (7 new — P02, Truth-1, Truth-2, Bridge-1, Opp-1, Plan-1, Close-1 — plus ~17 reused) and 3 section dividers, with the demoted slides available in the appendix.
- [ ] `--persona-module` flag toggles the 15-slide persona pack on/off.
- [ ] Fixture tests pass.
- [ ] PR into `main` after user runs the assembler on one real client dataset (local, outside repo) and confirms the report reads right.

## 14. Open items (none blocking this spec)

1. Notebook-truth handoff is a separate follow-on spec. Until it lands, Truth-1/Truth-2 render with placeholder values and a "pending denominator audit" footnote.
2. Benchmark slide A18.3 needs its denominator verified before the first client ships. Ops task, not spec work.
3. Transaction / ICS sections will reshape Diagnosis/Ecosystem when v2.0 TXN analytics land — re-open this spec at that point.
