# Load ODDD — ODD files live separately from TXN files
# ODD path: 02-Data-Ready for Analysis/{CSM}/{MONTH}/{client_id}/
# TXN path: 02-Data-Ready for Analysis/TXN Files/{CSM}/{client_id}/
# READY_FOR_ANALYSIS, CSM, MONTH, CLIENT_ID set by 02-file-config.py
odd_dir = READY_FOR_ANALYSIS / CSM / MONTH / CLIENT_ID
odd_candidates = list(odd_dir.glob(f"*{CLIENT_ID}*ODD*.xlsx")) if odd_dir.exists() else []
if not odd_candidates:
    # Fallback: check month folder directly (different naming)
    odd_candidates = list(odd_dir.parent.glob(f"*{CLIENT_ID}*ODD*.xlsx")) if odd_dir.parent.exists() else []
if not odd_candidates:
    # Fallback: scan all months for this CSM/client, use most recent
    csm_dir = READY_FOR_ANALYSIS / CSM
    if csm_dir.exists():
        for month_dir in sorted(csm_dir.iterdir(), reverse=True):
            if not month_dir.is_dir() or month_dir.name == "TXN Files":
                continue
            client_dir = month_dir / CLIENT_ID
            if client_dir.exists():
                odd_candidates = list(client_dir.glob(f"*ODD*.xlsx"))
                if odd_candidates:
                    break

if not odd_candidates:
    raise FileNotFoundError(
        f"No ODD file found for client {CLIENT_ID}. "
        f"Looked in: {odd_dir} and scanned {READY_FOR_ANALYSIS / CSM}/*/{CLIENT_ID}/. "
        f"Expected pattern: *ODD*.xlsx"
    )

odd_file = odd_candidates[0]
if len(odd_candidates) > 1:
    print(f"WARNING: Multiple ODD files found, using: {odd_file.name}")

print(f"Loading ODD file: {odd_file.name}")
# Reuse the pipeline's cached local-copy reader. step_load_file already read
# this exact ODD at startup, so the (mtime, size)-keyed temp-copy cache is warm
# here -> ~15s instead of a fresh ~6 min openpyxl parse of the 450-column
# workbook straight off the M: network share. openpyxl makes one network
# round-trip per random-access read; over SMB that single redundant read was
# the dominant TXN-runtime cost (issue #214). _read_file returns the raw,
# un-normalized columns -- identical to the previous pd.read_excel(odd_file) --
# so downstream scripts that key off 'Prod Code'/'Stat Code'/etc. are
# unaffected. Falls back to a direct read for standalone/notebook runs where
# the pipeline package isn't importable, or if the cached read errors.
try:
    from ars_analysis.pipeline.steps.load import _read_file as _read_odd
    rewards_df = _read_odd(odd_file)
except Exception:
    rewards_df = pd.read_excel(odd_file)
print(f"Loaded: {len(rewards_df):,} rows, {len(rewards_df.columns)} columns")

# ODD Columns
print("\nColumns:")
for col in rewards_df.columns:
    print(f"  {col}")
