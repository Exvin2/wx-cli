from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from wx import cli
from wx.openrouter_client import OpenRouterError, OpenRouterResponse


def _write_state(state_dir: Path, payload: dict[str, object]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "last_query.json").write_text(json.dumps(payload, ensure_ascii=True))


def test_explain_offline_mode(cli_runner: CliRunner, state_dir: Path) -> None:
    payload = {
        "command": "forecast",
        "question": "Forecast request",
        "feature_pack": {"units": {"temp": "F", "wind": "mph", "precip": "in"}},
    }
    _write_state(state_dir, payload)

    result = cli_runner.invoke(
        cli.app,
        ["", "explain"],
        env={"WX_OFFLINE": "1", "WX_STATE_DIR": str(state_dir)},
    )

    assert result.exit_code == 0
    assert "Explain (offline)" in result.stdout
    assert "Explain mode" in result.stdout


def test_explain_online_mocked(
    monkeypatch: pytest.MonkeyPatch, cli_runner: CliRunner, state_dir: Path
) -> None:
    payload = {
        "command": "forecast",
        "question": "Forecast request",
        "feature_pack": {"units": {"temp": "F"}},
    }
    _write_state(state_dir, payload)

    response_body = {
        "sections": {"summary": ["Mocked explanation content."]},
        "confidence": {"value": 88, "rationale": "mock"},
        "used_feature_fields": ["units.temp"],
        "bottom_line": "Mock bottom line.",
    }

    def _mock_chat_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return OpenRouterResponse(
            text=json.dumps(response_body),
            model="test/model",
            raw={"choices": []},
            usage={"total_tokens": 42},
            headers={},
            attempts=1,
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PRIVACY_MODE", "0")
    monkeypatch.setenv("WX_OFFLINE", "0")
    monkeypatch.setenv("WX_STATE_DIR", str(state_dir))
    monkeypatch.setenv("OPENROUTER_MODEL", "test/model")
    monkeypatch.setattr("wx.forecaster.chat_completion", _mock_chat_completion)

    result = cli_runner.invoke(cli.app, ["--verbose", "", "explain"])

    assert result.exit_code == 0
    assert "Explain (online)" in result.stdout
    assert "Mocked explanation content." in result.stdout
    assert "Explain Meta" in result.stdout
    assert "test/model" in result.stdout


def test_explain_respects_privacy(
    monkeypatch: pytest.MonkeyPatch, cli_runner: CliRunner, state_dir: Path
) -> None:
    monkeypatch.setenv("PRIVACY_MODE", "1")
    monkeypatch.setenv("WX_STATE_DIR", str(state_dir))

    result = cli_runner.invoke(cli.app, ["", "explain"])

    assert result.exit_code == 1
    assert "Disable privacy mode" in result.stdout


def test_explain_handles_openrouter_errors(
    monkeypatch: pytest.MonkeyPatch, cli_runner: CliRunner, state_dir: Path
) -> None:
    payload = {
        "command": "forecast",
        "question": "Forecast request",
        "feature_pack": {"units": {"temp": "F"}},
    }
    _write_state(state_dir, payload)

    def _raise_error(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OpenRouterError("rate-limit", status_code=429)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("WX_STATE_DIR", str(state_dir))
    monkeypatch.setattr("wx.forecaster.chat_completion", _raise_error)

    result = cli_runner.invoke(cli.app, ["--verbose", "", "explain"])

    assert result.exit_code == 0
    assert "Explain (fallback)" in result.stdout
    assert "rate-limit" in result.stdout
