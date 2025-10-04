# wx – Mostly-AI Weather CLI

wx is a lightweight command-line interface that wraps an AI forecaster prompt. It collects a tiny "Feature Pack" of context, hands it to Grok or ChatGPT OSS via OpenRouter (with Gemini fallback), and renders a concise meteorological briefing in your terminal.

## Highlights
- Mostly-AI philosophy: the model does the heavy lifting, optional micro-fetchers add just enough context.
- Typer-powered CLI with Rich output, single entry point `wx`.
- Routes through OpenRouter (Grok → ChatGPT OSS) with automatic Gemini fallback.
- Privacy-first defaults: no Feature Pack history is written unless `PRIVACY_MODE=0`.
- Honest offline mode: fallbacks explain limitations instead of failing.

## Installation
```bash
pip install -e .
```

Requires Python 3.11+. A `wx` console script is registered on install.

## Configuration
Set environment variables to tune behaviour:

| Variable | Description | Default |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | API key for OpenRouter (Grok / ChatGPT OSS routing) | – |
| `OPENROUTER_MODEL` / `OPENROUTER_MODELS` | Preferred OpenRouter model (`x-ai/grok-2-latest`, `openai/chatgpt-4o-latest`, …). Comma-separated for fallbacks. | Grok → ChatGPT OSS |
| `AI_MODEL` | Overrides the first OpenRouter model when set | Derived from models |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | API key for Google Gemini fallback | – |
| `GEMINI_MODEL` | Override Gemini model (`gemini-2.0-flash-exp`, …) | `gemini-2.0-flash-exp` |
| `AI_TEMPERATURE` | Sampling temperature | `0.2` |
| `AI_MAX_TOKENS` | Max output tokens | `900` |
| `UNITS` | `imperial` or `metric` | `imperial` |
| `PRIVACY_MODE` | `1` keeps history off disk; set `0` to enable `wx explain` | `1` |
| `WX_OFFLINE` | `1` skips all network fetchers | `0` |

Use CLI flags `--offline` and `--trust-tools` to temporarily override environment defaults.

## Usage
- Freeform question:
  ```bash
  wx "Will thunderstorms impact Nashville after 6 pm?"
  ```
- Structured forecast:
  ```bash
  wx forecast "Glasgow" --horizon 24h --focus wind
  ```
- Risk cards by hazard:
  ```bash
  wx risk "San Diego" --hazards fire,wind
  ```
- Explain last run (requires `PRIVACY_MODE=0` so the Feature Pack can be cached):
  ```bash
  wx explain
  ```
- Alert headlines (add `--ai` to triage via the model):
  ```bash
  wx alerts "38.90,-77.04" --ai
  ```

`--json` prints the raw Feature Pack and model response metadata. `--debug` adds timing and provider details (never prints API secrets).

## Testing
```bash
pytest
```

## Limitations & Safety
wx is an advisory tool. It does **not** replace official forecasts, warnings, or aviation weather briefings. Always consult your national weather service before acting on critical decisions.

Privacy mode blocks history persistence; disable it explicitly when you want `wx explain` to recall the last Feature Pack. Offline mode and missing API keys return qualitative summaries so you still get a truthful answer.

## Getting Started
```bash
# Ask anything quickly
wx "Morning commute weather for Boston?"

# Focus on marine winds with model context
wx forecast "Key West" --focus marine --trust-tools

# Review alerts without AI triage
wx alerts "Seattle"
```

## License

This project is distributed under a proprietary, all-rights-reserved license.
Contact the maintainers for commercial or redistribution permissions.
