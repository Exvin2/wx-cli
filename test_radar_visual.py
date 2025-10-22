#!/usr/bin/env python3
"""Test radar visualization components."""

import io

from PIL import Image, ImageDraw
from rich.console import Console

from wx.radar import RadarRenderer


def create_test_radar_image() -> bytes:
    """Create a synthetic radar image for testing."""
    # Create a 400x400 image
    img = Image.new("RGB", (400, 400), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw some "radar" patterns
    # Blue background (no precipitation)
    draw.rectangle([0, 0, 400, 400], fill=(0, 0, 50))

    # Green area (light rain)
    draw.ellipse([50, 50, 150, 150], fill=(0, 200, 0))

    # Yellow area (moderate rain)
    draw.ellipse([200, 100, 280, 180], fill=(255, 255, 0))

    # Orange area (heavy rain)
    draw.ellipse([100, 250, 170, 320], fill=(255, 150, 0))

    # Red area (very heavy rain/storm)
    draw.ellipse([280, 280, 350, 350], fill=(255, 0, 0))

    # Magenta area (extreme)
    draw.ellipse([150, 150, 200, 200], fill=(255, 0, 255))

    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_unicode_radar_rendering():
    """Test Unicode block radar rendering."""
    console = Console()
    renderer = RadarRenderer()

    console.print("\n" + "=" * 80)
    console.print("RADAR VISUALIZATION TEST - Unicode Blocks")
    console.print("=" * 80 + "\n")

    # Create test image
    image_data = create_test_radar_image()

    # Render with different sizes
    console.print("40x20 render:")
    console.print()
    radar_output = renderer.render_unicode_radar(image_data, width=40, height=20)
    console.print(radar_output)
    console.print()

    console.print("60x30 render:")
    console.print()
    radar_output = renderer.render_unicode_radar(image_data, width=60, height=30)
    console.print(radar_output)
    console.print()

    console.print("Legend:")
    console.print("  Black/Blue: No precipitation")
    console.print("  Cyan: Light precipitation")
    console.print("  Green: Light rain")
    console.print("  Yellow: Moderate rain")
    console.print("  Red: Heavy rain")
    console.print("  Magenta: Extreme precipitation/storm")
    console.print()


def test_terminal_detection():
    """Test terminal graphics capability detection."""
    console = Console()
    renderer = RadarRenderer()

    console.print("\n" + "=" * 80)
    console.print("TERMINAL GRAPHICS DETECTION TEST")
    console.print("=" * 80 + "\n")

    graphics_mode = renderer.detect_terminal_graphics()

    console.print(f"Detected graphics mode: [bold cyan]{graphics_mode}[/bold cyan]")
    console.print()

    if graphics_mode == "unicode":
        console.print("Your terminal supports: [green]Unicode block characters[/green]")
        console.print("Radar will be displayed using colored text blocks")
    elif graphics_mode == "kitty":
        console.print("Your terminal supports: [green]Kitty graphics protocol[/green]")
        console.print("Radar will be displayed as high-quality images")
    elif graphics_mode == "sixel":
        console.print("Your terminal supports: [green]Sixel graphics[/green]")
        console.print("Radar will be displayed as sixel graphics")
    elif graphics_mode == "iterm2":
        console.print("Your terminal supports: [green]iTerm2 inline images[/green]")
        console.print("Radar will be displayed as inline images")
    else:
        console.print("No advanced graphics detected")
        console.print("Radar will use fallback display method")

    console.print()


def test_radar_stations():
    """Test radar station database."""
    from wx.radar import RadarFetcher

    console = Console()
    fetcher = RadarFetcher()

    console.print("\n" + "=" * 80)
    console.print("RADAR STATIONS DATABASE TEST")
    console.print("=" * 80 + "\n")

    console.print(f"Total radar stations available: [bold cyan]{len(fetcher.RADAR_STATIONS)}[/bold cyan]")
    console.print()

    # Test finding nearest station
    test_locations = [
        (40.7128, -74.0060, "New York, NY"),
        (41.8781, -87.6298, "Chicago, IL"),
        (34.0522, -118.2437, "Los Angeles, CA"),
        (39.7392, -104.9903, "Denver, CO"),
        (29.7604, -95.3698, "Houston, TX"),
    ]

    console.print("Nearest station finder:")
    for lat, lon, city in test_locations:
        station = fetcher.find_nearest_station(lat, lon)
        station_name = fetcher.RADAR_STATIONS.get(station, "Unknown")
        console.print(f"  {city}: {station} - {station_name}")

    console.print()

    # List some major stations
    console.print("Sample of major radar stations:")
    major = ["KOKX", "KDMX", "KFTG", "KHGX", "KLAX", "KSEA", "KMIA", "KORD"]
    for station_id in major:
        if station_id in fetcher.RADAR_STATIONS:
            console.print(f"  {station_id}: {fetcher.RADAR_STATIONS[station_id]}")

    console.print()


def run_all_tests():
    """Run all radar visualization tests."""
    console = Console()

    console.print("\n")
    console.print("=" * 80, style="bold bright_blue")
    console.print("RADAR VISUALIZATION TEST SUITE", style="bold bright_blue")
    console.print("=" * 80, style="bold bright_blue")
    console.print()

    test_terminal_detection()
    test_radar_stations()
    test_unicode_radar_rendering()

    console.print("\n")
    console.print("=" * 80, style="bold bright_green")
    console.print("ALL RADAR TESTS COMPLETED", style="bold bright_green")
    console.print("=" * 80, style="bold bright_green")
    console.print()

    console.print("[bold]Notes:[/bold]")
    console.print("  • Radar fetching requires live network connection")
    console.print("  • Animation requires multiple frames from NWS")
    console.print("  • GUI mode requires tkinter for window display")
    console.print("  • Terminal graphics depend on your terminal emulator")
    console.print()


if __name__ == "__main__":
    run_all_tests()
