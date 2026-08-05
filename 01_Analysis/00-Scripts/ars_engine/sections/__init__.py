"""Section modules register here as each migration wave lands.

Import every section module below so its @register decorator fires. A section
only appears here once its implementation is ported AND its golden-master
parity is approved for capture (routing to it still requires the engine_flags
entry to be "new" -- see core/config.py).
"""

# Wave 1+: e.g.
# from ars_engine.sections import entity_profile  # noqa: F401
