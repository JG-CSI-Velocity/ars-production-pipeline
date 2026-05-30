# Walkthrough 1 — Sign off on SLIDE_DESIGN.md (T1.1.11)

**Who:** CSM owner (you)
**Time:** ~30 minutes
**Output:** updated `SLIDE_DESIGN.md` §15 with your name and today's date, committed and pushed.
**Why it gates everything else:** Tier 2 specs and Tier 3 quality checks reference the rules in this document. Signing it off freezes the contract so downstream work doesn't drift.

---

## Before you start

Open these two side by side:

1. `SLIDE_DESIGN.md` at repo root (Pull the latest first.)
2. A recent client deck you trust visually — pick one you've already shipped to a client without complaint.

This is a 30-minute read; you're checking whether the rules describe the deck you already use, **not** whether they describe an aspirational deck you wish you used.

---

## Read each section with one question

| Section | The question to answer |
|---|---|
| §1 Philosophy | Does "lead with the so-what" actually describe the slides you ship? |
| §2 Deck structure | Is the 13-slide preamble + sectioned body + appendix the structure your clients see? |
| §3 Slide anatomy + §3.1 spacing | Action title on top, chart in middle, callout bottom-right, footer at bottom — that match? |
| §4 Typography | 24pt action title, 12pt body, 11pt chart labels — match what your decks look like? |
| §5 Color system | Navy / accent teal / positive green / negative red — feel right? |
| §5.1 **NEW** Per-section accents | DCTR=teal, Reg E=purple, Attrition=red, Value=green, Mailer=blue, Insights=charcoal — accept or override |
| §6 Chart rules | No 3D, no chart-junk, time on x-axis ascending — already true in your decks? |
| §7 Callout boxes | Hero number + denominator + comparison — feel right, or do you want a different shape? |
| §8 Footer band | `Client \| Month \| Slide N \| STRICTLY CONFIDENTIAL` — accept or want to add/remove anything? |
| §9 Section dividers | Full-bleed navy with section number + lead-in — accept or want a different treatment? |
| §10 Naming + §11 Per-section application | Mostly admin; quick read |
| §12 **NEW** Drop-if-empty | Six drop reasons + section-level drops — accept |
| §13 Out of scope + §14 Update process | Quick read |

**If you have a problem with any section:** stop, edit the doc, commit your edits, *then* sign off. Don't sign off and then edit — that defeats the lock.

---

## The three likely points of debate (decide in advance)

1. **§5.1 Per-section accents.** The PRD called for DCTR=teal, Reg E=purple, etc. Code already applies these. If you want different colors, edit §5.1 and `01_Analysis/00-Scripts/shared/charts.py::SECTION_COLORS` together; they must match.

2. **§9 Section dividers.** PRD says "32pt bold navy on 10% opacity section background." The current code paints **full-bleed navy** with section number + lead-in. Two valid takes; pick one:
   - Keep full-bleed (current code): visually striking, dominant. No code change.
   - Switch to PRD 10%-opacity: subtler. Code change required — open a follow-up ticket.

3. **§7 Callouts.** Current code renders hero number + sub-label + (optional) denominator + comparison. PRD's CalloutBox dataclass already supports all four. Confirm you want all four fields populated on every callout (vs. just hero + sub).

If you want to defer any of these decisions, add a note in §15 like "approved with §X deferred — see issue #NNN".

---

## Apply the sign-off

Open `SLIDE_DESIGN.md`. Find this row at the bottom:

```
| 1.0 | 2026-05-29 | _pending_ | Initial pass through T1.1.1–T1.1.10 (issue #146). CSM sign-off (T1.1.11) is the gate to T1.2+. |
```

Replace `_pending_` with your name. Update the date to today. Optionally add notes about deferrals. Example:

```
| 1.0 | 2026-06-03 | James Gilmore | Approved. §5.1 accents accepted. §9 full-bleed retained over PRD 10%-opacity. |
```

Then commit and push from the work PC:

```
git pull
git add SLIDE_DESIGN.md
git commit -m "sign(design): approve SLIDE_DESIGN.md v1.0 (T1.1.11 / #146)"
git push
```

(If your operator workflow is GitHub Desktop instead of CLI, do the equivalent there: Fetch → commit `SLIDE_DESIGN.md` with that message → push.)

---

## After sign-off

- Don't edit `SLIDE_DESIGN.md` again until you bump the version to 1.1 with a fresh sign-off. The doc is locked for the rest of the rollout per PRD critical success factor #1.
- Tell the team it's locked. Anyone adding new rules to the deck contract opens a ticket against `SLIDE_DESIGN.md` first.
- The quality gate (T3.2) will keep enforcing what's in the doc — if you ever want to relax a rule, edit the doc *and* `output/quality_gate.py` together.
