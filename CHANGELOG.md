# Changelog

## [Unreleased] - NWS AI Bot Enhancement

### Major Features Added

#### 🤖 Conversational AI Chat Interface
- **New `wx chat` command** - Interactive conversational mode for natural language weather queries
- Session management with conversation history
- Location context persistence across queries
- Special commands:
  - `/location <place>` - Set default location context
  - `/clear` - Clear conversation history
  - `/help` - Display help information
  - `/quit` - Exit chat session
- Context-aware query enhancement (includes recent conversation and location)
- Rich terminal interface with colored output and panels

#### 🌐 Enhanced NWS Data Fetching
- **New NWS API endpoints integrated:**
  - `get_nws_forecast_grid()` - Gridded forecast data with 7-day periods
  - `get_nws_observation_stations()` - Nearby observation stations
  - `get_nws_latest_observation()` - Latest observations from specific stations
  - `get_nws_hourly_forecast()` - Hourly forecast data (24 hours)
  - `get_comprehensive_nws_data()` - Combined fetcher for all NWS data sources
- Comprehensive weather data including:
  - Temperature, dewpoint, wind speed/direction, gusts
  - Barometric pressure, visibility, relative humidity
  - Heat index and wind chill
  - Cloud layers and present weather conditions
  - Grid point metadata (grid_id, grid_x, grid_y)

#### 🌍 EU MeteoAlarm XML Parsing
- **Implemented full XML parsing** for European weather alerts (previously stubbed)
- Supports both RSS and CAP (Common Alerting Protocol) formats
- Extracts alert severity, event types, affected areas, and expiration times
- Filters for severe weather when `--severe` flag is used
- Properly handles XML namespaces and malformed data

### Security & Privacy Improvements

#### 🔒 API Key Validation
- Added comprehensive API key validation on startup
- Detects common issues:
  - Keys shorter than 20 characters
  - Placeholder values (e.g., "your_api_key_here", "xxx", "test")
  - Keys containing whitespace characters
- Validation for both OpenRouter and Gemini API keys
- Warnings printed to stderr without exposing key contents

#### 🔐 Enhanced File Permissions
- **Secure cache file handling** when `PRIVACY_MODE=0`
- Atomic file writes using temporary files
- Restrictive permissions (0600 = owner read/write only)
- Prevents race conditions and unauthorized access
- Proper cleanup on errors

### Bug Fixes & Improvements

#### 📊 Word Limiting Logic
- **Fixed unpredictable section truncation**
- Implemented fair allocation across response sections:
  - Summary: 30%
  - Timeline: 25%
  - Risk Cards: 20%
  - Confidence: 10%
  - Actions: 10%
  - Assumptions: 5%
- Section budgets prevent important information from being cut off
- Better user experience with more predictable output

#### 🕐 Timezone Handling
- **Improved timezone support** in forecast windows
- Now includes both UTC and local timezone information
- Uses Python's `zoneinfo` for accurate timezone conversions
- Forecast windows include:
  - `start_iso` / `end_iso` (UTC)
  - `start_local` / `end_local` (local timezone)
  - `timezone` (IANA timezone name)
- Graceful fallback to UTC if timezone conversion fails

### Documentation Updates

#### 📚 README Enhancements
- Updated project description to emphasize NWS AI bot capabilities
- Added comprehensive chat mode documentation
- Security & Privacy section with detailed information
- Advanced usage examples
- Improved getting started guide

### Technical Improvements

#### 🏗️ Architecture
- New `wx/chat.py` module for conversational interface
- `ConversationSession` class for managing chat state
- `ConversationMessage` dataclass for message history
- `ChatInterface` class with rich terminal UI

#### 🔄 Concurrent Data Fetching
- Enhanced parallel fetching in `get_comprehensive_nws_data()`
- Uses ThreadPoolExecutor with 5 workers for optimal performance
- Fetches forecast, hourly, stations, and alerts simultaneously
- Automatically retrieves latest observation from nearest station

#### 🛡️ Error Handling
- Improved error handling in XML parsing (catches `ET.ParseError`)
- Better exception handling in timezone conversion
- Graceful degradation when NWS endpoints are unavailable
- Prevents crashes from malformed API responses

### Breaking Changes
None - all changes are backward compatible.

### Deprecations
None

### Known Issues
- MeteoAlarm XML feed URL may vary by region
- Some NWS endpoints may be slow or unavailable during maintenance
- Chat mode requires terminal with Rich library support

### Migration Guide
No migration needed. All existing commands work as before.

To use new features:
1. Start chat mode: `wx chat`
2. Use comprehensive NWS data automatically via chat or `--trust-tools` flag
3. Enable privacy mode if needed: `export PRIVACY_MODE=0`

### Contributors
- Enhanced by Claude AI Assistant
- Original wx-cli by Exvin2

---

## Previous Versions

### [0.1.0] - Initial Release
- Basic CLI with forecast, risk, alerts, and explain commands
- OpenRouter integration with Gemini fallback
- Open-Meteo API for weather data
- NWS CAP API for US alerts
- Privacy mode and offline support
