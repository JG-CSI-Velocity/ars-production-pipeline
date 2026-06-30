"""run_pipeline must mark which results were critical so a failed run can exit
non-zero instead of reporting "0 slides" and a green "complete" (#232)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ars_analysis.pipeline.runner import PipelineStep, run_pipeline


def _ctx(tmp_path):
    return SimpleNamespace(
        client=SimpleNamespace(client_id="T", client_name="T", csm="x", month="m"),
        paths=SimpleNamespace(base_dir=tmp_path),
        settings=None,
        progress_callback=None,
        manifest=None,
    )


def _ok(ctx):
    pass


def _boom(ctx):
    raise ValueError("kaboom")


def test_critical_failure_is_flagged_and_stops_pipeline(tmp_path):
    results = run_pipeline(
        _ctx(tmp_path),
        [
            PipelineStep("a", _ok, critical=True),
            PipelineStep("load_data", _boom, critical=True),
            PipelineStep("after", _ok, critical=True),
        ],
    )
    crit = [r for r in results if not r.success and r.critical]
    assert [r.name for r in crit] == ["load_data"]
    # The pipeline must stop before 'after' runs.
    assert all(r.name != "after" for r in results)
    # The original exception is retained so run_ars can re-raise it.
    assert isinstance(crit[0].exception, ValueError)


def test_noncritical_failure_does_not_flag_critical(tmp_path):
    results = run_pipeline(
        _ctx(tmp_path),
        [
            PipelineStep("archive", _boom, critical=False),
            PipelineStep("after", _ok, critical=True),
        ],
    )
    # Non-critical failure continues and must NOT count as a critical failure.
    assert [r for r in results if not r.success and r.critical] == []
    assert any(r.name == "after" and r.success for r in results)
