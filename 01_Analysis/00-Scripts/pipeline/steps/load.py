"""Step: Load ODD data with Copy-on-Write, date pre-parsing, column validation."""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
from loguru import logger

from ars_analysis.exceptions import DataError
from ars_analysis.pipeline.context import PipelineContext

# Required columns that must be present in every ODD file.
# Each entry is (canonical_name, *aliases). The first alias found is renamed.
REQUIRED_COLUMNS: tuple[tuple[str, ...], ...] = (
    ("Stat Code",),
    ("Product Code", "Prod Code"),
    ("Date Opened",),
    ("Avg Bal", "Balance", "Current Balance", "Cur Bal"),
)

# Columns to pre-parse as dates (avoids 14+ redundant to_datetime calls downstream).
DATE_COLUMNS: tuple[str, ...] = (
    "Date Opened",
    "Date Closed",
)


def step_load(ctx: PipelineContext) -> None:
    """Load an ODD Excel/CSV file into ctx.data with validation.

    Applies:
    - pandas Copy-on-Write (eliminates 55+ unnecessary .copy() calls)
    - Date pre-parsing on known date columns
    - Column presence validation
    """
    pd.set_option("mode.copy_on_write", True)

    file_path = ctx.paths.base_dir / _find_data_file(ctx.paths.base_dir)
    logger.info("Loading data from {name}", name=file_path.name)

    df = _read_file(file_path)

    # Pre-parse date columns once at load time
    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
            logger.debug("Pre-parsed date column: {col}", col=col)

    _normalize_columns(df, file_path)
    df = _filter_by_start_date(df, ctx)

    ctx.data = df
    ctx.data_original = df
    logger.info(
        "Loaded {rows:,} rows x {cols} columns from {name}",
        rows=len(df),
        cols=len(df.columns),
        name=file_path.name,
    )


def step_load_file(ctx: PipelineContext, file_path: Path) -> None:
    """Load a specific file (used by CLI 'ars run <file>')."""
    pd.set_option("mode.copy_on_write", True)

    logger.info("Loading data from {name}", name=file_path.name)
    df = _read_file(file_path)

    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")

    _normalize_columns(df, file_path)
    df = _filter_by_start_date(df, ctx)

    ctx.data = df
    ctx.data_original = df
    logger.info(
        "Loaded {rows:,} rows x {cols} columns from {name}",
        rows=len(df),
        cols=len(df.columns),
        name=file_path.name,
    )


def _filter_by_start_date(df: pd.DataFrame, ctx: PipelineContext) -> pd.DataFrame:
    """Drop rows where Date Opened is before the program launch date.

    Accounts opened before data_start_date are test/bad data.
    Rows with NaT Date Opened are preserved (missing date != before start).
    """
    start = ctx.client.data_start_date
    if not start:
        return df

    if "Date Opened" not in df.columns:
        return df

    cutoff = pd.Timestamp(start)
    before = len(df)
    mask = df["Date Opened"].isna() | (df["Date Opened"] >= cutoff)
    df = df[mask].copy()
    dropped = before - len(df)
    if dropped > 0:
        logger.info(
            "Filtered {n} rows opened before {d} (program launch date)",
            n=dropped,
            d=start,
        )
    return df


def _normalize_columns(df: pd.DataFrame, file_path: Path) -> None:
    """Rename known aliases to canonical names and validate required columns."""
    renames: dict[str, str] = {}
    missing: list[str] = []

    for names in REQUIRED_COLUMNS:
        canonical = names[0]
        if canonical in df.columns:
            continue
        # Check aliases
        found = False
        for alias in names[1:]:
            if alias in df.columns:
                renames[alias] = canonical
                found = True
                break
        if not found:
            missing.append(canonical)

    if renames:
        df.rename(columns=renames, inplace=True)
        for old, new in renames.items():
            logger.info("Column renamed: '{old}' -> '{new}'", old=old, new=new)

    if missing:
        logger.warning(
            "Available columns: {cols}",
            cols=", ".join(sorted(df.columns[:20])),
        )
        raise DataError(
            f"ODD file missing required columns: {', '.join(sorted(missing))}",
            detail={"file": str(file_path), "missing": sorted(missing)},
        )


def _read_file(path: Path) -> pd.DataFrame:
    """Read a file based on extension.

    For Excel files on network drives, copies to a local temp file first.
    openpyxl makes many small random-access reads to .xlsx files (ZIP of XML),
    and each read is a network round-trip. A 450-column file can hang for hours
    over a slow connection. Local copy + read takes seconds.
    """
    import shutil
    import tempfile

    suffix = path.suffix.lower()

    # Reject unsupported formats first
    if suffix not in (".xlsx", ".xls", ".csv"):
        raise DataError(
            f"Unsupported file format: {suffix}",
            detail={"file": str(path), "supported": [".xlsx", ".xls", ".csv"]},
        )

    # Check file isn't empty/corrupt
    file_size = path.stat().st_size
    if file_size < 100:
        raise DataError(
            f"File is too small ({file_size} bytes) -- likely empty or corrupt",
            detail={"file": str(path), "size": file_size},
        )

    if suffix in (".xlsx", ".xls"):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
                # Wave 4 (CSM speed): keyed cache so a second run of the same
                # client in one session skips the network copy. Key = (mtime, size).
                # On cache hit, openpyxl reads the warm local copy -- ~15s instead of
                # ~3-5 min over the M: share.
                cached = _odd_cache_get(path)
                if cached is not None:
                    logger.info(
                        "Cache hit: reusing local copy of {name}", name=path.name
                    )
                    return pd.read_excel(cached)
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                logger.info("Copying {name} to local temp for faster read...", name=path.name)
                shutil.copy2(path, tmp_path)
                logger.info("Copy done ({mb:.1f} MB). Reading...", mb=file_size / 1024 / 1024)
                _odd_cache_put(path, tmp_path)
                # Do NOT unlink: cache reuses the file across runs in the same session.
                return pd.read_excel(tmp_path)
        except ValueError as exc:
            raise DataError(
                f"Cannot read Excel file: {exc}",
                detail={"file": str(path)},
            ) from exc
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# ODD temp-copy cache (Wave 4)
# ---------------------------------------------------------------------------

# Maps (source path string, mtime, size) -> local temp copy Path.
# Process-scoped: a fresh `python run.py` invocation starts empty. UI keeps the
# server running across runs, so cache hits accumulate over the day.
_ODD_CACHE: dict[tuple[str, float, int], Path] = {}


def _odd_cache_key(src: Path) -> tuple[str, float, int]:
    stat = src.stat()
    return (str(src), stat.st_mtime, stat.st_size)


def _odd_cache_get(src: Path) -> Path | None:
    """Return a cached local copy if one exists and the source hasn't changed."""
    try:
        key = _odd_cache_key(src)
    except OSError:
        return None
    cached = _ODD_CACHE.get(key)
    if cached is not None and cached.exists():
        return cached
    # Source changed -- invalidate any old entry for this path.
    for k in [k for k in _ODD_CACHE if k[0] == str(src)]:
        old = _ODD_CACHE.pop(k, None)
        if old is not None:
            try:
                old.unlink(missing_ok=True)
            except OSError:
                pass
    return None


def _odd_cache_put(src: Path, local_copy: Path) -> None:
    try:
        _ODD_CACHE[_odd_cache_key(src)] = local_copy
    except OSError:
        pass


def odd_cache_clear() -> None:
    """Drop every cached copy. Test hook + manual recovery."""
    for p in list(_ODD_CACHE.values()):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    _ODD_CACHE.clear()


def _find_data_file(directory: Path) -> str:
    """Find the ODD data file in a directory."""
    for ext in ("*.xlsx", "*.xls", "*.csv"):
        files = sorted(directory.glob(ext))
        if files:
            return files[0].name
    raise DataError(
        f"No data file found in {directory}",
        detail={"directory": str(directory), "searched": ["*.xlsx", "*.xls", "*.csv"]},
    )
