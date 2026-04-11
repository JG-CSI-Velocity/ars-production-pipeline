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
FORMATTING_BASE = ARS_BASE / "00_Formatting"
ANALYSIS_BASE = ARS_BASE / "01_Analysis"
PRESENTATIONS_BASE = ARS_BASE / "02_Presentations"
LOGS_BASE = ARS_BASE / "04_Logs"
READY_FOR_ANALYSIS = FORMATTING_BASE / "02-Data-Ready for Analysis"
COMPLETED_ANALYSIS = ANALYSIS_BASE / "01_Completed_Analysis"

# In-memory run tracking
runs = {}


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


def find_formatted_odd(csm, month, client_id):
    """Find the formatted ODD file for a client."""
    client_dir = READY_FOR_ANALYSIS / csm / month / client_id
    if not client_dir.exists():
        if READY_FOR_ANALYSIS.exists():
            for d in READY_FOR_ANALYSIS.iterdir():
                if d.is_dir() and d.name.lower().startswith(csm.lower()):
                    client_dir = d / month / client_id
                    break
    if not client_dir.exists():
        return None
    xlsx = list(client_dir.glob("*.xlsx"))
    return str(xlsx[0]) if xlsx else None


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
    return get_csm_list()


@app.get("/api/clients")
async def get_clients():
    """Return client list from config."""
    config = load_clients_config()
    clients = []
    for cid, data in config.items():
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
    return sorted_months[:6] or [datetime.now().strftime("%Y.%m")]


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
                   "--month", month, "--csm", csm]
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
):
    """Start a full pipeline run: format (if needed) + analysis + PPTX."""
    run_id = f"{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    formatting_run = ARS_BASE / "00_Formatting" / "run.py"
    analysis_run = ARS_BASE / "01_Analysis" / "run.py"

    if not analysis_run.exists():
        raise HTTPException(status_code=500, detail=f"Analysis run.py not found at {analysis_run}")

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
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                bufsize=1,
                cwd=str(analysis_run.parent),
            )
            for line in proc.stdout:
                line = line.rstrip()
                if run_id in runs:
                    runs[run_id]["log"].append(line)
                    runs[run_id]["current_step"] = line.strip()
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


if __name__ == "__main__":
    import socket

    port = 8000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            print(f"\n  ERROR: Port {port} is already in use.")
            print(f"  Kill the other process or use a different port:")
            print(f"    netstat -ano | findstr :{port}")
            print(f"    taskkill /PID <pid> /F")
            sys.exit(1)

    print()
    print("=" * 60)
    print("  Velocity Report Pipeline")
    print(f"  ARS Base:    {ARS_BASE} {'[OK]' if ARS_BASE.exists() else '[NOT FOUND]'}")
    print(f"  Config:      {CONFIG_PATH} {'[OK]' if CONFIG_PATH.exists() else '[NOT FOUND]'}")
    print(f"  CSMs:        {get_csm_list() or '[none configured]'}")
    print(f"  index.html:  {Path(__file__).parent / 'index.html'} {'[OK]' if (Path(__file__).parent / 'index.html').exists() else '[NOT FOUND]'}")
    print(f"  http://localhost:{port}")
    print("=" * 60)
    print()

    if not ARS_BASE.exists():
        print(f"  WARNING: {ARS_BASE} not found. Is the M: drive mapped?")
        print()

    uvicorn.run(app, host="0.0.0.0", port=port)
