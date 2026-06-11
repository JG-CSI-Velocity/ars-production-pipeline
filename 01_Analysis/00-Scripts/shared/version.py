"""Code-version stamp for run artifacts.

Answers "what code produced this deck?" -- the git SHA, branch, and a dirty
flag, resolved once per process. Stamped into run_manifest.json, the deck's
title-slide notes, and the UI footer so a stale work-PC clone is visible at
a glance instead of discovered three sections into a client review.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

# Repo root: shared/version.py -> shared -> 00-Scripts -> 01_Analysis -> root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _git(*args: str) -> str:
    """Run a git command at the repo root. Returns '' on any failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), *args],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


@lru_cache(maxsize=1)
def get_code_version() -> dict:
    """Return {"sha", "branch", "dirty", "label"} for the running checkout.

    Never raises. When git is unavailable (zip deploy, git not installed)
    every field degrades to a safe placeholder and label is "unknown".
    """
    sha = _git("rev-parse", "--short", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = bool(_git("status", "--porcelain"))
    if not sha:
        return {"sha": "", "branch": "", "dirty": False, "label": "unknown"}
    label = f"{sha}{'*' if dirty else ''} ({branch})" if branch else sha
    return {"sha": sha, "branch": branch, "dirty": dirty, "label": label}


def version_label() -> str:
    """One-line stamp, e.g. '9250ebb (main)' -- '*' suffix marks dirty tree."""
    return get_code_version()["label"]
