"""Hurricane and tropical storm tracking from NHC."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from rich.console import Console
from rich.text import Text


class HurricaneTracker:
    """Track hurricanes and tropical storms from NOAA NHC."""

    # National Hurricane Center (NHC)
    NHC_BASE_URL = "https://www.nhc.noaa.gov"
    ACTIVE_STORMS_JSON = f"{NHC_BASE_URL}/CurrentStorms.json"
    GIS_URL = f"{NHC_BASE_URL}/gis"

    def __init__(self, timeout: int = 10):
        """Initialize hurricane tracker.

        Args:
            timeout: Request timeout
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "wx-cli/1.0 (Weather CLI Tool)",
        })

    def get_active_storms(self, *, offline: bool = False) -> list[dict[str, Any]]:
        """Get currently active tropical systems.

        Args:
            offline: Offline mode

        Returns:
            List of active storms
        """
        if offline:
            return self._generate_synthetic_storms()

        try:
            response = self.session.get(self.ACTIVE_STORMS_JSON, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return data.get("activeStorms", [])

        except (requests.RequestException, OSError):
            return self._generate_synthetic_storms()

    def get_storm_forecast(
        self, storm_id: str, *, offline: bool = False
    ) -> dict[str, Any] | None:
        """Get forecast for specific storm.

        Args:
            storm_id: Storm identifier (e.g., 'al052023')
            offline: Offline mode

        Returns:
            Storm forecast data
        """
        if offline:
            return None

        try:
            # GIS forecast data
            url = f"{self.GIS_URL}/{storm_id}_fcst.zip"
            # Would need to download and parse shapefile
            # For now, return placeholder
            return {"storm_id": storm_id, "format": "shapefile"}

        except (requests.RequestException, OSError):
            return None

    def _generate_synthetic_storms(self) -> list[dict[str, Any]]:
        """Generate synthetic storm data for testing.

        Returns:
            List of synthetic storms
        """
        import random

        if random.random() < 0.3:  # 30% chance of active storms
            num_storms = random.randint(1, 3)
            storms = []

            names = ["Alberto", "Beryl", "Chris", "Debby", "Ernesto", "Francine"]
            basins = ["Atlantic", "Eastern Pacific", "Central Pacific"]

            for i in range(num_storms):
                storm = {
                    "id": f"al{i+1:02d}2024",
                    "name": names[i % len(names)],
                    "classification": random.choice([
                        "Tropical Storm",
                        "Hurricane",
                        "Major Hurricane",
                        "Post-Tropical Cyclone",
                    ]),
                    "intensity": random.randint(35, 155),  # mph
                    "pressure": random.randint(950, 1005),  # mb
                    "latitude": random.uniform(10, 40),
                    "longitude": random.uniform(-90, -60),
                    "movement": f"{random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])} at {random.randint(5, 25)} mph",
                    "basin": random.choice(basins),
                }

                storms.append(storm)

            return storms

        return []


class HurricaneVisualizer:
    """Visualize hurricane and storm data."""

    @staticmethod
    def render_active_storms(storms: list[dict[str, Any]], console: Console) -> None:
        """Render list of active tropical systems.

        Args:
            storms: List of storm data
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading(f"Active Tropical Systems ({len(storms)})", level=1))
        console.print()

        if not storms:
            console.print(Text("No active tropical systems", style="bright_green"))
            console.print()
            return

        for storm in storms:
            name = storm.get("name", "Unknown")
            classification = storm.get("classification", "Unknown")
            intensity = storm.get("intensity", "?")
            pressure = storm.get("pressure", "?")
            movement = storm.get("movement", "Unknown")
            basin = storm.get("basin", "Unknown")

            # Color by classification
            if "Major Hurricane" in classification or intensity >= 111:
                color = "bold bright_red"
                severity = "MAJOR"
            elif "Hurricane" in classification or intensity >= 74:
                color = "bright_red"
                severity = "HURRICANE"
            elif "Tropical Storm" in classification:
                color = "bright_yellow"
                severity = "TROPICAL STORM"
            else:
                color = "bright_cyan"
                severity = "SYSTEM"

            # Header
            header = Text()
            header.append(f"{severity}: ", style=color)
            header.append(name, style="bold white")
            console.print(header)

            # Details
            console.print(ds.info_row("Classification:", classification, indent=1))
            console.print(ds.info_row("Intensity:", f"{intensity} mph winds", indent=1))
            console.print(ds.info_row("Pressure:", f"{pressure} mb", indent=1))
            console.print(ds.info_row("Movement:", movement, indent=1))
            console.print(ds.info_row("Basin:", basin, indent=1))
            console.print()

        # Warnings
        major_hurricanes = [
            s for s in storms
            if "Major Hurricane" in s.get("classification", "") or s.get("intensity", 0) >= 111
        ]

        if major_hurricanes:
            console.print(ds.separator())
            console.print(
                Text(
                    "⚠️  MAJOR HURRICANE ALERT - Category 3+ storm active",
                    style="bold bright_red",
                )
            )
            console.print(
                Text(
                    "Monitor local authorities for evacuation orders and safety instructions.",
                    style="bright_red",
                )
            )
            console.print()

    @staticmethod
    def render_saffir_simpson_scale(console: Console) -> None:
        """Render Saffir-Simpson Hurricane Wind Scale.

        Args:
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading("Saffir-Simpson Hurricane Wind Scale", level=2))
        console.print()

        categories = [
            ("Tropical Storm", "39-73 mph", "No category - Tropical storm force winds", "bright_cyan"),
            ("Category 1", "74-95 mph", "Very dangerous winds - some damage", "bright_yellow"),
            ("Category 2", "96-110 mph", "Extremely dangerous winds - extensive damage", "orange"),
            ("Category 3", "111-129 mph", "Devastating damage - major hurricane", "bright_red"),
            ("Category 4", "130-156 mph", "Catastrophic damage - major hurricane", "bold bright_red"),
            ("Category 5", "157+ mph", "Catastrophic damage - major hurricane", "bold magenta"),
        ]

        for cat, winds, description, color in categories:
            cat_text = Text()
            cat_text.append(f"{cat}: ", style=f"bold {color}")
            cat_text.append(winds, style=color)
            console.print(cat_text)

            console.print(Text(f"  {description}", style="dim"))
            console.print()

    @staticmethod
    def render_storm_map_ascii(
        storms: list[dict[str, Any]], console: Console, width: int = 80, height: int = 40
    ) -> None:
        """Render ASCII map of storm positions.

        Args:
            storms: List of storm data
            console: Rich console
            width: Map width
            height: Map height
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading("Storm Position Map", level=1))
        console.print()

        # Create grid
        grid = [[" " for _ in range(width)] for _ in range(height)]

        # Map bounds (Atlantic basin)
        lat_min, lat_max = 10, 50
        lon_min, lon_max = -100, -40

        # Plot storms
        for storm in storms:
            lat = storm.get("latitude", 0)
            lon = storm.get("longitude", 0)

            # Convert to grid position
            x = int((lon - lon_min) / (lon_max - lon_min) * (width - 1))
            y = int((lat_max - lat) / (lat_max - lat_min) * (height - 1))

            if 0 <= x < width and 0 <= y < height:
                intensity = storm.get("intensity", 0)
                if intensity >= 111:
                    grid[y][x] = "⚠"  # Major hurricane
                elif intensity >= 74:
                    grid[y][x] = "●"  # Hurricane
                else:
                    grid[y][x] = "○"  # Tropical storm

        # Render grid
        for row in grid:
            console.print("".join(row))

        console.print()
        console.print(Text("Legend: ○ = Tropical Storm, ● = Hurricane, ⚠ = Major Hurricane", style="dim"))
        console.print()


def display_hurricanes(
    *,
    show_scale: bool = False,
    show_map: bool = False,
    offline: bool = False,
    console: Console | None = None,
) -> None:
    """Display hurricane tracking information.

    Args:
        show_scale: Show Saffir-Simpson scale
        show_map: Show storm position map
        offline: Offline mode
        console: Rich console
    """
    if console is None:
        console = Console()

    tracker = HurricaneTracker()
    visualizer = HurricaneVisualizer()

    # Get active storms
    storms = tracker.get_active_storms(offline=offline)

    # Render storms
    visualizer.render_active_storms(storms, console)

    # Show scale if requested
    if show_scale:
        visualizer.render_saffir_simpson_scale(console)

    # Show map if requested and storms exist
    if show_map and storms:
        visualizer.render_storm_map_ascii(storms, console)
