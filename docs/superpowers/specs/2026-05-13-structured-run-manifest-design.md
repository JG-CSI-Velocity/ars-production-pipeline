# Structured Run Manifest — Design

**Date:** 2026-05-13
**Status:** Approved (brainstorm complete; awaiting written-spec review)
**Owner:** James Gilmore
**Scope tag:** Run reliability + foundation for confidence layer + curation agent
**Predecessor:** Issues #92, #100, #101, #116 — chronic difficulty diagnosing pipeline runs from raw logs

## Background

The pipeline currently emits a single rolling log per run (loguru → `04_Logs/<csm>/<client>_<timestamp>.log`). The UI streams a tail of that log live. After-the-fact diagnosis means grep-ing 1,600+ line files. There's no structured representation of "what happened" — only prose.

Symptoms this causes:

- At-1:30-AM debugging sessions. The UI's running tally tells you the pipeline is *doing things*, but not whether what it's doing is right, whether a section failed, or what numbers it produced.
- Filing GitHub issues from a failed run is manual: open the log, find the error, copy stack trace, look up file/line context, write the issue body. 5-10 minutes per failure.
- Downstream consumers — a future confidence/anomaly layer, a future "head consultant" curation agent — have nowhere to read structured numbers from. They'd have to re-parse the same logs.

## What we're building

A **structured run manifest** (`run_manifest.json`) written alongside the existing log. The manifest captures:

1. Per-section status, slide counts, elapsed time, and key numbers as the run progresses (live, not after-the-fact).
2. Per-script failure entries with all the context needed to file a GitHub issue without log-grepping.
3. Anomaly flags (e.g., a section producing 0 slides when it shouldn't, a key number deviating from prior-month).
4. A post-run scorecard (`run_scorecard.md`) generated from the manifest — one page, scannable in 30 seconds.

This is **not** a UI rewrite, **not** a pre-flight validator, **not** a checkpoint/resume system. It's the data layer that future UI work, validation, confidence checks, and the curation agent will all read from.

## Goals

- **Diagnosis time from N minutes to N seconds.** Open `run_scorecard.md`; see at a glance what shipped, what failed, what's worth investigating. No log-grepping.
- **Issue-filing is one click.** Every failed script has a pre-formatted GitHub issue body in the manifest. Copy/paste, done.
- **Foundation, not silo.** The manifest schema is the contract that the future confidence layer and curation agent code against.

## Non-goals

- **No checkpoint or resume.** Explicitly excluded. If a run fails, the user re-runs from the top.
- **No UI work in this spec.** A separate spec will design the UI panel that reads this manifest live. This spec ends at "manifest exists on disk, scorecard exists on disk."
- **No pre-flight validation.** Worth doing eventually; not part of this spec. Failures are surfaced *during* the run, not before it starts.
- **No automatic retries.** If something fails, it stays failed in the manifest. Re-running is a user action.
- **No confidence/anomaly engine in this spec.** This spec defines the *fields* (`key_numbers`, `anomaly_flags`) but populates them with simple deterministic rules. A follow-up spec designs the real anomaly detector that reads those fields.

## Architecture

### Components

```
┌──────────────────────────────────────────────────────────────┐
│  ars_analysis/pipeline/runner.py                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ RunManifest (in-memory)                                │ │
│  │   - mutable Python object                              │ │
│  │   - one instance per run, lives on ctx.manifest        │ │
│  │   - flush_to_disk() called after every section + on   │ │
│  │     exception, atomic write via tempfile + rename      │ │
│  └────────────────────────────────────────────────────────┘ │
│           │                       │                          │
│           ▼                       ▼                          │
│   run_manifest.json        loguru log (unchanged)           │
└──────────────────────────────────────────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────┐
   │ scorecard.py (post-run)      │
   │   reads run_manifest.json     │
   │   writes run_scorecard.md     │
   └──────────────────────────────┘
```

### The `RunManifest` object

A single Python class in `ars_analysis/pipeline/manifest.py`. Owns one in-memory dict per run. Two responsibilities:

1. **Mutation API** — small set of methods that the pipeline calls at boundaries:
   - `start_run(client_id, csm, month, product) -> None`
   - `start_section(name) -> SectionRecorder` (context manager)
   - `record_script(section, name, status, **fields)` (called inside `txn_wrapper._execute_scripts`)
   - `record_slide_count(section, n)` and `record_key_numbers(section, dict)`
   - `record_anomaly(section, level, message)`
   - `end_run(status)`

2. **Persistence** — `flush()` writes the current state to `run_manifest.json` (atomic rename). Called automatically at the end of every section, on any exception, and on `end_run`.

`SectionRecorder` is a small context manager so call-sites read naturally:

```python
with ctx.manifest.start_section("Competition") as sec:
    sec.record_key_numbers({"top_25_fed_district": 0, "credit_unions": 2814})
    if 0 < credit_unions_count < 100:
        sec.flag("warn", "credit_unions count suspiciously low")
```

Failures inside the `with` block automatically set the section status to `failed` and attach the exception info.

### Wiring into existing code

Three integration points, all small:

- **`pipeline/runner.py`** — instantiate the manifest on run start, attach to `ctx.manifest`, call `start_run` / `end_run`. ~15 lines.
- **`analytics/txn_wrapper.py`** — in `_execute_scripts`, wrap the existing `exec(...)` in a try/except that calls `manifest.record_script(...)` with success or failure status. The structured error capture (class, message, traceback file/line, suggested-fix heuristic) lives here, in one place. ~30 lines.
- **`pipeline/steps/generate.py`** — after the deck is built, call `manifest.end_run` and `scorecard.write(manifest, output_path)`. ~5 lines.

No changes to any of the 220 analytics scripts.

### Manifest schema (JSON, written to disk)

Minimum viable shape. Future fields can be added without breaking consumers.

```json
{
  "schema_version": 1,
  "run_id": "1200_2026.05_20260513_013002",
  "client_id": "1200",
  "client_name": "Guardians Credit Union",
  "csm": "JamesG",
  "month": "2026.05",
  "product": "combined",
  "started_at": "2026-05-13T01:30:02Z",
  "ended_at": "2026-05-13T02:11:24Z",
  "elapsed_s": 2482,
  "status": "partial",
  "totals": {
    "sections_ok": 20,
    "sections_failed": 0,
    "sections_no_charts": 2,
    "scripts_total": 187,
    "scripts_ok": 181,
    "scripts_failed": 6,
    "slides_built": 326
  },
  "sections": [
    {
      "name": "Competition",
      "status": "ok",
      "started_at": "...",
      "elapsed_s": 187,
      "slides": 38,
      "key_numbers": {
        "total_competitor_txns": 412309,
        "credit_unions": 2814,
        "local_banks": 1456,
        "top_25_fed_district": 0,
        "big_nationals": 38127
      },
      "anomaly_flags": [
        { "level": "warn",
          "message": "top_25_fed_district=0 — unexpected for FL portfolio" }
      ],
      "scripts": [
        { "name": "02_competitor_detection", "status": "ok",
          "elapsed_s": 31, "slides": 3 },
        { "name": "04_build_threat_data", "status": "failed",
          "elapsed_s": 2,
          "error_class": "IndexError",
          "error_msg": "single positional indexer is out-of-bounds",
          "error_file": "competition/04_build_threat_data.py",
          "error_line": 18,
          "error_traceback_tail": "<last 10 frames as a single string>",
          "suggested_fix": "Empty group survived upstream filter; add a len() guard before iloc[0].",
          "issue_body_md": "## Failure during 1200 / 2026.05 run\n\n**Section:** Competition\n**Script:** 04_build_threat_data.py\n**Error:** IndexError — single positional indexer is out-of-bounds\n**Location:** competition/04_build_threat_data.py:18\n\n... (full pre-formatted body)" }
      ]
    }
  ]
}
```

`status` values:

- Section: `ok` / `partial` / `failed` / `no_charts` / `skipped`
- Script: `ok` / `failed` / `skipped`
- Run: `ok` / `partial` / `failed`

`anomaly_flags.level`: `info` / `warn` / `error`. This spec ships with a small set of **deterministic, single-run** rules only:

- Section produced 0 slides when its registry entry indicates it should produce >0 (`warn`).
- A script reported `status="ok"` but `slides=0` (`info`).
- A required column listed in `AnalysisModule.required_columns` was missing from input data (`warn`).

Anything that compares across runs (month-over-month deltas, trend deviation) is **explicitly deferred** to the anomaly-engine follow-up spec — it reads the same `anomaly_flags` field but has its own logic and a separate state store for prior-run baselines.

### Structured error capture

Where the real work is. Inside `txn_wrapper._execute_scripts`, the try/except already exists but only logs to loguru. We add three pieces of context:

1. **Frame extraction** — use `traceback.extract_tb()` to find the deepest frame inside the project's analytics folder. That's the `error_file` + `error_line`. Filters out pandas/numpy internals so the failure points at *your* code, not the library.
2. **Suggested-fix heuristic** — a small dict keyed by `(error_class, regex on message)`. E.g.:
   - `IndexError + "out-of-bounds"` → "Empty group/series. Add a `len() > 0` or `not .empty` guard."
   - `KeyError` → "Column or dict key not found. Check upstream dependency produced this field."
   - `MemoryError + "Unable to allocate"` → "Likely a cross-join or unbounded groupby. Check `competitor_match` cardinality or use `chunksize`."
   - `NameError + "is not defined"` → "An upstream script failed and didn't define this variable. Check the earliest failure in this section's manifest."
   - Default: empty string, no suggestion. The user is no worse off.
3. **`issue_body_md`** — a small templated string assembled from the other fields. Already issue-ready Markdown.

These three pieces make the manifest's failure entries self-contained. The user (or a future "file-this-issue" command) doesn't need to re-grep the log.

### Post-run scorecard

`run_scorecard.md`, written to the client's output folder next to the deck. Markdown, ~50 lines, generated from the manifest. Structure:

```markdown
# Run scorecard — 1200 / 2026.05 (JamesG)

**Verdict:** Investigate before shipping
- 6 scripts failed (Competition.04, Competition.13, Competition.15, Competition.16, Competition.17, Executive.05)
- 1 section flagged anomalous (Competition: top_25_fed_district=0)
- Deck shipped: `1200_2026.05_combined_deck.pptx` (326 slides)
- Elapsed: 41m 22s

## Section status

| Section            | Status | Slides | Key numbers                                       | Flags |
| ---                | ---    | ---    | ---                                               | ---   |
| Portfolio Overview | OK     | 17     | accounts=36,840 active=22,229                     |       |
| Competition        | OK*    | 38     | credit_unions=2,814 local_banks=1,456 fed=0       | warn  |
| Financial Services | OK     | 15     | auto_loans=947 insurance=2,184 brokerage=812      |       |
| ...                |        |        |                                                   |       |

## Failures (ready to file)

### Competition · 04_build_threat_data — IndexError

> single positional indexer is out-of-bounds at competition/04_build_threat_data.py:18
>
> *Suggested fix: Empty group survived upstream filter. Add a `len() > 0` guard before `iloc[0]`.*
>
> <details><summary>Issue body (copy/paste)</summary>
> ...pre-formatted markdown issue body...
> </details>

(Repeat per failure.)

## Anomaly flags

- **Competition:** `top_25_fed_district=0` — unexpected for FL portfolio. Verify Fed District 6 patterns matched.
```

The scorecard is **derived from** the manifest. The manifest is the source of truth.

## Data flow

1. UI's Run button kicks off `01_Analysis/run.py` (no change).
2. `runner.py` creates a `RunManifest` and attaches it to `ctx.manifest`. Writes initial `run_manifest.json` to client output folder.
3. Each step (`step_load`, `step_analyze`, `step_generate`) calls into existing analytics. `txn_wrapper._execute_scripts` is the chokepoint — every TXN script's success/failure flows through there into `manifest.record_script(...)`.
4. After every section, `manifest.flush()` writes the updated JSON to disk (atomic rename).
5. On any exception in the pipeline, the exception handler in `runner.py` calls `manifest.end_run("failed")` and `flush()` before re-raising. The manifest is always on disk in a valid state.
6. On clean completion, `runner.py` calls `manifest.end_run("ok" | "partial")` and `scorecard.write(...)` generates `run_scorecard.md`.
7. Both files sit in the client output folder alongside the deck, Excel, and run log. The cross-sell folder remains separate.

## Error handling

- **Manifest writes must never fail the run.** All `flush()` calls are wrapped in try/except → loguru warning. If disk is full or the path is bad, the pipeline keeps going.
- **Manifest reads must tolerate missing fields.** Consumers (scorecard, future UI, future curation agent) use `.get()` with defaults. Schema additions don't break older readers.
- **Concurrent runs.** Each manifest lives in a per-run directory, so two concurrent runs (different clients) don't collide. No locking needed.
- **Manifest corruption.** Atomic write via `tempfile.NamedTemporaryFile` + `os.replace` so a crash mid-write never leaves a half-written file.

## Testing

Three layers:

1. **Unit tests for `RunManifest`** — happy path (full lifecycle), failure path (exception inside section), schema serialization/deserialization round-trip. ~10 tests, no external dependencies, fast.
2. **Unit tests for `scorecard.write`** — given a fixture manifest with mixed-status sections, generate the markdown, snapshot-compare. ~5 tests.
3. **Integration check via existing test pipeline** — run the existing 1453 test fixture, assert that a `run_manifest.json` is produced, has the expected top-level keys, and contains entries for every section in the registry. ~1 test.

No tests rely on the live 1200 data or a live UI; the manifest object is pure Python.

## Risks and trade-offs

- **Schema churn.** As the curation agent + confidence layer come online, they'll want fields we haven't thought of yet. Mitigated by `schema_version` + permissive `.get()` consumers. We can add fields without breaking old manifests; we just can't rename or remove them.
- **Manifest can grow large.** A run with 220 scripts and rich `error_traceback_tail` strings might produce a 200-500 KB JSON. Acceptable. If it ever balloons past a few MB, we can move tracebacks to a separate `failures.jsonl`.
- **Heuristic fix suggestions might be wrong.** If `IndexError` gets the wrong suggestion, the user wastes a minute. Mitigated by keeping the suggestion always-optional and clearly labelled "suggested fix", not "the fix".
- **No backward compatibility.** New code; nothing to break. Existing logs remain unchanged so any external tooling that grep-s logs still works.

## Out of scope (filed as follow-ups before implementation begins)

1. **UI integration** — new spec to design the live status panel that polls `run_manifest.json`. Includes the per-section status cards, drill-in modal, "Copy to issue" button.
2. **Anomaly engine** — new spec for the real anomaly detector. Reads `key_numbers` across runs, computes month-over-month deltas, surfaces violations into `anomaly_flags`.
3. **Curation agent** — new spec for the "head consultant" that reads the manifest, picks the 30-40 storyline slides, applies brand formatting, emits a curated deck.
4. **Pre-flight validator** — new spec for the 30-second pre-run check (parseable inputs, wired config, dependencies present).

These four follow-ups all assume the manifest exists. This spec is the prerequisite.

## Implementation order (high-level — full plan is the writing-plans skill's job)

1. `RunManifest` class + JSON schema + atomic write.
2. Wire into `runner.py` start/end of run.
3. Wire into `txn_wrapper._execute_scripts` for per-script capture, including the suggested-fix heuristic table.
4. Add the deterministic anomaly rules (empty sections, missing required fields).
5. `scorecard.write(manifest, path)` + Markdown template.
6. Generate scorecard at end of `generate_output` step.
7. Tests (unit + integration).
8. Document the manifest schema in `docs/` for future-spec consumers.
