"""Configuration management for the wx CLI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

DEFAULT_OPENROUTER_MODELS = (
    "x-ai/grok-4-fast:free",
    "openai/gpt-oss-120b:free",
)
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 900
DEFAULT_UNITS = "imperial"
STATE_DIR = Path(os.getenv("WX_STATE_DIR", Path.home() / ".cache" / "wx"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "last_query.json"

UnitsLiteral = Literal["imperial", "metric"]
StyleLiteral = Literal["brief", "standard", "verbose"]
PersonaLiteral = Literal["default", "pilot", "runner", "sailor", "commuter"]


@dataclass(slots=True)
class Settings:
    """Runtime settings resolved from environment variables and CLI options."""

    openrouter_api_key: str | None = field(default=None)
    openrouter_models: tuple[str, ...] = field(default_factory=tuple)
    openrouter_base_url: str = field(default="https://openrouter.ai/api/v1/chat/completions")
    ai_model: str = field(default=DEFAULT_OPENROUTER_MODELS[0])
    ai_temperature: float = field(default=DEFAULT_TEMPERATURE)
    ai_max_tokens: int = field(default=DEFAULT_MAX_TOKENS)
    units: UnitsLiteral = field(default=DEFAULT_UNITS)  # type: ignore[assignment]
    privacy_mode: bool = field(default=True)
    offline: bool = field(default=False)
    debug: bool = field(default=False)
    style: StyleLiteral = field(default="standard")
    persona: PersonaLiteral = field(default="default")
    state_file: Path = field(default=STATE_FILE)
    gemini_api_key: str | None = field(default=None)
    gemini_model: str = field(default="gemini-2.0-flash-exp")

    def to_feature_metadata(self) -> dict[str, Any]:
        """Expose select settings that the model may need to know about."""

        return {
            "units": self.units,
            "style": self.style,
            "persona": None if self.persona == "default" else self.persona,
            "privacy_mode": self.privacy_mode,
        }

    def save_last_query(self, payload: dict[str, Any]) -> None:
        """Persist minimal request data for wx explain when privacy allows."""

        if self.privacy_mode:
            return

        minimal_payload = {
            "feature_pack": payload.get("feature_pack"),
            "question": payload.get("question"),
            "command": payload.get("command"),
            "style": payload.get("style"),
            "persona": payload.get("persona"),
            "timestamp": payload.get("timestamp"),
        }
        try:
            self.state_file.write_text(json.dumps(minimal_payload, ensure_ascii=True, indent=2))
        except OSError:
            # Failing to save state should never crash the CLI.
            pass

    def load_last_query(self) -> dict[str, Any] | None:
        """Load the last saved payload if present."""

        if not self.state_file.exists():
            return None
        try:
            return json.loads(self.state_file.read_text())
        except (OSError, json.JSONDecodeError):
            return None


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_from_env(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_from_env(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_settings(*, debug: bool = False, offline: bool | None = None,
                  style: StyleLiteral | None = None,
                  persona: PersonaLiteral | None = None) -> Settings:
    """Load runtime settings from the environment."""

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    models_env = os.getenv("OPENROUTER_MODELS")
    single_model = os.getenv("OPENROUTER_MODEL")
    ai_model_override = os.getenv("AI_MODEL")

    parsed_models = _parse_models(models_env)
    if not parsed_models:
        parsed_models = _parse_models(single_model)

    if not parsed_models and ai_model_override:
        parsed_models = (ai_model_override,)
    if not parsed_models and openrouter_key:
        parsed_models = DEFAULT_OPENROUTER_MODELS

    if parsed_models:
        ai_model = ai_model_override or parsed_models[0]
    else:
        ai_model = ai_model_override or DEFAULT_OPENROUTER_MODELS[0]
    ai_temperature = _float_from_env(os.getenv("AI_TEMPERATURE"), DEFAULT_TEMPERATURE)
    ai_max_tokens = _int_from_env(os.getenv("AI_MAX_TOKENS"), DEFAULT_MAX_TOKENS)
    units = os.getenv("UNITS", DEFAULT_UNITS)
    privacy_mode = _bool_from_env(os.getenv("PRIVACY_MODE"), True)
    offline_flag = _bool_from_env(os.getenv("WX_OFFLINE"), False)
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

    settings = Settings(
        openrouter_api_key=openrouter_key,
        openrouter_models=parsed_models,
        ai_model=ai_model,
        ai_temperature=ai_temperature,
        ai_max_tokens=ai_max_tokens,
        units="metric" if units.lower().startswith("metric") else DEFAULT_UNITS,
        privacy_mode=privacy_mode,
        offline=offline if offline is not None else offline_flag,
        debug=debug,
        style=style or "standard",
        persona=persona or "default",
        gemini_api_key=gemini_key,
        gemini_model=gemini_model,
    )

    return settings


def _parse_models(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return tuple(parts)
