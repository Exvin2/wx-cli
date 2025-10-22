"""Configuration management for the wx CLI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv

DEFAULT_OPENROUTER_MODELS = ("openrouter/auto",)
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 900
DEFAULT_UNITS = "imperial"
DEFAULT_HTTP_TIMEOUT = 5.0
DEFAULT_HTTP_RETRIES = 2

# Severe weather event filters (floods, severe thunderstorms, tornadoes)
SEVERE_WEATHER_KEYWORDS = {
    "tornado",
    "tor-",
    "tor pds",
    "tor-e",
    "tornado warning",
    "tornado watch",
    "tornado emergency",
    "pds",
    "particularly dangerous situation",
    "flood",
    "flash flood",
    "flooding",
    "severe thunderstorm",
    "severe tstm",
    "tstm",
    "thunderstorm",
}

# Regional sampling points for US + Europe worldview
REGIONAL_SAMPLES = {
    "us": [
        # West coast
        (47.6, -122.3),  # Seattle
        (45.5, -122.7),  # Portland
        (37.8, -122.4),  # San Francisco
        (34.0, -118.2),  # Los Angeles
        (32.7, -117.2),  # San Diego
        # Southwest
        (33.4, -112.1),  # Phoenix
        (36.2, -115.1),  # Las Vegas
        (35.1, -106.6),  # Albuquerque
        # Rockies
        (39.7, -104.9),  # Denver
        (40.8, -111.9),  # Salt Lake City
        # Plains
        (41.3, -96.0),   # Omaha
        (39.1, -94.6),   # Kansas City
        (32.8, -96.8),   # Dallas
        (29.8, -95.4),   # Houston
        # Midwest
        (41.9, -87.6),   # Chicago
        (42.3, -83.0),   # Detroit
        (44.9, -93.3),   # Minneapolis
        # Southeast
        (33.7, -84.4),   # Atlanta
        (30.3, -81.7),   # Jacksonville
        (25.8, -80.2),   # Miami
        (30.0, -90.1),   # New Orleans
        # Northeast
        (40.7, -74.0),   # New York
        (42.4, -71.1),   # Boston
        (39.9, -75.2),   # Philadelphia
        (38.9, -77.0),   # DC
        # Alaska & Hawaii
        (61.2, -149.9),  # Anchorage
        (21.3, -157.9),  # Honolulu
    ],
    "eu": [
        # Iberia
        (40.4, -3.7),    # Madrid
        (41.4, 2.2),     # Barcelona
        (38.7, -9.1),    # Lisbon
        # France
        (48.9, 2.3),     # Paris
        (43.6, 1.4),     # Toulouse
        (43.3, 5.4),     # Marseille
        # Benelux
        (52.4, 4.9),     # Amsterdam
        (50.8, 4.4),     # Brussels
        (49.6, 6.1),     # Luxembourg
        # DACH
        (52.5, 13.4),    # Berlin
        (50.1, 8.7),     # Frankfurt
        (48.1, 11.6),    # Munich
        (47.4, 8.5),     # Zurich
        (48.2, 16.4),    # Vienna
        # UK & Ireland
        (51.5, -0.1),    # London
        (53.5, -2.2),    # Manchester
        (55.9, -3.2),    # Edinburgh
        (53.3, -6.3),    # Dublin
        # Nordics
        (59.3, 18.1),    # Stockholm
        (60.2, 24.9),    # Helsinki
        (59.9, 10.8),    # Oslo
        (55.7, 12.6),    # Copenhagen
        # Baltics
        (59.4, 24.8),    # Tallinn
        (56.9, 24.1),    # Riga
        (54.7, 25.3),    # Vilnius
        # Central/Eastern
        (52.2, 21.0),    # Warsaw
        (50.1, 14.4),    # Prague
        (47.5, 19.0),    # Budapest
        (44.4, 26.1),    # Bucharest
        # Balkans
        (45.8, 15.9),    # Zagreb
        (44.8, 20.5),    # Belgrade
        (42.0, 21.4),    # Skopje
        (41.3, 19.8),    # Tirana
        # Mediterranean
        (41.9, 12.5),    # Rome
        (45.4, 9.2),     # Milan
        (40.9, 14.3),    # Naples
        (37.9, 23.7),    # Athens
    ],
}

# Load environment variables from a local .env if present without overriding existing env
load_dotenv()

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
    openrouter_base_url: str = field(default=DEFAULT_OPENROUTER_BASE_URL)
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
            # Ensure state directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Write with restricted permissions (user read/write only)
            import os
            import tempfile

            # Write to temp file first, then move (atomic operation)
            fd, temp_path = tempfile.mkstemp(
                dir=self.state_file.parent, prefix=".wx_temp_", suffix=".json"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps(minimal_payload, ensure_ascii=True, indent=2))

                # Set restrictive permissions (0o600 = rw-------)
                os.chmod(temp_path, 0o600)

                # Atomic move
                os.replace(temp_path, self.state_file)
            except Exception:  # noqa: BLE001
                # Clean up temp file if something went wrong
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
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


def load_settings(
    *,
    debug: bool = False,
    offline: bool | None = None,
    style: StyleLiteral | None = None,
    persona: PersonaLiteral | None = None,
) -> Settings:
    """Load runtime settings from the environment."""

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    # Validate OpenRouter API key if provided
    if openrouter_key:
        _validate_api_key(openrouter_key, "OPENROUTER_API_KEY")

    openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)
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
    # Validate Gemini API key if provided
    if gemini_key:
        _validate_api_key(gemini_key, "GEMINI_API_KEY")

    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

    state_root = Path(os.getenv("WX_STATE_DIR", str(STATE_DIR)))
    state_root.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        openrouter_api_key=openrouter_key,
        openrouter_models=parsed_models,
        openrouter_base_url=openrouter_base_url,
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
        state_file=state_root / "last_query.json",
    )

    return settings


def _parse_models(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return tuple(parts)


def _validate_api_key(key: str | None, key_name: str) -> bool:
    """Validate API key format and provide warnings if needed."""
    if not key:
        return False

    # Basic validation - check if it looks like a valid API key
    key = key.strip()

    # Check minimum length (most API keys are at least 20 characters)
    if len(key) < 20:
        import sys
        print(
            f"Warning: {key_name} appears to be too short (< 20 chars). "
            f"This may not be a valid API key.",
            file=sys.stderr,
        )
        return False

    # Check for common placeholder values
    placeholders = [
        "your_api_key_here",
        "placeholder",
        "INSERT_KEY_HERE",
        "xxx",
        "test",
        "example",
        "sk-proj-",  # Common prefix for fake keys
    ]
    key_lower = key.lower()
    if any(placeholder in key_lower for placeholder in placeholders):
        import sys
        print(
            f"Warning: {key_name} appears to be a placeholder value. "
            f"Please set a valid API key.",
            file=sys.stderr,
        )
        return False

    # Check for suspicious patterns (spaces, newlines, etc.)
    if any(char in key for char in [" ", "\n", "\r", "\t"]):
        import sys
        print(
            f"Warning: {key_name} contains whitespace characters. "
            f"This is likely an error.",
            file=sys.stderr,
        )
        return False

    return True


def get_openrouter_cfg() -> dict[str, str | None]:
    """Return OpenRouter configuration derived from environment variables."""

    config: dict[str, str | None] = {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
        "model": os.getenv("OPENROUTER_MODEL"),
    }

    if not config["model"]:
        models = _parse_models(os.getenv("OPENROUTER_MODELS"))
        if models:
            config["model"] = models[0]

    if not config["model"]:
        config["model"] = DEFAULT_OPENROUTER_MODELS[0]

    return config


def get_http_config() -> dict[str, Any]:
    """Return HTTP configuration for fetchers."""
    return {
        "timeout": float(os.getenv("WX_HTTP_TIMEOUT", str(DEFAULT_HTTP_TIMEOUT))),
        "retries": int(os.getenv("WX_HTTP_RETRIES", str(DEFAULT_HTTP_RETRIES))),
    }
