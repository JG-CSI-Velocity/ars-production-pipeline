# Contributing to ars-production-pipeline

This repo uses a three-branch soak flow so broken code doesn't reach real client runs.

```
feature/* ──► dev ──► main
  (work)    (soak)   (blessed)
```

## Branches

| Branch | Purpose | Who merges |
|---|---|---|
| `main` | Production. Runs real client reports. | Only via `promote.bat` after `dev` has been tested. |
| `dev` | Soak / staging. Test new code here against real clients before promoting. | Feature branches merge here first. |
| `feature/*`, `fix/*`, `claude/*` | One-task work branches. | Merge into `dev` via PR. |

## Day-to-day workflow

1. **Start a new piece of work** — branch off `dev`:

   ```
   git checkout dev
   git pull origin dev
   git checkout -b feature/my-change
   ```

2. **Make changes, commit, push:**

   ```
   git add <files>
   git commit -m "fix(section): short description"
   git push -u origin feature/my-change
   ```

3. **Open a PR into `dev`** on GitHub. CI runs automatically — green checkmark = syntax and lint are clean. Merge the PR.

4. **Test `dev` against a real client** locally:

   ```
   git checkout dev
   git pull origin dev
   # run pipeline via Start Here.bat or python run.py ...
   ```

5. **When `dev` looks good, promote to `main`:**

   ```
   promote.bat
   ```

   This merges `dev` into `main` and pushes. After this, `main` has the new code and future real runs will use it.

## Golden rules

- **Never push directly to `main`.** Always go through `dev`. Branch protection on GitHub will enforce this.
- **Never merge a feature branch into `main` directly.** Always `feature → dev → main`.
- **Don't merge until you've tested.** CI catches syntax, not correctness. A real client run is the only real test.
- **When in doubt, don't merge.** Feature branches cost nothing to leave open.

## What CI does (and doesn't)

CI runs on every push and PR. It does:
- `py_compile` on every `.py` file (catches syntax errors)
- `ruff` with strict rules (catches a handful of likely-broken patterns)

It does NOT:
- Run the full pipeline (no access to M: drive from GitHub servers)
- Validate that outputs look right
- Catch logic errors

That's what the `dev` soak is for.

---

## Architectural patterns

These are the patterns the codebase has converged on. New code should follow them; existing code is migrating to them PR by PR. Each section points at the canonical example.

### 1. Denominator law (4-layer framework)

Every rate, ratio, or share in the pipeline anchors to exactly one of four denominators:

| Layer | When |
|---|---|
| **Eligible** | Default for every rate unless the metric is inherently personal- or business-only |
| **Eligible Personal** | Personal-only metrics (Reg E by regulation, any personal product rate) |
| **Eligible Business** | Business-only metrics |
| **Open** | Reference framing only. Allowed as primary denominator on `dctr_2` (the methodology slide) ONLY |

How to comply:

- New `AnalysisResult` constructors that surface a rate should stamp `denominator_label="Eligible"` (or appropriate layer) + `denominator_n=<total>` directly. See `analytics/dctr/penetration.py` DCTR-1 / DCTR-2 for the canonical examples.
- For modules not yet stamped, `pipeline/steps/audit.py:DEFAULT_BY_PREFIX` infers the label from the slide_id prefix. Add an entry there when you introduce a new slide_id family.
- Every run writes `rates_audit.csv` next to `run_manifest.json`. Each row's `framework_compliant` is `True` only when the denominator label is in the 4-layer set. Aim for zero violations.

The framework is documented in detail at `memory/project_denominator_framework.md` (sessioned memory; copy the rules into a code comment when you stamp a non-obvious slide).

### 2. Brand authority

Single source of truth: `01_Analysis/00-Scripts/shared/brand.py`.

- `BRAND["navy"]` = `#1A1A1A` (CSI navy). Don't use any other navy hex.
- `BRAND["accent"]` = `#F15D22` (CSI orange). Same.
- Multi-series charts: use `CHART_PALETTE[0..7]` for series colors; semantic aliases (`PERSONAL`, `BUSINESS`, `HISTORICAL`, `TTM`, `ELIGIBLE`, `SILVER`, `TEAL`) resolve through brand.
- Fonts: `FONTS["title"]` / `FONTS["body"]` / `FONTS["mono"]` (Montserrat / Montserrat / Space Mono).
- Sizes: `SIZES["action_title"]` / `SIZES["callout_hero"]` / `SIZES["body"]`, etc. — per the `SLIDE_DESIGN.md` anatomy.

Don't introduce a new hex literal in analytics code. If you find one (e.g. `"#1E3D59"`), promote it through `brand.py` or use the brand alias.

### 3. Slide spec system (YAML-driven action titles)

Slide copy lives in `docs/slide_specs/<section>.yml`. The renderer (`output/slide_spec.py`) reads the YAML, resolves `inputs:` against `ctx.results`, format-maps the `action_title` / `callout` / `footer`, and the deck builder uses the rendered text in place of analytics-supplied generic titles.

Per-spec required fields:

```yaml
SLIDE-ID:
  layout: TWO_CONTENT
  components: [chart_id, ...]
  action_title: "Headline with a {number:.0%} in it"
  inputs:
    number: ctx.results.module_id.insights.rate
  denominator_label: Eligible       # one of the four layers; ties to W1 law
  callout:
    hero: "{hero_value}"
    sub: "..."
  footer:
    source: "Source: {client_name} ODD, {month}"
```

Special syntax:

- Pattern-keyed templates: `"A13.{month}"` matches every per-month slide ID; the captured `month` injects into the inputs. See `docs/slide_specs/mailer.yml`.
- Lenient placeholders: missing inputs leave `{name}` literal in the output and surface a render warning. They don't crash the deck build.

Authoring guide examples: `docs/slide_specs/dctr.yml`, `rege.yml`, `value.yml`.

### 4. Chart-PNG content-hash cache

Charts are expensive to render. Wrap each `chart_figure` site through `charts/cache.py`:

```python
from charts.cache import cached_chart, fingerprint_df

key = fingerprint_df(
    df=my_df,
    columns=["Stat Code", "Debit?"],
    extras={
        "client": ctx.client.client_id,
        "month": ctx.client.month,
        "style": "ars.mplstyle:v3",
        "chart": "my_chart_id:v1",
    },
)

def _draw(path):
    with chart_figure(save_path=path) as (fig, ax):
        ax.bar(...)

cached_chart(save_to, key, _draw)
```

The side-effect trap: `ctx.results[...]` writes (or any other state mutation) must live OUTSIDE `_draw`. A cache hit skips `_draw` entirely, so anything inside it gets skipped too. Canonical examples: `dctr/penetration.py` A7.2, `rege/status.py` A8.1, `attrition/rates.py` A9.1, `insights/synthesis.py` S1.

Adoption guide: `docs/chart-cache-adoption.md`. Each chart site is a small per-module commit.

### 5. TXN-results adapter

TXN sections (`analytics/competition/`, `analytics/executive/`, etc.) run numbered scripts in a shared namespace, not as `AnalysisModule` subclasses. To expose script output to `ctx.results` (so slide specs can bind to it), declare the export in `analytics/txn_exports.py`:

```python
SECTION_EXPORTS[("competition", 13)] = {
    "insights": ["top_competitor", "top_share", "threat_count"],
    "tables": ["threat_quadrant_df"],
}
```

The adapter (`txn_wrapper.expose_to_ctx_results`) runs after each script settles and copies declared variables into `ctx.results["competition_13"]`. Missing variables are silently skipped (DEBUG log only).

Rules:

- **Rename TXN scripts freely; renumber never.** The script number is the registry's stable key.
- The registry is project state (not infra) — co-located with `txn_wrapper.py`.
- Spec YAML uses explicit `ctx.results.{section}_{script_number}.{field}` paths.

Design doc: `docs/txn-results-adapter-design.md`.

### 6. HTML preview

Every completed run can be served as a self-contained HTML page (charts inlined as base64 data URIs). Operators preview without opening PowerPoint.

- `POST /api/preview_html/{csm}/{month}/{client_id}` builds the preview
- `GET /preview/{csm}/{month}/{client_id}/` serves it (iframe-embeddable)
- UI button on the Results tab triggers the build + iframe load

Adapter: `02_Presentations/html_review/from_run_report.py`. Section routing: `_section_for(slide_id, module_id)`.

### 7. UI-first rule (CLAUDE.md)

Every diagnostic, fix, run, audit, and tool must be operable from the UI. No "drop this in a notebook cell" or "run this from the terminal" as the recommendation. Each new capability ships as:

1. A button / panel / tab in `05_UI/index.html`
2. Backed by an endpoint in `05_UI/app.py`
3. With results streamed or displayed in the UI itself

If a script today only works as a notebook cell, refactor it into a callable function and wire it in. The terminal command is a stopgap, not the target.

---

## Test conventions

- Backend tests: `01_Analysis/00-Scripts/tests/`
- UI tests: `05_UI/tests/` (FastAPI TestClient — see `tests/conftest.py` for the `app_module` fixture pattern)
- HTML preview tests: `02_Presentations/html_review/tests/`

Naming: `test_<module_under_test>.py`. One assertion concern per test. Use `tmp_path` for any test that writes files.

Run before pushing:

```
cd 01_Analysis/00-Scripts && python -m pytest tests/ -q
cd 05_UI && python -m pytest tests/ -q
cd 02_Presentations && python -m pytest html_review/tests/ -q
```
