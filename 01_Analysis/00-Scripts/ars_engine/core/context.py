"""The ONE PipelineContext.

Merges the two legacy contexts:
- ``pipeline/context.py`` -- ClientInfo / OutputPaths / DataSubsets structure,
  product stamp, manifest hook (the shape every analytics module consumes).
- ``shared/context.py`` -- the L12M window math (compute_l12m_window / in_l12m).

`runner.py` existed largely to translate between those two; with one type the
translation layer disappears.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


def _ensure_list(value: object) -> list[str]:
    """Wrap a scalar string as a single-element list; pass through lists."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert a config value to float, returning default for empty/invalid."""
    if value is None or value == "":
        return default
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default


@dataclass
class ClientInfo:
    """Client identity and configuration."""

    client_id: str
    client_name: str
    month: str  # "YYYY.MM"
    eligible_stat_codes: list[str] = field(default_factory=list)
    eligible_prod_codes: list[str] = field(default_factory=list)
    eligible_mailable: list[str] = field(default_factory=list)
    nsf_od_fee: float = 0.0
    ic_rate: float = 0.0
    dc_indicator: str = "DC Indicator"
    reg_e_opt_in: list[str] = field(default_factory=list)
    reg_e_column: str = ""
    assigned_csm: str = ""
    # Program launch date (YYYY-MM-DD); drop rows opened before this.
    data_start_date: str | None = None

    @classmethod
    def from_client_config(
        cls,
        client_id: str,
        client_name: str,
        month: str,
        ccfg: dict[str, Any],
        csm: str = "",
    ) -> ClientInfo:
        """Build from a clients_config.json entry.

        This construction was copy-pasted four times in the legacy runner
        (run_ars / run_txn / run_module / _build_module_ctx); this is the one
        canonical version.
        """
        return cls(
            client_id=client_id,
            client_name=client_name or client_id,
            month=month,
            assigned_csm=csm,
            eligible_stat_codes=_ensure_list(ccfg.get("EligibleStatusCodes", [])),
            eligible_prod_codes=_ensure_list(ccfg.get("EligibleProductCodes", [])),
            eligible_mailable=_ensure_list(ccfg.get("EligibleMailCode", [])),
            nsf_od_fee=_safe_float(ccfg.get("NSF_OD_Fee", 0)),
            ic_rate=_safe_float(ccfg.get("ICRate", 0)),
            dc_indicator=ccfg.get("DCIndicator", "DC Indicator"),
            reg_e_opt_in=_ensure_list(ccfg.get("RegEOptInCode", [])),
            reg_e_column=ccfg.get("RegEColumn", ""),
            data_start_date=ccfg.get("DataStartDate"),
        )


@dataclass
class OutputPaths:
    """Resolved output directories for one pipeline run."""

    base_dir: Path = Path(".")
    charts_dir: Path = Path(".")
    excel_dir: Path = Path(".")
    pptx_dir: Path = Path(".")

    @classmethod
    def from_base(cls, base: Path, client_id: str, month: str) -> OutputPaths:
        run_dir = base / client_id / month
        return cls(
            base_dir=run_dir,
            charts_dir=run_dir / "charts",
            excel_dir=run_dir,
            pptx_dir=run_dir,
        )

    @classmethod
    def from_dir(cls, directory: Path) -> OutputPaths:
        """Use a directory directly as the output root (no extra nesting)."""
        return cls(
            base_dir=directory,
            charts_dir=directory / "charts",
            excel_dir=directory,
            pptx_dir=directory,
        )


@dataclass
class DataSubsets:
    """Pre-computed filtered views of the ODD data (the 4-layer denominator law).

    open_accounts / eligible_data / eligible_personal / eligible_business are
    the four sanctioned rate denominators; eligible_with_debit and
    last_12_months are derived working sets.
    """

    open_accounts: pd.DataFrame | None = None
    eligible_data: pd.DataFrame | None = None
    eligible_personal: pd.DataFrame | None = None
    eligible_business: pd.DataFrame | None = None
    eligible_with_debit: pd.DataFrame | None = None
    last_12_months: pd.DataFrame | None = None


@dataclass
class PipelineContext:
    """The single typed container for one pipeline run.

    - client: who (identity + config)
    - paths: where (output directories)
    - data / subsets / frames: what (DataFrames; `frames` is the v3 FrameCatalog)
    - results: output (slide specs keyed by producer)
    """

    client: ClientInfo
    paths: OutputPaths
    settings: object = None  # EngineConfig -- object-typed to avoid import cycle
    data: pd.DataFrame | None = None
    data_original: pd.DataFrame | None = None
    subsets: DataSubsets = field(default_factory=DataSubsets)
    # v3: lazily-loading frame catalog (ars_engine.data.frames.FrameCatalog).
    frames: object = None
    results: dict[str, list] = field(default_factory=dict)  # producer id -> [SlideSpec]
    all_slides: list = field(default_factory=list)
    export_log: list[str] = field(default_factory=list)
    start_date: date | pd.Timestamp | None = None
    end_date: date | pd.Timestamp | None = None
    debit_column: str = ""  # Auto-detected debit column name (set by subsets step)
    progress_callback: Callable[[str], None] | None = None
    # Slide IDs routed to a secondary aux deck instead of the main deck.
    auxiliary_slide_ids: set[str] = field(default_factory=set)
    # Pipeline product label -- "ars", "txn", or "combined". Deck filenames key
    # off this so a TXN run can never overwrite an ARS deck.
    product: str = "ars"
    # Structured run manifest; object-typed to avoid an import cycle.
    manifest: object = None

    # --- L12M window (set once, used everywhere) ---
    # If analysis_date is April 2026, L12M = Apr 2025 through Mar 2026.
    l12m_start: pd.Timestamp | None = None
    l12m_end: pd.Timestamp | None = None

    @property
    def analysis_date(self) -> date:
        """Reference date derived from the run month ('YYYY.MM')."""
        try:
            year, month = self.client.month.split(".")
            return date(int(year), int(month), 1)
        except (ValueError, AttributeError):
            return date.today()

    def compute_l12m_window(self) -> None:
        """Set l12m_start and l12m_end from the analysis date. Call once at start."""
        ref = pd.Timestamp(self.analysis_date)
        first_of_month = ref.replace(day=1)
        self.l12m_end = first_of_month - pd.Timedelta(days=1)
        self.l12m_start = first_of_month - pd.DateOffset(months=12)

    def in_l12m(self, dt_series: pd.Series) -> pd.Series:
        """Boolean mask: True for dates within the L12M window."""
        if self.l12m_start is None:
            self.compute_l12m_window()
        return (dt_series >= self.l12m_start) & (dt_series <= self.l12m_end)

    def progress(self, message: str) -> None:
        """Report progress if a callback is attached."""
        if self.progress_callback is not None:
            self.progress_callback(message)


def as_of_ts(ctx: PipelineContext) -> pd.Timestamp:
    """As-of timestamp for account-age / tenure math: the report end date, so
    ages (and buckets built from them) are reproducible for a given reporting
    period instead of drifting with the wall clock on re-runs. Falls back to
    now() only when the pipeline has no end_date set.

    Canonical home for every section -- never call pd.Timestamp.now() directly.
    """
    ed = getattr(ctx, "end_date", None)
    return pd.Timestamp(ed) if ed is not None else pd.Timestamp.now()
