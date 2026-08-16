"""Velocity Report Pipeline -- FastAPI Backend

Serves the UI and provides API endpoints for:
- Client list and config
- Module registry
- Pipeline execution with progress streaming
- Results and download serving

Run: python app.py
Then open: http://localhost:8000
"""

import asyncio
import ctypes
import json
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Force the headless matplotlib backend for this process AND every analysis
# subprocess it spawns (children inherit os.environ). Parallel client runs that
# fall back to the interactive TkAgg backend exhaust Windows GDI/Tk pixmaps
# under concurrent figure creation -> "Fail to create pixmap with Tk_GetPixmap
# in TkImgPhotoInstanceSetSize" (issue #214). An in-code matplotlib.use("Agg")
# only wins if it runs before the first pyplot import in every entry path;
# setting the env var here makes Agg authoritative regardless of import order.
# setdefault so an explicit operator override (rare) still takes precedence.
os.environ.setdefault("MPLBACKEND", "Agg")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="Velocity Report Pipeline")

# ─── CONFIG ───────────────────────────────────────────────────────────

# Resolve ARS base path
if sys.platform == "win32":
    ARS_BASE = Path(r"M:\ARS")
else:
    ARS_BASE = Path("/Volumes/M/ARS")  # Mac fallback for dev

# Fallback: if neither M: drive path exists, use the script's parent directory
# (handles local dev on Mac without M: drive mounted)
if not ARS_BASE.exists():
    ARS_BASE = Path(__file__).resolve().parent.parent

CONFIG_PATH = ARS_BASE / "03_Config" / "clients_config.json"
ARS_CONFIG_PATH = ARS_BASE / "03_Config" / "ars_config.json"
FORMATTING_BASE = ARS_BASE / "00_Formatting"
ANALYSIS_BASE = ARS_BASE / "01_Analysis"
PRESENTATIONS_BASE = ARS_BASE / "02_Presentations"
LOGS_BASE = ARS_BASE / "04_Logs"
READY_FOR_ANALYSIS = FORMATTING_BASE / "02-Data-Ready for Analysis"
COMPLETED_ANALYSIS = ANALYSIS_BASE / "01_Completed_Analysis"
COMPLETED_INTELLIGENCE = ANALYSIS_BASE / "01_Completed_Intelligence"

# Serve HTML documentation from the operator UI. The same links still work when
# files are opened directly from disk because the hrefs are relative.
app.mount("/docs", StaticFiles(directory=ARS_BASE / "docs", check_dir=False), name="docs")

# In-memory run tracking
runs = {}

# Live subprocess handle for each run, so the emergency STOP ALL can kill it.
# Kept OUT of `runs` because that dict is JSON-serialized back to the UI and a
# Popen object isn't serializable. Keyed by run_id; holds the currently-active
# child (a run formats then analyses, so the handle is overwritten as it moves
# from step to step).
run_procs: dict = {}


def _register_proc(run_id: str, proc) -> None:
    """Track the currently-active child process for a run (for STOP ALL)."""
    run_procs[run_id] = proc


def _popen_tree_kwargs() -> dict:
    """Popen kwargs that isolate the child so its whole tree can be killed.

    The analysis step can fan out ProcessPoolExecutor worker processes; killing
    only the top ``run.py`` would orphan them. On POSIX we give the child its own
    session so ``os.killpg`` targets that group (and never the server's). On
    Windows the tree is reaped by ``taskkill /T`` (no special flag needed).
    """
    if os.name == "posix":
        return {"start_new_session": True}
    return {}


_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001


def _keep_system_awake() -> bool:
    """Block Windows idle-sleep for the lifetime of the calling thread.

    Long runs die when the machine sleeps mid-pipeline (#251: a cold 1192
    load streams ~6.5 GB of TXN files off the M: share -- over an hour on
    that link). SetThreadExecutionState is per-thread and its requirement
    clears automatically when the thread exits, so each run thread calls
    this once at startup and no cleanup is needed. It does NOT override the
    lid-close action -- that stays with Windows power settings.

    Returns True if the request was made (Windows only), for testability.
    """
    if platform.system() != "Windows":
        return False
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
        )
        return True
    except Exception:
        return False


def _terminate_proc(proc) -> bool:
    """Kill a child process AND its descendants. Returns True if a live process
    was signalled; a no-op if ``proc`` is None or already exited."""
    if proc is None or proc.poll() is not None:
        return False
    pid = proc.pid
    try:
        if os.name == "nt":
            # /T kills the whole tree (analysis pool workers included), /F forces.
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
            )
        else:
            # Capture the group up front -- once the leader dies os.getpgid raises.
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            # Sweep the whole group: pool workers can outlive the parent, and a
            # child that ignored SIGTERM still dies here.
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    except (ProcessLookupError, PermissionError, OSError):
        # Fall back to terminating just the top process.
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        pass
    return True


def _mark_terminal(run_id: str, status: str, progress: int | None = None) -> None:
    """Set a run's final status -- but only if it's still ``running``.

    A STOP ALL flips the status to ``stopped`` and kills the subprocess; the
    worker thread then unblocks from its now-dead ``proc.wait()`` and would
    otherwise overwrite that with ``error``. Guarding on the current status
    keeps the operator's ``stopped`` verdict from being clobbered.
    """
    run = runs.get(run_id)
    run_procs.pop(run_id, None)
    if not run or run.get("status") != "running":
        return
    run["status"] = status
    if progress is not None:
        run["progress"] = progress
    run["finished"] = datetime.now().isoformat()


# A run still marked "running" after this many seconds is treated as dead (the
# server never saw its subprocess finish -- a hard crash or hang) so a stuck
# entry can't permanently block new runs for that client.
STALE_RUN_SECONDS = 2 * 60 * 60  # 2 hours -- well beyond the slowest real deck


def _seconds_since(iso_ts: str) -> float:
    """Seconds since an ISO timestamp; +inf if missing/unparseable."""
    if not iso_ts:
        return float("inf")
    try:
        return (datetime.now() - datetime.fromisoformat(iso_ts)).total_seconds()
    except (ValueError, TypeError):
        return float("inf")


def _active_run(csm: str, month: str, client_id: str, product: str):
    """Return (run_id, run) for an in-progress run on the same target, else None.

    Guards against a second run firing for the same client while the first is
    still going. Concurrent runs collide on the one output folder and
    run_manifest.json (Windows os.replace -> WinError 5) and garble each other's
    logs (#232). A different product (the ars+txn companion run) or a different
    client/period is not a collision and is allowed through.
    """
    target = (csm, month, client_id, product)
    for run_id, run in runs.items():
        if run.get("status") != "running":
            continue
        if (run.get("csm"), run.get("month"), run.get("client_id"), run.get("product")) != target:
            continue
        if _seconds_since(run.get("started", "")) > STALE_RUN_SECONDS:
            continue  # presumed dead -- don't let it block forever
        return run_id, run
    return None


def _reject_if_run_active(csm: str, month: str, client_id: str, product: str) -> None:
    """Raise 409 if a matching run is already in progress (#232)."""
    existing = _active_run(csm, month, client_id, product)
    if not existing:
        return
    _, run = existing
    mins = int(_seconds_since(run.get("started", "")) // 60)
    label = {"ars": "ARS", "txn": "TXN", "combined": "ARS + TXN", "formatting": "Formatting"}.get(
        product, product.upper()
    )
    raise HTTPException(
        status_code=409,
        detail=(
            f"A {label} run for client {client_id} ({csm} / {month}) is already in "
            f"progress (started {mins} min ago). Wait for it to finish, or watch it on "
            f"the History tab, before starting another for the same client."
        ),
    )


# Short-TTL cache for the dropdown directory scans (#229). Picking a CSM /
# month / client re-walks the network share each time; over SMB that's slow.
# Cache results for a minute so flipping around the dropdowns is instant.
# Pass refresh=true (the UI's Refresh button) to force a fresh scan.
_SCAN_CACHE: dict = {}
_SCAN_TTL_SECONDS = 60.0


def _scan_cached(key: str, producer, refresh: bool = False):
    """Return a cached scan result, or run ``producer()`` and cache it."""
    now = time.time()
    if not refresh:
        hit = _SCAN_CACHE.get(key)
        if hit is not None and (now - hit[0]) < _SCAN_TTL_SECONDS:
            return hit[1]
    value = producer()
    _SCAN_CACHE[key] = (now, value)
    return value


# ─── HELPERS ──────────────────────────────────────────────────────────

def _ensure_scripts_importable() -> None:
    """Make 01_Analysis/00-Scripts importable as both top-level and ars_analysis.*"""
    _scripts = str(Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts")
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    import ars_bootstrap
    ars_bootstrap.ensure_ars_analysis()


def get_code_version() -> dict:
    """Git stamp of the running checkout (sha/branch/dirty/label).

    Lets the operator confirm the server is on the code they think it is
    -- a stale work-PC clone produced an entire client run with last
    week's charts before anyone noticed.
    """
    _ensure_scripts_importable()
    try:
        from shared.version import get_code_version as _gcv
        return _gcv()
    except Exception:
        return {"sha": "", "branch": "", "dirty": False, "label": "unknown"}


def _newest_artifact(directory, pattern: str):
    """Newest file matching pattern (TXN runs suffix their artifacts so ARS +
    TXN can run concurrently; readers show whichever finished last)."""
    candidates = sorted(
        directory.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True
    )
    return candidates[0] if candidates else None


def load_run_report(csm: str, month: str, client_id: str) -> dict | None:
    """Load the persisted run_report.json for a completed run, or None."""
    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id
    report_path = _newest_artifact(analysis_dir, f"{client_id}_{month}*_run_report.json")
    if report_path is None:
        return None
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return None

def load_ars_config():
    """Load ars_config.json."""
    if ARS_CONFIG_PATH.exists():
        return json.loads(ARS_CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def load_clients_config():
    """Load clients_config.json."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _client_meta(client_id: str) -> dict:
    """Look up one client's metadata from clients_config.json.

    The config is keyed by client ID at the top level (see /api/clients).
    A previous `.get("clients", {})` lookup here always returned {} and
    silently rebuilt decks with client_name = client_id and empty
    eligibility codes. A legacy nested {"clients": {...}} shape is still
    honored as a fallback.
    """
    config = load_clients_config()
    meta = config.get(client_id)
    if isinstance(meta, dict):
        return meta
    nested = config.get("clients")
    if isinstance(nested, dict) and isinstance(nested.get(client_id), dict):
        return nested[client_id]
    return {}


def get_csm_list():
    """Get CSM names from ars_config.json sources (not hardcoded)."""
    cfg = load_ars_config()
    sources = cfg.get("csm_sources", {}).get("sources", {})
    if sources:
        return sorted(sources.keys())
    return []


def find_formatted_odd(csm, month, client_id):
    """Find the formatted ODD file for a client.

    Looks for an ODD file regardless of how it got into 02-Data-Ready for
    Analysis (UI, CLI, manual placement). Tries each candidate CSM folder
    (exact match first, then fuzzy `startswith`):

      1. `{CSM}/{month}/{client_id}/*.xlsx`           -- canonical
      2. `{CSM}/{month}/{client_id}-*-ODD.xlsx`       -- file at month level
      3. `{CSM}/{month}/{client_id}*.xlsx`            -- any xlsx prefixed by
                                                         client_id at month level

    Returns the first match as a string, or None.
    """
    if not READY_FOR_ANALYSIS.exists():
        return None

    csm_dirs: list[Path] = []
    exact = READY_FOR_ANALYSIS / csm
    if exact.is_dir():
        csm_dirs.append(exact)
    for d in READY_FOR_ANALYSIS.iterdir():
        if d.is_dir() and d.name.lower().startswith(csm.lower()) and d not in csm_dirs:
            csm_dirs.append(d)

    for csm_dir in csm_dirs:
        month_dir = csm_dir / month
        if not month_dir.is_dir():
            continue

        client_dir = month_dir / client_id
        if client_dir.is_dir():
            xlsx = sorted(client_dir.glob("*.xlsx"))
            if xlsx:
                return str(xlsx[0])

        for pattern in (f"{client_id}-*-ODD.xlsx", f"{client_id}-*.xlsx", f"{client_id}*.xlsx"):
            matches = sorted(f for f in month_dir.glob(pattern) if f.is_file())
            if matches:
                return str(matches[0])

    return None


SUPPORTED_INTELLIGENCE_INPUT_SUFFIXES = {".csv", ".txt", ".dat", ".xlsx", ".xlsm", ".xls", ".parquet", ""}
TRANSACTION_FILE_TOKENS = ("txn", "txns", "tran", "trans", "transaction", "transactions")


def _looks_like_transaction_file(path: Path) -> bool:
    """Return True for staged transaction extracts, while avoiding ODD workbooks."""
    if path.suffix.lower() not in SUPPORTED_INTELLIGENCE_INPUT_SUFFIXES:
        return False
    lineage = " ".join([path.name, *(p.name for p in list(path.parents)[:3])]).lower()
    if "odd" in lineage or "oddd" in lineage:
        return False
    normalized = re.sub(r"[^a-z0-9]+", " ", lineage)
    return any(token in normalized.split() for token in TRANSACTION_FILE_TOKENS)


def _find_transaction_files(csm: str, month: str, client_id: str) -> list[Path]:
    """Find staged transaction files for a client/month.

    The formatter can stage raw TXN files under a client folder, while some
    modified extracts land at the month level with the client ID in the file
    name. V1 accepts both shapes and filters out ODD files.
    """
    if not READY_FOR_ANALYSIS.exists():
        return []

    month_dir = _resolve_csm_dir(READY_FOR_ANALYSIS, csm) / month
    if not month_dir.exists():
        return []

    candidates: list[Path] = []
    client_dir = month_dir / client_id
    if client_dir.is_dir():
        candidates.extend(p for p in client_dir.rglob("*") if p.is_file())

    for p in month_dir.glob(f"{client_id}*"):
        if p.is_file():
            candidates.append(p)

    seen: set[Path] = set()
    txns: list[Path] = []
    for path in sorted(candidates):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _looks_like_transaction_file(path):
            txns.append(path)
    return txns


def _intelligence_output_dir(csm: str, month: str, client_id: str) -> Path:
    return _resolve_csm_dir(COMPLETED_INTELLIGENCE, csm) / month / client_id


def _period_sort_value(period: str) -> tuple[int, int, str]:
    cleaned = str(period or "").replace("-", ".")
    parts = cleaned.split(".")
    try:
        return int(parts[0]), int(parts[1]), cleaned
    except (IndexError, ValueError):
        return (0, 0, cleaned)


def _prior_intelligence_output_dir(csm: str, month: str, client_id: str) -> Path | None:
    """Most recent completed intelligence folder before the requested month."""
    csm_dir = _resolve_csm_dir(COMPLETED_INTELLIGENCE, csm)
    if not csm_dir.exists():
        return None
    current_key = _period_sort_value(month)
    candidates = []
    for month_dir in csm_dir.iterdir():
        if not month_dir.is_dir():
            continue
        key = _period_sort_value(month_dir.name)
        if key >= current_key:
            continue
        client_dir = month_dir / client_id
        if (client_dir / "campaign_targets.csv").exists():
            candidates.append((key, client_dir))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def _safe_float(value, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed > 1:
        parsed = parsed / 100
    return parsed


def _json_load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _csv_records(path: Path, limit: int = 200) -> list[dict]:
    if not path.exists():
        return []
    import csv
    try:
        with path.open(newline="", encoding="utf-8") as f:
            return [row for _, row in zip(range(limit), csv.DictReader(f))]
    except Exception:
        return []


def _html_escape(value) -> str:
    import html
    return html.escape("" if value is None else str(value))


def _fmt_intelligence_value(value, *, money: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _html_escape(value)
    if money:
        return f"${number:,.0f}"
    if abs(number) >= 1000:
        return f"{number:,.0f}"
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _download_href(path: Path, *, inline: bool = True) -> str:
    from urllib.parse import quote

    suffix = "&inline=true" if inline else ""
    return f"/api/download?path={quote(str(path))}{suffix}"


def _html_artifact_links(output_dir: Path, names: list[str]) -> str:
    links = []
    for name in names:
        if not name:
            continue
        path = output_dir / name
        href = _download_href(path, inline=path.suffix.lower() in {".html", ".json", ".csv", ".txt", ".sql"})
        links.append(f"<a href='{href}'>{_html_escape(name)}</a>")
    return "<div class='links'>" + "".join(links) + "</div>" if links else "<p class='subtle'>No linked artifacts.</p>"


def _df_records(df, limit: int) -> list[dict]:
    if df is None or getattr(df, "empty", True):
        return []
    return df.head(limit).to_dict(orient="records")


def _df_table_html(df, columns: list[str], limit: int, empty: str = "No rows generated.") -> str:
    rows = _df_records(df, limit)
    if not rows:
        return f"<p class='subtle'>{_html_escape(empty)}</p>"
    available = [col for col in columns if any(col in row for row in rows)]
    if not available:
        available = list(rows[0].keys())[:8]
    header = "".join(f"<th>{_html_escape(col.replace('_', ' ').title())}</th>" for col in available)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{_html_escape(_clean_html_cell(row.get(col)))}</td>" for col in available) + "</tr>")
    return f"<div class='scroll'><table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"


def _clean_html_cell(value) -> str:
    if value is None:
        return ""
    try:
        if value != value:
            return ""
    except Exception:
        pass
    return str(value)


def _numeric_column_sum(df, column: str) -> int:
    if df is None or getattr(df, "empty", True) or column not in df:
        return 0
    total = 0.0
    for value in df[column]:
        try:
            total += float(value)
        except (TypeError, ValueError):
            continue
    return int(total)


def _truthy_column_count(df, column: str) -> int:
    if df is None or getattr(df, "empty", True) or column not in df:
        return 0
    return sum(str(value).strip().lower() in {"true", "1", "yes", "y"} for value in df[column])


def _column_equals_count(df, column: str, expected: str) -> int:
    if df is None or getattr(df, "empty", True) or column not in df:
        return 0
    return sum(str(value).strip() == expected for value in df[column])


def _cards_html(items: list, *, ordered: bool = False) -> str:
    if not items:
        return "<p class='subtle'>No items generated.</p>"
    cards = []
    for index, item in enumerate(items, start=1):
        label = f"{index}. " if ordered else ""
        cards.append(f"<div class='move'>{_html_escape(label + str(item))}</div>")
    return "<div class='moves'>" + "".join(cards) + "</div>"


def _write_intelligence_workbook(outputs, output_dir: Path) -> Path:
    """Write the analyst-facing workbook: story + scored output tables."""
    import pandas as pd

    path = output_dir / "transactional_intelligence_package.xlsx"
    summary = pd.DataFrame([{
        "quality_score": outputs.data_quality.get("quality_score"),
        "confidence": outputs.data_quality.get("confidence"),
        "warnings": ", ".join(outputs.data_quality.get("warnings") or []),
        "intake_work_order_rows": len(outputs.intake_work_order),
        "file_assembly_plan_rows": len(outputs.file_assembly_plan),
        "monthly_file_requirements_rows": len(outputs.monthly_file_requirements),
        "layout_gap_report_rows": len(outputs.layout_gap_report),
        "layout_contract_draft_queue_rows": len(outputs.layout_contract_draft_queue),
        "layout_contract_export_manifest_rows": len(outputs.layout_contract_export_manifest),
        "intelligence_lineage_graph_rows": len(outputs.intelligence_lineage_graph),
        "engine_run_ledger_rows": len(outputs.engine_run_ledger),
        "account_rows": outputs.data_quality.get("account_rows"),
        "transaction_rows": outputs.data_quality.get("transaction_rows"),
        "feature_rows": outputs.data_quality.get("feature_rows"),
        "account_intelligence_profile_rows": len(outputs.account_intelligence_profile),
        "model_rulebook_rows": len(outputs.model_rulebook),
        "account_scoring_trace_rows": len(outputs.account_scoring_trace),
        "counterparty_signal_rows": len(outputs.counterparty_signals),
        "counterparty_summary_rows": len(outputs.counterparty_summary),
        "relationship_segment_rows": len(outputs.relationship_segments),
        "segment_summary_rows": len(outputs.segment_summary),
        "opportunity_rows": len(outputs.opportunities),
        "portfolio_rows": len(outputs.opportunity_portfolio),
        "executive_scorecard_rows": len(outputs.executive_scorecard),
        "strategy_roadmap_rows": len(outputs.strategy_roadmap),
        "action_plan_rows": len(outputs.action_plan),
        "measurement_plan_rows": len(outputs.measurement_plan),
        "campaign_target_rows": len(outputs.campaign_targets),
        "csm_review_queue_rows": len(outputs.csm_review_queue),
        "analyst_validation_queue_rows": len(outputs.analyst_validation_queue),
        "marketing_activation_export_rows": len(outputs.marketing_activation_export),
        "banker_call_list_rows": len(outputs.banker_call_list),
        "data_team_load_plan_rows": len(outputs.data_team_load_plan),
        "stakeholder_export_manifest_rows": len(outputs.stakeholder_export_manifest),
        "measurement_baseline_rows": len(outputs.measurement_baseline),
        "outcome_result_rows": len(outputs.outcome_results),
        "outcome_summary_rows": len(outputs.outcome_summary),
        "intelligence_delta_report_rows": len(outputs.intelligence_delta_report),
        "consulting_insight_register_rows": len(outputs.consulting_insight_register),
        "role_handoff_rows": len(outputs.role_handoffs),
        "operating_control_plane_rows": len(outputs.operating_control_plane),
        "user_interaction_map_rows": len(outputs.user_interaction_map),
        "production_readiness_backlog_rows": len(outputs.production_readiness_backlog),
        "analysis_section_catalog_rows": len(outputs.analysis_section_catalog),
        "analysis_script_catalog_rows": len(outputs.analysis_script_catalog),
        "analysis_provenance_map_rows": len(outputs.analysis_provenance_map),
        "analysis_execution_map_rows": len(outputs.analysis_execution_map),
        "analysis_chart_data_snapshot_rows": len(outputs.analysis_chart_data_snapshot),
        "intelligence_metric_catalog_rows": len(outputs.intelligence_metric_catalog),
        "analysis_feature_derivation_catalog_rows": len(outputs.analysis_feature_derivation_catalog),
        "analysis_consulting_playbook_rows": len(outputs.analysis_consulting_playbook),
        "analysis_insight_brief_rows": len(outputs.analysis_insight_brief),
        "client_meeting_deck_blueprint_rows": len(outputs.client_meeting_deck_blueprint),
        "analysis_review_board_rows": len(outputs.analysis_review_board),
        "analysis_package_index_rows": len(outputs.analysis_package_index),
        "insight_count": len(outputs.insights),
    }])
    insights = pd.DataFrame(outputs.insights)
    story = outputs.consulting_story or {}
    story_summary = pd.DataFrame([{
        "headline": story.get("headline", ""),
        "executive_summary": story.get("executive_summary", story.get("narrative", "")),
        "measurement_message": story.get("measurement_message", ""),
        "insight_count": story.get("insight_count", len(outputs.insights)),
    }])
    story_arc = pd.DataFrame(story.get("story_arc", []))

    def _sheet(df, fallback: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame({"message": [fallback]})
        return df

    with pd.ExcelWriter(path) as writer:
        summary.to_excel(writer, sheet_name="Run Summary", index=False)
        story_summary.to_excel(writer, sheet_name="Story", index=False)
        _sheet(story_arc, "No consulting story arc generated.").to_excel(
            writer, sheet_name="Story Arc", index=False
        )
        _sheet(insights, "No insights generated.").to_excel(writer, sheet_name="Insights", index=False)
        _sheet(outputs.opportunity_portfolio, "No opportunity portfolio generated.").to_excel(
            writer, sheet_name="Portfolio", index=False
        )
        _sheet(outputs.counterparty_summary, "No counterparty summary generated.").to_excel(
            writer, sheet_name="Counterparty Summary", index=False
        )
        _sheet(outputs.account_intelligence_profile, "No account intelligence profile generated.").to_excel(
            writer, sheet_name="Account Profile", index=False
        )
        _sheet(outputs.account_scoring_trace, "No account scoring trace generated.").to_excel(
            writer, sheet_name="Scoring Trace", index=False
        )
        _sheet(outputs.model_rulebook, "No model rulebook generated.").to_excel(
            writer, sheet_name="Model Rulebook", index=False
        )
        _sheet(outputs.counterparty_signals, "No counterparty signals generated.").to_excel(
            writer, sheet_name="Counterparties", index=False
        )
        _sheet(outputs.executive_scorecard, "No executive scorecard generated.").to_excel(
            writer, sheet_name="Scorecard", index=False
        )
        _sheet(outputs.strategy_roadmap, "No strategy roadmap generated.").to_excel(
            writer, sheet_name="Roadmap", index=False
        )
        _sheet(outputs.segment_summary, "No segment summary generated.").to_excel(
            writer, sheet_name="Segment Summary", index=False
        )
        _sheet(outputs.relationship_segments, "No relationship segments generated.").to_excel(
            writer, sheet_name="Segments", index=False
        )
        _sheet(outputs.action_plan, "No action plan generated.").to_excel(
            writer, sheet_name="Action Plan", index=False
        )
        _sheet(outputs.role_handoffs, "No role handoffs generated.").to_excel(
            writer, sheet_name="Role Handoffs", index=False
        )
        _sheet(outputs.operating_control_plane, "No operating control plane generated.").to_excel(
            writer, sheet_name="Control Plane", index=False
        )
        _sheet(outputs.user_interaction_map, "No user interaction map generated.").to_excel(
            writer, sheet_name="User Interactions", index=False
        )
        _sheet(outputs.production_readiness_backlog, "No production readiness backlog generated.").to_excel(
            writer, sheet_name="Production Backlog", index=False
        )
        _sheet(outputs.consulting_insight_register, "No consulting insight register generated.").to_excel(
            writer, sheet_name="Insight Register", index=False
        )
        _sheet(outputs.analysis_section_catalog, "No analysis section catalog generated.").to_excel(
            writer, sheet_name="Analysis Sections", index=False
        )
        _sheet(outputs.analysis_script_catalog, "No analysis script catalog generated.").to_excel(
            writer, sheet_name="Analysis Scripts", index=False
        )
        _sheet(outputs.analysis_provenance_map, "No analysis provenance map generated.").to_excel(
            writer, sheet_name="Provenance", index=False
        )
        _sheet(outputs.analysis_execution_map, "No analysis execution map generated.").to_excel(
            writer, sheet_name="Execution Map", index=False
        )
        _sheet(outputs.analysis_chart_data_snapshot, "No analysis chart data snapshots generated.").to_excel(
            writer, sheet_name="Chart Data", index=False
        )
        _sheet(outputs.intelligence_metric_catalog, "No intelligence metric catalog generated.").to_excel(
            writer, sheet_name="Metric Catalog", index=False
        )
        _sheet(outputs.analysis_feature_derivation_catalog, "No feature derivation catalog generated.").to_excel(
            writer, sheet_name="Feature Derivations", index=False
        )
        _sheet(outputs.analysis_consulting_playbook, "No analysis consulting playbook generated.").to_excel(
            writer, sheet_name="Analysis Playbook", index=False
        )
        _sheet(outputs.analysis_insight_brief, "No analysis insight brief generated.").to_excel(
            writer, sheet_name="Insight Brief", index=False
        )
        _sheet(outputs.client_meeting_deck_blueprint, "No client meeting deck blueprint generated.").to_excel(
            writer, sheet_name="Meeting Blueprint", index=False
        )
        _sheet(outputs.analysis_review_board, "No analysis review board generated.").to_excel(
            writer, sheet_name="Analysis Review", index=False
        )
        _sheet(outputs.analysis_package_index, "No analysis package index generated.").to_excel(
            writer, sheet_name="Package Index", index=False
        )
        _sheet(outputs.intake_work_order, "No intake work order generated.").to_excel(
            writer, sheet_name="Intake Work Order", index=False
        )
        _sheet(outputs.file_assembly_plan, "No file assembly plan generated.").to_excel(
            writer, sheet_name="File Assembly", index=False
        )
        _sheet(outputs.monthly_file_requirements, "No monthly file requirements generated.").to_excel(
            writer, sheet_name="File Requirements", index=False
        )
        _sheet(outputs.layout_gap_report, "No layout gap report generated.").to_excel(
            writer, sheet_name="Layout Gaps", index=False
        )
        _sheet(outputs.layout_contract_draft_queue, "No layout contract draft queue generated.").to_excel(
            writer, sheet_name="Contract Drafts", index=False
        )
        _sheet(outputs.layout_contract_export_manifest, "No layout contract exports generated.").to_excel(
            writer, sheet_name="Contract Exports", index=False
        )
        _sheet(outputs.intelligence_lineage_graph, "No intelligence lineage graph generated.").to_excel(
            writer, sheet_name="Lineage Graph", index=False
        )
        _sheet(outputs.engine_run_ledger, "No engine run ledger generated.").to_excel(
            writer, sheet_name="Run Ledger", index=False
        )
        _sheet(outputs.measurement_plan, "No measurement plan generated.").to_excel(
            writer, sheet_name="Measurement", index=False
        )
        _sheet(outputs.campaign_targets, "No campaign targets generated.").to_excel(
            writer, sheet_name="Targets", index=False
        )
        _sheet(outputs.csm_review_queue, "No CSM review queue generated.").to_excel(
            writer, sheet_name="CSM Queue", index=False
        )
        _sheet(outputs.analyst_validation_queue, "No analyst validation queue generated.").to_excel(
            writer, sheet_name="Analyst QA", index=False
        )
        _sheet(outputs.marketing_activation_export, "No marketing activation export generated.").to_excel(
            writer, sheet_name="Marketing Export", index=False
        )
        _sheet(outputs.banker_call_list, "No banker call list generated.").to_excel(
            writer, sheet_name="Banker Calls", index=False
        )
        _sheet(outputs.data_team_load_plan, "No data-team load plan generated.").to_excel(
            writer, sheet_name="Data Load Plan", index=False
        )
        _sheet(outputs.stakeholder_export_manifest, "No stakeholder export manifest generated.").to_excel(
            writer, sheet_name="Export Manifest", index=False
        )
        _sheet(outputs.measurement_baseline, "No measurement baseline generated.").to_excel(
            writer, sheet_name="Baseline", index=False
        )
        _sheet(outputs.outcome_summary, "No measured outcomes generated.").to_excel(
            writer, sheet_name="Outcome Summary", index=False
        )
        _sheet(outputs.outcome_results, "No account-level outcomes generated.").to_excel(
            writer, sheet_name="Outcome Results", index=False
        )
        _sheet(outputs.intelligence_delta_report, "No intelligence delta report generated.").to_excel(
            writer, sheet_name="Delta Report", index=False
        )
        _sheet(outputs.opportunities, "No opportunities generated.").to_excel(
            writer, sheet_name="Opportunities", index=False
        )
        _sheet(outputs.pfi_verdicts, "No PFI verdicts generated.").to_excel(
            writer, sheet_name="PFI Verdicts", index=False
        )
        _sheet(outputs.account_month_features, "No account-month features generated.").to_excel(
            writer, sheet_name="Account Features", index=False
        )
        _sheet(outputs.file_ledger, "No input files recorded.").to_excel(
            writer, sheet_name="File Ledger", index=False
        )
    return path


def _intelligence_story(outputs, client_name: str, month: str) -> dict:
    """Summarize the engine output into the consulting story the UI can show."""
    if getattr(outputs, "consulting_story", None):
        story = dict(outputs.consulting_story)
        story.setdefault("narrative", story.get("executive_summary", ""))
        story.setdefault("consulting_moves", story.get("recommended_conversation", []))
        return story

    opps = outputs.opportunities
    quality = outputs.data_quality or {}
    story = {
        "headline": "Transaction behavior is ready for relationship intelligence.",
        "narrative": (
            f"{client_name} has {quality.get('transaction_rows', 0):,} transaction rows and "
            f"{quality.get('feature_rows', 0):,} account-month feature rows available for {month}. "
            "The engine turns those rows into relationship signals, ranked opportunities, and exportable tables."
        ),
        "consulting_moves": [
            "Validate data confidence before presenting findings.",
            "Prioritize accounts where payroll, debit activity, balances, and external FI movement tell the same story.",
            "Use ranked opportunity rows for campaigns, banker follow-up, and client strategy sessions.",
            "Feed outcomes back into the next monthly run so the engine can measure movement.",
        ],
    }
    if opps is not None and not opps.empty and "opportunity_type" in opps:
        top_types = (
            opps.groupby("opportunity_type")
            .agg(accounts=("account_id", "nunique"), expected_value=("expected_value", "sum"))
            .reset_index()
            .sort_values(["expected_value", "accounts"], ascending=False)
            .head(3)
        )
        if not top_types.empty:
            leader = top_types.iloc[0]
            story["headline"] = (
                f"{str(leader['opportunity_type']).replace('_', ' ').title()} is the leading opportunity."
            )
            story["narrative"] = (
                f"The engine found {len(opps):,} ranked account-level opportunities. "
                f"The largest pool is {str(leader['opportunity_type']).replace('_', ' ')} "
                f"across {int(leader['accounts']):,} account(s), with "
                f"{_fmt_intelligence_value(leader['expected_value'], money=True)} in modeled value."
            )
            story["top_opportunity_types"] = top_types.to_dict(orient="records")
    return story


def _write_intelligence_html(outputs, output_dir: Path, *, client_name: str, client_id: str, month: str) -> dict[str, Path]:
    """Write CSM/consulting review pages without requiring PowerPoint."""
    story = _intelligence_story(outputs, client_name, month)
    quality = outputs.data_quality or {}
    opps = outputs.opportunities
    action_plan = outputs.action_plan
    role_handoffs = outputs.role_handoffs
    operating_control_plane = outputs.operating_control_plane
    intake_work_order = outputs.intake_work_order
    counterparty_summary = outputs.counterparty_summary
    segment_summary = outputs.segment_summary
    executive_scorecard = outputs.executive_scorecard
    strategy_roadmap = outputs.strategy_roadmap
    analysis_provenance = outputs.analysis_provenance_map
    top_opps = opps.head(12).to_dict(orient="records") if opps is not None and not opps.empty else []
    actions = action_plan.head(8).to_dict(orient="records") if action_plan is not None and not action_plan.empty else []
    handoffs = role_handoffs.head(8).to_dict(orient="records") if role_handoffs is not None and not role_handoffs.empty else []
    control_rows = (
        operating_control_plane.head(8).to_dict(orient="records")
        if operating_control_plane is not None and not operating_control_plane.empty
        else []
    )
    intake_rows = intake_work_order.head(12).to_dict(orient="records") if intake_work_order is not None and not intake_work_order.empty else []
    counterparties = counterparty_summary.head(10).to_dict(orient="records") if counterparty_summary is not None and not counterparty_summary.empty else []
    segments = segment_summary.head(8).to_dict(orient="records") if segment_summary is not None and not segment_summary.empty else []
    scorecard = executive_scorecard.head(10).to_dict(orient="records") if executive_scorecard is not None and not executive_scorecard.empty else []
    roadmap = strategy_roadmap.head(8).to_dict(orient="records") if strategy_roadmap is not None and not strategy_roadmap.empty else []
    provenance = analysis_provenance.head(12).to_dict(orient="records") if analysis_provenance is not None and not analysis_provenance.empty else []
    insights = outputs.insights[:8] if outputs.insights else []
    warnings = quality.get("warnings") or []

    css = """
    <style>
    body{font-family:Montserrat,Arial,sans-serif;margin:0;background:#efefef;color:#111827}
    main{max-width:1180px;margin:0 auto;padding:36px 28px 56px}
    header{background:#00274c;color:#fff;padding:28px}
    h1{font-size:34px;margin:0 0 6px;font-weight:700} h2{font-size:20px;margin:0 0 14px}
    .sub{color:#cbd5e1;font-size:14px}.band{background:#fff;border:1px solid #d6d6d6;border-radius:8px;padding:22px;margin-top:20px}
    .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric{background:#f8fafc;border-left:4px solid #f15d22;padding:14px;border-radius:6px}
    .val{font-size:26px;font-weight:700}.lbl{font-size:11px;text-transform:uppercase;color:#64748b;letter-spacing:1px;margin-top:3px}
    p{line-height:1.55}.moves{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.move{background:#fff7ed;border:1px solid #fed7aa;padding:12px;border-radius:6px}
    table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;color:#64748b;text-transform:uppercase;font-size:10px;letter-spacing:1px;border-bottom:2px solid #d6d6d6;padding:8px}
    td{border-bottom:1px solid #e5e7eb;padding:9px;vertical-align:top}.pill{display:inline-block;background:#eef2ff;color:#3730a3;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700}
    .warn{background:#fff4e5;border-color:#f5b461}.good{background:#e8f5e9;border-color:#2e7d32}.subtle{color:#64748b;font-size:13px}.scroll{overflow-x:auto}
    .hero{background:#fff;border:1px solid #d6d6d6;border-radius:8px;padding:22px;margin-top:20px}.hero h2{font-size:26px;margin-bottom:8px}
    .links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.links a{border:1px solid #d6d6d6;background:#fff;border-radius:6px;padding:7px 9px;text-decoration:none;color:#155eef;font-size:12px}
    @media(max-width:800px){.grid,.moves{grid-template-columns:1fr}main{padding:20px 14px}.band{padding:16px}}
    </style>
    """
    metrics = [
        ("Quality", quality.get("quality_score", "--")),
        ("Confidence", quality.get("confidence", "--")),
        ("Accounts", quality.get("account_rows", "--")),
        ("Transactions", quality.get("transaction_rows", "--")),
    ]
    metric_html = "".join(
        f"<div class='metric'><div class='val'>{_html_escape(v)}</div><div class='lbl'>{_html_escape(k)}</div></div>"
        for k, v in metrics
    )
    moves_html = "".join(f"<div class='move'>{_html_escape(m)}</div>" for m in story["consulting_moves"])
    insight_html = "".join(
        f"<tr><td><span class='pill'>{_html_escape(i.get('insight_type','insight'))}</span></td>"
        f"<td>{_html_escape(i.get('title',''))}</td><td>{_html_escape(i.get('summary',''))}</td></tr>"
        for i in insights
    ) or "<tr><td colspan='3'>No insight objects generated.</td></tr>"
    action_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('priority_rank',''))}</td>"
        f"<td>{_html_escape(row.get('play_name',''))}</td>"
        f"<td>{_html_escape(row.get('target_accounts',''))}</td>"
        f"<td>{_fmt_intelligence_value(row.get('expected_value'), money=True)}</td>"
        f"<td>{_html_escape(row.get('owner_role',''))}</td>"
        f"<td>{_html_escape(row.get('next_step',''))}</td>"
        "</tr>"
        for row in actions
    ) or "<tr><td colspan='6'>No action plan generated.</td></tr>"
    handoff_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('role',''))}</td>"
        f"<td>{_html_escape(row.get('decision_owned',''))}</td>"
        f"<td>{_html_escape(row.get('export_artifact',''))}</td>"
        f"<td>{_html_escape(row.get('first_action',''))}</td>"
        f"<td>{_html_escape(row.get('status',''))}</td>"
        "</tr>"
        for row in handoffs
    ) or "<tr><td colspan='5'>No role handoffs generated.</td></tr>"
    control_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('workflow_lane',''))}</td>"
        f"<td>{_html_escape(row.get('role',''))}</td>"
        f"<td>{_html_escape(row.get('client_use_status',''))}</td>"
        f"<td>{_html_escape(row.get('open_first',''))}</td>"
        f"<td>{_html_escape(row.get('next_action',''))}</td>"
        f"<td>{_html_escape(row.get('blocker_summary',''))}</td>"
        "</tr>"
        for row in control_rows
    ) or "<tr><td colspan='6'>No operating control plane generated.</td></tr>"
    segment_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('relationship_segment',''))}</td>"
        f"<td>{_html_escape(row.get('account_count',''))}</td>"
        f"<td>{_fmt_intelligence_value(row.get('total_expected_value'), money=True)}</td>"
        f"<td>{_html_escape(row.get('risk_level',''))}</td>"
        f"<td>{_html_escape(row.get('top_next_best_motion',''))}</td>"
        "</tr>"
        for row in segments
    ) or "<tr><td colspan='5'>No relationship segment summary generated.</td></tr>"
    counterparty_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('counterparty_name',''))}</td>"
        f"<td>{_html_escape(row.get('counterparty_category',''))}</td>"
        f"<td>{_html_escape(row.get('account_count',''))}</td>"
        f"<td>{_fmt_intelligence_value(row.get('total_amount'), money=True)}</td>"
        f"<td>{_html_escape(row.get('strategy_relevance',''))}</td>"
        "</tr>"
        for row in counterparties
    ) or "<tr><td colspan='5'>No counterparty summary generated.</td></tr>"
    scorecard_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('domain',''))}</td>"
        f"<td>{_html_escape(row.get('metric_display',''))}</td>"
        f"<td>{_html_escape(row.get('rag_status',''))}</td>"
        f"<td>{_html_escape(row.get('recommended_focus',''))}</td>"
        "</tr>"
        for row in scorecard
    ) or "<tr><td colspan='4'>No executive scorecard generated.</td></tr>"
    roadmap_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('phase',''))}</td>"
        f"<td>{_html_escape(row.get('initiative',''))}</td>"
        f"<td>{_html_escape(row.get('owner_role',''))}</td>"
        f"<td>{_html_escape(row.get('proof_metric',''))}</td>"
        "</tr>"
        for row in roadmap
    ) or "<tr><td colspan='4'>No strategy roadmap generated.</td></tr>"
    provenance_html = "".join(
        "<tr>"
        f"<td>{_html_escape(str(row.get('opportunity_type','')).replace('_',' ').title())}</td>"
        f"<td>{_html_escape(row.get('source_section_id',''))}</td>"
        f"<td>{_html_escape(row.get('display_name',''))}</td>"
        f"<td>{_html_escape(row.get('contribution',''))}</td>"
        "</tr>"
        for row in provenance
    ) or "<tr><td colspan='4'>No analysis provenance generated.</td></tr>"
    opp_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('account_id',''))}</td>"
        f"<td>{_html_escape(str(row.get('opportunity_type','')).replace('_',' ').title())}</td>"
        f"<td>{_fmt_intelligence_value(row.get('priority_score'))}</td>"
        f"<td>{_fmt_intelligence_value(row.get('expected_value'), money=True)}</td>"
        f"<td>{_html_escape(row.get('recommended_action',''))}</td>"
        "</tr>"
        for row in top_opps
    ) or "<tr><td colspan='5'>No opportunities generated.</td></tr>"
    warning_html = "".join(f"<li>{_html_escape(w)}</li>" for w in warnings) or "<li>No material warnings.</li>"
    intake_html = "".join(
        "<tr>"
        f"<td>{_html_escape(row.get('file_name',''))}</td>"
        f"<td>{_html_escape(row.get('source_family',''))}</td>"
        f"<td>{_html_escape(row.get('match_status',''))}</td>"
        f"<td>{_html_escape(row.get('intake_decision',''))}</td>"
        f"<td>{_html_escape(row.get('operator_action',''))}</td>"
        "</tr>"
        for row in intake_rows
    ) or "<tr><td colspan='5'>No intake work order generated.</td></tr>"

    brief = output_dir / "executive_brief.html"
    brief.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Transactional Intelligence Brief</title>{css}</head>
        <body><header><h1>Transactional Intelligence Brief</h1><div class="sub">{_html_escape(client_name)} · {_html_escape(client_id)} · {_html_escape(month)}</div></header>
        <main>
          <section class="band"><h2>{_html_escape(story['headline'])}</h2><p>{_html_escape(story['narrative'])}</p><div class="grid">{metric_html}</div></section>
          <section class="band"><h2>Consulting Moves</h2><div class="moves">{moves_html}</div></section>
          <section class="band"><h2>Operating Control Plane</h2><table><thead><tr><th>Lane</th><th>Role</th><th>Status</th><th>Open First</th><th>Next Action</th><th>Blockers</th></tr></thead><tbody>{control_html}</tbody></table></section>
          <section class="band"><h2>Executive Scorecard</h2><table><thead><tr><th>Domain</th><th>Metric</th><th>Status</th><th>Focus</th></tr></thead><tbody>{scorecard_html}</tbody></table></section>
          <section class="band"><h2>Strategy Roadmap</h2><table><thead><tr><th>Phase</th><th>Initiative</th><th>Owner</th><th>Proof Metric</th></tr></thead><tbody>{roadmap_html}</tbody></table></section>
          <section class="band"><h2>Analysis Provenance</h2><table><thead><tr><th>Opportunity</th><th>Source Section</th><th>Analysis</th><th>Contribution</th></tr></thead><tbody>{provenance_html}</tbody></table></section>
          <section class="band"><h2>Counterparty Intelligence</h2><table><thead><tr><th>Counterparty</th><th>Category</th><th>Accounts</th><th>Amount</th><th>Relevance</th></tr></thead><tbody>{counterparty_html}</tbody></table></section>
          <section class="band"><h2>Relationship Segments</h2><table><thead><tr><th>Segment</th><th>Accounts</th><th>Value</th><th>Risk</th><th>Next Motion</th></tr></thead><tbody>{segment_html}</tbody></table></section>
          <section class="band"><h2>Operating Handoff</h2><table><thead><tr><th>Role</th><th>Decision</th><th>Export</th><th>First Action</th><th>Status</th></tr></thead><tbody>{handoff_html}</tbody></table></section>
          <section class="band"><h2>Action Plan</h2><table><thead><tr><th>Rank</th><th>Play</th><th>Accounts</th><th>Value</th><th>Owner</th><th>Next Step</th></tr></thead><tbody>{action_html}</tbody></table></section>
          <section class="band"><h2>Top Opportunities</h2><table><thead><tr><th>Account</th><th>Type</th><th>Priority</th><th>Value</th><th>Action</th></tr></thead><tbody>{opp_html}</tbody></table></section>
          <section class="band"><h2>Insight Objects</h2><table><thead><tr><th>Type</th><th>Title</th><th>Summary</th></tr></thead><tbody>{insight_html}</tbody></table></section>
        </main></body></html>""",
        encoding="utf-8",
    )

    quality_page = output_dir / "data_quality_report.html"
    quality_page.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Data Quality Report</title>{css}</head>
        <body><header><h1>Data Quality Report</h1><div class="sub">{_html_escape(client_name)} · {_html_escape(client_id)} · {_html_escape(month)}</div></header>
        <main>
          <section class="band {'good' if quality.get('quality_score', 0) >= 75 else 'warn'}"><h2>Readiness</h2><div class="grid">{metric_html}</div></section>
          <section class="band"><h2>Warnings</h2><ul>{warning_html}</ul></section>
          <section class="band"><h2>File Intake Work Order</h2><table><thead><tr><th>File</th><th>Family</th><th>Match</th><th>Decision</th><th>Action</th></tr></thead><tbody>{intake_html}</tbody></table></section>
          <section class="band"><h2>Mapped Columns</h2><pre>{_html_escape(json.dumps({'accounts': quality.get('mapped_account_columns', {}), 'transactions': quality.get('mapped_transaction_columns', {})}, indent=2))}</pre></section>
        </main></body></html>""",
        encoding="utf-8",
    )

    story_arc_rows = ""
    for item in story.get("story_arc", []):
        artifact_names = [name.strip() for name in str(item.get("artifact", "")).split("|") if name.strip()]
        story_arc_rows += (
            "<tr>"
            f"<td>{_html_escape(item.get('step', ''))}</td>"
            f"<td>{_html_escape(item.get('summary', ''))}</td>"
            f"<td>{_html_artifact_links(output_dir, artifact_names)}</td>"
            "</tr>"
        )
    if not story_arc_rows:
        story_arc_rows = "<tr><td colspan='3'>No story arc generated.</td></tr>"
    delivery_backlog = outputs.production_readiness_backlog
    if delivery_backlog is not None and not delivery_backlog.empty and "workstream" in delivery_backlog:
        delivery_backlog = delivery_backlog[
            delivery_backlog["workstream"].isin(["Analysis readiness", "User delivery", "Metric validation"])
        ]
    story_page = output_dir / "transactional_intelligence_client_story.html"
    story_page.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Transactional Intelligence Client Story</title>{css}</head>
        <body><header><h1>Transactional Intelligence Client Story</h1><div class="sub">{_html_escape(client_name)} · {_html_escape(client_id)} · {_html_escape(month)}</div></header>
        <main>
          <section class="hero"><h2>{_html_escape(story['headline'])}</h2><p>{_html_escape(story['narrative'])}</p><div class="grid">{metric_html}</div></section>
          <section class="band"><h2>Client Conversation Guide</h2>{_cards_html(story.get('consulting_moves', []), ordered=True)}</section>
          <section class="band"><h2>Decision Questions</h2>{_cards_html(story.get('consulting_questions', []), ordered=True)}</section>
          <section class="band"><h2>Story Arc</h2><table><thead><tr><th>Step</th><th>Summary</th><th>Proof Artifacts</th></tr></thead><tbody>{story_arc_rows}</tbody></table></section>
          <section class="band"><h2>Top Plays And Talk Track</h2>{_df_table_html(outputs.action_plan, ['priority_rank', 'play_name', 'objective', 'target_accounts', 'expected_value', 'confidence', 'owner_role', 'recommended_channel', 'next_step', 'talk_track'], 8)}</section>
          <section class="band"><h2>Meeting Run Of Show</h2>{_df_table_html(outputs.client_meeting_deck_blueprint, ['blueprint_rank', 'meeting_phase', 'slide_type', 'slide_title', 'primary_message', 'decision_prompt', 'source_artifact', 'data_caveat', 'follow_up_action', 'blueprint_status'], 36)}</section>
          <section class="band"><h2>Proof And Caveats</h2>{_df_table_html(outputs.analysis_insight_brief, ['source_section_id', 'display_name', 'brief_status', 'headline_insight', 'primary_evidence', 'data_caveat', 'recommended_client_question'], 18)}</section>
          <section class="band"><h2>Activation Exports</h2>{_df_table_html(outputs.stakeholder_export_manifest, ['artifact_name', 'file_name', 'primary_role', 'row_count', 'use_case', 'first_action', 'status'], 8)}{_html_artifact_links(output_dir, ['campaign_targets.csv', 'marketing_activation_export.csv', 'banker_call_list.csv', 'measurement_plan.csv'])}</section>
          <section class="band"><h2>CSM Review Queue</h2>{_df_table_html(outputs.csm_review_queue, ['review_rank', 'account_id', 'relationship_segment', 'pfi_verdict', 'top_play_name', 'top_priority_score', 'recommended_action', 'evidence_summary'], 20)}</section>
          <section class="band"><h2>Banker Call List</h2>{_df_table_html(outputs.banker_call_list, ['call_rank', 'account_id', 'branch', 'relationship_segment', 'top_play_name', 'recommended_action', 'talk_track', 'top_counterparties'], 20)}</section>
          <section class="band"><h2>Measurement Plan</h2>{_df_table_html(outputs.measurement_plan, ['measurement_id', 'play_name', 'opportunity_type', 'primary_metric', 'measurement_window', 'success_definition'], 12)}</section>
          <section class="band"><h2>Outcome Readout</h2>{_df_table_html(outputs.outcome_summary, ['play_name', 'target_accounts', 'test_outcome_accounts', 'test_outcome_rate', 'lift_vs_holdout', 'measurement_status', 'interpretation'], 12)}</section>
          <section class="band"><h2>Role Handoffs</h2>{_df_table_html(outputs.role_handoffs, ['role', 'decision_owned', 'outputs_used', 'export_artifact', 'first_action', 'handoff_to', 'success_metric', 'status'], 12)}</section>
          <section class="band"><h2>Open Delivery Risks</h2>{_df_table_html(delivery_backlog, ['backlog_rank', 'priority_band', 'workstream', 'owner_role', 'problem_statement', 'required_action', 'client_use_status'], 20)}</section>
        </main></body></html>""",
        encoding="utf-8",
    )

    monthly = outputs.monthly_file_requirements
    assembly = outputs.file_assembly_plan
    missing_fields = _numeric_column_sum(monthly, "missing_required_field_count")
    selected_files = _truthy_column_count(assembly, "load_flag")
    selected_families = _column_equals_count(monthly, "monthly_status", "selected_for_load")
    contract_exports = len(outputs.layout_contract_export_manifest) if outputs.layout_contract_export_manifest is not None else 0
    intake_backlog = outputs.production_readiness_backlog
    if intake_backlog is not None and not intake_backlog.empty and "workstream" in intake_backlog:
        intake_backlog = intake_backlog[
            intake_backlog["workstream"].isin(["Monthly intake", "Data contracts / Snowflake"])
        ]
    intake_metrics = "".join(
        f"<div class='metric'><div class='val'>{_html_escape(value)}</div><div class='lbl'>{_html_escape(label)}</div></div>"
        for label, value in [
            ("Raw Files", len(outputs.file_ledger)),
            ("Selected Loads", selected_files),
            ("File Families", len(monthly)),
            ("Selected Families", selected_families),
            ("Missing Fields", missing_fields),
            ("Contract Exports", contract_exports),
        ]
    )
    intake_page = output_dir / "transactional_intelligence_intake_cockpit.html"
    intake_page.write_text(
        f"""<!doctype html><html><head><meta charset="utf-8"><title>Monthly Client File Intake Cockpit</title>{css}</head>
        <body><header><h1>Monthly Client File Intake Cockpit</h1><div class="sub">{_html_escape(client_name)} · {_html_escape(client_id)} · {_html_escape(month)}</div></header>
        <main>
          <section class="hero"><h2>Monthly Client File Intake Cockpit</h2><p>Confirm which files arrived, which files load, what layouts need review, what contracts need promotion, and what Snowflake blockers remain.</p><div class="grid">{intake_metrics}</div></section>
          <section class="band"><h2>Operational Intake Process</h2><div class="moves"><div class="move">1. Receive monthly client files.</div><div class="move">2. Profile headers, delimiters, row counts, and contract matches.</div><div class="move">3. Decide whether to use, hold, map, or request replacement/fallback extracts.</div><div class="move">4. Load selected files and publish Snowflake-ready outputs.</div></div></section>
          <section class="band"><h2>Direct Files</h2>{_html_artifact_links(output_dir, ['intake_work_order.csv', 'file_assembly_plan.csv', 'monthly_file_requirements.csv', 'layout_gap_report.csv', 'layout_contract_draft_queue.csv', 'layout_contract_export_manifest.csv', 'data_team_load_plan.csv', 'snowflake_load.sql', 'README_SNOWFLAKE.html'])}</section>
          <section class="band"><h2>Monthly Requirement Status</h2>{_df_table_html(outputs.monthly_file_requirements, ['input_family', 'display_name', 'requirement_level', 'monthly_status', 'received_file_count', 'selected_file_count', 'missing_required_field_count', 'target_snowflake_layer', 'data_team_action', 'analyst_question'], 20)}</section>
          <section class="band"><h2>Snowflake Load Readiness</h2>{_df_table_html(outputs.data_team_load_plan, ['load_rank', 'file_name', 'source_family', 'contract_id', 'assembly_role', 'load_flag', 'target_engine_input', 'target_snowflake_layer', 'load_readiness', 'operator_action'], 20)}</section>
          <section class="band"><h2>Received Files And Assembly Decisions</h2>{_df_table_html(outputs.intake_work_order, ['priority_rank', 'file_name', 'source_family', 'contract_id', 'match_status', 'match_score', 'intake_decision', 'assigned_role', 'operator_action', 'missing_required_fields'], 20)}{_df_table_html(outputs.file_assembly_plan, ['file_name', 'source_family', 'contract_id', 'match_status', 'intake_decision', 'assembly_role', 'load_flag', 'target_engine_input', 'target_snowflake_layer', 'operator_action'], 20)}</section>
          <section class="band"><h2>Layout Gap Report</h2>{_df_table_html(outputs.layout_gap_report, ['file_name', 'source_family', 'contract_id', 'canonical_field', 'required_flag', 'mapping_status', 'suggested_source_column', 'confidence', 'remediation_action'], 40)}</section>
          <section class="band"><h2>Layout Contract Draft Queue</h2>{_df_table_html(outputs.layout_contract_draft_queue, ['draft_rank', 'file_name', 'priority_band', 'contract_action', 'current_contract_id', 'proposed_contract_id', 'missing_required_fields', 'data_team_action', 'analyst_question'], 40)}</section>
          <section class="band"><h2>Contract Export Manifest</h2>{_df_table_html(outputs.layout_contract_export_manifest, ['export_rank', 'file_name', 'priority_band', 'proposed_contract_id', 'yaml_relative_path', 'yaml_ready', 'target_snowflake_layer', 'data_team_action'], 40)}</section>
          <section class="band"><h2>Intake And Snowflake Production Backlog</h2>{_df_table_html(intake_backlog, ['backlog_rank', 'priority_band', 'workstream', 'readiness_area', 'owner_role', 'problem_statement', 'required_action', 'acceptance_criteria', 'snowflake_targets', 'client_use_status'], 60)}</section>
        </main></body></html>""",
        encoding="utf-8",
    )
    return {
        "executive_brief": brief,
        "data_quality_report": quality_page,
        "client_story": story_page,
        "intake_cockpit": intake_page,
    }


def _list_intelligence_files(csm: str, month: str, client_id: str) -> list[dict]:
    files = []
    out_dir = _intelligence_output_dir(csm, month, client_id)
    if out_dir.exists():
        for f in sorted(out_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".xlsx", ".json", ".csv", ".html", ".sql", ".yml", ".yaml"):
                files.append({
                    "name": str(f.relative_to(out_dir)),
                    "type": f.suffix[1:],
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "path": str(f),
                    "category": "intelligence",
                })
    return files


def _run_intelligence_engine(run_id: str, csm: str, month: str, client_id: str) -> None:
    """Run the V1 transactional intelligence engine in-process."""
    _keep_system_awake()

    def _log(message: str, progress: int | None = None, step: str | None = None) -> None:
        run = runs.get(run_id)
        if not run or run.get("status") != "running":
            return
        run["log"].append(message)
        if progress is not None:
            run["progress"] = progress
        if step is not None:
            run["current_step"] = step

    try:
        _ensure_scripts_importable()
        import pandas as pd
        from ars_engine.intelligence import (
            EngineConfig,
            read_input_table,
            run_transactional_intelligence,
            write_snowflake_package,
        )

        meta = _client_meta(client_id)
        client_name = meta.get("ClientName", client_id)
        ic_rate = _safe_float(meta.get("ICRate"), 0.015)
        odd_path = find_formatted_odd(csm, month, client_id)
        txn_paths = _find_transaction_files(csm, month, client_id)
        input_files = [Path(odd_path)] if odd_path else []
        input_files.extend(txn_paths)

        _log("=" * 60)
        _log("  STEP 1: Locate staged account and transaction files", progress=5, step="Locating intelligence inputs...")
        _log(f"  ODD: {odd_path or 'missing'}")
        _log(f"  Transaction files: {len(txn_paths)}")

        accounts = None
        if odd_path:
            _log("  Reading account / ODD file...", progress=18, step="Reading account data...")
            accounts = read_input_table(Path(odd_path))
            _log(f"  Account rows loaded: {len(accounts):,}")

        transactions = None
        if txn_paths:
            _log("  Reading transaction files...", progress=35, step="Reading transaction data...")
            frames = []
            for path in txn_paths:
                try:
                    frame = read_input_table(path)
                    frame["_source_file"] = path.name
                    frames.append(frame)
                    _log(f"  Loaded {path.name}: {len(frame):,} rows")
                except Exception as exc:
                    _log(f"  WARNING: Could not read {path.name}: {exc}")
            if frames:
                transactions = pd.concat(frames, ignore_index=True)
                _log(f"  Transaction rows loaded: {len(transactions):,}")

        if accounts is None and transactions is None:
            _log("ERROR: No supported ODD or transaction files found for this client.")
            _mark_terminal(run_id, "error")
            return

        _log("=" * 60)
        _log("  STEP 2: Build relationship intelligence", progress=60, step="Building intelligence features...")
        cfg = EngineConfig(
            client_id=client_id,
            client_name=client_name,
            period_month=month,
            interchange_rate=ic_rate,
        )
        prior_campaign_targets = None
        prior_measurement_baseline = None
        prior_account_intelligence_profile = None
        prior_opportunities = None
        prior_opportunity_portfolio = None
        prior_data_quality = None
        prior_dir = _prior_intelligence_output_dir(csm, month, client_id)
        if prior_dir:
            try:
                prior_campaign_targets = pd.read_csv(prior_dir / "campaign_targets.csv")
                baseline_path = prior_dir / "measurement_baseline.csv"
                if baseline_path.exists():
                    prior_measurement_baseline = pd.read_csv(baseline_path)
                profile_path = prior_dir / "account_intelligence_profile.csv"
                if profile_path.exists():
                    prior_account_intelligence_profile = pd.read_csv(profile_path)
                opportunities_path = prior_dir / "opportunities.csv"
                if opportunities_path.exists():
                    prior_opportunities = pd.read_csv(opportunities_path)
                portfolio_path = prior_dir / "opportunity_portfolio.csv"
                if portfolio_path.exists():
                    prior_opportunity_portfolio = pd.read_csv(portfolio_path)
                quality_path = prior_dir / "data_quality.json"
                if quality_path.exists():
                    prior_data_quality = _json_load(quality_path, {})
                _log(f"  Prior measurement package: {prior_dir}")
            except Exception as exc:
                _log(f"  WARNING: Could not read prior measurement package: {exc}")

        outputs = run_transactional_intelligence(
            accounts=accounts,
            transactions=transactions,
            input_files=input_files,
            prior_campaign_targets=prior_campaign_targets,
            prior_measurement_baseline=prior_measurement_baseline,
            prior_account_intelligence_profile=prior_account_intelligence_profile,
            prior_opportunities=prior_opportunities,
            prior_opportunity_portfolio=prior_opportunity_portfolio,
            prior_data_quality=prior_data_quality,
            config=cfg,
        )

        _log(
            f"  Feature rows: {len(outputs.account_month_features):,}; "
            f"opportunities: {len(outputs.opportunities):,}; insights: {len(outputs.insights):,}",
            progress=78,
            step="Writing intelligence artifacts...",
        )
        out_dir = _intelligence_output_dir(csm, month, client_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        written = outputs.write(out_dir)
        workbook = _write_intelligence_workbook(outputs, out_dir)
        html_paths = _write_intelligence_html(
            outputs,
            out_dir,
            client_name=client_name,
            client_id=client_id,
            month=month,
        )
        artifact_paths = {
            **written,
            "workbook": str(workbook),
            **{k: str(v) for k, v in html_paths.items()},
        }
        snowflake_paths = write_snowflake_package(
            outputs,
            out_dir,
            config=cfg,
            artifact_paths=artifact_paths,
            run_id=run_id,
        )
        runs[run_id]["artifacts"] = {
            **artifact_paths,
            **snowflake_paths,
        }
        runs[run_id]["quality_score"] = outputs.data_quality.get("quality_score")
        runs[run_id]["opportunity_rows"] = len(outputs.opportunities)
        _log(f"  Output folder: {out_dir}", progress=96, step="Finalizing intelligence package...")
        _log("  Intelligence package complete.", progress=100, step="Transactional intelligence complete.")
        _mark_terminal(run_id, "complete", progress=100)
    except Exception as exc:
        _log(f"ERROR: {exc}")
        _mark_terminal(run_id, "error")


def get_recent_runs():
    """Scan logs directory for recent run info with parsed details."""
    import re
    recent = []
    if not LOGS_BASE.exists():
        return recent
    for csm_dir in sorted(LOGS_BASE.iterdir()):
        if not csm_dir.is_dir():
            continue
        for month_dir in sorted(csm_dir.iterdir(), reverse=True):
            if not month_dir.is_dir():
                continue
            for log_file in sorted(month_dir.glob("*.log"), reverse=True):
                parts = log_file.stem.split("_")
                client_id = parts[0] if parts else "?"

                # Parse log for duration, slide count, status
                duration = "--"
                slides = "--"
                status = "complete"
                client_name = ""
                product = "ARS"
                modules = "--"
                try:
                    text = log_file.read_text(encoding="utf-8", errors="replace")
                    # Look for: Pipeline done: 1776 (CoastHills CU) -- 4/4 steps in 1824.2s
                    m = re.search(r"Pipeline done:.*?(\d+)\s+\(([^)]+)\).*?in\s+([\d.]+)s", text)
                    if m:
                        client_name = m.group(2)
                        secs = float(m.group(3))
                        mins = int(secs // 60)
                        duration = f"{mins}m {int(secs % 60)}s"
                    # Look for: ARS complete: 108 slides generated
                    m2 = re.search(r"(\d+)\s+slides?\s+generated", text)
                    if m2:
                        slides = m2.group(1)
                    # Product from the run's step-2 header, e.g.
                    # "STEP 2: ARS + TXN ANALYSIS + POWERPOINT GENERATION"
                    if re.search(r"STEP 2:\s*ARS \+ TXN ANALYSIS", text):
                        product = "COMBINED"
                    elif re.search(r"STEP 2:\s*TXN ANALYSIS", text):
                        product = "TXN"
                    elif re.search(r"STEP 2:\s*ARS ANALYSIS", text):
                        product = "ARS"
                    # Module count from progress lines: "Module 14/25: mailer.cohort"
                    mod_totals = re.findall(r"Module\s+\d+\s*/\s*(\d+):", text)
                    if mod_totals:
                        modules = max(mod_totals, key=int)
                    # Check for errors
                    if "ERROR" in text and "0 failed" not in text:
                        status = "warning"
                except Exception:
                    pass

                recent.append({
                    "csm": csm_dir.name,
                    "month": month_dir.name,
                    "client_id": client_id,
                    "client_name": client_name,
                    "timestamp": log_file.stem,
                    "file": str(log_file),
                    "duration": duration,
                    "slides": slides,
                    "product": product,
                    "modules": modules,
                    "status": status,
                })
                if len(recent) >= 20:
                    return recent
    return recent


# ─── PRODUCT / MODULE REGISTRY ────────────────────────────────────────

# Products the analysis backend can actually run today (01_Analysis/run.py
# --product choices). "dep" (Deposits) is advertised in the UI but has no
# backend yet, so it is intentionally excluded -- start_run rejects it.
SUPPORTED_PRODUCTS = {"ars", "txn", "combined"}

PRODUCTS = {
    "ars": {
        "name": "ARS Full Suite",
        "count": 22,
        "time": "15-25 min",
        "groups": [
            {"name": "Overview", "count": 3, "desc": "Foundation: eligibility, stat codes, product codes.",
             "modules": ["Stat Codes", "Product Codes", "Eligibility"]},
            {"name": "Debit Card Throughput", "count": 5, "desc": "Card usage: penetration, trends, branches, funnel, overlays.",
             "modules": ["Penetration", "Trends", "Branches", "Funnel", "Overlays"]},
            {"name": "Reg E / Overdraft", "count": 3, "desc": "Overdraft opt-in rates by branch and demographics.",
             "modules": ["Opt-in Status", "Branch Rates", "Dimensions"]},
            {"name": "Attrition", "count": 3, "desc": "Account closures: who, how many, revenue impact.",
             "modules": ["Closure Rates", "Demographics", "Revenue Impact"]},
            {"name": "Mailer Campaign", "count": 5, "desc": "Program effectiveness: response, lift, cohort, reach.",
             "modules": ["Response", "Impact", "Cohort Lift", "Reach", "Insights"]},
            {"name": "Value & Insights", "count": 3, "desc": "Revenue attribution, findings synthesis, recommendations.",
             "modules": ["Revenue", "Synthesis", "Recommendations"]},
        ],
    },
    "txn": {
        "name": "Transaction Analysis",
        "count": 35,
        "time": "25-40 min",
        "groups": [
            {"name": "Portfolio", "count": 5, "desc": "KPIs, engagement, demographics, seasonal patterns.",
             "modules": ["KPIs", "Engagement", "Demographics", "Seasonal", "Monthly"]},
            {"name": "Merchant", "count": 8, "desc": "Top merchants, MCC categories, business vs personal.",
             "modules": ["Top Merchants", "Concentration", "MCC", "Business", "Personal", "Trends", "By Age", "Lifecycle"]},
            {"name": "Competition", "count": 6, "desc": "Competitors, wallet share, threat analysis.",
             "modules": ["Detection", "Wallet Share", "Threat Quadrant", "Categories", "FI Transactions", "Leakage"]},
            {"name": "Operations", "count": 8, "desc": "Branch, PIN/SIG, product, interchange, payroll.",
             "modules": ["Branch Rank", "Branch Spend", "PIN vs SIG", "Channels", "Products", "IC Revenue", "IC Gap", "Payroll"]},
            {"name": "Risk", "count": 5, "desc": "Attrition, balance, retention, early warning.",
             "modules": ["Attrition", "Balance", "PFI Score", "Retention", "Early Warning"]},
            {"name": "Executive", "count": 3, "desc": "Scorecard, priorities, action roadmap.",
             "modules": ["Scorecard", "Priorities", "Roadmap"]},
        ],
    },
    # Deposits ('dep') removed in Phase 3: it had no analysis backend and no
    # near-term path, so it isn't advertised. Re-add here (and build the
    # analytics + a run_dep runner) if/when Deposits ships.
}


# ─── API ROUTES ───────────────────────────────────────────────────────

@app.get("/")
async def index():
    """Serve the main UI."""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Velocity</h1><p>index.html not found</p>")


@app.get("/api/version")
async def api_version():
    """Code-version stamp for the footer chip. See get_code_version()."""
    return get_code_version()


@app.get("/api/csms")
async def get_csms():
    """Return CSM names from ars_config.json (dynamic, not hardcoded)."""
    return get_csm_list()


_ODDD_CLIENT_ID_RE = re.compile(r"^(\d+)_ODDD", re.IGNORECASE)


def _clients_from_raw_dumps(csm: str, month: str) -> set[str]:
    """Scan M:\\<CSM>\\OD Data Dumps\\<month>\\ for *_ODDD.zip and return client IDs."""
    cfg = load_ars_config()
    sources = cfg.get("csm_sources", {}).get("sources", {})
    src_path = None
    for name, path in sources.items():
        if name.lower().startswith(csm.lower()):
            src_path = Path(path)
            break
    if not src_path or not src_path.exists():
        return set()
    month_dir = src_path / month
    if not month_dir.exists():
        return set()
    ids = set()
    for zf in month_dir.iterdir():
        if not zf.is_file():
            continue
        m = _ODDD_CLIENT_ID_RE.match(zf.name)
        if m:
            ids.add(m.group(1))
    return ids


def _clients_from_folder(base: Path, csm: str, month: str) -> set[str]:
    """Return client IDs that have a directory under base/<csm>/<month>/."""
    csm_dir = _resolve_csm_dir(base, csm) / month
    if not csm_dir.exists():
        return set()
    return {d.name for d in csm_dir.iterdir() if d.is_dir()}


@app.get("/api/clients")
async def get_clients(csm: str = "", month: str = "", refresh: bool = False):
    """Return client list from config.

    When csm and month are both provided, filter to clients that show up
    anywhere in this CSM's pipeline for that month:
      - Raw dumps: M:\\<CSM>\\OD Data Dumps\\<month>\\<client>_ODDD.zip
      - Formatted: 02-Data-Ready for Analysis/<csm>/<month>/<client>/
      - Completed: 01_Completed_Analysis/<csm>/<month>/<client>/

    Union of all three so a client shows up as soon as their raw ZIP lands,
    and stays visible after formatting/analysis even if the ZIP is moved.

    With no csm/month, returns the full config (used by Results-tab dropdown).
    """
    cache_key = f"clients|{csm}|{month}"
    if not refresh:
        _hit = _SCAN_CACHE.get(cache_key)
        if _hit is not None and (time.time() - _hit[0]) < _SCAN_TTL_SECONDS:
            return _hit[1]

    config = load_clients_config()

    allowed_ids = None
    if csm and month:
        allowed_ids = (
            _clients_from_raw_dumps(csm, month)
            | _clients_from_folder(READY_FOR_ANALYSIS, csm, month)
            | _clients_from_folder(COMPLETED_ANALYSIS, csm, month)
            | _clients_from_folder(COMPLETED_INTELLIGENCE, csm, month)
        )

    clients = []
    for cid, data in config.items():
        if allowed_ids is not None and cid not in allowed_ids:
            continue
        clients.append({
            "id": cid,
            "name": data.get("ClientName", f"Client {cid}"),
            "config": {
                "ic_rate": data.get("ICRate", ""),
                "nsf_od_fee": data.get("NSF_OD_Fee", ""),
                "stat_codes": data.get("EligibleStatusCodes", []),
                "prod_codes": data.get("EligibleProductCodes", []),
                "ineligible_stat": data.get("IneligibleStatusCodes", []),
                "eligible_mail": data.get("EligibleMailCode", ""),
                "reg_e_opt_in": data.get("RegEOptInCode", []),
                "branch_mapping": data.get("BranchMapping", {}),
            },
        })

    # Also surface IDs found in folders but missing from clients_config.json
    # (so the operator can see something exists even if config is stale).
    if allowed_ids is not None:
        known = {c["id"] for c in clients}
        for cid in sorted(allowed_ids - known):
            clients.append({
                "id": cid,
                "name": f"Client {cid} (not in config)",
                "config": {},
            })

    _SCAN_CACHE[cache_key] = (time.time(), clients)
    return clients


@app.get("/api/products")
async def get_products():
    return PRODUCTS


_SECTIONS_CACHE: dict = {}


SECTIONS_JSON = ANALYSIS_BASE / "00-Scripts" / "tools" / "sections.json"


def _list_sections() -> list[dict]:
    """The unified section registry (for the module picker).

    Reads a STATIC precomputed file (tools/sections.json) -- no subprocess and
    no analytics import, so the endpoint is instant and can never hang (the
    subprocess version stalled importing matplotlib/pandas on the work machine,
    leaving the picker stuck on "Loading modules…"). The file is committed and
    regenerated with `python 01_Analysis/00-Scripts/tools/list_sections.py
    --write`; a test asserts it matches the live registry.

    Only a non-empty result is cached, so a missing/broken file recovers on the
    UI's Retry after it's regenerated.
    """
    cached = _SECTIONS_CACHE.get("data")
    if cached:
        return cached
    try:
        data = json.loads(SECTIONS_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"  /api/modules: cannot read {SECTIONS_JSON}: {exc} "
              f"(regenerate with: python 01_Analysis/00-Scripts/tools/list_sections.py --write)")
        return []
    if data:
        _SECTIONS_CACHE["data"] = data
    return data


@app.get("/api/modules")
async def get_modules():
    """List selectable analytics sections for the 'run one module' picker."""
    return _list_sections()


@app.get("/api/module_counts")
async def module_counts():
    """Live module/section/script counts from the files actually on disk.

    The product cards previously showed hardcoded copy ('22 modules') that
    silently went stale as analytics cells were added or deleted -- which
    made real pipeline changes look like they hadn't landed."""
    analytics = Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts" / "analytics"
    # Derive the section list from the unified registry (single source of truth)
    # rather than a hardcoded list that silently drifted -- it had omitted
    # ICS_cohort and invented a phantom 'ics' folder.
    sections = _list_sections()
    txn_sections = [s["section_id"].split(".", 1)[1]
                    for s in sections if s.get("product") == "txn"]
    ars_dirs = [s["section_id"].split(".", 1)[1]
                for s in sections if s.get("product") == "ars"]

    def _modules(d: str) -> int:
        p = analytics / d
        if not p.is_dir():
            return 0
        return len([f for f in p.glob("*.py") if not f.name.startswith("_")])

    ars = sum(_modules(d) for d in ars_dirs)
    txn_existing = [d for d in txn_sections if (analytics / d).is_dir()]
    txn_scripts = sum(_modules(d) for d in txn_existing)
    return {
        "ars_modules": ars,
        "txn_sections": len(txn_existing),
        "txn_scripts": txn_scripts,
        "combined": ars + len(txn_existing),
    }


@app.get("/api/months")
async def get_months(csm: str = "", source: str = "all", refresh: bool = False):
    """Return available months by scanning actual directories.

    source=raw: scan CSM source folders (raw data dumps -- for formatting step)
    source=formatted: scan 02-Data-Ready for Analysis (already formatted -- for analysis step)
    source=all: combine both
    """
    cache_key = f"months|{csm}|{source}"
    if not refresh:
        _hit = _SCAN_CACHE.get(cache_key)
        if _hit is not None and (time.time() - _hit[0]) < _SCAN_TTL_SECONDS:
            return _hit[1]

    months = set()

    # Scan formatted output directory
    if source in ("all", "formatted") and READY_FOR_ANALYSIS.exists():
        for csm_dir in READY_FOR_ANALYSIS.iterdir():
            if csm_dir.is_dir() and (not csm or csm_dir.name.lower().startswith(csm.lower())):
                for month_dir in csm_dir.iterdir():
                    if month_dir.is_dir() and "." in month_dir.name:
                        months.add(month_dir.name)

    if source == "all" and COMPLETED_INTELLIGENCE.exists():
        for csm_dir in COMPLETED_INTELLIGENCE.iterdir():
            if csm_dir.is_dir() and (not csm or csm_dir.name.lower().startswith(csm.lower())):
                for month_dir in csm_dir.iterdir():
                    if month_dir.is_dir() and "." in month_dir.name:
                        months.add(month_dir.name)

    # Scan raw CSM source folders (where ZIPs come from)
    if source in ("all", "raw"):
        cfg = load_ars_config()
        csm_sources = cfg.get("csm_sources", {}).get("sources", {})
        for csm_name, csm_path in csm_sources.items():
            if csm and not csm_name.lower().startswith(csm.lower()):
                continue
            src = Path(csm_path)
            if src.exists():
                for month_dir in src.iterdir():
                    if month_dir.is_dir() and "." in month_dir.name:
                        months.add(month_dir.name)

    # Cap to most recent 6 months
    sorted_months = sorted(months, reverse=True)
    result = sorted_months[:6] or [datetime.now().strftime("%Y.%m")]
    _SCAN_CACHE[cache_key] = (time.time(), result)
    return result


@app.get("/api/files/{csm}/{month}/{client_id}")
async def check_files(csm: str, month: str, client_id: str):
    """Check which data files are available for a client."""
    odd = find_formatted_odd(csm, month, client_id)
    txns = _find_transaction_files(csm, month, client_id)
    intelligence_files = _list_intelligence_files(csm, month, client_id)
    return {
        "odd": {"status": "ready" if odd else "missing", "path": odd},
        "transactions": {
            "status": "ready" if txns else "missing",
            "count": len(txns),
            "paths": [str(p) for p in txns],
        },
        "intelligence": {
            "status": "ready" if intelligence_files else "missing",
            "count": len(intelligence_files),
            "output_dir": str(_intelligence_output_dir(csm, month, client_id)),
        },
    }


@app.get("/api/recent")
async def get_recent():
    return get_recent_runs()


@app.get("/api/stats")
async def get_stats():
    """Dashboard KPIs with richer data."""
    config = load_clients_config()
    recent = get_recent_runs()

    completed_clients = set()
    if COMPLETED_ANALYSIS.exists():
        for csm_dir in COMPLETED_ANALYSIS.iterdir():
            if csm_dir.is_dir():
                for month_dir in csm_dir.iterdir():
                    if month_dir.is_dir():
                        for client_dir in month_dir.iterdir():
                            if client_dir.is_dir():
                                completed_clients.add(client_dir.name)

    pptx_count = 0
    if PRESENTATIONS_BASE.exists():
        for f in PRESENTATIONS_BASE.rglob("*.pptx"):
            if "_SAMPLER" not in f.name:
                pptx_count += 1

    # Calculate avg run time from recent runs
    avg_time = "--"
    durations = [r["duration"] for r in recent if r.get("duration", "--") != "--"]
    if durations:
        import re
        total_secs = 0
        for d in durations:
            m = re.match(r"(\d+)m\s*(\d+)s", d)
            if m:
                total_secs += int(m.group(1)) * 60 + int(m.group(2))
        if total_secs and durations:
            avg_secs = total_secs // len(durations)
            avg_time = f"{avg_secs // 60}m {avg_secs % 60}s"

    # Success rate
    success_count = sum(1 for r in recent if r.get("status") == "complete")
    success_rate = f"{round(success_count / len(recent) * 100)}%" if recent else "--"

    # Reports by CSM
    csm_counts = {}
    if PRESENTATIONS_BASE.exists():
        for csm_dir in PRESENTATIONS_BASE.iterdir():
            if csm_dir.is_dir() and not csm_dir.name.startswith("."):
                count = sum(1 for _ in csm_dir.rglob("*.pptx") if "_SAMPLER" not in _.name)
                if count > 0:
                    csm_counts[csm_dir.name] = count

    return {
        "total_clients": len(config),
        "completed_clients": len(completed_clients),
        "reports_generated": pptx_count,
        "recent_runs": len(recent),
        "avg_time": avg_time,
        "success_rate": success_rate,
        "csm_counts": csm_counts,
    }


@app.get("/api/results/clients")
async def get_results_clients():
    """Return clients that have completed analysis results (for Results tab dropdown)."""
    clients = []
    if COMPLETED_ANALYSIS.exists():
        for csm_dir in sorted(COMPLETED_ANALYSIS.iterdir()):
            if not csm_dir.is_dir():
                continue
            for month_dir in sorted(csm_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue
                for client_dir in sorted(month_dir.iterdir()):
                    if not client_dir.is_dir():
                        continue
                    chart_count = sum(1 for _ in client_dir.rglob("*.png"))
                    if chart_count > 0:
                        clients.append({
                            "client_id": client_dir.name,
                            "csm": csm_dir.name,
                            "month": month_dir.name,
                            "charts": chart_count,
                            "label": f"{client_dir.name} -- {csm_dir.name} / {month_dir.name} ({chart_count} charts)",
                        })
    return clients


# ─── SHARED RUN ORCHESTRATION ─────────────────────────────────────────
# Every subprocess the UI launches goes through these two helpers. The
# Generate button, the format-only button, and the scheduler previously
# carried three hand-copied variants of this logic that had drifted apart
# (the scheduler lost the ODD hand-off, env forwarding, and staleness
# tracking) -- a scheduled run silently was not the same operation as a
# clicked run.


def _stream_subprocess(run_id: str, cmd: list, cwd, *, step_prefix: str = "",
                       progress_per_line: int = 0, track_output: bool = False) -> int:
    """Spawn ``cmd``, stream its merged output into ``runs[run_id]``, return
    the exit code.

    The environment is an explicit copy of the parent's so SLIDE_MODE and
    SLIDE_BUDGET deck-size controls always reach the child, with
    PYTHONUNBUFFERED as belt+braces alongside ``-u``.
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        bufsize=1,
        cwd=str(cwd),
        env=env,
        **_popen_tree_kwargs(),
    )
    _register_proc(run_id, proc)
    if track_output and run_id in runs:
        runs[run_id]["last_output_at"] = datetime.now().isoformat()
    for line in proc.stdout:
        line = line.rstrip()
        if run_id not in runs:
            continue
        runs[run_id]["log"].append(line)
        runs[run_id]["current_step"] = f"{step_prefix}{line.strip()}"
        if track_output:
            runs[run_id]["last_output_at"] = datetime.now().isoformat()
        if progress_per_line:
            runs[run_id]["progress"] = min(95, len(runs[run_id]["log"]) * progress_per_line)
    proc.wait()
    return proc.returncode


def _run_full_pipeline(run_id: str, csm: str, month: str, client_id: str,
                       product: str, *, module: str = "", module_list=(),
                       local_copy: str = "", source: str = "",
                       format_extras=(), always_format: bool = False) -> None:
    """Format (if needed) then analyze -- the one pipeline body behind both
    the Generate button and the scheduler. Runs on a worker thread.

    ``always_format`` re-formats even when a formatted ODD already exists
    (scheduled runs always want the freshest data). ``format_extras`` are
    extra formatting flags such as ``--with-trans`` / ``--with-all``.
    """
    formatting_run = ARS_BASE / "00_Formatting" / "run.py"
    analysis_run = ARS_BASE / "01_Analysis" / "run.py"
    _keep_system_awake()
    try:
        odd_file = find_formatted_odd(csm, month, client_id)
        # With an explicit source path (#229) we always (re)format from that
        # file; otherwise we only format when no formatted ODD exists yet.
        need_format = always_format or bool(source) or not odd_file
        if need_format and formatting_run.exists():
            runs[run_id]["current_step"] = "Step 1: Formatting ODD file..."
            runs[run_id]["log"].append("=" * 60)
            runs[run_id]["log"].append("  STEP 1: Formatting ODD file")
            if source:
                runs[run_id]["log"].append(f"  Source: {source}")
            runs[run_id]["log"].append("=" * 60)

            fmt_cmd = [sys.executable, "-u", str(formatting_run),
                       "--month", month, "--csm", csm, "--client", client_id]
            fmt_cmd += list(format_extras)
            if source:
                fmt_cmd += ["--source-file", source, "--force"]

            rc = _stream_subprocess(run_id, fmt_cmd, formatting_run.parent,
                                    step_prefix="Formatting: ")
            if rc != 0:
                runs[run_id]["log"].append("  Formatting failed!")
            else:
                runs[run_id]["log"].append("  Formatting complete.")
                odd_file = find_formatted_odd(csm, month, client_id)

            runs[run_id]["log"].append("")

        if not odd_file:
            # Suppress the error verdict/log if the operator already stopped it.
            if runs.get(run_id, {}).get("status") == "running":
                runs[run_id]["log"].append("ERROR: No formatted ODD file found after formatting.")
                runs[run_id]["log"].append(f"Check: {READY_FOR_ANALYSIS / csm / month / client_id}")
                _mark_terminal(run_id, "error")
            return

        product_label = {"ars": "ARS", "txn": "TXN", "combined": "ARS + TXN"}.get(product, "ARS")
        runs[run_id]["current_step"] = f"Step 2: Running {product_label} analysis..."
        runs[run_id]["log"].append("=" * 60)
        runs[run_id]["log"].append(f"  STEP 2: Running {product_label} Analysis")
        runs[run_id]["log"].append("=" * 60)

        cmd = [sys.executable, "-u", str(analysis_run),
               "--month", month, "--csm", csm, "--client", client_id,
               "--product", product]
        if module_list:
            # Batch closed loop: aggregate ONCE, a scoped deck per section.
            # --sections overrides --product (run.py).
            cmd += ["--sections", ",".join(module_list)]
        elif module:
            # Closed-loop single-section run; --section overrides --product.
            cmd += ["--section", module]
        if local_copy:
            cmd += ["--local-copy", local_copy]
        # Hand the analysis step the exact ODD we already located, so it
        # doesn't re-discover it with a separate finder that can drift out
        # of sync (#231: app found it, analysis's stricter finder didn't).
        cmd.append(str(odd_file))

        rc = _stream_subprocess(run_id, cmd, analysis_run.parent,
                                progress_per_line=2, track_output=True)
        _mark_terminal(run_id, "complete" if rc == 0 else "error",
                       progress=100 if rc == 0 else None)
    except Exception as e:
        if run_id in runs:
            runs[run_id]["log"].append(f"ERROR: {e}")
        _mark_terminal(run_id, "error")


@app.post("/api/format")
async def start_format(
    csm: str,
    month: str,
    client_id: str = "",
    force: bool = False,
    source_path: str = "",
):
    """Start a formatting run.

    With source_path (#229), format an explicit file/folder for a CSM whose raw
    dump folder isn't reachable -- bypasses the ZIP auto-scan. Requires client_id.
    """
    run_id = f"fmt_{client_id or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    formatting_run = ARS_BASE / "00_Formatting" / "run.py"
    if not formatting_run.exists():
        raise HTTPException(status_code=500, detail=f"Formatting run.py not found at {formatting_run}")

    # Validate an explicit source path up front so we fail fast (#229).
    source_resolved = ""
    if source_path.strip():
        sp = Path(os.path.expandvars(os.path.expanduser(source_path.strip())))
        if not sp.exists():
            raise HTTPException(status_code=400, detail=f"Source path does not exist: {sp}")
        if not client_id:
            raise HTTPException(status_code=400, detail="A client ID is required when formatting from a source path.")
        source_resolved = str(sp)

    # Refuse a duplicate formatting run for the same target while one is going (#232).
    _reject_if_run_active(csm, month, client_id or "all", "formatting")

    runs[run_id] = {
        "status": "running",
        "client_id": client_id or "all",
        "csm": csm,
        "month": month,
        "product": "formatting",
        "started": datetime.now().isoformat(),
        "progress": 0,
        "current_step": "Starting formatting...",
        "log": [],
    }

    def _run():
        _keep_system_awake()
        try:
            cmd = [sys.executable, "-u", str(formatting_run),
                   "--month", month, "--csm", csm, "--with-trans"]
            if client_id:
                cmd.extend(["--client", client_id])
            if source_resolved:
                # --source-file mode formats this exact file (forces internally).
                cmd.extend(["--source-file", source_resolved])
            if force:
                cmd.append("--force")

            rc = _stream_subprocess(run_id, cmd, formatting_run.parent,
                                    progress_per_line=3)
            _mark_terminal(run_id, "complete" if rc == 0 else "error",
                           progress=100 if rc == 0 else None)
        except Exception as e:
            if run_id in runs:
                runs[run_id]["log"].append(f"ERROR: {e}")
            _mark_terminal(run_id, "error")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"run_id": run_id}


@app.post("/api/run")
async def start_run(
    csm: str,
    month: str,
    client_id: str,
    product: str = "ars",
    module: str = "",
    modules: str = "",
    local_copy_path: str = "",
    source_path: str = "",
):
    """Start a full pipeline run: format (if needed) + analysis + PPTX.

    ``module`` (a section id like "txn.merchant"), when set, runs the closed-loop
    single-section path instead of the whole product -- format-if-needed, just
    that section's analysis, and a scoped one-section deck.

    Optional local_copy_path: when provided, the final PPTX deck is also
    copied to this folder on the operator's machine so they don't have to
    download a large file from the shared M: drive. Validated to be a
    writable directory before the (long) run starts.
    """
    module_list = [m.strip() for m in modules.split(",") if m.strip()] if modules else []
    if module or module_list:
        # Fail fast on an unknown module rather than ~20 min in when run.py's
        # section registry rejects it.
        known = {m["section_id"] for m in _list_sections()}
        for _m in ([module] if module else []) + module_list:
            if _m not in known:
                raise HTTPException(status_code=400, detail=f"Unknown module: {_m!r}")
    elif product not in SUPPORTED_PRODUCTS:
        # Fail fast on an unsupported product (e.g. the Deposits 'dep' card,
        # which has no analysis backend). Without this the run launches and
        # only dies ~20 min in when run.py's argparse rejects --product dep.
        raise HTTPException(
            status_code=400,
            detail=(
                f"Product '{product}' is not available yet. "
                f"Choose one of: {', '.join(sorted(SUPPORTED_PRODUCTS))}."
            ),
        )

    run_id = f"{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    analysis_run = ARS_BASE / "01_Analysis" / "run.py"
    if not analysis_run.exists():
        raise HTTPException(status_code=500, detail=f"Analysis run.py not found at {analysis_run}")

    # Validate local_copy_path up front so we fail fast, not after 20 min.
    local_copy_resolved = ""
    if local_copy_path.strip():
        candidate = Path(os.path.expandvars(os.path.expanduser(local_copy_path.strip())))
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Local copy path is not writable: {candidate} ({exc})",
            )
        if not candidate.is_dir():
            raise HTTPException(status_code=400, detail=f"Local copy path is not a directory: {candidate}")
        local_copy_resolved = str(candidate)

    # Validate an explicit source path up front so we fail fast, not 20 min in (#229).
    source_resolved = ""
    if source_path.strip():
        sp = Path(os.path.expandvars(os.path.expanduser(source_path.strip())))
        if not sp.exists():
            raise HTTPException(status_code=400, detail=f"Source path does not exist: {sp}")
        source_resolved = str(sp)

    # Refuse a duplicate run for the same client while one is still going (#232).
    _reject_if_run_active(csm, month, client_id, product)

    runs[run_id] = {
        "status": "running",
        "client_id": client_id,
        "csm": csm,
        "month": month,
        "product": product,
        "started": datetime.now().isoformat(),
        "progress": 0,
        "current_step": "Starting...",
        "log": [],
    }

    thread = threading.Thread(
        target=_run_full_pipeline,
        args=(run_id, csm, month, client_id, product),
        kwargs=dict(
            module=module,
            module_list=module_list,
            local_copy=local_copy_resolved,
            source=source_resolved,
        ),
        daemon=True,
    )
    thread.start()

    return {"run_id": run_id}


@app.post("/api/intelligence/run")
async def start_intelligence_run(csm: str, month: str, client_id: str):
    """Start the V1 transactional intelligence engine.

    This is intentionally separate from `/api/run`: the engine produces
    reusable intelligence tables, briefs, and export workbooks rather than a
    traditional analysis deck.
    """
    if not csm or not month or not client_id:
        raise HTTPException(status_code=400, detail="CSM, month, and client_id are required.")

    odd = find_formatted_odd(csm, month, client_id)
    txns = _find_transaction_files(csm, month, client_id)
    if not odd and not txns:
        raise HTTPException(
            status_code=400,
            detail=(
                "No supported staged ODD or transaction files were found. "
                "Format the ODD/TXN files first, or place a supported extract in the ready-for-analysis folder."
            ),
        )

    _reject_if_run_active(csm, month, client_id, "intelligence")

    run_id = f"intel_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    runs[run_id] = {
        "status": "running",
        "client_id": client_id,
        "csm": csm,
        "month": month,
        "product": "intelligence",
        "started": datetime.now().isoformat(),
        "progress": 0,
        "current_step": "Starting transactional intelligence...",
        "log": [],
    }

    thread = threading.Thread(
        target=_run_intelligence_engine,
        args=(run_id, csm, month, client_id),
        daemon=True,
    )
    thread.start()
    return {"run_id": run_id}


@app.get("/api/run/{run_id}")
async def get_run_status(run_id: str):
    """Get the status of a running or completed pipeline."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs[run_id]


@app.get("/api/active_runs")
async def get_active_runs():
    """List in-flight runs so a fresh page load can reattach to them.

    A browser refresh mid-run used to lose all run visibility (the run
    continued server-side with nothing showing it). The UI calls this on
    load and offers a "view run" banner for anything still running.
    """
    active = []
    for run_id, run in list(runs.items()):
        if run.get("status") != "running":
            continue
        active.append({
            "run_id": run_id,
            "kind": run.get("product", ""),
            "csm": run.get("csm", ""),
            "client_id": run.get("client_id", ""),
            "month": run.get("month", ""),
            "started": run.get("started", ""),
        })
    return active


@app.get("/api/run/{run_id}/stream")
async def stream_run(run_id: str):
    """Stream run progress as Server-Sent Events."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_stream():
        last_idx = 0
        while True:
            run = runs.get(run_id)
            if not run:
                break

            new_lines = run["log"][last_idx:]
            for line in new_lines:
                yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
            last_idx = len(run["log"])

            yield f"data: {json.dumps({'type': 'progress', 'value': run['progress'], 'step': run['current_step']})}\n\n"

            if run["status"] in ("complete", "error", "stopped"):
                yield f"data: {json.dumps({'type': 'done', 'status': run['status']})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/stop_all")
async def stop_all():
    """Emergency stop: kill every in-progress formatting/analysis run and its
    whole child-process tree, right now.

    Safe to hit at any time -- a no-op if nothing is running. Files already
    written to disk are kept; only the in-flight work is aborted. Each stopped
    run is flipped to the terminal ``stopped`` status so the UI's poll loop
    ends and the buttons re-enable.
    """
    stopped = []
    for run_id, run in list(runs.items()):
        if run.get("status") != "running":
            continue
        _terminate_proc(run_procs.get(run_id))
        run_procs.pop(run_id, None)
        run["status"] = "stopped"
        run["current_step"] = "Stopped by operator"
        run["finished"] = datetime.now().isoformat()
        run["log"].append("")
        run["log"].append("=" * 60)
        run["log"].append("  STOPPED BY OPERATOR (emergency STOP ALL)")
        run["log"].append("=" * 60)
        stopped.append(run_id)
    return {"stopped": len(stopped), "run_ids": stopped}


def _resolve_csm_dir(base_path: Path, csm: str) -> Path:
    """Fuzzy match CSM folder name."""
    direct = base_path / csm
    if direct.exists():
        return direct
    if base_path.exists():
        for d in base_path.iterdir():
            if d.is_dir() and d.name.lower().startswith(csm.lower()):
                return d
    return direct


@app.get("/api/outputs/{csm}/{month}/{client_id}")
async def list_outputs(csm: str, month: str, client_id: str):
    """List output files for a completed run.

    Backwards-compatible: returns a list when called without a flag.
    Wave 4: when callers pass `?with_quality=1`, returns
    `{"files": [...], "quality": {...}}` with scorecard / rates_audit
    paths + counts surfaced to the UI completion card.
    """
    files = []

    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id
    if analysis_dir.exists():
        for f in analysis_dir.iterdir():
            if f.is_file() and f.suffix in (".xlsx", ".json", ".png", ".csv", ".md"):
                files.append({
                    "name": f.name,
                    "type": f.suffix[1:],
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "path": str(f),
                    "category": "analysis",
                })

    pptx_dir = _resolve_csm_dir(PRESENTATIONS_BASE, csm) / month / client_id
    if pptx_dir.exists():
        for f in pptx_dir.iterdir():
            if f.is_file() and f.suffix == ".pptx":
                files.append({
                    "name": f.name,
                    "type": "pptx",
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "path": str(f),
                    "category": "presentation",
                })

    charts_dir = analysis_dir / "charts" if analysis_dir.exists() else None
    if charts_dir and charts_dir.exists():
        for f in charts_dir.iterdir():
            if f.is_file() and f.suffix == ".png":
                files.append({
                    "name": f.name,
                    "type": "png",
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "path": str(f),
                    "category": "chart",
                })

    return files


@app.get("/api/intelligence/outputs/{csm}/{month}/{client_id}")
async def list_intelligence_outputs(csm: str, month: str, client_id: str):
    """List intelligence artifacts plus summary JSON for the operator UI."""
    out_dir = _intelligence_output_dir(csm, month, client_id)
    return {
        "output_dir": str(out_dir),
        "files": _list_intelligence_files(csm, month, client_id),
        "summary": _json_load(out_dir / "run_summary.json", {}),
        "quality": _json_load(out_dir / "data_quality.json", {}),
        "insights": _json_load(out_dir / "insights.json", []),
        "consulting_story": _json_load(out_dir / "consulting_story.json", {}),
        "intake_work_order": _csv_records(out_dir / "intake_work_order.csv", limit=100),
        "file_assembly_plan": _csv_records(out_dir / "file_assembly_plan.csv", limit=100),
        "monthly_file_requirements": _csv_records(out_dir / "monthly_file_requirements.csv", limit=100),
        "layout_gap_report": _csv_records(out_dir / "layout_gap_report.csv", limit=300),
        "layout_contract_draft_queue": _csv_records(out_dir / "layout_contract_draft_queue.csv", limit=100),
        "layout_contract_export_manifest": _csv_records(
            out_dir / "layout_contract_export_manifest.csv",
            limit=100,
        ),
        "intelligence_lineage_graph": _csv_records(out_dir / "intelligence_lineage_graph.csv", limit=500),
        "engine_run_ledger": _csv_records(out_dir / "engine_run_ledger.csv", limit=100),
        "account_intelligence_profile": _csv_records(out_dir / "account_intelligence_profile.csv", limit=300),
        "model_rulebook": _csv_records(out_dir / "model_rulebook.csv", limit=200),
        "account_scoring_trace": _csv_records(out_dir / "account_scoring_trace.csv", limit=300),
        "counterparty_signals": _csv_records(out_dir / "counterparty_signals.csv", limit=200),
        "counterparty_summary": _csv_records(out_dir / "counterparty_summary.csv", limit=50),
        "relationship_segments": _csv_records(out_dir / "relationship_segments.csv", limit=200),
        "segment_summary": _csv_records(out_dir / "segment_summary.csv", limit=50),
        "portfolio": _csv_records(out_dir / "opportunity_portfolio.csv", limit=50),
        "executive_scorecard": _csv_records(out_dir / "executive_scorecard.csv", limit=50),
        "strategy_roadmap": _csv_records(out_dir / "strategy_roadmap.csv", limit=50),
        "action_plan": _csv_records(out_dir / "action_plan.csv", limit=50),
        "role_handoffs": _csv_records(out_dir / "role_handoffs.csv", limit=50),
        "operating_control_plane": _csv_records(out_dir / "operating_control_plane.csv", limit=50),
        "user_interaction_map": _csv_records(out_dir / "user_interaction_map.csv", limit=150),
        "production_readiness_backlog": _csv_records(
            out_dir / "production_readiness_backlog.csv",
            limit=250,
        ),
        "analysis_section_catalog": _csv_records(out_dir / "analysis_section_catalog.csv", limit=100),
        "analysis_script_catalog": _csv_records(out_dir / "analysis_script_catalog.csv", limit=500),
        "analysis_provenance_map": _csv_records(out_dir / "analysis_provenance_map.csv", limit=100),
        "analysis_execution_map": _csv_records(out_dir / "analysis_execution_map.csv", limit=100),
        "analysis_chart_data_snapshot": _csv_records(
            out_dir / "analysis_chart_data_snapshot.csv",
            limit=150,
        ),
        "intelligence_metric_catalog": _csv_records(
            out_dir / "intelligence_metric_catalog.csv",
            limit=200,
        ),
        "analysis_feature_derivation_catalog": _csv_records(
            out_dir / "analysis_feature_derivation_catalog.csv",
            limit=300,
        ),
        "analysis_consulting_playbook": _csv_records(
            out_dir / "analysis_consulting_playbook.csv",
            limit=100,
        ),
        "analysis_insight_brief": _csv_records(
            out_dir / "analysis_insight_brief.csv",
            limit=100,
        ),
        "client_meeting_deck_blueprint": _csv_records(
            out_dir / "client_meeting_deck_blueprint.csv",
            limit=150,
        ),
        "analysis_review_board": _csv_records(
            out_dir / "analysis_review_board.csv",
            limit=150,
        ),
        "analysis_package_index": _csv_records(out_dir / "analysis_package_index.csv", limit=100),
        "measurement_plan": _csv_records(out_dir / "measurement_plan.csv", limit=50),
        "campaign_targets": _csv_records(out_dir / "campaign_targets.csv", limit=200),
        "csm_review_queue": _csv_records(out_dir / "csm_review_queue.csv", limit=200),
        "analyst_validation_queue": _csv_records(out_dir / "analyst_validation_queue.csv", limit=200),
        "marketing_activation_export": _csv_records(out_dir / "marketing_activation_export.csv", limit=300),
        "banker_call_list": _csv_records(out_dir / "banker_call_list.csv", limit=200),
        "data_team_load_plan": _csv_records(out_dir / "data_team_load_plan.csv", limit=100),
        "stakeholder_export_manifest": _csv_records(out_dir / "stakeholder_export_manifest.csv", limit=50),
        "measurement_baseline": _csv_records(out_dir / "measurement_baseline.csv", limit=50),
        "outcome_results": _csv_records(out_dir / "outcome_results.csv", limit=200),
        "outcome_summary": _csv_records(out_dir / "outcome_summary.csv", limit=50),
        "intelligence_delta_report": _csv_records(out_dir / "intelligence_delta_report.csv", limit=300),
        "consulting_insight_register": _csv_records(out_dir / "consulting_insight_register.csv", limit=200),
    }


@app.get("/api/run_quality/{csm}/{month}/{client_id}")
async def run_quality(csm: str, month: str, client_id: str):
    """Surface W1 audit + scorecard data for a completed run.

    Returns:
      {
        "scorecard_md": "...",                # full markdown contents of run_scorecard.md
        "scorecard_path": "...",
        "rates_audit_path": "...",
        "rates_audit_rows": [...],            # list of dicts from rates_audit.csv
        "denom_violations": 3,                # count of framework_compliant=False rows
        "anomaly_flags": [{"level":"warn","message":"..."}],
        "manifest_status": "ok"|"partial"|"failed"|"running"|"unknown"
      }

    Wave 4 (CSM experience): the completion card on the Generate tab consumes
    this to render a "Run Quality" panel with verdict + violation count.
    """
    import csv as _csv
    import json as _json

    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id
    out: dict = {
        "scorecard_md": "",
        "scorecard_path": "",
        "rates_audit_path": "",
        "rates_audit_rows": [],
        "denom_violations": 0,
        "anomaly_flags": [],
        "manifest_status": "unknown",
    }
    if not analysis_dir.exists():
        return out

    sc = _newest_artifact(analysis_dir, "run_scorecard*.md")
    if sc:
        out["scorecard_path"] = str(sc)
        try:
            out["scorecard_md"] = sc.read_text(encoding="utf-8")
        except Exception:
            pass

    ra = _newest_artifact(analysis_dir, "rates_audit*.csv")
    if ra:
        out["rates_audit_path"] = str(ra)
        try:
            with open(ra, newline="", encoding="utf-8") as f:
                rows = list(_csv.DictReader(f))
            out["rates_audit_rows"] = rows
            out["denom_violations"] = sum(
                1 for r in rows if str(r.get("framework_compliant", "")).lower() == "false"
            )
        except Exception:
            pass

    mf = _newest_artifact(analysis_dir, "run_manifest*.json")
    if mf:
        try:
            data = _json.loads(mf.read_text(encoding="utf-8"))
            out["manifest_status"] = data.get("status", "unknown")
            # Coarse stage durations (load_data / txn_setup / sections_total /
            # generate_output). Absent on manifests from older runs.
            out["stages"] = data.get("stages", {})
            flags: list = []
            # Run-level flags (deck QA, "0 closed accounts", denominator-law
            # violations) live at the manifest top level; section-scoped flags
            # live under each section. Surface both.
            for f_ in data.get("anomaly_flags", []):
                flags.append({
                    "section": "Run",
                    "level": f_.get("level", "info"),
                    "message": f_.get("message", ""),
                })
            for sec in data.get("sections", []):
                for f_ in sec.get("anomaly_flags", []):
                    flags.append({
                        "section": sec.get("name", ""),
                        "level": f_.get("level", "info"),
                        "message": f_.get("message", ""),
                    })
            out["anomaly_flags"] = flags
        except Exception:
            pass

    return out


@app.get("/api/manifest")
async def get_manifest():
    """Return every row from SLIDE_MANIFEST.xlsx for the UI editor.

    Response shape:
      {
        "path": "/Volumes/M/ARS/SLIDE_MANIFEST.xlsx" | null,
        "rows": [
          {"sheet": "ARS - DCTR", "slide_id": "DCTR-1",
           "title": "...", "decision": "Y"|"A"|"N"|""},
          ...
        ],
        "counts": {"main": 17, "aux": 8, "drop": 3, "blank": 12}
      }

    Wave 4 follow-up: backs the in-UI Deck Shape editor on the Results tab.
    """
    _ensure_scripts_importable()

    from ars_analysis.output.manifest import _resolve_manifest_path, read_manifest_rows

    resolved = _resolve_manifest_path()
    rows = read_manifest_rows()
    counts = {"main": 0, "aux": 0, "drop": 0, "blank": 0}
    for r in rows:
        if r.decision == "Y":
            counts["main"] += 1
        elif r.decision == "A":
            counts["aux"] += 1
        elif r.decision == "N":
            counts["drop"] += 1
        else:
            counts["blank"] += 1
    return {
        "path": str(resolved) if resolved else None,
        "rows": [
            {"sheet": r.sheet, "slide_id": r.slide_id,
             "title": r.title, "decision": r.decision}
            for r in rows
        ],
        "counts": counts,
    }


@app.post("/api/rebuild_deck/{csm}/{month}/{client_id}")
async def post_rebuild_deck(csm: str, month: str, client_id: str):
    """Rebuild the PPTX deck without re-running analysis.

    Reads the persisted run_report.json (which now carries chart_path per
    slide), reconstructs minimal AnalysisResult stubs, applies the current
    SLIDE_MANIFEST.xlsx Keep? decisions, and rewrites the .pptx.

    Wave 4 follow-up. Pairs with the Deck Shape editor: operator toggles
    Y/A/N in the UI, saves to manifest, then clicks Rebuild deck to test
    the new shape without paying for a full re-analysis.
    """
    _ensure_scripts_importable()

    from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
    from ars_analysis.pipeline.steps.generate import rebuild_deck_from_report

    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"No completed analysis at {analysis_dir}")

    pptx_dir = _resolve_csm_dir(PRESENTATIONS_BASE, csm) / month / client_id
    pptx_dir.mkdir(parents=True, exist_ok=True)

    client_meta = _client_meta(client_id)
    client = ClientInfo(
        client_id=client_id,
        client_name=client_meta.get("ClientName", client_id),
        month=month,
        assigned_csm=csm,
        eligible_stat_codes=client_meta.get("EligibleStatusCodes", []),
        eligible_prod_codes=client_meta.get("EligibleProductCodes", []),
    )
    paths = OutputPaths.from_dir(analysis_dir)
    paths.pptx_dir = pptx_dir
    ctx = PipelineContext(client=client, paths=paths, product="ars")
    ctx.export_log = []

    try:
        rebuild_deck_from_report(ctx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {exc}") from exc

    return {
        "ok": True,
        "deck_dir": str(pptx_dir),
        "client_name": client.client_name,
        "export_log": ctx.export_log,
    }


@app.post("/api/manifest")
async def post_manifest(updates: dict):
    """Persist Keep? decisions back to SLIDE_MANIFEST.xlsx.

    Request body: {"updates": {"DCTR-1": "Y", "A7.6a": "A", "A12.Foo": "N"}}
    Returns: {"updated": <count>, "path": "..."}
    """
    _ensure_scripts_importable()

    from ars_analysis.output.manifest import _resolve_manifest_path, write_manifest_decisions

    payload = (updates or {}).get("updates") or {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="`updates` must be an object {slide_id: decision}")
    n = write_manifest_decisions(payload)
    resolved = _resolve_manifest_path()
    return {"updated": n, "path": str(resolved) if resolved else None}


@app.get("/api/curate/{csm}/{month}/{client_id}")
async def get_curate(csm: str, month: str, client_id: str):
    """Per-run curation view: every slide from run_report.json, grouped by
    section, joined with the current SLIDE_MANIFEST Keep? decisions and a
    chart thumbnail URL.

    Backs the visual Curate panel: the operator triages a 150-slide run by
    looking at the charts, not by matching slide IDs to PowerPoint pages.

    Response shape:
      {
        "client_id": "...", "month": "...", "csm": "...",
        "manifest_path": "..." | null,
        "total_slides": 150, "missing_from_manifest": 12,
        "counts": {"main": 30, "aux": 80, "drop": 28, "blank": 12},
        "sections": [
          {"name": "TXN - Competition", "slides": [
            {"slide_id": "TXN-COMP-01", "title": "...", "decision": "Y",
             "in_manifest": true, "thumb_url": "/api/download?path=...",
             "has_chart": true, "error": ""},
          ]},
        ]
      }
    """
    from urllib.parse import quote

    _ensure_scripts_importable()
    from ars_analysis.output.manifest import (
        _resolve_manifest_path,
        read_manifest_rows,
        sheet_for_slide,
    )

    payload = load_run_report(csm, month, client_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="Run report not found -- re-run analysis to regenerate.",
        )
    raw_slides = payload.get("slides") or []
    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id

    decisions = {r.slide_id: r.decision for r in read_manifest_rows()}

    sections: dict[str, list] = {}
    order: list[str] = []
    counts = {"main": 0, "aux": 0, "drop": 0, "blank": 0}
    missing = 0
    for s in raw_slides:
        sid = s.get("slide_id", "") or ""
        chart = s.get("chart_path") or ""
        cp = Path(chart) if chart and Path(chart).exists() else None
        if cp is None and s.get("has_chart"):
            # Pre-chart_path run reports: glob charts/ for the slide_id token
            sid_token = sid.lower().replace("-", "_").replace(".", "_")
            if sid_token:
                for cand in (analysis_dir / "charts").glob("*.png"):
                    if sid_token in cand.name.lower():
                        cp = cand
                        break
        in_manifest = sid in decisions
        decision = decisions.get(sid, "")
        if not in_manifest:
            missing += 1
        counts[{"Y": "main", "A": "aux", "N": "drop"}.get(decision, "blank")] += 1
        sheet = sheet_for_slide(sid, s.get("module_id", "") or "")
        if sheet not in sections:
            sections[sheet] = []
            order.append(sheet)
        sections[sheet].append({
            "slide_id": sid,
            "title": s.get("title", "") or "",
            "decision": decision,
            "in_manifest": in_manifest,
            "thumb_url": f"/api/download?path={quote(str(cp))}&inline=true" if cp else None,
            "has_chart": cp is not None,
            "error": s.get("error", "") or "",
        })

    resolved = _resolve_manifest_path()
    return {
        "client_id": client_id,
        "month": month,
        "csm": csm,
        "manifest_path": str(resolved) if resolved else None,
        "total_slides": len(raw_slides),
        "missing_from_manifest": missing,
        "counts": counts,
        "sections": [{"name": n, "slides": sections[n]} for n in order],
    }


@app.post("/api/manifest/sync/{csm}/{month}/{client_id}")
async def post_manifest_sync(csm: str, month: str, client_id: str):
    """Append this run's slides to SLIDE_MANIFEST.xlsx if not already listed.

    New slide IDs land on their per-section sheet with a blank Keep? cell
    (= keep, undecided). Existing rows -- and the operator's decisions --
    are never modified. Creates the workbook when none exists yet.
    """
    _ensure_scripts_importable()
    from ars_analysis.output.manifest import ensure_manifest_rows

    payload = load_run_report(csm, month, client_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="Run report not found -- re-run analysis to regenerate.",
        )
    slides = [
        {
            "slide_id": s.get("slide_id", ""),
            "title": s.get("title", ""),
            "module_id": s.get("module_id", ""),
            "slide_type": s.get("slide_type", ""),
        }
        for s in (payload.get("slides") or [])
    ]
    path, added = ensure_manifest_rows(slides)
    return {"path": path, "added": added}
@app.post("/api/preview_html/{csm}/{month}/{client_id}")
async def post_preview_html(csm: str, month: str, client_id: str):
    """Build an HTML preview of a completed run and return its URL.

    Reads run_report.json from the analysis dir, walks every (slide_id,
    chart_path, title) tuple, and renders 02_Presentations/html_review/
    index.html. Charts are embedded as base64 data URIs so the file is
    self-contained -- operator can preview without opening PowerPoint.

    Returns: {"ok": True, "html_path": "...", "url": "/preview/..."}

    Requires W4's run_report.json schema (carries chart_path per slide).
    Pre-W4 runs return 404 with a re-run hint.
    """
    import sys as _sys
    _presentations = str(Path(__file__).resolve().parent.parent / "02_Presentations")
    if _presentations not in _sys.path:
        _sys.path.insert(0, _presentations)

    from html_review.from_run_report import build_html_from_run_report

    # COMPLETED_ANALYSIS is `<ARS_BASE>/01_Analysis/01_Completed_Analysis`,
    # PRESENTATIONS_BASE is `<ARS_BASE>/02_Presentations`. The helper takes
    # the per-stage *parents* (the level above the per-CSM folder) so it can
    # resolve `<root>/<csm>/<month>/<client_id>` consistently.
    analysis_root = COMPLETED_ANALYSIS
    pres_root = PRESENTATIONS_BASE

    client_display = _client_meta(client_id).get("ClientName", client_id)

    try:
        html_path = build_html_from_run_report(
            csm=csm, month=month, client_id=client_id,
            completed_analysis_root=analysis_root,
            presentations_root=pres_root,
            embed_images=True,
            client_display_name=client_display,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"HTML preview build failed: {exc}") from exc

    if html_path is None:
        raise HTTPException(
            status_code=404,
            detail="Run report not found -- re-run analysis to regenerate.",
        )

    return {
        "ok": True,
        "html_path": str(html_path),
        "url": f"/preview/{csm}/{month}/{client_id}/",
    }


@app.get("/preview/{csm}/{month}/{client_id}/")
async def get_preview_root(csm: str, month: str, client_id: str):
    """Serve the previously-built html_review/index.html for inline viewing.

    Loadable directly in a new tab or iframe-embedded by the UI. Returns 404
    if the preview hasn't been built yet -- caller should POST /api/preview_html
    first.
    """
    pres_root = PRESENTATIONS_BASE
    target = pres_root / csm / month / client_id / "html_review" / "index.html"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Preview not built; POST /api/preview_html first")
    return FileResponse(target, media_type="text/html")


@app.get("/api/download")
async def download_file(path: str, inline: bool = False):
    """Download an output file. `inline=true` serves it for in-page display
    (Curate panel thumbnails / open-in-tab) instead of as an attachment."""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_path.resolve().relative_to(ARS_BASE.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if inline:
        return FileResponse(file_path)
    return FileResponse(file_path, filename=file_path.name)


_LOG_TAIL_MAX_LINES = 400


@app.get("/api/run_log_tail")
async def run_log_tail(csm: str, month: str, name: str, lines: int = 80):
    """Return the last N lines of a run log for the History tab's in-page
    "View log" panel.

    Security: each path component is rejected if it contains a path
    separator or '..', and the resolved file must live under 04_Logs.
    """
    def _unsafe(part: str) -> bool:
        return (not part.strip()) or "/" in part or "\\" in part or ".." in part

    if _unsafe(csm) or _unsafe(month) or _unsafe(name):
        raise HTTPException(status_code=400, detail="Invalid log reference")
    if not name.endswith(".log"):
        name = f"{name}.log"

    logs_root = LOGS_BASE.resolve()
    target = (LOGS_BASE / csm / month / name).resolve()
    if logs_root not in target.parents:
        raise HTTPException(status_code=403, detail="Access denied")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Log not found")

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read log: {exc}") from exc

    n = max(1, min(lines, _LOG_TAIL_MAX_LINES))
    return {
        "name": name,
        "csm": csm,
        "month": month,
        "lines": text.splitlines()[-n:],
    }


# ─── SCHEDULES ──────────────────────────────────────────────────────

SCHEDULES_FILE = ARS_BASE / "03_Config" / "schedules.json"


def _load_schedules() -> list[dict]:
    if SCHEDULES_FILE.exists():
        return json.loads(SCHEDULES_FILE.read_text(encoding="utf-8"))
    return []


def _save_schedules(schedules: list[dict]):
    SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULES_FILE.write_text(json.dumps(schedules, indent=2), encoding="utf-8")


@app.get("/api/schedules")
async def list_schedules():
    return _load_schedules()


@app.post("/api/schedules")
async def create_schedule(schedule: dict):
    schedules = _load_schedules()
    schedule["id"] = f"sched_{uuid.uuid4().hex[:8]}"
    schedule["enabled"] = True
    schedule["created"] = datetime.now().isoformat()
    schedule["last_run"] = None
    schedules.append(schedule)
    _save_schedules(schedules)
    return schedule


@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    schedules = _load_schedules()
    schedules = [s for s in schedules if s.get("id") != schedule_id]
    _save_schedules(schedules)
    return {"deleted": schedule_id}


@app.post("/api/schedules/{schedule_id}/run")
async def run_schedule_now(schedule_id: str):
    """Manually trigger a scheduled run."""
    schedules = _load_schedules()
    sched = next((s for s in schedules if s.get("id") == schedule_id), None)
    if not sched:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Build the run parameters from the schedule
    month = datetime.now().strftime("%Y.%m")
    product = sched.get("product", "ars")

    run_id = f"{sched['client_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    # Same concurrency guard the manual Generate path uses -- the schedule
    # trigger previously bypassed it entirely and could stack a run on top of
    # an in-progress one for the same client (#232).
    _reject_if_run_active(sched["csm"], month, sched["client_id"], product)

    runs[run_id] = {
        "status": "running",
        "client_id": sched["client_id"],
        "csm": sched["csm"],
        "month": month,
        "product": product,
        "started": datetime.now().isoformat(),
        "progress": 0,
        "current_step": f"Scheduled run: {sched['client_id']}",
        "log": [],
    }

    extras = sched.get("extras", "none")
    format_extras = {"trans": ["--with-trans"], "all": ["--with-all"]}.get(extras, [])

    def _run():
        # Scheduled runs go through the same pipeline body as the Generate
        # button -- same ODD hand-off, env forwarding, and staleness tracking.
        # always_format because a scheduled run wants the freshest data even
        # when a formatted ODD from an earlier run exists.
        _run_full_pipeline(run_id, sched["csm"], month, sched["client_id"],
                           product, format_extras=format_extras,
                           always_format=True)

        # Stamp last_run once the pipeline reaches a terminal state.
        schedules = _load_schedules()
        for s in schedules:
            if s["id"] == schedule_id:
                s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                break
        _save_schedules(schedules)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"run_id": run_id}


if __name__ == "__main__":
    import os as _os
    import socket

    # Auto-pick a free port so a second instance doesn't leave the user
    # staring at the wrong tab wondering why the pipeline isn't moving
    # (the root cause of issue #90 yesterday). Start at 8000, walk up to
    # 8010, then fail with a clear message.
    preferred_port = int(_os.environ.get("ARS_UI_PORT", "8000"))

    def _is_port_free(p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", p)) != 0

    port = preferred_port
    if not _is_port_free(port):
        print(f"\n  NOTE: Port {port} is already in use (another UI instance?).")
        for alt in range(preferred_port + 1, preferred_port + 11):
            if _is_port_free(alt):
                port = alt
                print(f"  Using port {port} instead.")
                break
        else:
            print(f"\n  ERROR: Ports {preferred_port}-{preferred_port + 10} all in use.")
            print(f"  Kill the other process or set ARS_UI_PORT=<n>:")
            print(f"    netstat -ano | findstr :{preferred_port}")
            print(f"    taskkill /PID <pid> /F")
            sys.exit(1)

    # Remind users that SLIDE_MODE gates deck size. Forwarded to the
    # analyze subprocess through the environment.
    slide_mode = _os.environ.get("SLIDE_MODE", "standard")

    print()
    print("=" * 60)
    print("  Velocity Report Pipeline")
    print(f"  ARS Base:    {ARS_BASE} {'[OK]' if ARS_BASE.exists() else '[NOT FOUND]'}")
    print(f"  Config:      {CONFIG_PATH} {'[OK]' if CONFIG_PATH.exists() else '[NOT FOUND]'}")
    print(f"  CSMs:        {get_csm_list() or '[none configured]'}")
    print(f"  index.html:  {Path(__file__).parent / 'index.html'} {'[OK]' if (Path(__file__).parent / 'index.html').exists() else '[NOT FOUND]'}")
    print(f"  SLIDE_MODE:  {slide_mode}  (env SLIDE_MODE=deep|standard|minimal)")
    print(f"  URL:         http://localhost:{port}")
    print(f"  PID:         {_os.getpid()}")
    print("=" * 60)
    print()

    if not ARS_BASE.exists():
        print(f"  WARNING: {ARS_BASE} not found. Is the M: drive mapped?")
        print()

    # Resolve the git code-version stamp OFF the startup path. It shells out to
    # git (incl. `git status`), which on a network checkout can take seconds --
    # and the launcher polls the port, so any blocking here is felt as a slow
    # launch. Compute it in a daemon thread; it prints when ready and warms the
    # lru_cache that /api/version (the UI footer) reads. The port binds now.
    def _print_code_version():
        print(f"  Code:        {get_code_version().get('label', 'unknown')}")

    threading.Thread(target=_print_code_version, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=port)
