"""Weather data visualizations for terminal."""

from __future__ import annotations

from typing import Any

from rich.progress import BarColumn, Progress, TaskID, TextColumn


def create_precipitation_bar(probability: float, width: int = 20) -> str:
    """Create an ASCII progress bar for precipitation probability.

    Args:
        probability: Percentage (0-100)
        width: Bar width in characters

    Returns:
        Formatted bar string
    """
    if probability < 0 or probability > 100:
        probability = max(0, min(100, probability))

    filled = int((probability / 100) * width)
    empty = width - filled

    # Color coding
    if probability >= 70:
        color = "red"
    elif probability >= 40:
        color = "yellow"
    else:
        color = "green"

    bar = "[" + ("=" * filled) + (" " * empty) + "]"
    return f"[{color}]{bar}[/{color}] {probability:.0f}%"


def create_temperature_trend(temps: list[float], labels: list[str], width: int = 40) -> str:
    """Create ASCII temperature trend chart.

    Args:
        temps: List of temperatures
        labels: List of time labels
        width: Chart width

    Returns:
        Multi-line ASCII chart
    """
    if not temps or len(temps) != len(labels):
        return "No data available"

    min_temp = min(temps)
    max_temp = max(temps)
    temp_range = max_temp - min_temp

    if temp_range == 0:
        temp_range = 1

    # Normalize to chart height
    height = 10
    lines = []

    # Draw chart
    for i in range(height, -1, -1):
        line_parts = []
        threshold = min_temp + (temp_range * i / height)

        for temp in temps:
            if temp >= threshold:
                line_parts.append("*")
            else:
                line_parts.append(" ")

        # Add temperature scale
        temp_label = f"{threshold:5.1f}"
        lines.append(f"{temp_label} | {' '.join(line_parts)}")

    # Add time labels at bottom
    label_line = "      +" + ("-" * (len(temps) * 2 - 1))
    lines.append(label_line)

    # Add abbreviated labels
    if len(labels) <= 12:
        time_line = "        " + "  ".join(label[:3] for label in labels)
        lines.append(time_line)

    return "\n".join(lines)


def format_alert_severity(severity: str) -> str:
    """Format alert severity with color coding.

    Args:
        severity: Alert severity level

    Returns:
        Formatted severity string with color
    """
    severity_lower = severity.lower()

    severity_colors = {
        "extreme": "bold red",
        "severe": "red",
        "moderate": "yellow",
        "minor": "cyan",
        "unknown": "dim",
    }

    color = severity_colors.get(severity_lower, "white")
    return f"[{color}]{severity.upper()}[/{color}]"


def create_wind_direction_indicator(degrees: float) -> str:
    """Create arrow indicator for wind direction.

    Args:
        degrees: Wind direction in degrees (0-360)

    Returns:
        Arrow character indicating direction
    """
    if degrees < 0 or degrees > 360:
        return "?"

    # 16-point compass
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘", "↓"]
    index = int((degrees + 22.5) / 45) % 8

    return arrows[index]


def create_weather_symbol(condition: str) -> str:
    """Get weather symbol for condition.

    Args:
        condition: Weather condition description

    Returns:
        Weather symbol character or description
    """
    condition_lower = condition.lower()

    # Map conditions to symbols
    symbols = {
        "clear": "Clear",
        "sunny": "Sunny",
        "partly cloudy": "Partly Cloudy",
        "cloudy": "Cloudy",
        "overcast": "Overcast",
        "rain": "Rain",
        "drizzle": "Drizzle",
        "showers": "Showers",
        "thunderstorm": "Thunderstorm",
        "snow": "Snow",
        "sleet": "Sleet",
        "fog": "Fog",
        "mist": "Mist",
        "wind": "Windy",
    }

    for key, symbol in symbols.items():
        if key in condition_lower:
            return symbol

    return condition


def create_humidity_bar(humidity: float, width: int = 20) -> str:
    """Create bar for humidity percentage.

    Args:
        humidity: Humidity percentage (0-100)
        width: Bar width

    Returns:
        Formatted humidity bar
    """
    if humidity < 0 or humidity > 100:
        humidity = max(0, min(100, humidity))

    filled = int((humidity / 100) * width)
    empty = width - filled

    # Color based on comfort level
    if humidity < 30:
        color = "cyan"  # Dry
    elif humidity < 60:
        color = "green"  # Comfortable
    else:
        color = "yellow"  # Humid

    bar = "[" + ("=" * filled) + (" " * empty) + "]"
    return f"[{color}]{bar}[/{color}] {humidity:.0f}%"


def create_uv_index_indicator(uv_index: float) -> str:
    """Create color-coded UV index indicator.

    Args:
        uv_index: UV index value

    Returns:
        Formatted UV index with color
    """
    if uv_index < 3:
        color = "green"
        level = "Low"
    elif uv_index < 6:
        color = "yellow"
        level = "Moderate"
    elif uv_index < 8:
        color = "orange"  # Note: Rich doesn't have orange, will use yellow
        level = "High"
    elif uv_index < 11:
        color = "red"
        level = "Very High"
    else:
        color = "magenta"
        level = "Extreme"

    return f"[{color}]{uv_index:.1f} ({level})[/{color}]"


def format_forecast_table(periods: list[dict[str, Any]]) -> str:
    """Format forecast periods as a table.

    Args:
        periods: List of forecast period dictionaries

    Returns:
        Formatted table string
    """
    if not periods:
        return "No forecast data available"

    lines = []
    lines.append("Period          | Temp  | Wind      | Conditions")
    lines.append("----------------|-------|-----------|---------------------------")

    for period in periods[:7]:  # Show up to 7 periods
        name = period.get("name", "Unknown")[:15].ljust(15)
        temp = period.get("temperature", "?")
        temp_unit = period.get("temperatureUnit", "F")
        wind = period.get("windSpeed", "Unknown")[:9].ljust(9)
        forecast = period.get("shortForecast", "Unknown")[:25]

        lines.append(f"{name} | {temp}{temp_unit:>4} | {wind} | {forecast}")

    return "\n".join(lines)
