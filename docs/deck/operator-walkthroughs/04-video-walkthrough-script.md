# Walkthrough 4 — Video walkthrough script (T5.6)

**Who:** CSM owner
**Time:** 30 minutes to record (5-10 min finished video) + 15 minutes to upload
**Tools:** Windows Game Bar (Win+G → Record), Loom, Zoom record-to-cloud, or OBS — operator's choice
**Output:** mp4 saved + URL stashed in the README under the slide design system section

The goal is a one-shot, no-edit recording. Read the script straight through; if you stumble, restart from the section break, not the whole video.

---

## Setup before pressing record

1. UI open in a clean browser window at `http://localhost:8000` — Generate tab visible
2. Have client **1615** pre-selected (CSM=James, Month=most-recent, Product=ARS)
3. A previously-generated run for the same client open in another window so the "review the output" segment has something to show without waiting 5 minutes for a fresh run
4. Quit any apps that emit notifications
5. Mic levels checked

---

## The script (target 8 minutes)

### [00:00–00:30] Intro

> Hi, this is James. This video shows the slide design system workflow end-to-end. By the end you'll know how to run a client, review the five output files, and approve or reject the deck. The whole thing takes about 15 minutes per client.

> The system runs on the Velocity Pipeline UI at localhost:8000. You don't open a terminal. You don't run Python. You don't edit PowerPoint files by hand. Everything is buttons.

### [00:30–01:30] What changes per run

> When you click Run, the pipeline produces five files in this folder structure. (Switch to Explorer window showing `M:\ARS\01_Analysis\01_Completed_Analysis\James\2026.05\1615\`.)

> One: the main PowerPoint deck. Two: an aux deck with the detail slides we consolidated. Three: a four-sheet Excel review summary. Four: a quality report — pass-fail on ten automated checks. Five: a metadata JSON for the audit trail. We'll look at all five.

### [01:30–02:30] Running a client

> Switch to the Generate tab. CSM = James, Month = 2026.05, Client = 1615, Product = ARS. Notice the Sections panel below — every section is checked by default; if I don't want a particular section in this run I just uncheck it. I'll leave them all on.

> Click Format + Analyze + Build PPTX. (Click.) The run log shows progress in real time. The errors-only side panel — that toggle right there — shows just the things that need attention. We'll come back when it's done; for now let me show you a finished run.

### [02:30–04:00] Reviewing the deck

> Open the PPTX. (Switch to the previously-generated deck.) First slide — title with client name. Second slide — exec dashboard with the three big KPIs. Then the section dividers — full-bleed navy with the section number, title, and lead-in sentence. (Click through 2-3 of them.)

> Inside each section, this is what's new: callout box bottom-right with the hero KPI. Footer band at the bottom with client name, month, slide number, and STRICTLY CONFIDENTIAL.

> And the action titles — every title here has at least one number in it. (Point at 2-3.) That's the populator at work. If a title is generic — like "DCTR by branch" with no number — that's a bug worth flagging.

### [04:00–05:30] Reviewing the Excel summary

> Open the review_summary.xlsx file. Four tabs.

> Tab one: Slide Inventory. Every slide that landed, plus every slide that dropped. The Status column is the fastest filter — "dropped" rows tell you what was excluded and why.

> Tab two: KPI Summary. The headline metrics. (Scroll through.) Cross-check the values against your gut sense of the client. If DCTR shows 80% but your gut says this client is at 35%, something's wrong — go back to the analytics module.

> Tab three: Callout Text. Every callout printed out with metric + value + denominator + comparison. This is the fastest way to spot a number that doesn't smell right.

> Tab four: Data Quality Flags. High-severity items in light red. If there's anything here, fix it before sending.

### [05:30–06:30] Reviewing the quality report

> Open the quality_report.txt file. First line: `Overall: PASS` or `Overall: FAIL`. Below that, the ten checks individually with the per-check detail.

> If it says PASS, you're good. If it says FAIL, scroll down — the failing checks print exactly what's wrong. Sometimes you just need to rerun; sometimes it's a real bug.

### [06:30–07:30] Approving or rejecting

> Approve when: visual quality looks right, KPI Summary numbers match expectations, quality report says PASS, no high-severity data quality flags.

> Reject when: any of those is off. Most rejects come from a missing `ctx.results` path causing the populator to fall back to a generic title — that's a ticket against the relevant action-title template.

> Once you approve, the deck is ready to send to the client. The system doesn't auto-deliver — that's intentional. You're always the last step.

### [07:30–08:00] Wrap

> If you ever need to stop a run mid-flight, the red Stop button on the Generate tab kills the subprocess. The pipeline starts over from scratch on the next click.

> Everything in this video is documented in docs/deck/IMPLEMENTATION_GUIDE.md. Code structure is in docs/deck/CODE_DOCUMENTATION.md. Design rules are in SLIDE_DESIGN.md at repo root. Questions, file an issue. Thanks.

---

## After recording

1. Save the video as `docs/deck/operator-walkthroughs/video-walkthrough.mp4` (or upload to Loom/internal video service)
2. If hosting externally, drop the URL into `README.md` near the slide design system section
3. Commit + push:

```
git add docs/deck/operator-walkthroughs/video-walkthrough.mp4  # or update README with URL
git commit -m "docs(walkthrough): T5.6 video walkthrough"
git push
```

---

## Production notes

- **Don't apologize on camera** for stumbles. Either keep going or restart from the section break.
- **Don't show notification popups.** Quit Slack, Teams, email before recording.
- **Don't read the script word-for-word.** Use it as a structure; speak naturally. The point is showing how the workflow feels, not narrating a manual.
- **Show, then tell.** Click first; explain what you just clicked second.
- **One client only.** Don't try to demonstrate ARS + TXN + Hybrid in one video. If team members ask, record short follow-ups.
