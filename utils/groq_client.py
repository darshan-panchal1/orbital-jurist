"""
Groq API wrapper with retry, circuit breaker, and structured-output extraction.
"""
import json
import re
from typing import Any, Dict, List, Optional

from groq import Groq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from config import settings
from utils.logging_config import get_logger
from utils.resilience import get_circuit_breaker, CircuitBreakerOpenError

logger = get_logger("groq_client")

_groq_cb = get_circuit_breaker(
    "groq",
    failure_threshold=settings.CB_GROQ_FAILURE_THRESHOLD,
    recovery_timeout=settings.CB_GROQ_RECOVERY_TIMEOUT_S,
)

# Compiled once — strips ```json ... ``` or ``` ... ``` fences
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class GroqClient:
    """Wrapper for Groq API with retry, circuit breaker, and structured output support"""

    def __init__(self, model: str = None, temperature: float = None):
        self.model       = model       or settings.PHYSICS_MODEL
        self.temperature = temperature or settings.TEMPERATURE
        self._client     = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("GroqClient ready",
                    extra={"model": self.model, "temperature": self.temperature})

    # ── Internal retried call ────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, 30),
        reraise=True,
    )
    def _call_api(self, **kwargs) -> Any:
        return self._client.chat.completions.create(**kwargs)

    # ── Public chat interface ────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a chat completion with optional tool calling
        """
        kwargs: Dict[str, Any] = {
            "model":       self.model,
            "messages":    messages,
            "temperature": self.temperature,
            "max_tokens":  max_tokens or settings.MAX_TOKENS,
        }
        if tools:
            kwargs["tools"]       = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        logger.debug("Groq request",
                     extra={"model": self.model, "msg_count": len(messages)})
        try:
            response = _groq_cb.call(self._call_api, **kwargs)
        except CircuitBreakerOpenError as exc:
            logger.error("Groq circuit open", extra={"error": str(exc)})
            return {"error": str(exc), "content": None, "tool_calls": []}
        except Exception as exc:
            logger.error("Groq API failed after retries", extra={"error": str(exc)})
            return {"error": str(exc), "content": None, "tool_calls": []}

        return self._parse_response(response)

    # ── Structured JSON output ───────────────────────────────────────────────

    def structured_output(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Request JSON matching schema. Retries up to max_retries times on
        parse failure, appending the error to the conversation so the model
        can self-correct.
        """
        enhanced = messages.copy()
        schema_instruction = (
            "\n\nRespond ONLY with valid JSON (no markdown fences, no preamble) "
            f"matching this schema:\n{json.dumps(schema, indent=2)}"
        )
        enhanced[-1] = {
            **enhanced[-1],
            "content": enhanced[-1]["content"] + schema_instruction,
        }

        raw = ""
        for attempt in range(max_retries + 1):
            response = self.chat(enhanced)
            if response.get("error"):
                return response

            raw = response.get("content", "") or ""
            parsed, err = self._extract_json(raw)
            if parsed is not None:
                logger.debug("Structured output parsed OK",
                             extra={"attempt": attempt + 1})
                return parsed

            logger.warning("JSON parse failed — retrying",
                           extra={"attempt": attempt + 1, "error": err})
            enhanced.append({"role": "assistant", "content": raw})
            enhanced.append({
                "role":    "user",
                "content": (
                    f"Your previous response could not be parsed as JSON: {err}. "
                    "Please respond ONLY with valid JSON matching the schema."
                ),
            })

        return {
            "error": f"Failed to extract JSON after {max_retries + 1} attempts",
            "raw_content": raw,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _extract_json(self, text: str):
        """Try to extract JSON, stripping markdown fences first."""
        m = _JSON_FENCE_RE.search(text)
        candidate = m.group(1).strip() if m else text.strip()
        try:
            return json.loads(candidate), None
        except json.JSONDecodeError as exc:
            return None, str(exc)

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse Groq response into standardized format"""
        try:
            msg = response.choices[0].message
            result: Dict[str, Any] = {
                "content":       msg.content,
                "tool_calls":    [],
                "finish_reason": response.choices[0].finish_reason,
            }
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result["tool_calls"].append({
                        "id":       tc.id,
                        "function": {"name": tc.function.name, "arguments": args},
                    })
            return result
        except Exception as exc:
            logger.error("Response parse error", extra={"error": str(exc)})
            return {"error": "Response parsing failed", "content": None, "tool_calls": []}