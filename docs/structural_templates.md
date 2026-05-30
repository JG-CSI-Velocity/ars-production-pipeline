# Structural slide templates (autonomous decks design §C)

Consumed by: `01_Analysis/00-Scripts/output/structural_slides.py`
Authority: `docs/superpowers/specs/2026-05-29-autonomous-decks-design.md`

The structural builders read this file to pick subline copy for each
auto-built slide. POC scope is the Cover section only; Dashboard, Agenda,
Section openings, and Takeaways are stubbed and land in the long-tail plan.

## Cover

### Default subline
"Account Revenue Solution"

### Lead-finding override
When `ctx.results['value_summary']['lead_finding']` is a non-empty string,
the cover subline becomes that sentence verbatim. The lead finding is set by
the value-summary analytics module (existing).

### Fallback subline
"Performance review"
(used only when both the lead finding is missing AND the default subline
copy bank fails to load — edge case for failure-mode coverage.)

## Dashboard

_Deferred to long-tail plan._

## Agenda

_Deferred to long-tail plan._

## Section openings

_Deferred to long-tail plan._

## Takeaways

_Deferred to long-tail plan._
