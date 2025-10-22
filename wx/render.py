"""Rich rendering utilities for wx."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from rich.console import Console, Group
from rich.text import Text

from .design import DesignSystem
from .visualizations import format_alert_severity


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
    ds = DesignSystem()

    console.print()  # Top spacing

    # Summary section - clean, no borders
    limiter.set_section_budget("summary")
    console.print(ds.heading("Summary", level=1))
    summary_text = limiter.join_lines(response.sections.get("summary"), default="No summary provided.")
    console.print(Text(summary_text, style="white"))
    console.print()

    # Timeline section
    limiter.set_section_budget("timeline")
    console.print(ds.heading("Timeline", level=1))
    timeline_items = _normalize_list(response.sections.get("timeline"))
    if timeline_items:
        for item in timeline_items:
            consumed = limiter.consume(str(item))
            if consumed:
                console.print(ds.bullet_point(consumed))
    else:
        console.print(Text("No timeline available.", style="dim"))
    console.print()

    # Risk section - clean card layout
    limiter.set_section_budget("risk")
    console.print(ds.heading("Risk Assessment", level=1))
    _render_risk_cards_clean(response.sections.get("risk_cards"), limiter, console)
    console.print()

    # Confidence section
    limiter.set_section_budget("confidence")
    confidence_value = response.confidence.get('value', '?')
    console.print(ds.heading(f"Confidence  {confidence_value}%", level=1))
    conf_text = limiter.consume(str(response.sections.get("confidence", "Confidence not available.")))
    console.print(Text(conf_text, style="white"))
    console.print()

    # Actions section
    limiter.set_section_budget("actions")
    console.print(ds.heading("Recommended Actions", level=1))
    action_items = _normalize_list(response.sections.get("actions"))
    if action_items:
        for item in action_items:
            consumed = limiter.consume(str(item))
            if consumed:
                console.print(ds.bullet_point(consumed, color="bright_green"))
    else:
        console.print(Text("No actions provided.", style="dim"))
    console.print()

    # Assumptions section
    limiter.set_section_budget("assumptions")
    console.print(ds.heading("Assumptions", level=2))
    assumption_items = _normalize_list(response.sections.get("assumptions"))
    if assumption_items:
        for item in assumption_items:
            consumed = limiter.consume(str(item))
            if consumed:
                console.print(ds.bullet_point(consumed, color="bright_black"))
    else:
        console.print(Text("No assumptions recorded.", style="dim"))
    console.print()

    # Bottom line - prominent
    console.print(ds.separator())
    bottom_line_text = limiter.consume(response.bottom_line or "Bottom line unavailable.")
    console.print(Text(f"\n{bottom_line_text}\n", style="bold bright_blue"))

    if debug:
        console.print(ds.separator())
        console.print(ds.heading("Debug Information", level=2))
        console.print(Text(json.dumps(result.debug, indent=2), style="dim"))
        console.print()
        console.print(ds.heading("AI Metadata", level=2))
        console.print(
            Text(
                json.dumps(
                    {
                        "provider": response.provider,
                        "confidence": response.confidence,
                        "used_feature_fields": response.used_feature_fields,
                    },
                    indent=2,
                ),
                style="dim",
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


def _render_risk_cards_clean(cards: Any, limiter: _WordLimiter, console: Console) -> None:
    """Render risk cards with clean, modern design."""
    if isinstance(cards, dict) or isinstance(cards, (str, bytes)):
        records = []
    elif isinstance(cards, Iterable):
        records = list(cards)
    else:
        records = []

    if not records:
        console.print(Text("No specific risk cards available.", style="dim"))
        console.print(Text("  General risk level: Low", style="bright_black"))
        console.print(Text("  Insufficient data for detailed assessment", style="bright_black"))
        return

    ds = DesignSystem()

    for i, card in enumerate(records, 1):
        if not isinstance(card, dict):
            continue

        hazard = str(card.get("hazard", "Unknown"))
        level = str(card.get("level", "Unknown"))
        drivers = card.get("drivers", [])
        confidence = str(card.get("confidence", "Unknown"))

        # Card number and hazard
        title = Text()
        title.append(f"{i}. ", style="bright_blue")
        title.append(hazard, style="bold white")
        console.print(title)

        # Level with color coding
        level_text = Text()
        level_text.append("   Level: ", style="bright_black")
        if "high" in level.lower() or "extreme" in level.lower():
            level_text.append(level, style="bright_red")
        elif "moderate" in level.lower() or "medium" in level.lower():
            level_text.append(level, style="bright_yellow")
        else:
            level_text.append(level, style="bright_green")
        console.print(level_text)

        # Drivers
        if drivers:
            drivers_text = limiter.consume(", ".join(drivers))
            if drivers_text:
                info = Text()
                info.append("   Drivers: ", style="bright_black")
                info.append(drivers_text, style="white")
                console.print(info)

        # Confidence
        conf_text = limiter.consume(confidence)
        if conf_text:
            conf_info = Text()
            conf_info.append("   Confidence: ", style="bright_black")
            conf_info.append(conf_text, style="bright_cyan")
            console.print(conf_info)

        console.print()  # Spacing between cards


def _normalize_list(value: Any) -> list[str]:
    """Normalize value to list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    try:
        return [str(item) for item in value if item]
    except TypeError:
        return [str(value)]


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
    """Render worldview aggregate summary with modern design."""
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

    ds = DesignSystem()
    severe_only = worldview.meta.get("severe_only", False)

    console.print()

    # Title
    if severe_only:
        console.print(ds.heading("Severe Weather Alerts", level=1))
    else:
        console.print(ds.heading("Weather Overview", level=1))

    console.print()

    # Regional summaries - clean layout
    for region in worldview.regions:
        region_text = Text()
        region_text.append(f"{region.name}", style="bold bright_cyan")
        region_text.append(f"  {region.summary}", style="white")
        console.print(region_text)

    console.print()

    # Alerts section
    all_alerts = []
    for region in worldview.regions:
        for alert in region.alerts:
            event = alert['event']
            count = alert.get('count', 1)
            if _is_severe_alert(event):
                all_alerts.append((event, count, region.name, True))
            else:
                all_alerts.append((event, count, region.name, False))

    if all_alerts:
        if severe_only:
            console.print(ds.heading("Active Severe Weather Alerts", level=2))
        else:
            console.print(ds.heading("Active Alerts", level=2))

        # Display alerts with clean formatting
        display_count = 5 if severe_only else 3
        for event, count, region_name, is_severe in all_alerts[:display_count]:
            alert_line = Text()
            alert_line.append("  • ", style="bright_blue")
            if is_severe:
                alert_line.append(event, style="bold bright_red")
            else:
                alert_line.append(event, style="bright_yellow")
            alert_line.append(f" ({count})", style="bright_black")
            alert_line.append(f" in {region_name}", style="white")
            console.print(alert_line)

        console.print()
    else:
        if severe_only:
            success_msg = Text()
            success_msg.append("  No severe weather alerts", style="bold bright_green")
            console.print(success_msg)
            console.print(Text("  No floods, tornadoes, or severe thunderstorms detected", style="dim"))
        else:
            console.print(Text("  No significant risks reported", style="bright_green"))
        console.print()

    if verbose:
        # Metadata with clean formatting
        console.print(ds.separator())
        meta_parts = [
            f"Samples: US={worldview.meta.get('samples_us', 0)}, EU={worldview.meta.get('samples_eu', 0)}",
            f"Fetch time: {worldview.meta.get('fetch_ms', 0)}ms",
            f"Sources: {', '.join(worldview.meta.get('sources', []))}",
        ]
        if severe_only:
            meta_parts.append("Filter: SEVERE ONLY")

        console.print(Text("  ".join(meta_parts), style="dim"))
        console.print()


def _is_severe_alert(event: str) -> bool:
    """Check if alert is severe weather."""
    severe_keywords = ["tornado", "flood", "severe thunderstorm", "tor-", "tor pds", "pds"]
    event_lower = event.lower()
    return any(kw in event_lower for kw in severe_keywords)
