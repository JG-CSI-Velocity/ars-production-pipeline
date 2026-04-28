"""Validate slide_manifest.json module IDs against actual registered modules + script folders.

Run from repo root:
    python3 docs/deck/validate_manifest.py

Exits non-zero if unknown IDs found.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs" / "deck" / "slide_manifest.json"
REGISTRY = REPO_ROOT / "01_Analysis" / "00-Scripts" / "analytics" / "registry.py"
TXN_WRAPPER = REPO_ROOT / "01_Analysis" / "00-Scripts" / "analytics" / "txn_wrapper.py"
ANALYTICS_DIR = REPO_ROOT / "01_Analysis" / "00-Scripts" / "analytics"


def parse_module_order(registry_text: str) -> set[str]:
    """Extract MODULE_ORDER list entries from registry.py."""
    m = re.search(r"MODULE_ORDER:\s*list\[str\]\s*=\s*\[(.*?)\]", registry_text, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def parse_txn_sections(wrapper_text: str) -> set[str]:
    """Extract TXN_SECTIONS keys from txn_wrapper.py."""
    m = re.search(r"TXN_SECTIONS\s*=\s*\{(.*?)^\}", wrapper_text, re.DOTALL | re.MULTILINE)
    if not m:
        return set()
    return set(re.findall(r'"([^"]+)":\s*\{', m.group(1)))


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    registered_ars = parse_module_order(REGISTRY.read_text())
    txn_sections = parse_txn_sections(TXN_WRAPPER.read_text())
    txn_module_ids = {f"txn.{s}" for s in txn_sections}
    all_known = registered_ars | txn_module_ids

    unknown: dict[str, list[int]] = {}
    for slide in manifest["slides"]:
        for mid in slide.get("modules", []):
            if mid not in all_known:
                unknown.setdefault(mid, []).append(slide["n"])

    print(f"Manifest slides: {len(manifest['slides'])}")
    print(f"Registered ARS modules: {len(registered_ars)}")
    print(f"TXN sections: {len(txn_sections)}")
    print()

    if not unknown:
        print("OK: every manifest module ID maps to a registered ARS module or TXN section.")
        return 0

    print(f"FAIL: {len(unknown)} manifest module IDs not found in registry.py or txn_wrapper.TXN_SECTIONS.")
    print()
    for mid, slide_nums in sorted(unknown.items()):
        suggestion = _suggest_replacement(mid)
        print(f"  {mid:40s}  (slides {slide_nums})")
        if suggestion:
            print(f"    -> {suggestion}")
    return 1


def _suggest_replacement(mid: str) -> str | None:
    """Best-effort hint at what an unknown ID might map to."""
    if mid.startswith("ics."):
        return "ICS_cohort/ uses script-based exec; reference scripts directly (e.g. 'script:ICS_cohort/ics-40-exec-summary')"
    if mid.startswith("competition.") or mid.startswith("financial_services.") or mid.startswith("merchant.") or mid.startswith("general."):
        section, _, _ = mid.partition(".")
        section_dir = ANALYTICS_DIR / section
        if section_dir.exists():
            scripts = sorted(p.name for p in section_dir.glob("*.py") if not p.name.startswith("_"))[:5]
            return f"TXN section '{section}' exists as scripts: {scripts}... (use 'txn.{section}' + script filter)"
    if mid.startswith("executive."):
        return "Aspirational module -- not yet implemented. To build in analytics/executive/"
    return None


if __name__ == "__main__":
    sys.exit(main())
