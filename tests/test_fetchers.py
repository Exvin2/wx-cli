from __future__ import annotations

import importlib

fetchers = importlib.import_module("wx.fetchers")


def test_get_quick_obs_handles_failures(monkeypatch):
    def fail_request(*args, **kwargs):
        return None

    monkeypatch.setattr(fetchers, "_safe_request", fail_request)
    result = fetchers.get_quick_obs(35.0, -97.0, offline=False)
    assert result is None


def test_get_point_context_offline():
    assert fetchers.get_point_context("35,-97", offline=True) is None
