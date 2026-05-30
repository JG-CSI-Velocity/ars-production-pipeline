# Autonomous Decks POC Implementation Plan (Steps 1–5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the autonomous-decks design end-to-end on a single vertical slice — one section's branching template family (DCTR), one Plotly `themed_chart()` kind (`rate_volume_combo`) wired into one analytics module, and one auto-built structural slide (Cover) — by smoke-testing client 1615 produces a deck with all three new paths exercised.

**Architecture:** Three new modules slot **before** the existing deck composition without changing the orchestration: `output/template_catalog.py` (branching action-title selector), `shared/charts/themes.py` (Plotly template + `themed_chart()`), and `output/structural_slides.py` (data-driven structural builders). The legacy `headlines.py` + matplotlib + `blank` placeholder paths stay intact as fallbacks; new paths layer on top.

**Tech Stack:** Python 3.11+, Plotly 6.5.2 (already in `requirements.txt`, verified installed), pandas, python-pptx (existing), pytest, loguru.

**Scope (POC slice):** Migration steps 1–5 from the spec. Steps 6–12 (other sections, remaining ~24 module migrations, 4 remaining structural slides, quality gates, `--strict-templates`, README, full E2E) are deferred to a second plan document.

**Branch:** `feat/autonomous-decks` (already checked out; spec committed at `afdce7a` + `7a3fbbb`).

**Test fixture conventions (used throughout this plan):**
- New tests live under `01_Analysis/00-Scripts/tests/` and follow `test_<module>.py` naming.
- They import via the `ars_analysis.*` alias set up by `tests/conftest.py`.
- Tests that don't need the full pipeline construct a minimal `dict` for `ctx.results` and (where needed) a stub object with `.client.client_name`, `.client.month`, `.paths.charts_dir` — matching how `action_title_populator.py` already consumes `ctx_results` + `ctx`.

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `01_Analysis/00-Scripts/output/template_catalog.py` | Loads per-section markdown catalogs into one process-cached `{template_id: TemplateFamily}` map; `select_variant()` picks a variant via branch rules + stable hash. |
| `01_Analysis/00-Scripts/shared/charts/__init__.py` | Marks `shared/charts/` as a package so `shared.charts.themes` is importable. (Empty.) |
| `01_Analysis/00-Scripts/shared/charts/themes.py` | Plotly `Layout` template encoding SLIDE_DESIGN.md §5–6 defaults; single `themed_chart()` dispatcher; first `kind` implemented: `rate_volume_combo`. |
| `01_Analysis/00-Scripts/output/structural_slides.py` | Module owning `build_cover()` (and stub signatures for the four other structural builders, to be filled by the long-tail plan). |
| `docs/action_title_templates/dctr.md` | First per-section branching catalog (~20 templates, DCTR section). |
| `docs/structural_templates.md` | Copy bank for structural slides (Cover subline templates land here in POC; remaining sections deferred). |
| `01_Analysis/00-Scripts/tests/test_template_catalog.py` | Unit tests for catalog loader + `select_variant()`. |
| `01_Analysis/00-Scripts/tests/test_themed_chart.py` | Unit tests for `themed_chart()` output (file written, expected layout primitives present). |
| `01_Analysis/00-Scripts/tests/test_structural_slides.py` | Unit tests for `build_cover()`. |
| `01_Analysis/00-Scripts/tests/test_autonomous_decks_smoke.py` | The POC end-to-end smoke test (Task 14) covering catalog + chart + cover wired together for client 1615 fixture data. |

### Modified files

| Path | Change |
|---|---|
| `01_Analysis/00-Scripts/output/action_title_populator.py` | `ActionTitlePopulator.populate()` consults `template_catalog.select_variant()` first; on miss, falls through to today's flat-catalog path. Existing public API unchanged. |
| `01_Analysis/00-Scripts/output/deck_builder.py` | `_SLIDE_TEMPLATE_MAP` gains a comment that DCTR entries route into the branching catalog; `_build_preamble_slides()` calls `structural_slides.build_cover()` to replace the P01 master-title `SlideContent`. No public signature changes. |
| `01_Analysis/00-Scripts/analytics/dctr/trends.py` | `_decade_trend()` swaps its inline matplotlib block for a `themed_chart(kind="rate_volume_combo", ...)` call. Existing matplotlib path remains in place behind a try/except fallback. |

### Untouched (intentional — kept as fallback floors)

- `docs/action_title_templates.md` (flat 28-template catalog) — fallback when the per-section catalog has no match.
- `output/headlines.py` — last-resort fallback when the populator returns empty.
- Remaining analytics modules' matplotlib code paths — untouched in POC.
- `output/quality_gate.py` — untouched in POC (new gates added in long-tail plan, step 9).
- `pipeline/steps/generate.py` + `_run_tier3_outputs` — untouched (orchestration intact).

---

## Task 1: Verify Plotly install + benchmark PNG export speed

**Files:**
- Read: `01_Analysis/00-Scripts/requirements.txt`
- No code changes (this is a one-time diagnostic before writing the Plotly module).

- [ ] **Step 1: Confirm Plotly version on dev machine**

Run:
```bash
python3 -c "import plotly; print('plotly', plotly.__version__)"
```
Expected: `plotly 6.5.2` (or any 5.x+ — fail loudly if < 5.0). If a version below 5.0 is reported, STOP and surface the constraint to the operator before continuing.

- [ ] **Step 2: Confirm `kaleido` (Plotly's PNG exporter) is installed**

Run:
```bash
python3 -c "import kaleido; print('kaleido', kaleido.__version__)"
```
Expected: A version string. If `ModuleNotFoundError`, add `kaleido` to `01_Analysis/requirements.txt` in this step's commit.

- [ ] **Step 3: Add `plotly` and `kaleido` version floors to `requirements.txt` if not pinned**

Read `01_Analysis/requirements.txt`. Confirm both `plotly>=5.0` and `kaleido>=0.2` lines exist. If either is missing, add it.

- [ ] **Step 4: Micro-benchmark PNG export to a temp dir**

Save a one-shot script `/tmp/plot_bench.py` with this content and run it. The expected behavior section after the code block tells you what numbers are acceptable.

```python
# /tmp/plot_bench.py
import time
from pathlib import Path
import plotly.graph_objects as go

out = Path("/tmp/bench_out")
out.mkdir(exist_ok=True)
fig = go.Figure(data=[go.Bar(x=list(range(20)), y=list(range(20)))])
fig.update_layout(width=1500, height=900)

t0 = time.perf_counter()
fig.write_image(str(out / "bench.png"), scale=1)
elapsed = time.perf_counter() - t0
print(f"PNG export elapsed: {elapsed*1000:.0f} ms")
```

Run:
```bash
python3 /tmp/plot_bench.py
```
Expected: under ~1500ms on dev hardware. Anything above 5s on a local SSD is a red flag — surface to the operator and consider deferring `themed_chart()` rollout. Note the elapsed time in the commit message.

- [ ] **Step 5: Commit any requirements.txt change**

```bash
git add 01_Analysis/requirements.txt
git commit -m "chore(deps): pin plotly + kaleido floors for themed_chart() (POC step 1)"
```

(If `requirements.txt` was already correct, skip the commit and proceed to Task 2.)

---

## Task 2: Create `output/template_catalog.py` skeleton with parsing types

**Files:**
- Create: `01_Analysis/00-Scripts/output/template_catalog.py`
- Test: `01_Analysis/00-Scripts/tests/test_template_catalog.py`

- [ ] **Step 1: Write the failing test for the empty-catalog loader**

Create `01_Analysis/00-Scripts/tests/test_template_catalog.py`:

```python
"""Tests for output/template_catalog.py (autonomous decks POC)."""
from __future__ import annotations

from pathlib import Path

from ars_analysis.output import template_catalog


def test_load_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    catalog = template_catalog.load_catalog(catalog_dir=missing)
    assert catalog == {}


def test_load_returns_empty_when_dir_empty(tmp_path: Path) -> None:
    empty = tmp_path / "empty_catalog"
    empty.mkdir()
    catalog = template_catalog.load_catalog(catalog_dir=empty)
    assert catalog == {}
```

- [ ] **Step 2: Run the test, verify it fails on import**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py -v
```
Expected: `ImportError` / `ModuleNotFoundError` for `ars_analysis.output.template_catalog`.

- [ ] **Step 3: Create the module skeleton**

Create `01_Analysis/00-Scripts/output/template_catalog.py`:

```python
"""Branching action-title catalog (autonomous decks design, §A).

Loads one markdown file per section from ``docs/action_title_templates/``,
parses each into a ``TemplateFamily`` keyed by template id, and exposes
``select_variant(family_id, ctx_results, client_id)`` which picks a variant
deterministically based on the family's branch rule plus a stable hash of
``client_id + family_id``.

This module supersedes the flat catalog at ``docs/action_title_templates.md``
on a per-template-id basis: if a family is found here, it wins; otherwise the
populator falls back to the legacy flat catalog (kept for parity until rollout
completes).

Catalog file layout (per section markdown file):

  # <section_title>

  ## Family: `<family_id>`            (e.g. dctr.activation_baseline)
  - **branch_if:** `<dotted.ctx.results.path>`
  - **branches:**
    - `>= 0.55` → strong
    - `0.40..0.54` → healthy
    - `0.30..0.39` → opportunity
    - `< 0.30` → urgent
  - **fallback:** "<sentence used when no branch matches>"

  ### strong / variant 1 (data-first)
  - **template:** "..."
  - **placeholders:**
    | Slot | Path | Format |
    |---|---|---|
    | ... | ... | ... |

  ### strong / variant 2 (context-first)
  ...

Loader behavior:
  * Catalog directory missing OR empty -> returns ``{}`` (caller falls back).
  * One section file unreadable -> logs WARNING, skips it, keeps the rest.
  * One family unparseable -> logs WARNING, skips it, keeps the rest.
  * Catalog is read once per process; cache it at module level via
    ``CatalogCache.get()``.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


# Default catalog directory: <repo>/docs/action_title_templates/
_DEFAULT_CATALOG_DIR = (
    Path(__file__).resolve().parents[3] / "docs" / "action_title_templates"
)


@dataclass
class Variant:
    """One variant within one branch of a family."""

    branch: str          # branch label, e.g. "strong"
    angle: str           # "data_first" | "context_first" | "action_first"
    template: str
    placeholders: dict[str, dict[str, str]] = field(default_factory=dict)


@dataclass
class TemplateFamily:
    """A branching family (e.g. ``dctr.activation_baseline``)."""

    id: str
    section: str
    branch_path: str | None            # dotted ctx.results path; None => no branching
    branches: list[tuple[str, str]]    # ordered list of (rule_expr, branch_label)
    variants: dict[str, list[Variant]] # branch_label -> [Variant, Variant, Variant]
    fallback: str                      # used when no branch matches


def load_catalog(catalog_dir: Path | None = None) -> dict[str, TemplateFamily]:
    """Parse every .md file in ``catalog_dir`` and return a map of families.

    Returns ``{}`` when the directory is missing or empty. Per-file parse
    failures are logged as warnings and skipped; the loader never raises.
    """
    d = catalog_dir or _DEFAULT_CATALOG_DIR
    if not d.exists() or not d.is_dir():
        logger.info("Branching catalog dir missing at {d}; falling back to flat catalog", d=d)
        return {}
    families: dict[str, TemplateFamily] = {}
    for path in sorted(d.glob("*.md")):
        try:
            families.update(_parse_section_file(path))
        except OSError as exc:
            logger.warning("Could not read catalog file {p}: {err}", p=path, err=exc)
    return families


def _parse_section_file(path: Path) -> dict[str, TemplateFamily]:
    """Parse one section's markdown file into family entries.

    The grammar is intentionally narrow — see this module's docstring for the
    canonical layout. Anything we can't parse is skipped with a WARNING.
    """
    # Implementation lands in Task 3 — for now return empty so the skeleton
    # imports clean and the loader's directory-missing tests pass.
    return {}


class CatalogCache:
    """Process-wide single-load cache. Mirrors ``ActionTitlePopulator._catalog``."""

    _families: dict[str, TemplateFamily] | None = None

    @classmethod
    def get(cls, force_reload: bool = False) -> dict[str, TemplateFamily]:
        if cls._families is None or force_reload:
            cls._families = load_catalog()
        return cls._families


def select_variant(
    family_id: str,
    ctx_results: dict | None,
    client_id: str,
) -> Variant | None:
    """Select a variant for the given family. Stub — implemented in Task 4."""
    raise NotImplementedError("select_variant lands in Task 4")
```

- [ ] **Step 4: Re-run the test, verify it passes**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/output/template_catalog.py 01_Analysis/00-Scripts/tests/test_template_catalog.py
git commit -m "feat(decks): scaffold template_catalog loader + cache (POC step 1)"
```

---

## Task 3: Parse a section markdown file into TemplateFamily objects

**Files:**
- Modify: `01_Analysis/00-Scripts/output/template_catalog.py` — replace stub `_parse_section_file()` with real implementation.
- Modify: `01_Analysis/00-Scripts/tests/test_template_catalog.py` — add parse tests.
- Test fixture: `01_Analysis/00-Scripts/tests/fixtures/dctr_mini.md` (created inline by the test).

- [ ] **Step 1: Add the failing parse test**

Append to `01_Analysis/00-Scripts/tests/test_template_catalog.py`:

```python
import textwrap


def _write_mini_catalog(tmp_path: Path) -> Path:
    """Write a minimal DCTR section file with one family, two branches, two variants per branch."""
    d = tmp_path / "catalog"
    d.mkdir()
    (d / "dctr.md").write_text(textwrap.dedent("""
        # DCTR action titles

        ## Family: `dctr.activation_baseline`
        - **section:** `dctr`
        - **branch_if:** `dctr_1.rate`
        - **branches:**
          - `>= 0.55` → strong
          - `< 0.55` → opportunity
        - **fallback:** "DCTR performance snapshot."

        ### strong / variant 1 (data_first)
        - **template:** "DCTR at {dctr_rate} of {n_eligible} eligible — above the {peer_band} band."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `dctr_rate` | `dctr_1.rate` | `pct` |
          | `n_eligible` | `dctr_1.eligible_count` | `int` |
          | `peer_band` | `dctr_peer.upper_band_name` | `str` |

        ### strong / variant 2 (context_first)
        - **template:** "With {n_eligible} eligible accounts, DCTR at {dctr_rate} clears the {peer_band} bar."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `dctr_rate` | `dctr_1.rate` | `pct` |
          | `n_eligible` | `dctr_1.eligible_count` | `int` |
          | `peer_band` | `dctr_peer.upper_band_name` | `str` |

        ### opportunity / variant 1 (action_first)
        - **template:** "Closing the gap to peer median is the clearest near-term lever — DCTR sits at {dctr_rate}."
        - **placeholders:**
          | Slot | Path | Format |
          |---|---|---|
          | `dctr_rate` | `dctr_1.rate` | `pct` |
        """).lstrip(), encoding="utf-8")
    return d


def test_load_parses_one_family_with_two_branches(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    assert "dctr.activation_baseline" in catalog
    fam = catalog["dctr.activation_baseline"]
    assert fam.section == "dctr"
    assert fam.branch_path == "dctr_1.rate"
    assert [label for _, label in fam.branches] == ["strong", "opportunity"]
    assert fam.fallback == "DCTR performance snapshot."
    assert len(fam.variants["strong"]) == 2
    assert len(fam.variants["opportunity"]) == 1
    v = fam.variants["strong"][0]
    assert v.angle == "data_first"
    assert "{dctr_rate}" in v.template
    assert v.placeholders["dctr_rate"] == {"path": "dctr_1.rate", "format": "pct"}
```

- [ ] **Step 2: Run the test, verify it fails**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py::test_load_parses_one_family_with_two_branches -v
```
Expected: FAIL — `KeyError: 'dctr.activation_baseline'` because `_parse_section_file()` currently returns `{}`.

- [ ] **Step 3: Implement `_parse_section_file()`**

Replace the stub body in `01_Analysis/00-Scripts/output/template_catalog.py` with:

```python
_FAMILY_HDR_RE = re.compile(r"^##\s+Family:\s+`([^`]+)`\s*$")
_VARIANT_HDR_RE = re.compile(r"^###\s+(\S+)\s*/\s*variant\s+\d+\s*\((\w+)\)\s*$", re.IGNORECASE)
_KV_RE = re.compile(r"^\-\s+\*\*([^*]+)\*\*:\s*(.+?)\s*$")
_BRANCH_RULE_RE = re.compile(r"^\s*\-\s+`([^`]+)`\s*(?:→|->)\s*(\S+)\s*$")
_TEMPLATE_RE = re.compile(r"^\-\s+\*\*template:\*\*\s*\"(.+?)\"\s*$")
_FALLBACK_RE = re.compile(r"^\-\s+\*\*fallback:\*\*\s*\"(.+?)\"\s*$")
_TABLE_ROW_RE = re.compile(
    r"^\s*\|\s*`?([^|`]+?)`?\s*\|\s*`([^|`]+)`\s*\|\s*`([^|`]+)`\s*\|\s*$"
)


def _parse_section_file(path: Path) -> dict[str, TemplateFamily]:
    """Parse one section markdown file into ``{family_id: TemplateFamily}``."""
    text = path.read_text(encoding="utf-8")
    out: dict[str, TemplateFamily] = {}

    family_id: str | None = None
    section: str = ""
    branch_path: str | None = None
    branches: list[tuple[str, str]] = []
    variants: dict[str, list[Variant]] = {}
    fallback: str = ""
    cur_variant: Variant | None = None
    in_branches_list = False
    in_placeholder_table = False

    def _flush_variant() -> None:
        nonlocal cur_variant
        if cur_variant is not None:
            variants.setdefault(cur_variant.branch, []).append(cur_variant)
            cur_variant = None

    def _flush_family() -> None:
        nonlocal family_id, section, branch_path, branches, variants, fallback
        _flush_variant()
        if family_id is not None:
            out[family_id] = TemplateFamily(
                id=family_id,
                section=section,
                branch_path=branch_path,
                branches=list(branches),
                variants=dict(variants),
                fallback=fallback,
            )
        family_id = None
        section = ""
        branch_path = None
        branches = []
        variants = {}
        fallback = ""

    for raw in text.splitlines():
        m_fam = _FAMILY_HDR_RE.match(raw)
        if m_fam:
            _flush_family()
            family_id = m_fam.group(1).strip()
            in_branches_list = False
            in_placeholder_table = False
            continue
        if family_id is None:
            continue

        m_var = _VARIANT_HDR_RE.match(raw)
        if m_var:
            _flush_variant()
            cur_variant = Variant(
                branch=m_var.group(1).strip().lower(),
                angle=m_var.group(2).strip().lower(),
                template="",
            )
            in_branches_list = False
            in_placeholder_table = False
            continue

        if cur_variant is not None:
            m_tpl = _TEMPLATE_RE.match(raw)
            if m_tpl:
                cur_variant.template = m_tpl.group(1)
                continue
            if raw.lstrip().startswith("|"):
                m_row = _TABLE_ROW_RE.match(raw)
                if m_row:
                    slot = m_row.group(1).strip()
                    if slot.lower() in ("slot", "---"):
                        in_placeholder_table = True
                        continue
                    cur_variant.placeholders[slot] = {
                        "path": m_row.group(2).strip(),
                        "format": m_row.group(3).strip(),
                    }
                    in_placeholder_table = True
                    continue
            continue

        # Family-level lines (we're between family header and first variant).
        m_kv = _KV_RE.match(raw)
        if m_kv:
            key = m_kv.group(1).strip().lower()
            val = m_kv.group(2).strip().strip("`")
            if key == "section":
                section = val
            elif key == "branch_if":
                branch_path = val
            elif key == "branches":
                in_branches_list = True
                continue
            in_branches_list = False
            continue

        if in_branches_list:
            m_rule = _BRANCH_RULE_RE.match(raw)
            if m_rule:
                branches.append((m_rule.group(1).strip(), m_rule.group(2).strip().lower()))
                continue
            if raw.strip() == "":
                continue
            in_branches_list = False

        m_fb = _FALLBACK_RE.match(raw)
        if m_fb:
            fallback = m_fb.group(1)

    _flush_family()
    return out
```

- [ ] **Step 4: Re-run all template_catalog tests**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/output/template_catalog.py 01_Analysis/00-Scripts/tests/test_template_catalog.py
git commit -m "feat(decks): parse branching section files into TemplateFamily (POC step 1)"
```

---

## Task 4: Implement `select_variant()` with branch-rule eval + stable hash

**Files:**
- Modify: `01_Analysis/00-Scripts/output/template_catalog.py` — replace `select_variant()` stub.
- Modify: `01_Analysis/00-Scripts/tests/test_template_catalog.py` — add selection tests.

- [ ] **Step 1: Add the failing selection tests**

Append to `01_Analysis/00-Scripts/tests/test_template_catalog.py`:

```python
def test_select_variant_uses_strong_branch_when_rate_above_threshold(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    v = template_catalog.select_variant_from_family(
        fam, ctx_results={"dctr_1": {"rate": 0.62}}, client_id="1615"
    )
    assert v is not None
    assert v.branch == "strong"


def test_select_variant_uses_opportunity_branch_when_rate_below_threshold(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    v = template_catalog.select_variant_from_family(
        fam, ctx_results={"dctr_1": {"rate": 0.20}}, client_id="1615"
    )
    assert v is not None
    assert v.branch == "opportunity"


def test_select_variant_is_stable_across_calls(tmp_path: Path) -> None:
    """Same client + family must always pick the same variant — repeatable reruns."""
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    ctx = {"dctr_1": {"rate": 0.62}}
    picks = {template_catalog.select_variant_from_family(fam, ctx, "1615").angle for _ in range(10)}
    assert len(picks) == 1


def test_select_variant_returns_none_when_branch_value_missing(tmp_path: Path) -> None:
    d = _write_mini_catalog(tmp_path)
    catalog = template_catalog.load_catalog(catalog_dir=d)
    fam = catalog["dctr.activation_baseline"]
    v = template_catalog.select_variant_from_family(fam, ctx_results={}, client_id="1615")
    assert v is None
```

- [ ] **Step 2: Run the tests, verify they fail**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py -v
```
Expected: 4 new tests FAIL — `AttributeError: module 'ars_analysis.output.template_catalog' has no attribute 'select_variant_from_family'`.

- [ ] **Step 3: Implement `select_variant_from_family()` + rewrite `select_variant()`**

In `01_Analysis/00-Scripts/output/template_catalog.py`, replace the `select_variant()` stub at the bottom of the file with:

```python
# Branch rule grammar (intentionally narrow):
#   ">= 0.55"   ">0.55"   "<= 0.30"  "<0.30"  "==0"
#   "0.40..0.54"  (inclusive range)
#   "null"        (matches None / NaN)
_RANGE_RE = re.compile(r"^\s*([0-9.]+)\s*\.\.\s*([0-9.]+)\s*$")
_OP_RE = re.compile(r"^\s*(>=|<=|>|<|==)\s*(-?[0-9.]+)\s*$")


def _walk_path(path: str, ctx_results: dict) -> Any:
    """Dotted ``ctx.results`` walk; returns None on any miss."""
    if not path:
        return None
    obj: Any = ctx_results
    for seg in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(seg)
        else:
            obj = getattr(obj, seg, None)
        if obj is None:
            return None
    return obj


def _rule_matches(rule: str, value: Any) -> bool:
    rule = rule.strip()
    if rule.lower() == "null":
        return value is None
    if value is None:
        return False
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    m = _RANGE_RE.match(rule)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return lo <= v <= hi
    m = _OP_RE.match(rule)
    if not m:
        return False
    op, threshold = m.group(1), float(m.group(2))
    return {
        ">=": v >= threshold,
        "<=": v <= threshold,
        ">":  v > threshold,
        "<":  v < threshold,
        "==": v == threshold,
    }[op]


def _hash_index(client_id: str, family_id: str, modulus: int) -> int:
    """Stable index — md5, NOT Python's process-salted hash()."""
    h = hashlib.md5(f"{client_id}|{family_id}".encode("utf-8")).hexdigest()
    return int(h, 16) % max(modulus, 1)


def select_variant_from_family(
    family: TemplateFamily,
    ctx_results: dict | None,
    client_id: str,
) -> Variant | None:
    """Pick a variant for ``family`` given the data + client id."""
    ctx_results = ctx_results or {}
    if not family.branches or family.branch_path is None:
        return None
    value = _walk_path(family.branch_path, ctx_results)
    matched_branch: str | None = None
    for rule, label in family.branches:
        if _rule_matches(rule, value):
            matched_branch = label
            break
    if matched_branch is None:
        return None
    pool = family.variants.get(matched_branch, [])
    if not pool:
        return None
    idx = _hash_index(client_id, family.id, len(pool))
    return pool[idx]


def select_variant(
    family_id: str,
    ctx_results: dict | None,
    client_id: str,
) -> Variant | None:
    """Public entry point: look up the family from the cache, then select."""
    catalog = CatalogCache.get()
    family = catalog.get(family_id)
    if family is None:
        return None
    return select_variant_from_family(family, ctx_results, client_id)
```

- [ ] **Step 4: Re-run tests, verify all pass**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/output/template_catalog.py 01_Analysis/00-Scripts/tests/test_template_catalog.py
git commit -m "feat(decks): branching variant selection with stable md5 hash (POC step 1)"
```

---

## Task 5: Author the DCTR branching catalog (~20 templates)

**Files:**
- Create: `docs/action_title_templates/dctr.md`

**Why 20 templates here:** 5 families × (3 branches × 3 variants + 1 fallback) ≈ 50 sentence-worth of authoring is the spec target. For POC we author 5 families × 4 branches × 3 variants = 60 sentences condensed into 20 distinct sentence shapes by re-using sentence skeletons across the data-first / context-first / action-first angles.

The 5 DCTR families (consistent with the entries already in `_SLIDE_TEMPLATE_MAP`):
- `dctr.activation_baseline` → branches by `dctr_1.rate`
- `dctr.peer_comparison` → branches by `dctr_peer.gap_pp` (positive vs negative)
- `dctr.growth_driver` → branches by `dctr_growth.yoy_pp`
- `dctr.momentum` → branches by `dctr_momentum.last_quarter_pp`
- `dctr.opportunity_size` → branches by `dctr_value.usd_opportunity` (small / mid / large)

- [ ] **Step 1: Create the docs directory + file**

Create `docs/action_title_templates/dctr.md`. Use the grammar this plan's Task 3 already locked in. Content:

```markdown
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
```

- [ ] **Step 2: Sanity-check the catalog parses cleanly**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -c "
from ars_analysis.output import template_catalog
cat = template_catalog.load_catalog()
print(f'Families loaded: {len(cat)}')
for fid in sorted(cat):
    fam = cat[fid]
    print(f'  {fid}: {len(fam.branches)} branches, variants={ {b: len(vs) for b, vs in fam.variants.items()} }')
"
```
Expected:
- `Families loaded: 5`
- Each family shows its branches and 3 variants per branch (e.g. `{'strong': 3, 'healthy': 3, 'opportunity': 3, 'urgent': 3}` for `dctr.activation_baseline`).

If counts are wrong, the catalog markdown grammar drifted — fix the file before continuing.

- [ ] **Step 3: Commit**

```bash
git add docs/action_title_templates/dctr.md
git commit -m "feat(decks): author DCTR branching catalog (5 families, ~50 variants) (POC step 1)"
```

---

## Task 6: Wire `template_catalog.select_variant()` into `ActionTitlePopulator.populate()`

**Files:**
- Modify: `01_Analysis/00-Scripts/output/action_title_populator.py` — `populate()` consults the branching catalog first.
- Modify: `01_Analysis/00-Scripts/tests/test_template_catalog.py` — add integration test that exercises the populator path.

- [ ] **Step 1: Add the failing populator integration test**

Append to `01_Analysis/00-Scripts/tests/test_template_catalog.py`:

```python
import pytest


@pytest.fixture
def _stub_ctx():
    """Minimal stand-in for PipelineContext (only ``.client.client_name`` is read)."""
    class _Client:
        client_name = "Guardians CU"
    class _Ctx:
        client = _Client()
    return _Ctx()


def test_populator_uses_branching_catalog_when_present(tmp_path, monkeypatch, _stub_ctx):
    """Family found in branching catalog wins over the flat fallback."""
    from ars_analysis.output.action_title_populator import ActionTitlePopulator

    d = _write_mini_catalog(tmp_path)
    # Prime the cache with the test catalog dir.
    template_catalog.CatalogCache._families = template_catalog.load_catalog(catalog_dir=d)
    # Also force the flat populator's cache to be empty so we can prove the branching
    # catalog handled this call.
    ActionTitlePopulator._catalog = {}

    title = ActionTitlePopulator.populate(
        template_id="dctr.activation_baseline",
        ctx_results={"dctr_1": {"rate": 0.62, "eligible_count": 12400},
                     "dctr_peer": {"upper_band_name": "upper quartile"}},
        ctx=_stub_ctx,
        fallback_title="default",
    )
    assert "{" not in title    # All placeholders substituted.
    assert title != "default"   # Did not fall through to the absolute fallback.
    # Reset caches so other tests aren't polluted.
    template_catalog.CatalogCache._families = None
    ActionTitlePopulator._catalog = None
```

- [ ] **Step 2: Run the test, verify it fails**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py::test_populator_uses_branching_catalog_when_present -v
```
Expected: FAIL — populator returns `"default"` because it doesn't yet consult `template_catalog`.

- [ ] **Step 3: Update `ActionTitlePopulator.populate()` to consult the branching catalog first**

In `01_Analysis/00-Scripts/output/action_title_populator.py`, modify the `populate()` classmethod. Find the existing body (currently starts with `catalog = cls.catalog()`) and replace it with:

```python
    @classmethod
    def populate(
        cls,
        template_id: str,
        ctx_results: dict | None,
        ctx: Any | None = None,
        fallback_title: str = "",
    ) -> str:
        """Render an action title.

        Order of attempts:
          1. Branching catalog (``output/template_catalog.py``) — chosen by
             variant rules + stable hash of client id.
          2. Flat catalog (``docs/action_title_templates.md``) — legacy.
          3. ``fallback_title``.
        """
        # 1. Branching catalog
        try:
            from ars_analysis.output import template_catalog
            client_id = ""
            if ctx is not None:
                client = getattr(ctx, "client", None)
                client_id = str(getattr(client, "client_id", "") or getattr(client, "client_name", ""))
            variant = template_catalog.select_variant(
                template_id, ctx_results or {}, client_id or "default"
            )
            if variant is not None:
                rendered = cls._render_variant(variant, ctx_results or {}, ctx)
                if rendered is not None:
                    return rendered
                family = template_catalog.CatalogCache.get().get(template_id)
                if family is not None and family.fallback:
                    return family.fallback
        except Exception as exc:
            logger.warning(
                "Branching catalog lookup failed for {tid}: {err}; falling back to flat catalog",
                tid=template_id, err=exc,
            )

        # 2. Flat catalog (legacy path; unchanged from prior behavior)
        catalog = cls.catalog()
        block = catalog.get(template_id)
        if block is None:
            return fallback_title or template_id

        resolved: dict[str, str] = {}
        ok = True
        for name, meta in block.placeholders.items():
            raw = extract_value(meta.get("path", ""), ctx_results or {}, ctx)
            formatted = format_value(raw, meta.get("format", "str"))
            if formatted is None:
                ok = False
                logger.info(
                    "Action title {tid}: missing/invalid value for {{{name}}} (path={path})",
                    tid=template_id, name=name, path=meta.get("path", "?"),
                )
                break
            resolved[name] = formatted

        if ok:
            try:
                return block.template.format(**resolved)
            except (KeyError, IndexError) as exc:
                logger.warning(
                    "Action title {tid}: substitution failed ({err}); using fallback",
                    tid=template_id, err=exc,
                )

        if block.fallback:
            try:
                return block.fallback.format(**resolved) if "{" in block.fallback else block.fallback
            except (KeyError, IndexError):
                return block.fallback

        return fallback_title or template_id

    @classmethod
    def _render_variant(cls, variant, ctx_results: dict, ctx: Any | None) -> str | None:
        """Substitute a Variant's placeholders. Returns None if any required slot
        can't be resolved (so the caller can use the family-level fallback)."""
        resolved: dict[str, str] = {}
        for name, meta in variant.placeholders.items():
            raw = extract_value(meta.get("path", ""), ctx_results, ctx)
            formatted = format_value(raw, meta.get("format", "str"))
            if formatted is None:
                return None
            resolved[name] = formatted
        try:
            return variant.template.format(**resolved)
        except (KeyError, IndexError):
            return None
```

- [ ] **Step 4: Re-run all populator + catalog tests**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_template_catalog.py -v
```
Expected: all 8 tests passed.

- [ ] **Step 5: Confirm legacy populator tests (if any) still pass**

Run the full test suite to catch regressions:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/ -v 2>&1 | tail -30
```
Expected: zero new failures; pre-existing failures (if documented elsewhere) unchanged.

- [ ] **Step 6: Commit**

```bash
git add 01_Analysis/00-Scripts/output/action_title_populator.py 01_Analysis/00-Scripts/tests/test_template_catalog.py
git commit -m "feat(decks): populator delegates to branching catalog before flat fallback (POC step 4 partial)"
```

---

## Task 7: Scaffold `shared/charts/themes.py` with the Plotly base template

**Files:**
- Create: `01_Analysis/00-Scripts/shared/charts/__init__.py` (empty marker file).
- Create: `01_Analysis/00-Scripts/shared/charts/themes.py`
- Test: `01_Analysis/00-Scripts/tests/test_themed_chart.py`

- [ ] **Step 1: Write the failing test for the layout template**

Create `01_Analysis/00-Scripts/tests/test_themed_chart.py`:

```python
"""Tests for shared/charts/themes.py (autonomous decks POC, design §B)."""
from __future__ import annotations

import pandas as pd

from ars_analysis.shared.charts import themes


def test_base_layout_has_expected_font_family():
    layout = themes.base_layout()
    assert layout["font"]["family"].lower().startswith("arial")


def test_base_layout_origin_is_zero():
    layout = themes.base_layout()
    # Y axis must start at zero by default — SLIDE_DESIGN.md §6.
    assert layout["yaxis"]["rangemode"] == "tozero"


def test_base_layout_no_default_axis_titles():
    layout = themes.base_layout()
    assert (layout["xaxis"]["title"]["text"] or "") == ""
    assert (layout["yaxis"]["title"]["text"] or "") == ""
```

- [ ] **Step 2: Run the test, verify it fails on import**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_themed_chart.py -v
```
Expected: `ModuleNotFoundError: ars_analysis.shared.charts`.

- [ ] **Step 3: Create the package marker + themes module**

Create `01_Analysis/00-Scripts/shared/charts/__init__.py`:

```python
"""Plotly-themed chart engine (autonomous decks design §B)."""
```

Create `01_Analysis/00-Scripts/shared/charts/themes.py`:

```python
"""Plotly-themed chart engine.

A single ``themed_chart()`` function over a base Plotly layout that encodes
SLIDE_DESIGN.md §5–6 defaults: Arial 11pt, hero series in section accent,
peer median annotated, source line baked in, origin at zero.

POC scope: ``kind="rate_volume_combo"`` only. The dispatcher raises
``UnsupportedKind`` for everything else, so callers can fall back to their
existing matplotlib path (and the meta JSON can record `chart_engine:
matplotlib_fallback` — landed in the long-tail plan).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ars_analysis.shared.charts_palette import section_color, COLORS  # noqa: F401  (alias kept for downstream)


class UnsupportedKind(ValueError):
    """Raised by ``themed_chart`` when ``kind`` is not implemented yet."""


def base_layout() -> dict[str, Any]:
    """Return the canonical Plotly layout dict for the deck.

    Returned as a plain dict so tests can introspect keys without importing
    Plotly. ``themed_chart()`` passes this directly to ``fig.update_layout``.
    """
    return {
        "font": {"family": "Arial, Helvetica, sans-serif", "size": 11, "color": "#1E3D59"},
        "paper_bgcolor": "white",
        "plot_bgcolor": "white",
        "margin": {"l": 60, "r": 40, "t": 60, "b": 60},
        "showlegend": True,
        "legend": {"orientation": "h", "yanchor": "bottom", "y": -0.25, "x": 0.5, "xanchor": "center"},
        "xaxis": {
            "showgrid": False,
            "linecolor": "#BFC9D1",
            "ticks": "outside",
            "title": {"text": "", "font": {"size": 11}},
        },
        "yaxis": {
            "rangemode": "tozero",
            "showgrid": True,
            "gridcolor": "#EFF2F5",
            "zeroline": True,
            "zerolinecolor": "#BFC9D1",
            "title": {"text": "", "font": {"size": 11}},
        },
        "width": 1500,
        "height": 900,
    }
```

Note the import path `ars_analysis.shared.charts_palette` — the existing colors module lives at `01_Analysis/00-Scripts/shared/charts.py`, but to avoid colliding with the new package `shared/charts/`, we'll rename it in the next step.

- [ ] **Step 4: Resolve the package/module name collision**

The existing module `01_Analysis/00-Scripts/shared/charts.py` collides with the new package directory `01_Analysis/00-Scripts/shared/charts/`. Rename the old module to keep both alive:

```bash
git mv 01_Analysis/00-Scripts/shared/charts.py 01_Analysis/00-Scripts/shared/charts_palette.py
```

Now find every importer of the old path and update it. Run:

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow && grep -rn "from ars_analysis.shared.charts import\|from ars_analysis.shared import charts\b\|ars_analysis.shared.charts\b" 01_Analysis/00-Scripts/ --include="*.py" | grep -v "shared/charts/" | grep -v "charts_palette" 
```

For each match, change `ars_analysis.shared.charts` → `ars_analysis.shared.charts_palette`. Do this with `Edit` (one file at a time) — do not pipe through `sed`.

- [ ] **Step 5: Re-run themed_chart tests, verify they pass**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_themed_chart.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Re-run the full test suite to catch import-rename fallout**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/ -v 2>&1 | tail -30
```
Expected: zero new failures attributable to the rename. If any test fails with `ModuleNotFoundError: ars_analysis.shared.charts`, an importer was missed — go back to Step 4.

- [ ] **Step 7: Commit**

```bash
git add 01_Analysis/00-Scripts/shared/charts_palette.py 01_Analysis/00-Scripts/shared/charts/__init__.py 01_Analysis/00-Scripts/shared/charts/themes.py 01_Analysis/00-Scripts/tests/test_themed_chart.py
git add -u   # stage modified importers
git commit -m "feat(decks): scaffold shared/charts/themes.py + base layout (POC step 2)"
```

---

## Task 8: Implement `themed_chart(kind="rate_volume_combo")`

**Files:**
- Modify: `01_Analysis/00-Scripts/shared/charts/themes.py` — add `themed_chart()` + `_render_rate_volume_combo()`.
- Modify: `01_Analysis/00-Scripts/tests/test_themed_chart.py` — add rendering tests.

`rate_volume_combo` is the shape `dctr/trends.py::_decade_trend` builds today: gray bars (volume) on a secondary axis behind a colored rate line on the primary axis, peer-median annotation, source line baked in, origin at zero.

- [ ] **Step 1: Add the failing rendering test**

Append to `01_Analysis/00-Scripts/tests/test_themed_chart.py`:

```python
from pathlib import Path


def test_themed_chart_rate_volume_combo_writes_png(tmp_path: Path):
    df = pd.DataFrame(
        {
            "bucket": ["10-19", "20-29", "30-39", "40-49", "50-59", "60+"],
            "volume": [400, 1800, 2400, 2100, 1600, 700],
            "rate": [0.18, 0.36, 0.44, 0.41, 0.30, 0.21],
        }
    )
    out = tmp_path / "dctr_decade.png"
    written = themes.themed_chart(
        kind="rate_volume_combo",
        data=df,
        section_key="dctr",
        hero_series="rate",
        volume_series="volume",
        x_series="bucket",
        peer_median=0.34,
        your_value=0.42,
        source="dctr_1.decade",
        out_path=out,
    )
    assert written == out
    assert out.exists()
    assert out.stat().st_size > 0


def test_themed_chart_unknown_kind_raises():
    df = pd.DataFrame({"x": [0], "y": [0]})
    try:
        themes.themed_chart(
            kind="not_a_real_kind",
            data=df,
            section_key="dctr",
            hero_series="y",
            volume_series=None,
            x_series="x",
            peer_median=None,
            your_value=None,
            source="test",
            out_path=Path("/tmp/should_not_exist.png"),
        )
    except themes.UnsupportedKind:
        return
    raise AssertionError("Expected UnsupportedKind to be raised.")
```

- [ ] **Step 2: Run the tests, verify they fail**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_themed_chart.py -v
```
Expected: 2 new tests FAIL — `AttributeError: module ... has no attribute 'themed_chart'`.

- [ ] **Step 3: Implement `themed_chart()` + `_render_rate_volume_combo()`**

Append to `01_Analysis/00-Scripts/shared/charts/themes.py`:

```python
def themed_chart(
    *,
    kind: str,
    data: pd.DataFrame,
    section_key: str,
    hero_series: str,
    x_series: str,
    volume_series: str | None = None,
    peer_median: float | None = None,
    your_value: float | None = None,
    source: str,
    out_path: Path,
) -> Path:
    """Render a themed chart PNG.

    Only ``kind="rate_volume_combo"`` is implemented in the POC. Other kinds
    raise ``UnsupportedKind`` so callers can fall back to their existing
    matplotlib path.

    All arguments after ``kind`` are keyword-only — every call site reads as
    a labeled record. This is deliberate; the function will eventually accept
    8+ params and positional ordering would be a footgun.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "rate_volume_combo":
        return _render_rate_volume_combo(
            data=data,
            section_key=section_key,
            hero_series=hero_series,
            volume_series=volume_series,
            x_series=x_series,
            peer_median=peer_median,
            your_value=your_value,
            source=source,
            out_path=out_path,
        )
    raise UnsupportedKind(f"themed_chart kind={kind!r} not implemented yet")


def _render_rate_volume_combo(
    *,
    data: pd.DataFrame,
    section_key: str,
    hero_series: str,
    volume_series: str | None,
    x_series: str,
    peer_median: float | None,
    your_value: float | None,  # noqa: ARG001 — reserved for future annotation
    source: str,
    out_path: Path,
) -> Path:
    import plotly.graph_objects as go

    accent = section_color(section_key)
    x = data[x_series].tolist()
    rates_raw = data[hero_series].astype(float).tolist()
    rates_pct = [v * 100 for v in rates_raw]  # display as percent

    fig = go.Figure()

    if volume_series and volume_series in data.columns:
        fig.add_trace(
            go.Bar(
                x=x,
                y=data[volume_series].astype(float).tolist(),
                name="Volume",
                marker={"color": "#D9DEE3"},
                yaxis="y2",
                hovertemplate="%{y:,.0f}<extra>Volume</extra>",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=x,
            y=rates_pct,
            name=hero_series,
            mode="lines+markers",
            line={"color": accent, "width": 3},
            marker={"size": 9, "color": accent},
            hovertemplate="%{y:.1f}%<extra>" + hero_series + "</extra>",
        )
    )

    layout = base_layout()
    layout["yaxis"]["title"] = {"text": "Rate", "font": {"size": 11}}
    layout["yaxis"]["ticksuffix"] = "%"
    if volume_series and volume_series in data.columns:
        layout["yaxis2"] = {
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "rangemode": "tozero",
            "title": {"text": "Volume", "font": {"size": 11, "color": "#999"}},
            "tickfont": {"color": "#999"},
        }
    fig.update_layout(**layout)

    if peer_median is not None:
        fig.add_hline(
            y=peer_median * 100,
            line={"color": "#555555", "dash": "dash", "width": 1.5},
            annotation_text=f"Peer median {peer_median * 100:.0f}%",
            annotation_position="top left",
            annotation_font={"color": "#555555", "size": 10},
        )

    if source:
        fig.add_annotation(
            text=f"Source: {source}",
            xref="paper", yref="paper",
            x=0, y=-0.18,
            showarrow=False,
            font={"size": 9, "color": "#888"},
            align="left",
        )

    fig.write_image(str(out_path), scale=1)
    return out_path
```

- [ ] **Step 4: Re-run tests, verify all pass**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_themed_chart.py -v
```
Expected: 5 passed (3 layout + 2 render).

- [ ] **Step 5: Eyeball one generated PNG**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -c "
from pathlib import Path
import pandas as pd
from ars_analysis.shared.charts import themes
df = pd.DataFrame({
    'bucket': ['10-19', '20-29', '30-39', '40-49', '50-59', '60+'],
    'volume': [400, 1800, 2400, 2100, 1600, 700],
    'rate':   [0.18, 0.36, 0.44, 0.41, 0.30, 0.21],
})
out = Path('/tmp/themed_chart_sanity.png')
themes.themed_chart(
    kind='rate_volume_combo', data=df, section_key='dctr',
    hero_series='rate', volume_series='volume', x_series='bucket',
    peer_median=0.34, your_value=0.42, source='dctr_1.decade',
    out_path=out,
)
print('wrote', out, out.stat().st_size, 'bytes')
"
open /tmp/themed_chart_sanity.png
```
Expected: a 1500×900 PNG opens, with a teal line on top of gray volume bars, dashed peer-median line at ~34%, "Source: dctr_1.decade" footer. If the layout looks broken (axes inverted, missing peer line, etc.) — fix `_render_rate_volume_combo` before continuing; do not commit a broken first chart.

- [ ] **Step 6: Commit**

```bash
git add 01_Analysis/00-Scripts/shared/charts/themes.py 01_Analysis/00-Scripts/tests/test_themed_chart.py
git commit -m "feat(decks): implement themed_chart(rate_volume_combo) with peer-median annotation (POC step 2)"
```

---

## Task 9: Migrate `analytics/dctr/trends.py::_decade_trend` to `themed_chart()`

**Files:**
- Modify: `01_Analysis/00-Scripts/analytics/dctr/trends.py` — `_decade_trend()` calls `themed_chart()`; existing matplotlib block kept as fallback inside the same try/except.

- [ ] **Step 1: Add an integration test against fixture data**

Create `01_Analysis/00-Scripts/tests/test_dctr_trends_themed.py`:

```python
"""Verify analytics/dctr/trends._decade_trend can produce a themed PNG."""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def _ctx(tmp_path):
    """Build a minimal PipelineContext-shaped stub."""
    paths = types.SimpleNamespace(charts_dir=tmp_path, base_dir=tmp_path.parent)
    client = types.SimpleNamespace(client_name="Test Client", client_id="1615", month="2026.05")
    results = {
        "dctr_1": {"decade": pd.DataFrame({
            "Decade":         ["10-19", "20-29", "30-39", "40-49", "50-59", "60+"],
            "DCTR %":         [0.18,    0.36,    0.44,    0.41,    0.30,    0.21],
            "Total Accounts": [400,     1800,    2400,    2100,    1600,    700],
        })},
        "dctr_4": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
        "dctr_5": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
    }
    return types.SimpleNamespace(paths=paths, client=client, results=results, settings=None)


def test_decade_trend_emits_png_via_themed_chart(_ctx, tmp_path):
    from ars_analysis.analytics.dctr.trends import DctrTrendsModule
    out = DctrTrendsModule()._decade_trend(_ctx)
    assert len(out) == 1
    result = out[0]
    assert result.slide_id == "A7.5"
    assert result.chart_path is not None
    assert Path(result.chart_path).exists()
```

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_dctr_trends_themed.py -v
```
Expected: PASS — `_decade_trend` already produces a PNG via the matplotlib path. (This test acts as a regression net for the migration: it should keep passing after we swap to Plotly.)

- [ ] **Step 2: Modify `_decade_trend()` to prefer `themed_chart()`**

Open `01_Analysis/00-Scripts/analytics/dctr/trends.py` and replace the contents of `_decade_trend()` (the function spanning approximately lines 178–288). Keep the result-construction tail unchanged; only swap the chart-rendering block.

New body:

```python
    def _decade_trend(self, ctx: PipelineContext) -> list[AnalysisResult]:
        d1 = ctx.results.get("dctr_1", {}).get("decade", pd.DataFrame())
        if d1.empty:
            return []

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_decade_trend.png"
            try:
                from ars_analysis.shared.charts import themes
                df_plot = pd.DataFrame({
                    "Decade": d1["Decade"].values,
                    "DCTR %": d1["DCTR %"].astype(float).values,
                    "Total Accounts": d1["Total Accounts"].astype(float).values,
                })
                themes.themed_chart(
                    kind="rate_volume_combo",
                    data=df_plot,
                    section_key="dctr",
                    hero_series="DCTR %",
                    volume_series="Total Accounts",
                    x_series="Decade",
                    peer_median=None,
                    your_value=None,
                    source="dctr_1.decade",
                    out_path=save_to,
                )
                chart_path = save_to
            except themes.UnsupportedKind:
                logger.info("A7.5 kind not implemented in themed_chart; using matplotlib fallback")
                chart_path = self._decade_trend_matplotlib_fallback(ctx, save_to, d1)
            except Exception as exc:
                logger.warning("A7.5 themed_chart failed ({err}); using matplotlib fallback", err=exc)
                chart_path = self._decade_trend_matplotlib_fallback(ctx, save_to, d1)

        return [
            AnalysisResult(
                slide_id="A7.5",
                title="Historical Debit Card Take Rate Trend by Decade",
                chart_path=chart_path,
                excel_data={"Decade": d1},
                notes=f"{len(d1)} decades plotted",
            )
        ]

    def _decade_trend_matplotlib_fallback(
        self, ctx: PipelineContext, save_to: Path, d1: pd.DataFrame
    ) -> Path | None:
        """Original matplotlib renderer, preserved as fallback when themed_chart
        is unavailable or raises. Behavior identical to the pre-POC code."""
        d4 = ctx.results.get("dctr_4", {}).get("decade", pd.DataFrame())
        d5 = ctx.results.get("dctr_5", {}).get("decade", pd.DataFrame())
        try:
            decades = d1["Decade"].values
            overall = d1["DCTR %"].values * 100
            x = np.arange(len(decades))

            with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
                ax2 = ax.twinx()
                total_vol = d1["Total Accounts"].values
                ax2.bar(x, total_vol, alpha=0.2, color="gray", edgecolor="none", width=0.8)
                ax2.set_ylabel("Account Volume", fontsize=24, color="gray")
                max_vol = max(total_vol) if len(total_vol) > 0 else 100
                ax2.set_ylim(0, max_vol * 1.3)
                ax2.tick_params(axis="y", colors="gray", labelsize=24)

                ax.plot(
                    x, overall, color="black", linewidth=3, linestyle="--",
                    marker="o", markersize=18, label="Overall", zorder=2,
                )

                if not d4.empty:
                    p_merged = d4.set_index("Decade").reindex(decades)
                    p_vals = p_merged["DCTR %"].values * 100
                    valid_mask = ~np.isnan(p_vals)
                    if valid_mask.any():
                        ax.plot(
                            x[valid_mask], p_vals[valid_mask], color=PERSONAL,
                            linewidth=4, marker="o", markersize=12, label="Personal", zorder=3,
                        )

                if not d5.empty and d5["Total Accounts"].sum() > 0:
                    b_merged = d5.set_index("Decade").reindex(decades)
                    b_vals = b_merged["DCTR %"].values * 100
                    valid_mask = ~np.isnan(b_vals)
                    if valid_mask.any():
                        ax.plot(
                            x[valid_mask], b_vals[valid_mask], color=BUSINESS,
                            linewidth=4, marker="s", markersize=12, label="Business", zorder=3,
                        )

                ax.set_xticks(x)
                ax.set_xticklabels(decades, fontsize=24, rotation=45 if len(decades) > 8 else 0)
                ax.set_ylabel("DCTR (%)", fontsize=24, fontweight="bold")
                ax.set_title("Historical DCTR Trend by Decade", fontsize=24, fontweight="bold", pad=20)
                ax.set_ylim(0, min(110, max(overall) * 1.15) if len(overall) > 0 else 100)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x)}%"))
                ax.tick_params(axis="y", labelsize=24)
                ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=18)
                ax.set_axisbelow(True)
                ax.spines["top"].set_visible(False)
                ax2.spines["top"].set_visible(False)

                if len(overall) >= 2:
                    diffs = np.diff(overall)
                    best_idx = int(np.argmax(diffs)) + 1
                    ax.annotate(
                        f"+{diffs[best_idx - 1]:.1f}pp",
                        xy=(best_idx, overall[best_idx]),
                        xytext=(best_idx, overall[best_idx] + 5),
                        fontsize=14, fontweight="bold", color=TEAL, ha="center",
                        arrowprops={"arrowstyle": "->", "color": TEAL, "lw": 2},
                    )
            return save_to
        except Exception as exc:
            logger.warning("A7.5 matplotlib fallback failed: {err}", err=exc)
            return None
```

Note: the function references `Path` in its signature — confirm `from pathlib import Path` is already imported at the top of `trends.py`. If not, add it.

- [ ] **Step 3: Re-run the dctr trends test, verify it still passes**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_dctr_trends_themed.py -v
```
Expected: PASS — `_decade_trend` now produces a PNG via the Plotly path.

- [ ] **Step 4: Eyeball the migrated chart**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -c "
import sys, types
from pathlib import Path
import pandas as pd
from ars_analysis.analytics.dctr.trends import DctrTrendsModule

tmp = Path('/tmp/dctr_themed_check')
tmp.mkdir(exist_ok=True)
paths = types.SimpleNamespace(charts_dir=tmp, base_dir=tmp.parent)
client = types.SimpleNamespace(client_name='Test', client_id='1615', month='2026.05')
results = {
    'dctr_1': {'decade': pd.DataFrame({
        'Decade': ['10-19','20-29','30-39','40-49','50-59','60+'],
        'DCTR %': [0.18,0.36,0.44,0.41,0.30,0.21],
        'Total Accounts': [400,1800,2400,2100,1600,700],
    })},
    'dctr_4': {'decade': pd.DataFrame(columns=['Decade','DCTR %','Total Accounts'])},
    'dctr_5': {'decade': pd.DataFrame(columns=['Decade','DCTR %','Total Accounts'])},
}
ctx = types.SimpleNamespace(paths=paths, client=client, results=results, settings=None)
r = DctrTrendsModule()._decade_trend(ctx)
print('chart_path:', r[0].chart_path)
"
open /tmp/dctr_themed_check/dctr_decade_trend.png
```
Expected: a clean Plotly PNG. Compare visually against an old matplotlib PNG if one is around. The new chart should match the SLIDE_DESIGN.md §5–6 defaults: teal line, gray volume bars, no axis title saying "Values", origin at zero.

- [ ] **Step 5: Run the full test suite for regressions**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/ -v 2>&1 | tail -30
```
Expected: zero new failures.

- [ ] **Step 6: Commit**

```bash
git add 01_Analysis/00-Scripts/analytics/dctr/trends.py 01_Analysis/00-Scripts/tests/test_dctr_trends_themed.py
git commit -m "feat(decks): migrate dctr/_decade_trend to themed_chart with matplotlib fallback (POC step 2)"
```

---

## Task 10: Scaffold `output/structural_slides.py` with stub builders

**Files:**
- Create: `01_Analysis/00-Scripts/output/structural_slides.py`
- Test: `01_Analysis/00-Scripts/tests/test_structural_slides.py`

The POC only implements `build_cover()`. The remaining four builders land in the long-tail plan; here they exist as `None`-returning stubs so the wire-in code in `deck_builder.py` can already import their names.

- [ ] **Step 1: Write the failing test for `build_cover()`**

Create `01_Analysis/00-Scripts/tests/test_structural_slides.py`:

```python
"""Tests for output/structural_slides.py (autonomous decks design §C)."""
from __future__ import annotations

from ars_analysis.output import structural_slides


def test_build_cover_returns_slide_with_lead_finding_subline():
    sc = structural_slides.build_cover(
        client_name="Guardians CU",
        title_date="May 2026",
        ctx_results={"value_summary": {"lead_finding": "DCTR gap to peer is the largest revenue lever this cycle."}},
    )
    assert sc is not None
    assert "Guardians CU" in sc.title
    assert "May 2026" in sc.title
    assert "DCTR gap to peer" in sc.title


def test_build_cover_falls_back_when_lead_finding_missing():
    sc = structural_slides.build_cover(
        client_name="Guardians CU",
        title_date="May 2026",
        ctx_results={},
    )
    assert sc is not None
    assert "Guardians CU" in sc.title
    assert "May 2026" in sc.title
    # Fallback subline still present from the structural template bank.
    assert "Account Revenue Solution" in sc.title or "Performance review" in sc.title


def test_build_dashboard_is_stub_returning_none():
    assert structural_slides.build_dashboard(ctx_results={}) is None


def test_build_agenda_is_stub_returning_none():
    assert structural_slides.build_agenda(ctx_results={}) is None


def test_build_section_opening_is_stub_returning_none():
    assert structural_slides.build_section_opening(section_key="dctr", section_results=[]) is None


def test_build_takeaways_is_stub_returning_none():
    assert structural_slides.build_takeaways(ctx_results={}) is None
```

- [ ] **Step 2: Run the test, verify it fails on import**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_structural_slides.py -v
```
Expected: `ImportError`.

- [ ] **Step 3: Create the module with `build_cover()` + four stubs**

Create `01_Analysis/00-Scripts/output/structural_slides.py`:

```python
"""Auto-built structural slides (autonomous decks design §C).

Replaces ``blank`` placeholder ``SlideContent`` objects in the preamble + close
of the deck with data-driven builds. POC scope: ``build_cover()`` only.
The other four builders (dashboard, agenda, section openings, takeaways) are
stubs that return ``None`` so callers can wire them now and the long-tail plan
fills them in without touching deck_builder again.

Any builder that returns ``None`` triggers today's blank-placeholder behavior
upstream in ``deck_builder._build_preamble_slides`` — non-breaking by design.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from ars_analysis.output.deck_builder import (
    LAYOUT_TITLE_RPE,
    SlideContent,
)


# Structural copy bank. Loaded from docs/structural_templates.md if present,
# otherwise these baked-in defaults are used. Catalog loading lands fully in
# the long-tail plan; POC ships the cover defaults inline.
_DEFAULT_COVER_SUBLINE = "Account Revenue Solution"
_FALLBACK_COVER_SUBLINE = "Performance review"


def build_cover(
    *, client_name: str, title_date: str, ctx_results: dict | None
) -> SlideContent | None:
    """Build the deck cover slide.

    Picks a one-sentence lead-finding subline from
    ``ctx_results['value_summary']['lead_finding']`` when available; otherwise
    falls back to the static "Account Revenue Solution" subline (today's
    behavior).
    """
    ctx_results = ctx_results or {}
    lead = None
    vs = ctx_results.get("value_summary", {})
    if isinstance(vs, dict):
        lead = vs.get("lead_finding") or vs.get("subline")
    subline = lead or _DEFAULT_COVER_SUBLINE
    return SlideContent(
        slide_type="title",
        title=f"{client_name}\n{subline} | {title_date}",
        layout_index=LAYOUT_TITLE_RPE,
    )


def build_dashboard(ctx_results: dict | None) -> SlideContent | None:
    """Stub — long-tail plan implements 3 KPI tiles + 3 lead-finding bullets."""
    return None


def build_agenda(ctx_results: dict | None) -> SlideContent | None:
    """Stub — long-tail plan implements per-section headline-finding bullets."""
    return None


def build_section_opening(
    *, section_key: str, section_results: list[Any]
) -> SlideContent | None:
    """Stub — long-tail plan implements 3-bullet section opening from top slides."""
    return None


def build_takeaways(ctx_results: dict | None) -> SlideContent | None:
    """Stub — long-tail plan implements top-3-by-dollar-magnitude with verbs."""
    return None
```

Heads-up on the import: `structural_slides` imports `SlideContent` + `LAYOUT_TITLE_RPE` from `deck_builder`. That import is at module-top, which means `deck_builder` cannot import `structural_slides` at module-top in turn (cycle). Task 11 imports `structural_slides` inside the `_build_preamble_slides` function body — exactly to avoid the cycle.

- [ ] **Step 4: Re-run tests, verify all pass**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_structural_slides.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add 01_Analysis/00-Scripts/output/structural_slides.py 01_Analysis/00-Scripts/tests/test_structural_slides.py
git commit -m "feat(decks): scaffold structural_slides with build_cover (POC step 3)"
```

---

## Task 11: Wire `build_cover()` into `_build_preamble_slides()`

**Files:**
- Modify: `01_Analysis/00-Scripts/output/deck_builder.py` — `_preamble_ars()` calls `build_cover()` for P01; `_build_preamble_slides()` signature gains an optional `ctx_results` param so the cover builder can see lead findings.

- [ ] **Step 1: Add the failing wiring test**

Append to `01_Analysis/00-Scripts/tests/test_structural_slides.py`:

```python
def test_preamble_ars_uses_structural_cover():
    """The P01 master title slide must come from build_cover() when ctx_results
    contains a lead finding; falls back to the static subline otherwise."""
    from ars_analysis.output.deck_builder import _build_preamble_slides

    slides_with_finding = _build_preamble_slides(
        client_name="Guardians CU",
        month="2026.05",
        product_mode="ars",
        ctx_results={
            "value_summary": {
                "lead_finding": "DCTR gap to peer is the largest revenue lever this cycle."
            }
        },
    )
    assert "DCTR gap to peer" in slides_with_finding[0].title

    slides_no_finding = _build_preamble_slides(
        client_name="Guardians CU",
        month="2026.05",
        product_mode="ars",
        ctx_results={},
    )
    assert "Account Revenue Solution" in slides_no_finding[0].title
```

- [ ] **Step 2: Run the test, verify it fails**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_structural_slides.py::test_preamble_ars_uses_structural_cover -v
```
Expected: FAIL — `_build_preamble_slides()` does not yet accept `ctx_results`, and the current `_preamble_ars()` returns the static title.

- [ ] **Step 3: Add `ctx_results` parameter to `_build_preamble_slides()`**

In `01_Analysis/00-Scripts/output/deck_builder.py`, modify the `_build_preamble_slides()` signature (around line 1767). Replace:

```python
def _build_preamble_slides(client_name: str, month: str, product_mode: str = "ars") -> list[SlideContent]:
```

with:

```python
def _build_preamble_slides(
    client_name: str,
    month: str,
    product_mode: str = "ars",
    ctx_results: dict | None = None,
) -> list[SlideContent]:
```

Then update the three internal mode-dispatch calls inside the function body. Find:

```python
    if mode == "txn":
        return _preamble_txn(client_name, title_date)
    if mode == "hybrid":
        return _preamble_hybrid(client_name, title_date)
    return _preamble_ars(client_name, title_date)
```

Replace with:

```python
    if mode == "txn":
        return _preamble_txn(client_name, title_date)
    if mode == "hybrid":
        return _preamble_hybrid(client_name, title_date)
    return _preamble_ars(client_name, title_date, ctx_results=ctx_results)
```

(`_preamble_txn` and `_preamble_hybrid` stay unchanged in the POC — their cover-slide migration is part of the long-tail plan.)

- [ ] **Step 4: Update `_preamble_ars()` to use `build_cover()`**

Modify `_preamble_ars()` (around line 1795). Replace its signature + the first `SlideContent(...)` element. New body:

```python
def _preamble_ars(
    client_name: str,
    title_date: str,
    ctx_results: dict | None = None,
) -> list[SlideContent]:
    """13-slide ARS preamble. P01 cover sourced from structural_slides.build_cover()."""
    # Local import avoids a module-level cycle (structural_slides imports
    # SlideContent + LAYOUT_TITLE_RPE from this module).
    from ars_analysis.output.structural_slides import build_cover

    cover = build_cover(
        client_name=client_name, title_date=title_date, ctx_results=ctx_results,
    )
    if cover is None:
        # Build_cover never returns None in the POC; this guard is here so the
        # long-tail builders can return None to fall through to today's behavior.
        cover = SlideContent(
            slide_type="title",
            title=f"{client_name}\nAccount Revenue Solution | {title_date}",
            layout_index=LAYOUT_TITLE_RPE,
        )
    return [
        cover,
        # P02-P13 unchanged — copy them verbatim from the existing function.
        # [...remaining 12 SlideContent objects, identical to today's code...]
    ]
```

CRITICAL: in the actual edit you must keep all 12 existing P02–P13 `SlideContent(...)` objects exactly as they are today (the file already has them in `_preamble_ars`). Do not delete them; only replace the P01 element with the `cover` variable and the surrounding plumbing.

- [ ] **Step 5: Update the single caller in `build_deck()`**

Find the line near the bottom of the file (around line 2469):

```python
    preamble = _build_preamble_slides(client_name, month, product_mode=_preamble_mode)
```

Replace with:

```python
    preamble = _build_preamble_slides(
        client_name, month,
        product_mode=_preamble_mode,
        ctx_results=_ctx_results,
    )
```

(`_ctx_results` is already defined just above in the function body — confirm by reading the surrounding 10 lines.)

- [ ] **Step 6: Re-run the wiring test + full suite**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_structural_slides.py -v && python3 -m pytest tests/ 2>&1 | tail -20
```
Expected: all structural tests pass; full suite has zero new regressions.

- [ ] **Step 7: Commit**

```bash
git add 01_Analysis/00-Scripts/output/deck_builder.py 01_Analysis/00-Scripts/tests/test_structural_slides.py
git commit -m "feat(decks): wire build_cover into _build_preamble_slides for ARS mode (POC step 3-4)"
```

---

## Task 12: Mark DCTR entries in `_SLIDE_TEMPLATE_MAP` as branching-catalog-aware

**Files:**
- Modify: `01_Analysis/00-Scripts/output/deck_builder.py` — add a comment block above the DCTR entries documenting that they're routed into `template_catalog.py` (no code change to the map; the populator already does the routing).

The spec calls for "_SLIDE_TEMPLATE_MAP shrinks to a stub" in the end state. For the POC we don't shrink it — we leave it intact so the legacy flat-catalog fallback continues to work for non-DCTR sections. The stub shrink is a long-tail step (after all 7 catalogs land).

- [ ] **Step 1: Update the comment around `_SLIDE_TEMPLATE_MAP`**

In `01_Analysis/00-Scripts/output/deck_builder.py`, find the existing comment + map (around line 1634). Replace lines 1634–1637:

```python
# T2.2 slide_id -> action-title template id (catalog in
# docs/action_title_templates.md). Unmapped slide IDs fall back to the
# per-slide generators in headlines.py. Per-section specs (T2.5) will
# move this map into docs/slide_specs/*.md once they land.
```

with:

```python
# Slide_id -> action-title template id.
#
# Resolution order (see action_title_populator.populate):
#   1. Branching catalog (output/template_catalog.py + docs/action_title_templates/<section>.md)
#   2. Flat catalog (docs/action_title_templates.md) — legacy.
#   3. Per-slide generators in output/headlines.py — last resort.
#
# DCTR template ids resolve out of the branching catalog as of the
# autonomous-decks POC (docs/superpowers/specs/2026-05-29-autonomous-decks-design.md).
# Other sections still resolve via the flat catalog until their section
# catalogs land in the long-tail plan.
```

- [ ] **Step 2: Commit**

```bash
git add 01_Analysis/00-Scripts/output/deck_builder.py
git commit -m "docs(decks): document branching catalog resolution order in _SLIDE_TEMPLATE_MAP (POC step 4)"
```

---

## Task 13: Create `docs/structural_templates.md` (POC scope = cover only)

**Files:**
- Create: `docs/structural_templates.md`

This file is the future home for all structural-slide copy. POC only authors the cover section; the four remaining sections get placeholder headings + a one-line "deferred to long-tail plan" note so the file's structure is established.

- [ ] **Step 1: Create the file**

Create `docs/structural_templates.md`:

```markdown
# Structural slide templates (autonomous decks design §C)

Consumed by: `01_Analysis/00-Scripts/output/structural_slides.py`
Authority: `docs/superpowers/specs/2026-05-29-autonomous-decks-design.md`

The structural builders read this file to pick subline copy for each
auto-built slide. POC scope is the Cover section only; Dashboard, Agenda,
Section openings, and Takeaways are stubbed and land in the long-tail plan.

## Cover

### Default subline
"Account Revenue Solution"

### Lead-finding override
When `ctx.results['value_summary']['lead_finding']` is a non-empty string,
the cover subline becomes that sentence verbatim. The lead finding is set by
the value-summary analytics module (existing).

### Fallback subline
"Performance review"
(used only when both the lead finding is missing AND the default subline
copy bank fails to load — edge case for failure-mode coverage.)

## Dashboard

_Deferred to long-tail plan._

## Agenda

_Deferred to long-tail plan._

## Section openings

_Deferred to long-tail plan._

## Takeaways

_Deferred to long-tail plan._
```

- [ ] **Step 2: Commit**

```bash
git add docs/structural_templates.md
git commit -m "docs(decks): structural template copy bank with cover section authored (POC step 3)"
```

---

## Task 14: POC end-to-end smoke test

**Files:**
- Create: `01_Analysis/00-Scripts/tests/test_autonomous_decks_smoke.py`

This is the integration check the spec calls out as POC migration step 5: the three new paths (branching catalog title selection, themed-chart PNG, structural cover slide) work together on a synthetic client-1615-shaped fixture, end to end. It does NOT build a real PPTX; it verifies the wires connect.

- [ ] **Step 1: Write the smoke test**

Create `01_Analysis/00-Scripts/tests/test_autonomous_decks_smoke.py`:

```python
"""POC smoke test for autonomous decks (design step 5 / commit afdce7a).

Exercises the three new paths on synthetic data shaped like client 1615:
  1. Branching catalog title selection (dctr.activation_baseline -> populated sentence)
  2. Themed-chart PNG render (rate_volume_combo)
  3. Structural cover slide (lead-finding subline)

Does NOT touch PowerPoint output — that's the full E2E in the long-tail plan.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def fake_1615_ctx(tmp_path):
    """Synthetic context shaped like a real client run.

    Numbers are fake. Field names + path shapes mirror real `ctx.results`
    so the same module paths the analytics modules use also work here.
    """
    paths = types.SimpleNamespace(charts_dir=tmp_path, base_dir=tmp_path.parent)
    client = types.SimpleNamespace(client_name="Guardians Credit Union", client_id="1615", month="2026.05")
    results = {
        "dctr_1": {
            "rate": 0.42,
            "eligible_count": 12400,
            "decade": pd.DataFrame({
                "Decade":         ["10-19", "20-29", "30-39", "40-49", "50-59", "60+"],
                "DCTR %":         [0.18,    0.36,    0.44,    0.41,    0.30,    0.21],
                "Total Accounts": [400,     1800,    2400,    2100,    1600,    700],
            }),
        },
        "dctr_4": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
        "dctr_5": {"decade": pd.DataFrame(columns=["Decade", "DCTR %", "Total Accounts"])},
        "value_summary": {
            "lead_finding": "DCTR gap to peer is the largest revenue lever this cycle.",
        },
    }
    return types.SimpleNamespace(paths=paths, client=client, results=results, settings=None)


def test_branching_catalog_picks_a_dctr_variant(fake_1615_ctx):
    """Path 1: branching catalog resolves dctr.activation_baseline to a populated sentence."""
    from ars_analysis.output.action_title_populator import ActionTitlePopulator
    from ars_analysis.output import template_catalog

    # Force a fresh cache so this test sees the on-disk catalog.
    template_catalog.CatalogCache._families = None
    ActionTitlePopulator._catalog = None

    title = ActionTitlePopulator.populate(
        template_id="dctr.activation_baseline",
        ctx_results=fake_1615_ctx.results,
        ctx=fake_1615_ctx,
        fallback_title="default",
    )
    assert "{" not in title
    assert title != "default"
    assert "42%" in title  # rate=0.42 formatted as pct
    assert "12,400" in title  # eligible_count=12400 formatted as int


def test_themed_chart_renders_decade_trend_png(fake_1615_ctx):
    """Path 2: themed_chart produces a PNG for the rate_volume_combo shape."""
    from ars_analysis.analytics.dctr.trends import DctrTrendsModule
    out = DctrTrendsModule()._decade_trend(fake_1615_ctx)
    assert len(out) == 1
    assert out[0].chart_path is not None
    assert Path(out[0].chart_path).exists()
    assert Path(out[0].chart_path).stat().st_size > 0


def test_structural_cover_uses_lead_finding(fake_1615_ctx):
    """Path 3: structural cover slide picks up lead-finding subline."""
    from ars_analysis.output.deck_builder import _build_preamble_slides
    preamble = _build_preamble_slides(
        client_name=fake_1615_ctx.client.client_name,
        month=fake_1615_ctx.client.month,
        product_mode="ars",
        ctx_results=fake_1615_ctx.results,
    )
    assert "DCTR gap to peer" in preamble[0].title
    assert "Guardians Credit Union" in preamble[0].title
    # 13-slide ARS preamble must still have 13 slides.
    assert len(preamble) == 13


def test_smoke_all_three_paths_together(fake_1615_ctx):
    """All three paths exercise without raising. The actual content checks
    are above; this is the wires-connect check."""
    from ars_analysis.output.action_title_populator import ActionTitlePopulator
    from ars_analysis.output import template_catalog
    from ars_analysis.output.deck_builder import _build_preamble_slides
    from ars_analysis.analytics.dctr.trends import DctrTrendsModule

    template_catalog.CatalogCache._families = None
    ActionTitlePopulator._catalog = None

    # Title
    title = ActionTitlePopulator.populate(
        "dctr.activation_baseline", fake_1615_ctx.results, ctx=fake_1615_ctx,
        fallback_title="default",
    )
    # Chart
    chart_result = DctrTrendsModule()._decade_trend(fake_1615_ctx)
    # Cover
    preamble = _build_preamble_slides(
        fake_1615_ctx.client.client_name, fake_1615_ctx.client.month,
        product_mode="ars", ctx_results=fake_1615_ctx.results,
    )

    assert title and chart_result and preamble
    assert "{" not in title
    assert chart_result[0].chart_path and Path(chart_result[0].chart_path).exists()
    assert preamble[0].title
```

- [ ] **Step 2: Run the smoke test**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/test_autonomous_decks_smoke.py -v
```
Expected: 4 passed.

If any test fails, debug in this order: title path first (catalog-loading issue), then chart path (Plotly / kaleido issue), then cover (deck_builder wiring). The smoke test is the POC's quality gate — do not commit until all 4 are green.

- [ ] **Step 3: Run the full test suite one more time**

Run:
```bash
cd /Users/jgmbp/Desktop/RPE-Workflow/01_Analysis/00-Scripts && python3 -m pytest tests/ 2>&1 | tail -30
```
Expected: zero new regressions.

- [ ] **Step 4: Commit**

```bash
git add 01_Analysis/00-Scripts/tests/test_autonomous_decks_smoke.py
git commit -m "test(decks): POC end-to-end smoke for autonomous decks (POC step 5)"
```

- [ ] **Step 5: Tag the POC milestone**

```bash
git tag -a poc-autonomous-decks-2026-05-29 -m "POC complete: branching catalog (DCTR) + themed_chart(rate_volume_combo) + structural cover wired and smoke-tested"
```

(Tag stays local — don't push it without operator approval, per the handover doc.)

---

## Self-review checklist

Run through this once after Task 14 commits.

**Spec coverage (steps 1–5 from §Migration plan):**

| Spec step | Plan tasks |
|---|---|
| 1. Build `template_catalog.py` + author DCTR section (~20 templates) | Tasks 2, 3, 4, 5 |
| 2. Build `themes.py` + migrate `rate_volume_combo` end-to-end on one analytics module | Tasks 7, 8, 9 |
| 3. Build `structural_slides.py` + cover slide | Tasks 10, 13 |
| 4. Wire `_SLIDE_TEMPLATE_MAP` stub + populator delegation | Tasks 6, 11, 12 |
| 5. POC E2E smoke test on client 1615 | Task 14 |

**Deferred (not in this plan, by design):**

| Spec step | Where it lands |
|---|---|
| 6. Remaining 6 section catalogs | Long-tail plan |
| 7. Remaining ~24 module migrations | Long-tail plan |
| 8. Remaining 4 structural slides | Long-tail plan |
| 9. New quality-gate checks | Long-tail plan |
| 10. `--strict-templates` CLI flag | Long-tail plan |
| 11. README docs | Long-tail plan |
| 12. Full E2E 10-client matrix | Long-tail plan |

**Type-consistency sweep:**
- `TemplateFamily` and `Variant` dataclass field names match across tasks 2/3/4/6.
- `select_variant(family_id, ctx_results, client_id)` (public) and `select_variant_from_family(family, ctx_results, client_id)` (internal) — names match across tasks 4 and 6.
- `themed_chart(kind=..., data=..., section_key=..., hero_series=..., x_series=..., volume_series=..., peer_median=..., your_value=..., source=..., out_path=...)` — keyword set identical in tasks 8 and 9 (the dctr migration call site).
- `build_cover(*, client_name, title_date, ctx_results)` — same shape in tasks 10 and 11.
- `_build_preamble_slides(client_name, month, product_mode, ctx_results)` — new `ctx_results` kwarg in task 11; caller in task 11 step 5 passes it.

**Placeholder scan:** none. Every code step shows real code.

**Things deliberately NOT done in POC:**
- Plotly import-time version-check fallback to matplotlib (failure-modes table row "Plotly version mismatch on operator PC") — punted to long-tail step 9, where the quality gate work lives.
- Catalog M:\-disconnect retry-once logic — deferred. POC's `load_catalog()` is fine for dev (local FS); the retry pattern lands when the long-tail plan adds production hardening.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-29-autonomous-decks-poc.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
