# ===========================================================================
# DETECTION DIAGNOSTIC -- Audit competitor tagging for this client
# ===========================================================================
# Run this when category counts look wrong (empty local_banks / credit_unions,
# surprisingly low BNPL, etc.). It audits:
#
#   1. Whether CLIENT_ID has a CLIENT_CONFIGS entry in cell 01. If not, the
#      client's credit_unions + local_banks patterns are empty, so nothing
#      ever tags into those buckets. This is the #1 cause of "no local banks
#      or CU competitors" in a report.
#   2. How many transactions are tagged per category (including zeros).
#   3. Top merchants in each category -- sanity check the matches.
#   4. Unmatched merchants containing financial keywords -- competitors
#      that exist in the data but aren't in config yet. Copy these into
#      the client's CLIENT_CONFIGS entry.
#   5. Unmatched BNPL-looking merchants (AFFIRM / KLARNA / AFTERPAY / SEZZLE
#      / PAY anywhere in the name, not just starts_with).
#
# Runs at end of the competition section. Auto-skips with a clear message
# when the prerequisite state isn't present (e.g. detection skipped). Also
# writes a `competition_diagnostic.txt` artifact alongside the run output
# so the UI can surface it as a downloadable for issue #122.
# ===========================================================================

import io
import sys
from pathlib import Path

import pandas as pd


def _have(name):
    """True iff `name` is bound in the calling notebook namespace."""
    return name in globals()


def _check_prereqs():
    missing = []
    for var in ("competitor_txns", "combined_df", "COMPETITOR_MERCHANTS", "ALL_CATEGORIES"):
        if var not in globals():
            missing.append(var)
    return missing


def _run_diagnostic_body(out):
    """Write the diagnostic report to `out` (any file-like object).

    Reads from globals() the upstream state that earlier cells populated
    (CLIENT_ID, CLIENT_CONFIGS, competitor_txns, combined_df,
    COMPETITOR_MERCHANTS, ALL_CATEGORIES).
    """
    p = lambda s="": print(s, file=out)

    p("=" * 72)
    p("COMPETITOR DETECTION DIAGNOSTIC")
    p("=" * 72)

    # --- 1. CLIENT_ID + CLIENT_CONFIGS membership ---
    client_id = globals().get("CLIENT_ID", "")
    client_configs = globals().get("CLIENT_CONFIGS", None)
    has_cfg = client_configs is not None
    configured = has_cfg and client_id in client_configs
    p(f"\n  CLIENT_ID               : {client_id or '(not set)'}")
    p(f"  CLIENT_CONFIGS present  : {has_cfg}")
    p(f"  Entry for this client   : {configured}")
    if has_cfg and not configured and client_id:
        p()
        p("  >>> WARNING: this client has no CLIENT_CONFIGS entry in cell 01.")
        p("  >>> credit_unions / local_banks / custom patterns are EMPTY.")
        p("  >>> Nothing will tag into 'Credit Unions' or 'Local Banks' categories.")
        p()
        p(f"  >>> FIX: add an entry to CLIENT_CONFIGS in 01_competitor_config.py:")
        p(f"  >>>   '{client_id}': {{")
        p(f"  >>>       'fed_district': '<1-12>',")
        p(f"  >>>       'credit_unions': ['SOME CU', 'ANOTHER CU', ...],")
        p(f"  >>>       'local_banks':   ['SOME BANK', ...],")
        p(f"  >>>       'custom': [], 'rollups': {{}},")
        p(f"  >>>   }},")

    competitor_txns = globals()["competitor_txns"]
    combined_df = globals()["combined_df"]
    COMPETITOR_MERCHANTS = globals()["COMPETITOR_MERCHANTS"]
    ALL_CATEGORIES = globals()["ALL_CATEGORIES"]

    # --- 2. Per-category counts ---
    p()
    p("-" * 72)
    p("PER-CATEGORY COUNTS (all configured categories, including empty)")
    p("-" * 72)
    cat_counts = (
        competitor_txns["competitor_category"]
        .value_counts(dropna=False, sort=False)
        .reindex(ALL_CATEGORIES, fill_value=0)
    )
    cat_accts = {}
    for cat in ALL_CATEGORIES:
        sub = competitor_txns[competitor_txns["competitor_category"] == cat]
        cat_accts[cat] = sub["primary_account_num"].nunique() if len(sub) else 0

    for cat in ALL_CATEGORIES:
        n = int(cat_counts.get(cat, 0))
        a = int(cat_accts.get(cat, 0))
        patterns = COMPETITOR_MERCHANTS.get(cat, {})
        n_pats = len(patterns.get("starts_with", [])) + len(patterns.get("exact", []))
        flag = "  <-- EMPTY (no patterns configured)" if n_pats == 0 else ""
        p(f"  {cat:<25s}  {n:>10,} txns  {a:>8,} accts  ({n_pats} patterns){flag}")

    # --- 3. Top merchants per populated category ---
    p()
    p("-" * 72)
    p("TOP 5 MERCHANTS PER POPULATED CATEGORY")
    p("-" * 72)
    for cat in ALL_CATEGORIES:
        sub = competitor_txns[competitor_txns["competitor_category"] == cat]
        if len(sub) == 0:
            continue
        top = (sub.groupby("competitor_match")
               .size().sort_values(ascending=False).head(5))
        p(f"\n  [{cat}]")
        for name, cnt in top.items():
            p(f"    {cnt:>8,}  {name}")

    # --- 4. Unmatched financial-looking merchants ---
    p()
    p("-" * 72)
    p("TOP 30 UNMATCHED MERCHANTS WITH FINANCIAL KEYWORDS")
    p("(Candidates to add to credit_unions / local_banks / custom)")
    p("-" * 72)
    untagged = combined_df[combined_df["competitor_category"].isna()]
    if len(untagged):
        m_upper = untagged["merchant_consolidated"].astype(str).str.upper()
        fin_mask = m_upper.str.contains(
            r"BANK|CREDIT UNION|\bCU\b|FEDERAL CREDIT|SAVINGS|MORTGAGE|FINANCIAL|LENDING",
            regex=True, na=False,
        )
        fin = untagged[fin_mask]
        if len(fin):
            top_fin = (fin.groupby("merchant_consolidated")
                       .size().sort_values(ascending=False).head(30))
            for name, cnt in top_fin.items():
                p(f"    {cnt:>8,}  {name}")
        else:
            p("    (none found)")
    else:
        p("    (no untagged transactions in combined_df)")

    # --- 5. BNPL audit ---
    p()
    p("-" * 72)
    p("BNPL AUDIT -- any merchant containing AFFIRM / KLARNA / AFTERPAY / "
      "SEZZLE / ZIP / QUADPAY / SPLITIT")
    p("(Matched: already tagged. Unmatched: probably a detection gap.)")
    p("-" * 72)
    bnpl_regex = r"AFFIRM|KLARNA|AFTERPAY|SEZZLE|\bZIP PAY\b|QUADPAY|SPLITIT"
    all_m_upper = combined_df["merchant_consolidated"].astype(str).str.upper()
    hits = combined_df[all_m_upper.str.contains(bnpl_regex, regex=True, na=False)]
    if len(hits):
        grouped = (hits.groupby(["merchant_consolidated", "competitor_category"],
                                dropna=False, observed=True)
                   .size().reset_index(name="txns")
                   .sort_values("txns", ascending=False)
                   .head(30))
        for _, row in grouped.iterrows():
            cat = row["competitor_category"]
            cat_s = str(cat) if pd.notna(cat) else "UNMATCHED"
            tag = f"[{cat_s}]"
            p(f"    {int(row['txns']):>8,}  {tag:<18s}  {row['merchant_consolidated']}")
    else:
        p("    (no BNPL-like merchant names found anywhere in combined_df)")

    p()
    p("=" * 72)
    p("END DIAGNOSTIC")
    p("=" * 72)


def _resolve_output_path():
    """Resolve the file path for the diagnostic artifact.

    Prefer ctx.paths.client_dir when running inside the pipeline; fall back
    to CWD when running standalone.
    """
    ctx = globals().get("ctx", None)
    try:
        target_dir = Path(ctx.paths.client_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / "competition_diagnostic.txt"
    except Exception:
        return Path("competition_diagnostic.txt")


# --- Entry point ---
_missing = _check_prereqs()
if _missing:
    # Detection step probably didn't run (or this cell ran out of order).
    # Print a brief skip message but DON'T crash -- the section's other
    # diagnostic cells may still produce useful output.
    print()
    print("=" * 72)
    print("COMPETITOR DETECTION DIAGNOSTIC -- SKIPPED")
    print("=" * 72)
    print(f"  Missing prerequisites: {', '.join(_missing)}")
    print(f"  Detection (02_competitor_detection.py) may not have run.")
    print(f"  Re-run the competition section end-to-end and the diagnostic")
    print(f"  will execute automatically.")
    print("=" * 72)
else:
    # Capture the diagnostic output to BOTH stdout (so it appears in the
    # run log streamed to the UI) AND a file artifact next to the analysis
    # output (so the UI can surface a download link in the completion card).
    _buffer = io.StringIO()
    _run_diagnostic_body(_buffer)
    _text = _buffer.getvalue()
    # Mirror to stdout so the UI's run-log polling captures it.
    sys.stdout.write(_text)
    sys.stdout.flush()
    # Persist as artifact.
    try:
        _diag_path = _resolve_output_path()
        _diag_path.write_text(_text, encoding="utf-8")
        print(f"\n  Diagnostic saved to: {_diag_path}")
    except Exception as _exc:
        print(f"\n  WARNING: could not save diagnostic artifact ({_exc})")
