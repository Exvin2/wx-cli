#!/usr/bin/env python3
"""Visual test suite for wx-cli UI components."""

from rich.console import Console
from rich.text import Text

from wx.design import DesignSystem
from wx.visualizations import (
    create_humidity_bar,
    create_precipitation_bar,
    create_temperature_trend,
    create_uv_index_indicator,
    create_wind_direction_indicator,
    format_alert_severity,
    format_forecast_table_modern,
)


def test_design_system():
    """Test all design system components."""
    console = Console()
    ds = DesignSystem()

    console.print("\n" + "=" * 80)
    console.print("DESIGN SYSTEM COMPONENTS TEST")
    console.print("=" * 80 + "\n")

    # Test headings
    console.print("1. HEADINGS")
    console.print(ds.heading("Level 1 Heading", level=1))
    console.print(ds.heading("Level 2 Heading", level=2))
    console.print(ds.heading("Level 3 Heading", level=3))
    console.print()

    # Test text styles
    console.print("2. TEXT STYLES")
    console.print(ds.label("Label:"))
    console.print(ds.value("Value content"))
    console.print(ds.subtext("This is dimmed subtext"))
    console.print()

    # Test badges
    console.print("3. BADGES")
    console.print(ds.badge("DEFAULT", "default"))
    console.print(ds.badge("SUCCESS", "success"))
    console.print(ds.badge("WARNING", "warning"))
    console.print(ds.badge("DANGER", "danger"))
    console.print(ds.badge("INFO", "info"))
    console.print()

    # Test progress indicators
    console.print("4. PROGRESS INDICATORS")
    console.print(ds.progress_indicator(25.0))
    console.print(ds.progress_indicator(50.0))
    console.print(ds.progress_indicator(75.0))
    console.print(ds.progress_indicator(95.0))
    console.print()

    # Test bullet points
    console.print("5. BULLET POINTS")
    console.print(ds.bullet_point("First item"))
    console.print(ds.bullet_point("Second item", color="bright_green"))
    console.print(ds.bullet_point("Third item", color="bright_yellow"))
    console.print()

    # Test info rows
    console.print("6. INFO ROWS")
    console.print(ds.info_row("Temperature:", "72°F"))
    console.print(ds.info_row("Humidity:", "45%", indent=1))
    console.print(ds.info_row("Wind:", "10 mph NW", indent=2))
    console.print()

    # Test metrics
    console.print("7. METRICS")
    console.print(ds.metric("42", "Temperature", "°F"))
    console.print(ds.metric("65", "Humidity", "%"))
    console.print()

    # Test separators
    console.print("8. SEPARATORS")
    console.print(ds.separator(40))
    console.print()

    # Test section title
    console.print("9. SECTION TITLES")
    console.print(ds.section_title("Weather Summary"))
    console.print()

    # Test alert badges
    console.print("10. ALERT SEVERITY BADGES")
    console.print(ds.alert_badge("extreme"))
    console.print(ds.alert_badge("severe"))
    console.print(ds.alert_badge("moderate"))
    console.print(ds.alert_badge("minor"))
    console.print()

    # Test card
    console.print("11. CLEAN CARD")
    card_content = [
        ("Location:", "Denver, CO"),
        ("Temperature:", "72°F"),
        ("Conditions:", "Partly Cloudy"),
        ("Wind:", "10 mph NW"),
    ]
    console.print(ds.card("Current Weather", card_content, subtitle="Updated 2 minutes ago"))
    console.print()


def test_precipitation_bars():
    """Test precipitation visualization bars."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("PRECIPITATION BARS TEST")
    console.print("=" * 80 + "\n")

    console.print("Low probability (20%):")
    console.print(create_precipitation_bar(20))
    console.print()

    console.print("Medium probability (50%):")
    console.print(create_precipitation_bar(50))
    console.print()

    console.print("High probability (80%):")
    console.print(create_precipitation_bar(80))
    console.print()

    console.print("Very high probability (95%):")
    console.print(create_precipitation_bar(95))
    console.print()


def test_humidity_bars():
    """Test humidity visualization bars."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("HUMIDITY BARS TEST")
    console.print("=" * 80 + "\n")

    console.print("Dry (25%):")
    console.print(create_humidity_bar(25))
    console.print()

    console.print("Comfortable (50%):")
    console.print(create_humidity_bar(50))
    console.print()

    console.print("Humid (75%):")
    console.print(create_humidity_bar(75))
    console.print()

    console.print("Very humid (90%):")
    console.print(create_humidity_bar(90))
    console.print()


def test_temperature_trends():
    """Test temperature trend charts."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("TEMPERATURE TREND CHART TEST")
    console.print("=" * 80 + "\n")

    temps = [65, 68, 72, 75, 78, 76, 70, 65]
    labels = ["6AM", "9AM", "12PM", "3PM", "6PM", "9PM", "12AM", "3AM"]

    console.print("Daily Temperature Trend:")
    console.print(create_temperature_trend(temps, labels))
    console.print()


def test_wind_indicators():
    """Test wind direction indicators."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("WIND DIRECTION INDICATORS TEST")
    console.print("=" * 80 + "\n")

    directions = [
        (0, "North"),
        (45, "Northeast"),
        (90, "East"),
        (135, "Southeast"),
        (180, "South"),
        (225, "Southwest"),
        (270, "West"),
        (315, "Northwest"),
    ]

    for degrees, name in directions:
        arrow = create_wind_direction_indicator(degrees)
        console.print(f"{arrow} {degrees}° ({name})")
    console.print()


def test_uv_index():
    """Test UV index indicators."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("UV INDEX INDICATORS TEST")
    console.print("=" * 80 + "\n")

    console.print("Low: " + create_uv_index_indicator(2.0))
    console.print("Moderate: " + create_uv_index_indicator(5.0))
    console.print("High: " + create_uv_index_indicator(7.0))
    console.print("Very High: " + create_uv_index_indicator(9.0))
    console.print("Extreme: " + create_uv_index_indicator(12.0))
    console.print()


def test_alert_severity():
    """Test alert severity formatting."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("ALERT SEVERITY FORMATTING TEST")
    console.print("=" * 80 + "\n")

    console.print("Extreme: " + format_alert_severity("extreme"))
    console.print("Severe: " + format_alert_severity("severe"))
    console.print("Moderate: " + format_alert_severity("moderate"))
    console.print("Minor: " + format_alert_severity("minor"))
    console.print("Unknown: " + format_alert_severity("unknown"))
    console.print()


def test_forecast_table_modern():
    """Test modern forecast table display."""
    console = Console()

    console.print("\n" + "=" * 80)
    console.print("MODERN FORECAST TABLE TEST")
    console.print("=" * 80 + "\n")

    # Sample forecast data
    periods = [
        {
            "name": "Today",
            "temperature": 75,
            "temperatureUnit": "F",
            "windSpeed": "10 mph",
            "windDirection": "NW",
            "shortForecast": "Partly Cloudy",
            "detailedForecast": "Partly cloudy skies throughout the day.",
        },
        {
            "name": "Tonight",
            "temperature": 55,
            "temperatureUnit": "F",
            "windSpeed": "5 mph",
            "windDirection": "N",
            "shortForecast": "Mostly Clear",
            "detailedForecast": "Clear skies with light winds.",
        },
        {
            "name": "Tomorrow",
            "temperature": 78,
            "temperatureUnit": "F",
            "windSpeed": "12 mph",
            "windDirection": "SW",
            "shortForecast": "Chance Rain Showers",
            "detailedForecast": "A chance of rain showers in the afternoon.",
        },
        {
            "name": "Tomorrow Night",
            "temperature": 58,
            "temperatureUnit": "F",
            "windSpeed": "8 mph",
            "windDirection": "W",
            "shortForecast": "Thunderstorms",
            "detailedForecast": "Thunderstorms likely with heavy rainfall.",
        },
    ]

    format_forecast_table_modern(periods, console)
    console.print()


def test_worldview_display():
    """Test worldview/overview display."""
    console = Console()
    ds = DesignSystem()

    console.print("\n" + "=" * 80)
    console.print("WORLDVIEW DISPLAY TEST")
    console.print("=" * 80 + "\n")

    console.print(ds.heading("Weather Overview", level=1))
    console.print()

    # Regional summaries
    regions = [
        ("US", "Varied conditions coast to coast; warm South, cooler North"),
        ("Europe", "Mixed weather across continent; wet northwest, dry south"),
        ("Asia", "Monsoon season active in Southeast; dry conditions in Central regions"),
    ]

    for region, summary in regions:
        region_text = Text()
        region_text.append(f"{region}", style="bold bright_cyan")
        region_text.append(f"  {summary}", style="white")
        console.print(region_text)

    console.print()
    console.print(ds.heading("Active Alerts", level=2))

    # Sample alerts
    alerts = [
        ("Heat Advisory", 3, "US", False),
        ("Tornado Warning", 2, "US", True),
        ("Flash Flood Warning", 1, "Europe", True),
        ("Wind Warning", 2, "Asia", False),
    ]

    for event, count, region_name, is_severe in alerts:
        alert_line = Text()
        alert_line.append("  • ", style="bright_blue")
        if is_severe:
            alert_line.append(event, style="bold bright_red")
        else:
            alert_line.append(event, style="bright_yellow")
        alert_line.append(f" ({count})", style="bright_black")
        alert_line.append(f" in {region_name}", style="white")
        console.print(alert_line)

    console.print()


def test_chat_interface_elements():
    """Test chat interface visual elements."""
    console = Console()
    ds = DesignSystem()

    console.print("\n" + "=" * 80)
    console.print("CHAT INTERFACE ELEMENTS TEST")
    console.print("=" * 80 + "\n")

    # Welcome header
    console.print(ds.heading("wx AI Weather Bot", level=1))
    console.print()

    console.print(Text("I can help you with:", style="white"))
    console.print(ds.bullet_point("Real-time weather conditions from NWS"))
    console.print(ds.bullet_point("Weather forecasts for any location"))
    console.print(ds.bullet_point("Severe weather alerts"))
    console.print()

    console.print(ds.heading("Commands", level=2))
    console.print(ds.info_row("/help", "Show available commands", indent=1))
    console.print(ds.info_row("/widget", "Show current weather", indent=1))
    console.print(ds.info_row("/quit", "Exit chat", indent=1))
    console.print()

    console.print(ds.separator())
    console.print()

    # Weather widget example
    console.print(ds.heading("Current Weather - Denver, CO", level=1))
    console.print()

    temp_text = Text()
    temp_text.append("  ", style="")
    temp_text.append("72°F", style="bold bright_blue")
    temp_text.append("  feels like 70°F", style="bright_black")
    console.print(temp_text)

    console.print(ds.info_row("Wind:", "10 mph NW", indent=1))
    console.print(ds.info_row("Visibility:", "10 km", indent=1))
    console.print(ds.info_row("Ceiling:", "3000 m", indent=1))
    console.print()


def run_all_tests():
    """Run all visual tests."""
    console = Console()

    console.print("\n")
    console.print("=" * 80, style="bold bright_blue")
    console.print("WX-CLI VISUAL COMPONENTS TEST SUITE", style="bold bright_blue")
    console.print("=" * 80, style="bold bright_blue")
    console.print()

    test_design_system()
    test_precipitation_bars()
    test_humidity_bars()
    test_temperature_trends()
    test_wind_indicators()
    test_uv_index()
    test_alert_severity()
    test_forecast_table_modern()
    test_worldview_display()
    test_chat_interface_elements()

    console.print("\n")
    console.print("=" * 80, style="bold bright_green")
    console.print("ALL VISUAL TESTS COMPLETED", style="bold bright_green")
    console.print("=" * 80, style="bold bright_green")
    console.print()


if __name__ == "__main__":
    run_all_tests()
