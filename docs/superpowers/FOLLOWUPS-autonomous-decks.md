# Follow-ups — autonomous decks POC

Surfaced by reviewers during the POC build on `feat/autonomous-decks` (2026-05-29). Each item is real but out of POC scope. Pick these up in the long-tail plan or as one-off cleanups.

## 1. Latent `_KV_RE` bug in `action_title_populator.py` — ✅ FIXED (`413c3eb`)

Was: regex expected colon outside bold; flat catalog uses colon inside.
Fixed: regex now matches `**key:**` form. Regression test at `tests/test_action_title_populator_flat_catalog.py`.

## 2. Mixed `ars_analysis.*` vs bare imports in production code

**Scope:** ~36KB of grep hits across `runner.py`, `pipeline/`, `analytics/`, `output/`, `charts/`.

The `ars_analysis.*` namespace exists because:
- `tests/conftest.py` aliases it for pytest.
- `01_Analysis/run.py` ALSO sets it up at runtime via `sys.modules`.

Both forms work. The codebase is genuinely split — `output/callout_builder.py` and `charts/style.py` use bare `shared.X` form; many `analytics/*` modules use `ars_analysis.X`.

**Impact:** Cosmetic. Confusion for new contributors. Hard to remove the `ars_analysis` alias if we ever wanted to.

**Fix:** pick one convention and migrate. Recommend bare `shared.X` / `output.X` form since `run.py` could drop the alias if everything is bare. Punt until there's a real reason to standardize.

## 3. `output/` directory gitignore foot-gun — ✅ FIXED (`ddaf07a`)

Was: bare `output/` rule caught `01_Analysis/00-Scripts/output/`; every commit needed `-f`.
Fixed: added negation rules for the package dir + `.py` files + `template/` subdir. `__pycache__` still ignored via separate rule.

## 4. Dead code: `_FALLBACK_COVER_SUBLINE` — ✅ FIXED (`413c3eb`)

Deleted. Long-tail plan brings it back when the markdown parser lands.

## 5. `docs/structural_templates.md` contract ambiguity — ✅ FIXED (`413c3eb`)

Added a **Status:** reference-only header to the file. Long-tail plan promotes the markdown to source-of-truth via a parser.

## 6. Kaleido 0.2.x is past upstream support

**Scope:** `requirements.txt` has `kaleido>=0.2,<1.0`. Kaleido 0.2.1 (latest 0.x) is past support. Plotly emits a deprecation warning every render — currently ~16 warnings per test run.

**Fix:** evaluate kaleido 1.0+ API (different from 0.2.x) and migrate. Probably a long-tail plan task — the migration touches every chart-saving code path.

## 7. POC-only test hygiene gaps caught by reviewers

These were called out during review and accepted as "acceptable for POC scope":

- **Empty-file test for `_parse_section_file`** — minimal `(d/"empty.md").write_text("")` would lock in the no-op behavior. ~1 LOC test.
- **`_OP_RE` edge-case coverage** — no test for whitespace variants (`>=0.5` vs `>= 0.5`), `==0` vs `==0.0`. The regex handles both but tests don't pin it.
- **`_hash_index` empty client_id edge** — `client_id=""` hashes deterministically (same variant always for any family). Not asserted anywhere.
- **`select_variant` ambiguity** — returns `None` for both "family-not-found" and "no-branch-match". Caller can't distinguish. Acceptable today because populator does its own family lookup, but a sentinel or tuple return would be cleaner.

## 8. `_render_variant` placeholder format error handling

**File:** `01_Analysis/00-Scripts/output/action_title_populator.py:380` (new method from Task 6)

When a Variant references a placeholder path that resolves but `format_value` doesn't recognize the format hint, `format_value` defensively returns `str(value)` and logs a WARNING. That's the right call for prod robustness but it means a catalog typo (`- pct1` vs `- pcty`) becomes a silent string render rather than a blocker. Fine for POC; the long-tail `--strict-templates` flag (spec §Migration step 10) would surface these.

## Process retrospective

(For the long-tail plan, not code fixes.)

- **Plan-as-tutorial bias.** This plan had every code block fully written out. Caught bugs (regex, class name, file path) propagated verbatim into implementer dispatches. A tighter plan that says "use md5 hash for stability; tests at fixture X verify" lets the implementer validate against reality. Trade verbosity for resilience.
- **Validate plan code blocks before committing the plan.** Trace one example end-to-end through every code path in the plan. The `_KV_RE` colon-position, `_RANGE_RE` negative-number, `DctrTrendsModule` class-name, and `01_Analysis/requirements.txt` path errors were all catchable with `grep`/`pytest` from the plan-writing session.
- **Checkpoint discipline.** Continuous execution is faster but a natural pause after the catalog landed (Task 5) or after first migration (Task 9) would let the user redirect cheaply on big calls (e.g., the chart-content regression that was almost shipped as "POC limitation").
- **Don't combine spec + quality review.** The skill explicitly orders them. Combining saved subagent calls from Task 7 onward but removed a safety layer. Run them separately.
