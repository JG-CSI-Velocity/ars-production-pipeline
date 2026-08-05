---
persona: "Dana — non-technical CSM operator (Windows work PC, UI-only, launches via Start Here.bat)"
date: 2026-08-05
round: 2 (verification of round-1 dispositions, fresh eyes)
scope: "Verify every FIXED row in the CSM table of 2026-08-05-r1-dispositions.md against current main; hunt regressions from the fix commit (e4cc64d); re-grade DEFERRED rows; new findings."
code_version_reviewed: "3bffe56 (main) — confirmed live via /api/version"
method: "Full read of 05_UI/app.py, 05_UI/index.html, Start Here.bat; live server launch (.venv/bin/python 05_UI/app.py); curl probes of /api/active_runs, /api/run_log_tail (traversal cases), /api/run_quality, /api/version, /api/csms, /api/recent; pytest 05_UI/tests/test_operator_fixes.py (9 passed)."
---

# CSM Operator Audit — Round 2 Verification

## Part 1: FIXED-row verdicts

### 1. Schedules honest notice — VERIFIED
`05_UI/index.html:1038`: subtitle now reads "Automatic execution is not enabled
yet — saved schedules do not fire on their own. Use 'Run Now' to fire a
schedule today." That is the truth (still no scheduler loop anywhere in
`app.py`; only `POST /api/schedules/{id}/run` at `app.py:1815` does anything).
Caveat: the schedules table still renders a green **"Active"** badge per row
(`index.html:3756-3758`), which quietly re-promises the automation the subtitle
just disclaimed. See New Findings N4.

### 2. Start Here.bat kills stale :8000 listener — VERIFIED
`Start Here.bat:48-55`: before launching, a `for /f "tokens=5"` loop over
`netstat -ano | findstr :8000 | findstr LISTENING` taskkills the PID. Syntax is
sound: `^|` escaping inside the single-quoted command is correct, `tokens=5` is
the PID column for both IPv4 and IPv6 rows, `:8000` cannot false-match `:8001`
or `:18000` as a substring, `LISTENING` filters out client connections, and the
new `echo` line contains no parens needing escapes. The kill runs after `pushd`
and before `start "" /b`, so the wait loop at line 61-64 and the browser open
at line 73 now consistently target the fresh instance on 8000.
Two behavioral notes (not blockers, see Regressions R3): a relaunch mid-run now
silently kills an in-flight 40-minute analysis, and if `taskkill` fails
(access denied) the original stale-server bug path returns — the new server
port-walks (`app.py:1929-1942`) while the browser still opens 8000.

### 3. Lost-contact state + /api/active_runs reattach banner — VERIFIED (with a scope gap)
- Backend: `GET /api/active_runs` exists (`app.py:1163-1183`), returns only
  `status == "running"` runs with a lean payload (no log). Probed live:
  returns `[]` with nothing running; `test_active_runs_lists_only_running`
  passes and asserts the log is excluded.
- Lost-contact: `MAX_POLL_FAILURES = 10` + `LOST_CONTACT_MSG`
  (`index.html:1124-1127`); the Generate poll counts consecutive failures and
  flips the run view to "Lost contact with the run" with the canonical
  relaunch steps (`index.html:2293-2310`, triggered at 2314 and in the catch
  at 2449); the Format poll has the same guard (`index.html:3280-3293`); the
  reattach poll too (`index.html:3067-3080`). Success resets the counter.
- Reattach: banner markup at `index.html:437-442`, `loadActiveRuns()` called
  on load (`index.html:3122`), `reattachRun`/`_reattachPoll`
  (`index.html:3026-3117`) resume the live log, elapsed clock, and terminal
  states; a completed reattached generate run loads Downloads.

Scope gap: the fix covers the full-report Generate path and Format only. Three
poll loops were NOT given the lost-contact treatment and still spin forever
after a server restart — see Regressions R1. Verdict stands for what the
disposition claims ("poll loops" plural is generous), but the gap matters.

### 4. Rebuild/preview config-key bug (`_client_meta`) — VERIFIED
`app.py:322-338`: `_client_meta()` reads the top-level-keyed config exactly
like `/api/clients` does, with a legacy `{"clients": {...}}` fallback. Used by
both the rebuild path (`app.py:1475`) and the HTML preview path
(`app.py:1677`). The rebuild response echoes the resolved `client_name`
(`app.py:1497`) and the UI displays it, injected safely via `textContent`
(`index.html:2794-2800`), so a numeric name is visible before the deck ships.
All 4 dedicated tests pass, including the endpoint-level one asserting
`ClientInfo` gets the real name and eligibility codes
(`05_UI/tests/test_operator_fixes.py:50-85`).

### 6. History drill-in — VERIFIED
- Product column: parsed from the log's STEP 2 header (`app.py:430-437`). I
  checked the regexes against what the analysis runner actually writes
  (`01_Analysis/run.py:372-380`, e.g. "STEP 2: ARS + TXN ANALYSIS + POWERPOINT
  GENERATION") — all three patterns match, and the combined pattern is checked
  first so it can't be shadowed by the TXN one.
- Modules column: max of `Module N/M` totals (`app.py:439-441`), no longer a
  duplicate of the slide count; the History row renders `r.modules` and
  `r.slides` in separate cells (`index.html:2912`, `2916`).
- View log: 9th column header (`index.html:1025`), per-row button
  (`index.html:2920-2925`), expandable `colSpan=9` tail row rendered in-page
  (`toggleRunLog`, `index.html:2959-2997`).
- `GET /api/run_log_tail` (`app.py:1737-1771`): probed live — `..%2F..%2Fapp.py`,
  `..%5C..%5Csecret`, `a%2Fb.log`, and blank name all return 400; `csm=..`
  returns 400; missing log returns 404; resolved path must sit under 04_Logs.
  Tail capped at 400 lines. Tests cover the same cases and pass.

### 8. Scorecard rendered — VERIFIED
The "View scorecard" expander exists in the Run Quality panel
(`index.html:851-858`) and `loadRunQuality()` fills the `<pre>` with
`q.scorecard_md` when present, hiding the expander when absent
(`index.html:2046-2055`). The API already shipped the content
(`app.py:1338-1344`). Scope note: this renders only on the Generate tab's
completion card — History still has no route to it, which is part of the
deferred #6-adjacent queue, not this row.

### 13. Blank client = format ALL confirm — VERIFIED (count still missing)
`index.html:3205-3212`: blank client now triggers a confirm naming the CSM and
month ("this will format ALL of {csm}'s clients for {month}") and adds an
overwrite warning on Force Re-Format. The disposition's "confirm with
count/CSM" overstates slightly: no client count is fetched ("N clients found"
from the round-1 suggestion is absent). The dangerous silent path is gone,
which is the substance of the fix.

### 15. Hardcoded james.gilmore header — VERIFIED
`index.html:432` is now an empty `#hUser` div; `updateHeaderUser()`
(`index.html:1130-1133`) fills it from the selected CSM on load
(`index.html:3654`) and on change of either CSM dropdown
(`index.html:3658-3659`). No hardcoded name remains.

### 17. Canonical recovery string — VERIFIED
`SERVER_UNREACHABLE_MSG` (`index.html:1122-1123`) matches CLAUDE.md's canonical
recovery ("Close the Velocity Pipeline window, double-click Start Here.bat,
then refresh (Ctrl+Shift+R)") and is used by `smartRunGen`'s failure alert
(`index.html:3673`) and the module-list failure (`index.html:1302`). The only
remaining "app.py" occurrence in index.html is a code comment (line 1121).
Caveat: the string is now shown for a case where the server is reachable —
see Regressions R4.

**FIXED-row score: 9 of 9 VERIFIED** (2 with caveats: #3 scope gap, #13
missing count).

## Part 2: Regressions and gaps introduced or left by the fixes

### R1 (MAJOR): three poll loops still spin forever after a server restart
The lost-contact fix was applied to the full-report Generate and Format polls
but not to:
- **By-module batch queue** (`index.html:1447-1475`): after a restart,
  `/api/run/{id}` returns 404, `run.json()` is `{"detail": ...}`, so
  `run.status` is `undefined` and `if (run.status && run.status !== 'running')`
  never terminates — the queue shows "Running…" until the tab is closed. The
  network-error catch is `catch(e) { continue; }` (`index.html:1451-1452`).
- **`runOneModule`** (`index.html:1349-1367`): same structure, same infinite
  loop.
- **Companion-run watcher** (`_startCompanionRun`, `index.html:2073-2093`):
  `if (!r.ok) return;` inside a `setInterval` that is never cleared on
  failure — it silently polls a dead run every 5 s forever, and the companion
  strip freezes on its last message.

This is exactly the finding-3b failure class, unfixed on the module path Dana
uses for per-module decks. Fix is mechanical: reuse the `MAX_POLL_FAILURES`
counter pattern in all three.

### R2 (MINOR): programmatic `showPage()` breaks the nav highlight
`showPage` reads the global `event` and does `event.target.classList.add('on')`
(`index.html:1113-1118`). The new reattach banner button calls
`showPage('generate')` programmatically (`index.html:3018-3021`, via
`reattachRun` at 3028), so the click's `event.target` is the banner button:
all nav tabs lose their highlight and the banner button gets a stray `on`
class. Same latent issue for the completion card's "Open Generate tab" button
(`index.html:3356`). Nothing throws; purely cosmetic, but it debuts with the
new banner.

### R3 (MINOR, decision wanted): the stale-kill can kill a live run
Before e4cc64d, double-clicking `Start Here.bat` while a 40-minute run was in
flight left the old server (and its run) alive on 8000. Now
`Start Here.bat:52-55` force-kills that PID with no "a run is in progress"
check — the run dies silently and, because `runs{}` is in-memory, leaves no
trace. The old behavior had the stale-code hazard; the new one has a
kill-the-run hazard. Suggested mitigation: before taskkill, curl
`/api/active_runs` and warn ("A run is in progress on the old server — close
this window to leave it alone, or press a key to replace it").
Related: if `taskkill` fails (permissions), the launcher still opens 8000 while
the new server walks to 8001 (`app.py:1929-1942`) — the original round-1
finding-2 failure returns on that path. Low probability on the work PC.

### R4 (MINOR): module-list failure now blames the launcher
`renderModuleChecklist`'s catch (`index.html:1299-1304`) shows
`SERVER_UNREACHABLE_MSG` when `/api/modules` returns an empty list — but the
common cause is a missing/corrupt `tools/sections.json` on a running server
(`app.py:665-676` returns `[]` and prints the regeneration command to a console
Dana never sees). Round 1's message told her to check the wrong thing; the new
message tells her to do a restart ritual that cannot fix it. Interacts with
deferred #7 — see promote list.

No other regressions found: no duplicate route registrations (the only
repeated paths are legitimate GET/POST method pairs on `/api/manifest` and
`/api/schedules`), no undefined JS identifiers in the new code (banner
elements, `MAX_POLL_FAILURES`, `LOST_CONTACT_MSG`, `toggleRunLog` all defined
before use), History `colSpan=9` matches its 9-column header, and the batch
file's new block parses (correct `^|` escapes, no unescaped parens).

## Part 3: DEFERRED re-grade and promote list

| # | Round-1 finding | Still present? | Round-2 grade | Action |
|---|-----------------|----------------|---------------|--------|
| 5 | Results dropdown race + cross-tab Preview | Yes — `loadClients` still rebuilds `rClientSel` without `data-csm/month` (`index.html:1270-1279`) racing `loadResultsClients` (`index.html:2938-2954`); both fire on load (3652 and 3121→2931). `openHtmlPreview` still reads the Generate tab's CSM/period and issues the cross-tab alert (`index.html:2506-2512`) | **MAJOR** | **PROMOTE.** The other fixes push Dana toward the Results tab (reattach → downloads → gallery/curate); a race that yields "No results found" for a deck that exists, and a preview that can build the wrong month's client-facing HTML, is now the biggest remaining trap. Fix shape from round 1 still applies: one owner for the dropdown, `_resultsSelection()` for every action. |
| 7 | sections.json recovery CLI-only | Yes — and the in-UI message got more misleading (R4) | MAJOR-lite | **PROMOTE (small).** Distinguish "server unreachable" from "module list empty"; add the Rebuild-module-list button backed by a small endpoint. Until then the UI actively misdirects. |
| 9 | Run Quality speaks auditor | Yes — "law violations", "Investigate (law violations)", and `manifest: unknown` still rendered as-is (`index.html:2001-2011`) | MINOR | Keep queued (copy pass). |
| 10 | Diagnostic → GitHub instructions | Yes — verbatim "paste contents into issue #122" (`index.html:1951`) | MINOR | Keep queued (View/Download buttons). |
| 11 | Fake progress %, Format checklist regex stall | Yes — unchanged guessed regexes (`index.html:1731-1743`), log-line-count progress (`app.py:935`, `1139`) | MINOR | Keep queued, but note the stall can still cause a STOP ALL on a healthy run — stage markers in the formatter remain the right fix. |
| 12 | Months dropdown 6-period cap | Yes (`app.py:757-758`) | MINOR | Keep queued. |
| 16 | Gallery titles from filenames | Yes (`index.html:3475-3481`) | MINOR | Keep queued; folds naturally into the #5 Results refactor if promoted. |
| 18 | Onboarding drifts | Yes — all three confirmed: `INSTALL.md:33` ("has not been set up yet") vs `Start Here.bat:26` ("No Python found"); `CSM Setup.bat:41` verifies a hardcoded 5-package import (no duckdb, relevant with v3 coming); manifest-seed hint still SETUP.md-only | MINOR | Keep queued; the CSM Setup package check is the one to do before any v3 dependency lands. |
| 14 (OPEN) | Schedules always current-month | Yes — `app.py:1824` still `month = now`, form has no period concept | MINOR | Keep with feat/schedule-execution; the honest subtitle (#1) partially defuses the trust risk. |

**Promote: #5 (MAJOR) and #7 (small).** Everything else can stay in the queue
for Dana's month.

## Part 4: New findings (fresh eyes)

### N1 (MINOR): reattach banner only surfaces the first active run
`loadActiveRuns` renders `active[0]` only (`index.html:3011-3016`). With "Run
BOTH products in parallel" — an advertised checkbox (`index.html:717-720`) —
a refresh mid-parallel leaves the second run invisible again (the exact
finding-3 failure, for run #2). Banner should list each active run or say
"2 runs in progress".

### N2 (MINOR): lost-contact re-enables the button while the job may still burn
When the Generate poll gives up (`index.html:2293-2310`), the run button is
re-enabled — but the analysis subprocess survives a server crash (it is a
detached child writing to the M: share). After relaunching, Dana can start a
second run for the same client with no 409 (the new server's `runs{}` is
empty), colliding on outputs — the #232 class, now reachable through the very
recovery path we tell her to use. The disk-persisted run state from round-1
finding 3(c) remains the real fix; until then the lost-contact copy could add
"wait a few minutes before re-running this client".

### N3 (MINOR): `active_runs` trusts in-memory status with no staleness check
`_active_run` ignores runs older than `STALE_RUN_SECONDS` for the 409 guard
(`app.py:213-214`), but `/api/active_runs` (`app.py:1163-1183`) applies no such
filter — a hung subprocess shows a reattach banner with "(500m elapsed)"
forever until server restart. Cheap fix: reuse the same staleness cutoff.

### N4 (MINOR): schedules row badge contradicts the honest subtitle
The green "Active" badge (`index.html:3756-3758`) is the strongest visual
signal on the Schedules tab and still implies the schedule will fire. Until
execution ships, "Saved (manual)" or similar would keep the tab honest at the
row level, not just in the subtitle.

### N5 (NOTE): reattached runs skip the completion card
By design (`index.html:3039-3041`), a reattached run ends with a title line
("Run complete") and Downloads, but no completion card, warnings panel, or Run
Quality panel. Acceptable minimal state; worth folding into the #5/Results
work so post-run quality has one home regardless of how the run was watched.

## Verdict summary

- FIXED rows verified: **9/9 VERIFIED** (caveats on #3 — three poll loops out
  of scope — and #13 — no client count in the confirm).
- Live probes: traversal rejection (5 cases → 400), missing log → 404,
  active_runs shape, run_quality empty-shape, version stamp — all as claimed.
  Test suite: 9/9 pass.
- Regressions: 1 MAJOR (R1 module-queue/companion polls spin forever), 3 MINOR
  (R2 nav highlight, R3 stale-kill vs live run, R4 misleading module-list
  message).
- Promote from DEFERRED: **#5** (Results race + cross-tab preview, MAJOR) and
  **#7** (module-list recovery, small but now actively misleading).
