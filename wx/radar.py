"""Live weather radar display with animation support."""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

import requests


class RadarFetcher:
    """Fetch live radar data from NWS and other sources."""

    # NWS Ridge Radar stations
    RADAR_STATIONS = {
        "KABR": "Aberdeen, SD",
        "KABX": "Albuquerque, NM",
        "KAKQ": "Norfolk, VA",
        "KAMA": "Amarillo, TX",
        "KAMX": "Miami, FL",
        "KAPX": "Gaylord, MI",
        "KARX": "La Crosse, WI",
        "KATX": "Seattle, WA",
        "KBBX": "Beale AFB, CA",
        "KBGM": "Binghamton, NY",
        "KBHX": "Eureka, CA",
        "KBIS": "Bismarck, ND",
        "KBLX": "Billings, MT",
        "KBMX": "Birmingham, AL",
        "KBOX": "Boston, MA",
        "KBRO": "Brownsville, TX",
        "KBUF": "Buffalo, NY",
        "KBYX": "Key West, FL",
        "KCAE": "Columbia, SC",
        "KCBW": "Caribou, ME",
        "KCBX": "Boise, ID",
        "KCCX": "State College, PA",
        "KCLE": "Cleveland, OH",
        "KCLX": "Charleston, SC",
        "KCRP": "Corpus Christi, TX",
        "KCXX": "Burlington, VT",
        "KCYS": "Cheyenne, WY",
        "KDAX": "Sacramento, CA",
        "KDDC": "Dodge City, KS",
        "KDFX": "Laughlin AFB, TX",
        "KDGX": "Jackson, MS",
        "KDIX": "Philadelphia, PA",
        "KDLH": "Duluth, MN",
        "KDMX": "Des Moines, IA",
        "KDOX": "Dover AFB, DE",
        "KDTX": "Detroit, MI",
        "KDVN": "Davenport, IA",
        "KEAX": "Kansas City, MO",
        "KEMX": "Tucson, AZ",
        "KENX": "Albany, NY",
        "KEOX": "Fort Rucker, AL",
        "KEPZ": "El Paso, TX",
        "KESX": "Las Vegas, NV",
        "KEVX": "Eglin AFB, FL",
        "KEWX": "Austin, TX",
        "KEYX": "Edwards AFB, CA",
        "KFCX": "Roanoke, VA",
        "KFDR": "Frederick, OK",
        "KFFC": "Atlanta, GA",
        "KFSD": "Sioux Falls, SD",
        "KFSX": "Flagstaff, AZ",
        "KFTG": "Denver, CO",
        "KFWS": "Dallas, TX",
        "KGGW": "Glasgow, MT",
        "KGJX": "Grand Junction, CO",
        "KGLD": "Goodland, KS",
        "KGRB": "Green Bay, WI",
        "KGRK": "Fort Hood, TX",
        "KGRR": "Grand Rapids, MI",
        "KGSP": "Greer, SC",
        "KGWX": "Columbus, MS",
        "KGYX": "Portland, ME",
        "KHDX": "Holloman AFB, NM",
        "KHGX": "Houston, TX",
        "KHNX": "San Joaquin Valley, CA",
        "KHPX": "Fort Campbell, KY",
        "KHTX": "Huntsville, AL",
        "KICT": "Wichita, KS",
        "KICX": "Cedar City, UT",
        "KILN": "Cincinnati, OH",
        "KILX": "Lincoln, IL",
        "KIND": "Indianapolis, IN",
        "KINX": "Tulsa, OK",
        "KIWA": "Phoenix, AZ",
        "KIWX": "Fort Wayne, IN",
        "KJAX": "Jacksonville, FL",
        "KJGX": "Robins AFB, GA",
        "KJKL": "Jackson, KY",
        "KLBB": "Lubbock, TX",
        "KLCH": "Lake Charles, LA",
        "KLIX": "New Orleans, LA",
        "KLNX": "North Platte, NE",
        "KLOT": "Chicago, IL",
        "KLRX": "Elko, NV",
        "KLSX": "St. Louis, MO",
        "KLTX": "Wilmington, NC",
        "KLVX": "Louisville, KY",
        "KLWX": "Sterling, VA",
        "KLZK": "Little Rock, AR",
        "KMAF": "Midland, TX",
        "KMAX": "Medford, OR",
        "KMBX": "Minot AFB, ND",
        "KMHX": "Morehead City, NC",
        "KMKX": "Milwaukee, WI",
        "KMLB": "Melbourne, FL",
        "KMOB": "Mobile, AL",
        "KMPX": "Minneapolis, MN",
        "KMQT": "Marquette, MI",
        "KMRX": "Knoxville, TN",
        "KMSX": "Missoula, MT",
        "KMTX": "Salt Lake City, UT",
        "KMUX": "San Francisco, CA",
        "KMVX": "Grand Forks, ND",
        "KMXX": "Maxwell AFB, AL",
        "KNKX": "San Diego, CA",
        "KNQA": "Memphis, TN",
        "KOAX": "Omaha, NE",
        "KOHX": "Nashville, TN",
        "KOKX": "New York, NY",
        "KOTX": "Spokane, WA",
        "KPAH": "Paducah, KY",
        "KPBZ": "Pittsburgh, PA",
        "KPDT": "Pendleton, OR",
        "KPOE": "Fort Polk, LA",
        "KPUX": "Pueblo, CO",
        "KRAX": "Raleigh, NC",
        "KRGX": "Reno, NV",
        "KRIW": "Riverton, WY",
        "KRLX": "Charleston, WV",
        "KRTX": "Portland, OR",
        "KSFX": "Pocatello, ID",
        "KSGF": "Springfield, MO",
        "KSHV": "Shreveport, LA",
        "KSJT": "San Angelo, TX",
        "KSRX": "Fort Smith, AR",
        "KTBW": "Tampa, FL",
        "KTFX": "Great Falls, MT",
        "KTLH": "Tallahassee, FL",
        "KTLX": "Oklahoma City, OK",
        "KTWX": "Topeka, KS",
        "KTYX": "Fort Drum, NY",
        "KUDX": "Rapid City, SD",
        "KUEX": "Grand Island, NE",
        "KVNX": "Vance AFB, OK",
        "KVTX": "Los Angeles, CA",
        "KVWX": "Evansville, IN",
        "KYUX": "Yuma, AZ",
    }

    def __init__(self, timeout: int = 10):
        """Initialize radar fetcher.

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

    def find_nearest_station(self, lat: float, lon: float) -> str | None:
        """Find nearest radar station to coordinates.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Station ID or None
        """
        # Simplified - just return a default station for now
        # In production, calculate actual nearest station
        if lat > 40 and lon < -95:
            return "KDMX"  # Des Moines
        elif lat > 40:
            return "KOKX"  # New York
        elif lon < -100:
            return "KFTG"  # Denver
        elif lon > -90:
            return "KFFC"  # Atlanta
        else:
            return "KDFW"  # Dallas

    def get_radar_image(
        self, station: str, product: str = "N0R", *, offline: bool = False
    ) -> bytes | None:
        """Fetch radar image from NWS.

        Args:
            station: Radar station ID (e.g., KOKX)
            product: Radar product code (N0R=base reflectivity)
            offline: Offline mode

        Returns:
            Image bytes or None

        Radar Products:
            N0R: Base Reflectivity
            N0S: Storm Relative Velocity
            N0V: Base Velocity
            N0Z: Base Reflectivity (High Res)

        Raises:
            ValueError: If station ID is invalid
        """
        from .security import validate_radar_station, ValidationError

        # SECURITY: Validate station ID against whitelist before URL construction
        try:
            station_validated = validate_radar_station(station)
        except ValidationError as e:
            raise ValueError(str(e)) from e

        if offline:
            return None

        try:
            # Use validated station ID in URL construction
            url = f"https://radar.weather.gov/ridge/standard/{station_validated}_loop.gif"

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            return response.content

        except (requests.RequestException, OSError):
            return None

    def get_radar_frames(
        self, station: str, num_frames: int = 10, *, offline: bool = False
    ) -> list[bytes]:
        """Fetch multiple radar frames for animation.

        Args:
            station: Radar station ID
            num_frames: Number of frames to fetch
            offline: Offline mode

        Returns:
            List of image bytes
        """
        if offline:
            return []

        # For now, fetch the loop GIF which contains multiple frames
        # In production, we'd parse the GIF and extract individual frames
        image_data = self.get_radar_image(station, offline=offline)
        if image_data:
            return [image_data]  # Return as single frame for now

        return []

    def get_available_stations_near(self, lat: float, lon: float, count: int = 5) -> list[tuple[str, str]]:
        """Get list of nearby radar stations.

        Args:
            lat: Latitude
            lon: Longitude
            count: Number of stations to return

        Returns:
            List of (station_id, name) tuples
        """
        # Simplified - return some common stations
        # In production, calculate actual distances
        return [
            ("KDMX", "Des Moines, IA"),
            ("KOKX", "New York, NY"),
            ("KFTG", "Denver, CO"),
            ("KFFC", "Atlanta, GA"),
            ("KHGX", "Houston, TX"),
        ][:count]


class RadarRenderer:
    """Render radar images in the terminal using various methods."""

    @staticmethod
    def detect_terminal_graphics() -> str:
        """Detect terminal graphics capabilities.

        Returns:
            "sixel", "kitty", "iterm2", "unicode", or "none"
        """
        import os

        # Check for kitty
        if os.environ.get("TERM") == "xterm-kitty":
            return "kitty"

        # Check for iTerm2
        if os.environ.get("TERM_PROGRAM") == "iTerm.app":
            return "iterm2"

        # Check for sixel support
        if os.environ.get("TERM", "").find("sixel") != -1:
            return "sixel"

        # Default to unicode blocks
        return "unicode"

    @staticmethod
    def render_unicode_radar(image_data: bytes, width: int = 80, height: int = 40) -> str:
        """Render radar image as colored Unicode blocks.

        Args:
            image_data: Image bytes
            width: Output width in characters
            height: Output height in characters

        Returns:
            Colored Unicode block string
        """
        try:
            from PIL import Image

            # Load image
            img = Image.open(io.BytesIO(image_data))

            # Resize to terminal dimensions
            img = img.resize((width, height), Image.Resampling.LANCZOS)

            # Convert to RGB
            img = img.convert("RGB")

            # Build output with colored blocks
            lines = []
            for y in range(height):
                line_chars = []
                for x in range(width):
                    r, g, b = img.getpixel((x, y))

                    # Map intensity to block character
                    intensity = (r + g + b) // 3

                    # Choose block character based on intensity
                    if intensity < 32:
                        char = " "
                        color = "black"
                    elif intensity < 64:
                        char = "░"
                        color = "blue"
                    elif intensity < 96:
                        char = "▒"
                        color = "cyan"
                    elif intensity < 128:
                        char = "▓"
                        color = "green"
                    elif intensity < 160:
                        char = "▓"
                        color = "yellow"
                    elif intensity < 192:
                        char = "█"
                        color = "red"
                    else:
                        char = "█"
                        color = "magenta"

                    # Add colored character
                    line_chars.append(f"[{color}]{char}[/{color}]")

                lines.append("".join(line_chars))

            return "\n".join(lines)

        except (ImportError, OSError):
            return "Error: PIL not available for image rendering"

    @staticmethod
    def render_sixel(image_data: bytes) -> str:
        """Render radar image using sixel graphics.

        Args:
            image_data: Image bytes

        Returns:
            Sixel escape sequence
        """
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))

            # Convert to sixel (simplified - would need libsixel)
            return "[Sixel graphics not yet implemented]"

        except (ImportError, OSError):
            return "Error: Sixel rendering failed"

    @staticmethod
    def render_kitty(image_data: bytes) -> str:
        """Render radar image using Kitty graphics protocol.

        Args:
            image_data: Image bytes

        Returns:
            Kitty escape sequence
        """
        import base64

        # Kitty graphics protocol
        b64_data = base64.b64encode(image_data).decode("ascii")

        # Build kitty escape sequence
        chunks = [b64_data[i : i + 4096] for i in range(0, len(b64_data), 4096)]

        output = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                output.append(f"\x1b_Ga=T,f=100,m=1;{chunk}\x1b\\")
            elif i == len(chunks) - 1:
                output.append(f"\x1b_Gm=0;{chunk}\x1b\\")
            else:
                output.append(f"\x1b_Gm=1;{chunk}\x1b\\")

        return "".join(output)

    @staticmethod
    def open_gui_window(image_data: bytes, title: str = "Weather Radar") -> None:
        """Open GUI window to display radar image.

        Args:
            image_data: Image bytes
            title: Window title
        """
        try:
            from PIL import Image, ImageTk
            import tkinter as tk

            # Load image
            img = Image.open(io.BytesIO(image_data))

            # Create window
            root = tk.Tk()
            root.title(title)

            # Display image
            photo = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=photo)
            label.pack()

            # Run
            root.mainloop()

        except (ImportError, OSError) as e:
            print(f"Error opening GUI window: {e}")


def display_radar(
    station: str,
    *,
    animate: bool = False,
    frames: int | None = None,
    delay: float | None = None,
    gui: bool = False,
    offline: bool = False,
    console: Any = None,
    max_loops: int | None = None,
) -> None:
    """Display live weather radar.

    Args:
        station: Radar station ID
        animate: Enable animation loop
        frames: Number of frames for animation (default from constants)
        delay: Delay between frames in seconds (default from constants)
        gui: Force GUI window display
        offline: Offline mode
        console: Rich console for output
        max_loops: Maximum animation loops (default from constants, prevents infinite loop)
    """
    from .constants import (
        DEFAULT_RADAR_FRAMES,
        DEFAULT_RADAR_DELAY,
        MAX_RADAR_ANIMATION_LOOPS,
    )

    # Use constants as defaults
    if frames is None:
        frames = DEFAULT_RADAR_FRAMES
    if delay is None:
        delay = DEFAULT_RADAR_DELAY
    if max_loops is None:
        max_loops = MAX_RADAR_ANIMATION_LOOPS
    from rich.console import Console
    from rich.text import Text

    if console is None:
        console = Console()

    from .security import validate_radar_station, ValidationError

    # SECURITY: Validate station ID before processing
    try:
        station = validate_radar_station(station)
    except ValidationError as e:
        console.print(Text(f"Error: {e}", style="bright_red"))
        return

    fetcher = RadarFetcher()
    renderer = RadarRenderer()

    # Get station info (station is already uppercase from validation)
    station_name = fetcher.RADAR_STATIONS.get(station, "Unknown")

    console.print()
    console.print(Text(f"Weather Radar: {station.upper()} - {station_name}", style="bold bright_blue"))
    console.print()

    if offline:
        console.print(Text("Radar not available in offline mode", style="bright_yellow"))
        return

    # Fetch radar data
    console.print(Text("Fetching radar data...", style="dim"))

    if animate:
        # Fetch multiple frames
        frame_data = fetcher.get_radar_frames(station, num_frames=frames, offline=offline)

        if not frame_data:
            console.print(Text("Failed to fetch radar frames", style="bright_red"))
            return

        # Detect terminal capabilities
        graphics_mode = renderer.detect_terminal_graphics()

        if gui:
            # Open GUI window
            for frame in frame_data:
                renderer.open_gui_window(frame, f"Radar {station.upper()}")
        elif graphics_mode == "unicode":
            # Animate with Unicode blocks
            console.print(Text(f"Animating radar loop (max {max_loops} loops, Ctrl+C to stop)...", style="dim"))
            console.print()

            try:
                for loop_num in range(max_loops):
                    for i, frame in enumerate(frame_data):
                        # Clear screen
                        console.clear()

                        # Show progress
                        progress = Text(f"Loop {loop_num + 1}/{max_loops} | Frame {i + 1}/{len(frame_data)}", style="dim")
                        console.print(progress)

                        # Render frame
                        radar_image = renderer.render_unicode_radar(frame, width=120, height=50)
                        console.print(radar_image)

                        # Delay
                        time.sleep(delay)

                console.print()
                console.print(Text(f"Animation completed ({max_loops} loops)", style="bright_green"))

            except KeyboardInterrupt:
                console.print()
                console.print(Text("Animation stopped by user", style="bright_yellow"))

        else:
            console.print(Text(f"Using {graphics_mode} graphics", style="dim"))
            # Render with detected method
            for frame in frame_data:
                if graphics_mode == "kitty":
                    console.print(renderer.render_kitty(frame))
                elif graphics_mode == "sixel":
                    console.print(renderer.render_sixel(frame))

    else:
        # Single frame
        image_data = fetcher.get_radar_image(station, offline=offline)

        if not image_data:
            console.print(Text("Failed to fetch radar image", style="bright_red"))
            console.print(Text("Tip: Check station ID or try a different station", style="dim"))
            return

        if gui:
            # Open GUI window
            renderer.open_gui_window(image_data, f"Radar {station.upper()}")
        else:
            # Detect terminal capabilities
            graphics_mode = renderer.detect_terminal_graphics()

            console.print(Text(f"Rendering radar ({graphics_mode} mode)...", style="dim"))
            console.print()

            if graphics_mode == "unicode":
                radar_image = renderer.render_unicode_radar(image_data, width=120, height=50)
                console.print(radar_image)
            elif graphics_mode == "kitty":
                console.print(renderer.render_kitty(image_data))
            elif graphics_mode == "sixel":
                console.print(renderer.render_sixel(image_data))

    console.print()
    console.print(Text(f"Radar data from NWS RIDGE: {station.upper()}", style="dim"))
    console.print()
