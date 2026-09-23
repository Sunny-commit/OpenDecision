"""DecisionGuard with strict validation, audit traces, and fail-safe behavior."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from .audit import AuditEvent, AuditSink
from .errors import ContractValidationError, ProviderError
from .models import DecisionContext, DecisionQuestion, DecisionResult, ProviderAttempt
from .providers.base import DecisionProvider
from .providers.laya import LayaProvider

FailureMode = Literal["raise", "review", "block"]


class DecisionGuard:
    """Evaluate typed contracts before an agent acts."""

    def __init__(
        self,
        provider: DecisionProvider | None = None,
        *,
        model: str = "router",
        audit_sink: AuditSink | None = None,
        failure_mode: FailureMode = "raise",
        max_state_bytes: int = 100_000,
    ) -> None:
        self.provider = provider or LayaProvider(model=model)
        self.audit_sink = audit_sink
        self.failure_mode = failure_mode
        self.max_state_bytes = max_state_bytes

    def decide(
        self,
        state: Mapping[str, Any] | str,
        question: DecisionQuestion | Mapping[str, Any] | str,
        *,
        context: DecisionContext | Mapping[str, Any] | None = None,
    ) -> DecisionResult:
        contract = DecisionQuestion.from_input(question)
        decision_context = (
            context
            if isinstance(context, DecisionContext)
            else DecisionContext.model_validate(context or {})
        )
        context_hash = self._validate_and_hash_state(state)
        try:
            output = self.provider.predict(state, contract)
            answer = output.get("answer", output)
            raw_output = output.get("raw", output)
            provider_name = str(output.get("provider", self.provider.name))
            attempts = [
                ProviderAttempt.model_validate(item) for item in output.get("attempts", [])
            ]
            result = self._normalize(
                answer,
                raw_output,
                contract,
                decision_context,
                context_hash,
                provider_name,
                attempts,
            )
        except Exception as exc:
            if self.failure_mode == "raise":
                if isinstance(exc, (ContractValidationError, ProviderError)):
                    raise
                raise ProviderError(str(exc)) from exc
            result = self._failure_result(contract, decision_context, context_hash, exc)
        self._audit(result, decision_context)
        return result

    def check(
        self,
        state: Mapping[str, Any] | str,
        *,
        decision: str,
        context: DecisionContext | Mapping[str, Any] | None = None,
    ) -> DecisionResult:
        return self.decide(
            state,
            DecisionQuestion(type="noul", instructions=decision),
            context=context,
        )

    def _validate_and_hash_state(self, state: Mapping[str, Any] | str) -> str:
        if isinstance(state, str):
            if not state.strip():
                raise ContractValidationError("state string cannot be empty")
            encoded = state.encode()
        elif isinstance(state, Mapping):
            try:
                encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
            except (TypeError, ValueError) as exc:
                raise ContractValidationError("state must be JSON serializable") from exc
        else:
            raise ContractValidationError("state must be a string or mapping")
        if len(encoded) > self.max_state_bytes:
            raise ContractValidationError(
                f"state exceeds configured limit of {self.max_state_bytes} bytes"
            )
        return hashlib.sha256(encoded).hexdigest()

    def _normalize(
        self,
        answer: Mapping[str, Any],
        raw_output: Any,
        question: DecisionQuestion,
        context: DecisionContext,
        context_hash: str,
        provider_name: str,
        attempts: list[ProviderAttempt],
    ) -> DecisionResult:
        if not isinstance(answer, Mapping):
            raise ContractValidationError("provider answer must be a mapping")
        common = {
            "provider": provider_name,
            "decision_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc),
            "context_hash": context_hash,
            "policy_id": context.policy_id,
            "policy_version": context.policy_version,
            "provider_attempts": attempts,
            "raw_output": raw_output,
        }
        if question.type == "choice":
            probabilities = _probabilities(answer.get("probabilities") or answer.get("probs"))
            decision = _first(answer, "choice", "label", "decision")
            choice_options = question.options or (
                question.criteria if isinstance(question.criteria, dict) else {}
            )
            labels = set(choice_options.keys())
            if decision not in labels:
                raise ContractValidationError(
                    f"provider choice {decision!r} is not one of {sorted(labels)}"
                )
            if probabilities and set(probabilities) != labels:
                raise ContractValidationError("provider probabilities must match declared options")
            confidence = _probability(_first(answer, "confidence"))
            if confidence is None and probabilities:
                confidence = probabilities[str(decision)]
            requires_review = str(decision) == "review"
            return DecisionResult(
                decision=str(decision),
                probabilities=probabilities,
                confidence=confidence,
                question_type="choice",
                requires_review=requires_review,
                metadata={"raw_answer": dict(answer)},
                **common,
            )
        if question.type == "score":
            score = _first(answer, "score", "value", "decision")
            if score is None:
                raise ContractValidationError("provider response did not contain a score")
            confidence = _probability(_first(answer, "confidence"))
            distribution = _probabilities(
                answer.get("distribution") or answer.get("probabilities")
            )
            return DecisionResult(
                decision=float(score),
                probabilities=distribution,
                confidence=confidence,
                question_type="score",
                metadata={"raw_answer": dict(answer)},
                **common,
            )
        probability = _probability(
            _first(answer, "noul", "probability", "confidence", "decision")
        )
        if probability is None:
            raise ContractValidationError("provider response did not contain a noul probability")
        decision = probability >= question.threshold
        return DecisionResult(
            decision=decision,
            probabilities={"true": probability, "false": 1.0 - probability},
            confidence=max(probability, 1.0 - probability),
            question_type="noul",
            metadata={"threshold": question.threshold, "raw_answer": dict(answer)},
            **common,
        )

    def _failure_result(
        self,
        question: DecisionQuestion,
        context: DecisionContext,
        context_hash: str,
        error: Exception,
    ) -> DecisionResult:
        review = self.failure_mode == "review"
        if question.type == "choice":
            choice_options = question.options or (
                question.criteria if isinstance(question.criteria, dict) else {}
            )
            labels = list(choice_options.keys())
            preferred = "review" if review and "review" in labels else "block"
            decision: str | bool = preferred if preferred in labels else labels[-1]
        else:
            decision = False
        return DecisionResult(
            decision=decision,
            probabilities={},
            confidence=None,
            question_type=question.type,
            provider="failure_policy",
            decision_id=str(uuid4()),
            created_at=datetime.now(timezone.utc),
            context_hash=context_hash,
            policy_id=context.policy_id,
            policy_version=context.policy_version,
            requires_review=review,
            metadata={
                "failure_mode": self.failure_mode,
                "error": f"{type(error).__name__}: {error}",
            },
        )

    def _audit(self, result: DecisionResult, context: DecisionContext) -> None:
        if self.audit_sink is None:
            return
        self.audit_sink.write(
            AuditEvent.from_result(
                result,
                actor=context.actor,
                tool=context.tool,
                action_id=context.action_id,
            )
        )


def _first(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if mapping.get(key) is not None:
            return mapping[key]
    return None


def _probability(value: Any) -> float | None:
    if value is None:
        return None
    probability = float(value)
    if not 0.0 <= probability <= 1.0:
        raise ContractValidationError(f"probability must be between 0 and 1, got {value}")
    return probability


def _probabilities(value: Any) -> dict[str, float]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ContractValidationError("probabilities must be a mapping")
    return {
        str(key): _probability(probability) for key, probability in value.items()
    }  # type: ignore[misc]
