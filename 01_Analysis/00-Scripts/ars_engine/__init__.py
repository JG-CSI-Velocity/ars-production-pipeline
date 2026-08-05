"""ars_engine -- the v3 data + analytics engine.

Greenfield replacement for the legacy `ars_analysis` shim, `runner.py`, and
the 376 exec()-based TXN scripts. Installed via the repo-root pyproject.toml
(package-dir maps this directory to the top-level name `ars_engine`), so no
sys.path manipulation is ever required.

Layers:
    core/        one canonical Context / Result / Config / Brand / Registry
    data/        staged-data access: ODD snapshot, DuckDB TXN store, frames
    primitives/  kpi cards, action summaries, entity profiles, denominator law
    charts/      declarative ChartSpec + matplotlib renderer behind a seam
    sections/    ~27 section modules replacing the legacy script folders
    analytics/   ported domain math (DiD, exposure, survival, concentration)
"""

__version__ = "3.0.0a0"
