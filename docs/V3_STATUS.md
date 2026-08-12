# v3 Engine — Status

*Last verified against the code: 2026-08-12.*

The v3 greenfield engine merged to `main` in commit `efd6d0b` ("v3 engine
Wave 0"). Until this file existed, no tracked document described it — the
plan lived in commit messages and GitHub issues. This is the honest current
state, so nobody has to reverse-engineer it again.

## What exists (Wave 0)

Three packages, mapped to top-level import names by `pyproject.toml`:

| Package | Location | What it does |
|---|---|---|
| `ars_engine` | `01_Analysis/00-Scripts/ars_engine/` | Core context/config/brand + the DuckDB TXN store (`data/txn_store.py`) |
| `ars_parity` | `01_Analysis/00-Scripts/ars_parity/` | Parity harness: captures figure data from legacy runs for old-vs-new comparison |
| `ars_staging` | `00_Formatting/00-Scripts/ars_staging/` | Staging daemon: content-hash keyed file staging (`python -m ars_staging`) |

All three import cleanly and are covered by tests (`test_v3_core.py`,
`test_v3_txn_store.py`, `test_v3_staging.py`) that run in CI.

## What does NOT exist yet

- **No production callers.** Nothing in `05_UI/app.py`, `01_Analysis/run.py`,
  or `runner.py` imports `ars_engine`. Decks are built entirely by the legacy
  spine (`runner.py` → `analytics/` → `output/deck_builder.py`).
- **No sections.** `ars_engine/sections/` is an empty package; the first
  section port is Wave 1.
- **No routing.** `03_Config/engine_flags.json` is `{}`, so
  `engine_for_section()` routes every section to the legacy engine. The only
  live hook is opt-in parity capture: `ARS_PARITY_CAPTURE=1` makes
  `analytics/txn_wrapper.py` dump figure data through `ars_parity`.

## How it will go live (per-wave plan)

1. **Wave 1** — vertical slice: port `entity_profile` + deck compile +
   `odd_store`, behind a per-section flag in `engine_flags.json`.
2. **Parity gate** — a section flips only after the parity harness shows
   old-vs-new equivalence on reference clients. Known gap: the harness
   compares figure data but not slide text (titles/notes/KPIs) — issue #264.
3. Repeat per section until `analytics/` exec() scripts are retired.

## Dependency note

`duckdb` is required by `ars_engine.data.txn_store` at module level. Since
2026-08-12 it is in `requirements.txt` (which builds the CSM Windows Python
bundle) and in `pyproject.toml` — before that the CSM machines could not
import the v3 store at all. Keep the two dependency lists in lockstep; each
carries a comment saying so.

## Working rules

- All v3 code lives inside the numbered folders (repo rule) and is exposed
  via `pyproject.toml` `package-dir` — no parallel top-level packages.
- Don't add scaffolding ahead of a wave that uses it.
- The legacy spine stays the production path until a section's parity gate
  passes; v3 work must never change legacy numbers as a side effect.
