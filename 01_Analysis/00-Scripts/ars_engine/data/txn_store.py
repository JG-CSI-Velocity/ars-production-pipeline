"""Per-client DuckDB transaction store -- the v3 replacement for the 54M-row
in-memory ``combined_df`` (txn_setup/05-combine-data.py, ~25 min per run,
OOM-prone).

Design:
- ``transactions`` holds parsed rows exactly as the legacy parse produces
  them (signed amounts, raw merchant names). Ingestion is incremental and
  keyed by (source name, size, mtime) -- only new/changed staged files are
  parsed; a re-delivered file replaces its own rows.
- ``finalize`` applies the whole-dataset legacy semantics that cannot be
  per-file: the global abs-if-median<0 sign rule, the merchant consolidation
  map over distinct names (rules loaded from their legacy home -- exact
  parity), and the per-row smart-unknown fallback by transaction_type. Then
  it materializes the aggregate tables sections actually read (<1M rows
  each), replacing what 35 ``*_data.py`` scripts each rebuilt from scratch.
- DuckDB runs with a memory limit and spills out-of-core: the 416MiB-
  allocation OOM class disappears.

``python -m ars_engine.data.txn_store refresh|verify|tables --client 1759``
``verify`` is the Wave-0 frame-level golden gate: it computes the same
aggregates in pandas from the LEGACY combined-parquet cache and diffs them
against the store's tables at rtol=1e-9.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from ars_engine.core.config import local_cache_root
from ars_engine.data import merchant_rules
from ars_engine.data.txn_ingest import coerce_types, load_transaction_file

_TXN_COLUMNS = [
    "transaction_date",
    "primary_account_num",
    "transaction_type",
    "amount",
    "mcc_code",
    "merchant_name",
    "terminal_location_1",
    "terminal_location_2",
    "terminal_id",
    "merchant_id",
    "institution",
    "card_present",
    "transaction_code",
    "source_file",
]

# Mirrors _label_for_ttype in txn_setup/07-consolidation-summary.py, in the
# same branch order. Applied to rows whose consolidated name is UNKNOWN.
_UNKNOWN_FALLBACK_SQL = """
CASE
  WHEN t IS NULL OR t IN ('NAN', 'NONE', '') THEN 'UNKNOWN MERCHANT'
  WHEN t LIKE '%ATM%' THEN 'ATM WITHDRAWAL'
  WHEN t LIKE '%FEE%' OR t IN ('SC', 'NSF', 'OD') THEN 'BANK FEE'
  WHEN t LIKE '%ACH%' THEN 'ACH TRANSFER (NO MERCHANT)'
  WHEN t LIKE '%CHK%' OR t LIKE '%CHECK%' OR t = 'CK' THEN 'CHECK (NO MERCHANT)'
  WHEN t LIKE '%XFER%' OR t LIKE '%TRANSFER%' OR t IN ('TR', 'TRF') THEN 'INTERNAL TRANSFER'
  WHEN t IN ('PIN', 'SIG', 'POS', 'DEB') THEN 'POS TRANSACTION (NO MERCHANT)'
  WHEN t LIKE '%DEP%' OR t LIKE '%DEPOSIT%' THEN 'DEPOSIT (NO MERCHANT)'
  WHEN t LIKE '%WD%' OR t LIKE '%WTHD%' OR t LIKE '%WITHDRAW%' THEN 'WITHDRAWAL (NO MERCHANT)'
  ELSE 'UNKNOWN MERCHANT'
END
"""

AGGREGATE_TABLES = (
    "monthly_by_merchant",
    "monthly_by_mcc",
    "monthly_by_type",
    "monthly_by_account",
    "account_first_last",
)


def store_path(client_id: str) -> Path:
    root = local_cache_root() / "txn-store"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{client_id}.duckdb"


def connect(
    client_id: str,
    memory_limit: str = "4GB",
    retries: int = 3,
    retry_wait_s: float = 2.0,
) -> duckdb.DuckDBPyConnection:
    """Open the client's store. DuckDB allows a single writer per database
    file, so the staging daemon's post-stage refresh and a click-time run can
    collide; retry briefly, then let the caller's error path handle it (the
    daemon simply tries again next poll)."""
    import time

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            con = duckdb.connect(str(store_path(client_id)))
            con.execute(f"SET memory_limit = '{memory_limit}'")
            return con
        except duckdb.IOException as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(retry_wait_s)
    raise duckdb.IOException(
        f"store for client {client_id} is locked by another process "
        f"(staging refresh vs. run?): {last_exc}"
    )


def _ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_date   TIMESTAMP,
            primary_account_num VARCHAR,
            transaction_type   VARCHAR,
            amount             DOUBLE,
            mcc_code           VARCHAR,
            merchant_name      VARCHAR,
            terminal_location_1 VARCHAR,
            terminal_location_2 VARCHAR,
            terminal_id        VARCHAR,
            merchant_id        VARCHAR,
            institution        VARCHAR,
            card_present       VARCHAR,
            transaction_code   VARCHAR,
            source_file        VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS ingested_files (
            name        VARCHAR PRIMARY KEY,
            size        BIGINT,
            mtime       BIGINT,
            ingested_at VARCHAR
        )
        """
    )
    con.execute("CREATE TABLE IF NOT EXISTS meta (key VARCHAR PRIMARY KEY, value VARCHAR)")


def _meta_get(con, key: str) -> str | None:
    row = con.execute("SELECT value FROM meta WHERE key = ?", [key]).fetchone()
    return row[0] if row else None


def _meta_set(con, key: str, value: str) -> None:
    con.execute("DELETE FROM meta WHERE key = ?", [key])
    con.execute("INSERT INTO meta VALUES (?, ?)", [key, value])


@dataclass
class RefreshResult:
    client_id: str
    ingested: int = 0
    rows_added: int = 0
    skipped: int = 0
    orphans_removed: int = 0
    finalized: bool = False
    errors: list[str] = field(default_factory=list)


def _source_key(f: Path) -> str:
    """Stable identity for a staged source file in the store.

    The path below the staging ``txn/`` directory ("foo.txt" or
    "2026/foo.txt"), so same-basename files at different depths never collide;
    files outside a staging tree (tests, ad-hoc ingest) fall back to basename.
    """
    parts = f.parts
    if "txn" in parts:
        idx = len(parts) - 1 - parts[::-1].index("txn")
        rel = parts[idx + 1:]
        if rel:
            return "/".join(rel)
    return f.name


def refresh(
    client_id: str,
    staged_files: list[Path] | None = None,
    memory_limit: str = "4GB",
    log=print,
) -> RefreshResult:
    """Ingest new/changed staged TXN files and rebuild derived tables."""
    if staged_files is None:
        from ars_staging.poller import staged_txn_files

        staged_files = staged_txn_files(client_id)

    result = RefreshResult(client_id=client_id)
    con = connect(client_id, memory_limit)
    try:
        _ensure_schema(con)
        known = {
            name: (size, mtime)
            for name, size, mtime in con.execute(
                "SELECT name, size, mtime FROM ingested_files"
            ).fetchall()
        }

        changed = False
        for f in staged_files:
            key = _source_key(f)
            try:
                stat = f.stat()
            except OSError as exc:
                result.errors.append(f"{key}: {exc}")
                continue
            if known.get(key) == (stat.st_size, int(stat.st_mtime)):
                result.skipped += 1
                continue
            try:
                df = coerce_types(load_transaction_file(f, log=log), log=log)
            except (ValueError, OSError, pd.errors.ParserError) as exc:
                result.errors.append(f"{key}: {exc}")
                log(f"txn_store: ERROR parsing {key}: {exc}")
                continue
            for col in _TXN_COLUMNS:
                if col not in df.columns:
                    df[col] = None
            df = df[_TXN_COLUMNS]
            df["source_file"] = key
            con.register("_incoming", df)
            con.execute("BEGIN")
            # Committed ingest without a finalize (crash/sleep between this
            # commit and finalize()) must force a rebuild next refresh --
            # otherwise aggregates permanently exclude these rows while
            # `transactions` contains them. Setting the marker inside the
            # ingest transaction closes that window.
            _meta_set(con, "finalize_pending", "1")
            con.execute("DELETE FROM transactions WHERE source_file = ?", [key])
            con.execute("INSERT INTO transactions SELECT * FROM _incoming")
            con.execute("DELETE FROM ingested_files WHERE name = ?", [key])
            con.execute(
                "INSERT INTO ingested_files VALUES (?, ?, ?, ?)",
                [key, stat.st_size, int(stat.st_mtime),
                 datetime.now(timezone.utc).isoformat(timespec="seconds")],
            )
            con.execute("COMMIT")
            con.unregister("_incoming")
            result.ingested += 1
            result.rows_added += len(df)
            changed = True
            log(f"txn_store: ingested {key} ({len(df):,} rows)")

        # Reconcile: a source file that left the staged set (demoted to a
        # dedupe alias, or deleted upstream) must not keep contributing rows
        # -- otherwise a re-delivery under an alphabetically-earlier name
        # silently DOUBLES every dollar/volume aggregate for its month. An
        # empty staged list is treated as a staging glitch, never a mass
        # delete: the store is left untouched.
        if staged_files:
            current = [_source_key(f) for f in staged_files]
            ph = ",".join("?" * len(current))
            orphan_rows = con.execute(
                f"SELECT count(*) FROM transactions WHERE source_file NOT IN ({ph})",
                current,
            ).fetchone()[0]
            if orphan_rows:
                orphan_names = [
                    r[0] for r in con.execute(
                        f"SELECT DISTINCT source_file FROM transactions "
                        f"WHERE source_file NOT IN ({ph})",
                        current,
                    ).fetchall()
                ]
                # Same crash window as ingest: orphan removal mutates
                # `transactions`, so a kill before finalize() must still
                # trigger a rebuild on the next refresh. One transaction so a
                # kill between the two DELETEs can't leave rows deleted while
                # ingested_files still claims the file (r2 audit).
                con.execute("BEGIN")
                _meta_set(con, "finalize_pending", "1")
                con.execute(
                    f"DELETE FROM transactions WHERE source_file NOT IN ({ph})", current
                )
                con.execute(
                    f"DELETE FROM ingested_files WHERE name NOT IN ({ph})", current
                )
                con.execute("COMMIT")
                result.orphans_removed = int(orphan_rows)
                changed = True
                log(
                    f"txn_store: removed {orphan_rows:,} orphaned rows from "
                    f"{len(orphan_names)} de-staged file(s): {', '.join(orphan_names)}"
                )

        rules_stale = _meta_get(con, "rules_mtime") != str(merchant_rules.rules_mtime())
        aggregates_missing = any(
            not con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [t]
            ).fetchone()[0]
            for t in AGGREGATE_TABLES
        )
        # finalize_pending survives a crash mid-finalize (Windows sleep/reboot
        # mid-refresh): without it, the next refresh would see unchanged inputs
        # plus present-but-stale aggregate tables and silently skip the rebuild.
        finalize_interrupted = _meta_get(con, "finalize_pending") == "1"
        if changed or rules_stale or aggregates_missing or finalize_interrupted:
            if finalize_interrupted and not changed:
                log("txn_store: previous finalize was interrupted -- rebuilding aggregates")
            finalize(con, log=log)
            result.finalized = True
    finally:
        con.close()
    return result


def finalize(con: duckdb.DuckDBPyConnection, log=print) -> None:
    """Whole-dataset semantics + aggregate materialization.

    Crash-safe: finalize_pending is set first and cleared last, so an
    interrupted finalize is always retried on the next refresh instead of
    leaving present-but-stale aggregate tables that nothing would rebuild.
    """
    n = con.execute("SELECT count(*) FROM transactions").fetchone()[0]
    if n == 0:
        # transactions emptied (e.g. every source file de-staged): the OLD
        # aggregate tables would otherwise keep serving pre-removal numbers
        # forever. Drop them so readers see an empty store, then clear the
        # marker so we don't retry finalize pointlessly (r2 audit finding).
        for t in AGGREGATE_TABLES:
            con.execute(f"DROP TABLE IF EXISTS {t}")
        _meta_set(con, "finalize_pending", "0")
        log("txn_store: no transactions; dropped stale aggregates")
        return
    _meta_set(con, "finalize_pending", "1")

    # 1. Global sign rule (05-combine-data: abs() when the combined median < 0)
    median = con.execute("SELECT median(amount) FROM transactions").fetchone()[0]
    abs_amounts = median is not None and median < 0
    _meta_set(con, "abs_amounts", "1" if abs_amounts else "0")
    amount_expr = "abs(amount)" if abs_amounts else "amount"
    if abs_amounts:
        log("txn_store: negative median amount -- normalizing with abs() (legacy rule)")

    # 2. Merchant map over distinct names (incremental unless the rules changed)
    rules_mtime = str(merchant_rules.rules_mtime())
    rules_stale = _meta_get(con, "rules_mtime") != rules_mtime
    con.execute(
        "CREATE TABLE IF NOT EXISTS merchant_map "
        "(merchant_name VARCHAR PRIMARY KEY, merchant_consolidated VARCHAR)"
    )
    if rules_stale:
        con.execute("DELETE FROM merchant_map")
        log("txn_store: consolidation rules changed -- rebuilding merchant map")
    missing = [
        r[0]
        for r in con.execute(
            """
            SELECT DISTINCT t.merchant_name FROM transactions t
            LEFT JOIN merchant_map m ON t.merchant_name = m.merchant_name
            WHERE t.merchant_name IS NOT NULL AND m.merchant_name IS NULL
            """
        ).fetchall()
    ]
    if missing:
        log(f"txn_store: consolidating {len(missing):,} new merchant name(s)")
        mapping = merchant_rules.build_merchant_map(missing)
        con.register("_map_new", mapping)
        con.execute("INSERT INTO merchant_map SELECT * FROM _map_new")
        con.unregister("_map_new")

    # 3. Resolved view: consolidated merchant with the smart-unknown fallback
    con.execute(
        f"""
        CREATE OR REPLACE VIEW txn_resolved AS
        WITH joined AS (
            SELECT t.*,
                   coalesce(m.merchant_consolidated, 'UNKNOWN MERCHANT') AS mc0,
                   upper(trim(cast(t.transaction_type AS VARCHAR))) AS t
            FROM transactions t
            LEFT JOIN merchant_map m ON t.merchant_name = m.merchant_name
        )
        SELECT * EXCLUDE (mc0, t),
               CASE WHEN mc0 = 'UNKNOWN MERCHANT'
                    THEN {_UNKNOWN_FALLBACK_SQL}
                    ELSE mc0 END AS merchant_consolidated,
               {amount_expr} AS amount_n
        FROM joined
        """
    )

    # 4. Aggregates -- the frames sections read. NULL group keys (dates, mcc,
    #    type, account) are excluded to match pandas groupby's default
    #    dropna=True behavior in every legacy script; merchant_consolidated
    #    is never NULL (coalesce to UNKNOWN, same as legacy fillna).
    aggregates = {
        "monthly_by_merchant": """
            SELECT date_trunc('month', transaction_date)::DATE AS month,
                   merchant_consolidated,
                   count(*) AS txn_count,
                   sum(amount_n) AS total_amount,
                   count(DISTINCT primary_account_num) AS unique_accounts
            FROM txn_resolved WHERE transaction_date IS NOT NULL
            GROUP BY 1, 2
        """,
        "monthly_by_mcc": """
            SELECT date_trunc('month', transaction_date)::DATE AS month,
                   mcc_code,
                   count(*) AS txn_count,
                   sum(amount_n) AS total_amount,
                   count(DISTINCT primary_account_num) AS unique_accounts
            FROM txn_resolved
            WHERE transaction_date IS NOT NULL AND mcc_code IS NOT NULL
            GROUP BY 1, 2
        """,
        "monthly_by_type": """
            SELECT date_trunc('month', transaction_date)::DATE AS month,
                   transaction_type,
                   count(*) AS txn_count,
                   sum(amount_n) AS total_amount,
                   count(DISTINCT primary_account_num) AS unique_accounts
            FROM txn_resolved
            WHERE transaction_date IS NOT NULL AND transaction_type IS NOT NULL
            GROUP BY 1, 2
        """,
        "monthly_by_account": """
            SELECT date_trunc('month', transaction_date)::DATE AS month,
                   primary_account_num,
                   count(*) AS txn_count,
                   sum(amount_n) AS total_amount
            FROM txn_resolved
            WHERE transaction_date IS NOT NULL AND primary_account_num IS NOT NULL
            GROUP BY 1, 2
        """,
        "account_first_last": """
            SELECT primary_account_num,
                   min(transaction_date) AS first_txn,
                   max(transaction_date) AS last_txn,
                   count(*) AS txn_count,
                   sum(amount_n) AS total_amount
            FROM txn_resolved
            WHERE transaction_date IS NOT NULL AND primary_account_num IS NOT NULL
            GROUP BY 1
        """,
    }
    for name, sql in aggregates.items():
        con.execute(f"CREATE OR REPLACE TABLE {name} AS {sql}")

    # Success markers last: rules_mtime only counts once the tables that bake
    # it in actually exist, and clearing finalize_pending commits the run.
    _meta_set(con, "rules_mtime", rules_mtime)
    _meta_set(con, "finalized_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _meta_set(con, "finalize_pending", "0")
    log(f"txn_store: finalized {len(aggregates)} aggregate tables over {n:,} rows")


# ---------------------------------------------------------------------------
# Frame-level golden verification against the LEGACY combined parquet cache
# ---------------------------------------------------------------------------


def _legacy_aggregates(combined: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute the store's aggregate tables in pure pandas from the legacy
    combined_df (parquet cache). The legacy frame already carries
    merchant_consolidated (incl. unknown fallback) and post-abs amounts."""
    df = combined.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df = df[df["transaction_date"].notna()]
    df["month"] = df["transaction_date"].dt.to_period("M").dt.to_timestamp().dt.date

    def agg(keys: list[str], with_accounts: bool = True) -> pd.DataFrame:
        g = df.groupby(keys, dropna=True, observed=True)
        out = g.agg(
            txn_count=("amount", "size"),
            total_amount=("amount", "sum"),
        )
        if with_accounts:
            out["unique_accounts"] = g["primary_account_num"].nunique()
        return out.reset_index()

    first_last = (
        df.groupby("primary_account_num", dropna=True, observed=True)
        .agg(
            first_txn=("transaction_date", "min"),
            last_txn=("transaction_date", "max"),
            txn_count=("amount", "size"),
            total_amount=("amount", "sum"),
        )
        .reset_index()
    )
    return {
        "monthly_by_merchant": agg(["month", "merchant_consolidated"]),
        "monthly_by_mcc": agg(["month", "mcc_code"]),
        "monthly_by_type": agg(["month", "transaction_type"]),
        "monthly_by_account": agg(["month", "primary_account_num"], with_accounts=False),
        "account_first_last": first_last,
    }


def read_table(client_id: str, table: str) -> pd.DataFrame:
    con = connect(client_id)
    try:
        return con.execute(f"SELECT * FROM {table}").df()
    finally:
        con.close()


def verify(client_id: str, combined_parquet: Path | str, rtol: float = 1e-9, log=print) -> int:
    """Diff the store's aggregates against pandas aggregates of the legacy
    combined parquet cache. Returns the number of differences."""
    from ars_parity.compare import ComparePolicy, Diff, _compare_tables, summarize
    from ars_parity.normalize import normalize_df

    combined = pd.read_parquet(combined_parquet)
    legacy = _legacy_aggregates(combined)
    policy = ComparePolicy(rtol=rtol)
    diffs: list[Diff] = []
    for name, ldf in legacy.items():
        sdf = read_table(client_id, name)
        # A missing column is a hard diff, never silently intersected away.
        missing_cols = [c for c in ldf.columns if c not in sdf.columns]
        if missing_cols:
            diffs.append(
                Diff("sheet", name, "<columns>", "", list(ldf.columns), list(sdf.columns))
            )
            continue
        # Column order: legacy defines the canonical order. Calendar keys
        # (month/day) come back from DuckDB as midnight timestamps and from
        # pandas as date objects -- coerce both sides to dates.
        sdf = sdf[list(ldf.columns)].copy()
        ldf = ldf.copy()
        for col in ("month", "day"):
            for frame in (ldf, sdf):
                if col in frame.columns:
                    frame[col] = pd.to_datetime(frame[col]).dt.date
        _compare_tables(name, normalize_df(ldf), normalize_df(sdf), policy, diffs)
    log(summarize(diffs))
    return len(diffs)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="ars_engine.data.txn_store")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("refresh", help="ingest staged files + rebuild aggregates")
    p.add_argument("--client", required=True)
    p.set_defaults(cmd_name="refresh")

    p = sub.add_parser("verify", help="frame-level golden check vs legacy combined parquet")
    p.add_argument("--client", required=True)
    p.add_argument("--parquet", help="legacy combined cache (default: resolve via txn_cache)")
    p.add_argument("--rtol", type=float, default=1e-9)
    p.set_defaults(cmd_name="verify")

    p = sub.add_parser("tables", help="show table row counts")
    p.add_argument("--client", required=True)
    p.set_defaults(cmd_name="tables")

    args = parser.parse_args(argv)
    if args.cmd_name == "refresh":
        r = refresh(args.client)
        print(json.dumps({"ingested": r.ingested, "rows_added": r.rows_added,
                          "skipped": r.skipped, "finalized": r.finalized,
                          "errors": r.errors}, indent=1))
        return 1 if r.errors else 0
    if args.cmd_name == "verify":
        parquet = args.parquet
        if not parquet:
            legacy_local = (
                local_cache_root() / "txn-combined" / f"{args.client}_combined_cache.parquet"
            )
            if not legacy_local.exists():
                print(f"ERROR: no legacy combined cache at {legacy_local}; pass --parquet")
                return 2
            parquet = legacy_local
        return 1 if verify(args.client, parquet, rtol=args.rtol) else 0
    if args.cmd_name == "tables":
        con = connect(args.client)
        try:
            for t in ("transactions", "merchant_map", *AGGREGATE_TABLES):
                try:
                    cnt = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                    print(f"{t:24s} {cnt:>12,}")
                except duckdb.CatalogException:
                    print(f"{t:24s} {'<missing>':>12}")
        finally:
            con.close()
        return 0
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(main())
