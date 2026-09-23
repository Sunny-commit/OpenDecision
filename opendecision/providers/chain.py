"""Ordered provider fallback chains with attempt telemetry."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from ..errors import ProvidersExhaustedError
from ..models import DecisionQuestion
from .base import DecisionProvider


class ProviderChain:
    name = "provider_chain"

    def __init__(
        self,
        providers: list[DecisionProvider],
        *,
        terminal_answer: Mapping[str, Any] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("provider chain requires at least one provider")
        self.providers = providers
        self.terminal_answer = dict(terminal_answer) if terminal_answer else None

    def predict(
        self,
        state: Mapping[str, Any] | str,
        question: DecisionQuestion,
    ) -> Mapping[str, Any]:
        attempts: list[dict[str, Any]] = []
        for provider in self.providers:
            started = time.perf_counter()
            try:
                response = provider.predict(state, question)
                attempts.append(
                    {
                        "provider": provider.name,
                        "success": True,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                    }
                )
                return {
                    "answer": response.get("answer", response),
                    "raw": response.get("raw", response),
                    "provider": provider.name,
                    "attempts": attempts,
                }
            except Exception as exc:  # provider boundaries intentionally isolate failures
                attempts.append(
                    {
                        "provider": provider.name,
                        "success": False,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
        if self.terminal_answer is not None:
            return {
                "answer": self.terminal_answer,
                "raw": {"terminal_fallback": True},
                "provider": "terminal_fallback",
                "attempts": attempts,
            }
        raise ProvidersExhaustedError(f"all providers failed: {attempts}")
