"""AI forecaster abstraction."""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import httpx

from .config import Settings

try:  # pragma: no cover - optional dependency
    import google.genai as genai  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    genai = None  # type: ignore

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are wx, an expert operational meteorologist providing concise, actionable briefings.
    Follow this contract strictly:
    - Quantify uncertainty and avoid sensational language.
    - Use both local and UTC times when possible.
    - Never fabricate specific values; rely on provided Feature Pack or clearly state limitations.
    - Reference which Feature Pack fields you used.
    - Output JSON matching the schema discussed below.

    Response schema (JSON object):
    {
      "sections": {
        "summary": ["2-4 sentences"],
        "timeline": ["Bullet timeline items with local and UTC times"],
        "risk_cards": [
          {
            "hazard": "Severe|Flooding|Winter|Wind|Heat|Cold|Fire|Aviation",
            "level": "Low|Moderate|High",
            "drivers": ["key drivers"],
            "confidence": "short rationale"
          }
        ],
        "confidence": "Explain uncertainties and what could change.",
        "actions": ["Actionable advice tied to user context"],
        "assumptions": ["Key assumptions you made"]
      },
      "confidence": {"value": 0-100, "rationale": "One-line confidence summary"},
      "used_feature_fields": ["list of Feature Pack keys you relied on"],
      "bottom_line": "Single sentence takeaway"
    }

    Keep output \u2264 400 words unless explicitly told verbose. If information is missing,
    speak qualitatively and acknowledge the gap. If explain_mode is true, focus on
    clarifying which inputs drove the previous answer and why confidence is set.
    """
).strip()


@dataclass(slots=True)
class ForecasterResponse:
    """Standardised forecaster output."""

    sections: Dict[str, Any]
    confidence: Dict[str, Any]
    used_feature_fields: List[str]
    bottom_line: str
    raw_text: str
    provider: str
    prompt_summary: str

    @property
    def summary_text(self) -> str:
        if isinstance(self.sections.get("summary"), list):
            return " ".join(self.sections["summary"])
        return str(self.sections.get("summary", ""))


class Forecaster:
    """Dispatch AI requests via OpenRouter (Grok/ChatGPT OSS) with Gemini fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._gemini_client: Any | None = None

    def generate(
        self,
        *,
        query: str,
        feature_pack: Dict[str, Any],
        intent: str,
        verbose: bool,
        explain: bool = False,
    ) -> ForecasterResponse:
        prompt_summary = self._compose_prompt_summary(query, intent, verbose, explain)
        payload = {
            "intent": intent,
            "style": self.settings.style,
            "persona": self.settings.persona,
            "verbose": verbose,
            "explain_mode": explain,
            "feature_pack": feature_pack,
            "query": query,
        }

        if self.settings.offline:
            return self._fallback_response(payload, provider="offline", prompt_summary=prompt_summary)

        try:
            raw, provider = self._invoke_provider(payload)
            return self._parse_response(raw, prompt_summary, provider)
        except Exception as exc:  # noqa: BLE001
            return self._fallback_response(
                payload,
                provider=f"fallback:{exc.__class__.__name__}",
                prompt_summary=prompt_summary,
                raw_text=str(exc),
            )

    def _invoke_provider(self, payload: Dict[str, Any]) -> Tuple[str, str]:
        errors: List[str] = []
        prompt = self._build_prompt(payload)

        if self.settings.openrouter_api_key and self.settings.openrouter_models:
            try:
                result = self._call_openrouter(prompt)
                if result:
                    return result
                errors.append("openrouter:no-response")
            except RuntimeError as exc:
                errors.append(f"openrouter:{exc}")

        if self.settings.gemini_api_key:
            try:
                text = self._call_gemini(prompt)
                if text:
                    return text, "gemini"
                errors.append("gemini:no-response")
            except RuntimeError as exc:
                errors.append(f"gemini:{exc}")

        reason = "; ".join(errors) if errors else "no-provider-configured"
        raise RuntimeError(reason)

    def _call_openrouter(self, prompt: str) -> Tuple[str, str] | None:
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Exvin2/claudex-cli",
            "X-Title": "wx CLI",
        }

        for model in self.settings.openrouter_models:
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": self.settings.ai_temperature,
                "max_tokens": self.settings.ai_max_tokens,
            }
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        self.settings.openrouter_base_url,
                        json=data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    payload = response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {401, 403}:
                    raise RuntimeError(f"auth-{status}") from exc
                continue
            except httpx.HTTPError:
                continue

            choice = (payload.get("choices") or [{}])[0]
            message = choice.get("message", {})
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            if isinstance(content, str) and content.strip():
                return content.strip(), f"openrouter:{model}"

        return None

    def _call_gemini(self, prompt: str) -> str | None:
        if genai is None:
            raise RuntimeError("google-genai-not-installed")
        if not self.settings.gemini_api_key:
            raise RuntimeError("gemini-key-missing")

        if self._gemini_client is None:
            try:
                self._gemini_client = genai.Client(api_key=self.settings.gemini_api_key)
            except Exception as exc:  # pragma: no cover - defensive
                raise RuntimeError(f"gemini-client:{exc}") from exc

        try:
            response = self._gemini_client.models.generate_content(
                model=self.settings.gemini_model,
                contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"gemini-call:{exc}") from exc

        text = getattr(response, "text", None)
        return text.strip() if isinstance(text, str) else None

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        content = textwrap.dedent(
            f"""
            You are to answer as wx.
            Query: {payload['query']}
            Intent: {payload['intent']}
            Style: {self.settings.style}
            Persona: {self.settings.persona}
            Verbose: {payload['verbose']}
            Explain mode: {payload['explain_mode']}
            Feature Pack JSON:
            {json.dumps(payload['feature_pack'], ensure_ascii=True, indent=2)}
            """
        ).strip()
        instructions = (
            "Focus on explaining feature usage and confidence rationale."
            if payload["explain_mode"]
            else "Provide a meteorological briefing."
        )
        return f"{content}\nAdditional instructions: {instructions}"

    def _parse_response(self, raw_text: str, prompt_summary: str, provider: str) -> ForecasterResponse:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = self._strip_fence(cleaned)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return self._fallback_response(
                {"feature_pack": {}, "intent": "parse_error"},
                provider="fallback:unparseable",
                prompt_summary=prompt_summary,
                raw_text=raw_text,
            )

        sections = data.get("sections") or {}
        confidence = data.get("confidence") or {"value": 30, "rationale": "Model confidence not supplied."}
        used_fields = data.get("used_feature_fields") or []
        bottom_line = data.get("bottom_line") or "No bottom line provided."
        return ForecasterResponse(
            sections=sections,
            confidence=confidence,
            used_feature_fields=used_fields if isinstance(used_fields, list) else [],
            bottom_line=bottom_line,
            raw_text=raw_text,
            provider=provider,
            prompt_summary=prompt_summary,
        )

    def _fallback_response(
        self,
        payload: Dict[str, Any],
        *,
        provider: str,
        prompt_summary: str,
        raw_text: str | None = None,
    ) -> ForecasterResponse:
        feature_pack = payload.get("feature_pack") or {}
        used_fields = self._enumerate_feature_fields(feature_pack)
        summary = [
            "wx is operating with limited connectivity and cannot reach AI services.",
            "Responding with a conservative qualitative outlook based on provided context only.",
        ]
        if payload.get("explain_mode"):
            summary = [
                "Explain mode: describing which Feature Pack inputs were available and how they would influence a forecast.",
            ]
        sections = {
            "summary": summary,
            "timeline": ["No timeline available without model output."],
            "risk_cards": [
                {
                    "hazard": "General",
                    "level": "Low",
                    "drivers": ["Insufficient data; AI model unavailable"],
                    "confidence": "Low confidence; qualitative placeholder.",
                }
            ],
            "confidence": "Confidence limited by offline mode or missing API keys.",
            "actions": [
                "Monitor trusted weather sources and official alerts.",
                "Re-run wx with API keys configured for a richer briefing.",
            ],
            "assumptions": [
                "Feature Pack fields used: " + (", ".join(used_fields) if used_fields else "none supplied"),
            ],
        }
        confidence = {"value": 25, "rationale": "Offline fallback."}
        bottom_line = "Bottom line: wx requires an AI provider configured to deliver a full forecast."
        return ForecasterResponse(
            sections=sections,
            confidence=confidence,
            used_feature_fields=used_fields,
            bottom_line=bottom_line,
            raw_text=raw_text or json.dumps(sections, ensure_ascii=True),
            provider=provider,
            prompt_summary=prompt_summary,
        )

    def _compose_prompt_summary(self, query: str, intent: str, verbose: bool, explain: bool) -> str:
        parts = [intent, query]
        if verbose:
            parts.append("verbose")
        if explain:
            parts.append("explain")
        return " | ".join(parts)

    def _enumerate_feature_fields(self, feature_pack: Dict[str, Any]) -> List[str]:
        keys: List[str] = []
        for key, value in feature_pack.items():
            if value in (None, [], {}):
                continue
            if key == "units":
                keys.append("units")
            elif isinstance(value, dict):
                keys.extend(f"{key}.{inner}" for inner in value.keys())
            else:
                keys.append(key)
        return sorted(set(keys))

    def _strip_fence(self, text: str) -> str:
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)
