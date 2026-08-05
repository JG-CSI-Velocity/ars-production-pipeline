"""ars_parity -- golden-master parity harness for the v3 migration.

Captures the legacy pipeline's numeric outputs per section (never pixels),
compares the v3 engine's outputs against them, and records per-section
sign-off. A section's engine_flags entry may only move to "new" once approved
against >=2 real clients on the work PC.

    python -m ars_parity capture --client 1759 --month 2026.06
    python -m ars_parity check   --client 1759 --month 2026.06 --section txn.merchant
    python -m ars_parity approve --section txn.merchant --by JG
"""
