"""Per-module smoke for the ARS side: every registered ARS module validates and
runs over a shared synthetic ODD frame with real subsets built (as in a full
run). All 26 modules run clean."""

from __future__ import annotations

import contextlib
import io

import pytest

from ars_analysis.analytics.registry import load_all_modules, ordered_modules
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
from ars_analysis.pipeline.steps.subsets import step_subsets

from _fixtures import synthetic_rewards

load_all_modules()
_MODULES = ordered_modules()

# All ARS modules now run over the synthetic fixture. (insights.dormant used to
# be gapped because it reads ctx.subsets.eligible_data -- now populated below by
# running the real step_subsets, exactly as a full run does.)
_KNOWN_GAPS: dict[str, str] = {}


def _ctx(tmp_path):
    ctx = PipelineContext(
        client=ClientInfo(client_id="T", client_name="Test", month="2026.06",
                          eligible_stat_codes=["O"]),
        paths=OutputPaths.from_dir(tmp_path),
    )
    ctx.data = synthetic_rewards()
    # Build the real subsets (eligible_data, splits) the analyze step relies on,
    # so aggregators like insights.dormant have what a full run gives them.
    with contextlib.redirect_stdout(io.StringIO()):
        step_subsets(ctx)
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


def test_ars_module_coverage_is_full():
    # Every registered ARS module runs over the synthetic fixture -- no gaps.
    assert _KNOWN_GAPS == {}
    assert len(_MODULES) - len(_KNOWN_GAPS) == len(_MODULES)
