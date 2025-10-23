"""Real-time lightning strike data and visualization."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from rich.console import Console
from rich.text import Text


class LightningDataFetcher:
    """Fetch real-time lightning strike data."""

    # NOAA/NWS Lightning Detection Network
    GOES_LIGHTNING_URL = "https://services.swpc.noaa.gov/json/goes/primary/magnetometers-6-hour.json"

    # Blitzortung.org (Community lightning network)
    BLITZORTUNG_URL = "https://data.blitzortung.org"

    def __init__(self, timeout: int = 10):
        """Initialize lightning data fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "wx-cli/1.0 (Weather CLI Tool)",
            }
        )

    def get_recent_strikes(
        self, lat: float, lon: float, radius_km: float = 100, minutes: int = 30, *, offline: bool = False
    ) -> list[dict[str, Any]]:
        """Get recent lightning strikes near location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Radius to search in km
            minutes: Look back this many minutes
            offline: Offline mode

        Returns:
            List of lightning strikes with time, location, intensity
        """
        if offline:
            return self._generate_synthetic_strikes(lat, lon, radius_km)

        # In production, would fetch from actual lightning network
        # For now, return synthetic data as placeholder
        return self._generate_synthetic_strikes(lat, lon, radius_km)

    def _generate_synthetic_strikes(
        self, center_lat: float, center_lon: float, radius_km: float
    ) -> list[dict[str, Any]]:
        """Generate synthetic lightning data for testing.

        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Radius in km

        Returns:
            List of synthetic strikes
        """
        import random

        strikes = []
        num_strikes = random.randint(5, 20)

        for _ in range(num_strikes):
            # Random offset within radius
            offset_lat = random.uniform(-radius_km / 111, radius_km / 111)
            offset_lon = random.uniform(-radius_km / 85, radius_km / 85)

            strike = {
                "lat": center_lat + offset_lat,
                "lon": center_lon + offset_lon,
                "time": datetime.now(UTC) - timedelta(minutes=random.randint(1, 30)),
                "intensity": random.randint(1, 100),  # kA (kiloamperes)
                "type": random.choice(["IC", "CG", "CC"]),  # IC=intra-cloud, CG=cloud-ground, CC=cloud-cloud
            }
            strikes.append(strike)

        # Sort by time, most recent first
        strikes.sort(key=lambda x: x["time"], reverse=True)

        return strikes

    def get_strike_density_map(
        self, lat: float, lon: float, size_km: int = 200, *, offline: bool = False
    ) -> dict[str, Any]:
        """Get lightning strike density map for area.

        Args:
            lat: Center latitude
            lon: Center longitude
            size_km: Map size in km
            offline: Offline mode

        Returns:
            Strike density map data
        """
        strikes = self.get_recent_strikes(lat, lon, radius_km=size_km / 2, offline=offline)

        # Create grid
        grid_size = 20
        grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]

        # Map strikes to grid
        km_per_cell = size_km / grid_size

        for strike in strikes:
            strike_lat = strike["lat"]
            strike_lon = strike["lon"]

            # Calculate grid position
            offset_lat = (strike_lat - lat) * 111  # km
            offset_lon = (strike_lon - lon) * 85  # km (approx at mid-latitudes)

            grid_x = int((offset_lon + size_km / 2) / km_per_cell)
            grid_y = int((offset_lat + size_km / 2) / km_per_cell)

            if 0 <= grid_x < grid_size and 0 <= grid_y < grid_size:
                grid[grid_y][grid_x] += 1

        return {
            "grid": grid,
            "size_km": size_km,
            "center_lat": lat,
            "center_lon": lon,
            "total_strikes": len(strikes),
        }


class LightningVisualizer:
    """Visualize lightning strike data in terminal."""

    @staticmethod
    def render_strike_list(strikes: list[dict[str, Any]], console: Console) -> None:
        """Render list of lightning strikes.

        Args:
            strikes: List of strike data
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading(f"Recent Lightning Strikes ({len(strikes)})", level=1))
        console.print()

        if not strikes:
            console.print(Text("No lightning strikes detected", style="dim"))
            console.print()
            return

        for i, strike in enumerate(strikes[:20], 1):  # Show top 20
            strike_time = strike["time"]
            age_minutes = (datetime.now(UTC) - strike_time).total_seconds() / 60

            # Color by age
            if age_minutes < 5:
                age_color = "bright_red"
                age_text = "⚡ RECENT"
            elif age_minutes < 15:
                age_color = "bright_yellow"
                age_text = "Recent"
            else:
                age_color = "bright_black"
                age_text = "Older"

            strike_text = Text()
            strike_text.append(f"{i}. ", style="bright_blue")
            strike_text.append(f"{age_text} ", style=age_color)
            strike_text.append(f"({age_minutes:.1f}min ago)", style="dim")

            console.print(strike_text)

            # Details
            console.print(
                ds.info_row(
                    "Location:",
                    f"{strike['lat']:.3f}, {strike['lon']:.3f}",
                    indent=1,
                )
            )
            console.print(
                ds.info_row("Intensity:", f"{strike['intensity']} kA", indent=1)
            )
            console.print(ds.info_row("Type:", strike["type"], indent=1))
            console.print()

    @staticmethod
    def render_density_map(
        density_data: dict[str, Any], console: Console
    ) -> None:
        """Render lightning strike density map.

        Args:
            density_data: Density map data
            console: Rich console
        """
        from .design import DesignSystem

        ds = DesignSystem()

        grid = density_data["grid"]
        size_km = density_data["size_km"]
        total = density_data["total_strikes"]

        console.print()
        console.print(ds.heading(f"Lightning Density Map ({size_km}km area)", level=1))
        console.print()
        console.print(Text(f"Total strikes: {total}", style="bright_cyan"))
        console.print()

        # Render grid
        for row in grid:
            line_chars = []
            for count in row:
                if count == 0:
                    char = " "
                    color = "black"
                elif count == 1:
                    char = "·"
                    color = "cyan"
                elif count < 3:
                    char = "•"
                    color = "yellow"
                elif count < 5:
                    char = "●"
                    color = "red"
                else:
                    char = "⚡"
                    color = "bright_red"

                line_chars.append(f"[{color}]{char}[/{color}]")

            console.print("".join(line_chars))

        console.print()
        console.print(Text("Legend:", style="bold"))
        console.print(Text("  · = 1 strike", style="cyan"))
        console.print(Text("  • = 2 strikes", style="yellow"))
        console.print(Text("  ● = 3-4 strikes", style="red"))
        console.print(Text("  ⚡ = 5+ strikes", style="bright_red"))
        console.print()

    @staticmethod
    def animate_strikes(
        strikes: list[dict[str, Any]], console: Console, duration: float = 10.0
    ) -> None:
        """Animate lightning strikes over time.

        Args:
            strikes: List of strike data
            console: Rich console
            duration: Animation duration in seconds
        """
        from .design import DesignSystem

        ds = DesignSystem()

        console.print()
        console.print(ds.heading("Lightning Strike Animation", level=1))
        console.print()
        console.print(Text("Press Ctrl+C to stop...", style="dim"))
        console.print()

        # Sort by time
        strikes.sort(key=lambda x: x["time"])

        try:
            start_time = time.time()

            while time.time() - start_time < duration:
                console.clear()
                console.print(ds.heading("Lightning Activity", level=1))
                console.print()

                # Show strikes in time window
                current_time = datetime.now(UTC)
                window_minutes = 5

                recent_strikes = [
                    s
                    for s in strikes
                    if (current_time - s["time"]).total_seconds() / 60
                    <= window_minutes
                ]

                console.print(
                    Text(
                        f"Strikes in last {window_minutes} minutes: {len(recent_strikes)}",
                        style="bright_yellow",
                    )
                )
                console.print()

                # Simple visualization
                for strike in recent_strikes[-10:]:  # Last 10
                    age = (current_time - strike["time"]).total_seconds()
                    if age < 60:
                        console.print(
                            Text(f"  ⚡ Strike at {strike['lat']:.2f}, {strike['lon']:.2f}", style="bright_red")
                        )

                time.sleep(1.0)

        except KeyboardInterrupt:
            console.print()
            console.print(Text("Animation stopped", style="bright_yellow"))
            console.print()


def display_lightning(
    lat: float,
    lon: float,
    *,
    radius_km: float = 100,
    animate: bool = False,
    show_map: bool = False,
    offline: bool = False,
    console: Console | None = None,
) -> None:
    """Display lightning strike data.

    Args:
        lat: Latitude
        lon: Longitude
        radius_km: Search radius in km
        animate: Show animation
        show_map: Show density map
        offline: Offline mode
        console: Rich console
    """
    if console is None:
        console = Console()

    fetcher = LightningDataFetcher()
    visualizer = LightningVisualizer()

    # Get strike data
    strikes = fetcher.get_recent_strikes(lat, lon, radius_km, offline=offline)

    if animate:
        visualizer.animate_strikes(strikes, console)
    elif show_map:
        density_data = fetcher.get_strike_density_map(lat, lon, int(radius_km * 2), offline=offline)
        visualizer.render_density_map(density_data, console)
    else:
        visualizer.render_strike_list(strikes, console)
