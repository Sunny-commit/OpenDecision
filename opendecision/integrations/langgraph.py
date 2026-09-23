"""LangGraph-compatible helpers without a hard dependency on LangGraph."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..guard import DecisionGuard
from ..models import DecisionQuestion


def decision_node(guard: DecisionGuard, question: DecisionQuestion | Mapping[str, Any] | str, *, state_key: str | None = None, result_key: str = "decision_result") -> Callable[[Mapping[str, Any]], dict[str, Any]]:
    """Create a node function that returns a serializable decision result."""
    def node(state: Mapping[str, Any]) -> dict[str, Any]:
        decision_state: Any = state[state_key] if state_key else state
        result = guard.decide(decision_state, question)
        return {result_key: result.model_dump()}
    return node


def route_by_decision(*, result_key: str = "decision_result", decision_field: str = "decision") -> Callable[[Mapping[str, Any]], Any]:
    """Create a conditional-edge function for a LangGraph graph."""
    def route(state: Mapping[str, Any]) -> Any:
        result = state[result_key]
        if isinstance(result, Mapping):
            return result[decision_field]
        return getattr(result, decision_field)
    return route
