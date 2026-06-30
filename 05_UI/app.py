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
import json
import os
import re
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

# In-memory run tracking
runs = {}

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
    if "ars_analysis" not in sys.modules:
        import types as _types
        _pkg = _types.ModuleType("ars_analysis")
        _pkg.__path__ = [_scripts]
        sys.modules["ars_analysis"] = _pkg


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
                    "status": status,
                })
                if len(recent) >= 20:
                    return recent
    return recent


# ─── PRODUCT / MODULE REGISTRY ────────────────────────────────────────

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
    "dep": {
        "name": "Deposits Analysis",
        "count": 15,
        "time": "10-20 min",
        "groups": [
            {"name": "Baseline", "count": 4, "desc": "Portfolio deposit metrics, tiers, segmentation.",
             "modules": ["Baseline", "Tiers", "Segmentation", "Cross-check"]},
            {"name": "Campaign Impact", "count": 5, "desc": "Response, cohort DID, segment analysis, deposit lift.",
             "modules": ["Response", "Cohort DID", "Segments", "By Offer", "By Segment"]},
            {"name": "Evidence", "count": 4, "desc": "Distribution, trajectory, growth proof.",
             "modules": ["Distribution", "Trajectory", "Growth Proof", "NU Conversion"]},
            {"name": "Presentation", "count": 2, "desc": "Executive summary and visuals.",
             "modules": ["Summary", "Visuals"]},
        ],
    },
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


@app.get("/api/module_counts")
async def module_counts():
    """Live module/section/script counts from the files actually on disk.

    The product cards previously showed hardcoded copy ('22 modules') that
    silently went stale as analytics cells were added or deleted -- which
    made real pipeline changes look like they hadn't landed."""
    analytics = Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts" / "analytics"
    # Section dirs are stable; cells inside them are what churns.
    txn_sections = [
        "general", "merchant", "mcc_code", "business_accts", "personal_accts",
        "competition", "financial_services", "ics_acquisition", "campaign",
        "branch_txn", "transaction_type", "product", "attrition_txn", "balance",
        "interchange", "rege_overdraft", "payroll", "relationship",
        "segment_evolution", "retention", "engagement", "executive",
    ]
    ars_dirs = ["overview", "dctr", "rege", "attrition", "value", "mailer", "insights", "ics"]

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
    return {
        "odd": {"status": "ready" if odd else "missing", "path": odd},
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

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
                cwd=str(formatting_run.parent),
            )
            for line in proc.stdout:
                line = line.rstrip()
                if run_id in runs:
                    runs[run_id]["log"].append(line)
                    runs[run_id]["current_step"] = line.strip()
                    log_len = len(runs[run_id]["log"])
                    runs[run_id]["progress"] = min(95, log_len * 3)

            proc.wait()
            if run_id in runs:
                runs[run_id]["status"] = "complete" if proc.returncode == 0 else "error"
                runs[run_id]["progress"] = 100 if proc.returncode == 0 else runs[run_id]["progress"]
                runs[run_id]["finished"] = datetime.now().isoformat()
        except Exception as e:
            if run_id in runs:
                runs[run_id]["status"] = "error"
                runs[run_id]["log"].append(f"ERROR: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"run_id": run_id}


@app.post("/api/run")
async def start_run(
    csm: str,
    month: str,
    client_id: str,
    product: str = "ars",
    local_copy_path: str = "",
    source_path: str = "",
):
    """Start a full pipeline run: format (if needed) + analysis + PPTX.

    Optional local_copy_path: when provided, the final PPTX deck is also
    copied to this folder on the operator's machine so they don't have to
    download a large file from the shared M: drive. Validated to be a
    writable directory before the (long) run starts.
    """
    run_id = f"{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    formatting_run = ARS_BASE / "00_Formatting" / "run.py"
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

    def _run():
        try:
            odd_file = find_formatted_odd(csm, month, client_id)
            # With an explicit source path (#229) we always (re)format from that
            # file; otherwise we only format when no formatted ODD exists yet.
            need_format = bool(source_resolved) or not odd_file
            if need_format and formatting_run.exists():
                runs[run_id]["current_step"] = "Step 1: Formatting ODD file..."
                runs[run_id]["log"].append("=" * 60)
                runs[run_id]["log"].append("  STEP 1: Formatting ODD file")
                if source_resolved:
                    runs[run_id]["log"].append(f"  Source: {source_resolved}")
                runs[run_id]["log"].append("=" * 60)

                fmt_cmd = [sys.executable, "-u", str(formatting_run),
                           "--month", month, "--csm", csm, "--client", client_id]
                if source_resolved:
                    fmt_cmd += ["--source-file", source_resolved, "--force"]

                fmt_proc = subprocess.Popen(
                    fmt_cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    bufsize=1,
                    cwd=str(formatting_run.parent),
                )
                for line in fmt_proc.stdout:
                    line = line.rstrip()
                    if run_id in runs:
                        runs[run_id]["log"].append(line)
                        runs[run_id]["current_step"] = f"Formatting: {line.strip()}"
                fmt_proc.wait()

                if fmt_proc.returncode != 0:
                    runs[run_id]["log"].append("  Formatting failed!")
                else:
                    runs[run_id]["log"].append("  Formatting complete.")
                    odd_file = find_formatted_odd(csm, month, client_id)

                runs[run_id]["log"].append("")

            if not odd_file:
                runs[run_id]["status"] = "error"
                runs[run_id]["log"].append("ERROR: No formatted ODD file found after formatting.")
                runs[run_id]["log"].append(f"Check: {READY_FOR_ANALYSIS / csm / month / client_id}")
                return

            product_label = {"ars": "ARS", "txn": "TXN", "combined": "ARS + TXN"}.get(product, "ARS")
            runs[run_id]["current_step"] = f"Step 2: Running {product_label} analysis..."
            runs[run_id]["log"].append("=" * 60)
            runs[run_id]["log"].append(f"  STEP 2: Running {product_label} Analysis")
            runs[run_id]["log"].append("=" * 60)

            cmd = [sys.executable, "-u", str(analysis_run),
                   "--month", month, "--csm", csm, "--client", client_id,
                   "--product", product]
            if local_copy_resolved:
                cmd += ["--local-copy", local_copy_resolved]
            # Hand the analysis step the exact ODD we already located, so it
            # doesn't re-discover it with a separate finder that can drift out
            # of sync (#231: app found it, analysis's stricter finder didn't).
            # odd_file is guaranteed set here -- we returned above otherwise.
            if odd_file:
                cmd.append(str(odd_file))

            # Forward SLIDE_MODE and SLIDE_BUDGET so UI-set deck-size
            # controls reach the analysis subprocess. Without this, the
            # child inherits parent env but ARS_UI_PORT and similar
            # wrapper-only vars can overwrite intended values.
            _run_env = os.environ.copy()
            _run_env["PYTHONUNBUFFERED"] = "1"  # belt+braces with -u
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
                cwd=str(analysis_run.parent),
                env=_run_env,
            )
            runs[run_id]["last_output_at"] = datetime.now().isoformat()
            for line in proc.stdout:
                line = line.rstrip()
                if run_id in runs:
                    runs[run_id]["log"].append(line)
                    runs[run_id]["current_step"] = line.strip()
                    runs[run_id]["last_output_at"] = datetime.now().isoformat()
                    log_len = len(runs[run_id]["log"])
                    runs[run_id]["progress"] = min(95, log_len * 2)

            proc.wait()
            if run_id in runs:
                runs[run_id]["status"] = "complete" if proc.returncode == 0 else "error"
                runs[run_id]["progress"] = 100 if proc.returncode == 0 else runs[run_id]["progress"]
                runs[run_id]["finished"] = datetime.now().isoformat()
        except Exception as e:
            if run_id in runs:
                runs[run_id]["status"] = "error"
                runs[run_id]["log"].append(f"ERROR: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"run_id": run_id}


@app.get("/api/run/{run_id}")
async def get_run_status(run_id: str):
    """Get the status of a running or completed pipeline."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs[run_id]


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

            if run["status"] in ("complete", "error"):
                yield f"data: {json.dumps({'type': 'done', 'status': run['status']})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
            flags: list = []
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
    import sys as _sys
    _scripts = str(Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts")
    if _scripts not in _sys.path:
        _sys.path.insert(0, _scripts)
    if "ars_analysis" not in _sys.modules:
        import types as _types
        _pkg = _types.ModuleType("ars_analysis")
        _pkg.__path__ = [_scripts]
        _sys.modules["ars_analysis"] = _pkg

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
    import sys as _sys
    _scripts = str(Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts")
    if _scripts not in _sys.path:
        _sys.path.insert(0, _scripts)
    if "ars_analysis" not in _sys.modules:
        import types as _types
        _pkg = _types.ModuleType("ars_analysis")
        _pkg.__path__ = [_scripts]
        _sys.modules["ars_analysis"] = _pkg

    from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
    from ars_analysis.pipeline.steps.generate import rebuild_deck_from_report

    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail=f"No completed analysis at {analysis_dir}")

    pptx_dir = _resolve_csm_dir(PRESENTATIONS_BASE, csm) / month / client_id
    pptx_dir.mkdir(parents=True, exist_ok=True)

    clients = load_clients_config().get("clients", {})
    client_meta = clients.get(client_id, {})
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
        "export_log": ctx.export_log,
    }


@app.post("/api/manifest")
async def post_manifest(updates: dict):
    """Persist Keep? decisions back to SLIDE_MANIFEST.xlsx.

    Request body: {"updates": {"DCTR-1": "Y", "A7.6a": "A", "A12.Foo": "N"}}
    Returns: {"updated": <count>, "path": "..."}
    """
    import sys as _sys
    _scripts = str(Path(__file__).resolve().parent.parent / "01_Analysis" / "00-Scripts")
    if _scripts not in _sys.path:
        _sys.path.insert(0, _scripts)
    if "ars_analysis" not in _sys.modules:
        import types as _types
        _pkg = _types.ModuleType("ars_analysis")
        _pkg.__path__ = [_scripts]
        _sys.modules["ars_analysis"] = _pkg

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

    clients = load_clients_config().get("clients", {})
    client_display = clients.get(client_id, {}).get("ClientName", client_id)

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

    # Trigger the run via the existing /api/run logic
    run_id = f"{sched['client_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    analysis_run = ARS_BASE / "01_Analysis" / "run.py"
    formatting_run = ARS_BASE / "00_Formatting" / "run.py"

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

    def _run():
        try:
            # Format first
            if formatting_run.exists():
                fmt_cmd = [sys.executable, "-u", str(formatting_run),
                           "--month", month, "--csm", sched["csm"],
                           "--client", sched["client_id"]]
                extras = sched.get("extras", "none")
                if extras == "trans":
                    fmt_cmd.append("--with-trans")
                elif extras == "all":
                    fmt_cmd.append("--with-all")

                proc = subprocess.Popen(
                    fmt_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                    cwd=str(formatting_run.parent),
                )
                for line in proc.stdout:
                    if run_id in runs:
                        runs[run_id]["log"].append(line.rstrip())
                proc.wait()

            # Run analysis
            cmd = [sys.executable, "-u", str(analysis_run),
                   "--month", month, "--csm", sched["csm"],
                   "--client", sched["client_id"], "--product", product]
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                cwd=str(analysis_run.parent),
            )
            for line in proc.stdout:
                if run_id in runs:
                    runs[run_id]["log"].append(line.rstrip())
                    runs[run_id]["current_step"] = line.strip()
                    runs[run_id]["progress"] = min(95, len(runs[run_id]["log"]) * 2)
            proc.wait()

            if run_id in runs:
                runs[run_id]["status"] = "complete" if proc.returncode == 0 else "error"
                runs[run_id]["progress"] = 100 if proc.returncode == 0 else runs[run_id]["progress"]
                runs[run_id]["finished"] = datetime.now().isoformat()

            # Update schedule last_run
            schedules = _load_schedules()
            for s in schedules:
                if s["id"] == schedule_id:
                    s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    break
            _save_schedules(schedules)

        except Exception as e:
            if run_id in runs:
                runs[run_id]["status"] = "error"
                runs[run_id]["log"].append(f"ERROR: {e}")

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
    print(f"  Code:        {get_code_version().get('label', 'unknown')}")
    print(f"  URL:         http://localhost:{port}")
    print(f"  PID:         {_os.getpid()}")
    print("=" * 60)
    print()

    if not ARS_BASE.exists():
        print(f"  WARNING: {ARS_BASE} not found. Is the M: drive mapped?")
        print()

    uvicorn.run(app, host="0.0.0.0", port=port)
