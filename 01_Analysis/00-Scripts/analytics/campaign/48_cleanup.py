# ===========================================================================
# CAMPAIGN SECTION CLEANUP -- release transaction-level working frames
# ===========================================================================
# camp_txn and the responder/non-responder/never splits are each a full copy
# of combined_df (54M+ rows on a large client). Nothing outside this section
# reads them (audited: camp_txn/camp_never_df only in 01; camp_resp_df /
# camp_nonresp_df also in 08), but the wrapper's copy-back would pin all four
# in shared memory for the REST of the run -- a large slice of the section-5
# OOM in issues #92/#251. Deleting them in the section's LAST cell means they
# never propagate to the shared namespace at all. The small per-account
# frames later sections do read (camp_acct, camp_status_agg, camp_summary)
# are untouched.

import gc as _gc

_released = [
    _name for _name in (
        'camp_txn', 'camp_resp_df', 'camp_nonresp_df', 'camp_never_df',
    )
    if globals().pop(_name, None) is not None
]
_gc.collect()

if _released:
    print(f"  Released campaign working frames: {', '.join(_released)} "
          f"(memory freed for the remaining sections)")
