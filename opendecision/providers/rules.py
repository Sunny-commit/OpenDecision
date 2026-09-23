from __future__ import annotations
import re
from collections.abc import Mapping
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from ..models import DecisionQuestion
RuleOperator = Literal["equals", "contains", "in", "regex", "exists"]

class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    operator: RuleOperator
    value: Any = None
    decision: str | bool | float
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    def matches(self, state: Mapping[str, Any]) -> bool:
        actual: Any = state
        for part in self.field.split("."):
            if not isinstance(actual, Mapping) or part not in actual: return False
            actual = actual[part]
        if self.operator == "exists": return actual is not None
        if self.operator == "equals": return bool(actual == self.value)
        if self.operator == "contains": return str(self.value).casefold() in str(actual).casefold()
        if self.operator == "in": return bool(actual in self.value)
        if self.operator == "regex": return re.search(str(self.value), str(actual), re.IGNORECASE) is not None
        return False

class RuleProvider:
    name = "rules"
    def __init__(self, rules: list[Rule], *, default: str | bool | float | None = None) -> None:
        self.rules, self.default = rules, default
    def predict(self, state: Mapping[str, Any] | str, question: DecisionQuestion) -> Mapping[str, Any]:
        payload = state if isinstance(state, Mapping) else {"input": state}
        for rule in self.rules:
            if rule.matches(payload): return {"answer": _answer(question, rule.decision, rule.confidence), "raw": {"rule": rule.model_dump()}}
        if self.default is None: raise LookupError("no deterministic rule matched")
        return {"answer": _answer(question, self.default, 1.0), "raw": {"default": True}}

def _answer(question: DecisionQuestion, decision: str | bool | float, confidence: float) -> dict[str, Any]:
    if question.type == "choice":
        choices = question.options or (question.criteria if isinstance(question.criteria, dict) else {})
        labels = list(choices.keys())
        if str(decision) not in labels: raise ValueError(f"rule decision {decision!r} is not a declared option")
        remaining = (1.0 - confidence) / max(len(labels) - 1, 1)
        probabilities = {label: (confidence if label == decision else remaining) for label in labels}
        return {"choice": str(decision), "probabilities": probabilities, "confidence": confidence}
    if question.type == "score": return {"score": float(decision), "confidence": confidence}
    return {"noul": confidence if bool(decision) else 1.0 - confidence}
