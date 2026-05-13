"""Turn an Exception into structured manifest fields."""
from __future__ import annotations

import re
import traceback
from dataclasses import dataclass
from types import TracebackType
from typing import Iterable


@dataclass
class _FrameInfo:
    filename: str
    lineno: int


def _pick_deepest_marker_frame(frames: Iterable[_FrameInfo], project_marker: str) -> _FrameInfo | None:
    """Walk frames from outermost to innermost; return the LAST frame whose
    filename contains project_marker."""
    found: _FrameInfo | None = None
    for f in frames:
        if project_marker in f.filename:
            found = f
    return found


def deepest_project_frame(tb: TracebackType | None, project_marker: str = "analytics") -> _FrameInfo | None:
    """Extract the deepest traceback frame inside the project (filtering library internals)."""
    if tb is None:
        return None
    extracted = traceback.extract_tb(tb)
    frames = [_FrameInfo(filename=f.filename, lineno=f.lineno) for f in extracted]
    return _pick_deepest_marker_frame(frames, project_marker)


_FIX_RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "IndexError",
        re.compile(r"out.of.bounds|out of bounds", re.IGNORECASE),
        "Empty group or series. Add a `len() > 0` (or `not df.empty`) guard before `iloc[0]`.",
    ),
    (
        "KeyError",
        re.compile(r".*"),
        "Column or dict key not found. Check the upstream cell that's supposed to produce this field, and verify the column rename didn't happen in standardize_merchant_name.",
    ),
    (
        "MemoryError",
        re.compile(r"unable to allocate|cannot allocate", re.IGNORECASE),
        "Likely a cross-join or unbounded groupby. Check `competitor_match` (or other groupby key) cardinality; if it's in the millions, an upstream consolidation step probably failed.",
    ),
    (
        "NameError",
        re.compile(r"is not defined", re.IGNORECASE),
        "An upstream script in this section failed and never defined this variable. Look at the earliest failure in this section's manifest scripts list.",
    ),
    (
        "FileNotFoundError",
        re.compile(r".*"),
        "Path missing. If it looks like a dev-only path (/tmp, /private/tmp), remove the hardcoded reference; if it's a real input, check that the formatting step produced it.",
    ),
    (
        "ParserError",
        re.compile(r"expected.*fields|tokenizing data", re.IGNORECASE),
        "CSV delimiter mismatch. Verify the file is comma vs tab delimited; the loader auto-retries but only if the first try raises ParserError, not on a silent 1-column parse.",
    ),
]


def suggest_fix(error_class: str, error_msg: str) -> str:
    """Map (error_class, message) to a short suggested-fix string. Empty if no match."""
    for cls, pattern, suggestion in _FIX_RULES:
        if cls == error_class and pattern.search(error_msg or ""):
            return suggestion
    return ""


def _format_issue_body(
    *, error_class: str, error_msg: str, error_file: str, error_line: int,
    traceback_tail: str, suggested_fix: str,
    section_name: str, script_name: str,
    client_id: str, month: str,
) -> str:
    suggestion_block = f"**Suggested fix:** {suggested_fix}\n\n" if suggested_fix else ""
    return (
        f"## Failure during {client_id} / {month} run\n\n"
        f"**Section:** {section_name}\n"
        f"**Script:** {script_name}\n"
        f"**Error:** {error_class} — {error_msg}\n"
        f"**Location:** `{error_file}:{error_line}`\n\n"
        f"{suggestion_block}"
        f"<details><summary>Traceback tail</summary>\n\n"
        f"```\n{traceback_tail}\n```\n\n"
        f"</details>\n"
    )


def capture_exception(
    exc: BaseException,
    tb: TracebackType | None,
    *,
    section_name: str,
    script_name: str,
    client_id: str,
    month: str,
    project_marker: str = "analytics",
) -> dict[str, object]:
    """Turn an exception + traceback into the structured fields a ScriptRecord wants."""
    error_class = type(exc).__name__
    error_msg = str(exc)[:300]

    frame = deepest_project_frame(tb, project_marker=project_marker)
    error_file = frame.filename if frame else ""
    error_line = frame.lineno if frame else 0

    if tb is not None:
        tb_lines = traceback.format_exception(type(exc), exc, tb)
        traceback_tail = "".join(tb_lines)[-2000:]
    else:
        traceback_tail = ""

    suggested = suggest_fix(error_class, error_msg)

    body = _format_issue_body(
        error_class=error_class, error_msg=error_msg,
        error_file=error_file, error_line=error_line,
        traceback_tail=traceback_tail, suggested_fix=suggested,
        section_name=section_name, script_name=script_name,
        client_id=client_id, month=month,
    )

    return {
        "error_class": error_class,
        "error_msg": error_msg,
        "error_file": error_file,
        "error_line": error_line,
        "error_traceback_tail": traceback_tail,
        "suggested_fix": suggested,
        "issue_body_md": body,
    }
