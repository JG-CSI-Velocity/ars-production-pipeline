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
