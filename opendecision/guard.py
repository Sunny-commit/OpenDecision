"""DecisionGuard and provider-output normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import DecisionQuestion, DecisionResult
from .providers.base import DecisionProvider


class DecisionGuard:
    """Evaluate typed decision contracts before an agent takes an action."""

    def __init__(self, provider: DecisionProvider | None = None, *, model: str = "router") -> None:
        if provider is None:
            # Laya is optional; import lazily so importing opendecision doesn't require it.
            from .providers.laya import LayaProvider

            provider = LayaProvider(model=model)
        self.provider = provider

    def decide(
        self,
        state: Mapping[str, Any] | str,
        question: DecisionQuestion | Mapping[str, Any] | str,
    ) -> DecisionResult:
        """Evaluate a choice, score, or noul question and normalize its result."""
        contract = DecisionQuestion.from_input(question)
        output = self.provider.predict(state, contract)
        answer = output.get("answer", output)
        raw_output = output.get("raw", output)
        return self._normalize(answer, raw_output, contract)

    def check(self, state: Mapping[str, Any] | str, *, decision: str) -> DecisionResult:
        """Convenience method for a boolean allow/block gate."""
        return self.decide(state, DecisionQuestion(type="noul", instructions=decision))

    def _normalize(
        self,
        answer: Mapping[str, Any],
        raw_output: Any,
        question: DecisionQuestion,
    ) -> DecisionResult:
        if not isinstance(answer, Mapping):
            raise TypeError("decision provider must return a mapping for its answer")

        if question.type == "choice":
            probabilities = _float_mapping(answer.get("probabilities") or answer.get("probs"))
            decision = _first(answer, "choice", "label", "decision")
            if decision is None:
                raise ValueError("provider response did not contain a choice decision")
            confidence = _as_probability(_first(answer, "confidence"))
            if confidence is None and probabilities:
                confidence = max(probabilities.values())
            return DecisionResult(
                decision=str(decision),
                probabilities=probabilities,
                confidence=confidence,
                question_type="choice",
                provider=self.provider.name,
                metadata={"raw_answer": dict(answer)},
                raw_output=raw_output,
            )

        if question.type == "score":
            score = _first(answer, "score", "value", "decision")
            if score is None:
                raise ValueError("provider response did not contain a score decision")
            distribution = _float_mapping(answer.get("distribution") or answer.get("probabilities"))
            confidence = _as_probability(_first(answer, "confidence"))
            return DecisionResult(
                decision=float(score),
                probabilities=distribution,
                confidence=confidence,
                question_type="score",
                provider=self.provider.name,
                metadata={"raw_answer": dict(answer)},
                raw_output=raw_output,
            )

        probability = _as_probability(
            _first(answer, "noul", "probability", "confidence", "decision")
        )
        if probability is None:
            raise ValueError("provider response did not contain a noul probability")
        decision = probability >= question.threshold
        return DecisionResult(
            decision=decision,
            probabilities={"true": probability, "false": 1.0 - probability},
            confidence=max(probability, 1.0 - probability),
            question_type="noul",
            provider=self.provider.name,
            metadata={"threshold": question.threshold, "raw_answer": dict(answer)},
            raw_output=raw_output,
        )


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if mapping.get(key) is not None:
            return mapping[key]
    return None


def _as_probability(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"probability must be between 0 and 1, got {value}")
    return value


def _float_mapping(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): float(probability) for key, probability in value.items()}
