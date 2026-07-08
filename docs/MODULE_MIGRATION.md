# Module closed-loop: architecture & migration guide

This describes the per-module closed-loop system and how to migrate the
remaining analytics sections onto it. The **framework is complete and tested**;
what remains is mechanical per-module work that must be verified against real
client data on the Windows/M: machine.

## What "closed loop" means

Pick one analytics section → the pipeline runs any formatting not yet done, runs
just that section's analysis (plus the upstream producers it declares it needs),
and builds a PowerPoint of only that section's slides. One command, one deck,
easy to troubleshoot and change.

- **CLI:** `python 01_Analysis/run.py --section txn.merchant --month 2026.06 --csm JamesG --client 1776`
- **UI:** Generate tab → "run just one module" dropdown → Generate.

## The pieces (all built, all tested here)

| Concern | Where | Notes |
|---|---|---|
| Canonical section list | `analytics/section_registry.py` | 7 `ars.*` + 23 `txn.*`; one source of truth. `test_section_registry.py` asserts it ≡ on-disk folders. |
| Cross-section dependency graph | `analytics/section_deps.py` | AST static analysis. `upstream_sections(folder)`, `required_names(folder)`, `missing_section_deps(folder, ns)`. CLI: `tools/module_deps.py`. |
| Single-section runner | `runner.py:run_module(ctx, section_id)` | ARS: overview + selected modules. TXN: resolved upstreams (side-effects) → target → **hard-fail if the target's declared deps aren't in the namespace**. |
| Scoped deck | `output/deck_builder.py:build_scoped_deck(ctx, section)` | Title + divider + that section's slides → `modules/<id>/…_deck.pptx`. Never collides with a full-run deck. |
| CLI flag | `run.py --section` / `--rebuild-cache` | `--section` overrides `--product`. |
| UI | `GET /api/modules`, `POST /api/run?module=` | Registry via `tools/list_sections.py`; `runGenReal` adds `&module=`. |
| Cache correctness | `txn_setup/02-file-config.py`, `09-oddd-account-type.py` | `TXN_FORCE_REBUILD` (stale-after-fix), `TXN_CACHE_SYNC` (short-run write not lost). |

## Migrating a section (the remaining work)

Do this per section, **verifying each against a real client run** before moving on.
Start with the pilots: **ICS_cohort** (leaf) and **executive** (aggregator).

1. **Know its contract.** `python 01_Analysis/00-Scripts/tools/module_deps.py --upstream txn.<folder>` lists what runs before it. A leaf (e.g. `ICS_cohort`) has none.
2. **Promote genuinely-shared producers.** The hub is `general` (theme + `gen_*` formatters + `demo_df` + `acct_txn_counts`). Moving these into `txn_setup` turns many coupled sections into leaves and shrinks every module run. Verify the **full** `--product txn` deck is byte-for-byte unchanged after promotion (regression baseline).
3. **Kill silent skips.** Replace `if var in globals(): … else: print("run X first")` with a reliance on declared deps; `run_module` already hard-fails when a declared dep is absent, so a scoped run can't ship an incomplete deck silently.
4. **Stable slide ids.** Give each slide a logical id (declared, not positional `NN`) so `SLIDE_MANIFEST.xlsx` keep/drop and `docs/slide_specs/<section>.yml` copy don't desync between full and scoped runs. Migrate the manifest sheet + mapping row in lockstep.
5. **Aggregators** (`executive`, `insights.*`): declare `requires_modules`; the runner runs them and hard-fails on absence rather than emitting an empty scorecard.
6. **Add a smoke test** over a shared minimal `combined_df` fixture (leaves) or recorded upstream outputs (aggregators). Pattern: `tests/test_ics_cohort_smoke.py` (now sources `display_formatted` from production).
7. **Sync docs:** the section's `EQUATION_DICTIONARY` block, `SLIDE_MAPPING.md` rows, manifest sheet.

## Open decisions (Phase 3)

- **`cross_cohort`** (12 scripts, absent from `TXN_SECTIONS`): wire it as a real section (give it a `slide_code`) or delete it. `test_section_registry.py` guards against silent new orphans.
- **Deposits (`dep`)**: advertised in the UI but no backend. Build ~15 modules or remove the card. Currently gated "coming soon" and rejected server-side.
- **Retire legacy** once all sections are migrated and the full-deck regression holds: `TXN_SECTIONS`, the split registries, the dead `_SECTION_MAP` `txn-*` keys, `_UI_KEY_TO_PREFIXES`, and the hardcoded `05_UI/app.py:module_counts`.

## Regression guard

Before/after any migration step, a full `--product txn` (and `--product combined`)
run must produce the same module-count, slide-count, and deck as a pre-refactor
baseline. The rewrite must not change full-deck output — only make each module
independently runnable.
