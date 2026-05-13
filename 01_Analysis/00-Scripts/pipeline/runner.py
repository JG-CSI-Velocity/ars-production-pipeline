"""Pipeline runner -- orchestrates step execution with isolation."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from loguru import logger

from ars_analysis.logging_setup import get_username
from ars_analysis.pipeline.context import PipelineContext


@dataclass(frozen=True)
class PipelineStep:
    """A single pipeline step with execution metadata.

    critical: if True, failure aborts the pipeline.
              if False, failure is logged but execution continues (e.g. archiving).
    """

    name: str
    execute: Callable[[PipelineContext], None]
    critical: bool = True


@dataclass
class StepResult:
    """Outcome of a single step execution."""

    name: str
    success: bool
    elapsed_seconds: float
    error: str = ""
    exception: Exception | None = None


def run_pipeline(
    ctx: PipelineContext,
    steps: list[PipelineStep],
) -> list[StepResult]:
    """Execute pipeline steps in order with per-step isolation.

    Returns list of StepResults for every step attempted.
    Stops on first critical failure.
    """
    results: list[StepResult] = []
    client_label = f"{ctx.client.client_id} ({ctx.client.client_name})"

    # Structured run manifest -- writes run_manifest.json next to the log.
    try:
        from ars_analysis.pipeline.manifest import RunManifest, RunStatus
        _manifest = RunManifest(
            client_id=ctx.client.client_id,
            client_name=getattr(ctx.client, "client_name", "") or "",
            csm=getattr(ctx.client, "csm", "") or "",
            month=getattr(ctx.client, "month", "") or "",
            product=getattr(ctx.settings, "product", "") if ctx.settings else "",
            output_dir=ctx.paths.base_dir,
        )
        _manifest.start_run()
        ctx.manifest = _manifest
    except Exception as _exc:
        logger.warning("manifest init failed (continuing): {err}", err=_exc)
        ctx.manifest = None

    logger.info(
        "Pipeline start: {client}, {n} steps",
        client=client_label,
        n=len(steps),
    )
    logger.log(
        "AUDIT",
        "user={user} | action=pipeline_start | client={client} | steps={n}",
        user=get_username(),
        client=ctx.client.client_id,
        n=len(steps),
    )

    _notify = ctx.progress_callback

    for step in steps:
        if _notify:
            _notify(f"Step: {step.name}...")
        logger.info("Step '{name}' starting", name=step.name)
        t0 = time.perf_counter()

        try:
            step.execute(ctx)
            elapsed = time.perf_counter() - t0
            results.append(StepResult(name=step.name, success=True, elapsed_seconds=elapsed))
            if _notify:
                _notify(f"Step {step.name} done ({elapsed:.0f}s)")
            logger.info(
                "Step '{name}' completed in {t:.1f}s",
                name=step.name,
                t=elapsed,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            error_msg = f"{type(exc).__name__}: {exc}"
            results.append(
                StepResult(
                    name=step.name,
                    success=False,
                    elapsed_seconds=elapsed,
                    error=error_msg,
                    exception=exc,
                )
            )

            if step.critical:
                logger.error(
                    "Step '{name}' FAILED (critical) after {t:.1f}s: {err}",
                    name=step.name,
                    t=elapsed,
                    err=error_msg,
                )
                if getattr(ctx, "manifest", None) is not None:
                    try:
                        from ars_analysis.pipeline.manifest import RunStatus
                        ctx.manifest.end_run(RunStatus.FAILED)
                    except Exception:
                        pass
                break
            else:
                logger.warning(
                    "Step '{name}' failed (non-critical) after {t:.1f}s: {err}",
                    name=step.name,
                    t=elapsed,
                    err=error_msg,
                )

    # Finalize manifest with the overall run status (only if not already finalized
    # by the exception path above -- FAILED takes precedence and must not be
    # overwritten with PARTIAL).
    if getattr(ctx, "manifest", None) is not None:
        try:
            from ars_analysis.pipeline.manifest import RunStatus
            if ctx.manifest.status == RunStatus.RUNNING:
                any_failed = any(not r.success and r.name != "archive" for r in results)
                ctx.manifest.end_run(RunStatus.PARTIAL if any_failed else RunStatus.OK)
        except Exception as _exc:
            logger.warning("manifest end_run failed: {err}", err=_exc)

    success_count = sum(1 for r in results if r.success)
    total_time = sum(r.elapsed_seconds for r in results)
    logger.info(
        "Pipeline done: {client} -- {ok}/{total} steps in {t:.1f}s",
        client=client_label,
        ok=success_count,
        total=len(results),
        t=total_time,
    )
    logger.log(
        "AUDIT",
        "user={user} | action=pipeline_done | client={client} | status={status} | elapsed={t:.1f}s",
        user=get_username(),
        client=ctx.client.client_id,
        status="OK" if success_count == len(results) else "FAILED",
        t=total_time,
    )

    return results
