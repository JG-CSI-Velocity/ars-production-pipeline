---
persona: "Dana — non-technical CSM operator (Windows work PC, UI-only, launches via Start Here.bat)"
date: 2026-08-05
scope: "End-to-end operator experience: onboarding, Format, Generate, Results, History, Schedules, failure handling. Static review of 05_UI/app.py + 05_UI/index.html + launchers/docs, plus a live local launch of the server (endpoints probed, no data run)."
rule: "CLAUDE.md UI-First Rule: every diagnostic, fix, run, audit, and tool must be operable from the UI."
code_version_reviewed: "988b478 (main)"
---

# CSM Operator Audit — Dana's Month, End to End

What works well (credit where due): the Generate tab's 5-stage checklist with
plain-English stage names, the completion card with translated slide-failure
reasons (`_translateError`), the 409 "a run is already in progress" guard with a
human message, STOP ALL with a clear confirm, fail-fast validation of local-copy
and source paths, the Curate Deck visual triage + Rebuild-without-reanalysis
loop, and the footer code-version chip. INSTALL.md's CSM section is genuinely
written for Dana. The findings below are the gaps around that core.

---

## Findings

### 1. Schedules never actually run — the tab is a silent placebo
**Severity:** BLOCKER
**Where:** Schedules tab (`05_UI/index.html:1021`), backend `05_UI/app.py:1677-1815`
**What Dana experiences:** The tab says "Schedules run automatically on the specified day." Dana creates a schedule for the 5th, the row shows a green "Active" badge, and nothing ever happens — there is no scheduler loop anywhere in `app.py`; only the manual `POST /api/schedules/{id}/run` ("Run Now" button) does anything. No error, no "last run skipped" — the most trust-destroying kind of failure: a promised automation that silently doesn't exist.
**Suggested fix:** Until the execution engine ships (feat/schedule-execution), the tab must tell the truth: replace the subtitle with "Schedules run when the pipeline window is open on the scheduled day" or, if not even that is true yet, a visible banner: "Automatic runs are not enabled yet — use Run Now." When it ships, each row needs a "Next run" column and a red "Missed — server was off on the 5th" state.

### 2. Launcher and server disagree about the port — Dana can land on a stale server
**Severity:** BLOCKER
**Where:** `Start Here.bat:52-64` vs `05_UI/app.py:1826-1845`
**What Dana experiences:** `app.py` auto-walks to port 8001-8010 when 8000 is busy (e.g. an orphaned server from a previous session still holds 8000). But `Start Here.bat` polls **only** `http://localhost:8000` and opens the browser to `:8000`. The wait loop then succeeds against the *old* instance and Dana's browser opens last week's code with last week's run state — the exact "stale checkout produced a whole client run with old charts" incident the version chip was built to prevent, reintroduced by the launcher. The new server's "Using port 8001 instead" message is invisible (the process runs with `start /b`, output interleaved in a window Dana never reads).
**Suggested fix:** Make the launcher and server agree: either the bat kills any existing listener on 8000 before starting (then always opens 8000), or the server writes the chosen port to a file the bat reads and opens. In-UI backstop: on load, the page should compare its own origin port against a server-reported "I am the newest instance" stamp and show a red banner "Another copy of the pipeline is running — close all Velocity Pipeline windows and double-click Start Here.bat once."

### 3. Refresh, crash, or closed terminal mid-run = a UI that spins forever
**Severity:** MAJOR
**Where:** `05_UI/app.py:69` (in-memory `runs{}`), `05_UI/index.html:2247-2248` and `3026-3028` (poll loops: `if (!statusResp.ok) return;`)
**What Dana experiences:** Three flavors of the same dead-end during a 20-40 minute run:
- She refreshes the browser (or the tab crashes): all run visibility is client-side state, gone. The run continues on the server but no tab, panel, or page shows it. Buttons are re-enabled; only the 409 guard stops her from double-running.
- The server restarts: the poll gets 404 forever, the code silently `return`s, the elapsed clock keeps ticking, and the checklist sits on "Run analytics" until the heat death of the universe.
- She closes the terminal window mid-run (the bat itself says "Close this window to stop the server" with no mid-run warning): the analysis is killed silently; next launch shows no trace of an interrupted run.
**Suggested fix:** (a) An "Active runs" strip visible on every tab, fed by a `GET /api/runs?status=running` endpoint, so a fresh page load reattaches to any in-flight run. (b) The poll loop must count consecutive 404s and after ~10 flip the run view to "Lost contact with the run — the server may have restarted. Check the History tab; the last log lines are in the run log." (c) Persist run state to disk so a restart can report "a run was interrupted."

### 4. Rebuild Deck and HTML Preview read the client config wrong — rebuilt decks lose the client's name
**Severity:** MAJOR
**Where:** `05_UI/app.py:1417` and `05_UI/app.py:1619` (`load_clients_config().get("clients", {})`)
**What Dana experiences:** `clients_config.json` is keyed by client ID at the top level (verified: `['1776','1226',...]`, no `"clients"` key — and `/api/clients` at `app.py:573` iterates it that way). The Rebuild Deck and HTML Preview paths instead do `.get("clients", {})`, which is always empty. So a deck rebuilt from the Curate panel is built with `client_name = client_id` and **empty eligible stat/product codes**, and the HTML preview header shows "1776" instead of "CoastHills CU". Dana curates her deck, clicks Rebuild, and the client-facing title slide now says a number.
**Suggested fix:** One-line backend fix (drop `.get("clients", {})`), but the UI should also defend itself: the rebuild completion message should echo the client name it used ("Rebuilt deck for CoastHills CU"), so a numeric name is immediately visible before the deck goes to a client.

### 5. Results tab: client dropdown race + "Preview as HTML" ignores the selected run
**Severity:** MAJOR
**Where:** `05_UI/index.html:1238-1247` (`loadClients` rebuilds `rClientSel` without `data-csm/data-month`) vs `2858-2875` (`loadResultsClients` adds them); `2436-2443` (`openHtmlPreview` reads only the Generate tab's CSM/period)
**What Dana experiences:** Two loaders race to populate the same Results dropdown on page load. If the plain-config one wins last, the options lose their CSM/month tags and the slide viewer falls back to whatever CSM/period the *Generate* tab happens to show (`index.html:3187-3188`) — Dana picks a client whose deck definitely exists and gets "No results found." Separately, "Preview as HTML" *always* reads the Generate tab's CSM/period and alerts "Pick a CSM + period on the Generate tab and a client on the Results tab first" — a cross-tab scavenger hunt, and if the Generate tab points at a different month it builds/404s the wrong preview.
**Suggested fix:** One owner for the Results dropdown (`loadResultsClients` only — options always carry csm/month), and every Results-tab action (viewer, Curate, Preview as HTML) resolves csm/month/client from the selected option exactly like `_resultsSelection()` already does for Curate. No action on the Results tab should ever tell Dana to go set values on another tab.

### 6. History is a dead-end: no way to see WHY a run warned or failed
**Severity:** MAJOR
**Where:** History tab (`05_UI/index.html:2827-2848`), `05_UI/app.py:395-425` (`get_recent_runs`)
**What Dana experiences:** A run's status is a heuristic ("ERROR" appears in the log text → amber "Warning" badge) and that badge is the *entire* diagnostic surface. There is no click-through: not to the log (the API even returns the log-file path — the UI ignores it), not to the run's quality panel, not to the outputs. When the companion-run banner fails it literally says "see History tab / logs" — and History has nothing to see. Bonus mislabels: the Product column is hardcoded "ARS" for every run including TXN (`index.html:2816`, `2838`), and the History "Modules" column shows the *slide count* (same `r.slides` in both the Modules and Slides cells, `index.html:2839` + `2843`).
**Suggested fix:** Each History row expands (or opens a panel) showing: the last ~50 log lines rendered in-page, the Run Quality panel for that run, and Download buttons for its outputs. Fix the Product column (parse from the log filename/content) and the Modules column. "Warning" should be accompanied by a one-line reason ("2 slides failed: A8.7, B1.2"), pulled from the run_report the pipeline already writes.

### 7. Broken module registry tells Dana to check the wrong thing; the real fix is a terminal command
**Severity:** MAJOR
**Where:** `05_UI/index.html:1269-1271` vs `05_UI/app.py:630-641`
**What Dana experiences:** If `tools/sections.json` is missing or corrupt (e.g. a bad pull), the By-module picker says "Couldn't load the module list. Make sure the pipeline server is running." The server *is* running — the real remediation ("regenerate with: `python .../list_sections.py --write`") is printed only to the server console Dana never reads. She retries forever. This is a direct UI-First violation: the recovery path exists only as a CLI instruction.
**Suggested fix:** When `/api/modules` returns empty, the UI should show "The module list file is missing or out of date" with a **Rebuild module list** button backed by a small endpoint that runs the regeneration server-side and re-fetches. Same pattern for any future "regenerate X with this command" message.

### 8. The run scorecard is generated, shipped by the API — and never shown
**Severity:** MAJOR
**Where:** `05_UI/app.py:1280-1285` (`scorecard_md` in `/api/run_quality`), `05_UI/index.html:1949-2014` (`loadRunQuality` never renders it)
**What Dana experiences:** The pipeline writes `run_scorecard.md` per run; the API reads the whole file into `scorecard_md`; the UI uses it only as an existence check and drops the content. Dana gets a one-word verdict ("Ship" / "Investigate") with no way to see the scorecard behind it. Related unsurfaced artifacts (UI-First grade, capability exists but no UI): the competition detection diagnostic (`68_detection_diagnostic.py` output — see finding 12), raw per-run logs in `04_Logs/`, the TXN stale-cache clearer (`tools/clear_stale_txn_cache.py`), and the methodology/equation reference (`docs/EQUATION_DICTIONARY.md`) that would answer "what does this rate mean" questions in-UI.
**Suggested fix:** A "View scorecard" expander in the Run Quality panel rendering the markdown. A "Clear TXN cache" maintenance button (with plain-English description) near STOP ALL. A read-only "What do these numbers mean?" panel serving the equation dictionary.

### 9. Run Quality panel speaks auditor, not CSM
**Severity:** MINOR
**Where:** `05_UI/index.html:1964-2010`
**What Dana experiences:** "3 law violations", "Investigate (law violations)", "manifest: unknown", "12 rates audited", "anomaly flags", and the reassurance text "Every rate anchors to one of Eligible / Eligible Personal / Eligible Business / Open." None of this is defined anywhere in the UI. "manifest: unknown" on an old run reads like something is broken when it just predates the feature.
**Suggested fix:** Keep the mechanics, translate the labels: "law violations" → "numbers that need review before sending" (with a hover explaining the denominator rule in one sentence); hide the manifest status when `unknown`; a small "?" popover per term. The verdict line should say what to *do*: "Review 3 flagged numbers before sending this deck."

### 10. Competition diagnostic completion note sends Dana to GitHub with a file path
**Severity:** MINOR
**Where:** `05_UI/index.html:1918-1920`
**What Dana experiences:** "Competition diagnostic saved — `M:\ARS\...\competition_diagnostic.txt` — Open this file and paste contents into issue #122." Dana doesn't open file paths and doesn't have a GitHub account. The instruction violates the repo's own issue conventions.
**Suggested fix:** Two buttons on the notice: "View diagnostic" (serves the .txt inline via the existing `/api/download?inline=true`) and "Download" — with copy like "If the competitor list looks wrong, send this file to James."

### 11. Progress is fake and the Format checklist can silently stall
**Severity:** MINOR
**Where:** `05_UI/app.py:900`, `1104` (progress = log-line count × 2-3, capped 95); `05_UI/index.html:1699-1710` (Format stage regexes)
**What Dana experiences:** The percent bar is just "how many log lines have we printed," parks at 95% for the long tail, and the Format tab's 5-stage checklist is driven by guessed regexes ("applying 7-step", "unzip complete") that plausibly never match the formatter's real output — leaving the checklist stuck on "Locate raw ODD files" for an entire successful run. Dana reads a stuck checklist as a hung run and may hit STOP ALL on a healthy job. (The Generate tab is protected by real `Module N/M` parsing; Format has no equivalent.)
**Suggested fix:** Have the formatter emit explicit stage markers (`STAGE: unzip done`) and drive the checklist only from those; drop the fake percent on Format in favor of the checklist + elapsed clock (the Generate tab already models this correctly).

### 12. Months dropdown silently hides anything older than 6 periods
**Severity:** MINOR
**Where:** `05_UI/app.py:722-723`
**What Dana experiences:** `/api/months` truncates to the 6 most recent. Re-downloading or re-generating a deck from 7+ months ago is impossible from the Generate tab — the period simply isn't in the list, with no hint that it was cut. (The Results tab's own scan is uncapped, deepening the "why is it here but not there" confusion.)
**Suggested fix:** A "Show older periods…" option at the bottom of the dropdown that refetches without the cap.

### 13. "Client blank = format ALL clients" with no confirmation
**Severity:** MINOR
**Where:** Format tab (`05_UI/index.html:511-513`, `2995`)
**What Dana experiences:** The client field defaults to blank, and blank means "format every client for this CSM." One optimistic click starts a long multi-client job. The Force Re-Format variant will happily overwrite everything.
**Suggested fix:** When client is blank, the button click confirms: "Format ALL of Dan's clients for 2026.07? (N clients found)" — with the count fetched first.

### 14. Schedules always target the *current* month, and nothing says so
**Severity:** MINOR
**Where:** `05_UI/app.py:1727` (`month = now`), Schedules form (`05_UI/index.html:1027-1066`)
**What Dana experiences:** The schedule form has no period concept; Run Now (and any future auto-run) uses today's month. A run fired on the 1st-3rd targets a month whose data dump may not exist yet → an error Dana can only see by... finding 6.
**Suggested fix:** Show "Runs for the current period (e.g. 2026.08)" on the form, and have the run first check the raw dump exists — if not, report "No data dump for 2026.08 yet — will show here when it lands" instead of erroring.

### 15. Hardcoded "james.gilmore" in the header
**Severity:** MINOR
**Where:** `05_UI/index.html:432`
**What Dana experiences:** Every CSM's console says they are james.gilmore. Harmless but erodes the "this tool knows what it's doing" trust, and confuses the CSM-selection mental model ("do I need to be James?").
**Suggested fix:** Drop it, or show the CSM currently selected in the dropdowns.

### 16. Results gallery labels are raw filenames
**Severity:** MINOR
**Where:** `05_UI/index.html:3202-3205`
**What Dana experiences:** Slide titles like "a16 7 mailer combo Apr26" and a sidebar of sections named "a8", "b1" — because titles/sections are derived from PNG filenames. The Curate panel proves the system has real titles (from `run_report.json`); the gallery just doesn't use them.
**Suggested fix:** Feed the Results viewer from `/api/curate`'s slide list (real titles, real sections) and fall back to filenames only for pre-report runs.

### 17. Error wording still points at dev artifacts
**Severity:** NICE-TO-HAVE
**Where:** `05_UI/index.html:3395` ("Make sure app.py is running"), `1270`
**What Dana experiences:** When the server is unreachable the alert names `app.py` — a file Dana must never touch. The canonical recovery is documented in CLAUDE.md but not in the message.
**Suggested fix:** Standardize one recovery string everywhere: "Can't reach the pipeline. Close the Velocity Pipeline window, double-click Start Here.bat, then refresh this page (Ctrl+Shift+R)."

### 18. Onboarding: good bones, three drifts
**Severity:** MINOR
**Where:** `INSTALL.md:33-35` vs `Start Here.bat:26-29`; `CSM Setup.bat:41`; `SETUP.md:9-13`
**What Dana experiences:** On a fresh PC the CSM Setup.bat → Start Here.bat path is genuinely no-IT-needed (assuming GitHub releases are reachable from the corporate network — the only external dependency, with a decent "screenshot and send to James" failure path). Drifts: (a) INSTALL.md tells Dana to look for the message "This computer has not been set up yet", but the launcher actually prints "No Python found on this computer" — she may not connect the two; (b) the bundle verify check imports a fixed five packages, so a future requirements change (e.g. duckdb for v3) can pass setup and fail at runtime; (c) seeding `SLIDE_MANIFEST.xlsx` is documented only as a `copy` terminal command in SETUP.md — the UI's Sync button covers it, but nothing tells a new operator that.
**Suggested fix:** Align the two message strings; verify the bundle against `requirements.txt` instead of a hardcoded list; have the Curate panel's "manifest not found" state say "Click Sync to create your personal manifest — first time on this machine, this is expected."

---

## Top 5 fixes by operator impact

1. **Make Schedules honest** (finding 1) — either fire them or say they don't fire. A silently-dead automation is worse than none.
2. **Fix the launcher/port mismatch** (finding 2) — it can silently reintroduce the stale-code-client-deck incident the version chip exists to prevent.
3. **Survivable runs** (finding 3) — an "Active runs" reattach strip + a "lost contact" state kills the three worst dead-ends (refresh, crash, closed terminal) in one feature.
4. **History drill-in** (finding 6) — one expandable row with log tail + quality panel + downloads converts the only "what happened?" surface from a dead-end into the answer.
5. **Fix the rebuild/preview config bug** (finding 4) — a one-line backend fix that stops client-facing decks being rebuilt with a number for a name and empty eligibility codes.
