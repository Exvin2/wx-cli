"""Weather storytelling engine - transforms data into narratives."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config import Settings
from .forecaster import Forecaster, ForecasterResponse


@dataclass(slots=True)
class TimelinePhase:
    """A temporal phase in the weather story."""

    start_time: str
    end_time: str
    description: str
    key_changes: list[str] = field(default_factory=list)
    confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "description": self.description,
            "key_changes": self.key_changes,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class Decision:
    """A personalized recommendation tied to user context."""

    activity: str
    recommendation: str
    reasoning: str
    timing: str | None = None
    confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return {
            "activity": self.activity,
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "timing": self.timing,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class ConfidenceNote:
    """Uncertainty and alternative scenarios."""

    primary_uncertainty: str
    alternative_scenarios: list[str] = field(default_factory=list)
    confidence_level: str = "Medium"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_uncertainty": self.primary_uncertainty,
            "alternative_scenarios": self.alternative_scenarios,
            "confidence_level": self.confidence_level,
            "rationale": self.rationale,
        }


@dataclass(slots=True)
class Timeline:
    """Temporal progression of weather."""

    phases: list[TimelinePhase] = field(default_factory=list)
    visualization: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phases": [phase.to_dict() for phase in self.phases],
            "visualization": self.visualization,
        }

    @classmethod
    def from_raw_phases(cls, raw_phases: list[dict[str, Any]]) -> Timeline:
        """Create Timeline from raw dictionary data."""
        phases = [
            TimelinePhase(
                start_time=p.get("start_time", ""),
                end_time=p.get("end_time", ""),
                description=p.get("description", ""),
                key_changes=p.get("key_changes", []),
                confidence=p.get("confidence", 0.7),
            )
            for p in raw_phases
        ]
        return cls(phases=phases, visualization=_build_timeline_viz(phases))


@dataclass(slots=True)
class WeatherStory:
    """A complete weather narrative with context, evolution, and decisions."""

    setup: str
    current: str
    evolution: Timeline
    meteorology: str
    decisions: list[Decision]
    confidence: ConfidenceNote
    bottom_line: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "setup": self.setup,
            "current": self.current,
            "evolution": self.evolution.to_dict(),
            "meteorology": self.meteorology,
            "decisions": [d.to_dict() for d in self.decisions],
            "confidence": self.confidence.to_dict(),
            "bottom_line": self.bottom_line,
            "meta": self.meta,
        }


def _build_timeline_viz(phases: list[TimelinePhase]) -> str:
    """Create ASCII timeline visualization using box-drawing characters."""
    if not phases:
        return ""

    lines = []
    for i, phase in enumerate(phases):
        prefix = "├─" if i < len(phases) - 1 else "└─"
        time_range = f"{phase.start_time}–{phase.end_time}"
        lines.append(f"{prefix} {time_range}: {phase.description}")
    return "\n".join(lines)


# Story prompt template for AI
STORY_PROMPT_TEMPLATE = textwrap.dedent(
    """
    You are an expert meteorologist crafting a weather story, not just reporting data.

    Your story must educate, inform, and guide decisions. Tell people WHY weather happens,
    not just WHAT happens. Use clear language but don't avoid meteorological concepts—
    explain them naturally.

    Structure your response as a JSON object with these sections:

    {
      "setup": "2-3 sentences explaining the atmospheric pattern causing current conditions",
      "current": "2-3 sentences describing present conditions with interpretation",
      "evolution": {
        "phases": [
          {
            "start_time": "readable time (e.g., '7am', 'noon', 'evening')",
            "end_time": "readable time",
            "description": "what happens during this phase and why",
            "key_changes": ["specific changes to watch for"],
            "confidence": 0.7
          }
        ]
      },
      "meteorology": "2-3 sentences explaining WHY using concepts like fronts, pressure systems, jet stream, etc.",
      "decisions": [
        {
          "activity": "specific activity type (e.g., 'Morning commute', 'Outdoor lunch', 'Evening run')",
          "recommendation": "clear guidance",
          "reasoning": "why this recommendation makes sense",
          "timing": "best timing if relevant",
          "confidence": 0.8
        }
      ],
      "confidence": {
        "primary_uncertainty": "where is uncertainty highest?",
        "alternative_scenarios": ["what else could happen?"],
        "confidence_level": "High|Medium|Low",
        "rationale": "why this confidence level?"
      },
      "bottom_line": "single compelling sentence that captures the story"
    }

    Context:
    - Location: {location}
    - Current time: {current_time}
    - User query: {user_query}
    - Time horizon: {time_horizon}

    Weather Data (Feature Pack):
    {feature_pack_json}

    Guidelines:
    - Create 3-5 evolution phases covering the time horizon
    - Make decisions relevant to this location and time of day
    - Use specific times (not vague "later" or "soon")
    - Explain causality (fronts moving, systems clashing, energy building)
    - Be honest about uncertainty—don't fake precision
    - Make the bottom line memorable

    Generate the weather story now as valid JSON:
    """
).strip()


class Storyteller:
    """Generate narrative weather stories from Feature Packs."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.forecaster = Forecaster(settings)

    def generate_story(
        self,
        *,
        location: str,
        query: str,
        feature_pack: dict[str, Any],
        time_horizon: str = "next 12 hours",
        current_time: str | None = None,
        verbose: bool = False,
    ) -> WeatherStory:
        """Generate a complete weather story from a Feature Pack.

        Args:
            location: Human-readable location (e.g., "Seattle, WA")
            query: User's original question or intent
            feature_pack: Weather data assembled by orchestrator
            time_horizon: Time span to cover (e.g., "next 12 hours", "today", "tomorrow")
            current_time: ISO timestamp or human-readable time
            verbose: Allow longer responses

        Returns:
            WeatherStory with all narrative sections populated
        """
        if current_time is None:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Build the story prompt
        prompt = STORY_PROMPT_TEMPLATE.format(
            location=location,
            current_time=current_time,
            user_query=query,
            time_horizon=time_horizon,
            feature_pack_json=self._format_feature_pack(feature_pack),
        )

        # Use forecaster to generate the story via AI
        # We use a special intent flag to signal story mode
        response = self.forecaster.generate(
            query=prompt,
            feature_pack=feature_pack,
            intent="storytelling",
            verbose=verbose,
            explain=False,
        )

        # Parse the AI response into a WeatherStory
        return self._parse_story_response(response, location, query)

    def _format_feature_pack(self, feature_pack: dict[str, Any]) -> str:
        """Format Feature Pack for AI consumption."""
        import json

        # Include only relevant fields to keep prompt concise
        relevant_keys = [
            "location",
            "coordinates",
            "current_conditions",
            "forecast",
            "alerts",
            "gridpoint",
            "observations",
            "timezone",
            "timestamp",
        ]

        filtered = {k: v for k, v in feature_pack.items() if k in relevant_keys}
        return json.dumps(filtered, indent=2, default=str)

    def _parse_story_response(
        self, response: ForecasterResponse, location: str, query: str
    ) -> WeatherStory:
        """Parse AI response into WeatherStory structure."""
        import json

        # Try to parse the raw text as JSON (AI should return structured data)
        try:
            # First try to parse raw_text as JSON directly
            story_data = json.loads(response.raw_text)
        except json.JSONDecodeError:
            # Fallback: extract JSON from sections
            story_data = response.sections

        # Extract story components with fallbacks
        setup = story_data.get("setup", "Weather conditions are evolving.")
        current = story_data.get("current", "Current conditions are being analyzed.")
        meteorology = story_data.get(
            "meteorology", "Standard atmospheric processes are at play."
        )
        bottom_line = story_data.get("bottom_line", response.bottom_line or "Stay informed.")

        # Parse timeline
        evolution_data = story_data.get("evolution", {})
        if isinstance(evolution_data, dict):
            phases_raw = evolution_data.get("phases", [])
        else:
            phases_raw = []
        evolution = Timeline.from_raw_phases(phases_raw)

        # Parse decisions
        decisions_raw = story_data.get("decisions", [])
        decisions = [
            Decision(
                activity=d.get("activity", "General"),
                recommendation=d.get("recommendation", "Monitor conditions"),
                reasoning=d.get("reasoning", "Based on current forecast"),
                timing=d.get("timing"),
                confidence=d.get("confidence", 0.7),
            )
            for d in decisions_raw
            if isinstance(d, dict)
        ]

        # Parse confidence
        conf_data = story_data.get("confidence", {})
        if isinstance(conf_data, dict):
            confidence = ConfidenceNote(
                primary_uncertainty=conf_data.get(
                    "primary_uncertainty", "Timing and intensity"
                ),
                alternative_scenarios=conf_data.get("alternative_scenarios", []),
                confidence_level=conf_data.get("confidence_level", "Medium"),
                rationale=conf_data.get("rationale", "Based on model agreement"),
            )
        else:
            confidence = ConfidenceNote(
                primary_uncertainty="Timing and intensity",
                confidence_level="Medium",
                rationale=str(conf_data) if conf_data else "Standard uncertainty",
            )

        return WeatherStory(
            setup=setup,
            current=current,
            evolution=evolution,
            meteorology=meteorology,
            decisions=decisions,
            confidence=confidence,
            bottom_line=bottom_line,
            meta={
                "location": location,
                "query": query,
                "provider": response.provider,
                "used_fields": response.used_feature_fields,
            },
        )
