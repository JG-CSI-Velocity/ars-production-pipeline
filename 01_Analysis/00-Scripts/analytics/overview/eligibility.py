"""A3: Eligibility Funnel -- progressive filtering with drop-off tracking."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.pipeline.context import PipelineContext
from ars_analysis.shared.charts import draw_funnel


@register
class EligibilityFunnel(AnalysisModule):
    """Eligibility funnel showing progressive account filtering."""

    module_id = "overview.eligibility"
    display_name = "Eligibility Funnel"
    section = "overview"
    required_columns = ("Stat Code", "Product Code", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A3: Eligibility Funnel for {client}", client=ctx.client.client_id)
        data = ctx.data
        if data is None or data.empty:
            return [
                AnalysisResult(
                    slide_id="A3",
                    title="Eligibility Funnel",
                    success=False,
                    error="No data loaded",
                )
            ]

        ta = len(data)

        # Stage 2: Open accounts
        oa = ctx.subsets.open_accounts
        oc = len(oa) if oa is not None else 0

        # Stage 3: + Eligible Stat Code
        esc = ctx.client.eligible_stat_codes
        if oa is not None and esc and "Stat Code" in oa.columns:
            stat_filtered = oa[oa["Stat Code"].isin(esc)]
            sc = len(stat_filtered)
        else:
            stat_filtered = oa if oa is not None else pd.DataFrame()
            sc = len(stat_filtered)

        # Stage 4: + Eligible Product Code
        epc = ctx.client.eligible_prod_codes
        if not stat_filtered.empty and epc and "Product Code" in stat_filtered.columns:
            prod_filtered = stat_filtered[stat_filtered["Product Code"].isin(epc)]
            pc = len(prod_filtered)
        else:
            prod_filtered = stat_filtered
            pc = len(prod_filtered)

        # Stage 5: + Mailable (optional -- skip if no config)
        em = ctx.client.eligible_mailable
        include_mailable = bool(em) and "Mailable?" in data.columns
        if include_mailable and not prod_filtered.empty:
            mail_filtered = prod_filtered[prod_filtered["Mailable?"].isin(em)]
            mc = len(mail_filtered)
        else:
            mc = pc  # same as previous stage

        # Stage 6: Final eligible (from subsets)
        ed = ctx.subsets.eligible_data
        ec = len(ed) if ed is not None else 0

        # Build funnel rows
        stages: list[dict] = [
            {
                "Stage": "1. Total Accounts",
                "Count": ta,
                "Pct of Total": 1.0,
                "Drop-off": 0,
                "Drop-off %": 0.0,
            },
            {
                "Stage": "2. Open Accounts",
                "Count": oc,
                "Pct of Total": oc / ta if ta else 0,
                "Drop-off": ta - oc,
                "Drop-off %": (ta - oc) / ta if ta else 0,
            },
            {
                "Stage": "3. + Eligible Stat Code",
                "Count": sc,
                "Pct of Total": sc / ta if ta else 0,
                "Drop-off": oc - sc,
                "Drop-off %": (oc - sc) / oc if oc else 0,
            },
            {
                "Stage": "4. + Eligible Product Code",
                "Count": pc,
                "Pct of Total": pc / ta if ta else 0,
                "Drop-off": sc - pc,
                "Drop-off %": (sc - pc) / sc if sc else 0,
            },
        ]

        if include_mailable:
            stages.append(
                {
                    "Stage": "5. + Mailable",
                    "Count": mc,
                    "Pct of Total": mc / ta if ta else 0,
                    "Drop-off": pc - mc,
                    "Drop-off %": (pc - mc) / pc if pc else 0,
                }
            )

        # Final eligible stage
        prev_count = mc if include_mailable else pc
        eligible_label = f"{'6' if include_mailable else '5'}. ELIGIBLE"
        stages.append(
            {
                "Stage": eligible_label,
                "Count": ec,
                "Pct of Total": ec / ta if ta else 0,
                "Drop-off": prev_count - ec,
                "Drop-off %": (prev_count - ec) / prev_count if prev_count else 0,
            }
        )

        funnel = pd.DataFrame(stages)

        # P/B split rows
        ep = ctx.subsets.eligible_personal
        eb = ctx.subsets.eligible_business
        ep_count = len(ep) if ep is not None else 0
        eb_count = len(eb) if eb is not None else 0

        if ec > 0:
            split_rows = pd.DataFrame(
                [
                    {
                        "Stage": "   -> Personal",
                        "Count": ep_count,
                        "Pct of Total": ep_count / ec,
                        "Drop-off": float("nan"),
                        "Drop-off %": float("nan"),
                    },
                    {
                        "Stage": "   -> Business",
                        "Count": eb_count,
                        "Pct of Total": eb_count / ec,
                        "Drop-off": float("nan"),
                        "Drop-off %": float("nan"),
                    },
                ]
            )
            funnel = pd.concat([funnel, split_rows], ignore_index=True)

        # Find biggest drop-off
        drop_data = funnel[(funnel["Drop-off %"].notna()) & (funnel["Drop-off %"] > 0)]
        if len(drop_data) > 0:
            biggest = funnel.loc[drop_data["Drop-off %"].idxmax(), "Stage"]
        else:
            biggest = "N/A"

        er = (ec / ta) * 100 if ta else 0

        # Chart -- true horizontal funnel with drop-off connectors
        chart_path = None
        if ctx.paths.charts_dir != ctx.paths.base_dir:
            ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = ctx.paths.charts_dir / "a3_eligibility_funnel.png"
            try:
                fdf = funnel[~funnel["Stage"].str.startswith("   ")]
                # "1. Total Accounts" -> "Total Accounts"
                stage_names = [
                    s.split(". ", 1)[1] if ". " in s else s for s in fdf["Stage"]
                ]
                with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
                    draw_funnel(ax, stage_names, [float(c) for c in fdf["Count"]])
                    ax.set_title(
                        f"Eligibility Funnel — {er:.1f}% of accounts eligible",
                        fontsize=20,
                        fontweight="bold",
                        pad=20,
                    )
                    if ec > 0:
                        ax.text(
                            0.99, -0.06,
                            f"Eligible split — Personal: {ep_count:,}  |  Business: {eb_count:,}",
                            transform=ax.transAxes,
                            ha="right", va="top", fontsize=13, color="#666666",
                        )
                chart_path = save_to
            except Exception as exc:
                logger.warning("A3 chart failed: {err}", err=exc)

        # Build insights
        bc = biggest.split(". ", 1)[1] if ". " in biggest else biggest
        notes = (
            f"{er:.1f}% eligible ({ec:,} of {ta:,}). "
            f"Biggest drop-off: {bc}. "
            f"Personal: {ep_count:,} | Business: {eb_count:,}"
        )

        insights = {
            "total_accounts": ta,
            "eligible_accounts": ec,
            "eligibility_rate": er,
            "biggest_dropoff": biggest,
            "personal_pct": ep_count / ec * 100 if ec else 0,
            "business_pct": eb_count / ec * 100 if ec else 0,
        }
        ctx.results["a3"] = {"funnel": funnel, "insights": insights}

        result = AnalysisResult(
            slide_id="A3",
            title="Eligibility Funnel",
            chart_path=chart_path,
            excel_data={"Funnel": funnel},
            notes=notes,
        )

        logger.info(
            "A3 complete -- {er:.1f}% eligible, biggest drop: {bc}",
            er=er,
            bc=bc,
        )
        return [result]
