# ARS Deck — Lessons (read before diagnosing a "broken" deck)

## The stale-deck trap (the expensive one)

**Symptom.** A committed `1759_..._ars_deck.pptx` had 167 slides, leaked
`{overall_rate:.1f}` / `{total_*}` tokens on three slides, four slides per mail
wave instead of two, and un-merged attrition 2×1s. Every one of those looked
like a live bug worth fixing.

**Reality.** All of them were already fixed in the current code. The deck was a
binary artifact re-committed during an unrelated merge ("keep 1759 deck artifact
after TXN merges"), built *before* the fixes landed. Diagnosing the file instead
of the code nearly produced a round of fixes for already-fixed bugs.

**How it was caught.** The slide-spec template `A13.{month}` was *already*
tightened to only match real month tokens (`[A-Za-z]{3}\d{2,4}`), so it could not
produce the "5 response rate" leak seen on the slide. That contradiction —
"the slide shows a bug the code can't produce" — is the tell.

**The rule.** Before changing any code in response to a bad deck, prove the bug
still exists in current code by exercising the pure functions
(`scripts/check_consolidation.py`) and comparing the deck's commit/mtime to the
fix commits. If current code is correct, the fix is **rebuild**, not edit.

Verified, for the record, that current code produces:
- mailer: 22 waves → main = 15 slides (6 recent × [summary+combo] + aggregate),
  rest → ancillary. Not 120+.
- `get_spec(mailer, A13.5 / A13.Agg / A13.6)` → `None` (no token leak).
- attrition `A9.1 + A9.12` → one 2×1; `A9.3/A9.6/A9.9` → appendix.

## The synthetic-vs-real test gap

The synthetic end-to-end build composes ~39 clean slides and `deck_qa` passes it.
Real client data has ~22 mailer waves; the consolidation was never unit-tested at
that scale, so a multi-wave regression (or a stale multi-wave deck) was
indistinguishable from correct output. **QA on real output, and unit-test the
pure consolidation functions with ~22 waves, not 2.**

## Trust hygiene

Prior-session "done" notes and even memory entries have been wrong here (e.g.
slide-20 fonts and a slide-29 legend were marked done but were still broken).
Verify against the current code and the actually-extracted slide pixels, never a
claim. The user has been through several long nights of this — be concise, don't
over-promise, and show the evidence.
