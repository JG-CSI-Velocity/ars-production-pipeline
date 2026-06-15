"""End-to-end proof that competitor detection works for District 1 (CT).

Owner report (2026-06-11): client 1453 (Connex CU, Connecticut) shows ZERO
top_25_fed_district transactions. These tests exec the real competitor
config with CLIENT_ID='1453' and run realistic CT card descriptors through
tag_competitors(). If they pass, the code path is sound and a zero on a
real run means a runtime config problem -- most likely the CLIENT_ID lookup
missing and fed_district silently defaulting to '12' (San Francisco), whose
fingerprint test_wrong_district_yields_zero_top25 documents.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "analytics" / "competition" / "01_competitor_config.py"
)


def _load_config(client_id: str) -> dict:
    ns: dict = {"CLIENT_ID": client_id, "pd": pd}
    code = _CONFIG.read_text(encoding="utf-8")
    exec(compile(code, str(_CONFIG), "exec"), ns)  # noqa: S102 -- mirrors txn_wrapper
    return ns


_CT_DESCRIPTORS = pd.DataFrame({
    "merchant_consolidated": [
        # District-1 top-25 regionals as they appear in card data
        "WEBSTER BANK PAYMENT NEW HAVEN CT",
        "POS DEBIT CITIZENS BANK NA PROVIDENCE RI",
        "LIBERTY BANK LOAN PMT MIDDLETOWN CT",
        "ACH DEBIT SANTANDER CONSUMER USA",
        # 1453 client-specific lists
        "AMERICAN EAGLE FINANCIAL CU E HARTFORD",
        "ION BANK NAUGATUCK CT",
        # noise
        "STOP & SHOP 0612 NORTH HAVEN CT",
        "DUNKIN #341775 HAMDEN CT",
    ]
})


def test_district_1_descriptors_are_tagged_for_1453():
    ns = _load_config("1453")
    assert ns["CLIENT_FED_DISTRICT"] == "1"

    df = ns["tag_competitors"](_CT_DESCRIPTORS.copy())
    cats = df["competitor_category"].astype(str).tolist()

    assert cats.count("top_25_fed_district") >= 3, cats  # Webster/Citizens/Liberty
    assert "credit_unions" in cats, cats                 # American Eagle Financial
    assert "local_banks" in cats, cats                   # Ion Bank
    assert df["competitor_category"].isna().tolist()[-2:] == [True, True]  # noise untagged


def test_client_id_lookup_tolerates_int_and_padding():
    for cid in (1453, " 1453 "):
        ns = _load_config(cid)  # type: ignore[arg-type]
        assert ns["CLIENT_FED_DISTRICT"] == "1", f"lookup failed for {cid!r}"


def test_wrong_district_yields_zero_top25():
    """The failure fingerprint: an unknown CLIENT_ID falls back to District 12
    (San Francisco), and the same CT data produces ZERO top-25 matches."""
    ns = _load_config("0000")
    assert ns["CLIENT_FED_DISTRICT"] == "12"

    df = ns["tag_competitors"](_CT_DESCRIPTORS.copy())
    cats = df["competitor_category"].astype(str).tolist()
    assert cats.count("top_25_fed_district") == 0


# ---------------------------------------------------------------------------
# Dedup optimization (issue #214): tag_competitors tags the DISTINCT merchant
# strings and broadcasts back. These tests pin that the broadcast is identical
# to applying the matching core to every row (the pre-optimization behavior),
# so the speedup cannot silently change which transactions get tagged.
# ---------------------------------------------------------------------------

import numpy as np  # noqa: E402

# Heavy duplication + edge cases the dedup/broadcast must survive: repeated
# merchants, an FP-guard collision (NEIMAN MARCUS vs MARCUS), a venue collision
# (CHASE FIELD vs CHASE), empty string, and a None.
_DEDUP_FRAME = pd.DataFrame({
    "merchant_consolidated": (
        _CT_DESCRIPTORS["merchant_consolidated"].tolist() * 40
        + ["NEIMAN MARCUS DALLAS TX", "CHASE FIELD PHOENIX AZ", "", None]
        + ["WEBSTER BANK PAYMENT NEW HAVEN CT"] * 25
    )
})


def test_dedup_tagging_matches_rowwise_reference():
    """tag_competitors (dedup + broadcast) must yield the same per-row category
    codes as running the pure matching core over every row."""
    ns = _load_config("1453")
    cat_names = list(ns["COMPETITOR_MERCHANTS"].keys())

    # Reference: the pre-dedup path -- match every row directly.
    ref_codes = np.asarray(
        ns["_compute_category_codes"](_DEDUP_FRAME["merchant_consolidated"].astype(str)),
        dtype="int8",
    )

    out = ns["tag_competitors"](_DEDUP_FRAME.copy())
    got_codes = out["competitor_category"].cat.codes.to_numpy()

    assert got_codes.shape == ref_codes.shape
    assert np.array_equal(got_codes, ref_codes), (
        "dedup broadcast diverged from row-wise tagging"
    )
    # Categories line up with the same code ordering used by the reference.
    assert list(out["competitor_category"].cat.categories) == cat_names


def test_dedup_preserves_row_order_and_duplicates():
    """Duplicated merchants get the same tag on every occurrence, and row order
    is preserved (broadcast must not shuffle or collapse rows)."""
    ns = _load_config("1453")
    out = ns["tag_competitors"](_DEDUP_FRAME.copy())

    assert len(out) == len(_DEDUP_FRAME)  # no rows dropped/collapsed
    webster = out.loc[
        _DEDUP_FRAME["merchant_consolidated"] == "WEBSTER BANK PAYMENT NEW HAVEN CT",
        "competitor_category",
    ].astype(str)
    assert (webster == "top_25_fed_district").all()  # every duplicate tagged identically
