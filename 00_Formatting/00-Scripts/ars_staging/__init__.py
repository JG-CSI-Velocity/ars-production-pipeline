"""ars_staging -- background auto-staging for the v3 engine.

Pre-pulls CSM data dumps from the M:\\ share to machine-local storage and
converts them to analysis-ready formats (parquet), so the operator's click
always reads local data. Run by Windows Task Scheduler every 15 minutes and
kicked once on UI launch:

    python -m ars_staging poll
"""
