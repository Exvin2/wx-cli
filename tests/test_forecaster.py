from __future__ import annotations

import importlib

config = importlib.import_module("wx.config")
forecaster_module = importlib.import_module("wx.forecaster")


def test_forecaster_offline_fallback_sections():
    settings = config.Settings(offline=True, privacy_mode=True)
    forecaster = forecaster_module.Forecaster(settings)
    response = forecaster.generate(
        query="Will it rain?",
        feature_pack={"units": {"temp": "F"}},
        intent="question",
        verbose=False,
    )

    required_sections = {"summary", "timeline", "risk_cards", "confidence", "actions", "assumptions"}
    assert required_sections.issubset(response.sections.keys())
    assert response.bottom_line.startswith("Bottom line")
    assert response.confidence["value"] <= 100
