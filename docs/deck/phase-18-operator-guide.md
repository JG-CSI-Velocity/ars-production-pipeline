# Phase 18 — Operator Guide

**Audience:** the CSM running the pipeline on the work PC at `M:\ARS\`.
**You don't open a terminal. You don't run Python. You don't touch git from the command line.** Everything below is a click.

---

## What's changing in Phase 18

The deck builder gets five upgrades. Operator-facing, the UI doesn't change — you run the same Generate-tab flow. The output deck looks different (and better):

1. **Callout boxes** — every content slide has a teal hero-KPI box bottom-right
2. **Footer bands** — every content slide has a two-line footer (source + `Client | Month | Slide n | STRICTLY CONFIDENTIAL`)
3. **Section dividers** — full-bleed navy slides with white title and lead-in sentence
4. **Speaker notes** — section-specific talking points in Presenter View, not the old generic prompt
5. **Action-title headlines** — the 31 slides that used to get a generic category title now get a sentence-level finding (e.g. "Debit Card Take Rate held at 34% — 8 of 19 branches under 30%")

---

## Apply the update

### 1. Pull the new code

Open **GitHub Desktop**. Repo = `ars-production-pipeline`. Current branch = `pipeline-improvement` (or whichever branch the Phase 18 work has been promoted onto). Click **Fetch origin**, then **Pull origin**.

> Don't have GitHub Desktop set to `M:\ARS\`? Open it once, **Add Local Repository**, choose `M:\ARS\`. Done — it remembers from now on.

### 2. Stop the running pipeline

Find the **Velocity Pipeline** terminal window (the black box that opened when you double-clicked `Start Here.bat`). Close it. That stops the FastAPI server.

### 3. Relaunch

In Windows Explorer, navigate to `M:\ARS\`. Double-click **`Start Here.bat`**. A new terminal window opens. Wait ~5 seconds for the browser to open `http://localhost:8000`.

### 4. Hard-refresh the browser

`Ctrl + Shift + R`. (HTML/JS gets cached aggressively. Without this, you'll be looking at yesterday's UI.)

---

## Verify the update worked

### Verification client

- **CSM:** James
- **Month:** 2026.05
- **Client:** 1615

### Run ARS

1. **Generate tab** → CSM = James → Month = 2026.05 → Client = 1615 → Product = **ARS** → **Run**.
2. Wait for the **Results tab** to show the run finished (green check / no red errors).
3. Click the ARS deck in the Results tab to open it in PowerPoint.

### Run TXN

1. **Generate tab** → same CSM/month/client → Product = **TXN** → **Run**.
2. Open the TXN deck from the Results tab.

---

## What to check in each deck

Open each deck in PowerPoint and confirm:

| Check | Where to look | Pass criteria |
|---|---|---|
| Callout boxes | Any content slide (e.g. DCTR slides) | Bottom-right has a teal rounded rectangle with a large hero number |
| Footer band | Bottom of any content slide | Two lines: source on top, `Client \| Month \| Slide n \| STRICTLY CONFIDENTIAL` on bottom |
| Section dividers | Between sections (e.g. before DCTR) | Full navy background, teal section number ("02"), white title, white lead-in sentence — **no chart, no logo, no template placeholders** |
| Speaker notes | Switch to Presenter View on a DCTR slide | Notes start with `KEY FINDING:`, then bullet KPIs, then `TALKING POINTS:` with DCTR-specific prompts (e.g. about activation process, onboarding flow) |
| Action-title headlines | A8.7, A18.x, A19.x, A20.x, A7.5–A7.15 slides | Slide title reads like a finding (numbers + context), not a generic category like "Reg E Opt-In Rates by Branch" |

### What should **not** change

- Title slides — no callout, no footer
- Total slide count — same as the previous run
- Chart images — identical (formatting is additive, not regenerated)
- Excel workbook output — unchanged

---

## If something looks wrong

| Symptom | First check | Then |
|---|---|---|
| Run errored on the Results tab | Click the red row → error message panel opens in UI | Share screenshot in Slack |
| Deck opens but has zero callout boxes | Check you hard-refreshed (Ctrl+Shift+R) and the new terminal window is the one running | Re-run step 2–4 above |
| Speaker notes still say generic "What actions has the client taken?" | The `notes.py` import path on this PC may be pointing at a stale install | Flag for dev — needs a Python path check, not an operator fix |
| Headlines still say generic category text on A8.x / A18.x / A19.x / A20.x | The analytics module isn't populating the insights keys the new generator expects | Flag for dev with the slide_id — Phase 18.4 generator falls back to default title when data is missing |
| Footer band missing on some content slides | Note which slide IDs | Flag for dev — `_add_slide` skipped a slide type |
| Section divider still has placeholders or template text | Note which section | Flag for dev — `_build_section_slide` didn't fully clear the layout |

There is no need to open log files. The History tab in the UI shows everything. If the History tab doesn't tell you what went wrong, that's a UI gap to file as an issue, not an operator workaround.

---

## After verification passes

Nothing to do. The branch is live for all future runs on this PC. No further action required until the next phase ships.
