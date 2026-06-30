"""Step: Load ODD data with Copy-on-Write, date pre-parsing, column validation."""

from __future__ import annotations

import re
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
    df = _derive_monthly_metrics(df)
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
    df = _derive_monthly_metrics(df)
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


def _required_name_set() -> set[str]:
    """All accepted required-column names (canonical + aliases), normalized
    (stripped + casefolded) for tolerant matching."""
    out: set[str] = set()
    for names in REQUIRED_COLUMNS:
        for n in names:
            out.add(str(n).strip().casefold())
    return out


def _normalize_columns(df: pd.DataFrame, file_path: Path) -> None:
    """Rename known aliases to canonical names and validate required columns.

    Matching tolerates leading/trailing whitespace and case, because real ODD
    headers drift (the canonical field spec even lists ' Acct Number' with a
    leading space). Without this a ' Stat Code' or 'stat code' header would read
    as a missing required column (#232).
    """
    # normalized label -> the actual column object present in df
    lookup: dict[str, object] = {}
    for c in df.columns:
        lookup.setdefault(str(c).strip().casefold(), c)

    renames: dict[object, str] = {}
    missing: list[str] = []

    for names in REQUIRED_COLUMNS:
        canonical = names[0]
        if canonical in df.columns:
            continue
        actual = None
        for cand in names:  # canonical first, then aliases
            hit = lookup.get(str(cand).strip().casefold())
            if hit is not None:
                actual = hit
                break
        if actual is None:
            missing.append(canonical)
        elif actual != canonical:
            renames[actual] = canonical

    if renames:
        df.rename(columns=renames, inplace=True)
        for old, new in renames.items():
            logger.info("Column matched: '{old}' -> '{new}'", old=old, new=new)

    if missing:
        # Coerce to str before sorting: a vendor/placed-as-is ODD can carry
        # numeric column headers (e.g. a month labeled 202406). sorted() on a
        # mix of str + int raises "'<' not supported between 'str' and 'int'",
        # which crashed this *diagnostic* line and masked the real, actionable
        # "missing required columns" error below (#232).
        logger.warning(
            "Available columns: {cols}",
            cols=", ".join(sorted(str(c) for c in df.columns[:20])),
        )
        raise DataError(
            f"ODD file missing required columns: {', '.join(sorted(missing))}",
            detail={"file": str(file_path), "missing": sorted(missing)},
        )


_SPEND_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Spend$")
_SWIPE_RE = re.compile(r"^[A-Z][a-z]{2}\d{2} Swipes$")


def _derive_monthly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Derive per-month 'Mmm## Spend' / 'Mmm## Swipes' from raw PIN/Sig columns
    when the ODD lacks them.

    These columns are normally created by 00_Formatting's format_odd (step 4:
    'Mmm## PIN $' + 'Mmm## Sig $' -> 'Mmm## Spend'; '# ' -> 'Swipes'). A vendor
    file placed without running format_odd reaches analysis without them, so the
    mailer/value modules find no Spend/Swipes and the monthly spend/swipe slides
    come out empty (#232). Recompute them here as a safety net. No-op when they
    already exist (the 24 properly-formatted clients) or when there are no PIN/Sig
    columns to derive from.
    """
    cols = list(df.columns)
    have_spend = any(_SPEND_RE.match(str(c)) for c in cols)
    have_swipe = any(_SWIPE_RE.match(str(c)) for c in cols)
    if have_spend and have_swipe:
        return df

    new: dict[str, pd.Series] = {}
    if not have_spend:
        for col in [c for c in cols if str(c).endswith(" PIN $")]:
            prefix = str(col)[: -len(" PIN $")]
            sig = f"{prefix} Sig $"
            if sig in df.columns:
                new[f"{prefix} Spend"] = (
                    pd.to_numeric(df[col], errors="coerce").fillna(0)
                    + pd.to_numeric(df[sig], errors="coerce").fillna(0)
                )
    if not have_swipe:
        for col in [c for c in cols if str(c).endswith(" PIN #")]:
            prefix = str(col)[: -len(" PIN #")]
            sig = f"{prefix} Sig #"
            if sig in df.columns:
                new[f"{prefix} Swipes"] = (
                    pd.to_numeric(df[col], errors="coerce").fillna(0)
                    + pd.to_numeric(df[sig], errors="coerce").fillna(0)
                )

    if new:
        df = pd.concat([df, pd.DataFrame(new, index=df.index)], axis=1)
        logger.warning(
            "Derived {n} monthly Spend/Swipes column(s) from PIN $/Sig $ -- the ODD "
            "lacked them (not run through format_odd's combine step)",
            n=len(new),
        )
    elif not have_spend and not have_swipe:
        n_pin = sum(1 for c in cols if str(c).endswith((" PIN $", " PIN #")))
        logger.warning(
            "No monthly Spend/Swipes columns, and no PIN $/Sig $ pairs to derive "
            "them from ({n} PIN columns) -- monthly spend/swipe slides will be empty",
            n=n_pin,
        )
    return df


def _detect_header_row(probe: pd.DataFrame, max_scan: int = 15) -> int:
    """Return the row index that holds the real column headers.

    Some ODDs -- notably vendor files placed as-is -- carry a title/banner row
    above the headers (e.g. row 1 is 'First American Bank - OD Data Dump' and the
    real headers are on row 2). Reading with header=0 then makes every required
    column look missing and turns a stray numeric title cell into an int header
    (#232). Scan the first rows and pick the one containing the most required
    column names; fall back to row 0 so normal files are untouched.
    """
    wanted = _required_name_set()
    best_row, best_hits = 0, 0
    for i in range(min(max_scan, len(probe))):
        hits = sum(
            1 for v in probe.iloc[i].tolist()
            if v is not None and str(v).strip().casefold() in wanted
        )
        if hits > best_hits:
            best_hits, best_row = hits, i
    # Require >=2 matches to override row 0, so a normal header-on-row-0 file
    # (best_hits found at row 0) is never second-guessed.
    return best_row if best_hits >= 2 else 0


def _read_tabular(path: Path, reader) -> pd.DataFrame:
    """Read excel/csv, auto-skipping a title/preamble row above the header.

    Column labels are coerced to str: an ODD can carry numeric header cells
    (e.g. a month labeled 202406, or a stray number in 1800's banner rows), and
    analytics modules iterate df.columns with string ops -- `c.endswith(...)`,
    `"Reg E" in c`, regex -- which raise on an int label and kill the whole
    module (#232: mailer.*, insights.branch_scorecard/dormant/effectiveness).
    A non-string header is never a real ODD field, so stringifying is safe and
    lets those modules simply skip it. Existing string labels are unchanged --
    we deliberately do NOT strip, so exact names like ' Acct Number' survive.
    """
    probe = reader(path, header=None, nrows=15)
    hdr = _detect_header_row(probe)
    if hdr > 0:
        logger.warning(
            "Header row detected on row {n} -- skipping {n} title/preamble row(s) above it",
            n=hdr,
        )
    df = reader(path, header=hdr)
    df.columns = [str(c) for c in df.columns]
    return df


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
                    return _read_tabular(cached, pd.read_excel)
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                logger.info("Copying {name} to local temp for faster read...", name=path.name)
                shutil.copy2(path, tmp_path)
                logger.info("Copy done ({mb:.1f} MB). Reading...", mb=file_size / 1024 / 1024)
                _odd_cache_put(path, tmp_path)
                # Do NOT unlink: cache reuses the file across runs in the same session.
                return _read_tabular(tmp_path, pd.read_excel)
        except ValueError as exc:
            raise DataError(
                f"Cannot read Excel file: {exc}",
                detail={"file": str(path)},
            ) from exc
    return _read_tabular(path, pd.read_csv)


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
