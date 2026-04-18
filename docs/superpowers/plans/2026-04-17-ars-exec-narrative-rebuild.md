# ARS Executive Narrative Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the ARS client executive deck template around a Truth → Diagnosis → Opportunity → Plan narrative by adding new section modules, demoting detail slides to appendix, and layering an optional per-client persona deep-dive module.

**Architecture:** Additive. New section modules live alongside existing ones under `02_Powerpoint/sections/`, all following the existing `SectionSpec` pattern. A `placeholders.py` module centralizes `{{...}}` template variables. A new `persona_module/` package under `02_Powerpoint/` holds the optional deep-dive. The deck assembler gains a single `--persona-module` flag. No existing slide code or analytics is deleted — slides are demoted by moving IDs into each section's `appendix_ids` set.

**Tech Stack:** Python 3, python-pptx, pytest. Pipeline lives at `/Users/jgmbp/Desktop/RPE-Workflow/Step 3 - Powerpoint/ars-production-pipeline/`.

**Companion documents:**
- Design spec: `docs/superpowers/specs/2026-04-17-ars-exec-narrative-design.md`
- Deck blueprint (slide mapping): `docs/superpowers/specs/2026-04-17-deck-blueprint.md`

**Every number in every new slide is a placeholder.** Use `{{...}}` variables from `placeholders.py`. Real numbers arrive at pipeline run time per client.

---

## Working Directory — EXECUTION OVERRIDE (READ FIRST)

The code changes for this plan do **not** happen inside `RPE-Workflow/`. They happen inside a **git worktree of the ars-production-pipeline repo**, which the controller has already created.

**Actual working directory for all code changes:**

```bash
PIPELINE="/Users/jgmbp/Desktop/ars-exec-narrative-rebuild"
```

This worktree is already checked out on branch `feature/exec-narrative-rebuild` tracking `origin/02_powerpoint-pipeline` (the branch where the `02_Powerpoint/` code lives). The plan's original Task 0 branch-creation steps (steps 1–2) are **no-ops** — the branch and worktree already exist. Skip them and start Task 0 at Step 3 (reading the existing section pattern) or Step 4 (creating the tests directory).

**Path substitution rules when executing any task below:**

| Original command in plan | Actual command to run |
|---|---|
| `cd /Users/jgmbp/Desktop/RPE-Workflow` | `cd "$PIPELINE"` |
| `git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/foo"` | `git add "02_Powerpoint/foo"` |
| `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/...` (referenced as a file) | `02_Powerpoint/...` (relative to `$PIPELINE`) |
| `$PIPELINE/02_Powerpoint` | unchanged — already correct |

In short: **every `cd` is `cd "$PIPELINE"`, every git path is relative to the pipeline root, and every `$PIPELINE/...` reference is already correct.**

Do not push to origin until explicitly told at Task 14 Step 5. Do not merge anything. Do not touch `/Users/jgmbp/Desktop/RPE-Workflow/` — planning artifacts live there and stay there.

---

## Task 0: Branch + test infrastructure

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/__init__.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/conftest.py`
- Read: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/_base.py` (to learn `SectionSpec`)
- Read: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/overview.py` (reference module pattern)

- [ ] **Step 1: Create branch from main**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git fetch origin
git checkout -b feature/exec-narrative-rebuild origin/main
```

Expected: `Switched to a new branch 'feature/exec-narrative-rebuild'`

- [ ] **Step 2: Verify branch**

```bash
git branch --show-current
```

Expected: `feature/exec-narrative-rebuild`

- [ ] **Step 3: Read the existing section module pattern**

Open and read `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/_base.py` and `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/overview.py`. Every new section module in this plan follows the `overview.py` pattern exactly.

- [ ] **Step 4: Create the tests directory**

Create `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/__init__.py` as an empty file.

- [ ] **Step 5: Create conftest.py**

Create `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/conftest.py`:

```python
"""Pytest config for 02_Powerpoint tests.

Adds the parent 02_Powerpoint directory to sys.path so section modules can
import from `._base` and siblings without requiring install.
"""

from __future__ import annotations

import sys
from pathlib import Path

_POWERPOINT = Path(__file__).resolve().parent.parent
if str(_POWERPOINT) not in sys.path:
    sys.path.insert(0, str(_POWERPOINT))
```

- [ ] **Step 6: Verify pytest can discover the directory**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/ --collect-only -q
```

Expected: `no tests ran` (directory discovered but empty — no errors).

- [ ] **Step 7: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/__init__.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/conftest.py"
git commit -m "chore(02_Powerpoint): add tests directory for section module specs"
```

---

## Task 1: Placeholder registry

Central module for every `{{...}}` template variable the new slides use. One source of truth so the template has no magic strings.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/placeholders.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_placeholders.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_placeholders.py`:

```python
"""Tests for the template placeholder registry."""

from __future__ import annotations

import pytest

from placeholders import (
    PLACEHOLDERS,
    Placeholder,
    get_placeholder,
    render,
)


def test_required_placeholders_exist():
    required = {
        "CLIENT_NAME",
        "NOTEBOOK_PENETRATION",
        "PIPELINE_DCTR",
        "ADDRESSABLE_SPEND_USD",
        "NONUSER_COUNT",
        "CLIMBER_COUNT",
        "DECLINER_COUNT",
        "MOST_RECENT_MAILER_MONTH",
    }
    assert required <= set(PLACEHOLDERS.keys())


def test_get_placeholder_returns_dataclass():
    p = get_placeholder("CLIENT_NAME")
    assert isinstance(p, Placeholder)
    assert p.key == "CLIENT_NAME"
    assert p.fake_value  # every placeholder has a fake default


def test_get_placeholder_unknown_raises():
    with pytest.raises(KeyError):
        get_placeholder("NOT_A_REAL_KEY")


def test_render_substitutes_fake_values():
    text = "{{CLIENT_NAME}} has {{NOTEBOOK_PENETRATION}} debit penetration."
    out = render(text)
    assert "{{CLIENT_NAME}}" not in out
    assert "{{NOTEBOOK_PENETRATION}}" not in out


def test_render_accepts_overrides():
    text = "Hello {{CLIENT_NAME}}"
    out = render(text, overrides={"CLIENT_NAME": "First National"})
    assert out == "Hello First National"


def test_render_leaves_unknown_tokens_alone():
    text = "This has {{UNKNOWN_TOKEN}} in it."
    out = render(text)
    assert "{{UNKNOWN_TOKEN}}" in out  # untouched, not an error
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_placeholders.py -v
```

Expected: `ModuleNotFoundError: No module named 'placeholders'`

- [ ] **Step 3: Write the implementation**

Create `02_Powerpoint/placeholders.py`:

```python
"""Template placeholder registry for the exec-narrative deck.

Every new slide in the rebuild uses {{TOKEN}} syntax for numbers or names
that are client-specific. This module is the single source of truth for
every token, its fake default (used during template development), and the
rules for substituting real values at render time.

Real values arrive at pipeline run time; until then, rendering uses the
fake defaults so the template is always visually complete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Placeholder:
    """One template variable."""

    key: str                 # e.g. "NOTEBOOK_PENETRATION"
    description: str         # human-readable use
    fake_value: str          # shown when no real value is supplied
    source_hint: str = ""    # where the real value comes from at run time


PLACEHOLDERS: dict[str, Placeholder] = {
    p.key: p
    for p in [
        Placeholder(
            key="CLIENT_NAME",
            description="Bank or credit union name on the title slide",
            fake_value="Sample Bank",
            source_hint="clients_config.json -> client.name",
        ),
        Placeholder(
            key="NOTEBOOK_PENETRATION",
            description="Customer-level debit penetration (Truth slides)",
            fake_value="80%",
            source_hint="Jupyter notebook -- pending handoff spec",
        ),
        Placeholder(
            key="PIPELINE_DCTR",
            description="Account-level DCTR for contrast on Truth-2",
            fake_value="30%",
            source_hint="dctr/penetration.py -- existing analytics",
        ),
        Placeholder(
            key="ADDRESSABLE_SPEND_USD",
            description="Total addressable debit spend for Opportunity-1",
            fake_value="$12.4M",
            source_hint="value/analysis.py -- to be reworked with notebook denominator",
        ),
        Placeholder(
            key="NONUSER_COUNT",
            description="Number of customers matching the Non-User persona",
            fake_value="14,200",
            source_hint="complement of dctr/penetration.py",
        ),
        Placeholder(
            key="CLIMBER_COUNT",
            description="Number of customers matching the Climber persona",
            fake_value="6,800",
            source_hint="mailer/response.py + dctr/trends age",
        ),
        Placeholder(
            key="DECLINER_COUNT",
            description="Number of customers matching the Decliner persona",
            fake_value="3,100",
            source_hint="attrition/rates.py + insights/dormant.py",
        ),
        Placeholder(
            key="MOST_RECENT_MAILER_MONTH",
            description="Mailer month token used in the Plan section slide selector",
            fake_value="Mar26",
            source_hint="mailer section at run time -- picks newest month",
        ),
    ]
}


_TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def get_placeholder(key: str) -> Placeholder:
    """Return the Placeholder for key, or raise KeyError."""
    if key not in PLACEHOLDERS:
        raise KeyError(f"Unknown placeholder: {key}")
    return PLACEHOLDERS[key]


def render(text: str, overrides: dict[str, str] | None = None) -> str:
    """Substitute every known {{TOKEN}} in text.

    Known tokens are replaced with overrides[token] if present, otherwise
    with the placeholder's fake_value. Unknown tokens are left alone so
    upstream callers can layer additional registries.
    """
    overrides = overrides or {}

    def _replace(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in overrides:
            return overrides[key]
        if key in PLACEHOLDERS:
            return PLACEHOLDERS[key].fake_value
        return m.group(0)

    return _TOKEN_RE.sub(_replace, text)


def known_keys() -> Iterable[str]:
    """Return the set of registered placeholder keys."""
    return PLACEHOLDERS.keys()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_placeholders.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/placeholders.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_placeholders.py"
git commit -m "feat(02_Powerpoint): add placeholder registry for template variables"
```

---

## Task 2: Open section (open.py)

First section of the new narrative. Owns the Title slide (P01, reused) and the new 4-beat Agenda (P02-new).

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/open.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_open_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_open_section.py`:

```python
"""Smoke test for the Open section module."""

from __future__ import annotations

from sections.open import register
from sections._base import LAYOUT_BLANK, LAYOUT_TITLE_ARS, SectionSpec


def test_open_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "open"
    assert spec.label == "Open"


def test_open_owns_p01_and_p02():
    spec = register()
    # P01 is the title slide, P02 is the new 4-beat agenda
    assert "P01" in spec.layout_map
    assert "P02" in spec.layout_map


def test_open_p01_uses_ars_title_layout():
    spec = register()
    layout_idx, slide_type = spec.layout_map["P01"]
    assert layout_idx == LAYOUT_TITLE_ARS
    assert slide_type == "title"


def test_open_p02_uses_blank_layout():
    spec = register()
    layout_idx, slide_type = spec.layout_map["P02"]
    assert layout_idx == LAYOUT_BLANK
    assert slide_type == "agenda"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_open_section.py -v
```

Expected: `ModuleNotFoundError: No module named 'sections.open'`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/open.py`:

```python
"""Open section -- Title + 4-beat Agenda.

Mirrors: 01_Analysis/00-Scripts/ preamble (P01, P02)
Slide IDs: P01 (client title), P02 (new 4-beat agenda)

Owns the deck opener. P01 reuses the existing ARS title layout.
P02 replaces the legacy agenda placeholder with a 4-beat signpost
(Truth / Diagnosis / Opportunity / Plan).
"""

from __future__ import annotations

from ._base import LAYOUT_BLANK, LAYOUT_TITLE_ARS, SectionSpec

_PREFIXES = ["p01", "p02"]

_LAYOUT_MAP = {
    "P01": (LAYOUT_TITLE_ARS, "title"),
    "P02": (LAYOUT_BLANK, "agenda"),
}


def register() -> SectionSpec:
    """Return the Open section specification."""
    return SectionSpec(
        key="open",
        label="Open",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_open_section.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/open.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_open_section.py"
git commit -m "feat(02_Powerpoint): add open section module (title + 4-beat agenda)"
```

---

## Task 3: Truth section (truth.py)

Opens the diagnosis by reframing. Two new slides (Truth-1, Truth-2) plus DCTR-3 reused as the "TTM DCTR" narrative chart.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/truth.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_truth_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_truth_section.py`:

```python
"""Smoke test for the Truth section module."""

from __future__ import annotations

from sections.truth import register
from sections._base import LAYOUT_CUSTOM, SectionSpec


def test_truth_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "truth"
    assert spec.label == "The Truth"


def test_truth_owns_three_slides():
    spec = register()
    # Truth-1 and Truth-2 are new; DCTR-3 is absorbed from the dctr section
    assert "TRUTH-1" in spec.layout_map
    assert "TRUTH-2" in spec.layout_map
    assert "DCTR-3" in spec.layout_map


def test_truth_absorbs_dctr_3_from_dctr():
    spec = register()
    assert spec.absorb_ids.get("DCTR-3") == "dctr"


def test_truth_new_slides_use_custom_layout():
    spec = register()
    for sid in ("TRUTH-1", "TRUTH-2"):
        layout_idx, _ = spec.layout_map[sid]
        assert layout_idx == LAYOUT_CUSTOM
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_truth_section.py -v
```

Expected: `ModuleNotFoundError: No module named 'sections.truth'`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/truth.py`:

```python
"""Truth section -- the reframe.

New slides: TRUTH-1 (executive reframe), TRUTH-2 (true debit penetration)
Absorbed slides: DCTR-3 (TTM DCTR narrative, from dctr section)

Leads the deck after Open. Establishes that the program has not failed
on demand -- customers are spending. The gap is alignment.

Placeholders used by this section live in 02_Powerpoint/placeholders.py:
  TRUTH-1: {{CLIENT_NAME}}, {{NOTEBOOK_PENETRATION}}
  TRUTH-2: {{NOTEBOOK_PENETRATION}}, {{PIPELINE_DCTR}}
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["truth"]

_LAYOUT_MAP = {
    "TRUTH-1": (LAYOUT_CUSTOM, "kpi_hero"),        # big reframe headline + KPI
    "TRUTH-2": (LAYOUT_CUSTOM, "screenshot_kpi"),  # chart + contrast KPI
    "DCTR-3":  (LAYOUT_CUSTOM, "screenshot"),      # reused as-is, with footnote
}

# Pull DCTR-3 out of dctr's main list and into ours.
_ABSORB_IDS = {"DCTR-3": "dctr"}


def register() -> SectionSpec:
    """Return the Truth section specification."""
    return SectionSpec(
        key="truth",
        label="The Truth",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_truth_section.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/truth.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_truth_section.py"
git commit -m "feat(02_Powerpoint): add truth section (reframe + true penetration + DCTR-3)"
```

---

## Task 4: Diagnosis — Engagement Gap (diagnosis_engagement.py)

The first of three diagnosis sub-sections. Evidence that the Non-User segment exists and isn't responding today.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/diagnosis_engagement.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_diagnosis_engagement_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_diagnosis_engagement_section.py`:

```python
"""Smoke test for the Diagnosis: Engagement Gap section module."""

from __future__ import annotations

from sections.diagnosis_engagement import register
from sections._base import SectionSpec


def test_engagement_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "diagnosis_engagement"
    assert spec.label == "Engagement Gap"


def test_engagement_owns_age_and_dormant_slides():
    spec = register()
    for sid in ("A7.11", "A7.12", "A20.1"):
        assert sid in spec.layout_map, f"{sid} missing from engagement section"


def test_engagement_absorbs_from_other_sections():
    spec = register()
    # A7.11, A7.12 come from dctr; A20.1 comes from insights
    assert spec.absorb_ids.get("A7.11") == "dctr"
    assert spec.absorb_ids.get("A7.12") == "dctr"
    assert spec.absorb_ids.get("A20.1") == "insights"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_diagnosis_engagement_section.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/diagnosis_engagement.py`:

```python
"""Diagnosis / Engagement Gap section -- the Non-User evidence.

Absorbed slides (all reused, no new slides):
  A7.11 (dctr): DCTR by account age -- who never activated
  A7.12 (dctr): DCTR by holder age -- generational pattern
  A20.1 (insights): dormant population sizing

Frames the first diagnosis gap: a large population has simply never
engaged with the card. Maps to the Non-User persona.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["diag-eng"]

_LAYOUT_MAP = {
    "A7.11": (LAYOUT_CUSTOM, "screenshot"),
    "A7.12": (LAYOUT_CUSTOM, "screenshot"),
    "A20.1": (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A7.11": "dctr",
    "A7.12": "dctr",
    "A20.1": "insights",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="diagnosis_engagement",
        label="Engagement Gap",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_diagnosis_engagement_section.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/diagnosis_engagement.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_diagnosis_engagement_section.py"
git commit -m "feat(02_Powerpoint): add diagnosis/engagement section (Non-User evidence)"
```

---

## Task 5: Diagnosis — Targeting Gap (diagnosis_targeting.py)

Second diagnosis sub-section. Evidence that mailer response exists but spend isn't aligned.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/diagnosis_targeting.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_diagnosis_targeting_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_diagnosis_targeting_section.py`:

```python
"""Smoke test for the Diagnosis: Targeting Gap section module."""

from __future__ import annotations

from sections.diagnosis_targeting import register
from sections._base import SectionSpec


def test_targeting_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "diagnosis_targeting"
    assert spec.label == "Targeting Gap"


def test_targeting_owns_mailer_slides():
    spec = register()
    for sid in ("A14.2", "A15.3", "A16.1"):
        assert sid in spec.layout_map


def test_targeting_absorbs_from_mailer():
    spec = register()
    for sid in ("A14.2", "A15.3", "A16.1"):
        assert spec.absorb_ids.get(sid) == "mailer"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_diagnosis_targeting_section.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/diagnosis_targeting.py`:

```python
"""Diagnosis / Targeting Gap section -- the Climber evidence.

Absorbed slides from mailer:
  A14.2: responder profile
  A15.3: lift attribution
  A16.1: responder spend trajectory

Shows: mailers reach people who will respond, but response doesn't
translate into sustained wallet share. Maps to the Climber persona.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["diag-tgt"]

_LAYOUT_MAP = {
    "A14.2": (LAYOUT_CUSTOM, "screenshot"),
    "A15.3": (LAYOUT_CUSTOM, "screenshot"),
    "A16.1": (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A14.2": "mailer",
    "A15.3": "mailer",
    "A16.1": "mailer",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="diagnosis_targeting",
        label="Targeting Gap",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_diagnosis_targeting_section.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/diagnosis_targeting.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_diagnosis_targeting_section.py"
git commit -m "feat(02_Powerpoint): add diagnosis/targeting section (Climber evidence)"
```

---

## Task 6: Diagnosis — Ecosystem Gap (diagnosis_ecosystem.py)

Third diagnosis sub-section. Evidence of leakage / decliner population.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/diagnosis_ecosystem.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_diagnosis_ecosystem_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_diagnosis_ecosystem_section.py`:

```python
"""Smoke test for the Diagnosis: Ecosystem Gap section module."""

from __future__ import annotations

from sections.diagnosis_ecosystem import register
from sections._base import SectionSpec


def test_ecosystem_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "diagnosis_ecosystem"
    assert spec.label == "Ecosystem Gap"


def test_ecosystem_owns_attrition_and_branch_slides():
    spec = register()
    for sid in ("A9.1", "A9.3", "A9.9", "A7.10a"):
        assert sid in spec.layout_map


def test_ecosystem_absorbs_from_correct_sections():
    spec = register()
    assert spec.absorb_ids.get("A9.1") == "attrition"
    assert spec.absorb_ids.get("A9.3") == "attrition"
    assert spec.absorb_ids.get("A9.9") == "attrition"
    assert spec.absorb_ids.get("A7.10a") == "dctr"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_diagnosis_ecosystem_section.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/diagnosis_ecosystem.py`:

```python
"""Diagnosis / Ecosystem Gap section -- the Decliner evidence + leakage.

Absorbed slides:
  A9.1 (attrition): overall attrition rate
  A9.3 (attrition): open vs closed accounts
  A9.9 (attrition): debit retention effect (why it matters)
  A7.10a (dctr): branch ranking -- leakage signal

Frames the third diagnosis gap: customers are leaving or relocating
spend across the ecosystem. Maps to the Decliner persona.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["diag-eco"]

_LAYOUT_MAP = {
    "A9.1":   (LAYOUT_CUSTOM, "kpi_hero"),
    "A9.3":   (LAYOUT_CUSTOM, "screenshot"),
    "A9.9":   (LAYOUT_CUSTOM, "screenshot"),
    "A7.10a": (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A9.1": "attrition",
    "A9.3": "attrition",
    "A9.9": "attrition",
    "A7.10a": "dctr",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="diagnosis_ecosystem",
        label="Ecosystem Gap",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_diagnosis_ecosystem_section.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/diagnosis_ecosystem.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_diagnosis_ecosystem_section.py"
git commit -m "feat(02_Powerpoint): add diagnosis/ecosystem section (Decliner + leakage)"
```

---

## Task 7: Persona Bridge (persona_bridge.py)

Single slide: "meet the 3 customer types." Lives between Diagnosis and Opportunity.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/persona_bridge.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_persona_bridge_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_persona_bridge_section.py`:

```python
"""Smoke test for the Persona Bridge section module."""

from __future__ import annotations

from sections.persona_bridge import register
from sections._base import LAYOUT_CUSTOM, SectionSpec


def test_bridge_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "persona_bridge"
    assert spec.label == "Meet the Three Customer Types"


def test_bridge_owns_single_slide():
    spec = register()
    assert list(spec.layout_map.keys()) == ["BRIDGE-1"]


def test_bridge_uses_custom_layout_and_persona_card_type():
    spec = register()
    layout_idx, slide_type = spec.layout_map["BRIDGE-1"]
    assert layout_idx == LAYOUT_CUSTOM
    assert slide_type == "persona_cards"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_persona_bridge_section.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/persona_bridge.py`:

```python
"""Persona Bridge section -- one slide, three personas.

Introduces the 3 customer types (Non-User, Climber, Decliner) as a
3-card composite slide sized with placeholder counts. Sits between
Diagnosis and Opportunity to transition from "what's broken" to
"what's possible."

Placeholders used by this slide:
  {{NONUSER_COUNT}}, {{CLIMBER_COUNT}}, {{DECLINER_COUNT}}

slide_type is "persona_cards" -- a new type the deck_assembler renders
as three stacked cards side by side. If the assembler falls back to
"screenshot" because the type is unknown, the slide still builds.
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["bridge"]

_LAYOUT_MAP = {
    "BRIDGE-1": (LAYOUT_CUSTOM, "persona_cards"),
}


def register() -> SectionSpec:
    return SectionSpec(
        key="persona_bridge",
        label="Meet the Three Customer Types",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_persona_bridge_section.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/persona_bridge.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_persona_bridge_section.py"
git commit -m "feat(02_Powerpoint): add persona bridge section (3-card customer types)"
```

---

## Task 8: Opportunity section (opportunity.py)

Size of the prize. New Opp-1 + reused A11.2 (Reg E value) + reused S3 (synthesis).

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/opportunity.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_opportunity_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_opportunity_section.py`:

```python
"""Smoke test for the Opportunity section module."""

from __future__ import annotations

from sections.opportunity import register
from sections._base import LAYOUT_CUSTOM, SectionSpec


def test_opportunity_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "opportunity"
    assert spec.label == "The Opportunity"


def test_opportunity_owns_three_slides():
    spec = register()
    for sid in ("OPP-1", "A11.2", "S3"):
        assert sid in spec.layout_map


def test_opportunity_absorbs_reused_slides():
    spec = register()
    assert spec.absorb_ids.get("A11.2") == "value"
    assert spec.absorb_ids.get("S3") == "insights"


def test_opportunity_opp1_uses_kpi_hero():
    spec = register()
    layout_idx, slide_type = spec.layout_map["OPP-1"]
    assert layout_idx == LAYOUT_CUSTOM
    assert slide_type == "kpi_hero"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_opportunity_section.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/opportunity.py`:

```python
"""Opportunity section -- size of the prize.

New slide: OPP-1 (Total Addressable Spend, KPI hero)
Absorbed slides:
  A11.2 (value): Reg E value
  S3 (insights): opportunity synthesis

Opens with the big number. Closes Diagnosis and sets up Plan.

Placeholders used:
  OPP-1: {{ADDRESSABLE_SPEND_USD}}, {{NOTEBOOK_PENETRATION}}
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, SectionSpec

_PREFIXES = ["opp"]

_LAYOUT_MAP = {
    "OPP-1": (LAYOUT_CUSTOM, "kpi_hero"),
    "A11.2": (LAYOUT_CUSTOM, "screenshot"),
    "S3":    (LAYOUT_CUSTOM, "screenshot"),
}

_ABSORB_IDS = {
    "A11.2": "value",
    "S3": "insights",
}


def register() -> SectionSpec:
    return SectionSpec(
        key="opportunity",
        label="The Opportunity",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        absorb_ids=_ABSORB_IDS,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_opportunity_section.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/opportunity.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_opportunity_section.py"
git commit -m "feat(02_Powerpoint): add opportunity section (addressable spend + synthesis)"
```

---

## Task 9: Plan section (plan.py)

What to do. New Plan-1 + reused A17.1 + reused A18.3 (with footnote) + dynamic mailer month + new Close-1.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/plan.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_plan_section.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_plan_section.py`:

```python
"""Smoke test for the Plan section module."""

from __future__ import annotations

from sections.plan import register
from sections._base import LAYOUT_CUSTOM, SectionSpec


def test_plan_registers_valid_spec():
    spec = register()
    assert isinstance(spec, SectionSpec)
    assert spec.key == "plan"
    assert spec.label == "The Plan"


def test_plan_owns_expected_slides():
    spec = register()
    # Plan-1 (pillars), A17.1 reach, A18.3 benchmark, Close-1
    for sid in ("PLAN-1", "A17.1", "A18.3", "CLOSE-1"):
        assert sid in spec.layout_map, f"{sid} missing from plan section"


def test_plan_has_mailer_prefix_fallback_for_dynamic_month():
    spec = register()
    # The most recent mailer month (A12.{month}) is matched via prefix fallback
    assert spec.prefix_fallback is not None
    result = spec.prefix_fallback("A12.Mar26")
    assert result is not None
    layout_idx, slide_type = result
    assert layout_idx == LAYOUT_CUSTOM


def test_plan_absorbs_reused_slides():
    spec = register()
    assert spec.absorb_ids.get("A17.1") == "mailer"
    assert spec.absorb_ids.get("A18.3") == "insights"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_plan_section.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Write the section module**

Create `02_Powerpoint/sections/plan.py`:

```python
"""Plan section -- what we will do, ending with the CTA.

New slides:
  PLAN-1: 3-5 strategic pillars mapped to the three gaps
  CLOSE-1: final takeaway / CTA

Absorbed slides:
  A17.1 (mailer): reach -- evidence for targeting pillar
  A18.3 (insights): industry benchmark -- with denominator footnote
  A12.{most_recent_month}: dynamic mailer month, resolved at assembly time

Placeholders used:
  PLAN-1: pillar text only (no numbers)
  CLOSE-1: {{CLIENT_NAME}}
  A12.{month}: {{MOST_RECENT_MAILER_MONTH}} -- assembler picks newest month
"""

from __future__ import annotations

from ._base import LAYOUT_CUSTOM, LAYOUT_MAIL_SUMMARY, SectionSpec

_PREFIXES = ["plan", "close", "a17", "a18", "a12"]

_LAYOUT_MAP = {
    "PLAN-1":   (LAYOUT_CUSTOM, "screenshot"),
    "A17.1":    (LAYOUT_CUSTOM, "screenshot"),
    "A18.3":    (LAYOUT_CUSTOM, "screenshot"),
    "CLOSE-1":  (LAYOUT_CUSTOM, "kpi_hero"),
}

_ABSORB_IDS = {
    "A17.1": "mailer",
    "A18.3": "insights",
}


def _mailer_month_fallback(slide_id: str) -> tuple[int, str] | None:
    """Match the dynamic most-recent mailer month slide (A12.{month})."""
    if slide_id.startswith("A12."):
        return (LAYOUT_MAIL_SUMMARY, "mailer_summary")
    return None


def register() -> SectionSpec:
    return SectionSpec(
        key="plan",
        label="The Plan",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        prefix_fallback=_mailer_month_fallback,
        absorb_ids=_ABSORB_IDS,
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_plan_section.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/plan.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_plan_section.py"
git commit -m "feat(02_Powerpoint): add plan section (pillars + reach + benchmark + close)"
```

---

## Task 10: Demote detail slides to appendix

Take each existing section and move the slides listed in blueprint §4 into its `appendix_ids` set. No slides are deleted.

**Files (all under `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/`):**
- Modify: `dctr.py`
- Modify: `rege.py`
- Modify: `attrition.py`
- Modify: `mailer.py`
- Modify: `value.py`
- Modify: `insights.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_section_demotions.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_section_demotions.py`:

```python
"""Verify that detail slides are demoted to appendix per blueprint sec.4.

Blueprint reference:
  docs/superpowers/specs/2026-04-17-deck-blueprint.md section 4.
"""

from __future__ import annotations

from sections.attrition import register as register_attrition
from sections.dctr import register as register_dctr
from sections.insights import register as register_insights
from sections.mailer import register as register_mailer
from sections.rege import register as register_rege
from sections.value import register as register_value


def test_dctr_detail_slides_in_appendix():
    spec = register_dctr()
    for sid in (
        "DCTR-4", "DCTR-5", "DCTR-6", "DCTR-7",
        "DCTR-10", "DCTR-11", "DCTR-12", "DCTR-13",
        "DCTR-15", "DCTR-16",
    ):
        assert sid in spec.appendix_ids, f"{sid} should be in dctr appendix"


def test_rege_detail_slides_in_appendix():
    spec = register_rege()
    for sid in ("A8.3", "A8.10", "A8.11"):
        assert sid in spec.appendix_ids, f"{sid} should be in rege appendix"


def test_attrition_impact_in_appendix():
    spec = register_attrition()
    assert "A9.11" in spec.appendix_ids


def test_value_s1_demoted():
    spec = register_value()
    # S1 is absorbed into opportunity (OPP-1); the raw slide goes to appendix
    assert "S1" in spec.appendix_ids or "A11.1" in spec.appendix_ids


def test_insights_non_plan_slides_in_appendix():
    spec = register_insights()
    # S2, S4, S5 are appendix per blueprint
    for sid in ("S2", "S4", "S5"):
        assert sid in spec.appendix_ids


def test_mailer_older_months_appendix_logic_preserved():
    # Mailer month consolidation is already handled dynamically by
    # _consolidate_mailer. This test only guards that nothing breaks
    # by asserting register() returns a valid spec.
    spec = register_mailer()
    assert spec.key == "mailer"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_section_demotions.py -v
```

Expected: Assertion failures identifying which slides are not yet in appendix.

- [ ] **Step 3: Read current sections and extend appendix_ids**

Read each existing section file first, then add the required slide IDs to its `_APPENDIX_IDS` set. Pattern (use for each file below):

```python
# Open the file, locate the existing _APPENDIX_IDS line, and extend it.
# Do NOT replace or reorder existing appendix IDs -- only add.
```

Apply these additions. Each is a `_APPENDIX_IDS |= {...}` style extension, or you can literally add the IDs into the existing set literal.

**`sections/dctr.py` — add to `_APPENDIX_IDS`:**
```python
{"DCTR-4", "DCTR-5", "DCTR-6", "DCTR-7",
 "DCTR-10", "DCTR-11", "DCTR-12", "DCTR-13",
 "DCTR-15", "DCTR-16"}
```

**`sections/rege.py` — add to `_APPENDIX_IDS`:**
```python
{"A8.3", "A8.10", "A8.11"}
```

**`sections/attrition.py` — add to `_APPENDIX_IDS`:**
```python
{"A9.11"}
```

**`sections/value.py`** — this file does NOT yet have `_APPENDIX_IDS`. Create it and wire it through `register()`:

```python
# Add this after _LAYOUT_MAP, before register():
_APPENDIX_IDS = {"S1", "A11.1"}
```

Then modify the existing `register()` in `value.py` to pass the new set:

```python
def register() -> SectionSpec:
    """Return the Value section specification."""
    return SectionSpec(
        key="value",
        label="What Is the Revenue Impact?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        appendix_ids=_APPENDIX_IDS,  # <-- add this line
    )
```

**`sections/insights.py`** — same situation: this file does NOT yet have `_APPENDIX_IDS`. Create it and wire it through `register()`:

```python
# Add this after _LAYOUT_MAP, before register():
_APPENDIX_IDS = {"S2", "S4", "S5"}
```

Then modify the existing `register()` in `insights.py`:

```python
def register() -> SectionSpec:
    """Return the Insights section specification."""
    return SectionSpec(
        key="insights",
        label="What Should We Do Next?",
        prefixes=_PREFIXES,
        layout_map=_LAYOUT_MAP,
        appendix_ids=_APPENDIX_IDS,  # <-- add this line
    )
```

**`sections/mailer.py`** — no change required; the existing `_consolidate_mailer` already demotes older months.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_section_demotions.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Verify all previous tests still pass**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/"*.py \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_section_demotions.py"
git commit -m "refactor(02_Powerpoint): demote detail slides to appendix per blueprint"
```

---

## Task 11: Reorder SECTION_REGISTRY

Make the assembler produce the deck in narrative order: Open → Truth → Diagnosis (Engagement / Targeting / Ecosystem) → Persona Bridge → Opportunity → Plan. Existing topic sections (dctr, rege, attrition, mailer, value, insights, overview, transaction, ics) stay in the registry so their absorbed slides are still reachable, but they move to the end where they serve as appendix providers.

**Files:**
- Modify: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/__init__.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_registry_order.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_registry_order.py`:

```python
"""Verify SECTION_REGISTRY reflects the narrative order."""

from __future__ import annotations

from sections import SECTION_REGISTRY


def test_narrative_sections_lead_the_registry():
    keys = [s.key for s in SECTION_REGISTRY]
    expected_prefix = [
        "open",
        "truth",
        "diagnosis_engagement",
        "diagnosis_targeting",
        "diagnosis_ecosystem",
        "persona_bridge",
        "opportunity",
        "plan",
    ]
    assert keys[: len(expected_prefix)] == expected_prefix


def test_topic_sections_remain_in_registry_as_appendix_providers():
    keys = {s.key for s in SECTION_REGISTRY}
    for topic in ("overview", "dctr", "rege", "attrition", "mailer",
                  "transaction", "ics", "value", "insights"):
        assert topic in keys, f"{topic} missing -- its slides need to reach appendix"


def test_registry_has_no_duplicates():
    keys = [s.key for s in SECTION_REGISTRY]
    assert len(keys) == len(set(keys))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_registry_order.py -v
```

Expected: `AssertionError` — the narrative sections aren't imported yet.

- [ ] **Step 3: Rewrite `sections/__init__.py`**

Replace the contents of `02_Powerpoint/sections/__init__.py` with:

```python
"""Deck sections -- Narrative Arc ordering.

Top of the registry is the main-deck narrative (Open -> Truth -> Diagnosis
-> Persona Bridge -> Opportunity -> Plan). Topic sections remain in the
registry below the narrative so absorbed slides route correctly and
demoted slides reach the appendix.
"""

from __future__ import annotations

from ._base import SectionSpec, default_consolidate

# Narrative sections (new)
from .open import register as _open
from .truth import register as _truth
from .diagnosis_engagement import register as _diagnosis_engagement
from .diagnosis_targeting import register as _diagnosis_targeting
from .diagnosis_ecosystem import register as _diagnosis_ecosystem
from .persona_bridge import register as _persona_bridge
from .opportunity import register as _opportunity
from .plan import register as _plan

# Topic sections (existing -- now provide absorbed slides + appendix content)
from .overview import register as _overview
from .dctr import register as _dctr
from .rege import register as _rege
from .attrition import register as _attrition
from .mailer import register as _mailer
from .transaction import register as _transaction
from .ics import register as _ics
from .value import register as _value
from .insights import register as _insights

# Order matters -- narrative first, then topic sections as absorb donors.
SECTION_REGISTRY: list[SectionSpec] = [
    # --- Main-deck narrative ---
    _open(),
    _truth(),
    _diagnosis_engagement(),
    _diagnosis_targeting(),
    _diagnosis_ecosystem(),
    _persona_bridge(),
    _opportunity(),
    _plan(),

    # --- Topic sections (absorb donors / appendix providers) ---
    _overview(),
    _dctr(),
    _rege(),
    _attrition(),
    _mailer(),
    _transaction(),
    _ics(),
    _value(),
    _insights(),
]

__all__ = ["SECTION_REGISTRY", "SectionSpec", "default_consolidate"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_registry_order.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run the full test suite**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/sections/__init__.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_registry_order.py"
git commit -m "feat(02_Powerpoint): reorder SECTION_REGISTRY to narrative arc"
```

---

## Task 12: Persona deep-dive module package

Optional toggleable module: 5 slides per persona × 3 personas = 15 slides. Not in the core deck.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/persona_module/__init__.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/persona_module/nonuser.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/persona_module/climber.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/persona_module/decliner.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_persona_module.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_persona_module.py`:

```python
"""Smoke test for the optional persona deep-dive module."""

from __future__ import annotations

from persona_module import PERSONA_MODULES, build_persona_appendix
from persona_module.climber import register as register_climber
from persona_module.decliner import register as register_decliner
from persona_module.nonuser import register as register_nonuser


def test_three_personas_registered():
    keys = {m.key for m in PERSONA_MODULES}
    assert keys == {"nonuser", "climber", "decliner"}


def test_each_persona_has_five_slides():
    for module in PERSONA_MODULES:
        assert len(module.slide_ids) == 5, (
            f"{module.key} should contribute 5 deep-dive slides, "
            f"got {len(module.slide_ids)}"
        )


def test_nonuser_maps_to_engagement_gap():
    mod = register_nonuser()
    assert mod.gap == "engagement"


def test_climber_maps_to_targeting_gap():
    mod = register_climber()
    assert mod.gap == "targeting"


def test_decliner_maps_to_ecosystem_gap():
    mod = register_decliner()
    assert mod.gap == "ecosystem"


def test_build_persona_appendix_returns_fifteen_slide_ids():
    slide_ids = build_persona_appendix()
    assert len(slide_ids) == 15
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_persona_module.py -v
```

Expected: `ModuleNotFoundError: No module named 'persona_module'`

- [ ] **Step 3: Create `persona_module/__init__.py`**

```python
"""Optional persona deep-dive module.

Toggled on via --persona-module on the deck assembler. When on, adds a
15-slide appendix pack (5 slides per persona for Non-User, Climber,
Decliner). When off, the main deck has no persona content beyond the
Persona Bridge slide.

Each sub-module defines a PersonaModuleSpec dataclass declaring which
slide IDs belong to that persona and which Diagnosis gap it maps to.
Slides themselves are absorbed from existing analytics folders --
this module is metadata only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .climber import register as _climber
from .decliner import register as _decliner
from .nonuser import register as _nonuser


@dataclass
class PersonaModuleSpec:
    """Declaration for one persona deep-dive appendix."""

    key: str                  # "nonuser" | "climber" | "decliner"
    label: str
    gap: str                  # "engagement" | "targeting" | "ecosystem"
    slide_ids: list[str] = field(default_factory=list)
    source_sections: dict[str, str] = field(default_factory=dict)
    # slide_id -> donor section (e.g. "A14.2": "mailer")


PERSONA_MODULES: list[PersonaModuleSpec] = [
    _nonuser(),
    _climber(),
    _decliner(),
]


def build_persona_appendix() -> list[str]:
    """Return every persona slide ID in order (non-user, climber, decliner)."""
    out: list[str] = []
    for mod in PERSONA_MODULES:
        out.extend(mod.slide_ids)
    return out


__all__ = ["PERSONA_MODULES", "PersonaModuleSpec", "build_persona_appendix"]
```

- [ ] **Step 4: Create `persona_module/nonuser.py`**

```python
"""Non-User persona deep-dive (Engagement Gap)."""

from __future__ import annotations


def register():
    from . import PersonaModuleSpec

    return PersonaModuleSpec(
        key="nonuser",
        label="Non-User Deep Dive",
        gap="engagement",
        slide_ids=[
            "A7.11",   # DCTR by account age
            "A7.12",   # DCTR by holder age
            "A7.10a",  # Branch dispersion
            "A20.1",   # Dormant population sizing
            "A11.1",   # Activation unlock value (footnoted)
        ],
        source_sections={
            "A7.11": "dctr",
            "A7.12": "dctr",
            "A7.10a": "dctr",
            "A20.1": "insights",
            "A11.1": "value",
        },
    )
```

- [ ] **Step 5: Create `persona_module/climber.py`**

```python
"""Climber persona deep-dive (Targeting Gap)."""

from __future__ import annotations


def register():
    from . import PersonaModuleSpec

    return PersonaModuleSpec(
        key="climber",
        label="Climber Deep Dive",
        gap="targeting",
        slide_ids=[
            "A14.2",   # Mailer responder profile
            "A16.1",   # Responder spend trajectory
            "A16.3",   # Per-segment trajectory
            "A16.5",   # Spend direction change
            "A19.2",   # Branch opportunity map
        ],
        source_sections={
            "A14.2": "mailer",
            "A16.1": "mailer",
            "A16.3": "mailer",
            "A16.5": "mailer",
            "A19.2": "insights",
        },
    )
```

- [ ] **Step 6: Create `persona_module/decliner.py`**

```python
"""Decliner persona deep-dive (Ecosystem Gap / retention)."""

from __future__ import annotations


def register():
    from . import PersonaModuleSpec

    return PersonaModuleSpec(
        key="decliner",
        label="Decliner Deep Dive",
        gap="ecosystem",
        slide_ids=[
            "A9.1",    # Attrition rate
            "A9.5",    # Decliner profile
            "A9.9",    # Debit retention effect
            "A9.10",   # Mailer retention lift
            "A20.2",   # At-risk targeting matrix
        ],
        source_sections={
            "A9.1": "attrition",
            "A9.5": "attrition",
            "A9.9": "attrition",
            "A9.10": "attrition",
            "A20.2": "insights",
        },
    )
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_persona_module.py -v
```

Expected: 6 passed.

- [ ] **Step 8: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/persona_module/" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_persona_module.py"
git commit -m "feat(02_Powerpoint): add optional persona deep-dive module (15 slides)"
```

---

## Task 13: Wire --persona-module flag into deck_assembler.py

Give the assembler a CLI flag that toggles the 15-slide persona pack on or off. Off by default.

**Files:**
- Modify: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/deck_assembler.py`
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_assembler_flag.py`

- [ ] **Step 1: Read `deck_assembler.py` to locate the CLI / argparse block**

```bash
cd "$PIPELINE/02_Powerpoint"
grep -n "argparse\|ArgumentParser\|def main\|if __name__" deck_assembler.py
```

Note the line numbers where argument parsing is defined. Do NOT change any existing argument behavior — only add one new flag.

- [ ] **Step 2: Write the failing test**

Create `02_Powerpoint/tests/test_assembler_flag.py`:

```python
"""Verify the --persona-module flag is wired into the CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


_ASSEMBLER = (
    Path(__file__).resolve().parent.parent / "deck_assembler.py"
)


def test_persona_module_flag_documented_in_help():
    result = subprocess.run(
        [sys.executable, str(_ASSEMBLER), "--help"],
        capture_output=True,
        text=True,
    )
    # --help always exits 0
    assert result.returncode == 0
    assert "--persona-module" in result.stdout, (
        "CLI help should document the --persona-module flag"
    )
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_assembler_flag.py -v
```

Expected: AssertionError — flag not in help output.

- [ ] **Step 4: Add the flag to deck_assembler.py**

Open `02_Powerpoint/deck_assembler.py`. Locate the `argparse.ArgumentParser()` block (noted in Step 1). Add this argument alongside the existing ones:

```python
parser.add_argument(
    "--persona-module",
    action="store_true",
    default=False,
    help=(
        "Append the optional 15-slide persona deep-dive appendix "
        "(Non-User / Climber / Decliner). Off by default."
    ),
)
```

Then locate where the main assembly function uses the parsed args. Thread `args.persona_module` into whatever function appends appendix slides. If a clear integration point doesn't exist yet, wire it as a no-op for now — a later task can connect it to actual assembly logic:

```python
# Near where the appendix is finalized:
if getattr(args, "persona_module", False):
    from persona_module import build_persona_appendix
    extra_ids = build_persona_appendix()
    # TODO: route extra_ids through the existing appendix builder.
    # For now, log what would be appended so the flag is not silent.
    print(f"[assembler] --persona-module on: would append {len(extra_ids)} slides")
```

Keep the change additive — do not refactor existing assembly logic in this task.

- [ ] **Step 5: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_assembler_flag.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Verify the flag works end-to-end**

```bash
cd "$PIPELINE/02_Powerpoint"
python deck_assembler.py --help | grep persona-module
```

Expected: the help line for `--persona-module` prints.

- [ ] **Step 7: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/deck_assembler.py" \
        "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_assembler_flag.py"
git commit -m "feat(02_Powerpoint): add --persona-module flag to deck assembler"
```

---

## Task 14: Integration smoke test

End-to-end: import every section, build the registry, walk every slide ID, verify placeholders render with fake values. No real PPTX generation — this keeps the test fast and fixture-free.

**Files:**
- Create: `Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_integration_smoke.py`

- [ ] **Step 1: Write the failing test**

Create `02_Powerpoint/tests/test_integration_smoke.py`:

```python
"""Integration smoke test for the narrative rebuild.

Verifies:
  * Every narrative section is in the registry in the right order.
  * Absorb targets resolve to registered sections.
  * Persona module is importable and returns 15 slide IDs.
  * Every registered placeholder renders to a non-empty fake value.
  * No section key collides.
"""

from __future__ import annotations

from placeholders import PLACEHOLDERS, render
from persona_module import PERSONA_MODULES, build_persona_appendix
from sections import SECTION_REGISTRY


NARRATIVE_KEYS = [
    "open",
    "truth",
    "diagnosis_engagement",
    "diagnosis_targeting",
    "diagnosis_ecosystem",
    "persona_bridge",
    "opportunity",
    "plan",
]


def test_narrative_sections_lead_the_registry():
    keys = [s.key for s in SECTION_REGISTRY]
    assert keys[: len(NARRATIVE_KEYS)] == NARRATIVE_KEYS


def test_every_absorb_target_is_a_registered_section():
    registered = {s.key for s in SECTION_REGISTRY}
    for section in SECTION_REGISTRY:
        for donor in section.absorb_ids.values():
            assert donor in registered, (
                f"{section.key} absorbs from {donor!r} which is not registered"
            )


def test_persona_module_returns_fifteen_slides():
    assert len(build_persona_appendix()) == 15
    assert {m.key for m in PERSONA_MODULES} == {"nonuser", "climber", "decliner"}


def test_every_placeholder_has_non_empty_fake_value():
    for key, p in PLACEHOLDERS.items():
        assert p.fake_value, f"{key} has empty fake_value"


def test_render_produces_plain_strings_for_mixed_input():
    sample = (
        "{{CLIENT_NAME}} has {{NOTEBOOK_PENETRATION}} customer-level "
        "debit penetration compared to {{PIPELINE_DCTR}} account-level DCTR."
    )
    out = render(sample)
    for token in ("{{CLIENT_NAME}}", "{{NOTEBOOK_PENETRATION}}", "{{PIPELINE_DCTR}}"):
        assert token not in out


def test_no_section_key_collision():
    keys = [s.key for s in SECTION_REGISTRY]
    assert len(keys) == len(set(keys))
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/test_integration_smoke.py -v
```

Expected: 6 passed. If any fail, fix the underlying section module (not the test) and re-run.

- [ ] **Step 3: Run the full test suite one last time**

```bash
cd "$PIPELINE/02_Powerpoint"
python -m pytest tests/ -v
```

Expected: every test across every file passes.

- [ ] **Step 4: Commit**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git add "Step 3 - Powerpoint/ars-production-pipeline/02_Powerpoint/tests/test_integration_smoke.py"
git commit -m "test(02_Powerpoint): integration smoke test for narrative rebuild"
```

- [ ] **Step 5: Push the branch**

```bash
cd /Users/jgmbp/Desktop/RPE-Workflow
git push -u origin feature/exec-narrative-rebuild
```

Expected: branch pushed. Do NOT open a PR yet — the user wants to run the assembler against a local client dataset first (per spec §13 acceptance criteria).

---

## Post-implementation: user validation

Acceptance per spec §13 requires the user to run the assembler against one real client dataset locally and confirm the report reads right. This is a manual step outside the plan. After the user confirms:

1. Open PR from `feature/exec-narrative-rebuild` into `main`.
2. Resolve any review comments.
3. Merge.

The notebook-truth denominator handoff and the A18.3 benchmark audit are tracked as separate follow-on specs per design §14. They do not block merging this rebuild.
