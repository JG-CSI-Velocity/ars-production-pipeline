# Follow-ups — autonomous decks POC

Surfaced by reviewers during the POC build on `feat/autonomous-decks` (2026-05-29). Each item is real but out of POC scope. Pick these up in the long-tail plan or as one-off cleanups.

## 1. Latent `_KV_RE` bug in `action_title_populator.py`

**File:** `01_Analysis/00-Scripts/output/action_title_populator.py:76`

```python
_KV_RE = re.compile(r"^\-\s+\*\*([^*]+)\*\*:\s*(.+?)\s*$")
```

The regex expects `- **key**: value` (colon outside bold) but the actual flat catalog at `docs/action_title_templates.md` uses `- **key:** value` (colon inside bold). Same bug Task 3 fixed in `template_catalog.py::_parse_section_file`.

**Impact:** Benign at runtime — `section` field in `TemplateBlock` ends up empty but the populator never reads it for substitution. The bug means the populator's "section" metadata has been silently empty since T2.2 shipped.

**Fix:** change the regex to `r"^\-\s+\*\*([^*]+):\*\*\s*(.*?)\s*$"` matching the Task 3 fix in `template_catalog.py:131`. Add a regression test that parses one block from `docs/action_title_templates.md` and asserts `section == "overview"`.

## 2. Mixed `ars_analysis.*` vs bare imports in production code

**Scope:** ~36KB of grep hits across `runner.py`, `pipeline/`, `analytics/`, `output/`, `charts/`.

The `ars_analysis.*` namespace exists because:
- `tests/conftest.py` aliases it for pytest.
- `01_Analysis/run.py` ALSO sets it up at runtime via `sys.modules`.

Both forms work. The codebase is genuinely split — `output/callout_builder.py` and `charts/style.py` use bare `shared.X` form; many `analytics/*` modules use `ars_analysis.X`.

**Impact:** Cosmetic. Confusion for new contributors. Hard to remove the `ars_analysis` alias if we ever wanted to.

**Fix:** pick one convention and migrate. Recommend bare `shared.X` / `output.X` form since `run.py` could drop the alias if everything is bare. Punt until there's a real reason to standardize.

## 3. `output/` directory gitignore foot-gun

**Scope:** every commit to `01_Analysis/00-Scripts/output/*.py` needs `git add -f`.

The `.gitignore` at the repo root contains `output/` (line 51) which catches `01_Analysis/00-Scripts/output/`. The comment at `.gitignore:38` says "CRITICAL: do NOT ignore `01_Analysis/00-Scripts/output/`" but the negation rule isn't actually there. Commit `e735a10` (before POC) silently rescued some output modules; this branch added many more with `-f`.

**Fix:** add `!01_Analysis/00-Scripts/output/` to `.gitignore` after the `output/` rule. One line. Eliminates the `-f` need.

## 4. Dead code: `_FALLBACK_COVER_SUBLINE`

**File:** `01_Analysis/00-Scripts/output/structural_slides.py:29`

```python
_FALLBACK_COVER_SUBLINE = "Performance review"
```

Defined but never referenced. Intended for the path where `docs/structural_templates.md` becomes the live source of truth (currently human-reference only) and the default subline lookup fails. Until then it's dead.

**Fix:** either delete it now or wire the markdown parser in the long-tail plan so it gets used. Document the contract clearly either way.

## 5. `docs/structural_templates.md` contract ambiguity

The file exists, has the cover subline copy, and looks like data — but no code parses it. `structural_slides.build_cover()` uses hardcoded `_DEFAULT_COVER_SUBLINE = "Account Revenue Solution"` inline.

**Fix:** in long-tail plan, either:
- Wire a parser so the markdown becomes the source of truth (and unblocks #4), or
- Add a header to the file: "Reference only — defaults live in `output/structural_slides.py`."

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
