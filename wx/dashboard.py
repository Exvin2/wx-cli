"""Multi-location weather comparison dashboard."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text


class WeatherDashboard:
    """Compare weather across multiple locations."""

    @staticmethod
    def compare_locations(
        locations_data: list[dict[str, Any]], console: Console
    ) -> None:
        """Display side-by-side weather comparison.

        Args:
            locations_data: List of location weather data
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading(f"Weather Comparison ({len(locations_data)} locations)", level=1))
        console.print()

        if not locations_data:
            console.print(Text("No location data provided", style="dim"))
            return

        # Create comparison table
        table = Table(show_header=True, header_style="bold bright_cyan", border_style="bright_black")

        # Headers
        table.add_column("Metric", style="bright_black")
        for loc_data in locations_data:
            table.add_column(loc_data.get("name", "Unknown"), justify="center")

        # Temperature
        temps = [str(loc.get("temperature", "?")) + "°" for loc in locations_data]
        table.add_row("Temperature", *temps)

        # Feels Like
        feels = [str(loc.get("feels_like", "?")) + "°" for loc in locations_data]
        table.add_row("Feels Like", *feels)

        # Conditions
        conditions = [loc.get("conditions", "Unknown") for loc in locations_data]
        table.add_row("Conditions", *conditions)

        # Wind
        winds = [f"{loc.get('wind_speed', '?')} {loc.get('wind_direction', '')}" for loc in locations_data]
        table.add_row("Wind", *winds)

        # Humidity
        humidity = [str(loc.get("humidity", "?")) + "%" for loc in locations_data]
        table.add_row("Humidity", *humidity)

        # Precipitation
        precip = [str(loc.get("precip_chance", "?")) + "%" for loc in locations_data]
        table.add_row("Precip Chance", *precip)

        console.print(table)
        console.print()

        # Temperature differences
        temps_numeric = []
        for loc in locations_data:
            try:
                temps_numeric.append(float(loc.get("temperature", 0)))
            except (ValueError, TypeError):
                temps_numeric.append(0)

        if temps_numeric:
            temp_diff = max(temps_numeric) - min(temps_numeric)
            console.print(ds.info_row("Temperature Range:", f"{temp_diff:.1f}° difference"))
            console.print()

    @staticmethod
    def show_travel_comparison(
        home: dict[str, Any],
        destination: dict[str, Any],
        console: Console,
    ) -> None:
        """Compare home and travel destination weather.

        Args:
            home: Home location data
            destination: Destination location data
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading("Travel Weather Comparison", level=1))
        console.print()

        # Home
        console.print(Text(f"Home: {home.get('name', 'Unknown')}", style="bold bright_cyan"))
        console.print(ds.info_row("Temperature:", f"{home.get('temperature', '?')}°", indent=1))
        console.print(ds.info_row("Conditions:", home.get("conditions", "Unknown"), indent=1))
        console.print()

        # Destination
        console.print(Text(f"Destination: {destination.get('name', 'Unknown')}", style="bold bright_green"))
        console.print(ds.info_row("Temperature:", f"{destination.get('temperature', '?')}°", indent=1))
        console.print(ds.info_row("Conditions:", destination.get("conditions", "Unknown"), indent=1))
        console.print()

        # Differences
        console.print(ds.heading("What to Expect", level=2))

        try:
            home_temp = float(home.get("temperature", 0))
            dest_temp = float(destination.get("temperature", 0))
            temp_diff = dest_temp - home_temp

            if abs(temp_diff) < 5:
                console.print(Text("  Similar temperature to home", style="bright_green"))
            elif temp_diff > 0:
                console.print(Text(f"  {temp_diff:.1f}° warmer than home", style="bright_red"))
                if temp_diff > 20:
                    console.print(Text("  Pack light clothing and sunscreen", style="dim"))
            else:
                console.print(Text(f"  {abs(temp_diff):.1f}° cooler than home", style="bright_blue"))
                if abs(temp_diff) > 20:
                    console.print(Text("  Pack warm layers", style="dim"))

        except (ValueError, TypeError):
            console.print(Text("  Temperature comparison unavailable", style="dim"))

        console.print()

    @staticmethod
    def show_trending_locations(
        locations_data: list[dict[str, Any]], console: Console
    ) -> None:
        """Show locations sorted by various metrics.

        Args:
            locations_data: List of location data
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading("Location Rankings", level=1))
        console.print()

        # Warmest
        sorted_by_temp = sorted(
            locations_data,
            key=lambda x: float(x.get("temperature", 0)),
            reverse=True,
        )

        console.print(Text("Warmest:", style="bold bright_red"))
        for i, loc in enumerate(sorted_by_temp[:3], 1):
            console.print(
                ds.info_row(
                    f"{i}. {loc.get('name')}:",
                    f"{loc.get('temperature', '?')}°",
                    indent=1,
                )
            )
        console.print()

        # Coolest
        console.print(Text("Coolest:", style="bold bright_blue"))
        for i, loc in enumerate(reversed(sorted_by_temp[-3:]), 1):
            console.print(
                ds.info_row(
                    f"{i}. {loc.get('name')}:",
                    f"{loc.get('temperature', '?')}°",
                    indent=1,
                )
            )
        console.print()

        # Wettest
        sorted_by_precip = sorted(
            locations_data,
            key=lambda x: float(x.get("precip_chance", 0)),
            reverse=True,
        )

        console.print(Text("Highest Rain Chance:", style="bold cyan"))
        for i, loc in enumerate(sorted_by_precip[:3], 1):
            console.print(
                ds.info_row(
                    f"{i}. {loc.get('name')}:",
                    f"{loc.get('precip_chance', '?')}%",
                    indent=1,
                )
            )
        console.print()


def create_sample_location_data(location_name: str, *, offline: bool = False) -> dict[str, Any]:
    """Create sample location data for dashboard.

    Args:
        location_name: Name of location
        offline: Offline mode

    Returns:
        Sample weather data
    """
    import random

    return {
        "name": location_name,
        "temperature": random.randint(30, 90),
        "feels_like": random.randint(30, 95),
        "conditions": random.choice([
            "Clear", "Partly Cloudy", "Cloudy", "Rain", "Showers", "Thunderstorms", "Snow"
        ]),
        "wind_speed": random.randint(0, 30),
        "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
        "humidity": random.randint(20, 90),
        "precip_chance": random.randint(0, 100),
    }


def display_dashboard(
    locations: list[str],
    *,
    mode: str = "compare",  # compare, travel, trending
    offline: bool = False,
    console: Console | None = None,
) -> None:
    """Display multi-location weather dashboard.

    Args:
        locations: List of location names
        mode: Display mode
        offline: Offline mode
        console: Rich console
    """
    if console is None:
        console = Console()

    # Fetch data for each location
    locations_data = []
    for location in locations:
        # In production, fetch real data
        data = create_sample_location_data(location, offline=offline)
        locations_data.append(data)

    dashboard = WeatherDashboard()

    if mode == "travel" and len(locations_data) >= 2:
        dashboard.show_travel_comparison(locations_data[0], locations_data[1], console)
    elif mode == "trending":
        dashboard.show_trending_locations(locations_data, console)
    else:
        dashboard.compare_locations(locations_data, console)
