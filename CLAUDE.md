# RPE-Workflow — Working Rules for Claude

This repo ships a monthly reporting pipeline to CSMs at CSI/Velocity. The operator-facing surface is `05_UI/` (FastAPI `app.py` + static `index.html`). **It is the product**, not a convenience layer.

## The UI-First Rule

Every diagnostic, fix, run, audit, and tool must be operable from the UI. CSMs don't open notebooks. CSMs don't run Python. CSMs don't read `.py` files.

**Never tell the operator to:**
- Run a script in a Jupyter notebook (`exec(open(...).read())`, "drop in a cell", etc.)
- Run an analysis from the terminal (`python 01_Analysis/...`, `jupyter nbconvert`, etc.)
- Edit a Python file to change behavior
- Inspect output by tailing logs or opening CSVs manually

**Always:**
- Surface new functionality as a button, panel, or tab in `05_UI/index.html`
- Back it with an endpoint in `05_UI/app.py`
- Stream / display the result in the UI itself (text panel, table, chart — whatever fits)
- If a script today only works as a notebook cell, refactor it into a callable function and wire it in. The notebook form is legacy, not target state.

If a one-off terminal command is truly the only way to unblock right-now work, say so explicitly and frame it as a **stopgap**, not a recommendation.

## Repo Structure (orientation only — verify before citing)

- `00_Formatting/` — raw ODD extraction from CSM data dumps
- `01_Analysis/00-Scripts/analytics/` — analysis modules (`competition/`, `deposit/`, etc.)
- `02_Presentations/` — PPTX generation and Deck Polish
- `03_Config/clients_config.json` — client metadata. Note: **no CSM field** — CSM-to-client membership is implicit in folder layout, not config.
- `05_UI/app.py` — FastAPI backend
- `05_UI/index.html` — operator console
- `READY_FOR_ANALYSIS/{csm}/{month}/{client_id}/` — formatted ODDs; this layout is the source of truth for "which clients belong to which CSM in which month"

## GitHub Issues

When filing or commenting on issues in this repo:
- Describe **UI behavior** (what button, what panel, what the operator sees)
- Don't paste notebook commands as the resolution path
- Include reproduction steps as UI clicks, not CLI invocations
- Inline runnable instructions when relevant — issues are read across machines, don't reference local context

## Coding Conventions

- Follow existing `05_UI/app.py` patterns for new endpoints (FastAPI, query-param filters, JSON return)
- Follow existing `05_UI/index.html` patterns for new UI (vanilla JS, `async function loadX()` style, `onchange=` wiring)
- Keep backward compatibility on `/api/*` defaults — existing tabs depend on no-arg behavior

## Git Workflow

- Active branch: `feature/txn-deck-restructure`
- Commit message style: conventional commits (`feat(...)`, `fix(...)`, `docs(...)`)
- Always push after committing
- Issues closed by a commit: reference with `Closes #NNN` in the commit body

## Operator Environment (the work machine)

The work machine is **Windows**. The repo lives at **`M:\ARS\`** (not under a user directory). The UI is launched by double-clicking **`Start Here.bat`** at the repo root, which:
1. `cd`s into `05_UI` and runs `python app.py` in the background
2. Waits for `http://localhost:8000` to respond
3. Opens the browser to the UI
4. Closing the terminal window stops the server

**When telling the operator how to apply a code change**, the workflow is always:
1. `git pull` from `M:\ARS\`
2. Close the existing **Velocity Pipeline** terminal window
3. Double-click `Start Here.bat` to relaunch
4. Hard-refresh the browser (Ctrl+Shift+R) for HTML/JS changes

**Never tell the operator to run `python app.py` directly, `cd 05_UI`, or use a Unix-style path** — that's the dev environment, not theirs.

See `SETUP.md` for the canonical M: drive layout and first-time setup commands.
