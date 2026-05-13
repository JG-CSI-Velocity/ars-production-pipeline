# run_manifest.json schema

Source of truth: `01_Analysis/00-Scripts/pipeline/manifest.py`.

Consumers: post-run scorecard (today), future UI panel, future anomaly engine, future curation agent.

## Top-level fields

| Field            | Type   | Notes |
| ---              | ---    | --- |
| `schema_version` | int    | Always 1 in this spec. Bump for breaking changes. |
| `run_id`         | str    | `{client_id}_{month}_{YYYYMMDD_HHMMSS}` |
| `client_id`      | str    | |
| `client_name`    | str    | |
| `csm`            | str    | |
| `month`          | str    | `YYYY.MM` |
| `product`        | str    | `ars` / `txn` / `combined` |
| `started_at`     | str    | ISO 8601 UTC |
| `ended_at`       | str    | ISO 8601 UTC |
| `elapsed_s`      | float  | |
| `status`         | str    | `running` / `ok` / `partial` / `failed` |
| `totals`         | object | aggregate counters (see below) |
| `sections`       | array  | one entry per pipeline section |

## `totals`

| Field                | Type | Notes |
| ---                  | ---  | --- |
| `sections_ok`        | int  | |
| `sections_failed`    | int  | |
| `sections_no_charts` | int  | |
| `scripts_total`      | int  | |
| `scripts_ok`         | int  | |
| `scripts_failed`     | int  | |
| `slides_built`       | int  | sum across sections |

## `sections[]`

| Field            | Type   | Notes |
| ---              | ---    | --- |
| `name`           | str    | Section display name |
| `status`         | str    | `running` / `ok` / `partial` / `failed` / `no_charts` / `skipped` |
| `started_at`     | str    | ISO 8601 UTC |
| `ended_at`       | str    | ISO 8601 UTC |
| `elapsed_s`      | float  | |
| `slides`         | int    | Number of charts captured this section |
| `key_numbers`    | object | Free-form `{string: number}` — section reports its own KPIs |
| `anomaly_flags`  | array  | `[{level: info|warn|error, message: str}]` |
| `scripts`        | array  | one entry per .py script in the section |

## `sections[].scripts[]`

| Field                  | Type | Notes |
| ---                    | ---  | --- |
| `name`                 | str  | Script stem |
| `status`               | str  | `ok` / `failed` / `skipped` |
| `elapsed_s`            | float | |
| `slides`               | int  | Charts captured by this script |
| `error_class`          | str  | Exception class name (empty on success) |
| `error_msg`            | str  | First 300 chars |
| `error_file`           | str  | Deepest project frame path |
| `error_line`           | int  | Line in error_file |
| `error_traceback_tail` | str  | Last 2KB of traceback string |
| `suggested_fix`        | str  | Heuristic suggestion (may be empty) |
| `issue_body_md`        | str  | Pre-formatted GitHub issue body |

## Compatibility rules

- **Add fields freely.** Consumers must use `.get()` with defaults.
- **Never rename or remove fields** without bumping `schema_version`.
- **Status string values are stable** (UI/consumers may switch on them).
