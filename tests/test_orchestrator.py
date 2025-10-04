from __future__ import annotations

import importlib

config = importlib.import_module("wx.config")
orchestrator_module = importlib.import_module("wx.orchestrator")


def test_forecast_feature_pack_contains_window():
    settings = config.Settings(offline=True, privacy_mode=True)
    orchestrator = orchestrator_module.Orchestrator(settings, trust_tools=False)

    result = orchestrator.handle_forecast(
        "Springfield",
        when_text=None,
        horizon="12h",
        focus="wind",
        verbose=False,
    )

    window = result.feature_pack.get("window")
    assert window is not None
    assert window["horizon"] == "12h"
    assert "units" in result.feature_pack

    # Ensure response uses fallback without raising
    assert "summary" in result.response.sections
    assert result.response.bottom_line
