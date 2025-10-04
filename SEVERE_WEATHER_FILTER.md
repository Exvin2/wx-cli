# Severe Weather Filter Feature

## Overview
Added `--severe` flag to filter worldview alerts for **severe weather only**: floods, tornadoes, and severe thunderstorms.

## Usage

### Default (all alerts)
```bash
wx
```

### Severe weather only
```bash
wx --severe
```

### With verbose output
```bash
wx --severe --verbose
```

### JSON output
```bash
wx --severe --json
```

## Filtered Alert Types

The `--severe` flag filters for these event types:
- **Tornadoes**: Tornado Warning, Tornado Watch, Tornado Emergency, TOR-, TOR PDS, TOR-E, Particularly Dangerous Situation
- **Floods**: Flood Warning, Flash Flood Warning, Flooding, Coastal Flood Warning
- **Severe Thunderstorms**: Severe Thunderstorm Warning, Severe TSTM

## Implementation Details

### 1. Configuration (`wx/config.py`)
Added `SEVERE_WEATHER_KEYWORDS` set with all severe weather terms:
```python
SEVERE_WEATHER_KEYWORDS = {
    "tornado", "tor-", "tor pds", "tor-e", "tornado warning",
    "tornado watch", "tornado emergency", "pds",
    "particularly dangerous situation", "flood", "flash flood",
    "flooding", "severe thunderstorm", "severe tstm", "tstm",
    "thunderstorm",
}
```

### 2. Fetchers (`wx/fetchers.py`)
- Added `severe_only` parameter to `fetch_us_alerts()` and `fetch_eu_alerts()`
- New function `_is_severe_weather()` checks event names against keywords
- Filters alerts at fetch time for efficiency

### 3. Orchestrator (`wx/orchestrator.py`)
- Updated `handle_worldview(severe_only=False)` to accept filter parameter
- Passes `severe_only` to alert fetchers
- Updates metadata to indicate filter status
- Offline mode provides appropriate synthetic severe weather alerts

### 4. Renderer (`wx/render.py`)
- Highlights severe weather alerts in **bold red**
- Changes title to "⚠️ SEVERE WEATHER ALERTS" when filtering
- Shows up to 5 alerts in severe mode (vs 3 in normal mode)
- Special message when no severe alerts: "✓ No severe weather alerts"

### 5. CLI (`wx/cli.py`)
- Added `--severe` flag to root command
- Flag description: "Filter for severe weather only (floods, tornadoes, severe thunderstorms)"

## Test Coverage

Added 2 new tests in `tests/test_worldview.py`:
- `test_severe_weather_filtering()`: Tests keyword matching for various alert types
- `test_worldview_severe_only()`: Tests end-to-end filtering with mocked alerts

All 12 worldview tests pass ✓

## Example Output

### Offline mode with `--severe`
```
US — Varied conditions coast to coast; warm South, cooler North
Europe — Mixed weather across continent; wet northwest, dry south

⚠️  SEVERE WEATHER ALERTS — Tornado Warning in US; Flash Flood Warning in US; 
Severe Thunderstorm Warning in US; Flood Warning in Europe
```

### Online mode with `--severe` (real data)
```
US — Temps 7–29°; precip chance up to 100%; winds to 32 m/s; 27 active alerts
Europe — Temps 6–26°; precip chance up to 100%; winds to 38 m/s

⚠️  SEVERE WEATHER ALERTS — Coastal Flood Advisory in US; Coastal Flood Warning 
in US; Coastal Flood Statement in US; Flood Warning in US; Flash Flood Warning 
in US
```

### Comparison

**Without `--severe` (shows all 339 alerts):**
```
Top risks — Small Craft Advisory in US; Gale Warning in US; Rip Current Statement in US
```

**With `--severe` (shows only 27 severe alerts):**
```
⚠️  SEVERE WEATHER ALERTS — Coastal Flood Advisory in US; Coastal Flood Warning in US; ...
```

## Files Modified
1. `wx/config.py` - Added SEVERE_WEATHER_KEYWORDS
2. `wx/fetchers.py` - Added severe_only parameter and _is_severe_weather()
3. `wx/orchestrator.py` - Updated handle_worldview() and _synthetic_worldview()
4. `wx/render.py` - Added severe weather highlighting and messages
5. `wx/cli.py` - Added --severe flag
6. `tests/test_worldview.py` - Added 2 new tests
