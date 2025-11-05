# wx – NWS AI Weather Bot

wx is a conversational AI weather assistant that provides real-time weather data from the National Weather Service (NWS) and other sources. It combines powerful AI models with live weather data to answer your questions naturally.

## Highlights
- **Conversational AI Bot**: Interactive chat mode for natural language weather queries
- **Live NWS Data**: Real-time alerts, forecasts, observations, and gridded data from NOAA
- **Enhanced Data Fetching**: Comprehensive NWS integration including forecast grids, observation stations, and hourly forecasts
- **EU Weather Alerts**: Full MeteoAlarm XML parsing for European weather warnings
- **Secure & Private**: API key validation and restricted file permissions for cached data
- **Multiple Modes**: Freeform questions, structured forecasts, risk assessment, and interactive chat
- **Smart Rendering**: Improved word limiting with fair allocation across response sections
- **Timezone Aware**: Properly handles local timezones in forecast windows
- Routes through OpenRouter (Grok → ChatGPT OSS) with automatic Gemini fallback
- Privacy-first defaults: no Feature Pack history is written unless `PRIVACY_MODE=0`

## Installation

### Quick Start (All Platforms)
```bash
pip install -e .
```

Requires Python 3.11+. A `wx` console script is registered on install.

### Windows Installation
For Windows users, we provide an automated installation script:

```powershell
.\install.ps1
```

This will:
- Check Python version
- Create a virtual environment
- Install dependencies
- Set up your `.env` configuration interactively

For Windows-specific features (notifications, Task Scheduler), see [Windows Setup Guide](docs/WINDOWS_SETUP.md).

**Windows Optional Features:**
```powershell
# Install Windows-specific features (notifications, file permissions)
pip install -e .[windows]
```

## Configuration
wx automatically loads a local `.env` file if present (see `.env.example` for a starter template).
Set environment variables directly or via `.env` to tune behaviour:

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
| `NWS_API_KEY` | Reserved for future National Weather Service integrations | – |

Use CLI flags `--offline` and `--trust-tools` to temporarily override environment defaults.

## Usage

### Interactive Chat Mode (NEW!)
Start a conversational session with the AI weather bot:
```bash
wx chat
```

In chat mode, you can:
- Ask questions naturally: "What's the weather like in Seattle?"
- Set location context: `/location Denver, CO`
- Get severe weather alerts: "Are there any tornado warnings in Oklahoma?"
- Clear history: `/clear`
- Exit: `/quit` or Ctrl+D

### Command-Line Queries
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
- Alert headlines (add `--ai` to triage via the model):
  ```bash
  wx alerts "38.90,-77.04" --ai
  ```
- Explain last run (requires `PRIVACY_MODE=0` so the Feature Pack can be cached):
  ```bash
  wx explain
  ```

### Global Options
- `--json` - Print raw JSON response with Feature Pack and metadata
- `--debug` - Show timing and provider details (never prints API secrets)
- `--verbose` - Allow responses beyond 400 words
- `--offline` - Skip all network fetchers
- `--trust-tools` - Enable network micro-fetchers for enhanced data

## Windows-Specific Features

wx-cli includes special features for Windows 10/11 users:

### Desktop Notifications
Get toast notifications for severe weather alerts:
```powershell
# Install notification support
pip install -e .[windows]

# Enable in .env
WX_NOTIFICATIONS=1

# Test notifications
python wx\notifications_windows.py
```

### Task Scheduler Integration
Automate weather checks with Windows Task Scheduler:
```powershell
# Set up automated tasks (requires Administrator)
.\scripts\setup-scheduled-task.ps1

# Options:
# - Morning weather briefing (7:00 AM daily)
# - Severe weather monitoring (every 30 minutes)
# - Custom schedules
```

### Configuration Wizard
User-friendly GUI for configuration (no command-line needed):
```powershell
python wx\config_wizard.py
```

### Enhanced File Security
Windows-specific file permissions using ACLs for secure cache file storage.

For complete Windows setup instructions, see [Windows Setup Guide](docs/WINDOWS_SETUP.md).

## Testing
```bash
pytest
```

## Security & Privacy

### API Key Validation
wx validates API keys on startup to detect common issues:
- Keys shorter than 20 characters trigger warnings
- Placeholder values (e.g., "your_api_key_here") are rejected
- Keys with whitespace characters are flagged as errors

### File Permissions
When `PRIVACY_MODE=0`, cached data is stored in `~/.cache/wx/` with:
- Restrictive permissions (0600 = owner read/write only)
- Atomic file writes using temporary files
- No sensitive API keys are ever written to cache files

### Privacy Considerations
- Default `PRIVACY_MODE=1` prevents any history from being saved
- Set `PRIVACY_MODE=0` only if you need the `wx explain` feature
- Location and timing information is saved when privacy mode is disabled
- All API requests use HTTPS and respect standard timeout limits

## Limitations & Safety
wx is an advisory tool. It does **not** replace official forecasts, warnings, or aviation weather briefings. Always consult your national weather service before acting on critical decisions.

Privacy mode blocks history persistence; disable it explicitly when you want `wx explain` to recall the last Feature Pack. Offline mode and missing API keys return qualitative summaries so you still get a truthful answer.

## Getting Started

### Quick Examples
```bash
# Start interactive chat
wx chat

# Ask anything quickly
wx "Morning commute weather for Boston?"

# Focus on marine winds with model context
wx forecast "Key West" --focus marine --trust-tools

# Review alerts without AI triage
wx alerts "Seattle"

# Check severe weather nationwide
wx --severe
```

### Advanced Examples
```bash
# Get comprehensive NWS data for a location (gridded forecast, stations, observations)
# This is used internally by the chat bot when you ask detailed questions

# Get hourly forecast with timezone information
wx forecast "Chicago" --horizon 24h --when "tomorrow 3pm"

# Risk assessment for multiple hazards
wx risk "Miami" --hazards flooding,wind,storm --verbose

# Interactive conversation with location context
wx chat
# Then in chat: /location Portland, OR
# Then ask: What's the forecast for tomorrow?
```

## License

This project is distributed under a proprietary, all-rights-reserved license.
Contact the maintainers for commercial or redistribution permissions.
