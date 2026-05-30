# Handover — Autonomous Deck Generation (paused mid writing-plans)

**Paused at:** 2026-05-29
**Branch:** `feat/autonomous-decks` (off `pipeline-improvement`)
**Reason for pause:** prior session ran low on context budget before completing the implementation plan. Spec is fully written, decisions locked, plan **not yet drafted**.

## State of the work

### Done (committed on `feat/autonomous-decks`)

- `afdce7a` — `spec: autonomous deck generation design`
- `7a3fbbb` — `spec: lock 3 open decisions on autonomous decks design`

### In flight (paused)

- `superpowers:brainstorming` skill workflow: **completed**. Tasks 1-7 of the brainstorming checklist done; user approved the spec.
- `superpowers:writing-plans` skill: **invoked but did not produce a plan**. Plan file does NOT exist yet.

### Next action

Draft the implementation plan from the spec following the `superpowers:writing-plans` skill protocol, saved to `docs/superpowers/plans/2026-05-29-autonomous-decks.md`.

## Spec summary

Full spec at `docs/superpowers/specs/2026-05-29-autonomous-decks-design.md`. Highlights for the next agent:

- **Goal:** the operator clicks Run and gets a finished, send-ready deck. No per-slide authoring, no design review, no per-slide CSM check.
- **Constraint:** no runtime LLM access on the work PC. No Claude Desktop dependency. Runtime is pure Python on Windows backed by `M:\` network share. Claude is design-time only.
- **Three lever-pulls** (all runtime-deterministic):
  - **A.** Branching template catalog (~150 templates, 7 section files, stable-hash variant selection per client).
  - **B.** Themed Plotly chart engine (single `themed_chart()` function over a custom template; replaces ~25 modules' matplotlib code).
  - **C.** Auto-built structural slides (cover, dashboard, agenda, section openings, takeaways — no more `blank` placeholders).
- **Locked decisions:**
  - Variant differentiation: consultative-first / action-summary structure, 3 variants per branch (data-first / context-first / action-first).
  - Maintenance cadence: monthly feedback loop, documented in README.
  - `--strict-templates` flag: build it, default off, for CI + catalog authoring only.

## Migration plan (from the spec, 12 steps)

1. Build `output/template_catalog.py` + author DCTR section (~20 templates).
2. Build `shared/charts/themes.py` + migrate `rate_volume_combo` end-to-end on one analytics module.
3. Build `output/structural_slides.py` + cover slide.
4. Wire `_SLIDE_TEMPLATE_MAP` stub + populator delegation.
5. POC E2E smoke test on client 1615.
6. Author the remaining 6 section catalogs.
7. Migrate the remaining ~24 analytics modules to `themed_chart()`.
8. Build the remaining 4 structural slides.
9. Add `templates_loaded` + `structural_slides_built` quality-gate checks.
10. Wire `--strict-templates` CLI flag.
11. Document monthly feedback loop + `--strict-templates` in README.
12. Full E2E on the 10-client matrix from `03-e2e-test-plan.md`.

**Steps 1-5 = POC slice (1-2 sessions). Steps 6-12 = long tail (3-5 sessions).**

## Recommendation for the next session

Given the size of the plan (12 migration steps × multiple tasks each, ~30-50 tasks total at bite-sized granularity), the previous session's recommendation was to **slice the plan** — draft only the POC slice (steps 1-5) at full skill fidelity in the next session; defer the long tail to a third session. This keeps each session's output high-fidelity.

If you want one plan covering all 12 steps, expect that session to also pause partway and need stitching.

## Files the next agent should read first

| File | Why |
|---|---|
| `docs/superpowers/specs/2026-05-29-autonomous-decks-design.md` | The spec being implemented. Start here. |
| `01_Analysis/00-Scripts/output/action_title_populator.py` | What gets refactored to delegate into the new template_catalog. |
| `01_Analysis/00-Scripts/output/deck_builder.py` | `_result_to_slide` + `_build_preamble_slides` are the wire-in points. `_SLIDE_TEMPLATE_MAP` is at line ~50-100 area. |
| `01_Analysis/00-Scripts/shared/charts.py` | Existing palette + `SECTION_COLORS` that `themed_chart()` will reuse. |
| `01_Analysis/00-Scripts/charts/style.py` | Existing chart helpers (apply_section_color, auto_rotate_xticks, etc.). `themed_chart()` will subsume or delegate. |
| `docs/action_title_templates.md` | The current flat 28-template catalog that becomes the fallback when the per-section catalog is missing. |
| `01_Analysis/00-Scripts/output/headlines.py` | The legacy per-slide generator path; kept as final fallback. |
| `01_Analysis/00-Scripts/tests/conftest.py` | Existing pytest setup. New tests should follow the same fixture style. |
| `01_Analysis/00-Scripts/pipeline/steps/generate.py` | `step_generate` + `_run_tier3_outputs` for understanding where the new modules slot in. |
| `01_Analysis/00-Scripts/output/quality_gate.py` | Where the 2 new checks will be added. |

## Branch state

```
$ git -C /Users/jgmbp/Desktop/RPE-Workflow log --oneline feat/autonomous-decks
7a3fbbb spec: lock 3 open decisions on autonomous decks design
afdce7a spec: autonomous deck generation design
aeae889 docs(walkthroughs): operator step-by-step for the 6 remaining items from #145
e735a10 fix(repo): commit Tier 1/2/3 modules that .gitignore was silently dropping
87e48cb feat(tier3+final): close T3.1-T3.4 + T4+T5 from PRD/#145
...
```

`feat/autonomous-decks` has not been pushed to GitHub. It's local-only on the dev machine until the operator pulls.

## Launch prompt for the next session

Paste this verbatim to start the next session:

```
Resume autonomous deck generation work on branch feat/autonomous-decks.

Spec is committed at docs/superpowers/specs/2026-05-29-autonomous-decks-design.md
(commits afdce7a + 7a3fbbb).

Read docs/superpowers/HANDOVER-2026-05-29-autonomous-decks.md for full context.

Goal for this session: invoke the superpowers:writing-plans skill and draft
the implementation plan for the POC slice (migration steps 1-5 from the spec)
ONLY. Save to docs/superpowers/plans/2026-05-29-autonomous-decks-poc.md.
The long-tail steps 6-12 get their own plan in a future session.

After the plan is committed, offer execution choice per the writing-plans
skill exit protocol.
```

## Open issues / risks for the next agent

- **Plotly version floor not yet pinned.** Spec says "verify version floor before merging." First task in the plan should be a `python -c "import plotly; print(plotly.__version__)"` smoke + confirm `requirements.txt` lists it.
- **Plotly PNG export on M:\ network share** not yet benchmarked. Spec calls out the local-temp + `shutil.move` fallback pattern from `run.py`. The plan should include a quick benchmark task.
- **Test infrastructure** in `01_Analysis/00-Scripts/tests/` — confirm pytest discovery works for new tests under the same tree before writing them; existing conftest may have fixtures the new code can lean on.
- **Branch not pushed.** Push gates on the operator pulling; the operator hasn't asked us to push `feat/autonomous-decks` yet, and it's a brand-new design direction that hasn't been validated against the operator's expectations. Don't push without a checkpoint.
