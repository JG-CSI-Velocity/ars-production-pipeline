"""Template placeholder registry for the exec-narrative deck.

Every new slide in the rebuild uses {{TOKEN}} syntax for numbers or names
that are client-specific. This module is the single source of truth for
every token, its fake default (used during template development), and the
rules for substituting real values at render time.

Real values arrive at pipeline run time; until then, rendering uses the
fake defaults so the template is always visually complete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Placeholder:
    """One template variable."""

    key: str                 # e.g. "NOTEBOOK_PENETRATION"
    description: str         # human-readable use
    fake_value: str          # shown when no real value is supplied
    source_hint: str = ""    # where the real value comes from at run time


PLACEHOLDERS: dict[str, Placeholder] = {
    p.key: p
    for p in [
        Placeholder(
            key="CLIENT_NAME",
            description="Bank or credit union name on the title slide",
            fake_value="Sample Bank",
            source_hint="clients_config.json -> client.name",
        ),
        Placeholder(
            key="NOTEBOOK_PENETRATION",
            description="Customer-level debit penetration (Truth slides)",
            fake_value="80%",
            source_hint="Jupyter notebook -- pending handoff spec",
        ),
        Placeholder(
            key="PIPELINE_DCTR",
            description="Account-level DCTR for contrast on Truth-2",
            fake_value="30%",
            source_hint="dctr/penetration.py -- existing analytics",
        ),
        Placeholder(
            key="ADDRESSABLE_SPEND_USD",
            description="Total addressable debit spend for Opportunity-1",
            fake_value="$12.4M",
            source_hint="value/analysis.py -- to be reworked with notebook denominator",
        ),
        Placeholder(
            key="NONUSER_COUNT",
            description="Number of customers matching the Non-User persona",
            fake_value="14,200",
            source_hint="complement of dctr/penetration.py",
        ),
        Placeholder(
            key="CLIMBER_COUNT",
            description="Number of customers matching the Climber persona",
            fake_value="6,800",
            source_hint="mailer/response.py + dctr/trends age",
        ),
        Placeholder(
            key="DECLINER_COUNT",
            description="Number of customers matching the Decliner persona",
            fake_value="3,100",
            source_hint="attrition/rates.py + insights/dormant.py",
        ),
        Placeholder(
            key="MOST_RECENT_MAILER_MONTH",
            description="Mailer month token used in the Plan section slide selector",
            fake_value="Mar26",
            source_hint="mailer section at run time -- picks newest month",
        ),
    ]
}


_TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def get_placeholder(key: str) -> Placeholder:
    """Return the Placeholder for key, or raise KeyError."""
    if key not in PLACEHOLDERS:
        raise KeyError(f"Unknown placeholder: {key}")
    return PLACEHOLDERS[key]


def render(text: str, overrides: dict[str, str] | None = None) -> str:
    """Substitute every known {{TOKEN}} in text.

    Known tokens are replaced with overrides[token] if present, otherwise
    with the placeholder's fake_value. Unknown tokens are left alone so
    upstream callers can layer additional registries.
    """
    overrides = overrides or {}

    def _replace(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in overrides:
            return overrides[key]
        if key in PLACEHOLDERS:
            return PLACEHOLDERS[key].fake_value
        return m.group(0)

    return _TOKEN_RE.sub(_replace, text)


def known_keys() -> Iterable[str]:
    """Return the set of registered placeholder keys."""
    return PLACEHOLDERS.keys()
