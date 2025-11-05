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

    # Summary section
    limiter.set_section_budget("summary")
    summary_panel = Panel(
        limiter.join_lines(response.sections.get("summary"), default="No summary provided."),
        title="Summary",
        expand=False,
    )

    # Timeline section
    limiter.set_section_budget("timeline")
    timeline_panel = Panel(
        limiter.join_bullets(response.sections.get("timeline"), default="No timeline available."),
        title="Timeline",
        expand=False,
    )

    # Risk section
    limiter.set_section_budget("risk")
    risk_content = _build_risk_cards(response.sections.get("risk_cards"), limiter)
    risk_panel = Panel(
        risk_content,
        title="Risk Cards",
        expand=False,
    )

    # Confidence section
    limiter.set_section_budget("confidence")
    confidence_panel = Panel(
        limiter.consume(str(response.sections.get("confidence", "Confidence not available."))),
        title=f"Confidence ({response.confidence.get('value', '?')}%)",
        expand=False,
    )

    # Actions section
    limiter.set_section_budget("actions")
    actions_panel = Panel(
        limiter.join_bullets(response.sections.get("actions"), default="No actions provided."),
        title="Actions",
        expand=False,
    )

    # Assumptions section
    limiter.set_section_budget("assumptions")
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
    """Apply a global word cap across sections with fair allocation."""

    def __init__(self, limit: int | None) -> None:
        self.limit = limit
        self.words_used = 0
        # Allocate words per section for more predictable behavior
        # Summary: 30%, Timeline: 25%, Risk: 20%, Confidence: 10%, Actions: 10%, Assumptions: 5%
        self.section_allocations = {
            "summary": 0.30,
            "timeline": 0.25,
            "risk": 0.20,
            "confidence": 0.10,
            "actions": 0.10,
            "assumptions": 0.05,
        }
        self.current_section_budget = None

    def set_section_budget(self, section: str) -> None:
        """Set the budget for the current section."""
        if self.limit is None:
            self.current_section_budget = None
        else:
            allocation = self.section_allocations.get(section, 0.05)
            self.current_section_budget = int(self.limit * allocation)

    def consume(self, text: str) -> str:
        if not text:
            return ""
        if self.limit is None:
            return text
        words = text.split()
        if not words:
            return text

        # Check both global limit and section budget
        global_remaining = self.limit - self.words_used
        if global_remaining <= 0:
            return ""

        # Use section budget if set, otherwise use global limit
        effective_limit = global_remaining
        if self.current_section_budget is not None:
            effective_limit = min(global_remaining, self.current_section_budget)

        if effective_limit <= 0:
            return ""

        if len(words) <= effective_limit:
            self.words_used += len(words)
            if self.current_section_budget is not None:
                self.current_section_budget -= len(words)
            return text

        truncated = " ".join(words[:effective_limit]) + " …"
        self.words_used += effective_limit
        if self.current_section_budget is not None:
            self.current_section_budget = 0
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


def _build_risk_cards(cards: Any, limiter: _WordLimiter) -> str:
    """Build risk cards as formatted text instead of nested table."""
    if isinstance(cards, dict) or isinstance(cards, (str, bytes)):
        records = []
    elif isinstance(cards, Iterable):
        records = list(cards)
    else:
        records = []

    if not records:
        return "No specific risk cards available.\n• General risk level: Low\n• Insufficient data for detailed assessment"

    lines = []
    for i, card in enumerate(records, 1):
        if not isinstance(card, dict):
            continue

        hazard = str(card.get("hazard", "Unknown"))
        level = str(card.get("level", "Unknown"))
        drivers = card.get("drivers", [])
        confidence = str(card.get("confidence", "Unknown"))

        # Format each risk card
        lines.append(f"[bold]{i}. {hazard}[/bold]")
        lines.append(f"   Level: [yellow]{level}[/yellow]")

        if drivers:
            drivers_text = limiter.consume(", ".join(drivers))
            lines.append(f"   Drivers: {drivers_text}")

        conf_text = limiter.consume(confidence)
        lines.append(f"   Confidence: {conf_text}")
        lines.append("")  # Blank line between cards

    return "\n".join(lines).rstrip()


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


def render_story(story, *, console: Console, json_mode: bool = False, verbose: bool = False) -> None:
    """Render a weather story with rich formatting.

    Args:
        story: WeatherStory object from storyteller module
        console: Rich Console instance
        json_mode: Output as JSON instead of formatted text
        verbose: Include extended metadata and details
    """
    if json_mode:
        console.print(json.dumps(story.to_dict(), indent=2, ensure_ascii=True))
        return

    # Title with location if available
    location = story.meta.get("location", "Weather Story")
    title_text = Text(f"📖  {location}", style="bold cyan")
    console.print(title_text)
    console.print()

    # THE SETUP section
    setup_panel = Panel(
        story.setup,
        title="[bold]🌤️  THE SETUP[/bold] [dim](What's Happening)[/dim]",
        border_style="blue",
        expand=False,
    )
    console.print(setup_panel)

    # THE PRESENT section
    current_panel = Panel(
        story.current,
        title="[bold]🌡️  THE PRESENT[/bold]",
        border_style="cyan",
        expand=False,
    )
    console.print(current_panel)

    # THE EVOLUTION section (timeline)
    if story.evolution.phases:
        timeline_content = _build_story_timeline(story.evolution)
        evolution_panel = Panel(
            timeline_content,
            title="[bold]⏳  THE EVOLUTION[/bold] [dim](Your Next Hours)[/dim]",
            border_style="yellow",
            expand=False,
        )
        console.print(evolution_panel)

    # THE METEOROLOGY section
    meteorology_panel = Panel(
        story.meteorology,
        title="[bold]🌀  THE METEOROLOGY[/bold] [dim](Why This Matters)[/dim]",
        border_style="magenta",
        expand=False,
    )
    console.print(meteorology_panel)

    # YOUR DECISIONS section
    if story.decisions:
        decisions_content = _build_story_decisions(story.decisions)
        decisions_panel = Panel(
            decisions_content,
            title="[bold]🎯  YOUR DECISIONS[/bold] [dim](What To Do)[/dim]",
            border_style="green",
            expand=False,
        )
        console.print(decisions_panel)

    # CONFIDENCE NOTES section
    confidence_content = _build_story_confidence(story.confidence)
    confidence_panel = Panel(
        confidence_content,
        title="[bold]📊  CONFIDENCE NOTES[/bold]",
        border_style="white",
        expand=False,
    )
    console.print(confidence_panel)

    # Bottom line
    console.print()
    bottom_line_text = Text(f"💡 {story.bottom_line}", style="bold yellow")
    console.print(bottom_line_text)

    # Verbose metadata
    if verbose:
        meta_lines = [
            f"Provider: {story.meta.get('provider', 'unknown')}",
            f"Used fields: {', '.join(story.meta.get('used_fields', []))}",
        ]
        console.print(f"\n[dim]{' | '.join(meta_lines)}[/dim]")


def _build_story_timeline(timeline) -> str:
    """Build timeline visualization with phases."""
    if not timeline.phases:
        return "No timeline available."

    lines = []
    for i, phase in enumerate(timeline.phases):
        prefix = "├─" if i < len(timeline.phases) - 1 else "└─"
        time_range = f"{phase.start_time}–{phase.end_time}"

        # Phase description
        lines.append(f"{prefix} [bold]{time_range}[/bold]: {phase.description}")

        # Key changes if present
        if phase.key_changes:
            for change in phase.key_changes:
                indent = "│  " if i < len(timeline.phases) - 1 else "   "
                lines.append(f"{indent}  • {change}")

        # Confidence indicator
        conf_bars = _confidence_bars(phase.confidence)
        if i < len(timeline.phases) - 1:
            lines.append(f"│  [dim]Confidence: {conf_bars}[/dim]")
        else:
            lines.append(f"   [dim]Confidence: {conf_bars}[/dim]")

        # Blank line between phases except the last
        if i < len(timeline.phases) - 1:
            lines.append("│")

    return "\n".join(lines)


def _build_story_decisions(decisions: list) -> str:
    """Format decision recommendations."""
    if not decisions:
        return "No specific recommendations available."

    lines = []
    for i, decision in enumerate(decisions, 1):
        # Activity with emoji
        emoji = _get_activity_emoji(decision.activity)
        lines.append(f"{emoji}  [bold]{decision.activity}[/bold]")

        # Recommendation
        lines.append(f"   → {decision.recommendation}")

        # Reasoning
        lines.append(f"   [dim]Why: {decision.reasoning}[/dim]")

        # Timing if specified
        if decision.timing:
            lines.append(f"   [dim]Best timing: {decision.timing}[/dim]")

        # Confidence
        conf_bars = _confidence_bars(decision.confidence)
        lines.append(f"   [dim]Confidence: {conf_bars}[/dim]")

        # Blank line between decisions
        if i < len(decisions):
            lines.append("")

    return "\n".join(lines)


def _build_story_confidence(confidence) -> str:
    """Format confidence notes."""
    lines = []

    # Primary uncertainty
    lines.append(f"[yellow]⚠️  Primary uncertainty:[/yellow] {confidence.primary_uncertainty}")

    # Alternative scenarios
    if confidence.alternative_scenarios:
        lines.append("")
        lines.append("[cyan]Alternative scenarios:[/cyan]")
        for scenario in confidence.alternative_scenarios:
            lines.append(f"  • {scenario}")

    # Overall confidence level
    lines.append("")
    level_color = {
        "High": "green",
        "Medium": "yellow",
        "Low": "red",
    }.get(confidence.confidence_level, "white")

    lines.append(
        f"[{level_color}]Overall confidence: {confidence.confidence_level}[/{level_color}]"
    )

    # Rationale
    if confidence.rationale:
        lines.append(f"[dim]{confidence.rationale}[/dim]")

    return "\n".join(lines)


def _confidence_bars(confidence: float) -> str:
    """Create visual confidence indicator."""
    filled = int(confidence * 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty


def _get_activity_emoji(activity: str) -> str:
    """Map activity types to emoji."""
    activity_lower = activity.lower()

    emoji_map = {
        "commute": "🚗",
        "bike": "🚴",
        "run": "🏃",
        "walk": "🚶",
        "outdoor": "🌳",
        "lunch": "☕",
        "dinner": "🍽️",
        "aviation": "✈️",
        "sailing": "⛵",
        "marine": "🌊",
        "sports": "⚽",
        "event": "📅",
        "travel": "🧳",
        "work": "💼",
        "school": "🎒",
    }

    for key, emoji in emoji_map.items():
        if key in activity_lower:
            return emoji

    return "📌"  # Default pin emoji
