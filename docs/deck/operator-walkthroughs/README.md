# Operator Walkthroughs

The six items the code couldn't ship for you. Work through them in order.

| # | Doc | What | Time |
|---|---|---|---|
| 1 | [01-slide-design-signoff.md](01-slide-design-signoff.md) | Read SLIDE_DESIGN.md, edit §15, commit | 30 min |
| 2 | [02-powerpoint-template-edits.md](02-powerpoint-template-edits.md) | Master-slide font + margin + picture edits | 45 min first time |
| 3 | [03-e2e-test-plan.md](03-e2e-test-plan.md) | Run 10 clients, fill in `e2e-test-results.md` | ~3 hr compute + 1 hr review |
| 4 | [04-video-walkthrough-script.md](04-video-walkthrough-script.md) | Record an 8-min Loom of the CSM workflow | 45 min |
| 5 | [05-csm-quick-reference-card.md](05-csm-quick-reference-card.md) | **Already done** — print + post at workstation | 5 min |
| 6 | [06-go-live-signoff.md](06-go-live-signoff.md) | Final approval for 70-client portfolio | 30 min reading |

## Dependency chain

```
1 (signoff) ────┐
                ├──> 2 (template) ──> 3 (E2E test) ──> 6 (go-live)
                │                       │
                │                       └──> 4 (video) ──┘
                │                            5 (card) ───┘
                └──> 3, 4, 5, 6
```

#1 unblocks everything. #6 is the last step. #5 is already authored — printing it is the only action.

## What you'll produce

By the end of all six walkthroughs:

- `SLIDE_DESIGN.md` §15 with your sign-off
- `2025-CSI-PPT-Template.pptx` updated and committed
- `e2e-test-results.md` filled in
- `video-walkthrough.mp4` (or a URL referenced in README)
- Printed `05-csm-quick-reference-card.md` at your workstation
- `go-live-signoff.md` with your approval

Once those exist, #145 can be closed-for-production and the system is live.
