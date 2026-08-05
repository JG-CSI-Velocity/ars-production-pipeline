"""Core contracts: the ONE context, result, config, brand, and registry.

Legacy had two PipelineContexts (shared/context.py vs pipeline/context.py),
two AnalysisResults (shared/types.py vs analytics/base.py), two
PipelineConfigs, and four brand/color sources. This package is the single
replacement for all of them; `runner` bridges legacy objects through the
adapters in `result.py` during the migration window.
"""

from ars_engine.core.brand import BRAND, CHART_PALETTE, FONTS, SIZES
from ars_engine.core.config import EngineConfig, load_client_config
from ars_engine.core.context import (
    ClientInfo,
    DataSubsets,
    OutputPaths,
    PipelineContext,
    as_of_ts,
)
from ars_engine.core.registry import Section, SectionMeta, get_section, iter_sections, register
from ars_engine.core.result import SlideSpec, from_legacy_result

__all__ = [
    "BRAND",
    "CHART_PALETTE",
    "FONTS",
    "SIZES",
    "ClientInfo",
    "DataSubsets",
    "EngineConfig",
    "OutputPaths",
    "PipelineContext",
    "Section",
    "SectionMeta",
    "SlideSpec",
    "as_of_ts",
    "from_legacy_result",
    "get_section",
    "iter_sections",
    "load_client_config",
    "register",
]
