"""Per-module smoke for the ARS side: every registered ARS module validates and
runs over a shared synthetic ODD frame. 25/26 run clean; insights.dormant needs
upstream results (it's an insights aggregator) and is xfail'd."""

from __future__ import annotations

import contextlib
import io

import pytest

from ars_analysis.analytics.registry import load_all_modules, ordered_modules
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext

from _fixtures import synthetic_rewards

load_all_modules()
_MODULES = ordered_modules()

# Modules that need other modules' outputs (aggregators) rather than raw data.
_KNOWN_GAPS = {"insights.dormant": "insights aggregator -- needs upstream module results"}


def _ctx(tmp_path):
    ctx = PipelineContext(
        client=ClientInfo(client_id="T", client_name="Test", month="2026.06"),
        paths=OutputPaths.from_dir(tmp_path),
    )
    ctx.data = synthetic_rewards()
    return ctx


@pytest.mark.parametrize("cls", _MODULES, ids=lambda c: c.module_id)
def test_ars_module_validates_and_runs(cls, tmp_path):
    m = cls()
    if m.module_id in _KNOWN_GAPS:
        pytest.xfail(_KNOWN_GAPS[m.module_id])
    ctx = _ctx(tmp_path)
    assert m.validate(ctx) == [], f"{m.module_id} rejected the synthetic ODD frame"
    with contextlib.redirect_stdout(io.StringIO()):
        results = m.run(ctx)
    assert isinstance(results, list)


def test_ars_module_coverage_is_broad():
    assert len(_MODULES) - len(_KNOWN_GAPS) >= 25
