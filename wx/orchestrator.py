"""Core orchestration logic for wx commands."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable

from dateutil import parser as date_parser

from .config import Settings
from .fetchers import (
    FetchResult,
    get_point_context,
    get_quick_alerts,
    get_quick_obs,
    get_quick_profile,
)
from .forecaster import Forecaster, ForecasterResponse


@dataclass(slots=True)
class OrchestrationResult:
    """Outcome of a single CLI invocation."""

    command: str
    query: str
    feature_pack: Dict[str, Any]
    response: ForecasterResponse
    timings: Dict[str, float]
    debug: Dict[str, Any]


def _unit_pack(units: str) -> Dict[str, str]:
    if units == "metric":
        return {"temp": "C", "wind": "mps", "precip": "mm"}
    return {"temp": "F", "wind": "mph", "precip": "in"}


class Orchestrator:
    """Build Feature Packs and invoke the AI forecaster."""

    def __init__(self, settings: Settings, *, trust_tools: bool = False) -> None:
        self.settings = settings
        self.trust_tools = trust_tools
        self.forecaster = Forecaster(settings)

    def handle_question(self, question: str, *, verbose: bool) -> OrchestrationResult:
        feature_pack = self._base_feature_pack()
        timings: Dict[str, float] = {}
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
        timings: Dict[str, float] = {}
        debug_info: Dict[str, Any] = {"fetchers": []}

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

        user_context: Dict[str, Any] = {"use_case": "forecast"}
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
        timings: Dict[str, float] = {}
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
            feature_pack.setdefault("user_context", {})["constraints"] = [f"hazards:{','.join(hazards)}"]

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
        timings: Dict[str, float] = {}
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

        alerts: list[Dict[str, Any]] = []
        if place_info:
            lat = place_info.get("lat")
            lon = place_info.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                alerts = self._maybe_fetch(
                    "quick_alerts",
                    lambda: get_quick_alerts(lat, lon, offline=self.settings.offline),
                    timings,
                    debug_info,
                ) or []
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

    def handle_explain(self) -> OrchestrationResult:
        saved = self.settings.load_last_query()
        if not saved:
            raise RuntimeError("No prior query available. Disable privacy mode to enable explain.")

        feature_pack = saved.get("feature_pack") or {}
        command = saved.get("command", "question")
        question = saved.get("question", "Explain the last forecast")

        response = self.forecaster.generate(
            query=question,
            feature_pack=feature_pack,
            intent=f"explain:{command}",
            verbose=True,
            explain=True,
        )

        return OrchestrationResult(
            command="explain",
            query=question,
            feature_pack=feature_pack,
            response=response,
            timings={},
            debug={"source": "saved"},
        )

    def _base_feature_pack(self) -> Dict[str, Any]:
        return {"units": _unit_pack(self.settings.units)}

    def _build_window(
        self,
        place_info: Dict[str, Any] | None,
        when_text: str | None,
        horizon: str,
    ) -> Dict[str, Any] | None:
        horizon_hours = self._parse_horizon(horizon)
        tz_name = (place_info or {}).get("tz")
        now_utc = datetime.now(timezone.utc)
        start = now_utc
        if when_text:
            parsed = self._safe_parse_time(when_text, tz_name)
            if parsed:
                start = parsed.astimezone(timezone.utc)
        end = start + timedelta(hours=horizon_hours)
        return {
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "horizon": f"{horizon_hours}h",
        }

    def _parse_horizon(self, horizon: str) -> int:
        mapping = {"6h": 6, "12h": 12, "24h": 24, "3d": 72}
        return mapping.get(horizon.lower(), 24)

    def _safe_parse_time(self, when_text: str, tz_name: str | None) -> datetime | None:
        try:
            parsed = date_parser.parse(when_text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError, OverflowError):
            return None

    def _compose_forecast_query(self, place: str, when_text: str | None, horizon: str, focus: str | None) -> str:
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
        timings: Dict[str, float],
        debug_info: Dict[str, Any],
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

    def _persist_state(self, *, command: str, query: str, feature_pack: Dict[str, Any]) -> None:
        payload = {
            "command": command,
            "question": query,
            "feature_pack": feature_pack,
            "style": self.settings.style,
            "persona": self.settings.persona,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.settings.save_last_query(payload)

    def _alerts_response(self, place: str, alerts: Iterable[Dict[str, Any]]) -> ForecasterResponse:
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
                "Bottom line: monitor these alerts." if records else "Bottom line: no alerts currently active."
            ),
            raw_text=json.dumps(sections, ensure_ascii=True),
            provider="alerts-manual",
            prompt_summary=f"alerts | {place}",
        )
