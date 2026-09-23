"""Decision guard with strict validation, audit traces, and fail-safe behavior."""
from __future__ import annotations
import hashlib, json
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
    def __init__(self, provider: DecisionProvider | None = None, *, model: str = "router", audit_sink: AuditSink | None = None, failure_mode: FailureMode = "raise", max_state_bytes: int = 100_000) -> None:
        self.provider, self.audit_sink, self.failure_mode, self.max_state_bytes = provider or LayaProvider(model=model), audit_sink, failure_mode, max_state_bytes
    def decide(self, state: Mapping[str, Any] | str, question: DecisionQuestion | Mapping[str, Any] | str, *, context: DecisionContext | Mapping[str, Any] | None = None) -> DecisionResult:
        contract = DecisionQuestion.from_input(question)
        ctx = context if isinstance(context, DecisionContext) else DecisionContext.model_validate(context or {})
        context_hash = self._hash(state)
        try:
            output = self.provider.predict(state, contract)
            result = self._normalize(output.get("answer", output), output.get("raw", output), contract, ctx, context_hash, str(output.get("provider", self.provider.name)), [ProviderAttempt.model_validate(x) for x in output.get("attempts", [])])
        except Exception as exc:
            if self.failure_mode == "raise":
                if isinstance(exc, (ContractValidationError, ProviderError)): raise
                raise ProviderError(str(exc)) from exc
            result = self._failure(contract, ctx, context_hash, exc)
        if self.audit_sink: self.audit_sink.write(AuditEvent.from_result(result, actor=ctx.actor, tool=ctx.tool, action_id=ctx.action_id))
        return result
    def check(self, state: Mapping[str, Any] | str, *, decision: str, context: DecisionContext | Mapping[str, Any] | None = None) -> DecisionResult:
        return self.decide(state, DecisionQuestion(type="noul", instructions=decision), context=context)
    def _hash(self, state: Mapping[str, Any] | str) -> str:
        if isinstance(state, str):
            if not state.strip(): raise ContractValidationError("state string cannot be empty")
            data = state.encode()
        elif isinstance(state, Mapping):
            try: data = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
            except (TypeError, ValueError) as exc: raise ContractValidationError("state must be JSON serializable") from exc
        else: raise ContractValidationError("state must be a string or mapping")
        if len(data) > self.max_state_bytes: raise ContractValidationError(f"state exceeds configured limit of {self.max_state_bytes} bytes")
        return hashlib.sha256(data).hexdigest()
    def _normalize(self, answer: Mapping[str, Any], raw: Any, q: DecisionQuestion, ctx: DecisionContext, context_hash: str, provider: str, attempts: list[ProviderAttempt]) -> DecisionResult:
        if not isinstance(answer, Mapping): raise ContractValidationError("provider answer must be a mapping")
        common = dict(provider=provider, decision_id=str(uuid4()), created_at=datetime.now(timezone.utc), context_hash=context_hash, policy_id=ctx.policy_id, policy_version=ctx.policy_version, provider_attempts=attempts, raw_output=raw)
        if q.type == "choice":
            probs = _probs(answer.get("probabilities") or answer.get("probs")); decision = _first(answer, "choice", "label", "decision")
            choices = q.options or (q.criteria if isinstance(q.criteria, dict) else {}); labels = set(choices)
            if decision not in labels: raise ContractValidationError(f"provider choice {decision!r} is not one of {sorted(labels)}")
            if probs and set(probs) != labels: raise ContractValidationError("provider probabilities must match declared options")
            confidence = _prob(_first(answer, "confidence")) or (probs.get(str(decision)) if probs else None)
            return DecisionResult(decision=str(decision), probabilities=probs, confidence=confidence, question_type="choice", requires_review=str(decision) == "review", metadata={"raw_answer": dict(answer)}, **common)
        if q.type == "score":
            score = _first(answer, "score", "value", "decision")
            if score is None: raise ContractValidationError("provider response did not contain a score")
            return DecisionResult(decision=float(score), probabilities=_probs(answer.get("distribution") or answer.get("probabilities")), confidence=_prob(_first(answer, "confidence")), question_type="score", metadata={"raw_answer": dict(answer)}, **common)
        p = _prob(_first(answer, "noul", "probability", "confidence", "decision"))
        if p is None: raise ContractValidationError("provider response did not contain a noul probability")
        return DecisionResult(decision=p >= q.threshold, probabilities={"true": p, "false": 1-p}, confidence=max(p,1-p), question_type="noul", metadata={"threshold": q.threshold, "raw_answer": dict(answer)}, **common)
    def _failure(self, q: DecisionQuestion, ctx: DecisionContext, context_hash: str, error: Exception) -> DecisionResult:
        review = self.failure_mode == "review"
        if q.type == "choice":
            choices = q.options or (q.criteria if isinstance(q.criteria, dict) else {}); labels = list(choices); preferred = "review" if review and "review" in labels else "block"; decision: str | bool = preferred if preferred in labels else labels[-1]
        else: decision = False
        return DecisionResult(decision=decision, probabilities={}, confidence=None, question_type=q.type, provider="failure_policy", decision_id=str(uuid4()), created_at=datetime.now(timezone.utc), context_hash=context_hash, policy_id=ctx.policy_id, policy_version=ctx.policy_version, requires_review=review, metadata={"failure_mode": self.failure_mode, "error": f"{type(error).__name__}: {error}"})

def _first(m: Mapping[str, Any], *keys: str) -> Any:
    return next((m[k] for k in keys if m.get(k) is not None), None)
def _prob(value: Any) -> float | None:
    if value is None: return None
    p=float(value)
    if not 0<=p<=1: raise ContractValidationError(f"probability must be between 0 and 1, got {value}")
    return p
def _probs(value: Any) -> dict[str,float]:
    if value is None: return {}
    if not isinstance(value, Mapping): raise ContractValidationError("probabilities must be a mapping")
    return {str(k): float(_prob(v)) for k,v in value.items()}
