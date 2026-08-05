"""CLI for the staging daemon.

    python -m ars_staging poll [--csm Dan] [--client 1759] [--no-aggregate]
    python -m ars_staging status --client 1759

Scheduled on the work PC via Windows Task Scheduler (every 15 min) and kicked
once on UI launch. Safe to run concurrently with analysis: staging writes to
its own tree and replaces files atomically.
"""

from __future__ import annotations

import argparse
import json
import sys

from ars_staging.manifest import load_manifest, staging_root
from ars_staging.poller import poll, staged_txn_files


def _refresh_store(client_id: str) -> None:
    """Pre-aggregate freshly staged TXN data so the click hits warm tables."""
    try:
        from ars_engine.data.txn_store import refresh

        refresh(client_id)
    except Exception as exc:  # noqa: BLE001 - staging must not die on engine errors
        print(f"staging: store refresh for {client_id} failed: {exc}")


def cmd_poll(args: argparse.Namespace) -> int:
    result = poll(
        csm_filter=args.csm,
        client_filter=args.client,
        on_client_staged=None if args.no_aggregate else _refresh_store,
    )
    return 1 if result.errors else 0


def cmd_status(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.client)
    files = manifest["files"]
    staged = [r for r in files.values() if r.get("status") == "staged"]
    aliases = [r for r in files.values() if str(r.get("status", "")).startswith("alias_of:")]
    print(
        json.dumps(
            {
                "client": args.client,
                "root": str(staging_root(args.client)),
                "last_poll": manifest.get("last_poll"),
                "files_staged": len(staged),
                "bytes_staged": sum(r.get("size", 0) for r in staged),
                "aliases": len(aliases),
                "txn_files": len(staged_txn_files(args.client)),
            },
            indent=1,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ars_staging")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("poll", help="scan the ready tree and stage new files locally")
    p.add_argument("--csm", help="only this CSM (prefix match)")
    p.add_argument("--client", help="only this client id")
    p.add_argument("--no-aggregate", action="store_true",
                   help="skip the DuckDB store refresh after staging")
    p.set_defaults(fn=cmd_poll)

    p = sub.add_parser("status", help="print one client's staging status as JSON")
    p.add_argument("--client", required=True)
    p.set_defaults(fn=cmd_status)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
