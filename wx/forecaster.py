"""AI forecaster abstraction."""

from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass
from typing import Any

from .config import DEFAULT_OPENROUTER_BASE_URL, DEFAULT_OPENROUTER_MODELS, Settings
from .openrouter_client import OpenRouterConfig, OpenRouterError, chat_completion

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


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ForecasterResponse:
    """Standardised forecaster output."""

    sections: dict[str, Any]
    confidence: dict[str, Any]
    used_feature_fields: list[str]
    bottom_line: str
    raw_text: str
    provider: str
    prompt_summary: str
    meta: dict[str, Any] | None = None

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
        self._warned_missing_openrouter_key = False

    def generate(
        self,
        *,
        query: str,
        feature_pack: dict[str, Any],
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
            return self._fallback_response(
                payload, provider="offline", prompt_summary=prompt_summary
            )

        try:
            raw, provider, meta = self._invoke_provider(payload)
            return self._parse_response(raw, prompt_summary, provider, meta)
        except Exception as exc:  # noqa: BLE001
            return self._fallback_response(
                payload,
                provider=f"fallback:{exc.__class__.__name__}",
                prompt_summary=prompt_summary,
                raw_text=str(exc),
                meta={"error": str(exc)},
            )

    def _invoke_provider(self, payload: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None]:
        errors: list[str] = []
        prompt = self._build_prompt(payload)

        config = self._build_openrouter_config()
        if config:
            try:
                response = chat_completion(
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    config=config,
                )
                meta: dict[str, Any] = {
                    "model": response.model,
                    "usage": response.usage,
                    "attempts": response.attempts,
                    "headers": dict(response.headers),
                }
                return response.text, f"openrouter:{response.model}", meta
            except OpenRouterError as exc:
                errors.append(f"openrouter:{exc}")

        if self.settings.gemini_api_key:
            try:
                text = self._call_gemini(prompt)
                if text:
                    meta = {"model": self.settings.gemini_model}
                    return text, "gemini", meta
                errors.append("gemini:no-response")
            except RuntimeError as exc:
                errors.append(f"gemini:{exc}")

        reason = "; ".join(errors) if errors else "no-provider-configured"
        raise RuntimeError(reason)

    def _build_openrouter_config(self) -> OpenRouterConfig | None:
        api_key = self.settings.openrouter_api_key
        if not api_key:
            if not self._warned_missing_openrouter_key:
                logger.warning("OPENROUTER_API_KEY not configured; using offline fallback.")
                self._warned_missing_openrouter_key = True
            return None

        models = self.settings.openrouter_models or DEFAULT_OPENROUTER_MODELS
        model = models[0]
        base_url = self.settings.openrouter_base_url or DEFAULT_OPENROUTER_BASE_URL

        return OpenRouterConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=self.settings.ai_temperature,
            max_tokens=self.settings.ai_max_tokens,
        )

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

    def _build_prompt(self, payload: dict[str, Any]) -> str:
        content = textwrap.dedent(
            f"""
            You are to answer as wx.
            Query: {payload["query"]}
            Intent: {payload["intent"]}
            Style: {self.settings.style}
            Persona: {self.settings.persona}
            Verbose: {payload["verbose"]}
            Explain mode: {payload["explain_mode"]}
            Feature Pack JSON:
            {json.dumps(payload["feature_pack"], ensure_ascii=True, indent=2)}
            """
        ).strip()
        instructions = (
            "Focus on explaining feature usage and confidence rationale."
            if payload["explain_mode"]
            else "Provide a meteorological briefing."
        )
        return f"{content}\nAdditional instructions: {instructions}"

    def _parse_response(
        self,
        raw_text: str,
        prompt_summary: str,
        provider: str,
        meta: dict[str, Any] | None,
    ) -> ForecasterResponse:
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
                meta=meta,
            )

        sections = data.get("sections") or {}
        confidence = data.get("confidence") or {
            "value": 30,
            "rationale": "Model confidence not supplied.",
        }
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
            meta=meta,
        )

    def _fallback_response(
        self,
        payload: dict[str, Any],
        *,
        provider: str,
        prompt_summary: str,
        raw_text: str | None = None,
        meta: dict[str, Any] | None = None,
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
                "Feature Pack fields used: "
                + (", ".join(used_fields) if used_fields else "none supplied"),
            ],
        }
        confidence = {"value": 25, "rationale": "Offline fallback."}
        bottom_line = (
            "Bottom line: wx requires an AI provider configured to deliver a full forecast."
        )
        return ForecasterResponse(
            sections=sections,
            confidence=confidence,
            used_feature_fields=used_fields,
            bottom_line=bottom_line,
            raw_text=raw_text or json.dumps(sections, ensure_ascii=True),
            provider=provider,
            prompt_summary=prompt_summary,
            meta=meta,
        )

    def explain(
        self,
        *,
        question: str,
        feature_pack: dict[str, Any],
        command: str,
    ) -> dict[str, Any]:
        """Generate an explanation for the previous run and normalise the output."""

        response = self.generate(
            query=question,
            feature_pack=feature_pack,
            intent=f"explain:{command}",
            verbose=True,
            explain=True,
        )

        provider = response.provider or "offline"
        if provider.startswith("openrouter") or provider.startswith("gemini"):
            mode = "online"
        elif provider.startswith("offline"):
            mode = "offline"
        else:
            mode = "fallback"

        text = response.summary_text or response.bottom_line
        meta: dict[str, Any] = {
            "provider": provider,
            "confidence": response.confidence,
            "used_feature_fields": response.used_feature_fields,
            "bottom_line": response.bottom_line,
            "prompt_summary": response.prompt_summary,
        }
        if response.meta:
            meta.update(response.meta)

        return {
            "mode": mode,
            "text": text,
            "meta": meta,
            "response": response,
        }

    def _compose_prompt_summary(self, query: str, intent: str, verbose: bool, explain: bool) -> str:
        parts = [intent, query]
        if verbose:
            parts.append("verbose")
        if explain:
            parts.append("explain")
        return " | ".join(parts)

    def _enumerate_feature_fields(self, feature_pack: dict[str, Any]) -> list[str]:
        keys: list[str] = []
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
