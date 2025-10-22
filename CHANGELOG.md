# Changelog

## [Unreleased] - Enhanced Features (4-7)

### New Data Sources Added

#### NOAA Buoy Data Support
- `get_nearby_buoys()` - Find NOAA buoys near a location
- `get_buoy_observations()` - Latest observations from specific buoys
- `get_marine_forecast()` - Marine forecasts for coastal areas
- Wave height, period, direction data
- Water temperature and pressure readings

#### Aviation Weather (METAR/TAF)
- `get_metar()` - Current aviation weather observations
- `get_taf()` - Terminal Aerodrome Forecasts
- `find_nearest_airport()` - Locate nearest airport for aviation data
- Flight category, visibility, cloud cover
- Wind data for flight planning

### Chat Bot Improvements

#### Session Persistence
- Conversations now automatically save and resume
- `session.save_to_file()` - Save session to disk
- `session.load_from_file()` - Resume previous session
- Secure file storage with 0600 permissions
- Works with privacy mode settings

#### New Chat Commands
- `/widget` - Show current weather widget for your location
- `/favorites` - List saved favorite locations
- `/save` - Manually save current conversation
- Session persistence across restarts

#### Weather Widgets
- Real-time conditions display in chat
- Temperature, wind, visibility, ceiling
- Updates when location context changes

### Location Management

#### Favorites System
- `FavoritesManager` - Manage saved locations
- Add/remove/list favorite locations
- Store coordinates, timezone, notes
- Secure storage with atomic writes
- Quick access to frequently checked locations

### Extended Forecasts

#### New `extended` Command
- Multi-day forecasts (up to 14 days)
- NWS gridded forecast data
- Formatted forecast tables
- `wx extended "Denver" --days 7`
- Shows day/night periods with conditions

### Visualizations

#### Weather Data Visualization Tools
- `create_precipitation_bar()` - Progress bars for precip probability
- `create_temperature_trend()` - ASCII temperature charts
- `create_humidity_bar()` - Humidity visualization
- `create_wind_direction_indicator()` - Arrow indicators for wind
- `create_uv_index_indicator()` - Color-coded UV index
- `format_forecast_table()` - Multi-day forecast tables

#### Color-Coded Alert Severity
- `format_alert_severity()` - Color codes for alert levels
- Extreme: Bold red
- Severe: Red
- Moderate: Yellow
- Minor: Cyan
- Applied to worldview alert displays

### Features Summary

**New Modules Added:**
- `wx/favorites.py` - Location favorites management
- `wx/marine.py` - NOAA buoy and marine data
- `wx/aviation.py` - METAR/TAF aviation weather
- `wx/visualizations.py` - Terminal visualizations

**New Commands:**
- `wx extended <place>` - Multi-day forecasts

**Chat Enhancements:**
- Session persistence and resume
- Weather widgets
- Favorites integration
- Auto-save on exit

**Data Sources:**
- NOAA buoys
- Aviation weather (METAR/TAF)
- Marine forecasts
- Extended NWS gridded forecasts

### Technical Improvements
- Atomic file writes for all saved data
- Secure permissions (0600) on all cache files
- Session management with timestamps
- Enhanced error handling for new data sources

---

## [Previous] - NWS AI Bot Enhancement

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
