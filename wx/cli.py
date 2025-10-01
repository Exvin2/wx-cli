"""Typer CLI entry-point for wx."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from .config import PersonaLiteral, StyleLiteral, load_settings
from .orchestrator import Orchestrator
from .render import render_result

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    question: Optional[str] = typer.Argument(None, metavar="<question>", show_default=False),
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),
    json_mode: bool = typer.Option(False, "--json", help="Emit raw JSON response."),
    debug: bool = typer.Option(False, "--debug", help="Show debug timing and metadata."),
    offline: bool = typer.Option(False, "--offline/--online", help="Skip network fetchers."),
    style: StyleLiteral = typer.Option("standard", "--style", case_sensitive=False),
    persona: PersonaLiteral = typer.Option("default", "--persona", case_sensitive=False),
    trust_tools: bool = typer.Option(False, "--trust-tools/--no-trust-tools", help="Allow network micro-fetchers."),
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
    }

    if ctx.invoked_subcommand is not None:
        return

    if not question:
        console.print("Provide a question or use a subcommand. Try: wx forecast \"Boston\"")
        raise typer.Exit(1)

    result = orchestrator.handle_question(question, verbose=verbose)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def forecast(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Target place name or lat,lon."),
    when: Optional[str] = typer.Option(None, "--when", help="Natural language time hint."),
    horizon: str = typer.Option("24h", "--horizon", help="Forecast horizon", case_sensitive=False),
    focus: Optional[str] = typer.Option(None, "--focus", help="Primary hazard or interest."),
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),
):
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    debug: bool = ctx.obj["debug"]
    result = orchestrator.handle_forecast(place, when_text=when, horizon=horizon, focus=focus, verbose=verbose)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def risk(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Target place name or lat,lon."),
    hazards: Optional[str] = typer.Option(None, "--hazards", help="Comma-separated hazard list."),
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),
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
        result = orchestrator.handle_explain()
    except RuntimeError as err:
        console.print(str(err))
        raise typer.Exit(1)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


@app.command()
def alerts(
    ctx: typer.Context,
    place: str = typer.Argument(..., help="Place name or lat,lon."),
    ai: bool = typer.Option(False, "--ai/--no-ai", help="Ask the AI to triage alerts."),
    stream: bool = typer.Option(False, "--stream", help="Stream headlines (future feature)."),
    verbose: bool = typer.Option(False, "--verbose", help="Allow responses beyond 400 words."),
):
    orchestrator: Orchestrator = ctx.obj["orchestrator"]
    json_mode: bool = ctx.obj["json"]
    debug: bool = ctx.obj["debug"]
    result = orchestrator.handle_alerts(place, ai=ai, stream=stream, verbose=verbose)
    render_result(result, console=console, json_mode=json_mode, debug=debug, verbose=verbose)


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
