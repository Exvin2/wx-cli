"""Rich rendering utilities for wx."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def render_result(
    result,
    *,
    console: Console,
    json_mode: bool,
    debug: bool,
    verbose: bool,
) -> None:
    if json_mode:
        console.print(_result_to_json(result))
        return

    response = result.response
    word_limit = None if verbose else 400
    limiter = _WordLimiter(word_limit)

    summary_panel = Panel(
        limiter.join_lines(response.sections.get("summary"), default="No summary provided."),
        title="Summary",
        expand=False,
    )

    timeline_panel = Panel(
        limiter.join_bullets(response.sections.get("timeline"), default="No timeline available."),
        title="Timeline",
        expand=False,
    )

    risk_panel = Panel(
        _build_risk_table(response.sections.get("risk_cards"), limiter),
        title="Risk Cards",
        expand=False,
    )

    confidence_panel = Panel(
        limiter.consume(str(response.sections.get("confidence", "Confidence not available."))),
        title=f"Confidence ({response.confidence.get('value', '?')}%)",
        expand=False,
    )

    actions_panel = Panel(
        limiter.join_bullets(response.sections.get("actions"), default="No actions provided."),
        title="Actions",
        expand=False,
    )

    assumptions_panel = Panel(
        limiter.join_bullets(
            response.sections.get("assumptions"), default="No assumptions recorded."
        ),
        title="Assumptions",
        expand=False,
    )

    console.print(summary_panel)
    console.print(timeline_panel)
    console.print(risk_panel)
    console.print(confidence_panel)
    console.print(actions_panel)
    console.print(assumptions_panel)

    bottom_line_text = limiter.consume(response.bottom_line or "Bottom line unavailable.")
    console.print(Text(bottom_line_text, style="bold"))

    if debug:
        console.print(Panel(json.dumps(result.debug, indent=2), title="Debug"))
        console.print(
            Panel(
                json.dumps(
                    {
                        "provider": response.provider,
                        "confidence": response.confidence,
                        "used_feature_fields": response.used_feature_fields,
                    },
                    indent=2,
                ),
                title="AI Metadata",
            )
        )


class _WordLimiter:
    """Apply a global word cap across sections."""

    def __init__(self, limit: int | None) -> None:
        self.limit = limit
        self.words_used = 0

    def consume(self, text: str) -> str:
        if not text:
            return ""
        if self.limit is None:
            return text
        words = text.split()
        if not words:
            return text
        remaining = self.limit - self.words_used
        if remaining <= 0:
            return ""
        if len(words) <= remaining:
            self.words_used += len(words)
            return text
        truncated = " ".join(words[:remaining]) + " …"
        self.words_used = self.limit
        return truncated

    def join_lines(self, value: Any, *, default: str) -> str:
        lines = self._normalize_list(value)
        if not lines:
            return default
        rendered = [self.consume(str(line)) for line in lines]
        return "\n".join(filter(None, rendered)) or default

    def join_bullets(self, value: Any, *, default: str) -> str:
        items = self._normalize_list(value)
        if not items:
            return default
        rendered = [self.consume(str(item)) for item in items]
        rendered = [item for item in rendered if item]
        if not rendered:
            return default
        return "\n".join(f"• {item}" for item in rendered)

    def _normalize_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        try:
            return [str(item) for item in value if item]
        except TypeError:
            return [str(value)]


def _build_risk_table(cards: Any, limiter: _WordLimiter) -> Table:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Hazard")
    table.add_column("Level")
    table.add_column("Drivers")
    table.add_column("Confidence")

    if isinstance(cards, dict) or isinstance(cards, (str, bytes)):
        records = []
    elif isinstance(cards, Iterable):
        records = cards
    else:
        records = []
    added = False
    for card in records:
        if not isinstance(card, dict):
            continue
        hazard = str(card.get("hazard", "Unknown"))
        level = str(card.get("level", ""))
        drivers = limiter.consume(", ".join(card.get("drivers", [])))
        confidence = limiter.consume(str(card.get("confidence", "")))
        table.add_row(hazard, level, drivers, confidence)
        added = True
    if not added:
        table.add_row("General", "Low", "Insufficient data", "Low confidence")
    return table


def _result_to_json(result) -> str:
    payload = {
        "command": result.command,
        "query": result.query,
        "feature_pack": result.feature_pack,
        "response": {
            "sections": result.response.sections,
            "confidence": result.response.confidence,
            "used_feature_fields": result.response.used_feature_fields,
            "bottom_line": result.response.bottom_line,
            "provider": result.response.provider,
        },
        "timings": result.timings,
        "debug": result.debug,
    }
    return json.dumps(payload, indent=2)


def render_worldview(worldview, *, console: Console, json_mode: bool = False, verbose: bool = False) -> None:
    """Render worldview aggregate summary."""
    if json_mode:
        payload = {
            "regions": [
                {
                    "name": region.name,
                    "summary": region.summary,
                    "stats": {
                        "tmin": region.stats.tmin,
                        "tmax": region.stats.tmax,
                        "pop_max": region.stats.pop_max,
                        "wind_max": region.stats.wind_max,
                        "gust_max": region.stats.gust_max,
                    },
                    "alerts": region.alerts,
                }
                for region in worldview.regions
            ],
            "meta": worldview.meta,
        }
        console.print(json.dumps(payload, indent=2, ensure_ascii=True))
        return

    # Check if severe weather mode
    severe_only = worldview.meta.get("severe_only", False)

    # Human-readable summary
    for region in worldview.regions:
        console.print(f"[bold]{region.name}[/bold] — {region.summary}")

    # Top risks with severe weather highlighting
    all_alerts = []
    for region in worldview.regions:
        for alert in region.alerts:
            event = alert['event']
            # Highlight severe weather events
            if _is_severe_alert(event):
                all_alerts.append(f"[bold red]{event}[/bold red] in {region.name}")
            else:
                all_alerts.append(f"{event} in {region.name}")

    if all_alerts:
        title = "[bold red]⚠️  SEVERE WEATHER ALERTS[/bold red]" if severe_only else "[bold yellow]Top risks[/bold yellow]"
        risks_text = "; ".join(all_alerts[:5] if severe_only else all_alerts[:3])  # Show more in severe mode
        console.print(f"\n{title} — {risks_text}")
    else:
        if severe_only:
            console.print("\n[bold green]✓ No severe weather alerts (floods, tornadoes, severe thunderstorms)[/bold green]")
        else:
            console.print("\n[bold green]No significant risks reported[/bold green]")

    if verbose:
        # Show metadata
        meta_text = f"Samples: US={worldview.meta.get('samples_us', 0)}, EU={worldview.meta.get('samples_eu', 0)} | "
        meta_text += f"Fetch time: {worldview.meta.get('fetch_ms', 0)}ms | "
        meta_text += f"Sources: {', '.join(worldview.meta.get('sources', []))}"
        if severe_only:
            meta_text += " | Filter: SEVERE ONLY"
        console.print(f"\n[dim]{meta_text}[/dim]")


def _is_severe_alert(event: str) -> bool:
    """Check if alert is severe weather."""
    severe_keywords = ["tornado", "flood", "severe thunderstorm", "tor-", "tor pds", "pds"]
    event_lower = event.lower()
    return any(kw in event_lower for kw in severe_keywords)
