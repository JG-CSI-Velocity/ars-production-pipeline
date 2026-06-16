# Installing the Velocity Pipeline

There are two parts here. **CSMs only ever read the first part.** The second
part is for James — how it actually works and how to rebuild the bundle.

---

## For CSMs — getting set up (read this only)

You open the same shared folder you always open. Two files matter:

| File | When you use it |
|---|---|
| **`CSM Setup.bat`** | Double-click **once**, the very first day. |
| **`Start Here.bat`** | Double-click **every time** you want to use the tool. |

### The first day (once)

1. Double-click **`CSM Setup.bat`**.
2. Wait until it says **`Done`** (a few minutes — it's downloading once).
3. Close that window.

### Every day after that

1. Double-click **`Start Here.bat`**.
2. The tool opens in your browser.

That's it. You never type anything, never open a black command window, and
never install Python yourself.

### If something goes wrong

- **`Start Here.bat` says "This computer has not been set up yet"** → you
  skipped the first day. Double-click `CSM Setup.bat` once, wait for `Done`,
  then try `Start Here.bat` again.
- **`CSM Setup.bat` says it couldn't download** → check your internet and run
  it again. If it still fails, screenshot the window and send it to James.

---

## For James — how it works and how to rebuild

### The idea

The CSM machines don't have Python, or have Python but none of our packages
(see issue #226 — one machine had Python 3.12 but `ModuleNotFoundError: No
module named 'fastapi'`). Rather than install Python on every machine by hand,
we ship a **self-contained Python** — interpreter plus all 14 packages from
`requirements.txt` — and the launcher uses *that* instead of the system Python.

Two locations, and only two:

| What | Where | Changes |
|---|---|---|
| Python + all packages | **Local** on each machine: `%LOCALAPPDATA%\Velocity\python\` | Once, dropped by `CSM Setup.bat` |
| Code, data, outputs, the `.bat` files | **On the share**: `\\PADMIS105\Velocity_Company\ARS\` | Weekly, centrally (unchanged) |

The interpreter goes **local** because loading pandas / numpy / matplotlib
(thousands of files) over the network share on every launch is slow. The code
and data stay **on the share** so the weekly update flow and the `code:`
version stamp are untouched. Nothing needs admin rights — `%LOCALAPPDATA%` is
always writable by the user.

### The three pieces

1. **`CSM Setup.bat`** (repo root) — downloads the bundle and unpacks it to
   `%LOCALAPPDATA%\Velocity\`. Idempotent: if it's already installed it just
   says `Done`.
2. **`Start Here.bat`** (repo root, rewritten) — runs the server with the
   bundled Python (`%LOCALAPPDATA%\Velocity\python\python.exe`). Also fixed the
   real bug from #226: it used `cd /d` on the `\\PADMIS105\...` UNC path, which
   Windows silently refuses, dropping the user into `C:\Windows\System32`. Now
   uses `pushd`, which maps a temp drive for UNC paths.
3. **`.github/workflows/build-python-bundle.yml`** — builds the bundle in the
   cloud on a Windows runner and publishes it as the `python-bundle` release
   asset. You never need a Windows machine to produce it.

### Rebuilding the bundle (when requirements.txt changes)

It rebuilds automatically when you push a change to `requirements.txt`. To
build it by hand: **GitHub → Actions tab → "Build Python Bundle" → Run
workflow.** When it finishes, the new bundle is the `python-bundle` release
asset, and `CSM Setup.bat` will pick it up on the next run.

The download URL baked into `CSM Setup.bat` is a **fixed tag** on purpose:

```
https://github.com/JG-CSI-Velocity/ars-production-pipeline/releases/download/python-bundle/Velocity-Python.zip
```

Not `releases/latest/...` — "latest" points at whatever the most recent
release is (right now that's `deck-polish-v0.1.0-pre`), which is the wrong file.

### When a CSM needs the new bundle

Code updates (the weekly `.py` changes) need **nothing** new from the CSM — the
bundle only holds third-party packages. A CSM re-runs `CSM Setup.bat` **only**
when the package list itself changes. To force a clean reinstall, delete
`%LOCALAPPDATA%\Velocity\` and run `CSM Setup.bat` again.

### Not yet verified on Windows

The two `.bat` files and the workflow were written on macOS and have **not**
been run on a real Windows/UNC machine yet. First real tests:
1. Trigger the workflow and confirm `Velocity-Python.zip` publishes.
2. Run `CSM Setup.bat` then `Start Here.bat` on one CSM machine.
