"""
LLM Gateway — Phase 10: LLM Layer Architecture
Grounded in ESP APM LLM Architecture Design (Phase 10 §8)

Provides an OpenAI-compatible HTTP transport layer for local inference servers:
  - Ollama (http://localhost:11434/v1)
  - vLLM, LM Studio, or any OpenAI-compatible endpoint

Features:
  - Configurable timeout, exponential backoff retries (max 3)
  - Structured telemetry: tokens, latency_ms, model version
  - Offline/mock mode: deterministic responses when LLM_OFFLINE=1
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (from environment)
# ---------------------------------------------------------------------------
# Defaults to llama.cpp HTTP server (llama-server) on CPU (http://localhost:8080/v1)
LLM_GATEWAY_URL: str = os.getenv("LLM_GATEWAY_URL", "http://localhost:8080/v1")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "qwen2.5-3b-instruct")
LLM_TIMEOUT_SEC: float = float(os.getenv("LLM_TIMEOUT_SEC", "1.5"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "1"))
LLM_OFFLINE: bool = os.getenv("LLM_OFFLINE", "0").strip() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Response Schema
# ---------------------------------------------------------------------------
@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMGatewayResponse:
    content: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    latency_ms: float = 0.0
    is_mock: bool = False
    finish_reason: str = "stop"


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------
class LLMGateway:
    """
    OpenAI-compatible HTTP transport layer for local LLM inference via llama.cpp (llama-server).
    LangGraph → LLM Adapter → LLM Gateway → llama.cpp (CPU) / Qwen GGUF
    """

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_sec: Optional[float] = None,
        max_retries: Optional[int] = None,
        offline_mode: Optional[bool] = None,
    ):
        self.gateway_url = (gateway_url or LLM_GATEWAY_URL).rstrip("/")
        self.model_name = model_name or LLM_MODEL_NAME
        self.timeout_sec = timeout_sec if timeout_sec is not None else LLM_TIMEOUT_SEC
        self.max_retries = max_retries if max_retries is not None else LLM_MAX_RETRIES
        self.offline_mode = offline_mode if offline_mode is not None else LLM_OFFLINE

    def is_available(self) -> bool:
        """Probe the llama.cpp / OpenAI health endpoint."""
        health_urls = [
            self.gateway_url.replace("/v1", "") + "/health",
            f"{self.gateway_url}/models",
        ]
        for url in health_urls:
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue
        return False

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 180,
    ) -> LLMGatewayResponse:
        """
        POST to /v1/chat/completions with exponential backoff retries.
        Falls back to deterministic mock response if offline_mode=True or server unreachable.
        """
        if self.offline_mode or not self.is_available():
            logger.info("LLMGateway: Server offline or unavailable — returning fast mock response.")
            return self._mock_response(messages)

        payload = json.dumps({
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode("utf-8")

        url = f"{self.gateway_url}/chat/completions"
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                t0 = time.monotonic()
                req = urllib.request.Request(
                    url,
                    data=payload,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                    raw = resp.read().decode("utf-8")
                    latency_ms = (time.monotonic() - t0) * 1000
                    data = json.loads(raw)
                    return self._parse_response(data, latency_ms)

            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                wait = min(2 ** attempt, 8)
                logger.warning(
                    f"LLMGateway: attempt {attempt + 1}/{self.max_retries} failed ({exc}). "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)

        logger.error(
            f"LLMGateway: all {self.max_retries} attempts failed. "
            f"Last error: {last_exc}. Returning offline mock response."
        )
        return self._mock_response(messages)

    def _parse_response(self, data: Dict[str, Any], latency_ms: float) -> LLMGatewayResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "").strip()
        finish_reason = choice.get("finish_reason", "stop")

        usage_raw = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        )

        logger.info(
            f"LLMGateway: response received. "
            f"model={data.get('model', self.model_name)} "
            f"tokens={usage.total_tokens} latency={latency_ms:.0f}ms"
        )
        return LLMGatewayResponse(
            content=content,
            model=data.get("model", self.model_name),
            usage=usage,
            latency_ms=latency_ms,
            is_mock=False,
            finish_reason=finish_reason,
        )

    def _mock_response(self, messages: List[Dict[str, str]]) -> LLMGatewayResponse:
        """
        Deterministic offline mock response. Returns structured JSON that the
        structured_output parser can validate. Used in CI and when LLM is offline.
        """
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            ""
        )
        mock_content = json.dumps({
            "assessment": "Asset is operating within tolerable parameters. Monitoring recommended.",
            "hypotheses": [
                {
                    "cause": "Intake Gas Interference",
                    "confidence": 0.72,
                    "supporting_evidence": ["EV-001"],
                    "contradicting_evidence": []
                }
            ],
            "uncertainties": ["Insufficient historical data for multi-window trend correlation."],
            "recommendation": "Maintain current parameters. Schedule intake pressure inspection.",
            "verification": "Confirm PIP readings against SCADA gauge within 4 hours.",
            "_mock": True,
            "_query_echo": last_user_msg[:80],
        })
        logger.info("LLMGateway: returning deterministic mock advisory response.")
        return LLMGatewayResponse(
            content=mock_content,
            model=f"{self.model_name}-mock",
            usage=LLMUsage(prompt_tokens=80, completion_tokens=120, total_tokens=200),
            latency_ms=1.0,
            is_mock=True,
            finish_reason="stop",
        )
