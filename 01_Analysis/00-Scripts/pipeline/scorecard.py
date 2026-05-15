"""Render run_scorecard.md from a finished RunManifest."""
from __future__ import annotations

from pathlib import Path

from ars_analysis.pipeline.manifest import (
    FlagLevel,
    RunManifest,
    RunStatus,
    ScriptStatus,
    SectionStatus,
)


def _verdict(rm: RunManifest) -> str:
    totals = rm._totals()
    if rm.status == RunStatus.OK and totals["scripts_failed"] == 0:
        flagged = sum(
            1 for sec in rm.sections
            for f in sec.anomaly_flags
            if f.level in (FlagLevel.WARN, FlagLevel.ERROR)
        )
        if flagged:
            return "Ship with caution — anomaly flags present"
        return "Ship"
    if rm.status == RunStatus.FAILED:
        return "Do not ship — pipeline failed"
    return "Investigate before shipping"


def _section_row(sec) -> str:
    flags = ", ".join(f.level.value for f in sec.anomaly_flags) or "—"
    keys = ", ".join(f"{k}={v}" for k, v in list(sec.key_numbers.items())[:3]) or "—"
    status_label = {
        SectionStatus.OK: "OK",
        SectionStatus.PARTIAL: "Partial",
        SectionStatus.FAILED: "Failed",
        SectionStatus.NO_CHARTS: "No charts",
        SectionStatus.SKIPPED: "Skipped",
        SectionStatus.RUNNING: "Running",
    }.get(sec.status, str(sec.status))
    return f"| {sec.name} | {status_label} | {sec.slides} | {keys} | {flags} |"


def _failure_block(sec, script) -> str:
    body = script.issue_body_md or "(no issue body)"
    suggestion = f"\n*Suggested fix: {script.suggested_fix}*\n" if script.suggested_fix else ""
    return (
        f"### {sec.name} · {script.name} — {script.error_class}\n\n"
        f"> {script.error_msg} at `{script.error_file}:{script.error_line}`{suggestion}\n\n"
        f"<details><summary>Issue body (copy/paste)</summary>\n\n"
        f"{body}\n\n"
        f"</details>\n"
    )


def _anomaly_lines(rm: RunManifest) -> list[str]:
    lines: list[str] = []
    for sec in rm.sections:
        for flag in sec.anomaly_flags:
            lines.append(f"- **{sec.name}** ({flag.level.value}): {flag.message}")
    return lines


def write(rm: RunManifest, path: Path) -> Path:
    """Render the scorecard markdown. Returns the path written."""
    path = Path(path)
    totals = rm._totals()
    failures = [
        (sec, sc)
        for sec in rm.sections
        for sc in sec.scripts
        if sc.status == ScriptStatus.FAILED
    ]
    anomaly_lines = _anomaly_lines(rm)

    out: list[str] = []
    out.append(f"# Run scorecard — {rm.client_id} / {rm.month} ({rm.csm})")
    out.append("")
    out.append(f"**Verdict:** {_verdict(rm)}")
    out.append("")
    out.append(f"- Slides built: **{totals['slides_built']}**")
    out.append(
        f"- Sections OK: {totals['sections_ok']} | failed: {totals['sections_failed']}"
        f" | no charts: {totals['sections_no_charts']}"
    )
    out.append(
        f"- Scripts OK: {totals['scripts_ok']} / {totals['scripts_total']}"
        f" (failed: {totals['scripts_failed']})"
    )
    out.append(f"- Elapsed: {rm.elapsed_s:.0f}s")
    out.append("")
    out.append("## Section status")
    out.append("")
    out.append("| Section | Status | Slides | Key numbers | Flags |")
    out.append("| --- | --- | --- | --- | --- |")
    for sec in rm.sections:
        out.append(_section_row(sec))
    out.append("")

    if failures:
        out.append("## Failures (ready to file)")
        out.append("")
        for sec, sc in failures:
            out.append(_failure_block(sec, sc))
            out.append("")

    if anomaly_lines:
        out.append("## Anomaly flags")
        out.append("")
        out.extend(anomaly_lines)
        out.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    return path
