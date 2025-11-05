"""Core orchestration logic for wx commands."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from dateutil import parser as date_parser

from .config import REGIONAL_SAMPLES, Settings
from .fetchers import (
    Alert,
    FetchResult,
    Observation,
    fetch_eu_alerts,
    fetch_openmeteo_points,
    fetch_us_alerts,
    get_point_context,
    get_quick_alerts,
    get_quick_obs,
    get_quick_profile,
)
from .forecaster import Forecaster, ForecasterResponse
from .storyteller import Storyteller, WeatherStory


@dataclass(slots=True)
class OrchestrationResult:
    """Outcome of a single CLI invocation."""

    command: str
    query: str
    feature_pack: dict[str, Any]
    response: ForecasterResponse
    timings: dict[str, float]
    debug: dict[str, Any]


@dataclass(slots=True)
class ExplainResult:
    """Normalised output for explain invocations."""

    command: str
    question: str
    mode: str
    text: str
    meta: dict[str, Any]
    response: ForecasterResponse
    feature_pack: dict[str, Any]


@dataclass(slots=True)
class StoryResult:
    """Result of a story generation."""

    story: WeatherStory
    timings: dict[str, float]
    debug: dict[str, Any]
    feature_pack: dict[str, Any]


@dataclass(slots=True)
class RegionStats:
    """Aggregated statistics for a region."""

    tmin: float | None
    tmax: float | None
    pop_max: float | None
    wind_max: float | None
    gust_max: float | None


@dataclass(slots=True)
class RegionView:
    """Weather summary for a region."""

    name: str
    summary: str
    stats: RegionStats
    alerts: list[dict[str, Any]]


@dataclass(slots=True)
class Worldview:
    """Aggregate view of US + Europe weather."""

    regions: list[RegionView]
    meta: dict[str, Any]


def _unit_pack(units: str) -> dict[str, str]:
    if units == "metric":
        return {"temp": "C", "wind": "mps", "precip": "mm"}
    return {"temp": "F", "wind": "mph", "precip": "in"}


class Orchestrator:
    """Build Feature Packs and invoke the AI forecaster."""

    def __init__(self, settings: Settings, *, trust_tools: bool = False) -> None:
        self.settings = settings
        self.trust_tools = trust_tools
        self.forecaster = Forecaster(settings)
        self.storyteller = Storyteller(settings)

    def handle_question(self, question: str, *, verbose: bool) -> OrchestrationResult:
        feature_pack = self._base_feature_pack()
        timings: dict[str, float] = {}
        debug_info = {"fetchers": []}

        response = self.forecaster.generate(
            query=question,
            feature_pack=feature_pack,
            intent="question",
            verbose=verbose,
        )

        self._persist_state(command="question", query=question, feature_pack=feature_pack)
        return OrchestrationResult(
            command="question",
            query=question,
            feature_pack=feature_pack,
            response=response,
            timings=timings,
            debug=debug_info,
        )

    def handle_forecast(
        self,
        place: str,
        *,
        when_text: str | None,
        horizon: str,
        focus: str | None,
        verbose: bool,
    ) -> OrchestrationResult:
        timings: dict[str, float] = {}
        debug_info: dict[str, Any] = {"fetchers": []}

        feature_pack = self._base_feature_pack()
        place_info = self._maybe_fetch(
            "point_context",
            lambda: get_point_context(place, offline=self.settings.offline),
            timings,
            debug_info,
        )
        if place_info:
            feature_pack["place"] = place_info
        window = self._build_window(place_info, when_text, horizon)
        if window:
            feature_pack["window"] = window

        if place_info:
            lat = place_info.get("lat")
            lon = place_info.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and self.trust_tools:
                obs = self._maybe_fetch(
                    "quick_obs",
                    lambda: get_quick_obs(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if obs:
                    feature_pack["obs_quick"] = obs
                profile = self._maybe_fetch(
                    "quick_profile",
                    lambda: get_quick_profile(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if profile:
                    feature_pack["profile_quick"] = profile
                alerts = self._maybe_fetch(
                    "quick_alerts",
                    lambda: get_quick_alerts(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if alerts:
                    feature_pack["alerts_quick"] = alerts

        user_context: dict[str, Any] = {"use_case": "forecast"}
        if focus:
            user_context["constraints"] = [f"focus:{focus}"]
        if verbose:
            user_context["constraints"] = (user_context.get("constraints") or []) + ["verbose"]
        if user_context:
            feature_pack["user_context"] = user_context

        response = self.forecaster.generate(
            query=self._compose_forecast_query(place, when_text, horizon, focus),
            feature_pack=feature_pack,
            intent="forecast",
            verbose=verbose,
        )

        self._persist_state(
            command="forecast",
            query=response.prompt_summary,
            feature_pack=feature_pack,
        )
        return OrchestrationResult(
            command="forecast",
            query=place,
            feature_pack=feature_pack,
            response=response,
            timings=timings,
            debug=debug_info,
        )

    def handle_risk(
        self,
        place: str,
        *,
        hazards: Iterable[str] | None,
        verbose: bool,
    ) -> OrchestrationResult:
        timings: dict[str, float] = {}
        debug_info = {"fetchers": []}

        feature_pack = self._base_feature_pack()
        place_info = self._maybe_fetch(
            "point_context",
            lambda: get_point_context(place, offline=self.settings.offline),
            timings,
            debug_info,
        )
        if place_info:
            feature_pack["place"] = place_info
        if place_info and self.trust_tools:
            lat = place_info.get("lat")
            lon = place_info.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                alerts = self._maybe_fetch(
                    "quick_alerts",
                    lambda: get_quick_alerts(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if alerts:
                    feature_pack["alerts_quick"] = alerts
        if hazards:
            feature_pack.setdefault("user_context", {})["constraints"] = [
                f"hazards:{','.join(hazards)}"
            ]

        response = self.forecaster.generate(
            query=self._compose_risk_query(place, hazards),
            feature_pack=feature_pack,
            intent="risk",
            verbose=verbose,
        )

        self._persist_state(
            command="risk",
            query=response.prompt_summary,
            feature_pack=feature_pack,
        )
        return OrchestrationResult(
            command="risk",
            query=place,
            feature_pack=feature_pack,
            response=response,
            timings=timings,
            debug=debug_info,
        )

    def handle_alerts(
        self,
        place: str,
        *,
        ai: bool,
        stream: bool,
        verbose: bool,
    ) -> OrchestrationResult:
        timings: dict[str, float] = {}
        debug_info = {"fetchers": []}

        feature_pack = self._base_feature_pack()
        place_info = self._maybe_fetch(
            "point_context",
            lambda: get_point_context(place, offline=self.settings.offline),
            timings,
            debug_info,
        )
        if place_info:
            feature_pack["place"] = place_info

        alerts: list[dict[str, Any]] = []
        if place_info:
            lat = place_info.get("lat")
            lon = place_info.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                alerts = (
                    self._maybe_fetch(
                        "quick_alerts",
                        lambda: get_quick_alerts(lat, lon, offline=self.settings.offline),
                        timings,
                        debug_info,
                    )
                    or []
                )
        if alerts:
            feature_pack["alerts_quick"] = alerts

        if stream:
            debug_info["stream"] = False  # streaming not yet supported

        if ai and alerts:
            response = self.forecaster.generate(
                query=f"Alert triage for {place}.",
                feature_pack=feature_pack,
                intent="alerts",
                verbose=verbose,
            )
        else:
            response = self._alerts_response(place, alerts)

        return OrchestrationResult(
            command="alerts",
            query=place,
            feature_pack=feature_pack,
            response=response,
            timings=timings,
            debug=debug_info,
        )

    def handle_explain(self) -> ExplainResult:
        saved = self.settings.load_last_query()
        if not saved:
            raise RuntimeError("No prior query available. Disable privacy mode to enable explain.")

        feature_pack = saved.get("feature_pack") or {}
        command = saved.get("command", "question")
        question = saved.get("question", "Explain the last forecast")

        explain_payload = self.forecaster.explain(
            question=question,
            feature_pack=feature_pack,
            command=command,
        )

        if not isinstance(explain_payload, dict):
            raise RuntimeError("Explain payload malformed")

        response = explain_payload.get("response")
        if not isinstance(response, ForecasterResponse):
            response = self.forecaster._fallback_response(  # noqa: SLF001 - controlled internal call
                {"feature_pack": feature_pack},
                provider="fallback:explain",
                prompt_summary=f"explain:{command}",
                meta={"error": "invalid-response"},
            )

        mode = explain_payload.get("mode", "fallback")
        meta = explain_payload.get("meta")
        if not isinstance(meta, dict):
            meta = {"provider": response.provider}
        text = explain_payload.get("text") or response.summary_text or response.bottom_line

        return ExplainResult(
            command=command,
            question=question,
            mode=mode,
            text=text,
            meta=meta,
            response=response,
            feature_pack=feature_pack,
        )

    def handle_story(
        self,
        place: str,
        *,
        when_text: str | None = None,
        horizon: str = "12h",
        focus: str | None = None,
        verbose: bool = False,
    ) -> StoryResult:
        """Generate a narrative weather story for a location.

        Args:
            place: Location name or coordinates
            when_text: Optional time reference (e.g., "tomorrow", "tonight")
            horizon: Time span to cover (default: "12h")
            focus: Optional focus area (e.g., "commuting", "outdoor activities")
            verbose: Allow longer, more detailed stories

        Returns:
            StoryResult with the generated weather narrative
        """
        timings: dict[str, float] = {}
        debug_info: dict[str, Any] = {"fetchers": []}

        # Build feature pack with location context
        feature_pack = self._base_feature_pack()
        place_info = self._maybe_fetch(
            "point_context",
            lambda: get_point_context(place, offline=self.settings.offline),
            timings,
            debug_info,
        )
        if place_info:
            feature_pack["place"] = place_info

        # Build time window
        window = self._build_window(place_info, when_text, horizon)
        if window:
            feature_pack["window"] = window

        # Fetch comprehensive weather data if trust_tools enabled
        if place_info and self.trust_tools:
            lat = place_info.get("lat")
            lon = place_info.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                # Fetch observations, forecast, and alerts
                obs = self._maybe_fetch(
                    "quick_obs",
                    lambda: get_quick_obs(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if obs:
                    feature_pack["obs_quick"] = obs

                profile = self._maybe_fetch(
                    "quick_profile",
                    lambda: get_quick_profile(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if profile:
                    feature_pack["profile_quick"] = profile

                alerts = self._maybe_fetch(
                    "quick_alerts",
                    lambda: get_quick_alerts(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                )
                if alerts:
                    feature_pack["alerts_quick"] = alerts

        # Build user query
        query_parts = [f"Weather story for {place}"]
        if when_text:
            query_parts.append(f"starting {when_text}")
        if focus:
            query_parts.append(f"focused on {focus}")
        user_query = " ".join(query_parts)

        # Determine time horizon in human-readable form
        horizon_map = {
            "6h": "next 6 hours",
            "12h": "next 12 hours",
            "24h": "today",
            "3d": "next 3 days",
        }
        time_horizon = horizon_map.get(horizon.lower(), "next 12 hours")

        # Generate the story
        start_time = time.perf_counter()
        story = self.storyteller.generate_story(
            location=place,
            query=user_query,
            feature_pack=feature_pack,
            time_horizon=time_horizon,
            current_time=window.get("start_local") if window else None,
            verbose=verbose,
        )
        timings["story_generation"] = time.perf_counter() - start_time

        # Persist state for explain mode
        self._persist_state(
            command="story",
            query=user_query,
            feature_pack=feature_pack,
        )

        return StoryResult(
            story=story,
            timings=timings,
            debug=debug_info,
            feature_pack=feature_pack,
        )

    def _base_feature_pack(self) -> dict[str, Any]:
        return {"units": _unit_pack(self.settings.units)}

    def _build_window(
        self,
        place_info: dict[str, Any] | None,
        when_text: str | None,
        horizon: str,
    ) -> dict[str, Any] | None:
        horizon_hours = self._parse_horizon(horizon)
        tz_name = (place_info or {}).get("tz")
        now_utc = datetime.now(UTC)
        start = now_utc
        if when_text:
            parsed = self._safe_parse_time(when_text, tz_name)
            if parsed:
                start = parsed.astimezone(UTC)
        end = start + timedelta(hours=horizon_hours)

        # Include both UTC and local timezone information
        window = {
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "horizon": f"{horizon_hours}h",
        }

        # Add local timezone information if available
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                local_tz = ZoneInfo(tz_name)
                start_local = start.astimezone(local_tz)
                end_local = end.astimezone(local_tz)
                window["start_local"] = start_local.isoformat()
                window["end_local"] = end_local.isoformat()
                window["timezone"] = tz_name
            except Exception:  # noqa: BLE001
                # If timezone conversion fails, just use UTC
                pass

        return window

    def _parse_horizon(self, horizon: str) -> int:
        mapping = {"6h": 6, "12h": 12, "24h": 24, "3d": 72}
        return mapping.get(horizon.lower(), 24)

    def _safe_parse_time(self, when_text: str, tz_name: str | None) -> datetime | None:
        try:
            parsed = date_parser.parse(when_text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        except (ValueError, TypeError, OverflowError):
            return None

    def _compose_forecast_query(
        self, place: str, when_text: str | None, horizon: str, focus: str | None
    ) -> str:
        parts = [f"Forecast request for {place}"]
        if when_text:
            parts.append(f"window hint: {when_text}")
        parts.append(f"horizon: {horizon}")
        if focus:
            parts.append(f"focus: {focus}")
        return "; ".join(parts)

    def _compose_risk_query(self, place: str, hazards: Iterable[str] | None) -> str:
        if hazards:
            hazard_text = ",".join(sorted(set(hazards)))
            return f"Risk assessment for {place}: hazards={hazard_text}"
        return f"Risk assessment for {place}"

    def _maybe_fetch(
        self,
        name: str,
        func,
        timings: dict[str, float],
        debug_info: dict[str, Any],
    ) -> Any:
        start = time.perf_counter()
        try:
            result = func()
            succeeded = result not in (None, [], {})
            detail = None
        except Exception as exc:  # noqa: BLE001
            result = None
            succeeded = False
            detail = str(exc)
        elapsed = time.perf_counter() - start
        timings[name] = elapsed
        debug_info.setdefault("fetchers", []).append(
            asdict(FetchResult(name=name, elapsed=elapsed, succeeded=succeeded, detail=detail))
        )
        return result

    def _persist_state(self, *, command: str, query: str, feature_pack: dict[str, Any]) -> None:
        payload = {
            "command": command,
            "question": query,
            "feature_pack": feature_pack,
            "style": self.settings.style,
            "persona": self.settings.persona,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.settings.save_last_query(payload)

    def _alerts_response(self, place: str, alerts: Iterable[dict[str, Any]]) -> ForecasterResponse:
        records = list(alerts)
        if not records:
            sections = {
                "summary": [f"No active alerts found for {place} at this time."],
                "timeline": ["No urgent alerts."],
                "risk_cards": [],
                "confidence": "Based on NOAA live feed availability.",
                "actions": ["Monitor official channels for updates."],
                "assumptions": ["No AI triage performed."],
            }
        else:
            summary_lines = [f"{len(records)} active alerts near {place}."]
            timeline = [
                f"{record.get('event', 'Alert')} expires {record.get('expires_iso', 'unknown')}"
                for record in records
            ]
            risk_cards = [
                {
                    "hazard": record.get("event", "Alert"),
                    "level": record.get("severity", "Unknown"),
                    "drivers": ["Official alert headline"],
                    "confidence": "Official source",
                }
                for record in records
            ]
            sections = {
                "summary": summary_lines,
                "timeline": timeline,
                "risk_cards": risk_cards,
                "confidence": "Reporting official alerts without AI triage.",
                "actions": ["Review alert details and follow guidance."],
                "assumptions": ["Alerts feed is up to date."],
            }

        return ForecasterResponse(
            sections=sections,
            confidence={"value": 60 if records else 40, "rationale": "Derived from alert feed."},
            used_feature_fields=["alerts_quick"] if records else [],
            bottom_line=(
                "Bottom line: monitor these alerts."
                if records
                else "Bottom line: no alerts currently active."
            ),
            raw_text=json.dumps(sections, ensure_ascii=True),
            provider="alerts-manual",
            prompt_summary=f"alerts | {place}",
            meta={"records": len(records)},
        )

    def handle_worldview(self, *, verbose: bool = False, severe_only: bool = False) -> Worldview:
        """Fetch and aggregate US + Europe weather overview."""
        start_time = time.perf_counter()

        if self.settings.offline:
            return self._synthetic_worldview(severe_only=severe_only)

        # Fetch all data in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            us_obs_future = executor.submit(
                fetch_openmeteo_points,
                REGIONAL_SAMPLES["us"],
                offline=self.settings.offline,
            )
            eu_obs_future = executor.submit(
                fetch_openmeteo_points,
                REGIONAL_SAMPLES["eu"],
                offline=self.settings.offline,
            )
            us_alerts_future = executor.submit(
                fetch_us_alerts,
                offline=self.settings.offline,
                severe_only=severe_only,
            )
            eu_alerts_future = executor.submit(
                fetch_eu_alerts,
                offline=self.settings.offline,
                severe_only=severe_only,
            )

            us_obs = us_obs_future.result()
            eu_obs = eu_obs_future.result()
            us_alerts = us_alerts_future.result()
            eu_alerts = eu_alerts_future.result()

        # Compute region stats
        us_stats = self._compute_region_stats(us_obs)
        eu_stats = self._compute_region_stats(eu_obs)

        # Generate summaries
        us_summary = self._generate_region_summary("US", us_obs, us_alerts)
        eu_summary = self._generate_region_summary("Europe", eu_obs, eu_alerts)

        # Prepare alert summaries
        us_alert_summary = self._summarize_alerts(us_alerts)
        eu_alert_summary = self._summarize_alerts(eu_alerts)

        elapsed = time.perf_counter() - start_time

        return Worldview(
            regions=[
                RegionView(
                    name="US",
                    summary=us_summary,
                    stats=us_stats,
                    alerts=us_alert_summary,
                ),
                RegionView(
                    name="Europe",
                    summary=eu_summary,
                    stats=eu_stats,
                    alerts=eu_alert_summary,
                ),
            ],
            meta={
                "samples_us": len(us_obs),
                "samples_eu": len(eu_obs),
                "fetch_ms": round(elapsed * 1000),
                "sources": ["Open-Meteo", "NWS CAP", "MeteoAlarm"],
                "severe_only": severe_only,
            },
        )

    def _synthetic_worldview(self, severe_only: bool = False) -> Worldview:
        """Return deterministic synthetic data for offline mode."""
        if severe_only:
            # Severe weather only: floods, tornadoes, severe thunderstorms
            us_alerts = [
                {"event": "Tornado Warning", "count": 2, "areas": ["Oklahoma", "Kansas"]},
                {"event": "Flash Flood Warning", "count": 3, "areas": ["Texas", "Louisiana"]},
                {"event": "Severe Thunderstorm Warning", "count": 5, "areas": ["Nebraska", "Iowa"]},
            ]
            eu_alerts = [
                {"event": "Flood Warning", "count": 1, "areas": ["Netherlands"]},
            ]
            sources = ["Offline synthetic data (severe weather only)"]
        else:
            us_alerts = [
                {"event": "Heat Advisory", "count": 3, "areas": ["Texas", "Arizona", "New Mexico"]},
            ]
            eu_alerts = [
                {"event": "Wind Warning", "count": 2, "areas": ["UK", "Netherlands"]},
            ]
            sources = ["Offline synthetic data"]

        return Worldview(
            regions=[
                RegionView(
                    name="US",
                    summary="Varied conditions coast to coast; warm South, cooler North",
                    stats=RegionStats(tmin=45.0, tmax=85.0, pop_max=40.0, wind_max=15.0, gust_max=25.0),
                    alerts=us_alerts,
                ),
                RegionView(
                    name="Europe",
                    summary="Mixed weather across continent; wet northwest, dry south",
                    stats=RegionStats(tmin=10.0, tmax=25.0, pop_max=60.0, wind_max=20.0, gust_max=35.0),
                    alerts=eu_alerts,
                ),
            ],
            meta={
                "samples_us": 0,
                "samples_eu": 0,
                "fetch_ms": 0,
                "sources": sources,
                "severe_only": severe_only,
            },
        )

    def _compute_region_stats(self, observations: list[Observation]) -> RegionStats:
        """Compute aggregate statistics from observations."""
        if not observations:
            return RegionStats(tmin=None, tmax=None, pop_max=None, wind_max=None, gust_max=None)

        temps = [obs.temp for obs in observations if obs.temp is not None]
        precip_probs = [obs.precip_prob for obs in observations if obs.precip_prob is not None]
        winds = [obs.wind for obs in observations if obs.wind is not None]
        gusts = [obs.gust for obs in observations if obs.gust is not None]

        return RegionStats(
            tmin=min(temps) if temps else None,
            tmax=max(temps) if temps else None,
            pop_max=max(precip_probs) if precip_probs else None,
            wind_max=max(winds) if winds else None,
            gust_max=max(gusts) if gusts else None,
        )

    def _generate_region_summary(
        self, region: str, observations: list[Observation], alerts: list[Alert]
    ) -> str:
        """Generate a concise text summary for a region."""
        if not observations:
            return f"No data available for {region}."

        stats = self._compute_region_stats(observations)
        parts = []

        if stats.tmin is not None and stats.tmax is not None:
            parts.append(f"Temps {int(stats.tmin)}–{int(stats.tmax)}°")

        if stats.pop_max and stats.pop_max > 30:
            parts.append(f"precip chance up to {int(stats.pop_max)}%")

        if stats.wind_max and stats.wind_max > 10:
            parts.append(f"winds to {int(stats.wind_max)} m/s")

        if alerts:
            parts.append(f"{len(alerts)} active alerts")

        return "; ".join(parts) if parts else "Conditions variable"

    def _summarize_alerts(self, alerts: list[Alert]) -> list[dict[str, Any]]:
        """Group and summarize alerts by event type."""
        if not alerts:
            return []

        # Group by event
        grouped: dict[str, dict[str, Any]] = {}
        for alert in alerts:
            event = alert.event
            if event not in grouped:
                grouped[event] = {"event": event, "count": 0, "areas": set()}
            grouped[event]["count"] += 1
            grouped[event]["areas"].update(alert.areas[:2])  # Limit areas

        # Convert to list and format
        result = []
        for data in grouped.values():
            result.append(
                {
                    "event": data["event"],
                    "count": data["count"],
                    "areas": sorted(list(data["areas"]))[:5],  # Top 5 areas
                }
            )

        return sorted(result, key=lambda x: x["count"], reverse=True)[:5]  # Top 5 events
