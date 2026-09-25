"""Framework-agnostic tool protection helpers.

The decorator defined here is intentionally raw-Python and works with any agent
framework. It evaluates a decision contract before executing a tool and fails
closed for ambiguous outcomes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeVar

from .guard import DecisionGuard
from .models import DecisionQuestion, DecisionResult

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class ToolBlockedError(RuntimeError):
    result: DecisionResult


@dataclass
class ToolReviewRequiredError(RuntimeError):
    result: DecisionResult


def protect_tool(
    guard: DecisionGuard,
    question: DecisionQuestion | Mapping[str, Any] | str,
    *,
    state_builder: Callable[[tuple[Any, ...], dict[str, Any]], Mapping[str, Any] | str] | None = None,
    allow_value: str = "allow",
    review_value: str = "review",
    block_value: str = "block",
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Protect a tool call with a decision contract.

    The decorated function receives the same inputs, but is executed only when
    the decision matches allow_value. Review and block raise dedicated errors.
    """

    contract = DecisionQuestion.from_input(question)

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            if state_builder is None:
                state: Mapping[str, Any] | str = {
                    "tool": getattr(fn, "__name__", "tool"),
                    "args": args,
                    "kwargs": kwargs,
                }
            else:
                state = state_builder(args, kwargs)
            result = guard.decide(state, contract)
            if result.decision == allow_value:
                return fn(*args, **kwargs)
            if result.decision == review_value:
                raise ToolReviewRequiredError(result)
            raise ToolBlockedError(result)

        wrapped.__name__ = getattr(fn, "__name__", "wrapped")
        wrapped.__doc__ = fn.__doc__
        return wrapped

    return decorator
