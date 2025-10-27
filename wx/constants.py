"""Centralized constants for wx-cli.

This module contains all magic numbers, configuration values, and
constants used throughout the codebase to improve maintainability.
"""

# Version
__version__ = "1.0.0"

# Network Configuration
DEFAULT_NETWORK_TIMEOUT = 10  # seconds
RADAR_TIMEOUT = 15  # seconds (radar images may be larger)
AVIATION_TIMEOUT = 10  # seconds
MARINE_TIMEOUT = 10  # seconds
AQI_TIMEOUT = 10  # seconds
HURRICANE_TIMEOUT = 10  # seconds
INTERNATIONAL_TIMEOUT = 10  # seconds

# Rate Limiting
DEFAULT_RATE_LIMIT = 60  # requests per minute
BURST_RATE_LIMIT = 10  # requests in 10 seconds

# Response Size Limits
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JSON_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_SIZE = 15 * 1024 * 1024  # 15MB for radar images

# Input Validation
MAX_LOCATION_LENGTH = 100  # characters
MAX_RULE_NAME_LENGTH = 50  # characters
MAX_CONDITION_LENGTH = 100  # characters
MAX_NOTIFICATION_LOCATION_LENGTH = 100  # characters

# Radar Configuration
DEFAULT_RADAR_FRAMES = 10  # animation frames
DEFAULT_RADAR_DELAY = 0.5  # seconds between frames
MAX_RADAR_FRAMES = 30  # maximum frames to prevent abuse
MAX_RADAR_ANIMATION_LOOPS = 10  # prevent infinite loops

# Forecast Configuration
PERIODS_PER_DAY = 2  # day and night periods
DEFAULT_FORECAST_DAYS = 7  # default extended forecast length
MAX_FORECAST_DAYS = 14  # maximum forecast days

# Air Quality Configuration
DEFAULT_AQI_SEARCH_RADIUS_MILES = 25
DEFAULT_AQI_SEARCH_RADIUS_KM = 40

# Hurricane Configuration
SYNTHETIC_STORM_PROBABILITY = 0.3  # 30% chance in offline mode
MIN_SYNTHETIC_STORMS = 1
MAX_SYNTHETIC_STORMS = 3

# User Agent
USER_AGENT = f"wx-cli/{__version__} (+https://github.com/Exvin2/wx-cli)"

# File Permissions
SECURE_FILE_MODE = 0o600  # owner read/write only
SECURE_DIR_MODE = 0o700  # owner read/write/execute only

# Logging
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_LEVEL = "INFO"
DEBUG_LOG_LEVEL = "DEBUG"

# API Key Validation
MIN_API_KEY_LENGTH = 20
PLACEHOLDER_PATTERNS = [
    "your_api_key_here",
    "your_key_here",
    "placeholder",
    "example_key",
    "test_key",
    "api_key_here",
]

# Temperature and Weather
TEMP_PRECISION = 1  # decimal places
COORD_PRECISION = 4  # decimal places for lat/lon

# Cache Configuration
CACHE_DIR_NAME = "wx"
CONFIG_DIR_NAME = "wx"

# Error Messages
ERROR_OFFLINE_MODE = "Feature not available in offline mode"
ERROR_INVALID_LOCATION = "Invalid location format"
ERROR_NETWORK_FAILURE = "Network request failed"
ERROR_API_KEY_MISSING = "API key required but not configured"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded, please wait"

# Success Messages
SUCCESS_SAVED = "Successfully saved"
SUCCESS_LOADED = "Successfully loaded"
SUCCESS_UPDATED = "Successfully updated"

# Validation Patterns (moved from security.py for reference)
RADAR_STATION_PATTERN = r'^[KPTIC][A-Z]{3}$'
ICAO_STATION_PATTERN = r'^[A-Z]{4}$'
BUOY_ID_PATTERN = r'^[A-Z0-9]{5}$'
LOCATION_PATTERN = r'^[a-zA-Z0-9\s\-,.\'()]+$'
CONDITION_PATTERN = r'^([a-z_][a-z0-9_]*)\s*([<>=!]+)\s*(-?\d+(?:\.\d+)?)$'

# Allowed Operators for Notification Conditions
ALLOWED_OPERATORS = {'<', '<=', '>', '>=', '==', '!='}

# Allowed Variables for Notification Conditions
ALLOWED_WEATHER_VARIABLES = {
    'temp', 'temperature',
    'wind', 'wind_speed', 'windspeed',
    'humidity',
    'precip', 'precipitation',
    'pressure',
    'visibility',
    'dewpoint', 'dew_point',
    'heat_index', 'heatindex',
    'wind_chill', 'windchill',
    'aqi', 'air_quality',
    'uv', 'uv_index',
}

# Coordinate Bounds
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

# HTTP Configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # exponential backoff: 2s, 4s, 8s
INITIAL_RETRY_DELAY = 2  # seconds

# Connection Pool Configuration
CONNECTION_POOL_SIZE = 10
CONNECTION_POOL_MAXSIZE = 20

# Chunk size for streaming responses
STREAM_CHUNK_SIZE = 8192  # 8KB chunks
