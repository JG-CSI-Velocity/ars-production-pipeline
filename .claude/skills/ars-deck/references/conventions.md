# ARS Deck — Locked Owner Conventions

These are taste/structure decisions the owner (JG) already made. **Verify a deck
honors them; do not relitigate or "improve" them** without the owner asking.
Each is paired with the *why* so you can apply judgment to new cases.

## Section narrative

The deck follows an SCR (Situation → Complication → Resolution) arc, encoded in
`SECTION_ORDER`:

```
overview → dctr → rege → attrition → mailer → transaction → ics → value → insights
```

Overview sets the situation; DCTR/Reg E/attrition are the complications; mailer
and beyond are the resolution and call to action.

## Mailer

- **Every mail wave = exactly TWO slides:** the A13 summary + its A16.7 combo
  chart. The combo shows spend AND swipes in one figure, so the separate A12
  Swipes/Spend slides are dropped (their results still live in `ctx.results` for
  the P08/P09 preamble). Net slide reduction, no information loss.
- **Only the most recent `MAIN_MAILER_MONTHS` (6) waves lead the main deck.**
  Older waves move to a separate `{client}_{month}_Mailer_Performance.pptx`
  ancillary deck (cover + divider + each older wave's two slides) so the operator
  doesn't hand-delete a long appendix.
- **The "ARS Mailer Revisit" preamble slide features the OLDEST wave**, not the
  most recent — the furthest-back campaign has the most post-mail months to look
  back on and isn't a duplicate of the recent waves shown in the section.

## Reg E

- The Reg E funnel must match the DCTR funnel's visual language: **proportional
  boxes** (scale to count) with between-stage badges — not a monochrome
  waterfall and not equal-width boxes. The two funnels (all-time vs TTM) must be
  **equal-sized to each other** in the 2×1.
- L12M funnels anchor to OPEN accounts (`filter_l12m(open_accounts)`), never a
  raw `last_12_months` that includes closed — keeps denominator parity with DCTR.

## Attrition

- A9.0 headline dashboard leads (real title, Eligible-accounts + Eligible-closures
  tiles, a two-rate All/Eligible tile, monthly opens-vs-closes with net-new line).
- A9.1 (Closures by Year) + A9.12 (Monthly Closures) merge into one 2×1
  ("Account Closures: Annual & Monthly Trend"). A9.4b + A9.4c likewise.
- A9.9 (debit retention) shows ~0% with-debit attrition because debit flags are
  blanked at close — it can't attribute closures to with/without debit, so it
  lives in the appendix, not the main body.
- "Active cardholders" = open accounts with recent swipe > 0 (swipe data IS in
  the ODD via `shared/format_odd.py`; don't claim it's TXN-only).

## Intentionally blank (operator hand-fills)

P04 Executive Summary, P05 Monthly Revenue, P06 ARS Lift Matrix, and the Agenda
(slide 2) are **intentionally blank** — the operator fills them from a separate
PowerPoint/Excel. They are not bugs. `deck_qa` whitelists these titles. Slide 2
is the Agenda, NOT a KPI dashboard (the dashboard replacement was removed).

## Denominator framework (the 4-layer law)

Every rate anchors to exactly one of: **Eligible / Eligible Personal / Eligible
Business / Open.** No bespoke per-slide filters. Mailer response anchors to the
Eligible Mailable subset *within* Eligible — the mailable filter frames the
numerator, it does not narrow the denominator. The `generate` step runs a
denominator-law audit (`rates_audit.csv`) that flags any rate whose denominator
label is outside the framework — check it after a run.

## deck_qa policy

`deck_qa` findings are advisory data, not exceptions — the caller decides policy.
Thresholds are tuned so the known-good reference decks pass clean, so treat any
finding as real. It deliberately does NOT do geometric overlap detection (it
false-positived on intentional layering like a label on a stat card);
`text_overflow` is the calibrated proxy for text-collision.
