"""Score slide headlines against SLIDE_MAPPING.md rules.

Polish never rewrites headlines -- that's an analyst judgment call. It
surfaces violations so the analyst can fix them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_CHARS = 120

DIRECTION_WORDS = (
    "rose", "fell", "grew", "declined", "up", "down", "increased",
    "decreased", "climbed", "dropped", "gained", "lost", "drove",
    "jumped", "slipped", "rebounded",
)

DRIVER_PHRASES = (
    ", led by", ", due to", ", driven by", ", on the ", " on the ",
    ", because", ", as ", " led by ", " due to ", " driven by ",
)


@dataclass
class HeadlineScore:
    text: str
    is_complete_sentence: bool
    has_metric: bool
    has_direction: bool
    has_driver_clause: bool
    char_count: int
    violates: list[str] = field(default_factory=list)


def _is_complete_sentence(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped[-1] not in ".!?":
        return False
    words = stripped.rstrip(".!?").split()
    if len(words) < 4:
        return False
    # Title-case-all-words is a fragment signal (e.g. "Debit Card by Branch").
    # Sentences usually have at least one lowercase non-short word.
    lower_content_words = [
        w for w in words if len(w) > 3 and w[0].islower()
    ]
    return len(lower_content_words) >= 1


def _has_metric(text: str) -> bool:
    return bool(re.search(r"\d", text))


def _has_direction(text: str) -> bool:
    lower = text.lower()
    return any(re.search(rf"\b{w}\b", lower) for w in DIRECTION_WORDS)


def _has_driver_clause(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in DRIVER_PHRASES)


def score_headline(text: str) -> HeadlineScore:
    is_sent = _is_complete_sentence(text)
    has_met = _has_metric(text)
    has_dir = _has_direction(text)
    has_drv = _has_driver_clause(text)
    n = len(text)

    violates: list[str] = []
    if not is_sent:
        violates.append("not a complete sentence")
    if not has_met:
        violates.append("missing metric (number, %, or $)")
    if not has_dir:
        violates.append("missing direction word (rose/fell/grew/...)")
    if not has_drv:
        violates.append("missing driver clause (comma + 'led by'/'due to'/...)")
    if n > MAX_CHARS:
        violates.append(f"too long ({n} > {MAX_CHARS} chars)")

    return HeadlineScore(
        text=text,
        is_complete_sentence=is_sent,
        has_metric=has_met,
        has_direction=has_dir,
        has_driver_clause=has_drv,
        char_count=n,
        violates=violates,
    )
