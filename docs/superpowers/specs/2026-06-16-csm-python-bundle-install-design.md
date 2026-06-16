# CSM Python Bundle Install — Design

**Date:** 2026-06-16
**Status:** Approved (verbal), implementation on branch `feat/csm-python-bundle`
**Issue:** #226 (csm install issue)

## Problem

CSMs cannot launch the UI. `Start Here.bat` runs the system `python`, which on
their machines is either absent or present-but-without-our-packages. Issue #226
shows a machine with Python 3.12.10 installed but `ModuleNotFoundError: No
module named 'fastapi'`. The same screenshot reveals two more facts:

- The repo is accessed over a **UNC path** (`\\PADMIS105\Velocity_Company\ARS\`),
  not always a mapped `M:` drive.
- CSMs don't know how to launch it — they paste the file path into the Python
  REPL (`SyntaxError`) and into CMD instead of using `Start Here.bat`.

Constraints: non-technical operators; no admin rights (plan for it); internet
available; **all inputs/outputs/code live on the network share**; large data
(100k–160k rows) where speed matters; the code must stay as plain `.py` files
so the weekly update flow and the `code:` version stamp keep working.

## Decision

Ship a **self-contained, relocatable Windows Python** (interpreter + all 14
`requirements.txt` packages) and have the launcher use it instead of the system
Python. Split by change-frequency and by what the network is slow at:

| Concern | Location | Rationale |
|---|---|---|
| Python + packages | **Local**: `%LOCALAPPDATA%\Velocity\python\` | Big, file-heavy, slow over SMB; rarely changes; no admin needed |
| Code, data, outputs, `.bat`s | **Share** (unchanged) | Central weekly updates; system of record; `code:` stamp intact |

Rejected alternatives: PyInstaller `.exe` (fragile with pandas/matplotlib/pptx,
and freezes the weekly code updates); `uv` bootstrap (elegant but per-machine
online first-run and a hidden cache location, which works against the operator's
need to understand where things live); scripted per-user `pip install` (most
"where did it go" confusion; assumes Python already present).

### Speed note

Packaging carries **zero compute penalty** — a relocatable CPython runs the same
compiled wheels as an installed one. 160k rows is a seconds-scale vectorized
pandas workload. If a *run* is slow, the lever is the analysis code + share I/O
(re-reading `.xlsx` via openpyxl, repeated reads, per-file network round-trips),
which is a separate profiling task, not a packaging concern.

## Components

1. **`CSM Setup.bat`** (root) — one-time, idempotent. Downloads the bundle from
   the fixed-tag release and `Expand-Archive`s it to `%LOCALAPPDATA%\Velocity\`.
   Verifies by importing fastapi/pandas/numpy/matplotlib/pptx. Plain-English
   failure messages.
2. **`Start Here.bat`** (root, rewritten) — runs the server with the bundled
   interpreter; clear message if setup hasn't run. **UNC fix:** `pushd "%~dp0..."`
   replaces `cd /d`, which Windows refuses on UNC paths (the #226 root cause).
   The temp drive mapping is left in place for the server's lifetime (no `popd`
   before `pause`).
3. **`.github/workflows/build-python-bundle.yml`** — Windows runner downloads
   the latest `astral-sh/python-build-standalone` `install_only` x64 CPython,
   pip-installs `requirements.txt` into it, zips with `python\` at the archive
   root, and publishes to the **fixed `python-bundle` release tag**. Triggered
   manually or on `requirements.txt` change. No local Windows machine required.
4. **`INSTALL.md`** — two-step CSM guide + operator "how it works / rebuild".

## Contracts

- Bundle archive root contains `python\python.exe` (matches both the workflow's
  `Compress-Archive -Path python` and Setup's `Expand-Archive` + the launcher's
  `%LOCALAPPDATA%\Velocity\python\python.exe`).
- Download URL is the fixed tag, **not** `releases/latest` (latest currently
  points at `deck-polish-v0.1.0-pre`).
- No admin: everything lands under `%LOCALAPPDATA%`.

## Verification (not yet done — authored on macOS)

1. Trigger the workflow; confirm `Velocity-Python.zip` publishes to
   `python-bundle`.
2. On one CSM machine: `CSM Setup.bat` → `Done`; `Start Here.bat` → UI opens;
   confirm it works from the `\\PADMIS105\...` UNC path, not just a mapped drive.

## Out of scope

Run-time performance optimization of the analysis pipeline (separate profiling
effort). UI-First rule does not apply: this is the pre-UI bootstrap that lets
the UI launch at all.
