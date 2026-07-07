"""Step: load transaction frames onto ctx.txn (the TXN-side enabler).

Structured TXN modules read transaction data from ``ctx.txn`` (parallel to how
ARS modules read ``ctx.subsets``). This step is the single place that populates
it. It does NOT reimplement loading/filtering -- it reuses the exact same code
the exec path already uses:

    txn_wrapper.prepare_shared_namespace(ctx)
        -> runs txn_setup once (builds combined_df + rewards_df from the TXN
           files on disk + ODD), optimizes memory, then applies
           _inject_eligible_filter (the 4-denominator framework).

So ``ctx.txn`` holds the SAME frames the exec cells see -- just lifted off the
mutable namespace and onto a typed accessor.

Returns the fully-populated exec namespace so a caller (e.g. the equivalence
diff harness) can also drive the old exec wrapper against the identical
namespace, guaranteeing both paths start from the same data.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from ars_analysis.pipeline.context import PipelineContext, TxnData


def step_txn_load(ctx: PipelineContext) -> dict[str, Any]:
    """Build combined/rewards frames and store them on ``ctx.txn``.

    Reuses ``prepare_shared_namespace`` (which runs txn_setup + the eligible
    filter). Populates ``ctx.txn`` and returns the exec namespace ``ns`` so the
    same data can drive the exec wrapper in a diff harness.
    """
    # Imported lazily: txn_wrapper forces the matplotlib Agg backend at import
    # time, and this step is only invoked on the TXN path.
    from ars_analysis.analytics.txn_wrapper import prepare_shared_namespace

    ns = prepare_shared_namespace(ctx)

    ctx.txn = TxnData(
        combined=ns.get("combined_df"),
        rewards=ns.get("rewards_df"),
        combined_all=ns.get("combined_df_all"),
        rewards_all=ns.get("rewards_df_all"),
        eligible_accounts=set(ns.get("ELIGIBLE_ACCOUNTS") or set()),
    )

    combined = ctx.txn.combined
    n_rows = len(combined) if combined is not None and hasattr(combined, "__len__") else 0
    logger.info(
        "ctx.txn populated: combined={rows:,} rows, eligible_accounts={ea:,}",
        rows=n_rows, ea=len(ctx.txn.eligible_accounts),
    )
    return ns
