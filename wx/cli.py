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

COMMAND_NAMES = {"forecast", "risk", "explain", "alerts", "chat", "extended"}
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
