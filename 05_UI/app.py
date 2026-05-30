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
SECTION_REGISTRY = ARS_BASE / "03_Config" / "section_registry.json"
FORMATTING_BASE = ARS_BASE / "00_Formatting"
ANALYSIS_BASE = ARS_BASE / "01_Analysis"
PRESENTATIONS_BASE = ARS_BASE / "02_Presentations"
LOGS_BASE = ARS_BASE / "04_Logs"
READY_FOR_ANALYSIS = FORMATTING_BASE / "02-Data-Ready for Analysis"
COMPLETED_ANALYSIS = ANALYSIS_BASE / "01_Completed_Analysis"

# In-memory run tracking
runs = {}

# Live subprocess handles per run_id (kept separate from `runs` so the dict
# stays JSON-serializable for /api/run/{run_id}). Populated by _run() once
# the analysis subprocess is launched; cleared when the run finishes.
_run_procs: dict[str, subprocess.Popen] = {}

# In-memory dropdown cache (Phase 17.4). 5-minute TTL on M: drive scans so the
# Generate tab doesn't re-walk the share on every dropdown click.
_api_cache: dict[str, dict] = {}
_API_CACHE_TTL_SEC = 300


def _cached(key: str, fetch_fn):
    """Return cached value if fresh, otherwise call fetch_fn and cache it."""
    now = time.time()
    entry = _api_cache.get(key)
    if entry and (now - entry["ts"]) < _API_CACHE_TTL_SEC:
        return entry["data"]
    data = fetch_fn()
    _api_cache[key] = {"data": data, "ts": now}
    return data


def _invalidate_cache(prefix: str = ""):
    """Drop cache entries matching prefix, or all entries if prefix is empty."""
    if not prefix:
        _api_cache.clear()
        return
    for k in [k for k in _api_cache if k.startswith(prefix)]:
        del _api_cache[k]


# ─── HELPERS ──────────────────────────────────────────────────────────

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


def _fetch_clients_all():
    """Cacheable unfiltered client list (Phase 17.4). Used by Results dropdown."""
    config = load_clients_config()
    return [
        {
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
        }
        for cid, data in config.items()
    ]


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


@app.get("/api/csms")
async def get_csms():
    """Return CSM names from ars_config.json (dynamic, not hardcoded)."""
    return _cached("csms", get_csm_list)


@app.get("/api/sections")
async def get_sections(product: str = "ars"):
    """Return available sections for the given product (Phase 17.1).

    Reads 03_Config/section_registry.json. Returns a list of
    {key, display_name, description, section_number, enabled, product}.

    - product=ars      -> ARS sections only
    - product=txn      -> TXN sections only
    - product=combined -> both
    - registry missing -> []  (UI hides the panel gracefully)
    - status="routed_elsewhere" entries are excluded (no slides to filter on)
    - status="aspirational" entries are excluded today (not wired into
      build_deck grouping yet). They'll surface when the routing lands.
    """
    if not SECTION_REGISTRY.exists():
        return []

    try:
        registry = json.loads(SECTION_REGISTRY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    products_wanted = []
    if product in ("ars", "combined"):
        products_wanted.append("ars")
    if product in ("txn", "combined"):
        products_wanted.append("txn")

    out = []
    for prod_key in products_wanted:
        for key, info in registry.get(prod_key, {}).items():
            if not isinstance(info, dict):
                continue
            status = info.get("status", "active")
            if status != "active":
                continue
            out.append({
                "key": key,
                "display_name": info.get("display_name", key.title()),
                "description": info.get("description", ""),
                "section_number": info.get("section_number", ""),
                "enabled": True,
                "product": prod_key,
            })
    return out


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


@app.post("/api/stage")
async def stage_formatted_odd(
    src_path: str,
    csm: str,
    month: str,
    client_id: str,
):
    """Manually stage pre-formatted ODD files (#124).

    For CSMs whose raw dump folder isn't accessible (Dan, Aaron, etc.),
    the operator can paste a path to already-extracted ODD .xlsx files
    and copy them into the canonical READY_FOR_ANALYSIS layout in one
    click. Skips the 7-step formatting pipeline.

    src_path: file or folder containing one or more .xlsx ODD files.
    Returns: {copied: [...], skipped: [...], dest: "<destination dir>"}.
    """
    src = Path(os.path.expandvars(os.path.expanduser(src_path.strip())))
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"Source path does not exist: {src}")

    if not csm or not month or not client_id:
        raise HTTPException(status_code=400, detail="csm, month, and client_id are all required")

    # Build the destination using the canonical layout. Reuse fuzzy CSM matching
    # so 'James' picks up the 'JamesG' folder if it already exists.
    csm_dir = READY_FOR_ANALYSIS / csm
    if not csm_dir.exists() and READY_FOR_ANALYSIS.exists():
        for d in READY_FOR_ANALYSIS.iterdir():
            if d.is_dir() and d.name.lower().startswith(csm.lower()):
                csm_dir = d
                break
    dest_dir = csm_dir / month / client_id

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not create destination {dest_dir}: {exc}")

    # Gather source files. A single .xlsx file or a folder containing them.
    sources: list[Path] = []
    if src.is_file():
        if src.suffix.lower() == ".xlsx":
            sources = [src]
        else:
            raise HTTPException(status_code=400, detail=f"Source file must be .xlsx, got {src.suffix}")
    else:  # directory
        sources = sorted(src.glob("*.xlsx"))
        if not sources:
            raise HTTPException(status_code=400, detail=f"No .xlsx files found in {src}")

    import shutil
    copied: list[str] = []
    skipped: list[str] = []
    for fp in sources:
        target = dest_dir / fp.name
        if target.exists():
            skipped.append(fp.name)
            continue
        try:
            shutil.copy2(fp, target)
            copied.append(fp.name)
        except (PermissionError, OSError) as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to copy {fp.name} to {target}: {exc}",
            )

    return {
        "copied": copied,
        "skipped": skipped,
        "dest": str(dest_dir),
    }


@app.get("/api/clients")
async def get_clients(csm: str = "", month: str = ""):
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
    # Phase 17.4: only cache the unfiltered fetch. Filtered queries always
    # walk the live folder layout because new ZIPs/dirs can appear mid-session
    # and we want them visible immediately on the Generate-tab dropdown.
    if not csm and not month:
        return _cached("clients_all", _fetch_clients_all)

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

    return clients


@app.get("/api/products")
async def get_products():
    return PRODUCTS


@app.get("/api/months")
async def get_months(csm: str = "", source: str = "all"):
    """Return available months by scanning actual directories.

    source=raw: scan CSM source folders (raw data dumps -- for formatting step)
    source=formatted: scan 02-Data-Ready for Analysis (already formatted -- for analysis step)
    source=all: combine both
    """
    cache_key = f"months_{csm}_{source}"
    cached = _api_cache.get(cache_key)
    if cached and (time.time() - cached["ts"]) < _API_CACHE_TTL_SEC:
        return cached["data"]

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
    _api_cache[cache_key] = {"data": result, "ts": time.time()}
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
):
    """Start a formatting run."""
    run_id = f"fmt_{client_id or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    formatting_run = ARS_BASE / "00_Formatting" / "run.py"
    if not formatting_run.exists():
        raise HTTPException(status_code=500, detail=f"Formatting run.py not found at {formatting_run}")

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
    sections: str = "",
):
    """Start a full pipeline run: format (if needed) + analysis + PPTX.

    Optional local_copy_path: when provided, the final PPTX deck is also
    copied to this folder on the operator's machine so they don't have to
    download a large file from the shared M: drive. Validated to be a
    writable directory before the (long) run starts.

    Optional sections (Phase 17.1): comma-separated section keys (e.g.
    "dctr,rege"). Empty = run every section (default behavior). All analytics
    still execute -- this filter only trims which slides end up in the deck.
    """
    # Drop month/clients caches so any new run shows up immediately in dropdowns.
    _invalidate_cache("months_")
    _invalidate_cache("clients_all")
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
            if not odd_file and formatting_run.exists():
                runs[run_id]["current_step"] = "Step 1: Formatting ODD file..."
                runs[run_id]["log"].append("=" * 60)
                runs[run_id]["log"].append("  STEP 1: Formatting ODD file")
                runs[run_id]["log"].append("=" * 60)

                fmt_proc = subprocess.Popen(
                    [sys.executable, "-u", str(formatting_run),
                     "--month", month, "--csm", csm, "--client", client_id],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    bufsize=1,
                    cwd=str(formatting_run.parent),
                )
                _run_procs[run_id] = fmt_proc  # so /stop can terminate during formatting
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
            if sections.strip():
                cmd += ["--sections", sections.strip()]

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
            _run_procs[run_id] = proc  # so /stop can terminate during analysis
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
            # Run finished -- new outputs are now on disk; drop dropdown caches
            # so the Results tab picks them up next refresh.
            _invalidate_cache("months_")
            _invalidate_cache("clients_all")
        except Exception as e:
            if run_id in runs:
                runs[run_id]["status"] = "error"
                runs[run_id]["log"].append(f"ERROR: {e}")
        finally:
            _run_procs.pop(run_id, None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"run_id": run_id}


# ─── Batch runs (Phase 17.2) ─────────────────────────────────────────
# Each batch is a sequential queue of single-client runs. We deliberately
# serialize on the operator PC because the analysis pipeline is already
# memory-hungry per client; parallel execution would thrash the M: drive
# and Matplotlib. The batch_id is returned immediately; client UI polls
# /api/batch/{id} for per-client status.

batches: dict[str, dict] = {}


@app.post("/api/batch")
async def start_batch(payload: dict):
    """Queue a sequential batch of client runs.

    Body: {"csm": ..., "month": ..., "product": ..., "client_ids": [...],
           "sections": "", "local_copy_path": ""}
    Returns: {"batch_id": "..."}
    """
    csm = (payload.get("csm") or "").strip()
    month = (payload.get("month") or "").strip()
    product = (payload.get("product") or "ars").strip()
    client_ids = payload.get("client_ids") or []
    sections = (payload.get("sections") or "").strip()
    local_copy_path = (payload.get("local_copy_path") or "").strip()

    if not csm or not month or not client_ids:
        raise HTTPException(
            status_code=400,
            detail="csm, month, and client_ids are all required",
        )

    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    batches[batch_id] = {
        "batch_id": batch_id,
        "csm": csm,
        "month": month,
        "product": product,
        "sections": sections,
        "started": datetime.now().isoformat(),
        "finished": None,
        "status": "running",
        "clients": [
            {"client_id": cid, "status": "pending", "run_id": None,
             "started": None, "finished": None}
            for cid in client_ids
        ],
    }

    async def _run_batch():
        for entry in batches[batch_id]["clients"]:
            entry["status"] = "running"
            entry["started"] = datetime.now().isoformat()
            try:
                # Reuse start_run() so the formatting + analysis + cache
                # invalidation logic stays in one place.
                resp = await start_run(
                    csm=csm,
                    month=month,
                    client_id=entry["client_id"],
                    product=product,
                    local_copy_path=local_copy_path,
                    sections=sections,
                )
                entry["run_id"] = resp.get("run_id")
            except HTTPException as exc:
                entry["status"] = "error"
                entry["error"] = exc.detail
                entry["finished"] = datetime.now().isoformat()
                continue
            # Wait for the run to finish before starting the next client.
            run_id = entry["run_id"]
            while run_id in runs and runs[run_id]["status"] == "running":
                await asyncio.sleep(2)
            run = runs.get(run_id) or {}
            entry["status"] = run.get("status", "error")
            entry["finished"] = datetime.now().isoformat()
        batches[batch_id]["finished"] = datetime.now().isoformat()
        any_error = any(c["status"] == "error" for c in batches[batch_id]["clients"])
        batches[batch_id]["status"] = "error" if any_error else "complete"

    asyncio.create_task(_run_batch())
    return {"batch_id": batch_id}


@app.get("/api/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    if batch_id not in batches:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batches[batch_id]


@app.get("/api/batches")
async def list_batches():
    """Return the 20 most recent batches (most recent first)."""
    return sorted(batches.values(), key=lambda b: b.get("started", ""), reverse=True)[:20]


@app.get("/api/run/{run_id}")
async def get_run_status(run_id: str):
    """Get the status of a running or completed pipeline."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs[run_id]


@app.post("/api/run/{run_id}/stop")
async def stop_run(run_id: str):
    """Emergency stop -- terminate the live subprocess for a run.

    Tries SIGTERM first (subprocess.terminate), waits up to 3s, then
    SIGKILL. Marks the run status as 'stopped'. Subsequent log lines
    that arrive after termination (the reader loop drains the pipe) are
    still recorded for diagnostics.
    """
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    if runs[run_id].get("status") != "running":
        return {"run_id": run_id, "result": "not_running", "status": runs[run_id].get("status")}

    proc = _run_procs.get(run_id)
    if proc is None:
        # Run is "running" but no live subprocess (formatting just finished,
        # analysis not yet launched, etc.). Mark stopped so the next branch
        # of _run() can short-circuit.
        runs[run_id]["status"] = "stopped"
        runs[run_id]["log"].append("STOPPED: no live subprocess; marking run as stopped")
        runs[run_id]["finished"] = datetime.now().isoformat()
        return {"run_id": run_id, "result": "marked_stopped"}

    runs[run_id]["log"].append("STOPPED: operator clicked Stop. Terminating subprocess...")
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
            result = "terminated"
        except subprocess.TimeoutExpired:
            proc.kill()
            result = "killed"
        runs[run_id]["status"] = "stopped"
        runs[run_id]["finished"] = datetime.now().isoformat()
        runs[run_id]["log"].append(f"STOPPED: subprocess {result}.")
        return {"run_id": run_id, "result": result}
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=500, detail=f"Stop failed: {exc}")


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
    """List output files for a completed run."""
    files = []

    analysis_dir = _resolve_csm_dir(COMPLETED_ANALYSIS, csm) / month / client_id
    if analysis_dir.exists():
        for f in analysis_dir.iterdir():
            if f.is_file() and f.suffix in (".xlsx", ".json", ".png"):
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


@app.get("/api/download")
async def download_file(path: str):
    """Download an output file."""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        file_path.resolve().relative_to(ARS_BASE.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
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


# ─── Overnight format sweep (Phase 19) ───────────────────────────────

OVERNIGHT_WHITELIST = ARS_BASE / "03_Config" / "overnight_whitelist.json"
SWEEP_HISTORY_DIR = LOGS_BASE / "overnight"


def _load_overnight_whitelist() -> list[str]:
    if not OVERNIGHT_WHITELIST.exists():
        return []
    try:
        data = json.loads(OVERNIGHT_WHITELIST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("enabled_csms", []))


@app.post("/api/format-sweep")
async def format_sweep():
    """Phase 19 -- Task Scheduler hook.

    Scans each opt-in CSM's source folder for *_ODDD.zip files, kicks off
    00_Formatting/run.py for each client that isn't already in
    02-Data-Ready for Analysis, and records the result to
    04_Logs/overnight/{date}.json. Returns the same JSON in the response.
    """
    enabled_csms = _load_overnight_whitelist()
    if not enabled_csms:
        return {
            "started": datetime.now().isoformat(),
            "skipped_reason": "no CSMs in overnight_whitelist.json",
            "csms": [],
        }

    cfg = load_ars_config()
    sources = cfg.get("csm_sources", {}).get("sources", {})
    formatting_run = ARS_BASE / "00_Formatting" / "run.py"
    started = datetime.now()
    summary = {
        "started": started.isoformat(),
        "finished": None,
        "csms": [],
    }

    for csm in enabled_csms:
        src = None
        for name, path in sources.items():
            if name.lower().startswith(csm.lower()):
                src = Path(path)
                break
        if not src or not src.exists():
            summary["csms"].append({
                "csm": csm, "status": "skipped",
                "reason": f"source folder missing for {csm}",
            })
            continue

        csm_report = {"csm": csm, "status": "ok", "formatted": [], "skipped": []}
        # For each month folder under the CSM source, look at the ZIPs.
        for month_dir in src.iterdir():
            if not month_dir.is_dir() or "." not in month_dir.name:
                continue
            month = month_dir.name
            for zf in month_dir.iterdir():
                m = _ODDD_CLIENT_ID_RE.match(zf.name)
                if not m:
                    continue
                client_id = m.group(1)
                already = find_formatted_odd(csm, month, client_id)
                if already:
                    csm_report["skipped"].append({
                        "client_id": client_id, "month": month, "reason": "already formatted",
                    })
                    continue
                if not formatting_run.exists():
                    csm_report["status"] = "error"
                    csm_report["reason"] = "formatting/run.py not found"
                    break
                try:
                    proc = subprocess.run(
                        [sys.executable, "-u", str(formatting_run),
                         "--month", month, "--csm", csm, "--client", client_id],
                        cwd=str(formatting_run.parent),
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace",
                        timeout=600,
                    )
                    csm_report["formatted"].append({
                        "client_id": client_id, "month": month,
                        "returncode": proc.returncode,
                    })
                except subprocess.TimeoutExpired:
                    csm_report["formatted"].append({
                        "client_id": client_id, "month": month, "error": "timeout (>10min)",
                    })
                except (OSError, subprocess.SubprocessError) as exc:
                    csm_report["formatted"].append({
                        "client_id": client_id, "month": month, "error": str(exc),
                    })
        summary["csms"].append(csm_report)

    summary["finished"] = datetime.now().isoformat()

    # Persist to 04_Logs/overnight/{date}.json
    try:
        SWEEP_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        out = SWEEP_HISTORY_DIR / f"{started.strftime('%Y-%m-%d')}.json"
        out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except (OSError, PermissionError) as exc:
        summary["history_write_error"] = str(exc)

    # New ZIPs likely landed -- bust the dropdown caches.
    _invalidate_cache("months_")
    _invalidate_cache("clients_all")
    return summary


@app.get("/api/format-sweep/history")
async def format_sweep_history():
    """Return the last 10 overnight sweep summaries."""
    if not SWEEP_HISTORY_DIR.exists():
        return []
    files = sorted(SWEEP_HISTORY_DIR.glob("*.json"), reverse=True)[:10]
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


@app.get("/api/overnight-whitelist")
async def get_overnight_whitelist():
    return {"enabled_csms": _load_overnight_whitelist()}


@app.post("/api/schedules/run-due")
async def run_due_schedules():
    """Phase 17.3 -- Task Scheduler hook.

    Invoked by Windows Task Scheduler daily. Fires every enabled schedule
    whose `day` field matches today, then records the result. Idempotent
    within a single calendar day: a schedule already fired today is skipped.

    See docs/deck/task-scheduler-setup.md for the Task Scheduler config.
    """
    schedules = _load_schedules()
    today = datetime.now()
    today_iso_date = today.strftime("%Y-%m-%d")
    fired: list[dict] = []
    skipped: list[dict] = []

    for sched in schedules:
        if not sched.get("enabled", True):
            skipped.append({"id": sched.get("id"), "reason": "disabled"})
            continue
        if int(sched.get("day", 0)) != today.day:
            skipped.append({"id": sched.get("id"), "reason": f"day {sched.get('day')} != today {today.day}"})
            continue
        last_run = (sched.get("last_run") or "")[:10]
        if last_run == today_iso_date:
            skipped.append({"id": sched.get("id"), "reason": "already fired today"})
            continue
        try:
            result = await run_schedule_now(sched["id"])
            fired.append({"id": sched["id"], "run_id": result.get("run_id")})
        except HTTPException as exc:
            fired.append({"id": sched["id"], "error": exc.detail})

    return {
        "fired": fired,
        "skipped": skipped,
        "today": today_iso_date,
    }


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

    uvicorn.run(app, host="0.0.0.0", port=port)
