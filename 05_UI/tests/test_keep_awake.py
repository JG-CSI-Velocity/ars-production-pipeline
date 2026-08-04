"""Keep-awake guard: run threads must block Windows idle-sleep (#251).

A cold TXN load streams gigabytes off the M: share; the machine idling to
sleep mid-run kills hours of work. Each run thread requests
ES_CONTINUOUS | ES_SYSTEM_REQUIRED at startup; the requirement clears itself
when the thread exits, so there is nothing to unwind.
"""

from __future__ import annotations

import ctypes


def test_noop_on_non_windows(app_module, monkeypatch):
    monkeypatch.setattr(app_module.platform, "system", lambda: "Darwin")
    assert app_module._keep_system_awake() is False


def test_requests_system_required_on_windows(app_module, monkeypatch):
    calls = []

    class _Kernel32:
        @staticmethod
        def SetThreadExecutionState(flags):
            calls.append(flags)
            return flags

    class _WinDLL:
        kernel32 = _Kernel32()

    monkeypatch.setattr(app_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ctypes, "windll", _WinDLL(), raising=False)

    assert app_module._keep_system_awake() is True
    assert calls == [app_module._ES_CONTINUOUS | app_module._ES_SYSTEM_REQUIRED]


def test_windows_api_failure_is_swallowed(app_module, monkeypatch):
    class _WinDLL:
        @property
        def kernel32(self):
            raise OSError("no kernel32 here")

    monkeypatch.setattr(app_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ctypes, "windll", _WinDLL(), raising=False)

    assert app_module._keep_system_awake() is False


def test_every_run_thread_calls_keep_awake(app_module):
    # All three run-launching endpoints spawn a thread whose body opens with
    # the keep-awake call -- source-level check so a new launch site that
    # forgets the guard fails loudly here.
    import inspect

    src = inspect.getsource(app_module)
    assert src.count("_keep_system_awake()") >= 4  # 1 def + 3 call sites
