"""Typer CLI entry-point for wx."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

import typer
from rich.console import Console
from rich.text import Text

from .chat import start_chat_session
from .config import PersonaLiteral, StyleLiteral, load_settings
from .design import DesignSystem
from .orchestrator import Orchestrator
from .render import render_result, render_worldview

COMMAND_NAMES = {
    "forecast", "risk", "explain", "alerts", "chat", "extended", "radar",
    "international", "lightning", "aqi", "hurricanes", "notify", "dashboard"
}
_OPTIONS_WITH_VALUES = {"--style", "--persona"}


app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


@app.callback(invoke_without_command=True)
def cli_root(
    ctx: typer.Context,
    question: str | None = typer.Argument(None, metavar="<question>", show_default=False),
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),  # noqa: B008
    json_mode: bool = typer.Option(False, "--json", help="Emit raw JSON response."),  # noqa: B008
    debug: bool = typer.Option(False, "--debug", help="Show debug timing and metadata."),  # noqa: B008
    offline: bool | None = typer.Option(None, "--offline/--online", help="Skip network fetchers."),  # noqa: B008
    style: StyleLiteral = typer.Option("standard", "--style", case_sensitive=False),  # noqa: B008
    persona: PersonaLiteral = typer.Option("default", "--persona", case_sensitive=False),  # noqa: B008
    trust_tools: bool = typer.Option(
        False, "--trust-tools/--no-trust-tools", help="Allow network micro-fetchers."
    ),  # noqa: B008
    severe: bool = typer.Option(
        False, "--severe", help="Filter for severe weather only (floods, tornadoes, severe thunderstorms)."
    ),  # noqa: B008
):
    """Entry point that also handles freeform questions."""

    settings = load_settings(debug=debug, offline=offline, style=style, persona=persona)
    orchestrator = Orchestrator(settings, trust_tools=trust_tools)
    ctx.obj = {
        "settings": settings,
        "orchestrator": orchestrator,
        "json": json_mode,
        "debug": debug,
        "verbose": verbose,
        "trust_tools": trust_tools,
        "severe": severe,
    }

    if ctx.invoked_subcommand is not None:
        return

    # If no question provided, default to worldview
    if not question:
        worldview = orchestrator.handle_worldview(verbose=verbose, severe_only=severe)
        render_worldview(worldview, console=console, json_mode=json_mode, verbose=verbose or debug)
        return

    result = orchestrator.handle_question(question, verbose=verbose)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def forecast(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Target place name or lat,lon."),
    when: str | None = typer.Option(None, "--when", help="Natural language time hint."),  # noqa: B008
    horizon: str = typer.Option("24h", "--horizon", help="Forecast horizon", case_sensitive=False),  # noqa: B008
    focus: str | None = typer.Option(None, "--focus", help="Primary hazard or interest."),  # noqa: B008
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),  # noqa: B008
):
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    debug: bool = ctx.obj["debug"]
    result = orchestrator.handle_forecast(
        place, when_text=when, horizon=horizon, focus=focus, verbose=verbose
    )
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def risk(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Target place name or lat,lon."),
    hazards: str | None = typer.Option(None, "--hazards", help="Comma-separated hazard list."),  # noqa: B008
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),  # noqa: B008
):
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    debug: bool = ctx.obj["debug"]
    hazard_list = [h.strip() for h in hazards.split(",")] if hazards else None
    result = orchestrator.handle_risk(place, hazards=hazard_list, verbose=verbose)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def explain(ctx: typer.Context):
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    debug: bool = ctx.obj["debug"]
    verbose: bool = ctx.obj["verbose"]
    try:
        outcome = orchestrator.handle_explain()
    except RuntimeError as err:
        console.print(str(err))
        raise typer.Exit(1) from err

    if json_mode:
        payload = {
            "command": outcome.command,
            "question": outcome.question,
            "mode": outcome.mode,
            "text": outcome.text,
            "meta": outcome.meta,
            "provider": outcome.response.provider,
            "feature_pack": outcome.feature_pack,
        }
        console.print(json.dumps(payload, indent=2))
        return

    ds = DesignSystem()

    console.print()
    console.print(ds.heading(f"Explain ({outcome.mode})", level=1))
    console.print(Text(outcome.text or "No explanation available.", style="white"))
    console.print()

    if verbose or debug:
        console.print(ds.heading("Metadata", level=2))
        meta_payload = dict(outcome.meta)
        meta_payload.setdefault("provider", outcome.response.provider)
        meta_payload.setdefault("prompt_summary", outcome.response.prompt_summary)
        meta_payload.setdefault("confidence", outcome.response.confidence)
        console.print(Text(json.dumps(meta_payload, indent=2), style="dim"))
        console.print()

    if debug:
        console.print(ds.heading("Explain Sections", level=2))
        console.print(Text(json.dumps(outcome.response.sections, indent=2), style="dim"))
        console.print()
        console.print(ds.heading("Feature Pack", level=2))
        console.print(Text(json.dumps(outcome.feature_pack, indent=2), style="dim"))
        console.print()


@app.command()
def alerts(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Place name or lat,lon."),
    ai: bool = typer.Option(False, "--ai/--no-ai", help="Ask the AI to triage alerts."),  # noqa: B008
    stream: bool = typer.Option(False, "--stream", help="Stream headlines (future feature)."),  # noqa: B008
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),  # noqa: B008
):
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    debug: bool = ctx.obj["debug"]
    result = orchestrator.handle_alerts(place, ai=ai, stream=stream, verbose=verbose)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def chat(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),  # noqa: B008
):
    """Start an interactive conversational AI weather bot session."""
    settings = ctx.obj["settings"]
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    start_chat_session(settings, orchestrator, console, verbose=verbose, json_mode=json_mode)


@app.command()
def extended(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Target place name or lat,lon."),
    days: int = typer.Option(7, "--days", help="Number of days for extended forecast (max 14)."),  # noqa: B008
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),  # noqa: B008
):
    """Get extended multi-day forecast for a location."""
    from .fetchers import get_nws_forecast_grid, get_point_context
    from .visualizations import format_forecast_table_modern

    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    settings = ctx.obj["settings"]
    json_mode: bool = ctx.obj["json"]
    ds = DesignSystem()

    # Resolve location
    console.print(Text(f"Fetching {days}-day forecast for {place}...", style="dim"))

    place_info = get_point_context(place, offline=settings.offline)
    if not place_info:
        console.print(Text(f"Could not find location: {place}", style="bright_red"))
        raise typer.Exit(1)

    lat = place_info["lat"]
    lon = place_info["lon"]
    loc_name = place_info.get("resolved", place)

    # Get NWS gridded forecast
    forecast_data = get_nws_forecast_grid(lat, lon, offline=settings.offline)

    if json_mode:
        console.print(json.dumps(forecast_data, indent=2))
        return

    if forecast_data and forecast_data.get("periods"):
        periods = forecast_data["periods"][:days * 2]  # 2 periods per day (day/night)

        console.print()
        console.print(ds.heading(f"Extended Forecast - {loc_name}", level=1))
        console.print()

        format_forecast_table_modern(periods, console)

        console.print()
        console.print(Text(f"Updated: {forecast_data.get('updated', 'Unknown')}", style="dim"))
        console.print()
    else:
        console.print(Text(f"No extended forecast data available for {loc_name}.", style="bright_yellow"))


@app.command()
def radar(
    ctx: typer.Context,
    station: str | None = typer.Argument(None, help="Radar station ID (e.g., KOKX, KDMX). Leave empty to auto-detect."),
    place: str | None = typer.Option(None, "--place", "-p", help="Location to find nearest radar station."),  # noqa: B008
    animate: bool = typer.Option(False, "--animate", "-a", help="Show animated radar loop."),  # noqa: B008
    frames: int = typer.Option(10, "--frames", "-f", help="Number of frames for animation."),  # noqa: B008
    delay: float = typer.Option(0.5, "--delay", "-d", help="Delay between frames in seconds."),  # noqa: B008
    gui: bool = typer.Option(False, "--gui", "-g", help="Open GUI window for radar display."),  # noqa: B008
    list_stations: bool = typer.Option(False, "--list", "-l", help="List nearby radar stations."),  # noqa: B008
):
    """Display live weather radar with optional animation."""
    from .fetchers import get_point_context
    from .radar import RadarFetcher, display_radar

    settings = ctx.obj["settings"]
    ds = DesignSystem()

    if settings.offline:
        console.print(Text("Radar not available in offline mode", style="bright_yellow"))
        return

    fetcher = RadarFetcher()

    # List stations mode
    if list_stations:
        console.print()
        console.print(ds.heading("Available Radar Stations", level=1))
        console.print()

        if place:
            # Find stations near place
            place_info = get_point_context(place, offline=False)
            if place_info:
                lat = place_info["lat"]
                lon = place_info["lon"]
                stations = fetcher.get_available_stations_near(lat, lon, count=10)

                console.print(Text(f"Stations near {place_info.get('resolved', place)}:", style="bright_cyan"))
                console.print()

                for station_id, name in stations:
                    console.print(ds.info_row(station_id, name, indent=1))
            else:
                console.print(Text(f"Could not find location: {place}", style="bright_red"))
        else:
            # List some major stations
            major_stations = [
                ("KOKX", "New York, NY"),
                ("KDMX", "Des Moines, IA"),
                ("KFTG", "Denver, CO"),
                ("KFFC", "Atlanta, GA"),
                ("KHGX", "Houston, TX"),
                ("KLAX", "Los Angeles, CA"),
                ("KSEA", "Seattle, WA"),
                ("KMIA", "Miami, FL"),
                ("KORD", "Chicago, IL"),
                ("KDFW", "Dallas, TX"),
            ]

            console.print(Text("Major Radar Stations:", style="bright_cyan"))
            console.print()

            for station_id, name in major_stations:
                if station_id in fetcher.RADAR_STATIONS:
                    console.print(ds.info_row(station_id, fetcher.RADAR_STATIONS[station_id], indent=1))

        console.print()
        console.print(Text("Use: wx radar <STATION_ID> to view radar", style="dim"))
        console.print(Text("Example: wx radar KOKX --animate", style="dim"))
        console.print()
        return

    # Determine station
    if not station:
        if place:
            # Find nearest station to place
            place_info = get_point_context(place, offline=False)
            if place_info:
                lat = place_info["lat"]
                lon = place_info["lon"]
                station = fetcher.find_nearest_station(lat, lon)
                console.print(Text(f"Using nearest station for {place_info.get('resolved', place)}: {station}", style="dim"))
            else:
                console.print(Text(f"Could not find location: {place}", style="bright_red"))
                return
        else:
            # Default station
            station = "KDMX"
            console.print(Text(f"No station specified, using default: {station}", style="dim"))
            console.print(Text("Tip: Use --list to see available stations", style="dim"))
            console.print()

    # Display radar
    display_radar(
        station,
        animate=animate,
        frames=frames,
        delay=delay,
        gui=gui,
        offline=settings.offline,
        console=console,
    )


@app.command()
def international(
    ctx: typer.Context,
    location: str = typer.Argument(..., help="Location name (e.g., 'London', 'Toronto')"),
    forecast: bool = typer.Option(True, "--forecast/--no-forecast", help="Show forecast"),  # noqa: B008
    observations: bool = typer.Option(True, "--observations/--no-observations", help="Show observations"),  # noqa: B008
):
    """Get weather from international sources (UK Met Office, Environment Canada, etc.)."""
    from .international import get_international_weather

    settings = ctx.obj["settings"]
    ds = DesignSystem()

    # Get API keys from environment
    import os
    api_keys = {
        "metoffice": os.environ.get("METOFFICE_API_KEY"),
    }

    console.print()
    console.print(ds.heading(f"International Weather: {location}", level=1))
    console.print()

    result = get_international_weather(
        location,
        api_keys=api_keys,
        offline=settings.offline,
    )

    if result["error"]:
        console.print(Text(f"Error: {result['error']}", style="bright_red"))
        if "API key" in result["error"]:
            console.print()
            console.print(Text("Set your API key:", style="dim"))
            console.print(Text("  Met Office: export METOFFICE_API_KEY=your_key_here", style="dim"))
            console.print(Text("  Get a free key at: https://www.metoffice.gov.uk/datapoint", style="dim"))
        console.print()
        return

    console.print(Text(f"Data source: {result['service']}", style="bright_cyan"))
    console.print()

    if result["data"]:
        # Format and display data
        if result["service"] == "metoffice" and "forecast" in result["data"]:
            from .international import format_metoffice_forecast
            forecast_text = format_metoffice_forecast(result["data"]["forecast"])
            console.print(forecast_text)
        else:
            console.print(Text("Data received but formatting not yet implemented", style="dim"))
            console.print(Text("Raw data available in JSON mode", style="dim"))
    else:
        console.print(Text("No data available", style="bright_yellow"))

    console.print()


@app.command()
def lightning(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Location to check for lightning"),
    radius: int = typer.Option(100, "--radius", "-r", help="Search radius in km"),  # noqa: B008
    animate: bool = typer.Option(False, "--animate", "-a", help="Animate strikes"),  # noqa: B008
    show_map: bool = typer.Option(False, "--map", "-m", help="Show density map"),  # noqa: B008
):
    """Display real-time lightning strike data."""
    from .fetchers import get_point_context
    from .lightning import display_lightning

    settings = ctx.obj["settings"]

    # Resolve location
    place_info = get_point_context(place, offline=settings.offline)
    if not place_info:
        console.print(Text(f"Could not find location: {place}", style="bright_red"))
        return

    lat = place_info["lat"]
    lon = place_info["lon"]
    loc_name = place_info.get("resolved", place)

    console.print(Text(f"Lightning data for {loc_name} (within {radius}km)...", style="dim"))

    display_lightning(
        lat,
        lon,
        radius_km=radius,
        animate=animate,
        show_map=show_map,
        offline=settings.offline,
        console=console,
    )


@app.command()
def aqi(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Location to check air quality"),
    region: str = typer.Option("US", "--region", "-r", help="Region: US or UK"),  # noqa: B008
):
    """Display Air Quality Index (AQI) data."""
    from .airquality import display_air_quality
    from .fetchers import get_point_context

    settings = ctx.obj["settings"]

    # Resolve location
    place_info = get_point_context(place, offline=settings.offline)
    if not place_info:
        console.print(Text(f"Could not find location: {place}", style="bright_red"))
        return

    lat = place_info["lat"]
    lon = place_info["lon"]
    loc_name = place_info.get("resolved", place)

    # Get API key from environment
    import os
    api_key = os.environ.get("AIRNOW_API_KEY")

    if not api_key and not settings.offline:
        console.print(Text("Note: AirNow API key not set, using offline data", style="bright_yellow"))
        console.print(Text("Get a free key at: https://docs.airnowapi.org/", style="dim"))
        console.print()

    display_air_quality(
        lat,
        lon,
        location=loc_name,
        region=region.upper(),
        api_key=api_key,
        offline=settings.offline,
        console=console,
    )


@app.command()
def hurricanes(
    ctx: typer.Context,
    show_scale: bool = typer.Option(False, "--scale", "-s", help="Show Saffir-Simpson scale"),  # noqa: B008
    show_map: bool = typer.Option(False, "--map", "-m", help="Show storm position map"),  # noqa: B008
):
    """Display active hurricanes and tropical storms."""
    from .hurricanes import display_hurricanes

    settings = ctx.obj["settings"]

    display_hurricanes(
        show_scale=show_scale,
        show_map=show_map,
        offline=settings.offline,
        console=console,
    )


@app.command()
def notify(
    ctx: typer.Context,
    action: str = typer.Argument("list", help="Action: list, add, remove, toggle"),
    name: str | None = typer.Argument(None, help="Rule name"),  # noqa: B008
    condition: str | None = typer.Argument(None, help='Condition (e.g., "temp < 32")'),  # noqa: B008
    location: str | None = typer.Argument(None, help="Location to monitor"),  # noqa: B008
):
    """Manage weather notification rules."""
    from .notifications import NotificationManager, display_notification_config

    settings = ctx.obj["settings"]
    config_dir = settings.state_file.parent

    manager = NotificationManager(config_dir)

    if action == "list":
        display_notification_config(config_dir, console)

    elif action == "add":
        if not all([name, condition, location]):
            console.print(Text("Error: add requires name, condition, and location", style="bright_red"))
            console.print(Text('Example: wx notify add freeze "temp < 32" Denver', style="dim"))
            return

        if manager.add_rule(name, condition, location):
            console.print(Text(f"✓ Added rule: {name}", style="bright_green"))
        else:
            console.print(Text("Failed to add rule", style="bright_red"))

    elif action == "remove":
        if not name:
            console.print(Text("Error: remove requires rule name", style="bright_red"))
            return

        if manager.remove_rule(name):
            console.print(Text(f"✓ Removed rule: {name}", style="bright_green"))
        else:
            console.print(Text(f"Rule not found: {name}", style="bright_yellow"))

    elif action == "toggle":
        if not name:
            console.print(Text("Error: toggle requires rule name", style="bright_red"))
            return

        if manager.toggle_rule(name):
            console.print(Text(f"✓ Toggled rule: {name}", style="bright_green"))
        else:
            console.print(Text(f"Rule not found: {name}", style="bright_yellow"))

    else:
        console.print(Text(f"Unknown action: {action}", style="bright_red"))
        console.print(Text("Valid actions: list, add, remove, toggle", style="dim"))


@app.command()
def dashboard(
    ctx: typer.Context,
    locations: list[str] = typer.Argument(..., help="Locations to compare (space-separated)"),
    mode: str = typer.Option("compare", "--mode", "-m", help="Mode: compare, travel, trending"),  # noqa: B008
):
    """Compare weather across multiple locations."""
    from .dashboard import display_dashboard

    settings = ctx.obj["settings"]

    if len(locations) < 2:
        console.print(Text("Error: dashboard requires at least 2 locations", style="bright_red"))
        console.print(Text('Example: wx dashboard "New York" "London" "Tokyo"', style="dim"))
        return

    display_dashboard(
        locations,
        mode=mode,
        offline=settings.offline,
        console=console,
    )


def _normalize_invocation(args: Sequence[str]) -> list[str]:
    """Insert a placeholder question when the first positional is a subcommand."""

    tokens = list(args)
    idx = 0
    forced_question = False

    while idx < len(tokens):
        token = tokens[idx]
        if token == "--":
            forced_question = True
            idx += 1
            break
        if token.startswith("-"):
            if token in _OPTIONS_WITH_VALUES and idx + 1 < len(tokens):
                idx += 2
            else:
                idx += 1
            continue
        break

    if idx >= len(tokens):
        return tokens

    if forced_question:
        return tokens

    candidate = tokens[idx]
    if candidate in COMMAND_NAMES and (idx == 0 or tokens[idx - 1] != ""):
        return tokens[:idx] + [""] + tokens[idx:]

    return tokens


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    normalized = _normalize_invocation(args)
    app(args=normalized)


if __name__ == "__main__":  # pragma: no cover
    main()
