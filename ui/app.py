"""Velocity Report Pipeline -- FastAPI Backend

Serves the UI and provides API endpoints for:
- Client list and config
- Module registry
- Pipeline execution with progress streaming
- Results and download serving

Run: python app.py
Then open: http://localhost:8000
"""

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

# Paths (Windows M: drive)
if sys.platform == "win32":
    ARS_BASE = Path(r"M:\ARS")
else:
    ARS_BASE = Path("/Volumes/M/ARS")  # Mac fallback for dev

CONFIG_PATH = ARS_BASE / "03_Config" / "clients_config.json"
FORMATTING_BASE = ARS_BASE / "00_Formatting"
ANALYSIS_BASE = ARS_BASE / "01_Analysis"
PRESENTATIONS_BASE = ARS_BASE / "02_Presentations"
LOGS_BASE = ARS_BASE / "04_Logs"
READY_FOR_ANALYSIS = FORMATTING_BASE / "02-Data-Ready for Analysis"
COMPLETED_ANALYSIS = ANALYSIS_BASE / "01_Completed_Analysis"

# In-memory run tracking
runs = {}

# ─── HELPERS ──────────────────────────────────────────────────────────

def load_clients_config():
    """Load clients_config.json."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def find_formatted_odd(csm, month, client_id):
    """Find the formatted ODD file for a client."""
    client_dir = READY_FOR_ANALYSIS / csm / month / client_id
    if not client_dir.exists():
        # Fuzzy CSM match
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
    """Scan logs directory for recent run info."""
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
                recent.append({
                    "csm": csm_dir.name,
                    "month": month_dir.name,
                    "client_id": parts[0] if parts else "?",
                    "timestamp": log_file.stem,
                    "file": str(log_file),
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

CSM_LIST = ["James Gilmore", "Jordan", "Aaron", "Gregg", "Dan", "Max"]

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
    return CSM_LIST


@app.get("/api/clients")
async def get_clients():
    """Return client list from config."""
    config = load_clients_config()
    clients = []
    for cid, data in config.items():
        clients.append({
            "id": cid,
            "name": data.get("ClientName", data.get("client_name", f"Client {cid}")),
            "config": {
                "ic_rate": data.get("ICRate", ""),
                "nsf_od_fee": data.get("NSF_OD_Fee", ""),
                "stat_codes": data.get("EligibleStatusCodes", []),
                "prod_codes": data.get("EligibleProductCodes", []),
                "dc_indicator": data.get("DCIndicator", ""),
                "reg_e_column": data.get("RegEColumn", ""),
                "reg_e_opt_in": data.get("RegEOptInCode", []),
                "data_start": data.get("DataStartDate", ""),
                "branch_mapping": data.get("BranchMapping", {}),
            },
        })
    return clients


@app.get("/api/products")
async def get_products():
    return PRODUCTS


@app.get("/api/months")
async def get_months():
    """Return available months from the formatted data directory."""
    months = set()
    if READY_FOR_ANALYSIS.exists():
        for csm_dir in READY_FOR_ANALYSIS.iterdir():
            if csm_dir.is_dir():
                for month_dir in csm_dir.iterdir():
                    if month_dir.is_dir() and "." in month_dir.name:
                        months.add(month_dir.name)
    return sorted(months, reverse=True) or [datetime.now().strftime("%Y.%m")]


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


@app.post("/api/run")
async def start_run(
    csm: str,
    month: str,
    client_id: str,
    product: str = "ars",
):
    """Start a pipeline run. Returns a run_id for tracking."""
    run_id = f"{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    # Find the analysis run.py
    analysis_run = ARS_BASE / "01_Analysis" / "run.py"
    if not analysis_run.exists():
        raise HTTPException(status_code=500, detail=f"run.py not found at {analysis_run}")

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
            proc = subprocess.Popen(
                [sys.executable, str(analysis_run),
                 "--month", month, "--csm", csm, "--client", client_id],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for line in proc.stdout:
                line = line.rstrip()
                if run_id in runs:
                    runs[run_id]["log"].append(line)
                    runs[run_id]["current_step"] = line.strip()
                    # Estimate progress from log output
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

            # Send new log lines
            new_lines = run["log"][last_idx:]
            for line in new_lines:
                yield f"data: {json.dumps({'type': 'log', 'message': line})}\n\n"
            last_idx = len(run["log"])

            # Send progress
            yield f"data: {json.dumps({'type': 'progress', 'value': run['progress'], 'step': run['current_step']})}\n\n"

            if run["status"] in ("complete", "error"):
                yield f"data: {json.dumps({'type': 'done', 'status': run['status']})}\n\n"
                break

            await asyncio.sleep(0.5)

    import asyncio
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/outputs/{csm}/{month}/{client_id}")
async def list_outputs(csm: str, month: str, client_id: str):
    """List output files for a completed run."""
    files = []

    # Check completed analysis
    analysis_dir = COMPLETED_ANALYSIS / csm / month / client_id
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

    # Check presentations
    pptx_dir = PRESENTATIONS_BASE / csm / month / client_id
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

    # Check for chart images
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
    # Security: only allow files under ARS_BASE
    try:
        file_path.resolve().relative_to(ARS_BASE.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    return FileResponse(file_path, filename=file_path.name)


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  Velocity Report Pipeline")
    print("  http://localhost:8000")
    print("=" * 60)
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
