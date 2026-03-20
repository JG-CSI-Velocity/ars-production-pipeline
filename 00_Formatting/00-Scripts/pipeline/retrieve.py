"""Retrieve ODD files from CSM M: drive folders into the local directory structure.

Copies ODD files from each CSM's source folder into:
    retrieve_dir/CSM/YYYY.MM/ClientID/filename.xlsx

Handles raw .xlsx ODD files and ####_ODDD.zip archives.
Parallel scanning across CSMs to avoid sequential network waits.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from shared.utils import (
    parse_month_folder,
    parse_odd_filename,
    parse_oddd_zip,
    resolve_target_month,
)

logger = logging.getLogger(__name__)

# Timeout (seconds) for checking if a network path is accessible.
_PATH_TIMEOUT = 5.0


@dataclass
class RetrieveResult:
    """Structured result from a retrieve operation."""

    copied: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    errors: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.copied) + len(self.skipped) + len(self.errors)


def _path_accessible(path: Path, timeout: float = _PATH_TIMEOUT) -> bool | None:
    """Check if path exists, with a timeout to avoid hanging on offline shares."""
    result: list[bool | None] = [None]

    def _check() -> None:
        try:
            result[0] = path.exists()
        except OSError:
            result[0] = False

    t = threading.Thread(target=_check, daemon=True)
    t.start()
    t.join(timeout)
    return result[0]


def retrieve_all(
    settings,
    target_month: str | None = None,
    max_per_csm: int = 0,
    csm_filter: str | None = None,
    client_filter: str | None = None,
) -> RetrieveResult:
    """Copy ODD files from CSM sources into retrieve_dir/CSM/YYYY.MM/ClientID/.

    Scans all CSM source folders in parallel to avoid sequential network waits.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    full_month, target_year, target_mm = resolve_target_month(target_month)
    dest_root = settings.paths.retrieve_dir
    result = RetrieveResult()

    # Verify base path exists
    base = settings.paths.ars_base
    if not base.exists():
        logger.error("ars_base does not exist: %s", base)
        print(f"  ERROR: ars_base does not exist: {base}")
        return result

    try:
        dest_root.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error("Permission denied creating %s", dest_root)
        return result

    print(f"  Retrieving ODD files for {full_month} -> {dest_root}")

    sources = settings.csm_sources.sources
    # Skip CSMs with placeholder paths, apply CSM filter
    active_sources = {
        name: path for name, path in sources.items()
        if str(path) != "UPDATE_THIS_PATH"
        and (csm_filter is None or name == csm_filter)
    }

    if not active_sources:
        print("  No CSM sources configured (all are UPDATE_THIS_PATH).")
        return result

    print(f"  Scanning {len(active_sources)} CSM source(s) in parallel ...")

    with ThreadPoolExecutor(max_workers=len(active_sources)) as pool:
        futures = {
            pool.submit(
                _scan_one_csm,
                csm_name, source_dir, dest_root,
                target_year, target_mm, max_per_csm, client_filter,
            ): csm_name
            for csm_name, source_dir in active_sources.items()
        }

        for future in as_completed(futures):
            csm_name, status, per_csm = future.result()

            if status == "TIMEOUT":
                print(f"  {csm_name}: TIMEOUT (network share not responding)")
                continue
            if status == "OFFLINE":
                print(f"  {csm_name}: OFFLINE (path does not exist)")
                continue

            result.copied.extend(per_csm.copied)
            result.skipped.extend(per_csm.skipped)
            result.errors.extend(per_csm.errors)

            n = per_csm.total
            if n == 0:
                print(f"  {csm_name}: OK -- no files for this month")
            else:
                parts = []
                if per_csm.copied:
                    parts.append(f"{len(per_csm.copied)} copied")
                if per_csm.skipped:
                    parts.append(f"{len(per_csm.skipped)} existing")
                if per_csm.errors:
                    parts.append(f"{len(per_csm.errors)} errors")
                print(f"  {csm_name}: OK -- {', '.join(parts)}")

    print()
    print(f"  Retrieve done: {len(result.copied)} copied, "
          f"{len(result.skipped)} skipped, {len(result.errors)} errors")
    return result


def _scan_one_csm(csm_name, source_dir, dest_root, target_year, target_mm, max_per_csm, client_filter=None):
    """Scan a single CSM source in a worker thread."""
    per_csm = RetrieveResult()

    accessible = _path_accessible(source_dir)
    if accessible is None:
        return csm_name, "TIMEOUT", per_csm
    if not accessible:
        return csm_name, "OFFLINE", per_csm

    _retrieve_csm(source_dir, csm_name, dest_root, target_year, target_mm, per_csm, max_per_csm, client_filter)
    return csm_name, "OK", per_csm


def _retrieve_csm(source_dir, csm_name, dest_root, target_year, target_mm, result, max_files=0, client_filter=None):
    """Retrieve ODD files from a single CSM source folder."""
    count_before = len(result.copied)

    month_dirs = _find_month_dirs(source_dir, target_year, target_mm)

    if month_dirs:
        for month_dir in month_dirs:
            if max_files and len(result.copied) - count_before >= max_files:
                break
            _scan_dir_for_odds(month_dir, csm_name, dest_root, target_year, target_mm,
                               result, max_files, count_before, client_filter)
            try:
                for child in month_dir.iterdir():
                    if max_files and len(result.copied) - count_before >= max_files:
                        break
                    if child.is_dir():
                        _scan_dir_for_odds(child, csm_name, dest_root, target_year, target_mm,
                                           result, max_files, count_before, client_filter)
            except (PermissionError, OSError) as exc:
                logger.warning("%s: error scanning %s: %s", csm_name, month_dir.name, exc)
    else:
        _scan_dir_for_odds(source_dir, csm_name, dest_root, target_year, target_mm,
                           result, max_files, count_before, client_filter)


def _find_month_dirs(source_dir, target_year, target_mm):
    """Find subfolders matching the target month (non-recursive, one level)."""
    matches = []
    try:
        for child in source_dir.iterdir():
            month_info = parse_month_folder(child.name)
            if not month_info:
                continue
            if month_info[0] != target_year or month_info[1] != target_mm:
                continue
            if child.is_dir():
                matches.append(child)
    except (PermissionError, OSError) as exc:
        logger.warning("Error listing %s: %s", source_dir, exc)
    return matches


def _scan_dir_for_odds(directory, csm_name, dest_root, target_year, target_mm,
                        result, max_files=0, count_base=0, client_filter=None):
    """Scan a single directory (non-recursive) for ODD xlsx and zip files."""
    try:
        entries = list(directory.iterdir())
    except (PermissionError, OSError):
        return

    for f in entries:
        if max_files and len(result.copied) - count_base >= max_files:
            return

        name_lower = f.name.lower()
        if f.name.startswith("~$"):
            continue
        if not (name_lower.endswith(".xlsx") or name_lower.endswith(".zip")):
            continue
        if not f.is_file():
            continue

        if name_lower.endswith(".xlsx"):
            parsed = parse_odd_filename(f.name)
            if parsed and parsed["year"] == target_year and parsed["month"] == target_mm:
                if client_filter and parsed["client_id"] != client_filter:
                    continue
                _place_odd(f, parsed, csm_name, dest_root, result)

        elif name_lower.endswith(".zip"):
            _process_zip(f, csm_name, target_year, target_mm, dest_root, result, client_filter)


def _place_odd(xlsx_data, parsed, csm_name, dest_root, result, source_label=None):
    """Copy a single ODD file into CSM/YYYY.MM/ClientID/ structure."""
    month_folder = f"{parsed['year']}.{parsed['month']}"
    target_dir = dest_root / csm_name / month_folder / parsed["client_id"]
    target_file = target_dir / parsed["filename"]

    if target_file.exists():
        result.skipped.append((csm_name, parsed["filename"]))
        return

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(xlsx_data, Path):
            shutil.copy2(xlsx_data, target_file)
        else:
            target_file.write_bytes(xlsx_data)
        label = source_label or parsed["filename"]
        result.copied.append((csm_name, label))
        print(f"      + {parsed['client_id']} {parsed['filename']}")
    except (PermissionError, OSError) as exc:
        result.errors.append((csm_name, parsed["filename"], str(exc)))
        print(f"      x {parsed['filename']}: {exc}")


def _process_zip(zf_path, csm_name, target_year, target_mm, dest_root, result, client_filter=None):
    """Process a zip archive: copy to local temp first (avoids slow SMB seeks)."""
    client_id_from_zip = parse_oddd_zip(zf_path.name)
    month_info = parse_month_folder(zf_path.parent.name)

    if month_info and (month_info[0] != target_year or month_info[1] != target_mm):
        return
    if not month_info:
        return

    if not client_id_from_zip:
        lead_digits = re.match(r"^(\d+)", zf_path.stem)
        if lead_digits:
            client_id_from_zip = lead_digits.group(1)

    # Skip if client filter doesn't match
    if client_filter and client_id_from_zip and client_id_from_zip != client_filter:
        return

    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            local_zip = Path(tmp.name)
            shutil.copy2(zf_path, local_zip)

        try:
            _extract_zip(local_zip, zf_path.name, csm_name, client_id_from_zip,
                         month_info, target_year, target_mm, dest_root, result)
        finally:
            local_zip.unlink(missing_ok=True)

    except (PermissionError, OSError) as exc:
        result.errors.append((csm_name, zf_path.name, str(exc)))


def _extract_zip(local_zip, original_name, csm_name, client_id_from_zip,
                 month_info, target_year, target_mm, dest_root, result):
    """Extract ODD files from a local copy of a zip archive."""
    try:
        with zipfile.ZipFile(local_zip, "r") as zf:
            entries = [n for n in zf.namelist()
                       if Path(n).name and not Path(n).name.startswith("~$")]

            for name in entries:
                basename = Path(name).name
                parsed = parse_odd_filename(basename)

                if parsed and (parsed["year"] != target_year or parsed["month"] != target_mm):
                    parsed = None

                if not parsed and client_id_from_zip and month_info:
                    if basename.lower().endswith((".xlsx", ".csv")):
                        year, month = month_info
                        parsed = {
                            "client_id": client_id_from_zip,
                            "year": year,
                            "month": month,
                            "client_name": "",
                            "filename": basename,
                        }

                if not parsed:
                    continue

                data = zf.read(name)
                _place_odd(data, parsed, csm_name, dest_root, result,
                           source_label=f"{original_name}/{basename}")

    except zipfile.BadZipFile as exc:
        result.errors.append((csm_name, original_name, str(exc)))
